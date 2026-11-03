import logging
import os
import subprocess
from unittest.mock import patch

import pytest

from src.check_settings import check_settings
from src.configuration import Configuration, load_config
from src.modules.IPGlasma import (
    CRONOS_CONTROLLED_PARAMETERS,
    IPGlasma,
    format_ipglasma_value,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_config(modules):
    config = load_config(
        os.path.join(PROJECT_ROOT, "config", "main_config.py"),
        os.path.join(PROJECT_ROOT, "config", "user_config_ipglasma.py"),
    )
    config.general.modules = modules
    return config


def _kompost_after_ipglasma_config():
    config = _load_config(["IPGlasma", "KoMPoST", "entropy_matching", "MUSIC"])
    config.IPGlasma.writeTmunu = 1
    config.KoMPoST.tIn = config.IPGlasma.maxTime
    config.KoMPoST.Ns = config.IPGlasma.sizeOutput
    config.KoMPoST.afm = config.IPGlasma.LOutput / config.IPGlasma.sizeOutput
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


def _write_parameter_file(tmp_path, config):
    (tmp_path / "IPGlasma").mkdir()
    module = IPGlasma(config.IPGlasma, config, PROJECT_ROOT, "event_0")
    module.prepare_input(str(tmp_path))
    return _read_parameter_file(str(tmp_path))


def test_shipped_configs_are_valid():
    assert check_settings(_load_config(["IPGlasma", "MUSIC"]))
    assert check_settings(_kompost_after_ipglasma_config())


@pytest.mark.parametrize("random_seed", [-1, 42])
def test_prepare_input_writes_every_parameter(tmp_path, random_seed):
    config = _load_config(["IPGlasma", "MUSIC"])
    config.general.random_seed = random_seed

    parameters = _write_parameter_file(tmp_path, config)

    expected_keys = set(config.IPGlasma.to_dict()) | set(
        CRONOS_CONTROLLED_PARAMETERS
    )
    assert set(parameters) == expected_keys
    assert parameters["seed"] == str(random_seed)
    assert parameters["writeTmunuBinary"] == "0"  # KoMPoST reads text
    assert parameters["writeOutputsToHDF5"] == "0"
    assert parameters["projectile"] == "Pb"  # from the user config
    assert parameters["nucleonModel"] == "hotspots"


def test_prepare_input_passes_unknown_keys_to_ipglasma(tmp_path):
    """IP-Glasma rejects a misspelled key instead of it being ignored."""
    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma["maxTIme"] = 0.6

    parameters = _write_parameter_file(tmp_path, config)

    assert parameters["maxTIme"] == "0.6"


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "1"),
        (False, "0"),
        (800, "800"),
        (0.4, "0.4"),
        ("hotspots", "hotspots"),
        ([5e-3, 1.294820717e-4], "0.005,0.0001294820717"),
        ([], "none"),
    ],
)
def test_format_ipglasma_value(value, expected):
    assert format_ipglasma_value(value) == expected


@pytest.mark.parametrize(
    "change",
    [
        {"seed": 7},
        {"writeTmunuBinary": 1},
        {"useFluctuatingX": 1},
        {"writeHydro": 0},
        {"maxTime": 0.6},  # MUSIC starts at 0.4
    ],
)
def test_check_settings_rejects_inconsistent_ipglasma_settings(change):
    config = _load_config(["IPGlasma", "MUSIC"])
    for key, value in change.items():
        config.IPGlasma[key] = value
    assert not check_settings(config)


@pytest.mark.parametrize(
    "section, key, value",
    [
        ("IPGlasma", "writeTmunu", 0),
        ("KoMPoST", "tIn", 0.2),
        ("KoMPoST", "Ns", 512),
        ("KoMPoST", "afm", 0.08),
    ],
)
def test_check_settings_checks_kompost_after_ipglasma(section, key, value):
    config = _kompost_after_ipglasma_config()
    config[section][key] = value
    assert not check_settings(config)


def test_check_settings_warns_if_jimwlk_does_not_evolve(caplog):
    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma.projectileX = config.IPGlasma.jimwlkInitialX
    with caplog.at_level(logging.WARNING):
        assert check_settings(config)
    assert "JIMWLK only evolves" in caplog.text


@pytest.mark.parametrize(
    "modules, write_hydro, max_time, expected",
    [
        (["IPGlasma", "MUSIC"], 1, 0.4, "hydro"),
        (["IPGlasma", "KoMPoST", "entropy_matching", "MUSIC"], 1, 0.4, "tmunu"),
        # IP-Glasma writes Tmunu-t1-0.dat for maxTime 1
        (["IPGlasma", "KoMPoST", "entropy_matching", "MUSIC"], 0, 1, "tmunu"),
    ],
)
def test_fetch_output_selects_file_for_next_module(
    tmp_path, modules, write_hydro, max_time, expected
):
    config = Configuration({"general": {"modules": modules}})
    ipglasma_config = Configuration(
        {"writeHydro": write_hydro, "writeTmunu": 1, "maxTime": max_time}
    )
    ipglasma_dir = tmp_path / "IPGlasma"
    ipglasma_dir.mkdir()
    if write_hydro:
        (ipglasma_dir / "epsilon-u-Hydro-TauHydro-0.dat").write_text("hydro")
    (ipglasma_dir / f"Tmunu-t{max_time:g}-0.dat").write_text("tmunu")
    (ipglasma_dir / "usedParameters0.dat").write_text("# parameters")
    module = IPGlasma(ipglasma_config, config, PROJECT_ROOT, "event_0")

    module.fetch_output(str(tmp_path))

    assert (tmp_path / "results" / "output_0.dat").read_text() == expected
    assert (tmp_path / "results" / "usedParameters0.dat").exists()
    assert not ipglasma_dir.exists()


def test_run_reports_ipglasma_output_on_failure(tmp_path, caplog):
    """IP-Glasma reports input errors on stdout, which is otherwise hidden."""
    config = _load_config(["IPGlasma", "MUSIC"])
    config.general.module_terminal_output = False
    (tmp_path / "IPGlasma").mkdir()
    module = IPGlasma(config.IPGlasma, config, PROJECT_ROOT, "event_0")

    def failing_run(cmd, **kwargs):
        kwargs["stdout"].write("input:6: maxtime was renamed to maxTime\n")
        kwargs["stdout"].flush()
        raise subprocess.CalledProcessError(1, cmd)

    with patch(
        "src.modules.IPGlasma.run_external_command", side_effect=failing_run
    ):
        with pytest.raises(subprocess.CalledProcessError):
            module.run(str(tmp_path))

    assert "maxtime was renamed to maxTime" in caplog.text
    assert (tmp_path / "IPGlasma" / "ipglasma.log").exists()
