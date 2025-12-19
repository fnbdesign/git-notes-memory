"""Tests for git_notes_memory.exceptions module.

Tests all exception classes, error categories, and pre-defined error instances.
"""

from __future__ import annotations

import pytest

from git_notes_memory.exceptions import (
    # Pre-defined Errors
    CONTENT_TOO_LARGE_ERROR,
    INDEX_LOCKED_ERROR,
    INVALID_GIT_REF_ERROR,
    INVALID_NAMESPACE_ERROR,
    INVALID_YAML_ERROR,
    LOCK_TIMEOUT_ERROR,
    MISSING_FIELD_ERROR,
    MODEL_CORRUPTED_ERROR,
    MODEL_OOM_ERROR,
    NO_COMMITS_ERROR,
    PATH_TRAVERSAL_ERROR,
    PERMISSION_DENIED_ERROR,
    SQLITE_VEC_MISSING_ERROR,
    # Exception Classes
    CaptureError,
    EmbeddingError,
    # Error Categories
    ErrorCategory,
    MemoryError,
    MemoryIndexError,
    ParseError,
    RecallError,
    StorageError,
    ValidationError,
)

# =============================================================================
# ErrorCategory Tests
# =============================================================================


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_category_count(self) -> None:
        """Test that exactly 7 categories are defined."""
        assert len(ErrorCategory) == 7

    def test_category_values(self) -> None:
        """Test all expected category values exist."""
        expected = {
            "storage",
            "index",
            "embedding",
            "parse",
            "capture",
            "recall",
            "validation",
        }
        actual = {cat.value for cat in ErrorCategory}
        assert actual == expected

    def test_storage_category(self) -> None:
        """Test STORAGE category."""
        assert ErrorCategory.STORAGE.value == "storage"

    def test_index_category(self) -> None:
        """Test INDEX category."""
        assert ErrorCategory.INDEX.value == "index"

    def test_embedding_category(self) -> None:
        """Test EMBEDDING category."""
        assert ErrorCategory.EMBEDDING.value == "embedding"

    def test_parse_category(self) -> None:
        """Test PARSE category."""
        assert ErrorCategory.PARSE.value == "parse"

    def test_capture_category(self) -> None:
        """Test CAPTURE category."""
        assert ErrorCategory.CAPTURE.value == "capture"

    def test_recall_category(self) -> None:
        """Test RECALL category."""
        assert ErrorCategory.RECALL.value == "recall"

    def test_validation_category(self) -> None:
        """Test VALIDATION category."""
        assert ErrorCategory.VALIDATION.value == "validation"


# =============================================================================
# Base MemoryError Tests
# =============================================================================


class TestMemoryError:
    """Tests for base MemoryError exception."""

    def test_memory_error_creation(self) -> None:
        """Test MemoryError can be created with all attributes."""
        err = MemoryError(
            category=ErrorCategory.STORAGE,
            message="Test error message",
            recovery_action="Try again",
        )
        assert err.category == ErrorCategory.STORAGE
        assert err.message == "Test error message"
        assert err.recovery_action == "Try again"

    def test_memory_error_inherits_exception(self) -> None:
        """Test MemoryError inherits from Exception."""
        err = MemoryError(ErrorCategory.STORAGE, "msg", "action")
        assert isinstance(err, Exception)

    def test_memory_error_str_format(self) -> None:
        """Test MemoryError __str__ format."""
        err = MemoryError(
            category=ErrorCategory.INDEX,
            message="Database locked",
            recovery_action="Wait and retry",
        )
        expected = "[index] Database locked\n-> Wait and retry"
        assert str(err) == expected

    def test_memory_error_exception_message(self) -> None:
        """Test that the exception message is set correctly."""
        err = MemoryError(ErrorCategory.PARSE, "Parse failed", "Fix syntax")
        # The parent Exception stores message as args[0]
        assert err.args[0] == "Parse failed"

    def test_memory_error_can_be_raised(self) -> None:
        """Test MemoryError can be raised and caught."""
        with pytest.raises(MemoryError) as exc_info:
            raise MemoryError(ErrorCategory.CAPTURE, "Capture failed", "Retry")
        assert exc_info.value.category == ErrorCategory.CAPTURE
        assert exc_info.value.message == "Capture failed"

    def test_memory_error_can_be_caught_as_exception(self) -> None:
        """Test MemoryError can be caught as generic Exception."""
        with pytest.raises(Exception):
            raise MemoryError(ErrorCategory.STORAGE, "msg", "action")


