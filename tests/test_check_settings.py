import logging
import os

import pytest

from src.check_settings import check_settings
from src.configuration import load_config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _kompost3d_config(**overrides):
    """The shipped KoMPoST3D chain (main_config + example user config)."""
    config = load_config(
        os.path.join(PROJECT_ROOT, "config", "main_config.py"),
        os.path.join(
            PROJECT_ROOT,
            "config",
            "user_config_from_file_KoMPoST3D_SMASH_decays.py",
        ),
    )
    for key, value in overrides.items():
        section, name = key.split("__")
        config[section][name] = value
    return config


def test_kompost3d_consistent_settings_are_valid():
    assert check_settings(_kompost3d_config())


@pytest.mark.parametrize(
    "override, message",
    [
        (
            {"general__modules": ["from_file_IC", "KoMPoST", "KoMPoST3D", "MUSIC"]},
            "cannot be used together",
        ),
        (
            {"general__modules": ["KoMPoST3D", "entropy_matching", "MUSIC"]},
            "must directly follow from_file_IC",
        ),
        (
            {"general__modules": ["from_file_IC", "KoMPoST3D", "MUSIC"]},
            "entropy_matching must directly follow KoMPoST3D",
        ),
        ({"KoMPoST3D__EVOLUTION_MODE": 0}, "EVOLUTION_MODE"),
        ({"KoMPoST3D__MOMENTUM_PERTURBATIONS": 1}, "MOMENTUM_PERTURBATIONS"),
        ({"KoMPoST3D__ENERGY_PERTURBATIONS": 2}, "ENERGY_PERTURBATIONS"),
        ({"KoMPoST3D__Regulator": "Twopass"}, "Regulator"),
        ({"KoMPoST3D__tIn": 0.8}, "'tIn' < 'tOut'"),
        ({"KoMPoST3D__xEND": 128}, "xEND"),
        ({"KoMPoST3D__ySTART": -1}, "ySTART"),
        ({"KoMPoST3D__etaEND": 65}, "etaEND"),
        ({"from_file_IC__boost_invariant": 1}, "boost_invariant"),
        ({"MUSIC__boost_invariant": 1}, "boost_invariant"),
        ({"MUSIC__Initial_profile": 94}, "Initial_profile"),
        ({"MUSIC__Initial_time_tau_0": 0.6}, "Initial_time_tau_0"),
        # MUSIC takes the eta grid and the grid extent from its parameters
        ({"MUSIC__Grid_size_in_eta": 101}, "Grid_size_in_eta"),
        ({"MUSIC__Eta_grid_size": 20.0}, "Eta_grid_size"),
        ({"MUSIC__X_grid_size_in_fm": 30.0}, "X_grid_size_in_fm"),
        (
            {
                "entropy_matching__matching_type": 1,
                "entropy_matching__nu_eff": 16.0,
            },
            "nu_eff",
        ),
    ],
)
def test_kompost3d_inconsistent_settings_are_invalid(override, message, caplog):
    with caplog.at_level(logging.ERROR):
        assert not check_settings(_kompost3d_config(**override))
    assert message in caplog.text


def test_nu_eff_only_checked_for_entropy_matching():
    config = _kompost3d_config(
        entropy_matching__nu_eff=16.0, entropy_matching__matching_type=0
    )
    assert check_settings(config)


def test_kompost3d_partial_region_and_low_memory_only_warn(caplog):
    config = _kompost3d_config(
        KoMPoST3D__xSTART=10, general__memory_threshold_mb=4096
    )
    with caplog.at_level(logging.WARNING):
        assert check_settings(config)
    assert "only evolves xSTART..xEND" in caplog.text
    assert "~9 GB of memory" in caplog.text
