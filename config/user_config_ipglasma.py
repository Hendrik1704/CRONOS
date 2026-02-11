# This file contains the user settings for the application.
# It overrides the main config parameters.

general = {
    # Logging level for the application
    # Possible choices:
    #   "INFO"  - Show key runtime messages
    #   "DEBUG" - Show all debug messages (verbose)
    #   "NONE"  - Suppress all log output
    "log_level": "DEBUG",
    "module_terminal_output": True,
    # List of modules to connect/load.
    "modules": [
        "IPGlasma",
        "KoMPoST",
        "entropy_matching",
        "MUSIC",
        "iSS",
        "SMASH",
        "afterburner_toolkit",
    ],
    "keep_particle_files": False,
}

IPGlasma = {
    'Projectile': "Au",
    'Target': "Au",
    'maxtime': 0.4,
    'dtau': 0.1,
    'LOutput': 30,
    'sizeOutput': 301,
}

KoMPoST = {
    "tIn": 0.4,
    "tOut": 1.0,
    "EtaOverS": 0.16,  # specific shear viscosity
    "EtaOverSTemperatureScale": 0.0,
    "NuEffective": 40.0,
    "EVOLUTION_MODE": 1,  # 0 for free-streaming, 1: for "KoMPoST" EKT evolution
    "ENERGY_PERTURBATIONS": 1,
    "MOMENTUM_PERTURBATIONS": 0,
    "DECOMPOSITION_METHOD": 1,
    "normFactor": 1.0,  # scaling of the input Tmunu
    "afm": 0.1,  # lattice spacing in fm
    "Ns": 301,  # number of grid points on a square lattice
    "xSTART": 0,  # The first grid point to include in the x direction
    "xEND": 300,  # The last grid point to include in the x direction
    "ySTART": 0,  # The first grid point to include in the y direction
    "yEND": 300,  # The last grid point to include in the y direction
}

entropy_matching = {
    "nu_eff": 40.0,  # effective degrees of freedom, should match with KoMPoST's NuEffective
}

MUSIC = {
    "EOS_to_use": 91,
}

iSS = {
    "hydro_mode": 1,  # mode for reading in freeze out information
    "afterburner_type": 2,  # 0: no afterburner, 1: UrQMD, 2: SMASH
    "sample_upto_desired_particle_number": 0,  # 1: flag to run sampling until desired
    # particle numbers is reached
    "number_of_repeated_sampling": 25000,  # number of repeated sampling
}

SMASH = {
    "No_Collisions": 1,  # 1: disable collisions, decays only
}

afterburner_toolkit = {}
