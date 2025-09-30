import logging
import argparse
import os
from src.configuration import load_config
from src.executor import run_modules

from src.modules.from_file_IC import FromFileIC
from src.modules.KoMPoST import KoMPoST
from src.modules.entropy_matching import EntropyMatching
from src.modules.MUSIC import MUSIC
from src.modules.iSS import iSS
from src.modules.SMASH import SMASH
from src.modules.afterburner_toolkit import afterburner_toolkit

MODULE_REGISTRY = {
    "from_file_IC": FromFileIC,
    "KoMPoST": KoMPoST,
    "entropy_matching": EntropyMatching,
    "MUSIC": MUSIC,
    "iSS": iSS,
    "SMASH": SMASH,
    "afterburner_toolkit": afterburner_toolkit,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the iEBE framework")
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

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Handle force restart by removing checkpoint file
    if args.force_restart:
        checkpoint_file = os.path.join(args.job_dir, ".cronos_checkpoint.json")
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logging.info("Removed existing checkpoint file - starting from beginning")

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
            logging.info("You can resubmit the job to resume from the last successful checkpoint")
        else:
            logging.info("No checkpoint file found - this appears to be an early failure")
        
        # Check for output files to help diagnose the issue
        if os.path.exists(args.job_dir):
            output_files = []
            for root, dirs, files in os.walk(args.job_dir):
                for file in files:
                    if file.endswith(('.h5', '.dat', '.txt', '.log')):
                        output_files.append(os.path.join(root, file))
            
            if output_files:
                logging.info(f"Found {len(output_files)} output files - simulation may have partially succeeded")
                logging.debug(f"Output files: {output_files[:5]}...")  # Show first 5 files
        
        exit(1)