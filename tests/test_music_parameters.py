import os
import re

import pytest
from cpp_source import read_cpp_sources

from src.check_settings import check_settings, music_parameter_errors
from src.configuration import Configuration, load_config
from src.modules.MUSIC import MUSIC, format_music_value
from src.modules.music_parameters import (
    MUSIC_CRONOS_CONTROLLED_PARAMETERS,
    MUSIC_PARAMETERS,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
MUSIC_PARAMETER_SOURCE = os.path.join(
    PROJECT_ROOT, "external_codes", "MUSIC", "src", "read_in_parameters.cpp"
)
MODULES = ["from_file_IC", "MUSIC", "iSS", "SMASH"]


def _load_config():
    config = load_config(os.path.join(CONFIG_DIR, "main_config.py"))
    config.general.modules = MODULES
    return config


def _write_parameter_file(tmp_path, config):
    (tmp_path / "MUSIC").mkdir()
    (tmp_path / "results").mkdir()
    module = MUSIC(config.MUSIC, config, PROJECT_ROOT, "event_0")
    module.prepare_input(str(tmp_path))
    lines = (tmp_path / "MUSIC" / "parameters_MUSIC.ini").read_text()
    lines = lines.splitlines()
    assert lines[-1] == "EndOfData"
    return dict(line.split(" ", 1) for line in lines[:-1])


@pytest.mark.skipif(
    not os.path.exists(MUSIC_PARAMETER_SOURCE),
    reason="MUSIC source not downloaded",
)
def test_parameter_list_matches_music_source():
    """Regenerate music_parameters.py when this fails after a MUSIC update."""
    source = read_cpp_sources([MUSIC_PARAMETER_SOURCE])
    keys = re.findall(
        r'(?:getParameter|StringFind4)\(\s*input_file,\s*"(\w+)"', source
    )
    assert set(keys) == MUSIC_PARAMETERS


def test_main_config_only_has_music_parameters():
    config = _load_config()
    assert music_parameter_errors(config.MUSIC) == []
    assert not set(config.MUSIC.to_dict()) & set(
        MUSIC_CRONOS_CONTROLLED_PARAMETERS
    )


def test_prepare_input_writes_every_parameter(tmp_path):
    config = _load_config()
    # A parametrization the main config does not set
    config.MUSIC.T_dependent_Shear_to_S_ratio = 2
    config.MUSIC["shear_viscosity_2_min"] = 0.1
    config.MUSIC["Include_vorticity_terms"] = True

    parameters = _write_parameter_file(tmp_path, config)

    assert set(parameters) == set(config.MUSIC.to_dict()) | set(
        MUSIC_CRONOS_CONTROLLED_PARAMETERS
    )
    assert parameters["T_dependent_Shear_to_S_ratio"] == "2"
    assert parameters["shear_viscosity_2_min"] == "0.1"
    assert parameters["Include_vorticity_terms"] == "1"
    # The input is the output of the module before MUSIC
    assert (
        parameters["Initial_Distribution_input_filename"]
        == "../results/output_0.dat"
    )
    # iSS reads the parameter file from the results directory
    assert (tmp_path / "results" / "parameters_MUSIC.ini").exists()


@pytest.mark.parametrize(
    "value, expected",
    [(True, "1"), (False, "0"), (201, "201"), (0.155, "0.155"), ("a", "a")],
)
def test_format_music_value(value, expected):
    assert format_music_value(value) == expected


@pytest.mark.parametrize(
    "key, value, message",
    [
        ("shear_viscosity_3_eta_over_s_at_kinks", 0.1, "Did you mean"),
        ("shear_to_s_ratio", 0.1, "MUSIC spells it 'Shear_to_S_ratio'"),
        ("freeze_Ncell_y_step", 2, "does not read"),
        ("Initial_Distribution_input_filename", "x.dat", "set by CRONOS"),
        ("Shear_to_S_ratio", [0.1, 0.2], "without spaces"),
        ("freeze_list_filename", "my list.dat", "without spaces"),
    ],
)
def test_check_settings_rejects_music_parameters(key, value, message, caplog):
    config = _load_config()
    config.MUSIC[key] = value
    assert not check_settings(config)
    assert message in caplog.text


def test_check_settings_accepts_other_music_parametrizations():
    config = _load_config()
    config.MUSIC.merge(
        {
            "T_dependent_Shear_to_S_ratio": 2,
            "shear_viscosity_2_min": 0.08,
            "shear_viscosity_2_slope": 1.0,
            "shear_viscosity_2_curv": 0.0,
        }
    )
    assert check_settings(config)


def test_music_keys_are_only_checked_when_music_runs():
    config = Configuration(
        {"general": {"modules": ["iSS"]}, "MUSIC": {"typo": 1}}
    )
    assert check_settings(config)
