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
            ]
        },
        "from_file_IC": {"boost_invariant": 0},
        "KoMPoST3D": {
            "tOut": 0.8,
            "NuEffective": 40.0,
            "EVOLUTION_MODE": 1,
            "MOMENTUM_PERTURBATIONS": 0,
        },
        "entropy_matching": {"nu_eff": 40.0},
        "MUSIC": {
            "boost_invariant": 0,
            "Initial_profile": 95,
            "Initial_time_tau_0": 0.8,
        },
    }
    for key, value in overrides.items():
        section, name = key.split("__")
        if section == "general":
            settings["general"][name] = value
        else:
            settings[section][name] = value
    return Configuration(settings)


def test_kompost3d_consistent_settings_are_valid():
    assert check_settings(_kompost3d_config())


@pytest.mark.parametrize(
    "override",
    [
        {"general__modules": ["from_file_IC", "KoMPoST", "KoMPoST3D", "MUSIC"]},
        {"KoMPoST3D__EVOLUTION_MODE": 0},
        {"KoMPoST3D__MOMENTUM_PERTURBATIONS": 1},
        {"from_file_IC__boost_invariant": 1},
        {"MUSIC__boost_invariant": 1},
        {"MUSIC__Initial_profile": 94},
        {"MUSIC__Initial_time_tau_0": 0.6},
        {"entropy_matching__nu_eff": 16.0},
    ],
)
def test_kompost3d_inconsistent_settings_are_invalid(override):
    assert not check_settings(_kompost3d_config(**override))
