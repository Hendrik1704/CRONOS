from src.module_base import BaseModule, time_execution
import logging
import os
import subprocess
import shutil


class afterburner_toolkit(BaseModule):
    def prepare_environment(self, event_dir):
        logging.info(
            f"[afterburner_toolkit] Preparing environment in {event_dir}..."
        )
        afterburner_toolkit_EOS_path = os.path.join(
            self.project_root,
            "external_codes",
            "hadronic_afterburner_toolkit",
            "EOS",
        )
        if os.path.exists(afterburner_toolkit_EOS_path):
            os.symlink(
                afterburner_toolkit_EOS_path,
                os.path.join(event_dir, "afterburner_toolkit", "EOS"),
            )
        else:
            logging.error(
                f"[afterburner_toolkit] Required directory {afterburner_toolkit_EOS_path} does not exist."
            )
            exit(1)

        # Check if SMASH is in the module list
        if "SMASH" in self.full_config.general.modules:
            # If SMASH is present, link the SMASH executable
            smash_converter_path = os.path.join(
                self.project_root,
                "external_codes",
                "hadronic_afterburner_toolkit",
                "convert_to_binary_SMASH.e",
            )
            if os.path.exists(smash_converter_path):
                os.symlink(
                    smash_converter_path,
                    os.path.join(
                        event_dir,
                        "afterburner_toolkit",
                        "convert_to_binary_SMASH.e",
                    ),
                )
            else:
                logging.error(
                    f"[afterburner_toolkit] Required executable {smash_converter_path} does not exist."
                )
                exit(1)
        else:
            logging.debug(
                "[afterburner_toolkit] SMASH module not found in configuration. Skipping SMASH converter linking."
            )

        # Link the afterburner_toolkit executable
        afterburner_toolkit_exe_path = os.path.join(
            self.project_root,
            "external_codes",
            "hadronic_afterburner_toolkit",
            "hadronic_afterburner_tools.e",
        )
        if os.path.exists(afterburner_toolkit_exe_path):
            os.symlink(
                afterburner_toolkit_exe_path,
                os.path.join(
                    event_dir,
                    "afterburner_toolkit",
                    "hadronic_afterburner_tools.e",
                ),
            )
        else:
            logging.error(
                f"[afterburner_toolkit] Required executable {afterburner_toolkit_exe_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        logging.info(f"[afterburner_toolkit] Create input file...")
        current_module_index = self.full_config.general.modules.index(
            "afterburner_toolkit"
        )
        self.config.input_filename = f"output_{current_module_index-1}.dat"

        afterburner_toolkit_dir = os.path.join(event_dir, "afterburner_toolkit")
        if not os.path.exists(afterburner_toolkit_dir):
            logging.error(
                f"[afterburner_toolkit] Required directory {afterburner_toolkit_dir} does not exist."
            )
            exit(1)

        input_file = os.path.join(
            event_dir, "results", self.config.input_filename
        )
        input_file = os.path.abspath(input_file)  # resolve relative path
        symlink_path = os.path.join(
            afterburner_toolkit_dir, self.config.input_filename
        )

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(input_file, symlink_path)
        logging.debug(f"Created symlink: {symlink_path} -> {input_file}")
        ini_file = os.path.join(afterburner_toolkit_dir, "parameters.dat")

        # If SMASH is used, then read_in_mode should be 7
        if (
            "SMASH" in self.full_config.general.modules
            and self.config.read_in_mode != 7
        ):
            self.config.read_in_mode = 7
            logging.info(
                "[afterburner_toolkit] SMASH module detected. Setting read_in_mode to 7."
            )
        elif (
            "SMASH" not in self.full_config.general.modules
            and self.config.read_in_mode == 7
        ):
            self.config.read_in_mode = 9
            logging.info(
                "[afterburner_toolkit] SMASH module not detected. Setting read_in_mode to default 9. Assuming iSS output format."
            )

        with open(ini_file, "w") as f:
            f.write(f"echo_level = {self.config.echo_level} #\n")
            f.write(f"read_in_mode = {self.config.read_in_mode} #\n")
            f.write(f"ecoOutput = {self.config.ecoOutput} #\n")
            f.write(f"analyze_flow = {self.config.analyze_flow} #\n")
            f.write(f"analyze_HBT = {self.config.analyze_HBT} #\n")
            f.write(
                f"analyze_balance_function = {self.config.analyze_balance_function} #\n"
            )
            f.write(f"analyze_ebe_yield = {self.config.analyze_ebe_yield} #\n")
            f.write(
                f"read_in_real_mixed_events = {self.config.read_in_real_mixed_events} #\n"
            )
            f.write(f"randomSeed = {self.config.randomSeed} #\n")
            f.write(f"particle_monval = {self.config.particle_monval} #\n")
            f.write(
                f"distinguish_isospin = {self.config.distinguish_isospin} #\n"
            )
            f.write(f"event_buffer_size = {self.config.event_buffer_size} #\n")
            f.write(
                f"resonance_weak_feed_down_flag = {self.config.resonance_weak_feed_down_flag} #\n"
            )
            f.write(
                f"resonance_feed_down_flag = {self.config.resonance_feed_down_flag} #\n"
            )
            f.write(
                f"select_resonances_flag = {self.config.select_resonances_flag} #\n"
            )
            f.write(
                f"resonance_weak_feed_down_Sigma_to_Lambda_flag = {self.config.resonance_weak_feed_down_Sigma_to_Lambda_flag} #\n"
            )
            f.write(f"net_particle_flag = {self.config.net_particle_flag} #\n")
            f.write(
                f"collect_neutral_particles = {self.config.collect_neutral_particles} #\n"
            )
            f.write(f"rapidity_shift = {self.config.rapidity_shift} #\n")
            f.write(
                f"readRapidityShiftFromFile = {self.config.readRapidityShiftFromFile} #\n"
            )
            f.write(f"order_max = {self.config.order_max} #\n")
            f.write(
                f"compute_correlation = {self.config.compute_correlation} #\n"
            )
            f.write(
                f"flag_charge_dependence = {self.config.flag_charge_dependence} #\n"
            )
            f.write(
                f"compute_corr_rap_dep = {self.config.compute_corr_rap_dep} #\n"
            )
            f.write(f"npT = {self.config.npT} #\n")
            f.write(f"pT_min = {self.config.pT_min} #\n")
            f.write(f"pT_max = {self.config.pT_max} #\n")
            f.write(f"rap_min = {self.config.rap_min} #\n")
            f.write(f"rap_max = {self.config.rap_max} #\n")
            f.write(f"rap_type = {self.config.rap_type} #\n")
            f.write(
                f"rapidity_distribution = {self.config.rapidity_distribution} #\n"
            )
            f.write(f"n_rap = {self.config.n_rap} #\n")
            f.write(f"rapidity_dis_min = {self.config.rapidity_dis_min} #\n")
            f.write(f"rapidity_dis_max = {self.config.rapidity_dis_max} #\n")
            f.write(
                f"vn_rapidity_dis_pT_min = {self.config.vn_rapidity_dis_pT_min} #\n"
            )
            f.write(
                f"vn_rapidity_dis_pT_max = {self.config.vn_rapidity_dis_pT_max} #\n"
            )
            f.write(
                f"rapidityPTDistributionFlag = {self.config.rapidityPTDistributionFlag} #\n"
            )
            f.write(
                f"pidwithRapidityPTDistribution = {self.config.pidwithRapidityPTDistribution} #\n"
            )
            f.write(
                f"pidwithPseudoRapCuts = {self.config.pidwithPseudoRapCuts} #\n"
            )
            f.write(f"check_spatial_dis = {self.config.check_spatial_dis} #\n")
            f.write(f"intrinsic_detas = {self.config.intrinsic_detas} #\n")
            f.write(f"intrinsic_dtau = {self.config.intrinsic_dtau} #\n")
            f.write(f"intrinsic_dx = {self.config.intrinsic_dx} #\n")
            f.write(
                f"long_comoving_boost = {self.config.long_comoving_boost} #\n"
            )
            f.write(
                f"needed_number_of_pairs = {self.config.needed_number_of_pairs} #\n"
            )
            f.write(
                f"number_of_oversample_events = {self.config.number_of_oversample_events} #\n"
            )
            f.write(
                f"number_of_mixed_events = {self.config.number_of_mixed_events} #\n"
            )
            f.write(
                f"invariant_radius_flag = {self.config.invariant_radius_flag} #\n"
            )
            f.write(f"azimuthal_flag = {self.config.azimuthal_flag} #\n")
            f.write(
                f"kT_differenitial_flag = {self.config.kT_differenitial_flag} #\n"
            )
            f.write(f"n_KT = {self.config.n_KT} #\n")
            f.write(f"KT_min = {self.config.KT_min} #\n")
            f.write(f"KT_max = {self.config.KT_max} #\n")
            f.write(f"n_Kphi = {self.config.n_Kphi} #\n")
            f.write(f"HBTrap_min = {self.config.HBTrap_min} #\n")
            f.write(f"HBTrap_max = {self.config.HBTrap_max} #\n")
            f.write(f"qnpts = {self.config.qnpts} #\n")
            f.write(f"q_min = {self.config.q_min} #\n")
            f.write(f"q_max = {self.config.q_max} #\n")
            f.write(f"reject_decay_flag = {self.config.reject_decay_flag} #\n")
            f.write(f"tau_reject = {self.config.tau_reject} #\n")
            f.write(f"particle_alpha = {self.config.particle_alpha} #\n")
            f.write(f"particle_beta = {self.config.particle_beta} #\n")
            f.write(f"Bnpts = {self.config.Bnpts} #\n")
            f.write(f"Brap_max = {self.config.Brap_max} #\n")
            f.write(f"BpT_min = {self.config.BpT_min} #\n")
            f.write(f"BpT_max = {self.config.BpT_max} #\n")
        logging.info("[afterburner_toolkit] Input file created successfully.")

    @time_execution
    def run(self, event_dir):
        logging.info("[afterburner_toolkit] run...")

        afterburner_toolkit_dir = os.path.join(event_dir, "afterburner_toolkit")
        afterburner_toolkit_converter = "convert_to_binary_SMASH.e"
        afterburner_toolkit_exe = "hadronic_afterburner_tools.e"
        logging.info("[afterburner_toolkit] Running afterburner_toolkit...")

        cwd = os.getcwd()
        # Converter step for SMASH output
        if "SMASH" in self.full_config.general.modules:
            try:
                os.chdir(afterburner_toolkit_dir)
                subprocess.run(
                    [
                        f"./{afterburner_toolkit_converter}",
                        self.config.input_filename,
                    ],
                    check=True,
                )
                # Create results directory in current directory if not exists
                results_dir = os.path.join(afterburner_toolkit_dir, "results")
                if not os.path.exists(results_dir):
                    os.makedirs(results_dir)
                # Move the converted file (self.config.input_filename -.dat + .gz) to results directory and rename it particle_list.dat
                converted_file = self.config.input_filename.replace(
                    ".dat", ".gz"
                )
                if os.path.exists(converted_file):
                    shutil.move(
                        converted_file,
                        os.path.join(results_dir, "particle_list.dat"),
                    )
                    logging.info(
                        f"[afterburner_toolkit] Moved converted file to {os.path.join(results_dir, 'particle_list.dat')}"
                    )
                else:
                    logging.error(
                        f"[afterburner_toolkit] Converted file {converted_file} does not exist."
                    )
            except subprocess.CalledProcessError as e:
                logging.error(
                    f"[afterburner_toolkit] Converter execution failed: {e}"
                )
            finally:
                os.chdir(cwd)
        else:
            # If there is no SMASH, then we assume that the input file is already in the correct format and just move it to results/particle_list.dat
            results_dir = os.path.join(afterburner_toolkit_dir, "results")
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
            src_file = os.path.join(
                afterburner_toolkit_dir, self.config.input_filename
            )
            dst_file = os.path.join(results_dir, "particle_list.bin")
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                logging.info(
                    f"[afterburner_toolkit] Copied input file to {dst_file}"
                )
            else:
                logging.error(
                    f"[afterburner_toolkit] Input file {src_file} does not exist."
                )

        # Run the actual afterburner_toolkit
        try:
            os.chdir(afterburner_toolkit_dir)
            subprocess.run([f"./{afterburner_toolkit_exe}"], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"[afterburner_toolkit] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[afterburner_toolkit] Execution finished.")

    def fetch_output(self, event_dir):
        logging.info("[afterburner_toolkit] Data successfully processed...")
        afterburner_toolkit_dir = os.path.join(event_dir, "afterburner_toolkit")
        results_dir = os.path.join(afterburner_toolkit_dir, "results")
        if "SMASH" in self.full_config.general.modules:
            particle_list_file = os.path.join(results_dir, "particle_list.dat")
        else:
            particle_list_file = os.path.join(results_dir, "particle_list.bin")
        if os.path.exists(particle_list_file):
            os.remove(particle_list_file)
            logging.info(f"[afterburner_toolkit] Removed {particle_list_file}")
        else:
            logging.warning(
                f"[afterburner_toolkit] {particle_list_file} does not exist."
            )
        dst_dir = os.path.join(
            event_dir, "results", f"spvn_results_{self.event_id}"
        )
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for item in os.listdir(results_dir):
            s = os.path.join(results_dir, item)
            d = os.path.join(dst_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, False, None)
            else:
                shutil.copy2(s, d)
        shutil.rmtree(afterburner_toolkit_dir)
        logging.info(f"[afterburner_toolkit] Moved results to {dst_dir}")
