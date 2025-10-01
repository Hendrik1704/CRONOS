# Test configuration for pytest

import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utilities'))

# Configure pytest settings
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")

@pytest.fixture(scope="session")
def project_root():
    """Provide project root directory for tests."""
    return os.path.dirname(__file__)

@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    from src.configuration import Configuration
    return Configuration({
        "general": {
            "modules": ["from_file_IC", "KoMPoST", "MUSIC", "iSS", "SMASH"],
            "memory_threshold_mb": 1000,
            "project_root": "/tmp/test_project"
        },
        "from_file_IC": {
            "data_directory": "/test/initial_conditions",
            "filename_pattern": "ic_{event_id}.dat"
        },
        "KoMPoST": {
            "shear_viscosity": 0.08,
            "tau0": 0.2,
            "tauf": 1.0,
            "dTau": 0.01,
            "nx": 200,
            "ny": 200,
            "dx": 0.1,
            "dy": 0.1
        },
        "MUSIC": {
            "tau0": 0.6,
            "tau_max": 30.0,
            "dtau": 0.01,
            "eta_over_s": 0.08,
            "grid_max_x": 10.0,
            "grid_step_x": 0.1
        },
        "iSS": {
            "number_of_repeated_sampling": 10,
            "y_cut": 2.5
        },
        "SMASH": {
            "nevents": 1,
            "end_time": 200.0,
            "dt": 0.1
        }
    })

# Mock external dependencies for testing
@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch):
    """Mock external dependencies that might not be available in test environment."""
    # Mock psutil if not available
    try:
        import psutil
    except ImportError:
        import sys
        from unittest.mock import Mock
        mock_psutil = Mock()
        sys.modules['psutil'] = mock_psutil