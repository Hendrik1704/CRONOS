import logging
import math


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

    # Only perform consistency checks for modules that are actually enabled
    if (
        "from_file_IC" in active_modules
        and "MUSIC" in active_modules
        and "iSS" in active_modules
        and hasattr(config, "from_file_IC")
        and hasattr(config, "MUSIC")
        and hasattr(config, "iSS")
    ):
        # Check that the "boost_invariant" settings match between from_file_IC and MUSIC
        if config.from_file_IC.boost_invariant != config.MUSIC.boost_invariant:
            logging.error(
                "Mismatch in 'boost_invariant' between from_file_IC and MUSIC modules."
            )
            valid = False
        # Check compatibility between MUSIC boost_invariant setting and iSS hydro_mode
        if config.MUSIC.boost_invariant == 1 and config.iSS.hydro_mode != 1:
            logging.error(
                "Incompatible 'boost_invariant' settings: MUSIC and iSS."
            )
            valid = False

    if "KoMPoST3D" in active_modules and hasattr(config, "KoMPoST3D"):
        kompost3d = config.KoMPoST3D
        if "KoMPoST" in active_modules:
            logging.error("KoMPoST and KoMPoST3D cannot be used together.")
            valid = False
        # KoMPoST-3D only implements the kinetic theory energy perturbations
        if kompost3d.EVOLUTION_MODE != 1:
            logging.error("KoMPoST3D only supports EVOLUTION_MODE = 1.")
            valid = False
        if kompost3d.MOMENTUM_PERTURBATIONS != 0:
            logging.error("KoMPoST3D only supports MOMENTUM_PERTURBATIONS = 0.")
            valid = False
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
            if config.MUSIC.boost_invariant != 0:
                logging.error(
                    "KoMPoST3D requires 'boost_invariant' = 0 in MUSIC."
                )
                valid = False
            if config.MUSIC.Initial_profile != 95:
                logging.error(
                    "KoMPoST3D output requires 'Initial_profile' = 95 in MUSIC."
                )
                valid = False
            # MUSIC takes the grid from the file header, but not the time
            if not math.isclose(
                config.MUSIC.Initial_time_tau_0, kompost3d.tOut
            ):
                logging.error(
                    "Mismatch between KoMPoST3D 'tOut' and MUSIC 'Initial_time_tau_0'."
                )
                valid = False
        if (
            "entropy_matching" in active_modules
            and hasattr(config, "entropy_matching")
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
