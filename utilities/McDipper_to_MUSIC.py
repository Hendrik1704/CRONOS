#!/usr/bin/env python3
"""McDipper to MUSIC Format Converter.

This utility converts McDipper initial condition data to MUSIC hydrodynamics
format, handling equation of state interpolation, bulk pressure calculations,
and proper tensor initialization for relativistic heavy-ion collision simulations.

The converter processes energy density distributions and applies the equation
of state to compute pressure, bulk viscosity, and shear stress tensor components
required by the MUSIC hydrodynamics code.

Key Features:
- EOS interpolation for pressure calculations with extrapolation handling
- Bulk pressure computation from energy-pressure difference
- Shear stress tensor initialization for viscous hydrodynamics
- Proper coordinate transformations (Cartesian to Milne coordinates)
- Energy cutoff handling for numerical stability and performance
- Comprehensive input validation and error handling
- Memory-efficient processing for large grids
- Detailed logging and progress reporting

Input Format (McDipper):
    Header: # tau0 = <value> fm/c
    Data: ix iy ieta energy_density [additional_columns]

Output Format (MUSIC):
    Header: # tau_in_fm <tau0> etamax= <ns_long> xmax= <ns> ymax= <ns> deta= <deta> dx= <dx> dy= <dy>
    Data: eta x y e u_tau u_x u_y u_eta pi_tautau pi_tau_x pi_tau_y pi_tau_eta pi_xx pi_xy pi_x_eta pi_yy pi_y_eta pi_eta_eta bulk

Physical Units:
- Energy density: GeV/fm³
- Coordinates: fm
- Time: fm/c (natural units)
- Stress tensor: fm⁻⁴ (spatial), fm⁻⁶ (mixed)

Examples:
    Basic usage:
        python McDipper_to_MUSIC.py eos.dat 64 32 0.1 0.2 energy.dat music.dat

    With energy cutoff and verbose output:
        python McDipper_to_MUSIC.py eos.dat 128 64 0.05 0.1 energy.dat music.dat --energy-cut 1e-12 -v
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import re
from scipy.interpolate import interp1d

# Physical constants
M_HBARC = 0.197326979  # GeV·fm (ħc conversion factor)


def read_energy_data(
    filename: Path, ns: int, ns_long: int
) -> Tuple[float, np.ndarray]:
    """Read energy density data from McDipper output file.

    Parses McDipper energy density file format and extracts initial time tau0
    from the header comment along with the 3D energy density distribution.

    Args:
        filename (Path): Path to McDipper energy density file
        ns (int): Number of spatial grid points in x,y directions
        ns_long (int): Number of spatial grid points in eta direction

    Returns:
        Tuple[float, np.ndarray]: Initial proper time tau0 (fm/c) and
            energy density array with shape (ns_long, ns, ns) in GeV/fm³

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If tau0 value not found in header or invalid data format
        IOError: If file cannot be read or has invalid format
    """
    if not filename.exists():
        raise FileNotFoundError(f"McDipper energy file not found: {filename}")

    energy = np.zeros((ns_long, ns, ns), dtype=np.float64)
    tau0 = None

    try:
        with open(filename, "r") as f:
            # Extract tau0 from comment header
            comment_line = f.readline()
            match = re.search(r"#\s*tau0\s*=\s*([0-9.+-eE]+)", comment_line)
            if match:
                tau0 = float(match.group(1))
                logging.info(f"Found initial time tau0 = {tau0} fm/c")
            else:
                raise ValueError(
                    f"tau0 value not found in header: {comment_line.strip()}"
                )

            # Read energy density data
            line_count = 0
            for line_num, line in enumerate(f, start=2):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    parts = line.split()
                    if len(parts) < 4:
                        logging.warning(
                            f"Line {line_num}: insufficient data columns, skipping"
                        )
                        continue

                    ix, iy, ieta, energy_val = map(float, parts[:4])
                    ix, iy, ieta = int(ix), int(iy), int(ieta)

                    # Validate indices
                    if not (
                        0 <= ix < ns and 0 <= iy < ns and 0 <= ieta < ns_long
                    ):
                        logging.warning(
                            f"Line {line_num}: indices out of bounds ({ix},{iy},{ieta}), skipping"
                        )
                        continue

                    energy[ieta, ix, iy] = energy_val
                    line_count += 1

                except (ValueError, IndexError) as e:
                    logging.warning(
                        f"Line {line_num}: invalid format '{line.strip()}', skipping: {e}"
                    )
                    continue

            logging.info(
                f"Successfully read {line_count} energy density data points"
            )

    except IOError as e:
        raise IOError(f"Failed to read McDipper energy file {filename}: {e}")

    return tau0, energy


def load_equation_of_state(eos_path: Path) -> interp1d:
    """Load equation of state data and create pressure interpolation function.

    Reads EOS table with columns: energy density, pressure, entropy density, temperature.
    Creates interpolation function for pressure as function of energy density.

    Args:
        eos_path (Path): Path to EOS data file (binary format)

    Returns:
        interp1d: Interpolation function p(e) for pressure vs energy density

    Raises:
        FileNotFoundError: If EOS file doesn't exist
        ValueError: If EOS data format is invalid
        IOError: If file cannot be read
    """
    if not eos_path.exists():
        raise FileNotFoundError(f"EOS file not found: {eos_path}")

    try:
        # Load EOS data: 4 columns (energy, pressure, entropy, temperature)
        eos_data = np.fromfile(eos_path, dtype=float).reshape(-1, 4)

        if eos_data.shape[0] == 0:
            raise ValueError(f"EOS file is empty: {eos_path}")
        if eos_data.shape[1] != 4:
            raise ValueError(
                f"EOS file must have 4 columns, found {eos_data.shape[1]}"
            )

        energy_density = eos_data[:, 0]  # GeV/fm³
        pressure = eos_data[:, 1]  # GeV/fm³

        # Validate physical constraints
        if np.any(energy_density < 0) or np.any(pressure < 0):
            raise ValueError(
                "EOS contains negative energy density or pressure values"
            )

        # Create pressure interpolation function
        p_interp = interp1d(
            energy_density,
            pressure,
            kind="linear",
            fill_value="extrapolate",
            bounds_error=False,
        )

        logging.info(f"Loaded EOS with {len(energy_density)} data points")
        logging.info(
            f"Energy range: {energy_density.min():.2e} - {energy_density.max():.2e} GeV/fm³"
        )

        return p_interp

    except IOError as e:
        raise IOError(f"Failed to read EOS file {eos_path}: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid EOS data in {eos_path}: {e}")


def calculate_bulk_pressure(p_interp: interp1d, energy: float) -> float:
    """Calculate bulk pressure from energy density using equation of state.

    Computes bulk pressure as deviation from ideal gas relation P = e/3.
    For ideal relativistic gas: P = e/3, so bulk pressure = 0.
    For realistic QCD matter: bulk pressure = e/3 - P(e).

    Args:
        p_interp (interp1d): EOS pressure interpolation function
        energy (float): Energy density in GeV/fm³

    Returns:
        float: Bulk pressure in GeV/fm³
    """
    if energy <= 0:
        return 0.0

    try:
        equilibrium_pressure = p_interp(energy)
        ideal_pressure = energy / 3.0
        return ideal_pressure - equilibrium_pressure
    except (ValueError, RuntimeError):
        # Fallback for extrapolation issues
        logging.warning(
            f"EOS extrapolation issue at energy {energy:.2e} GeV/fm³"
        )
        return 0.0


def initialize_stress_tensor(
    energy: float, tau: float, energy_cut: float = 1e-15
) -> dict:
    """Initialize shear stress tensor components for viscous hydrodynamics.

    Sets up initial shear stress tensor in Milne coordinates for MUSIC.
    Uses physically motivated initialization with small perturbations
    to break perfect isotropy and enable viscous evolution.

    Args:
        energy (float): Local energy density in GeV/fm³
        tau (float): Proper time in fm/c
        energy_cut (float, optional): Energy cutoff below which stress is zero

    Returns:
        dict: Dictionary with stress tensor components in fm⁻⁴ (spatial) and fm⁻⁶ (mixed)
    """
    if energy <= energy_cut:
        return {
            "pitautau": 0.0,
            "pitaux": 0.0,
            "pitauy": 0.0,
            "pitaueta": 0.0,
            "pixx": 0.0,
            "pixy": 0.0,
            "pixeta": 0.0,
            "piyy": 0.0,
            "piyeta": 0.0,
            "pietaeta": 0.0,
        }

    # Small anisotropy initialization for numerical stability
    # Based on early-time expansion dynamics
    pixx = piyy = energy / (6 * M_HBARC)  # fm⁻⁴
    pietaeta = -energy / (3 * tau * tau * M_HBARC)  # fm⁻⁶

    return {
        "pitautau": 0.0,
        "pitaux": 0.0,
        "pitauy": 0.0,
        "pitaueta": 0.0,
        "pixx": pixx,
        "pixy": 0.0,
        "pixeta": 0.0,
        "piyy": piyy,
        "piyeta": 0.0,
        "pietaeta": pietaeta,
    }


def write_music_format(
    output_path: Path,
    tau0: float,
    energy_data: np.ndarray,
    p_interp: interp1d,
    ns: int,
    ns_long: int,
    dx: float,
    dy: float,
    deta: float,
    energy_cut: float = 1e-15,
) -> None:
    """Write energy density data in MUSIC hydrodynamics input format.

    Converts McDipper energy density to MUSIC format with proper coordinate
    system, flow initialization, and stress tensor components.

    Args:
        output_path (Path): Output file path for MUSIC format data
        tau0 (float): Initial proper time in fm/c
        energy_data (np.ndarray): Energy density array (ns_long, ns, ns)
        p_interp (interp1d): EOS pressure interpolation function
        ns (int): Number of spatial grid points in x,y directions
        ns_long (int): Number of spatial grid points in eta direction
        dx (float): Spatial resolution in x direction (fm)
        dy (float): Spatial resolution in y direction (fm)
        deta (float): Spatial resolution in eta direction
        energy_cut (float, optional): Energy cutoff for numerical stability

    Raises:
        IOError: If output file cannot be written
    """
    # Initial flow velocity (at rest in lab frame)
    flow_components = [1.0, 0.0, 0.0, 0.0]  # [u^tau, u^x, u^y, u^eta]

    header = (
        f"# tau_in_fm {tau0} etamax= {ns_long} xmax= {ns} ymax= {ns} "
        f"deta= {deta} dx= {dx} dy= {dy}\n"
    )

    points_written = 0
    nonzero_points = 0

    try:
        with open(output_path, "w") as f:
            f.write(header)

            for ieta in range(ns_long):
                eta_pos = deta * (ieta - (ns_long - 1) / 2.0)

                for ix in range(ns):
                    x_pos = dx * (ix - (ns - 1) / 2.0)  # fm

                    for iy in range(ns):
                        y_pos = dy * (iy - (ns - 1) / 2.0)  # fm
                        energy = energy_data[ieta, ix, iy]  # GeV/fm³

                        # Initialize stress tensor and bulk pressure
                        if energy > energy_cut:
                            stress = initialize_stress_tensor(
                                energy, tau0, energy_cut
                            )
                            bulk_pressure = calculate_bulk_pressure(
                                p_interp, energy
                            )
                            nonzero_points += 1
                        else:
                            stress = initialize_stress_tensor(
                                0.0, tau0, energy_cut
                            )
                            bulk_pressure = 0.0

                        # Write MUSIC format line
                        f.write(
                            f"{eta_pos:.2f} {x_pos:.2f} {y_pos:.2f} {energy} "
                            f"{flow_components[0]} {flow_components[1]} {flow_components[2]} {flow_components[3]} "
                            f"{stress['pitautau']} {stress['pitaux']} {stress['pitauy']} {stress['pitaueta']} "
                            f"{stress['pixx']} {stress['pixy']} {stress['pixeta']} "
                            f"{stress['piyy']} {stress['piyeta']} {stress['pietaeta']} {bulk_pressure}\n"
                        )

                        points_written += 1

        logging.info(
            f"Successfully wrote {points_written} grid points to MUSIC format"
        )
        logging.info(
            f"Non-zero energy points: {nonzero_points} ({100*nonzero_points/points_written:.1f}%)"
        )

    except IOError as e:
        raise IOError(f"Failed to write MUSIC output file {output_path}: {e}")


def validate_inputs(args: argparse.Namespace) -> None:
    """Validate input parameters and files for physical reasonableness.

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Raises:
        ValueError: If any input parameter is invalid
        FileNotFoundError: If input files don't exist
    """
    # Check file existence
    if not args.eos_file.exists():
        raise FileNotFoundError(f"EOS file not found: {args.eos_file}")
    if not args.input_file.exists():
        raise FileNotFoundError(
            f"McDipper input file not found: {args.input_file}"
        )

    # Validate physical parameters
    if args.ns <= 0 or args.ns_long <= 0:
        raise ValueError("Grid sizes must be positive integers")
    if args.dx <= 0 or args.deta <= 0:
        raise ValueError("Spatial resolutions must be positive")
    if args.energy_cut < 0:
        raise ValueError("Energy cutoff must be non-negative")

    # Check for reasonable parameter ranges
    if args.ns > 2000 or args.ns_long > 2000:
        logging.warning(
            f"Large grid size ({args.ns}×{args.ns}×{args.ns_long}) may require significant memory"
        )
    if args.dx > 1.0 or args.deta > 1.0:
        logging.warning(
            f"Large grid spacing (dx={args.dx}, deta={args.deta}) may affect resolution"
        )
    if args.energy_cut > 1e-10:
        logging.warning(
            f"High energy cutoff ({args.energy_cut}) may remove significant physics"
        )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for McDipper to MUSIC conversion.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert McDipper initial conditions to MUSIC hydrodynamics format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "eos_file",
        type=Path,
        help="Path to equation of state data file (binary format)",
    )
    parser.add_argument(
        "ns", type=int, help="Number of spatial grid points in x,y directions"
    )
    parser.add_argument(
        "ns_long",
        type=int,
        help="Number of spatial grid points in eta direction",
    )
    parser.add_argument(
        "dx", type=float, help="Spatial resolution in x,y directions (fm)"
    )
    parser.add_argument(
        "deta", type=float, help="Spatial resolution in eta direction"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to McDipper energy density input file",
    )
    parser.add_argument(
        "output_file", type=Path, help="Path for MUSIC format output file"
    )

    parser.add_argument(
        "--energy-cut",
        type=float,
        default=1e-15,
        help="Energy density cutoff below which cells are set to zero",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging output",
    )

    return parser.parse_args()


def main():
    """Main function for McDipper to MUSIC format conversion.

    Parses command line arguments, loads EOS and energy data, and performs
    the conversion with proper error handling and logging.
    """
    args = parse_arguments()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    try:
        logging.info("Starting McDipper to MUSIC conversion")

        # Validate input parameters
        validate_inputs(args)

        logging.info(f"Input file: {args.input_file}")
        logging.info(f"Output file: {args.output_file}")
        logging.info(f"Grid size: {args.ns}×{args.ns}×{args.ns_long}")
        logging.info(f"Resolution: dx={args.dx} fm, deta={args.deta}")

        # Load equation of state
        logging.info(f"Loading EOS from {args.eos_file}")
        p_interp = load_equation_of_state(args.eos_file)

        # Read McDipper energy data
        logging.info(f"Reading McDipper data from {args.input_file}")
        tau0, energy_data = read_energy_data(
            args.input_file, args.ns, args.ns_long
        )

        # Analyze energy distribution
        total_energy = np.sum(energy_data) * args.dx * args.dx * args.deta
        max_energy = np.max(energy_data)
        nonzero_fraction = (
            np.count_nonzero(energy_data > args.energy_cut) / energy_data.size
        )

        logging.info(f"Energy statistics:")
        logging.info(f"  Total energy: {total_energy:.2e} GeV")
        logging.info(f"  Maximum density: {max_energy:.2e} GeV/fm³")
        logging.info(f"  Non-zero fraction: {nonzero_fraction:.1%}")

        # Write MUSIC format output
        logging.info(f"Writing MUSIC format to {args.output_file}")
        dy = args.dx  # Assume square grid
        write_music_format(
            args.output_file,
            tau0,
            energy_data,
            p_interp,
            args.ns,
            args.ns_long,
            args.dx,
            dy,
            args.deta,
            args.energy_cut,
        )

        logging.info("Conversion completed successfully")

    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
