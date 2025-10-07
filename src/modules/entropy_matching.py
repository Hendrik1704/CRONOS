from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class EntropyMatching(BaseModule):
    """Entropy matching module for smooth KoMPoST to MUSIC transition.

    Implements entropy density matching to ensure smooth transition from
    KoMPoST pre-equilibrium evolution to MUSIC hydrodynamics. Converts
    the energy-momentum tensor from KoMPoST into proper entropy density
    and flow velocity fields for MUSIC initialization.

    Key physics features:
    - Energy-momentum tensor to entropy density conversion
    - Proper velocity field extraction
    - Equation of state consistency between modules
    - Effective degrees of freedom matching
    - Temperature and chemical potential initialization

    Module workflow:
    1. Links equation of state tables and conversion script
    2. Links KoMPoST output (energy-momentum tensor)
    3. Executes entropy matching conversion script
    4. Outputs MUSIC-compatible initial conditions
    5. Cleans up intermediate files

    The conversion ensures thermodynamic consistency and smooth evolution
    from pre-equilibrium to hydrodynamic phases without artificial
    discontinuities that could affect flow development.

    Example:
        >>> entropy = EntropyMatching(config.entropy_matching, full_config, project_root, event_id)
        >>> entropy.prepare_environment(event_dir)
        >>> entropy.prepare_input(event_dir)
        >>> entropy.run(event_dir)  # Entropy density matching
        >>> entropy.fetch_output(event_dir)  # MUSIC initial conditions
    """

    def prepare_environment(self, event_dir):
        """Set up entropy matching environment with EOS tables and conversion script.

        Prepares the entropy matching working environment by establishing symbolic
        links to required equation of state (EOS) tables and the KoMPoST-to-MUSIC
        conversion utility. This setup enables thermodynamically consistent
        matching between pre-equilibrium evolution and hydrodynamics.

        Environment Setup:
            - Links MUSIC EOS directory for thermodynamic consistency
            - Links KoMPoST_to_MUSIC.py conversion utility
            - Validates availability of required components
            - Creates entropy_matching/ working directory structure

        The EOS tables ensure that entropy density calculations use the same
        thermodynamic relations as MUSIC hydrodynamics, maintaining consistency
        across the pre-equilibrium to hydrodynamic transition.

        Args:
            event_dir (str): Event directory where entropy_matching/ subdirectory
                will be populated with EOS tables and conversion utilities

        Raises:
            SystemExit: If required KoMPoST_to_MUSIC.py script is not found,
                as this is critical for entropy matching functionality

        Side Effects:
            - Creates symbolic links to external EOS tables and utilities
            - Logs environment preparation progress and any missing components
            - May exit program if critical conversion script unavailable
        """
        logging.info(
            f"[EntropyMatching] Preparing environment in {event_dir}..."
        )
        entropy_eos_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "EOS"
        )
        if os.path.exists(entropy_eos_path):
            os.symlink(
                entropy_eos_path,
                os.path.join(event_dir, "entropy_matching", "EOS"),
            )
        else:
            logging.error(
                f"[EntropyMatching] Required directory {entropy_eos_path} does not exist."
            )

        entropy_matching_script_path = os.path.join(
            self.project_root, "utilities", "KoMPoST_to_MUSIC.py"
        )
        if os.path.exists(entropy_matching_script_path):
            os.symlink(
                entropy_matching_script_path,
                os.path.join(
                    event_dir, "entropy_matching", "KoMPoST_to_MUSIC.py"
                ),
            )
        else:
            logging.error(
                f"[EntropyMatching] Required executable {entropy_matching_script_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        """Establish symbolic links to KoMPoST pre-equilibrium evolution output.

        Creates symbolic link to KoMPoST output data in the entropy_matching
        working directory. This enables the entropy matching utility to access
        the pre-equilibrium energy-momentum tensor for thermodynamic matching
        with MUSIC hydrodynamics.

        Args:
            event_dir (str): Event directory containing entropy_matching/ subdirectory
                and KoMPoST output in results/ directory

        Side Effects:
            - Creates symbolic link to previous module output
            - Validates input file existence
            - Exits with error if required input missing
        """
        logging.info(f"[EntropyMatching] Create input file...")
        current_module_index = self.full_config.general.modules.index(
            "entropy_matching"
        )
        pre_eq_evolved_path = os.path.join(
            event_dir, "results", f"output_{current_module_index-1}.dat"
        )
        if os.path.exists(pre_eq_evolved_path):
            os.symlink(
                pre_eq_evolved_path,
                os.path.join(
                    event_dir,
                    "entropy_matching",
                    f"output_{current_module_index-1}.dat",
                ),
            )
        else:
            logging.error(
                f"[EntropyMatching] Required file {pre_eq_evolved_path} does not exist."
            )
            exit(1)

    @time_execution
    def run(self, event_dir):
        """Execute entropy matching between KoMPoST and MUSIC modules.

        Runs the KoMPoST_to_MUSIC.py utility to perform thermodynamically
        consistent matching between pre-equilibrium evolution and hydrodynamics.
        Uses entropy conservation principles to ensure proper energy-momentum
        tensor transition.

        Physics Process:
            Entropy matching maintains thermodynamic consistency by calculating
            the energy density that corresponds to the same entropy density
            as produced by KoMPoST, using the equation of state.

        Args:
            event_dir (str): Event directory with entropy_matching/ configuration

        Side Effects:
            - Executes KoMPoST_to_MUSIC.py conversion utility
            - Creates thermodynamically matched output file
            - Logs execution progress and performance
        """
        logging.info("[EntropyMatching] run...")
        # run with python script.py type_of_matching nu_eff <eos_file> <filename_in> <filename_out>
        s_matching_dir = os.path.join(event_dir, "entropy_matching")
        s_matching_script = "KoMPoST_to_MUSIC.py"
        current_module_index = self.full_config.general.modules.index(
            "entropy_matching"
        )
        logging.info("[EntropyMatching] Running Entropy Matching...")

        cwd = os.getcwd()
        try:
            os.chdir(s_matching_dir)
            run_external_command(
                [
                    "python3",
                    s_matching_script,
                    str(self.config.matching_type),
                    str(self.config.nu_eff),
                    "./EOS/hotQCD/hrg_hotqcd_eos_SMASH_binary.dat",
                    f"output_{current_module_index-1}.dat",
                    f"output_{current_module_index}.dat",
                ],
                check=True,
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="entropy_matching",
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[EntropyMatching] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[EntropyMatching] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect entropy-matched output and clean up working directory.

        Moves the thermodynamically matched energy-momentum tensor to the
        results directory and cleans up temporary entropy_matching files.

        Args:
            event_dir (str): Event directory with entropy_matching/ and results/

        Side Effects:
            - Moves matched output to standardized results location
            - Removes entropy_matching working directory
            - Logs successful entropy matching completion
        """
        logging.info("[EntropyMatching] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index(
            "entropy_matching"
        )
        src_file = os.path.join(
            event_dir, "entropy_matching", f"output_{current_module_index}.dat"
        )
        dest_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dest_file)
        shutil.rmtree(os.path.join(event_dir, "entropy_matching"))
        logging.info(f"[EntropyMatching] Output moved to {dest_file}")
