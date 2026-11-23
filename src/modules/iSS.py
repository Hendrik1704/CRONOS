from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


def format_iss_value(value):
    """Format a configuration value for the iSS parameter file.

    iSS converts every value to a number, so booleans are written as 0 or 1.
    """
    if isinstance(value, bool):
        return str(int(value))
    return str(value)


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
            FileNotFoundError: If iSS executable or particle tables are missing.
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
            raise FileNotFoundError(
                f"[iSS] Required directory {iss_tables_path} does not exist."
            )

        iss_exe_path = os.path.join(
            self.project_root, "external_codes", "iSS", "iSS.e"
        )
        if os.path.exists(iss_exe_path):
            os.symlink(iss_exe_path, os.path.join(event_dir, "iSS", "iSS.e"))
        else:
            raise FileNotFoundError(
                f"[iSS] Required executable {iss_exe_path} does not exist."
            )

    def parameters(self):
        """Return the parameters CRONOS writes to the iSS parameter file.

        Every key of the iSS section is passed on (check_settings rejects the
        keys iSS does not read). CRONOS sets the random seed and, without
        SMASH, the output format and the resonance decays.
        """
        parameters = self.config.to_dict()
        parameters["randomSeed"] = self.full_config.general.random_seed
        if "SMASH" not in self.full_config.general.modules:
            parameters.update(
                {
                    "use_OSCAR_format": 0,
                    "use_binary_format": 1,
                    "perform_decays": 1,
                }
            )
        return parameters

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
        input_filename = f"output_{current_module_index-1}.dat"

        iSS_dir = os.path.join(event_dir, "iSS")
        if not os.path.exists(iSS_dir):
            raise FileNotFoundError(
                f"[iSS] Required directory {iSS_dir} does not exist."
            )
        ini_file = os.path.join(iSS_dir, "parameters_iSS.ini")

        parameters = self.parameters()
        if "SMASH" not in self.full_config.general.modules:
            logging.info(
                "[iSS] SMASH module not detected. Setting use_OSCAR_format=0, "
                "use_binary_format=1, perform_decays=1."
            )

        with open(ini_file, "w") as f:
            for key, value in parameters.items():
                f.write(f"{key} = {format_iss_value(value)}\n")

        logging.info("[iSS] Input file created successfully.")

        # Create a results directory in the iSS directory and move the surface there
        results_dir = os.path.join(event_dir, "iSS", "results")
        os.makedirs(results_dir, exist_ok=True)

        input_surface_file = os.path.join(event_dir, "results", input_filename)
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
            raise
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
        if self.parameters()["use_OSCAR_format"] == 1:
            src_file = os.path.join(event_dir, "iSS", f"OSCAR.DAT")
        else:
            src_file = os.path.join(event_dir, "iSS", f"particle_samples.bin")
        dst_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        # remove the MUSIC parameter file in results first: output_N.dat is
        # published last, so that its existence shows that iSS finished
        music_param_file = os.path.join(
            event_dir, "results", "parameters_MUSIC.ini"
        )
        if os.path.exists(music_param_file):
            os.remove(music_param_file)
            logging.info(f"[iSS] Removed {music_param_file}")

        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "iSS"))
        logging.info(f"[iSS] Moved {src_file} to {dst_file}")
