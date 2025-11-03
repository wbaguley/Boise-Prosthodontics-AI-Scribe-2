# Testing Guide for AI Scribe Backend

## Overview

This directory contains comprehensive pytest test suites for the AI Scribe backend, covering:
- Export/Import functionality (PDF, DOCX, CSV, ZIP)
- Tenant configuration and multi-tenant white-label system
- Database CRUD operations
- API key encryption
- API endpoints

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── test_export_service.py   # Export functionality tests
├── test_import_service.py   # Import functionality tests
├── test_tenant_config.py    # Multi-tenant configuration tests
└── test_database.py         # Database and encryption tests
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test export functionality
pytest tests/test_export_service.py

# Test import functionality
pytest tests/test_import_service.py

# Test tenant configuration
pytest tests/test_tenant_config.py

# Test database operations
pytest tests/test_database.py
```

### Run Specific Test Functions

```bash
# Run a single test
pytest tests/test_export_service.py::TestExportService::test_export_session_to_pdf_success

# Run all tests in a class
pytest tests/test_export_service.py::TestExportService

# Run tests matching a pattern
pytest -k "pdf"  # Runs all tests with 'pdf' in the name
```

## Coverage Reports

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=. --cov-report=html

# View HTML coverage report
# Open htmlcov/index.html in browser
```

### Coverage Targets

- **Overall Coverage Goal**: 80%+
- **Critical Modules**: 90%+
  - database.py
  - export_service.py
  - import_service.py
  - tenant_config.py

## Test Types

### Unit Tests (`@pytest.mark.unit`)
- Test individual functions and classes in isolation
- Use mocks for external dependencies
- Fast execution (< 1 second each)

### Integration Tests (`@pytest.mark.integration`)
- Test API endpoints with real database
- Test component interactions
- May take longer to execute

### Performance Tests (`@pytest.mark.performance`)
- Verify operations complete within 2 seconds
- Test with realistic data volumes (100+ records)
- Use `performance_timer` fixture

## Writing New Tests

### Test Template

```python
import pytest
from your_module import YourClass

class TestYourFeature:
    """Test cases for YourFeature."""
    
    @pytest.fixture
    def your_fixture(self):
        """Create test data or mock objects."""
        return YourClass()
    
    @pytest.mark.unit
    def test_feature_success(self, your_fixture):
        """Test successful operation."""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = your_fixture.do_something(input_data)
        
        # Assert
        assert result is not None
        assert result["status"] == "success"
    
    @pytest.mark.unit
    def test_feature_with_invalid_input(self, your_fixture):
        """Test error handling."""
        # Arrange
        invalid_data = None
        
        # Act & Assert
        with pytest.raises(ValueError):
            your_fixture.do_something(invalid_data)
    
    @pytest.mark.performance
    def test_feature_performance(self, your_fixture, performance_timer):
        """Test performance requirements."""
        # Act
        performance_timer.start()
        result = your_fixture.do_something(large_dataset)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0
```

## Available Fixtures

### Database Fixtures
- `test_db`: Temporary SQLite database for each test
- `client`: FastAPI TestClient with database override

### Mock Data Fixtures
- `mock_provider_data`: Sample provider data
- `mock_session_data`: Sample session data
- `mock_tenant_data`: Sample tenant data
- `mock_tenant_config`: Sample tenant configuration
- `mock_voice_profile`: Mock voice profile data

### Mock Service Fixtures
- `mock_whisper_model`: Mocked Whisper transcription model
- `mock_llm_client`: Mocked LLM client
- `mock_dentrix_client`: Mocked Dentrix client
- `mock_encryption_manager`: Mocked encryption manager

### File System Fixtures
- `temp_audio_file`: Temporary WAV file
- `temp_export_dir`: Temporary directory for exports
- `mock_csv_file`: Sample CSV file
- `mock_json_template`: Sample JSON template

### Utility Fixtures
- `performance_timer`: Timer for performance testing
- `event_loop`: Event loop for async tests

## Continuous Integration

### GitHub Actions Example

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest
      - uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

## Troubleshooting

### Tests Fail to Import Modules

```bash
# Make sure you're in the Backend directory
cd Backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

### Database Locked Errors

```bash
# Clean up any existing test databases
rm -f test_*.db

# Run tests again
pytest
```

### Performance Tests Failing

- Performance tests may fail on slower systems
- Adjust thresholds in individual tests if needed
- Use `-m "not performance"` to skip performance tests

## Best Practices

1. **AAA Pattern**: Arrange, Act, Assert
2. **One assertion per test** (when possible)
3. **Descriptive test names**: `test_feature_with_condition_expects_result`
4. **Use fixtures** for common setup
5. **Mock external dependencies** (API calls, file I/O)
6. **Clean up after tests** (temp files, database records)
7. **Test edge cases** (empty data, invalid input, boundary conditions)
8. **Test error handling** (exceptions, validation errors)
9. **Document complex tests** with docstrings

## Code Coverage Goals

| Module | Target Coverage | Critical Functions |
|--------|----------------|-------------------|
| export_service.py | 90%+ | All export methods |
| import_service.py | 90%+ | All import methods |
| tenant_config.py | 85%+ | CRUD operations |
| database.py | 95%+ | All CRUD operations |
| main.py | 70%+ | All API endpoints |

## Performance Benchmarks

| Operation | Target Time | Test Load |
|-----------|-------------|-----------|
| PDF Export | < 2s | Single session |
| DOCX Export | < 2s | Single session |
| CSV Export | < 2s | 100 sessions |
| Voice Profile Import | < 2s | 20 samples |
| Provider CSV Import | < 2s | 100 providers |
| Database Query | < 0.1s | Single record |
| Encryption/Decryption | < 0.02s | 100 operations |

## Support

For questions or issues:
1. Check existing tests for examples
2. Review fixture documentation in `conftest.py`
3. Consult pytest documentation: https://docs.pytest.org/
