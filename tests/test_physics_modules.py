import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from src.configuration import Configuration
from src.modules.from_file_IC import FromFileIC
from src.modules.KoMPoST import KoMPoST
from src.modules.MUSIC import MUSIC
from src.modules.SMASH import SMASH
from src.modules.iSS import iSS
from src.modules.entropy_matching import EntropyMatching
from src.modules.afterburner_toolkit import afterburner_toolkit


class TestPhysicsModuleBase:
    """Base test class for physics modules."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_root)
        
        # Create basic directory structure
        os.makedirs(os.path.join(self.project_root, "external_codes"))
        os.makedirs(os.path.join(self.project_root, "utilities"))
        
        self.event_dir = os.path.join(self.temp_dir, "event_0")
        os.makedirs(self.event_dir)
        os.makedirs(os.path.join(self.event_dir, "results"))
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)


class TestFromFileIC(TestPhysicsModuleBase):
    """Test FromFileIC module functionality."""
    
    def test_from_file_ic_initialization(self):
        """Test FromFileIC module initialization."""
        config = Configuration({
            "data_directory": "/path/to/initial_conditions",
            "filename_pattern": "ic_{event_id}.dat"
        })
        full_config = Configuration({
            "general": {"modules": ["from_file_IC", "KoMPoST"]}
        })
        
        module = FromFileIC(config, full_config, self.project_root, "event_0")
        
        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == self.project_root
        assert module.event_id == "event_0"
    
    def test_prepare_environment(self):
        """Test prepare_environment method."""
        config = Configuration({"data_directory": "/test"})
        full_config = Configuration({"general": {"modules": ["from_file_IC"]}})
        
        module = FromFileIC(config, full_config, self.project_root, "event_0")
        
        with patch('src.modules.from_file_IC.logging.info') as mock_logging:
            module.prepare_environment(self.event_dir)
            mock_logging.assert_called_once()
    
    def test_prepare_input_file_exists(self):
        """Test prepare_input when input file exists."""
        # Create mock input file
        data_dir = os.path.join(self.temp_dir, "input_data")
        os.makedirs(data_dir)
        input_file = os.path.join(data_dir, "ic_event_0.dat")
        with open(input_file, 'w') as f:
            f.write("test initial condition data")
        
        config = Configuration({
            "input_path": data_dir + "/"
        })
        full_config = Configuration({"general": {"modules": ["from_file_IC"]}})
        
        module = FromFileIC(config, full_config, self.project_root, "event_0")
        
        module.prepare_input(self.event_dir)
        
        # Should complete without error
        assert True
    
    def test_prepare_input_file_not_exists(self):
        """Test prepare_input when input file doesn't exist."""
        config = Configuration({
            "input_path": "/nonexistent/"
        })
        full_config = Configuration({"general": {"modules": ["from_file_IC"]}})
        
        module = FromFileIC(config, full_config, self.project_root, "event_0")
        
        # This should not raise an error as prepare_input just logs the path
        module.prepare_input(self.event_dir)
        assert True
    
    @patch('src.modules.from_file_IC.logging.info')
    def test_run_method(self, mock_logging):
        """Test run method."""
        config = Configuration({"data_directory": "/test"})
        full_config = Configuration({"general": {"modules": ["from_file_IC"]}})
        
        module = FromFileIC(config, full_config, self.project_root, "event_0")
        
        module.run(self.event_dir)
        mock_logging.assert_called()
    
    def test_fetch_output(self):
        """Test fetch_output method."""
        # Create test input file in module directory
        from_file_dir = os.path.join(self.event_dir, "from_file_IC")
        os.makedirs(from_file_dir)
        test_file = os.path.join(from_file_dir, "output_0.dat")
        with open(test_file, 'w') as f:
            f.write("test output")
        
        config = Configuration({"data_directory": "/test"})
        full_config = Configuration({"general": {"modules": ["from_file_IC"]}})
        
        module = FromFileIC(config, full_config, self.project_root, "event_0")
        
        module.fetch_output(self.event_dir)
        
        # Check file was moved to results
        result_file = os.path.join(self.event_dir, "results", "output_0.dat")
        assert os.path.exists(result_file)
        assert not os.path.exists(from_file_dir)  # Directory should be removed


