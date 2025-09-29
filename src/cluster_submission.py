from .colors import Colors
import logging
import os


def create_noctua1_submission_script(args):
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
        script_file.write(f"#SBATCH -o {slurm_logging_dir}/output.log\n")
        script_file.write(f"#SBATCH -e {slurm_logging_dir}/error.log\n")
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
        script_file.write("module load lang/Python/3.10.4-GCCcore-11.3.0\n\n")

        script_file.write("pip install h5py\n")

        # Implement that each array task runs one of the job_ directories in the run_dir
        script_file.write("export OMP_NUM_THREADS=1\n")
        script_file.write("cd $SLURM_SUBMIT_DIR\n")
        script_file.write(
            'echo "Running job in directory: job_$SLURM_ARRAY_TASK_ID"\n'
        )

        script_file.write(
            f"python ../run_simulations.py --main_config_path ../{args.main_config_path} --user_config_path ../{args.user_config_path} --job_dir job_$SLURM_ARRAY_TASK_ID/\n"
        )


def submission_script_cluster(args, config):
    cluster_name = args.cluster

    if cluster_name == "local":
        message = (
            "Cluster is set to 'local'; no submission script will be created."
        )
        colored_message = Colors.yellow(message, bold=True)
        logging.info(colored_message)
        pass
    elif cluster_name == "noctua1":
        create_noctua1_submission_script(args)
        message
    else:
        message = f"Cluster '{cluster_name}' is not supported."
        colored_message = Colors.red(message, bold=True)
        logging.error(colored_message)
