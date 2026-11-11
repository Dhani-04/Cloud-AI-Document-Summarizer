"""Supabase integration: authentication, database history and file storage.

IMPORTANT: one Supabase client is created *per browser session* and kept in
st.session_state. Never share a client across users (e.g. with
st.cache_resource) because it holds the signed-in user's access token.
Row Level Security in Postgres then guarantees each user only sees their
own rows and files.
"""
import uuid

import streamlit as st
from supabase import Client, create_client

from config import STORAGE_BUCKET, SUPABASE_KEY, SUPABASE_URL


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_client() -> Client:
    if "sb_client" not in st.session_state:
        st.session_state.sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.sb_client


# ------------------------------------------------------------------ auth
def sign_in(email: str, password: str) -> None:
    res = get_client().auth.sign_in_with_password({"email": email, "password": password})
    st.session_state.user = res.user


def sign_up(email: str, password: str) -> bool:
    """Create an account. Returns True if signed in immediately.

    Returns False when Supabase requires email confirmation first.
    """
    res = get_client().auth.sign_up({"email": email, "password": password})
    if res.session is not None:
        st.session_state.user = res.user
        return True
    return False


def sign_out() -> None:
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("sb_client", None)


# -------------------------------------------------------------- database
def save_summary(
    user_id: str,
    file_name: str,
    page_count: int,
    summary: str,
    pdf_bytes: bytes | None = None,
) -> None:
    client = get_client()
    storage_path = None

    if pdf_bytes:
        storage_path = f"{user_id}/{uuid.uuid4()}.pdf"
        client.storage.from_(STORAGE_BUCKET).upload(
            storage_path, pdf_bytes, {"content-type": "application/pdf"}
        )

    client.table("summaries").insert(
        {
            "user_id": user_id,
            "file_name": file_name,
            "page_count": page_count,
            "summary": summary,
            "storage_path": storage_path,
        }
    ).execute()


def list_summaries(limit: int = 50) -> list[dict]:
    res = (
        get_client()
        .table("summaries")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def delete_summary(row: dict) -> None:
    client = get_client()
    if row.get("storage_path"):
        client.storage.from_(STORAGE_BUCKET).remove([row["storage_path"]])
    client.table("summaries").delete().eq("id", row["id"]).execute()


def get_pdf_url(storage_path: str, expires_in: int = 3600) -> str | None:
    """Time-limited signed URL for a private PDF."""
    res = get_client().storage.from_(STORAGE_BUCKET).create_signed_url(storage_path, expires_in)
    return res.get("signedURL") or res.get("signedUrl")
