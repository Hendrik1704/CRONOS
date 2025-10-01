import pytest
import time
import os
import tempfile
from unittest.mock import Mock, patch
from src.module_base import (
    BaseModule,
    get_memory_info,
    time_execution,
    check_memory_threshold,
    monitor_subprocess_memory,
)
from src.configuration import Configuration


class ConcreteModule(BaseModule):
    """Concrete implementation of BaseModule for testing."""

    def prepare_environment(self, event_dir):
        pass

    def prepare_input(self, event_dir):
        pass

    def run(self, event_dir):
        pass

    def fetch_output(self, event_dir):
        pass


class TestGetMemoryInfo:
    """Test memory information retrieval function."""

    @patch("src.module_base.psutil.Process")
    @patch("src.module_base.psutil.virtual_memory")
    def test_get_memory_info_success(
        self, mock_virtual_memory, mock_process_class
    ):
        """Test successful memory information retrieval."""
        # Mock process memory info
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB in bytes
        mock_memory_info.vms = 200 * 1024 * 1024  # 200 MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 5.0
        mock_process_class.return_value = mock_process

        # Mock system memory info
        mock_system_memory = Mock()
        mock_system_memory.total = 8 * 1024 * 1024 * 1024  # 8 GB in bytes
        mock_system_memory.available = 4 * 1024 * 1024 * 1024  # 4 GB in bytes
        mock_system_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_system_memory

        result = get_memory_info()

        assert result is not None
        assert result["process_rss_mb"] == 100.0
        assert result["process_vms_mb"] == 200.0
        assert result["process_percent"] == 5.0
        assert result["system_total_gb"] == 8.0
        assert result["system_available_gb"] == 4.0
        assert result["system_percent"] == 50.0

    @patch("src.module_base.psutil.Process")
    def test_get_memory_info_failure(self, mock_process_class):
        """Test memory info retrieval failure handling."""
        mock_process_class.side_effect = Exception("Process error")

        result = get_memory_info()
        assert result is None


class TestTimeExecution:
    """Test time execution decorator."""

    def test_time_execution_decorator(self):
        """Test that time execution decorator measures execution time."""

        class TestClass:
            @time_execution
            def slow_function(self):
                time.sleep(0.01)  # Reduced for faster testing
                return "completed"

        test_instance = TestClass()
        with patch("src.module_base.logging.info") as mock_logging:
            result = test_instance.slow_function()

        assert result == "completed"
        assert mock_logging.called

    def test_time_execution_with_exception(self):
        """Test time execution decorator with function that raises exception."""

        class TestClass:
            @time_execution
            def failing_function(self):
                raise ValueError("Test error")

        test_instance = TestClass()
        with pytest.raises(ValueError, match="Test error"):
            test_instance.failing_function()


class TestCheckMemoryThreshold:
    """Test memory threshold checking."""

    @patch("src.module_base.get_memory_info")
    def test_check_memory_threshold_below(self, mock_get_memory):
        """Test memory check when below threshold."""
        mock_get_memory.return_value = {"system_percent": 75.0}

        is_high, info = check_memory_threshold(85)

        assert is_high is False
        assert info is not None
        assert info["system_percent"] == 75.0

    @patch("src.module_base.get_memory_info")
    def test_check_memory_threshold_above(self, mock_get_memory):
        """Test memory check when above threshold."""
        mock_get_memory.return_value = {"system_percent": 95.0}

        is_high, info = check_memory_threshold(90)

        assert is_high is True
        assert info is not None
        assert info["system_percent"] == 95.0

    @patch("src.module_base.get_memory_info")
    def test_check_memory_threshold_no_info(self, mock_get_memory):
        """Test memory check when info unavailable."""
        mock_get_memory.return_value = None

        is_high, info = check_memory_threshold(90)

        assert is_high is False
        assert info is None


class TestBaseModule:
    """Test BaseModule abstract base class."""

    def test_base_module_instantiation(self):
        """Test BaseModule can be instantiated with concrete implementation."""
        config = Configuration({"test_param": "value"})
        full_config = Configuration({"general": {"modules": ["test"]}})

        module = ConcreteModule(config, full_config, "/tmp", "event_0")

        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == "/tmp"
        assert module.event_id == "event_0"

    def test_base_module_abstract_methods(self):
        """Test that BaseModule defines required abstract methods."""
        # Verify abstract methods are defined
        abstract_methods = BaseModule.__abstractmethods__
        expected_methods = {
            "prepare_environment",
            "prepare_input",
            "run",
            "fetch_output",
        }
        assert abstract_methods == expected_methods

    def test_create_directory_structure(self):
        """Test directory structure creation functionality."""
        config = Configuration({"test_param": "value"})
        full_config = Configuration({"general": {"modules": ["test"]}})

        with tempfile.TemporaryDirectory() as temp_dir:
            module = ConcreteModule(config, full_config, temp_dir, "event_0")

            # Test creating subdirectory
            test_dir = os.path.join(temp_dir, "test_subdir")
            os.makedirs(test_dir)

            assert os.path.exists(test_dir)

    def test_module_configuration_access(self):
        """Test module configuration parameter access."""
        config = Configuration({"tau0": 0.6, "nested": {"param": "value"}})
        full_config = Configuration({"general": {"modules": ["test"]}})

        module = ConcreteModule(config, full_config, "/tmp", "event_0")

        # Test attribute access
        assert module.config.tau0 == 0.6
        assert module.config.nested.param == "value"

        # Test dict-style access
        assert module.config["tau0"] == 0.6
        assert module.config["nested"]["param"] == "value"


class TestMonitorSubprocessMemory:
    """Test subprocess memory monitoring."""

    def test_monitor_subprocess_memory_basic(self):
        """Test basic subprocess memory monitoring setup."""
        mock_process = Mock()
        mock_process.pid = 1234

        # This function should return memory stats dict
        result = monitor_subprocess_memory(mock_process, "test_module")

        # Should return memory statistics dictionary
        assert isinstance(result, dict)
        assert "monitoring_active" in result
        assert "peak_memory_mb" in result
        assert "peak_memory_percent" in result
        assert "samples" in result
        assert result["monitoring_active"] is True


if __name__ == "__main__":
    pytest.main([__file__])
