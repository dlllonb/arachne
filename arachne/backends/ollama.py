"""Ollama backend - uses local Ollama instance ."""

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b"


def query(real_query: str) -> str:
    """
    Send a prompt to the local Ollama server and return the response.

    Stateless: each call is independent (for now).
    """

    payload = {
        "model": MODEL,
        "prompt": real_query,
        "stream": False,
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()

        data = r.json()
        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return (
            "Arachne could not connect to the Ollama server at "
            "http://localhost:11434. Is Ollama running?"
        )

    except Exception as e:
        return f"Arachne Ollama backend error: {e}"