# =============================================================================
# Specific Exception Class Tests
# =============================================================================


class TestStorageError:
    """Tests for StorageError exception."""

    def test_storage_error_creation(self) -> None:
        """Test StorageError can be created."""
        err = StorageError("Git operation failed", "Check permissions")
        assert err.message == "Git operation failed"
        assert err.recovery_action == "Check permissions"

    def test_storage_error_category(self) -> None:
        """Test StorageError has STORAGE category."""
        err = StorageError("msg", "action")
        assert err.category == ErrorCategory.STORAGE

    def test_storage_error_inherits_memory_error(self) -> None:
        """Test StorageError inherits from MemoryError."""
        err = StorageError("msg", "action")
        assert isinstance(err, MemoryError)
        assert isinstance(err, Exception)

    def test_storage_error_str_format(self) -> None:
        """Test StorageError __str__ uses storage category."""
        err = StorageError("Cannot write", "Check access")
        assert str(err).startswith("[storage]")


class TestMemoryIndexError:
    """Tests for MemoryIndexError exception."""

    def test_memory_index_error_creation(self) -> None:
        """Test MemoryIndexError can be created."""
        err = MemoryIndexError("Index corrupted", "Rebuild index")
        assert err.message == "Index corrupted"
        assert err.recovery_action == "Rebuild index"

    def test_memory_index_error_category(self) -> None:
        """Test MemoryIndexError has INDEX category."""
        err = MemoryIndexError("msg", "action")
        assert err.category == ErrorCategory.INDEX

    def test_memory_index_error_inherits_memory_error(self) -> None:
        """Test MemoryIndexError inherits from MemoryError."""
        err = MemoryIndexError("msg", "action")
        assert isinstance(err, MemoryError)

    def test_memory_index_error_not_builtin_index_error(self) -> None:
        """Test MemoryIndexError is NOT the builtin IndexError."""
        err = MemoryIndexError("msg", "action")
        assert not isinstance(err, IndexError)  # Python builtin


class TestEmbeddingError:
    """Tests for EmbeddingError exception."""

    def test_embedding_error_creation(self) -> None:
        """Test EmbeddingError can be created."""
        err = EmbeddingError("Model load failed", "Reinstall model")
        assert err.message == "Model load failed"
        assert err.recovery_action == "Reinstall model"

    def test_embedding_error_category(self) -> None:
        """Test EmbeddingError has EMBEDDING category."""
        err = EmbeddingError("msg", "action")
        assert err.category == ErrorCategory.EMBEDDING

    def test_embedding_error_inherits_memory_error(self) -> None:
        """Test EmbeddingError inherits from MemoryError."""
        err = EmbeddingError("msg", "action")
        assert isinstance(err, MemoryError)


class TestParseError:
    """Tests for ParseError exception."""

    def test_parse_error_creation(self) -> None:
        """Test ParseError can be created."""
        err = ParseError("Invalid YAML", "Fix syntax")
        assert err.message == "Invalid YAML"
        assert err.recovery_action == "Fix syntax"

    def test_parse_error_category(self) -> None:
        """Test ParseError has PARSE category."""
        err = ParseError("msg", "action")
        assert err.category == ErrorCategory.PARSE

    def test_parse_error_inherits_memory_error(self) -> None:
        """Test ParseError inherits from MemoryError."""
        err = ParseError("msg", "action")
        assert isinstance(err, MemoryError)


class TestCaptureError:
    """Tests for CaptureError exception."""

    def test_capture_error_creation(self) -> None:
        """Test CaptureError can be created."""
        err = CaptureError("Lock timeout", "Wait and retry")
        assert err.message == "Lock timeout"
        assert err.recovery_action == "Wait and retry"

    def test_capture_error_category(self) -> None:
        """Test CaptureError has CAPTURE category."""
        err = CaptureError("msg", "action")
        assert err.category == ErrorCategory.CAPTURE

    def test_capture_error_inherits_memory_error(self) -> None:
        """Test CaptureError inherits from MemoryError."""
        err = CaptureError("msg", "action")
        assert isinstance(err, MemoryError)


