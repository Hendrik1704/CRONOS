from src.module_base import BaseModule
from src.handle_results import handle_results
from src.colors import Colors
from src.cluster_submission import submission_script_cluster
from src.checkpoint_manager import CheckpointManager
import logging
import os
import shutil
import pprint
import traceback


def prepare_modules(args, config, module_registry, project_root):
    # Create the run directory if it does not exist and check that it is empty
    if not os.path.exists(args.run_dir):
        os.makedirs(args.run_dir)
    elif os.listdir(args.run_dir):
        logging.error(f"Run directory {args.run_dir} is not empty.")
        exit(1)
    IC_from_file = "from_file_IC" in config.general.modules
    if IC_from_file:
        logging.info(
            "FromFileIC is used, preparing separate job directories for each IC file."
        )
        input_path = config.from_file_IC.input_path
        ic_files = [f for f in os.listdir(input_path)]
        ic_files.sort()
        config.number_of_jobs = len(ic_files)
        config.number_events_per_job = 1  # Each IC file corresponds to one job
        logging.info(f"Found {config.number_of_jobs} IC files in {input_path}.")
    else:
        logging.info(
            f"Preparing {config.number_of_jobs} jobs with {config.number_events_per_job} events each."
        )

    # Create a directory for each job (job_0, job_1,...)
    for job_id in range(config.number_of_jobs):
        job_dir = os.path.join(args.run_dir, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)
        # Create a sub-directory for each event (event_0, event_1, ...)
        for event_id in range(config.number_events_per_job):
            event_dir = os.path.join(job_dir, f"event_{event_id}")
            os.makedirs(event_dir, exist_ok=True)

            # Create a directory for each module in config.general.modules in the event directory
            for module_name in config.general.modules:
                module_dir = os.path.join(event_dir, module_name)
                os.makedirs(module_dir, exist_ok=True)

                # Check that the module is in the module registry
                if module_name not in module_registry:
                    logging.error(f"Module '{module_name}' is not registered.")
                    exit(1)

                module_class = module_registry[module_name]
                if not issubclass(module_class, BaseModule):
                    raise TypeError(
                        f"Module '{module_name}' does not subclass BaseModule."
                    )

                module_config = getattr(config, module_name)
                module_instance = module_class(
                    module_config, full_config=config, project_root=project_root
                )
                module_instance.prepare_environment(event_dir)

                if IC_from_file and module_name == "from_file_IC":
                    # Copy the file in the created "from_file_IC" directory to the IC file in the module directory
                    ic_file = ic_files[job_id]
                    shutil.copy2(
                        os.path.join(input_path, ic_file),
                        os.path.join(module_dir, ic_file),
                    )
                    logging.debug(f"Copied {ic_file} to {module_dir}")

            # Create a result directory
            result_dir = os.path.join(event_dir, "results")
            os.makedirs(result_dir, exist_ok=True)

    submission_script_cluster(args, config)

    colored_message = f"Prepared {config.number_of_jobs} jobs with {config.number_events_per_job} events each in '{args.run_dir}'"
    colored_message = Colors.green(colored_message, bold=True)
    logging.info(colored_message)


