from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class KoMPoST3D(BaseModule):
    """KoMPoST-3D pre-equilibrium evolution module for 3+1D initial conditions.

    Implements pre-equilibrium evolution of the full 3D energy-momentum tensor
    using KoMPoST-3D. The perturbations around the local background are
    propagated with kinetic theory response functions in the relaxation time
    approximation (RTA) in the transverse plane and in spatial rapidity.

    Key physics features:
    - Pre-equilibrium evolution of 3D (non boost-invariant) initial conditions
    - Kinetic theory (RTA) background and energy perturbation propagation
    - Viscous corrections with configurable shear viscosity
    - Output of e, u^μ and the Navier-Stokes π^μν for 3+1D hydrodynamics

    Module workflow:
    1. Links KoMPoST-3D executable and RTA response tables
    2. Generates parameter file with evolution settings and the 3D grid
    3. Links initial energy-momentum tensor from previous module
    4. Executes KoMPoST-3D pre-equilibrium evolution
    5. Outputs evolved T^μν ready for 3+1D hydrodynamics (MUSIC)

    The input is the KoMPoST-3D format: one header line, then
    ix iy ieta τT^ττ τT^xx τT^yy τ³T^ηη -τT^τx -τT^τy -τ²T^τη -τT^xy -τ²T^yη -τ²T^ηx
    with τT^μν in GeV/fm². KoMPoST-3D only supports EVOLUTION_MODE=1 and
    MOMENTUM_PERTURBATIONS=0.

    Example:
        >>> kompost = KoMPoST3D(config.KoMPoST3D, full_config, project_root, event_id)
        >>> kompost.prepare_environment(event_dir)
        >>> kompost.prepare_input(event_dir)
        >>> kompost.run(event_dir)  # 3D pre-equilibrium evolution
        >>> kompost.fetch_output(event_dir)  # Evolved T^μν for MUSIC
    """

    def prepare_environment(self, event_dir):
        """Set up KoMPoST-3D execution environment with executable and RTA tables.

        Creates symbolic links in the KoMPoST3D directory to:
        - KoMPoST-3D executable (KoMPoST.exe)
        - Kinetic theory response tables (RTA directory)

        KoMPoST-3D reads the response tables from ./RTA/ENERGYRESPONSE/
        relative to its working directory.

        Args:
            event_dir (str): Path to event-specific directory where KoMPoST-3D will execute.

        Raises:
            SystemExit: If KoMPoST-3D executable or RTA tables are missing.
        """
        logging.info(f"[KoMPoST3D] Preparing environment in {event_dir}...")
        kompost_rta_path = os.path.join(
            self.project_root, "external_codes", "KoMPoST-3D", "RTA"
        )
        if os.path.exists(kompost_rta_path):
            os.symlink(
                kompost_rta_path, os.path.join(event_dir, "KoMPoST3D", "RTA")
            )
        else:
            logging.error(
                f"[KoMPoST3D] Required directory {kompost_rta_path} does not exist."
            )
            exit(1)

        kompost_exe_path = os.path.join(
            self.project_root, "external_codes", "KoMPoST-3D", "KoMPoST.exe"
        )
        if os.path.exists(kompost_exe_path):
            os.symlink(
                kompost_exe_path,
                os.path.join(event_dir, "KoMPoST3D", "KoMPoST.exe"),
            )
        else:
            logging.error(
                f"[KoMPoST3D] Required executable {kompost_exe_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        """Generate KoMPoST-3D configuration file and establish input data links.

        Creates the KoMPoST-3D parameter file (parameters_KoMPoST3D.ini) and
        links the input energy-momentum tensor from the previous module.

        Configuration Parameters:
        - tIn: Initial time for pre-equilibrium evolution (fm/c)
        - tOut: Final time when hydrodynamics takes over (fm/c)
        - InputFile: Energy-momentum tensor data from initial conditions
        - OutputFileTag: Prefix for KoMPoST-3D output files
        - WriteTmunuBackup: Always 0, the backup T^μν maps are not needed
        - afm, Ns, deta, Neta: Transverse and rapidity grid
        - xSTART/xEND, ySTART/yEND, etaSTART/etaEND: Grid region to evolve

        Args:
            event_dir (str): Event directory containing KoMPoST3D/ subdirectory
                and results/ directory for input file linking

        Side Effects:
            - Creates parameters_KoMPoST3D.ini in KoMPoST3D subdirectory
            - Creates symbolic link to previous module output as input
        """
        logging.info(f"[KoMPoST3D] Create input file...")
        current_module_index = self.full_config.general.modules.index(
            "KoMPoST3D"
        )
        self.config.InputFile = f"output_{current_module_index-1}.dat"
        self.config.OutputFileTag = f"output_{current_module_index}"

        kompost_dir = os.path.join(event_dir, "KoMPoST3D")
        if not os.path.exists(kompost_dir):
            logging.error(
                f"[KoMPoST3D] Required directory {kompost_dir} does not exist."
            )
            exit(1)
        ini_file = os.path.join(kompost_dir, "parameters_KoMPoST3D.ini")

        with open(ini_file, "w") as f:
            # KoMPoSTInputs
            f.write("[KoMPoSTInputs]\n")
            f.write(f"tIn={self.config.tIn};\n\n")
            f.write(f"tOut = {self.config.tOut};\n\n")
            f.write(f"InputFile={self.config.InputFile}\n")
            f.write(f"OutputFileTag={self.config.OutputFileTag}\n")
            f.write(
                "# The KoMPoST3D directory is removed in fetch_output, so skip\n"
            )
            f.write("# the input, full and background T^{munu} backup files\n")
            f.write("WriteTmunuBackup = 0\n\n")

            # KoMPoSTParameters
            f.write("[KoMPoSTParameters]\n")
            f.write(f"EtaOverS = {self.config.EtaOverS}\n")
            f.write(
                f"EtaOverSTemperatureScale = {self.config.EtaOverSTemperatureScale}\n"
            )
            f.write(f"# Effective number of degrees of freedom\n")
            f.write(f"NuEffective = {self.config.NuEffective}\n")
            f.write(f"# only 1 (kinetic theory) is supported by KoMPoST-3D\n")
            f.write(f"EVOLUTION_MODE={self.config.EVOLUTION_MODE}\n\n")
            f.write(f"# 0 or 1\n")
            f.write(
                f"ENERGY_PERTURBATIONS={self.config.ENERGY_PERTURBATIONS}\n\n"
            )
            f.write(f"# only 0 is supported by KoMPoST-3D\n")
            f.write(
                f"MOMENTUM_PERTURBATIONS={self.config.MOMENTUM_PERTURBATIONS}\n\n"
            )
            f.write(f"Regulator={self.config.Regulator}\n\n")

            # EventInput
            f.write("[EventInput]\n")
            f.write(
                f"# scaling parameter for the input energy momentum tensor\n"
            )
            f.write(f"normFactor = {self.config.normFactor}\n")
            f.write(f"# transverse lattice spacing in fm\n")
            f.write(f"afm = {self.config.afm}\n")
            f.write(f"# lattice spacing in spatial rapidity\n")
            f.write(f"deta = {self.config.deta}\n")
            f.write(f"# number of grid points in x, y and eta\n")
            f.write(f"Ns={self.config.Ns};\n")
            f.write(f"Neta={self.config.Neta};\n\n")
            f.write(f"# The first grid point to include in the x direction\n")
            f.write(f"xSTART={self.config.xSTART};\n")
            f.write(f"# The last grid point to include in the x direction\n")
            f.write(f"xEND={self.config.xEND};\n\n")
            f.write(f"#The first grid point to include in the y direction\n")
            f.write(f"ySTART={self.config.ySTART};\n")
            f.write(f"#The last grid point to include in the y direction\n")
            f.write(f"yEND={self.config.yEND};\n\n")
            f.write(f"#The first grid point to include in the eta direction\n")
            f.write(f"etaSTART={self.config.etaSTART};\n")
            f.write(f"#The last grid point to include in the eta direction\n")
            f.write(f"etaEND={self.config.etaEND};\n")
        logging.info("[KoMPoST3D] Input file created successfully.")

        input_Tmunu_file = os.path.join(
            event_dir, "results", self.config.InputFile
        )
        input_Tmunu_file = os.path.abspath(
            input_Tmunu_file
        )  # resolve relative path
        symlink_path = os.path.join(kompost_dir, self.config.InputFile)

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(input_Tmunu_file, symlink_path)
        logging.debug(f"Created symlink: {symlink_path} -> {input_Tmunu_file}")

    @time_execution
    def run(self, event_dir):
        """Execute KoMPoST-3D pre-equilibrium evolution simulation.

        Runs KoMPoST-3D with parameters_KoMPoST3D.ini in the KoMPoST3D
        directory, using run_external_command for memory monitoring.
        KoMPoST-3D keeps the full response tables in memory, so a single
        event needs several GB.

        Args:
            event_dir (str): Event directory containing configured KoMPoST3D/ subdirectory

        Raises:
            subprocess.CalledProcessError: If KoMPoST-3D execution fails
        """
        logging.info("[KoMPoST3D] run...")
        kompost_dir = os.path.join(event_dir, "KoMPoST3D")
        kompost_exe = "KoMPoST.exe"  # just the filename
        ini_file = "parameters_KoMPoST3D.ini"

        logging.info("[KoMPoST3D] Running KoMPoST-3D...")

        cwd = os.getcwd()
        try:
            os.chdir(kompost_dir)

            run_kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
                run_kwargs["stdout"] = subprocess.DEVNULL
                run_kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[KoMPoST3D] Running with suppressed output...")
            run_external_command(
                [f"./{kompost_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="KoMPoST3D",
                **run_kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[KoMPoST3D] Execution failed: {e}")
            raise
        finally:
            os.chdir(cwd)

        logging.info("[KoMPoST3D] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect KoMPoST-3D output for downstream modules.

        Moves the MUSIC initial condition file with the Navier-Stokes shear
        stress tensor (same choice as the KoMPoST module) to the results
        directory and removes the KoMPoST3D working directory.

        File Operations:
            - Source: KoMPoST3D/output_N_pimunuNS.dat
            - Target: results/output_N.dat (standardized format)

        Args:
            event_dir (str): Event directory containing KoMPoST3D/ and results/ subdirectories

        Raises:
            FileNotFoundError: If expected KoMPoST-3D output file doesn't exist
        """
        logging.info("[KoMPoST3D] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index(
            "KoMPoST3D"
        )
        src_file = os.path.join(
            event_dir,
            "KoMPoST3D",
            f"output_{current_module_index}_pimunuNS.dat",
        )
        dst_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "KoMPoST3D"))
        logging.info(f"[KoMPoST3D] Moved {src_file} to {dst_file}")