class TestKoMPoST(TestPhysicsModuleBase):
    """Test KoMPoST module functionality."""
    
    def test_kompost_initialization(self):
        """Test KoMPoST module initialization."""
        config = Configuration({
            "shear_viscosity": 0.08,
            "tau0": 0.2,
            "tauf": 1.0,
            "dTau": 0.01
        })
        full_config = Configuration({
            "general": {"modules": ["KoMPoST", "MUSIC"]}
        })
        
        module = KoMPoST(config, full_config, self.project_root, "event_0")
        
        assert module.config.shear_viscosity == 0.08
        assert module.config.tau0 == 0.2
    
    def test_prepare_environment_executable_exists(self):
        """Test prepare_environment when KoMPoST executable exists."""
        # Create mock executable (KoMPoST.exe, not kompost.x)
        kompost_dir = os.path.join(self.project_root, "external_codes", "KoMPoST")
        os.makedirs(kompost_dir)
        executable = os.path.join(kompost_dir, "KoMPoST.exe")
        with open(executable, 'w') as f:
            f.write("#!/bin/bash\necho 'KoMPoST executable'")
        os.chmod(executable, 0o755)
        
        # Create mock EKT data directory (the actual expected name)
        ekt_dir = os.path.join(kompost_dir, "EKT")
        os.makedirs(ekt_dir)
        
        # Create event KoMPoST directory first
        event_kompost_dir = os.path.join(self.event_dir, "KoMPoST")
        os.makedirs(event_kompost_dir)
        
        config = Configuration({"shear_viscosity": 0.08})
        full_config = Configuration({"general": {"modules": ["KoMPoST"]}})
        
        module = KoMPoST(config, full_config, self.project_root, "event_0")
        
        module.prepare_environment(self.event_dir)
        
        # Check links were created (actual names from KoMPoST.py)
        linked_executable = os.path.join(self.event_dir, "KoMPoST", "KoMPoST.exe")
        linked_ekt = os.path.join(self.event_dir, "KoMPoST", "EKT")
        assert os.path.exists(linked_executable)
        assert os.path.exists(linked_ekt)
    
    def test_prepare_environment_executable_missing(self):
        """Test prepare_environment when KoMPoST executable is missing."""
        config = Configuration({"shear_viscosity": 0.08})
        full_config = Configuration({"general": {"modules": ["KoMPoST"]}})
        
        module = KoMPoST(config, full_config, self.project_root, "event_0")
        
        with pytest.raises(SystemExit):
            module.prepare_environment(self.event_dir)
    
    def test_prepare_input_creates_parameter_file(self):
        """Test prepare_input creates proper parameter file."""
        config = Configuration({
            "shear_viscosity": 0.08,
            "tau0": 0.2,
            "tauf": 1.0,
            "dTau": 0.01,
            "nx": 200,
            "ny": 200,
            "dx": 0.1,
            "dy": 0.1,
            # Required KoMPoST parameters
            "tIn": 0.2,
            "tOut": 1.0,
            "InputFile": "input.dat",
            "OutputFileTag": "output",
            "EtaOverS": 0.08,
            "EtaOverSTemperatureScale": 0.154,
            "NuEffective": 47.5,
            "EVOLUTION_MODE": 1,
            "ENERGY_PERTURBATIONS": 0,
            "MOMENTUM_PERTURBATIONS": 0,
            "DECOMPOSITION_METHOD": 1,
            "Regulator": 0.5,
            # EventInput parameters
            "normFactor": 1.0,
            "afm": 0.1,
            "Ns": 200,
            "xSTART": 0,
            "xEND": 199,
            "ySTART": 0,
            "yEND": 199
        })
        full_config = Configuration({"general": {"modules": ["from_file_IC", "KoMPoST"]}})
        
        # Create mock input file from previous module
        results_dir = os.path.join(self.event_dir, "results")
        input_file = os.path.join(results_dir, "output_0.dat")
        with open(input_file, 'w') as f:
            f.write("mock initial conditions")
        
        # Create KoMPoST directory that prepare_input expects
        kompost_event_dir = os.path.join(self.event_dir, "KoMPoST")
        os.makedirs(kompost_event_dir)
        
        module = KoMPoST(config, full_config, self.project_root, "event_0")
        
        module.prepare_input(self.event_dir)
        
        # Check parameter file was created
        param_file = os.path.join(self.event_dir, "KoMPoST", "parameters_KoMPoST.ini")
        assert os.path.exists(param_file)
        
        # Check parameter file content
        with open(param_file, 'r') as f:
            content = f.read()
            assert "0.08" in content  # shear viscosity
            assert "0.2" in content   # tau0
    
    @patch('src.modules.KoMPoST.run_external_command')
    def test_run_method(self, mock_run_command):
        """Test KoMPoST run method."""
        config = Configuration({"shear_viscosity": 0.08})
        full_config = Configuration({
            "general": {
                "modules": ["KoMPoST"],
                "memory_threshold_mb": 1000,
                "module_terminal_output": False
            }
        })
        
        module = KoMPoST(config, full_config, self.project_root, "event_0")
        
        # Create KoMPoST directory
        kompost_dir = os.path.join(self.event_dir, "KoMPoST")
        os.makedirs(kompost_dir)
        
        module.run(self.event_dir)
        
        # Verify external command was called
        # Verify the command was called correctly
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args[0]
        # KoMPoST uses KoMPoST.exe, not kompost.x
        assert "./KoMPoST.exe" in call_args[0] or "KoMPoST.exe" in str(call_args[0])


