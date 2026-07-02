"""LLM access layer.

A `ModelClient` is anything that can turn a prompt into text. Agents never talk
to a provider directly; they call `call(tier, prompt, system)` and this module
routes to the concrete client configured for that tier in `config.TIERS`.

Clients that ship:
  * `AnthropicClient` - the Claude API (default for all three tiers). Uses the
                        official `anthropic` SDK if installed, else raw HTTP.
                        Reads ANTHROPIC_API_KEY from the environment.
  * `OllamaClient`    - a local Ollama server over HTTP.
  * `MockClient`      - deterministic, offline; lets the whole pipeline run in
                        tests without any model. Install with `use_mock()`.

Switch the active backend for all tiers with `use_anthropic()`, `use_deepseek()`,
`use_ollama()`, or `use_mock()`. To add another provider (e.g. an OpenAI-compatible 
endpoint), write a client with the same `.generate` signature and `register_client(...)`.
"""
from __future__ import annotations

import json
import os
from typing import Protocol, runtime_checkable

from . import config
from .config import ANTHROPIC_TIERS, DEEPSEEK_TIERS, OLLAMA_TIERS, TIERS, ModelConfig


@runtime_checkable
class ModelClient(Protocol):
    def generate(self, model: str, prompt: str, system: str | None,
                 temperature: float, max_tokens: int) -> str:
        ...


