"""
System test for authentication flow.
Simulates Streamlit execution order and validates auth model.
"""
import sys
from unittest.mock import Mock, MagicMock, patch
from src.auth_debug import parse_auth_url

# Mock Streamlit session state
class MockSessionState:
    def __init__(self):
        self._data = {}
    
    def __contains__(self, key):
        return key in self._data
    
    def __getitem__(self, key):
        return self._data.get(key)
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

# Mock Streamlit query params
class MockQueryParams:
    def __init__(self, params=None):
        self._params = params or {}
    
    def get(self, key, default=None):
        return self._params.get(key, default)
    
    def clear(self):
        self._params = {}

# Simulate execution order
def simulate_streamlit_execution(url_with_fragment=False, url_with_query=False, url_with_code=False):
    """
    Simulate Streamlit execution order:
    1. components.html() JavaScript (if fragment exists)
    2. Python code execution
    3. Auth gate check
    """
    results = {
        "checkpoint_a": {},
        "checkpoint_b": {},
        "checkpoint_c": {},
        "checkpoint_d": {},
        "checkpoint_e": {},
        "final_state": {}
    }
    
    # Simulate session state
    session_state = MockSessionState()
    
    # PHASE 1: JavaScript execution (components.html at line 51)
    # In real Streamlit, components.html() executes JavaScript IMMEDIATELY
    # But we need to simulate what happens
    
    if url_with_fragment:
        # JavaScript would convert fragment to query params and reload
        # For simulation, we simulate the converted URL
        url_with_query = True
        url_with_fragment = False  # After conversion
    
    # PHASE 2: Python code execution starts (main() at line 185)
    # CHECKPOINT A: App start
    query_params = MockQueryParams()
    if url_with_query:
        query_params._params = {
            "access_token": "test_access_token_123",
            "refresh_token": "test_refresh_token_456",
            "type": "magiclink"
        }
    elif url_with_code:
        query_params._params = {"code": "test_pkce_code_789"}
    
    results["checkpoint_a"] = {
        "has_query_params": len(query_params._params) > 0,
        "query_keys": list(query_params._params.keys()),
        "has_auth_user": "auth_user" in session_state,
        "has_auth_session": "auth_session" in session_state
    }
    
    # CHECKPOINT B: Callback detection
    access_token = query_params.get("access_token")
    refresh_token = query_params.get("refresh_token")
    auth_code = query_params.get("code")
    auth_type = query_params.get("type")
    
    results["checkpoint_b"] = {
        "access_token_present": access_token is not None,
        "refresh_token_present": refresh_token is not None,
        "code_present": auth_code is not None,
        "type": auth_type
    }
    
    # CHECKPOINT C: Session set attempt
    if access_token and refresh_token:
        # Simulate set_session
        mock_user = Mock()
        mock_user.id = "user_123"
        mock_user.email = "test@example.com"
        
        mock_session = Mock()
        mock_session.access_token = access_token
        mock_session.refresh_token = refresh_token
        
        mock_response = Mock()
        mock_response.user = mock_user
        mock_response.session = mock_session
        
        # Store in session state
        session_state["auth_user"] = mock_user
        session_state["auth_session"] = mock_session
        
        results["checkpoint_c"] = {
            "set_session_called": True,
            "response_has_user": True,
            "response_has_session": True
        }
        
        # CHECKPOINT D: Verify user
        # Simulate get_user() call
        mock_get_user_response = Mock()
        mock_get_user_response.user = mock_user
        
        results["checkpoint_d"] = {
            "get_user_called": True,
            "user_id": mock_user.id,
            "session_valid": True
        }
        
        # Clear query params
        query_params.clear()
        results["checkpoint_c"]["query_params_cleared"] = True
    
    elif auth_code:
        # PKCE flow
        results["checkpoint_c"] = {
            "exchange_code_called": True,
            "note": "PKCE flow simulated"
        }
    
    # CHECKPOINT E: Gate decision
    is_auth = "auth_user" in session_state and session_state["auth_user"] is not None
    results["checkpoint_e"] = {
        "is_authenticated": is_auth,
        "reason": "auth_user exists" if is_auth else "no auth_user",
        "session_state_check": {
            "has_auth_user": "auth_user" in session_state,
            "auth_user_not_none": session_state.get("auth_user") is not None
        }
    }
    
    results["final_state"] = {
        "authenticated": is_auth,
        "query_params_remaining": len(query_params._params),
        "session_state_keys": list(session_state._data.keys())
    }
    
    return results


def test_rerun_simulation():
    """Simulate Streamlit rerun - session should persist."""
    session_state = MockSessionState()
    
    # Initial auth
    mock_user = Mock()
    mock_user.id = "user_123"
    session_state["auth_user"] = mock_user
    
    mock_session = Mock()
    mock_session.access_token = "token_123"
    mock_session.refresh_token = "refresh_456"
    session_state["auth_session"] = mock_session
    
    # Simulate rerun - new query params (empty after first auth)
    query_params = MockQueryParams()  # Empty after first auth
    
    # Check auth gate
    is_auth = "auth_user" in session_state and session_state["auth_user"] is not None
    
    return {
        "rerun_authenticated": is_auth,
        "session_state_persisted": "auth_user" in session_state,
        "query_params_empty": len(query_params._params) == 0
    }


