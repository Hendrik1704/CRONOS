from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil

from src.modules.kompost_parameters import (
    KOMPOST_PARAMETERS,
    write_kompost_parameters,
)


class KoMPoST(BaseModule):
    """KoMPoST pre-equilibrium evolution module using effective kinetic theory.

    Implements pre-equilibrium evolution of the energy-momentum tensor using the
    KoMPoST (Kinetic Theory-based pre-equilibrium evolution) framework. Evolves
    the system from initial time until hydrodynamic applicability through
    effective kinetic theory (EKT) with viscous corrections.

    Key physics features:
    - Pre-equilibrium evolution with effective kinetic theory
    - Viscous corrections with configurable shear viscosity
    - Energy and momentum perturbation evolution
    - Transition from initial conditions to hydrodynamic regime
    - Support for various initial condition formats (IP-Glasma, MC-Glauber)

    Module workflow:
    1. Links KoMPoST executable and EKT tables
    2. Generates parameter file with evolution settings
    3. Links initial energy-momentum tensor from previous module
    4. Executes KoMPoST pre-equilibrium evolution
    5. Outputs evolved T^μν ready for hydrodynamics (MUSIC)

    Configuration includes evolution times, viscosity parameters, grid settings,
    and decomposition methods. The output provides smooth initial conditions
    for subsequent hydrodynamic evolution.

    Example:
        >>> kompost = KoMPoST(config.KoMPoST, full_config, project_root, event_id)
        >>> kompost.prepare_environment(event_dir)
        >>> kompost.prepare_input(event_dir)
        >>> kompost.run(event_dir)  # Pre-equilibrium evolution
        >>> kompost.fetch_output(event_dir)  # Evolved T^μν for MUSIC
    """

    def prepare_environment(self, event_dir):
        """Set up KoMPoST execution environment with executable and EKT tables.

        Creates KoMPoST directory structure and establishes symbolic links to:
        - KoMPoST executable (KoMPoST.exe)
        - Effective kinetic theory data tables (EKT directory)

        The EKT tables contain pre-computed coefficients for the effective
        kinetic theory evolution used in the pre-equilibrium phase.

        Args:
            event_dir (str): Path to event-specific directory where KoMPoST will execute.

        Raises:
            FileNotFoundError: If KoMPoST executable or EKT tables are missing.
        """
        logging.info(f"[KoMPoST] Preparing environment in {event_dir}...")
        kompost_ekt_path = os.path.join(
            self.project_root, "external_codes", "KoMPoST", "EKT"
        )
        if os.path.exists(kompost_ekt_path):
            os.symlink(
                kompost_ekt_path, os.path.join(event_dir, "KoMPoST", "EKT")
            )
        else:
            raise FileNotFoundError(
                f"[KoMPoST] Required directory {kompost_ekt_path} does not exist."
            )

        kompost_exe_path = os.path.join(
            self.project_root, "external_codes", "KoMPoST", "KoMPoST.exe"
        )
        if os.path.exists(kompost_exe_path):
            os.symlink(
                kompost_exe_path,
                os.path.join(event_dir, "KoMPoST", "KoMPoST.exe"),
            )
        else:
            raise FileNotFoundError(
                f"[KoMPoST] Required executable {kompost_exe_path} does not exist."
            )

    def prepare_input(self, event_dir):
        """Generate KoMPoST configuration file and establish input data links.

        Creates the KoMPoST parameter file (parameters_KoMPoST.ini) with physics
        settings and establishes symbolic links to input energy-momentum tensor
        data from previous simulation stages.

        Configuration Parameters:
        - tIn: Initial time for pre-equilibrium evolution (fm/c)
        - tOut: Final time when hydrodynamics takes over (fm/c)
        - InputFile: Energy-momentum tensor data from initial conditions
        - OutputFileTag: Prefix for KoMPoST output files
        - WriteTmunuBackup: Always 0, the backup T^μν maps are not needed

        Physics Context:
            KoMPoST performs effective kinetic theory evolution of the energy-momentum
            tensor from initial non-equilibrium state until local equilibration.
            The configuration controls the evolution time window and numerical precision.

        Args:
            event_dir (str): Event directory containing KoMPoST/ subdirectory
                and results/ directory for input file linking

        Side Effects:
            - Creates parameters_KoMPoST.ini in KoMPoST subdirectory
            - Creates symbolic link to previous module output as input
            - Sets module-specific input/output file naming
        """
        logging.info(f"[KoMPoST] Create input file...")
        current_module_index = self.full_config.general.modules.index("KoMPoST")
        input_file = f"output_{current_module_index-1}.dat"

        kompost_dir = os.path.join(event_dir, "KoMPoST")
        if not os.path.exists(kompost_dir):
            raise FileNotFoundError(
                f"[KoMPoST] Required directory {kompost_dir} does not exist."
            )
        ini_file = os.path.join(kompost_dir, "parameters_KoMPoST.ini")

        # Every KoMPoST setting is passed on (check_settings rejects the keys
        # KoMPoST does not read). The KoMPoST directory is removed in
        # fetch_output, so skip the input, full and background T^munu backups.
        parameters = self.config.to_dict()
        parameters.update(
            {
                "InputFile": input_file,
                "OutputFileTag": f"output_{current_module_index}",
                "WriteTmunuBackup": 0,
            }
        )
        write_kompost_parameters(ini_file, parameters, KOMPOST_PARAMETERS)

        logging.info("[KoMPoST] Input file created successfully.")

        input_Tmunu_file = os.path.join(
            event_dir, "results", input_file
        )
        input_Tmunu_file = os.path.abspath(
            input_Tmunu_file
        )  # resolve relative path
        symlink_path = os.path.join(kompost_dir, input_file)

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(input_Tmunu_file, symlink_path)
        logging.debug(f"Created symlink: {symlink_path} -> {input_Tmunu_file}")

    @time_execution
    def run(self, event_dir):
        """Execute KoMPoST pre-equilibrium evolution simulation.

        Runs the KoMPoST effective kinetic theory code to evolve the energy-momentum
        tensor from initial non-equilibrium state through pre-equilibrium dynamics
        until local thermodynamic equilibrium is achieved.

        Physics Process:
            KoMPoST solves the effective kinetic theory equations that describe
            the approach to local equilibrium in the early stages of heavy-ion
            collisions. It bridges the gap between initial condition models and
            relativistic hydrodynamics.

        Execution Details:
            - Changes to KoMPoST directory for proper file access
            - Executes KoMPoST.exe with parameters_KoMPoST.ini configuration
            - Uses run_external_command for memory monitoring and error handling
            - Restores original working directory after execution

        Args:
            event_dir (str): Event directory containing configured KoMPoST/ subdirectory

        Side Effects:
            - Temporarily changes working directory to KoMPoST/
            - Executes external KoMPoST binary with subprocess monitoring
            - Creates output files with energy-momentum tensor evolution
            - Logs execution progress and performance metrics

        Raises:
            subprocess.CalledProcessError: If KoMPoST execution fails
            OSError: If KoMPoST directory or executable not accessible
        """
        logging.info("[KoMPoST] run...")
        kompost_dir = os.path.join(event_dir, "KoMPoST")
        kompost_exe = "KoMPoST.exe"  # just the filename
        ini_file = "parameters_KoMPoST.ini"

        logging.info("[KoMPoST] Running KoMPoST...")

        cwd = os.getcwd()
        try:
            os.chdir(kompost_dir)

            run_kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
                run_kwargs["stdout"] = subprocess.DEVNULL
                run_kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[KoMPoST] Running with suppressed output...")
            run_external_command(
                [f"./{kompost_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="KoMPoST",
                **run_kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[KoMPoST] Execution failed: {e}")
            raise
        finally:
            os.chdir(cwd)

        logging.info("[KoMPoST] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect and organize KoMPoST simulation output for downstream modules.

        Moves the KoMPoST energy-momentum tensor output to the standardized
        results directory for use by subsequent physics modules (typically MUSIC
        hydrodynamics). Handles the complex KoMPoST output filename format.

        Output Processing:
            KoMPoST generates files with descriptive physics names that include
            flow components and transport coefficients. This method standardizes
            the naming for integration with the CRONOS simulation chain.

        File Operations:
            - Source: KoMPoST/output_N.music_init_flowNonLinear_pimunuTransverse_pimunuNS.txt
            - Target: results/output_N.dat (standardized format)
            - Preserves all physics data while simplifying file management

        Args:
            event_dir (str): Event directory containing KoMPoST/ and results/ subdirectories

        Side Effects:
            - Moves KoMPoST output file to results/ directory
            - Renames file to standard output_N.dat format
            - Logs successful data processing completion

        Raises:
            FileNotFoundError: If expected KoMPoST output file doesn't exist
            OSError: If file move operation fails due to permissions

        Notes:
            The output contains energy density, flow velocity, and viscous stress
            tensor components needed for hydrodynamic initialization in MUSIC.
        """
        logging.info("[KoMPoST] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index("KoMPoST")
        src_file = os.path.join(
            event_dir,
            "KoMPoST",
            f"output_{current_module_index}.music_init_flowNonLinear_pimunuTransverse_pimunuNS.txt",
        )
        dst_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "KoMPoST"))
        logging.info(f"[KoMPoST] Moved {src_file} to {dst_file}")
