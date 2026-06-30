"""CRONOS Simulation Result Processing and HDF5 Compression Module.

This module handles post-simulation result validation, organization, and compression
for CRONOS heavy-ion collision simulation outputs. It ensures data quality through
event validation, manages intermediate file cleanup based on configuration, and
compresses results into efficient HDF5 format for long-term storage and analysis.

Author: CRONOS Development Team
Requires: h5py, numpy for HDF5 operations and data handling
"""

import os
import logging
from glob import glob
import h5py
import numpy as np


def check_an_event_is_good_afterburner_toolkit(folder):
    """Validate afterburner_toolkit flow analysis output completeness.

    Performs quality assurance check for afterburner_toolkit module output by
    verifying presence of required flow analysis files for heavy-ion collision analysis.

    Args:
        folder (str): Path to directory containing afterburner_toolkit output files

    Returns:
        bool: True if all required files present, False if any missing
    """
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
    """Orchestrate event quality validation based on active physics modules.

    Performs comprehensive event validation by dispatching to module-specific
    quality check functions based on the CRONOS configuration.

    Args:
        config (Configuration): CRONOS configuration with active modules
        event_dir_results_path (str): Path to event results directory
        event_id (str): Event identifier for logging

    Returns:
        bool: True if event passed all quality checks, False otherwise
    """
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
    """Compress event results into HDF5 format with automatic content detection.

    Performs comprehensive HDF5 compression of CRONOS simulation results with
    intelligent text/binary content detection and preservation.

    Args:
        config (Configuration): CRONOS configuration object
        event_dir_results_path (str): Path to event results directory
        event_id (str): Event identifier for output file naming

    Side Effects:
        - Creates event_{event_id}.h5 in event_dir_results_path
        - Logs compression progress and dataset creation details
    """
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
        group_temp = hdf5_file.create_group(f"event_{event_id}")

        file_list = glob.glob(os.path.join(spvn_dir, "*"))

        for file_path in file_list:
            file_name = os.path.basename(file_path)

            try:
                data = np.genfromtxt(file_path, dtype=np.float32)

                dset = group_temp.create_dataset(
                    file_name,
                    data=data,
                    compression="gzip",
                    compression_opts=9
                )

                # save header if exists
                with open(file_path, "r") as f:
                    first_line = f.readline().strip()

                if first_line.startswith("#"):
                    dset.attrs["header"] = np.bytes_(first_line)

                continue

            except Exception:
                pass  # fallback below

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                dt = h5py.string_dtype(encoding="utf-8")

                group_temp.create_dataset(
                    file_name,
                    data=text,
                    dtype=dt
                )

            except UnicodeDecodeError:
                # final fallback: binary
                with open(file_path, "rb") as f:
                    data = f.read()

                group_temp.create_dataset(
                    file_name,
                    data=np.frombuffer(data, dtype=np.uint8)
                )

            logging.debug(f"Added {file_path} as {file_name} in HDF5.")
    logging.info(f"Results zipped into {hdf5_filename} successfully.")


def handle_results(config, event_dir_results_path, event_id):
    """Orchestrate complete result processing workflow with configurable file management.

    Main entry point for CRONOS result processing that manages the complete
    post-simulation workflow including file cleanup, organization, validation,
    and HDF5 compression based on user configuration settings.

    Args:
        config (Configuration): CRONOS configuration with file retention settings
        event_dir_results_path (str): Path to event results directory
        event_id (str): Event identifier for directory naming and logging

    Side Effects:
        - Removes intermediate files based on configuration
        - Creates spvn_results_{event_id}/ subdirectory
        - Creates event_{event_id}.h5 compressed archive
        - Provides detailed logging of all operations
    """
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
