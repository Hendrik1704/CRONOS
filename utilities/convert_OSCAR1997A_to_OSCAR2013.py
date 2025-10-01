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
- Memory-efficient streaming processing for large files
- Optimized charge lookup for improved performance

Performance Optimizations:
- Line-by-line streaming processing (no full file loading)
- Pre-computed charge lookup dictionary
- Buffered I/O operations
- Event-level memory management (particles released after processing)

Author: CRONOS Development Team
Compatibility: SMASH, UrQMD, OSCAR-compatible analysis tools
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import time
import re

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

def parse_particle_line(line: str) -> dict:
    """Parse a single particle line from OSCAR1999A format.
    
    Args:
        line (str): Raw line from OSCAR1999A file
        
    Returns:
        dict: Parsed particle data or None if line is invalid
    """
    # Split on whitespace, handling multiple spaces
    parts = re.split(r'\s+', line.strip())
    
    # Expected format: sample_idx PDG_ID px py pz E m x y z t
    if len(parts) < 11:
        return None
    
    try:
        return {
            'sample_idx': int(parts[0]),
            'PDG_ID': int(parts[1]),
            'px': float(parts[2]),
            'py': float(parts[3]),
            'pz': float(parts[4]),
            'E': float(parts[5]),
            'm': float(parts[6]),
            'x': float(parts[7]),
            'y': float(parts[8]),
            'z': float(parts[9]),
            't': float(parts[10])
        }
    except (ValueError, IndexError):
        return None

def is_event_boundary(line: str) -> bool:
    """Check if a line represents an event boundary (contains NaN or fewer fields)."""
    if not line.strip():
        return True
    
    parts = re.split(r'\s+', line.strip())
    
    # Event boundary lines typically have fewer fields or NaN values
    if len(parts) < 11:
        return True
    
    # Check for NaN or non-numeric values in expected numeric positions
    try:
        float(parts[1])  # PDG_ID should be numeric
        return False
    except (ValueError, IndexError):
        return True

def convert_oscar_streaming(input_path: Path, pdg_df: pd.DataFrame, output_path: Path, 
                           buffer_size: int = 8192) -> int:
    """Convert OSCAR1999A to OSCAR2013 format using streaming approach.
    
    Processes the file line by line to minimize memory usage for large files.
    Uses buffered I/O and limits in-memory storage to one event at a time.
    
    Args:
        input_path (Path): Path to OSCAR1999A input file
        pdg_df (pd.DataFrame): SMASH PDG table with charge information
        output_path (Path): Path for OSCAR2013 output file
        buffer_size (int): Buffer size for file I/O operations (default: 8192)
        
    Returns:
        int: Number of events processed
    """
    num_events = 0
    current_event_particles = []
    
    # Create charge lookup dictionary for faster access
    charge_lookup = {}
    for _, row in pdg_df.iterrows():
        pdg_id = int(row['PDG_ID'])
        charge = int(row['charge'])
        charge_lookup[pdg_id] = charge
        charge_lookup[-pdg_id] = -charge  # antiparticle
    
    with open(input_path, 'r', buffering=buffer_size) as infile, \
         open(output_path, 'w', buffering=buffer_size) as outfile:
        # Write OSCAR2013 header
        outfile.write("#!OSCAR2013 particle_lists t x y z mass p0 px py pz pdg ID charge\n")
        outfile.write("# Units: fm fm fm fm GeV GeV GeV GeV GeV none none e\n")
        
        # Skip the first 3 header lines from OSCAR1999A
        for _ in range(3):
            next(infile, None)
        
        for line_num, line in enumerate(infile):
            if is_event_boundary(line):
                # Process accumulated particles for current event
                if current_event_particles:
                    num_events += 1
                    
                    # Extract multiplicity from first particle line (if available)
                    multiplicity = len(current_event_particles)
                    if current_event_particles:
                        # Use the PDG_ID from the event boundary as multiplicity indicator
                        try:
                            parts = re.split(r'\s+', line.strip())
                            if len(parts) > 1:
                                multiplicity = int(parts[1])
                        except (ValueError, IndexError):
                            pass
                    
                    # Write event header
                    outfile.write(f"# event {num_events} out {multiplicity}\n")
                    
                    # Write all particles for this event
                    for particle in current_event_particles:
                        # Use fast lookup for charge
                        charge = charge_lookup.get(particle["PDG_ID"], 0)
                        
                        # Add small random wiggle to prevent particles at same position
                        wiggle_x = particle['x'] + np.random.uniform(-1e-5, 1e-5)
                        wiggle_y = particle['y'] + np.random.uniform(-1e-5, 1e-5)
                        wiggle_z = particle['z'] + np.random.uniform(-1e-5, 1e-5)
                        
                        outfile.write(
                            f"{particle['t']:.6f} {wiggle_x:.6f} {wiggle_y:.6f} {wiggle_z:.6f} "
                            f"{particle['m']:.6f} {particle['E']:.6f} {particle['px']:.6f} {particle['py']:.6f} {particle['pz']:.6f} "
                            f"{particle['PDG_ID']} {particle['sample_idx']} {charge}\n"
                        )
                    
                    # Write event footer
                    outfile.write(f"# event {num_events} end 0 impact 0.000\n")
                    
                    # Clear particles list for next event
                    current_event_particles = []
            else:
                # Parse particle line
                particle = parse_particle_line(line)
                if particle is not None:
                    current_event_particles.append(particle)
        
        # Process any remaining particles (last event without explicit boundary)
        if current_event_particles:
            num_events += 1
            multiplicity = len(current_event_particles)
            
            outfile.write(f"# event {num_events} out {multiplicity}\n")
            
            for particle in current_event_particles:
                charge = charge_lookup.get(particle["PDG_ID"], 0)
                
                wiggle_x = particle['x'] + np.random.uniform(-1e-5, 1e-5)
                wiggle_y = particle['y'] + np.random.uniform(-1e-5, 1e-5)
                wiggle_z = particle['z'] + np.random.uniform(-1e-5, 1e-5)
                
                outfile.write(
                    f"{particle['t']:.6f} {wiggle_x:.6f} {wiggle_y:.6f} {wiggle_z:.6f} "
                    f"{particle['m']:.6f} {particle['E']:.6f} {particle['px']:.6f} {particle['py']:.6f} {particle['pz']:.6f} "
                    f"{particle['PDG_ID']} {particle['sample_idx']} {charge}\n"
                )
            
            outfile.write(f"# event {num_events} end 0 impact 0.000\n")
    
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

    num_events = convert_oscar_streaming(args.inputFilePath, pdg_df, args.outputFilePath)
    # Print result so subprocess can capture it
    print(num_events)

if __name__ == "__main__":
    main()
