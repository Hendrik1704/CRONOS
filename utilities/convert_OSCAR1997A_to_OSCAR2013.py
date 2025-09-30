#!/usr/bin/env python3
"""OSCAR Format Conversion Utility: OSCAR1999A to OSCAR2013.

This utility converts particle data from the legacy OSCAR1999A format to the
modern OSCAR2013 standard used in heavy-ion collision event generators and
analysis tools. It handles PDG particle identification, charge assignment,
and format standardization for compatibility with current analysis frameworks.

OSCAR Format Background:
    OSCAR (Output of Simulated Collisions And Reactions) is a standard format
    for storing particle-level information from heavy-ion collision simulations.
    The 2013 revision includes enhanced metadata, charge information, and
    improved precision for spatial coordinates.

Conversion Features:
- PDG particle identification and charge mapping
- Spatial coordinate precision enhancement with position wiggle
- Event boundary detection and proper formatting
- Header generation with units and metadata
- Random seed control for reproducible position adjustments

Author: CRONOS Development Team
Compatibility: SMASH, UrQMD, OSCAR-compatible analysis tools
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import time

def load_pdg_table(pdg_path: Path) -> pd.DataFrame:
    """Load and parse SMASH PDG particle data table for charge information.
    
    Args:
        pdg_path (Path): Path to SMASH PDG data file (typically pdg-SMASH.dat)
    
    Returns:
        pd.DataFrame: Cleaned particle data with PDG_ID and charge columns
    """
    pdg = pd.read_csv(
        pdg_path,
        header=None,
        sep=r"\s\s+|,",
        engine="python",
    )
    pdg.columns = [
        "PDG_ID",
        "name",
        "mass",
        "width",
        "gspin",
        "baryon",
        "strange",
        "charm",
        "bottom",
        "gisospin",
        "charge",
        "decays",
    ]
    return pdg.dropna()

def get_PDG_ID_charge(pdg_id: int, pdg_df: pd.DataFrame) -> int:
    """Determine electric charge for particle given PDG identification code.
    
    Handles both particles and antiparticles according to PDG conventions.
    
    Args:
        pdg_id (int): PDG particle identification code
        pdg_df (pd.DataFrame): SMASH PDG table with charge information
    
    Returns:
        int: Electric charge in units of elementary charge (0 if unknown)
    """
    pdg_ids = pdg_df["PDG_ID"].to_numpy()
    charges = pdg_df["charge"].to_numpy()

    # direct match
    match = np.where(pdg_ids == pdg_id)[0]
    if match.size > 0:
        return int(charges[match[0]])

    # check antiparticle
    match = np.where(pdg_ids == -pdg_id)[0]
    if match.size > 0:
        return int(-charges[match[0]])

    return 0

def load_oscar1999a(input_path: Path) -> pd.DataFrame:
    """Load OSCAR1999A file into DataFrame."""
    col_names = [
        "sample_idx",
        "PDG_ID",
        "px",
        "py",
        "pz",
        "E",
        "m",
        "x",
        "y",
        "z",
        "t",
    ]
    return pd.read_csv(
        input_path, names=col_names, sep=r"\s\s+|,", engine="python", skiprows=3
    )

def find_event_boundaries(df: pd.DataFrame) -> list[int]:
    """Find indices where events start and end in the OSCAR1999A file."""
    row_has_nan = df.isnull().any(axis=1)
    event_idx = [i for i, has_nan in enumerate(row_has_nan) if has_nan]
    event_idx.append(len(df))  # mark end of last event
    return event_idx

def write_oscar2013(df: pd.DataFrame, pdg_df: pd.DataFrame, output_path: Path):
    """Convert OSCAR1999A to OSCAR2013 format and write to file."""
    event_idx = find_event_boundaries(df)
    num_events = len(event_idx) - 1

    with open(output_path, "w") as f:
        f.write("#!OSCAR2013 particle_lists t x y z mass p0 px py pz pdg ID charge\n")
        f.write("# Units: fm fm fm fm GeV GeV GeV GeV GeV none none e\n")
        for ev in range(num_events):
            f.write(f"# event {ev+1} out {df.loc[event_idx[ev], 'PDG_ID']}\n")
            for line in range(event_idx[ev] + 1, event_idx[ev + 1]):
                row = df.loc[line]
                charge = get_PDG_ID_charge(int(row["PDG_ID"]), pdg_df)
                
                # Add small random wiggle to prevent particles at same position
                wiggle_x = row['x'] + np.random.uniform(-1e-5, 1e-5)
                wiggle_y = row['y'] + np.random.uniform(-1e-5, 1e-5)
                wiggle_z = row['z'] + np.random.uniform(-1e-5, 1e-5)
                
                f.write(
                    f"{row['t']:.6f} {wiggle_x:.6f} {wiggle_y:.6f} {wiggle_z:.6f} "
                    f"{row['m']:.6f} {row['E']:.6f} {row['px']:.6f} {row['py']:.6f} {row['pz']:.6f} "
                    f"{int(row['PDG_ID'])} {int(row['sample_idx'])} {charge}\n"
                )
            f.write(f"# event {ev+1} end 0 impact 0.000\n")

    return num_events

def main():
    """Command-line interface for OSCAR format conversion utility.
    
    Converts OSCAR1999A particle data to OSCAR2013 format with proper
    argument parsing and integration with CRONOS simulation pipelines.
    
    Prints number of events converted for subprocess capture.
    """
    parser = argparse.ArgumentParser(description="Convert OSCAR1999A to OSCAR2013 format.")
    parser.add_argument("pdgPath", type=Path, help="Path to pdg-SMASH.dat file")
    parser.add_argument("inputFilePath", type=Path, help="Path to OSCAR1999A input file")
    parser.add_argument("outputFilePath", type=Path, help="Directory to save OSCAR2013 file")
    parser.add_argument("--seed", type=int, default=-1, 
                       help="Random seed for position wiggle. Use -1 for time-based seed (default: -1)")
    args = parser.parse_args()

    # Set random seed for position wiggle
    if args.seed == -1:
        seed = int(time.time())
    else:
        seed = args.seed
    np.random.seed(seed)

    pdg_df = load_pdg_table(args.pdgPath)
    oscar_df = load_oscar1999a(args.inputFilePath)

    num_events = write_oscar2013(oscar_df, pdg_df, args.outputFilePath)
    # Print result so subprocess can capture it
    print(num_events)

if __name__ == "__main__":
    main()
