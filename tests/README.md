# install-cli.sh Tests

Pytest-based tests for the Miru CLI install script.

## Setup

```sh
cd setup/tests
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Running Tests

```sh
# Run all tests (or use ./run.sh from repo root)
pytest

# Run with verbose output (see script stdout/stderr)
TEST_VERBOSE=1 pytest -v -s

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test class
pytest test.py::TestSuccess

# Run tests matching pattern
pytest -k "checksum"
```

## Test Categories

- **TestSuccess** - Successful installation scenarios
- **TestAlreadyInstalled** - Skip/upgrade behavior for existing installs
- **TestFailure** - Error handling with informative messages
- **TestRetry** - Network retry logic
- **TestEdgeCases** - Edge cases and special scenarios
- **TestScriptStructure** - Script structure validation
- **TestIntegration** - Real network tests (skipped by default)

## How It Works

The tests use a **mock `curl`** approach rather than HTTP mocking libraries. This is necessary because `install-cli.sh` uses system `curl` directly.

The `MockCurl` class in `conftest.py`:
1. Creates a fake `curl` script in a temporary directory
2. The script reads config flags to simulate various failure modes
3. The mock directory is prepended to `PATH` when running tests
4. `INSTALL_DIR` and `SUDO` environment variables control install location

## Script Features Tested

- Latest version detection via GitHub API
- Specific version installation (`--version=v1.0.0`)
- Version normalization (adds `v` prefix if missing)
- Skip download if same version already installed
- Upgrade message when upgrading versions
- Quiet mode (`--quiet` / `-q`) for CI
- Network retry with backoff
- Checksum verification
- Corrupted archive handling
- Download timeout behavior
