from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil

# IP-Glasma 2.0 input parameters written from the IPGlasma configuration
IPGLASMA_PARAMETERS = [
    "runEvolution",
    "size",
    "L",
    "Ny",
    "g",
    "maxTime",
    "timeStepsPerLatticeSpacing",
    "inverseQsForMaxTime",
    "projectile",
    "target",
    "sigmaNN",
    "useNucleus",
    "readInitialWilsonLines",
    "bMin",
    "bMax",
    "sampleBFromLinearDistribution",
    "rotateReactionPlane",
    "g2muGeV",
    "useSmoothNucleus",
    "useFixedNpart",
    "nucleiToAverage",
    "gaussianWounding",
    "nucleonPositionsFromFile",
    "polarizationProjectile",
    "polarizationTarget",
    "polarizationProjectileJz",
    "polarizationTargetJz",
    "lightNucleusOption",
    "useInputWSParams",
    "radiusWS",
    "diffusenessWS",
    "beta2",
    "beta3",
    "beta4",
    "gamma",
    "deltaRnp",
    "deltaAnp",
    "forceDMin",
    "dMin",
    "nucleonModel",
    "subNucleonParamType",
    "subNucleonParamSet",
    "m",
    "BG",
    "protonAnisotropy",
    "BGq",
    "BGqVar",
    "dqMin",
    "omega",
    "Nq",
    "NqFluc",
    "shiftConstituentQuarkProtonOrigin",
    "QsMuRatio",
    "smearQs",
    "smearingWidth",
    "UVDamp",
    "minimumQs2ST",
    "nucleusQsTableFileName",
    "rapidity",
    "usePseudoRapidity",
    "jacobianMass",
    "useFluctuatingX",
    "sqrtS",
    "projectileX",
    "targetX",
    "xQsFactor",
    "runningCoupling",
    "mu0",
    "c",
    "nFlavors",
    "LambdaQCD",
    "runWithQs",
    "runningCouplingQsFactor",
    "runWithLocalQs",
    "runWithKt",
    "computeGluonMultiplicity",
    "computeEccentricities",
    "writeHydro",
    "writeJazma",
    "writeTmunu",
    "LOutput",
    "sizeOutput",
    "writeWilsonLines",
    "writeOutputsToHDF5",
    "useJIMWLK",
    "jimwlkMu0",
    "jimwlkLambdaQCD",
    "jimwlkC",
    "jimwlkMass",
    "jimwlkAlphaS",
    "jimwlkDs",
    "jimwlkInitialX",
    "jimwlkSaveSnapshots",
]


