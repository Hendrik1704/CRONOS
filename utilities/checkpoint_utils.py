#!/usr/bin/env python3
"""CRONOS Checkpoint Management Utility.

This script provides comprehensive checkpoint inspection and management capabilities
for CRONOS heavy-ion collision simulations. It enables users to monitor simulation
progress, diagnose failures, and manage checkpoint states for production workflows.

Features:
- Inspect detailed checkpoint status for individual jobs
- Clear checkpoints to force simulation restart
- List all checkpoints across multiple job directories
- Colored terminal output for enhanced readability
- Integration with SLURM job arrays and cluster workflows

The checkpoint system enables fault-tolerant simulations by tracking progress
at both event and module levels, allowing automatic resumption after failures
in long-running heavy-ion collision calculations.

Usage Examples:
    # Inspect specific job checkpoint
    python checkpoint_utils.py inspect run/job_0/

    # List all checkpoints in run directory
    python checkpoint_utils.py list run/

    # Clear checkpoint to force restart
    python checkpoint_utils.py clear run/job_5/ --force

Commands:
    inspect: Display detailed checkpoint status and progress information
    clear: Remove checkpoint file to force simulation restart from beginning
    list: Show overview of all checkpoints in a run directory

Integration:
    This utility integrates with the CRONOS checkpoint system (CheckpointManager)
    and provides the diagnostic capabilities referenced in error messages from
    failed simulations. It's particularly useful for cluster job management
    and debugging simulation workflows.

Author: CRONOS Development Team
Requires: Python 3.8+, CRONOS checkpoint_manager and colors modules
"""

import argparse
import os
import sys
from pathlib import Path

# Add src directory to path for imports
# This works whether called from project root or utilities directory
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir.endswith("utilities"):
    # Called from utilities directory - go up one level
    project_root = os.path.dirname(script_dir)
else:
    # Called from project root
    project_root = script_dir

src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from checkpoint_manager import CheckpointManager
    from colors import Colors
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Make sure you're running from the CRONOS project root directory")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script directory: {script_dir}")
    print(f"Looking for src in: {src_path}")
    sys.exit(1)


def inspect_checkpoint(job_dir: str):
    """Inspect and display comprehensive checkpoint status for a CRONOS simulation job.

    Provides detailed analysis of simulation progress including event-level status,
    module completion tracking, failure analysis, and progress visualization with
    colored terminal output for production cluster environments.

    The function displays:
    - Overall job completion summary with progress statistics
    - Event-by-event status (COMPLETED/FAILED/IN PROGRESS)
    - Module-level progress within each event
    - Error messages and failure details for debugging
    - Color-coded output for quick visual assessment

    Args:
        job_dir (str): Absolute or relative path to job directory containing:
            - .cronos_checkpoint.json: Checkpoint state file
            - event_*/ subdirectories: Individual event workspaces
            - Module-specific output directories within each event

    Returns:
        None: Prints formatted checkpoint analysis to stdout

    Side Effects:
        - Reads checkpoint file using CheckpointManager
        - Prints colored terminal output using Colors utility
        - Does not modify checkpoint state or simulation files

    Example:
        >>> inspect_checkpoint('run/job_0/')
        === CRONOS Checkpoint Status ===
        Job Status: IN PROGRESS (2/5 events completed)

        Detailed Event Status:
          event_0: COMPLETED
            Completed modules: KoMPoST, MUSIC, iSS
          event_1: FAILED
            Error: Memory allocation failed in SMASH module

    Notes:
        If no checkpoint file exists, displays informative message rather
        than raising an error, making it safe to use in job monitoring scripts.
    """
    checkpoint_manager = CheckpointManager(job_dir)

    if not os.path.exists(checkpoint_manager.checkpoint_file):
        print(Colors.yellow(f"No checkpoint found for {job_dir}"))
        return

    print(Colors.green("=== CRONOS Checkpoint Status ===", bold=True))
    print(checkpoint_manager.get_summary())

    # Show detailed event status
    print(f"\n{Colors.cyan('Detailed Event Status:', bold=True)}")
    for event_id, status in checkpoint_manager.checkpoint_data[
        "events"
    ].items():
        if status["completed"]:
            status_color = Colors.green("COMPLETED")
        elif status["failed"]:
            status_color = Colors.red("FAILED")
        else:
            status_color = Colors.yellow("IN PROGRESS")

        print(f"  {event_id}: {status_color}")

        if status["completed_modules"]:
            completed_str = ", ".join(status["completed_modules"])
            print(f"    Completed modules: {Colors.green(completed_str)}")

        if status["current_module"]:
            print(
                f"    Current module: {Colors.yellow(status['current_module'])}"
            )

        if status["failed"] and status["error_message"]:
            print(f"    Error: {Colors.red(status['error_message'])}")


