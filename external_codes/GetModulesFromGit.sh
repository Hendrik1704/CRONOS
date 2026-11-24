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
# IP-Glasma 2.0 (devel branch, not released yet)
git clone https://github.com/schenke/ipglasma -b devel
cd ipglasma
git checkout d3088aa8de19a5cb78135f6e9e46dc6989c9fa48
cd nucleusConfigurations && with_retries bash download_nucleusTables.sh

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

echo "Download KoMPoST-3D from GitHub:"
KOMPOST3D_COMMIT=d3307864db44e7365db58130d8386933a47e579d
# Skip the git-lfs files (if git-lfs is installed), only the response table is needed
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/Hendrik1704/KoMPoST-3D.git
cd KoMPoST-3D
GIT_LFS_SKIP_SMUDGE=1 git checkout "$KOMPOST3D_COMMIT"
# The kinetic theory response table is stored in git-lfs, download it directly
# so that git-lfs is not required. A failed download does not stop the
# installation of the other codes; KoMPoST3D then stops with an error when it
# cannot read the table.
if ! wget -O RTA/ENERGYRESPONSE/Gs_tot_finer.dat \
	"https://media.githubusercontent.com/media/Hendrik1704/KoMPoST-3D/${KOMPOST3D_COMMIT}/RTA/ENERGYRESPONSE/Gs_tot_finer.dat" ||
	! echo "f03a7ebfd316d457ac3380579b11bb866bc5950b93a7326d5d9e2960a3903e1e  RTA/ENERGYRESPONSE/Gs_tot_finer.dat" | sha256sum -c --status; then
	echo "WARNING: Failed to download the KoMPoST-3D response table (RTA/ENERGYRESPONSE/Gs_tot_finer.dat)." >&2
	echo "WARNING: The KoMPoST3D module cannot run until it is downloaded; the other codes are not affected." >&2
	rm -f RTA/ENERGYRESPONSE/Gs_tot_finer.dat
fi

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
