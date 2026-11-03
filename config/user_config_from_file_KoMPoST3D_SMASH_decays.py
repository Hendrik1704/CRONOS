# This file contains the user settings for the application.
# It overrides the main config parameters.

general = {
    # Logging level for the application
    # Possible choices:
    #   "INFO"  - Show key runtime messages
    #   "DEBUG" - Show all debug messages (verbose)
    "log_level": "INFO",
    "module_terminal_output": False,
    # KoMPoST-3D keeps its response tables in memory (~9 GB per event)
    "memory_threshold_mb": 12288,
    # List of modules to connect/load.
    "modules": [
        "from_file_IC",
        "KoMPoST3D",
        "entropy_matching",
        "MUSIC",
        "iSS",
        "SMASH",
        "afterburner_toolkit",
    ],
    "keep_particle_files": False,
}

# The input files must already be in the KoMPoST-3D T^munu format
# (e.g. converted with a separate script) and named like Tmunu1_*.dat
from_file_IC = {
    "input_path": "input_energy_momentum_tensors_KoMPoST3D/",
    "boost_invariant": 0,  # 0: no boost invariance, 1: boost invariance
}

KoMPoST3D = {
    "tIn": 0.2,
    "tOut": 0.8,
    "EtaOverS": 0.16,  # specific shear viscosity
    "NuEffective": 40.0,
    "normFactor": 1.0,  # scaling of the input tau*Tmunu
    "afm": 0.21,  # transverse lattice spacing in fm
    "deta": 0.25,  # lattice spacing in spatial rapidity
    "Ns": 128,  # number of grid points in x and y
    "Neta": 65,  # number of grid points in spatial rapidity
    "xEND": 127,  # The last grid point to include in the x direction
    "yEND": 127,  # The last grid point to include in the y direction
    "etaEND": 64,  # The last grid point to include in the eta direction
}

entropy_matching = {
    "nu_eff": 40.0,  # effective degrees of freedom, should match with KoMPoST3D's NuEffective
}

# MUSIC only reads Nx, Ny, dx and dy from the KoMPoST-3D output header. The eta grid
# and the grid extent must match KoMPoST3D (checked by check_settings):
# Grid_size_in_eta = Neta, Eta_grid_size = (Neta-1)*deta, X/Y_grid_size_in_fm = (Ns-1)*afm
MUSIC = {
    "hydro_mode": 2,  # mode for reading in freeze out information
    "boost_invariant": 0,  # 0: no boost invariance, 1: boost invariance
    "Initial_profile": 95,  # full T^munu and bulk (3+1D) from file
    "Initial_time_tau_0": 0.8,  # must match KoMPoST3D tOut (fm/c)
    "Eta_grid_size": 16.0,  # spatial rapidity range
    "Grid_size_in_eta": 65,  # number of the grid points in spatial rapidity direction
    "X_grid_size_in_fm": 26.67,  # spatial range along x direction
    "Y_grid_size_in_fm": 26.67,  # spatial range along y direction
    "Grid_size_in_y": 128,  # number of the grid points in y direction
    "Grid_size_in_x": 128,  # number of the grid points in x direction
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
