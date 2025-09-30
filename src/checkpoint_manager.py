"""
Checkpoint management for CRONOS simulation framework.
Enables resuming simulations from the last successful module.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from .colors import Colors  # Relative import when used as module
except ImportError:
    from colors import Colors   # Direct import when used standalone


class CheckpointManager:
    """
    Manages checkpoint creation and loading for simulation resumption.
    
    Checkpoints store:
    - Last completed module for each event
    - Event processing status
    - Job completion status
    """
    
    def __init__(self, job_dir: str):
        """
        Initialize checkpoint manager for a specific job.
        
        Args:
            job_dir: Path to the job directory
        """
        self.job_dir = os.path.abspath(job_dir)
        self.checkpoint_file = os.path.join(self.job_dir, ".cronos_checkpoint.json")
        self.checkpoint_data = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict:
        """Load existing checkpoint data or create new structure."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    logging.info(f"Loaded checkpoint from {self.checkpoint_file}")
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load checkpoint: {e}. Starting fresh.")
        
        return {
            "job_dir": self.job_dir,
            "events": {},
            "completed_events": [],
            "job_completed": False,
            "last_updated": None
        }
    
    def _save_checkpoint(self):
        """Save current checkpoint data to file."""
        import time
        self.checkpoint_data["last_updated"] = time.time()
        
        try:
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.checkpoint_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
            os.rename(temp_file, self.checkpoint_file)
            logging.debug(f"Checkpoint saved to {self.checkpoint_file}")
        except IOError as e:
            logging.error(f"Failed to save checkpoint: {e}")
    
    def get_event_status(self, event_id: str) -> Dict:
        """
        Get checkpoint status for a specific event.
        
        Args:
            event_id: Event identifier (e.g., "event_0")
            
        Returns:
            Dict with event status information
        """
        return self.checkpoint_data["events"].get(event_id, {
            "completed_modules": [],
            "current_module": None,
            "completed": False,
            "failed": False,
            "error_message": None
        })
    
    def mark_module_started(self, event_id: str, module_name: str):
        """
        Mark a module as started for an event.
        
        Args:
            event_id: Event identifier
            module_name: Name of the module being started
        """
        if event_id not in self.checkpoint_data["events"]:
            self.checkpoint_data["events"][event_id] = {
                "completed_modules": [],
                "current_module": None,
                "completed": False,
                "failed": False,
                "error_message": None
            }
        
        self.checkpoint_data["events"][event_id]["current_module"] = module_name
        self._save_checkpoint()
        
        colored_msg = Colors.cyan(f"[CHECKPOINT] Starting module '{module_name}' for {event_id}")
        logging.info(colored_msg)
    
    def mark_module_completed(self, event_id: str, module_name: str):
        """
        Mark a module as successfully completed for an event.
        
        Args:
            event_id: Event identifier
            module_name: Name of the completed module
        """
        event_status = self.get_event_status(event_id)
        
        if module_name not in event_status["completed_modules"]:
            event_status["completed_modules"].append(module_name)
        
        event_status["current_module"] = None
        self.checkpoint_data["events"][event_id] = event_status
        self._save_checkpoint()
        
        colored_msg = Colors.green(f"[CHECKPOINT] Completed module '{module_name}' for {event_id}")
        logging.info(colored_msg)
    
    def mark_module_failed(self, event_id: str, module_name: str, error_message: str = None):
        """
        Mark a module as failed for an event.
        
        Args:
            event_id: Event identifier
            module_name: Name of the failed module
            error_message: Optional error description
        """
        event_status = self.get_event_status(event_id)
        event_status["failed"] = True
        event_status["current_module"] = module_name
        event_status["error_message"] = error_message
        
        self.checkpoint_data["events"][event_id] = event_status
        self._save_checkpoint()
        
        colored_msg = Colors.red(f"[CHECKPOINT] Module '{module_name}' failed for {event_id}")
        logging.error(colored_msg)
        if error_message:
            logging.error(f"Error: {error_message}")
    
    def mark_event_completed(self, event_id: str):
        """
        Mark an entire event as completed.
        
        Args:
            event_id: Event identifier
        """
        event_status = self.get_event_status(event_id)
        event_status["completed"] = True
        event_status["current_module"] = None
        
        self.checkpoint_data["events"][event_id] = event_status
        if event_id not in self.checkpoint_data["completed_events"]:
            self.checkpoint_data["completed_events"].append(event_id)
        
        self._save_checkpoint()
        
        colored_msg = Colors.green(f"[CHECKPOINT] Event {event_id} completed successfully", bold=True)
        logging.info(colored_msg)
    
    def mark_job_completed(self):
        """Mark the entire job as completed."""
        self.checkpoint_data["job_completed"] = True
        self._save_checkpoint()
        
        colored_msg = Colors.green("[CHECKPOINT] Job completed successfully", bold=True)
        logging.info(colored_msg)
    
    def get_resume_point(self, event_id: str, all_modules: List[str]) -> Tuple[int, Optional[str]]:
        """
        Determine where to resume processing for an event.
        
        Args:
            event_id: Event identifier
            all_modules: List of all modules in execution order
            
        Returns:
            Tuple of (start_index, reason) where start_index is the module
            index to resume from, and reason explains the resume point
        """
        event_status = self.get_event_status(event_id)
        
        # If event is completed, skip it
        if event_status["completed"]:
            return len(all_modules), f"Event {event_id} already completed"
        
        # If event failed, resume from failed module
        if event_status["failed"]:
            current_module = event_status["current_module"]
            if current_module and current_module in all_modules:
                resume_idx = all_modules.index(current_module)
                return resume_idx, f"Resuming from failed module '{current_module}'"
        
        # Resume from next module after last completed
        completed_modules = event_status["completed_modules"]
        if not completed_modules:
            return 0, f"Starting {event_id} from beginning"
        
        # Find the last completed module
        last_completed_idx = -1
        for module in completed_modules:
            if module in all_modules:
                module_idx = all_modules.index(module)
                last_completed_idx = max(last_completed_idx, module_idx)
        
        resume_idx = last_completed_idx + 1
        if resume_idx >= len(all_modules):
            return len(all_modules), f"All modules completed for {event_id}"
        
        last_module = all_modules[last_completed_idx] if last_completed_idx >= 0 else "none"
        next_module = all_modules[resume_idx]
        return resume_idx, f"Resuming {event_id} from '{next_module}' (after '{last_module}')"
    
    def should_skip_event(self, event_id: str) -> bool:
        """Check if an event should be skipped (already completed)."""
        return self.get_event_status(event_id)["completed"]
    
    def get_summary(self) -> str:
        """Get a summary of the current checkpoint status."""
        total_events = len(self.checkpoint_data["events"])
        completed_events = len(self.checkpoint_data["completed_events"])
        
        summary = [
            f"Checkpoint Summary for {os.path.basename(self.job_dir)}:",
            f"  Total events: {total_events}",
            f"  Completed events: {completed_events}",
            f"  Job completed: {self.checkpoint_data['job_completed']}"
        ]
        
        # Show status of incomplete events
        for event_id, status in self.checkpoint_data["events"].items():
            if not status["completed"]:
                completed_count = len(status["completed_modules"])
                current = status["current_module"] or "none"
                failed = " (FAILED)" if status["failed"] else ""
                summary.append(f"  {event_id}: {completed_count} modules completed, current: {current}{failed}")
        
        return "\n".join(summary)
    
    def cleanup_checkpoint(self):
        """Remove checkpoint file after successful job completion."""
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
                logging.info("Checkpoint file cleaned up after successful completion")
            except IOError as e:
                logging.warning(f"Failed to cleanup checkpoint file: {e}")