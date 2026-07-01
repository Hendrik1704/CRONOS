import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


def _import_centrality_module(project_root: Path):
    mod_path = project_root / "utilities" / "centrality_binning.py"
    spec = importlib.util.spec_from_file_location(
        "centrality_binning", mod_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_nch_event(path: Path, *, nch: float, key: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    dt = h5py.string_dtype(encoding="utf-8")
    # columns: n, Qn_real, Qn_real_err, Qn_imag, Qn_imag_err
    text = (
        "# n  Qn_real  Qn_real_err  Qn_imag  Qn_imag_err\n"
        f"0  {nch:.6e}  0.0  0.0  0.0\n"
        "1  0.0  0.0  0.0  0.0\n"
    )
    event_name = path.stem  # e.g. "event_0"
    with h5py.File(path, "w") as f:
        g = f.create_group(event_name)
        g.create_dataset(key, data=text, dtype=dt)


@pytest.mark.unit
def test_extract_nch_single_row_edge_case(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    cb = _import_centrality_module(project_root)

    event = tmp_path / "event_0.h5"
    dt = h5py.string_dtype(encoding="utf-8")
    text = "# n Qn_real Qn_real_err Qn_imag Qn_imag_err\n0  1.23e+02  0  0  0\n"
    with h5py.File(event, "w") as f:
        g = f.create_group("event_0")
        g.create_dataset(cb.NCH_KEY, data=text, dtype=dt)

    nch = cb._extract_nch_from_event_file(event)
    assert nch == pytest.approx(123.0)


@pytest.mark.unit
def test_centrality_binning_writes_expected_bins(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    cb = _import_centrality_module(project_root)

    run_dir = tmp_path / "run"
    events = [
        (run_dir / "job_0" / "event_0.h5", 100.0),
        (run_dir / "job_0" / "event_1.h5", 50.0),
        (run_dir / "job_1" / "event_0.h5", 10.0),
        (run_dir / "job_1" / "event_1.h5", 1.0),
    ]
    for path, nch in events:
        _write_nch_event(path, nch=nch, key=cb.NCH_KEY)

    out_dir = tmp_path / "bins"
    pattern = str(run_dir / "job_*" / "event_*.h5")

    rc = cb.main(
        [
            str(run_dir),
            "--pattern",
            pattern,
            "--cuts",
            "0",
            "50",
            "100",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0

    c0 = out_dir / "C0-50.txt"
    c1 = out_dir / "C50-100.txt"
    assert c0.exists()
    assert c1.exists()

    def read_nch_values(p: Path) -> list[float]:
        lines = p.read_text(encoding="utf-8").splitlines()
        data = [ln for ln in lines if ln and not ln.startswith("#")]
        return [float(ln.split()[1]) for ln in data]

    v0 = read_nch_values(c0)
    v1 = read_nch_values(c1)

    assert len(v0) == 2
    assert len(v1) == 2
    # Sorted descending: most central first.
    assert np.allclose(v0, [100.0, 50.0])
    assert np.allclose(v1, [10.0, 1.0])
