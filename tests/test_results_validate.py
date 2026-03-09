import importlib.util
import sys
from pathlib import Path

import h5py
import pytest


def _import_results_validate_module(project_root: Path):
    mod_path = project_root / "utilities" / "results_validate.py"
    spec = importlib.util.spec_from_file_location("results_validate", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_event_h5(path: Path, keys: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    dt = h5py.string_dtype(encoding="utf-8")
    with h5py.File(path, "w") as f:
        for k in keys:
            f.create_dataset(k, data="x", dtype=dt)


@pytest.mark.unit
def test_results_validate_ok_and_missing(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    rv = _import_results_validate_module(project_root)

    good = tmp_path / "event_good.h5"
    bad = tmp_path / "event_bad.h5"

    _write_event_h5(good, list(rv.DEFAULT_REQUIRED_DATASETS))
    _write_event_h5(bad, [rv.DEFAULT_REQUIRED_DATASETS[0]])

    res_good = rv.validate_file(good, rv.DEFAULT_REQUIRED_DATASETS)
    assert res_good.missing == ()

    res_bad = rv.validate_file(bad, rv.DEFAULT_REQUIRED_DATASETS)
    assert len(res_bad.missing) > 0

    assert rv.main([str(good)]) == 0
    assert rv.main([str(bad)]) == 2


@pytest.mark.unit
def test_results_validate_directory_input_with_pattern(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    rv = _import_results_validate_module(project_root)

    e0 = tmp_path / "run" / "job_0" / "event_0.h5"
    e1 = tmp_path / "run" / "job_0" / "event_1.h5"
    _write_event_h5(e0, list(rv.DEFAULT_REQUIRED_DATASETS))
    _write_event_h5(e1, list(rv.DEFAULT_REQUIRED_DATASETS))

    pattern = str(tmp_path / "run" / "job_*" / "event_*.h5")
    rc = rv.main([str(tmp_path / "run"), "--pattern", pattern])
    assert rc == 0