def clear_checkpoint(job_dir: str, force: bool = False):
    """Remove checkpoint file to force simulation restart from beginning.

    Safely removes the CRONOS checkpoint file, allowing simulations to restart
    from the beginning rather than resuming from the last successful module.
    This is useful for debugging, configuration changes, or recovering from
    corrupted intermediate states.

    Safety Features:
    - Interactive confirmation prompt (unless --force specified)
    - Graceful handling of missing checkpoint files
    - Colored terminal feedback for operation status
    - No modification of simulation output or configuration files

    Args:
        job_dir (str): Path to job directory containing checkpoint file:
            - Must contain .cronos_checkpoint.json to clear
            - Preserves all event directories and simulation output
            - Only removes checkpoint state tracking
        force (bool, optional): Skip confirmation prompt if True.
            Default False requires interactive user confirmation.

    Returns:
        None: Prints operation status to stdout

    Side Effects:
        - Removes .cronos_checkpoint.json file if present
        - Prompts for user confirmation unless force=True
        - Prints colored status messages to terminal
        - Leaves all simulation output and configuration intact

    Warning:
        Clearing checkpoints will cause the next simulation run to restart
        from the beginning, potentially overwriting existing output files
        if the simulation is resubmitted without proper cleanup.

    Example:
        >>> clear_checkpoint('run/job_0/', force=False)
        Are you sure you want to clear the checkpoint for run/job_0/? [y/N]: y
        Checkpoint cleared for run/job_0/

        >>> clear_checkpoint('run/job_1/', force=True)
        Checkpoint cleared for run/job_1/
    """
    checkpoint_manager = CheckpointManager(job_dir)

    if not os.path.exists(checkpoint_manager.checkpoint_file):
        print(Colors.yellow(f"No checkpoint found for {job_dir}"))
        return

    if not force:
        response = input(
            f"Are you sure you want to clear the checkpoint for {job_dir}? [y/N]: "
        )
        if response.lower() not in ["y", "yes"]:
            print("Checkpoint clearing cancelled.")
            return

    os.remove(checkpoint_manager.checkpoint_file)
    print(Colors.green(f"Checkpoint cleared for {job_dir}"))


def main():
    """Main entry point for CRONOS checkpoint management utility.

    Provides command-line interface for comprehensive checkpoint operations
    including inspection, clearing, and listing across multiple job directories.
    Integrates with SLURM job arrays and cluster workflow management.

    Command Structure:
        python checkpoint_utils.py <command> [options]

    Available Commands:
        inspect <job_dir>: Display detailed checkpoint status and progress
        clear <job_dir> [--force]: Remove checkpoint to force restart
        list [run_dir]: Show overview of all checkpoints in directory

    Integration:
        - Called automatically in error handling of run_simulations.py
        - Used by cluster job monitoring and resubmission scripts
        - Supports both interactive and automated workflow management
        - Compatible with CRONOS directory structure conventions

    Returns:
        None: Executes requested operation and exits

    Side Effects:
        - Parses command-line arguments using argparse
        - Calls appropriate checkpoint operation function
        - Handles import errors with informative diagnostics
        - Exits with appropriate status codes for scripting

    Example:
        $ python checkpoint_utils.py list run/
        === CRONOS Checkpoints ===
        job_0: COMPLETED (5/5 events)
        job_1: IN PROGRESS (2/5 events)
        job_2: IN PROGRESS (0/5 events)
    """
    parser = argparse.ArgumentParser(
        description="Inspect and manage CRONOS simulation checkpoints"
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # Inspect command
    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect checkpoint status"
    )
    inspect_parser.add_argument("job_dir", help="Path to job directory")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear checkpoint")
    clear_parser.add_argument("job_dir", help="Path to job directory")
    clear_parser.add_argument(
        "--force", action="store_true", help="Force clear without confirmation"
    )

    # List command
    list_parser = subparsers.add_parser(
        "list", help="List all checkpoints in run directory"
    )
    list_parser.add_argument(
        "run_dir",
        nargs="?",
        default="run",
        help="Path to run directory (default: run)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "inspect":
        inspect_checkpoint(args.job_dir)

    elif args.command == "clear":
        clear_checkpoint(args.job_dir, args.force)

    elif args.command == "list":
        """List all checkpoints in run directory with progress overview.

        Scans the specified run directory for job_* subdirectories containing
        checkpoint files and displays a concise overview of simulation progress
        across all jobs. Useful for monitoring large job arrays and identifying
        failed or stalled simulations.

        Output Format:
            job_name: STATUS (completed/total events)

        Color Coding:
            - Green: COMPLETED jobs (all events finished)
            - Yellow: IN PROGRESS jobs (partial completion)
            - Red: Error messages for missing directories
        """
        run_dir = Path(args.run_dir)
        if not run_dir.exists():
            print(Colors.red(f"Run directory {run_dir} does not exist"))
            return

        print(Colors.green("=== CRONOS Checkpoints ===", bold=True))
        found_checkpoints = False

        for job_dir in run_dir.iterdir():
            if job_dir.is_dir() and job_dir.name.startswith("job_"):
                checkpoint_file = job_dir / ".cronos_checkpoint.json"
                if checkpoint_file.exists():
                    found_checkpoints = True
                    checkpoint_manager = CheckpointManager(str(job_dir))
                    total_events = len(
                        checkpoint_manager.checkpoint_data["events"]
                    )
                    completed_events = len(
                        checkpoint_manager.checkpoint_data["completed_events"]
                    )
                    job_completed = checkpoint_manager.checkpoint_data[
                        "job_completed"
                    ]

                    status = (
                        Colors.green("COMPLETED")
                        if job_completed
                        else Colors.yellow("IN PROGRESS")
                    )
                    print(
                        f"{job_dir.name}: {status} ({completed_events}/{total_events} events)"
                    )

        if not found_checkpoints:
            print(Colors.yellow("No checkpoints found in run directory"))


if __name__ == "__main__":
    main()
