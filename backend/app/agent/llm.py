"""
LLM client with tool calling support.
Uses Groq (or any OpenAI-compatible endpoint) for free-tier friendliness.
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from app.agent.tools import TOOLS_SCHEMA, execute_tool
from app.config import get_settings


SYSTEM_PROMPT = """You are a helpful, friendly voice assistant.

Guidelines:
- Keep spoken responses concise and natural (1-3 sentences when possible).
- When the user asks about documents, use the search_documents or list_uploaded_documents tools.
- When the user asks you to read or dictate a document, use the dictate_document tool.
- Use the calculator tool for any math.
- Be conversational and warm.
- If you don't know something, say so honestly.
- Never invent document content — always ground answers in retrieved text.
"""


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.llm_model

        if settings.llm_provider == "groq" and settings.groq_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            # Fallback to OpenAI-compatible endpoint
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key or settings.groq_api_key,
                base_url=settings.openai_base_url,
            )

        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    async def chat(self, user_text: str) -> str:
        """
        Non-streaming chat with automatic tool calling loop.
        Returns the final assistant text response.
        """
        self.add_user_message(user_text)

        max_tool_rounds = 5
        for _ in range(max_tool_rounds):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1024,
            )

            message = response.choices[0].message

            # If the model wants to call tools
            if message.tool_calls:
                self.messages.append(message.model_dump())

                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    result = await execute_tool(name, args)

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
                continue  # let the model respond after tools

            # Normal text response
            content = message.content or ""
            self.add_assistant_message(content)
            return content

        return "I ran into a problem while processing that request."

    async def stream(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Streaming version (text tokens). Tool calls are still handled
        in a non-streaming loop first for simplicity.
        """
        # For MVP we do tool calling non-streaming, then stream the final answer
        final = await self.chat(user_text)
        # Simulate streaming by yielding chunks
        words = final.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
