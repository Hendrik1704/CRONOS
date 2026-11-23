"""Input parameters of the iSS version that CRONOS builds.

iSS reads its parameter file with ParameterReader::getVal in src/*.cpp. It
stores every "name = value" line, ignores names it does not ask for, and
converts every value to a number, so a misspelled key would be ignored
without a warning. check_settings uses this list to reject such keys.

Generated from iSS ef5c307 (Hendrik1704/iSS branch cronos, see
external_codes/GetModulesFromGit.sh). Update it when the iSS pin changes;
tests/test_iss_parameters.py compares it with the iSS source.
"""

# Parameters iSS reads. iSS compares the names case-insensitively, CRONOS
# requires the spelling used in the iSS source.
ISS_PARAMETERS = frozenset(
    (
        "afterburner_type",
        "bin_dtau",
        "bin_dx",
        "bin_tau0",
        "bin_tau_max",
        "bin_x_max",
        "bin_x_min",
        "bulk_deltaf_kind",
        "calculate_dN_deta",
        "calculate_dN_dphi",
        "calculate_dN_dtau",
        "calculate_dN_dx",
        "calculate_dN_dxt",
        "calculate_polarization",
        "calculate_vn",
        "calculate_vn_to_order",
        "correlated_block_deta",
        "correlated_block_dtau",
        "correlated_block_dx",
        "correlated_sampling",
        "deltaf_max_ratio",
        "dN_dy_sampling_model",
        "dN_dy_sampling_para1",
        "grouping_particles",
        "grouping_tolerance",
        "hydro_Cartesian",
        "hydro_mode",
        "include_deltaf_bulk",
        "include_deltaf_diffusion",
        "include_deltaf_shear",
        "include_spectators",
        "JSechoLevel",
        "local_charge_conservation",
        "maximum_sampling_events",
        "MC_sampling",
        "minimum_emission_function_val",
        "number_of_particles_needed",
        "number_of_repeated_sampling",
        "OSCAR2013_position_jitter",
        "output_dN_dxtdy_4all",
        "output_samples_into_files",
        "perform_checks",
        "perform_decays",
        "polarizationRapType",
        "quantum_statistics",
        "randomSeed",
        "regulateEOS",
        "RegVisYield",
        "restrict_deltaf",
        "sample_pT_up_to",
        "sample_upto_desired_particle_number",
        "sample_y_minus_eta_s_range",
        "store_samples_in_memory",
        "turn_on_bulk",
        "turn_on_diff",
        "turn_on_rhob",
        "use_binary_format",
        "use_gzip_format",
        "use_historic_flow_output_format",
        "use_OSCAR2013",
        "use_OSCAR_format",
        "use_pos_dN_only",
        "y_LB",
        "y_RB",
    )
)

# Parameters CRONOS sets itself when it writes the iSS parameter file: the
# random seed and the output the next module reads (src/modules/iSS.py).
ISS_CRONOS_CONTROLLED_PARAMETERS = (
    "randomSeed",
    "use_OSCAR_format",
    "use_OSCAR2013",
    "OSCAR2013_position_jitter",
    "use_gzip_format",
    "use_binary_format",
    "perform_decays",
)

# Parameters iSS reads but sets itself before (from the MUSIC parameter file).
ISS_INTERNAL_PARAMETERS = ("iEoS_MUSIC",)
