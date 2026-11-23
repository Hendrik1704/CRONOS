import glob
import os
import re

import pytest

from src.check_settings import check_settings, iss_parameter_errors
from src.configuration import Configuration, load_config
from src.modules.iSS import format_iss_value, iSS
from src.modules.iss_parameters import (
    ISS_CRONOS_CONTROLLED_PARAMETERS,
    ISS_PARAMETERS,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
ISS_SOURCE_DIR = os.path.join(PROJECT_ROOT, "external_codes", "iSS", "src")


def _load_config(modules=("from_file_IC", "MUSIC", "iSS", "SMASH")):
    config = load_config(os.path.join(CONFIG_DIR, "main_config.py"))
    config.general.modules = list(modules)
    return config


def _write_parameter_file(tmp_path, config):
    (tmp_path / "iSS").mkdir()
    (tmp_path / "results").mkdir()
    module = iSS(config.iSS, config, PROJECT_ROOT, "event_0")
    module.prepare_input(str(tmp_path))
    text = (tmp_path / "iSS" / "parameters_iSS.ini").read_text()
    return dict(line.split(" = ") for line in text.splitlines())


@pytest.mark.skipif(
    not os.path.isdir(ISS_SOURCE_DIR), reason="iSS source not downloaded"
)
def test_parameter_list_matches_iss_source():
    """Regenerate iss_parameters.py when this fails after an iSS update."""
    source = ""
    for path in sorted(glob.glob(os.path.join(ISS_SOURCE_DIR, "*.[ch]*"))):
        with open(path, errors="replace") as f:
            source += f.read()
    keys = re.findall(r'(?:getVal|exist)\(\s*"(\w+)"', source)
    assert set(keys) == ISS_PARAMETERS


def test_main_config_only_has_iss_parameters():
    config = _load_config()
    assert iss_parameter_errors(config.iSS) == []


@pytest.mark.parametrize("random_seed", [-1, 42])
def test_prepare_input_writes_every_parameter(tmp_path, random_seed):
    config = _load_config()
    config.general.random_seed = random_seed
    config.iSS["include_spectators"] = True

    parameters = _write_parameter_file(tmp_path, config)

    assert set(parameters) == set(config.iSS.to_dict()) | set(
        ISS_CRONOS_CONTROLLED_PARAMETERS
    )
    assert parameters["randomSeed"] == str(random_seed)
    assert parameters["include_spectators"] == "1"
    assert parameters["use_OSCAR_format"] == "1"  # SMASH reads OSCAR
    assert (tmp_path / "iSS" / "results" / "surface.dat").is_symlink()


def test_prepare_input_without_smash_performs_decays(tmp_path):
    config = _load_config(["from_file_IC", "MUSIC", "iSS"])
    parameters = _write_parameter_file(tmp_path, config)
    assert parameters["use_OSCAR_format"] == "0"
    assert parameters["use_binary_format"] == "1"
    assert parameters["perform_decays"] == "1"


@pytest.mark.parametrize(
    "modules, output_file",
    [
        (["from_file_IC", "MUSIC", "iSS", "SMASH"], "OSCAR.DAT"),
        (["from_file_IC", "MUSIC", "iSS"], "particle_samples.bin"),
    ],
)
def test_fetch_output_finds_the_sampled_particles(
    tmp_path, modules, output_file
):
    """A fresh module (e.g. on resume) must find the file iSS wrote."""
    config = _load_config(modules)
    (tmp_path / "iSS").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "iSS" / output_file).write_text("particles")
    module = iSS(config.iSS, config, PROJECT_ROOT, "event_0")

    module.fetch_output(str(tmp_path))

    assert (tmp_path / "results" / "output_2.dat").read_text() == "particles"


@pytest.mark.parametrize(
    "value, expected",
    [(True, "1"), (False, "0"), (100000, "100000"), (0.16, "0.16")],
)
def test_format_iss_value(value, expected):
    assert format_iss_value(value) == expected


@pytest.mark.parametrize(
    "key, value, message",
    [
        ("number_of_particle_needed", 10, "Did you mean"),
        ("Hydro_Mode", 1, "iSS spells it 'hydro_mode'"),
        ("global_momentum_conservation", 0, "does not read"),
        ("randomSeed", 7, "set by CRONOS"),
        ("y_LB", "-5", "must be a number"),
        ("y_RB", [5.0], "must be a number"),
    ],
)
def test_check_settings_rejects_iss_parameters(key, value, message, caplog):
    config = _load_config()
    config.iSS[key] = value
    assert not check_settings(config)
    assert message in caplog.text


def test_iss_keys_are_only_checked_when_iss_runs():
    config = Configuration(
        {"general": {"modules": ["SMASH"]}, "iSS": {"typo": 1}}
    )
    assert check_settings(config)
