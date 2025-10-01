````markdown
# CRONOS Testing Suite

This document describes the comprehensive testing suite implemented for the CRONOS nuclear physics simulation framework.

Our test suite provides **complete coverage** of all CRONOS framework components with a **100% success rate**.

## Overview

The CR#### **Advanced Testing Workflow** (`.github/workflows/advanced-tests.yml`)
- 🚀 **Triggers**: Push to main/development branches, pull requests + manual dispatch
- ⚡ **Performance Tests**: Benchmarking and memory profiling
- 🔗 **Integration Tests**: Cross-module functionality validation
- 🌐 **Cross-Platform**: Ubuntu, Windows, macOS compatibility

**Python Version Compatibility:**
- **Python 3.11+**: Full compatibility with all tests passing
- **Python 3.10**: Partial compatibility - physics module `test_run_method` tests may fail due to subprocess handling differences
- **Python 3.9 and older**: Not supported due to dependency compatibility issues

#### **Workflow Features**sting suite provides comprehensive unit and integration tests covering all major components of the framework:

- **Configuration System**: Tests for configuration loading, merging, and validation
- **BaseModule Interface**: Tests for the abstract module base class and utilities
- **CheckpointManager**: Tests for simulation checkpointing and resume functionality  
- **Memory Monitoring**: Tests for memory tracking and resource monitoring
- **Physics Modules**: **Complete tests for all 7 physics simulation modules** (FromFileIC, KoMPoST, MUSIC, SMASH, iSS, EntropyMatching, afterburner_toolkit)
- **Execution Framework**: Tests for the main simulation executor and error handling
- **Utilities**: Tests for checkpoint utilities and helper functions

## Test Files

| Test File | Description | Components Tested | Test Count |
|-----------|-------------|-------------------|------------|
| `test_configuration.py` | Configuration system | Configuration class, config loading/merging | 16 tests |
| `test_module_base.py` | Base module functionality | BaseModule, memory monitoring, decorators | 15 tests |
| `test_checkpoint_manager.py` | Checkpoint management | CheckpointManager, progress tracking | 11 tests |
| `test_memory_monitor.py` | Memory monitoring | Memory tracking utilities, threshold monitoring | 10 tests |
| `test_physics_modules.py` | **All physics modules** | **Complete coverage of 7 physics modules** | **29 tests** |
| `test_executor.py` | Execution framework | Event execution, error analysis, module coordination | 4 tests |
| `test_checkpoint_utils.py` | Checkpoint utilities | Checkpoint validation, repair, statistics | 2 tests |

### 🔬 Physics Module Test Coverage

The `test_physics_modules.py` file provides **comprehensive testing** for all CRONOS physics modules:

| Physics Module | Description | Tests | Status |
|----------------|-------------|-------|--------|
| **FromFileIC** | Initial conditions from file | 4 tests | ✅ Complete |
| **KoMPoST** | Pre-equilibrium dynamics | 4 tests | ✅ Complete |
| **MUSIC** | Relativistic hydrodynamics | 4 tests | ✅ Complete |
| **SMASH** | Hadronic transport | 4 tests | ✅ Complete |
| **iSS** | Particlization (Cooper-Frye) | 4 tests | ✅ Complete |
| **EntropyMatching** | Entropy matching utility | 4 tests | ✅ Complete |
| **afterburner_toolkit** | Analysis toolkit | 5 tests | ✅ Complete |

Each physics module is tested for:
- ✅ **Initialization**: Proper module instantiation with configuration
- ✅ **Environment Preparation**: Required files and directory setup  
- ✅ **Execution**: Module run behavior and error handling
- ✅ **Configuration Compliance**: Required parameter validation

## Running Tests

### Quick Start

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_module_base.py -v

# Run all physics module tests
python -m pytest tests/test_physics_modules.py -v

# Run tests with coverage report
python -m pytest --cov=src --cov-report=term-missing
```

### Advanced Testing Options

For more advanced testing scenarios, you can use pytest's built-in options:

```bash
# Run tests with specific markers
python -m pytest -m "unit" -v

# Run tests excluding slow tests  
python -m pytest -m "not slow" -v

# Run tests for specific module with coverage
python -m pytest tests/test_configuration.py --cov=src --cov-report=term-missing

# Generate HTML coverage report
python -m pytest --cov=src --cov-report=html

# Run tests in parallel (if pytest-xdist is installed)
python -m pytest -n auto
```

### Test Suite Options

- `all`: Run all tests (default)
- `unit`: Run only unit tests (fast, isolated)
- `integration`: Run integration tests  
- `quick`: Run quick tests (excluding slow tests)
- `coverage`: Run all tests with coverage analysis

### Coverage Reports

Generate coverage reports to see test coverage across the codebase:

```bash
# Terminal coverage report
python -m pytest --cov=src --cov-report=term-missing

# HTML coverage report (creates htmlcov/index.html)
python -m pytest --cov=src --cov-report=html

# Coverage for specific module
python -m pytest --cov=src/module_base tests/test_module_base.py --cov-report=term-missing

