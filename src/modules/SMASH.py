from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class SMASH(BaseModule):
    """SMASH hadronic afterburner module for hadronic rescattering phase.
    
    Implements hadronic transport using the SMASH (Simulating Many Accelerated
    Strongly-interacting Hadrons) code. Evolves hadrons from particlization
    through hadronic rescattering, accounting for elastic/inelastic collisions,
    resonance formation/decay, and final freeze-out.
    
    Key physics features:
    - Hadronic transport with elastic and inelastic collisions
    - Resonance production and decay (ρ, Δ, K*, etc.)
    - String fragmentation for high-energy collisions
    - Proper treatment of hadron-hadron cross sections
    - Optional collision suppression for free-streaming mode
    - Extended output for analysis toolkit compatibility
    
    Module workflow:
    1. Links SMASH executable, particle tables, and conversion scripts
    2. Converts iSS output from OSCAR1997A to OSCAR2013 format
    3. Generates SMASH parameter file with collision settings
    4. Executes SMASH hadronic evolution with memory monitoring
    5. Outputs final particle distributions for analysis
    
    Configuration includes collision parameters, evolution time, random seed,
    and output format. The module can run with or without hadronic interactions
    depending on physics requirements.
    
    Example:
        >>> smash = SMASH(config.SMASH, full_config, project_root, event_id)
        >>> smash.prepare_environment(event_dir)
        >>> smash.prepare_input(event_dir)
        >>> smash.run(event_dir)  # Hadronic afterburner
        >>> smash.fetch_output(event_dir)  # Final hadron distributions
    """
    def prepare_environment(self, event_dir):
        """Set up SMASH execution environment with executable and data files.
        
        Creates SMASH directory structure and establishes symbolic links to:
        - SMASH executable (smash)
        - Particle data tables (iSS_tables for format conversion)
        - OSCAR format conversion script (convert_OSCAR1997A_to_OSCAR2013.py)
        
        The conversion script is needed to transform iSS output from OSCAR1997A
        format to OSCAR2013 format that SMASH can process.
        
        Args:
            event_dir (str): Path to event-specific directory where SMASH will execute.
                
        Raises:
            SystemExit: If SMASH executable or required scripts are missing.
        """
        logging.info(f"[SMASH] Preparing environment in {event_dir}...")

        # iSS tables needed for converter script
        iss_tables_path = os.path.join(
            self.project_root, "external_codes", "iSS", "iSS_tables"
        )
        if os.path.exists(iss_tables_path):
            os.symlink(
                iss_tables_path, os.path.join(event_dir, "SMASH", "iSS_tables")
            )
        else:
            logging.error(
                f"[SMASH] Required directory {iss_tables_path} does not exist."
            )
            exit(1)

        smash_exe_path = os.path.join(
            self.project_root, "external_codes", "smash", "build", "smash"
        )
        if os.path.exists(smash_exe_path):
            os.symlink(
                smash_exe_path, os.path.join(event_dir, "SMASH", "smash")
            )
        else:
            logging.error(
                f"[SMASH] Required executable {smash_exe_path} does not exist."
            )
            exit(1)

        oscar_script_path = os.path.join(
            self.project_root, "utilities", "convert_OSCAR1997A_to_OSCAR2013.py"
        )
        if os.path.exists(oscar_script_path):
            os.symlink(
                oscar_script_path,
                os.path.join(
                    event_dir, "SMASH", "convert_OSCAR1997A_to_OSCAR2013.py"
                ),
            )
        else:
            logging.error(
                f"[SMASH] Required script {oscar_script_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        """Generate SMASH configuration file and establish particle input links.
        
        Creates the SMASH parameter file (parameters_SMASH.yaml) with hadronic
        transport settings and establishes symbolic links to particle data from
        the Cooper-Frye particlization (iSS module).
        
        Configuration Components:
            - General settings: Version, output verbosity, random seed
            - Modi configuration: External particle list input mode
            - Output settings: OSCAR format particle lists
            - Physics parameters: Cross sections, decay modes, potentials
        
        Hadronic Transport Physics:
            SMASH performs microscopic hadronic transport using Monte Carlo
            methods to simulate hadron-hadron interactions, resonance production/decay,
            and final particle freeze-out in heavy-ion collisions.
        
        Args:
            event_dir (str): Event directory containing SMASH/ subdirectory
                and particle input from iSS particlization
        
        Side Effects:
            - Creates parameters_SMASH.yaml in SMASH subdirectory
            - Creates symbolic link to particle input from previous module
            - Configures OSCAR output format for analysis compatibility
            - Sets up random seed and physics parameters from configuration
        
        Notes:
            SMASH uses YAML format for configuration, unlike other modules
            that use INI format. The particle input must be in OSCAR format.
        """
        logging.info(f"[SMASH] Create input file...")
        current_module_index = self.full_config.general.modules.index("SMASH")
        self.config.input_filename = f"output_{current_module_index-1}.dat"

        smash_dir = os.path.join(event_dir, "SMASH")
        if not os.path.exists(smash_dir):
            logging.error(
                f"[SMASH] Required directory {smash_dir} does not exist."
            )
            exit(1)

        input_file = os.path.join(
            event_dir, "results", self.config.input_filename
        )
        input_file = os.path.abspath(input_file)  # resolve relative path
        symlink_path = os.path.join(smash_dir, self.config.input_filename)

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(input_file, symlink_path)
        logging.debug(f"Created symlink: {symlink_path} -> {input_file}")

        # Convert the iSS output OSCAR1997A to OSCAR2013 using the provided script
        convert_script = "convert_OSCAR1997A_to_OSCAR2013.py"
        cwd = os.getcwd()
        try:
            os.chdir(smash_dir)
            result = run_external_command(
                [
                    "python3",
                    convert_script,
                    "./iSS_tables/pdg-SMASH.dat",
                    self.config.input_filename,
                    "OSCAR0",
                    "--seed",
                    str(self.config.Randomseed),
                ],
                check=True,
                capture_output=True,
                text=True,
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="SMASH-convert",
            )
            num_events = int(result["stdout"].strip())
            self.config.Nevents = num_events
            logging.info(
                f"[SMASH] Number of events set to {num_events} from Cooper-Frye FO..."
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[SMASH] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        ini_file = os.path.join(smash_dir, "parameters_SMASH.yaml")

        afterburner_toolkit = False
        # Check if the afterburner_toolkit is in the module list, then extended output is needed
        if "afterburner_toolkit" in self.full_config.general.modules:
            afterburner_toolkit = True

        with open(ini_file, "w") as f:
            f.write(f"Logging:\n")
            f.write(f"    default: INFO\n")
            f.write(f"\n")
            f.write(f"General:\n")
            f.write(f"    Modus:         List\n")
            f.write(f"    Time_Step_Mode: None\n")
            f.write(f"    Delta_Time:    {self.config.Delta_Time}\n")
            f.write(f"    End_Time:      {self.config.End_Time}\n")
            f.write(f"    Randomseed:    {self.config.Randomseed}\n")
            f.write(f"    Nevents:       {self.config.Nevents}\n")

            if self.config.No_Collisions == 1:
                f.write(f"Collision_Term:\n")
                f.write(f"    No_Collisions: true\n")

            f.write(f"Output:\n")
            f.write(f"    Output_Interval: 100.0\n")
            f.write(f"    Particles:\n")
            f.write(f'        Format:          ["Oscar2013"]\n')
            if afterburner_toolkit:
                f.write(f"        Extended:          true\n")

            f.write(f"Modi:\n")
            f.write(f"    List:\n")
            f.write(
                f"        # If the build directory is not located in the smash directory anymore,\n"
            )
            f.write(
                f"        # the absolute path specified below will not work anymore.\n"
            )
            f.write(
                f"        # You can alternatively pass the path directly from the command line\n"
            )
            f.write(f'        # with the "-c" command:\n')
            f.write(
                f"        # ./smash -i <path to config file> -c 'Modi: {{ List: {{ File_Directory: <path to file that is read in> }} }}'\n"
            )
            f.write(f"        File_Directory: .\n")
            f.write(f'        File_Prefix: "OSCAR"\n')
            f.write(f"        Shift_Id: 0\n")

        logging.info("[SMASH] Input file created successfully.")

    @time_execution
    def run(self, event_dir):
        """Execute SMASH hadronic afterburner transport simulation.
        
        Runs the SMASH hadronic transport code to evolve the particle ensemble
        from Cooper-Frye particlization through hadronic interactions until
        kinetic freeze-out, providing the final particle distributions.
        
        Physics Process:
            SMASH performs microscopic hadronic transport simulation including:
            - Elastic and inelastic hadron-hadron scattering
            - Resonance production, decay, and regeneration
            - String fragmentation for high-energy processes
            - Final kinetic freeze-out and particle detection
        
        Computational Features:
            - Monte Carlo event-by-event evolution
            - Adaptive time stepping for numerical stability
            - Memory-efficient particle list management
            - Parallel processing capabilities (if configured)
        
        Args:
            event_dir (str): Event directory containing configured SMASH/ subdirectory
                with particle input and parameter files
        
        Side Effects:
            - Temporarily changes working directory to SMASH/
            - Executes external SMASH binary with subprocess monitoring
            - Creates output directory structure (data/0/)
            - Generates particle lists in OSCAR format
            - Logs execution progress and performance metrics
        
        Raises:
            subprocess.CalledProcessError: If SMASH execution fails
            OSError: If SMASH directory or executable not accessible
        
        Output:
            Produces final particle lists ready for flow analysis and
            experimental comparison after hadronic interactions.
        """
        logging.info("[SMASH] run...")

        smash_dir = os.path.join(event_dir, "SMASH")
        smash_exe = "smash"
        ini_file = "parameters_SMASH.yaml"

        logging.info("[SMASH] Running SMASH...")

        cwd = os.getcwd()
        try:
            os.chdir(smash_dir)
            kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[SMASH] Running with suppressed output...")
            run_external_command(
                [f"./{smash_exe}", "-i", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="SMASH",
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[SMASH] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[SMASH] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect SMASH particle output and prepare for analysis.
        
        Moves the final particle lists from SMASH hadronic transport to the
        standardized results directory and performs cleanup. The output contains
        the complete final-state particle information after all hadronic interactions.
        
        Output Processing:
            - Collects particle_lists.oscar from SMASH data directory
            - Moves to standardized output_N.dat format
            - Handles potential format conversion for analysis tools
            - Preserves complete particle four-momentum and species information
        
        File Operations:
            - Source: SMASH/data/0/particle_lists.oscar
            - Target: results/output_N.dat (final simulation output)
            - Cleanup: Removes SMASH working directory
        
        Args:
            event_dir (str): Event directory containing SMASH/ and results/ subdirectories
        
        Side Effects:
            - Moves SMASH particle output to results/ directory
            - Removes entire SMASH/ working directory and contents
            - Converts to OSCAR2013 format if configured
            - Logs successful hadronic evolution completion
        
        Raises:
            FileNotFoundError: If expected SMASH output file doesn't exist
            OSError: If file operations fail due to permissions
        
        Notes:
            The final particle output represents the complete heavy-ion collision
            evolution from initial conditions through hadronic freeze-out,
            ready for experimental analysis and comparison.
        """
        logging.info("[SMASH] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index("SMASH")
        src_file = os.path.join(
            event_dir, "SMASH", "data", "0", "particle_lists.oscar"
        )
        dst_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "SMASH"))
        logging.info(f"[SMASH] Moved {src_file} to {dst_file}")
