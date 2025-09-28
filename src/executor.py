from src.module_base import BaseModule
from src.handle_results import handle_results
import logging
import os
import shutil
import pprint


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


def run_modules(config, module_registry, job_dir, project_root):
    """
    Run all modules listed in config.general.modules in order.

    Args:
        config (Configuration): Loaded configuration object.
        module_registry (dict): Mapping of module name -> Module class.
    """
    job_dir = os.path.abspath(job_dir)
    if not os.path.exists(job_dir):
        logging.error(f"Job directory '{job_dir}' does not exist.")
        exit(1)

    # loop over the event directories in the job directory
    for event_dir in os.listdir(job_dir):
        event_dir_path = os.path.join(job_dir, event_dir)

        # Check that the event directory exists
        if not os.path.exists(event_dir_path):
            logging.error(f"Event directory '{event_dir_path}' does not exist.")
            exit(1)

        event_id = event_dir.split("_")[-1]

        for module_name in config.general.modules:
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

            module_instance.prepare_input(event_dir_path)
            module_instance.run(event_dir_path)
            module_instance.fetch_output(event_dir_path)

        event_dir_results_path = os.path.join(event_dir_path, "results")
        if not os.path.exists(event_dir_results_path):
            logging.error(
                f"Results directory '{event_dir_results_path}' does not exist."
            )
            exit(1)
        else:
            logging.info(f"Handling results in {event_dir_results_path}...")
            # create a file named configuration.py in the results directory and write the current configuration to it
            with open(
                os.path.join(event_dir_results_path, "configuration.py"), "w"
            ) as f:
                for section, values in config.to_dict().items():
                    f.write(f"{section} = \\\n")
                    pprint.pprint(
                        values, stream=f, indent=4, width=80, compact=False
                    )
                    f.write("\n\n")
            handle_results(config, event_dir_results_path, event_id)

        # Move the h5 file to the job directory
        hdf5_filename = os.path.join(
            event_dir_results_path, f"event_{event_id}.h5"
        )
        if os.path.exists(hdf5_filename):
            shutil.move(
                hdf5_filename, os.path.join(job_dir, f"event_{event_id}.h5")
            )
            logging.info(f"Moved {hdf5_filename} to {job_dir}")
            # Remove the event directory after moving the h5 file
            shutil.rmtree(event_dir_path)
            logging.info(f"Removed event directory {event_dir_path}")
        else:
            logging.warning(
                f"HDF5 file '{hdf5_filename}' not found, skipping move."
            )
