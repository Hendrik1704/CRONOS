import os
from unittest.mock import patch

import pytest

from src.configuration import Configuration
from src.handle_results import handle_results


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


def _run_handle_results(tmp_path, config):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    for i in range(3):
        (results_dir / f"output_{i}.dat").write_text(f"module {i}")
    (results_dir / "configuration.py").write_text("")

    with patch("src.handle_results.zip_into_hdf5"):
        handle_results(config, str(results_dir), "0")

    spvn_dir = results_dir / "spvn_results_0"
    return sorted(f for f in os.listdir(spvn_dir) if f.startswith("output_"))


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
    modules = ["from_file_IC", "MUSIC", "afterburner_toolkit"]
    config = _make_config(
        modules, keep_intermediate_results, keep_particle_files
    )
    assert _run_handle_results(tmp_path, config) == expected


def test_particle_files_removed_without_afterburner_toolkit(tmp_path):
    # keep_particle_files only takes effect with afterburner_toolkit
    config = _make_config(["from_file_IC", "KoMPoST", "MUSIC"], True, True)
    assert _run_handle_results(tmp_path, config) == [
        "output_0.dat",
        "output_1.dat",
    ]
