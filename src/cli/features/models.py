# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Feature data model and the registry of available feature checks."""

from typing import NamedTuple


class FeatureInfo(NamedTuple):
    """Complete information about a feature check."""

    name: str
    description: str
    category: str
    config_file: str | None = None
    config_example: str | None = None
    detection_method: str | None = None


# Feature registry with name, description, category, and optional config info
AVAILABLE_FEATURES: dict[str, tuple[str, str, str | None, str | None, str | None]] = {
    # CI/CD Features
    "dependabot": (
        "Dependabot configuration detection",
        "CI/CD",
        ".github/dependabot.yml",
        '''version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"''',
        "Checks for .github/dependabot.yml or .github/dependabot.yaml",
    ),
    "github2gerrit": (
        "GitHub to Gerrit workflow synchronization",
        "CI/CD",
        ".github/workflows/gerrit-sync.yml",
        """name: Gerrit Sync
on: [push]
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Sync to Gerrit
        run: git push gerrit""",
        "Detects GitHub Actions workflows with Gerrit sync jobs",
    ),
    "github-actions": (
        "GitHub Actions workflows",
        "CI/CD",
        ".github/workflows/*.yml",
        """name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest""",
        "Checks for any YAML files in .github/workflows/",
    ),
    "jenkins": (
        "Jenkins CI/CD jobs",
        "CI/CD",
        "Jenkinsfile",
        """pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'make'
            }
        }
    }
}""",
        "Looks for Jenkinsfile in repository root",
    ),
    # Code Quality Features
    "pre-commit": (
        "Pre-commit hooks configuration",
        "Code Quality",
        ".pre-commit-config.yaml",
        """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml""",
        "Checks for .pre-commit-config.yaml",
    ),
    "linting": (
        "Code linting configuration (pylint, flake8, etc.)",
        "Code Quality",
        ".pylintrc, .flake8, pyproject.toml",
        """[tool.pylint]
max-line-length = 100
disable = ["C0111"]

[tool.flake8]
max-line-length = 100
exclude = [".git", "__pycache__"]""",
        "Detects .pylintrc, .flake8, setup.cfg, or pyproject.toml with linting config",
    ),
    "sonarqube": (
        "SonarQube analysis configuration",
        "Code Quality",
        "sonar-project.properties",
        """sonar.projectKey=my-project
sonar.projectName=My Project
sonar.sources=src
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml""",
        "Checks for sonar-project.properties or sonar scanner configuration",
    ),
    # Documentation Features
    "readthedocs": (
        "ReadTheDocs integration",
        "Documentation",
        ".readthedocs.yml",
        """version: 2
build:
  os: ubuntu-22.04
  tools:
    python: "3.10"
sphinx:
  configuration: docs/conf.py""",
        "Checks for .readthedocs.yml or .readthedocs.yaml",
    ),
    "sphinx": (
        "Sphinx documentation",
        "Documentation",
        "docs/conf.py",
        """project = 'My Project'
copyright = '2025, Author'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]
html_theme = 'sphinx_rtd_theme' """,
        "Looks for docs/conf.py or docs/source/conf.py",
    ),
    "mkdocs": (
        "MkDocs documentation",
        "Documentation",
        "mkdocs.yml",
        """site_name: My Project
theme:
  name: material
nav:
  - Home: index.md
  - API: api.md""",
        "Checks for mkdocs.yml or mkdocs.yaml",
    ),
    # Build & Package Features
    "maven": (
        "Maven build configuration",
        "Build & Package",
        "pom.xml",
        """<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
</project>""",
        "Detects pom.xml in repository",
    ),
    "gradle": (
        "Gradle build configuration",
        "Build & Package",
        "build.gradle or build.gradle.kts",
        """plugins {
    id 'java'
    id 'application'
}

group = 'com.example'
version = '1.0.0'

repositories {
    mavenCentral()
}""",
        "Checks for build.gradle, build.gradle.kts, or settings.gradle",
    ),
    "npm": (
        "NPM package configuration",
        "Build & Package",
        "package.json",
        """{
  "name": "my-package",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "build": "webpack"
  },
  "dependencies": {}
}""",
        "Looks for package.json in repository root",
    ),
    "docker": (
        "Docker containerization",
        "Build & Package",
        "Dockerfile",
        """FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]""",
        "Checks for Dockerfile or docker-compose.yml",
    ),
    "sonatype": (
        "Sonatype/Maven Central publishing",
        "Build & Package",
        "pom.xml with distribution management",
        """<distributionManagement>
  <repository>
    <id>ossrh</id>
    <url>https://oss.sonatype.org/service/local/staging/deploy/maven2/</url>
  </repository>
</distributionManagement>""",
        "Analyzes pom.xml for Sonatype/Maven Central configuration",
    ),
    # Repository Features
    "github-mirror": (
        "GitHub mirror repository detection",
        "Repository",
        "Repository description or topics",
        None,
        "Checks repository description and topics for mirror indicators",
    ),
    "gitreview": (
        "Gerrit git-review configuration",
        "Repository",
        ".gitreview",
        """[gerrit]
host=gerrit.example.com
port=29418
project=my-project.git
defaultbranch=main""",
        "Looks for .gitreview file",
    ),
    "license": (
        "License file detection",
        "Repository",
        "LICENSE, COPYING, or LICENSE.txt",
        """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/""",
        "Searches for LICENSE, COPYING, LICENSE.txt, LICENSE.md, or LICENSES/ directory",
    ),
    "readme": (
        "README file quality check",
        "Repository",
        "README.md or README.rst",
        r"""# My Project

A brief description of the project.

## Installation
```bash
pip install my-project
```

## Usage
...""",
        "Checks for README.md, README.rst, or README.txt and evaluates quality",
    ),
    # Testing Features
    "pytest": (
        "PyTest testing framework",
        "Testing",
        "pytest.ini or pyproject.toml",
        '''[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --cov=src"''',
        "Detects pytest.ini, pyproject.toml, or tests/ directory with test files",
    ),
    "junit": (
        "JUnit testing framework",
        "Testing",
        "pom.xml with JUnit dependency",
        """<dependency>
  <groupId>org.junit.jupiter</groupId>
  <artifactId>junit-jupiter</artifactId>
  <version>5.9.0</version>
  <scope>test</scope>
</dependency>""",
        "Checks for JUnit dependencies in pom.xml or build.gradle",
    ),
    "coverage": (
        "Code coverage reporting",
        "Testing",
        ".coveragerc or pyproject.toml",
        """[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover"]""",
        "Looks for .coveragerc, .coverage, or coverage configuration in pyproject.toml",
    ),
    # Security Features
    "security-scanning": (
        "Security vulnerability scanning",
        "Security",
        ".github/workflows/security.yml",
        """name: Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Bandit
        run: bandit -r src/""",
        "Detects security scanning in CI/CD or config files like .bandit",
    ),
    "secrets-detection": (
        "Secrets and credentials detection",
        "Security",
        ".gitleaks.toml or .gitguardian.yml",
        """[allowlist]
description = "Allowed patterns"
regexes = ["""
        + "'''"
        + r"""^test_"""
        + """]

[[rules]]
description = "AWS Access Key"
regex = """
        + "'''"
        + r"""AKIA[0-9A-Z]{16}"""
        + '''""''',
        "Checks for gitleaks, git-secrets, or GitGuardian configuration",
    ),
}
