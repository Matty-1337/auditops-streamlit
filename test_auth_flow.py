"""
Manual test script to verify authentication flow.
Run with: python test_auth_flow.py
"""
from src.auth_debug import parse_auth_url, redact_token

def test_flow():
    """Test URL parsing for various auth scenarios."""
    print("=" * 80)
    print("AUTHENTICATION FLOW TEST HARNESS")
    print("=" * 80)
    
    test_urls = [
        # Query params (converted from fragment)
        "https://auditops.streamlit.app?access_token=abc123xyz&refresh_token=def456uvw&type=magiclink",
        
        # Fragment (original Supabase format)
        "https://auditops.streamlit.app#access_token=abc123xyz&refresh_token=def456uvw&type=magiclink",
        
        # PKCE code
        "https://auditops.streamlit.app?code=abc123def456",
        
        # Recovery type
        "https://auditops.streamlit.app#access_token=abc123xyz&refresh_token=def456uvw&type=recovery",
        
        # Error case
        "https://auditops.streamlit.app?error=access_denied",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {url}")
        print('='*80)
        result = parse_auth_url(url)
        
        print(f"Fragment tokens: {result['has_fragment_tokens']}")
        print(f"Query tokens: {result['has_query_tokens']}")
        print(f"Has code: {result['has_code']}")
        print(f"Access token: {redact_token(result['parsed_access_token'])}")
        print(f"Refresh token: {redact_token(result['parsed_refresh_token'])}")
        print(f"Code: {redact_token(result['parsed_code'])}")
        print(f"Type: {result['parsed_type']}")
        if result['parsed_error']:
            print(f"Error: {result['parsed_error']}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nExpected behavior:")
    print("1. Fragment URLs should be converted to query params by JavaScript")
    print("2. Query param URLs should be parsed correctly by Python")
    print("3. Tokens should be extracted and passed to authenticate_with_tokens()")
    print("4. Session should be set and verified before clearing query params")

if __name__ == "__main__":
    test_flow()

