from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class KoMPoST(BaseModule):
    def prepare_environment(self, event_dir):
        logging.info(f"[KoMPoST] Preparing environment in {event_dir}...")
        kompost_ekt_path = os.path.join(
            self.project_root, "external_codes", "KoMPoST", "EKT"
        )
        if os.path.exists(kompost_ekt_path):
            os.symlink(
                kompost_ekt_path, os.path.join(event_dir, "KoMPoST", "EKT")
            )
        else:
            logging.error(
                f"[KoMPoST] Required directory {kompost_ekt_path} does not exist."
            )
            exit(1)

        kompost_exe_path = os.path.join(
            self.project_root, "external_codes", "KoMPoST", "KoMPoST.exe"
        )
        if os.path.exists(kompost_exe_path):
            os.symlink(
                kompost_exe_path,
                os.path.join(event_dir, "KoMPoST", "KoMPoST.exe"),
            )
        else:
            logging.error(
                f"[KoMPoST] Required executable {kompost_exe_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        logging.info(f"[KoMPoST] Create input file...")
        current_module_index = self.full_config.general.modules.index("KoMPoST")
        self.config.InputFile = f"output_{current_module_index-1}.dat"
        self.config.OutputFileTag = f"output_{current_module_index}"

        kompost_dir = os.path.join(event_dir, "KoMPoST")
        if not os.path.exists(kompost_dir):
            logging.error(
                f"[KoMPoST] Required directory {kompost_dir} does not exist."
            )
            exit(1)
        ini_file = os.path.join(kompost_dir, "parameters_KoMPoST.ini")

        with open(ini_file, "w") as f:
            # KoMPoSTInputs
            f.write("[KoMPoSTInputs]\n")
            f.write(f"tIn={self.config.tIn};\n\n")
            f.write(f"tOut = {self.config.tOut};\n\n")
            f.write(f"InputFile={self.config.InputFile}\n")
            f.write(f"OutputFileTag={self.config.OutputFileTag}\n\n")

            # KoMPoSTParameters
            f.write("[KoMPoSTParameters]\n")
            f.write(f"EtaOverS = {self.config.EtaOverS}\n")
            f.write(
                f"EtaOverSTemperatureScale = {self.config.EtaOverSTemperatureScale}\n"
            )
            f.write(f"# Effective number of degrees of freedom\n")
            f.write(f"NuEffective = {self.config.NuEffective}\n")
            f.write(f'# 0 for free-streaming, 1 for "KoMPoST" EKT evolution\n')
            f.write(f"EVOLUTION_MODE={self.config.EVOLUTION_MODE}\n\n")
            f.write(f"# 0 or 1\n")
            f.write(
                f"ENERGY_PERTURBATIONS={self.config.ENERGY_PERTURBATIONS}\n\n"
            )
            f.write(f"# 0 or 1\n")
            f.write(
                f"MOMENTUM_PERTURBATIONS={self.config.MOMENTUM_PERTURBATIONS}\n\n"
            )
            f.write(
                f"DECOMPOSITION_METHOD={self.config.DECOMPOSITION_METHOD}\n\n"
            )
            f.write(f"Regulator={self.config.Regulator}\n\n")

            # EventInput
            f.write("[EventInput]\n")
            f.write(
                f"# scaling parameter for the input energy momentum tensor\n"
            )
            f.write(f"normFactor = {self.config.normFactor}\n")
            f.write(f"# lattice spacing in fm\n")
            f.write(f"afm = {self.config.afm}\n")
            f.write(f"# number of grid points on a square lattice\n")
            f.write(f"Ns={self.config.Ns};\n\n")
            f.write(f"# The first grid point to include in the x direction\n")
            f.write(f"xSTART={self.config.xSTART};\n")
            f.write(f"# The last grid point to include in the x direction\n")
            f.write(f"xEND={self.config.xEND};\n\n")
            f.write(f"#The first grid point to include in the y direction\n")
            f.write(f"ySTART={self.config.ySTART};\n")
            f.write(f"#The last grid point to include in the y direction\n")
            f.write(f"yEND={self.config.yEND};\n")
        logging.info("[KoMPoST] Input file created successfully.")

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
        finally:
            os.chdir(cwd)

        logging.info("[KoMPoST] Execution finished.")

    def fetch_output(self, event_dir):
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