class TestMUSIC:
    """Test MUSIC relativistic hydrodynamics module."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.temp_dir, "project")
        self.event_dir = os.path.join(self.temp_dir, "event_0")
        os.makedirs(self.project_root)
        os.makedirs(self.event_dir)
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)
    
    def test_music_initialization(self):
        """Test MUSIC module initialization."""
        config = Configuration({"tau0": 0.6, "dt": 0.01})
        full_config = Configuration({"general": {"modules": ["MUSIC"]}})
        
        module = MUSIC(config, full_config, self.project_root, "event_0")
        
        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == self.project_root
        assert module.event_id == "event_0"
    
    def test_prepare_environment(self):
        """Test MUSIC environment preparation."""
        config = Configuration({"tau0": 0.6})
        full_config = Configuration({"general": {"modules": ["MUSIC"]}})
        
        module = MUSIC(config, full_config, self.project_root, "event_0")
        
        # Test should handle missing external directories gracefully by catching SystemExit
        with pytest.raises(SystemExit):
            module.prepare_environment(self.event_dir)
        
        # SystemExit occurs before directory creation, which is expected behavior
    
    def test_prepare_environment_with_executable(self):
        """Test MUSIC prepare_environment when executable and data exist."""
        # Create mock MUSIC structure
        music_external_dir = os.path.join(self.project_root, "external_codes", "MUSIC")
        os.makedirs(music_external_dir)
        
        # Create mock executable
        executable = os.path.join(music_external_dir, "MUSIChydro")
        with open(executable, 'w') as f:
            f.write("#!/bin/bash\necho 'MUSIC executable'")
        os.chmod(executable, 0o755)
        
        # Create mock data directories
        for dirname in ["EOS", "tables"]:
            os.makedirs(os.path.join(music_external_dir, dirname))
        
        config = Configuration({"tau0": 0.6})
        full_config = Configuration({"general": {"modules": ["MUSIC"]}})
        
        # Create event MUSIC directory first
        event_music_dir = os.path.join(self.event_dir, "MUSIC")
        os.makedirs(event_music_dir)
        
        module = MUSIC(config, full_config, self.project_root, "event_0")
        module.prepare_environment(self.event_dir)
        
        # Check links were created
        music_dir = os.path.join(self.event_dir, "MUSIC")
        assert os.path.exists(os.path.join(music_dir, "MUSIChydro"))
        assert os.path.exists(os.path.join(music_dir, "EOS"))
        assert os.path.exists(os.path.join(music_dir, "tables"))
    
    @patch('src.modules.MUSIC.run_external_command')
    def test_run_method(self, mock_run_command):
        """Test MUSIC run method."""
        config = Configuration({"tau0": 0.6})
        full_config = Configuration({
            "general": {
                "modules": ["MUSIC"],
                "module_terminal_output": False,
                "memory_threshold_mb": 1000
            }
        })
        
        # Create MUSIC directory
        music_dir = os.path.join(self.event_dir, "MUSIC")
        os.makedirs(music_dir)
        
        module = MUSIC(config, full_config, self.project_root, "event_0")
        module.run(self.event_dir)
        
        # Verify external command was called
        mock_run_command.assert_called_once()


class TestSMASH:
    """Test SMASH hadronic transport module."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.temp_dir, "project")
        self.event_dir = os.path.join(self.temp_dir, "event_0")
        os.makedirs(self.project_root)
        os.makedirs(self.event_dir)
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)
    
    def test_smash_initialization(self):
        """Test SMASH module initialization."""
        config = Configuration({"End_Time": 200.0, "Randomseed": 1})
        full_config = Configuration({"general": {"modules": ["SMASH"]}})
        
        module = SMASH(config, full_config, self.project_root, "event_0")
        
        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == self.project_root
        assert module.event_id == "event_0"
    
    def test_prepare_environment(self):
        """Test SMASH environment preparation."""
        config = Configuration({"End_Time": 200.0})
        full_config = Configuration({"general": {"modules": ["SMASH"]}})
        
        module = SMASH(config, full_config, self.project_root, "event_0")
        
        # Test should handle missing external directories gracefully by catching SystemExit
        with pytest.raises(SystemExit):
            module.prepare_environment(self.event_dir)
        
        # SystemExit occurs before directory creation, which is expected behavior
    
    @patch('src.modules.SMASH.run_external_command')
    def test_run_method(self, mock_run_command):
        """Test SMASH run method."""
        config = Configuration({"End_Time": 200.0})
        full_config = Configuration({
            "general": {
                "modules": ["SMASH"],
                "module_terminal_output": False,
                "memory_threshold_mb": 1000
            }
        })
        
        # Create SMASH directory
        smash_dir = os.path.join(self.event_dir, "SMASH")
        os.makedirs(smash_dir)
        
        module = SMASH(config, full_config, self.project_root, "event_0")
        module.run(self.event_dir)
        
        # Verify external command was called
        mock_run_command.assert_called_once()


