import logging
import os
import re
import subprocess
import sys
from unittest.mock import patch

import pytest
from cpp_source import read_cpp_sources

from src.check_settings import check_settings, ipglasma_parameter_errors
from src.configuration import Configuration, load_config
from src.modules.ipglasma_parameters import IPGLASMA_PARAMETERS
from src.modules.IPGlasma import (
    CRONOS_CONTROLLED_PARAMETERS,
    IPGlasma,
    format_ipglasma_value,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPGLASMA_PARAMETER_TABLE = os.path.join(
    PROJECT_ROOT, "external_codes", "ipglasma", "src", "ParameterTable.cpp"
)


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
    config.KoMPoST.xEND = config.KoMPoST.yEND = config.KoMPoST.Ns - 1
    config.KoMPoST.tOut = config.MUSIC.Initial_time_tau_0 = 1.0
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
    "change, message",
    [
        ({"seed": 7}, "set by CRONOS"),
        ({"writeTmunuBinary": 1}, "set by CRONOS"),
        ({"useFluctuatingX": 1}, "useFluctuatingX"),
        ({"writeHydro": 0}, "writeHydro"),
        ({"maxTime": 0.6}, "Initial_time_tau_0"),  # MUSIC starts at 0.4
        ({"runEvolution": 0}, "runEvolution"),
        ({"inverseQsForMaxTime": 1}, "inverseQsForMaxTime"),
        ({"projectileX": 0.02}, "above 'jimwlkInitialX'"),
    ],
)
def test_check_settings_rejects_inconsistent_ipglasma_settings(
    change, message, caplog
):
    config = _load_config(["IPGlasma", "MUSIC"])
    for key, value in change.items():
        config.IPGlasma[key] = value
    with caplog.at_level(logging.ERROR):
        assert not check_settings(config)
    assert message in caplog.text


def test_check_settings_rejects_music_profile_with_bulk_after_ipglasma(caplog):
    """The IP-Glasma hydro file has no bulk column (profile 94 reads one)."""
    config = _load_config(["IPGlasma", "MUSIC"])
    config.MUSIC.Initial_profile = 94
    with caplog.at_level(logging.ERROR):
        assert not check_settings(config)
    assert "Initial_profile" in caplog.text


@pytest.mark.parametrize(
    "section, key, value, message",
    [
        ("IPGlasma", "writeTmunu", 0, "writeTmunu"),
        ("KoMPoST", "tIn", 0.2, "'tIn'"),
        ("KoMPoST", "Ns", 512, "'Ns' and 'afm'"),
        ("KoMPoST", "afm", 0.08, "'Ns' and 'afm'"),
        # KoMPoST indexes its grid without range checks
        ("KoMPoST", "xEND", 511, "xEND"),
    ],
)
def test_check_settings_checks_kompost_after_ipglasma(
    section, key, value, message, caplog
):
    config = _kompost_after_ipglasma_config()
    assert check_settings(config)
    config[section][key] = value
    with caplog.at_level(logging.ERROR):
        assert not check_settings(config)
    assert message in caplog.text


def test_check_settings_warns_if_jimwlk_does_not_evolve(caplog):
    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma.projectileX = config.IPGlasma.jimwlkInitialX
    with caplog.at_level(logging.WARNING):
        assert check_settings(config)
    assert "JIMWLK does not evolve it" in caplog.text


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

    with patch.object(
        sys.modules["src.modules.IPGlasma"],
        "run_external_command",
        side_effect=failing_run,
    ):
        with pytest.raises(subprocess.CalledProcessError):
            module.run(str(tmp_path))

    assert "maxtime was renamed to maxTime" in caplog.text
    assert (tmp_path / "IPGlasma" / "ipglasma.log").exists()


def test_fetch_output_ignores_tmunu_at_other_times(tmp_path):
    """Only the file at maxTime is passed on (not e.g. an outputTimes file)."""
    config = Configuration(
        {"general": {"modules": ["IPGlasma", "KoMPoST", "MUSIC"]}}
    )
    ipglasma_config = Configuration(
        {"writeHydro": 0, "writeTmunu": 1, "maxTime": 0.4}
    )
    ipglasma_dir = tmp_path / "IPGlasma"
    ipglasma_dir.mkdir()
    (ipglasma_dir / "Tmunu-t0.05-0.dat").write_text("early")
    module = IPGlasma(ipglasma_config, config, PROJECT_ROOT, "event_0")

    with pytest.raises(FileNotFoundError):
        module.fetch_output(str(tmp_path))


@pytest.mark.skipif(
    not os.path.exists(IPGLASMA_PARAMETER_TABLE),
    reason="IP-Glasma 2.0 source not downloaded",
)
def test_parameter_list_matches_ipglasma_source():
    """Regenerate ipglasma_parameters.py when this fails after an update."""
    source = read_cpp_sources([IPGLASMA_PARAMETER_TABLE])
    keys = re.findall(r'\bparam\(\s*"(\w+)"', source)
    assert set(keys) == IPGLASMA_PARAMETERS


def test_shipped_configs_only_have_ipglasma_parameters():
    assert ipglasma_parameter_errors(_load_config(["IPGlasma"]).IPGlasma) == []
    assert set(CRONOS_CONTROLLED_PARAMETERS) <= IPGLASMA_PARAMETERS


@pytest.mark.parametrize(
    "key, value, message",
    [
        ("maxTIme", 0.4, "IPGlasma spells it 'maxTime'"),
        ("jimwlkMuu0", 0.28, "Did you mean 'jimwlkMu0'"),
        ("subNucleonParamType", 0, "does not read"),
        ("seed", 7, "set by CRONOS (set from general.random_seed)"),
        ("nucleonModel", "hot spots", "list of numbers"),
        ("jimwlkXSnapshotList", ["0.005"], "list of numbers"),
    ],
)
def test_check_settings_rejects_ipglasma_parameters(
    key, value, message, caplog
):
    """Problems are found before the runs, not only when IP-Glasma starts."""
    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma[key] = value
    assert not check_settings(config)
    assert message in caplog.text


def test_check_settings_accepts_a_list_of_numbers():
    config = _load_config(["IPGlasma", "MUSIC"])
    config.IPGlasma["jimwlkXSnapshotList"] = [5e-3, 1e-3]
    assert check_settings(config)
