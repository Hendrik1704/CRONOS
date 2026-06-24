# CRONOS on WSU Cluster

This document describes how to run CRONOS on the WSU cluster using the Apptainer (Singularity-compatible) container and the `wsu` cluster option.

## 0. Load modules and obtain the Apptainer image

On the WSU cluster, first load the required modules and then pull the CRONOS image with Apptainer:

```bash
module purge
module load gnu9/9.1.0
module load apptainer/1.3.0

# Example: pull from a registry (adjust to your image name)
apptainer pull cronos.sif docker://hendrik1704/cronos:latest
```
Or use the hash of the container image you want to pull, usually `latest` or `devel`.

Place `cronos.sif` either in the CRONOS repository root or inside the run directory, or set `CRONOS_SIF` explicitly.

## 1. Clone CRONOS and prepare simulations

On the WSU cluster:

```bash
git clone https://github.com/Hendrik1704/CRONOS.git -b main
cd CRONOS
```
Prepare your user configuration, e.g. `config/user_config_ipglasma.py`, and adjust it as needed.
The `main_config.py` should usually not be modified, but you can override settings in your user config.

```bash
# Prepare a run directory and jobs (executed inside container for consistency)
apptainer exec \
    --bind $(pwd):/work \
    ./cronos.sif \
    python3 /app/prepare_simulations.py \
    --main_config_path /work/config/main_config.py \
    --user_config_path /work/config/user_config_ipglasma.py \
    --run_dir /work/run_wsu \
    --cluster wsu
```
Note: `/work` is the mounted repository root inside the container.

This will create `run_wsu/` with `job_*` subdirectories and a `submit_job.sh` tailored for the WSU cluster.
The SLURM submission script automatically binds the repository root to `/work` during execution. No manual binding is required when running jobs.

## 2. Submit jobs on WSU

Change into the run directory created by `prepare_simulations.py` and submit the SLURM array job:

```bash
cd run_wsu
sbatch submit_job.sh
```

The script will:
- Load required modules (`gnu9/9.1.0`, `apptainer/1.3.0`)
- Execute `python3 /app/run_simulations.py` inside the container for each SLURM array task (`job_$SLURM_ARRAY_TASK_ID`)
- Pass `--main_config_path` and `--user_config_path` from `/work/config/`

## 3. Memory and requeue behaviour

- The script reads `general["memory_threshold_mb"]` from your config and uses it as the SLURM `--mem` request.
- The `requeue` queue (or similar) can be used to allow jobs to be preempted and restarted. CRONOS checkpoints each job in `.cronos_checkpoint.json` inside the `job_*` directory.
- When a job is requeued and restarted, `run_simulations.py` detects the existing checkpoint and resumes from the last completed module/event.

## 4. Logs and troubleshooting

- SLURM stdout and stderr for each array task are written to the `log/` directory as `output_<jobid>_<arrayid>.log` and `error_<jobid>_<arrayid>.log`.
- Inside those logs you will see CRONOS messages about checkpoints, module progress, and any errors from the external codes.