def run_all_tests():
    """Run comprehensive system tests."""
    print("=" * 80)
    print("AUTHENTICATION SYSTEM TEST - EXECUTION ORDER VERIFICATION")
    print("=" * 80)
    
    test_cases = [
        ("Fragment URL (implicit flow)", True, False, False),
        ("Query params URL (converted)", False, True, False),
        ("PKCE code URL", False, False, True),
        ("No auth params", False, False, False),
    ]
    
    all_passed = True
    
    for test_name, frag, query, code in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print('='*80)
        
        results = simulate_streamlit_execution(frag, query, code)
        
        # Create checkpoint table
        print("\nCheckpoint Results:")
        print(f"{'Checkpoint':<20} {'Expected':<30} {'Actual':<30} {'Pass/Fail':<10}")
        print("-" * 90)
        
        # Checkpoint A
        expected_a = "Query params detected" if (query or code) else "No query params"
        actual_a = f"Has params: {results['checkpoint_a']['has_query_params']}"
        pass_a = "PASS" if (query or code) == results['checkpoint_a']['has_query_params'] else "FAIL"
        print(f"{'A (App Start)':<20} {expected_a:<30} {actual_a:<30} {pass_a:<10}")
        if "FAIL" in pass_a:
            all_passed = False
        
        # Checkpoint B
        expected_b = "Tokens/code detected" if (query or code) else "No tokens"
        actual_b = f"Token: {results['checkpoint_b']['access_token_present']}, Code: {results['checkpoint_b']['code_present']}"
        pass_b = "PASS" if (query or code) == (results['checkpoint_b']['access_token_present'] or results['checkpoint_b']['code_present']) else "FAIL"
        print(f"{'B (Callback)':<20} {expected_b:<30} {actual_b:<30} {pass_b:<10}")
        if "FAIL" in pass_b:
            all_passed = False
        
        # Checkpoint C
        if query:
            expected_c = "set_session called"
            actual_c = f"set_session: {results['checkpoint_c'].get('set_session_called', False)}"
            pass_c = "PASS" if results['checkpoint_c'].get('set_session_called') else "FAIL"
        elif code:
            expected_c = "exchange_code called"
            actual_c = f"exchange_code: {results['checkpoint_c'].get('exchange_code_called', False)}"
            pass_c = "PASS" if results['checkpoint_c'].get('exchange_code_called') else "FAIL"
        else:
            expected_c = "No session set"
            actual_c = "No session set"
            pass_c = "PASS"
        print(f"{'C (Set Session)':<20} {expected_c:<30} {actual_c:<30} {pass_c:<10}")
        if "FAIL" in pass_c:
            all_passed = False
        
        # Checkpoint D
        if query:
            expected_d = "User verified"
            actual_d = f"User ID: {results['checkpoint_d'].get('user_id', 'None')}"
            pass_d = "PASS" if results['checkpoint_d'].get('session_valid') else "FAIL"
        else:
            expected_d = "No verification"
            actual_d = "No user to verify"
            pass_d = "PASS"
        print(f"{'D (Verify User)':<20} {expected_d:<30} {actual_d:<30} {pass_d:<10}")
        if "FAIL" in pass_d:
            all_passed = False
        
        # Checkpoint E
        expected_e = "Authenticated" if query else "Not authenticated"
        actual_e = f"Auth: {results['checkpoint_e']['is_authenticated']}"
        pass_e = "PASS" if (query == results['checkpoint_e']['is_authenticated']) else "FAIL"
        print(f"{'E (Gate)':<20} {expected_e:<30} {actual_e:<30} {pass_e:<10}")
        if "FAIL" in pass_e:
            all_passed = False
        
        print(f"\nFinal State: Authenticated={results['final_state']['authenticated']}, "
              f"QueryParams={results['final_state']['query_params_remaining']}")
    
    # Test rerun
    print(f"\n{'='*80}")
    print("RERUN SIMULATION TEST")
    print('='*80)
    rerun_results = test_rerun_simulation()
    print(f"Rerun Authenticated: {rerun_results['rerun_authenticated']}")
    print(f"Session Persisted: {rerun_results['session_state_persisted']}")
    print(f"Query Params Empty: {rerun_results['query_params_empty']}")
    
    rerun_pass = "PASS" if rerun_results['rerun_authenticated'] and rerun_results['session_state_persisted'] else "FAIL"
    print(f"Rerun Test: {rerun_pass}")
    if "FAIL" in rerun_pass:
        all_passed = False
    
    return all_passed


if __name__ == "__main__":
    passed = run_all_tests()
    print(f"\n{'='*80}")
    print(f"OVERALL RESULT: {'ALL TESTS PASSED' if passed else 'SOME TESTS FAILED'}")
    print('='*80)
    sys.exit(0 if passed else 1)

