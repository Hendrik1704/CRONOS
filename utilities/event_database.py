#!/usr/bin/env python3
"""Manage merged HDF5 databases built from CRONOS per-event `.h5` files.

CRONOS typically produces one HDF5 file per event (e.g. `run/job_17/event_0.h5`).
For downstream analysis it can be convenient to have a single "database" HDF5
with one group per event.

This utility copies datasets losslessly (no parsing) into an output file:

    /job_17/event_0/<datasets...>

Typical usage:
    python utilities/event_database.py build --pattern 'run/job_*/event_*.h5' \
        --out merged_events.h5 --validate
    # Save disk space by deleting originals after successful merge:
    python utilities/event_database.py build --pattern 'run/job_*/event_*.h5' \
        --out merged_events.h5 --validate --delete-source

Notes:
- This keeps CRONOS' current storage model (datasets often contain full text
  blobs), matching your preference to not change simulation outputs.
- Validation is shallow by default (checks dataset presence), but catches the
  most common broken/partial events.
- `build` appends to an existing database, so it can be rerun when more jobs
  have finished. The job is taken from the `job_<N>` directory closest to the
  event file. An event file is never merged over a different event that is
  already stored under the same `/job_<N>/event_<M>` group; such files are
  skipped (and not deleted). Rerunning on the same unchanged source file
  (same path, size and modification time) keeps the stored event.
- Exit codes: `build` returns 2 if any file was skipped; `prune` returns 2 if
  it deleted at least one event group and 0 otherwise (always 0 with
  --dry-run).

Additional subcommands:
    # Remove unstable/broken events from an existing database:
    python utilities/event_database.py prune merged_events.h5 --required ...

    # Combine multiple merged databases into one:
    python utilities/event_database.py combine --out combined.h5 db1.h5 db2.h5
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import h5py


DEFAULT_REQUIRED_DATASETS: tuple[str, ...] = (
    "particle_9999_vndata_eta_-0.5_0.5.dat",
    "particle_9999_vndata_diff_eta_0.5_2.5.dat",
    "particle_211_vndata_diff_y_-0.5_0.5.dat",
    "particle_321_vndata_diff_y_-0.5_0.5.dat",
    "particle_2212_vndata_diff_y_-0.5_0.5.dat",
    "particle_-211_vndata_diff_y_-0.5_0.5.dat",
    "particle_-321_vndata_diff_y_-0.5_0.5.dat",
    "particle_-2212_vndata_diff_y_-0.5_0.5.dat",
    "particle_3122_vndata_diff_y_-0.5_0.5.dat",
    "particle_3312_vndata_diff_y_-0.5_0.5.dat",
    "particle_3334_vndata_diff_y_-0.5_0.5.dat",
    "particle_-3122_vndata_diff_y_-0.5_0.5.dat",
    "particle_-3312_vndata_diff_y_-0.5_0.5.dat",
    "particle_-3334_vndata_diff_y_-0.5_0.5.dat",
    "particle_333_vndata_diff_y_-0.5_0.5.dat",
)


@dataclass(frozen=True)
class EventRef:
    source_file: Path
    job_name: str
    event_name: str

    @property
    def group_path(self) -> str:
        return f"/{self.job_name}/{self.event_name}"


_JOB_RE = re.compile(r"job_(\d+)")
_EVENT_RE = re.compile(r"event_(\d+)\.h5$")


def discover_event_files(pattern: str) -> list[Path]:
    paths = [Path(p).resolve() for p in glob.glob(pattern, recursive=True)]
    paths = [p for p in paths if p.is_file() and p.suffix == ".h5"]
    return sorted(paths)


def event_ref_from_path(p: Path) -> EventRef:
    # Infer job/event from path conventions. Use the job_# directory closest
    # to the event file (normally its parent), so that a job_# component
    # further up the path (e.g. a scratch dir named job_123) is ignored.
    job_match = None
    for part in reversed(p.parent.parts):
        m = _JOB_RE.fullmatch(part)
        if m:
            job_match = m
            break
    if not job_match:
        raise ValueError(f"Could not infer job_# from path: {p}")

    event_match = _EVENT_RE.search(p.name)
    if not event_match:
        raise ValueError(f"Could not infer event_# from filename: {p.name}")

    job_name = f"job_{job_match.group(1)}"
    event_name = f"event_{event_match.group(1)}"
    return EventRef(source_file=p, job_name=job_name, event_name=event_name)


def has_required_datasets(
    h5f: h5py.File, required: Iterable[str]
) -> tuple[bool, tuple[str, ...]]:
    required = tuple(required)
    keys = set(h5f.keys())
    missing = tuple(name for name in required if name not in keys)
    return (len(missing) == 0, missing)


def iter_event_groups(h5f: h5py.File) -> Iterator[tuple[str, h5py.Group]]:
    """Yield (group_path, group) for each event group in a merged database.

    Supported layouts:
    1) CRONOS merged DB (this script):
        /job_17/event_0/<datasets...>
    2) Legacy flat layout (common in other frameworks):
        /spvn_results_1234/<datasets...>
    """

    # Preferred CRONOS layout
    job_names = [k for k in h5f.keys() if _JOB_RE.fullmatch(k)]
    for job_name in sorted(job_names):
        job_group = h5f[job_name]
        for event_name in sorted(job_group.keys()):
            if event_name.startswith("event_") and isinstance(
                job_group[event_name], h5py.Group
            ):
                grp = job_group[event_name]
                yield (f"/{job_name}/{event_name}", grp)

    # Legacy flat layout
    for k in sorted(h5f.keys()):
        if k.startswith("spvn_results_") and isinstance(h5f[k], h5py.Group):
            yield (f"/{k}", h5f[k])


def copy_event_file(
    src_path: Path,
    out_h5: h5py.File,
    ref: EventRef,
) -> None:
    # Ensure groups exist.
    job_group = out_h5.require_group(ref.job_name)
    stat = src_path.stat()
    if ref.event_name in job_group:
        attrs = job_group[ref.event_name].attrs
        existing_src = attrs.get("source_file", "")
        if not existing_src:
            # No source attributes: an incomplete copy (e.g. the process was
            # killed), which is replaced
            print(f"REPAIR {ref.group_path}: incomplete earlier copy")
            del job_group[ref.event_name]
            return copy_event_file(src_path, out_h5, ref)
        if existing_src == str(src_path) and (
            "source_size" not in attrs
            or (
                attrs["source_size"] == stat.st_size
                and attrs["source_mtime"] == stat.st_mtime
            )
        ):
            # The same file was merged before (databases written before
            # size and mtime were recorded only store the path)
            return
        # A different event file (or a new file at a reused path, e.g. a
        # run directory prepared again) maps to the same group: never
        # overwrite.
        raise ValueError(
            f"{ref.group_path} already exists in the database "
            f"(from {existing_src or 'an unknown source'})"
        )

    with h5py.File(src_path, "r") as in_h5:
        event_group = job_group.create_group(ref.event_name)
        try:
            # New format: datasets are stored inside an event_{id} group.
            # Navigate into it if present; fall back to the file root.
            inner: h5py.Group = (
                in_h5[ref.event_name]
                if ref.event_name in in_h5 and isinstance(in_h5[ref.event_name], h5py.Group)
                else in_h5
            )
            for key in inner.keys():
                inner.copy(inner[key], event_group, name=key)
            # The source attributes mark the group as complete, so they are
            # only written after all datasets were copied
            event_group.attrs["source_file"] = str(src_path)
            event_group.attrs["source_size"] = stat.st_size
            event_group.attrs["source_mtime"] = stat.st_mtime
        except BaseException:
            # Do not leave a partially copied event behind (also on Ctrl+C).
            del job_group[ref.event_name]
            raise


def cmd_build(args: argparse.Namespace) -> int:
    event_files = discover_event_files(args.pattern)
    if not event_files:
        print(f"No files matched: {args.pattern}", file=sys.stderr)
        return 2

    required = tuple(args.required)
    out_path = Path(args.out).resolve()

    # Safety: refuse to write output to a path that is also an input.
    if out_path in event_files:
        print(
            f"Refusing to overwrite input file with output: {out_path}",
            file=sys.stderr,
        )
        return 2

    # Append to an existing database so that incremental builds (e.g. after
    # earlier sources were removed with --delete-source) keep previous events.
    if out_path.exists():
        try:
            with h5py.File(out_path, "r") as h5f:
                is_db = bool(h5f.attrs.get("cronos_event_database", False))
        except OSError as e:
            print(f"Cannot open existing output {out_path}: {e}", file=sys.stderr)
            return 2
        if not is_db:
            print(
                f"Refusing to append to {out_path}: not a CRONOS event database",
                file=sys.stderr,
            )
            return 2

    included = 0
    skipped = 0

    with h5py.File(out_path, "a") as out_h5:
        out_h5.attrs["cronos_event_database"] = True
        out_h5.attrs["source_pattern"] = args.pattern
        out_h5.attrs["required_datasets"] = list(required)

        for src in event_files:
            try:
                ref = event_ref_from_path(src)
            except ValueError as e:
                skipped += 1
                print(f"SKIP {src} ({e})", file=sys.stderr)
                continue

            if args.validate:
                try:
                    with h5py.File(src, "r") as in_h5:
                        # Navigate into the inner event group if present (new format).
                        inner: h5py.Group = (
                            in_h5[ref.event_name]
                            if ref.event_name in in_h5 and isinstance(in_h5[ref.event_name], h5py.Group)
                            else in_h5
                        )
                        ok, missing = has_required_datasets(inner, required)
                except Exception as e:
                    skipped += 1
                    print(f"SKIP {src} (unreadable: {e})", file=sys.stderr)
                    continue
                if not ok:
                    skipped += 1
                    if not args.quiet:
                        miss_str = ", ".join(missing)
                        print(f"SKIP {src} (missing: {miss_str})")
                    continue

            try:
                copy_event_file(src, out_h5, ref)
                # Ensure we persist the copied data before optionally deleting.
                out_h5.flush()
            except Exception as e:
                skipped += 1
                print(f"SKIP {src} (copy failed: {e})", file=sys.stderr)
                continue

            included += 1
            if not args.quiet:
                print(f"ADD  {src} -> {ref.group_path}")

            if args.delete_source:
                try:
                    src.unlink()
                    if not args.quiet:
                        print(f"DEL  {src}")
                except Exception as e:
                    print(
                        f"WARN could not delete source file {src}: {e}",
                        file=sys.stderr,
                    )

    print(f"Wrote {out_path}")
    print(f"Included {included}, skipped {skipped}")
    return 0 if skipped == 0 else 2


def cmd_prune(args: argparse.Namespace) -> int:
    db_path = Path(args.database).resolve()
    if not db_path.exists():
        print(f"Missing database file: {db_path}", file=sys.stderr)
        return 2

    required = tuple(args.required)
    deleted = 0
    kept = 0

    with h5py.File(db_path, "a") as h5f:
        to_delete: list[str] = []
        for group_path, grp in iter_event_groups(h5f):
            ok, missing = has_required_datasets(grp, required)
            if ok:
                kept += 1
                continue
            to_delete.append(group_path)
            if not args.quiet:
                miss_str = ", ".join(missing)
                print(f"BAD  {group_path} (missing: {miss_str})")

        if args.dry_run:
            if not args.quiet:
                for gp in to_delete:
                    print(f"DRY  would delete {gp}")
        else:
            for gp in to_delete:
                # Delete by path (strip leading slash for h5py)
                del h5f[gp.lstrip("/")]
                deleted += 1
                if not args.quiet:
                    print(f"DEL  {gp}")

    print(f"Checked: kept {kept}, deleted {deleted}")
    return 0 if deleted == 0 else 2


def cmd_combine(args: argparse.Namespace) -> int:
    out_path = Path(args.out).resolve()
    input_paths = [Path(p).resolve() for p in args.inputs]
    if len(input_paths) < 2:
        print("Need at least two input database files.", file=sys.stderr)
        return 2

    for p in input_paths:
        if not p.exists():
            print(f"Missing input database: {p}", file=sys.stderr)
            return 2
        if p == out_path:
            print(
                f"Output file must be different from inputs: {out_path}",
                file=sys.stderr,
            )
            return 2

    def resolve_conflict(name: str, existing: Iterable[str], what: str) -> str:
        if name not in existing:
            return name
        if args.on_conflict == "error":
            raise ValueError(f"Conflict on {what} '{name}'")
        if args.on_conflict == "overwrite":
            return name
        # rename
        i = 1
        while f"{name}__{i}" in existing:
            i += 1
        return f"{name}__{i}"

    def copy_group(src: h5py.Group, name: str, dst: h5py.Group, what: str):
        # Copy src[name] into dst, applying the --on-conflict policy.
        target_name = resolve_conflict(name, dst.keys(), what)
        if args.on_conflict == "overwrite" and target_name in dst:
            del dst[target_name]
        src.copy(src[name], dst, name=target_name)
        if not args.quiet:
            src_disp = f"{in_path}:{src[name].name}"
            dst_disp = f"{out_path}:{dst.name.rstrip('/')}/{target_name}"
            print(f"ADD  {src_disp} -> {dst_disp}")

    # Job groups (/job_N) are merged at the event level, so that events of
    # the same job coming from different databases end up in the same job
    # group; only colliding event groups are renamed (event_M__K), which keeps
    # them visible to iter_event_groups(). Other top-level objects are copied
    # as a whole.
    written = 0
    try:
        with h5py.File(out_path, "w") as out_h5:
            out_h5.attrs["cronos_event_database"] = True
            out_h5.attrs["combined_from"] = [str(p) for p in input_paths]

            for in_path in input_paths:
                with h5py.File(in_path, "r") as in_h5:
                    for top_name in in_h5.keys():
                        is_job = _JOB_RE.fullmatch(top_name) and isinstance(
                            in_h5[top_name], h5py.Group
                        )
                        if not is_job:
                            copy_group(in_h5, top_name, out_h5, "top-level group")
                            written += 1
                            continue
                        job_out = out_h5.require_group(top_name)
                        for ev_name in in_h5[top_name].keys():
                            copy_group(
                                in_h5[top_name],
                                ev_name,
                                job_out,
                                f"event group '/{top_name}'",
                            )
                            written += 1
    except ValueError as e:
        print(f"ERROR {e} (use --on-conflict rename/overwrite)", file=sys.stderr)
        # Do not leave a partially combined database behind
        out_path.unlink(missing_ok=True)
        return 2

    print(f"Wrote {out_path} (copied {written} group(s))")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge CRONOS per-event HDF5 files into one database"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Build a merged HDF5 database")
    p_build.add_argument(
        "--pattern",
        required=True,
        help="Glob for event files, e.g. 'run/job_*/event_*.h5'",
    )
    p_build.add_argument(
        "--out",
        required=True,
        help="Output HDF5 filename",
    )
    p_build.add_argument(
        "--validate",
        action="store_true",
        help="Skip files that miss required datasets",
    )
    p_build.add_argument(
        "--required",
        nargs="*",
        default=list(DEFAULT_REQUIRED_DATASETS),
        help="Required dataset names (used with --validate)",
    )
    p_build.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file logs",
    )
    p_build.add_argument(
        "--delete-source",
        dest="delete_source",
        action="store_true",
        help=(
            "Delete each per-event input .h5 after it is successfully copied "
            "into the output database. Skipped/failed inputs are not deleted."
        ),
    )
    p_build.set_defaults(func=cmd_build)

    p_prune = sub.add_parser(
        "prune",
        help=(
            "Check an existing merged database and delete unstable/broken "
            "event groups. Exits with 2 if any group was deleted."
        ),
    )
    p_prune.add_argument(
        "database",
        help="Path to an existing merged database .h5 file",
    )
    p_prune.add_argument(
        "--required",
        nargs="*",
        default=list(DEFAULT_REQUIRED_DATASETS),
        help="Dataset names that must exist inside each event group.",
    )
    p_prune.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be deleted; do not modify the file.",
    )
    p_prune.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-group logs",
    )
    p_prune.set_defaults(func=cmd_prune)

    p_combine = sub.add_parser(
        "combine",
        help="Combine multiple merged database HDF5 files into one",
    )
    p_combine.add_argument(
        "--out",
        required=True,
        help="Output HDF5 filename",
    )
    p_combine.add_argument(
        "--on-conflict",
        choices=("error", "overwrite", "rename"),
        default="rename",
        help=(
            "What to do if two inputs contain the same event group "
            "(/job_N/event_M) or the same other top-level group. "
            "'rename' (default) appends __N to the later one (e.g. "
            "/job_0/event_0__1), 'overwrite' keeps the last one, 'error' stops."
        ),
    )
    p_combine.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-group logs",
    )
    p_combine.add_argument(
        "inputs",
        nargs="+",
        help="Two or more input merged database .h5 files",
    )
    p_combine.set_defaults(func=cmd_combine)

    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
