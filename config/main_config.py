# This file contains the general settings for the application.
# It can be overridden by user-specific config files.

general ={
    # Logging level for the application
    # Possible choices:
    #   "INFO"  - Show key runtime messages
    #   "DEBUG" - Show all debug messages (verbose)
    #   "NONE"  - Suppress all log output
    "log_level": "INFO",
    "module_terminal_output": True,  # If True, show terminal output of each module
                                      # If False, suppress terminal output of each module

    # List of modules to connect/load.
    # Possible modules: from_file_IC, KoMPoST, entropy_matching, MUSIC, iSS, SMASH, afterburner_toolkit
    "modules": [],

    "number_of_jobs": 1,
    "number_events_per_job": 1,

    # Keep intermediate results
    "keep_intermediate_results": False,
    "keep_particle_files": False, # If the afterburner_toolkit module is used, keep the particle files from iSS or the afterburner
}

from_file_IC = {
    "input_path": "data/",
}

KoMPoST = {
    "tIn": 0.2,
    "tOut": 0.8,
    "EtaOverS": 0.16,  # specific shear viscosity
    "EtaOverSTemperatureScale": 0.0,
    "NuEffective": 40.0,
    "EVOLUTION_MODE": 1,  # 0 for free-streaming, 1: for "KoMPoST" EKT evolution
    "ENERGY_PERTURBATIONS": 1,
    "MOMENTUM_PERTURBATIONS": 0,
    "DECOMPOSITION_METHOD": 1,
    "Regulator": "TwoPass",
    "normFactor": 1.0,  # scaling of the input Tmunu
    "afm": 0.1,  # lattice spacing in fm
    "Ns": 512,  # number of grid points on a square lattice
    "xSTART": 0,  # The first grid point to include in the x direction
    "xEND": 511,  # The last grid point to include in the x direction
    "ySTART": 0,  # The first grid point to include in the y direction
    "yEND": 511,  # The last grid point to include in the y direction
}

entropy_matching = {
    "nu_eff": 40.0,  # effective degrees of freedom, should match with KoMPoST
}

