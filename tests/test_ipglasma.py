import os

import pytest

from src.check_settings import check_settings
from src.configuration import Configuration, load_config
from src.modules.IPGlasma import (
    IPGLASMA_PARAMETERS,
    RENAMED_PARAMETERS,
    REPLACED_PARAMETERS,
    IPGlasma,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_config(modules):
    config = load_config(
        os.path.join(PROJECT_ROOT, "config", "main_config.py"),
        os.path.join(PROJECT_ROOT, "config", "user_config_ipglasma.py"),
    )
    config.general.modules = modules
    return config


def _read_parameter_file(event_dir):
    path = os.path.join(event_dir, "IPGlasma", "parameters_IPGlasma.ini")
    parameters = {}
    with open(path) as f:
        for line in f:
            if line.strip() and line.strip() != "EndOfFile":
                key, value = line.split(maxsplit=1)
                parameters[key] = value.strip()
    return parameters


def test_main_config_provides_all_parameters():
    config = _load_config(["IPGlasma", "MUSIC"])
    ipglasma_config = config.IPGlasma.to_dict()
    assert [k for k in IPGLASMA_PARAMETERS if k not in ipglasma_config] == []


def test_shipped_configs_use_no_old_parameter_names():
    config = _load_config(["IPGlasma", "MUSIC"])
    old_names = set(RENAMED_PARAMETERS) | set(REPLACED_PARAMETERS)
    assert old_names.isdisjoint(config.IPGlasma.to_dict())
    assert check_settings(config)


@pytest.mark.parametrize("random_seed", [-1, 42])
def test_prepare_input_writes_ipglasma2_parameters(tmp_path, random_seed):
    config = _load_config(["IPGlasma", "MUSIC"])
    config.general.random_seed = random_seed
    (tmp_path / "IPGlasma").mkdir()
    module = IPGlasma(config.IPGlasma, config, PROJECT_ROOT, "event_0")

    module.prepare_input(str(tmp_path))

    parameters = _read_parameter_file(str(tmp_path))
    expected_keys = set(IPGLASMA_PARAMETERS) | {
        "useSeedList",
        "seed",
        "writeTmunuBinary",
        "jimwlkXSnapshotList",
    }
    assert set(parameters) == expected_keys
    assert parameters["seed"] == str(random_seed)
    assert parameters["writeTmunuBinary"] == "0"  # KoMPoST reads text
    assert parameters["projectile"] == "Pb"  # from the user config
    assert parameters["nucleonModel"] == "hotspots"


@pytest.mark.parametrize(
    "old_key", ["Projectile", "x_projectile_jimwlk", "writeOutputs", "mode"]
)
def test_check_settings_rejects_old_parameter_names(old_key):
    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma[old_key] = 1
    assert not check_settings(config)


def test_check_settings_requires_matching_output():
    config = _load_config(["IPGlasma", "KoMPoST", "entropy_matching", "MUSIC"])
    config.IPGlasma.writeTmunu = 0
    assert not check_settings(config)

    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma.writeHydro = 0
    assert not check_settings(config)


@pytest.mark.parametrize(
    "modules, expected",
    [
        (["IPGlasma", "MUSIC"], "hydro"),
        (["IPGlasma", "KoMPoST", "entropy_matching", "MUSIC"], "tmunu"),
    ],
)
def test_fetch_output_selects_file_for_next_module(tmp_path, modules, expected):
    config = Configuration(
        {
            "general": {"modules": modules},
        }
    )
    ipglasma_config = Configuration(
        {"writeHydro": 1, "writeTmunu": 1, "maxTime": 0.4}
    )
    ipglasma_dir = tmp_path / "IPGlasma"
    ipglasma_dir.mkdir()
    (ipglasma_dir / "epsilon-u-Hydro-TauHydro-0.dat").write_text("hydro")
    (ipglasma_dir / "Tmunu-t0.4-0.dat").write_text("tmunu")
    (ipglasma_dir / "usedParameters0.dat").write_text("# parameters")
    module = IPGlasma(ipglasma_config, config, PROJECT_ROOT, "event_0")

    module.fetch_output(str(tmp_path))

    assert (tmp_path / "results" / "output_0.dat").read_text() == expected
    assert (tmp_path / "results" / "usedParameters0.dat").exists()
    assert not ipglasma_dir.exists()
