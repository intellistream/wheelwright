---
name: sage-pypi-publisher
description: Agent for compiler/build/publish workflow in sage-pypi-publisher.
argument-hint: Include module/command touched, expected behavior, and failure mode to guard.
tools: ['vscode', 'execute', 'read', 'agent', 'edit', 'search', 'web', 'todo', 'vscode.mermaid-chat-features/renderMermaidDiagram', 'github.vscode-pull-request-github/issue_fetch', 'github.vscode-pull-request-github/suggest-fix', 'github.vscode-pull-request-github/searchSyntax', 'github.vscode-pull-request-github/doSearch', 'github.vscode-pull-request-github/renderIssues', 'github.vscode-pull-request-github/activePullRequest', 'github.vscode-pull-request-github/openPullRequest', 'ms-azuretools.vscode-containers/containerToolsConfig', 'ms-python.python/getPythonEnvironmentInfo', 'ms-python.python/getPythonExecutableCommand', 'ms-python.python/installPythonPackage', 'ms-python.python/configurePythonEnvironment', 'ms-toolsai.jupyter/configureNotebook', 'ms-toolsai.jupyter/listNotebookPackages', 'ms-toolsai.jupyter/installNotebookPackages', 'ms-vscode.cpp-devtools/Build_CMakeTools', 'ms-vscode.cpp-devtools/RunCtest_CMakeTools', 'ms-vscode.cpp-devtools/ListBuildTargets_CMakeTools', 'ms-vscode.cpp-devtools/ListTests_CMakeTools']
---

# Sage PyPI Publisher Agent

## Scope
- `src/pypi_publisher/` compiler, CLI, and exception flows.

## Rules
- Keep strong typing and Google-style docstrings.
- Preserve compile policy (`__init__.py` and `_version.py` source retention).
- Use explicit exception types (`CompilationError`, `BuildError`, `UploadError`).
- Keep user output concise and consistent with Rich.

## Workflow
1. Implement minimal coherent change in CLI/compiler.
2. Add tests for success/failure paths.
3. Validate lint/type/tests.
