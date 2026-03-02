"""CRONOS Simulation Execution Script.

This script executes prepared CRONOS simulations with full checkpoint support,
allowing for robust simulation execution with automatic resumption after failures.
It runs the complete heavy-ion collision simulation chain through multiple physics
modules in sequence.

Features:
- Checkpoint-based resumption for fault tolerance
- Memory monitoring and error analysis
- Support for multiple events and physics modules
- Comprehensive error reporting and diagnostics
- Integration with SLURM job arrays for cluster execution

Physics Workflow:
1. Initial conditions (IPGlasma or from_file_IC)
2. Pre-equilibrium evolution (KoMPoST)
3. Hydrodynamic evolution (MUSIC)
4. Particlization (iSS Cooper-Frye)
5. Hadronic afterburner (SMASH)
6. Flow analysis (afterburner_toolkit)

Usage:
    python run_simulations.py [OPTIONS]
    
    # Basic execution of prepared simulation
    python run_simulations.py --job_dir run/job_0/
    
    # Force restart from beginning (ignore checkpoints)
    python run_simulations.py --job_dir run/job_0/ --force-restart
    
    # Custom configuration with specific job
    python run_simulations.py --main_config_path config/production.py \\
                              --job_dir run/job_5/

Checkpoint Features:
- Automatic checkpoint creation after each module completion
- Resume from last successful checkpoint on resubmission
- Detailed progress tracking and error analysis
- Memory usage monitoring for debugging

Error Handling:
- Memory-related error detection and suggestions
- Diagnostic information for failed modules
- Checkpoint inspection tools for debugging
- Partial simulation recovery capabilities

Output:
- HDF5 compressed result files
- Module-specific output in respective directories
- Comprehensive logging with colored terminal output
- Checkpoint status files for progress tracking

Author: CRONOS Development Team
Requires: Python 3.8+, psutil, h5py, NumPy
"""

import logging
import argparse
import os
from pathlib import Path
from src.configuration import load_config
from src.executor import run_modules
from src.check_settings import check_settings

from src.modules.from_file_IC import FromFileIC
from src.modules.IPGlasma import IPGlasma
from src.modules.KoMPoST import KoMPoST
from src.modules.entropy_matching import EntropyMatching
from src.modules.MUSIC import MUSIC
from src.modules.iSS import iSS
from src.modules.SMASH import SMASH
from src.modules.afterburner_toolkit import afterburner_toolkit

MODULE_REGISTRY = {
    "from_file_IC": FromFileIC,
    "IPGlasma": IPGlasma,
    "KoMPoST": KoMPoST,
    "entropy_matching": EntropyMatching,
    "MUSIC": MUSIC,
    "iSS": iSS,
    "SMASH": SMASH,
    "afterburner_toolkit": afterburner_toolkit,
}


def main():
    """Main function for CRONOS simulation execution.

    Executes a prepared CRONOS simulation job with comprehensive checkpoint
    support and error handling. The function manages the complete simulation
    workflow from initial conditions through hadronic afterburner.

    Features:
    - Checkpoint-based resumption for fault tolerance
    - Memory monitoring and analysis
    - Enhanced error reporting with diagnostic information
    - Support for force-restart to bypass checkpoints
    - Comprehensive logging with colored terminal output

    The execution process:
    1. Load configuration files and validate job directory
    2. Initialize checkpoint manager for progress tracking
    3. Resume from checkpoint or start fresh (based on --force-restart)
    4. Execute physics modules in sequence for each event
    5. Handle errors with memory analysis and suggestions
    6. Provide diagnostic information for failed simulations

    Exit Codes:
        0: Simulation completed successfully
        1: Configuration loading failure or simulation error

    Raises:
        SystemExit: On configuration errors or simulation failures
    """
    parser = argparse.ArgumentParser(
        description="Execute prepared CRONOS heavy-ion collision simulation",
        epilog="Example: python run_simulations.py --job_dir run/job_0/ --force-restart",
    )
    parser.add_argument(
        "--main_config_path",
        nargs="?",
        default="config/main_config.py",
        help="Path to the main configuration file",
    )
    parser.add_argument(
        "--user_config_path",
        nargs="?",
        default="config/user_config.py",
        help="Path to the user configuration file",
    )
    parser.add_argument(
        "--job_dir",
        nargs="?",
        default="run/job_0/",
        help="Path to the job directory that is supposed to be executed",
    )
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Force restart from beginning, ignoring existing checkpoints",
    )
    args = parser.parse_args()

    config = load_config(args.main_config_path, args.user_config_path)
    if not config:
        logging.error("Failed to load configuration.")
        exit(1)
    logging.basicConfig(level=config.general.log_level)
    valid_config = check_settings(config)
    if not valid_config:
        logging.error("Configuration settings are invalid.")
        exit(1)

    # Determine CRONOS project root based on this script location.
    project_root = Path(__file__).resolve().parent
    logging.info(f"Project root is: {project_root}")

    # Handle force restart by removing checkpoint file
    if args.force_restart:
        checkpoint_file = os.path.join(args.job_dir, ".cronos_checkpoint.json")
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logging.info(
                "Removed existing checkpoint file - starting from beginning"
            )

    try:
        run_modules(config, MODULE_REGISTRY, args.job_dir, project_root)
        logging.info("Simulation completed successfully!")
        exit(0)
    except Exception as e:
        logging.error(f"Simulation failed: {e}")

        # Provide helpful diagnostic information
        checkpoint_file = os.path.join(args.job_dir, ".cronos_checkpoint.json")
        if os.path.exists(checkpoint_file):
            logging.info("Checkpoint file exists - you can inspect it with:")
            logging.info(f"  python checkpoint_utils.py inspect {args.job_dir}")
            logging.info(
                "You can resubmit the job to resume from the last successful checkpoint"
            )
        else:
            logging.info(
                "No checkpoint file found - this appears to be an early failure"
            )

        # Check for output files to help diagnose the issue
        if os.path.exists(args.job_dir):
            output_files = []
            for root, dirs, files in os.walk(args.job_dir):
                for file in files:
                    if file.endswith((".h5", ".dat", ".txt", ".log")):
                        output_files.append(os.path.join(root, file))

            if output_files:
                logging.info(
                    f"Found {len(output_files)} output files - simulation may have partially succeeded"
                )
                logging.debug(
                    f"Output files: {output_files[:5]}..."
                )  # Show first 5 files

        exit(1)


if __name__ == "__main__":
    main()
