"""SLURM Cluster Submission Script Generation for CRONOS Simulations.

This module generates cluster-specific job submission scripts for CRONOS heavy-ion
collision simulations, enabling scalable execution on HPC systems via SLURM job
arrays. It handles environment setup, module loading, and job array configuration
for production simulation workflows.

Supported Clusters:
    - noctua2: Paderborn University HPC cluster with specific module environment
    - local: Local execution (no submission script generated)

Features:
- Automatic job array size calculation based on prepared job directories
- Cluster-specific environment module loading
- SLURM job array configuration with proper resource allocation
- Integration with CRONOS directory structure and configuration system
- Colored terminal feedback for script generation status

Generated Scripts:
    Creates submit_job.sh in the run directory with:
    - SLURM directives for job arrays, resources, and logging
    - Environment module loading for target cluster
    - Python dependency installation
    - Job array task mapping to CRONOS job directories
    - Proper working directory and path management

Usage:
    Called automatically by prepare_simulations.py during environment setup:

    submission_script_cluster(args, config)

    The function detects cluster type from args.cluster and generates
    appropriate submission script or provides local execution guidance.

Integration:
    - Used in prepare_simulations.py after job directory creation
    - Integrates with CRONOS configuration and argument parsing
    - Supports checkpoint-enabled simulation execution
    - Compatible with SLURM job resubmission workflows

Author: CRONOS Development Team
Requires: SLURM workload manager (for cluster execution)
"""

from .colors import Colors
import logging
import os


def create_noctua2_submission_script(args):
    """Generate SLURM submission script specifically configured for Noctua2 cluster.

    Creates a complete SLURM job array submission script optimized for the
    Noctua2 HPC system at Paderborn University. Handles environment module
    loading, resource allocation, and job array configuration for CRONOS
    heavy-ion collision simulation workflows.

    Noctua2 Configuration:
    - Account: hpc-prf-flucurhi (research group allocation)
    - Partition: normal (standard compute nodes)
    - Resources: 1 node, 1 core per job (serial physics codes)
    - Time limit: 40 hours (typical collision simulation duration)
    - Array size: Automatically determined from job_* directories

    Environment Setup:
    - GCC 11.3.0 compiler toolchain
    - OpenMPI 4.1.4 for parallel components
    - Python 3.10.4 with h5py for data processing
    - GSL 2.7 for numerical computations
    - CMake 3.23.1 for build system support
    - FFTW 3.3.10 for fast Fourier transforms

    Args:
        args (argparse.Namespace): Command-line arguments containing:
            - run_dir (str): Base directory containing job_* subdirectories
            - main_config_path (str): Path to main CRONOS configuration
            - user_config_path (str): Path to user-specific configuration

    Side Effects:
        - Creates submit_job.sh in args.run_dir
        - Counts existing job_* directories to set array size
        - Generates SLURM directives for proper job array execution
        - Sets up environment modules and Python dependencies
        - Configures job array task to directory mapping

    Generated Script Features:
        - SLURM array job with proper resource requests
        - Separate stdout/stderr logging per array task
        - Environment module loading for Noctua2 specifications
        - Python dependency installation (h5py for data output)
        - OMP thread limitation for reproducible execution
        - Working directory management for relative paths
        - Integration with run_simulations.py execution

    Example Generated Script:
        #!/bin/bash
        #SBATCH -J CRONOS
        #SBATCH -A hpc-prf-flucurhi
        #SBATCH --array=0-99
        #SBATCH -t 40:00:00
        ...
        python ../run_simulations.py --job_dir job_$SLURM_ARRAY_TASK_ID/

    Notes:
        - Each array task executes one job_* directory independently
        - Supports checkpoint-based resumption for fault tolerance
        - Optimized for memory-intensive heavy-ion collision simulations
    """
    run_dir = args.run_dir
    slurm_logging_dir = "log"

    # open a file in the run_dir
    script_path = f"{run_dir}/submit_job.sh"

    # Count the number of job_ directories in the run_dir
    job_dirs = [
        d
        for d in os.listdir(run_dir)
        if os.path.isdir(os.path.join(run_dir, d)) and d.startswith("job_")
    ]
    num_jobs_found = len(job_dirs)

    with open(script_path, "w") as script_file:
        script_file.write("#!/bin/bash\n")
        script_file.write(f"#SBATCH -J CRONOS\n")
        script_file.write(f"#SBATCH -A hpc-prf-flucurhi\n")
        script_file.write(f"#SBATCH -o {slurm_logging_dir}/output_%A_%a.log\n")
        script_file.write(f"#SBATCH -e {slurm_logging_dir}/error_%A_%a.log\n")
        script_file.write(f"#SBATCH -t 40:00:00\n")
        script_file.write(f"#SBATCH -p normal\n")
        script_file.write(f"#SBATCH -N 1\n")
        script_file.write(f"#SBATCH -n 1\n")
        script_file.write(f"#SBATCH --array=0-{num_jobs_found - 1}\n\n")

        script_file.write("module purge\n")
        script_file.write("module load compiler/GCC/11.3.0\n")
        script_file.write("module load compiler/GCCcore/11.3.0\n")
        script_file.write("module load tools/binutils/2.38-GCCcore-11.3.0\n")
        script_file.write("module load lib/zlib/1.2.12-GCCcore-11.3.0\n")
        script_file.write("module load numlib/GSL/2.7-GCC-11.3.0\n")
        script_file.write("module load mpi/OpenMPI/4.1.4-GCC-11.3.0\n")
        script_file.write("module load devel/CMake/3.23.1-GCCcore-11.3.0\n")
        script_file.write("module load lang/Python/3.10.4-GCCcore-11.3.0\n")
        script_file.write("module load numlib/FFTW/3.3.10-GCC-12.3.0\n\n")

        # Implement that each array task runs one of the job_directories in the run_dir
        script_file.write("cd $SLURM_SUBMIT_DIR\n")
        script_file.write(
            'echo "Running job in directory: job_$SLURM_ARRAY_TASK_ID"\n'
        )

        script_file.write(
            f"python ../run_simulations.py --main_config_path ../{args.main_config_path} --user_config_path ../{args.user_config_path} --job_dir job_$SLURM_ARRAY_TASK_ID/\n"
        )


