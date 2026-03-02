# CRONOS Docker Image

This directory contains the Dockerfile and `.dockerignore` for building the CRONOS container image.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)

## Building the image locally

Run from the **repository root**:

```bash
docker build -f docker/Dockerfile -t cronos .
```

> **Note:** The first build takes a while (~20–40 min) because it clones and compiles all
> external C++ codes (IP-Glasma, KoMPoST, MUSIC, iSS, SMASH/Pythia, hadronic\_afterburner\_toolkit).
> Subsequent builds are cached unless the build scripts change.

## Pulling a pre-built image from Docker Hub

```bash
docker pull hendrik1704/cronos:latest
```

Images are automatically published on every push to `main` or `devel` via GitHub Actions.

## Running a simulation

```bash
# Prepare simulation
docker run --rm -v $(pwd)/run:/app/run hendrik1704/cronos:latest \
    prepare_simulations.py --user_config_path config/user_config.py

# Run simulation
docker run --rm -v $(pwd)/run:/app/run hendrik1704/cronos:latest \
    run_simulations.py --user_config_path config/user_config.py --job_dir run/job_0/
```

Mount additional directories as needed, e.g. custom config files or input data.

## Interactive shell

```bash
docker run --rm -it --entrypoint /bin/bash hendrik1704/cronos:latest
```

## Usage on HPC clusters (Apptainer / Singularity)

Most HPC clusters do not allow Docker directly but support
[Apptainer](https://apptainer.org/) (the Singularity-compatible successor).

### Convert the Docker image to a SIF file

```bash
# From Docker Hub (recommended)
apptainer pull cronos.sif docker://hendrik1704/cronos:latest

# Or from a locally built Docker image
apptainer pull cronos.sif docker-daemon://cronos:latest
```

### Run with Apptainer

```bash
apptainer exec cronos.sif python3 /app/prepare_simulations.py \
    --user_config_path config/user_config_ipglasma.py

apptainer exec cronos.sif python3 /app/run_simulations.py \
    --user_config_path config/user_config_ipglasma.py \
    --job_dir run/job_0/
```

> **Tip:** Apptainer (and Singularity) automatically bind-mount `$HOME`, `$PWD`, and `/tmp` by default.
> For other directories use `--bind /path/on/host:/path/in/container`.

## Image details

| Property | Value |
|---|---|
| Base image | `ubuntu:22.04` |
| Build type | Multi-stage (builder + runtime) |
| Python | 3.x (system) |
| C++ standard | C++17 |
| Docker Hub | `hendrik1704/cronos` |
