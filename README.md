# CRONOS - Collision Runs with Orchestrated Nuclear Observable Simulations
<img src="assets/CRONOS.png" alt="CRONOS Logo" width="200">

## Overview

CRONOS is a comprehensive framework designed to facilitate the simulation and analysis of nuclear collision events. It integrates various modules for event generation, hydrodynamic evolution, and particle production, providing researchers with a robust toolset for studying high-energy nuclear physics phenomena.

### Key Features

- **Modular Architecture**: Seamlessly integrates multiple physics modules (initial conditions, hydrodynamics, particlization, afterburner)
- **Checkpoint System**: Automatic simulation resumption from last successful module in case of failures
- **Cluster Support**: Built-in SLURM job array generation for high-performance computing
- **Flexible Configuration**: Python-based configuration system for easy parameter management
- **Output Management**: Automated HDF5 data packaging and result handling

### Supported Modules

- **Initial Conditions**: `from_file_IC` (load from external files)
- **Pre-equilibrium**: `KoMPoST` (Kinetic Theory based pre-equilibrium evolution)
- **Entropy Matching**: `entropy_matching` (smooth transition between modules)
- **Hydrodynamics**: `MUSIC` (3+1D relativistic hydrodynamics)
- **Particlization**: `iSS` (Cooper-Frye particlization)
- **Afterburner**: `SMASH` (hadronic rescattering), `afterburner_toolkit` (analysis tools)

## Installation

### Prerequisites
- Python 3.8+
- GCC compiler
- CMake
- MPI (for parallel execution)
- Python packages (see `requirements.txt`)

### Setup Process

1. **Download and compile external codes:**
   ```bash
   cd external_codes/
   ./GetModulesFromGit.sh
   ./CompileFramework.sh
   ```

2. **For supported clusters** (optional):
   ```bash
   cd cluster_support/
   # Submit installation job for your cluster
   sbatch install_[cluster_name].sh
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Configuration Files

CRONOS uses a two-tier configuration system:

1. **Main Config** (`config/main_config.py`): Default framework settings
2. **User Config** (`config/user_config_*.py`): Simulation-specific parameters

### Example Configuration Structure

```python
# General settings
general = {
    'modules': ['from_file_IC', 'KoMPoST', 'MUSIC', 'iSS', 'SMASH'],
    'log_level': 'INFO',
    'number_of_jobs': 1,
    'number_events_per_job': 1,
    'cleanup_checkpoints': True
    ...
}

# Module-specific settings
KoMPoST = {
    'tIn': 0.5,
    'tOut': 10.0,
    'EtaOverS': 0.2,
    ...
}

MUSIC = {
    'Initial_time_tau_0': 0.5,
    'Total_evolution_time_tau': 30.0,
    'Grid_size_in_eta': 128
    ...
}
```

## Running Simulations

### 1. Prepare Simulation Environment

```bash
python prepare_simulations.py \
    --main_config_path config/main_config.py \
    --user_config_path config/user_config_from_file_SMASH_scatterings.py \
    --cluster noctua1 \
    --run_dir run/
```

**Options:**
- `--cluster`: Target cluster (`local`, `noctua1`, etc.)
- `--run_dir`: Output directory for simulation files

### 2. Submit Jobs

#### Local Execution
```bash
python run_simulations.py --job_dir run/job_0/
```

#### Cluster Execution
```bash
cd run/
sbatch submit_job.sh
```

### 3. Monitor Progress

#### Check Specific Job
```bash
python utilities/checkpoint_utils.py inspect run/job_0/
```

#### Overview of All Jobs
```bash
python utilities/checkpoint_utils.py list run/
```

## Checkpoint System

CRONOS features an advanced checkpoint system for robust simulation management:

### Features
- **Automatic Checkpointing**: Saves progress after each module completion
- **Smart Resumption**: Resumes from last successful module on restart
- **Failure Recovery**: Continues from failed module after fixes
- **Progress Tracking**: Detailed status information for all events

### Checkpoint Commands

```bash
# Inspect checkpoint status
python utilities/checkpoint_utils.py inspect run/job_0/

# List all checkpoints
python utilities/checkpoint_utils.py list run/

# Resume failed simulation
python run_simulations.py --job_dir run/job_0/  # Automatic resume

# Force restart (ignore checkpoints and start over)
python run_simulations.py --job_dir run/job_0/ --force-restart
```

## Output Management

### File Structure
```
run/
├── job_0/
│   ├── event_0.h5          # Final HDF5 output
│   └── .cronos_checkpoint.json
├── job_1/                  # Not run yet
└── log/
    ├── output_[jobid]_[taskid].log
    └── error_[jobid]_[taskid].log
```

### Output Files
- **HDF5 Files**: Compressed simulation results (`event_X.h5`)
- **Log Files**: Separate stdout/stderr for each job array task
- **Checkpoints**: Progress tracking files (`.cronos_checkpoint.json`)

## Custom Module Integration

1. Create module class inheriting from `BaseModule`
2. Implement required methods: `prepare_environment()`, `prepare_input()`, `run()`, `fetch_output()`
3. Register in `MODULE_REGISTRY`

## Troubleshooting

### Common Issues

1. **"Module not found in registry"**
   - Ensure module is imported in `run_simulations.py`
   - Check `MODULE_REGISTRY` dictionary

2. **Memory issues on cluster**
   - Adjust SLURM memory requests in `cluster_submission.py`
   - Enable output suppression: `suppress_output: True`

### Getting Help

- **Inspect checkpoints**: `python utilities/checkpoint_utils.py inspect [job_dir]`
- **Check logs**: Look in `run/log/` directory for SLURM output

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions from the community! Everyone is encouraged to:

- Report bugs and issues
- Suggest new features or improvements
- Submit pull requests with bug fixes or enhancements
- Improve documentation
- Add support for new physics modules

Please feel free to open a Pull Request or create an issue on GitHub.

## Citation

Currently, there is no official release or publication to cite. Please check back for updates on how to properly cite CRONOS in your research once a release is available.