import difflib
import logging
import math

from src.modules.IPGlasma import CRONOS_CONTROLLED_PARAMETERS
from src.modules.iss_parameters import (
    ISS_CRONOS_CONTROLLED_PARAMETERS,
    ISS_PARAMETERS,
)
from src.modules.SMASH import SMASH_PARTICLE_FORMATS
from src.modules.kompost_parameters import (
    KOMPOST3D_PARAMETERS,
    KOMPOST_CRONOS_CONTROLLED_PARAMETERS,
    KOMPOST_PARAMETERS,
)
from src.modules.music_parameters import (
    MUSIC_CRONOS_CONTROLLED_PARAMETERS,
    MUSIC_PARAMETERS,
)

# MUSIC Initial_profile values that read the initial state from a file.
# 9 and 91-94 read one transverse slice (boost-invariant), 95 reads a (3+1)D
# profile (MUSIC init.cpp).
MUSIC_2D_FILE_PROFILES = (9, 91, 92, 93, 94)
MUSIC_3D_FILE_PROFILES = (95,)

# MUSIC EOS_to_use values CRONOS supports: the hotQCD EoS matched to the UrQMD
# (9) or SMASH (91) hadron list. GetModulesFromGit.sh downloads only these
# tables, and iSS samples the hadrons of the matching list.
MUSIC_SUPPORTED_EOS = (9, 91)

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


def _parameter_errors(code, section, known, controlled, list_file, is_valid):
    """Return the problems with the keys and values of a module section.

    The external code ignores keys it does not read, so a misspelled key would
    be dropped without a warning.
    """
    errors = []
    spelling = {key.lower(): key for key in known}
    for key, value in section.to_dict().items():
        if key in controlled:
            errors.append(
                f"{code} parameter '{key}' is set by CRONOS, remove it from "
                "the configuration."
            )
        elif key not in known:
            if key.lower() in spelling:
                hint = f" {code} spells it '{spelling[key.lower()]}'."
            else:
                close = difflib.get_close_matches(key, known, n=1)
                hint = f" Did you mean '{close[0]}'?" if close else ""
            errors.append(
                f"{code} does not read the parameter '{key}'.{hint} The "
                f"parameters {code} reads are listed in {list_file}."
            )
        else:
            message = is_valid(value)
            if message:
                errors.append(
                    f"{code} parameter '{key}' must be {message}, "
                    f"not {value!r}."
                )
    return errors


def music_parameter_errors(music_config):
    """Return the problems with the keys and values of the MUSIC section.

    MUSIC reads one token per value, so a value with spaces would be cut.
    """

    def is_valid(value):
        if isinstance(value, (bool, int, float)) or (
            isinstance(value, str) and len(value.split()) == 1
        ):
            return None
        return "a number or a string without spaces"

    return _parameter_errors(
        "MUSIC",
        music_config,
        MUSIC_PARAMETERS,
        MUSIC_CRONOS_CONTROLLED_PARAMETERS,
        "src/modules/music_parameters.py",
        is_valid,
    )


def iss_parameter_errors(iss_config):
    """Return the problems with the keys and values of the iSS section.

    iSS converts every value to a number.
    """

    def is_valid(value):
        if isinstance(value, (bool, int, float)):
            return None
        return "a number"

    return _parameter_errors(
        "iSS",
        iss_config,
        ISS_PARAMETERS,
        ISS_CRONOS_CONTROLLED_PARAMETERS,
        "src/modules/iss_parameters.py",
        is_valid,
    )


def kompost_parameter_errors(section_name, section_config, known):
    """Return the problems with the keys and values of a KoMPoST section.

    INIReader reads a value up to an inline comment, so a value must be a
    number or one word.
    """

    def is_valid(value):
        if isinstance(value, (bool, int, float)) or (
            isinstance(value, str)
            and len(value.split()) == 1
            and not any(c in value for c in ";#")
        ):
            return None
        return "a number or a string without spaces, ';' or '#'"

    return _parameter_errors(
        section_name,
        section_config,
        known,
        KOMPOST_CRONOS_CONTROLLED_PARAMETERS,
        "src/modules/kompost_parameters.py",
        is_valid,
    )


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
        for error in music_parameter_errors(config.MUSIC):
            logging.error(error)
            valid = False

        if config.MUSIC.EOS_to_use not in MUSIC_SUPPORTED_EOS:
            logging.error(
                f"MUSIC EOS_to_use {config.MUSIC.EOS_to_use} is not "
                "supported: use 9 (hotQCD matched to UrQMD hadrons, for iSS "
                "decays) or 91 (hotQCD matched to SMASH hadrons). Another EoS "
                "needs its tables in external_codes/GetModulesFromGit.sh and "
                "a hadron list in iSS that matches it."
            )
            valid = False

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

    for name, known in [
        ("KoMPoST", KOMPOST_PARAMETERS),
        ("KoMPoST3D", KOMPOST3D_PARAMETERS),
    ]:
        if active(name):
            for error in kompost_parameter_errors(name, config[name], known):
                logging.error(error)
                valid = False

    if active("iSS"):
        for error in iss_parameter_errors(config.iSS):
            logging.error(error)
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
                    "EOS_to_use to 91."
                )
                valid = False
        elif afterburner_type == ISS_AFTERBURNER_SMASH:
            # iSS skips resonance decays for the SMASH afterburner type
            logging.error(
                "Without SMASH, iSS would skip the resonance decays: set MUSIC "
                "EOS_to_use to 9."
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
        if kompost3d.ENERGY_PERTURBATIONS not in (0, 1):
            logging.error("KoMPoST3D 'ENERGY_PERTURBATIONS' must be 0 or 1.")
            valid = False
        # Other regulator names are ignored by KoMPoST-3D (no regulation)
        if kompost3d.Regulator not in (
            "TwoPass",
            "KoMPoSTAddition",
            "NoRegulator",
        ):
            logging.error(
                "KoMPoST3D 'Regulator' must be TwoPass, KoMPoSTAddition or "
                "NoRegulator."
            )
            valid = False
        # KoMPoST-3D smears with a width of 0.1 / (tOut - tIn)
        if not kompost3d.tIn < kompost3d.tOut:
            logging.error("KoMPoST3D requires 'tIn' < 'tOut'.")
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
            # KoMPoST-3D writes 18 columns; MUSIC's profile 95 also reads the
            # bulk pressure, which entropy_matching appends
            next_module = (
                active_modules[kompost3d_index + 1]
                if kompost3d_index + 1 < len(active_modules)
                else None
            )
            if next_module != "entropy_matching":
                logging.error(
                    "entropy_matching must directly follow KoMPoST3D when "
                    "MUSIC is used."
                )
                valid = False
            # (MUSIC boost_invariant 0 follows from the general rule for
            # Initial_profile 95)
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

    if active("SMASH"):
        particles_format = getattr(
            config.SMASH, "Particles_Format", SMASH_PARTICLE_FORMATS[0]
        )
        if particles_format not in SMASH_PARTICLE_FORMATS:
            logging.error(
                f"SMASH Particles_Format {particles_format!r} is not supported: "
                "use 'Oscar2013_bin' (binary) or 'Oscar2013' (text)."
            )
            valid = False

    if active("afterburner_toolkit") and "read_in_mode" in (
        config.afterburner_toolkit.to_dict()
    ):
        logging.error(
            "afterburner_toolkit read_in_mode is set by CRONOS for the output "
            "of the previous module (choose the SMASH output with SMASH "
            "Particles_Format); remove it from the configuration."
        )
        valid = False

    # Add more checks as needed for other configuration sections

    return valid
