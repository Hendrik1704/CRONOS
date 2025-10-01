import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from utilities.memory_monitor import monitor_memory, check_cronos_processes


class TestMemoryMonitor:
    """Test memory monitoring functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("utilities.memory_monitor.time.sleep")
    @patch("utilities.memory_monitor.psutil.virtual_memory")
    @patch("utilities.memory_monitor.psutil.process_iter")
    def test_monitor_memory_basic(
        self, mock_process_iter, mock_virtual_memory, mock_sleep
    ):
        """Test basic memory monitoring functionality."""
        # Mock memory data
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
        mock_virtual_memory.return_value = mock_memory

        # Mock processes
        mock_proc = Mock()
        mock_proc.info = {"pid": 1234, "name": "python", "memory_percent": 10.0}
        mock_process_iter.return_value = [mock_proc]

        # Mock sleep to exit after first iteration
        mock_sleep.side_effect = KeyboardInterrupt()

        # Should exit gracefully on KeyboardInterrupt
        with patch("builtins.print"):
            monitor_memory(interval=1, threshold=80, log_file=None)

        mock_sleep.assert_called_once_with(1)

    @patch("utilities.memory_monitor.psutil.process_iter")
    def test_check_cronos_processes(self, mock_process_iter):
        """Test checking CRONOS processes functionality."""
        # Mock processes with all required fields
        mock_proc1 = Mock()
        mock_proc1.info = {
            "name": "python",
            "pid": 1234,
            "ppid": 1000,
            "memory_percent": 5.0,
            "create_time": 1234567890,
            "cmdline": ["python", "cronos_simulation.py"],
            "memory_info": Mock(rss=100 * 1024 * 1024),  # 100MB
        }
        mock_proc2 = Mock()
        mock_proc2.info = {
            "name": "music.x",
            "pid": 5678,
            "ppid": 1234,
            "memory_percent": 15.0,
            "create_time": 1234567900,
            "cmdline": ["./music.x"],
            "memory_info": Mock(rss=300 * 1024 * 1024),  # 300MB
        }

        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        with patch("builtins.print"):
            result = check_cronos_processes()

        # Should complete without error
        assert result is None  # Function returns None

    @patch("utilities.memory_monitor.time.sleep")
    @patch("utilities.memory_monitor.psutil.virtual_memory")
    def test_monitor_memory_with_logging(self, mock_virtual_memory, mock_sleep):
        """Test memory monitoring with file logging."""
        # Mock memory data
        mock_memory = Mock()
        mock_memory.percent = 70.0
        mock_memory.available = 2 * 1024 * 1024 * 1024  # 2GB
        mock_virtual_memory.return_value = mock_memory

        # Mock sleep to exit after first iteration
        mock_sleep.side_effect = KeyboardInterrupt()

        log_file = os.path.join(self.temp_dir, "memory.log")

        with patch(
            "utilities.memory_monitor.psutil.process_iter"
        ) as mock_process_iter:
            mock_process_iter.return_value = []
            with patch("builtins.print"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_file = Mock()
                    mock_open.return_value.__enter__.return_value = mock_file

                    monitor_memory(interval=2, threshold=75, log_file=log_file)

                    # Should have attempted to open the log file
                    mock_open.assert_called()

    @patch("utilities.memory_monitor.psutil.process_iter")
    def test_check_cronos_processes_with_exceptions(self, mock_process_iter):
        """Test CRONOS process checking with process exceptions."""
        # Test with empty process list (simulates no CRONOS processes found)
        mock_process_iter.return_value = []

        # Should handle empty process list gracefully
        with patch("builtins.print"):
            result = check_cronos_processes()

        # Should complete without error even with no processes
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
