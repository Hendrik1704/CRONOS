from src.module_base import BaseModule, time_execution
import logging
import os
import shutil


class FromFileIC(BaseModule):
    def prepare_environment(self, event_dir):
        logging.info(f"[FromFileIC] Preparing environment in {event_dir}...")

    def prepare_input(self, event_dir):
        logging.info(f"[FromFileIC] Input file from {self.config.input_path}")

    @time_execution
    def run(self, event_dir):
        logging.info("[FromFileIC] No IC to run, profile saved...")

    def fetch_output(self, event_dir):
        logging.info("[FromFileIC] Data loaded successfully.")

        results_dir = os.path.join(event_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        from_file_ic_dir = os.path.join(event_dir, "from_file_IC")
        entries = os.listdir(from_file_ic_dir)
        if not entries:
            raise FileNotFoundError(f"No files found in {from_file_ic_dir}")

        src_file = os.path.join(from_file_ic_dir, entries[0])
        current_module_index = self.full_config.general.modules.index(
            "from_file_IC"
        )
        dst_file = os.path.join(
            results_dir, f"output_{current_module_index}.dat"
        )

        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "from_file_IC"))

        logging.info(f"[FromFileIC] Moved {src_file} to {dst_file}")
