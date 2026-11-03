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
