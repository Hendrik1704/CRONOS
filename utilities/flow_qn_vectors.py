#!/usr/bin/env python3
"""Compute Qn vectors and basic yields from CRONOS HDF5 outputs.

Outputs (per event):
- `Qn_vectors_<event_label>.dat` : pT-integrated Qn and vn (n=0..nmax)
- `particle_yield_and_meanpT_<event_label>.dat` : yield + mean pT for a PID list

Typical usage:
    python utilities/flow_qn_vectors.py run/job_0/event_0.h5
    python utilities/flow_qn_vectors.py run/ --pattern 'run/job_*/event_*.h5'

Database usage (merged HDF5 from `utilities/event_database.py build`):
    # One event group
    python utilities/flow_qn_vectors.py --db merged_events.h5 --group /job_0/event_0

    # All event groups
    python utilities/flow_qn_vectors.py --db merged_events.h5 --all-events
"""

from __future__ import annotations

import argparse
import glob
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import h5py
import numpy as np


DEFAULT_PT_MIN = 0.2
DEFAULT_PT_MAX = 3.0

# Charged uses diff_eta; identified uses diff_y in CRONOS outputs.
CH_VNDATA_KEY = "particle_9999_vndata_diff_eta_-0.5_0.5.dat"

PID_FILES: tuple[tuple[str, int, str], ...] = (
    ("ch", 9999, "particle_9999_vndata_diff_eta_-0.5_0.5.dat"),
    ("pi+", 211, "particle_211_vndata_diff_y_-0.5_0.5.dat"),
    ("pi-", -211, "particle_-211_vndata_diff_y_-0.5_0.5.dat"),
    ("K+", 321, "particle_321_vndata_diff_y_-0.5_0.5.dat"),
    ("K-", -321, "particle_-321_vndata_diff_y_-0.5_0.5.dat"),
    ("p", 2212, "particle_2212_vndata_diff_y_-0.5_0.5.dat"),
    ("pbar", -2212, "particle_-2212_vndata_diff_y_-0.5_0.5.dat"),
)


_JOB_RE = re.compile(r"job_(\d+)$")


@dataclass(frozen=True)
class EventInput:
    path: Path

    @property
    def label(self) -> str:
        # Create a stable label like job_0_event_0
        parts = list(self.path.parts)
        job = next((p for p in parts if p.startswith("job_")), "job")
        m = re.search(r"event_(\d+)\.h5$", self.path.name)
        ev = f"event_{m.group(1)}" if m else self.path.stem
        return f"{job}_{ev}"


def iter_event_files(
    inputs: Sequence[str], pattern: str | None
) -> list[EventInput]:
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
    unique = sorted({p.resolve() for p in files if p.suffix == ".h5"})
    return [EventInput(path=p) for p in unique]


def iter_database_event_groups(
    h5f: h5py.File,
) -> Iterator[tuple[str, h5py.Group]]:
    """Yield (group_path, group) for each event group in a merged database.

    Supported layouts:
    - CRONOS merged DB layout:
        /job_17/event_0/<datasets...>
    - Legacy flat layout:
        /spvn_results_1234/<datasets...>
    """

    job_names = [k for k in h5f.keys() if _JOB_RE.fullmatch(k)]
    for job_name in sorted(job_names):
        job_group = h5f[job_name]
        for event_name in sorted(job_group.keys()):
            if event_name.startswith("event_") and isinstance(
                job_group[event_name], h5py.Group
            ):
                grp = job_group[event_name]
                yield (f"/{job_name}/{event_name}", grp)

    for k in sorted(h5f.keys()):
        if k.startswith("spvn_results_") and isinstance(h5f[k], h5py.Group):
            yield (f"/{k}", h5f[k])


def _read_text_dataset(h5obj: h5py.File | h5py.Group, key: str) -> str:
    ds = h5obj[key]
    data = ds[()]
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8", errors="replace")
    return str(data)


def _load_table(text: str) -> np.ndarray:
    # loadtxt handles comments and whitespace; keep it simple.
    return np.loadtxt(io.StringIO(text), comments="#")


