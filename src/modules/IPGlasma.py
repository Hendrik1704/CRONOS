from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class IPGlasma(BaseModule):
    """IP-Glasma initial condition module for the CRONOS framework.

    Wraps the IP-Glasma code to generate fluctuating Glasma initial
    conditions for hydrodynamic evolution. This module prepares the
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
        - ``qs2Adj_vs_Tp_vs_Y_200.in`` (Qs table)
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

        ipglasma_qs2adj_path = os.path.join(
            self.project_root,
            "external_codes",
            "ipglasma",
            "qs2Adj_vs_Tp_vs_Y_200.in",
        )
        if os.path.exists(ipglasma_qs2adj_path):
            os.symlink(
                ipglasma_qs2adj_path,
                os.path.join(ipglasma_event_dir, "qs2Adj_vs_Tp_vs_Y_200.in"),
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
            f.write(f"mode {self.config.mode}\n")
            f.write(f"readMultFromFile {self.config.readMultFromFile}\n")
            f.write(f"size {self.config.size}\n")
            f.write(f"L {self.config.L}\n")
            f.write(f"Nc {self.config.Nc}\n")
            f.write(f"m {self.config.m}\n")
            f.write(f"rmax {self.config.rmax}\n")
            f.write(f"UVdamp {self.config.UVdamp}\n")
            f.write(f"Jacobianm {self.config.Jacobianm}\n")
            f.write(f"g {self.config.g}\n")
            f.write(f"SubNucleonParamType {self.config.SubNucleonParamType}\n")
            f.write(f"SubNucleonParamSet {self.config.SubNucleonParamSet}\n")
            f.write(f"BG {self.config.BG}\n")
            f.write(f"BGq {self.config.BGq}\n")
            f.write(f"BGqVar {self.config.BGqVar}\n")
            f.write(f"dqMin {self.config.dqMin}\n")
            f.write(f"omega {self.config.omega}\n")
            f.write(f"useSmoothNucleus {self.config.useSmoothNucleus}\n")
            f.write(
                f"useConstituentQuarkProton {self.config.useConstituentQuarkProton}\n"
            )
            f.write(f"NqFluc {self.config.NqFluc}\n")
            f.write(
                f"shiftConstituentQuarkProtonOrigin {self.config.shiftConstituentQuarkProtonOrigin}\n"
            )
            f.write(f"runningCoupling {self.config.runningCoupling}\n")
            f.write(f"muZero {self.config.muZero}\n")
            f.write(f"minimumQs2ST {self.config.minimumQs2ST}\n")
            f.write(f"setWSDeformParams {self.config.setWSDeformParams}\n")
            f.write(f"R_WS {self.config.R_WS}\n")
            f.write(f"a_WS {self.config.a_WS}\n")
            f.write(f"dR_np {self.config.dR_np}\n")
            f.write(f"da_np {self.config.da_np}\n")
            f.write(f"beta2 {self.config.beta2}\n")
            f.write(f"beta3 {self.config.beta3}\n")
            f.write(f"beta4 {self.config.beta4}\n")
            f.write(f"gamma {self.config.gamma}\n")
            f.write(f"force_dmin_flag {self.config.force_dmin_flag}\n")
            f.write(f"d_min {self.config.d_min}\n")
            f.write(f"c {self.config.c}\n")
            f.write(f"g2mu {self.config.g2mu}\n")
            f.write(f"useFatTails {self.config.useFatTails}\n")
            f.write(f"tDistNu {self.config.tDistNu}\n")
            f.write(f"smearQs {self.config.smearQs}\n")
            f.write(f"smearingWidth {self.config.smearingWidth}\n")
            f.write(f"protonAnisotropy {self.config.protonAnisotropy}\n")
            f.write(f"roots {self.config.roots}\n")
            f.write(f"usePseudoRapidity {self.config.usePseudoRapidity}\n")
            f.write(f"RapidityA {self.config.RapidityA}\n")
            f.write(f"RapidityB {self.config.RapidityB}\n")
            f.write(f"useFluctuatingx {self.config.useFluctuatingx}\n")
            f.write(
                f"xFromThisFactorTimesQs {self.config.xFromThisFactorTimesQs}\n"
            )
            f.write(f"useNucleus {self.config.useNucleus}\n")
            f.write(f"useGaussian {self.config.useGaussian}\n")
            f.write(
                f"nucleonPositionsFromFile {self.config.nucleonPositionsFromFile}\n"
            )
            f.write(
                f"NucleusQsTableFileName {self.config.NucleusQsTableFileName}\n"
            )
            f.write(f"QsmuRatio {self.config.QsmuRatio}\n")
            f.write(
                f"samplebFromLinearDistribution {self.config.samplebFromLinearDistribution}\n"
            )
            f.write(
                f"runWith0Min1Avg2MaxQs {self.config.runWith0Min1Avg2MaxQs}\n"
            )
            f.write(
                f"runWithThisFactorTimesQs {self.config.runWithThisFactorTimesQs}\n"
            )
            f.write(f"runWithLocalQs {self.config.runWithLocalQs}\n")
            f.write(f"runWithkt {self.config.runWithkt}\n")
            f.write(f"Ny {self.config.Ny}\n")
            f.write(f"useSeedList 0\n")
            if self.full_config.general.random_seed == -1:
                f.write(f"useTimeForSeed 1\n")
                f.write(f"seed 42\n")
            else:
                f.write(f"useTimeForSeed 0\n")
                f.write(f"seed {self.full_config.general.random_seed}\n")
            f.write(f"Projectile {self.config.Projectile}\n")
            f.write(f"Target {self.config.Target}\n")
            f.write(f"bmin {self.config.bmin}\n")
            f.write(f"bmax {self.config.bmax}\n")
            f.write(f"rotateReactionPlane {self.config.rotateReactionPlane}\n")
            f.write(f"lightNucleusOption {self.config.lightNucleusOption}\n")
            f.write(
                f"polariztionProjectile {self.config.polariztionProjectile}\n"
            )
            f.write(f"polariztionTarget {self.config.polariztionTarget}\n")
            f.write(
                f"polarizationProjectileJz {self.config.polarizationProjectileJz}\n"
            )
            f.write(
                f"polarizationTargetJz {self.config.polarizationTargetJz}\n"
            )
            f.write(f"useFixedNpart {self.config.useFixedNpart}\n")
            f.write(
                f"averageOverThisManyNuclei {self.config.averageOverThisManyNuclei}\n"
            )
            f.write(f"SigmaNN {self.config.SigmaNN}\n")
            f.write(f"gaussianWounding {self.config.gaussianWounding}\n")
            f.write(f"inverseQsForMaxTime {self.config.inverseQsForMaxTime}\n")
            f.write(f"maxtime {self.config.maxtime}\n")
            f.write(f"dtau {self.config.dtau}\n")
            f.write(f"LOutput {self.config.LOutput}\n")
            f.write(f"sizeOutput {self.config.sizeOutput}\n")
            f.write(
                f"computeGluonMultiplicity {self.config.computeGluonMultiplicity}\n"
            )
            f.write(f"etaSizeOutput {self.config.etaSizeOutput}\n")
            f.write(f"detaOutput {self.config.detaOutput}\n")
            f.write(f"writeOutputs {self.config.writeOutputs}\n")
            f.write(f"writeEvolution {self.config.writeEvolution}\n")
            f.write(
                f"readInitialWilsonLines {self.config.readInitialWilsonLines}\n"
            )
            f.write(f"writeWilsonLines {self.config.writeWilsonLines}\n")
            f.write(f"writeOutputsToHDF5 {self.config.writeOutputsToHDF5}\n")
            f.write(f"useJIMWLK {self.config.useJIMWLK}\n")
            f.write(f"mu0_jimwlk {self.config.mu0_jimwlk}\n")
            f.write(f"simpleLangevin {self.config.simpleLangevin}\n")
            f.write(f"alphas_jimwlk {self.config.alphas_jimwlk}\n")
            f.write(f"jimwlk_ic_x {self.config.jimwlk_ic_x}\n")
            f.write(f"x_projectile_jimwlk {self.config.x_projectile_jimwlk}\n")
            f.write(f"x_target_jimwlk {self.config.x_target_jimwlk}\n")
            f.write(f"Ds_jimwlk {self.config.Ds_jimwlk}\n")
            f.write(f"Lambda_QCD_jimwlk {self.config.Lambda_QCD_jimwlk}\n")
            f.write(f"m_jimwlk {self.config.m_jimwlk}\n")
            f.write(f"saveSnapshots {self.config.saveSnapshots}\n")
            snapshot = self.config.xSnapshotList
            if isinstance(snapshot, list):
                varStr = ",".join(f"{float(var):.7f}" for var in snapshot)
            else:
                varStr = f"{float(snapshot):.7f}"

            f.write(f"xSnapshotList {varStr}\n")
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

            run_kwargs = {"check": True}
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
            logging.error(f"[IPGlasma] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[IPGlasma] Execution finished.")

    def fetch_output(self, event_dir):
        """Collect IP-Glasma output files and clean up.

        Moves the main IP-Glasma energy-momentum tensor output
        (``epsilon-u-Hydro-TauHydro-0.dat``) to the event ``results``
        directory, renaming it to ``output_{module_index}.dat`` so that
        subsequent modules can locate it consistently.

        In addition, the following auxiliary files are moved unchanged
        (if present) from the ``IPGlasma`` directory to ``results``:

        - ``NcollList0.dat``
        - ``NgluonEstimators0.dat``
        - ``NpartList0.dat``

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

        # Main output file: rename to module-indexed filename
        src_file = os.path.join(ipglasma_dir, "epsilon-u-Hydro-TauHydro-0.dat")
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
