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
        "IPGlasma",
        "KoMPoST",
        "entropy_matching",
        "MUSIC",
        "iSS",
        "SMASH",
        "afterburner_toolkit",
    ],
    "number_of_jobs": 1,
    "number_events_per_job": 1,
    "keep_intermediate_results": False,
    "keep_particle_files": False,
    "random_seed": -1,  # set to -1 for random seed based on system time
}

IPGlasma = {
    "bmin": 0.,
    "bmax": 20.,
    "Projectile": "Pb",
    "Target": "Pb",
    "nucleonPositionsFromFile": 0,
    "roots": 5020.,
    "SigmaNN": 67.,
    "useConstituentQuarkProton": 3,   # 0: round proton; 3: fluctuating proton
    "L": 30.,
    "size": 800,
    "LOutput": 34.,
    "sizeOutput": 340,
    "writeOutputs": 4, # 1: initial conditions e, u^\mu, \pi^{\mu\nu} for hydro; 4: initial T^{\mu\nu} for KoMPoST
    "writeWilsonLines": 0,
    "maxtime": 0.2,
    "setWSDeformParams": 0,
    "SubNucleonParamType": 0,
    "SubNucleonParamSet": 0,
    "m": 0.51,
    "BG": 3.83,
    "BGq": 0.30,
    "omega": 1.0,
    "dqMin": 0.2582,
    "UVdamp": 0.0,
    "smearingWidth": 0.88,
    "QsmuRatio": 0.37,
    "useFluctuatingx": 0,
    "RapidityA": 0.0,
    "RapidityB": 0.0,
    "useJIMWLK": 1,
    "mu0_jimwlk": 0.28,
    "alphas_jimwlk": 0,
    "jimwlk_ic_x":  0.01,
    "x_projectile_jimwlk": 0.0001294820717,
    "x_target_jimwlk": 0.0001294820717,
    "Ds_jimwlk": 0.003,
    "Lambda_QCD_jimwlk": 0.0348,
    "m_jimwlk": 0.16,
    "saveSnapshots": 0,
}

KoMPoST = {
    "tIn": 0.2,
    "tOut": 1.0,
    "EtaOverS": 0.16,  # specific shear viscosity
    "EtaOverSTemperatureScale": 0.0,
    "NuEffective": 40.0,
    "EVOLUTION_MODE": 1,  # 0 for free-streaming, 1: for "KoMPoST" EKT evolution
    "ENERGY_PERTURBATIONS": 1,
    "MOMENTUM_PERTURBATIONS": 1,
    "DECOMPOSITION_METHOD": 1,
    "Regulator": "TwoPass",
    "normFactor": 1.0,  # scaling of the input Tmunu
    "afm": 0.1,  # lattice spacing in fm
    "Ns": 340,  # number of grid points on a square lattice
    "xSTART": 0,  # The first grid point to include in the x direction
    "xEND": 339,  # The last grid point to include in the x direction
    "ySTART": 0,  # The first grid point to include in the y direction
    "yEND": 339,  # The last grid point to include in the y direction
}

entropy_matching = {
    "nu_eff": 40.0,
    "matching_type": 0,  # 0: energy matching, 1: entropy matching
}

MUSIC = {
    "beastMode": 1,
    "Initial_profile": 94,
    "s_factor": 1.0,
    "preEqVisFactor": 1.0,
    "Initial_time_tau_0": 1.0,
    "Delta_Tau": 0.005,
    "boost_invariant":  1,
    "Include_Shear_Visc_Yes_1_No_0": 1,
    "T_dependent_Shear_to_S_ratio": 1,
    "shear_viscosity_3_eta_over_s_T_kink_in_GeV": 0.18,
    "shear_viscosity_3_eta_over_s_low_T_slope_in_GeV": -4.,
    "shear_viscosity_3_eta_over_s_high_T_slope_in_GeV": 0.,
    "shear_viscosity_3_eta_over_s_at_kink": 0.12,
    "Include_Bulk_Visc_Yes_1_No_0": 1,
    "T_dependent_zeta_over_s": 10,
    "bulk_viscosity_10_max": 0.123,
    "bulk_viscosity_10_width_high": 0.08,
    "bulk_viscosity_10_width_low": 0.03,
    "bulk_viscosity_10_T_peak": 0.18,
    "T_dependent_Shear_to_S_ratio": 3,
    "use_eps_for_freeze_out": 1,
    "eps_switch": 0.15,
}

iSS = {
    "hydro_mode": 1,  # mode for reading in freeze out information
    "afterburner_type": 2,  # 0: no afterburner, 1: UrQMD, 2: SMASH
    "bulk_deltaf_kind": 20,
    "sample_upto_desired_particle_number": 1,  # 1: flag to run sampling until desired
    # particle number is reached
}

SMASH = {}

afterburner_toolkit = {
    "ecoOutput": 0,
    "analyze_flow": 4,
    "npT": 20,
    "n_rap": 71,
}
