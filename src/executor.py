from src.module_base import BaseModule, get_memory_info
from src.handle_results import handle_results
from src.colors import Colors
from src.cluster_submission import submission_script_cluster
from src.checkpoint_manager import CheckpointManager
import logging
import os
import shutil
import pprint
import traceback
import re


def analyze_error(exception, module_name):
    """Analyze simulation exceptions to provide enhanced error diagnostics and optimization suggestions.

    This function performs intelligent analysis of simulation failures to categorize
    error types, detect memory-related issues, and provide actionable suggestions
    for resolving common problems in heavy-ion collision simulations.

    Error Categories Detected:
    - Memory-related errors (MemoryError, malloc failures, bad_alloc)
    - Resource exhaustion (file limits, disk space, quotas)
    - System-level issues (process limits, permissions)
    - Physics code failures (subprocess errors, numerical issues)

    Args:
        exception (Exception): The exception object that caused the failure
        module_name (str): Name of the physics module where failure occurred
            (e.g., 'KoMPoST', 'MUSIC', 'iSS', 'SMASH')

    Returns:
        dict: Comprehensive error analysis containing:
            - enhanced_message (str): Human-readable error description
            - is_memory_related (bool): True if memory issue detected
            - is_resource_related (bool): True if system resource issue
            - memory_info (dict): Current system memory state if available
            - error_type (str): Original exception type name
            - suggestions (list): Optimization recommendations

    Example:
        >>> try:
        ...     run_physics_module()
        ... except Exception as e:
        ...     analysis = analyze_error(e, 'MUSIC')
        ...     if analysis['is_memory_related']:
        ...         print(f"Memory issue: {analysis['enhanced_message']}")
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__

    # Memory-related error patterns
    memory_patterns = [
        "memory",
        "malloc",
        "out of memory",
        "cannot allocate",
        "memoryerror",
        "bad_alloc",
        "enomem",
        "resource temporarily unavailable",
    ]

    # Process/system resource patterns
    resource_patterns = [
        "too many open files",
        "resource unavailable",
        "no space left",
        "disk full",
        "quota exceeded",
    ]

    is_memory_related = (
        isinstance(exception, MemoryError)
        or error_type in ["MemoryError", "OSError"]
        or any(pattern in error_str for pattern in memory_patterns)
    )

    is_resource_related = any(
        pattern in error_str for pattern in resource_patterns
    )

    # Get current memory state
    memory_info = get_memory_info()

    # Create enhanced error message
    if isinstance(exception, MemoryError):
        enhanced_msg = f"MEMORY ERROR in module '{module_name}': Python MemoryError - process ran out of memory"
    elif is_memory_related:
        enhanced_msg = (
            f"MEMORY-RELATED ERROR in module '{module_name}': {exception}"
        )
    elif is_resource_related:
        enhanced_msg = f"RESOURCE ERROR in module '{module_name}': {exception}"
    elif memory_info and memory_info["system_percent"] > 90:
        enhanced_msg = f"ERROR in module '{module_name}' (system memory {memory_info['system_percent']:.1f}% - possible memory issue): {exception}"
    else:
        enhanced_msg = f"Module '{module_name}' failed: {exception}"

    return {
        "enhanced_message": enhanced_msg,
        "is_memory_related": is_memory_related
        or (memory_info and memory_info["system_percent"] > 90),
        "is_resource_related": is_resource_related,
        "memory_info": memory_info,
        "original_exception": exception,
    }


def get_memory_suggestions(memory_info, module_name):
    """Generate memory optimization suggestions based on system state and physics module.

    Provides context-aware recommendations for reducing memory usage in CRONOS
    simulations, with module-specific optimizations for different physics codes
    and general strategies for cluster resource management.

    Args:
        memory_info (dict): Current system memory information containing:
            - system_percent (float): System memory usage percentage (0-100)
            - process_rss_mb (float): Process resident set size in MB
            - system_available_gb (float): Available system memory in GB
        module_name (str): Name of physics module experiencing memory issues
            ('KoMPoST', 'MUSIC', 'iSS', 'SMASH', 'afterburner_toolkit')

    Returns:
        list[str]: Ordered list of optimization suggestions, from most critical
            to general recommendations. Empty list if memory usage is acceptable.

    Suggestion Categories:
        - Critical: Memory usage >95% - immediate action required
        - High: Memory usage >85% - monitoring and optimization needed
        - Module-specific: Physics code parameter optimizations
        - General: Framework-level memory reduction strategies

    Example:
        >>> memory_info = {'system_percent': 92.5, 'process_rss_mb': 8192}
        >>> suggestions = get_memory_suggestions(memory_info, 'MUSIC')
        >>> print(suggestions[0])
        'Critical memory shortage - consider using a node with more RAM'
    """
    suggestions = []

    if memory_info["system_percent"] > 95:
        suggestions.append(
            "Critical memory shortage - consider using a node with more RAM"
        )
        suggestions.append(
            "Try reducing the number of grid points or lattice size in configuration"
        )

    elif memory_info["system_percent"] > 85:
        suggestions.append(
            "High memory usage detected - monitor for memory leaks"
        )

    # Module-specific suggestions
    if module_name.lower() in ["ipglasma", "music", "kompost"]:
        suggestions.extend(
            [
                f"For {module_name}: Try reducing grid size (Ns parameter) or evolution time",
                f"For {module_name}: Consider using smaller lattice spacing (afm parameter)",
            ]
        )

    elif module_name.lower() in ["iss"]:
        suggestions.extend(
            [
                "For iSS: Try reducing particle_diff_reso or using fewer sample particles",
                "For iSS: Consider using binary output format to reduce memory usage",
            ]
        )

    elif module_name.lower() in ["smash"]:
        suggestions.extend(
            [
                "For SMASH: Reduce number of test particles or collision criteria",
                "For SMASH: Enable particle output compression",
            ]
        )

    # General suggestions
    suggestions.extend(
        [
            "Enable 'suppress_output: True' for modules to reduce memory usage",
            "Consider running fewer events per job (reduce number_events_per_job)",
            "Check if external codes have memory leak issues",
        ]
    )

    return suggestions


def prepare_modules(args, config, module_registry, project_root):
    """Prepare the complete CRONOS simulation environment with directory structure and module initialization.

    This function creates the hierarchical directory structure required for CRONOS
    simulations, initializes all physics modules, and prepares the environment for
    either local execution or cluster submission via SLURM job arrays.

    Directory Structure Created:
        run_dir/
        ├── job_0/
        │   ├── event_0/
        │   │   ├── module_name_1/  (e.g., KoMPoST/)
        │   │   ├── module_name_2/  (e.g., MUSIC/)
        │   │   ├── ...
        │   │   └── results/
        │   └── event_1/
        └── job_1/
            └── ...

    Special Handling:
    - FromFileIC mode: Creates one job per initial condition file
    - Standard mode: Creates jobs based on config.number_of_jobs
    - Each job contains config.number_events_per_job event directories
    - Each event contains directories for all configured physics modules

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing:
            - run_dir (str): Base directory for simulation runs
            - cluster (str): Target cluster environment (local, noctua1)
        config (Configuration): Complete CRONOS configuration object with:
            - general.modules (list): Physics modules to include in simulation
            - number_of_jobs (int): Number of job arrays to create
            - number_events_per_job (int): Events per job directory
            - from_file_IC.input_path (str): Path to initial condition files (if used)
        module_registry (dict): Mapping of module names to module classes:
            - Keys: Module names as strings (e.g., 'KoMPoST', 'MUSIC')
            - Values: Module class objects (subclasses of BaseModule)
        project_root (Path): Absolute path to CRONOS project root directory

    Raises:
        SystemExit: If run directory is not empty or module is not registered
        TypeError: If registered module does not subclass BaseModule
        OSError: If directory creation fails due to permissions

    Side Effects:
        - Creates complete directory structure in args.run_dir
        - Calls prepare_environment() on each module instance
        - Copies initial condition files for FromFileIC mode
        - Generates cluster submission scripts via submission_script_cluster()
        - Updates config.number_of_jobs and config.number_events_per_job for FromFileIC
        - Provides colored terminal feedback on preparation status

    Example:
        >>> args = argparse.Namespace(run_dir='run/', cluster='local')
        >>> config = load_config('config/main.py', 'config/user.py')
        >>> registry = {'KoMPoST': KoMPoST, 'MUSIC': MUSIC}
        >>> prepare_modules(args, config, registry, Path('/path/to/cronos'))
        # Creates run/job_0/event_0/{KoMPoST,MUSIC,results}/ structure
    """

    # Ensure top-level job/event counters exist, falling back to general settings
    if hasattr(config, "general"):
        if not hasattr(config, "number_of_jobs"):
            try:
                config.number_of_jobs = config.general.number_of_jobs
            except AttributeError:
                config.number_of_jobs = 1
        if not hasattr(config, "number_events_per_job"):
            try:
                config.number_events_per_job = (
                    config.general.number_events_per_job
                )
            except AttributeError:
                config.number_events_per_job = 1

    # Create the run directory if it does not exist and check that it is empty
    if not os.path.exists(args.run_dir):
        os.makedirs(args.run_dir)
    elif os.listdir(args.run_dir):
        logging.error(f"Run directory {args.run_dir} is not empty.")
        exit(1)
    IC_from_file = "from_file_IC" in config.general.modules
    if IC_from_file:
        logging.info(
            "FromFileIC is used, preparing separate job directories for each IC file."
        )
        input_path = config.from_file_IC.input_path
        # List only actual files in the directory (skip subdirectories)
        all_entries = os.listdir(input_path)
        file_entries = [
            f
            for f in all_entries
            if os.path.isfile(os.path.join(input_path, f))
        ]

        # Special-case sorting: filenames like 'Tmunu10_Ns151_NsLong71.dat'
        # If all files match the pattern ^Tmunu(\d+)_, sort them by the numeric index
        pattern = re.compile(r"^Tmunu(\d+)_")
        numeric_matches = []
        all_match = True if file_entries else False
        for fname in file_entries:
            m = pattern.match(fname)
            if m:
                try:
                    numeric_matches.append((int(m.group(1)), fname))
                except ValueError:
                    all_match = False
                    break
            else:
                all_match = False
                break

        if all_match and numeric_matches:
            ic_files = [
                fname
                for _, fname in sorted(numeric_matches, key=lambda x: x[0])
            ]
        else:
            ic_files = sorted(file_entries)
        config.number_of_jobs = len(ic_files)
        config.number_events_per_job = 1  # Each IC file corresponds to one job
        logging.info(f"Found {config.number_of_jobs} IC files in {input_path}.")
    else:
        logging.info(
            f"Preparing {config.number_of_jobs} jobs with {config.number_events_per_job} events each."
        )

    # Create a directory for each job (job_0, job_1,...)
    for job_id in range(config.number_of_jobs):
        job_dir = os.path.join(args.run_dir, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)
        # Create a sub-directory for each event (event_0, event_1, ...)
        for event_id in range(config.number_events_per_job):
            event_dir = os.path.join(job_dir, f"event_{event_id}")
            os.makedirs(event_dir, exist_ok=True)

            # Create a directory for each module in config.general.modules in the event directory
            for module_name in config.general.modules:
                module_dir = os.path.join(event_dir, module_name)
                os.makedirs(module_dir, exist_ok=True)

                # Check that the module is in the module registry
                if module_name not in module_registry:
                    logging.error(f"Module '{module_name}' is not registered.")
                    exit(1)

                module_class = module_registry[module_name]
                if not issubclass(module_class, BaseModule):
                    raise TypeError(
                        f"Module '{module_name}' does not subclass BaseModule."
                    )

                module_config = getattr(config, module_name)
                module_instance = module_class(
                    module_config, full_config=config, project_root=project_root
                )
                module_instance.prepare_environment(event_dir)

                if IC_from_file and module_name == "from_file_IC":
                    # Copy the file in the created "from_file_IC" directory to the IC file in the module directory
                    ic_file = ic_files[job_id]
                    shutil.copy2(
                        os.path.join(input_path, ic_file),
                        os.path.join(module_dir, ic_file),
                    )
                    logging.debug(f"Copied {ic_file} to {module_dir}")

            # Create a result directory
            result_dir = os.path.join(event_dir, "results")
            os.makedirs(result_dir, exist_ok=True)

    submission_script_cluster(args, config)

    colored_message = f"Prepared {config.number_of_jobs} jobs with {config.number_events_per_job} events each in '{args.run_dir}'"
    colored_message = Colors.green(colored_message, bold=True)
    logging.info(colored_message)


def run_modules(config, module_registry, job_dir, project_root):
    """Execute complete CRONOS simulation with checkpoint support and comprehensive error handling.

    This function orchestrates the execution of heavy-ion collision simulations
    through the complete physics chain, with robust checkpoint-based resumption
    and advanced memory monitoring for production cluster environments.

    Physics Execution Workflow:
    1. Initial conditions generation (IPGlasma/from_file_IC)
    2. Pre-equilibrium evolution (KoMPoST)
    3. Hydrodynamic evolution (MUSIC)
    4. Cooper-Frye particlization (iSS)
    5. Hadronic afterburner (SMASH)
    6. Flow analysis (afterburner_toolkit)

    Checkpoint Features:
    - Automatic checkpoint creation after each module completion
    - Event-level and module-level progress tracking
    - Intelligent resumption from last successful checkpoint
    - Comprehensive failure analysis and memory diagnostics
    - Integration with SLURM job resubmission workflows

    Error Handling:
    - Memory-related error detection with usage analysis
    - Subprocess memory monitoring for external physics codes
    - Enhanced error messages with optimization suggestions
    - Detailed traceback logging for debugging
    - Partial simulation recovery capabilities

    Args:
        config (Configuration): Complete CRONOS configuration object containing:
            - general.modules (list): Ordered list of physics modules to execute
            - Module-specific configuration sections (e.g., config.KoMPoST)
            - Execution parameters and resource limits
        module_registry (dict): Registry mapping module names to classes:
            - Keys: Module name strings matching config.general.modules
            - Values: BaseModule subclass objects for instantiation
        job_dir (str): Absolute path to job directory containing event subdirectories:
            - Must contain event_0/, event_1/, ... subdirectories
            - Each event dir contains module-specific subdirectories
            - Checkpoint file (.cronos_checkpoint.json) stored at this level
        project_root (str): Absolute path to CRONOS project root for:
            - External code executable locations
            - Configuration file resolution
            - Resource and data file access

    Raises:
        SystemExit: If job directory doesn't exist or configuration is invalid
        MemoryError: If system runs out of memory during simulation
        subprocess.CalledProcessError: If external physics code fails
        Exception: Any module execution error (logged with enhanced analysis)

    Side Effects:
        - Creates/updates .cronos_checkpoint.json with progress tracking
        - Executes external physics codes via subprocess with memory monitoring
        - Generates physics output files in respective module directories
        - Calls handle_results() for output processing and compression
        - Provides colored terminal output for progress and error reporting
        - May consume significant CPU, memory, and disk resources

    Checkpoint Resumption:
        The function automatically detects existing checkpoints and resumes
        from the last successful module completion. Events and modules that
        completed successfully are skipped, allowing efficient recovery from
        failures in long-running simulations.

    Memory Management:
        Advanced memory monitoring tracks both Python process memory and
        subprocess memory usage. Memory-related failures trigger detailed
        analysis with optimization suggestions for cluster resource requests.

    Example:
        >>> config = load_config('config/main.py', 'config/user.py')
        >>> registry = {'KoMPoST': KoMPoST, 'MUSIC': MUSIC, 'iSS': iSS}
        >>> run_modules(config, registry, '/path/to/run/job_0', '/path/to/cronos')
        # Executes complete simulation chain with checkpoint support
    """
    job_dir = os.path.abspath(job_dir)
    if not os.path.exists(job_dir):
        logging.error(f"Job directory '{job_dir}' does not exist.")
        exit(1)

    # Initialize checkpoint manager
    checkpoint_manager = CheckpointManager(job_dir)

    # Log checkpoint summary if resuming
    if os.path.exists(checkpoint_manager.checkpoint_file):
        colored_msg = Colors.yellow(
            "[CHECKPOINT] Resuming from previous checkpoint", bold=True
        )
        logging.info(colored_msg)
        logging.info(checkpoint_manager.get_summary())

    # loop over the event directories in the job directory
    for event_dir in os.listdir(job_dir):
        event_dir_path = os.path.join(job_dir, event_dir)

        # Skip non-directories and non-event directories (like checkpoint files)
        if not os.path.isdir(event_dir_path) or not event_dir.startswith(
            "event_"
        ):
            continue

        event_id = event_dir.split("_")[-1]

        # Check if this event should be skipped (already completed)
        if checkpoint_manager.should_skip_event(event_dir):
            colored_msg = Colors.green(
                f"[CHECKPOINT] Skipping completed {event_dir}"
            )
            logging.info(colored_msg)
            continue

        # Determine where to resume processing for this event
        all_modules = config.general.modules
        start_index, resume_reason = checkpoint_manager.get_resume_point(
            event_dir, all_modules
        )

        if start_index >= len(all_modules):
            colored_msg = Colors.green(f"[CHECKPOINT] {resume_reason}")
            logging.info(colored_msg)
            continue

        if start_index > 0:
            colored_msg = Colors.yellow(f"[CHECKPOINT] {resume_reason}")
            logging.info(colored_msg)

        # Process modules starting from resume point
        modules_to_process = all_modules[start_index:]

        try:
            for module_name in modules_to_process:
                # Mark module as started in checkpoint
                checkpoint_manager.mark_module_started(event_dir, module_name)

                if module_name not in module_registry:
                    raise ValueError(
                        f"Module '{module_name}' not found in registry."
                    )

                module_class = module_registry[module_name]
                if not issubclass(module_class, BaseModule):
                    raise TypeError(
                        f"Module '{module_name}' does not subclass BaseModule."
                    )

                module_config = getattr(config, module_name)
                logging.debug(
                    f"Initializing module '{module_name}' with config: {module_config.to_dict()}"
                )
                module_instance = module_class(
                    module_config,
                    full_config=config,
                    project_root=project_root,
                    event_id=event_id,
                )

                # Execute module phases
                module_instance.prepare_input(event_dir_path)
                module_instance.run(event_dir_path)
                module_instance.fetch_output(event_dir_path)

                # Mark module as completed in checkpoint
                checkpoint_manager.mark_module_completed(event_dir, module_name)

        except Exception as e:
            # Determine which module was actually running when failure occurred
            current_module = "unknown"
            for i, module_name in enumerate(modules_to_process):
                event_status = checkpoint_manager.get_event_status(event_dir)
                if module_name not in event_status["completed_modules"]:
                    current_module = module_name
                    break

            # Enhanced error analysis
            error_analysis = analyze_error(e, current_module)

            checkpoint_manager.mark_module_failed(
                event_dir, current_module, error_analysis["enhanced_message"]
            )

            # Display enhanced error message
            colored_msg = Colors.red(
                f"[ERROR] {error_analysis['enhanced_message']}"
            )
            logging.error(colored_msg)

            # Show memory info if memory-related
            if error_analysis["is_memory_related"]:
                memory_info = error_analysis["memory_info"]
                if memory_info:
                    memory_msg = (
                        f"Memory usage at failure: Process={memory_info['process_rss_mb']:.1f}MB, "
                        f"System={memory_info['system_percent']:.1f}% "
                        f"({memory_info['system_available_gb']:.1f}GB available)"
                    )
                    logging.error(Colors.red(f"[MEMORY] {memory_msg}"))

                    # Provide memory optimization suggestions
                    suggestions = get_memory_suggestions(
                        memory_info, current_module
                    )
                    for suggestion in suggestions:
                        logging.info(
                            Colors.yellow(f"[SUGGESTION] {suggestion}")
                        )

            # Log more detailed error information
            logging.error(f"Full traceback:\n{traceback.format_exc()}")

            # Re-raise the exception to maintain original behavior
            raise

        # Handle results and cleanup only if all modules completed successfully
        try:
            event_dir_results_path = os.path.join(event_dir_path, "results")
            if not os.path.exists(event_dir_results_path):
                raise FileNotFoundError(
                    f"Results directory '{event_dir_results_path}' does not exist."
                )

            logging.info(f"Handling results in {event_dir_results_path}...")

            # Create configuration file in results directory
            try:
                config_file_path = os.path.join(
                    event_dir_results_path, "configuration.py"
                )
                with open(config_file_path, "w") as f:
                    for section, values in config.to_dict().items():
                        f.write(f"{section} = \\\n")
                        pprint.pprint(
                            values, stream=f, indent=4, width=80, compact=False
                        )
                        f.write("\n\n")
                logging.debug(f"Created configuration file: {config_file_path}")
            except Exception as e:
                logging.error(f"Failed to create configuration file: {e}")
                raise

            # Handle results processing
            try:
                handle_results(config, event_dir_results_path, event_id)
                logging.info("Results handling completed successfully")
            except Exception as e:
                logging.error(f"Results handling failed: {e}")
                raise

            # Move the h5 file to the job directory
            hdf5_filename = os.path.join(
                event_dir_results_path, f"event_{event_id}.h5"
            )
            hdf5_destination = os.path.join(job_dir, f"event_{event_id}.h5")

            if os.path.exists(hdf5_filename):
                try:
                    shutil.move(hdf5_filename, hdf5_destination)
                    logging.info(f"Moved {hdf5_filename} to {job_dir}")
                except Exception as e:
                    logging.error(f"Failed to move HDF5 file: {e}")
                    raise

                # Remove the event directory after moving the h5 file
                try:
                    shutil.rmtree(event_dir_path)
                    logging.info(f"Removed event directory {event_dir_path}")
                except Exception as e:
                    logging.error(f"Failed to remove event directory: {e}")
                    # Don't raise here - file was moved successfully
                    logging.warning(
                        "Event directory cleanup failed, but simulation completed successfully"
                    )
            else:
                # Check if there are any expected output files
                result_files = [
                    f
                    for f in os.listdir(event_dir_results_path)
                    if f.endswith((".h5", ".dat", ".txt"))
                ]
                if result_files:
                    logging.warning(
                        f"HDF5 file '{hdf5_filename}' not found, but other result files exist: {result_files}"
                    )
                else:
                    logging.error(
                        f"No output files found in results directory: {event_dir_results_path}"
                    )
                    raise FileNotFoundError(
                        f"Expected output file '{hdf5_filename}' not found and no alternative results exist"
                    )

            # Mark event as completed in checkpoint (only if we got this far)
            checkpoint_manager.mark_event_completed(event_dir)

        except Exception as e:
            # Mark the event as failed if result processing fails
            checkpoint_manager.mark_module_failed(
                event_dir, "result_processing", str(e)
            )
            colored_msg = Colors.red(
                f"[ERROR] Result processing failed for {event_dir}: {e}"
            )
            logging.error(colored_msg)
            raise

    # Mark entire job as completed
    checkpoint_manager.mark_job_completed()

    # Optionally cleanup checkpoint file after successful completion
    # Default behavior is to cleanup checkpoints unless explicitly disabled
    cleanup_checkpoints = getattr(config.general, "cleanup_checkpoints", True)
    if cleanup_checkpoints:
        checkpoint_manager.cleanup_checkpoint()
