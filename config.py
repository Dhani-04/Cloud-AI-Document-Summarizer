"""Central configuration.

Settings are read from environment variables first (Hugging Face Spaces,
Docker, Cloud Run, Render) and then from Streamlit secrets
(.streamlit/secrets.toml for local development).
"""
import os

import streamlit as st


def get_setting(name: str, default=None):
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets file present
        return default


# --- Supabase (use the *anon/public* key, never the service_role key) ---
SUPABASE_URL = get_setting("SUPABASE_URL")
SUPABASE_KEY = get_setting("SUPABASE_KEY")
STORAGE_BUCKET = get_setting("SUPABASE_BUCKET", "documents")

# --- AI model ---
MODEL_NAME = get_setting("MODEL_NAME", "sshleifer/distilbart-cnn-6-6")

# Safety cap so one huge PDF cannot tie up a CPU-only server for many minutes.
MAX_CHUNKS = int(get_setting("MAX_CHUNKS", 40))
