import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from src.checkpoint_manager import CheckpointManager


class TestCheckpointManager:
    """Test CheckpointManager functionality."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.job_dir = os.path.join(self.temp_dir, "job_0")
        os.makedirs(self.job_dir, exist_ok=True)
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_checkpoint_manager_initialization(self):
        """Test CheckpointManager initialization."""
        manager = CheckpointManager(self.job_dir)
        
        assert manager.job_dir == self.job_dir
        expected_checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        assert manager.checkpoint_file == expected_checkpoint_file
        assert isinstance(manager.checkpoint_data, dict)
    
    def test_load_existing_checkpoint(self):
        """Test loading existing checkpoint file."""
        checkpoint_data = {
            "events": {
                "event_0": {
                    "status": "in_progress",
                    "last_completed_module": "KoMPoST",
                    "current_module": "MUSIC"
                }
            },
            "job_status": "running"
        }
        
        checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        
        manager = CheckpointManager(self.job_dir)
        
        assert manager.checkpoint_data == checkpoint_data
        assert manager.checkpoint_data["events"]["event_0"]["status"] == "in_progress"
    
    def test_load_corrupted_checkpoint(self):
        """Test handling corrupted checkpoint file."""
        checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        with open(checkpoint_file, 'w') as f:
            f.write("invalid json content")
        
        with patch('src.checkpoint_manager.logging.warning') as mock_logging:
            manager = CheckpointManager(self.job_dir)
            
            # Should initialize with default checkpoint structure
            expected_keys = {"job_dir", "events", "completed_events", "job_completed", "last_updated"}
            assert set(manager.checkpoint_data.keys()) == expected_keys
            assert manager.checkpoint_data["events"] == {}
            assert manager.checkpoint_data["job_completed"] is False
            mock_logging.assert_called()
    
    def test_save_checkpoint(self):
        """Test saving checkpoint data to file."""
        manager = CheckpointManager(self.job_dir)
        
        # Add some test data using the proper method
        manager.mark_module_completed("event_0", "MUSIC")
        manager.mark_event_completed("event_0")
        
        manager._save_checkpoint()
        
        # Verify file was saved correctly
        checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        assert os.path.exists(checkpoint_file)
        
        with open(checkpoint_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["events"]["event_0"]["completed"] is True
        assert "MUSIC" in loaded_data["events"]["event_0"]["completed_modules"]
    
    def test_mark_module_started(self):
        """Test marking a module as started."""
        manager = CheckpointManager(self.job_dir)
        
        manager.mark_module_started("event_0", "KoMPoST")
        
        event_data = manager.checkpoint_data["events"]["event_0"]
        assert event_data["current_module"] == "KoMPoST"
        assert event_data["completed"] is False
        assert event_data["failed"] is False
    
    def test_mark_module_completed(self):
        """Test marking a module as completed."""
        manager = CheckpointManager(self.job_dir)
        
        # First start the module
        manager.mark_module_started("event_0", "KoMPoST")
        
        # Then complete it
        manager.mark_module_completed("event_0", "KoMPoST")
        
        event_data = manager.checkpoint_data["events"]["event_0"]
        assert "KoMPoST" in event_data["completed_modules"]
        assert event_data["current_module"] is None
        assert event_data["completed"] is False  # Event not marked complete yet
        assert event_data["failed"] is False
    
    def test_mark_module_failed(self):
        """Test marking a module as failed."""
        manager = CheckpointManager(self.job_dir)
        
        error_message = "Module execution failed"
        manager.mark_module_failed("event_0", "MUSIC", error_message)
        
        event_data = manager.checkpoint_data["events"]["event_0"]
        assert event_data["failed"] is True
        assert event_data["error_message"] == error_message
        assert event_data["current_module"] == "MUSIC"
        assert event_data["completed"] is False
    
    def test_mark_event_completed(self):
        """Test marking entire event as completed."""
        manager = CheckpointManager(self.job_dir)
        
        manager.mark_event_completed("event_0")
        
        event_data = manager.checkpoint_data["events"]["event_0"]
        assert event_data["completed"] is True
        assert event_data["current_module"] is None
        assert "event_0" in manager.checkpoint_data["completed_events"]
    
    def test_get_resume_point_new_event(self):
        """Test getting resume point for new event."""
        manager = CheckpointManager(self.job_dir)
        modules = ["KoMPoST", "MUSIC", "iSS", "SMASH"]
        
        resume_idx, reason = manager.get_resume_point("event_0", modules)
        
        assert resume_idx == 0  # Start from first module
        assert "beginning" in reason.lower()
    
    def test_get_resume_point_partially_completed(self):
        """Test getting resume point for partially completed event."""
        manager = CheckpointManager(self.job_dir)
        modules = ["KoMPoST", "MUSIC", "iSS", "SMASH"]
        
        # Mark first module as completed
        manager.mark_module_completed("event_0", "KoMPoST")
        
        resume_idx, reason = manager.get_resume_point("event_0", modules)
        
        assert resume_idx == 1  # Resume from MUSIC (index 1)
        assert "MUSIC" in reason
    
    def test_get_resume_point_all_completed(self):
        """Test getting resume point when all modules completed."""
        manager = CheckpointManager(self.job_dir)
        modules = ["KoMPoST", "MUSIC"]
        
        # Mark event as completed
        manager.mark_event_completed("event_0")
        
        resume_idx, reason = manager.get_resume_point("event_0", modules)
        
        assert resume_idx == len(modules)  # Beyond last module
        assert "completed" in reason.lower()
    
    def test_get_resume_point_failed_event(self):
        """Test getting resume point for failed event."""
        manager = CheckpointManager(self.job_dir)
        modules = ["KoMPoST", "MUSIC", "iSS"]
        
        # Mark event as failed
        manager.mark_module_failed("event_0", "MUSIC", "Test failure")
        
        resume_idx, reason = manager.get_resume_point("event_0", modules)
        
        assert resume_idx == 1  # Resume from failed module MUSIC
        assert "failed" in reason.lower()
    
    def test_should_skip_event_not_completed(self):
        """Test should_skip_event for incomplete event."""
        manager = CheckpointManager(self.job_dir)
        
        # Complete some modules but not the entire event
        manager.mark_module_completed("event_0", "KoMPoST")
        manager.mark_module_completed("event_0", "MUSIC")
        
        should_skip = manager.should_skip_event("event_0")
        
        assert should_skip is False  # Event not fully complete
    
    def test_should_skip_event_completed(self):
        """Test should_skip_event for completed event."""
        manager = CheckpointManager(self.job_dir)
        
        # Mark entire event as completed
        manager.mark_event_completed("event_0")
        
        should_skip = manager.should_skip_event("event_0")
        
        assert should_skip is True  # Event is complete
    
    def test_get_event_status_new_event(self):
        """Test getting status for new event."""
        manager = CheckpointManager(self.job_dir)
        
        status = manager.get_event_status("event_0")
        
        assert status["completed"] is False
        assert status["failed"] is False
        assert status["current_module"] is None
        assert status["completed_modules"] == []
    
    def test_get_event_status_failed_event(self):
        """Test getting status for failed event."""
        manager = CheckpointManager(self.job_dir)
        
        # Mark as failed
        manager.mark_module_failed("event_0", "MUSIC", "Test error")
        
        status = manager.get_event_status("event_0")
        assert status["failed"] is True
        assert status["error_message"] == "Test error"
        assert status["current_module"] == "MUSIC"
    
    def test_get_event_status_progression(self):
        """Test event status during progression."""
        manager = CheckpointManager(self.job_dir)
        
        # New event
        status = manager.get_event_status("event_0")
        assert status["completed"] is False
        assert status["failed"] is False
        
        # Start a module
        manager.mark_module_started("event_0", "KoMPoST")
        status = manager.get_event_status("event_0")
        assert status["current_module"] == "KoMPoST"
        assert status["completed"] is False
        
        # Complete event
        manager.mark_event_completed("event_0")
        status = manager.get_event_status("event_0")
        assert status["completed"] is True
    
    def test_get_progress_summary(self):
        """Test getting progress summary."""
        manager = CheckpointManager(self.job_dir)
        
        # Add some events
        manager.mark_event_completed("event_0")
        manager.mark_module_failed("event_1", "MUSIC", "Test error")
        manager.mark_module_started("event_2", "KoMPoST")
        
        summary = manager.get_summary()
        
        assert isinstance(summary, str)
        assert "event_0" in summary or "completed" in summary
        assert len(summary) > 0
    
    def test_cleanup_checkpoint(self):
        """Test cleaning up checkpoint file."""
        manager = CheckpointManager(self.job_dir)
        
        # Save checkpoint first
        manager._save_checkpoint()
        checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        assert os.path.exists(checkpoint_file)
        
        # Clean up
        manager.cleanup_checkpoint()
        assert not os.path.exists(checkpoint_file)
    
    @patch('src.checkpoint_manager.logging.info')
    def test_logging_integration(self, mock_logging):
        """Test that checkpoint operations are properly logged."""
        manager = CheckpointManager(self.job_dir)
        
        manager.mark_module_started("event_0", "KoMPoST")
        manager.mark_module_completed("event_0", "KoMPoST")
        
        # Verify logging calls
        assert mock_logging.call_count >= 2
    
    def test_concurrent_access_safety(self):
        """Test thread safety with file locking."""
        manager = CheckpointManager(self.job_dir)
        
        # This test ensures basic functionality works
        # Real concurrent testing would require threading
        manager.mark_module_started("event_0", "KoMPoST")
        manager._save_checkpoint()
        
        # Verify state is consistent
        status = manager.get_event_status("event_0")
        assert status["current_module"] == "KoMPoST"


if __name__ == "__main__":
    pytest.main([__file__])