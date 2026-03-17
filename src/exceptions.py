"""Custom exception classes for the marketplace agent.

This module defines a hierarchy of exceptions used throughout the application
for handling various error conditions in a structured way.
"""


class MarketplaceAgentError(Exception):
    """Base exception for all marketplace agent errors.

    All custom exceptions in the marketplace agent inherit from this class,
    allowing for broad exception handling when needed.

    Attributes:
        message: Human-readable error description.

    Args:
        message: Optional error message. Defaults to a generic message.
    """

    def __init__(
        self, message: str = "An error occurred in the marketplace agent"
    ) -> None:
        """Initialize the exception with an optional message.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(self.message)


class ScraperError(MarketplaceAgentError):
    """Exception raised when a scraper operation fails.

    This exception is raised when external scraping services (eBay, Vinted)
    encounter errors such as timeouts, rate limits, or invalid responses.

    Args:
        message: Description of the scraper failure.
    """

    def __init__(self, message: str = "Scraper operation failed") -> None:
        """Initialize the exception with an optional message.

        Args:
            message: Description of the scraper failure.
        """
        super().__init__(message)


class LLMError(MarketplaceAgentError):
    """Exception raised when an LLM operation fails.

    This exception covers failures in LiteLLM gateway communication,
    model inference errors, or invalid LLM responses.

    Args:
        message: Description of the LLM failure.
    """

    def __init__(self, message: str = "LLM operation failed") -> None:
        """Initialize the exception with an optional message.

        Args:
            message: Description of the LLM failure.
        """
        super().__init__(message)


class ValidationError(MarketplaceAgentError):
    """Exception raised when input validation fails.

    This exception is raised when user input, API requests, or
    internal data fails validation checks.

    Args:
        message: Description of the validation failure.
    """

    def __init__(self, message: str = "Validation failed") -> None:
        """Initialize the exception with an optional message.

        Args:
            message: Description of the validation failure.
        """
        super().__init__(message)


class ImageProcessingError(MarketplaceAgentError):
    """Exception raised when image processing fails.

    This exception covers failures in image upload, format conversion,
    size validation, or vision model analysis.

    Args:
        message: Description of the image processing failure.
    """

    def __init__(self, message: str = "Image processing failed") -> None:
        """Initialize the exception with an optional message.

        Args:
            message: Description of the image processing failure.
        """
        super().__init__(message)


class ClarificationTimeoutError(MarketplaceAgentError):
    """Exception raised when a clarification request times out.

    This exception is raised when the agent requests additional information
    from the user but receives no response within the expected timeframe.

    Args:
        message: Description of the timeout condition.
    """

    def __init__(self, message: str = "Clarification request timed out") -> None:
        """Initialize the exception with an optional message.

        Args:
            message: Description of the timeout condition.
        """
        super().__init__(message)
