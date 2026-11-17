import logging
import math

# MUSIC Initial_profile values that read the initial state from a file.
# 9 and 91-94 read one transverse slice (boost-invariant), 95 reads a (3+1)D
# profile (MUSIC init.cpp).
MUSIC_2D_FILE_PROFILES = (9, 91, 92, 93, 94)
MUSIC_3D_FILE_PROFILES = (95,)

# iSS afterburner types (iSS readindata.cpp)
ISS_AFTERBURNER_PDG_DECAY = 0
ISS_AFTERBURNER_URQMD = 1
ISS_AFTERBURNER_SMASH = 2


def iss_effective_afterburner_type(music_eos, iss_afterburner_type):
    """Return the afterburner type iSS actually uses.

    iSS reads EOS_to_use from the MUSIC parameter file and overrides its
    afterburner_type for EOS 9 (UrQMD) and EOS 91 (SMASH). The afterburner
    type selects the particle list, the decay table, and whether iSS performs
    resonance decays (not for SMASH).
    """
    if music_eos == 9:
        return ISS_AFTERBURNER_URQMD
    if music_eos == 91:
        return ISS_AFTERBURNER_SMASH
    if iss_afterburner_type in (ISS_AFTERBURNER_URQMD, ISS_AFTERBURNER_SMASH):
        return iss_afterburner_type
    return ISS_AFTERBURNER_PDG_DECAY


