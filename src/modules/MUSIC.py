from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil
import glob


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
            SystemExit: If any required MUSIC components are missing.

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
            logging.error(
                f"[MUSIC] Required directory {music_eos_path} does not exist."
            )
            exit(1)

        music_tables_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "tables"
        )
        if os.path.exists(music_tables_path):
            os.symlink(
                music_tables_path, os.path.join(event_dir, "MUSIC", "tables")
            )
        else:
            logging.error(
                f"[MUSIC] Required directory {music_tables_path} does not exist."
            )
            exit(1)

        music_exe_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "MUSIChydro"
        )
        if os.path.exists(music_exe_path):
            os.symlink(
                music_exe_path, os.path.join(event_dir, "MUSIC", "MUSIChydro")
            )
        else:
            logging.error(
                f"[MUSIC] Required executable {music_exe_path} does not exist."
            )
            exit(1)

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
            SystemExit: If MUSIC directory doesn't exist or input linking fails.
        """
        logging.info(f"[MUSIC] Create input file...")
        current_module_index = self.full_config.general.modules.index("MUSIC")
        self.config.Initial_Distribution_input_filename = (
            f"output_{current_module_index-1}.dat"
        )

        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        if not os.path.exists(MUSIC_dir):
            logging.error(
                f"[MUSIC] Required directory {MUSIC_dir} does not exist."
            )
            exit(1)
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
            f.write(f"freeze_eps_flag {self.config.freeze_eps_flag}\n")
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

        Note:
            Execution time and peak memory usage are automatically logged
            due to @time_execution decorator.
        """
        logging.info("[MUSIC] run...")
        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        MUSIC_exe = "MUSIChydro"
        ini_file = "parameters_MUSIC.ini"

        logging.info("[MUSIC] Running MUSIC...")

        cwd = os.getcwd()
        try:
            os.chdir(MUSIC_dir)

            kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[MUSIC] Running with suppressed output...")
            run_external_command(
                [f"./{MUSIC_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="MUSIC",
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[MUSIC] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[MUSIC] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect MUSIC freeze-out surface and clean up temporary files.

        Locates the freeze-out hypersurface file produced by MUSIC, moves it to
        the standardized output location, and cleans up the temporary MUSIC
        directory. The freeze-out surface contains the space-time coordinates
        and thermodynamic quantities needed for Cooper-Frye particlization.

        The process:
        1. Searches for freeze-out surface files (surface_*.dat pattern)
        2. Handles multiple surface files by selecting the first match
        3. Moves surface to standardized output name for next module
        4. Removes temporary MUSIC directory and working files
        5. Logs completion and file locations

        Args:
            event_dir (str): Path to event-specific directory containing MUSIC
                output and results directory for standardized file placement.

        Raises:
            Logs errors if no surface files found but continues execution.

        Example:
            >>> music.fetch_output(event_dir)
            # Moves surface_0.dat to results/output_2.dat (if MUSIC is module 2)
            # Removes MUSIC/ directory and temporary files
        """
        logging.info("[MUSIC] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index("MUSIC")
        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        src_pattern = os.path.join(MUSIC_dir, "surface_*.dat")
        matching_files = sorted(glob.glob(src_pattern))

        if not matching_files:
            logging.error(f"[MUSIC] No files found matching {src_pattern}")
            return

        # If exactly one surface file exists, move it directly and return
        if len(matching_files) == 1:
            single_src = matching_files[0]
            results_dir = os.path.join(event_dir, "results")
            os.makedirs(results_dir, exist_ok=True)
            dst_file = os.path.join(
                results_dir, f"output_{current_module_index}.dat"
            )
            shutil.move(single_src, dst_file)
            try:
                shutil.rmtree(MUSIC_dir)
            except Exception:
                logging.warning(
                    f"[MUSIC] Failed to remove {MUSIC_dir} - leaving it for inspection"
                )
            logging.info(
                f"[MUSIC] Moved single surface {single_src} to {dst_file}"
            )
            return

        # Group files by the first three underscore-separated fields of the filename
        groups = {}
        for path in matching_files:
            name = os.path.basename(path)
            stem = os.path.splitext(name)[0]
            parts = stem.split("_")
            if len(parts) >= 3:
                key = "_".join(parts[:3])
            else:
                key = stem
            groups.setdefault(key, []).append(path)

        # Create group files by concatenating members of each group (streaming)
        group_files = []
        for key in sorted(groups.keys()):
            group_path = os.path.join(MUSIC_dir, f"{key}.dat")
            logging.info(
                f"[MUSIC] Creating group file {group_path} from {len(groups[key])} parts"
            )
            # Overwrite if exists
            with open(group_path, "wb") as out_f:
                for src in groups[key]:
                    # Skip if the source is the same as the intended group file
                    if os.path.abspath(src) == os.path.abspath(group_path):
                        continue
                    with open(src, "rb") as in_f:
                        shutil.copyfileobj(in_f, out_f)
            group_files.append(group_path)

        # Concatenate all group files into a single combined surface file
        combined_path = os.path.join(MUSIC_dir, "__combined_surface__.dat")
        with open(combined_path, "wb") as out_comb:
            for gf in sorted(group_files):
                with open(gf, "rb") as in_gf:
                    shutil.copyfileobj(in_gf, out_comb)

        # Ensure results directory exists
        results_dir = os.path.join(event_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        dst_file = os.path.join(
            results_dir, f"output_{current_module_index}.dat"
        )

        # Move the combined file to the standardized results filename
        shutil.move(combined_path, dst_file)

        # Clean up MUSIC working directory entirely
        try:
            shutil.rmtree(MUSIC_dir)
        except Exception:
            logging.warning(
                f"[MUSIC] Failed to remove {MUSIC_dir} - leaving it for inspection"
            )

        logging.info(f"[MUSIC] Moved combined surface(s) to {dst_file}")
