"""Unified LLM client supporting Ollama, LM Studio, and GPT4All."""

from collections.abc import AsyncGenerator
from typing import Any

import httpx
from openai import AsyncOpenAI

from backend.config import get_settings


class LLMClient:
    """Unified interface for local LLM backends."""

    def __init__(self):
        """Initialize LLM client with configured backend."""
        self.settings = get_settings()
        self._openai_client: AsyncOpenAI | None = None

    @property
    def backend(self) -> str:
        """Get active backend name."""
        return self.settings.llm_backend

    @property
    def base_url(self) -> str:
        """Get base URL for active backend."""
        if self.backend == "ollama":
            return self.settings.ollama_base_url
        elif self.backend == "lmstudio":
            return self.settings.lmstudio_base_url
        else:  # gpt4all
            return self.settings.gpt4all_base_url

    @property
    def openai_client(self) -> AsyncOpenAI:
        """Get OpenAI-compatible client for LM Studio / GPT4All."""
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="not-needed",
            )
        return self._openai_client

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List available models from active backend.

        Returns:
            List of model info dicts.
        """
        if self.backend == "ollama":
            return await self._list_ollama_models()
        else:
            return await self._list_openai_models()

    async def _list_ollama_models(self) -> list[dict[str, Any]]:
        """List models from Ollama."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.settings.ollama_base_url}/api/tags",
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()
                return [
                    {
                        "id": m["name"],
                        "name": m["name"],
                        "size": m.get("size", 0),
                        "modified": m.get("modified_at", ""),
                    }
                    for m in data.get("models", [])
                ]
            except Exception:
                return []

    async def _list_openai_models(self) -> list[dict[str, Any]]:
        """List models from OpenAI-compatible endpoint."""
        try:
            models = await self.openai_client.models.list()
            return [
                {
                    "id": m.id,
                    "name": m.id,
                    "owned_by": getattr(m, "owned_by", "local"),
                }
                for m in models.data
            ]
        except Exception:
            return []

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_k: int | None = None,
        top_p: float | None = None,
    ) -> str:
        """
        Generate a response (non-streaming).

        Args:
            prompt: User prompt.
            model: Model name (uses default if not specified).
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            top_k: Top-k sampling parameter (Ollama only).
            top_p: Top-p sampling parameter (Ollama only).

        Returns:
            Generated text.
        """
        model = model or self.settings.default_model

        if self.backend == "ollama":
            return await self._generate_ollama(
                prompt, model, system_prompt, temperature, max_tokens, top_k, top_p
            )
        else:
            return await self._generate_openai(
                prompt, model, system_prompt, temperature, max_tokens
            )

    async def _generate_ollama(
        self,
        prompt: str,
        model: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        top_k: int | None = None,
        top_p: float | None = None,
    ) -> str:
        """Generate using Ollama."""
        async with httpx.AsyncClient() as client:
            options = {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
            if top_k is not None:
                options["top_k"] = top_k
            if top_p is not None:
                options["top_p"] = top_p
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options,
            }
            if system_prompt:
                payload["system"] = system_prompt

            response = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def _generate_openai(
        self,
        prompt: str,
        model: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate using OpenAI-compatible endpoint."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def stream_generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a response with streaming.

        Args:
            prompt: User prompt.
            model: Model name (uses default if not specified).
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Yields:
            Generated text chunks.
        """
        model = model or self.settings.default_model

        if self.backend == "ollama":
            async for chunk in self._stream_ollama(
                prompt, model, system_prompt, temperature, max_tokens
            ):
                yield chunk
        else:
            async for chunk in self._stream_openai(
                prompt, model, system_prompt, temperature, max_tokens
            ):
                yield chunk

    async def _stream_ollama(
        self,
        prompt: str,
        model: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream generate using Ollama."""
        async with httpx.AsyncClient() as client:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            if system_prompt:
                payload["system"] = system_prompt

            async with client.stream(
                "POST",
                f"{self.settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=120,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json

                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue

    async def _stream_openai(
        self,
        prompt: str,
        model: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream generate using OpenAI-compatible endpoint."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def check_health(self) -> dict[str, Any]:
        """
        Check backend health status.

        Returns:
            Health status dict.
        """
        try:
            if self.backend == "ollama":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.settings.ollama_base_url}/api/tags",
                        timeout=5,
                    )
                    return {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "backend": self.backend,
                        "url": self.base_url,
                    }
            else:
                models = await self._list_openai_models()
                return {
                    "status": "healthy" if models else "unhealthy",
                    "backend": self.backend,
                    "url": self.base_url,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": self.backend,
                "url": self.base_url,
                "error": str(e),
            }


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
