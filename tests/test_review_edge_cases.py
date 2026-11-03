"""Edge cases from the review of the framework fixes: interrupted database
copies, the row/column layout of one-dimensional tables and directory-relative
glob patterns."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import h5py
import numpy as np
import pytest

from src.configuration import Configuration
from src.handle_results import zip_into_hdf5

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _import_utility(name):
    spec = importlib.util.spec_from_file_location(
        name, PROJECT_ROOT / "utilities" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_interrupted_copy_leaves_no_event_group(tmp_path):
    """A partial group must not look complete after Ctrl+C."""
    event_database = _import_utility("event_database")
    src = tmp_path / "run" / "job_0" / "event_0.h5"
    src.parent.mkdir(parents=True)
    with h5py.File(src, "w") as f:
        f.create_dataset("a.dat", data=np.arange(3.0))
    ref = event_database.event_ref_from_path(src)

    with h5py.File(tmp_path / "db.h5", "w") as out_h5:
        with patch.object(h5py.Group, "copy", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                event_database.copy_event_file(src, out_h5, ref)
        assert "event_0" not in out_h5.require_group("job_0")


@pytest.mark.parametrize(
    "lines, layout, shape",
    [
        (["# tau_in_fm 0.4", "1 2 3 4"], "row", (1, 4)),
        (["# values", "1", "2", "3", "4"], "column", (4, 1)),
    ],
)
def test_one_dimensional_table_layout_survives_extraction(
    tmp_path, lines, layout, shape
):
    results = tmp_path / "results"
    spvn = results / "spvn_results_0"
    spvn.mkdir(parents=True)
    (spvn / "table.dat").write_text("\n".join(lines) + "\n")
    config = Configuration({"general": {"modules": ["IPGlasma"]}})

    assert zip_into_hdf5(config, str(results), "0")

    with h5py.File(results / "event_0.h5") as f:
        dset = f["event_0"]["table.dat"]
        assert dset.attrs["table_layout"].decode() == layout
        attributes = dict(dset.attrs)
        data = dset[()]

    h5_extractor = _import_utility("h5_extractor")
    extractor = h5_extractor.HDF5Extractor.__new__(h5_extractor.HDF5Extractor)
    extractor.output_dir = tmp_path
    path = extractor._save_as_numeric_table(data, "table.dat", attributes)
    assert np.loadtxt(path, ndmin=2).shape == shape


@pytest.mark.parametrize(
    "tool", ["flow_qn_vectors", "results_validate", "centrality_binning"]
)
def test_directory_relative_pattern_does_not_fall_back_to_cwd(
    tmp_path, monkeypatch, tool
):
    """No events from another run in the working directory are picked up."""
    module = _import_utility(tool)
    other = tmp_path / "job_0"
    other.mkdir()
    (other / "event_0.h5").touch()
    requested = tmp_path / "runB"
    requested.mkdir()
    monkeypatch.chdir(tmp_path)

    assert module.glob_in_directory(requested, "job_*/event_*.h5") == []
    # A pattern that starts with the directory keeps working
    (requested / "job_1").mkdir()
    (requested / "job_1" / "event_0.h5").touch()
    assert module.glob_in_directory(
        requested, "runB/job_*/event_*.h5"
    ) == ["runB/job_1/event_0.h5"]
