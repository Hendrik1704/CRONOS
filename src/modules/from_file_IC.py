from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class FromFileIC(BaseModule):
    """Initial conditions module for loading external initial condition files.

    Loads pre-generated initial condition files from external sources such as
    Monte Carlo Glauber models, IP-Glasma calculations, McDipper simulations,
    or other event generators. Provides standardized interface for various
    initial condition formats in the CRONOS simulation chain with automatic
    format conversion capabilities.

    Key features:
    - Automatic .dat file detection and loading
    - McDipper to MUSIC format conversion integration
    - Boost-invariant and full 3D+1 mode support
    - Grid parameter configuration (Nx, Neta, dx, deta)
    - EOS integration for thermodynamic conversions
    - Memory-monitored subprocess execution
    - Comprehensive error handling and validation

    Module workflow:
    1. Sets up conversion environment (EOS symlinks, converter script)
    2. Validates input configuration and file availability
    3. Automatically detects .dat files in the working directory
    4. Converts McDipper format to MUSIC format using enhanced converter
    5. Applies grid parameters and equation of state data
    6. Moves converted output to standardized results location

    The module seamlessly integrates with the enhanced McDipper_to_MUSIC.py
    converter, providing enterprise-level initial condition processing with
    comprehensive error handling and memory monitoring.

    Example:
        >>> ic_module = FromFileIC(config.from_file_IC, full_config, project_root, event_id)
        >>> ic_module.prepare_environment(event_dir)  # Setup EOS and converter
        >>> ic_module.prepare_input(event_dir)        # Validate configuration
        >>> ic_module.run(event_dir)                  # Auto-detect and convert
        >>> ic_module.fetch_output(event_dir)         # Standardized output
    """

    def prepare_environment(self, event_dir):
        """Prepare environment for external initial conditions loading.

        Sets up the necessary environment for initial condition processing,
        including equation of state (EOS) data symlinks and the McDipper
        to MUSIC converter script. In boost-invariant mode, minimal setup
        is required since no conversion is performed.

        Environment Setup:
            - Creates symlinks to EOS data directory for thermodynamic tables
            - Links McDipper_to_MUSIC.py converter script to working directory
            - Validates required paths and reports missing dependencies

        Args:
            event_dir (str): Event directory for initial conditions processing

        Side Effects:
            - Creates symlinks in event_dir/from_file_IC/
            - Logs setup progress and any missing dependencies
            - Exits with error code 1 if critical dependencies missing
        """
        if self.config.boost_invariant == 1:
            logging.info(
                f"[FromFileIC] Boost invariant mode active. Nothing to prepare."
            )
        else:
            logging.info(
                f"[FromFileIC] Preparing environment in {event_dir}..."
            )
            eos_path = os.path.join(
                self.project_root, "external_codes", "MUSIC", "EOS"
            )
            if os.path.exists(eos_path):
                os.symlink(
                    eos_path,
                    os.path.join(event_dir, "from_file_IC", "EOS"),
                )
            else:
                logging.error(
                    f"[FromFileIC] Required directory {eos_path} does not exist."
                )

            matching_script_path = os.path.join(
                self.project_root, "utilities", "McDipper_to_MUSIC.py"
            )
            if os.path.exists(matching_script_path):
                os.symlink(
                    matching_script_path,
                    os.path.join(
                        event_dir, "from_file_IC", "McDipper_to_MUSIC.py"
                    ),
                )
            else:
                logging.error(
                    f"[FromFileIC] Required executable {matching_script_path} does not exist."
                )
                exit(1)

    def prepare_input(self, event_dir):
        """Log input configuration for external initial conditions.

        Reports the configured input path for initial condition files.
        Actual file detection and validation occurs during the run phase.

        Args:
            event_dir (str): Event directory containing from_file_IC/ subdirectory

        Side Effects:
            - Logs configured input path for tracking purposes
        """
        logging.info(f"[FromFileIC] Input file from {self.config.input_path}")

    @time_execution
    def run(self, event_dir):
        """Execute initial condition conversion with performance profiling.

                Automatically detects .dat files in the working directory and converts
                McDipper format initial conditions to MUSIC format using the enhanced
                converter with grid parameters and equation of state integration.
                In boost-invariant mode, skips conversion and logs completion.

                Conversion Process:
                    - Automatically detects first .dat file in working directory
                    - Assigns detected filename to config.input_filename
                    - Executes McDipper_to_MUSIC.py with grid and EOS parameters
                    - Monitors memory usage and subprocess execution
                    - Handles conversion errors with comprehensive logging

                Args:
                    event_dir (str): Event directory containing from_file_IC/ subdirectory

                Side Effects:
        +            - Profiles conversion time for performance monitoring
                    - Updates config.input_filename with detected file
                    - Creates converted_output.dat in working directory
                    - Logs conversion progress and completion status
                    - Exits with error if no .dat files found or conversion fails

                Raises:
                    SystemExit: If working directory missing or no .dat files found
                    subprocess.CalledProcessError: If McDipper conversion fails
        """
        if self.config.boost_invariant == 1:
            logging.info("[FromFileIC] No IC to run, profile saved...")
        else:
            from_file_ic_dir = os.path.join(event_dir, "from_file_IC")
            if not os.path.exists(from_file_ic_dir):
                logging.error(
                    f"[FromFileIC] Required directory {from_file_ic_dir} does not exist."
                )
                exit(1)
            convert_script = "McDipper_to_MUSIC.py"
            cwd = os.getcwd()
            try:
                os.chdir(from_file_ic_dir)
                # Find the .dat file in the directory
                dat_files = [f for f in os.listdir(".") if f.endswith(".dat")]
                if not dat_files:
                    logging.error(
                        f"[FromFileIC] No .dat files found in {from_file_ic_dir}."
                    )
                    exit(1)
                # There should be only one .dat file, take the first
                self.config.input_filename = dat_files[0]
                run_external_command(
                    [
                        "python3",
                        convert_script,
                        "./EOS/hotQCD/hrg_hotqcd_eos_SMASH_binary.dat",
                        f"{self.config.Nx}",
                        f"{self.config.Neta}",
                        f"{self.config.dx}",
                        f"{self.config.deta}",
                        self.config.input_filename,
                        "converted_output.dat",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                    module_name="FromFileIC-convert",
                )
                logging.info(f"[FromFileIC] Conversion completed successfully.")
            except subprocess.CalledProcessError as e:
                logging.error(f"[FromFileIC] Execution failed: {e}")
            finally:
                os.chdir(cwd)

    def fetch_output(self, event_dir):
        """Move external initial conditions to standardized output location.

        Transfers the loaded initial condition file to the results directory
        with standardized naming for use by subsequent physics modules.
        Cleans up the temporary from_file_IC directory after successful transfer.

        File Processing:
            - Locates initial condition file in from_file_IC/ directory
            - Moves to results/output_N.dat with proper module indexing
            - Removes temporary working directory after transfer

        Args:
            event_dir (str): Event directory containing from_file_IC/ and results/

        Side Effects:
            - Creates results/ directory if it doesn't exist
            - Moves initial condition file to standardized location
            - Removes from_file_IC/ working directory
            - Logs successful file transfer

        Raises:
            FileNotFoundError: If no initial condition files found in directory
            OSError: If file move operations fail

        Notes:
            The standardized output format enables seamless integration with
            downstream modules regardless of the original IC file format.
        """
        logging.info("[FromFileIC] Data loaded successfully.")

        results_dir = os.path.join(event_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        from_file_ic_dir = os.path.join(event_dir, "from_file_IC")
        entries = os.listdir(from_file_ic_dir)
        if not entries:
            raise FileNotFoundError(f"No files found in {from_file_ic_dir}")
        current_module_index = self.full_config.general.modules.index(
            "from_file_IC"
        )

        if self.config.boost_invariant == 1:
            src_file = os.path.join(from_file_ic_dir, entries[0])
            dst_file = os.path.join(
                results_dir, f"output_{current_module_index}.dat"
            )
        else:
            src_file = os.path.join(from_file_ic_dir, "converted_output.dat")
            dst_file = os.path.join(
                results_dir, f"output_{current_module_index}.dat"
            )

        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "from_file_IC"))

        logging.info(f"[FromFileIC] Moved {src_file} to {dst_file}")
