from abc import ABC, abstractmethod
import time
import logging
import psutil
import os
import signal
from functools import wraps
from .colors import Colors


def get_memory_info():
    """Get current memory usage information."""
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
    """Check if memory usage exceeds threshold."""
    memory_info = get_memory_info()
    if memory_info and memory_info["system_percent"] > threshold_percent:
        return True, memory_info
    return False, memory_info


def monitor_subprocess_memory(
    process, module_name, memory_threshold_mb=8192, check_interval=2
):
    """
    Monitor memory usage of a running subprocess.

    Args:
        process: subprocess.Popen object
        module_name: Name of the module for logging
        memory_threshold_mb: Memory threshold in MB for warnings (default: 8GB)
        check_interval: How often to check memory (seconds)

    Returns:
        dict: Memory usage statistics
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
    """
    Run subprocess with memory monitoring.

    Args:
        cmd: Command to run (list or string)
        module_name: Name of module for logging
        memory_threshold_mb: Memory threshold in MB for warnings (default: 8GB)
        cwd: Working directory
        **kwargs: Additional subprocess arguments

    Returns:
        tuple: (return_code, memory_stats)
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
        # Wait for process to complete
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
    """Decorator to measure execution time and monitor memory usage."""

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

        return {
            "return_code": return_code,
            "peak_memory_mb": memory_stats["peak_memory_mb"],
            "peak_memory_percent": memory_stats["peak_memory_percent"],
            "memory_samples": len(memory_stats["samples"]),
            "success": True,
        }

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
    """
    Abstract base class for all modules in the framework.
    Each module must implement the three lifecycle methods:
    - prepare_input()
    - run()
    - fetch_output()
    """

    def __init__(
        self, config, full_config=None, project_root=None, event_id=None
    ):
        self.config = config
        self.full_config = full_config
        self.project_root = project_root
        self.event_id = event_id

    @abstractmethod
    def prepare_environment(self, event_dir):
        """Prepare the execution environment for this module."""
        pass

    @abstractmethod
    def prepare_input(self, event_dir):
        """Prepare all necessary input files/data for this module."""
        pass

    @abstractmethod
    def run(self, event_dir):
        """Execute the module (Python code, C++ binary, etc.)."""
        pass

    @abstractmethod
    def fetch_output(self, event_dir):
        """Collect and store the results of the module."""
        pass