class TestRecallError:
    """Tests for RecallError exception."""

    def test_recall_error_creation(self) -> None:
        """Test RecallError can be created."""
        err = RecallError("Search failed", "Reindex and retry")
        assert err.message == "Search failed"
        assert err.recovery_action == "Reindex and retry"

    def test_recall_error_category(self) -> None:
        """Test RecallError has RECALL category."""
        err = RecallError("msg", "action")
        assert err.category == ErrorCategory.RECALL

    def test_recall_error_inherits_memory_error(self) -> None:
        """Test RecallError inherits from MemoryError."""
        err = RecallError("msg", "action")
        assert isinstance(err, MemoryError)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_creation(self) -> None:
        """Test ValidationError can be created."""
        err = ValidationError("Invalid input", "Check format")
        assert err.message == "Invalid input"
        assert err.recovery_action == "Check format"

    def test_validation_error_category(self) -> None:
        """Test ValidationError has VALIDATION category."""
        err = ValidationError("msg", "action")
        assert err.category == ErrorCategory.VALIDATION

    def test_validation_error_inherits_memory_error(self) -> None:
        """Test ValidationError inherits from MemoryError."""
        err = ValidationError("msg", "action")
        assert isinstance(err, MemoryError)


# =============================================================================
# Pre-defined Storage Errors Tests
# =============================================================================


class TestPredefinedStorageErrors:
    """Tests for pre-defined StorageError instances."""

    def test_no_commits_error_type(self) -> None:
        """Test NO_COMMITS_ERROR is a StorageError."""
        assert isinstance(NO_COMMITS_ERROR, StorageError)

    def test_no_commits_error_message(self) -> None:
        """Test NO_COMMITS_ERROR message content."""
        assert "no commits" in NO_COMMITS_ERROR.message.lower()

    def test_no_commits_error_recovery(self) -> None:
        """Test NO_COMMITS_ERROR recovery action."""
        assert "commit" in NO_COMMITS_ERROR.recovery_action.lower()

    def test_permission_denied_error_type(self) -> None:
        """Test PERMISSION_DENIED_ERROR is a StorageError."""
        assert isinstance(PERMISSION_DENIED_ERROR, StorageError)

    def test_permission_denied_error_message(self) -> None:
        """Test PERMISSION_DENIED_ERROR message content."""
        assert "permission" in PERMISSION_DENIED_ERROR.message.lower()


# =============================================================================
# Pre-defined Index Errors Tests
# =============================================================================


class TestPredefinedIndexErrors:
    """Tests for pre-defined MemoryIndexError instances."""

    def test_index_locked_error_type(self) -> None:
        """Test INDEX_LOCKED_ERROR is a MemoryIndexError."""
        assert isinstance(INDEX_LOCKED_ERROR, MemoryIndexError)

    def test_index_locked_error_message(self) -> None:
        """Test INDEX_LOCKED_ERROR message content."""
        assert "locked" in INDEX_LOCKED_ERROR.message.lower()

    def test_index_locked_error_recovery(self) -> None:
        """Test INDEX_LOCKED_ERROR recovery action."""
        assert "wait" in INDEX_LOCKED_ERROR.recovery_action.lower()

    def test_sqlite_vec_missing_error_type(self) -> None:
        """Test SQLITE_VEC_MISSING_ERROR is a MemoryIndexError."""
        assert isinstance(SQLITE_VEC_MISSING_ERROR, MemoryIndexError)

    def test_sqlite_vec_missing_error_message(self) -> None:
        """Test SQLITE_VEC_MISSING_ERROR message content."""
        assert "sqlite-vec" in SQLITE_VEC_MISSING_ERROR.message.lower()

    def test_sqlite_vec_missing_error_recovery(self) -> None:
        """Test SQLITE_VEC_MISSING_ERROR recovery action."""
        assert "pip install" in SQLITE_VEC_MISSING_ERROR.recovery_action.lower()


# =============================================================================
# Pre-defined Embedding Errors Tests
# =============================================================================


