import importlib.util
from pathlib import Path
from typing import Any, Dict


class Configuration:
    """Flexible nested configuration object with multiple access patterns and deep merging.

    Provides a unified interface for managing hierarchical configuration data with
    support for both attribute-style (config.general.modules) and dictionary-style
    (config['general']['modules']) access patterns. Enables deep merging of nested
    configurations for layered configuration management.

    Key features:
    - Attribute and dictionary-style access to nested data
    - Recursive nested Configuration objects for hierarchical access
    - Deep merging preserving nested structure
    - Conversion between Configuration objects and plain dictionaries
    - Support for CRONOS module-specific and general configuration sections

    Attributes:
        _data (dict): Internal storage of configuration parameters as nested structure.

    Example:
        >>> config_dict = {'general': {'log_level': 'INFO'}, 'MUSIC': {'tau_0': 0.5}}
        >>> config = Configuration(config_dict)
        >>>
        >>> # Attribute-style access
        >>> print(config.general.log_level)  # 'INFO'
        >>> print(config.MUSIC.tau_0)        # 0.5
        >>>
        >>> # Dictionary-style access
        >>> print(config['general']['log_level'])  # 'INFO'
        >>>
        >>> # Deep merging
        >>> overrides = {'general': {'log_level': 'DEBUG'}}
        >>> config.merge(overrides)
        >>> print(config.general.log_level)  # 'DEBUG'
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
        try:
            return self._data[name]
        except KeyError:
            # Attribute access should raise AttributeError when missing so that
            # builtin getattr(obj, name, default) can return the provided default
            # instead of causing an unexpected KeyError.
            raise AttributeError(f"Configuration has no attribute '{name}'")

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
    """Load Python configuration file and extract public variables as dictionary.

    Dynamically imports a Python file and extracts all public (non-underscore)
    variables as a configuration dictionary. This enables Python-based configuration
    files with full language support (comments, calculations, imports).

    The function uses importlib to safely load the Python file as a module and
    extracts only variables that don't start with underscore (convention for public API).

    Args:
        path (str): Path to Python configuration file (e.g., 'config/main_config.py').

    Returns:
        dict[str, Any]: Dictionary containing all public variables from the Python file.
            Keys are variable names, values are the variable values.

    Raises:
        FileNotFoundError: If the specified config file doesn't exist.
        ImportError: If the Python file has syntax errors or import issues.

    Example:
        >>> # config/test.py contains: general = {'log_level': 'INFO'}
        >>> config_data = _load_py_config('config/test.py')
        >>> assert config_data['general']['log_level'] == 'INFO'
    """
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
    """Load and merge multiple Python configuration files with override precedence.

    Loads multiple Python configuration files in sequence, performing deep merges
    where later files override earlier ones. This implements layered configuration
    management typical in CRONOS: main_config.py provides defaults, user_config.py
    provides simulation-specific overrides.

    The merge process preserves nested structure, so only specified keys in later
    configs override earlier values, leaving other nested keys intact.

    Args:
        *paths (str): Variable number of paths to Python configuration files.
            Files are processed in order, with later files taking precedence.
            At least one path must be provided.

    Returns:
        Configuration: Merged configuration object with all files combined.
            Later files override earlier ones at each level of nesting.

    Raises:
        ValueError: If no configuration file paths are provided.
        FileNotFoundError: If any specified config file doesn't exist.
        ImportError: If any Python config file has syntax or import errors.

    Example:
        >>> # Load main config with user overrides
        >>> config = load_config('config/main_config.py', 'config/user_config.py')
        >>>
        >>> # User config overrides take precedence
        >>> # main: general = {'log_level': 'INFO', 'debug': False}
        >>> # user: general = {'log_level': 'DEBUG'}
        >>> # result: general = {'log_level': 'DEBUG', 'debug': False}

    Note:
        This is the primary entry point for CRONOS configuration loading.
    """
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