def _infer_nmax_from_vndata(data: np.ndarray) -> int:
    # Expected columns: pT, dN, (vn_real, vn_imag) for n=1..nmax, optional totalN column.
    ncols = data.shape[1]
    # Heuristic: if last column is huge integer-ish counts and the rest are small,
    # treat it as totalN and exclude it from harmonic inference.
    # Most CRONOS afterburner_toolkit vndata files include totalN as last column.
    core_cols = ncols
    if ncols >= 5:
        core_cols = ncols - 1

    # core cols: 2 + 2*nmax
    if core_cols < 4 or (core_cols - 2) % 2 != 0:
        raise ValueError(f"Unexpected vndata column count: {ncols}")
    return (core_cols - 2) // 2


def calculate_integrated_Qn(
    pT_low: float, pT_high: float, vndata: np.ndarray
) -> list[complex]:
    """Compute pT-integrated Qn for one event.

    Uses the same numerical approach as the imported scripts:
    - interpolate dN(pT) in log space
    - integrate with weight 2π pT dpT

    Expects vndata columns:
        pT, dN, vn_real(n=1), vn_imag(n=1), ..., [totalN]

    Returns:
        list where index 0 is Q0 = N (real), and index n is Qn (complex).
    """
    nmax = _infer_nmax_from_vndata(vndata)

    npT = 50
    pT_inte = np.linspace(pT_low, pT_high, npT)
    dpT = float(pT_inte[1] - pT_inte[0])

    pT_event = vndata[:, 0]
    dN_event = vndata[:, 1]
    dN_interp = np.exp(np.interp(pT_inte, pT_event, np.log(dN_event + 1e-30)))

    # Q0 = N
    N = 2.0 * np.pi * np.sum(dN_interp * pT_inte) * dpT
    out: list[complex] = [complex(N, 0.0)]

    for n in range(1, nmax + 1):
        vn_real = vndata[:, 2 * n]
        vn_imag = vndata[:, 2 * n + 1]
        vn_real_i = np.interp(pT_inte, pT_event, vn_real)
        vn_imag_i = np.interp(pT_inte, pT_event, vn_imag)

        Qn_real = 2.0 * np.pi * np.sum(vn_real_i * dN_interp * pT_inte) * dpT
        Qn_imag = 2.0 * np.pi * np.sum(vn_imag_i * dN_interp * pT_inte) * dpT
        out.append(complex(Qn_real, Qn_imag))

    return out


def calculate_yield_and_meanpT(
    pT_low: float, pT_high: float, vndata: np.ndarray
) -> tuple[float, float]:
    npT = 50
    pT_inte = np.linspace(pT_low, pT_high, npT)
    dpT = float(pT_inte[1] - pT_inte[0])

    pT_event = vndata[:, 0]
    dN_event = vndata[:, 1]
    dN_interp = np.exp(np.interp(pT_inte, pT_event, np.log(dN_event + 1e-30)))

    N = 2.0 * np.pi * np.sum(dN_interp * pT_inte) * dpT
    mean_pT = float(
        np.sum(dN_interp * pT_inte**2) / np.sum(dN_interp * pT_inte)
    )
    return float(N), mean_pT


def write_Qn_vectors(out_path: Path, Qn: Sequence[complex]) -> None:
    rows = []
    for n, q in enumerate(Qn):
        vn = q / (Qn[0] + 1e-30)
        vn_real = float(np.real(vn))
        vn_imag = float(np.imag(vn))
        vn_mag = float(np.hypot(vn_real, vn_imag))
        psi_n = float(np.arctan2(vn_imag, vn_real) / (n + 1e-15))
        rows.append(
            [
                n,
                float(np.real(q)),
                float(np.imag(q)),
                vn_real,
                vn_imag,
                vn_mag,
                psi_n,
            ]
        )

    arr = np.array(rows)
    np.savetxt(
        out_path,
        arr,
        fmt="%d  " + "%.6e  " * 6,
        header="n  Qn_real  Qn_imag  vn_real  vn_imag  vn_mag  psi_n",
    )


def write_yields(out_path: Path, rows: Sequence[Sequence[float]]) -> None:
    arr = np.array(rows, dtype=float)
    np.savetxt(
        out_path,
        arr,
        fmt="%d  " + "%.6e  " * 2,
        header="pid  dN/dy  <pT> (GeV)",
    )