def run_modules(config, module_registry, job_dir, project_root):
    """
    Run all modules listed in config.general.modules in order with checkpoint support.

    Args:
        config (Configuration): Loaded configuration object.
        module_registry (dict): Mapping of module name -> Module class.
        job_dir (str): Path to the job directory.
        project_root (str): Path to the project root.
    """
    job_dir = os.path.abspath(job_dir)
    if not os.path.exists(job_dir):
        logging.error(f"Job directory '{job_dir}' does not exist.")
        exit(1)

    # Initialize checkpoint manager
    checkpoint_manager = CheckpointManager(job_dir)
    
    # Log checkpoint summary if resuming
    if os.path.exists(checkpoint_manager.checkpoint_file):
        colored_msg = Colors.yellow("[CHECKPOINT] Resuming from previous checkpoint", bold=True)
        logging.info(colored_msg)
        logging.info(checkpoint_manager.get_summary())

    # loop over the event directories in the job directory
    for event_dir in os.listdir(job_dir):
        event_dir_path = os.path.join(job_dir, event_dir)

        # Skip non-directories and non-event directories (like checkpoint files)
        if not os.path.isdir(event_dir_path) or not event_dir.startswith("event_"):
            continue

        event_id = event_dir.split("_")[-1]

        # Check if this event should be skipped (already completed)
        if checkpoint_manager.should_skip_event(event_dir):
            colored_msg = Colors.green(f"[CHECKPOINT] Skipping completed {event_dir}")
            logging.info(colored_msg)
            continue

        # Determine where to resume processing for this event
        all_modules = config.general.modules
        start_index, resume_reason = checkpoint_manager.get_resume_point(event_dir, all_modules)
        
        if start_index >= len(all_modules):
            colored_msg = Colors.green(f"[CHECKPOINT] {resume_reason}")
            logging.info(colored_msg)
            continue
        
        if start_index > 0:
            colored_msg = Colors.yellow(f"[CHECKPOINT] {resume_reason}")
            logging.info(colored_msg)

        # Process modules starting from resume point
        modules_to_process = all_modules[start_index:]
        
        try:
            for module_name in modules_to_process:
                # Mark module as started in checkpoint
                checkpoint_manager.mark_module_started(event_dir, module_name)
                
                if module_name not in module_registry:
                    raise ValueError(
                        f"Module '{module_name}' not found in registry."
                    )

                module_class = module_registry[module_name]
                if not issubclass(module_class, BaseModule):
                    raise TypeError(
                        f"Module '{module_name}' does not subclass BaseModule."
                    )

                module_config = getattr(config, module_name)
                logging.debug(
                    f"Initializing module '{module_name}' with config: {module_config.to_dict()}"
                )
                module_instance = module_class(
                    module_config,
                    full_config=config,
                    project_root=project_root,
                    event_id=event_id,
                )

                # Execute module phases
                module_instance.prepare_input(event_dir_path)
                module_instance.run(event_dir_path)
                module_instance.fetch_output(event_dir_path)
                
                # Mark module as completed in checkpoint
                checkpoint_manager.mark_module_completed(event_dir, module_name)
        
        except Exception as e:
            # Determine which module was actually running when failure occurred
            current_module = "unknown"
            for i, module_name in enumerate(modules_to_process):
                event_status = checkpoint_manager.get_event_status(event_dir)
                if module_name not in event_status["completed_modules"]:
                    current_module = module_name
                    break
            
            checkpoint_manager.mark_module_failed(event_dir, current_module, str(e))
            colored_msg = Colors.red(f"[ERROR] Module '{current_module}' failed for {event_dir}: {e}")
            logging.error(colored_msg)
            
            # Log more detailed error information
            logging.error(f"Full traceback:\n{traceback.format_exc()}")
            
            # Re-raise the exception to maintain original behavior
            raise

        # Handle results and cleanup only if all modules completed successfully
        try:
            event_dir_results_path = os.path.join(event_dir_path, "results")
            if not os.path.exists(event_dir_results_path):
                raise FileNotFoundError(f"Results directory '{event_dir_results_path}' does not exist.")
            
            logging.info(f"Handling results in {event_dir_results_path}...")
            
            # Create configuration file in results directory
            try:
                config_file_path = os.path.join(event_dir_results_path, "configuration.py")
                with open(config_file_path, "w") as f:
                    for section, values in config.to_dict().items():
                        f.write(f"{section} = \\\n")
                        pprint.pprint(
                            values, stream=f, indent=4, width=80, compact=False
                        )
                        f.write("\n\n")
                logging.debug(f"Created configuration file: {config_file_path}")
            except Exception as e:
                logging.error(f"Failed to create configuration file: {e}")
                raise
            
            # Handle results processing
            try:
                handle_results(config, event_dir_results_path, event_id)
                logging.info("Results handling completed successfully")
            except Exception as e:
                logging.error(f"Results handling failed: {e}")
                raise

            # Move the h5 file to the job directory
            hdf5_filename = os.path.join(event_dir_results_path, f"event_{event_id}.h5")
            hdf5_destination = os.path.join(job_dir, f"event_{event_id}.h5")
            
            if os.path.exists(hdf5_filename):
                try:
                    shutil.move(hdf5_filename, hdf5_destination)
                    logging.info(f"Moved {hdf5_filename} to {job_dir}")
                except Exception as e:
                    logging.error(f"Failed to move HDF5 file: {e}")
                    raise
                
                # Remove the event directory after moving the h5 file
                try:
                    shutil.rmtree(event_dir_path)
                    logging.info(f"Removed event directory {event_dir_path}")
                except Exception as e:
                    logging.error(f"Failed to remove event directory: {e}")
                    # Don't raise here - file was moved successfully
                    logging.warning("Event directory cleanup failed, but simulation completed successfully")
            else:
                # Check if there are any expected output files
                result_files = [f for f in os.listdir(event_dir_results_path) if f.endswith(('.h5', '.dat', '.txt'))]
                if result_files:
                    logging.warning(f"HDF5 file '{hdf5_filename}' not found, but other result files exist: {result_files}")
                else:
                    logging.error(f"No output files found in results directory: {event_dir_results_path}")
                    raise FileNotFoundError(f"Expected output file '{hdf5_filename}' not found and no alternative results exist")

            # Mark event as completed in checkpoint (only if we got this far)
            checkpoint_manager.mark_event_completed(event_dir)
            
        except Exception as e:
            # Mark the event as failed if result processing fails
            checkpoint_manager.mark_module_failed(event_dir, "result_processing", str(e))
            colored_msg = Colors.red(f"[ERROR] Result processing failed for {event_dir}: {e}")
            logging.error(colored_msg)
            raise

    # Mark entire job as completed
    checkpoint_manager.mark_job_completed()

    # Optionally cleanup checkpoint file after successful completion
    # Default behavior is to cleanup checkpoints unless explicitly disabled
    cleanup_checkpoints = getattr(config.general, 'cleanup_checkpoints', True)
    if cleanup_checkpoints:
        checkpoint_manager.cleanup_checkpoint()
