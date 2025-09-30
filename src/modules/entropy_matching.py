from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class EntropyMatching(BaseModule):
    def prepare_environment(self, event_dir):
        logging.info(
            f"[EntropyMatching] Preparing environment in {event_dir}..."
        )
        entropy_eos_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "EOS"
        )
        if os.path.exists(entropy_eos_path):
            os.symlink(
                entropy_eos_path,
                os.path.join(event_dir, "entropy_matching", "EOS"),
            )
        else:
            logging.error(
                f"[EntropyMatching] Required directory {entropy_eos_path} does not exist."
            )

        entropy_matching_script_path = os.path.join(
            self.project_root, "utilities", "KoMPoST_to_MUSIC.py"
        )
        if os.path.exists(entropy_matching_script_path):
            os.symlink(
                entropy_matching_script_path,
                os.path.join(
                    event_dir, "entropy_matching", "KoMPoST_to_MUSIC.py"
                ),
            )
        else:
            logging.error(
                f"[EntropyMatching] Required executable {entropy_matching_script_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        logging.info(f"[EntropyMatching] Create input file...")
        current_module_index = self.full_config.general.modules.index(
            "entropy_matching"
        )
        pre_eq_evolved_path = os.path.join(
            event_dir, "results", f"output_{current_module_index-1}.dat"
        )
        if os.path.exists(pre_eq_evolved_path):
            os.symlink(
                pre_eq_evolved_path,
                os.path.join(
                    event_dir,
                    "entropy_matching",
                    f"output_{current_module_index-1}.dat",
                ),
            )
        else:
            logging.error(
                f"[EntropyMatching] Required file {pre_eq_evolved_path} does not exist."
            )
            exit(1)

    @time_execution
    def run(self, event_dir):
        logging.info("[EntropyMatching] run...")
        # run with python script.py type_of_matching nu_eff <eos_file> <filename_in> <filename_out>
        s_matching_dir = os.path.join(event_dir, "entropy_matching")
        s_matching_script = "KoMPoST_to_MUSIC.py"
        current_module_index = self.full_config.general.modules.index(
            "entropy_matching"
        )
        logging.info("[EntropyMatching] Running Entropy Matching...")

        cwd = os.getcwd()
        try:
            os.chdir(s_matching_dir)
            run_external_command(
                [
                    "python3",
                    s_matching_script,
                    "1",
                    str(self.config.nu_eff),
                    "./EOS/hotQCD/hrg_hotqcd_eos_SMASH_binary.dat",
                    f"output_{current_module_index-1}.dat",
                    f"output_{current_module_index}.dat",
                ],
                check=True,
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="entropy_matching",
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[EntropyMatching] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[EntropyMatching] Execution finished.")

    def fetch_output(self, event_dir):
        logging.info("[EntropyMatching] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index(
            "entropy_matching"
        )
        src_file = os.path.join(
            event_dir, "entropy_matching", f"output_{current_module_index}.dat"
        )
        dest_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dest_file)
        shutil.rmtree(os.path.join(event_dir, "entropy_matching"))
        logging.info(f"[EntropyMatching] Output moved to {dest_file}")