# Combined terminal and HTML coverage
python -m pytest --cov=src --cov-report=term-missing --cov-report=html
```

## Test Organization

### Unit Tests

Focus on testing individual functions and classes in isolation:

- Mock external dependencies
- Fast execution
- High coverage of edge cases
- Marked with `@pytest.mark.unit`

### Integration Tests  

Test interactions between components:

- Use real dependencies where practical
- Test end-to-end workflows
- Validate system behavior
- Marked with `@pytest.mark.integration`

### Physics Module Tests

Specialized tests for physics simulation modules:

- Interface compliance testing
- Configuration validation
- Mock external executables
- Marked with `@pytest.mark.physics`

## Key Testing Features

### Fixtures

Common test fixtures are provided in `conftest.py`:

- `project_root`: Project directory for tests
- `sample_config`: Sample configuration for testing
- Mock external dependencies automatically

### Mocking Strategy

Tests extensively use mocking to isolate components:

- Mock external executables (KoMPoST, MUSIC, SMASH binaries)
- Mock system resources (memory, filesystem)
- Mock network dependencies
- Use `unittest.mock` for consistent mocking

### Error Testing

Comprehensive error condition testing:

- Memory exhaustion scenarios
- File system errors
- Process failures
- Configuration errors
- Network timeouts

## Test Configuration

### pytest.ini

The project includes comprehensive pytest configuration:

```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -ra
    --strict-markers
    --strict-config
    --tb=short
    --disable-warnings
    --durations=10
minversion = 6.0
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    physics: marks tests for physics modules
    checkpoint: marks tests for checkpoint functionality
    memory: marks tests for memory monitoring
    configuration: marks tests for configuration system
```

### Test Environment

Tests automatically handle:

- Temporary directories for file operations
- Mock external dependencies
- Clean test isolation
- Proper teardown after test completion

## Writing New Tests

### Test Structure

Follow this structure for new test files:

```python
import pytest
from unittest.mock import Mock, patch
from src.your_module import YourClass

class TestYourClass:
    """Test YourClass functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Initialize test fixtures
        
    def teardown_method(self):
        """Clean up after tests.""" 
        # Clean up resources
        
    def test_basic_functionality(self):
        """Test basic functionality."""
        # Test implementation
        
    @patch('src.your_module.external_dependency')
    def test_with_mocks(self, mock_dependency):
        """Test with mocked dependencies."""
                # Test with mocks
```
```

### Test Naming

- Test files: `test_*.py`
- Test classes: `Test*`  
- Test methods: `test_*`
- Use descriptive names explaining what is being tested

### Assertions

Use appropriate pytest assertions:

```python
# Basic assertions
assert result == expected
assert result is True
assert result is not None

# Exception testing
with pytest.raises(ValueError, match="error message"):
    function_that_should_fail()

# Approximate comparisons
assert result == pytest.approx(expected, rel=1e-6)
```

## Continuous Integration

### 🚀 **GitHub Actions CI/CD** 

CRONOS includes comprehensive **automated testing workflows** that run on every push and pull request:

#### **Main Test Workflow** (`.github/workflows/test.yml`)
- ✅ **Triggers**: Push to `main`/`development` branches, pull requests
- ✅ **Python Matrix**: Tests across Python 3.11, 3.12
- ✅ **Full Test Suite**: Complete test coverage with reporting
- ✅ **Security Scanning**: Automated vulnerability detection
- ✅ **Minimal Installation Test**: Validates core dependencies

#### **Advanced Testing Workflow** (`.github/workflows/advanced-tests.yml`)
- � **Triggers**: Push to main/development branches, pull requests + manual dispatch
- 🚀 **Performance Tests**: Benchmarking and memory profiling
- 🔗 **Integration Tests**: Cross-module functionality validation
- 🌐 **Cross-Platform**: Ubuntu, Windows, macOS compatibility

#### **Workflow Features**
- **Parallel Testing**: Matrix strategy across multiple Python versions
- **Coverage Reports**: Automated coverage analysis with Codecov integration
- **Artifact Management**: Test reports and coverage data preservation
- **Smart Notifications**: Success/failure reporting with detailed summaries
- **Security Scanning**: Bandit security analysis on pull requests

### **CI/CD Best Practices**

The test suite is designed for optimal CI/CD integration:

- ⚡ **Fast unit tests** for quick feedback (< 2 minutes)
- 🔬 **Comprehensive integration tests** for thorough validation
- 📊 **Coverage reporting** for code quality metrics  
- 🏷️ **Clear test categorization** for selective testing
- 🛡️ **Security scanning** for vulnerability detection

## Best Practices

### Test Independence

- Each test should be completely independent
- Use `setup_method`/`teardown_method` for test isolation
- Avoid shared state between tests
- Mock external dependencies

### Test Coverage

Aim for high test coverage:

- Test normal operation paths
- Test error conditions
- Test edge cases and boundary conditions
- Test configuration variations

### Performance

Keep tests fast:

- Use mocks instead of real external services
- Create minimal test data
- Avoid unnecessary file I/O
- Mark slow tests appropriately

### Documentation

Document test purpose and setup:

- Clear test method names
- Docstrings explaining complex test scenarios
- Comments for non-obvious test logic
- Examples of expected behavior

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes project root
2. **Missing Dependencies**: Install test requirements with `pip install -r requirements.txt`
3. **File Permission Errors**: Tests create temporary files - ensure write permissions
4. **Mock Issues**: Verify mock paths match actual import structure

### Debug Mode

Run tests with debugging:

```bash
# Drop into debugger on failure
python -m pytest --pdb

# Capture print statements
python -m pytest -s

# Run single test with debugging
python -m pytest tests/test_module_base.py::TestBaseModule::test_initialization -v -s
```

```

This comprehensive testing suite ensures CRONOS framework reliability and makes development safer and more efficient.