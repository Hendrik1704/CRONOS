#!/usr/bin/env python3
"""Bin CRONOS events into centrality classes using Nch from event HDF5.

Centrality observable (default):
- Read dataset `particle_9999_vndata_eta_-0.5_0.5.dat`
- Use the row with `n==0`
- Take `Q0_real` as the event multiplicity proxy (Nch / dN/dy)

The script outputs one text file per bin listing:
    event_file_path   Nch

Typical usage:
    python utilities/centrality_binning.py run/ --pattern 'run/job_*/event_*.h5'

Optionally it can also create directories and symlink the event files
(`<out-dir>/<bin>/job_<N>/event_<M>.h5`, using relative symlinks).

Event files that cannot be read are skipped with a message; the exit code is
then 2 (0 if all files were used).
"""

from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import h5py
import numpy as np


DEFAULT_CENTRALITY_CUTS = (0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)

NCH_KEY = "particle_9999_vndata_eta_-0.5_0.5.dat"

_JOB_RE = re.compile(r"job_\d+")


@dataclass(frozen=True)
class EventNch:
    path: Path
    nch: float


def _read_text_dataset(h5obj: h5py.File | h5py.Group, key: str) -> str:
    ds = h5obj[key]
    data = ds[()]
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8", errors="replace")
    if isinstance(data, str):
        return data
    # Numeric array stored by zip_into_hdf5 (np.genfromtxt / float32).
    # Reconstruct text, prepending the header attribute if present.
    buf = io.StringIO()
    header_attr = ds.attrs.get("header", None)
    if header_attr is not None:
        raw = header_attr
        if isinstance(raw, (bytes, bytearray, np.bytes_)):
            raw = raw.decode("utf-8", errors="replace")
        buf.write(str(raw) + "\n")
    np.savetxt(buf, np.atleast_2d(data))
    return buf.getvalue()


def _load_table(text: str) -> np.ndarray:
    return np.loadtxt(io.StringIO(text), comments="#")


def _extract_nch_from_event_file(event_h5: Path) -> float:
    with h5py.File(event_h5, "r") as h5f:
        # Navigate into the inner event group if present (new format).
        event_keys = [
            k for k in h5f.keys()
            if k.startswith("event_") and isinstance(h5f[k], h5py.Group)
        ]
        h5obj: h5py.Group = h5f[event_keys[0]] if len(event_keys) == 1 else h5f
        text = _read_text_dataset(h5obj, NCH_KEY)
        table = _load_table(text)

    # expected columns: n, Qn_real, Qn_real_err, Qn_imag, Qn_imag_err
    # pick the row where n==0.
    if table.ndim == 1:
        # single-row edge case
        n = int(table[0])
        if n != 0:
            raise ValueError(f"Unexpected n={n} in {event_h5}")
        return float(table[1])

    n_col = table[:, 0].astype(int)
    idx = np.where(n_col == 0)[0]
    if len(idx) != 1:
        raise ValueError(f"Could not uniquely find n=0 row in {event_h5}")
    return float(table[idx[0], 1])


def glob_in_directory(directory: Path, pattern: str) -> list[str]:
    """Glob `pattern` relative to `directory` (absolute patterns are used as is).

    A relative pattern that starts with `directory` itself, as in
    `run/ --pattern 'run/job_*/event_*.h5'`, is used as given.
    """
    if os.path.isabs(pattern):
        return glob.glob(pattern, recursive=True)
    # A pattern that already starts with the directory, as in
    # `run/ --pattern 'run/job_*/event_*.h5'`, is used as given; any other
    # pattern only matches inside the directory
    paths = [str(directory)]
    try:
        paths.append(os.path.relpath(str(directory)))
    except ValueError:  # e.g. another drive on Windows
        pass
    prefixes = tuple(os.path.normpath(path) + os.sep for path in paths)
    if os.path.normpath(pattern).startswith(prefixes):
        return glob.glob(pattern, recursive=True)
    in_dir = os.path.join(glob.escape(str(directory)), pattern)
    return glob.glob(in_dir, recursive=True)


