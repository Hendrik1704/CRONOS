from abc import ABC, abstractmethod
import time
import logging
import psutil
from functools import wraps
from .colors import Colors


def get_memory_info():
    """Retrieve comprehensive memory usage information for current process and system.

    Collects memory statistics using psutil for both the current Python process
    and overall system memory status. Used for memory monitoring and threshold checks.

    Returns:
        dict or None: Memory information dictionary containing:
            - process_rss_mb (float): Process resident set size in MB
            - process_vms_mb (float): Process virtual memory size in MB
            - process_percent (float): Process memory as percentage of system total
            - system_total_gb (float): Total system memory in GB
            - system_available_gb (float): Available system memory in GB
            - system_percent (float): Used system memory percentage
        Returns None if memory information cannot be retrieved.

    Example:
        >>> info = get_memory_info()
        >>> print(f"Process using {info['process_rss_mb']:.1f}MB")
        Process using 245.2MB
    """
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        # Get system memory
        system_memory = psutil.virtual_memory()

        return {
            "process_rss_mb": memory_info.rss
            / 1024
            / 1024,  # Resident Set Size
            "process_vms_mb": memory_info.vms
            / 1024
            / 1024,  # Virtual Memory Size
            "process_percent": memory_percent,
            "system_total_gb": system_memory.total / 1024 / 1024 / 1024,
            "system_available_gb": system_memory.available / 1024 / 1024 / 1024,
            "system_percent": system_memory.percent,
        }
    except Exception as e:
        logging.warning(f"Could not get memory info: {e}")
        return None


def check_memory_threshold(threshold_percent=90):
    """Evaluate whether current system memory usage exceeds specified threshold.

    Checks system memory percentage against a configurable threshold to determine
    if memory usage is critically high. Used for early warning systems and
    resource management decisions.

    Args:
        threshold_percent (int, optional): Memory usage percentage threshold.
            Defaults to 90.

    Returns:
        tuple: A tuple containing:
            - bool: True if memory usage exceeds threshold, False otherwise
            - dict or None: Memory information from get_memory_info()

    Example:
        >>> is_high, info = check_memory_threshold(85)
        >>> if is_high:
        ...     print(f"Warning: Memory at {info['system_percent']:.1f}%")
    """
    memory_info = get_memory_info()
    if memory_info and memory_info["system_percent"] > threshold_percent:
        return True, memory_info
    return False, memory_info


def monitor_subprocess_memory(
    process, module_name, memory_threshold_mb=8192, check_interval=2
):
    """Monitor memory usage of a running subprocess in real-time using threading.

    Starts a daemon thread to continuously monitor memory consumption of an external
    subprocess (physics codes like MUSIC, SMASH, etc.). Tracks peak memory usage,
    generates warnings when thresholds are exceeded, and collects time-series data.

    The monitoring runs asynchronously and stops automatically when the subprocess
    terminates or monitoring is explicitly disabled.

    Args:
        process (subprocess.Popen): The subprocess object to monitor.
        module_name (str): Name of the calling module for log identification.
        memory_threshold_mb (int, optional): Memory threshold in MB for warnings.
            Defaults to 8192 (8GB).
        check_interval (int, optional): Monitoring interval in seconds.
            Defaults to 2.

    Returns:
        dict: Memory statistics dictionary containing:
            - peak_memory_mb (float): Maximum memory usage observed
            - peak_memory_percent (float): Peak memory as system percentage
            - samples (list): Time-series memory usage data points
            - monitoring_active (bool): Flag to control monitoring thread

    Example:
        >>> process = subprocess.Popen(['./physics_code'])
        >>> stats = monitor_subprocess_memory(process, "MUSIC", 4096)
        >>> # Monitoring continues in background thread
        >>> process.wait()
        >>> print(f"Peak memory: {stats['peak_memory_mb']:.1f}MB")

    Note:
        Uses daemon threads to avoid blocking main execution. Memory warnings
        are logged when subprocess exceeds the configured threshold.
    """
    import threading
    import time

    memory_stats = {
        "peak_memory_mb": 0,
        "peak_memory_percent": 0,
        "samples": [],
        "monitoring_active": True,
    }

    def memory_monitor_thread():
        try:
            psutil_process = psutil.Process(process.pid)
            start_time = time.time()

            while memory_stats["monitoring_active"] and process.poll() is None:
                try:
                    # Get memory info for the subprocess
                    mem_info = psutil_process.memory_info()
                    mem_percent = psutil_process.memory_percent()

                    current_memory_mb = mem_info.rss / 1024 / 1024

                    # Track peak usage
                    if current_memory_mb > memory_stats["peak_memory_mb"]:
                        memory_stats["peak_memory_mb"] = current_memory_mb
                        memory_stats["peak_memory_percent"] = mem_percent

                    # Store sample
                    elapsed = time.time() - start_time
                    memory_stats["samples"].append(
                        {
                            "time": elapsed,
                            "memory_mb": current_memory_mb,
                            "memory_percent": mem_percent,
                        }
                    )

                    # Log high memory usage
                    system_memory = psutil.virtual_memory()
                    if current_memory_mb > memory_threshold_mb:
                        logging.warning(
                            f"[{module_name}] HIGH MEMORY: Subprocess using {current_memory_mb:.1f}MB "
                            f"exceeds threshold {memory_threshold_mb}MB ({mem_percent:.1f}%), "
                            f"system at {system_memory.percent:.1f}%"
                        )

                    time.sleep(check_interval)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process ended or no access
                    break

        except Exception as e:
            logging.debug(f"Memory monitoring thread error: {e}")

    # Start monitoring thread
    monitor_thread = threading.Thread(target=memory_monitor_thread, daemon=True)
    monitor_thread.start()

    return memory_stats


