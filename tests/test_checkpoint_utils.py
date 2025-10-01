import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch
from utilities.checkpoint_utils import (
    inspect_checkpoint,
    clear_checkpoint,
    main
)


class TestCheckpointUtils:
    """Test checkpoint utility functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.job_dir = os.path.join(self.temp_dir, "job_0")
        os.makedirs(self.job_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('utilities.checkpoint_utils.CheckpointManager')
    @patch('utilities.checkpoint_utils.os.path.exists')
    def test_inspect_checkpoint_no_file(self, mock_exists, mock_checkpoint_manager):
        """Test inspect_checkpoint when no checkpoint file exists."""
        mock_exists.return_value = False
        
        with patch('builtins.print') as mock_print:
            inspect_checkpoint(self.job_dir)
            mock_print.assert_called()
    
    @patch('utilities.checkpoint_utils.CheckpointManager')
    @patch('utilities.checkpoint_utils.os.path.exists')
    def test_inspect_checkpoint_with_file(self, mock_exists, mock_checkpoint_manager):
        """Test inspect_checkpoint when checkpoint file exists."""
        mock_exists.return_value = True
        
        # Mock checkpoint manager
        mock_manager = Mock()
        mock_manager.get_summary.return_value = "Test summary"
        mock_manager.checkpoint_data = {
            "events": {
                "event_0": {
                    "completed": True,
                    "failed": False,
                    "completed_modules": ["KoMPoST", "MUSIC"],
                    "current_module": None,
                    "error_message": None
                }
            }
        }
        mock_checkpoint_manager.return_value = mock_manager
        
        with patch('builtins.print') as mock_print:
            inspect_checkpoint(self.job_dir)
            mock_print.assert_called()
    
    @patch('utilities.checkpoint_utils.CheckpointManager')
    @patch('utilities.checkpoint_utils.os.path.exists')
    @patch('utilities.checkpoint_utils.os.remove')
    @patch('builtins.input')
    def test_clear_checkpoint_with_confirmation(self, mock_input, mock_remove, mock_exists, mock_checkpoint_manager):
        """Test clear_checkpoint with user confirmation."""
        mock_exists.return_value = True
        mock_input.return_value = 'y'
        
        mock_manager = Mock()
        mock_manager.checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        mock_checkpoint_manager.return_value = mock_manager
        
        with patch('builtins.print') as mock_print:
            clear_checkpoint(self.job_dir, force=False)
            mock_remove.assert_called_once()
            mock_print.assert_called()
    
    @patch('utilities.checkpoint_utils.CheckpointManager')
    @patch('utilities.checkpoint_utils.os.path.exists')
    def test_clear_checkpoint_no_file(self, mock_exists, mock_checkpoint_manager):
        """Test clear_checkpoint when no checkpoint file exists."""
        mock_exists.return_value = False
        
        with patch('builtins.print') as mock_print:
            clear_checkpoint(self.job_dir, force=True)
            mock_print.assert_called()
    
    @patch('utilities.checkpoint_utils.argparse.ArgumentParser')
    def test_main_no_command(self, mock_parser_class):
        """Test main function with no command."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.command = None
        mock_parser.parse_args.return_value = mock_args
        mock_parser_class.return_value = mock_parser
        
        main()
        mock_parser.print_help.assert_called_once()
    
    @patch('utilities.checkpoint_utils.argparse.ArgumentParser')
    @patch('utilities.checkpoint_utils.inspect_checkpoint')
    def test_main_inspect_command(self, mock_inspect, mock_parser_class):
        """Test main function with inspect command."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.command = 'inspect'
        mock_args.job_dir = 'test_job'
        mock_parser.parse_args.return_value = mock_args
        mock_parser_class.return_value = mock_parser
        
        main()
        mock_inspect.assert_called_once_with('test_job')
    
    @patch('utilities.checkpoint_utils.argparse.ArgumentParser')
    @patch('utilities.checkpoint_utils.clear_checkpoint')
    def test_main_clear_command(self, mock_clear, mock_parser_class):
        """Test main function with clear command."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.command = 'clear'
        mock_args.job_dir = 'test_job'
        mock_args.force = True
        mock_parser.parse_args.return_value = mock_args
        mock_parser_class.return_value = mock_parser
        
        main()
        mock_clear.assert_called_once_with('test_job', True)


if __name__ == "__main__":
    pytest.main([__file__])