def process_event_container(
    *,
    label: str,
    h5obj: h5py.File | h5py.Group,
    out_dir: Path,
    pTmin: float,
    pTmax: float,
) -> None:
    # Qn vectors for charged hadrons
    text = _read_text_dataset(h5obj, CH_VNDATA_KEY)
    vndata = _load_table(text)
    Qn = calculate_integrated_Qn(pTmin, pTmax, vndata)

    qn_out = out_dir / f"Qn_vectors_{label}.dat"
    write_Qn_vectors(qn_out, Qn)

    # yields and mean pT
    yield_rows = []
    for _, pid, key in PID_FILES:
        if key not in h5obj:
            continue
        text_pid = _read_text_dataset(h5obj, key)
        vndata_pid = _load_table(text_pid)
        N, mean_pT = calculate_yield_and_meanpT(0.0, pTmax, vndata_pid)
        yield_rows.append([pid, N, mean_pT])

    yield_out = out_dir / f"particle_yield_and_meanpT_{label}.dat"
    write_yields(yield_out, yield_rows)


def process_event_file(
    event: EventInput, out_dir: Path, pTmin: float, pTmax: float
) -> None:
    with h5py.File(event.path, "r") as h5f:
        process_event_container(
            label=event.label,
            h5obj=h5f,
            out_dir=out_dir,
            pTmin=pTmin,
            pTmax=pTmax,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute Qn vectors and yields from CRONOS HDF5 outputs"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="One or more event .h5 files, or a directory (use --pattern).",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        help="Glob pattern used when an input is a directory, e.g. 'run/job_*/event_*.h5'",
    )
    parser.add_argument(
        "--out-dir",
        default="extracted_data",
        help="Directory to write output .dat files",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=(
            "Path to a merged database .h5 (from utilities/event_database.py). "
            "If set, inputs/pattern are ignored unless --all-events is used."
        ),
    )
    parser.add_argument(
        "--group",
        default=None,
        help=(
            "Event group path inside --db, e.g. /job_0/event_0 or /spvn_results_123. "
            "If omitted, use --all-events."
        ),
    )
    parser.add_argument(
        "--all-events",
        action="store_true",
        help="Process all event groups found inside --db.",
    )
    parser.add_argument(
        "--job",
        type=int,
        default=None,
        help="Shortcut for --group /job_<job>/event_<event> (requires --event)",
    )
    parser.add_argument(
        "--event",
        type=int,
        default=None,
        help="Shortcut for --group /job_<job>/event_<event> (requires --job)",
    )
    parser.add_argument("--pTmin", type=float, default=DEFAULT_PT_MIN)
    parser.add_argument("--pTmax", type=float, default=DEFAULT_PT_MAX)
    args = parser.parse_args(list(argv) if argv is not None else None)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.job is not None or args.event is not None:
        if args.job is None or args.event is None:
            raise SystemExit("--job and --event must be provided together")
        args.group = f"/job_{args.job}/event_{args.event}"

    if args.db:
        db_path = Path(args.db).resolve()
        if not db_path.exists():
            raise SystemExit(f"Database file not found: {db_path}")

        processed = 0
        with h5py.File(db_path, "r") as h5f:
            if args.all_events:
                for group_path, grp in iter_database_event_groups(h5f):
                    label = group_path.strip("/").replace("/", "_")
                    process_event_container(
                        label=label,
                        h5obj=grp,
                        out_dir=out_dir,
                        pTmin=args.pTmin,
                        pTmax=args.pTmax,
                    )
                    processed += 1
            else:
                if not args.group:
                    raise SystemExit(
                        "With --db, provide --group or use --all-events"
                    )
                group_key = args.group.lstrip("/")
                if group_key not in h5f:
                    raise SystemExit(
                        f"Group not found in database: {args.group}"
                    )
                grp = h5f[group_key]
                if not isinstance(grp, h5py.Group):
                    raise SystemExit(f"Not a group: {args.group}")
                label = args.group.strip("/").replace("/", "_")
                process_event_container(
                    label=label,
                    h5obj=grp,
                    out_dir=out_dir,
                    pTmin=args.pTmin,
                    pTmax=args.pTmax,
                )
                processed = 1

        print(f"Processed {processed} event group(s). Outputs in {out_dir}")
        return 0

    events = iter_event_files(args.inputs, args.pattern)
    if not events:
        raise SystemExit("No event .h5 files found (or use --db)")

    for ev in events:
        process_event_file(ev, out_dir, args.pTmin, args.pTmax)

    print(f"Processed {len(events)} event file(s). Outputs in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
