# git-notes-memory-manager - Copilot Instructions

This file provides context to GitHub Copilot for better code suggestions.

## Project Overview

git-notes-memory-manager is a Python project for managing memory and context using git notes.

## Python Guidelines

- Use Python 3.12+ features and syntax
- Type hints are required for all functions and methods
- Use `uv` for package management (NOT pip)
- Follow ruff formatting and linting rules
- Use mypy for static type checking (strict mode preferred)
- Use pytest for testing with high coverage (80% minimum)
- Use bandit for security scanning

## Code Style

- Write clean, readable, maintainable code
- Prefer explicit over implicit
- Keep functions small and focused
- Add comments only when necessary (code should be self-documenting)
- Use descriptive names for variables and functions
- Follow PEP 8 naming conventions:
  - snake_case for functions and variables
  - PascalCase for classes
  - UPPER_CASE for constants

## Project Structure

```
src/
  git_notes_memory_manager/
    __init__.py
    ...
tests/
  __init__.py
  test_*.py
  conftest.py
```

## Testing Patterns

- Write tests for new functionality
- Aim for high test coverage (80% minimum)
- Test edge cases and error conditions
- Use meaningful test names that describe the expected behavior
- Use pytest fixtures for common setup
- Prefer parametrized tests for testing multiple inputs
- Mock external dependencies appropriately

Example test structure:
```python
import pytest
from git_notes_memory_manager import SomeClass

class TestSomeClass:
    def test_method_returns_expected_value(self):
        """Test that method returns expected value for valid input."""
        obj = SomeClass()
        result = obj.method("input")
        assert result == "expected"

    def test_method_raises_on_invalid_input(self):
        """Test that method raises ValueError for invalid input."""
        obj = SomeClass()
        with pytest.raises(ValueError):
            obj.method(None)
```

## Dependencies

- Use `uv add <package>` to add dependencies
- Use `uv add --dev <package>` for dev dependencies
- Keep dependencies minimal and well-justified

## Git Workflow

- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- Keep commits atomic and focused
- Write clear commit messages

## Documentation

- Keep documentation up to date with code changes
- Document public APIs thoroughly with docstrings
- Include examples in documentation when helpful
- Use Google-style docstrings:

```python
def function(arg1: str, arg2: int) -> bool:
    """Short description of function.

    Longer description if needed.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        Description of return value.

    Raises:
        ValueError: Description of when this is raised.
    """
```
