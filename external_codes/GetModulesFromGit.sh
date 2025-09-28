#!/bin/bash

echo "Download KoMPoST from GitHub:"
git clone --depth 1 https://github.com/Hendrik1704/KoMPoST.git
cd KoMPoST
git checkout 3cc99ea40edac68da25eae784e922cac11548297
cd ..

echo "Download MUSIC from GitHub:"
git clone --branch chun_dev --single-branch https://github.com/Hendrik1704/MUSIC
cd MUSIC
git checkout e9523630fa9bfe7ed4b05c968bae6918c3e3ef97
cd EOS
bash download_hotQCD.sh SMASH_binary
bash download_hotQCD.sh
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
git checkout 98f16a2a016c7acd461fdba35f9746af8f338b96
cd ..

echo "Downloaded all the modules successfully"
