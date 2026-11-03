import glob
import os

import pytest

from src.check_settings import check_settings, iss_effective_afterburner_type
from src.configuration import load_config

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
MAIN_CONFIG = os.path.join(CONFIG_DIR, "main_config.py")
USER_CONFIGS = sorted(glob.glob(os.path.join(CONFIG_DIR, "user_config_*.py")))


def make_config(modules, **overrides):
    """main_config.py with the given modules and section overrides."""
    config = load_config(MAIN_CONFIG)
    config.merge({"general": {"modules": modules}})
    config.merge(overrides)
    return config


BOOST_INVARIANT_CHAIN = ["MUSIC", "iSS", "SMASH"]
KOMPOST_CHAIN = [
    "from_file_IC",
    "KoMPoST",
    "entropy_matching",
    "MUSIC",
    "iSS",
    "SMASH",
]


def test_shipped_user_configs_found():
    assert len(USER_CONFIGS) >= 5


@pytest.mark.parametrize(
    "user_config", USER_CONFIGS, ids=[os.path.basename(p) for p in USER_CONFIGS]
)
def test_shipped_user_configs_pass(user_config):
    assert check_settings(load_config(MAIN_CONFIG, user_config))


def test_main_config_defaults_are_consistent():
    assert check_settings(make_config(BOOST_INVARIANT_CHAIN))
    assert check_settings(make_config(["from_file_IC"] + BOOST_INVARIANT_CHAIN))


def test_kompost_tout_must_match_music_tau0():
    music = {"Initial_time_tau_0": 0.4}
    kompost = {"tOut": 1.0}
    assert not check_settings(
        make_config(KOMPOST_CHAIN, KoMPoST=kompost, MUSIC=music)
    )
    music = {"Initial_time_tau_0": 0.1 + 0.9}  # 0.9999999999999999
    assert check_settings(
        make_config(KOMPOST_CHAIN, KoMPoST=kompost, MUSIC=music)
    )
    # Only checked when KoMPoST feeds MUSIC
    assert check_settings(
        make_config(BOOST_INVARIANT_CHAIN, KoMPoST=kompost, MUSIC={})
    )


@pytest.mark.parametrize(
    "boost_invariant, profile, hydro_mode, valid",
    [
        (1, 94, 1, True),
        (1, 9, 1, True),
        (0, 95, 2, True),
        (1, 94, 2, False),  # main_config defaults before the fix
        (0, 95, 1, False),
        (0, 94, 2, False),  # 2D profile in a (3+1)D run
        (1, 95, 1, False),  # 3D profile in a boost-invariant run
    ],
)
def test_music_iss_dimensions(boost_invariant, profile, hydro_mode, valid):
    config = make_config(
        BOOST_INVARIANT_CHAIN,
        MUSIC={"boost_invariant": boost_invariant, "Initial_profile": profile},
        iSS={"hydro_mode": hydro_mode},
    )
    assert check_settings(config) == valid


def test_from_file_ic_must_match_music_without_iss():
    config = make_config(
        ["from_file_IC", "MUSIC"],
        from_file_IC={"boost_invariant": 0},
        MUSIC={"boost_invariant": 1},
    )
    assert not check_settings(config)


@pytest.mark.parametrize(
    "use_eps, n_freeze_out, valid",
    [(1, 1, True), (1, 2, False), (0, 2, True)],  # MUSIC uses 1 for T_freeze
)
def test_single_freeze_out_surface(use_eps, n_freeze_out, valid):
    config = make_config(
        BOOST_INVARIANT_CHAIN,
        MUSIC={"use_eps_for_freeze_out": use_eps, "N_freeze_out": n_freeze_out},
    )
    assert check_settings(config) == valid


@pytest.mark.parametrize(
    "eos, afterburner_type, expected",
    [(91, 0, 2), (9, 2, 1), (14, 2, 2), (14, 1, 1), (14, 0, 0), (2, 5, 0)],
)
def test_iss_effective_afterburner_type(eos, afterburner_type, expected):
    assert iss_effective_afterburner_type(eos, afterburner_type) == expected


@pytest.mark.parametrize(
    "eos, afterburner_type, with_smash, valid",
    [
        (91, 2, True, True),
        (91, 0, True, True),
        (14, 2, True, True),
        (9, 2, True, False),  # UrQMD particles, SMASH converter
        (14, 0, True, False),
        (91, 0, False, False),  # decays skipped without SMASH
        (14, 2, False, False),
        (9, 2, False, True),
        (14, 0, False, True),
    ],
)
def test_iss_afterburner_type(eos, afterburner_type, with_smash, valid):
    modules = ["MUSIC", "iSS"] + (["SMASH"] if with_smash else [])
    config = make_config(
        modules,
        MUSIC={"EOS_to_use": eos},
        iSS={"afterburner_type": afterburner_type},
    )
    assert check_settings(config) == valid