class IPGlasma(BaseModule):
    """IP-Glasma initial condition module for the CRONOS framework.

    Wraps the IP-Glasma code (version 2.0) to generate fluctuating Glasma
    initial conditions for hydrodynamic evolution. This module prepares the
    execution environment, writes the IP-Glasma parameter file from the
    configuration, runs the external binary with memory monitoring, and
    collects the relevant output files.

    Typical workflow:
    1. :meth:`prepare_environment` links the executable, tables and
       auxiliary input files into an event-specific IPGlasma directory.
    2. :meth:`prepare_input` creates ``parameters_IPGlasma.ini`` based on
       the configuration object.
    3. :meth:`run` executes the IP-Glasma binary in the prepared
       directory.
    4. :meth:`fetch_output` moves the produced energy-momentum tensor and
       auxiliary event-by-event observables into the event ``results``
       directory and cleans up temporary files.
    """

    def prepare_environment(self, event_dir):
        """Set up IP-Glasma execution environment for a single event.

        Creates the ``IPGlasma`` subdirectory in the given event
        directory and establishes symbolic links to all IP-Glasma
        resources that are required at run time:

        - ``nucleusConfigurations`` (nuclear density profiles)
        - ``ipglasma`` executable
        - the nuclear Qs table named by ``nucleusQsTableFileName``
          (``qs2Adj_vs_Tp_vs_Y_240.in`` by default)
        - ``tables`` and ``utilities`` directories

        Args:
            event_dir (str): Path to the event-specific directory.

        Raises:
            SystemExit: If any of the required IP-Glasma components are
                missing in ``external_codes/ipglasma``.
        """
        logging.info(f"Preparing IP-Glasma environment in {event_dir}")
        ipglasma_event_dir = os.path.join(event_dir, "IPGlasma")
        os.makedirs(ipglasma_event_dir, exist_ok=True)
        nucleus_config_path = os.path.join(
            self.project_root,
            "external_codes",
            "ipglasma",
            "nucleusConfigurations",
        )
        if os.path.exists(nucleus_config_path):
            os.symlink(
                nucleus_config_path,
                os.path.join(ipglasma_event_dir, "nucleusConfigurations"),
            )
        else:
            logging.error(
                f"[IPGlasma] Required directory {nucleus_config_path} does not exist."
            )
            exit(1)
        ipglasma_exe_path = os.path.join(
            self.project_root, "external_codes", "ipglasma", "ipglasma"
        )
        if os.path.exists(ipglasma_exe_path):
            os.symlink(
                ipglasma_exe_path, os.path.join(ipglasma_event_dir, "ipglasma")
            )
        else:
            logging.error(
                f"[IPGlasma] Required executable {ipglasma_exe_path} does not exist."
            )
            exit(1)

        qs_table = self.config.nucleusQsTableFileName
        ipglasma_qs2adj_path = os.path.join(
            self.project_root, "external_codes", "ipglasma", qs_table
        )
        if os.path.exists(ipglasma_qs2adj_path):
            os.symlink(
                ipglasma_qs2adj_path,
                os.path.join(ipglasma_event_dir, qs_table),
            )
        else:
            logging.error(
                f"[IPGlasma] Required file {ipglasma_qs2adj_path} does not exist."
            )
            exit(1)

        ipglasma_tables_path = os.path.join(
            self.project_root, "external_codes", "ipglasma", "tables"
        )
        if os.path.exists(ipglasma_tables_path):
            os.symlink(
                ipglasma_tables_path, os.path.join(ipglasma_event_dir, "tables")
            )
        else:
            logging.error(
                f"[IPGlasma] Required directory {ipglasma_tables_path} does not exist."
            )
            exit(1)

        ipglasma_utilities_path = os.path.join(
            self.project_root, "external_codes", "ipglasma", "utilities"
        )
        if os.path.exists(ipglasma_utilities_path):
            os.symlink(
                ipglasma_utilities_path,
                os.path.join(ipglasma_event_dir, "utilities"),
            )
        else:
            logging.error(
                f"[IPGlasma] Required directory {ipglasma_utilities_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        """Generate IP-Glasma parameter file for the current event.

        Writes ``parameters_IPGlasma.ini`` in the event's ``IPGlasma``
        directory. All parameters are taken from ``self.config`` and
        written in the format expected by the IP-Glasma code, including
        handling of the snapshot list without scientific notation.

        Args:
            event_dir (str): Path to the event-specific directory that
                contains the ``IPGlasma`` subdirectory.

        Raises:
            SystemExit: If the ``IPGlasma`` directory does not exist.
        """
        IPGlasma_dir = os.path.join(event_dir, "IPGlasma")
        if not os.path.exists(IPGlasma_dir):
            logging.error(
                f"[IPGlasma] Required directory {IPGlasma_dir} does not exist."
            )
            exit(1)
        ini_file = os.path.join(IPGlasma_dir, "parameters_IPGlasma.ini")

        with open(ini_file, "w") as f:
            # IP-Glasma 2.0 rejects unknown keys and requires all keys
            # that are not optional; keys of switched-off features are
            # ignored
            for key in IPGLASMA_PARAMETERS:
                f.write(f"{key} {self.config[key]}\n")
            f.write("useSeedList 0\n")
            # seed -1 draws a random seed
            f.write(f"seed {self.full_config.general.random_seed}\n")
            # KoMPoST reads the text T^munu file
            f.write("writeTmunuBinary 0\n")
            snapshot = self.config.jimwlkXSnapshotList
            if isinstance(snapshot, list):
                varStr = ",".join(f"{float(var):.7f}" for var in snapshot)
            else:
                varStr = f"{float(snapshot):.7f}"
            f.write(f"jimwlkXSnapshotList {varStr}\n")
            f.write("EndOfFile")

        logging.info("[IPGlasma] Input file created successfully.")

    @time_execution
    def run(self, event_dir):
        """Execute the IP-Glasma binary for the current event.

        Runs the ``ipglasma`` executable in the event-specific
        ``IPGlasma`` directory using :func:`run_external_command`, which
        provides optional memory monitoring and output suppression based
        on the global configuration.

        Args:
            event_dir (str): Path to the event-specific directory.
        """
        logging.info(f"[IPGlasma] run...")
        ipglasma_dir = os.path.join(event_dir, "IPGlasma")
        ipglasma_exe = "ipglasma"  # just the filename
        ini_file = "parameters_IPGlasma.ini"

        logging.info("[IPGlasma] Running IP-Glasma...")

        cwd = os.getcwd()
        try:
            os.chdir(ipglasma_dir)

            run_kwargs = {}
            if not self.full_config.general.module_terminal_output:
                run_kwargs["stdout"] = subprocess.DEVNULL
                run_kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[IPGlasma] Running with suppressed output...")
            run_external_command(
                [f"./{ipglasma_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="IPGlasma",
                **run_kwargs,
            )
        except subprocess.CalledProcessError as e:
            # IP-Glasma 2.0 returns 1 for an invalid input file
            logging.error(f"[IPGlasma] Execution failed: {e}")
            raise
        finally:
            os.chdir(cwd)

        logging.info("[IPGlasma] Execution finished.")

    # ------------------------------------------------------------------
    # Helpers for locating IP-Glasma output files
    # ------------------------------------------------------------------

    def _find_tmunu(self, ipglasma_dir):
        """Return path to the Tmunu output file, or ``None``."""
        import glob

        maxtime = float(self.config.maxTime)
        candidate = os.path.join(ipglasma_dir, f"Tmunu-t{maxtime}-0.dat")
        if os.path.exists(candidate):
            return candidate
        # Fallback: glob for float-formatting differences
        matches = glob.glob(os.path.join(ipglasma_dir, "Tmunu-t*-0.dat"))
        if matches:
            logging.info(
                f"[IPGlasma] Found Tmunu output: "
                f"{os.path.basename(matches[0])}"
            )
            return matches[0]
        return None

    def _find_epsilon_u(self, ipglasma_dir):
        """Return path to the epsilon-u-Hydro output file, or ``None``."""
        candidate = os.path.join(ipglasma_dir, "epsilon-u-Hydro-TauHydro-0.dat")
        if os.path.exists(candidate):
            return candidate
        return None

    def fetch_output(self, event_dir):
        """Collect IP-Glasma output files and clean up.

        Moves the main IP-Glasma energy-momentum tensor output to the
        event ``results`` directory, renaming it to
        ``output_{module_index}.dat`` so that subsequent modules can
        locate it consistently.

        The output file depends on the output switches:

        - ``writeHydro 1``: ``epsilon-u-Hydro-TauHydro-0.dat``
        - ``writeTmunu 1``: ``Tmunu-t{maxTime}-0.dat`` (text format)

        When both are written, the ``Tmunu`` file is preferred if
        KoMPoST is among the active modules (it requires the full
        T^μν); otherwise ``epsilon-u-Hydro`` is used.

        In addition, the following auxiliary files are moved unchanged
        (if present) from the ``IPGlasma`` directory to ``results``:

        - ``NcollList0.dat``
        - ``NgluonEstimators0.dat``
        - ``NpartList0.dat``
        - ``usedParameters0.dat`` (all parameters used, the IP-Glasma
          version and the random seed)

        After moving the files the temporary ``IPGlasma`` directory is
        removed.

        Args:
            event_dir (str): Path to the event-specific directory.
        """
        logging.info(f"[IPGlasma] Fetching output...")
        current_module_index = self.full_config.general.modules.index(
            "IPGlasma"
        )

        ipglasma_dir = os.path.join(event_dir, "IPGlasma")
        results_dir = os.path.join(event_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        # Determine the main output file from the output switches
        write_hydro = int(self.config.writeHydro) == 1
        write_tmunu = int(self.config.writeTmunu) == 1
        uses_kompost = "KoMPoST" in self.full_config.general.modules
        src_file = None

        # When both outputs exist, prefer Tmunu only if KoMPoST is active;
        # otherwise prefer epsilon-u-Hydro.
        if write_tmunu and write_hydro:
            check_order = (
                [self._find_tmunu, self._find_epsilon_u]
                if uses_kompost
                else [self._find_epsilon_u, self._find_tmunu]
            )
        elif write_tmunu:
            check_order = [self._find_tmunu]
        elif write_hydro:
            check_order = [self._find_epsilon_u]
        else:
            check_order = []

        for finder in check_order:
            src_file = finder(ipglasma_dir)
            if src_file is not None:
                break

        if src_file is None:
            logging.error(
                f"[IPGlasma] No output file found in {ipglasma_dir} "
                f"for writeHydro={self.config.writeHydro}, "
                f"writeTmunu={self.config.writeTmunu}."
            )
            raise FileNotFoundError(
                f"IP-Glasma output not found for writeHydro="
                f"{self.config.writeHydro}, writeTmunu={self.config.writeTmunu}"
            )

        dst_file = os.path.join(
            results_dir, f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dst_file)
        logging.info(f"[IPGlasma] Moved {src_file} to {dst_file}")

        # Additional files: keep original names
        extra_files = [
            "NcollList0.dat",
            "NgluonEstimators0.dat",
            "NpartList0.dat",
            "usedParameters0.dat",
        ]
        for fname in extra_files:
            src = os.path.join(ipglasma_dir, fname)
            if os.path.exists(src):
                dst = os.path.join(results_dir, fname)
                shutil.move(src, dst)
                logging.info(f"[IPGlasma] Moved {src} to {dst}")
            else:
                logging.warning(
                    f"[IPGlasma] Expected file {src} not found; skipping."
                )

        shutil.rmtree(ipglasma_dir)
        logging.info(f"[IPGlasma] Removed directory {ipglasma_dir}")