MUSIC = {
    "echo_level": 1,  # controls the amount of messages in the terminal
    "mode": 2,  # this mode is evolution only
    "beastMode": 1,  # 0: no beast mode, 1: float precision, 2: float precision, increased time step after 4 fm
    "Initial_profile": 94,  # Read in initial profile from a file
                            # 9: IPGlasma (full Tmunu),
                            #   -- 91: e and u^\mu,
                            #   -- 92: e only,
                            #   -- 93: e, u^\mu, and pi^\munu,
                            #   -- 94: full T^\mu\nu and read bulk
    "initialize_with_entropy": 0,  # 0: with energy density
    "s_factor": 1.0,  # normalization factor for initial profile
    "preEqVisFactor": 1.0,  # additional scale factor for initial viscous tensor
    "boost_invariant": 1,  # 0: no boost invariance, 1: boost invariance
    "Initial_time_tau_0": 0.4,  # starting time of the hydrodynamic evolution (fm/c)
    "Total_evolution_time_tau": 50.0,  # the maximum allowed running evolution time (fm/c)
    "Delta_Tau": 0.005,  # time step to use in the evolution [fm/c]
    "Eta_grid_size": 14.0,  # spatial rapidity range
    "Grid_size_in_eta": 1,  # number of the grid points in spatial rapidity direction
    "X_grid_size_in_fm": 20.0,  # spatial range along x direction
    "Y_grid_size_in_fm": 20.0,  # spatial range along y direction
    "Grid_size_in_y": 200,  # number of the grid points in y direction
    "Grid_size_in_x": 200,  # number of the grid points in x direction
    "gridPadding": 3,  # grid padding size in the transverse plane (fm)
    "EOS_to_use": 91,  # type of the equation of state
                       # 0: ideal gas
                       # 1: EOS-Q from azhydro
                       # 2: lattice EOS s95p-v1
                       #    (from Huovinen and Petreczky)
                       # 3: lattice EOS s95p with partial
                       #    chemical equilibrium (PCE) at 150 MeV
                       #    (see https://wiki.bnl.gov/TECHQM
                       #         /index.php/QCD_Equation_of_State)
                       # 4: lattice EOS s95p PCE at 155 MeV
                       # 5: lattice EOS s95p PCE at 160 MeV
                       # 6: lattice EOS s95p PCE at 165 MeV
                       # 7: lattice EOS s95p-v1.2 for UrQMD
                       # 9: lattice EOS hotQCD with UrQMD
                       # 91: lattice EOS hotQCD with SMASH
                       # 14: lattice EOS hotQCD at finite muB
    # transport coefficients
    "quest_revert_strength": 10.0,
    "FlagResumTransportCoeff": 0,  # switch to use resummed transport coeff.
    "FlagResetCausality": 0,
    "resumTransCoeffAlpha": 1.5,  # resummed transport coeff. control parameter
    "Viscosity_Flag_Yes_1_No_0": 1,  # turn on viscosity in the evolution
    "Include_Shear_Visc_Yes_1_No_0": 1,  # include shear viscous effect
    "Shear_to_S_ratio": 0.16,  # value of \eta/s
    "T_dependent_Shear_to_S_ratio": 0,  # flag to use temperature dep. \eta/s(T)
    "muB_dependent_Shear_to_S_ratio": 0,  # flag to use temperature dep. \eta/s(T, muB)
    "shear_muBf0p2": 1.,  # piece-wise eta/s(muB) for muB_dependent_Shear_to_S_ratio == 7
    "shear_muBf0p4": 1.,  # piece-wise eta/s(muB) for muB_dependent_Shear_to_S_ratio == 7
    "Include_Bulk_Visc_Yes_1_No_0": 0,  # include bulk viscous effect
    "T_dependent_zeta_over_s": 7,  # parameterization of \zeta/s(T)
    "Include_second_order_terms": 1,  # include second order non-linear coupling terms
    "Include_vorticity_terms": 0,  # include vorticity coupling terms
    "Include_Rhob_Yes_1_No_0": 0,
    "turn_on_baryon_diffusion": 0,
    "kappa_coefficient": 0.0,
    
    # evolution output parameters
    "output_hydro_debug_info": 0,  # flag to output debug information
    "output_evolution_data": 0,  # flag to output evolution history to file
    "output_movie_flag": 0,
    "output_evolution_T_cut": 0.145,
    "output_evolution_e_cut": 0.15,
    "output_evolution_ideal_only": 0,
    "outputBinaryEvolution": 1,  # output evolution file in binary format
    "output_evolution_every_N_eta": 1,  # output evolution file every Neta steps
    "output_evolution_every_N_y": 1,    # output evolution file every Ny steps
    "output_evolution_every_N_x": 1,    # output evolution file every Nx steps
    "output_evolution_every_N_timesteps": 10,  # output evolution every Ntime steps

    # parameters for freeze out and Cooper-Frye
    "Do_FreezeOut_Yes_1_No_0": 1,  # flag to find freeze-out surface
    "Do_FreezeOut_lowtemp": 1,  # flag to include cold corona
    "freeze_out_tau_start_max": 2,  # the maximum freeze-out starting time [fm/c]
    "freeze_out_method": 4,  # method for hyper-surface finder, 4 Cornelius
    "freeze_surface_in_binary": 1,  # switch to output surface file in binary format
    "average_surface_over_this_many_time_steps": 10,  # the step skipped in the tau
    "freeze_Ncell_x_step": 1,
    "freeze_Ncell_y_step": 1,
    "freeze_Ncell_eta_step": 1,
    "freeze_eps_flag": 0,
    "N_freeze_out": 1,
    "use_eps_for_freeze_out": 0,  # flag to use energy density as criteria to
                                    # find freeze-out surface
                                    # 0: use temperature, 1: use energy density
    "T_freeze": 0.155,  # freeze out temperature
    "N_freeze_out": 1,
    "eps_switch": 0.18,
    "eps_freeze_max": 0.18,
    "eps_freeze_min": 0.18,
    "freeze_eps_flag": 0,  #0: use eps_freeze_max and eps_freeze_min
                           #1: read eps_freeze from an external file
}

