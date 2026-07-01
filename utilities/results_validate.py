#!/usr/bin/env python3
"""Validate CRONOS per-event HDF5 outputs.

CRONOS stores one compressed HDF5 per simulated event, typically at
`run/job_*/event_*.h5`.

This utility scans one or many event files and reports which ones are missing
required datasets.

Typical usage:
    python utilities/results_validate.py run/ --pattern 'run/job_*/event_*.h5'
    python utilities/results_validate.py run/job_0/event_0.h5

Exit codes:
    0: all files OK
    2: some files missing required datasets
"""

from __future__ import annotations

import argparse
import glob
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

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
class ValidationResult:
    file_path: Path
    missing: tuple[str, ...]


def iter_event_files(inputs: Sequence[str], pattern: str | None) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            if not pattern:
                raise ValueError(
                    "When an input is a directory you must provide --pattern"
                )
            files.extend(Path(x) for x in glob.glob(pattern, recursive=True))
        else:
            files.append(p)
    # normalize + de-dup
    unique = sorted({p.resolve() for p in files if p.suffix == ".h5"})
    return unique


def validate_file(file_path: Path, required: Iterable[str]) -> ValidationResult:
    required = tuple(required)
    missing: list[str] = []
    with h5py.File(file_path, "r") as h5f:
        # Navigate into the inner event group if present (new format: datasets
        # are stored inside an event_{id} group rather than at the file root).
        event_keys = [
            k for k in h5f.keys()
            if k.startswith("event_") and isinstance(h5f[k], h5py.Group)
        ]
        h5obj: h5py.Group = h5f[event_keys[0]] if len(event_keys) == 1 else h5f
        keys = set(h5obj.keys())
        for name in required:
            if name not in keys:
                missing.append(name)
    return ValidationResult(file_path=file_path, missing=tuple(missing))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate CRONOS per-event HDF5 files for required datasets"
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
            "Glob pattern used when an input is a directory, e.g. "
            "'run/job_*/event_*.h5'"
        ),
    )
    parser.add_argument(
        "--required",
        nargs="*",
        default=list(DEFAULT_REQUIRED_DATASETS),
        help="Dataset names that must exist inside each event file.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    event_files = iter_event_files(args.inputs, args.pattern)
    if not event_files:
        print("No event .h5 files found.", file=sys.stderr)
        return 2

    bad: list[ValidationResult] = []
    for fpath in event_files:
        if not fpath.exists():
            print(f"Missing file: {fpath}", file=sys.stderr)
            bad.append(ValidationResult(fpath, tuple(args.required)))
            continue
        res = validate_file(fpath, args.required)
        if res.missing:
            bad.append(res)

    print(f"Checked {len(event_files)} file(s).")
    if bad:
        print(f"{len(bad)} file(s) missing required datasets:")
        for res in bad:
            missing_str = ", ".join(res.missing)
            print(f"- {res.file_path}: {missing_str}")
        return 2

    print("All files contain the required datasets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
