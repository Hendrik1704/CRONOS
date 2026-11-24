from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil
import glob

# MUSIC's stdout is written here (and printed afterwards with
# module_terminal_output). It must
# not end in .dat, because MUSIC removes *.dat from its working directory.
MUSIC_LOG_FILE = "MUSIC.log"
# Messages MUSIC prints when the hydro evolution ends normally (Evolve::EvolveIt
# in evolve.cpp). MUSIC also returns 0 after some failures (exit(0) calls in
# advance.cpp, or failed hydro re-runs in main.cpp), so the return code alone
# does not show that the evolution finished.
MUSIC_FINISHED_MESSAGE = "Finished."
MUSIC_MAX_TIME_MESSAGE = "Maximum allowed time reached."


def format_music_value(value):
    """Format a configuration value for the MUSIC parameter file.

    MUSIC reads one token per parameter and converts it with stoi or stod, so
    booleans are written as 0 or 1.
    """
    if isinstance(value, bool):
        return str(int(value))
    return str(value)


def music_evolution_finished(log_path):
    """Return True if the MUSIC log shows that the evolution ended normally.

    Reaching Total_evolution_time_tau before all cells froze out counts as a
    failure, since the freeze-out surface is then not closed.
    """
    with open(log_path, errors="replace") as f:
        for line in f:
            line = line.rstrip()
            if line.endswith(f" {MUSIC_FINISHED_MESSAGE}"):
                return True
            if MUSIC_MAX_TIME_MESSAGE in line:
                # The freeze-out surface is not closed, which is a failure
                logging.error(
                    "[MUSIC] Total_evolution_time_tau was reached before all "
                    "cells froze out; the freeze-out surface is not closed."
                )
                return False
    return False


