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

## 5. Collect simulation output into a single HDF5 database

After all jobs have finished successfully, the individual event output files (`event_*.h5`) can be merged into a single HDF5 database for convenient analysis.

Run the collection utility inside the Apptainer container:

```bash
apptainer exec \
    --bind $(pwd):/work \
    ./cronos.sif \
    python3 /app/utilities/event_database.py \
    build \
    --pattern "/work/run_wsu/job_*/event_*.h5" \
    --out "/work/run_wsu/merged_events.h5" \
    --validate
```

This command

* searches for all event HDF5 files inside `run_wsu/job_*/`,
* validates that each event contains the required analysis datasets,
* copies all valid events into a single file `merged_events.h5`, and
* skips incomplete or corrupted events.

The resulting database has the structure

```
merged_events.h5
├── job_0
│   ├── event_0
│   ├── event_1
│   └── ...
├── job_1
│   └── ...
└── ...
```

### Optional: delete per-event files after merging

To save disk space, the original event files can be removed automatically after they have been successfully copied:

```bash
apptainer exec \
    --bind $(pwd):/work \
    ./cronos.sif \
    python3 /app/utilities/event_database.py \
    build \
    --pattern "/work/run_wsu/job_*/event_*.h5" \
    --out "/work/run_wsu/merged_events.h5" \
    --validate \
    --delete-source
```

Only successfully copied event files are deleted. Events that fail validation or cannot be copied are left untouched.

## 6. Bin events into centrality classes

CRONOS provides a utility to classify events into centrality bins based on the charged-particle multiplicity.

The centrality estimator is

* dataset: `particle_9999_vndata_eta_-0.5_0.5.dat`
* row with `n = 0`
* value of `Q0_real`, corresponding to the charged-particle multiplicity (`N_\mathrm{ch}` or `dN/dy`).

Events are sorted by decreasing multiplicity (most central first), and percentile cuts are applied to define the centrality classes.

### Create centrality bin lists

The following command creates one text file for each centrality class containing the event filename and its multiplicity:

```bash
apptainer exec \
    --bind $(pwd):/work \
    ./cronos.sif \
    python3 /app/utilities/centrality_binning.py \
    /work/run_wsu \
    --pattern "/work/run_wsu/job_*/event_*.h5" \
    --out-dir "/work/run_wsu/centrality_bins"
```

This produces

```text
run_wsu/
└── centrality_bins/
    ├── C0-5.txt
    ├── C5-10.txt
    ├── C10-20.txt
    ├── ...
    └── C90-100.txt
```

Each file contains the absolute path to every event in the corresponding centrality class together with its charged-particle multiplicity.

### Create centrality directories

For many analysis workflows it is convenient to have one directory per centrality class containing symbolic links to the corresponding event files while preserving the original job structure.

This can be done with

```bash
apptainer exec \
    --bind $(pwd):/work \
    ./cronos.sif \
    python3 /app/utilities/centrality_binning.py \
    /work/run_wsu \
    --pattern "/work/run_wsu/job_*/event_*.h5" \
    --out-dir "/work/run_wsu/centrality_bins" \
    --link symlink
```

This creates a directory structure such as

```text
run_wsu/
└── centrality_bins/
    ├── C0-5.txt
    ├── C0-5/
    │   ├── job_0/
    │   │   ├── event_0.h5 -> ../../../job_0/event_0.h5
    │   │   ├── event_1.h5 -> ../../../job_0/event_1.h5
    │   │   └── ...
    │   ├── job_1/
    │   │   ├── event_0.h5 -> ../../../job_1/event_0.h5
    │   │   └── ...
    │   └── ...
    ├── C5-10.txt
    ├── C5-10/
    │   ├── job_0/
    │   ├── job_1/
    │   └── ...
    └── ...
```

The original `job_*` directory structure is preserved inside each centrality class to avoid filename collisions, since every simulation job typically produces files with the same event names (e.g. `event_0.h5`, `event_1.h5`, ...).

Instead of symbolic links, physical copies of the event files can be created by replacing

```bash
--link symlink
```

with

```bash
--link copy
```

### Custom centrality definitions

By default the centrality classes are

```text
0–5, 5–10, 10–20, 20–30, 30–40,
40–50, 50–60, 60–70, 70–80,
80–90, 90–100%
```

Custom percentile boundaries can be specified using, for example,

```bash
--cuts 0 1 5 10 20 40 60 80 100
```

to generate the bins

```text
0–1, 1–5, 5–10, 10–20, 20–40, 40–60, 60–80, 80–100%
```