#!/bin/bash

# Create a script that submits a job to download and install necessary modules

#SBATCH -J Install_CRONOS
#SBATCH -A hpc-prf-flucurhi
#SBATCH -t 00:15:00
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -n 10

module load numlib/GSL/2.7-GCC-11.3.0
module load compiler/GCC/11.3.0
module load compiler/GCCcore/11.3.0
module load devel/CMake/3.23.1-GCCcore-11.3.0
module load mpi/OpenMPI/4.1.4-GCC-11.3.0
module load lib/zlib/1.2.12-GCCcore-11.3.0
module load tools/binutils/2.38-GCCcore-11.3.0
module load lang/Python/3.10.4-GCCcore-11.3.0

./ClearFramework.sh || true
./GetModulesFromGit.sh   || { echo "Failed to fetch modules"; exit 1; }
./CompileFramework.sh    || { echo "Compilation failed"; exit 1; }
