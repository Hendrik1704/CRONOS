# This file contains the user settings for the application.
# It overrides the main config parameters.

general = {
    # Logging level for the application
    # Possible choices:
    #   "INFO"  - Show key runtime messages
    #   "DEBUG" - Show all debug messages (verbose)
    #   "NONE"  - Suppress all log output
    "log_level": "INFO",
    "module_terminal_output": False,
    # List of modules to connect/load.
    "modules": [
        "from_file_IC",
        "MUSIC",
        "iSS",
        "afterburner_toolkit",
    ],
    "keep_particle_files": False,
}

from_file_IC = {
    "input_path": "input_energy_momentum_tensors/",
    "boost_invariant": 0,  # 0: no boost invariance, 1: boost invariance
    "Nx": 151,
    "Neta": 71,
    "dx": 0.1,
    "deta": 0.2,
}

MUSIC = {
    "Initial_profile": 95,
    "boost_invariant": 0,
    "Initial_time_tau_0": 0.6,
    "Eta_grid_size": 14.0,
    "Grid_size_in_eta": 71,
    "X_grid_size_in_fm": 15.0,
    "Y_grid_size_in_fm": 15.0,
    "Grid_size_in_x": 151,
    "Grid_size_in_y": 151,
    "EOS_to_use": 9,
    "Include_Bulk_Visc_Yes_1_No_0": 1,
    "T_dependent_zeta_over_s": 1,
    "freeze_Ncell_x_step": 2,
    "freeze_Ncell_y_step": 2,
}

iSS = {
    "hydro_mode": 2,  # mode for reading in freeze out information
    "afterburner_type": 0,  # 0: no afterburner, 1: UrQMD, 2: SMASH
    # automatic binary file and 3d input read mode in afternurner toolkit
    "sample_upto_desired_particle_number": 0,  # 1: flag to run sampling until desired
    # particle numbers is reached
    "number_of_repeated_sampling": 100,  # number of repeated sampling
    "perform_decays": 1,
}

afterburner_toolkit = {}