# --------------------------------------------------------------------------- #
# Anthropic (Claude API)
# --------------------------------------------------------------------------- #
class AnthropicClient:
    """Client for the Anthropic Messages API.

    Prefers the official `anthropic` SDK; falls back to raw HTTP (httpx, then
    urllib) so the package works without the SDK installed. Text is assembled
    from the `text` content blocks, so it is robust to models that also return
    (adaptive) thinking blocks.
    """

    def __init__(self, api_key: str | None = None,
                 base_url: str = "https://api.anthropic.com",
                 version: str = "2023-06-01", timeout: float = 600.0,
                 api_key_env: str = "ANTHROPIC_API_KEY"):  # Add this parameter
        self.api_key = api_key or os.environ.get(api_key_env)
        self.base_url = base_url.rstrip("/")
        self.version = version
        self.timeout = timeout
        self._sdk = None  # lazily constructed official client

    # -- public ------------------------------------------------------------- #
    def generate(self, model: str, prompt: str, system: str | None,
                 temperature: float, max_tokens: int = 4096) -> str:
        try:
            return self._via_sdk(model, prompt, system, temperature, max_tokens)
        except ImportError:
            return self._via_http(model, prompt, system, temperature, max_tokens)

    # -- backends ----------------------------------------------------------- #
    def _via_sdk(self, model, prompt, system, temperature, max_tokens) -> str:
        import anthropic  # raises ImportError if SDK absent -> HTTP fallback
        if self._sdk is None:
            kwargs = {"base_url": self.base_url}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._sdk = anthropic.Anthropic(**kwargs)
        kwargs = dict(model=model, max_tokens=max_tokens,
                      temperature=temperature,
                      messages=[{"role": "user", "content": prompt}])
        if system:
            kwargs["system"] = system
        try:
            msg = self._sdk.messages.create(**kwargs)
        except Exception as exc:  # temperature constraint under thinking, etc.
            if "temperature" in str(exc).lower():
                kwargs.pop("temperature", None)
                msg = self._sdk.messages.create(**kwargs)
            else:
                raise
        return "".join(b.text for b in msg.content
                       if getattr(b, "type", None) == "text")

    def _via_http(self, model, prompt, system, temperature, max_tokens) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
            "content-type": "application/json",
        }
        data = self._post(body, headers)
        return "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")

    def _post(self, body: dict, headers: dict) -> dict:
        url = f"{self.base_url}/v1/messages"
        try:
            import httpx  # type: ignore
            r = httpx.post(url, json=body, headers=headers, timeout=self.timeout)
            if r.status_code == 400 and "temperature" in r.text.lower():
                body.pop("temperature", None)
                r = httpx.post(url, json=body, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except ImportError:
            import urllib.request
            req = urllib.request.Request(
                url, data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return json.loads(resp.read())
            
# --------------------------------------------------------------------------- #
# Deepseek (uses anthropic SDK)
# --------------------------------------------------------------------------- #
class DeepSeekClient(AnthropicClient):
    def __init__(self, **kwargs):
        kwargs.setdefault("base_url", "https://api.deepseek.com/anthropic")
        kwargs.setdefault("api_key_env", "DEEPSEEK_API_KEY")
        super().__init__(**kwargs)

# --------------------------------------------------------------------------- #
# Ollama (local)
# --------------------------------------------------------------------------- #
class OllamaClient:
    """Minimal client for the Ollama REST API (default http://localhost:11434).

    Ollama cannot browse or fetch URLs - tool calls (search, page reading, Lean)
    are executed by the `tools/` layer and fed back in as prompt context.
    """

    def __init__(self, host: str = "http://localhost:11434", timeout: float = 600.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def generate(self, model: str, prompt: str, system: str | None,
                 temperature: float, max_tokens: int = 4096) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            import httpx  # type: ignore
            resp = httpx.post(f"{self.host}/api/generate", json=payload,
                              timeout=self.timeout)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except ImportError:
            import urllib.request
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
                return json.loads(r.read()).get("response", "")


# --------------------------------------------------------------------------- #
# Mock (offline, deterministic)
# --------------------------------------------------------------------------- #
class MockClient:
    """Offline stand-in. Emits a structurally-valid response with a SCORE= line
    so score-parsing agents work end-to-end in tests. Deterministic per prompt."""

    def generate(self, model: str, prompt: str, system: str | None,
                 temperature: float, max_tokens: int = 4096) -> str:
        score = (sum(map(ord, prompt)) % 5) + 1
        return (f"[mock:{model}] Structurally-valid placeholder response.\n"
                f"SCORE={score}")


# --------------------------------------------------------------------------- #
# Registry + dispatch
# --------------------------------------------------------------------------- #
_CLIENTS: dict[str, ModelClient] = {
    "anthropic": AnthropicClient(),
    "deepseek":DeepSeekClient(),
    "ollama": OllamaClient(),
    "mock": MockClient(),
}


def register_client(name: str, client: ModelClient) -> None:
    _CLIENTS[name] = client


def _set_tiers(preset: dict[str, ModelConfig]) -> None:
    TIERS.clear()
    TIERS.update({k: v for k, v in preset.items()})


def use_anthropic() -> None:
    """Route every tier to the Anthropic API preset."""
    _set_tiers(ANTHROPIC_TIERS)

def use_deepseek() -> None:
    """Route every tier to the Deepseek API preset (the default).
    """
    _set_tiers(DEEPSEEK_TIERS)

def use_ollama() -> None:
    """Route every tier to the local Ollama preset."""
    _set_tiers(OLLAMA_TIERS)


def use_mock() -> None:
    """Route every tier to the offline MockClient (keeps each tier's model id)."""
    _set_tiers({t: ModelConfig("mock", c.model, c.temperature, c.max_tokens)
                for t, c in TIERS.items()})


def resolve(tier: str) -> tuple[ModelClient, ModelConfig]:
    if tier not in TIERS:
        raise KeyError(f"Unknown tier {tier!r}; expected one of {list(TIERS)}")
    cfg = TIERS[tier]
    if cfg.client not in _CLIENTS:
        raise KeyError(f"No client registered for {cfg.client!r}")
    return _CLIENTS[cfg.client], cfg


def call(tier: str, prompt: str, system: str | None = None) -> str:
    client, cfg = resolve(tier)
    return client.generate(cfg.model, prompt, system, cfg.temperature,
                           cfg.max_tokens)
