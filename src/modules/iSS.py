from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class iSS(BaseModule):
    """Cooper-Frye particlization module for freeze-out surface sampling.

    Implements Cooper-Frye particlization using the iSS (integrated Sampler)
    code to convert the hydrodynamic freeze-out surface into hadron momentum
    distributions. Performs Monte Carlo sampling of particles from the
    freeze-out hypersurface with proper statistical distributions.

    Key physics features:
    - Cooper-Frye particlization with viscous corrections
    - Quantum statistics (Bose-Einstein and Fermi-Dirac)
    - Resonance decay handling and feed-down corrections
    - Multiple sampling modes (momentum, spatial, energy-momentum)
    - Support for bulk viscosity and baryon chemical potential
    - Polarization calculations for Lambda hyperons

    Module workflow:
    1. Links iSS executable and particle data tables
    2. Generates comprehensive parameter file with sampling settings
    3. Links freeze-out surface from MUSIC and MUSIC parameters
    4. Executes iSS Cooper-Frye sampling with memory monitoring
    5. Outputs particle momentum distributions (OSCAR or binary format)

    Configuration includes sampling parameters, particle selection,
    statistical settings, and output format options. The module interfaces
    with both MUSIC (freeze-out surface) and SMASH (particle output).

    Example:
        >>> iss = iSS(config.iSS, full_config, project_root, event_id)
        >>> iss.prepare_environment(event_dir)
        >>> iss.prepare_input(event_dir)
        >>> iss.run(event_dir)  # Cooper-Frye sampling
        >>> iss.fetch_output(event_dir)  # Particle distributions
    """

    def prepare_environment(self, event_dir):
        """Set up iSS execution environment with executable and particle tables.

        Creates iSS directory structure and establishes symbolic links to:
        - iSS executable (iSS.e)
        - Particle data tables (iSS_tables directory)

        The iSS_tables contain particle properties, decay channels, and
        statistical weights needed for proper Cooper-Frye particlization.

        Args:
            event_dir (str): Path to event-specific directory where iSS will execute.

        Raises:
            SystemExit: If iSS executable or particle tables are missing.
        """
        logging.info(f"[iSS] Preparing environment in {event_dir}...")

        iss_tables_path = os.path.join(
            self.project_root, "external_codes", "iSS", "iSS_tables"
        )
        if os.path.exists(iss_tables_path):
            os.symlink(
                iss_tables_path, os.path.join(event_dir, "iSS", "iSS_tables")
            )
        else:
            logging.error(
                f"[iSS] Required directory {iss_tables_path} does not exist."
            )
            exit(1)

        iss_exe_path = os.path.join(
            self.project_root, "external_codes", "iSS", "iSS.e"
        )
        if os.path.exists(iss_exe_path):
            os.symlink(iss_exe_path, os.path.join(event_dir, "iSS", "iSS.e"))
        else:
            logging.error(
                f"[iSS] Required executable {iss_exe_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        """Generate iSS configuration file and adapt settings for downstream modules.

        Creates the iSS parameter file (parameters_iSS.ini) with Cooper-Frye
        particlization settings and adapts output format based on whether SMASH
        hadronic afterburner will be used in the simulation chain.

        Configuration Adaptation:
            - If SMASH detected: Use OSCAR format for particle output
            - If no SMASH: Use binary format with built-in decay handling

        Physics Parameters:
            - Hydro mode: Specifies hydrodynamic input format
            - Afterburner type: Configures particle output for specific codes
            - Bulk viscosity: Controls non-equilibrium corrections
            - Chemical potentials: Enables baryon number conservation
            - Diffusion: Handles charge and strangeness diffusion

        Args:
            event_dir (str): Event directory containing iSS/ subdirectory
                and freeze-out surface from MUSIC hydrodynamics

        Side Effects:
            - Creates parameters_iSS.ini in iSS subdirectory
            - Links freeze-out surface from previous module output
            - Links MUSIC parameters for thermodynamic consistency
            - Adapts output format based on module chain configuration

        Notes:
            Cooper-Frye particlization converts the freeze-out hypersurface
            from hydrodynamics into individual hadrons for afterburner evolution.
        """
        logging.info(f"[iSS] Create input file...")
        current_module_index = self.full_config.general.modules.index("iSS")
        self.config.input_filename = f"output_{current_module_index-1}.dat"

        iSS_dir = os.path.join(event_dir, "iSS")
        if not os.path.exists(iSS_dir):
            logging.error(f"[iSS] Required directory {iSS_dir} does not exist.")
            exit(1)
        ini_file = os.path.join(iSS_dir, "parameters_iSS.ini")

        # If SMASH is not used, then use other defaults for some parameters
        if "SMASH" not in self.full_config.general.modules:
            self.config.use_OSCAR_format = 0
            self.config.use_binary_format = 1
            self.config.perform_decays = 1
            logging.info(
                "[iSS] SMASH module not detected. Setting use_OSCAR_format=0, use_binary_format=1, perform_decays=1."
            )

        with open(ini_file, "w") as f:
            f.write(f"hydro_mode = {self.config.hydro_mode}\n")
            f.write(f"afterburner_type = {self.config.afterburner_type}\n")
            f.write(f"turn_on_bulk = {self.config.turn_on_bulk}\n")
            f.write(f"turn_on_rhob = {self.config.turn_on_rhob}\n")
            f.write(f"turn_on_diff = {self.config.turn_on_diff}\n")
            f.write(f"regulateEOS = {self.config.regulateEOS}\n")
            f.write(
                f"include_deltaf_shear = {self.config.include_deltaf_shear}\n"
            )
            f.write(
                f"include_deltaf_bulk = {self.config.include_deltaf_bulk}\n"
            )
            f.write(
                f"include_deltaf_diffusion = {self.config.include_deltaf_diffusion}\n"
            )
            f.write(f"bulk_deltaf_kind = {self.config.bulk_deltaf_kind}\n")
            f.write(f"restrict_deltaf = {self.config.restrict_deltaf}\n")
            f.write(f"deltaf_max_ratio = {self.config.deltaf_max_ratio}\n")
            f.write(f"quantum_statistics = {self.config.quantum_statistics}\n")
            f.write(
                f"calculate_polarization = {self.config.calculate_polarization}\n"
            )
            f.write(
                f"polarizationRapType = {self.config.polarizationRapType}\n"
            )
            f.write(f"randomSeed = {self.config.randomSeed}\n")
            f.write(f"calculate_vn = {self.config.calculate_vn}\n")
            f.write(f"MC_sampling = {self.config.MC_sampling}\n")
            f.write(
                f"sample_upto_desired_particle_number = {self.config.sample_upto_desired_particle_number}\n"
            )
            f.write(
                f"number_of_repeated_sampling = {self.config.number_of_repeated_sampling}\n"
            )
            f.write(
                f"number_of_particles_needed = {self.config.number_of_particles_needed}\n"
            )
            f.write(
                f"maximum_sampling_events = {self.config.maximum_sampling_events}\n"
            )
            f.write(
                f"sample_y_minus_eta_s_range = {self.config.sample_y_minus_eta_s_range}\n"
            )
            f.write(f"sample_pT_up_to = {self.config.sample_pT_up_to}\n")
            f.write(
                f"dN_dy_sampling_model = {self.config.dN_dy_sampling_model}\n"
            )
            f.write(
                f"dN_dy_sampling_para1 = {self.config.dN_dy_sampling_para1}\n"
            )
            f.write(f"perform_decays = {self.config.perform_decays}\n")
            f.write(f"perform_checks = {self.config.perform_checks}\n")
            f.write(f"include_spectators = {self.config.include_spectators}\n")
            f.write(
                f"local_charge_conservation = {self.config.local_charge_conservation}\n"
            )
            f.write(
                f"global_momentum_conservation = {self.config.global_momentum_conservation}\n"
            )
            f.write(f"y_LB = {self.config.y_LB}\n")
            f.write(f"y_RB = {self.config.y_RB}\n")
            f.write(
                f"output_samples_into_files = {self.config.output_samples_into_files}\n"
            )
            f.write(
                f"store_samples_in_memory = {self.config.store_samples_in_memory}\n"
            )
            f.write(f"use_OSCAR_format = {self.config.use_OSCAR_format}\n")
            f.write(f"use_gzip_format = {self.config.use_gzip_format}\n")
            f.write(f"use_binary_format = {self.config.use_binary_format}\n")
            f.write(
                f"calculate_vn_to_order = {self.config.calculate_vn_to_order}\n"
            )
            f.write(f"use_pos_dN_only = {self.config.use_pos_dN_only}\n")
            f.write(f"grouping_particles = {self.config.grouping_particles}\n")
            f.write(f"grouping_tolerance = {self.config.grouping_tolerance}\n")
            f.write(
                f"minimum_emission_function_val = {self.config.minimum_emission_function_val}\n"
            )
            f.write(
                f"use_historic_flow_output_format = {self.config.use_historic_flow_output_format}\n"
            )
            f.write(f"eta_s_LB = {self.config.eta_s_LB}\n")
            f.write(f"eta_s_RB = {self.config.eta_s_RB}\n")
            f.write(
                f"use_dynamic_maximum = {self.config.use_dynamic_maximum}\n"
            )
            f.write(
                f"adjust_maximum_after = {self.config.adjust_maximum_after}\n"
            )
            f.write(f"adjust_maximum_to = {self.config.adjust_maximum_to}\n")
            f.write(f"calculate_dN_dtau = {self.config.calculate_dN_dtau}\n")
            f.write(f"bin_tau0 = {self.config.bin_tau0}\n")
            f.write(f"bin_dtau = {self.config.bin_dtau}\n")
            f.write(f"bin_tau_max = {self.config.bin_tau_max}\n")
            f.write(f"calculate_dN_dx = {self.config.calculate_dN_dx}\n")
            f.write(f"bin_x_min = {self.config.bin_x_min}\n")
            f.write(f"bin_dx = {self.config.bin_dx}\n")
            f.write(f"bin_x_max = {self.config.bin_x_max}\n")
            f.write(f"calculate_dN_dphi = {self.config.calculate_dN_dphi}\n")
            f.write(f"calculate_dN_deta = {self.config.calculate_dN_deta}\n")
            f.write(f"calculate_dN_dxt = {self.config.calculate_dN_dxt}\n")
            f.write(
                f"output_dN_dxtdy_4all = {self.config.output_dN_dxtdy_4all}\n"
            )

        logging.info("[iSS] Input file created successfully.")

        # Create a results directory in the iSS directory and move the surface there
        results_dir = os.path.join(event_dir, "iSS", "results")
        os.makedirs(results_dir, exist_ok=True)

        input_surface_file = os.path.join(
            event_dir, "results", self.config.input_filename
        )
        input_surface_file = os.path.abspath(
            input_surface_file
        )  # resolve relative path
        symlink_path = os.path.join(results_dir, "surface.dat")

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(input_surface_file, symlink_path)
        logging.debug(
            f"Created symlink: {symlink_path} -> {input_surface_file}"
        )

        # Create a symlink to parameters_MUSIC.ini in results
        music_param_file = os.path.join(
            event_dir, "results", "parameters_MUSIC.ini"
        )
        music_param_file = os.path.abspath(
            music_param_file
        )  # resolve relative path
        symlink_path = os.path.join(results_dir, "music_input")

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(music_param_file, symlink_path)
        logging.debug(f"Created symlink: {symlink_path} -> {music_param_file}")

    @time_execution
    def run(self, event_dir):
        """Execute iSS Cooper-Frye particlization of hydrodynamic freeze-out surface.

        Runs the iSS particlization code to convert the freeze-out hypersurface
        from MUSIC hydrodynamics into individual hadron samples using the
        Cooper-Frye prescription. This bridges hydrodynamics and hadronic physics.

        Physics Process:
            The Cooper-Frye formula converts continuous hydrodynamic fields on
            the freeze-out surface into discrete particle four-momenta and positions,
            accounting for thermal and chemical equilibrium distributions.

        Computational Features:
            - Monte Carlo sampling of particle distributions
            - Resonance decay handling (if enabled)
            - Memory-efficient processing of large freeze-out surfaces
            - Format adaptation for different afterburner codes

        Args:
            event_dir (str): Event directory containing configured iSS/ subdirectory
                with freeze-out surface and parameter files

        Side Effects:
            - Temporarily changes working directory to iSS/
            - Executes external iSS binary with subprocess monitoring
            - Creates particle output in OSCAR or binary format
            - Logs execution progress and performance metrics

        Raises:
            subprocess.CalledProcessError: If iSS execution fails
            OSError: If iSS directory or executable not accessible

        Output:
            Produces particle list files ready for hadronic afterburner (SMASH)
            or direct analysis, depending on configuration.
        """
        logging.info("[iSS] run...")

        iSS_dir = os.path.join(event_dir, "iSS")
        iSS_exe = "iSS.e"
        ini_file = "parameters_iSS.ini"

        logging.info("[iSS] Running iSS...")

        cwd = os.getcwd()
        try:
            os.chdir(iSS_dir)
            kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[iSS] Running with suppressed output...")
            run_external_command(
                [f"./{iSS_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="iSS",
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[iSS] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[iSS] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect iSS particle output and clean up temporary files.

        Moves the Cooper-Frye particlization output to the standardized results
        directory and performs cleanup of temporary iSS files. Handles both OSCAR
        and binary output formats depending on configuration.

        Output Format Handling:
            - OSCAR format (OSCAR.DAT): Text-based particle lists for SMASH
            - Binary format (particle_samples.bin): Efficient binary particle data

        File Operations:
            - Moves particle output to results/output_N.dat
            - Removes temporary iSS working directory
            - Cleans up MUSIC parameter file copy
            - Standardizes output naming for simulation chain

        Args:
            event_dir (str): Event directory containing iSS/ and results/ subdirectories

        Side Effects:
            - Moves particle output file to results/ directory
            - Removes entire iSS/ working directory and contents
            - Removes MUSIC parameter file from results/
            - Logs successful particle processing completion

        Raises:
            FileNotFoundError: If expected iSS output file doesn't exist
            OSError: If file operations fail due to permissions

        Notes:
            The particle output contains hadron species, four-momenta, and
            space-time positions needed for hadronic afterburner evolution.
        """
        logging.info("[iSS] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index("iSS")
        if self.config.use_OSCAR_format == 1:
            src_file = os.path.join(event_dir, "iSS", f"OSCAR.DAT")
        else:
            src_file = os.path.join(event_dir, "iSS", f"particle_samples.bin")
        dst_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "iSS"))
        logging.info(f"[iSS] Moved {src_file} to {dst_file}")

        # remove the MUSIC parameter file in results
        music_param_file = os.path.join(
            event_dir, "results", "parameters_MUSIC.ini"
        )
        if os.path.exists(music_param_file):
            os.remove(music_param_file)
            logging.info(f"[iSS] Removed {music_param_file}")