class TestiSS:
    """Test iSS Cooper-Frye particlization module."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.temp_dir, "project")
        self.event_dir = os.path.join(self.temp_dir, "event_0")
        os.makedirs(self.project_root)
        os.makedirs(self.event_dir)
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)
    
    def test_iss_initialization(self):
        """Test iSS module initialization."""
        config = Configuration({"number_of_particles_needed": 100000})
        full_config = Configuration({"general": {"modules": ["iSS"]}})
        
        module = iSS(config, full_config, self.project_root, "event_0")
        
        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == self.project_root
        assert module.event_id == "event_0"
    
    def test_prepare_environment(self):
        """Test iSS environment preparation."""
        config = Configuration({"number_of_particles_needed": 100000})
        full_config = Configuration({"general": {"modules": ["iSS"]}})
        
        module = iSS(config, full_config, self.project_root, "event_0")
        
        # Test should handle missing external directories gracefully by catching SystemExit
        with pytest.raises(SystemExit):
            module.prepare_environment(self.event_dir)
        
        # SystemExit occurs before directory creation, which is expected behavior
    
    @patch('src.modules.iSS.run_external_command')
    def test_run_method(self, mock_run_command):
        """Test iSS run method."""
        config = Configuration({"number_of_particles_needed": 100000})
        full_config = Configuration({
            "general": {
                "modules": ["iSS"],
                "module_terminal_output": False,
                "memory_threshold_mb": 1000
            }
        })
        
        # Create iSS directory
        iss_dir = os.path.join(self.event_dir, "iSS")
        os.makedirs(iss_dir)
        
        module = iSS(config, full_config, self.project_root, "event_0")
        module.run(self.event_dir)
        
        # Verify external command was called
        mock_run_command.assert_called_once()


class TestEntropyMatching:
    """Test entropy matching utility module."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.temp_dir, "project")
        self.event_dir = os.path.join(self.temp_dir, "event_0")
        os.makedirs(self.project_root)
        os.makedirs(self.event_dir)
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)
    
    def test_entropy_matching_initialization(self):
        """Test entropy matching module initialization."""
        config = Configuration({"target_entropy": 1000})
        full_config = Configuration({"general": {"modules": ["entropy_matching"]}})
        
        module = EntropyMatching(config, full_config, self.project_root, "event_0")
        
        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == self.project_root
        assert module.event_id == "event_0"
    
    def test_prepare_environment(self):
        """Test entropy matching environment preparation."""
        config = Configuration({"target_entropy": 1000})
        full_config = Configuration({"general": {"modules": ["entropy_matching"]}})
        
        module = EntropyMatching(config, full_config, self.project_root, "event_0")
        
        # Test should handle missing external directories gracefully by catching SystemExit
        with pytest.raises(SystemExit):
            module.prepare_environment(self.event_dir)


