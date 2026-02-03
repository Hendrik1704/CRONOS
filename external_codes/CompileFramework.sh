#!/bin/bash

# Determine the number of available CPUs
NUM_CPUS=$(nproc)

echo "Build IP-Glasma code for initial condition generation"
cd ipglasma && mkdir build && cd build && cmake .. && make -j$NUM_CPUS && make install && cd .. && rm -r build && cd ..

echo "Build KoMPoST code for pre-equilibrium stage"
cd KoMPoST && make -j$NUM_CPUS && cd ..

echo "Prepare the Eigen library for MUSIC and SMASH"
cp -r eigen-3.4.0/ MUSIC/

echo "Build MUSIC code for hydrodynamic stage"
cd MUSIC && mkdir build && cd build && cmake .. && make -Bj$NUM_CPUS && make install && cd .. && rm -r build && cd ..

echo "Build iSS sampler to perform freeze out"
cd iSS && mkdir -p build && cd build && rm -fr * && cmake .. && make -Bj$NUM_CPUS && make install && cd .. && rm -fr build && cd ..

echo "Build Pythia which is used in SMASH for the hadronic afterburner phase"
cd pythia8315
./configure --cxx-common='-std=c++17 -march=native -O3 -fPIC -pthread'
make -j$NUM_CPUS && cd ..

echo "Build SMASH as an hadronic afterburner"
cd smash && mkdir build && cd build && cmake .. -DTRY_USE_ROOT=OFF -DTRY_USE_HEPMC=OFF -DPythia_CONFIG_EXECUTABLE=../../pythia8315/bin/pythia8-config -DCMAKE_PREFIX_PATH=../../eigen-3.4.0/ && make smash -j$NUM_CPUS && cd ../..

echo "Build hadronic_afterburner_toolkit to analyze SMASH output"
cd hadronic_afterburner_toolkit && mkdir -p build && cd build && cmake .. -Dlink_with_lib=OFF && make -j$NUM_CPUS && make install
cd ../ebe_scripts && g++ convert_to_binary_SMASH.cpp -lz -o convert_to_binary_SMASH.e && mv convert_to_binary_SMASH.e ../
g++ concatenate_binary_files.cpp -lz -o concatenate_binary_files.e && mv concatenate_binary_files.e ../ && cd ../..

echo "Finished building all the modules successfully"

