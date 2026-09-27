import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

def get_config_val(key: str, default: str = "") -> str:
    """Retrieve configuration value checking environment variables or Streamlit secrets if available."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default

GROQ_API_KEY = get_config_val("GROQ_API_KEY", "")
GROQ_MODEL = get_config_val("GROQ_MODEL", "openai/gpt-oss-120b")

HINDSIGHT_API_KEY = get_config_val("HINDSIGHT_API_KEY", "")
HINDSIGHT_API_URL = get_config_val("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_BANK_ID = get_config_val("HINDSIGHT_BANK_ID", "incidentmind-default")

DATABASE_PATH = get_config_val("DATABASE_PATH", "incidentmind.db")