class MUSIC(BaseModule):
    """MUSIC relativistic hydrodynamics module for CRONOS simulation framework.

    Implements (3+1)D relativistic viscous hydrodynamics evolution using the MUSIC
    code. MUSIC evolves the energy-momentum tensor from initial conditions through
    hydrodynamic expansion until freeze-out, producing a hypersurface for subsequent
    particlization with iSS.

    Key physics features:
    - (3+1)D relativistic hydrodynamics with boost invariance option
    - Shear and bulk viscosity with temperature-dependent transport coefficients
    - Multiple equations of state (ideal gas, lattice QCD, hotQCD)
    - Freeze-out surface finding with temperature or energy density criteria
    - Initial conditions from various sources (MC-Glauber, IP-Glasma, KoMPoST)

    Module workflow:
    1. Links MUSIC executable, EOS tables, and transport coefficient tables
    2. Generates MUSIC parameter file from configuration
    3. Links initial conditions from previous module (e.g., KoMPoST output)
    4. Executes MUSIC hydrodynamics with memory monitoring
    5. Collects freeze-out surface and cleans up temporary files

    Configuration parameters include grid size, evolution time, viscosity ratios,
    EOS selection, and freeze-out criteria. See config/main_config.py for details.

    Example:
        >>> music = MUSIC(config.MUSIC, full_config, project_root, event_id)
        >>> music.prepare_environment(event_dir)
        >>> music.prepare_input(event_dir)
        >>> music.run(event_dir)  # Executes MUSIC hydrodynamics
        >>> music.fetch_output(event_dir)  # Collects freeze-out surface
    """

    def prepare_environment(self, event_dir):
        """Set up MUSIC execution environment with executable and data tables.

        Creates MUSIC directory structure and establishes symbolic links to:
        - MUSIC executable (MUSIChydro)
        - Equation of state tables (EOS directory)
        - Transport coefficient tables (tables directory)

        This ensures MUSIC has access to all required physics data and executable
        while maintaining clean separation between project structure and execution.

        Args:
            event_dir (str): Path to event-specific directory where MUSIC will execute.

        Raises:
            FileNotFoundError: If any required MUSIC components are missing.

        Example:
            >>> music.prepare_environment(\"/path/to/run/job_0/event_0/\")
            # Creates /path/to/run/job_0/event_0/MUSIC/ with proper links
        """
        logging.info(f"[MUSIC] Preparing environment in {event_dir}...")
        music_eos_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "EOS"
        )
        if os.path.exists(music_eos_path):
            os.symlink(music_eos_path, os.path.join(event_dir, "MUSIC", "EOS"))
        else:
            raise FileNotFoundError(
                f"[MUSIC] Required directory {music_eos_path} does not exist."
            )

        music_tables_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "tables"
        )
        if os.path.exists(music_tables_path):
            os.symlink(
                music_tables_path, os.path.join(event_dir, "MUSIC", "tables")
            )
        else:
            raise FileNotFoundError(
                f"[MUSIC] Required directory {music_tables_path} does not exist."
            )

        music_exe_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "MUSIChydro"
        )
        if os.path.exists(music_exe_path):
            os.symlink(
                music_exe_path, os.path.join(event_dir, "MUSIC", "MUSIChydro")
            )
        else:
            raise FileNotFoundError(
                f"[MUSIC] Required executable {music_exe_path} does not exist."
            )

    def prepare_input(self, event_dir):
        """Generate MUSIC parameter file and link initial conditions data.

        Creates the MUSIC parameter file (parameters_MUSIC.ini) containing all
        configuration parameters for hydrodynamic evolution. Links input data
        from previous module and copies parameter file to results for iSS usage.

        Key tasks:
        - Determines input filename from module execution order
        - Writes every key of the MUSIC configuration section to the
          parameter file (check_settings rejects keys MUSIC does not read)
        - Links initial conditions from previous module output
        - Copies parameter file to results directory for iSS module access

        Args:
            event_dir (str): Path to event-specific directory containing results
                from previous modules and MUSIC subdirectory.

        Raises:
            FileNotFoundError: If MUSIC directory doesn't exist or input linking fails.
        """
        logging.info(f"[MUSIC] Create input file...")
        current_module_index = self.full_config.general.modules.index("MUSIC")

        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        if not os.path.exists(MUSIC_dir):
            raise FileNotFoundError(
                f"[MUSIC] Required directory {MUSIC_dir} does not exist."
            )
        ini_file = os.path.join(MUSIC_dir, "parameters_MUSIC.ini")

        # Every MUSIC setting is passed on, check_settings has rejected the
        # keys MUSIC does not read
        parameters = self.config.to_dict()
        parameters["Initial_Distribution_input_filename"] = (
            f"../results/output_{current_module_index - 1}.dat"
        )
        with open(ini_file, "w") as f:
            for key, value in parameters.items():
                f.write(f"{key} {format_music_value(value)}\n")
            f.write("EndOfData\n")

        logging.info("[MUSIC] Input file created successfully.")

        # Copy the music input parameter file to the results directory, iSS needs it
        music_input_param_file = os.path.join(MUSIC_dir, "parameters_MUSIC.ini")
        music_input_param_file = os.path.abspath(music_input_param_file)
        results_path = os.path.join(event_dir, "results")
        shutil.copy(music_input_param_file, results_path)

    @time_execution
    def run(self, event_dir):
        """Execute MUSIC hydrodynamic evolution with memory monitoring.

        Runs the MUSIC hydrodynamics code using the prepared parameter file and
        initial conditions. Executes with comprehensive memory monitoring to track
        resource usage during the computationally intensive hydrodynamic evolution.

        The execution process:
        1. Changes to MUSIC working directory
        2. Configures output suppression based on settings
        3. Runs MUSIChydro executable with parameter file
        4. Monitors memory usage throughout evolution
        5. Handles execution errors and cleanup

        Memory monitoring tracks peak usage and generates warnings if the evolution
        exceeds configured thresholds, helping optimize grid parameters and system
        resource allocation for large-scale simulations.

        Args:
            event_dir (str): Path to event-specific directory containing MUSIC
                subdirectory with prepared parameter file and initial conditions.

        Raises:
            subprocess.CalledProcessError: If MUSIC execution fails.
            RuntimeError: If MUSIC exits without its completion message (only
                checked when the output goes to the MUSIC log file).

        Note:
            Execution time and peak memory usage are automatically logged
            due to @time_execution decorator.
        """
        logging.info("[MUSIC] run...")
        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        MUSIC_exe = "MUSIChydro"
        ini_file = "parameters_MUSIC.ini"

        logging.info("[MUSIC] Running MUSIC...")

        log_path = None
        log_file = None
        cwd = os.getcwd()
        try:
            os.chdir(MUSIC_dir)

            # MUSIC's output is always kept in a log file, since the
            # completion check needs it
            kwargs = {"check": True}
            log_path = os.path.join(os.getcwd(), MUSIC_LOG_FILE)
            log_file = open(log_path, "w")
            kwargs["stdout"] = log_file
            kwargs["stderr"] = subprocess.STDOUT
            logging.debug(f"[MUSIC] Writing MUSIC output to {log_path}")
            run_external_command(
                [f"./{MUSIC_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="MUSIC",
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[MUSIC] Execution failed: {e}, see {log_path}")
            raise
        finally:
            if log_file is not None:
                log_file.close()
            os.chdir(cwd)
            # Show the output also when MUSIC failed
            if self.full_config.general.module_terminal_output and log_path:
                with open(log_path, errors="replace") as f:
                    print(f.read(), end="")

        if not music_evolution_finished(log_path):
            raise RuntimeError(
                f"[MUSIC] MUSIC exited without finishing the hydro evolution, "
                f"see {log_path}"
            )

        logging.info("[MUSIC] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect MUSIC freeze-out surface and clean up temporary files.

        Locates the freeze-out hypersurface file produced by MUSIC, moves it to
        the standardized output location, and cleans up the temporary MUSIC
        directory. The freeze-out surface contains the space-time coordinates
        and thermodynamic quantities needed for Cooper-Frye particlization.

        The process:
        1. Searches for freeze-out surface files (surface_*.dat pattern)
        2. Checks that all files belong to one isotherm (iSS samples one)
        3. Moves the surface (or concatenates the per-thread parts of a
           (3+1)D surface) to the standardized output name for next module
        4. Removes temporary MUSIC directory and working files
        5. Logs completion and file locations

        Args:
            event_dir (str): Path to event-specific directory containing MUSIC
                output and results directory for standardized file placement.

        Raises:
            FileNotFoundError: If MUSIC did not write a freeze-out surface.
            RuntimeError: If surfaces for more than one isotherm exist.

        Example:
            >>> music.fetch_output(event_dir)
            # Moves surface_eps_0.18.dat to results/output_2.dat (if MUSIC is module 2)
            # Removes MUSIC/ directory and temporary files
        """
        logging.info("[MUSIC] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index("MUSIC")
        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        src_pattern = os.path.join(MUSIC_dir, "surface_*.dat")
        matching_files = sorted(glob.glob(src_pattern))

        if not matching_files:
            raise FileNotFoundError(
                f"[MUSIC] No freeze-out surface found matching {src_pattern}"
            )

        # MUSIC writes surface_eps_<e>.dat (boost-invariant) or one
        # surface_eps_<e>_<thread>.dat per OpenMP thread ((3+1)D) for each
        # isotherm <e>. iSS samples a single isotherm.
        isotherms = sorted(
            {
                "_".join(os.path.basename(path)[: -len(".dat")].split("_")[:3])
                for path in matching_files
            }
        )
        if len(isotherms) > 1:
            raise RuntimeError(
                f"[MUSIC] Found freeze-out surfaces for several isotherms "
                f"{isotherms}, but iSS needs exactly one (set N_freeze_out = 1)."
            )

        results_dir = os.path.join(event_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        dst_file = os.path.join(
            results_dir, f"output_{current_module_index}.dat"
        )

        if len(matching_files) == 1:
            shutil.move(matching_files[0], dst_file)
        else:
            # Concatenate the per-thread parts into the results file; write
            # a temporary file first, so that output_N.dat is only ever
            # complete (resume treats an existing output as finished)
            # (inside MUSIC_dir, so a failed attempt leaves nothing in
            # results/ and the file is removed with the directory)
            combined = os.path.join(MUSIC_dir, "surface_combined.tmp")
            with open(combined, "wb") as out_f:
                for src in matching_files:
                    with open(src, "rb") as in_f:
                        shutil.copyfileobj(in_f, out_f)
            os.replace(combined, dst_file)

        # Clean up MUSIC working directory entirely
        try:
            shutil.rmtree(MUSIC_dir)
        except Exception:
            logging.warning(
                f"[MUSIC] Failed to remove {MUSIC_dir} - leaving it for inspection"
            )

        logging.info(
            f"[MUSIC] Moved surface ({len(matching_files)} file(s)) to {dst_file}"
        )
