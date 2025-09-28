from abc import ABC, abstractmethod
import time
import logging
from functools import wraps


def time_execution(func):
    """Decorator to measure and log execution time of a method."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        result = func(self, *args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        module_name = self.__class__.__name__
        logging.info(f"[{module_name}] {func.__name__} completed in {execution_time:.3f} seconds")
        return result
    return wrapper


class BaseModule(ABC):
    """
    Abstract base class for all modules in the framework.
    Each module must implement the three lifecycle methods:
    - prepare_input()
    - run()
    - fetch_output()
    """

    def __init__(
        self, config, full_config=None, project_root=None, event_id=None
    ):
        self.config = config
        self.full_config = full_config
        self.project_root = project_root
        self.event_id = event_id

    @abstractmethod
    def prepare_environment(self, event_dir):
        """Prepare the execution environment for this module."""
        pass

    @abstractmethod
    def prepare_input(self, event_dir):
        """Prepare all necessary input files/data for this module."""
        pass

    @abstractmethod
    def run(self, event_dir):
        """Execute the module (Python code, C++ binary, etc.)."""
        pass

    @abstractmethod
    def fetch_output(self, event_dir):
        """Collect and store the results of the module."""
        pass
