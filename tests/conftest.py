"""Pytest fixtures for testing install-cli.sh."""

import hashlib
import io
import os
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "install-cli.sh"

# =============================================================================
# Test Helpers
# =============================================================================


def create_mock_tarball(version: str = "v1.0.0") -> bytes:
    """Create a minimal tar.gz containing a fake 'miru' binary."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        content = f"#!/bin/sh\necho 'miru {version}'\n".encode()
        info = tarfile.TarInfo(name="miru")
        info.size = len(content)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(content))
    buffer.seek(0)
    return buffer.read()


def create_checksums(tarball: bytes) -> str:
    """Generate checksums file for all supported platforms."""
    checksum = hashlib.sha256(tarball).hexdigest()
    platforms = ["Linux_x86_64", "Linux_arm64", "Darwin_x86_64", "Darwin_arm64"]
    return "\n".join(f"{checksum}  cli_{p}.tar.gz" for p in platforms) + "\n"


def assert_install_success(result: subprocess.CompletedProcess, verbose: bool = False) -> None:
    """Assert that installation completed successfully."""
    if verbose:
        print(f"\n--- stdout ---\n{result.stdout}")
        if result.stderr:
            print(f"--- stderr ---\n{result.stderr}")
    assert result.returncode == 0, f"Install failed:\n{result.stderr}"
    assert "successfully installed to" in result.stdout, f"Missing success message:\n{result.stdout}"


# =============================================================================
# Mock Infrastructure
# =============================================================================

LATEST_VERSION = "v0.8.0"


@dataclass
class MockConfig:
    """Configuration for mock curl behavior."""

    version: str = LATEST_VERSION
    fail_api: bool = False
    fail_download: bool = False
    fail_checksum: bool = False
    empty_response: bool = False
    bad_checksum: bool = False
    corrupt_tarball: bool = False
    slow_download: float = 0  # Delay in seconds
    api_error_message: str = ""  # Simulate GitHub API error response (e.g., "Not Found")


class MockCurl:
    """Creates a mock curl script for testing."""

    def __init__(self, directory: Path, tarball: bytes, config: MockConfig):
        self.dir = directory
        self.data_dir = directory / "data"
        self.tarball = tarball
        self.config = config

    def setup(self) -> None:
        """Write all mock files."""
        self.data_dir.mkdir(exist_ok=True)
        self._write_data()
        self._write_script()

    def _write_data(self) -> None:
        """Write data files that mock curl will serve."""
        cfg = self.config

        # API response
        if cfg.api_error_message:
            api_response = f'{{"message": "{cfg.api_error_message}"}}'
        elif cfg.empty_response:
            api_response = "{}"
        else:
            api_response = f'{{"tag_name": "{cfg.version}"}}'
        (self.data_dir / "api.json").write_text(api_response)

        # Binary tarball
        if cfg.corrupt_tarball:
            # Invalid gzip data
            (self.data_dir / "binary.tar.gz").write_bytes(b"not a valid tarball")
        else:
            (self.data_dir / "binary.tar.gz").write_bytes(self.tarball)

        # Checksums - use the actual tarball checksum even for corrupt files
        # (script downloads first, then verifies, then extracts)
        if cfg.bad_checksum:
            checksums = "0" * 64 + "  cli_Linux_x86_64.tar.gz\n"
        elif cfg.corrupt_tarball:
            # Checksum matches the corrupt data so extraction is attempted
            corrupt_checksum = hashlib.sha256(b"not a valid tarball").hexdigest()
            platforms = ["Linux_x86_64", "Linux_arm64", "Darwin_x86_64", "Darwin_arm64"]
            checksums = "\n".join(f"{corrupt_checksum}  cli_{p}.tar.gz" for p in platforms) + "\n"
        else:
            checksums = create_checksums(self.tarball)
        (self.data_dir / "checksums.txt").write_text(checksums)

        # Config flags
        (self.data_dir / "fail_api").write_text("1" if cfg.fail_api else "0")
        (self.data_dir / "fail_download").write_text("1" if cfg.fail_download else "0")
        (self.data_dir / "fail_checksum").write_text("1" if cfg.fail_checksum else "0")
        (self.data_dir / "slow_download").write_text(str(cfg.slow_download))

    def _write_script(self) -> None:
        """Write the mock curl shell script."""
        script = self.dir / "curl"
        script.write_text(self._generate_script())
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _generate_script(self) -> str:
        return f'''#!/bin/sh
DATA="{self.data_dir}"

# Parse args to find URL and output file
URL="" OUTPUT=""
while [ $# -gt 0 ]; do
    case "$1" in
        -o) OUTPUT="$2"; shift 2 ;;
        -*) shift ;;
        *)  URL="$1"; shift ;;
    esac
done

# Check failure flags
[ "$(cat "$DATA/fail_api")" = "1" ] && case "$URL" in *api.github.com*) exit 1 ;; esac
[ "$(cat "$DATA/fail_download")" = "1" ] && case "$URL" in *.tar.gz) exit 22 ;; esac
[ "$(cat "$DATA/fail_checksum")" = "1" ] && case "$URL" in *checksums*) exit 22 ;; esac

# Simulate slow download
DELAY=$(cat "$DATA/slow_download" 2>/dev/null || echo 0)
if [ "$DELAY" != "0" ]; then
    case "$URL" in *.tar.gz) sleep "$DELAY" ;; esac
fi

# Serve content based on URL
serve() {{ [ -n "$OUTPUT" ] && cp "$1" "$OUTPUT" || cat "$1"; }}

case "$URL" in
    *releases/latest*) cat "$DATA/api.json" ;;
    *.tar.gz)          serve "$DATA/binary.tar.gz" ;;
    *checksums*)       serve "$DATA/checksums.txt" ;;
    *)                 echo "Unknown URL: $URL" >&2; exit 1 ;;
esac
'''


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tarball() -> bytes:
    """Provide a mock binary tarball."""
    return create_mock_tarball()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_curl(temp_dir: Path, mock_tarball: bytes):
    """Provide a configurable mock curl instance."""
    mock_dir = temp_dir / "mock"
    mock_dir.mkdir()
    return MockCurl(mock_dir, mock_tarball, MockConfig())


# =============================================================================
# Test Runner
# =============================================================================


def run_install(
    *args: str,
    install_dir: Path,
    mock_curl: MockCurl,
    env: dict | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run install-cli.sh with mocked curl.

    Args:
        *args: Command line arguments (e.g., "--version=v1.0.0")
        install_dir: Directory to install the binary to
        mock_curl: MockCurl instance (must have setup() called first)
        env: Additional environment variables
        timeout: Timeout in seconds for the subprocess

    Returns:
        CompletedProcess with stdout, stderr, and returncode
    """
    run_env = os.environ.copy()
    run_env["PATH"] = f"{mock_curl.dir}:{run_env.get('PATH', '')}"
    run_env["INSTALL_DIR"] = str(install_dir)
    run_env["SUDO"] = ""
    run_env["MAX_RETRIES"] = "1"  # Disable retries in tests for speed
    run_env["RETRY_DELAY"] = "0"
    if env:
        run_env.update(env)

    result = subprocess.run(
        ["sh", str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        env=run_env,
        timeout=timeout,
    )

    # Print output in verbose mode (set TEST_VERBOSE=1)
    if os.environ.get("TEST_VERBOSE"):
        print(f"\n{'='*60}")
        print(f"Command: sh {SCRIPT_PATH} {' '.join(args)}")
        print(f"{'='*60}")
        print(result.stdout)
        if result.stderr:
            print(f"--- stderr ---\n{result.stderr}")

    return result


def install_mock_binary(install_dir: Path, version: str) -> Path:
    """Install a mock miru binary that reports a specific version."""
    binary = install_dir / "miru"
    binary.write_text(f"#!/bin/sh\necho 'miru {version}'\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary
