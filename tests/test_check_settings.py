import pytest

from src.check_settings import check_settings
from src.configuration import Configuration


def _kompost3d_config(**overrides):
    """Consistent from_file_IC -> KoMPoST3D -> entropy_matching -> MUSIC setup."""
    settings = {
        "general": {
            "modules": [
                "from_file_IC",
                "KoMPoST3D",
                "entropy_matching",
                "MUSIC",
            ],
            "memory_threshold_mb": 12288,
        },
        "from_file_IC": {"boost_invariant": 0},
        "KoMPoST3D": {
            "tOut": 0.8,
            "NuEffective": 40.0,
            "EVOLUTION_MODE": 1,
            "MOMENTUM_PERTURBATIONS": 0,
            "afm": 0.21,
            "deta": 0.25,
            "Ns": 128,
            "Neta": 65,
            "xSTART": 0,
            "xEND": 127,
            "ySTART": 0,
            "yEND": 127,
            "etaSTART": 0,
            "etaEND": 64,
        },
        "entropy_matching": {"nu_eff": 40.0, "matching_type": 1},
        "MUSIC": {
            "boost_invariant": 0,
            "Initial_profile": 95,
            "Initial_time_tau_0": 0.8,
            "Grid_size_in_eta": 65,
            "Eta_grid_size": 16.0,
            "X_grid_size_in_fm": 26.67,
            "Y_grid_size_in_fm": 26.67,
        },
    }
    for key, value in overrides.items():
        section, name = key.split("__")
        settings[section][name] = value
    return Configuration(settings)


def test_kompost3d_consistent_settings_are_valid():
    assert check_settings(_kompost3d_config())


@pytest.mark.parametrize(
    "override",
    [
        {"general__modules": ["from_file_IC", "KoMPoST", "KoMPoST3D", "MUSIC"]},
        {"general__modules": ["KoMPoST3D", "entropy_matching", "MUSIC"]},
        {"KoMPoST3D__EVOLUTION_MODE": 0},
        {"KoMPoST3D__MOMENTUM_PERTURBATIONS": 1},
        {"KoMPoST3D__xEND": 128},
        {"KoMPoST3D__ySTART": -1},
        {"KoMPoST3D__etaEND": 65},
        {"from_file_IC__boost_invariant": 1},
        {"MUSIC__boost_invariant": 1},
        {"MUSIC__Initial_profile": 94},
        {"MUSIC__Initial_time_tau_0": 0.6},
        # MUSIC takes the eta grid and the grid extent from its parameters
        {"MUSIC__Grid_size_in_eta": 101},
        {"MUSIC__Eta_grid_size": 20.0},
        {"MUSIC__X_grid_size_in_fm": 30.0},
        {"entropy_matching__nu_eff": 16.0},
    ],
)
def test_kompost3d_inconsistent_settings_are_invalid(override):
    assert not check_settings(_kompost3d_config(**override))


def test_nu_eff_only_checked_for_entropy_matching():
    config = _kompost3d_config(
        entropy_matching__nu_eff=16.0, entropy_matching__matching_type=0
    )
    assert check_settings(config)


def test_kompost3d_partial_region_and_low_memory_only_warn(caplog):
    config = _kompost3d_config(
        KoMPoST3D__xSTART=10, general__memory_threshold_mb=4096
    )
    assert check_settings(config)
    assert "only evolves xSTART..xEND" in caplog.text
    assert "~9 GB of memory" in caplog.text
