# PgOSM-Flex Tests

Full documentation at [https://pgosm-flex.com/tests.html](https://pgosm-flex.com/tests.html).

## Quick Start

### Unit Tests

Located in `tests/tests/` - Pure Python tests, no external dependencies.

Run with:
```bash
uv run python -m unittest discover tests/tests
```

### Integration Tests

Located in `tests/integration/` - Requires PostgreSQL database with OSM data.

#### Prerequisites
1. PostgreSQL with PostGIS
2. osm2pgsql installed
3. Test database loaded with OSM data

#### Run Integration Tests
```bash
# All integration tests
uv run pytest -m integration

# Only SQL output validation
uv run pytest -m "integration and output"

# Only extra region loads
uv run pytest -m "integration and slow"

# Skip integration tests (unit tests only)
uv run pytest -m "not integration"
```

See `tests/integration/README.md` for detailed integration test documentation.

## Legacy Bash Scripts

The bash scripts `run-output-tests.sh` and `run-extra-loads.sh` have been
converted to pytest (see `tests/integration/`). The bash scripts are kept
for reference but the pytest versions should be used going forward.

