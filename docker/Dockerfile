# =============================================================================
# CRONOS Docker Image — Multi-stage build
# =============================================================================
# Stage 1: build   — compiles all C++ external codes
# Stage 2: runtime — slim image with only binaries + Python
#
# Build (from repository root):
#   docker build -f docker/Dockerfile -t cronos .
#
# Run:
#   docker run --rm -v $(pwd)/run:/app/run cronos \
#       python3 prepare_simulations.py --user_config_path config/user_config.py
#
# Convert to Singularity/Apptainer for HPC:
#   singularity pull cronos.sif docker://hendrik1704/cronos:latest
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 – Builder
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS builder

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        g++ \
        gfortran \
        git \
        wget \
        ca-certificates \
        # IP-Glasma dependencies
        libfftw3-dev \
        # Shared: GSL (IP-Glasma, KoMPoST, MUSIC, iSS, SMASH)
        libgsl-dev \
        # iSS / hadronic_afterburner_toolkit
        zlib1g-dev \
        # Python (needed at build time for scripts)
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for external codes
WORKDIR /build/external_codes

# Copy only the scripts needed to fetch and compile external codes
COPY external_codes/GetModulesFromGit.sh  ./GetModulesFromGit.sh
COPY external_codes/CompileFramework.sh   ./CompileFramework.sh

# Clone all external modules
RUN bash GetModulesFromGit.sh

# Compile all external C++ codes
RUN bash CompileFramework.sh

# ---------------------------------------------------------------------------
# Stage 2 – Runtime
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# Install only runtime libraries + Python
RUN apt-get update && apt-get install -y --no-install-recommends \
        # Runtime libraries for compiled C++ codes
        libfftw3-3 \
        libgsl27 \
        libgomp1 \
        zlib1g \
        libgfortran5 \
        # Python
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Create application directory
WORKDIR /app

# Copy compiled external codes from the builder stage
# IP-Glasma
COPY --from=builder /build/external_codes/ipglasma /app/external_codes/ipglasma

# KoMPoST
COPY --from=builder /build/external_codes/KoMPoST /app/external_codes/KoMPoST

# MUSIC
COPY --from=builder /build/external_codes/MUSIC /app/external_codes/MUSIC

# Eigen (headers, needed by some runtime configs)
COPY --from=builder /build/external_codes/eigen-3.4.0 /app/external_codes/eigen-3.4.0

# iSS
COPY --from=builder /build/external_codes/iSS /app/external_codes/iSS

# Pythia (runtime data tables are needed by SMASH)
COPY --from=builder /build/external_codes/pythia8315 /app/external_codes/pythia8315

# SMASH
COPY --from=builder /build/external_codes/smash /app/external_codes/smash

# hadronic_afterburner_toolkit
COPY --from=builder /build/external_codes/hadronic_afterburner_toolkit /app/external_codes/hadronic_afterburner_toolkit

# Copy the CRONOS Python framework
COPY src/               /app/src/
COPY config/            /app/config/
COPY utilities/         /app/utilities/
COPY prepare_simulations.py run_simulations.py /app/

# Default entrypoint — can be overridden at runtime
ENTRYPOINT ["python3"]
CMD ["--help"]
