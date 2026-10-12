# .pre-commit

Pre-commit hooks configuration and linting/formatting rules.

## Files

- `.pre-commit-config.yaml` - Hook definitions and versions
- `.yamllint` - YAML linting rules
- `.markdownlint-cli2.jsonc` - Markdown linting rules
- `.secrets.baseline` - Secrets detection baseline

## Setup

```bash
pip install pre-commit
pre-commit install --config .pre-commit/.pre-commit-config.yaml
```

## Run Manually

```bash
pre-commit run --all-files --config .pre-commit/.pre-commit-config.yaml
```

## Hooks Enabled

- End-of-file fixer
- Trailing whitespace
- YAML validation
- Python formatting (black)
- Python linting (ruff)
- Secrets detection
- Shell script linting
- Markdown linting

See `.pre-commit-config.yaml` for versions and configurations.
