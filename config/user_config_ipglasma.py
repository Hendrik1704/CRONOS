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
    "bMin": 0.,
    "bMax": 20.,
    "projectile": "Pb",
    "target": "Pb",
    "nucleonPositionsFromFile": 0,
    "sqrtS": 5020.,
    "sigmaNN": 67.,
    "nucleonModel": "hotspots",   # gaussian: round proton; hotspots: fluctuating proton
    "Nq": 3,  # number of hot spots
    "L": 30.,
    "size": 800,
    "LOutput": 34.,
    "sizeOutput": 340,
    "writeHydro": 1,  # initial conditions e, u^\mu, \pi^{\mu\nu} for hydro
    "writeTmunu": 0,  # initial T^{\mu\nu} for KoMPoST
    "writeWilsonLines": 0,
    "maxTime": 0.4,
    "useInputWSParams": 0,
    "subNucleonParamType": 0,
    "subNucleonParamSet": 0,
    "m": 0.51,
    "BG": 3.83,
    "BGq": 0.30,
    "omega": 1.0,
    "dqMin": 0.2582,
    "UVDamp": 0.0,
    "smearingWidth": 0.88,
    "QsMuRatio": 0.37,
    "useFluctuatingX": 0,
    "useJIMWLK": 1,
    "jimwlkMu0": 0.28,
    "jimwlkAlphaS": 0,
    "jimwlkInitialX":  0.01,
    "projectileX": 0.0001294820717,  # JIMWLK evolves the projectile to this x
    "targetX": 0.0001294820717,  # JIMWLK evolves the target to this x
    "jimwlkDs": 0.003,
    "jimwlkLambdaQCD": 0.0348,
    "jimwlkMass": 0.16,
    "jimwlkSaveSnapshots": 0,
}

MUSIC = {
    "beastMode": 1,
    "Initial_profile": 9,
    "s_factor": 0.0335,
    "preEqVisFactor": 1.0,
    "Initial_time_tau_0": 0.4,
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
    "ecoOutput": 1,
    "analyze_flow": 4,
    "npT": 20,
    "n_rap": 71,
}
