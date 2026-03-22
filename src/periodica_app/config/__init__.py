"""
Configuration module for Periodics.
Provides secure access to API keys and other secrets.
"""

import json
import os
from pathlib import Path
from typing import Optional


_CONFIG_DIR = Path(__file__).parent
_SECRETS_FILE = _CONFIG_DIR / "secrets.json"
_secrets_cache: Optional[dict] = None


def _load_secrets() -> dict:
    """Load secrets from config file or environment variables."""
    global _secrets_cache

    if _secrets_cache is not None:
        return _secrets_cache

    secrets = {
        "gemini_api_key": None,
        "anthropic_api_key": None,
        "openai_api_key": None,
    }

    # Try loading from secrets.json first
    if _SECRETS_FILE.exists():
        try:
            with open(_SECRETS_FILE, 'r', encoding='utf-8') as f:
                file_secrets = json.load(f)
                for key in secrets:
                    if key in file_secrets and file_secrets[key]:
                        secrets[key] = file_secrets[key]
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load secrets.json: {e}")

    # Environment variables override file values
    env_mapping = {
        "gemini_api_key": "GEMINI_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "openai_api_key": "OPENAI_API_KEY",
    }

    for key, env_var in env_mapping.items():
        env_value = os.environ.get(env_var)
        if env_value:
            secrets[key] = env_value

    _secrets_cache = secrets
    return secrets


def get_gemini_api_key() -> Optional[str]:
    """Get the Gemini API key from config or environment."""
    secrets = _load_secrets()
    key = secrets.get("gemini_api_key")
    if key and key != "YOUR_GEMINI_API_KEY_HERE":
        return key
    return None


def get_anthropic_api_key() -> Optional[str]:
    """Get the Anthropic API key from config or environment."""
    secrets = _load_secrets()
    return secrets.get("anthropic_api_key")


def get_openai_api_key() -> Optional[str]:
    """Get the OpenAI API key from config or environment."""
    secrets = _load_secrets()
    return secrets.get("openai_api_key")


def reload_secrets() -> None:
    """Force reload of secrets from file/environment."""
    global _secrets_cache
    _secrets_cache = None
    _load_secrets()


def set_gemini_api_key(key: str) -> bool:
    """
    Save the Gemini API key to the secrets file.

    Args:
        key: The API key to save

    Returns:
        True if saved successfully, False otherwise
    """
    global _secrets_cache

    try:
        # Load existing secrets or create new dict
        secrets = {}
        if _SECRETS_FILE.exists():
            try:
                with open(_SECRETS_FILE, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Update the key
        secrets["gemini_api_key"] = key

        # Ensure other keys exist
        if "anthropic_api_key" not in secrets:
            secrets["anthropic_api_key"] = None
        if "openai_api_key" not in secrets:
            secrets["openai_api_key"] = None

        # Save to file
        _SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_SECRETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(secrets, f, indent=2)

        # Clear cache so next load picks up new key
        _secrets_cache = None

        return True

    except (IOError, OSError) as e:
        print(f"Error saving API key: {e}")
        return False


def is_gemini_configured() -> bool:
    """Check if a valid Gemini API key is configured."""
    return get_gemini_api_key() is not None
