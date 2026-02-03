"""
Checkpoint management for CRONOS simulation framework.
Enables resuming simulations from the last successful module.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple

try:
    from .colors import Colors  # Relative import when used as module
except ImportError:
    from colors import Colors  # Direct import when used standalone


class CheckpointManager:
    """Manages checkpoint creation and loading for robust simulation resumption.

    The CheckpointManager provides fault-tolerant execution by tracking simulation
    progress at the module level. It enables automatic resumption from the last
    successfully completed module in case of failures, crashes, or interruptions.

    Key features:
    - Atomic checkpoint updates to prevent corruption during crashes
    - Per-event progress tracking for job arrays
    - Module-level granularity for precise resumption
    - Comprehensive error logging and status reporting
    - Integration with SLURM job arrays for HPC environments

    The checkpoint file (.cronos_checkpoint.json) contains:
    - Last completed module for each event in the job
    - Event processing status (completed, failed, in-progress)
    - Job completion status and metadata
    - Error messages and failure context
    - Timestamps for progress tracking

    Attributes:
        job_dir (str): Absolute path to job directory
        checkpoint_file (str): Path to JSON checkpoint file
        checkpoint_data (dict): In-memory checkpoint state

    Example:
        >>> manager = CheckpointManager("run/job_0/")
        >>> manager.mark_module_started("event_0", "MUSIC")
        >>> # ... module execution ...
        >>> manager.mark_module_completed("event_0", "MUSIC")
        >>>
        >>> # On restart, automatically resumes from last completed module
        >>> next_module = manager.get_next_module("event_0", all_modules)
    """

    def __init__(self, job_dir: str):
        """Initialize checkpoint manager for a specific CRONOS job.

        Sets up checkpoint tracking for a job directory, loading existing
        checkpoint data if available or creating a new checkpoint structure.
        The job directory typically corresponds to a single SLURM job array task.

        Args:
            job_dir (str): Path to the job directory (e.g., "run/job_0/").
                Must be accessible for reading and writing checkpoint files.

        Example:
            >>> manager = CheckpointManager("/path/to/run/job_0/")
            >>> print(f"Managing checkpoints in {manager.job_dir}")
        """
        self.job_dir = os.path.abspath(job_dir)
        self.checkpoint_file = os.path.join(
            self.job_dir, ".cronos_checkpoint.json"
        )
        self.checkpoint_data = self._load_checkpoint()

    def _load_checkpoint(self) -> Dict:
        """Load existing checkpoint data from file or initialize new structure.

        Attempts to read and parse the JSON checkpoint file. If the file doesn't
        exist or is corrupted, creates a new checkpoint structure with default values.
        Handles JSON parsing errors gracefully to ensure robust startup.

        Returns:
            dict: Checkpoint data structure containing:
                - job_dir (str): Job directory path
                - events (dict): Per-event progress tracking
                - completed_events (list): List of fully completed event IDs
                - job_completed (bool): Overall job completion status
                - last_updated (float): Timestamp of last checkpoint update

        Example:
            >>> data = manager._load_checkpoint()
            >>> if data['job_completed']:
            ...     print("Job already completed")
        """
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    data = json.load(f)
                    logging.info(
                        f"Loaded checkpoint from {self.checkpoint_file}"
                    )
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(
                    f"Failed to load checkpoint: {e}. Starting fresh."
                )

        return {
            "job_dir": self.job_dir,
            "events": {},
            "completed_events": [],
            "job_completed": False,
            "last_updated": None,
        }

    def _save_checkpoint(self):
        """Save current checkpoint state to file with atomic write operations.

        Implements atomic file writing using a temporary file and rename operation
        to prevent checkpoint corruption if the process is killed during writing.
        Updates the last_updated timestamp before saving.

        The atomic write process:
        1. Write data to temporary file (.cronos_checkpoint.json.tmp)
        2. Atomically rename temp file to actual checkpoint file
        3. Ensures checkpoint is never in a partially written state

        Raises:
            IOError: If checkpoint file cannot be written (permissions, disk space).

        Example:
            >>> manager.checkpoint_data['job_completed'] = True
            >>> manager._save_checkpoint()  # Atomically updates checkpoint
        """
        import time

        self.checkpoint_data["last_updated"] = time.time()

        try:
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.checkpoint_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(self.checkpoint_data, f, indent=2)
            os.rename(temp_file, self.checkpoint_file)
            logging.debug(f"Checkpoint saved to {self.checkpoint_file}")
        except IOError as e:
            logging.error(f"Failed to save checkpoint: {e}")

    def get_event_status(self, event_id: str) -> Dict:
        """Retrieve comprehensive status information for a specific simulation event.

        Returns detailed progress tracking data for the specified event, including
        completed modules, current processing status, and any error information.
        If no checkpoint exists for the event, returns default status structure.

        Args:
            event_id (str): Event identifier (e.g., "event_0", "event_42").

        Returns:
            dict: Event status dictionary containing:
                - completed_modules (list): Names of successfully completed modules
                - current_module (str or None): Currently executing module name
                - completed (bool): Whether event processing is complete
                - failed (bool): Whether event processing has failed
                - error_message (str or None): Error details if failed

        Example:
            >>> status = manager.get_event_status("event_0")
            >>> print(f"Completed modules: {status['completed_modules']}")
            >>> if status['failed']:
            ...     print(f"Error: {status['error_message']}")
        """
        return self.checkpoint_data["events"].get(
            event_id,
            {
                "completed_modules": [],
                "current_module": None,
                "completed": False,
                "failed": False,
                "error_message": None,
            },
        )

    def mark_module_started(self, event_id: str, module_name: str):
        """Mark a module as started for progress tracking and resumption logic.

        Updates the checkpoint to indicate that a specific module has begun execution
        for an event. This is used for progress monitoring and to determine the
        resumption point if the simulation is interrupted.

        Args:
            event_id (str): Event identifier (e.g., "event_0").
            module_name (str): Name of the module being started (e.g., "MUSIC").

        Example:
            >>> manager.mark_module_started("event_0", "MUSIC")
            >>> # Module execution begins...

        Note:
            Should be called immediately before module execution begins.
            Paired with mark_module_completed() or mark_module_failed().
        """
        if event_id not in self.checkpoint_data["events"]:
            self.checkpoint_data["events"][event_id] = {
                "completed_modules": [],
                "current_module": None,
                "completed": False,
                "failed": False,
                "error_message": None,
            }

        self.checkpoint_data["events"][event_id]["current_module"] = module_name
        self._save_checkpoint()

        colored_msg = Colors.cyan(
            f"[CHECKPOINT] Starting module '{module_name}' for {event_id}"
        )
        logging.info(colored_msg)

    def mark_module_completed(self, event_id: str, module_name: str):
        """Mark a module as successfully completed for checkpoint tracking.

        Updates the checkpoint to record successful completion of a module,
        enabling precise resumption from the next module if simulation is interrupted.
        The module is added to the completed_modules list and current_module is cleared.

        Args:
            event_id (str): Event identifier (e.g., "event_0").
            module_name (str): Name of the successfully completed module (e.g., "MUSIC").

        Example:
            >>> manager.mark_module_completed("event_0", "MUSIC")
            >>> # Checkpoint now shows MUSIC as completed for event_0

        Note:
            Should be called immediately after successful module execution.
            Automatically saves checkpoint and logs success with color formatting.
        """
        event_status = self.get_event_status(event_id)

        if module_name not in event_status["completed_modules"]:
            event_status["completed_modules"].append(module_name)

        event_status["current_module"] = None
        self.checkpoint_data["events"][event_id] = event_status
        self._save_checkpoint()

        colored_msg = Colors.green(
            f"[CHECKPOINT] Completed module '{module_name}' for {event_id}"
        )
        logging.info(colored_msg)

    def mark_module_failed(
        self, event_id: str, module_name: str, error_message: str = None
    ):
        """Mark a module as failed with error details for debugging and resumption.

        Records module failure in the checkpoint, preserving error context for
        troubleshooting and enabling resumption from the failed module after fixes.
        The event is marked as failed but can be resumed from this module.

        Args:
            event_id (str): Event identifier (e.g., "event_0").
            module_name (str): Name of the failed module (e.g., "MUSIC").
            error_message (str, optional): Detailed error description for debugging.
                Defaults to None.

        Example:
            >>> try:
            ...     run_physics_module()
            ... except Exception as e:
            ...     manager.mark_module_failed("event_0", "MUSIC", str(e))

        Note:
            Logs failure with red color formatting and preserves error details
            in checkpoint for later inspection and resumption.
        """
        event_status = self.get_event_status(event_id)
        event_status["failed"] = True
        event_status["current_module"] = module_name
        event_status["error_message"] = error_message

        self.checkpoint_data["events"][event_id] = event_status
        self._save_checkpoint()

        colored_msg = Colors.red(
            f"[CHECKPOINT] Module '{module_name}' failed for {event_id}"
        )
        logging.error(colored_msg)
        if error_message:
            logging.error(f"Error: {error_message}")

    def mark_event_completed(self, event_id: str):
        """Mark an entire event as successfully completed with all modules finished.

        Finalizes event processing by marking it as complete and adding it to the
        completed events list. This indicates that all modules in the simulation
        chain have been successfully executed for this event.

        Args:
            event_id (str): Event identifier to mark as completed (e.g., "event_0").

        Example:
            >>> # After all modules complete successfully
            >>> manager.mark_event_completed("event_0")
            >>> assert manager.should_skip_event("event_0") == True

        Note:
            Clears current_module field and adds event to completed_events list.
            Used for job array progress tracking and final HDF5 output generation.
        """
        event_status = self.get_event_status(event_id)
        event_status["completed"] = True
        event_status["current_module"] = None

        self.checkpoint_data["events"][event_id] = event_status
        if event_id not in self.checkpoint_data["completed_events"]:
            self.checkpoint_data["completed_events"].append(event_id)

        self._save_checkpoint()

        colored_msg = Colors.green(
            f"[CHECKPOINT] Event {event_id} completed successfully", bold=True
        )
        logging.info(colored_msg)

    def mark_job_completed(self):
        """Mark the entire job as completed successfully with all events finished.

        Finalizes job processing by setting the job_completed flag, indicating
        that all events in this job have been successfully processed through
        all modules. Used for cleanup decisions and job array coordination.

        Example:
            >>> # After all events complete successfully
            >>> manager.mark_job_completed()
            >>> if config.cleanup_checkpoints:
            ...     manager.cleanup_checkpoint()

        Note:
            Logs completion with bold green formatting. Typically followed
            by checkpoint cleanup if configured to do so.
        """
        self.checkpoint_data["job_completed"] = True
        self._save_checkpoint()

        colored_msg = Colors.green(
            "[CHECKPOINT] Job completed successfully", bold=True
        )
        logging.info(colored_msg)

    def get_resume_point(
        self, event_id: str, all_modules: List[str]
    ) -> Tuple[int, Optional[str]]:
        """Determine optimal resumption point for event processing after interruption.

        Analyzes checkpoint data to identify where to resume processing for a specific
        event, handling various scenarios including completed events, failed modules,
        and partial progress. This enables efficient resumption without repeating
        successfully completed work.

        Resume logic:
        - Skip if event already completed
        - Resume from failed module if failure occurred
        - Resume from next module after last completed module
        - Start from beginning if no progress recorded

        Args:
            event_id (str): Event identifier to analyze (e.g., "event_0").
            all_modules (list of str): Complete ordered list of modules in simulation
                chain (e.g., ["from_file_IC", "MUSIC", "iSS", "SMASH"]).

        Returns:
            tuple: A tuple containing:
                - int: Module index to resume from (0-based, len(all_modules) if complete)
                - str: Human-readable explanation of resumption logic

        Example:
            >>> modules = ["from_file_IC", "MUSIC", "iSS", "SMASH"]
            >>> idx, reason = manager.get_resume_point("event_0", modules)
            >>> if idx < len(modules):
            ...     print(f"Resuming from {modules[idx]}: {reason}")
            ... else:
            ...     print(f"Event complete: {reason}")
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
                return (
                    resume_idx,
                    f"Resuming from failed module '{current_module}'",
                )

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

        last_module = (
            all_modules[last_completed_idx]
            if last_completed_idx >= 0
            else "none"
        )
        next_module = all_modules[resume_idx]
        return (
            resume_idx,
            f"Resuming {event_id} from '{next_module}' (after '{last_module}')",
        )

    def should_skip_event(self, event_id: str) -> bool:
        """Determine if an event should be skipped due to prior completion.

        Checks checkpoint data to see if the specified event has already been
        fully processed through all modules. Used to avoid redundant processing
        when resuming jobs or handling job arrays.

        Args:
            event_id (str): Event identifier to check (e.g., "event_0").

        Returns:
            bool: True if event is already completed and should be skipped,
                False if event needs processing.

        Example:
            >>> if not manager.should_skip_event("event_0"):
            ...     process_event("event_0")
            ... else:
            ...     print("Event already completed, skipping")
        """
        return self.get_event_status(event_id)["completed"]

    def get_summary(self) -> str:
        """Generate comprehensive human-readable checkpoint status summary.

        Creates a formatted multi-line string showing overall job progress,
        event completion statistics, and detailed status of any incomplete events.
        Used for progress reporting and debugging checkpoint issues.

        Returns:
            str: Multi-line formatted summary containing:
                - Job directory name and overall completion status
                - Total event count and completion statistics
                - Detailed status of incomplete events with module progress
                - Failure indicators for any failed events

        Example:
            >>> print(manager.get_summary())
            Checkpoint Summary for job_0:
              Total events: 10
              Completed events: 7
              Job completed: False
              event_8: 2 modules completed, current: MUSIC
              event_9: 0 modules completed, current: none
        """
        total_events = len(self.checkpoint_data["events"])
        completed_events = len(self.checkpoint_data["completed_events"])

        summary = [
            f"Checkpoint Summary for {os.path.basename(self.job_dir)}:",
            f"  Total events: {total_events}",
            f"  Completed events: {completed_events}",
            f"  Job completed: {self.checkpoint_data['job_completed']}",
        ]

        # Show status of incomplete events
        for event_id, status in self.checkpoint_data["events"].items():
            if not status["completed"]:
                completed_count = len(status["completed_modules"])
                current = status["current_module"] or "none"
                failed = " (FAILED)" if status["failed"] else ""
                summary.append(
                    f"  {event_id}: {completed_count} modules completed, current: {current}{failed}"
                )

        return "\n".join(summary)

    def cleanup_checkpoint(self):
        """Remove checkpoint file after successful job completion for cleanup.

        Deletes the checkpoint file when job processing is complete and cleanup
        is enabled in configuration. This prevents accumulation of checkpoint
        files from successful runs while preserving them for failed runs.

        Raises:
            IOError: If checkpoint file cannot be removed (permissions, etc.).
            Logged as warning but does not halt execution.

        Example:
            >>> if manager.checkpoint_data['job_completed']:
            ...     if config.cleanup_checkpoints:
            ...         manager.cleanup_checkpoint()

        Note:
            Should only be called after confirming job completion.
            Failure to remove file is logged but non-fatal.
        """
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
                logging.info(
                    "Checkpoint file cleaned up after successful completion"
                )
            except IOError as e:
                logging.warning(f"Failed to cleanup checkpoint file: {e}")