def run_subprocess_with_memory_monitoring(
    cmd, module_name, memory_threshold_mb=8192, cwd=None, **kwargs
):
    """Execute subprocess with comprehensive real-time memory monitoring.

    Runs external commands (physics codes) while monitoring their memory consumption.
    Handles subprocess.run() compatibility by filtering arguments and implementing
    equivalent functionality using subprocess.Popen() with memory tracking.

    The function automatically:
    - Converts subprocess.run() arguments for Popen compatibility
    - Starts memory monitoring in a separate thread
    - Tracks peak memory usage throughout execution
    - Generates warnings when memory thresholds are exceeded
    - Implements 'check' behavior for error handling

    Args:
        cmd (list or str): Command and arguments to execute.
        module_name (str): Name of calling module for log identification.
        memory_threshold_mb (int, optional): Memory warning threshold in MB.
            Defaults to 8192 (8GB).
        cwd (str, optional): Working directory for subprocess. Defaults to None.
        **kwargs: Additional subprocess arguments including:
            - check (bool): Raise exception on non-zero return codes
            - capture_output (bool): Capture stdout/stderr to PIPE
            - text (bool): Use text mode for captured output
            - stdout, stderr: Output redirection
            - timeout: Maximum execution time

    Returns:
        tuple: A tuple containing:
            - int: Process return code (0 for success)
            - dict: Memory statistics with peak usage and samples

    Raises:
        subprocess.CalledProcessError: If check=True and process returns non-zero.
        subprocess.TimeoutExpired: If timeout is exceeded.
        KeyboardInterrupt: If interrupted by user (Ctrl+C).

    Example:
        >>> cmd = ['./MUSIChydro', 'input.ini']
        >>> returncode, stats = run_subprocess_with_memory_monitoring(
        ...     cmd, "MUSIC", memory_threshold_mb=4096, check=True
        ... )
        >>> print(f"MUSIC completed, peak memory: {stats['peak_memory_mb']:.1f}MB")

    Note:
        This function replaces direct subprocess.run() calls in physics modules
        to enable memory monitoring of external physics codes.
    """
    import subprocess
    import time

    # Extract subprocess.run() specific arguments that Popen doesn't support
    check = kwargs.pop("check", False)
    capture_output = kwargs.pop("capture_output", False)
    text = kwargs.pop("text", False)

    # Handle capture_output for Popen
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    # Handle text mode
    if text:
        kwargs["text"] = True

    # Start subprocess
    start_time = time.time()
    process = subprocess.Popen(cmd, cwd=cwd, **kwargs)

    logging.info(f"[{module_name}] Started subprocess PID {process.pid}")

    # Start memory monitoring
    memory_stats = monitor_subprocess_memory(
        process, module_name, memory_threshold_mb=memory_threshold_mb
    )

    try:
        # Wait for process to complete and capture output if needed
        if capture_output:
            stdout, stderr = process.communicate()
            return_code = process.returncode
        else:
            stdout, stderr = None, None
            return_code = process.wait()
        end_time = time.time()

        # Stop monitoring
        memory_stats["monitoring_active"] = False

        # Handle check parameter (raise exception if process failed)
        if check and return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)

        # Log results
        execution_time = end_time - start_time
        peak_mb = memory_stats["peak_memory_mb"]

        if peak_mb > 0:
            logging.info(
                f"[{module_name}] Subprocess completed in {execution_time:.2f}s, "
                f"peak memory: {peak_mb:.1f}MB ({memory_stats['peak_memory_percent']:.1f}%)"
            )

            # Warn about high memory usage
            if peak_mb > memory_threshold_mb:
                logging.warning(
                    f"[{module_name}] HIGH MEMORY USAGE: Peak {peak_mb:.1f}MB exceeds threshold {memory_threshold_mb}MB - "
                    f"consider reducing grid size or other parameters"
                )

        # Add captured output to memory_stats if available
        if capture_output:
            memory_stats["stdout"] = stdout
            memory_stats["stderr"] = stderr

        return return_code, memory_stats

    except KeyboardInterrupt:
        logging.warning(
            f"[{module_name}] Subprocess interrupted, terminating..."
        )
        process.terminate()
        memory_stats["monitoring_active"] = False
        raise

    except Exception as e:
        memory_stats["monitoring_active"] = False
        logging.error(f"[{module_name}] Subprocess error: {e}")
        raise


