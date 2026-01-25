# Integration Tests

Integration tests that require a running PostgreSQL database with PostGIS and OSM data.

## Prerequisites

1. PostgreSQL 12+ with PostGIS extension
2. osm2pgsql installed and in PATH
3. Test data loaded (district-of-columbia PBF)

## Running Tests

### Run all integration tests:
```bash
uv run pytest -m integration
```

### Run only output validation tests:
```bash
uv run pytest -m "integration and output"
```

### Run only extra region load tests:
```bash
uv run pytest -m "integration and slow"
```

### Skip integration tests (run only unit tests):
```bash
uv run pytest -m "not integration"
```

## Environment Variables

Tests use these environment variables for database connection:
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD` (default: none, uses ~/.pgpass)
- `POSTGRES_HOST` (default: localhost)

## Test Structure

- `test_output_validation.py`: SQL query output validation (27 queries)
- `test_extra_loads.py`: Extra region data loading tests
- `conftest.py`: Shared fixtures and helper functions

## Markers

- `@pytest.mark.integration`: Requires database
- `@pytest.mark.output`: Tests SQL query output
- `@pytest.mark.slow`: Long-running tests (>30s)
