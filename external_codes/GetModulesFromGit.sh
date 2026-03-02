#!/bin/bash

set -euo pipefail

echo "Download IP-Glasma from GitHub:"
git clone --depth 1 https://github.com/chunshen1987/ipglasma -b ipglasma_jimwlk
cd ipglasma
git checkout bf92fe1758a61acc5cf84dff2428b83570ea81fa
cd nucleusConfigurations && bash download_nucleusTables.sh

# Basic sanity check: make sure a key nucleus configuration exists
if [ ! -f "Pb208.bin.in" ]; then
	echo "ERROR: Failed to download IP-Glasma nucleus configuration tables (Pb208.bin.in missing)." >&2
	exit 1
fi

cd ../..

echo "Download KoMPoST from GitHub:"
git clone --depth 1 https://github.com/Hendrik1704/KoMPoST.git
cd KoMPoST
git checkout 3cc99ea40edac68da25eae784e922cac11548297
cd ..

echo "Download MUSIC from GitHub:"
git clone --branch chun_dev --single-branch https://github.com/Hendrik1704/MUSIC
cd MUSIC
git checkout ef77326527929d8db472fa9a7b0c4f55613c6d6c
cd EOS
bash download_hotQCD.sh SMASH_binary
bash download_hotQCD.sh

# Verify hotQCD EOS tables were downloaded correctly
if [ ! -f "hotQCD/hrg_hotqcd_eos_SMASH_binary.dat" ] || [ ! -f "hotQCD/hrg_hotqcd_eos_binary.dat" ]; then
	echo "ERROR: Failed to download hotQCD EOS tables for MUSIC (hrg_hotqcd_eos_* files missing)." >&2
	exit 1
fi

cd ../..

echo "Download iSS from GitHub:"
git clone --depth 1 https://github.com/chunshen1987/iSS.git
cd iSS
git checkout 7d39d84ff95925bf3bc0edfaf8aae1ac5a28b387
cd ..

echo "Download SMASH from GitHub:"
git clone --depth 1 https://github.com/smash-transport/smash.git --branch SMASH-3.2.2

echo "Download Pythia (used for SMASH):"
wget https://pythia.org/download/pythia83/pythia8315.tgz
tar xf pythia8315.tgz

echo "Download stable Eigen library version 3.4.0:"
wget https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
tar xf eigen-3.4.0.tar.gz

echo "Download hadronic_afterburner_toolkit from GitHub:"
git clone --depth 1 https://github.com/Hendrik1704/hadronic_afterburner_toolkit.git
cd hadronic_afterburner_toolkit
git checkout ccfec0e1bba8662d8b5d6544f94cd81be2d11fee
cd ..

echo "Downloaded all the modules successfully"
