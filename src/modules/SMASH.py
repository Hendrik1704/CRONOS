from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class SMASH(BaseModule):
    def prepare_environment(self, event_dir):
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
            num_events = int(result.stdout.strip())
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