def discover_event_files(
    inputs: Sequence[str], pattern: str | None
) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            if not pattern:
                raise ValueError(
                    "When an input is a directory you must provide --pattern"
                )
            files.extend(Path(x) for x in glob_in_directory(p, pattern))
        else:
            files.append(p)
    unique = sorted({p.resolve() for p in files if p.suffix == ".h5"})
    return unique


def write_bin_list(out_path: Path, events: list[EventNch]) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# event_h5\tNch(Q0_real,n=0 from particle_9999_vndata_eta_-0.5_0.5.dat)\n"
        )
        for ev in events:
            f.write(f"{ev.path}\t{ev.nch:.6e}\n")


def maybe_link_events(
    bin_dir: Path, events: list[EventNch], method: str
) -> None:
    if method == "none":
        return
    
    # Create main bin directory if it doesn't exist
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    for ev in events:
        # Use the job directory closest to the event file (e.g. "job_123"),
        # i.e. normally its parent directory.
        job_name = next(
            (p for p in reversed(ev.path.parent.parts) if _JOB_RE.fullmatch(p)),
            None,
        )

        if job_name is None:
            raise ValueError(
                f"Could not extract job index from path: {ev.path}"
            )
        
        # Create job-specific subdirectory (bin_dir/job_N/)
        job_dir = bin_dir / job_name
        job_dir.mkdir(parents=True, exist_ok=True)
        
        dst = job_dir / ev.path.name
        
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        
        if method == "symlink":
            # Relative link: stays valid when the tree is accessed through a
            # different mount point (e.g. created in Apptainer under /work).
            os.symlink(os.path.relpath(ev.path, job_dir), dst)
        elif method == "copy":
            import shutil

            shutil.copy2(ev.path, dst)
        else:
            raise ValueError(f"Unknown method: {method}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bin CRONOS event files into centrality classes"
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more event .h5 files, or a directory (use --pattern).",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        help=(
            "Glob used when input is a directory, relative to that directory, "
            "e.g. 'job_*/event_*.h5'"
        ),
    )
    parser.add_argument(
        "--cuts",
        nargs="*",
        type=float,
        default=list(DEFAULT_CENTRALITY_CUTS),
        help="Centrality cut edges in percent (ascending), e.g. 0 5 10 ... 100",
    )
    parser.add_argument(
        "--out-dir",
        default="centrality_bins",
        help="Output directory for bin lists (and optional links)",
    )
    parser.add_argument(
        "--link",
        choices=["none", "symlink", "copy"],
        default="none",
        help="Optionally create per-bin folders containing symlinks/copies of event files",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    event_files = discover_event_files(args.inputs, args.pattern)
    if not event_files:
        raise SystemExit("No event .h5 files found")

    event_nch: list[EventNch] = []
    skipped = 0
    for p in event_files:
        try:
            nch = _extract_nch_from_event_file(p)
        except Exception as e:
            # One unreadable/incomplete event must not abort the binning.
            skipped += 1
            print(f"SKIP {p} (failed to extract Nch: {e})", file=sys.stderr)
            continue
        event_nch.append(EventNch(path=p, nch=nch))
    if not event_nch:
        raise SystemExit("No readable event .h5 files found")

    # Sort by multiplicity descending: most central first.
    event_nch.sort(key=lambda x: x.nch, reverse=True)

    cuts = list(args.cuts)
    if len(cuts) < 2 or cuts[0] != 0 or cuts[-1] != 100:
        raise ValueError("--cuts must start at 0 and end at 100")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    n = len(event_nch)
    for i in range(len(cuts) - 1):
        c_lo = float(cuts[i])
        c_hi = float(cuts[i + 1])
        if c_hi <= c_lo:
            continue

        # Percentile indices (inclusive/exclusive)
        i0 = int(np.floor(n * c_lo / 100.0))
        i1 = int(np.floor(n * c_hi / 100.0))
        i1 = min(max(i1, i0), n)

        selected = event_nch[i0:i1]
        label = f"C{int(c_lo)}-{int(c_hi)}"
        list_path = out_dir / f"{label}.txt"
        write_bin_list(list_path, selected)

        if args.link != "none":
            maybe_link_events(out_dir / label, selected, args.link)

        print(f"{label}: {len(selected)} event(s)")

    print(f"Wrote centrality bin lists to {out_dir}")
    if skipped:
        print(f"Skipped {skipped} unreadable event file(s)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
