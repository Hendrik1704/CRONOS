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

    # Add more checks as needed for other configuration sections

    return valid
