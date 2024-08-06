# Bifrost2 - The Python SDK for [DCP](https://www.dcp.dev/)

## Build

Install [Poetry](https://python-poetry.org/), then in the root of the project directory run the following:
- `$ poetry install`
- `$ poetry shell`

Verify your installation is correct by running the test suite:
- `$ poetry run pytest`

## Tests

Run tests with:
- `$ poetry run pytest`

## Publishing

We need to upload the tar since we need to run NPM i after installation - this is not possible with the wheel distribution option.
- `$ poetry build -f sdist`
- `$ twine upload dist/dcp-<new-version-here>.tar.gz`

