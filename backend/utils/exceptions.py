"""Custom exceptions for the ClearSignal pipeline.

Provides a hierarchy of specific exceptions so pipeline stages can catch
and handle errors appropriately without bare `except Exception:` blocks.
"""
from __future__ import annotations


class ClearSignalError(Exception):
    """Base exception for all pipeline errors."""


class PipelineStageError(ClearSignalError):
    """A pipeline stage failed but the pipeline can continue."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")


class AICallError(ClearSignalError):
    """An AI API call failed (OpenAI, Anthropic)."""

    def __init__(self, provider: str, model: str, message: str) -> None:
        self.provider = provider
        self.model = model
        super().__init__(f"{provider}/{model}: {message}")


class DatabaseError(ClearSignalError):
    """Supabase query failed."""


class ValidationError(ClearSignalError):
    """Input validation failed (bad JSON from AI, missing fields, etc.)."""
