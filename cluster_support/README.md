# Cluster Support

This directory contains cluster-specific configuration and installation scripts for running CRONOS on HPC systems.

## Supported Clusters

| Cluster | Description | Documentation |
|---------|-------------|---------------|
| [noctua2](noctua2/) | Noctua2 HPC cluster (PC² Paderborn) — bare-metal installation via SLURM job | [noctua2/README.md](noctua2/README.md) |
| [wsu_cluster](wsu_cluster/) | WSU cluster — Apptainer/Singularity container-based workflow | [wsu_cluster/README.md](wsu_cluster/README.md) |

## General Workflow

Regardless of cluster, the high-level steps are the same:

1. **Install / compile** external codes (either natively or inside a container).
2. **Prepare** a run directory with `prepare_simulations.py --cluster <name>`.
3. **Submit** the generated `submit_job.sh` via `sbatch`.
4. **Collect** results with `utilities/event_database.py build`.

See the cluster-specific README linked above for exact commands and module loads.