class TestPredefinedEmbeddingErrors:
    """Tests for pre-defined EmbeddingError instances."""

    def test_model_oom_error_type(self) -> None:
        """Test MODEL_OOM_ERROR is an EmbeddingError."""
        assert isinstance(MODEL_OOM_ERROR, EmbeddingError)

    def test_model_oom_error_message(self) -> None:
        """Test MODEL_OOM_ERROR message content."""
        assert "memory" in MODEL_OOM_ERROR.message.lower()

    def test_model_corrupted_error_type(self) -> None:
        """Test MODEL_CORRUPTED_ERROR is an EmbeddingError."""
        assert isinstance(MODEL_CORRUPTED_ERROR, EmbeddingError)

    def test_model_corrupted_error_message(self) -> None:
        """Test MODEL_CORRUPTED_ERROR message content."""
        assert "corrupted" in MODEL_CORRUPTED_ERROR.message.lower()

    def test_model_corrupted_error_recovery(self) -> None:
        """Test MODEL_CORRUPTED_ERROR recovery action."""
        assert "delete" in MODEL_CORRUPTED_ERROR.recovery_action.lower()


# =============================================================================
# Pre-defined Parse Errors Tests
# =============================================================================


class TestPredefinedParseErrors:
    """Tests for pre-defined ParseError instances."""

    def test_invalid_yaml_error_type(self) -> None:
        """Test INVALID_YAML_ERROR is a ParseError."""
        assert isinstance(INVALID_YAML_ERROR, ParseError)

    def test_invalid_yaml_error_message(self) -> None:
        """Test INVALID_YAML_ERROR message content."""
        assert "yaml" in INVALID_YAML_ERROR.message.lower()

    def test_missing_field_error_type(self) -> None:
        """Test MISSING_FIELD_ERROR is a ParseError."""
        assert isinstance(MISSING_FIELD_ERROR, ParseError)

    def test_missing_field_error_message(self) -> None:
        """Test MISSING_FIELD_ERROR message content."""
        assert "missing" in MISSING_FIELD_ERROR.message.lower()

    def test_missing_field_error_recovery(self) -> None:
        """Test MISSING_FIELD_ERROR recovery action."""
        # Should mention required fields
        assert "type" in MISSING_FIELD_ERROR.recovery_action.lower()
        assert "spec" in MISSING_FIELD_ERROR.recovery_action.lower()


# =============================================================================
# Pre-defined Capture Errors Tests
# =============================================================================


class TestPredefinedCaptureErrors:
    """Tests for pre-defined CaptureError instances."""

    def test_lock_timeout_error_type(self) -> None:
        """Test LOCK_TIMEOUT_ERROR is a CaptureError."""
        assert isinstance(LOCK_TIMEOUT_ERROR, CaptureError)

    def test_lock_timeout_error_message(self) -> None:
        """Test LOCK_TIMEOUT_ERROR message content."""
        assert "capture" in LOCK_TIMEOUT_ERROR.message.lower()

    def test_lock_timeout_error_recovery(self) -> None:
        """Test LOCK_TIMEOUT_ERROR recovery action."""
        assert "retry" in LOCK_TIMEOUT_ERROR.recovery_action.lower()


# =============================================================================
# Pre-defined Validation Errors Tests
# =============================================================================


