"""
Authentication instrumentation and checkpoint logging.
Safe logging that never exposes full tokens.
"""
import os
import logging
import streamlit as st
from typing import Optional, Dict, Any
from src.auth_debug import redact_token, parse_auth_url

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("AUTH_DEBUG") == "1" else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auth_instrumentation")

# Debug mode flag
AUTH_DEBUG = os.getenv("AUTH_DEBUG") == "1"


def log_checkpoint(checkpoint: str, data: Dict[str, Any] = None, error: Exception = None):
    """
    Log checkpoint with safe token redaction.
    
    Args:
        checkpoint: Checkpoint name (A, B, C, D, E)
        data: Optional data dict (tokens will be redacted)
        error: Optional exception
    """
    if not AUTH_DEBUG and not error:
        return  # Only log errors in production
    
    msg = f"[CHECKPOINT {checkpoint}]"
    
    if data:
        safe_data = {}
        for key, value in data.items():
            if "token" in key.lower() and isinstance(value, str):
                safe_data[key] = redact_token(value)
            elif isinstance(value, dict) and "token" in str(key).lower():
                safe_data[key] = {k: redact_token(v) if isinstance(v, str) else v 
                                 for k, v in value.items()}
            else:
                safe_data[key] = value
        msg += f" {safe_data}"
    
    if error:
        msg += f" ERROR: {str(error)}"
        logger.error(msg, exc_info=error)
    else:
        logger.debug(msg)


def checkpoint_a_app_start():
    """CHECKPOINT A: App start - dump request/query context."""
    query_params = st.query_params
    url_info = {
        "has_query_params": len(query_params) > 0,
        "query_keys": list(query_params.keys()) if query_params else [],
        "has_access_token": "access_token" in query_params,
        "has_refresh_token": "refresh_token" in query_params,
        "has_code": "code" in query_params,
        "has_type": "type" in query_params,
    }
    
    # Check session state
    session_info = {
        "has_auth_user": "auth_user" in st.session_state,
        "has_auth_session": "auth_session" in st.session_state,
        "has_user_profile": "user_profile" in st.session_state,
    }
    
    if st.session_state.get("auth_user"):
        session_info["user_id"] = getattr(st.session_state.auth_user, "id", None)
        session_info["user_email"] = getattr(st.session_state.auth_user, "email", None)
    
    log_checkpoint("A", {
        "url_info": url_info,
        "session_info": session_info
    })
    
    if AUTH_DEBUG:
        with st.expander("🔍 Auth Debug: Checkpoint A (App Start)", expanded=False):
            st.json({"url_info": url_info, "session_info": session_info})


def checkpoint_b_callback_detected(access_token: Optional[str], refresh_token: Optional[str], 
                                   auth_code: Optional[str], auth_type: Optional[str]):
    """CHECKPOINT B: Detect callback params/fragments - confirm tokens/code detected."""
    log_checkpoint("B", {
        "access_token_present": access_token is not None,
        "refresh_token_present": refresh_token is not None,
        "code_present": auth_code is not None,
        "type": auth_type,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "code": auth_code
    })
    
    if AUTH_DEBUG:
        with st.expander("🔍 Auth Debug: Checkpoint B (Callback Detected)", expanded=False):
            st.write("**Tokens Detected:**")
            st.write(f"- Access Token: {'✅ Present' if access_token else '❌ Missing'}")
            st.write(f"- Refresh Token: {'✅ Present' if refresh_token else '❌ Missing'}")
            st.write(f"- Code: {'✅ Present' if auth_code else '❌ Missing'}")
            st.write(f"- Type: {auth_type or 'None'}")


def checkpoint_c_set_session_attempt(access_token: Optional[str], refresh_token: Optional[str],
                                    method: str = "set_session"):
    """CHECKPOINT C: Attempt set_session/exchange - capture response + exceptions."""
    log_checkpoint("C", {
        "method": method,
        "access_token": access_token,
        "refresh_token": refresh_token
    })


