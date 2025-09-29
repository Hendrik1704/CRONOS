# CRONOS - Collision Runs with Orchestrated Nuclear Observable Simulations
<img src="assets/CRONOS.png" alt="CRONOS Logo" width="200">

## Overview

CRONOS is a comprehensive framework designed to facilitate the simulation and analysis of nuclear collision events. It integrates various modules for event generation, hydrodynamic evolution, and particle production, providing researchers with a robust toolset for studying high-energy nuclear physics phenomena.

## Installation

To use the framework the modules have to be downloaded and installed first.
This can be done by running the `/external_codes/GetModulesFromGit.sh` and 
`/external_codes/CompileFramework.sh` scripts.
For some supported clusters there are scripts to submit an installation job in the 
`cluster_support/` directory.

## Run events

The event runs can be prepared by using the `prepare_simulations.py` script:
```bash
python prepare_simulations.py --user_config_path config/user_config_from_file_SMASH_scatterings.py --cluster noctua1
```
Including the cluster in the preparation script will automatically generate a slurm script for a job array on the noctua1
cluster in this example. This will be in the default `run/` directory.
Just go inside that directory and run `sbatch submit_job.sh`.

This documentation has to be extended!!!