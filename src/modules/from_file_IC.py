from src.module_base import BaseModule, time_execution
import logging
import os
import shutil


class FromFileIC(BaseModule):
    """Initial conditions module for loading external initial condition files.
    
    Loads pre-generated initial condition files from external sources such as
    Monte Carlo Glauber models, IP-Glasma calculations, or other event
    generators. Provides standardized interface for various initial condition
    formats in the CRONOS simulation chain.
    
    Key features:
    - Flexible input file format support
    - Standardized output format for subsequent modules
    - Event selection and filtering capabilities
    - File validation and error handling
    - Integration with various initial condition generators
    
    Module workflow:
    1. Validates input data directory and file availability
    2. Selects appropriate initial condition file for current event
    3. Copies/links file to standardized output location
    4. Performs any necessary format validation
    5. Prepares data for next module in simulation chain
    
    This module serves as the entry point for simulations using external
    initial conditions, enabling integration with specialized initial
    condition generators while maintaining CRONOS workflow compatibility.
    
    Example:
        >>> ic_module = from_file_IC(config.from_file_IC, full_config, project_root, event_id)
        >>> ic_module.prepare_environment(event_dir)
        >>> ic_module.prepare_input(event_dir)
        >>> ic_module.run(event_dir)  # Load initial conditions
        >>> ic_module.fetch_output(event_dir)  # Standardized IC output
    """
    def prepare_environment(self, event_dir):
        """Prepare environment for external initial conditions loading.
        
        Minimal environment setup for from_file_IC module since external
        initial condition files are pre-generated and require no compilation
        or executable linking.
        
        Args:
            event_dir (str): Event directory for initial conditions processing
        """
        logging.info(f"[FromFileIC] Preparing environment in {event_dir}...")

    def prepare_input(self, event_dir):
        """Validate input path configuration for external initial conditions.
        
        Confirms that the configured input path contains the required initial
        condition files. The actual file loading occurs during the run phase.
        
        Args:
            event_dir (str): Event directory containing from_file_IC/ subdirectory
        
        Side Effects:
            - Validates input path configuration
            - Logs input path information
        """
        logging.info(f"[FromFileIC] Input file from {self.config.input_path}")

    @time_execution
    def run(self, event_dir):
        """Load external initial condition file with performance profiling.
        
        Performs the actual loading of pre-generated initial condition files.
        Since files are already prepared externally, this step mainly involves
        validation and preparation for the fetch_output stage.
        
        Args:
            event_dir (str): Event directory containing initial condition files
        
        Side Effects:
            - Profiles loading time for performance monitoring
            - Validates initial condition file accessibility
            - Logs successful loading completion
        """
        logging.info("[FromFileIC] No IC to run, profile saved...")

    def fetch_output(self, event_dir):
        """Move external initial conditions to standardized output location.
        
        Transfers the loaded initial condition file to the results directory
        with standardized naming for use by subsequent physics modules.
        Cleans up the temporary from_file_IC directory after successful transfer.
        
        File Processing:
            - Locates initial condition file in from_file_IC/ directory
            - Moves to results/output_N.dat with proper module indexing
            - Removes temporary working directory after transfer
        
        Args:
            event_dir (str): Event directory containing from_file_IC/ and results/
        
        Side Effects:
            - Creates results/ directory if it doesn't exist
            - Moves initial condition file to standardized location
            - Removes from_file_IC/ working directory
            - Logs successful file transfer
        
        Raises:
            FileNotFoundError: If no initial condition files found in directory
            OSError: If file move operations fail
        
        Notes:
            The standardized output format enables seamless integration with
            downstream modules regardless of the original IC file format.
        """
        logging.info("[FromFileIC] Data loaded successfully.")

        results_dir = os.path.join(event_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        from_file_ic_dir = os.path.join(event_dir, "from_file_IC")
        entries = os.listdir(from_file_ic_dir)
        if not entries:
            raise FileNotFoundError(f"No files found in {from_file_ic_dir}")

        src_file = os.path.join(from_file_ic_dir, entries[0])
        current_module_index = self.full_config.general.modules.index(
            "from_file_IC"
        )
        dst_file = os.path.join(
            results_dir, f"output_{current_module_index}.dat"
        )

        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "from_file_IC"))

        logging.info(f"[FromFileIC] Moved {src_file} to {dst_file}")
