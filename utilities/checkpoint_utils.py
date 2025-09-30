#!/usr/bin/env python3
"""
Utility script to inspect and manage CRONOS simulation checkpoints.
"""

import argparse
import os
import sys
from pathlib import Path

# Add src directory to path for imports
# This works whether called from project root or utilities directory
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir.endswith('utilities'):
    # Called from utilities directory - go up one level
    project_root = os.path.dirname(script_dir)
else:
    # Called from project root
    project_root = script_dir

src_path = os.path.join(project_root, 'src')
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
    """Inspect and display checkpoint status for a job directory."""
    checkpoint_manager = CheckpointManager(job_dir)
    
    if not os.path.exists(checkpoint_manager.checkpoint_file):
        print(Colors.yellow(f"No checkpoint found for {job_dir}"))
        return
    
    print(Colors.green("=== CRONOS Checkpoint Status ===", bold=True))
    print(checkpoint_manager.get_summary())
    
    # Show detailed event status
    print(f"\n{Colors.cyan('Detailed Event Status:', bold=True)}")
    for event_id, status in checkpoint_manager.checkpoint_data["events"].items():
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
            print(f"    Current module: {Colors.yellow(status['current_module'])}")
        
        if status["failed"] and status["error_message"]:
            print(f"    Error: {Colors.red(status['error_message'])}")


def clear_checkpoint(job_dir: str, force: bool = False):
    """Clear checkpoint for a job directory."""
    checkpoint_manager = CheckpointManager(job_dir)
    
    if not os.path.exists(checkpoint_manager.checkpoint_file):
        print(Colors.yellow(f"No checkpoint found for {job_dir}"))
        return
    
    if not force:
        response = input(f"Are you sure you want to clear the checkpoint for {job_dir}? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Checkpoint clearing cancelled.")
            return
    
    os.remove(checkpoint_manager.checkpoint_file)
    print(Colors.green(f"Checkpoint cleared for {job_dir}"))


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and manage CRONOS simulation checkpoints"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect checkpoint status')
    inspect_parser.add_argument('job_dir', help='Path to job directory')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear checkpoint')
    clear_parser.add_argument('job_dir', help='Path to job directory')
    clear_parser.add_argument('--force', action='store_true', help='Force clear without confirmation')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all checkpoints in run directory')
    list_parser.add_argument('run_dir', nargs='?', default='run', help='Path to run directory (default: run)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'inspect':
        inspect_checkpoint(args.job_dir)
    
    elif args.command == 'clear':
        clear_checkpoint(args.job_dir, args.force)
    
    elif args.command == 'list':
        run_dir = Path(args.run_dir)
        if not run_dir.exists():
            print(Colors.red(f"Run directory {run_dir} does not exist"))
            return
        
        print(Colors.green("=== CRONOS Checkpoints ===", bold=True))
        found_checkpoints = False
        
        for job_dir in run_dir.iterdir():
            if job_dir.is_dir() and job_dir.name.startswith('job_'):
                checkpoint_file = job_dir / '.cronos_checkpoint.json'
                if checkpoint_file.exists():
                    found_checkpoints = True
                    checkpoint_manager = CheckpointManager(str(job_dir))
                    total_events = len(checkpoint_manager.checkpoint_data["events"])
                    completed_events = len(checkpoint_manager.checkpoint_data["completed_events"])
                    job_completed = checkpoint_manager.checkpoint_data["job_completed"]
                    
                    status = Colors.green("COMPLETED") if job_completed else Colors.yellow("IN PROGRESS")
                    print(f"{job_dir.name}: {status} ({completed_events}/{total_events} events)")
        
        if not found_checkpoints:
            print(Colors.yellow("No checkpoints found in run directory"))


if __name__ == "__main__":
    main()