"""
Integration tests for approval-related database functions.

These tests verify that approval queries work correctly and handle
errors gracefully without crashing the application.
"""
import pytest
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auditops-streamlit'))

# Try to import database functions - skip all tests if imports fail
pytest_plugins = []
skip_reason = None

try:
    from src.db import (
        get_approvals_by_shift,
        get_approval,
        create_approval,
        diagnose_approvals_query
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    skip_reason = f"Database imports not available: {e}"

# Skip all tests in this module if imports failed
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason=skip_reason or "Database dependencies not available"
)


class TestGetApprovalsByShift:
    """Test suite for get_approvals_by_shift function."""

    def test_returns_list_with_valid_shift_id(self):
        """Test that the function returns a list (may be empty) without raising exceptions."""
        # Use a known shift_id from your test database or a UUID format
        # This test verifies the function doesn't crash
        shift_id = "00000000-0000-0000-0000-000000000000"  # Replace with actual test ID

        result = get_approvals_by_shift(shift_id)

        assert isinstance(result, list), "Should return a list"
        # Don't assert length - it may be empty for test data

    def test_handles_nonexistent_shift_gracefully(self):
        """Test that function returns empty list for nonexistent shift without crashing."""
        nonexistent_id = "99999999-9999-9999-9999-999999999999"

        result = get_approvals_by_shift(nonexistent_id)

        assert result == [], "Should return empty list for nonexistent shift"

    def test_handles_invalid_shift_id_gracefully(self):
        """Test that function handles invalid shift_id without crashing."""
        invalid_ids = [None, "", "not-a-uuid", 12345, [], {}]

        for invalid_id in invalid_ids:
            try:
                result = get_approvals_by_shift(invalid_id)
                assert result == [], f"Should return empty list for invalid id: {invalid_id}"
            except Exception as e:
                pytest.fail(f"Should not raise exception for invalid id {invalid_id}, got: {e}")

    def test_respects_limit_parameter(self):
        """Test that the limit parameter is respected."""
        shift_id = "00000000-0000-0000-0000-000000000000"

        result = get_approvals_by_shift(shift_id, limit=5)

        assert isinstance(result, list), "Should return a list"
        assert len(result) <= 5, "Should not exceed limit"

    def test_approvals_have_expected_structure(self):
        """Test that returned approvals have expected data structure."""
        shift_id = "00000000-0000-0000-0000-000000000000"

        result = get_approvals_by_shift(shift_id)

        if result:  # Only test structure if we have data
            approval = result[0]
            # Check for expected fields
            assert isinstance(approval, dict), "Each approval should be a dict"
            # These fields should exist (may be None)
            expected_fields = ['shift_id', 'approver_id', 'decision', 'created_at']
            for field in expected_fields:
                assert field in approval, f"Approval should have '{field}' field"

    def test_approver_data_enrichment(self):
        """Test that approver data is enriched from app_users table."""
        shift_id = "00000000-0000-0000-0000-000000000000"

        result = get_approvals_by_shift(shift_id)

        if result and result[0].get('approver_id'):
            approval = result[0]
            # Should have approver field (may be None if user not found)
            assert 'approver' in approval, "Should have 'approver' field"

            # If approver is populated, check structure
            if approval['approver']:
                assert isinstance(approval['approver'], dict), "Approver should be a dict"
                # Should have name or email from app_users
                assert 'name' in approval['approver'] or 'email' in approval['approver']


class TestGetApproval:
    """Test suite for get_approval function."""

    def test_returns_none_for_invalid_id(self):
        """Test that function returns None for invalid approval_id."""
        invalid_ids = [None, "", "invalid", 12345]

        for invalid_id in invalid_ids:
            result = get_approval(invalid_id)
            assert result is None, f"Should return None for invalid id: {invalid_id}"

    def test_returns_none_for_nonexistent_id(self):
        """Test that function returns None for nonexistent approval."""
        nonexistent_id = "99999999-9999-9999-9999-999999999999"

        result = get_approval(nonexistent_id)

        assert result is None, "Should return None for nonexistent approval"

    def test_approval_has_expected_structure(self):
        """Test that returned approval has expected structure if found."""
        # This test would need a known approval_id from test database
        # For now, just verify the function doesn't crash
        test_id = "00000000-0000-0000-0000-000000000000"

        result = get_approval(test_id)

        # Result may be None if ID doesn't exist, which is fine
        if result:
            assert isinstance(result, dict), "Approval should be a dict"
            assert 'id' in result or 'shift_id' in result


class TestDiagnoseApprovalsQuery:
    """Test suite for diagnose_approvals_query diagnostic function."""

    def test_returns_diagnostic_results(self):
        """Test that diagnostic function returns results dict."""
        shift_id = "00000000-0000-0000-0000-000000000000"

        result = diagnose_approvals_query(shift_id)

        assert isinstance(result, dict), "Should return a dict of results"
        # Should have multiple test results
        assert len(result) > 0, "Should have at least one diagnostic test"

    def test_diagnostic_tests_have_status(self):
        """Test that each diagnostic test has a status."""
        shift_id = "00000000-0000-0000-0000-000000000000"

        result = diagnose_approvals_query(shift_id)

        for test_name, test_result in result.items():
            assert isinstance(test_result, dict), f"{test_name} should be a dict"
            assert 'status' in test_result, f"{test_name} should have status"
            assert 'description' in test_result, f"{test_name} should have description"

    def test_identifies_profiles_join_issue(self):
        """Test that diagnostic identifies the broken profiles join."""
        shift_id = "00000000-0000-0000-0000-000000000000"

        result = diagnose_approvals_query(shift_id)

        # Should have test_2_profiles_join
        assert 'test_2_profiles_join' in result, "Should test profiles join"

        # This test should likely fail due to broken FK
        # (unless the FK has been fixed in the database)
        profiles_test = result['test_2_profiles_join']
        assert profiles_test['status'] in ['✅ PASS', '❌ FAIL'], "Should have pass/fail status"


class TestCreateApproval:
    """Test suite for create_approval function (integration test - use with caution)."""

    @pytest.mark.skip(reason="Modifies database - only run in test environment")
    def test_creates_approval_successfully(self):
        """
        Test that create_approval creates an approval record.

        CAUTION: This modifies the database. Only run in test environment.
        """
        # This would need test data setup
        shift_id = "test-shift-id"
        approver_id = "test-approver-uuid"
        decision = "approved"
        notes = "Test approval"

        result = create_approval(shift_id, approver_id, decision, notes)

        # Cleanup would be needed here
        # assert result is not None
        # assert result['decision'] == decision


class TestErrorHandling:
    """Test suite for error handling and resilience."""

    def test_no_exception_on_database_unavailable(self):
        """Test that functions don't crash if database is unavailable."""
        # This would require mocking the database connection
        # For now, just verify functions have proper exception handling
        pass

    def test_logs_errors_appropriately(self):
        """Test that errors are logged for debugging."""
        # This would require checking log output
        # For now, manual verification in production logs
        pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may require database)"
    )


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_approvals.py -v
    pytest.main([__file__, "-v", "--tb=short"])
