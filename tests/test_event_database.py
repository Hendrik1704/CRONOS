import importlib.util
from pathlib import Path

import sys

import h5py
import pytest


DEFAULT_REQUIRED = (
    "particle_9999_vndata_eta_-0.5_0.5.dat",
    "particle_9999_vndata_diff_eta_0.5_2.5.dat",
    "particle_9999_vndata_eta_-2.5_2.5.dat",
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


def _import_event_database_module(project_root: Path):
    mod_path = project_root / "utilities" / "event_database.py"
    spec = importlib.util.spec_from_file_location("event_database", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_event_h5(path: Path, *, include_required: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    dt = h5py.string_dtype(encoding="utf-8")
    event_name = path.stem  # e.g. "event_0"
    with h5py.File(path, "w") as f:
        g = f.create_group(event_name)
        if include_required:
            for name in DEFAULT_REQUIRED:
                g.create_dataset(name, data="# header\n0 1 2\n", dtype=dt)
        else:
            g.create_dataset("some_other.dat", data="x", dtype=dt)


@pytest.mark.unit
def test_build_database_does_not_delete_sources_by_default(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    event_database = _import_event_database_module(project_root)

    e1 = tmp_path / "run" / "job_0" / "event_0.h5"
    e2 = tmp_path / "run" / "job_1" / "event_0.h5"
    _write_event_h5(e1, include_required=True)
    _write_event_h5(e2, include_required=True)

    out = tmp_path / "merged.h5"
    rc = event_database.main(
        [
            "build",
            "--pattern",
            str(tmp_path / "run" / "job_*" / "event_*.h5"),
            "--out",
            str(out),
            "--validate",
            "--quiet",
        ]
    )
    assert rc == 0
    assert e1.exists()
    assert e2.exists()

    with h5py.File(out, "r") as f:
        assert "job_0" in f
        assert "event_0" in f["job_0"]
        assert DEFAULT_REQUIRED[0] in f["job_0"]["event_0"]


@pytest.mark.unit
def test_build_database_can_delete_only_merged_sources(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    event_database = _import_event_database_module(project_root)

    good = tmp_path / "run" / "job_0" / "event_0.h5"
    bad = tmp_path / "run" / "job_0" / "event_1.h5"
    _write_event_h5(good, include_required=True)
    _write_event_h5(bad, include_required=False)

    out = tmp_path / "merged.h5"
    rc = event_database.main(
        [
            "build",
            "--pattern",
            str(tmp_path / "run" / "job_*" / "event_*.h5"),
            "--out",
            str(out),
            "--validate",
            "--delete-source",
            "--quiet",
        ]
    )

    # bad should be skipped (missing required datasets) and not deleted
    assert rc == 2
    assert not good.exists()
    assert bad.exists()

    with h5py.File(out, "r") as f:
        assert "job_0" in f
        assert "event_0" in f["job_0"]
        assert "event_1" not in f["job_0"]


@pytest.mark.unit
def test_prune_deletes_bad_event_groups(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    event_database = _import_event_database_module(project_root)

    db = tmp_path / "db.h5"
    dt = h5py.string_dtype(encoding="utf-8")
    with h5py.File(db, "w") as f:
        j0 = f.create_group("job_0")
        good = j0.create_group("event_0")
        bad = j0.create_group("event_1")
        for name in DEFAULT_REQUIRED:
            good.create_dataset(name, data="# header\n0 1 2\n", dtype=dt)
        bad.create_dataset("some_other.dat", data="x", dtype=dt)

    rc = event_database.main(
        [
            "prune",
            str(db),
            "--quiet",
        ]
    )
    assert rc == 2
    with h5py.File(db, "r") as f:
        assert "job_0" in f
        assert "event_0" in f["job_0"]
        assert "event_1" not in f["job_0"]


@pytest.mark.unit
def test_combine_merges_two_databases(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    event_database = _import_event_database_module(project_root)

    dt = h5py.string_dtype(encoding="utf-8")
    db1 = tmp_path / "db1.h5"
    db2 = tmp_path / "db2.h5"
    out = tmp_path / "combined.h5"

    with h5py.File(db1, "w") as f:
        j0 = f.create_group("job_0")
        e0 = j0.create_group("event_0")
        for name in DEFAULT_REQUIRED:
            e0.create_dataset(name, data="a", dtype=dt)

    with h5py.File(db2, "w") as f:
        j1 = f.create_group("job_1")
        e0 = j1.create_group("event_0")
        for name in DEFAULT_REQUIRED:
            e0.create_dataset(name, data="b", dtype=dt)

    rc = event_database.main(
        [
            "combine",
            "--out",
            str(out),
            "--quiet",
            str(db1),
            str(db2),
        ]
    )
    assert rc == 0
    with h5py.File(out, "r") as f:
        assert "job_0" in f
        assert "job_1" in f


@pytest.mark.unit
def test_combine_default_renames_conflicts(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    event_database = _import_event_database_module(project_root)

    dt = h5py.string_dtype(encoding="utf-8")
    db1 = tmp_path / "db1.h5"
    db2 = tmp_path / "db2.h5"
    out = tmp_path / "combined.h5"

    with h5py.File(db1, "w") as f:
        j0 = f.create_group("job_0")
        e0 = j0.create_group("event_0")
        for name in DEFAULT_REQUIRED:
            e0.create_dataset(name, data="a", dtype=dt)

    with h5py.File(db2, "w") as f:
        j0 = f.create_group("job_0")
        e1 = j0.create_group("event_1")
        for name in DEFAULT_REQUIRED:
            e1.create_dataset(name, data="b", dtype=dt)

    rc = event_database.main(
        [
            "combine",
            "--out",
            str(out),
            "--quiet",
            str(db1),
            str(db2),
        ]
    )
    assert rc == 0
    with h5py.File(out, "r") as f:
        assert "job_0" in f
        assert "job_0__1" in f
        assert "event_0" in f["job_0"]
        assert "event_1" in f["job_0__1"]
