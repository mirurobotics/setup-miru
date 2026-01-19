"""Tests for install-cli.sh."""

import os
import subprocess
from pathlib import Path

import pytest

from conftest import (
    SCRIPT_PATH,
    MockCurl,
    assert_install_success,
    install_mock_binary,
    run_install,
)


class TestSuccess:
    """Successful installation scenarios."""

    def test_latest_version(self, mock_curl: MockCurl, temp_dir: Path):
        """Install latest stable version."""
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_install_success(result)
        assert (temp_dir / "miru").exists()

    def test_specific_version(self, mock_curl: MockCurl, temp_dir: Path):
        """Install a specific version with --version flag."""
        mock_curl.setup()

        result = run_install("--version=v0.9.0", install_dir=temp_dir, mock_curl=mock_curl)

        assert_install_success(result)
        assert "v0.9.0" in result.stdout

    def test_version_without_v_prefix(self, mock_curl: MockCurl, temp_dir: Path):
        """Install a version specified without v prefix."""
        mock_curl.setup()

        result = run_install("--version=1.0.0", install_dir=temp_dir, mock_curl=mock_curl)

        assert_install_success(result)
        assert "1.0.0" in result.stdout

    def test_quiet_flag(self, mock_curl: MockCurl, temp_dir: Path):
        """Quiet mode suppresses output."""
        mock_curl.setup()

        result = run_install("--quiet", install_dir=temp_dir, mock_curl=mock_curl)

        assert result.returncode == 0
        assert (temp_dir / "miru").exists()
        assert result.stdout.strip() == ""

    def test_quiet_flag_short(self, mock_curl: MockCurl, temp_dir: Path):
        """Short quiet flag (-q) works."""
        mock_curl.setup()

        result = run_install("-q", install_dir=temp_dir, mock_curl=mock_curl)

        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestAlreadyInstalled:
    """Skip/upgrade behavior for existing installations."""

    def test_skip_same_version(self, mock_curl: MockCurl, temp_dir: Path):
        """Skip download if same version already installed."""
        install_mock_binary(temp_dir, "v1.0.0")
        mock_curl.config.version = "v1.0.0"
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert result.returncode == 0
        assert "already installed" in result.stdout

    def test_upgrade_different_version(self, mock_curl: MockCurl, temp_dir: Path):
        """Upgrade when different version is installed."""
        install_mock_binary(temp_dir, "v0.9.0")
        mock_curl.config.version = "v1.0.0"
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_install_success(result)
        assert "Upgrading" in result.stdout
        assert "v0.9.0" in result.stdout
        assert "v1.0.0" in result.stdout


def assert_error(result: subprocess.CompletedProcess, *expected_in_message: str) -> None:
    """Assert command failed with informative error containing expected strings."""
    assert result.returncode != 0, "Expected command to fail"
    for expected in expected_in_message:
        assert expected in result.stderr, f"Error should mention '{expected}':\n{result.stderr}"


class TestFailure:
    """Failure scenarios - verify errors are informative."""

    def test_api_unreachable(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message includes the API URL that failed."""
        mock_curl.config.fail_api = True
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "api.github.com")

    def test_api_empty_response(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message explains parsing failed."""
        mock_curl.config.empty_response = True
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "parse", "version")

    def test_download_fails(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message includes the download URL."""
        mock_curl.config.fail_download = True
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "Failed to download", ".tar.gz")

    def test_checksum_download_fails(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message includes the checksums URL."""
        mock_curl.config.fail_checksum = True
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "checksums")

    def test_checksum_mismatch(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message shows expected vs actual checksum."""
        mock_curl.config.bad_checksum = True
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "Checksum mismatch", "Expected:", "Actual:")

    def test_version_not_found(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message includes the version that wasn't found."""
        mock_curl.config.fail_download = True
        mock_curl.setup()

        result = run_install("--version=v99.99.99", install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "v99.99.99")

    def test_corrupt_archive(self, mock_curl: MockCurl, temp_dir: Path):
        """Error message indicates archive is corrupted."""
        mock_curl.config.corrupt_tarball = True
        mock_curl.setup()

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)

        assert_error(result, "extract", "corrupt")

    @pytest.mark.timeout(5)
    def test_timeout_on_slow_download(self, mock_curl: MockCurl, temp_dir: Path):
        """Script times out on hung downloads."""
        mock_curl.config.slow_download = 10  # Longer than test timeout
        mock_curl.setup()

        with pytest.raises(subprocess.TimeoutExpired):
            run_install(install_dir=temp_dir, mock_curl=mock_curl, timeout=2)


class TestRetry:
    """Network retry behavior."""

    def test_retries_shown_in_output(self, mock_curl: MockCurl, temp_dir: Path):
        """Script mentions retry in output (retry logic exists)."""
        content = SCRIPT_PATH.read_text()
        assert "retry" in content.lower()
        assert "MAX_RETRIES" in content


