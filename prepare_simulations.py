"""CRONOS Simulation Preparation Script.

This script prepares the CRONOS simulation environment by creating the necessary
directory structure, initializing physics modules, and setting up job arrays for
heavy-ion collision simulations on local or cluster environments.

The preparation process includes:
- Creating job and event directories based on configuration
- Initializing physics modules (KoMPoST, MUSIC, iSS, SMASH, etc.)
- Setting up input files and initial conditions
- Generating cluster submission scripts for SLURM environments
- Configuring checkpoint and result directories

Usage:
    python prepare_simulations.py [OPTIONS]
    
    # Basic usage with default config
    python prepare_simulations.py
    
    # Custom configuration files
    python prepare_simulations.py --main_config_path config/custom_main.py \\
                                  --user_config_path config/custom_user.py
    
    # Prepare for cluster execution
    python prepare_simulations.py --cluster noctua2 --run_dir production_run/

Supported Clusters:
    - local: Local machine execution
    - noctua2: Paderborn University HPC cluster
    - wsu: Wayne State University HPC cluster
    
Example Directory Structure Created:
    run/
    ├── job_0/
    │   ├── event_0/
    │   │   ├── KoMPoST/
    │   │   ├── MUSIC/
    │   │   ├── iSS/
    │   │   ├── SMASH/
    │   │   └── results/
    │   └── event_1/
    └── job_1/
        └── ...

Author: CRONOS Development Team
Requires: Python 3.8+, NumPy, h5py
"""

import logging
import argparse
import shutil
from pathlib import Path
from src.configuration import load_config
from src.executor import prepare_modules
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

CLUSTER_OPTIONS = [
    "local",
    "noctua2",
    "wsu",
]


def main():
    """Main function for CRONOS simulation preparation.

    Parses command-line arguments, loads configuration files, validates cluster
    settings, and prepares the simulation environment with all necessary
    directories and module initialization.

    The function performs the following steps:
    1. Parse command-line arguments for configuration and run parameters
    2. Load and validate main and user configuration files
    3. Verify cluster environment compatibility
    4. Create job and event directory structure
    5. Initialize all physics modules with proper configuration
    6. Generate cluster submission scripts if needed
    7. Provide colored terminal feedback on preparation status

    Exit Codes:
        0: Successful preparation
        1: Configuration loading failure
        1: Unsupported cluster specified

    Raises:
        SystemExit: On configuration errors or invalid cluster selection
    """
    parser = argparse.ArgumentParser(
        description="Prepare CRONOS heavy-ion collision simulation environment",
        epilog="Example: python prepare_simulations.py --cluster noctua2 --run_dir production/",
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
        "--run_dir",
        nargs="?",
        default="run/",
        help="Path to the run directory",
    )
    parser.add_argument(
        "--cluster",
        nargs="?",
        default="local",
        help="Cluster name for environment setup (default: local)",
    )
    args = parser.parse_args()

    config = load_config(args.main_config_path, args.user_config_path)
    if not config:
        logging.error("Failed to load configuration.")
        exit(1)
    logging.basicConfig(level=config.general.log_level)

    if args.cluster not in CLUSTER_OPTIONS:
        logging.error(
            f"Cluster '{args.cluster}' is not supported. Supported clusters: {CLUSTER_OPTIONS}"
        )
        exit(1)
    valid_config = check_settings(config)
    if not valid_config:
        logging.error("Configuration settings are invalid.")
        exit(1)

    project_root = Path(__file__).resolve().parent
    logging.info(f"Project root is: {project_root}")

    prepare_modules(args, config, MODULE_REGISTRY, project_root)

    run_dir = Path(args.run_dir)
    user_config_src = Path(args.user_config_path).expanduser()
    if not user_config_src.is_absolute():
        user_config_src = Path.cwd() / user_config_src

    if user_config_src.exists():
        user_config_dst = run_dir / user_config_src.name
        try:
            shutil.copy2(user_config_src, user_config_dst)
            logging.info(
                "Copied user parameter file to run directory: %s", user_config_dst
            )
        except OSError:
            logging.exception(
                "Failed to copy user parameter file '%s' into '%s'",
                user_config_src,
                run_dir,
            )
    else:
        logging.warning(
            "User parameter file not found (not copied): %s", user_config_src
        )


if __name__ == "__main__":
    main()
