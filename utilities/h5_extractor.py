#!/usr/bin/env python3
"""
HDF5 File Extractor Utility for CRONOS

This utility provides functionality to:
1. List all datasets and groups in an HDF5 file with indices
2. Allow interactive selection of datasets to extract
3. Export selected datasets to their native/original format
4. Provide both programmatic and command-line interfaces

Usage:
    python utilities/h5_extractor.py input.h5 --output-dir extracted_data/
    python utilities/h5_extractor.py input.h5 --list-only
    python utilities/h5_extractor.py input.h5 --extract 1,3,5
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import logging
from datetime import datetime

try:
    import h5py
    import numpy as np
except ImportError as e:
    print(f"Required dependencies missing: {e}")
    print("Install with: pip install h5py numpy")
    sys.exit(1)

# Add the parent directory to path for CRONOS imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.colors import Colors
except ImportError:
    # Fallback if colors module is not available
    class Colors:
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        MAGENTA = "\033[95m"
        CYAN = "\033[96m"
        WHITE = "\033[97m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        UNDERLINE = "\033[4m"
        BLINK = "\033[5m"
        RESET = "\033[0m"


class HDF5Extractor:
    """
    A comprehensive utility for extracting and analyzing HDF5 files from CRONOS simulations.
    """

    def __init__(
        self,
        h5_file_path: str,
        output_dir: str = "extracted_data",
        log_level: str = "INFO",
    ):
        """
        Initialize the HDF5 extractor.

        Args:
            h5_file_path (str): Path to the HDF5 file to process
            output_dir (str): Directory to save extracted files
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.h5_file_path = Path(h5_file_path)
        self.output_dir = Path(output_dir)
        self.datasets_info = []
        self.groups_info = []

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # Validate inputs
        self._validate_inputs()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _validate_inputs(self) -> None:
        """Validate input file and paths."""
        if not self.h5_file_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {self.h5_file_path}")

        if not self.h5_file_path.suffix.lower() in [".h5", ".hdf5"]:
            self.logger.warning(
                f"File extension {self.h5_file_path.suffix} may not be HDF5"
            )

    def scan_h5_file(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Scan the HDF5 file and collect information about all datasets and groups.

        Returns:
            Tuple[List[Dict], List[Dict]]: Lists of dataset and group information
        """
        self.logger.info(f"Scanning HDF5 file: {self.h5_file_path}")

        datasets = []
        groups = []

        def collect_info(name, obj):
            if isinstance(obj, h5py.Dataset):
                info = {
                    "name": name,
                    "path": name,
                    "shape": obj.shape,
                    "dtype": str(obj.dtype),
                    "size": obj.size,
                    "size_mb": obj.nbytes / (1024 * 1024),
                    "attributes": dict(obj.attrs) if obj.attrs else {},
                }
                datasets.append(info)
                self.logger.debug(
                    f"Found dataset: {name}, shape: {obj.shape}, dtype: {obj.dtype}"
                )

            elif isinstance(obj, h5py.Group):
                info = {
                    "name": name,
                    "path": name,
                    "attributes": dict(obj.attrs) if obj.attrs else {},
                    "num_items": len(obj.keys()),
                }
                groups.append(info)
                self.logger.debug(
                    f"Found group: {name}, items: {len(obj.keys())}"
                )

        try:
            with h5py.File(self.h5_file_path, "r") as h5_file:
                h5_file.visititems(collect_info)

        except Exception as e:
            self.logger.error(f"Error scanning HDF5 file: {e}")
            raise

        self.datasets_info = datasets
        self.groups_info = groups

        self.logger.info(
            f"Scan complete: {len(datasets)} datasets, {len(groups)} groups"
        )
        return datasets, groups

    def display_file_contents(self) -> None:
        """Display the contents of the HDF5 file in a user-friendly format."""
        if not self.datasets_info:
            self.scan_h5_file()

        print(
            f"\n{Colors.BOLD}{Colors.CYAN}=== HDF5 File Contents ==={Colors.RESET}"
        )
        print(f"{Colors.BLUE}File: {self.h5_file_path}{Colors.RESET}")
        print(
            f"{Colors.BLUE}Total datasets: {len(self.datasets_info)}{Colors.RESET}"
        )
        print(
            f"{Colors.BLUE}Total groups: {len(self.groups_info)}{Colors.RESET}\n"
        )

        # Display groups
        if self.groups_info:
            print(f"{Colors.BOLD}{Colors.YELLOW}Groups:{Colors.RESET}")
            for i, group in enumerate(self.groups_info):
                print(
                    f"  {Colors.MAGENTA}G{i:2d}{Colors.RESET}: {group['name']} "
                    f"({group['num_items']} items)"
                )
            print()

        # Display datasets
        if self.datasets_info:
            print(f"{Colors.BOLD}{Colors.GREEN}Datasets:{Colors.RESET}")
            for i, dataset in enumerate(self.datasets_info):
                size_str = (
                    f"{dataset['size_mb']:.2f} MB"
                    if dataset["size_mb"] > 0.1
                    else f"{dataset['size']} elements"
                )
                print(
                    f"  {Colors.GREEN}{i:2d}{Colors.RESET}: {dataset['name']}"
                )
                print(
                    f"       Shape: {dataset['shape']}, Type: {dataset['dtype']}, Size: {size_str}"
                )

                # Show attributes if available
                if dataset["attributes"]:
                    print(
                        f"       Attributes: {list(dataset['attributes'].keys())}"
                    )
                print()

        if not self.datasets_info and not self.groups_info:
            print(
                f"{Colors.RED}No datasets or groups found in file.{Colors.RESET}"
            )

    def get_user_selection(self) -> List[int]:
        """
        Get user selection of datasets to extract.

        Returns:
            List[int]: List of selected dataset indices
        """
        if not self.datasets_info:
            print(
                f"{Colors.RED}No datasets available for selection.{Colors.RESET}"
            )
            return []

        print(f"\n{Colors.BOLD}Select datasets to extract:{Colors.RESET}")
        print(f"Enter dataset numbers separated by commas (e.g., 0,2,5)")
        print(f"Enter 'all' to select all datasets")
        print(f"Enter 'quit' to exit")

        while True:
            try:
                user_input = input(
                    f"\n{Colors.CYAN}Your selection: {Colors.RESET}"
                ).strip()

                if user_input.lower() == "quit":
                    return []

                if user_input.lower() == "all":
                    return list(range(len(self.datasets_info)))

                # Parse comma-separated indices
                selected_indices = []
                for item in user_input.split(","):
                    item = item.strip()
                    if item.isdigit():
                        idx = int(item)
                        if 0 <= idx < len(self.datasets_info):
                            selected_indices.append(idx)
                        else:
                            print(
                                f"{Colors.RED}Index {idx} out of range (0-{len(self.datasets_info)-1}){Colors.RESET}"
                            )
                            continue
                    else:
                        print(
                            f"{Colors.RED}Invalid input: {item}. Please use numbers.{Colors.RESET}"
                        )
                        continue

                if selected_indices:
                    return sorted(
                        list(set(selected_indices))
                    )  # Remove duplicates and sort
                else:
                    print(
                        f"{Colors.RED}No valid indices selected. Please try again.{Colors.RESET}"
                    )

            except KeyboardInterrupt:
                print(
                    f"\n{Colors.YELLOW}Operation cancelled by user.{Colors.RESET}"
                )
                return []
            except Exception as e:
                print(
                    f"{Colors.RED}Error parsing input: {e}. Please try again.{Colors.RESET}"
                )

    def extract_dataset(self, dataset_info: Dict) -> Optional[str]:
        """
        Extract a single dataset in native format.

        Args:
            dataset_info (Dict): Dataset information dictionary

        Returns:
            Optional[str]: Path to the extracted file, or None if extraction failed
        """
        dataset_name = dataset_info["name"]
        self.logger.info(f"Extracting dataset: {dataset_name} to native format")

        try:
            with h5py.File(self.h5_file_path, "r") as h5_file:
                dataset = h5_file[dataset_name]
                # Handle scalar datasets properly
                if dataset.shape == ():
                    data = dataset[()]  # Use [()] for scalar datasets
                else:
                    data = dataset[:]

                # Create safe filename
                safe_name = dataset_name.replace("/", "_").replace("\\", "_")

                # Only native format is supported
                output_path = self._save_as_native(
                    dataset, safe_name, dataset_info
                )
                if not output_path:
                    self.logger.error(
                        f"Could not determine native format for {dataset_name}"
                    )
                    return None

                self.logger.info(f"Successfully extracted to: {output_path}")
                return str(output_path)

        except Exception as e:
            self.logger.error(f"Error extracting dataset {dataset_name}: {e}")
            return None

    def _save_as_native(
        self, dataset, safe_name: str, dataset_info: Dict
    ) -> Optional[str]:
        """
        Save data in its native/original format by analyzing metadata and data structure.

        This method attempts to reconstruct the original file format by examining:
        - HDF5 attributes that indicate original format
        - Data structure and content patterns
        - Filename patterns in the dataset name
        - Data type and shape characteristics

        Args:
            dataset: The h5py dataset object (not just data array)
            safe_name (str): Safe filename without path separators
            dataset_info (Dict): Dataset metadata information

        Returns:
            Optional[str]: Path to extracted file in native format, or None if failed
        """
        try:
            # Handle scalar datasets properly
            if dataset.shape == ():
                data = dataset[()]  # Use [()] for scalar datasets
            else:
                data = dataset[:]
            attributes = dict(dataset.attrs) if dataset.attrs else {}

            # Analyze attributes for format hints
            format_hint = self._detect_native_format(
                dataset_info, attributes, data
            )

            if format_hint == "config":
                return self._save_as_config_file(data, safe_name, attributes)
            elif format_hint == "particle_data":
                return self._save_as_particle_file(data, safe_name, attributes)
            elif format_hint == "text_table":
                return self._save_as_text_table(data, safe_name, attributes)
            elif format_hint == "binary_data":
                return self._save_as_binary_data(data, safe_name, attributes)
            elif format_hint == "source_code":
                return self._save_as_source_file(data, safe_name, attributes)
            else:
                # Fallback to smart format detection based on data characteristics
                return self._save_with_smart_detection(
                    data, safe_name, dataset_info, attributes
                )

        except Exception as e:
            self.logger.error(f"Error in native format detection: {e}")
            return None

    def _detect_native_format(
        self,
        dataset_info: Dict,
        attributes: Dict,
        data: Union[np.ndarray, bytes, str, Any],
    ) -> str:
        """Detect the likely native format based on various indicators."""
        name = dataset_info["name"].lower()
        dtype = dataset_info["dtype"]

        # Handle non-numpy data types first
        if isinstance(data, bytes):
            return "binary_data"
        elif isinstance(data, str):
            return (
                "source_code"
                if name.endswith((".py", ".cpp", ".c", ".h", ".sh"))
                else "config"
            )

        # Check for configuration files
        if "config" in name or name.endswith(".py") or name.endswith(".conf"):
            return "config"

        # Check for source code files
        if name.endswith((".py", ".cpp", ".c", ".h", ".sh", ".txt")):
            return "source_code"

        # Check for particle physics data patterns
        if any(
            keyword in name
            for keyword in [
                "particle",
                "track",
                "momentum",
                "position",
                "energy",
            ]
        ):
            return "particle_data"

        # Check for binary data markers
        if "binary" in attributes.get("format", "") or "dat" in name:
            return "binary_data"

        # Check for tabular data - ensure data is a numpy array with ndim attribute
        if (
            hasattr(data, "ndim")
            and data.ndim == 2
            and hasattr(data, "shape")
            and len(data.shape) > 1
            and data.shape[1] > 1
        ):
            return "text_table"

        return "auto"

    def _save_as_config_file(
        self, data: Union[np.ndarray, str], safe_name: str, attributes: Dict
    ) -> str:
        """Save as configuration file (Python or text format)."""
        if safe_name.endswith("_py") or safe_name.endswith(".py"):
            extension = ".py"
        elif "format" in attributes and attributes["format"] == "ini":
            extension = ".ini"
        else:
            extension = ".conf"

        output_path = self.output_dir / f"{safe_name}{extension}"

        with open(output_path, "w") as f:
            # Handle scalar string data
            if isinstance(data, (str, bytes)):
                content = (
                    data.decode("utf-8") if isinstance(data, bytes) else data
                )
                f.write(content)
            elif hasattr(data, "dtype") and data.dtype.kind in [
                "U",
                "S",
                "O",
            ]:  # String or object data
                if hasattr(data, "shape") and data.shape == ():  # Scalar
                    content = data.item()
                    if isinstance(content, bytes):
                        content = content.decode("utf-8")
                    f.write(str(content))
                elif hasattr(data, "size") and data.size == 1:
                    # Single string content
                    content = data.item()
                    if isinstance(content, bytes):
                        content = content.decode("utf-8")
                    f.write(str(content))
                else:
                    # Multiple strings, write line by line
                    for item in data.flat:
                        content = str(item)
                        if isinstance(item, bytes):
                            content = item.decode("utf-8")
                        f.write(content + "\n")
            else:
                # Numeric data - write as readable format
                f.write(f"# Configuration data extracted from HDF5\n")
                f.write(
                    f"# Original shape: {getattr(data, 'shape', 'scalar')}, type: {getattr(data, 'dtype', type(data))}\n\n"
                )
                if hasattr(data, "shape") and data.shape == ():
                    f.write(str(data.item()))
                else:
                    np.savetxt(f, data, fmt="%g")

        return str(output_path)

    def _save_as_particle_file(
        self, data: np.ndarray, safe_name: str, attributes: Dict
    ) -> str:
        """Save particle physics data in common format."""
        # Don't add .dat if the name already has it
        if safe_name.endswith(".dat"):
            output_path = self.output_dir / safe_name
        else:
            output_path = self.output_dir / f"{safe_name}.dat"

        with open(output_path, "w") as f:
            # Write header with metadata
            f.write("# Particle data extracted from CRONOS HDF5\n")
            if "units" in attributes:
                f.write(f"# Units: {attributes['units']}\n")
            if "description" in attributes:
                f.write(f"# Description: {attributes['description']}\n")

            # Write column headers based on data shape
            if data.ndim == 2:
                if data.shape[1] == 3:
                    f.write("# x y z\n")
                elif data.shape[1] == 4:
                    f.write("# px py pz E\n")
                else:
                    f.write(
                        f"# {' '.join([f'col{i}' for i in range(data.shape[1])])}\n"
                    )

            # Write data
            if data.ndim == 1:
                for val in data:
                    f.write(f"{val}\n")
            else:
                np.savetxt(f, data, fmt="%g")

        return str(output_path)

    def _save_as_text_table(
        self, data: np.ndarray, safe_name: str, attributes: Dict
    ) -> str:
        """Save as space-separated text table."""
        output_path = self.output_dir / f"{safe_name}.txt"

        with open(output_path, "w") as f:
            # Write metadata header
            f.write(f"# Data shape: {data.shape}\n")
            if attributes:
                for key, value in attributes.items():
                    f.write(f"# {key}: {value}\n")
            f.write("#\n")

            # Write data
            if data.ndim == 1:
                for val in data:
                    f.write(f"{val}\n")
            elif data.ndim == 2:
                np.savetxt(f, data, fmt="%g")
            else:
                # For higher dimensions, flatten and indicate structure
                f.write(
                    f"# Multi-dimensional data flattened from shape {data.shape}\n"
                )
                flat_data = data.flatten()
                for i, val in enumerate(flat_data):
                    f.write(f"{val}\n")

        return str(output_path)

    def _save_as_binary_data(
        self,
        data: Union[np.ndarray, bytes, str, Any],
        safe_name: str,
        attributes: Dict,
    ) -> str:
        """Save as binary data file with metadata."""
        # Don't add .dat if the name already has it
        if safe_name.endswith(".dat"):
            output_path = self.output_dir / safe_name
        else:
            output_path = self.output_dir / f"{safe_name}.dat"

        # Save binary data
        if isinstance(data, bytes):
            # Try to decode bytes as text and clean up if it's readable
            try:
                decoded_text = data.decode("utf-8", errors="strict")
                # Check if it looks like structured text data
                if "\n" in decoded_text or any(
                    c in decoded_text for c in "0123456789.-+e"
                ):
                    # Save as text with cleaned lines
                    with open(output_path, "w") as f:
                        cleaned_lines = [
                            line.strip() for line in decoded_text.splitlines()
                        ]
                        f.write("\n".join(cleaned_lines))
                        if cleaned_lines and not decoded_text.endswith("\n"):
                            f.write("\n")
                else:
                    # Save as binary if not structured text
                    with open(output_path, "wb") as f:
                        f.write(data)
            except UnicodeDecodeError:
                # Save as binary if not decodable
                with open(output_path, "wb") as f:
                    f.write(data)
        else:
            with open(output_path, "wb") as f:
                if hasattr(data, "tobytes"):
                    # NumPy array or similar with tobytes method
                    f.write(data.tobytes())
                else:
                    # Convert string or other types to bytes
                    data_str = str(data)
                    f.write(data_str.encode("utf-8"))

        # Save metadata
        meta_path = output_path.with_suffix(".dat.meta")
        with open(meta_path, "w") as f:
            # Determine if data was saved as text or binary
            is_text_file = False
            if isinstance(data, bytes):
                try:
                    decoded_text = data.decode("utf-8", errors="strict")
                    if "\n" in decoded_text or any(
                        c in decoded_text for c in "0123456789.-+e"
                    ):
                        is_text_file = True
                except UnicodeDecodeError:
                    pass

            if is_text_file:
                f.write(f"# Text data metadata (cleaned from bytes)\n")
                decoded_text = data.decode("utf-8", errors="replace")
                cleaned_lines = [
                    line.strip() for line in decoded_text.splitlines()
                ]
                f.write(f"lines: {len(cleaned_lines)}\n")
                f.write(f"original_size_bytes: {len(data)}\n")
                f.write(f"type: decoded_text\n")
            else:
                f.write(f"# Binary data metadata\n")
                if hasattr(data, "shape"):
                    f.write(f"shape: {data.shape}\n")
                else:
                    f.write(f"shape: N/A (bytes/string data)\n")
                if hasattr(data, "dtype"):
                    f.write(f"dtype: {data.dtype}\n")
                else:
                    f.write(f"dtype: {type(data).__name__}\n")
                if hasattr(data, "nbytes"):
                    f.write(f"size_bytes: {data.nbytes}\n")
                elif isinstance(data, bytes):
                    f.write(f"size_bytes: {len(data)}\n")
                else:
                    f.write(f"size_bytes: {len(str(data).encode('utf-8'))}\n")
            for key, value in attributes.items():
                f.write(f"{key}: {value}\n")

        return str(output_path)

    def _save_as_source_file(
        self, data: np.ndarray, safe_name: str, attributes: Dict
    ) -> str:
        """Save as source code file."""
        # Determine extension from name
        if safe_name.endswith("_py"):
            extension = ".py"
        elif safe_name.endswith("_cpp"):
            extension = ".cpp"
        elif safe_name.endswith("_c"):
            extension = ".c"
        elif safe_name.endswith("_h"):
            extension = ".h"
        elif safe_name.endswith("_sh"):
            extension = ".sh"
        else:
            extension = ".txt"

        output_path = self.output_dir / f"{safe_name}{extension}"

        with open(output_path, "w") as f:
            if data.dtype.kind in ["U", "S", "O"]:  # String data
                if data.size == 1:
                    content = str(data.item())
                    f.write(content)
                else:
                    for item in data.flat:
                        f.write(str(item) + "\n")
            else:
                f.write(f"# Numeric data from {safe_name}\n")
                f.write(f"# Shape: {data.shape}, Type: {data.dtype}\n")
                f.write(str(data))

        return str(output_path)

    def _save_with_smart_detection(
        self,
        data: Union[np.ndarray, bytes, str],
        safe_name: str,
        dataset_info: Dict,
        attributes: Dict,
    ) -> str:
        """Fallback method using smart detection based on data characteristics."""

        # Handle bytes data first
        if isinstance(data, bytes):
            # Try to decode bytes as text and clean up if it's readable
            try:
                decoded_text = data.decode("utf-8", errors="strict")
                # Check if it looks like structured text data
                if "\n" in decoded_text or any(
                    c in decoded_text for c in "0123456789.-+e"
                ):
                    # Save as text with cleaned lines
                    if safe_name.endswith(".dat"):
                        output_path = self.output_dir / safe_name
                    else:
                        output_path = self.output_dir / f"{safe_name}.dat"
                    with open(output_path, "w") as f:
                        # Clean up leading and trailing whitespace from each line
                        cleaned_lines = [
                            line.strip() for line in decoded_text.splitlines()
                        ]
                        f.write("\n".join(cleaned_lines))
                        if cleaned_lines and not decoded_text.endswith("\n"):
                            f.write("\n")
                    # Create metadata file
                    meta_path = output_path.with_suffix(".dat.meta")
                    with open(meta_path, "w") as f:
                        f.write(
                            f"# Text data from HDF5 dataset (decoded from bytes)\n"
                        )
                        f.write(f"size_bytes: {len(data)}\n")
                        f.write(f"lines: {len(cleaned_lines)}\n")
                        f.write(f"type: decoded_text\n")
                        for key, value in attributes.items():
                            f.write(f"{key}: {value}\n")
                    return str(output_path)
            except UnicodeDecodeError:
                pass  # Fall through to binary handling

            # Save as binary data if not decodable as text
            if safe_name.endswith(".dat"):
                output_path = self.output_dir / safe_name
            else:
                output_path = self.output_dir / f"{safe_name}.dat"
            with open(output_path, "wb") as f:
                f.write(data)
            # Also create a metadata file
            meta_path = output_path.with_suffix(".dat.meta")
            with open(meta_path, "w") as f:
                f.write(f"# Binary data from HDF5 dataset\n")
                f.write(f"size_bytes: {len(data)}\n")
                f.write(f"type: bytes\n")
                for key, value in attributes.items():
                    f.write(f"{key}: {value}\n")
            return str(output_path)

        # Handle string data
        elif isinstance(data, str):
            output_path = self.output_dir / f"{safe_name}.txt"
            with open(output_path, "w") as f:
                f.write(data)
            return str(output_path)

        # Handle numpy arrays
        elif hasattr(data, "dtype"):
            # For string/object data, save as text file
            if data.dtype.kind in ["U", "S", "O"]:
                output_path = self.output_dir / f"{safe_name}.txt"
                with open(output_path, "w") as f:
                    if hasattr(data, "size") and data.size == 1:
                        content = (
                            data.item() if hasattr(data, "item") else str(data)
                        )
                        if isinstance(content, bytes):
                            content = content.decode("utf-8", errors="replace")
                        # Clean up leading and trailing whitespace and write
                        cleaned_content = "\n".join(
                            line.strip() for line in str(content).splitlines()
                        )
                        f.write(cleaned_content)
                    else:
                        for item in (
                            data.flat if hasattr(data, "flat") else [data]
                        ):
                            content = str(item)
                            if isinstance(item, bytes):
                                content = item.decode("utf-8", errors="replace")
                            # Clean up leading and trailing whitespace from each line
                            cleaned_content = "\n".join(
                                line.strip() for line in content.splitlines()
                            )
                            f.write(cleaned_content + "\n")
                return str(output_path)

            # For 1D numeric data, save as column
            elif hasattr(data, "ndim") and data.ndim == 1:
                output_path = self.output_dir / f"{safe_name}.dat"
                with open(output_path, "w") as f:
                    f.write("# 1D numeric data\n")
                    for val in data:
                        f.write(f"{val}\n")
                return str(output_path)

            # For 2D data, save as table
            elif hasattr(data, "ndim") and data.ndim == 2:
                output_path = self.output_dir / f"{safe_name}.dat"
                with open(output_path, "w") as f:
                    f.write(
                        f"# 2D data table ({data.shape[0]} x {data.shape[1]})\n"
                    )
                    np.savetxt(f, data, fmt="%g")
                return str(output_path)

            # For higher dimensions, save as structured text
            elif hasattr(data, "ndim"):
                output_path = self.output_dir / f"{safe_name}.txt"
                with open(output_path, "w") as f:
                    f.write(f"# Multi-dimensional data\n")
                    f.write(f"# Shape: {data.shape}\n")
                    f.write(f"# Data:\n")
                    f.write(str(data))
                return str(output_path)

        # Fallback for any other type
        output_path = self.output_dir / f"{safe_name}.txt"
        with open(output_path, "w") as f:
            f.write(f"# Data type: {type(data)}\n")
            f.write(f"# Content:\n")
            f.write(str(data))
        return str(output_path)

    def extract_multiple_datasets(
        self, dataset_indices: List[int]
    ) -> List[str]:
        """
        Extract multiple datasets at once in native format.

        Args:
            dataset_indices (List[int]): List of dataset indices to extract

        Returns:
            List[str]: List of paths to extracted files
        """
        if not self.datasets_info:
            self.scan_h5_file()

        extracted_files = []

        print(
            f"\n{Colors.BOLD}Extracting {len(dataset_indices)} datasets...{Colors.RESET}"
        )

        for i, idx in enumerate(dataset_indices):
            if 0 <= idx < len(self.datasets_info):
                dataset_info = self.datasets_info[idx]
                print(
                    f"  {Colors.CYAN}[{i+1}/{len(dataset_indices)}]{Colors.RESET} "
                    f"Extracting: {dataset_info['name']}"
                )

                extracted_path = self.extract_dataset(dataset_info)
                if extracted_path:
                    extracted_files.append(extracted_path)
                    print(
                        f"    {Colors.GREEN}✓ Saved to: {extracted_path}{Colors.RESET}"
                    )
                else:
                    print(f"    {Colors.RED}✗ Failed to extract{Colors.RESET}")
            else:
                print(f"  {Colors.RED}✗ Invalid index: {idx}{Colors.RESET}")

        print(
            f"\n{Colors.BOLD}{Colors.GREEN}Extraction complete!{Colors.RESET}"
        )
        print(
            f"Successfully extracted {len(extracted_files)} out of {len(dataset_indices)} datasets"
        )
        print(f"Output directory: {self.output_dir}")

        return extracted_files

    def create_extraction_summary(self, extracted_files: List[str]) -> str:
        """
        Create a summary report of the extraction process.

        Args:
            extracted_files (List[str]): List of extracted file paths

        Returns:
            str: Path to the summary report
        """
        summary_path = self.output_dir / "extraction_summary.txt"

        with open(summary_path, "w") as f:
            f.write("HDF5 Extraction Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Source file: {self.h5_file_path}\n")
            f.write(f"Extraction date: {datetime.now()}\n")
            f.write(f"Output directory: {self.output_dir}\n")
            f.write(f"Total files extracted: {len(extracted_files)}\n\n")

            f.write("Extracted files:\n")
            for i, file_path in enumerate(extracted_files, 1):
                f.write(f"  {i:2d}. {Path(file_path).name}\n")

            f.write(f"\nTotal datasets in source: {len(self.datasets_info)}\n")
            f.write(f"Total groups in source: {len(self.groups_info)}\n")

        return str(summary_path)


def main():
    """Command-line interface for the HDF5 extractor."""
    parser = argparse.ArgumentParser(
        description="Extract datasets from HDF5 files into human-readable formats",
        epilog="Examples:\n"
        "  %(prog)s data.h5 --list-only\n"
        "  %(prog)s data.h5 --extract 0,2,5 --format csv\n"
        "  %(prog)s data.h5 --interactive\n"
        "  %(prog)s data.h5 --extract all --format json --output-dir results/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("h5_file", help="Path to the HDF5 file to process")
    parser.add_argument(
        "--list-only",
        "-l",
        action="store_true",
        help="Only list the contents without extracting",
    )
    parser.add_argument(
        "--extract",
        "-e",
        type=str,
        help='Comma-separated dataset indices to extract (or "all")',
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="extracted_data",
        help="Output directory (default: extracted_data)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode for dataset selection",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    try:
        # Initialize extractor
        extractor = HDF5Extractor(args.h5_file, args.output_dir, args.log_level)

        # Scan the file
        extractor.scan_h5_file()

        # Display contents
        extractor.display_file_contents()

        if args.list_only:
            print(f"\n{Colors.GREEN}File listing complete.{Colors.RESET}")
            return 0

        # Determine which datasets to extract
        selected_indices = []

        if args.extract:
            if args.extract.lower() == "all":
                selected_indices = list(range(len(extractor.datasets_info)))
            else:
                try:
                    selected_indices = [
                        int(x.strip()) for x in args.extract.split(",")
                    ]
                except ValueError:
                    print(
                        f"{Colors.RED}Error: Invalid dataset indices format{Colors.RESET}"
                    )
                    return 1
        elif args.interactive:
            selected_indices = extractor.get_user_selection()
        else:
            # Default to interactive mode if no extraction specified
            selected_indices = extractor.get_user_selection()

        if not selected_indices:
            print(
                f"\n{Colors.YELLOW}No datasets selected for extraction.{Colors.RESET}"
            )
            return 0

        # Extract selected datasets
        extracted_files = extractor.extract_multiple_datasets(selected_indices)

        # Create summary
        if extracted_files:
            summary_path = extractor.create_extraction_summary(extracted_files)
            print(
                f"\n{Colors.BLUE}Summary report saved to: {summary_path}{Colors.RESET}"
            )

    except FileNotFoundError as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        return 1
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user.{Colors.RESET}")
        return 1
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {e}{Colors.RESET}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
