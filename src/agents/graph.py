"""LangGraph state graph definition.

This module assembles the complete agent graph with all nodes and routing logic
for the marketplace listing agent workflow.

Graph Structure:
    START
      ↓
    image_analysis
      ↓
    agent_reasoning
      ↓
      ├─ confidence < threshold → clarify → (user) → agent_reasoning (loop)
      ↓
    scrape_parallel (ebay_scrape + vinted_scrape run in parallel)
      ↓
    agent_decision
      ↓
    listing_writer
      ↓
    quality_check
      ↓
      ├─ fail → listing_writer (retry once)
      ↓
    END
"""

import logging

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.agent_decision import agent_decision
from src.agents.nodes.agent_reasoning import agent_reasoning
from src.agents.nodes.clarify import clarify
from src.agents.nodes.image_analysis import image_analysis
from src.agents.nodes.listing_writer import listing_writer
from src.agents.nodes.quality_check import quality_check, should_retry
from src.agents.nodes.scrape_ebay import scrape_ebay
from src.agents.nodes.scrape_vinted import scrape_vinted
from src.models.state import ListState

logger = logging.getLogger(__name__)


def route_after_reasoning(state: ListState) -> str:
    """Route after agent reasoning based on confidence level.

    Determines whether to request clarification from the user or proceed
    with marketplace scraping.

    Args:
        state: Current agent state containing needs_clarification flag.

    Returns:
        "clarify" if clarification is needed, "scrape_ebay" otherwise.
        The "scrape_ebay" return triggers the parallel fan-out to both
        scrapers via the graph edges.

    """
    needs_clarification = state.get("needs_clarification", False)

    if needs_clarification:
        logger.info(
            "Routing to clarify",
            extra={"confidence": state.get("confidence")},
        )
        return ["clarify"]

    logger.info(
        "Routing to parallel scrapers",
        extra={"confidence": state.get("confidence")},
    )
    return ["scrape_ebay", "scrape_vinted"]


def route_after_quality(state: ListState) -> str:
    """Route after quality check based on validation results.

    Determines whether to retry listing generation or end the workflow.

    Args:
        state: Current agent state containing quality_passed and retry_count.

    Returns:
        "listing_writer" if quality failed and retry is available, END otherwise.

    """
    quality_passed = state.get("quality_passed", False)
    can_retry = should_retry(state)

    if not quality_passed and can_retry:
        logger.info(
            "Quality check failed, retrying listing generation",
            extra={
                "quality_issues": state.get("quality_issues", []),
                "retry_count": state.get("retry_count", 0),
            },
        )
        return "listing_writer"

    if not quality_passed:
        logger.warning(
            "Quality check failed, max retries exceeded",
            extra={
                "quality_issues": state.get("quality_issues", []),
                "retry_count": state.get("retry_count", 0),
            },
        )

    return END


def build_graph() -> StateGraph:
    """Build the LangGraph state graph for the listing agent.

    Constructs the complete workflow graph with all nodes and edges,
    including conditional routing for clarification loops and quality retries.

    Returns:
        Compiled StateGraph ready for execution.

    """
    # Create the state graph
    graph = StateGraph(ListState)

    # Add all nodes
    graph.add_node("image_analysis", image_analysis)
    graph.add_node("agent_reasoning", agent_reasoning)
    graph.add_node("clarify", clarify)
    graph.add_node("scrape_ebay", scrape_ebay)
    graph.add_node("scrape_vinted", scrape_vinted)
    graph.add_node("agent_decision", agent_decision)
    graph.add_node("listing_writer", listing_writer)
    graph.add_node("quality_check", quality_check)

    # Add edges: START -> image_analysis
    graph.add_edge(START, "image_analysis")

    # Add edges: image_analysis -> agent_reasoning
    graph.add_edge("image_analysis", "agent_reasoning")

    # Add conditional routing after agent_reasoning
    # - If needs_clarification: route to clarify
    # - Otherwise: route to parallel scrapers (fan-out)
    graph.add_conditional_edges(
        "agent_reasoning",
        route_after_reasoning,
        {
            "clarify": "clarify",
            "scrape_ebay": "scrape_ebay",
            "scrape_vinted": "scrape_vinted",
        },
    )

    # Add edge: clarify -> agent_reasoning (loop back for re-analysis)
    graph.add_edge("clarify", "agent_reasoning")

    # Add fan-in: both scrapers -> agent_decision
    graph.add_edge("scrape_ebay", "agent_decision")
    graph.add_edge("scrape_vinted", "agent_decision")

    # Add edges: agent_decision -> listing_writer -> quality_check
    graph.add_edge("agent_decision", "listing_writer")
    graph.add_edge("listing_writer", "quality_check")

    # Add conditional routing after quality_check
    # - If quality failed and retry available: route back to listing_writer
    # - Otherwise: END
    graph.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {
            "listing_writer": "listing_writer",
            END: END,
        },
    )

    return graph


# Build and compile the graph
_graph = build_graph()
agent_graph = _graph.compile()

# Export the compiled graph
__all__ = ["agent_graph", "build_graph"]
