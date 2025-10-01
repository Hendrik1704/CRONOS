import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from src.executor import analyze_error
from src.configuration import Configuration


class TestAnalyzeError:
    """Test error analysis functionality."""
    
    def test_analyze_memory_error(self):
        """Test analysis of memory-related errors."""
        memory_error = MemoryError("Unable to allocate memory")
        
        analysis = analyze_error(memory_error, "MUSIC")
        
        assert analysis['is_memory_related'] is True
        assert "memory" in analysis['enhanced_message'].lower()
        assert 'original_exception' in analysis
    
    def test_analyze_subprocess_error(self):
        """Test analysis of subprocess/external command errors."""
        import subprocess
        subprocess_error = subprocess.CalledProcessError(1, "kompost.x", "execution failed")
        
        analysis = analyze_error(subprocess_error, "KoMPoST")
        
        assert analysis['is_resource_related'] is False  # Based on actual implementation
        assert "kompost" in analysis['enhanced_message'].lower() or "command" in analysis['enhanced_message'].lower()
        assert 'original_exception' in analysis
    
    def test_analyze_file_not_found_error(self):
        """Test analysis of file system errors."""
        file_error = FileNotFoundError("Required executable not found")
        
        analysis = analyze_error(file_error, "SMASH")
        
        assert "executable" in analysis['enhanced_message'].lower() or "smash" in analysis['enhanced_message'].lower()
        assert analysis['is_resource_related'] is False  # Based on actual implementation
        assert 'original_exception' in analysis
    
    def test_analyze_generic_error(self):
        """Test analysis of generic errors."""
        generic_error = ValueError("Invalid parameter value")
        
        analysis = analyze_error(generic_error, "MUSIC")
        
        assert analysis['is_memory_related'] is False or analysis['is_memory_related'] is None
        assert "music" in analysis['enhanced_message'].lower()
        assert 'original_exception' in analysis
    
    @patch('src.executor.get_memory_info')
    def test_analyze_error_with_memory_info(self, mock_memory_info):
        """Test error analysis includes memory information when available."""
        mock_memory_info.return_value = {
            'process_rss_mb': 1500.0,
            'system_percent': 85.0
        }
        
        memory_error = MemoryError("Out of memory")
        analysis = analyze_error(memory_error, "MUSIC")
        
        assert analysis['is_memory_related'] is True
        mock_memory_info.assert_called_once()
    
    @patch('src.executor.get_memory_info')
    def test_analyze_error_memory_info_unavailable(self, mock_memory_info):
        """Test error analysis when memory info unavailable."""
        mock_memory_info.return_value = None
        
        error = Exception("Test error")
        analysis = analyze_error(error, "KoMPoST")
        
        assert 'enhanced_message' in analysis
        assert 'original_exception' in analysis
        assert analysis['memory_info'] is None


class TestExecutorIntegration:
    """Integration tests for executor functionality."""
    
    def test_error_analysis_integration(self):
        """Test error analysis with real exception types."""
        import subprocess
        
        # Test with various real exception types
        exceptions_to_test = [
            MemoryError("Memory allocation failed"),
            subprocess.CalledProcessError(1, "test_cmd"),
            FileNotFoundError("Executable not found"),
            PermissionError("Access denied"),
            RuntimeError("Runtime failure")
        ]
        
        for exception in exceptions_to_test:
            analysis = analyze_error(exception, "test_module")
            
            # All analyses should have required fields
            assert 'enhanced_message' in analysis
            assert 'is_memory_related' in analysis
            assert 'is_resource_related' in analysis
            assert 'original_exception' in analysis


if __name__ == "__main__":
    pytest.main([__file__])