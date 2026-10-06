"""
api_client.py - Shared helper for API calls with error handling.

Provides a centralized httpx client with consistent timeout, error handling,
and logging to avoid repeated boilerplate in page modules.
"""

import httpx
import streamlit as st
from typing import Optional, Any, Dict

API_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_TIMEOUT = 10.0


def api_get(endpoint: str, timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    GET request helper. Returns JSON dict on success, shows st.error() on failure.
    Returns None if any error occurs.
    """
    try:
        response = httpx.get(
            f"{API_BASE_URL}{endpoint}",
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"API error: {response.status_code} on GET {endpoint}"
            )
            return None
    except httpx.RequestError as e:
        st.error(f"Cannot connect to API server: {e}")
        return None
    except Exception as e:
        st.error(f"Error on GET {endpoint}: {e}")
        return None


def api_post(
    endpoint: str,
    payload: Dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """
    POST request helper. Returns JSON dict on success (200/201), shows st.error() on failure.
    Returns None if any error occurs.
    """
    try:
        response = httpx.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=timeout
        )
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(
                f"API error: {response.status_code} on POST {endpoint}"
            )
            return None
    except httpx.RequestError as e:
        st.error(f"Cannot connect to API server: {e}")
        return None
    except Exception as e:
        st.error(f"Error on POST {endpoint}: {e}")
        return None


def api_patch(
    endpoint: str,
    payload: Dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """
    PATCH request helper. Returns JSON dict on success (200), shows st.error() on failure.
    Returns None if any error occurs.
    """
    try:
        response = httpx.patch(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"API error: {response.status_code} on PATCH {endpoint}"
            )
            return None
    except httpx.RequestError as e:
        st.error(f"Cannot connect to API server: {e}")
        return None
    except Exception as e:
        st.error(f"Error on PATCH {endpoint}: {e}")
        return None


def api_delete(
    endpoint: str,
    timeout: float = DEFAULT_TIMEOUT
) -> bool:
    """
    DELETE request helper. Returns True on success (200/204), shows st.error() on failure.
    Returns False if any error occurs.
    """
    try:
        response = httpx.delete(
            f"{API_BASE_URL}{endpoint}",
            timeout=timeout
        )
        if response.status_code in [200, 204]:
            return True
        else:
            st.error(
                f"API error: {response.status_code} on DELETE {endpoint}"
            )
            return False
    except httpx.RequestError as e:
        st.error(f"Cannot connect to API server: {e}")
        return False
    except Exception as e:
        st.error(f"Error on DELETE {endpoint}: {e}")
        return False