def check_settings(config):
    """
    Check the configuration settings for consistency and validity.

    Parameters:
    -----------
    config : Configuration
        The configuration object containing all settings.

    Returns:
    --------
    bool
        True if all settings are valid, False otherwise.
    """
    valid = True
    if not hasattr(config, "general"):
        logging.error("Configuration missing 'general' section.")
        valid = False

    # Ensure we have a non-empty list of active modules
    if (
        not hasattr(config.general, "modules")
        or len(config.general.modules) == 0
    ):
        logging.error("No modules specified in configuration.")
        valid = False
    # Active modules list (may be empty if above check failed)
    active_modules = getattr(config.general, "modules", [])

    def active(module_name):
        return module_name in active_modules and hasattr(config, module_name)

    # Only perform consistency checks for modules that are actually enabled
    if active("from_file_IC") and active("MUSIC"):
        # Check that the "boost_invariant" settings match between from_file_IC and MUSIC
        if config.from_file_IC.boost_invariant != config.MUSIC.boost_invariant:
            logging.error(
                "Mismatch in 'boost_invariant' between from_file_IC and MUSIC modules."
            )
            valid = False

    if active("MUSIC"):
        music_boost_invariant = config.MUSIC.boost_invariant != 0
        # The file profiles are either one transverse slice or a (3+1)D profile
        profile = config.MUSIC.Initial_profile
        if profile in MUSIC_2D_FILE_PROFILES and not music_boost_invariant:
            logging.error(
                f"MUSIC Initial_profile {profile} reads a boost-invariant "
                "profile, but MUSIC boost_invariant is 0."
            )
            valid = False
        if profile in MUSIC_3D_FILE_PROFILES and music_boost_invariant:
            logging.error(
                f"MUSIC Initial_profile {profile} reads a (3+1)D profile, "
                "but MUSIC boost_invariant is 1."
            )
            valid = False

        # With use_eps_for_freeze_out, MUSIC writes one surface per isotherm,
        # but the next module (iSS) samples a single surface
        if (
            config.MUSIC.use_eps_for_freeze_out != 0
            and config.MUSIC.N_freeze_out != 1
        ):
            logging.error(
                "MUSIC N_freeze_out must be 1, only one freeze-out surface "
                "can be passed on to iSS."
            )
            valid = False

    # MUSIC takes its start time only from Initial_time_tau_0 (the tau in the
    # header of the KoMPoST output file is ignored)
    if (
        active("KoMPoST")
        and active("MUSIC")
        and active_modules.index("KoMPoST") < active_modules.index("MUSIC")
        and not math.isclose(
            config.MUSIC.Initial_time_tau_0, config.KoMPoST.tOut
        )
    ):
        logging.error(
            f"MUSIC Initial_time_tau_0 ({config.MUSIC.Initial_time_tau_0}) "
            f"must equal KoMPoST tOut ({config.KoMPoST.tOut})."
        )
        valid = False

    if active("MUSIC") and active("iSS"):
        # iSS hydro_mode 1 reads a boost-invariant MUSIC surface,
        # hydro_mode 2 a (3+1)D MUSIC surface
        expected_hydro_mode = 1 if config.MUSIC.boost_invariant != 0 else 2
        if config.iSS.hydro_mode != expected_hydro_mode:
            logging.error(
                f"Incompatible settings: MUSIC boost_invariant "
                f"{config.MUSIC.boost_invariant} requires iSS hydro_mode "
                f"{expected_hydro_mode}, got {config.iSS.hydro_mode}."
            )
            valid = False

        afterburner_type = iss_effective_afterburner_type(
            config.MUSIC.EOS_to_use, config.iSS.afterburner_type
        )
        if "SMASH" in active_modules:
            # The SMASH input converter uses the SMASH particle list
            if afterburner_type != ISS_AFTERBURNER_SMASH:
                logging.error(
                    "With SMASH, iSS must sample SMASH hadrons: set MUSIC "
                    "EOS_to_use to 91, or iSS afterburner_type to 2 with a "
                    "MUSIC EOS_to_use other than 9."
                )
                valid = False
        elif afterburner_type == ISS_AFTERBURNER_SMASH:
            # iSS skips resonance decays for the SMASH afterburner type
            logging.error(
                "Without SMASH, iSS would skip the resonance decays: MUSIC "
                "EOS_to_use 91 or iSS afterburner_type 2 (with a MUSIC "
                "EOS_to_use other than 9) select the SMASH afterburner type."
            )
            valid = False

    if "KoMPoST3D" in active_modules and hasattr(config, "KoMPoST3D"):
        kompost3d = config.KoMPoST3D
        if "KoMPoST" in active_modules:
            logging.error("KoMPoST and KoMPoST3D cannot be used together.")
            valid = False
        # The input must already be in the KoMPoST-3D T^munu format
        kompost3d_index = active_modules.index("KoMPoST3D")
        if (
            kompost3d_index == 0
            or active_modules[kompost3d_index - 1] != "from_file_IC"
        ):
            logging.error("KoMPoST3D must directly follow from_file_IC.")
            valid = False
        # KoMPoST-3D only implements the kinetic theory energy perturbations
        if kompost3d.EVOLUTION_MODE != 1:
            logging.error("KoMPoST3D only supports EVOLUTION_MODE = 1.")
            valid = False
        if kompost3d.MOMENTUM_PERTURBATIONS != 0:
            logging.error("KoMPoST3D only supports MOMENTUM_PERTURBATIONS = 0.")
            valid = False
        # KoMPoST-3D writes the full grid but only evolves the cells inside
        # the bounds, and the bounds index the grid without range checks
        for start, end, size in [
            ("xSTART", "xEND", "Ns"),
            ("ySTART", "yEND", "Ns"),
            ("etaSTART", "etaEND", "Neta"),
        ]:
            first, last, n = kompost3d[start], kompost3d[end], kompost3d[size]
            if not 0 <= first <= last <= n - 1:
                logging.error(
                    f"KoMPoST3D requires 0 <= {start} <= {end} <= {size} - 1."
                )
                valid = False
            elif first != 0 or last != n - 1:
                logging.warning(
                    f"KoMPoST3D only evolves {start}..{end} of the {n} grid "
                    "points, the other cells of the output are zero."
                )
        # One event keeps the response tables in memory; the threshold is
        # also the memory requested from SLURM
        if config.general.memory_threshold_mb < 10240:
            logging.warning(
                "KoMPoST3D needs ~9 GB of memory per event, but "
                "'memory_threshold_mb' is "
                f"{config.general.memory_threshold_mb} MB."
            )
        if (
            "from_file_IC" in active_modules
            and hasattr(config, "from_file_IC")
            and config.from_file_IC.boost_invariant != 0
        ):
            logging.error(
                "KoMPoST3D requires 'boost_invariant' = 0 in from_file_IC."
            )
            valid = False
        if "MUSIC" in active_modules and hasattr(config, "MUSIC"):
            music = config.MUSIC
            if music.boost_invariant != 0:
                logging.error(
                    "KoMPoST3D requires 'boost_invariant' = 0 in MUSIC."
                )
                valid = False
            if music.Initial_profile != 95:
                logging.error(
                    "KoMPoST3D output requires 'Initial_profile' = 95 in MUSIC."
                )
                valid = False
            if not math.isclose(music.Initial_time_tau_0, kompost3d.tOut):
                logging.error(
                    "Mismatch between KoMPoST3D 'tOut' and MUSIC 'Initial_time_tau_0'."
                )
                valid = False
            # MUSIC only takes Nx, Ny, dx and dy from the file header. The eta
            # grid and the extent of the grid (used for the positions) come
            # from the MUSIC parameters and must match the KoMPoST3D grid.
            if music.Grid_size_in_eta != kompost3d.Neta or not math.isclose(
                music.Eta_grid_size, (kompost3d.Neta - 1) * kompost3d.deta
            ):
                logging.error(
                    "MUSIC 'Grid_size_in_eta' and 'Eta_grid_size' must equal "
                    "KoMPoST3D 'Neta' and ('Neta' - 1) * 'deta'."
                )
                valid = False
            transverse_size = (kompost3d.Ns - 1) * kompost3d.afm
            if not (
                math.isclose(
                    music.X_grid_size_in_fm, transverse_size, rel_tol=1e-3
                )
                and math.isclose(
                    music.Y_grid_size_in_fm, transverse_size, rel_tol=1e-3
                )
            ):
                logging.error(
                    "MUSIC 'X_grid_size_in_fm' and 'Y_grid_size_in_fm' must "
                    "equal KoMPoST3D ('Ns' - 1) * 'afm'."
                )
                valid = False
        if (
            "entropy_matching" in active_modules
            and hasattr(config, "entropy_matching")
            and config.entropy_matching.matching_type == 1
            and not math.isclose(
                config.entropy_matching.nu_eff, kompost3d.NuEffective
            )
        ):
            logging.error(
                "Mismatch between KoMPoST3D 'NuEffective' and entropy_matching 'nu_eff'."
            )
            valid = False

    # Add more checks as needed for other configuration sections

    return valid
