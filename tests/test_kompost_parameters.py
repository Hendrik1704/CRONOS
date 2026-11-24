import glob
import os
import re

import pytest
from cpp_source import read_cpp_sources, strip_cpp_comments

from src.check_settings import check_settings, kompost_parameter_errors
from src.configuration import load_config
from src.modules.kompost_parameters import (
    KOMPOST3D_PARAMETERS,
    KOMPOST_CRONOS_CONTROLLED_PARAMETERS,
    KOMPOST_PARAMETERS,
    KOMPOST_SECTIONS,
    format_kompost_value,
    write_kompost_parameters,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
CHAINS = {
    "KoMPoST": ["from_file_IC", "KoMPoST", "entropy_matching", "MUSIC"],
    "KoMPoST3D": ["from_file_IC", "KoMPoST3D", "entropy_matching", "MUSIC"],
}
KNOWN = {"KoMPoST": KOMPOST_PARAMETERS, "KoMPoST3D": KOMPOST3D_PARAMETERS}


def _source_dir(code):
    return os.path.join(PROJECT_ROOT, "external_codes", code, "src")


def _load_config(module):
    config = load_config(os.path.join(CONFIG_DIR, "main_config.py"))
    config.general.modules = CHAINS[module]
    return config


def test_comment_stripping_keeps_strings():
    source = 'a = "x//y"; // c\nb /* d */ = 1; s = "p/*.dat";'
    assert strip_cpp_comments(source) == 'a = "x//y"; \nb  = 1; s = "p/*.dat";'


@pytest.mark.parametrize(
    "code, known",
    [("KoMPoST", KOMPOST_PARAMETERS), ("KoMPoST-3D", KOMPOST3D_PARAMETERS)],
)
def test_parameter_lists_match_the_source(code, known):
    """Regenerate kompost_parameters.py when this fails after an update."""
    if not os.path.isdir(_source_dir(code)):
        pytest.skip(f"{code} source not downloaded")
    source = read_cpp_sources(
        glob.glob(os.path.join(_source_dir(code), "*.cpp"))
        + glob.glob(os.path.join(_source_dir(code), "*.h"))
    )
    reads = re.findall(
        r'\.Get(?:Real|Integer|String|Boolean|)\(\s*"(\w+)"\s*,\s*"(\w+)"',
        source,
    )
    assert {key: section for section, key in reads} == known


@pytest.mark.parametrize("module", ["KoMPoST", "KoMPoST3D"])
def test_main_config_only_has_kompost_parameters(module):
    config = _load_config(module)
    assert kompost_parameter_errors(module, config[module], KNOWN[module]) == []


def _read_ini(path):
    sections, section = {}, None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("["):
                section = line.strip("[]")
                sections[section] = {}
            elif line:
                key, value = (part.strip() for part in line.split("=", 1))
                sections[section][key] = value
    return sections


@pytest.mark.parametrize("module", ["KoMPoST", "KoMPoST3D"])
def test_write_puts_every_parameter_in_its_section(tmp_path, module):
    config = _load_config(module)
    parameters = config[module].to_dict()
    parameters["ENERGY_PERTURBATIONS"] = True
    path = tmp_path / "parameters.ini"

    write_kompost_parameters(path, parameters, KNOWN[module])

    sections = _read_ini(path)
    assert list(sections) == list(KOMPOST_SECTIONS)
    for key, value in parameters.items():
        assert sections[KNOWN[module][key]][key] == format_kompost_value(value)
    assert sections["KoMPoSTParameters"]["ENERGY_PERTURBATIONS"] == "1"


def test_write_rejects_unknown_parameters(tmp_path):
    with pytest.raises(ValueError, match="does not read"):
        write_kompost_parameters(
            tmp_path / "parameters.ini",
            {"tIn": 0.2, "tin_typo": 1},
            KOMPOST_PARAMETERS,
        )


@pytest.mark.parametrize("module", ["KoMPoST", "KoMPoST3D"])
@pytest.mark.parametrize(
    "key, value, message",
    [
        ("EtaOverSs", 0.1, "Did you mean 'EtaOverS'"),
        ("etaovers", 0.1, "spells it 'EtaOverS'"),
        ("DECOMPOSITION_METHOD", 1, "does not read"),
        ("Sigma", 1.0, "does not read"),  # only read in commented-out code
        ("InputFile", "x.dat", "set by CRONOS"),
        ("Regulator", "Two Pass", "without spaces"),
        ("Regulator", "TwoPass;", "without spaces"),
    ],
)
def test_check_settings_rejects_kompost_parameters(
    module, key, value, message, caplog
):
    config = _load_config(module)
    config[module][key] = value
    assert not check_settings(config)
    assert message in caplog.text


@pytest.mark.parametrize("module", ["KoMPoST", "KoMPoST3D"])
def test_kompost_keys_are_only_checked_when_kompost_runs(module):
    config = load_config(os.path.join(CONFIG_DIR, "main_config.py"))
    config.general.modules = ["from_file_IC", "MUSIC"]
    config[module]["typo"] = 1
    assert check_settings(config)


def test_controlled_parameters_are_kompost_parameters():
    for name in KOMPOST_CRONOS_CONTROLLED_PARAMETERS:
        assert name in KOMPOST_PARAMETERS and name in KOMPOST3D_PARAMETERS
