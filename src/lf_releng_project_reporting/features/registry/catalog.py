# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Project type detection catalogue.

The static mapping from project type to the configuration files and glob
patterns that indicate it, used by the project type scoring pass.
"""

# Mapping of detected project type to the config files / glob patterns that
# indicate it. Patterns containing "*" are treated as globs; all others are
# checked as exact repository-relative paths.
_PROJECT_TYPE_PATTERNS: dict[str, list[str]] = {
    "Maven": ["pom.xml"],
    "Gradle": [
        "build.gradle",
        "build.gradle.kts",
        "gradle.properties",
        "settings.gradle",
    ],
    "JavaScript": ["package.json", "**/*.js", "**/*.mjs", "**/*.cjs"],
    "TypeScript": ["tsconfig.json", "**/*.ts", "**/*.tsx"],
    "Node": ["package.json"],
    "Python": [
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "poetry.lock",
        "**/*.py",
    ],
    "Dockerfile": [
        "Dockerfile",
        "**/*.dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    ],
    "Shell": ["**/*.sh", "**/*.bash", "**/*.zsh", "**/*.ksh"],
    "Go": ["go.mod", "go.sum", "**/*.go"],
    "Rust": ["Cargo.toml", "Cargo.lock", "**/*.rs"],
    "Java": ["**/*.java"],
    "Java/Ant": ["build.xml", "ivy.xml"],
    "C++": [
        "**/*.cpp",
        "**/*.hpp",
        "**/*.cc",
        "**/*.hh",
        "**/*.cxx",
        "**/*.hxx",
        "CMakeLists.txt",
    ],
    "C": ["**/*.c", "**/*.h"],
    ".NET": ["**/*.csproj", "**/*.sln", "project.json", "**/*.vbproj", "**/*.fsproj"],
    "Ruby": ["Gemfile", "Rakefile", "**/*.gemspec", "**/*.rb"],
    "PHP": ["composer.json", "composer.lock", "**/*.php"],
    "Scala": ["build.sbt", "project/build.properties", "**/*.scala"],
    "Swift": ["Package.swift", "**/*.swift"],
    "Kotlin": ["**/*.kt", "**/*.kts"],
    "Groovy": ["**/*.groovy", "Jenkinsfile", "**/*.gradle"],
    "Smarty": ["**/*.tpl", "smarty.conf", "**/*.smarty"],
    "EJS": ["**/*.ejs", "**/*.ect"],
    "Robot Framework": ["**/*.robot", "**/*.resource"],
    "D": ["**/*.d", "**/*.di"],
    "SCSS": ["**/*.scss"],
    "HTML": ["**/*.html", "**/*.htm"],
    "CSS": ["**/*.css"],
    "HCL": ["**/*.hcl", "**/*.tf", "**/*.tfvars"],
    "Clojure": ["**/*.clj", "**/*.cljs", "**/*.cljc", "**/*.edn"],
    "Erlang": ["**/*.erl", "**/*.hrl", "rebar.config"],
    "Lua": ["**/*.lua"],
    "PLpgSQL": ["**/*.pgsql", "**/*.sql"],
}