def create_wsu_submission_script(args, config):
    """Generate SLURM submission script configured for the WSU cluster using Apptainer.

    This script assumes that:
    - You have a CRONOS Apptainer/Singularity image (cronos.sif) accessible from the
        run directory or via the CRONOS_SIF environment variable.
    - The container image contains the CRONOS framework under /app.

    The script will run each job_* directory via an Apptainer exec
    call that forwards the configuration paths from the command-line
    arguments (args.main_config_path, args.user_config_path),
    analogous to the noctua2 submission script.
    """
    run_dir = args.run_dir
    slurm_logging_dir = "log"

    script_path = f"{run_dir}/submit_job.sh"

    job_dirs = [
        d
        for d in os.listdir(run_dir)
        if os.path.isdir(os.path.join(run_dir, d)) and d.startswith("job_")
    ]
    num_jobs_found = len(job_dirs)

    # Try to read memory threshold from configuration; if present, use it
    # as the SLURM memory request in megabytes.
    memory_mb = None
    try:
        general_cfg = config.general
        try:
            memory_mb = general_cfg.memory_threshold_mb
        except AttributeError:
            memory_mb = None
    except AttributeError:
        memory_mb = None

    with open(script_path, "w") as script_file:
        script_file.write("#!/bin/bash\n")
        script_file.write("#SBATCH -J CRONOS\n")
        script_file.write(f"#SBATCH -o {slurm_logging_dir}/output_%A_%a.log\n")
        script_file.write(f"#SBATCH -e {slurm_logging_dir}/error_%A_%a.log\n")
        script_file.write("#SBATCH -t 48:00:00\n")
        script_file.write("#SBATCH -q requeue\n")
        script_file.write("#SBATCH -N 1\n")
        script_file.write("#SBATCH -n 1\n")
        if memory_mb is not None:
            script_file.write(f"#SBATCH --mem={memory_mb}\n")
        script_file.write(f"#SBATCH --array=0-{num_jobs_found - 1}\n\n")

        script_file.write("module purge\n")
        script_file.write("module load gnu9/9.1.0\n")
        script_file.write("module load apptainer/1.3.0\n\n")

        script_file.write("cd $SLURM_SUBMIT_DIR\n")
        script_file.write(
            'echo "Running job in directory: job_$SLURM_ARRAY_TASK_ID"\n'
        )

        script_file.write('SIF_IMAGE="${CRONOS_SIF:-cronos.sif}"\n')

        script_file.write(
            f'apptainer exec "$SIF_IMAGE" python3 /app/run_simulations.py '
        )
        script_file.write(f"--main_config_path ../{args.main_config_path} ")
        script_file.write(f"--user_config_path ../{args.user_config_path} ")
        script_file.write("--job_dir job_$SLURM_ARRAY_TASK_ID/\n")