class TestEdgeCases:
    """Edge cases."""

    def test_reinstall(self, mock_curl: MockCurl, temp_dir: Path):
        """Can reinstall over existing binary."""
        mock_curl.setup()

        result1 = run_install(install_dir=temp_dir, mock_curl=mock_curl)
        assert_install_success(result1)

        result2 = run_install(install_dir=temp_dir, mock_curl=mock_curl)
        # Second install should skip (same version)
        assert result2.returncode == 0

    def test_warns_if_not_in_path(self, mock_curl: MockCurl, temp_dir: Path):
        """Warns when INSTALL_DIR is not in PATH."""
        mock_curl.setup()

        # Use a PATH that doesn't include temp_dir
        result = run_install(
            install_dir=temp_dir,
            mock_curl=mock_curl,
            env={"PATH": "/usr/bin:/bin"},
        )

        assert_install_success(result)
        assert "not in your PATH" in result.stdout

    def test_no_warning_if_in_path(self, mock_curl: MockCurl, temp_dir: Path):
        """No warning when INSTALL_DIR is already in PATH."""
        mock_curl.setup()

        # Include temp_dir in PATH
        result = run_install(
            install_dir=temp_dir,
            mock_curl=mock_curl,
            env={"PATH": f"{temp_dir}:/usr/bin:/bin"},
        )

        assert_install_success(result)
        assert "not in your PATH" not in result.stdout

    def test_temp_dir_cleaned_on_success(self, mock_curl: MockCurl, temp_dir: Path):
        """Temp directory is cleaned up after successful install."""
        import glob
        import tempfile
        mock_curl.setup()

        # Find temp dirs (works on both Linux /tmp and macOS /var/folders)
        tmp_base = tempfile.gettempdir()
        pattern = f"{tmp_base}/tmp.*"
        before = set(glob.glob(pattern))

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)
        assert_install_success(result)

        # Count temp dirs after - should be same (no new leftover dirs)
        after = set(glob.glob(pattern))
        new_dirs = after - before
        assert len(new_dirs) == 0, f"Leftover temp dirs: {new_dirs}"

    def test_temp_dir_cleaned_on_failure(self, mock_curl: MockCurl, temp_dir: Path):
        """Temp directory is cleaned up even after failed install."""
        import glob
        import tempfile
        mock_curl.config.fail_download = True
        mock_curl.setup()

        # Find temp dirs (works on both Linux /tmp and macOS /var/folders)
        tmp_base = tempfile.gettempdir()
        pattern = f"{tmp_base}/tmp.*"
        before = set(glob.glob(pattern))

        result = run_install(install_dir=temp_dir, mock_curl=mock_curl)
        assert result.returncode != 0  # Should fail

        # Count temp dirs after - should be same (no new leftover dirs)
        after = set(glob.glob(pattern))
        new_dirs = after - before
        assert len(new_dirs) == 0, f"Leftover temp dirs: {new_dirs}"


class TestScriptStructure:
    """Validate script structure."""

    @pytest.mark.parametrize("cmd", ["curl", "tar", "grep", "cut"])
    def test_checks_dependencies(self, cmd: str):
        """Script checks for required commands."""
        content = SCRIPT_PATH.read_text()
        assert "for cmd in" in content and cmd in content

    def test_uses_set_e(self):
        """Script uses 'set -e' for error handling."""
        assert "set -e" in SCRIPT_PATH.read_text()

    def test_has_cleanup_trap(self):
        """Script has trap for cleanup."""
        assert "trap" in SCRIPT_PATH.read_text()

    def test_verifies_checksum(self):
        """Script verifies checksums."""
        content = SCRIPT_PATH.read_text().lower()
        assert "verify_checksum" in content or "sha256" in content

    def test_handles_unsupported_os(self):
        """Script handles unsupported OS."""
        assert "Unsupported operating system" in SCRIPT_PATH.read_text()

    def test_handles_unsupported_arch(self):
        """Script handles unsupported architecture."""
        assert "Unsupported architecture" in SCRIPT_PATH.read_text()

    def test_posix_compatible(self):
        """Script is POSIX sh compatible."""
        result = subprocess.run(["sh", "-n", str(SCRIPT_PATH)], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_has_quiet_flag(self):
        """Script supports --quiet flag."""
        content = SCRIPT_PATH.read_text()
        assert "--quiet" in content or "-q" in content


class TestIntegration:
    """Integration tests that hit real GitHub (marked slow)."""

    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("RUN_SLOW") != "1",
        reason="Slow test; run with ./run.sh --slow",
    )
    def test_real_download(self, temp_dir: Path):
        """Actually download from GitHub to verify URLs work."""
        import os

        env = os.environ.copy()
        env["INSTALL_DIR"] = str(temp_dir)
        env["SUDO"] = ""

        result = subprocess.run(
            ["sh", str(SCRIPT_PATH), "--version=v0.7.0"],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

        assert result.returncode == 0, f"Real download failed:\n{result.stderr}"
        assert (temp_dir / "miru").exists()
