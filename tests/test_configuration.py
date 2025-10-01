import pytest
import tempfile
import os
import shutil
from pathlib import Path
from src import Configuration, load_config


class TestConfiguration:
    """Test Configuration class functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)

    def test_attribute_and_dict_access(self):
        """Test both attribute and dictionary-style access to configuration values."""
        cfg = Configuration({"hydro": {"tau0": 0.6, "eta_over_s": 0.08}})

        # Attribute access
        assert cfg.hydro.tau0 == 0.6
        assert cfg.hydro.eta_over_s == 0.08

        # Dict-style access
        assert cfg["hydro"]["tau0"] == 0.6
        assert cfg["hydro"]["eta_over_s"] == 0.08

    def test_set_attribute_and_dict(self):
        """Test setting configuration values using both attribute and dictionary styles."""
        cfg = Configuration({"a": 1})

        # Attribute style
        cfg.b = 2
        assert cfg.b == 2

        # Dict style
        cfg["c"] = 3
        assert cfg.c == 3
        assert cfg["c"] == 3

    def test_to_dict_conversion(self):
        """Test converting configuration back to dictionary format."""
        cfg = Configuration({"x": {"y": 1}, "z": 2})
        expected = {"x": {"y": 1}, "z": 2}

        assert cfg.to_dict() == expected

    def test_modify_after_load(self):
        """Test modifying configuration values after initial creation."""
        cfg = Configuration({"a": 1})

        cfg.a = 5
        assert cfg.a == 5

        cfg["b"] = 10
        assert cfg.b == 10


class TestConfigurationMerging:
    """Test configuration merging functionality."""

    def test_basic_merge(self):
        """Test basic configuration merging with simple structures."""
        cfg = Configuration({"a": 1, "b": {"c": 2}})
        cfg.merge({"b": {"d": 3}, "e": 4})

        assert cfg.b.c == 2  # Original value preserved
        assert cfg.b.d == 3  # New value added
        assert cfg.e == 4  # New top-level value added

    def test_nested_merge(self):
        """Test merging nested configuration structures with override behavior."""
        base = Configuration(
            {
                "hydro": {"tau0": 0.6, "eta_over_s": 0.08},
                "init": {"model": "TRENTO", "norm": 1.0},
            }
        )

        override = {"hydro": {"tau0": 0.2}, "init": {"norm": 1.5}}
        base.merge(override)

        assert base.hydro.tau0 == 0.2  # Value overridden
        assert base.hydro.eta_over_s == 0.08  # Original value preserved
        assert base.init.norm == 1.5  # Value overridden


class TestConfigurationLoading:
    """Test configuration file loading functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)

    def test_load_config_with_override(self):
        """Test loading configuration from default and user files with proper merging."""
        default_cfg_path = os.path.join(self.temp_dir, "default_config.py")
        user_cfg_path = os.path.join(self.temp_dir, "user_config.py")

        # Create default configuration file
        with open(default_cfg_path, "w") as f:
            f.write(
                """
model = {"layers": 3, "units": 128}
training = {"epochs": 10, "batch_size": 32}
"""
            )

        # Create user override configuration file
        with open(user_cfg_path, "w") as f:
            f.write(
                """
model = {"units": 256}
training = {"batch_size": 64}
"""
            )

        config = load_config(str(default_cfg_path), str(user_cfg_path))

        # Check that defaults are preserved where not overridden
        assert config.model.layers == 3
        assert config.training.epochs == 10

        # Check that user overrides are applied
        assert config.model.units == 256
        assert config.training.batch_size == 64


if __name__ == "__main__":
    pytest.main([__file__])
