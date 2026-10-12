"""Portkey model configuration for every agent call."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
AGENT_MODEL_NAME = "gpt-6-luna"


def create_agent_model() -> OpenAIChatModel:
    """Create the one allowed model through Portkey."""
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT.parent / ".env")
    portkey_api_key = os.getenv("PORTKEY_API_KEY")
    if not portkey_api_key:
        raise RuntimeError("PORTKEY_API_KEY must be set before running the agent team")

    client = AsyncOpenAI(
        api_key=portkey_api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": portkey_api_key},
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIChatModel(AGENT_MODEL_NAME, provider=provider)
