"""Agent prompt templates.

This package contains prompt templates and Pydantic models for structured LLM outputs.
"""

from src.agents.prompts.clarification import (
    CLARIFICATION_SYSTEM,
    CLARIFICATION_USER,
    ClarificationResult,
)
from src.agents.prompts.decision import (
    DECISION_SYSTEM,
    DECISION_USER,
    PricingDecision,
)
from src.agents.prompts.image_analysis import (
    IMAGE_ANALYSIS_SYSTEM,
    IMAGE_ANALYSIS_USER,
    ImageAnalysisResult,
)
from src.agents.prompts.listing_writer import (
    WRITER_SYSTEM,
    WRITER_USER,
    ListingDraftResult,
)
from src.agents.prompts.reasoning import (
    REASONING_SYSTEM,
    REASONING_USER,
    ReasoningResult,
)

__all__ = [
    "CLARIFICATION_SYSTEM",
    "CLARIFICATION_USER",
    "DECISION_SYSTEM",
    "DECISION_USER",
    "IMAGE_ANALYSIS_SYSTEM",
    "IMAGE_ANALYSIS_USER",
    "REASONING_SYSTEM",
    "REASONING_USER",
    "WRITER_SYSTEM",
    "WRITER_USER",
    "ClarificationResult",
    "ImageAnalysisResult",
    "ListingDraftResult",
    "PricingDecision",
    "ReasoningResult",
]
