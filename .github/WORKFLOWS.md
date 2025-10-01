# CRONOS GitHub Actions CI/CD Workflows

This document explains the automated CI/CD setup for the CRONOS nuclear physics simulation framework.

## 🚀 Overview

CRONOS uses **GitHub Actions** for comprehensive automated testing and quality assurance. The workflows ensure that:

- ✅ All code changes are thoroughly tested
- ✅ Multiple Python versions are supported (3.8-3.12)
- ✅ Cross-platform compatibility is maintained
- ✅ Security vulnerabilities are detected
- ✅ Code coverage is tracked and reported

## 📋 Workflow Files

### 1. Main Test Workflow (`.github/workflows/test.yml`)

**Triggers:**
- Push to `main`, `development`, or `dev` branches
- Pull requests targeting these branches
- Manual workflow dispatch

**Features:**
- **Python Matrix Testing**: Tests across Python 3.11, 3.12
- **Full Test Suite**: Complete test coverage with detailed reporting
- **Security Scanning**: Bandit security analysis on pull requests
- **Minimal Installation Test**: Validates core dependencies work standalone
- **Coverage Upload**: Integrates with Codecov for coverage tracking
- **Artifact Management**: Preserves test reports and coverage data

**Jobs:**
1. `test` - Main testing matrix across Python versions
2. `test-minimal` - Minimal installation validation
3. `security-scan` - Security vulnerability scanning (PR only)
4. `notify-success` - Success notification with summary

### 2. Advanced Testing Workflow (`.github/workflows/advanced-tests.yml`)

**Triggers:**
- Push to `main`, `development`, or `dev` branches
- Pull requests targeting these branches
- Manual workflow dispatch with test type selection

**Test Types:**
- `performance` - Performance benchmarking and memory profiling
- `memory` - Memory usage pattern analysis
- `integration` - Cross-module integration testing
- `all` - Complete advanced test suite including cross-platform matrix (default)

**Jobs:**
1. `performance-tests` - Performance and memory benchmarking
2. `integration-tests` - Module integration validation
3. `test-matrix-extended` - Cross-platform testing (Ubuntu, Windows, macOS)
4. `notify-advanced-complete` - Advanced test completion summary

## 🎯 Workflow Benefits

### For Developers
- **Immediate Feedback**: Test results within minutes of push
- **Multi-Version Support**: Confidence across Python versions
- **Security Alerts**: Early vulnerability detection
- **Coverage Insights**: Code coverage tracking and improvement

### For Maintainers
- **Quality Assurance**: Automated quality gates
- **Performance Monitoring**: Performance regression detection
- **Cross-Platform Confidence**: Multi-OS compatibility validation
- **Integration Validation**: Cross-module functionality verification

### For Users
- **Reliability**: Thoroughly tested releases
- **Compatibility**: Known Python version support
- **Security**: Regular vulnerability scanning
- **Trust**: Transparent testing process with public results

## 🔧 Configuration Details

### Python Dependencies
The workflows automatically install:
- Core dependencies from `requirements.txt`
- Testing frameworks: `pytest`, `pytest-cov`, `pytest-mock`
- Development tools: `flake8`, `bandit`
- Performance tools: `pytest-benchmark`, `memory-profiler`

### Test Execution
- **Test Discovery**: Automatic via pytest configuration
- **Parallel Execution**: Using `pytest-xdist` for speed
- **Coverage Collection**: Source code coverage with exclusions
- **Report Generation**: Multiple formats (terminal, XML, HTML)

### Security Scanning
- **Tool**: Bandit for Python security analysis
- **Scope**: All source code in `src/` directory
- **Output**: JSON and text reports
- **Integration**: Results uploaded as artifacts

## 📊 Status Badges

The README.md includes status badges for:
- **Main Test Suite**: Current test status across Python versions
- **Advanced Tests**: Status of extended testing workflow
- **Python Support**: Supported Python version range
- **License**: MIT license indicator
- **Test Status**: Current test passing status

## 🚨 Troubleshooting

### Common Issues

1. **Test Failures**: Check the Actions tab for detailed logs
2. **Coverage Drops**: Review the coverage report in artifacts
3. **Security Alerts**: Check Bandit report in PR artifacts
4. **Performance Regression**: Review performance test results

### Manual Workflow Triggers

You can manually trigger workflows:

```bash
# Via GitHub CLI (if installed)
gh workflow run "CRONOS Test Suite"
gh workflow run "CRONOS Advanced Testing" -f test_type=all

# Via GitHub Web Interface
# Go to Actions tab → Select workflow → "Run workflow" button
```

### Local Testing

Before pushing, run the same tests locally:

```bash
# Same as CI main tests
python -m pytest tests/ --cov=src --cov-report=term-missing -v

# Same as CI security scan
pip install bandit
bandit -r src/ -f txt

# Same as CI performance tests
python -c "
import time
from src.configuration import Configuration
start = time.time()
for i in range(100):
    config = Configuration()
print(f'Average: {(time.time()-start)/100:.4f}s')
"
```

## 🔮 Future Enhancements

Potential workflow improvements:
- **Integration with External Physics Codes**: Test with actual MUSIC/SMASH when available
- **Performance Regression Detection**: Automated performance comparison
- **Release Automation**: Automated version tagging and releases
- **Cluster Testing**: Integration with actual SLURM environments
- **Deployment Automation**: Automated deployment to staging environments

## 📈 Metrics and Monitoring

The workflows provide metrics on:
- **Test Execution Time**: Track performance over time
- **Coverage Trends**: Monitor code coverage changes
- **Security Posture**: Track vulnerability remediation
- **Cross-Platform Compatibility**: Ensure broad compatibility

This comprehensive CI/CD setup ensures CRONOS maintains high quality, security, and reliability standards throughout development.