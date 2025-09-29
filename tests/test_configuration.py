import pytest
import tempfile
from pathlib import Path
from src import Configuration, load_config


def test_attribute_and_dict_access():
    cfg = Configuration({"hydro": {"tau0": 0.6, "eta_over_s": 0.08}})

    # Attribute access
    assert cfg.hydro.tau0 == 0.6
    assert cfg.hydro.eta_over_s == 0.08

    # Dict-style access
    assert cfg["hydro"]["tau0"] == 0.6
    assert cfg["hydro"]["eta_over_s"] == 0.08


def test_set_attribute_and_dict():
    cfg = Configuration({"a": 1})

    # Attribute style
    cfg.b = 2
    assert cfg.b == 2

    # Dict style
    cfg["c"] = 3
    assert cfg.c == 3
    assert cfg["c"] == 3


def test_nested_merge():
    base = Configuration(
        {
            "hydro": {"tau0": 0.6, "eta_over_s": 0.08},
            "init": {"model": "TRENTO", "norm": 1.0},
        }
    )

    override = {"hydro": {"tau0": 0.2}, "init": {"norm": 1.5}}

    base.merge(override)

    assert base.hydro.tau0 == 0.2
    assert base.hydro.eta_over_s == 0.08  # should remain
    assert base.init.norm == 1.5


def test_to_dict_conversion():
    cfg = Configuration({"x": {"y": 1}, "z": 2})

    expected = {"x": {"y": 1}, "z": 2}

    assert cfg.to_dict() == expected


def test_basic_merge():
    cfg = Configuration({"a": 1, "b": {"c": 2}})
    cfg.merge({"b": {"d": 3}, "e": 4})
    assert cfg.b.c == 2
    assert cfg.b.d == 3
    assert cfg.e == 4


def test_load_config(tmp_path: Path):
    default_cfg_path = tmp_path / "default_config.py"
    user_cfg_path = tmp_path / "user_config.py"

    default_cfg_path.write_text(
        """
model = {"layers": 3, "units": 128}
training = {"epochs": 10, "batch_size": 32}
"""
    )

    user_cfg_path.write_text(
        """
model = {"units": 256}
training = {"batch_size": 64}
"""
    )

    config = load_config(str(default_cfg_path), str(user_cfg_path))

    assert config.model.layers == 3
    assert config.model.units == 256  # overridden
    assert config.training.batch_size == 64
    assert config.training.epochs == 10


def test_modify_after_load():
    cfg = Configuration({"a": 1})
    cfg.a = 5
    assert cfg.a == 5
    cfg["b"] = 10
    assert cfg.b == 10
