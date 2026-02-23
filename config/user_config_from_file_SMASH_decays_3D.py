# This file contains the user settings for the application.
# It overrides the main config parameters.

general = {
    # Logging level for the application
    # Possible choices:
    #   "INFO"  - Show key runtime messages
    #   "DEBUG" - Show all debug messages (verbose)
    "log_level": "INFO",
    "module_terminal_output": False,
    # List of modules to connect/load.
    "modules": [
        "from_file_IC",
        "MUSIC",
        "iSS",
        "SMASH",
        "afterburner_toolkit",
    ],
    "keep_particle_files": False,
}

from_file_IC = {
    "input_path": "input_energy_momentum_tensors_3D/",
    "boost_invariant": 0,  # 0: no boost invariance, 1: boost invariance
    "Nx": 151,
    "Neta": 101,
    "dx": 0.1,
    "deta": 0.2,
}

MUSIC = {
    "hydro_mode": 2,  # mode for reading in freeze out information
    "boost_invariant": 0,  # 0: no boost invariance, 1: boost invariance
    "Initial_time_tau_0": 0.6,  # starting time of the hydrodynamic evolution (fm/c)
    "Initial_profile": 95,  # Read in initial profile from a file
    "Eta_grid_size": 20.0,  # spatial rapidity range
    "Grid_size_in_eta": 101,  # number of the grid points in spatial rapidity direction
    "X_grid_size_in_fm": 30.0,  # spatial range along x direction
    "Y_grid_size_in_fm": 30.0,  # spatial range along y direction
    "Grid_size_in_y": 151,  # number of the grid points in y direction
    "Grid_size_in_x": 151,  # number of the grid points in x direction
}

iSS = {
    "hydro_mode": 2,  # mode for reading in freeze out information
    "afterburner_type": 2,  # 0: no afterburner, 1: UrQMD, 2: SMASH
    "sample_upto_desired_particle_number": 0,  # 1: flag to run sampling until desired
    # particle numbers is reached
    "number_of_repeated_sampling": 25000,  # number of repeated sampling
}

SMASH = {
    "No_Collisions": 1,  # 1: disable collisions, decays only
}

afterburner_toolkit = {}
