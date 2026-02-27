# Contributing to seeds

Thanks for your interest in contributing to seeds!

## Getting Started

1. Fork the repository
2. Clone your fork and install dependencies:

```bash
uv sync
```

3. Run the test suite to make sure everything works:

```bash
uv run pytest
```

## Development

- Format and lint with ruff: `uv run ruff check . && uv run ruff format .`
- Type check with mypy: `uv run mypy src/`
- Run tests with coverage: `uv run pytest --cov=seeds`

## Submitting Changes

1. Create a branch for your change
2. Make your changes and add tests
3. Ensure all checks pass (`ruff check`, `ruff format --check`, `mypy`, `pytest`)
4. Open a pull request with a clear description of what and why

## Reporting Issues

Issues and feature requests are welcome! Please open a GitHub issue.

## License

By submitting a pull request, you agree that your contribution is licensed under the [MIT License](LICENSE).
