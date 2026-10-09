"""
Tool definitions for the Voice Agent.

Each tool is a simple async function + a JSON schema.
The LLM discovers tools automatically via function calling.
"""

from __future__ import annotations

import datetime
import math
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def get_current_time() -> str:
    """Return the current date and time."""
    now = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    return f"The current date and time is {now}."


async def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.
    Example: "2 + 2 * 10" or "sqrt(16) + 3**2"
    """
    allowed = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "pi": math.pi,
        "e": math.e,
        "pow": math.pow,
        "abs": abs,
        "round": round,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)  # noqa: S307
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Could not calculate '{expression}': {e}"


async def search_documents(query: str) -> str:
    """
    Search across all uploaded documents and return relevant excerpts.
    """
    from app.documents.rag import rag_service
    return rag_service.query(query)


async def list_uploaded_documents() -> str:
    """List all currently uploaded documents."""
    from app.config import get_settings
    settings = get_settings()
    docs = list(settings.documents_dir.glob("*"))
    if not docs:
        return "No documents have been uploaded yet."
    names = [d.name for d in docs if d.is_file()]
    return "Uploaded documents:\n" + "\n".join(f"- {n}" for n in names)


async def dictate_document(filename: str, section: str | None = None) -> str:
    """
    Instruct the system to start dictating a document (or a section of it).
    Returns a special marker that the pipeline understands.
    """
    return f"__DICTATE__:{filename}:{section or 'full'}"


# ---------------------------------------------------------------------------
# OpenAI-compatible tool schemas
# ---------------------------------------------------------------------------

TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a mathematical expression. Supports +, -, *, /, sqrt, sin, cos, pow, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate, e.g. '2 + 2 * 10' or 'sqrt(16)'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search across all uploaded documents for relevant information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question about the documents",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_uploaded_documents",
            "description": "List all documents that have been uploaded so far.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dictate_document",
            "description": "Start reading / dictating a document out loud. Use when the user asks to read a document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Exact filename of the document to dictate",
                    },
                    "section": {
                        "type": "string",
                        "description": "Optional section or page range, e.g. 'introduction' or 'pages 1-3'",
                    },
                },
                "required": ["filename"],
            },
        },
    },
]


# Map name → callable
TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
    "calculator": calculator,
    "search_documents": search_documents,
    "list_uploaded_documents": list_uploaded_documents,
    "dictate_document": dictate_document,
}


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name and return its string result."""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Unknown tool: {name}"
    try:
        logger.info(f"Executing tool: {name} with args {arguments}")
        result = await func(**arguments)
        return str(result)
    except Exception as e:
        logger.exception(f"Tool {name} failed")
        return f"Tool error: {e}"
