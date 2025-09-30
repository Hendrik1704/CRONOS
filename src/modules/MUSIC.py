from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil
import glob


class MUSIC(BaseModule):
    def prepare_environment(self, event_dir):
        logging.info(f"[MUSIC] Preparing environment in {event_dir}...")
        music_eos_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "EOS"
        )
        if os.path.exists(music_eos_path):
            os.symlink(music_eos_path, os.path.join(event_dir, "MUSIC", "EOS"))
        else:
            logging.error(
                f"[MUSIC] Required directory {music_eos_path} does not exist."
            )

        music_tables_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "tables"
        )
        if os.path.exists(music_tables_path):
            os.symlink(
                music_tables_path, os.path.join(event_dir, "MUSIC", "tables")
            )
        else:
            logging.error(
                f"[MUSIC] Required directory {music_tables_path} does not exist."
            )
            exit(1)

        music_exe_path = os.path.join(
            self.project_root, "external_codes", "MUSIC", "MUSIChydro"
        )
        if os.path.exists(music_exe_path):
            os.symlink(
                music_exe_path, os.path.join(event_dir, "MUSIC", "MUSIChydro")
            )
        else:
            logging.error(
                f"[MUSIC] Required executable {music_exe_path} does not exist."
            )
            exit(1)

    def prepare_input(self, event_dir):
        logging.info(f"[MUSIC] Create input file...")
        current_module_index = self.full_config.general.modules.index("MUSIC")
        self.config.Initial_Distribution_input_filename = (
            f"output_{current_module_index-1}.dat"
        )

        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        if not os.path.exists(MUSIC_dir):
            logging.error(
                f"[MUSIC] Required directory {MUSIC_dir} does not exist."
            )
            exit(1)
        ini_file = os.path.join(MUSIC_dir, "parameters_MUSIC.ini")

        with open(ini_file, "w") as f:
            f.write(f"echo_level {self.config.echo_level}\n")
            f.write(f"mode {self.config.mode}\n")
            f.write(f"beastMode {self.config.beastMode}\n")
            f.write(f"Initial_profile {self.config.Initial_profile}\n")
            f.write(
                f"initialize_with_entropy {self.config.initialize_with_entropy}\n"
            )
            f.write(
                f"Initial_Distribution_input_filename {self.config.Initial_Distribution_input_filename}\n"
            )
            f.write(f"s_factor {self.config.s_factor}\n")
            f.write(f"preEqVisFactor {self.config.preEqVisFactor}\n")
            f.write(f"boost_invariant {self.config.boost_invariant}\n")
            f.write(f"Initial_time_tau_0 {self.config.Initial_time_tau_0}\n")
            f.write(
                f"Total_evolution_time_tau {self.config.Total_evolution_time_tau}\n"
            )
            f.write(f"Delta_Tau {self.config.Delta_Tau}\n")
            f.write(f"Eta_grid_size {self.config.Eta_grid_size}\n")
            f.write(f"Grid_size_in_eta {self.config.Grid_size_in_eta}\n")
            f.write(f"X_grid_size_in_fm {self.config.X_grid_size_in_fm}\n")
            f.write(f"Y_grid_size_in_fm {self.config.Y_grid_size_in_fm}\n")
            f.write(f"Grid_size_in_x {self.config.Grid_size_in_x}\n")
            f.write(f"Grid_size_in_y {self.config.Grid_size_in_y}\n")
            f.write(f"gridPadding {self.config.gridPadding}\n")
            f.write(f"EOS_to_use {self.config.EOS_to_use}\n")
            f.write(
                f"quest_revert_strength {self.config.quest_revert_strength}\n"
            )
            f.write(
                f"FlagResumTransportCoeff {self.config.FlagResumTransportCoeff}\n"
            )
            f.write(f"FlagResetCausality {self.config.FlagResetCausality}\n")
            f.write(
                f"resumTransCoeffAlpha {self.config.resumTransCoeffAlpha}\n"
            )
            f.write(
                f"Viscosity_Flag_Yes_1_No_0 {self.config.Viscosity_Flag_Yes_1_No_0}\n"
            )
            f.write(
                f"Include_Shear_Visc_Yes_1_No_0 {self.config.Include_Shear_Visc_Yes_1_No_0}\n"
            )
            f.write(f"Shear_to_S_ratio {self.config.Shear_to_S_ratio}\n")
            f.write(
                f"T_dependent_Shear_to_S_ratio {self.config.T_dependent_Shear_to_S_ratio}\n"
            )
            f.write(
                f"Include_Bulk_Visc_Yes_1_No_0 {self.config.Include_Bulk_Visc_Yes_1_No_0}\n"
            )
            f.write(
                f"T_dependent_zeta_over_s {self.config.T_dependent_zeta_over_s}\n"
            )
            f.write(
                f"Include_second_order_terms {self.config.Include_second_order_terms}\n"
            )
            f.write(
                f"Include_vorticity_terms {self.config.Include_vorticity_terms}\n"
            )
            f.write(
                f"Include_Rhob_Yes_1_No_0 {self.config.Include_Rhob_Yes_1_No_0}\n"
            )
            f.write(
                f"turn_on_baryon_diffusion {self.config.turn_on_baryon_diffusion}\n"
            )
            f.write(f"kappa_coefficient {self.config.kappa_coefficient}\n")
            f.write(
                f"output_hydro_debug_info {self.config.output_hydro_debug_info}\n"
            )
            f.write(
                f"output_evolution_data {self.config.output_evolution_data}\n"
            )
            f.write(f"output_movie_flag {self.config.output_movie_flag}\n")
            f.write(
                f"output_evolution_T_cut {self.config.output_evolution_T_cut}\n"
            )
            f.write(
                f"output_evolution_e_cut {self.config.output_evolution_e_cut}\n"
            )
            f.write(
                f"output_evolution_ideal_only {self.config.output_evolution_ideal_only}\n"
            )
            f.write(
                f"outputBinaryEvolution {self.config.outputBinaryEvolution}\n"
            )
            f.write(
                f"output_evolution_every_N_eta {self.config.output_evolution_every_N_eta}\n"
            )
            f.write(
                f"output_evolution_every_N_y {self.config.output_evolution_every_N_y}\n"
            )
            f.write(
                f"output_evolution_every_N_x {self.config.output_evolution_every_N_x}\n"
            )
            f.write(
                f"output_evolution_every_N_timesteps {self.config.output_evolution_every_N_timesteps}\n"
            )
            f.write(
                f"Do_FreezeOut_Yes_1_No_0 {self.config.Do_FreezeOut_Yes_1_No_0}\n"
            )
            f.write(
                f"Do_FreezeOut_lowtemp {self.config.Do_FreezeOut_lowtemp}\n"
            )
            f.write(
                f"freeze_out_tau_start_max {self.config.freeze_out_tau_start_max}\n"
            )
            f.write(f"freeze_out_method {self.config.freeze_out_method}\n")
            f.write(
                f"freeze_surface_in_binary {self.config.freeze_surface_in_binary}\n"
            )
            f.write(
                f"average_surface_over_this_many_time_steps {self.config.average_surface_over_this_many_time_steps}\n"
            )
            f.write(f"freeze_Ncell_x_step {self.config.freeze_Ncell_x_step}\n")
            f.write(f"freeze_Ncell_y_step {self.config.freeze_Ncell_y_step}\n")
            f.write(
                f"freeze_Ncell_eta_step {self.config.freeze_Ncell_eta_step}\n"
            )
            f.write(f"freeze_eps_flag {self.config.freeze_eps_flag}\n")
            f.write(f"N_freeze_out {self.config.N_freeze_out}\n")
            f.write(
                f"use_eps_for_freeze_out {self.config.use_eps_for_freeze_out}\n"
            )
            f.write(f"T_freeze {self.config.T_freeze}\n")
            f.write(f"N_freeze_out {self.config.N_freeze_out}\n")
            f.write(f"eps_switch {self.config.eps_switch}\n")
            f.write(f"eps_freeze_max {self.config.eps_freeze_max}\n")
            f.write(f"eps_freeze_min {self.config.eps_freeze_min}\n")
            f.write(f"freeze_eps_flag {self.config.freeze_eps_flag}\n")
            f.write(f"EndOfData\n")

        logging.info("[MUSIC] Input file created successfully.")

        input_Tmunu_file = os.path.join(
            event_dir,
            "results",
            self.config.Initial_Distribution_input_filename,
        )
        input_Tmunu_file = os.path.abspath(
            input_Tmunu_file
        )  # resolve relative path
        symlink_path = os.path.join(
            MUSIC_dir, self.config.Initial_Distribution_input_filename
        )

        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)

        os.symlink(input_Tmunu_file, symlink_path)
        logging.debug(f"Created symlink: {symlink_path} -> {input_Tmunu_file}")

        # Copy the music input parameter file to the results directory, iSS needs it
        music_input_param_file = os.path.join(MUSIC_dir, "parameters_MUSIC.ini")
        music_input_param_file = os.path.abspath(music_input_param_file)
        results_path = os.path.join(event_dir, "results")
        shutil.copy(music_input_param_file, results_path)

    @time_execution
    def run(self, event_dir):
        logging.info("[MUSIC] run...")
        MUSIC_dir = os.path.join(event_dir, "MUSIC")
        MUSIC_exe = "MUSIChydro"
        ini_file = "parameters_MUSIC.ini"

        logging.info("[MUSIC] Running MUSIC...")

        cwd = os.getcwd()
        try:
            os.chdir(MUSIC_dir)

            kwargs = {"check": True}
            if not self.full_config.general.module_terminal_output:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
                logging.debug("[MUSIC] Running with suppressed output...")
            run_external_command(
                [f"./{MUSIC_exe}", ini_file],
                memory_threshold_mb=self.full_config.general.memory_threshold_mb,
                module_name="MUSIC",
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"[MUSIC] Execution failed: {e}")
        finally:
            os.chdir(cwd)

        logging.info("[MUSIC] Execution finished.")

    def fetch_output(self, event_dir):
        logging.info("[MUSIC] Data successfully processed...")
        current_module_index = self.full_config.general.modules.index("MUSIC")
        src_pattern = os.path.join(event_dir, "MUSIC", "surface_*.dat")
        matching_files = glob.glob(src_pattern)

        if not matching_files:
            logging.error(f"[MUSIC] No files found matching {src_pattern}")
            return
        if len(matching_files) > 1:
            logging.warning(
                f"[MUSIC] Multiple files found matching {src_pattern}, using the first one."
            )

        src_file = matching_files[0]
        dst_file = os.path.join(
            event_dir, "results", f"output_{current_module_index}.dat"
        )
        shutil.move(src_file, dst_file)
        shutil.rmtree(os.path.join(event_dir, "MUSIC"))
        logging.info(f"[MUSIC] Moved {src_file} to {dst_file}")
