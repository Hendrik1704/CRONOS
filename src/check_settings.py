import logging
import math

from src.modules.IPGlasma import CRONOS_CONTROLLED_PARAMETERS

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
            # (with readInitialWilsonLines, the evolution starts at the x of
            # the read Wilson lines instead)
            final_x = max(ipglasma.projectileX, ipglasma.targetX)
            if ipglasma.readInitialWilsonLines == 0:
                if final_x > ipglasma.jimwlkInitialX:
                    # IP-Glasma rejects this
                    logging.error(
                        "IPGlasma: JIMWLK evolves to smaller x, but "
                        "'projectileX' or 'targetX' is above 'jimwlkInitialX'."
                    )
                    valid = False
                elif final_x == ipglasma.jimwlkInitialX:
                    logging.warning(
                        "IPGlasma: 'projectileX' or 'targetX' equals "
                        "'jimwlkInitialX', so JIMWLK does not evolve it."
                    )
        # The next module needs the matching IP-Glasma output file, time
        # and grid
        ipglasma_index = active_modules.index("IPGlasma")
        next_module = (
            active_modules[ipglasma_index + 1]
            if ipglasma_index + 1 < len(active_modules)
            else None
        )
        if next_module is not None:
            if ipglasma.runEvolution != 1:
                logging.error(
                    f"{next_module} after IPGlasma requires 'runEvolution' = 1 "
                    "(otherwise IP-Glasma writes no initial conditions)."
                )
                valid = False
            if ipglasma.inverseQsForMaxTime != 0:
                # The final time then differs per event, so neither the output
                # file name nor the start time of the next module is known
                logging.error(
                    f"{next_module} after IPGlasma requires "
                    "'inverseQsForMaxTime' = 0."
                )
                valid = False
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
            # The IP-Glasma hydro file has 18 columns; Initial_profile 94 would
            # also read a bulk pressure column
            if config.MUSIC.Initial_profile not in (9, 91, 92, 93):
                logging.error(
                    "MUSIC after IPGlasma requires 'Initial_profile' 9, 91, 92 "
                    "or 93."
                )
                valid = False
            if not math.isclose(
                config.MUSIC.Initial_time_tau_0, ipglasma.maxTime
            ):
                logging.error(
                    "Mismatch between IPGlasma 'maxTime' and MUSIC "
                    "'Initial_time_tau_0'."
                )
                valid = False

    if "KoMPoST" in active_modules and hasattr(config, "KoMPoST"):
        kompost = config.KoMPoST
        # KoMPoST indexes its Ns x Ns grid without range checks
        for start, end in [("xSTART", "xEND"), ("ySTART", "yEND")]:
            if not 0 <= kompost[start] <= kompost[end] <= kompost.Ns - 1:
                logging.error(
                    f"KoMPoST requires 0 <= {start} <= {end} <= 'Ns' - 1."
                )
                valid = False

    # Add more checks as needed for other configuration sections

    return valid
