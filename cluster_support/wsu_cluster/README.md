# CRONOS on WSU Cluster

This document describes how to run CRONOS on the WSU cluster using the Apptainer (Singularity-compatible) container and the `wsu` cluster option.

## 1. Load modules and obtain the Apptainer image

On the WSU cluster, first load the required modules and then pull the CRONOS image with Apptainer:

```bash
module load gnu9/9.1.0
module load apptainer/1.3.0

# Example: pull from a registry (adjust to your image name)
apptainer pull cronos.sif docker://hendrik1704/cronos:latest
```

Copy `cronos.sif` to a location accessible from the WSU cluster (e.g. your `$HOME` or project space).

## 2. Clone CRONOS and prepare simulations

On the WSU cluster:

```bash
git clone https://github.com/Hendrik1704/CRONOS.git
cd CRONOS

# (Optional) create and activate a Python environment if needed
# module load python
# python -m venv venv
# source venv/bin/activate

# Prepare a run directory and jobs (host Python)
python3 prepare_simulations.py \
  --main_config_path config/main_config.py \
  --user_config_path config/user_config_ipglasma.py \
  --run_dir run_wsu \
  --cluster wsu

# Alternatively, prepare directly inside the Apptainer container
export CRONOS_SIF=/path/to/cronos.sif
apptainer exec "$CRONOS_SIF" python3 /app/prepare_simulations.py \
  --main_config_path config/main_config.py \
  --user_config_path config/user_config_ipglasma.py \
  --run_dir run_wsu \
  --cluster wsu
```

This will create `run_wsu/` with `job_*` subdirectories and a `submit_job.sh` tailored for the WSU cluster.

## 3. Point CRONOS to your Apptainer image

The WSU submission script uses the environment variable `CRONOS_SIF` to locate the Apptainer/Singularity image. If `CRONOS_SIF` is not set, it defaults to `cronos.sif` in the submission directory.

Typical setup:

```bash
# In your shell before submitting
export CRONOS_SIF=/path/to/cronos.sif
```

## 4. Submit jobs on WSU

Change into the run directory created by `prepare_simulations.py` and submit the SLURM array job:

```bash
cd run_wsu
sbatch submit_job.sh
```

The script will:
- Load the `gnu9/9.1.0` and `apptainer/1.3.0` modules
- Use `CRONOS_SIF` (or `cronos.sif` if unset)
- Run `python3 /app/run_simulations.py` inside the Apptainer container for each `job_$SLURM_ARRAY_TASK_ID`
- Forward your `--main_config_path` and `--user_config_path` to the container

## 5. Memory and requeue behaviour

- The script reads `general["memory_threshold_mb"]` from your config and uses it as the SLURM `--mem` request.
- The `requeue` queue (or similar) can be used to allow jobs to be preempted and restarted. CRONOS checkpoints each job in `.cronos_checkpoint.json` inside the `job_*` directory.
- When a job is requeued and restarted, `run_simulations.py` detects the existing checkpoint and resumes from the last completed module/event.

## 6. Logs and troubleshooting

- SLURM stdout and stderr for each array task are written to the `log/` directory as `output_<jobid>_<arrayid>.log` and `error_<jobid>_<arrayid>.log`.
- Inside those logs you will see CRONOS messages about checkpoints, module progress, and any errors from the external codes.

If you need cluster-specific changes (account name, partition, time limit), edit `submit_job.sh` after generation or adjust `create_wsu_submission_script` in `src/cluster_submission.py` accordingly.