def submission_script_cluster(args, config):
    """Generate appropriate cluster submission script based on target environment.

    Main entry point for cluster submission script generation that dispatches
    to cluster-specific functions based on the target environment. Provides
    colored terminal feedback and handles both local and cluster execution
    scenarios for CRONOS simulation workflows.

    Supported Environments:
    - 'local': Local machine execution (no script generated)
    - 'noctua2': Paderborn University HPC cluster
    - Future: Extensible to additional cluster environments

    Args:
        args (argparse.Namespace): Command-line arguments from prepare_simulations.py:
            - cluster (str): Target cluster name ('local', 'noctua2', etc.)
            - run_dir (str): Directory containing prepared job structure
            - Configuration file paths for script generation
        config (Configuration): CRONOS configuration object (currently unused
            but available for future cluster-specific customization)

    Side Effects:
        - Calls cluster-specific script generation functions
        - Prints colored status messages via Colors utility
        - Creates submission scripts in run directory (cluster-dependent)
        - Logs informational or error messages based on cluster support

    Behavior by Cluster:
        'local':
            - Logs yellow informational message about local execution
            - No submission script created (direct Python execution expected)

        'noctua2':
            - Calls create_noctua2_submission_script() for SLURM generation
            - Creates submit_job.sh with proper Noctua2 configuration

        Unsupported:
            - Logs red error message with supported cluster list
            - Does not create submission script or exit program

    Example Usage:
        >>> args = argparse.Namespace(cluster='noctua2', run_dir='run/')
        >>> config = load_config('config/main.py', 'config/user.py')
        >>> submission_script_cluster(args, config)
        # Creates run/submit_job.sh with Noctua2 SLURM configuration

    Extension Pattern:
        To add new cluster support:
        1. Create cluster-specific function (e.g., create_noctua2_script)
        2. Add elif branch with cluster name check
        3. Call cluster-specific function with appropriate parameters
        4. Update supported cluster documentation

    Integration:
        - Called at end of prepare_modules() after job directory creation
        - Enables seamless transition from preparation to execution phase
        - Supports both interactive and automated workflow management
    """
    cluster_name = args.cluster

    if cluster_name == "local":
        message = (
            "Cluster is set to 'local'; no submission script will be created."
        )
        colored_message = Colors.yellow(message, bold=True)
        logging.info(colored_message)
        pass
    elif cluster_name == "noctua2":
        create_noctua2_submission_script(args)
        message = (
            f"SLURM submission script created for '{cluster_name}' cluster."
        )
        colored_message = Colors.green(message, bold=True)
        logging.info(colored_message)
    elif cluster_name == "wsu":
        create_wsu_submission_script(args, config)
        message = (
            f"SLURM submission script created for '{cluster_name}' cluster."
        )
        colored_message = Colors.green(message, bold=True)
        logging.info(colored_message)
    else:
        message = f"Cluster '{cluster_name}' is not supported."
        colored_message = Colors.red(message, bold=True)
        logging.error(colored_message)
