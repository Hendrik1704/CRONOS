#!/usr/bin/env python3
"""Tests for the HDF5 Extractor utility."""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock h5py
h5py_mock = MagicMock()

with patch.dict("sys.modules", {"h5py": h5py_mock}):
    # Mock colors
    colors_mock = MagicMock()
    colors_mock.RESET = "\033[0m"
    colors_mock.RED = "\033[91m"
    colors_mock.GREEN = "\033[92m"
    colors_mock.YELLOW = "\033[93m"
    colors_mock.BLUE = "\033[94m"
    colors_mock.CYAN = "\033[96m"
    colors_mock.BOLD = "\033[1m"

    with patch.dict("sys.modules", {"src.colors": colors_mock}):
        from utilities.h5_extractor import HDF5Extractor, main


class TestHDF5Extractor:
    """Test cases for HDF5Extractor."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_h5_file = Path(self.temp_dir) / "test.h5"
        self.output_dir = Path(self.temp_dir) / "extracted"
        self.test_h5_file.touch()

    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_initialization_valid_file(self):
        """Test initialization with valid file."""
        extractor = HDF5Extractor(str(self.test_h5_file), str(self.output_dir))
        assert extractor.h5_file_path == self.test_h5_file
        assert self.output_dir.exists()

    def test_initialization_nonexistent_file(self):
        """Test initialization with nonexistent file."""
        nonexistent = Path(self.temp_dir) / "nonexistent.h5"
        with pytest.raises(FileNotFoundError):
            HDF5Extractor(str(nonexistent), str(self.output_dir))

    def test_display_empty_file(self, capsys):
        """Test display with empty file."""
        extractor = HDF5Extractor(str(self.test_h5_file), str(self.output_dir))
        extractor.datasets_info = []
        extractor.groups_info = []
        extractor.display_file_contents()
        captured = capsys.readouterr()
        assert "No datasets or groups found" in captured.out

    def test_get_user_selection_quit(self):
        """Test user selection quit."""
        extractor = HDF5Extractor(str(self.test_h5_file), str(self.output_dir))
        extractor.datasets_info = [{"name": "/test"}]
        with patch("builtins.input", return_value="quit"):
            result = extractor.get_user_selection()
            assert result == []

    def test_create_extraction_summary(self):
        """Test extraction summary."""
        extractor = HDF5Extractor(str(self.test_h5_file), str(self.output_dir))
        with patch("builtins.open", mock_open()) as mock_file:
            result = extractor.create_extraction_summary(["/test/file.dat"])
            assert result.endswith("extraction_summary.txt")
            mock_file.assert_called_once()


class TestMainFunction:
    """Test cases for main CLI function."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_h5_file = Path(self.temp_dir) / "test.h5"
        self.test_h5_file.touch()

    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_main_list_only(self, capsys):
        """Test main function list-only mode."""
        with patch(
            "sys.argv",
            ["h5_extractor.py", str(self.test_h5_file), "--list-only"],
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "File listing complete" in captured.out

    @patch("sys.argv", ["h5_extractor.py", "nonexistent.h5"])
    def test_main_file_not_found(self, capsys):
        """Test main with nonexistent file."""
        result = main()
        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out

    def test_main_no_datasets(self, capsys):
        """Test main function when no datasets are available."""
        with patch("sys.argv", ["h5_extractor.py", str(self.test_h5_file)]):
            result = main()

        # Should succeed even with no datasets
        assert result == 0
        captured = capsys.readouterr()
        assert "No datasets selected for extraction" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
