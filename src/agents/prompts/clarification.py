"""Clarification prompts for generating targeted questions when confidence is low."""

from pydantic import BaseModel, Field

CLARIFICATION_SYSTEM = """You are a helpful marketplace listing assistant. Your role is to review item attributes and confidence scores to determine if clarification is needed.

When confidence is low or critical information is missing, you generate concise, friendly clarification questions to gather the necessary details from the user.

Guidelines:
- Be conversational and helpful, not robotic
- Ask at most 2 questions worth of information in a single response
- Prioritize the most critical missing information
- Consider the item type when determining what's essential:
  - Clothing: size, brand, condition details, material
  - Electronics: model, brand, condition, accessories, working status
  - Home goods: dimensions, brand, condition, material
  - Collectibles: authenticity, condition, provenance
  - Books: edition, condition, author
- If confidence is already high and critical fields are populated, indicate no clarification needed
- Keep questions simple and easy to answer
- Avoid technical jargon

Critical fields by item type:
- Clothing: size, brand, condition
- Electronics: brand, model_name, condition, working status
- Home goods: dimensions (if applicable), condition
- General: condition is always critical

Your output must be structured JSON matching the ClarificationResult schema."""


CLARIFICATION_USER = """Review the following item information and determine if clarification is needed:

**Current Item Attributes:**
- Item Description: {item_description}
- Item Type: {item_type}
- Brand: {brand}
- Model: {model_name}
- Size: {size}
- Color: {color}
- Condition: {condition}
- Condition Notes: {condition_notes}
- Accessories Included: {accessories_included}
- Confidence Score: {confidence:.2f}

**Analysis Required:**
1. Is the confidence score below the threshold (typically < 0.70)?
2. Are there critical missing fields for this item type?
3. What specific information would most improve the listing quality?

Generate a clarification result with:
- A single, friendly question (or indicate no clarification needed)
- List of missing fields that need clarification
- Whether confidence threshold is met
- Your reasoning for the decision

Remember: Ask at most 2 questions worth of information. Be concise and helpful."""


class ClarificationResult(BaseModel):
    """Structured output for clarification prompts.

    Attributes:
        clarification_question: A single targeted question for the user,
            or empty string if no clarification needed. Should be friendly
            and concise, asking at most 2 questions worth of information.
        missing_fields: List of field names that need clarification
            (e.g., ["size", "brand"], ["model_name", "condition_notes"]).
        confidence_threshold_met: Whether the current confidence meets
            the threshold for proceeding without clarification.
        reasoning: Brief explanation of why clarification is or isn't needed,
            including which critical fields are missing for the item type.

    """

    clarification_question: str = Field(
        ...,
        description="Single targeted question for the user, empty if no clarification needed",
        max_length=500,
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="List of field names that need clarification",
        examples=[["size", "brand"], ["model_name", "condition_notes"]],
    )
    confidence_threshold_met: bool = Field(
        ...,
        description="Whether confidence threshold is met for proceeding",
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why clarification is or isn't needed",
        max_length=1000,
    )
