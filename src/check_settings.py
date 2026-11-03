import logging
import math

from src.modules.IPGlasma import CRONOS_CONTROLLED_PARAMETERS


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

    if "IPGlasma" in active_modules and hasattr(config, "IPGlasma"):
        ipglasma = config.IPGlasma
        for key, reason in CRONOS_CONTROLLED_PARAMETERS.items():
            if key in ipglasma.to_dict():
                logging.error(
                    f"IPGlasma parameter '{key}' is set by CRONOS ({reason}); "
                    "remove it from the configuration."
                )
                valid = False
        if ipglasma.useJIMWLK == 1:
            if ipglasma.useFluctuatingX != 0:
                logging.error(
                    "IPGlasma 'useJIMWLK' 1 requires 'useFluctuatingX' 0."
                )
                valid = False
            if (
                max(ipglasma.projectileX, ipglasma.targetX)
                >= ipglasma.jimwlkInitialX
            ):
                logging.warning(
                    "IPGlasma: JIMWLK only evolves to an x below 'jimwlkInitialX', "
                    "but 'projectileX' or 'targetX' is not below it."
                )
        # The next module needs the matching IP-Glasma output file, time
        # and grid
        ipglasma_index = active_modules.index("IPGlasma")
        next_module = (
            active_modules[ipglasma_index + 1]
            if ipglasma_index + 1 < len(active_modules)
            else None
        )
        if next_module == "KoMPoST" and hasattr(config, "KoMPoST"):
            kompost = config.KoMPoST
            if ipglasma.writeTmunu != 1:
                logging.error(
                    "KoMPoST after IPGlasma requires 'writeTmunu' = 1."
                )
                valid = False
            if not math.isclose(kompost.tIn, ipglasma.maxTime):
                logging.error(
                    "Mismatch between IPGlasma 'maxTime' and KoMPoST 'tIn'."
                )
                valid = False
            if kompost.Ns != ipglasma.sizeOutput or not math.isclose(
                kompost.afm, ipglasma.LOutput / ipglasma.sizeOutput
            ):
                logging.error(
                    "KoMPoST 'Ns' and 'afm' must equal IPGlasma 'sizeOutput' "
                    "and 'LOutput' / 'sizeOutput'."
                )
                valid = False
        elif next_module == "MUSIC" and hasattr(config, "MUSIC"):
            if ipglasma.writeHydro != 1:
                logging.error("MUSIC after IPGlasma requires 'writeHydro' = 1.")
                valid = False
            if not math.isclose(
                config.MUSIC.Initial_time_tau_0, ipglasma.maxTime
            ):
                logging.error(
                    "Mismatch between IPGlasma 'maxTime' and MUSIC "
                    "'Initial_time_tau_0'."
                )
                valid = False

    # Add more checks as needed for other configuration sections

    return valid
