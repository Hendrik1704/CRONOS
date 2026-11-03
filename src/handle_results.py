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

    Numeric text files are stored as float64 arrays. The first comment line
    ('#') of such a file is stored in the dataset attribute 'header'; if the
    file has more than one comment line, all of them (joined by newlines)
    are additionally stored in the attribute 'full_header' (only the leading
    block of comment lines).

    Returns:
        bool: True if the HDF5 file was written, False if the event failed
            the quality check and no HDF5 file was written.

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
        return False
    spvn_dir = os.path.join(event_dir_results_path, f"spvn_results_{event_id}")
    # Pack all files in spvn_dir into a single HDF5 file named event_{event_id}.h5
    hdf5_filename = os.path.join(event_dir_results_path, f"event_{event_id}.h5")
    with h5py.File(hdf5_filename, "w") as hdf5_file:
        group_temp = hdf5_file.create_group(f"event_{event_id}")

        file_list = glob(os.path.join(spvn_dir, "*"))

        for file_path in file_list:
            file_name = os.path.basename(file_path)

            try:
                data = np.genfromtxt(file_path, dtype=np.float64)

                dset = group_temp.create_dataset(
                    file_name,
                    data=data,
                    compression="gzip",
                    compression_opts=9
                )

                # save the header lines if they exist
                # Only the leading comment block: files like the SMASH
                # particle list have comment lines for every event, which
                # would exceed the 64 kB attribute size limit of HDF5
                header_lines = []
                with open(file_path, "r") as f:
                    for line in f:
                        if not line.startswith("#"):
                            break
                        header_lines.append(line.strip())

                if data.ndim == 1:
                    # genfromtxt gives 1-D arrays for one row and for one
                    # column; keep which one it was for the extraction
                    with open(file_path, "r") as f:
                        n_rows = sum(
                            1
                            for line in f
                            if line.strip() and not line.startswith("#")
                        )
                    dset.attrs["table_layout"] = np.bytes_(
                        "row" if n_rows == 1 else "column"
                    )

                if header_lines:
                    dset.attrs["header"] = np.bytes_(header_lines[0])
                if len(header_lines) > 1:
                    dset.attrs["full_header"] = np.bytes_(
                        "\n".join(header_lines)
                    )

                continue

            except Exception:
                # fallback below; drop a dataset created before the failure
                if file_name in group_temp:
                    del group_temp[file_name]

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
    return True


def _output_file_index(file_name):
    """Return the module index N of an 'output_N.dat' file name."""
    try:
        return int(file_name[len("output_") : -len(".dat")])
    except ValueError:
        return -1


def handle_results(config, event_dir_results_path, event_id):
    """Orchestrate complete result processing workflow with configurable file management.

    Main entry point for CRONOS result processing that manages the complete
    post-simulation workflow including file cleanup, organization, validation,
    and HDF5 compression based on user configuration settings.

    File retention:
        - keep_intermediate_results=False: only the last output_N.dat file
          is kept, all other output_*.dat files are removed.
        - If the afterburner_toolkit module is used, the last output file is
          the particle file it analyses (output of the module before it). It
          is removed unless keep_particle_files is True. Without
          afterburner_toolkit, keep_particle_files has no effect and the last
          output file is always kept.

    The function can be called again on a results directory where a
    previous call was interrupted or failed (files already moved into
    spvn_results_{event_id}/, files already removed, HDF5 file written).

    Args:
        config (Configuration): CRONOS configuration with file retention settings
        event_dir_results_path (str): Path to event results directory
        event_id (str): Event identifier for directory naming and logging

    Returns:
        bool: True if event_{event_id}.h5 was written, False if the event
            failed the quality check (no HDF5 file is written in that case).

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
    modules = list(config.general.modules)
    afterburner_toolkit_used = "afterburner_toolkit" in modules
    keep_particle_files = config.general.keep_particle_files
    logging.debug(
        f"Configuration 'keep_particle_files': {keep_particle_files}, afterburner_toolkit used: {afterburner_toolkit_used}"
    )

    spvn_dir_name = f"spvn_results_{event_id}"
    spvn_dir = os.path.join(event_dir_results_path, spvn_dir_name)
    hdf5_name = f"event_{event_id}.h5"

    # Find all filenames with output_*.dat pattern, also those already moved
    # into the spvn_results directory by a previous (interrupted) call
    def is_output_file(f):
        return f.startswith("output_") and f.endswith(".dat")

    all_output_files = [
        f for f in os.listdir(event_dir_results_path) if is_output_file(f)
    ]
    if os.path.isdir(spvn_dir):
        all_output_files += [
            f
            for f in os.listdir(spvn_dir)
            if is_output_file(f) and f not in all_output_files
        ]
    logging.debug(f"All output files found: {all_output_files}")

    # Determine the last module's output file
    if afterburner_toolkit_used:
        # The particle file analysed by the afterburner_toolkit
        particle_file_index = modules.index("afterburner_toolkit") - 1
        last_output_file = f"output_{particle_file_index}.dat"
    else:
        last_output_file = (
            max(all_output_files, key=_output_file_index)
            if all_output_files
            else None
        )

    files_to_remove = []
    if not save_intermediate:
        if last_output_file:
            logging.info(
                f"Keeping only the last output file: {last_output_file}"
            )
        else:
            logging.warning("No output files found to keep.")
        files_to_remove += [
            f for f in all_output_files if f != last_output_file
        ]

    if afterburner_toolkit_used and not keep_particle_files:
        # Remove also the particle file analysed by the afterburner_toolkit
        files_to_remove.append(last_output_file)

    for f in files_to_remove:
        for directory in (event_dir_results_path, spvn_dir):
            file_path = os.path.join(directory, f)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.debug(f"Removed output file: {file_path}")

    os.makedirs(spvn_dir, exist_ok=True)
    for f in os.listdir(event_dir_results_path):
        # Move all files to the spvn_results directory (except an HDF5
        # file left over from a previous, interrupted call)
        if f not in (spvn_dir_name, hdf5_name):
            src_path = os.path.join(event_dir_results_path, f)
            dst_path = os.path.join(spvn_dir, f)
            os.rename(src_path, dst_path)
            logging.debug(f"Moved {src_path} to {dst_path}")

    return zip_into_hdf5(config, event_dir_results_path, event_id)
