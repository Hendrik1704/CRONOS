# CRONOS on Noctua2 (PC² Paderborn)

This document describes how to install and run CRONOS on the [Noctua2](https://pc2.uni-paderborn.de/hpc-services/available-systems/noctua2) cluster at Paderborn Center for Parallel Computing (PC²).

## 0. Clone CRONOS

```bash
git clone https://github.com/Hendrik1704/CRONOS.git -b main
cd CRONOS
```

## 1. Install external codes

A SLURM installation script is provided that loads the required modules and compiles all external codes:

```bash
cd external_codes/
sbatch ../cluster_support/noctua2/noctua2_install.sh
```

The script loads the following modules and runs the compilation:

```
numlib/GSL/2.7-GCC-11.3.0
compiler/GCC/11.3.0
compiler/GCCcore/11.3.0
devel/CMake/3.23.1-GCCcore-11.3.0
mpi/OpenMPI/4.1.4-GCC-11.3.0
lib/zlib/1.2.12-GCCcore-11.3.0
tools/binutils/2.38-GCCcore-11.3.0
lang/Python/3.10.4-GCCcore-11.3.0
numlib/FFTW/3.3.10-GCC-12.3.0
```

It then calls `GetModulesFromGit.sh` and `CompileFramework.sh` automatically. The job requests 10 cores on the `normal` partition with a 15-minute wall time.

## 2. Prepare simulations

Adjust your user configuration (e.g. `config/user_config_ipglasma.py`) and prepare a run directory:

```bash
python3 prepare_simulations.py \
    --main_config_path config/main_config.py \
    --user_config_path config/user_config_ipglasma.py \
    --run_dir run/ \
    --cluster noctua2
```

This creates `run/` with `job_*` subdirectories and a `submit_job.sh` tailored for Noctua2.

## 3. Submit jobs

```bash
cd run/
sbatch submit_job.sh
```

CRONOS checkpoints each job in `.cronos_checkpoint.json` inside the `job_*` directory. If a job is requeued or fails, resubmitting will resume from the last completed module.

## 4. Logs and troubleshooting

SLURM stdout and stderr for each array task are written to `log/` as:
- `output_<jobid>_<arrayid>.log`
- `error_<jobid>_<arrayid>.log`

## 5. Collect simulation output

After all jobs finish, merge the per-event HDF5 files into a single database:

```bash
python3 utilities/event_database.py build \
    --pattern 'run/job_*/event_*.h5' \
    --out run/merged_events.h5 \
    --validate
```

See **[utilities/README.md](../../utilities/README.md)** for the full post-processing workflow.
