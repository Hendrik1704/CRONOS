#!/usr/bin/env python3
"""KoMPoST to MUSIC Format Conversion and Entropy Matching Utility.

This utility handles the transition between KoMPoST pre-equilibrium evolution
and MUSIC hydrodynamic simulation in heavy-ion collision workflows. It performs
entropy matching to ensure thermodynamic consistency between the two physics
models while converting between their respective data formats.

Physics Background:
    The transition from pre-equilibrium (KoMPoST) to hydrodynamics (MUSIC)
    requires careful matching of thermodynamic quantities to maintain energy
    and entropy conservation. This script implements entropy matching based
    on effective degrees of freedom and equation of state consistency.

Matching Types:
    0: Energy matching (MUSIC starts with the KoMPoST energy density)
    1: Entropy matching (MUSIC starts with the energy density that has the
       KoMPoST entropy density in the EOS)

Bulk pressure:
    KoMPoST is conformal, its pressure is e_KoMPoST / 3. Both matching types
    write the bulk pressure Pi = e_KoMPoST / 3 - p_EOS(e_MUSIC) as the 19th
    column, which MUSIC reads with Initial_profile 94 (95 in 3D). For energy
    matching this is the value MUSIC computes itself with Initial_profile 9.

Entropy Matching Algorithm:
    1. Calculate KoMPoST entropy density using effective degrees of freedom
    2. Interpolate energy density from EOS entropy-energy relation
    3. Calculate the bulk pressure
    4. Update energy density and add bulk pressure column

Cells below the EOS table are treated as vacuum: Pi = 0, and for entropy
matching also e = 0 (a linear extrapolation would give negative energies).

Usage:
    python KoMPoST_to_MUSIC.py <type> <nu_eff> <eos_file> <input> <output>

Author: CRONOS Development Team
Physics: Pre-equilibrium to hydrodynamics transition
"""

import sys
import numpy as np
from scipy.interpolate import interp1d
import math
import os

HBARC = 0.197326979


def read_file(filename):
    """Read KoMPoST output file with error handling and validation.

    Args:
        filename (str): Path to KoMPoST output file

    Returns:
        tuple: (data_array, comment_line) where data is numpy array
               and comment contains metadata from first line
    """
    data = []
    comment_line = ""

    try:
        with open(filename, "r") as file:
            comment_line = next(file).strip()
            for line in file:
                # Split each line into a list of floating-point numbers
                row = [float(value) for value in line.split()]
                if len(row) > 0:
                    data.append(row)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except ValueError as e:
        print(
            f"Error: {e} in file '{filename}'. Make sure all values are numbers."
        )
        sys.exit(1)

    return np.array(data), comment_line


def read_eos(file_path_eos):
    """Read a MUSIC binary EOS table.

    Returns:
        tuple: (e, p, T) - energy density and pressure in GeV/fm^3,
               temperature in GeV
    """
    raw = np.fromfile(file_path_eos, dtype=(float, 4))
    # 4 columns (energy density, local pressure, entropy density, local temperature)
    return raw[:, 0], raw[:, 1], raw[:, 3]


def bulk_pressure(e_kompost, e_music, e_eos, p_eos):
    """Return the bulk pressure of the conformal KoMPoST T^{mu nu} in MUSIC.

    Pi = e_kompost / 3 - p_EOS(e_music) in GeV/fm^3: the conformal KoMPoST
    pressure minus the equilibrium pressure at the energy density MUSIC starts
    with.
    """
    # pressure as a function of energy [p(e)]
    p_interp = interp1d(e_eos, p_eos, kind="linear", fill_value="extrapolate")
    return e_kompost / 3 - p_interp(e_music)


def e_matching(e_kompost, file_path_eos):
    """Perform energy matching between KoMPoST and MUSIC.

    MUSIC starts with the KoMPoST energy density.

    Args:
        e_kompost (array): KoMPoST energy density in GeV/fm^3
        file_path_eos (str): Path to equation of state file

    Returns:
        tuple: (e_music, bulk_pressure) in GeV/fm^3
    """
    e, p, _ = read_eos(file_path_eos)
    Bulk_pressure = bulk_pressure(e_kompost, e_kompost, e, p)
    # Below the EOS table (and for invalid cells, e = nan) there is no
    # equilibrium pressure: treat these (near-)empty cells as vacuum.
    below_table = ~(e_kompost >= e[0])
    Bulk_pressure = np.where(below_table, 0.0, Bulk_pressure)
    return e_kompost, Bulk_pressure


