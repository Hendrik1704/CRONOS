import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Dict


class Configuration:
    """
    A nested configuration object that supports both attribute and dict-style access,
    as well as deep merging of nested dictionaries.

    Attributes:
        _data (dict): Internal storage of configuration parameters.
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initializes the Configuration object.

        Args:
            config_dict (dict): Dictionary representing the configuration.
        """
        self._data = {}
        for k, v in config_dict.items():
            self._data[k] = Configuration(v) if isinstance(v, dict) else v

    def __getattr__(self, name):
        """
        Allows attribute-style access to configuration values.

        Args:
            name (str): The attribute name to access.

        Returns:
            Any: The value associated with the attribute.
        """
        return self._data[name]

    def __setattr__(self, name, value):
        """
        Allows setting configuration values via attributes.

        Args:
            name (str): The attribute name to set.
            value (Any): The value to assign.
        """
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __getitem__(self, key):
        """
        Allows dictionary-style access to configuration values.

        Args:
            key (str): The key to access.

        Returns:
            Any: The value associated with the key.
        """
        return self._data[key]

    def __setitem__(self, key, value):
        """
        Allows setting configuration values via dictionary-style access.

        Args:
            key (str): The key to set.
            value (Any): The value to assign.
        """
        self._data[key] = value

    def merge(self, override_dict: Dict[str, Any]):
        """
        Merges an override dictionary into the current configuration.

        Performs a deep merge, updating nested keys if they exist.

        Args:
            override_dict (dict): Dictionary containing overrides.
        """
        for k, v in override_dict.items():
            if (
                k in self._data
                and isinstance(self._data[k], Configuration)
                and isinstance(v, dict)
            ):
                self._data[k].merge(v)
            else:
                self._data[k] = Configuration(v) if isinstance(v, dict) else v

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the Configuration object back to a plain dictionary.

        Returns:
            dict: A nested dictionary representation of the configuration.
        """
        out = {}
        for k, v in self._data.items():
            out[k] = v.to_dict() if isinstance(v, Configuration) else v
        return out


def _load_py_config(path: str) -> Dict[str, Any]:
    """Load a .py file and return variables as a dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore

    # Only collect dicts, ignore built-ins
    config_vars = {
        k: v
        for k, v in vars(module).items()
        if not k.startswith("_")  # ignore private/builtins
    }
    return config_vars


def load_config(*paths: str) -> Configuration:
    """Load multiple .py config files and merge them (later overrides earlier)."""
    if not paths:
        raise ValueError("At least one config file must be provided.")

    # Start with the first config
    config_data = _load_py_config(paths[0])
    config = Configuration(config_data)

    # Merge any overrides
    for override_path in paths[1:]:
        override_data = _load_py_config(override_path)
        config.merge(override_data)

    return config
