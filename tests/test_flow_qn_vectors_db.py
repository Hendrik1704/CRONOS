import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


def _import_flow_module(project_root: Path):
    mod_path = project_root / "utilities" / "flow_qn_vectors.py"
    spec = importlib.util.spec_from_file_location("flow_qn_vectors", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_text_dataset(group: h5py.Group, name: str, text: str):
    dt = h5py.string_dtype(encoding="utf-8")
    group.create_dataset(name, data=text, dtype=dt)


@pytest.mark.unit
def test_flow_qn_vectors_from_db_group(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    flow = _import_flow_module(project_root)

    db = tmp_path / "merged.h5"

    # Minimal pT-differential vndata: pT, dN, v1r, v1i, v2r, v2i, totalN
    vndata = np.array(
        [
            [0.2, 10.0, 0.01, 0.00, 0.02, 0.00, 100.0],
            [1.0, 5.0, 0.01, 0.00, 0.02, 0.00, 100.0],
            [3.0, 1.0, 0.01, 0.00, 0.02, 0.00, 100.0],
        ]
    )
    vndata_text = "# pT dN v1r v1i v2r v2i totalN\n" + "\n".join(
        " ".join(f"{x:.6e}" for x in row) for row in vndata
    )

    # Identified particle: reuse same shape
    pid_text = vndata_text

    with h5py.File(db, "w") as f:
        j0 = f.create_group("job_0")
        e0 = j0.create_group("event_0")
        _write_text_dataset(e0, flow.CH_VNDATA_KEY, vndata_text)
        # Provide a couple of PID files so yield writing is exercised
        _write_text_dataset(
            e0, "particle_211_vndata_diff_y_-0.5_0.5.dat", pid_text
        )
        _write_text_dataset(
            e0, "particle_-211_vndata_diff_y_-0.5_0.5.dat", pid_text
        )

    out_dir = tmp_path / "out"
    rc = flow.main(
        [
            "--db",
            str(db),
            "--group",
            "/job_0/event_0",
            "--out-dir",
            str(out_dir),
            "--pTmin",
            "0.2",
            "--pTmax",
            "3.0",
        ]
    )
    assert rc == 0

    qn_path = out_dir / "Qn_vectors_job_0_event_0.dat"
    y_path = out_dir / "particle_yield_and_meanpT_job_0_event_0.dat"
    assert qn_path.exists()
    assert y_path.exists()

    qn = np.loadtxt(qn_path)
    assert qn.shape[1] == 7  # n + 6 cols


@pytest.mark.unit
def test_flow_qn_vectors_from_event_file(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    flow = _import_flow_module(project_root)

    run_dir = tmp_path / "run" / "job_0"
    run_dir.mkdir(parents=True, exist_ok=True)
    event_file = run_dir / "event_0.h5"

    vndata = np.array(
        [
            [0.2, 10.0, 0.01, 0.00, 0.02, 0.00, 100.0],
            [1.0, 5.0, 0.01, 0.00, 0.02, 0.00, 100.0],
            [3.0, 1.0, 0.01, 0.00, 0.02, 0.00, 100.0],
        ]
    )
    vndata_text = "# pT dN v1r v1i v2r v2i totalN\n" + "\n".join(
        " ".join(f"{x:.6e}" for x in row) for row in vndata
    )

    with h5py.File(event_file, "w") as f:
        g = f.create_group("event_0")
        _write_text_dataset(g, flow.CH_VNDATA_KEY, vndata_text)
        _write_text_dataset(
            g, "particle_211_vndata_diff_y_-0.5_0.5.dat", vndata_text
        )

    out_dir = tmp_path / "out"
    rc = flow.main(
        [
            str(event_file),
            "--out-dir",
            str(out_dir),
            "--pTmin",
            "0.2",
            "--pTmax",
            "3.0",
        ]
    )
    assert rc == 0

    qn_path = out_dir / "Qn_vectors_job_0_event_0.dat"
    y_path = out_dir / "particle_yield_and_meanpT_job_0_event_0.dat"
    assert qn_path.exists()
    assert y_path.exists()