def s_matching(e_kompost, nu_eff, file_path_eos):
    """Perform entropy matching between KoMPoST and MUSIC using equation of state.

    Calculates thermodynamically consistent energy density for MUSIC based on
    KoMPoST entropy and the bulk pressure of the KoMPoST T^{mu nu}.

    Args:
        e_kompost (array): KoMPoST energy density in GeV/fm^3
        nu_eff (float): Effective degrees of freedom for entropy calculation
        file_path_eos (str): Path to equation of state file

    Returns:
        tuple: (e_music, bulk_pressure) - matched energy and bulk pressure in GeV/fm^3
    """
    # Kompost entropy
    s_kompost = (
        (4 / 3.0)
        * (nu_eff * math.pi * math.pi / 30.0) ** (1 / 4.0)
        * (e_kompost ** (3 / 4.0))
    )  # GeV^3/4 / fm^9/4
    s_kompost = s_kompost * (HBARC ** (1 / 4.0))  # GeV/fm^2

    # EOS
    e, p, T = read_eos(file_path_eos)
    entropy = HBARC * (p + e) / T  # GeV/fm^2
    # energy as a function of entropy [e(s)]
    energy_interp = interp1d(
        entropy, e, kind="linear", fill_value="extrapolate"
    )

    # Calculate the new energy and new bulk pressure
    e_Music = energy_interp(s_kompost)  # GeV/fm^3
    Bulk_pressure = bulk_pressure(e_kompost, e_Music, e, p)  # GeV/fm^3

    # Below the EOS table a linear extrapolation gives negative energies:
    # treat these (near-)empty cells (and invalid ones, s = nan) as vacuum.
    below_table = ~(s_kompost >= entropy[0])
    e_Music = np.where(below_table, 0.0, e_Music)
    Bulk_pressure = np.where(below_table, 0.0, Bulk_pressure)

    return e_Music, Bulk_pressure


def main():
    """Command-line interface for KoMPoST-MUSIC format conversion.

    Handles both energy and entropy matching modes with proper parameter
    validation and file I/O for integration with CRONOS simulation chain.

    Command-line Arguments:
        type_of_matching: 0 (energy) or 1 (entropy matching)
        nu_eff: Effective degrees of freedom for entropy calculation
        eos_file: Path to equation of state data file
        filename_in: Input file from KoMPoST
        filename_out: Output file for MUSIC
    """
    # Check if all parameters are provided as command line arguments
    if len(sys.argv) != 6:
        print(
            "Usage: python script.py type_of_matching nu_eff <eos_file> <filename_in> <filename_out>"
        )
        sys.exit(1)

    # parse input parameters
    type_of_matching = int(sys.argv[1])
    nu_eff = float(sys.argv[2])
    file_path_eos = sys.argv[3]
    filename_in = sys.argv[4]
    filename_out = sys.argv[5]

    if type_of_matching not in (0, 1):
        print(
            "Problem with the variable type_of_matching, should be equal to 0 or 1.",
            file=sys.stderr,
        )
        sys.exit(1)

    # read the input file
    data, comment = read_file(filename_in)
    energy_density = data[:, 3]  # GeV/fm^3
    if type_of_matching == 0:
        e_new, Pi = e_matching(energy_density, file_path_eos)
    else:
        e_new, Pi = s_matching(energy_density, nu_eff, file_path_eos)

    # add the bulk pressure as a column in data
    data = np.column_stack((data, Pi))
    # Replace the column 4: the energy density MUSIC starts with
    data[:, 3] = e_new

    # Write the final file: eta, x, y, new_energy, u^tau, u^x, u^y, u^eta,
    # pi^tautau, pi^taux, pi^tauy, pi^taueta, pi^xx, pi^xy, pi^xeta, pi^yy, pi^yeta, pi^etaeta and Pi,
    # i.e. the 19 columns read by MUSIC.
    with open(filename_out, "w") as file:
        file.write(comment + "\n")
        for row in data:
            file.write(" ".join(map(str, row)) + "\n")


if __name__ == "__main__":
    main()
