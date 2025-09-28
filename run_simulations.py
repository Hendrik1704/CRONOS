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
    args = parser.parse_args()

    config = load_config(args.main_config_path, args.user_config_path)
    if not config:
        logging.error("Failed to load configuration.")
        exit(1)
    logging.basicConfig(level=config.general.log_level)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    run_modules(config, MODULE_REGISTRY, args.job_dir, project_root)