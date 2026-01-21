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
    uses: mirurobotics/setup-miru@v0.1

  - name: Verify installation
    run: miru version
```

### Pin to a Specific Version

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Setup Miru CLI
    uses: mirurobotics/setup-miru@v0.1
    with:
      version: 'v0.8.0'
```

### Pin to a Major or Minor Version

You can also specify a major or minor version to get the latest release within that range:

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Setup Miru CLI (latest v0.x.x)
    uses: mirurobotics/setup-miru@v0.1
    with:
      version: 'v0'

  # Or pin to a minor version (latest v0.8.x)
  - name: Setup Miru CLI (latest v0.8.x)
    uses: mirurobotics/setup-miru@v0.1
    with:
      version: 'v0.8'
```

### Use the Installed Version in Subsequent Steps

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Setup Miru CLI
    id: miru
    uses: mirurobotics/setup-miru@v0.1

  - name: Print installed version
    run: echo "Installed Miru CLI ${{ steps.miru.outputs.version }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `version` | Miru CLI version to install. Supports exact (`v0.8.0`), major (`v0`), and minor (`v0.8`) versions. Omit or use `latest` for the most recent release. | No | `latest` |

## Outputs

| Output | Description |
|--------|-------------|
| `version` | The version of the Miru CLI that was installed |

## Supported Platforms

This action supports the following runner environments:

| OS | Architecture |
|----|--------------|
| Linux | x86_64, arm64 |
| macOS | x86_64 (Intel), arm64 (Apple Silicon) |

> **Note:** Windows runners are not currently supported.

## Example - CI Pipeline with Miru

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
        uses: mirurobotics/setup-miru@v0.1

      - name: Run Miru commands
        run: |
          miru version
```