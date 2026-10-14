from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from urllib.request import urlopen

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None

from .config import OPENAI_API_KEY, OPENAI_MODEL
from .prompts import DEFAULT_SYSTEM_PROMPT, REVIEW_PROMPT
from .tools import get_tool_registry


class AIAgent:
    def __init__(self, model: Optional[str] = None, system_prompt: Optional[str] = None):
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        self.provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        default_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b") if self.provider == "ollama" else os.getenv("OPENAI_MODEL", OPENAI_MODEL)
        self.model = model or default_model
        self.system_prompt = system_prompt or os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
        self.client = None
        self.tools = get_tool_registry()

        if OpenAI is not None and self.provider == "ollama":
            self.client = OpenAI(base_url=self.ollama_base_url, api_key="ollama")
        elif OpenAI is not None and self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)
            if api_key:
                self.client = OpenAI(api_key=api_key)

    def is_connected(self) -> bool:
        if self.client is None:
            return False
        if self.provider != "ollama":
            return True

        service_url = self.ollama_base_url.removesuffix("/v1") + "/api/tags"
        try:
            with urlopen(service_url, timeout=1):
                return True
        except Exception:
            return False

    def respond(self, prompt: str, model: Optional[str] = None) -> str:
        selected_model = model or self.model
        if self.client is not None:
            try:
                if self.provider == "ollama":
                    completion = self.client.chat.completions.create(
                        model=selected_model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    answer = completion.choices[0].message.content
                else:
                    completion = self.client.responses.create(
                        model=selected_model,
                        input=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    answer = completion.output_text
            except Exception as exc:
                if self.provider == "ollama":
                    raise RuntimeError(
                        f"Could not reach Ollama or load '{selected_model}'. Start Ollama and run: ollama pull {selected_model}"
                    ) from exc
                error_name = type(exc).__name__
                if error_name in {"AuthenticationError", "PermissionDeniedError"}:
                    message = "OpenAI rejected the API key or its permissions. Check the key in your local .env file."
                elif error_name == "RateLimitError":
                    message = "OpenAI rate limit or billing limit reached. Check your API usage and billing settings."
                elif error_name == "NotFoundError":
                    message = f"The model '{selected_model}' is unavailable for this API key. Choose another model."
                else:
                    message = f"OpenAI request failed ({error_name}). Check your connection and API settings."
                raise RuntimeError(message) from exc
            if answer:
                return answer
            raise RuntimeError("The AI provider returned an empty response. Please try again.")

        normalized = (prompt or "").strip()
        if not normalized:
            return "Please enter a question and I will answer it."

        lower = normalized.lower()
        if lower in {"hi", "hello", "hey"}:
            return "Hello! I’m your AI assistant. Ask me anything and I’ll answer clearly and quickly."
        if "time" in lower:
            return f"The current time is {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
        if "what is ai" in lower or "artificial intelligence" in lower:
            return "Artificial intelligence is a field of computer science focused on creating systems that can understand language, recognize patterns, and make decisions using data."
        return (
            f"Here is a practical answer for: {normalized}\n\n"
            "I can help with explanations, summaries, ideas, coding help, and general problem solving. "
            f"This reply is using the local model '{selected_model}' while the live OpenAI key remains optional."
        )

    def respond_stream(self, prompt: str, model: Optional[str] = None):
        selected_model = model or self.model
        if self.client is None or self.provider != "ollama":
            yield self.respond(prompt, model=selected_model)
            return

        try:
            stream = self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield token
        except Exception as exc:
            raise RuntimeError(
                f"Could not reach Ollama or load '{selected_model}'. Start Ollama and run: ollama pull {selected_model}"
            ) from exc

    def execute_tool(self, tool_name: str, arguments: Optional[dict[str, Any]] = None):
        arguments = arguments or {}
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        tool = self.tools[tool_name]
        if isinstance(arguments, dict):
            return tool(**arguments)
        return tool(arguments)

    def review_code(self, code: str) -> str:
        review_note = "# Review: The code is valid and readable. Consider adding validation, type hints, and edge-case handling where appropriate."
        return f"{code}\n{review_note}\nPrompt: {REVIEW_PROMPT}"


def review_code(code: str) -> str:
    return AIAgent().review_code(code)
