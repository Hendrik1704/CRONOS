import os
from unittest.mock import patch

import h5py
import numpy as np
import pytest

from src.configuration import Configuration
from src.handle_results import handle_results, zip_into_hdf5


AFTERBURNER_MODULES = ["from_file_IC", "MUSIC", "iSS", "afterburner_toolkit"]
GOOD_SPVN_FILES = [
    "particle_9999_vndata_eta_-0.5_0.5.dat",
    "particle_211_vndata_diff_y_-0.5_0.5.dat",
    "particle_321_vndata_diff_y_-0.5_0.5.dat",
    "particle_2212_vndata_diff_y_-0.5_0.5.dat",
]


def _make_config(modules, keep_intermediate_results, keep_particle_files):
    return Configuration(
        {
            "general": {
                "modules": modules,
                "keep_intermediate_results": keep_intermediate_results,
                "keep_particle_files": keep_particle_files,
            }
        }
    )


def _fill_results_dir(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True)
    for i in range(3):
        (results_dir / f"output_{i}.dat").write_text(f"module {i}")
    (results_dir / "configuration.py").write_text("")
    return results_dir


def _output_files_in_spvn(results_dir):
    spvn_dir = results_dir / "spvn_results_0"
    return sorted(f for f in os.listdir(spvn_dir) if f.startswith("output_"))


def _run_handle_results(tmp_path, config):
    results_dir = _fill_results_dir(tmp_path)

    with patch("src.handle_results.zip_into_hdf5"):
        handle_results(config, str(results_dir), "0")

    return _output_files_in_spvn(results_dir)


@pytest.mark.parametrize(
    "keep_intermediate_results, keep_particle_files, expected",
    [
        (False, False, []),
        (False, True, ["output_2.dat"]),
        (True, False, ["output_0.dat", "output_1.dat"]),
        (True, True, ["output_0.dat", "output_1.dat", "output_2.dat"]),
    ],
)
def test_output_file_retention(
    tmp_path, keep_intermediate_results, keep_particle_files, expected
):
    config = _make_config(
        AFTERBURNER_MODULES, keep_intermediate_results, keep_particle_files
    )
    assert _run_handle_results(tmp_path, config) == expected


@pytest.mark.parametrize(
    "keep_intermediate_results, keep_particle_files, expected",
    [
        (False, False, ["output_2.dat"]),
        (False, True, ["output_2.dat"]),
        (True, False, ["output_0.dat", "output_1.dat", "output_2.dat"]),
        (True, True, ["output_0.dat", "output_1.dat", "output_2.dat"]),
    ],
)
def test_last_output_kept_without_afterburner_toolkit(
    tmp_path, keep_intermediate_results, keep_particle_files, expected
):
    # keep_particle_files only takes effect with afterburner_toolkit; without
    # it the last output file is the result of the chain and always kept
    config = _make_config(
        ["from_file_IC", "MUSIC", "iSS"],
        keep_intermediate_results,
        keep_particle_files,
    )
    assert _run_handle_results(tmp_path, config) == expected


def test_last_output_kept_with_more_than_ten_outputs(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    for i in (2, 9, 10):
        (results_dir / f"output_{i}.dat").write_text(f"module {i}")
    config = _make_config(["from_file_IC", "MUSIC"], False, False)
    with patch("src.handle_results.zip_into_hdf5"):
        handle_results(config, str(results_dir), "0")
    assert _output_files_in_spvn(results_dir) == ["output_10.dat"]


@pytest.mark.parametrize(
    "keep_intermediate_results, keep_particle_files",
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_handle_results_can_be_rerun(
    tmp_path, keep_intermediate_results, keep_particle_files
):
    """A second call (e.g. after a crash in zip_into_hdf5) gives the same
    retained files as a single call."""
    config = _make_config(
        AFTERBURNER_MODULES, keep_intermediate_results, keep_particle_files
    )
    expected = _run_handle_results(tmp_path / "a", config)

    results_dir = _fill_results_dir(tmp_path)
    with patch(
        "src.handle_results.zip_into_hdf5", side_effect=RuntimeError("crash")
    ):
        with pytest.raises(RuntimeError):
            handle_results(config, str(results_dir), "0")
    # the executor writes configuration.py again before the second call
    (results_dir / "configuration.py").write_text("")
    # a stale HDF5 file from the previous call must not be packaged
    (results_dir / "event_0.h5").write_text("stale")
    with patch("src.handle_results.zip_into_hdf5", return_value=True):
        assert handle_results(config, str(results_dir), "0") is True

    assert _output_files_in_spvn(results_dir) == expected
    spvn_files = os.listdir(results_dir / "spvn_results_0")
    assert "configuration.py" in spvn_files
    assert "event_0.h5" not in spvn_files


def _write_spvn_dir(results_dir, files):
    spvn_dir = results_dir / "spvn_results_0"
    spvn_dir.mkdir(parents=True)
    for f in files:
        (spvn_dir / f).write_text("1 2\n3 4\n")
    return spvn_dir


def test_bad_event_writes_no_hdf5(tmp_path):
    results_dir = tmp_path / "results"
    _write_spvn_dir(results_dir, GOOD_SPVN_FILES[:2])
    config = _make_config(AFTERBURNER_MODULES, False, False)

    assert zip_into_hdf5(config, str(results_dir), "0") is False
    assert not (results_dir / "event_0.h5").exists()


def test_zip_into_hdf5_precision_and_headers(tmp_path):
    results_dir = tmp_path / "results"
    spvn_dir = _write_spvn_dir(results_dir, GOOD_SPVN_FILES)
    (spvn_dir / "particles.dat").write_text(
        "# first header line\n"
        "# second header line\n"
        "1000010020 0.123456789012345\n"
        "-211 1.0000000001\n"
    )
    (spvn_dir / "single_header.dat").write_text("# only header\n1 2\n")
    config = _make_config(AFTERBURNER_MODULES, False, False)

    assert zip_into_hdf5(config, str(results_dir), "0") is True

    with h5py.File(results_dir / "event_0.h5", "r") as f:
        dset = f["event_0/particles.dat"]
        data = dset[()]
        assert dset.dtype == np.float64
        assert data[0, 0] == 1000010020
        assert data[0, 1] == 0.123456789012345
        assert data[1, 1] == 1.0000000001
        assert dset.attrs["header"] == b"# first header line"
        assert (
            dset.attrs["full_header"]
            == b"# first header line\n# second header line"
        )
        single = f["event_0/single_header.dat"]
        assert single.attrs["header"] == b"# only header"
        assert "full_header" not in single.attrs


def test_file_with_many_comment_lines_is_packed(tmp_path):
    """E.g. the SMASH particle list has comment lines for every event."""
    import h5py

    results = tmp_path / "results"
    results.mkdir()
    lines = ["#!OSCAR2013 particle_lists t x y z", "# Units: fm"]
    for event in range(2000):
        lines += [f"# event {event} out 1", "1 2 3 4", f"# event {event} end"]
    (results / "output_0.dat").write_text("\n".join(lines) + "\n")
    config = Configuration(
        {
            "general": {
                "modules": ["IPGlasma"],
                "keep_intermediate_results": False,
                "keep_particle_files": False,
            }
        }
    )

    assert handle_results(config, str(results), "0")

    with h5py.File(results / "event_0.h5") as f:
        dset = f["event_0"]["output_0.dat"]
        assert dset.shape == (2000, 4)
        full_header = dset.attrs["full_header"].decode()
        assert full_header.count("\n") == 2  # only the leading block