class TestAfterburnerToolkit:
    """Test afterburner analysis toolkit module."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.temp_dir, "project")
        self.event_dir = os.path.join(self.temp_dir, "event_0")
        os.makedirs(self.project_root)
        os.makedirs(self.event_dir)
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.temp_dir)
    
    def test_afterburner_toolkit_initialization(self):
        """Test afterburner toolkit module initialization."""
        config = Configuration({"analysis_mode": "full"})
        full_config = Configuration({"general": {"modules": ["afterburner_toolkit"]}})
        
        module = afterburner_toolkit(config, full_config, self.project_root, "event_0")
        
        assert module.config == config
        assert module.full_config == full_config
        assert module.project_root == self.project_root
        assert module.event_id == "event_0"
    
    def test_prepare_environment(self):
        """Test afterburner toolkit environment preparation."""
        config = Configuration({"analysis_mode": "full"})
        full_config = Configuration({"general": {"modules": ["afterburner_toolkit"]}})
        
        module = afterburner_toolkit(config, full_config, self.project_root, "event_0")
        
        # Test should handle missing external directories gracefully by catching SystemExit
        with pytest.raises(SystemExit):
            module.prepare_environment(self.event_dir)


class TestModuleInterfaceCompliance:
    """Test that all physics modules comply with BaseModule interface."""
    
    def test_all_modules_implement_required_methods(self):
        """Test that all physics modules implement BaseModule interface."""
        from src.modules import (
            KoMPoST, MUSIC, SMASH,
            FromFileIC as FromFileIC_module,
            iSS, EntropyMatching as entropy_matching, afterburner_toolkit
        )
        
        modules = [
            KoMPoST,
            MUSIC,
            SMASH,
            FromFileIC_module,
            iSS,
            entropy_matching,
            afterburner_toolkit
        ]
        
        required_methods = {
            'prepare_environment', 
            'prepare_input', 
            'run', 
            'fetch_output'
        }
        
        for module_class in modules:
            for method_name in required_methods:
                assert hasattr(module_class, method_name), \
                    f"{module_class.__name__} missing {method_name} method"
                
                method = getattr(module_class, method_name)
                assert callable(method), \
                    f"{module_class.__name__}.{method_name} is not callable"
    
    def test_module_initialization_parameters(self):
        """Test that modules can be initialized with standard parameters."""
        config = Configuration({"test_param": "value"})
        full_config = Configuration({"general": {"modules": ["test"]}})
        project_root = "/tmp"
        event_id = "event_0"
        
        # Test all physics modules
        modules_to_test = [
            FromFileIC,
            KoMPoST,
            MUSIC,
            SMASH,
            iSS,
            EntropyMatching,
            afterburner_toolkit
        ]
        
        for module_class in modules_to_test:
            try:
                module = module_class(config, full_config, project_root, event_id)
                assert module.config == config
                assert module.full_config == full_config
                assert module.project_root == project_root
                assert module.event_id == event_id
            except Exception as e:
                pytest.fail(f"Failed to initialize {module_class.__name__}: {e}")


class TestModuleConfigurationValidation:
    """Test configuration validation for physics modules."""
    
    def test_kompost_configuration_validation(self):
        """Test KoMPoST configuration parameter validation."""
        # Test with missing required parameters
        incomplete_config = Configuration({"tau0": 0.2})  # Missing other params
        full_config = Configuration({"general": {"modules": ["KoMPoST"]}})
        
        module = KoMPoST(incomplete_config, full_config, "/tmp", "event_0")
        
        # Module should initialize even with incomplete config
        # Validation happens during runtime
        assert hasattr(module, 'config')
    
    def test_configuration_parameter_access(self):
        """Test accessing configuration parameters in various ways."""
        config = Configuration({
            "nested": {
                "param1": "value1",
                "param2": 42
            },
            "simple_param": "simple_value"
        })
        full_config = Configuration({"general": {"modules": ["test"]}})
        
        module = FromFileIC(config, full_config, "/tmp", "event_0")
        
        # Test attribute access
        assert module.config.simple_param == "simple_value"
        assert module.config.nested.param1 == "value1"
        assert module.config.nested.param2 == 42
        
        # Test dict access
        assert module.config["simple_param"] == "simple_value"
        assert module.config["nested"]["param1"] == "value1"


if __name__ == "__main__":
    pytest.main([__file__])