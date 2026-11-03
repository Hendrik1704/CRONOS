from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil
import glob

# MUSIC's stdout is written here when module_terminal_output is False. It must
# not end in .dat, because MUSIC removes *.dat from its working directory.
MUSIC_LOG_FILE = "MUSIC.log"
# Messages MUSIC prints when the hydro evolution ends normally (Evolve::EvolveIt
# in evolve.cpp). MUSIC also returns 0 after some failures (exit(0) calls in
# advance.cpp, or failed hydro re-runs in main.cpp), so the return code alone
# does not show that the evolution finished.
MUSIC_FINISHED_MESSAGE = "Finished."
MUSIC_MAX_TIME_MESSAGE = "Maximum allowed time reached."


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
        - Generates comprehensive MUSIC parameter file with all physics settings
        - Links initial conditions from previous module output
        - Copies parameter file to results directory for iSS module access

        The parameter file includes settings for:
        - Grid configuration (size, spacing, dimensions)
        - Evolution parameters (time step, duration, freeze-out criteria)
        - Physics options (viscosity, EOS, transport coefficients)
        - Output settings (evolution data, freeze-out surface format)

        Args:
            event_dir (str): Path to event-specific directory containing results
                from previous modules and MUSIC subdirectory.

        Raises:
            FileNotFoundError: If MUSIC directory doesn't exist or input linking fails.
        """
        logging.info(f"[MUSIC] Create input file...")
        current_module_index = self.full_config.general.modules.index("MUSIC")
        self.config.Initial_Distribution_input_filename = (
            f"output_{current_module_index-1}.dat"
        )

        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        if not os.path.exists(MUSIC_dir):
            raise FileNotFoundError(
                f"[MUSIC] Required directory {MUSIC_dir} does not exist."
            )
        ini_file = os.path.join(MUSIC_dir, "parameters_MUSIC.ini")

        with open(ini_file, "w") as f:
            f.write(f"echo_level {self.config.echo_level}\n")
            f.write(f"mode {self.config.mode}\n")
            f.write(f"beastMode {self.config.beastMode}\n")
            f.write(f"Initial_profile {self.config.Initial_profile}\n")
            f.write(
                f"initialize_with_entropy {self.config.initialize_with_entropy}\n"
            )
            f.write(
                f"Initial_Distribution_input_filename ../results/{self.config.Initial_Distribution_input_filename}\n"
            )
            f.write(f"s_factor {self.config.s_factor}\n")
            f.write(f"preEqVisFactor {self.config.preEqVisFactor}\n")
            f.write(f"boost_invariant {self.config.boost_invariant}\n")
            f.write(f"Initial_time_tau_0 {self.config.Initial_time_tau_0}\n")
            f.write(
                f"Total_evolution_time_tau {self.config.Total_evolution_time_tau}\n"
            )
            f.write(f"Delta_Tau {self.config.Delta_Tau}\n")
            f.write(f"Eta_grid_size {self.config.Eta_grid_size}\n")
            f.write(f"Grid_size_in_eta {self.config.Grid_size_in_eta}\n")
            f.write(f"X_grid_size_in_fm {self.config.X_grid_size_in_fm}\n")
            f.write(f"Y_grid_size_in_fm {self.config.Y_grid_size_in_fm}\n")
            f.write(f"Grid_size_in_x {self.config.Grid_size_in_x}\n")
            f.write(f"Grid_size_in_y {self.config.Grid_size_in_y}\n")
            f.write(f"gridPadding {self.config.gridPadding}\n")
            f.write(f"EOS_to_use {self.config.EOS_to_use}\n")
            f.write(
                f"quest_revert_strength {self.config.quest_revert_strength}\n"
            )
            f.write(
                f"FlagResumTransportCoeff {self.config.FlagResumTransportCoeff}\n"
            )
            f.write(f"FlagResetCausality {self.config.FlagResetCausality}\n")
            f.write(
                f"resumTransCoeffAlpha {self.config.resumTransCoeffAlpha}\n"
            )
            f.write(f"turn_on_bulk_chem {self.config.turn_on_bulk_chem}\n")
            f.write(f"chem_rate_C {self.config.chem_rate_C}\n")
            f.write(
                f"Viscosity_Flag_Yes_1_No_0 {self.config.Viscosity_Flag_Yes_1_No_0}\n"
            )
            f.write(
                f"Include_Shear_Visc_Yes_1_No_0 {self.config.Include_Shear_Visc_Yes_1_No_0}\n"
            )
            f.write(f"Shear_to_S_ratio {self.config.Shear_to_S_ratio}\n")
            f.write(
                f"T_dependent_Shear_to_S_ratio {self.config.T_dependent_Shear_to_S_ratio}\n"
            )
            f.write(
                f"shear_viscosity_3_eta_over_s_T_kink_in_GeV {self.config.shear_viscosity_3_eta_over_s_T_kink_in_GeV}\n"
            )
            f.write(
                f"shear_viscosity_3_eta_over_s_low_T_slope_in_GeV {self.config.shear_viscosity_3_eta_over_s_low_T_slope_in_GeV}\n"
            )
            f.write(
                f"shear_viscosity_3_eta_over_s_high_T_slope_in_GeV {self.config.shear_viscosity_3_eta_over_s_high_T_slope_in_GeV}\n"
            )
            f.write(
                f"shear_viscosity_3_eta_over_s_at_kink {self.config.shear_viscosity_3_eta_over_s_at_kink}\n"
            )
            f.write(
                f"Include_Bulk_Visc_Yes_1_No_0 {self.config.Include_Bulk_Visc_Yes_1_No_0}\n"
            )
            f.write(
                f"T_dependent_zeta_over_s {self.config.T_dependent_zeta_over_s}\n"
            )
            f.write(
                f"bulk_viscosity_10_max {self.config.bulk_viscosity_10_max}\n"
            )
            f.write(
                f"bulk_viscosity_10_width_high {self.config.bulk_viscosity_10_width_high}\n"
            )
            f.write(
                f"bulk_viscosity_10_width_low {self.config.bulk_viscosity_10_width_low}\n"
            )
            f.write(
                f"bulk_viscosity_10_T_peak {self.config.bulk_viscosity_10_T_peak}\n"
            )
            f.write(
                f"Include_second_order_terms {self.config.Include_second_order_terms}\n"
            )
            f.write(
                f"Include_vorticity_terms {self.config.Include_vorticity_terms}\n"
            )
            f.write(
                f"Include_Rhob_Yes_1_No_0 {self.config.Include_Rhob_Yes_1_No_0}\n"
            )
            f.write(
                f"turn_on_baryon_diffusion {self.config.turn_on_baryon_diffusion}\n"
            )
            f.write(f"kappa_coefficient {self.config.kappa_coefficient}\n")
            f.write(
                f"output_hydro_debug_info {self.config.output_hydro_debug_info}\n"
            )
            f.write(
                f"output_evolution_data {self.config.output_evolution_data}\n"
            )
            f.write(f"output_movie_flag {self.config.output_movie_flag}\n")
            f.write(
                f"output_evolution_T_cut {self.config.output_evolution_T_cut}\n"
            )
            f.write(
                f"output_evolution_e_cut {self.config.output_evolution_e_cut}\n"
            )
            f.write(
                f"output_evolution_ideal_only {self.config.output_evolution_ideal_only}\n"
            )
            f.write(
                f"outputBinaryEvolution {self.config.outputBinaryEvolution}\n"
            )
            f.write(
                f"output_evolution_every_N_eta {self.config.output_evolution_every_N_eta}\n"
            )
            f.write(
                f"output_evolution_every_N_y {self.config.output_evolution_every_N_y}\n"
            )
            f.write(
                f"output_evolution_every_N_x {self.config.output_evolution_every_N_x}\n"
            )
            f.write(
                f"output_evolution_every_N_timesteps {self.config.output_evolution_every_N_timesteps}\n"
            )
            f.write(
                f"Do_FreezeOut_Yes_1_No_0 {self.config.Do_FreezeOut_Yes_1_No_0}\n"
            )
            f.write(
                f"Do_FreezeOut_lowtemp {self.config.Do_FreezeOut_lowtemp}\n"
            )
            f.write(
                f"freeze_out_tau_start_max {self.config.freeze_out_tau_start_max}\n"
            )
            f.write(f"freeze_out_method {self.config.freeze_out_method}\n")
            f.write(
                f"freeze_surface_in_binary {self.config.freeze_surface_in_binary}\n"
            )
            f.write(
                f"average_surface_over_this_many_time_steps {self.config.average_surface_over_this_many_time_steps}\n"
            )
            f.write(f"freeze_Ncell_x_step {self.config.freeze_Ncell_x_step}\n")
            f.write(f"freeze_Ncell_y_step {self.config.freeze_Ncell_y_step}\n")
            f.write(
                f"freeze_Ncell_eta_step {self.config.freeze_Ncell_eta_step}\n"
            )
            f.write(f"freeze_eps_flag {self.config.freeze_eps_flag}\n")
            f.write(f"N_freeze_out {self.config.N_freeze_out}\n")
            f.write(
                f"use_eps_for_freeze_out {self.config.use_eps_for_freeze_out}\n"
            )
            f.write(f"T_freeze {self.config.T_freeze}\n")
            f.write(f"eps_switch {self.config.eps_switch}\n")
            f.write(f"eps_freeze_max {self.config.eps_freeze_max}\n")
            f.write(f"eps_freeze_min {self.config.eps_freeze_min}\n")
            f.write(f"EndOfData\n")

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

            kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
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
            logging.error(f"[MUSIC] Execution failed: {e}")
            raise
        finally:
            if log_file is not None:
                log_file.close()
            os.chdir(cwd)

        if log_path is None:
            logging.debug(
                "[MUSIC] Output went to the terminal, completion check skipped."
            )
        elif not music_evolution_finished(log_path):
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
            # Concatenate the per-thread parts into the results file
            with open(dst_file, "wb") as out_f:
                for src in matching_files:
                    with open(src, "rb") as in_f:
                        shutil.copyfileobj(in_f, out_f)

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