iSS = {
    "hydro_mode": 2,  # mode for reading in freeze out information
    "afterburner_type": 2,  # 0: PDG_Decay, 1: UrQMD, 2: SMASH
    "turn_on_bulk": 0,  # read in bulk viscous pressure
    "turn_on_rhob": 0,  # read in net baryon chemical potential
    "turn_on_diff": 0,  # read in baryon diffusion current
    "regulateEOS": 1,  # flag to regulate T and mu with pure HRG EOS
    "include_deltaf_shear": 1,  # include delta f contribution from shear
    "include_deltaf_bulk": 1,  # include delta f contribution from bulk
    "include_deltaf_diffusion": 0,  # include delta f contribution from diffusion
    "bulk_deltaf_kind": 1,  # 0: 14-momentum approximation, 1: relaxation time approximation
    "restrict_deltaf": 0,  # flag to apply restriction on the size of delta f
    "deltaf_max_ratio": 1.0,  # the maximum allowed size of delta f w.r.t f0
    "quantum_statistics": 1,  # include quantum statistics (1: yes, 0: no)
    "calculate_polarization": 0,  # switch to compute Lambda's polarization
    "polarizationRapType": 1,  # 0: rapidity; 1: pseudorapidity; 2: both
    "randomSeed": 0,  # If <0, use system clock.
    "calculate_vn": 0,  # 1/0: whether to calculate the
    "MC_sampling": 4,  # 0/1/2/3: whether to perform Monte-Carlo sampling
    # (not required for spectra calculation).
    # 0: No sampling.
    # 1: use dN_dxtdetady to sample.
    # 2: use dN_dxtdy to sample.
    # 3: use dN_pTdpTdphidy to sample
    #    (overwrites calculate_vn to be 1).
    "sample_upto_desired_particle_number": 0,  # 1: flag to run sampling until desired
                                               # particle numbers is reached
    "number_of_repeated_sampling": 10,  # number of repeated sampling
    "number_of_particles_needed": 100000,  # number of hadrons to sample
    "maximum_sampling_events": 10000,
    "sample_y_minus_eta_s_range": 4,  # y_minus_eta_s will be sampled
    "sample_pT_up_to": -1,  # Up to this value will pT be sampled; 
    # if<0 then use the largest value in the pT table.
    "dN_dy_sampling_model": 30,  # 30: Use Poisson distribution to sample the 
    #      whole dN_dy.
    "dN_dy_sampling_para1": 0.16,  # Additional parameters for dN/dy sampling. 
    # -- For dN_dy_sampling_model==10 or 20,
    "perform_decays": 0,  # flag to perform resonance decay
    "perform_checks": 0,  # flag to perform tests for the sampler
    "include_spectators": 0,  # flag to include spectators
    "local_charge_conservation": 0,  # flag to impose local charge conservation
    "global_momentum_conservation": 0,  # flag to impose GMC
    "y_LB": -5.0,  # lower bound for y-sampling;
    "y_RB": 5.0,  # upper bound for y-sampling;
    "output_samples_into_files": 0,  # output particle samples into individual files
    "store_samples_in_memory": 1,  # flag to store particle samples in memory
    "use_OSCAR_format": 1,  # output results in OSCAR format
    "use_gzip_format": 0,  # output results in gzip format (only works with
    # store_samples_in_memory = 1)
    "use_binary_format": 0,
    "calculate_vn_to_order": 9,  # v_n's are calculated up to this order
    "use_pos_dN_only": 0,  # 1: all negative emission functions will be skipped.
    "grouping_particles": 1,  # 0/1: Particles will be re-order according to
    # their mass. This parameter combined with
    # grouping_tolerance parameter can make particles
    # with similar mass and chemical potentials to be
    # sampled together.
    "grouping_tolerance": 0.01,  # If two particles adjacent in the table have
    # mass and chemical potentials close within this
    # relative tolerance, they are considered to be
    # identical and will be sampled successively
    # without regenerating the dN / (dxt deta dy)
    # matrix for efficiency.
    "minimum_emission_function_val": 1e-30,  # If dN/(dx_t deta dy) is evaluated to
    # be smaller than this value, then it
    # is replaced by this value.
    "use_historic_flow_output_format": 0,
    "eta_s_LB": -0.5,  # lower bound for eta_s sampling; used only when
    # sampling using total energy flux
    "eta_s_RB": 0.5,  # upper bound for eta_s sampling.
    "use_dynamic_maximum": 0,  # 0/1: Whether to automatically reduce the
    # guessed maximum after some calculations.
    # Work only when MC_sampling is set to 2.
    "adjust_maximum_after": 100000,  # Used only when use_dynamic_maximum=1.
    # After the number of sampling given by
    # this parameter the guessed maximum is
    # adjusted.
    "adjust_maximum_to": 1.2,  # [1,inf]: When guessed maximum is adjusted,
    # it is adjusted to the "observed maximum"
    # multiplied by this value. Note that the
    # "observed maximum" is measured relative to
    # the guessed maximum. See code for details.
    "calculate_dN_dtau": 0,  # Output dN_dtau table. Only applicable
    # if MC_sampling parameter is set to 1.
    "bin_tau0": 0.6,  # used to generate bins for
    # calculate_dN_dtau_using_dN_dxtdeta function
    "bin_dtau": 0.2,  # used to generate bins for
    # calculate_dN_dtau_using_dN_dxtdeta function
    "bin_tau_max": 17.0,  # used to generate bins for
    # calculate_dN_dtau_using_dN_dxtdeta function
    "calculate_dN_dx": 0,  # Output dN_dx table. Only applicable
    # if MC_sampling parameter is set to 1.
    "bin_x_min": -10.0,  # used to generate bins for
    # calculate_dN_dx_using_dN_dxtdeta function
    "bin_dx": 0.5,  # used to generate bins
    # for calculate_dN_dx_using_dN_dxtdeta function
    "bin_x_max": 10.0,  # used to generate bins for
    # calculate_dN_dx_using_dN_dxtdeta function
    "calculate_dN_dphi": 0,  # Output dN_dphi table. Only applicable
    # if calculate_vn parameter is set to 1.
    "calculate_dN_deta": 1,  # Output dN_deta table. Only applicable
    # if MC_sampling parameter is set to 1.
    "calculate_dN_dxt": 1,  # Output dN_dxt table. Only applicable
    # if MC_sampling parameter is set to 1.
    "output_dN_dxtdy_4all": 0,  # Output dN_dxtdy table. Only applicable
    # if MC_sampling parameter is set to 2.
}