def time_execution(func):
    """Decorator to measure and log function execution time with memory monitoring.

    A function decorator that wraps module methods to automatically measure
    execution time and memory usage. Provides colored log output and memory
    warnings for performance monitoring of physics simulation modules.

    The decorator:
    - Measures total execution time with high precision
    - Monitors memory usage before and after execution
    - Logs results with color-coded formatting
    - Generates warnings for high memory usage
    - Preserves original function metadata

    Args:
        func (callable): The function to be decorated (typically module.run()).

    Returns:
        callable: Wrapped function with timing and memory monitoring.

    Example:
        >>> @time_execution
        ... def run_physics_simulation(self):
        ...     # Physics simulation code
        ...     pass

        >>> # When called, outputs:
        >>> # [MODULE] Starting execution...
        >>> # [MODULE] Completed in 45.32s (Peak memory: 2048.5MB)

    Note:
        Applied to module.run() methods in physics modules to track
        simulation performance and resource usage.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        module_name = self.__class__.__name__

        # Get initial memory state
        start_memory = get_memory_info()
        if start_memory:
            logging.debug(
                f"[{module_name}] {func.__name__} starting - Memory: "
                f"{start_memory['process_rss_mb']:.1f}MB process, "
                f"{start_memory['system_percent']:.1f}% system"
            )

        # Check if we're already close to memory limits
        is_high, memory_info = check_memory_threshold(85)
        if is_high:
            warning_msg = (
                f"[{module_name}] WARNING: High memory usage detected before {func.__name__} "
                f"({memory_info['system_percent']:.1f}% system memory used)"
            )
            colored_warning = Colors.yellow(warning_msg, bold=True)
            logging.warning(colored_warning)

        try:
            result = func(self, *args, **kwargs)
        except MemoryError:
            error_memory = get_memory_info()
            error_msg = f"[{module_name}] MEMORY ERROR in {func.__name__}!"
            if error_memory:
                error_msg += (
                    f" Process was using {error_memory['process_rss_mb']:.1f}MB, "
                    f"system at {error_memory['system_percent']:.1f}%"
                )
            colored_error = Colors.red(error_msg, bold=True)
            logging.error(colored_error)
            raise
        except Exception as e:
            # Check if this might be a hidden memory error
            current_memory = get_memory_info()
            if current_memory and current_memory["system_percent"] > 95:
                memory_warning = (
                    f"[{module_name}] ERROR occurred with very high memory usage "
                    f"({current_memory['system_percent']:.1f}%) - possible memory issue"
                )
                colored_warning = Colors.red(memory_warning, bold=True)
                logging.error(colored_warning)
            raise

        end_time = time.time()
        execution_time = end_time - start_time

        # Get final memory state
        end_memory = get_memory_info()

        # Create completion message with memory info
        message = f"[{module_name}] {func.__name__} completed in {execution_time:.3f} seconds"

        if start_memory and end_memory:
            memory_diff = (
                end_memory["process_rss_mb"] - start_memory["process_rss_mb"]
            )
            if abs(memory_diff) > 10:  # Only show if significant change (>10MB)
                message += f" (Δ memory: {memory_diff:+.1f}MB)"

        colored_message = Colors.green(message, bold=True)
        logging.info(colored_message)

        # Warn about high memory usage at completion
        if end_memory:
            is_high, _ = check_memory_threshold(90)
            if is_high:
                warning_msg = (
                    f"[{module_name}] WARNING: High memory usage after {func.__name__} "
                    f"({end_memory['system_percent']:.1f}% system, "
                    f"{end_memory['process_rss_mb']:.1f}MB process)"
                )
                colored_warning = Colors.yellow(warning_msg, bold=True)
                logging.warning(colored_warning)

        return result

    return wrapper


def run_external_command(
    cmd,
    module_name,
    memory_threshold_mb=None,
    cwd=None,
    suppress_output=False,
    timeout=None,
    **kwargs,
):
    """
    Enhanced subprocess runner with memory monitoring for external codes.

    This should be used by modules instead of subprocess.run() to get memory monitoring.

    Args:
        cmd: Command to run (list)
        module_name: Name of calling module
        memory_threshold_mb: Memory threshold in MB for alerts (default: 8192 MB = 8 GB)
        cwd: Working directory
        suppress_output: Whether to suppress stdout/stderr
        timeout: Command timeout in seconds
        **kwargs: Additional arguments passed to subprocess

    Returns:
        dict: Execution results including memory stats
    """
    import subprocess

    # Set default memory threshold if not provided
    if memory_threshold_mb is None:
        memory_threshold_mb = 8192  # Default to 8GB

    # Set up subprocess arguments
    run_kwargs = kwargs.copy()  # Include any additional kwargs
    if suppress_output:
        run_kwargs.update(
            {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        )

    if timeout:
        run_kwargs["timeout"] = timeout

    logging.info(f"[{module_name}] Running external command: {' '.join(cmd)}")
    logging.debug(f"[{module_name}] Memory threshold: {memory_threshold_mb} MB")

    try:
        # Use memory monitoring subprocess runner
        return_code, memory_stats = run_subprocess_with_memory_monitoring(
            cmd,
            module_name,
            memory_threshold_mb=memory_threshold_mb,
            cwd=cwd,
            **run_kwargs,
        )

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)

        result = {
            "return_code": return_code,
            "peak_memory_mb": memory_stats["peak_memory_mb"],
            "peak_memory_percent": memory_stats["peak_memory_percent"],
            "memory_samples": len(memory_stats["samples"]),
            "success": True,
        }

        # Include captured output if available
        if "stdout" in memory_stats:
            result["stdout"] = memory_stats["stdout"]
        if "stderr" in memory_stats:
            result["stderr"] = memory_stats["stderr"]

        return result

    except subprocess.TimeoutExpired as e:
        logging.error(f"[{module_name}] Command timed out after {timeout}s")
        raise

    except subprocess.CalledProcessError as e:
        peak_mb = (
            memory_stats.get("peak_memory_mb", 0)
            if "memory_stats" in locals()
            else 0
        )
        logging.error(
            f"[{module_name}] Command failed (exit code {e.returncode})"
        )
        if peak_mb > 0:
            logging.error(
                f"[{module_name}] Memory usage at failure: {peak_mb:.1f}MB"
            )
        raise


class BaseModule(ABC):
    """Abstract base class for all physics simulation modules in CRONOS framework.

    Defines the standard interface and lifecycle for physics modules including
    initial conditions, pre-equilibrium evolution, hydrodynamics, particlization,
    and afterburner components. All modules must implement the core lifecycle methods.

    The module lifecycle consists of four phases:
    1. Environment preparation (linking executables, creating directories)
    2. Input preparation (generating parameter files, linking data)
    3. Execution (running physics codes with memory monitoring)
    4. Output handling (collecting results, cleanup)

    Attributes:
        config: Module-specific configuration parameters
        full_config: Complete simulation configuration (all modules)
        project_root: Path to CRONOS project root directory
        event_id: Unique identifier for current simulation event

    Example:
        >>> class MUSIC(BaseModule):
        ...     def prepare_environment(self, event_dir):
        ...         # Link MUSIC executable and EOS tables
        ...         pass
        ...     def prepare_input(self, event_dir):
        ...         # Generate MUSIC parameter file
        ...         pass
        ...     def run(self, event_dir):
        ...         # Execute MUSIC hydrodynamics
        ...         pass
        ...     def fetch_output(self, event_dir):
        ...         # Collect freeze-out surface
        ...         pass
    """

    def __init__(
        self, config, full_config=None, project_root=None, event_id=None
    ):
        """Initialize base module with configuration and runtime parameters.

        Args:
            config: Module-specific configuration dictionary containing parameters
                for this physics module (e.g., MUSIC config, SMASH config).
            full_config: Complete simulation configuration containing all modules
                and general settings. Used for cross-module coordination.
            project_root (str, optional): Absolute path to CRONOS project root.
                Used for locating external codes and utilities.
            event_id (str, optional): Unique identifier for current simulation event.
                Used in output file naming and logging.
        """
        self.config = config
        self.full_config = full_config
        self.project_root = project_root
        self.event_id = event_id

    @abstractmethod
    def prepare_environment(self, event_dir):
        """Prepare the execution environment for this physics module.

        Sets up the necessary environment for module execution including:
        - Creating module-specific directory structure
        - Linking external executables and libraries
        - Setting up data tables and equation of state files
        - Configuring any required symlinks or environment variables

        This method is called before prepare_input() and should ensure all
        external dependencies are properly accessible for the module.

        Args:
            event_dir (str): Path to event-specific directory where the module
                will execute. Module should create its subdirectory here.

        Raises:
            SystemExit: If required executables or data files are missing.

        Example:
            >>> def prepare_environment(self, event_dir):
            ...     music_dir = os.path.join(event_dir, "MUSIC")
            ...     os.makedirs(music_dir, exist_ok=True)
            ...     # Link MUSIC executable
            ...     os.symlink(exe_path, os.path.join(music_dir, "MUSIChydro"))
        """
        pass

    @abstractmethod
    def prepare_input(self, event_dir):
        """Generate input files and link data required for module execution.

        Creates module-specific input files and establishes links to data from
        previous modules in the simulation chain. This includes:
        - Generating parameter/configuration files from module config
        - Linking output from previous modules as input
        - Setting up initial conditions or boundary conditions
        - Preparing any module-specific data transformations

        This method is called after prepare_environment() and before run().

        Args:
            event_dir (str): Path to event-specific directory containing module
                subdirectories and results from previous modules.

        Example:
            >>> def prepare_input(self, event_dir):
            ...     # Link previous module output
            ...     input_file = os.path.join(event_dir, "results", "output_1.dat")
            ...     os.symlink(input_file, os.path.join(module_dir, "input.dat"))
            ...     # Generate parameter file
            ...     with open("parameters.ini", "w") as f:
            ...         f.write(f"temperature = {self.config.temperature}\n")
        """
        pass

    @abstractmethod
    def run(self, event_dir):
        """Execute the physics simulation for this module.

        Performs the main computation/simulation work of the module. This typically
        involves running external physics codes with memory monitoring, but can also
        include pure Python calculations. The method should:
        - Execute the physics simulation with appropriate parameters
        - Use run_external_command() for external executables to enable memory monitoring
        - Handle execution errors appropriately
        - Log execution progress and results

        This method is decorated with @time_execution to automatically measure
        execution time and peak memory usage.

        Args:
            event_dir (str): Path to event-specific directory where module
                operates and finds its input data.

        Raises:
            subprocess.CalledProcessError: If external physics code fails.
            RuntimeError: If module execution encounters critical errors.

        Example:
            >>> @time_execution
            ... def run(self, event_dir):
            ...     music_dir = os.path.join(event_dir, "MUSIC")
            ...     result = run_external_command(
            ...         ["./MUSIChydro", "parameters.ini"],
            ...         module_name="MUSIC",
            ...         cwd=music_dir,
            ...         check=True
            ...     )
        """
        pass

    @abstractmethod
    def fetch_output(self, event_dir):
        """Collect, organize, and store module output for subsequent processing.

        Handles post-execution tasks including:
        - Moving/copying output files to standardized locations
        - Renaming files according to CRONOS conventions
        - Cleaning up temporary files and directories
        - Preparing output for next module in simulation chain
        - Organizing results for final HDF5 packaging

        Output files are typically moved to the event_dir/results/ directory
        with standardized naming (e.g., output_N.dat where N is module index).

        Args:
            event_dir (str): Path to event-specific directory where module
                executed and where results should be organized.

        Example:
            >>> def fetch_output(self, event_dir):
            ...     # Move output to standard location
            ...     src = os.path.join(event_dir, "MUSIC", "surface.dat")
            ...     dst = os.path.join(event_dir, "results", "output_2.dat")
            ...     shutil.move(src, dst)
            ...     # Clean up temporary directory
            ...     shutil.rmtree(os.path.join(event_dir, "MUSIC"))
            ...     logging.info(f"MUSIC output moved to {dst}")
        """
        pass
