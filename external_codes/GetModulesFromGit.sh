#!/bin/bash

set -euo pipefail

# Run a download command again if it fails: the tables are fetched from
# Bitbucket, which sometimes answers with a server error
with_retries() {
	local attempt
	for attempt in 1 2 3 4 5; do
		if "$@"; then
			return 0
		fi
		echo "'$*' failed (attempt $attempt of 5)" >&2
		if [ "$attempt" -lt 5 ]; then
			sleep 30
		fi
	done
	return 1
}

echo "Download IP-Glasma from GitHub:"
git clone https://github.com/chunshen1987/ipglasma -b ipglasma_jimwlk
cd ipglasma
git checkout bf92fe1758a61acc5cf84dff2428b83570ea81fa
# (the download script reports success even if its git clone fails)
cd nucleusConfigurations && with_retries bash -c 'bash download_nucleusTables.sh && [ -f Pb208.bin.in ]'

# Basic sanity check: make sure a key nucleus configuration exists
if [ ! -f "Pb208.bin.in" ]; then
	echo "ERROR: Failed to download IP-Glasma nucleus configuration tables (Pb208.bin.in missing)." >&2
	exit 1
fi

cd ../..

echo "Download KoMPoST from GitHub:"
git clone https://github.com/Hendrik1704/KoMPoST.git
cd KoMPoST
git checkout 5d35aed36635ffa92f9ba9d97531f209097dacb0
cd ..

echo "Download MUSIC from GitHub:"
git clone --branch chun_dev_4D --single-branch https://github.com/Hendrik1704/MUSIC
cd MUSIC
git checkout 227d81363bc579a15ee4b5f19830db7f6d168033
cd EOS
with_retries bash download_hotQCD.sh SMASH_binary
with_retries bash download_hotQCD.sh

# Verify hotQCD EOS tables were downloaded correctly
if [ ! -f "hotQCD/hrg_hotqcd_eos_SMASH_binary.dat" ] || [ ! -f "hotQCD/hrg_hotqcd_eos_binary.dat" ]; then
	echo "ERROR: Failed to download hotQCD EOS tables for MUSIC (hrg_hotqcd_eos_* files missing)." >&2
	exit 1
fi

cd ../..

echo "Download iSS from GitHub:"
git clone --branch cronos --single-branch https://github.com/Hendrik1704/iSS.git
cd iSS
git checkout ef5c307801a2be887536d71db6bf085e0533a093
cd ..

echo "Download SMASH from GitHub:"
git clone https://github.com/smash-transport/smash.git --branch SMASH-3.4.2

echo "Download Pythia (used for SMASH):"
wget https://pythia.org/releases/pythia83/pythia8316.tgz
tar xf pythia8316.tgz

echo "Download stable Eigen library version 3.4.0:"
wget https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
tar xf eigen-3.4.0.tar.gz

echo "Download hadronic_afterburner_toolkit from GitHub:"
git clone https://github.com/Hendrik1704/hadronic_afterburner_toolkit.git
cd hadronic_afterburner_toolkit
git checkout a3d031f740802d1bdace7d5a7f62f4f695514bd6
cd ..

echo "Downloaded all the modules successfully"