SMASH = {
    "Delta_Time": 0.1,
    "End_Time": 2000.0,
    "Randomseed": 1,
    "No_Collisions": 0, # 1: disable collisions, decays only
}

afterburner_toolkit = {
    'echo_level': 9,  # control the amount of print messages
    'read_in_mode': 7,  # mode for reading in particle information
                        # 0: reads outputs from OSCAR outputs
                        # 1: reads outputs from UrQMD outputs
                        # 2: reads outputs from zipped UrQMD outputs
                        # 21: reads outputs from binary UrQMD outputs
                        # 3: reads outputs from Sangwook's UrQMD outputs 
                        #    (without header lines)
                        # 4: reads outputs from UrQMD 3.3p2 outputs
                        # 7: reads outputs from gzipped SMASH outputs
                        # 8: read outputs from SMASH binary format
                        # 9: reads outputs from binary outputs (iSS)
                        # 10: reads outputs from gzip outputs (iSS)
    'ecoOutput': 1,  # 1: only save Qn without errors
    'analyze_flow': 1,  # 0/1: flag to perform flow analysis
    'analyze_HBT': 0,  # 0/1: flag to perform HBT analysis
    'analyze_balance_function': 0,  # 0/1: flag to analyze Balance function
    'analyze_ebe_yield': 0,  # 0/1: flag to analyze ebe dis. of particle yield
    
    'read_in_real_mixed_events': 0,  # 0/1: read in real mixed events
    'randomSeed': -1,
    'particle_monval': 211,  # particle Monte-Carlo number
    'distinguish_isospin': 1,  # flag whether to distinguish the isospin of particles
    'event_buffer_size': 100000,  # the number of events read in at once
    'resonance_weak_feed_down_flag': 0,  # include weak feed down contribution
    'resonance_feed_down_flag': 0,  # perform resonance feed down
                                    # (will read in all hadrons and filter particle
                                    #  after decays are performed)
    'select_resonances_flag': 0,  # perform resonance decays only for selected particle species
    'resonance_weak_feed_down_Sigma_to_Lambda_flag': 0,  # include weak feed down contribution
                                                         # turn on only for Lambda (monval=3122)
                                                         # for Sigma^0 -> Lambda + gamma
    'net_particle_flag': 0,  # flag to collect net particle yield distribution
    'collect_neutral_particles': 0,  # flag to collect neutral particles
    # Parameters for single particle spectra and vn
    'rapidity_shift': 0.,
    'readRapidityShiftFromFile': 0,
    'order_max': 10,  # the maximum harmonic order (= order_max - 1 ) of anisotropic flow
                      # for charged hadron; order_max = 6 for identified particles
    'compute_correlation': 0,  # flag to compute correlation function
    'flag_charge_dependence': 0,  # flag to compute charge dependence correlation
    'compute_corr_rap_dep': 0,  # flag to compute the rapidity dependent multi-particle correlation
    'npT': 41,  # number of pT points for pT-differential spectra and vn
    'pT_min': 0.05,  # the minimum value of transverse momentum (GeV)
    'pT_max': 4.05,  # the maximum value of transverse momentum (GeV)
    'rap_min': -0.5,  # minimum value of rapidity integration range for mid-rapidity observables
    'rap_max': 0.5,  # maximum value of rapidity integration range for mid-rapidity observables
    'rap_type': 1,  # 0: for pseudo-rapidity; 1: for rapidity
    'rapidity_distribution': 1,  # 1: output particle rapidity distribution 
    'n_rap': 141,  # number of points in rapidity distr.
    'rapidity_dis_min': -7.0,  # minimum value of particle rapidity distribution
    'rapidity_dis_max': 7.0,  # maximum value of particle rapidity distribution
    'vn_rapidity_dis_pT_min': 0.20,  # the minimum value of pT for vn rap. distr.
    'vn_rapidity_dis_pT_max': 3.0,  # the maximum value of pT for vn rap. distr.
    'rapidityPTDistributionFlag': 0,  # output Qn vectors in (eta, pT)
    'pidwithRapidityPTDistribution': 0,
    'pidwithPseudoRapCuts': 0,  # Analyze pid particles Qn vectors with
                                # pseudo-rapidity cuts in additional to the
                                # default rapidity cuts
    'check_spatial_dis': 0,  # flag to check dN/dtau distribution
    'intrinsic_detas': 0.1,  # deta_s in the output samples
    'intrinsic_dtau': 0.01,  # dtau in the output samples
    'intrinsic_dx': 0.1,  # dx in the output samples
    # Parameters for HBT correlation functions
    'long_comoving_boost': 1,  # whether qlong will be boost by the pair velocity
    'needed_number_of_pairs': 30000000,  # number of pairs for each K point
    'number_of_oversample_events': 100,  # number of the combined events in the numerator
    'number_of_mixed_events': 50,  # number of the mixed events in the denominator
    'invariant_radius_flag': 0,  # 0: compute 3D HBT correlation function
                                 # 1: compute 1D HBT correlation function for q_inv
    'azimuthal_flag': 0,  # 0: compute the azimuthal averaged HBT correlation function
                          # 1: compute azimuthal dependent HBT correlation function
    'kT_differenitial_flag': 1,  # 0: integrate the pair momentum k_T over  a given kT range for correlation function
                                 # 1: compute the correlation function at each specific kT point
    'n_KT': 5,  # number of the pair momentum k_T to calculate
    'KT_min': 0.15,  # minimum value of the pair momentum k_T 
    'KT_max': 0.55,  # maximum value of the pair momentum k_T 
    'n_Kphi': 48,  # number of the azimuthal angles for the pair momentum k_T
                   # (range is assumed to be from 0 to 2*pi)
    'HBTrap_min': -0.5,  # minimum accept rapidity for particle pair
    'HBTrap_max': 0.5,  # maximum accept rapidity for particle pair
    'qnpts': 31,  # number of points for momentum q (difference of the pair momentum) for correlation function
    'q_min': -0.15,  # minimum value for momentum q (GeV)
    'q_max': 0.15,  # maximum value for momentum q (GeV)
    'reject_decay_flag': 0,  # reject particles from resonance decays
                             # 0: no rejection
                             # 1: reject particles from all decay channels
                             # 2: reject particles only from long lived resonance decays (future)
    'tau_reject': 10.,  # reject decay particle whose tau_f > tau_reject
                        # only effective when reject_decay_flag == 2
                        # options for calculating Balance function
    'particle_alpha': 9998,  # monte carlo number for particle alpha
    'particle_beta': -9998,  # monte carlo number for particle beta
    'Bnpts': 21,  # number of bins for the balance function
    'Brap_max': 2.0,  # the maximum \Delta y rapidity for balance function
    'BpT_min': 0.2,  # the minimum pT cut for particles used in balance function
    'BpT_max': 3.0,  # the maximum pT cut for particles used in balance function
}