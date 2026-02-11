import logging


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

    # Add more checks as needed for other configuration sections

    return valid
