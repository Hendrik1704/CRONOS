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

# =============================================================================
# CRONOS Docker Image — ABI-stable multi-stage build
# =============================================================================

ARG BASE_IMAGE=ubuntu:22.04

# ---------------------------------------------------------------------------
# Base (shared environment for builder + runtime)
# ---------------------------------------------------------------------------
FROM ${BASE_IMAGE} AS base

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
        curl \
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
        libeigen3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV CC=gcc
ENV CXX=g++

# ---------------------------------------------------------------------------
# Builder stage
# ---------------------------------------------------------------------------
FROM base AS builder

# Set working directory for external codes
WORKDIR /build/external_codes

# Copy only the scripts needed to fetch and compile external codes
COPY external_codes/GetModulesFromGit.sh  ./GetModulesFromGit.sh

# Clone all external modules
RUN bash GetModulesFromGit.sh

# Ensure Eigen is discoverable by CMake everywhere
ENV CMAKE_PREFIX_PATH="/usr/share/eigen3/cmake"

# Compile all external C++ codes
RUN cd ipglasma && mkdir build && cd build && cmake .. -DdisableMPI=ON && \
    make -j$(nproc) && make install && cd .. && rm -r build && cd ..

RUN cd KoMPoST && make -j$(nproc) && cd ..

RUN cd MUSIC && mkdir build && cd build && \
    cmake .. -DCMAKE_PREFIX_PATH=/usr/share/eigen3/cmake && \
    make -Bj$(nproc) && make install && cd .. && rm -r build && cd ..

RUN cd iSS && mkdir -p build && cd build && rm -fr * && cmake .. && \
    make -Bj$(nproc) && make install && cd .. && rm -fr build && cd ..

RUN cd pythia8315 && \
    ./configure --cxx-common='-std=c++17 -march=native -O3 -fPIC -pthread' && \
    make -j$(nproc) && cd ..

RUN cd smash && mkdir build && cd build && \
    cmake .. \
      -DTRY_USE_ROOT=OFF \
      -DTRY_USE_HEPMC=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_FLAGS_RELEASE="-O3 -mtune=generic" \
      -DCMAKE_C_FLAGS_RELEASE="-O3 -mtune=generic" \
      -DPythia_CONFIG_EXECUTABLE=../../pythia8315/bin/pythia8-config \
      -DCMAKE_PREFIX_PATH=/usr/share/eigen3/cmake && \
    make smash -j$(nproc) && cd ../..

RUN cd hadronic_afterburner_toolkit && mkdir -p build && cd build && \
    cmake .. -Dlink_with_lib=OFF && make -j$(nproc) && make install && \
    cd ../ebe_scripts && \
    g++ convert_to_binary_SMASH.cpp -lz -o convert_to_binary_SMASH.e && \
    mv convert_to_binary_SMASH.e ../ && \
    g++ concatenate_binary_files.cpp -lz -o concatenate_binary_files.e && \
    mv concatenate_binary_files.e ../ && cd ../..

# ---------------------------------------------------------------------------
# Runtime stage (IDENTICAL ABI = no GLIBC mismatch possible)
# ---------------------------------------------------------------------------
FROM base AS runtime

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

# Copy everything built
COPY --from=builder /build/external_codes /app/external_codes

# Ensure shared libraries and Pythia8 data are found at runtime
ENV LD_LIBRARY_PATH="/app/external_codes/MUSIC:/app/external_codes/iSS/lib:/app/external_codes/pythia8315/lib"
ENV PYTHIA8DATA="/app/external_codes/pythia8315/share/Pythia8/xmldoc"

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
