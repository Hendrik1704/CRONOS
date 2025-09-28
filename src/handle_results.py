import os
import logging
from glob import glob
import h5py
import numpy as np


def check_an_event_is_good_afterburner_toolkit(folder):
    """This function checks the given event contains all required files"""
    required_files_list = [
        "particle_9999_vndata_eta_-0.5_0.5.dat",
        "particle_211_vndata_diff_y_-0.5_0.5.dat",
        "particle_321_vndata_diff_y_-0.5_0.5.dat",
        "particle_2212_vndata_diff_y_-0.5_0.5.dat",
    ]
    event_file_list = glob(os.path.join(folder, "*"))
    for ifile in required_files_list:
        filename = os.path.join(folder, ifile)
        if filename not in event_file_list:
            print(
                "event {} is bad, missing {} ...".format(folder, filename),
                flush=True,
            )
            return False
    return True


def check_if_event_is_good(config, event_dir_results_path, event_id):
    logging.info(f"Checking if event in {event_dir_results_path} is good...")

    if "afterburner_toolkit" in config.general.modules:
        logging.debug(
            "afterburner_toolkit module is used, checking event quality..."
        )
        spvn_dir = os.path.join(
            event_dir_results_path, f"spvn_results_{event_id}"
        )
        is_good = check_an_event_is_good_afterburner_toolkit(spvn_dir)
        if not is_good:
            logging.warning(
                f"Event in {event_dir_results_path} is marked as bad."
            )
            return False
        else:
            logging.info(
                f"Event in {event_dir_results_path} passed the quality check."
            )
            return True

    # Currently only checking for the afterburner_toolkit module
    logging.info(
        "No specific quality checks implemented for the current module configuration."
    )
    return True


def zip_into_hdf5(config, event_dir_results_path, event_id):
    logging.info(f"Zipping results in {event_dir_results_path} into HDF5...")
    is_good = check_if_event_is_good(config, event_dir_results_path, event_id)
    if not is_good:
        logging.warning(
            f"Event in {event_dir_results_path} is bad, skipping zipping into HDF5."
        )
        return
    spvn_dir = os.path.join(event_dir_results_path, f"spvn_results_{event_id}")
    # Pack all files in spvn_dir into a single HDF5 file named event_{event_id}.h5
    hdf5_filename = os.path.join(event_dir_results_path, f"event_{event_id}.h5")
    with h5py.File(hdf5_filename, "w") as hdf5_file:
        for root, _, files in os.walk(spvn_dir):
            for file in files:
                file_path = os.path.join(root, file)
                dataset_name = os.path.relpath(file_path, spvn_dir)

                # Try reading as text first
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = f.read()
                    # Store text data as variable-length UTF-8 string in HDF5
                    dt = h5py.string_dtype(encoding="utf-8")
                    hdf5_file.create_dataset(dataset_name, data=data, dtype=dt)
                except UnicodeDecodeError:
                    # Fallback: read as binary
                    with open(file_path, "rb") as f:
                        data = f.read()
                    # Store binary data as uint8 array
                    hdf5_file.create_dataset(
                        dataset_name, data=np.frombuffer(data, dtype="uint8")
                    )
                logging.debug(f"Added {file_path} as {dataset_name} in HDF5.")
    logging.info(f"Results zipped into {hdf5_filename} successfully.")


def handle_results(config, event_dir_results_path, event_id):
    save_intermediate = config.general.keep_intermediate_results
    logging.debug(
        f"Configuration 'keep_intermediate_results': {save_intermediate}"
    )

    # Check if the afterburner_toolkit module is used
    afterburner_toolkit_used = "afterburner_toolkit" in config.general.modules
    keep_particle_files = (
        config.general.keep_particle_files and afterburner_toolkit_used
    )
    logging.debug(
        f"Configuration 'keep_particle_files': {keep_particle_files}, afterburner_toolkit used: {afterburner_toolkit_used}"
    )

    # Find all filenames with output_*.dat pattern
    all_output_files = [
        f
        for f in os.listdir(event_dir_results_path)
        if f.startswith("output_") and f.endswith(".dat")
    ]
    logging.debug(f"All output files found: {all_output_files}")
    if not save_intermediate:
        # Determine the last module's output file
        if all_output_files:
            last_output_file = sorted(all_output_files)[-1]
            logging.info(
                f"Keeping only the last output file: {last_output_file}"
            )
        else:
            last_output_file = None
            logging.warning("No output files found to keep.")

        # Remove all other output files except the last one
        for f in all_output_files:
            if f != last_output_file:
                file_path = os.path.join(event_dir_results_path, f)
                os.remove(file_path)
                logging.debug(f"Removed intermediate file: {file_path}")

    if not keep_particle_files:
        # Remove also the last output_*.dat file if it exists
        for f in all_output_files:
            file_path = os.path.join(event_dir_results_path, f)
            if f == last_output_file:
                os.remove(file_path)
            logging.debug(f"Removed particle file: {file_path}")

    spvn_dir = os.path.join(event_dir_results_path, f"spvn_results_{event_id}")
    os.makedirs(spvn_dir, exist_ok=True)
    for f in os.listdir(event_dir_results_path):
        # Move all files to the spvn_results directory
        if f != f"spvn_results_{event_id}":
            src_path = os.path.join(event_dir_results_path, f)
            dst_path = os.path.join(spvn_dir, f)
            os.rename(src_path, dst_path)
            logging.debug(f"Moved {src_path} to {dst_path}")

    zip_into_hdf5(config, event_dir_results_path, event_id)