class TestPredefinedValidationErrors:
    """Tests for pre-defined ValidationError instances."""

    def test_invalid_namespace_error_type(self) -> None:
        """Test INVALID_NAMESPACE_ERROR is a ValidationError."""
        assert isinstance(INVALID_NAMESPACE_ERROR, ValidationError)

    def test_invalid_namespace_error_message(self) -> None:
        """Test INVALID_NAMESPACE_ERROR message content."""
        assert "namespace" in INVALID_NAMESPACE_ERROR.message.lower()

    def test_invalid_namespace_error_recovery_lists_namespaces(self) -> None:
        """Test INVALID_NAMESPACE_ERROR recovery lists valid namespaces."""
        recovery = INVALID_NAMESPACE_ERROR.recovery_action.lower()
        assert "inception" in recovery
        assert "decisions" in recovery
        assert "learnings" in recovery

    def test_content_too_large_error_type(self) -> None:
        """Test CONTENT_TOO_LARGE_ERROR is a ValidationError."""
        assert isinstance(CONTENT_TOO_LARGE_ERROR, ValidationError)

    def test_content_too_large_error_message(self) -> None:
        """Test CONTENT_TOO_LARGE_ERROR message content."""
        assert "100kb" in CONTENT_TOO_LARGE_ERROR.message.lower()

    def test_invalid_git_ref_error_type(self) -> None:
        """Test INVALID_GIT_REF_ERROR is a ValidationError."""
        assert isinstance(INVALID_GIT_REF_ERROR, ValidationError)

    def test_invalid_git_ref_error_message(self) -> None:
        """Test INVALID_GIT_REF_ERROR message content."""
        assert "git" in INVALID_GIT_REF_ERROR.message.lower()

    def test_path_traversal_error_type(self) -> None:
        """Test PATH_TRAVERSAL_ERROR is a ValidationError."""
        assert isinstance(PATH_TRAVERSAL_ERROR, ValidationError)

    def test_path_traversal_error_message(self) -> None:
        """Test PATH_TRAVERSAL_ERROR message content."""
        assert "traversal" in PATH_TRAVERSAL_ERROR.message.lower()


# =============================================================================
# Module Export Tests
# =============================================================================


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_exist(self) -> None:
        """Test all items in __all__ are actually defined."""
        from git_notes_memory import exceptions

        for name in exceptions.__all__:
            assert hasattr(exceptions, name), f"'{name}' in __all__ but not defined"

    def test_error_category_exported(self) -> None:
        """Test ErrorCategory is exported."""
        from git_notes_memory import exceptions

        assert "ErrorCategory" in exceptions.__all__

    def test_all_exception_classes_exported(self) -> None:
        """Test all exception classes are exported."""
        from git_notes_memory import exceptions

        expected_classes = [
            "MemoryError",
            "StorageError",
            "MemoryIndexError",
            "EmbeddingError",
            "ParseError",
            "CaptureError",
            "ValidationError",
        ]
        for cls_name in expected_classes:
            assert cls_name in exceptions.__all__

    def test_all_predefined_errors_exported(self) -> None:
        """Test all pre-defined errors are exported."""
        from git_notes_memory import exceptions

        expected_errors = [
            "NO_COMMITS_ERROR",
            "PERMISSION_DENIED_ERROR",
            "INDEX_LOCKED_ERROR",
            "SQLITE_VEC_MISSING_ERROR",
            "MODEL_OOM_ERROR",
            "MODEL_CORRUPTED_ERROR",
            "INVALID_YAML_ERROR",
            "MISSING_FIELD_ERROR",
            "LOCK_TIMEOUT_ERROR",
            "INVALID_NAMESPACE_ERROR",
            "CONTENT_TOO_LARGE_ERROR",
            "INVALID_GIT_REF_ERROR",
            "PATH_TRAVERSAL_ERROR",
        ]
        for err_name in expected_errors:
            assert err_name in exceptions.__all__


# =============================================================================
# Inheritance Hierarchy Tests
# =============================================================================


class TestInheritanceHierarchy:
    """Tests for proper exception inheritance hierarchy."""

    def test_all_specific_errors_inherit_memory_error(self) -> None:
        """Test all specific exception classes inherit from MemoryError."""
        error_classes = [
            StorageError,
            MemoryIndexError,
            EmbeddingError,
            ParseError,
            CaptureError,
            ValidationError,
        ]
        for cls in error_classes:
            assert issubclass(cls, MemoryError), (
                f"{cls.__name__} should inherit MemoryError"
            )

    def test_memory_error_inherits_exception(self) -> None:
        """Test MemoryError inherits from Exception."""
        assert issubclass(MemoryError, Exception)

    def test_can_catch_all_as_memory_error(self) -> None:
        """Test all specific errors can be caught as MemoryError."""
        errors = [
            StorageError("msg", "action"),
            MemoryIndexError("msg", "action"),
            EmbeddingError("msg", "action"),
            ParseError("msg", "action"),
            CaptureError("msg", "action"),
            ValidationError("msg", "action"),
        ]
        for err in errors:
            try:
                raise err
            except MemoryError as caught:
                assert caught is err
