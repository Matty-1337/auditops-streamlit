"""
Authentication debug harness and URL parsing utilities.
Used for debugging callback handling and token extraction.
"""
import re
from urllib.parse import urlparse, parse_qs, parse_qsl
from typing import Dict, Optional


def parse_auth_url(url: str) -> Dict[str, any]:
    """
    Parse authentication URL and extract tokens/code from fragments or query params.
    
    Args:
        url: Full URL string (e.g., from magic link redirect)
    
    Returns:
        dict with keys:
        - has_fragment_tokens: bool
        - has_query_tokens: bool
        - has_code: bool
        - parsed_access_token: str | None
        - parsed_refresh_token: str | None
        - parsed_code: str | None
        - parsed_type: str | None
        - parsed_error: str | None
    """
    result = {
        "has_fragment_tokens": False,
        "has_query_tokens": False,
        "has_code": False,
        "parsed_access_token": None,
        "parsed_refresh_token": None,
        "parsed_code": None,
        "parsed_type": None,
        "parsed_error": None
    }
    
    try:
        parsed = urlparse(url)
        
        # Check query params
        query_params = parse_qs(parsed.query)
        if "access_token" in query_params:
            result["has_query_tokens"] = True
            result["parsed_access_token"] = query_params["access_token"][0]
        if "refresh_token" in query_params:
            result["parsed_refresh_token"] = query_params["refresh_token"][0]
        if "code" in query_params:
            result["has_code"] = True
            result["parsed_code"] = query_params["code"][0]
        if "type" in query_params:
            result["parsed_type"] = query_params["type"][0]
        if "error" in query_params:
            result["parsed_error"] = query_params["error"][0]
        
        # Check fragment (hash)
        if parsed.fragment:
            # Parse fragment as if it were query params
            fragment_params = parse_qs(parsed.fragment)
            if "access_token" in fragment_params:
                result["has_fragment_tokens"] = True
                if not result["parsed_access_token"]:  # Prefer query over fragment
                    result["parsed_access_token"] = fragment_params["access_token"][0]
            if "refresh_token" in fragment_params:
                if not result["parsed_refresh_token"]:
                    result["parsed_refresh_token"] = fragment_params["refresh_token"][0]
            if "code" in fragment_params:
                result["has_code"] = True
                if not result["parsed_code"]:
                    result["parsed_code"] = fragment_params["code"][0]
            if "type" in fragment_params:
                if not result["parsed_type"]:
                    result["parsed_type"] = fragment_params["type"][0]
            if "error" in fragment_params:
                if not result["parsed_error"]:
                    result["parsed_error"] = fragment_params["error"][0]
    
    except Exception as e:
        result["parsed_error"] = f"Parse error: {str(e)}"
    
    return result


def redact_token(token: Optional[str], show_length: bool = True) -> str:
    """
    Redact token for safe logging (first 4 + last 4 chars only).
    
    Args:
        token: Token string to redact
        show_length: If True, include token length
    
    Returns:
        Redacted token string (e.g., "abcd...wxyz (128 chars)")
    """
    if not token:
        return "None"
    
    if len(token) <= 8:
        return "***"  # Too short to show anything
    
    redacted = f"{token[:4]}...{token[-4:]}"
    if show_length:
        redacted += f" ({len(token)} chars)"
    
    return redacted


def test_url_parsing():
    """Test URL parsing with various formats."""
    test_cases = [
        # Query params (converted from fragment)
        "https://app.streamlit.app?access_token=abc123&refresh_token=xyz789&type=magiclink",
        
        # Fragment (original Supabase format)
        "https://app.streamlit.app#access_token=abc123&refresh_token=xyz789&type=magiclink",
        
        # PKCE code
        "https://app.streamlit.app?code=abc123def456",
        
        # Recovery type
        "https://app.streamlit.app#access_token=abc123&refresh_token=xyz789&type=recovery",
        
        # Error case
        "https://app.streamlit.app?error=access_denied&error_description=Invalid+token",
        
        # Mixed (should prefer query)
        "https://app.streamlit.app?access_token=query_token#access_token=fragment_token",
    ]
    
    print("=" * 80)
    print("URL PARSING TEST HARNESS")
    print("=" * 80)
    
    for i, url in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"URL: {url}")
        result = parse_auth_url(url)
        print(f"  Fragment tokens: {result['has_fragment_tokens']}")
        print(f"  Query tokens: {result['has_query_tokens']}")
        print(f"  Has code: {result['has_code']}")
        print(f"  Access token: {redact_token(result['parsed_access_token'])}")
        print(f"  Refresh token: {redact_token(result['parsed_refresh_token'])}")
        print(f"  Code: {redact_token(result['parsed_code'])}")
        print(f"  Type: {result['parsed_type']}")
        if result['parsed_error']:
            print(f"  Error: {result['parsed_error']}")


def test_pkce_flow():
    """Test PKCE code flow detection and handling."""
    print("\n" + "=" * 80)
    print("PKCE FLOW TEST")
    print("=" * 80)
    
    test_urls = [
        # PKCE code in query params
        "https://app.streamlit.app?code=abc123def456",
        
        # PKCE code in fragment
        "https://app.streamlit.app#code=abc123def456",
        
        # PKCE code with auth_pending
        "https://app.streamlit.app?auth_pending=1&code=abc123def456",
        
        # Error in PKCE flow
        "https://app.streamlit.app?code=invalid&error=invalid_code",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTest Case {i}: {url}")
        result = parse_auth_url(url)
        print(f"  Has code: {result['has_code']}")
        print(f"  Code: {redact_token(result['parsed_code'])}")
        print(f"  Has error: {result['parsed_error'] is not None}")
        if result['parsed_error']:
            print(f"  Error: {result['parsed_error']}")
    
    print("\n" + "=" * 80)
    print("PKCE FLOW TEST COMPLETE")
    print("=" * 80)
    print("\nNote: PKCE code exchange requires:")
    print("  1. Authorization code from Supabase")
    print("  2. Code verifier (if PKCE flow was initiated with verifier)")
    print("  3. Direct HTTP call to /auth/v1/token endpoint if supabase-py doesn't support it")


if __name__ == "__main__":
    test_url_parsing()
    test_pkce_flow()