def checkpoint_c_set_session_result(response: Any = None, error: Exception = None):
    """CHECKPOINT C (continued): Result of set_session."""
    if error:
        log_checkpoint("C", error=error)
    else:
        result_info = {
            "response_received": response is not None,
            "has_user": hasattr(response, "user") and response.user is not None if response else False,
            "has_session": hasattr(response, "session") and response.session is not None if response else False,
        }
        
        if response and hasattr(response, "user") and response.user:
            result_info["user_id"] = getattr(response.user, "id", None)
            result_info["user_email"] = getattr(response.user, "email", None)
        
        log_checkpoint("C", {"result": result_info})


def checkpoint_d_verify_user(client, user_id: Optional[str] = None):
    """CHECKPOINT D: After session set - call auth.get_user() and confirm user.id exists."""
    try:
        # Try to get user from Supabase client
        current_user = None
        try:
            user_response = client.auth.get_user()
            # Handle both response.user and direct user object
            current_user = user_response.user if hasattr(user_response, "user") else user_response
        except Exception as e:
            log_checkpoint("D", {"get_user_error": str(e)}, error=e)
        
        # Also check session state
        session_state_user = st.session_state.get("auth_user")
        
        # Extract user IDs
        client_user_id = None
        if current_user:
            if hasattr(current_user, "id"):
                client_user_id = current_user.id
            elif isinstance(current_user, dict):
                client_user_id = current_user.get("id")
        
        session_state_user_id = None
        if session_state_user:
            if hasattr(session_state_user, "id"):
                session_state_user_id = session_state_user.id
            elif isinstance(session_state_user, dict):
                session_state_user_id = session_state_user.get("id")
        
        result = {
            "client_user_id": client_user_id,
            "session_state_user_id": session_state_user_id,
            "user_id_match": False
        }
        
        if result["client_user_id"] and result["session_state_user_id"]:
            result["user_id_match"] = result["client_user_id"] == result["session_state_user_id"]
        
        if user_id:
            result["expected_user_id"] = user_id
            result["matches_expected"] = (
                result["client_user_id"] == user_id or 
                result["session_state_user_id"] == user_id
            )
        
        log_checkpoint("D", result)
        
        if AUTH_DEBUG:
            with st.expander("🔍 Auth Debug: Checkpoint D (User Verification)", expanded=False):
                st.write("**Client User:**")
                st.write(f"- ID: {result['client_user_id'] or 'None'}")
                st.write("**Session State User:**")
                st.write(f"- ID: {result['session_state_user_id'] or 'None'}")
                st.write(f"- Match: {'✅' if result['user_id_match'] else '❌'}")
                if user_id:
                    st.write(f"- Expected: {user_id}")
                    st.write(f"- Matches Expected: {'✅' if result['matches_expected'] else '❌'}")
        
        return result
        
    except Exception as e:
        log_checkpoint("D", error=e)
        return {"error": str(e)}


def checkpoint_e_gate_decision(is_authenticated: bool, reason: str = ""):
    """CHECKPOINT E: Gate logic - confirm why it decides you're authenticated/unauthenticated."""
    session_state_check = {
        "has_auth_user": "auth_user" in st.session_state,
        "auth_user_not_none": st.session_state.get("auth_user") is not None,
        "has_auth_session": "auth_session" in st.session_state,
        "has_user_profile": "user_profile" in st.session_state,
    }
    
    log_checkpoint("E", {
        "is_authenticated": is_authenticated,
        "reason": reason,
        "session_state": session_state_check
    })
    
    if AUTH_DEBUG:
        with st.expander("🔍 Auth Debug: Checkpoint E (Gate Decision)", expanded=False):
            st.write(f"**Decision:** {'✅ AUTHENTICATED' if is_authenticated else '❌ NOT AUTHENTICATED'}")
            st.write(f"**Reason:** {reason or 'Not provided'}")
            st.write("**Session State:**")
            st.json(session_state_check)

