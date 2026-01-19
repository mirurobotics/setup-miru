# Setup Miru CLI Action

[![CI](https://github.com/mirurobotics/setup-miru/actions/workflows/test.yml/badge.svg)](https://github.com/mirurobotics/setup-miru/actions/workflows/test.yml)
[![GitHub release](https://img.shields.io/github/v/release/mirurobotics/setup-miru)](https://github.com/mirurobotics/setup-miru/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A GitHub Action to install the [Miru CLI](https://github.com/mirurobotics/cli) in your workflows.

## Usage

### Basic Usage

Install the latest version of the Miru CLI:

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Setup Miru CLI
    uses: mirurobotics/setup-miru@v0

  - name: Verify installation
    run: miru version
```

### Pin to a Specific Version

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Setup Miru CLI
    uses: mirurobotics/setup-miru@v0
    with:
      cli-version: 'v1.2.3'
```

### Use the Installed Version in Subsequent Steps

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Setup Miru CLI
    id: miru
    uses: mirurobotics/setup-miru@v0

  - name: Print installed version
    run: echo "Installed Miru CLI ${{ steps.miru.outputs.cli-version }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `cli-version` | Miru CLI version to install (e.g., `v1.2.3`). Omit or use `latest` for the most recent release. | No | `latest` |

## Outputs

| Output | Description |
|--------|-------------|
| `cli-version` | The version of the Miru CLI that was installed |

## Supported Platforms

This action supports the following runner environments:

| OS | Architecture |
|----|--------------|
| Linux | x86_64, arm64, armv7 |
| macOS | x86_64 (Intel), arm64 (Apple Silicon) |

> **Note:** Windows runners are not currently supported.

## Features

- **Automatic version detection** — Fetches the latest release from GitHub when no version is specified
- **Version pinning** — Install a specific version for reproducible builds
- **Skip reinstall** — If the requested version is already installed, the action exits early
- **Checksum verification** — Downloads are verified against SHA256 checksums
- **Retry logic** — Automatic retries on transient network failures

## Examples

### CI Pipeline with Miru

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Setup Miru CLI
        uses: mirurobotics/setup-miru@v0

      - name: Run Miru commands
        run: |
          miru version
```

### Matrix Build Across Platforms

```yaml
name: Cross-Platform

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v6

      - name: Setup Miru CLI
        uses: mirurobotics/setup-miru@v0

      - name: Run tests
        run: miru test
```

## Development

### Testing

The action includes a comprehensive test suite using pytest. See [tests/README.md](tests/README.md) for details.

```sh
cd tests
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest
```

### Local Testing

You can test the install script directly:

```sh
# Install latest version
./scripts/install-cli.sh

# Install specific version
./scripts/install-cli.sh --version=v1.0.0

# Quiet mode (for CI)
./scripts/install-cli.sh --quiet
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

