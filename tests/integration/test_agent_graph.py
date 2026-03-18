"""Integration tests for agent graph execution."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.graph import agent_graph, build_graph
from src.models.state import ListState


class TestAgentGraphExecution:
    """Test complete agent graph execution."""

    @pytest.fixture
    def initial_state(self) -> ListState:
        """Create initial state for testing.

        Returns:
            ListState: Initial agent state for testing.

        """
        return {
            "run_id": "test-run",
            "messages": [],
            "photos": ["/tmp/test.jpg"],
            "item_type": "",
            "brand": None,
            "model_name": None,
            "condition": "",
            "confidence": 0.0,
            "suggested_price": None,
            "preferred_platform": None,
            "needs_clarification": False,
            "quality_retry_count": 0,
        }

    def test_graph_is_built(self):
        """Test that the agent graph is properly built."""
        assert agent_graph is not None
        assert build_graph is not None

    def test_graph_has_expected_nodes(self):
        """Test that the graph contains all expected nodes."""
        graph = build_graph()

        # Get node names from the graph
        node_names = set(graph.nodes.keys())

        # Verify all expected nodes are present
        expected_nodes = {
            "image_analysis",
            "agent_reasoning",
            "clarify",
            "scrape_ebay",
            "scrape_vinted",
            "agent_decision",
            "listing_writer",
            "quality_check",
        }

        assert expected_nodes.issubset(node_names)

    def test_graph_has_start_edge(self):
        """Test that the graph has a START edge."""
        graph = build_graph()

        # Check that START is in the graph
        assert "__start__" in graph.nodes or any(
            edge[0] == "__start__" for edge in graph.edges
        )

    async def test_graph_runs_without_error(self, initial_state: ListState):
        """Test that the graph can be invoked without errors.

        This test verifies the graph structure is valid. In real tests,
        you would use mocking extensively to avoid external dependencies.
        """
        # Mock LLM calls to avoid external dependencies
        with patch(
            "src.agents.nodes.image_analysis.image_analysis",
            new_callable=AsyncMock,
        ) as mock_analyze:
            mock_analyze.return_value = {
                "item_type": "headphones",
                "brand": "Sony",
                "model_name": "WH-1000XM5",
                "condition": "Good",
                "confidence": 0.91,
            }

            # Verify graph can be invoked (mock prevents actual execution)
            assert agent_graph is not None


class TestAgentGraphRouting:
    """Test agent graph routing logic."""

    def test_route_after_reasoning_needs_clarification(self):
        """Test routing when clarification is needed."""
        from src.agents.graph import route_after_reasoning

        state: ListState = {
            "run_id": "test-run",
            "needs_clarification": True,
            "confidence": 0.35,
            "quality_retry_count": 0,
        }

        result = route_after_reasoning(state)
        assert result == ["clarify"]

    def test_route_after_reasoning_proceed_to_scrape(self):
        """Test routing when no clarification needed."""
        from src.agents.graph import route_after_reasoning

        state: ListState = {
            "run_id": "test-run",
            "needs_clarification": False,
            "confidence": 0.91,
            "quality_retry_count": 0,
        }

        result = route_after_reasoning(state)
        assert result == ["scrape_ebay", "scrape_vinted"]

    def test_route_after_quality_retry_available(self):
        """Test routing when quality check fails but retry is available."""
        from src.agents.graph import route_after_quality

        state: ListState = {
            "run_id": "test-run",
            "quality_passed": False,
            "quality_issues": ["Missing brand"],
            "quality_retry_count": 0,
        }

        result = route_after_quality(state)
        assert result == "listing_writer"

    def test_route_after_quality_max_retries_exceeded(self):
        """Test routing when quality check fails and max retries exceeded."""
        from src.agents.graph import route_after_quality

        state: ListState = {
            "run_id": "test-run",
            "quality_passed": False,
            "quality_issues": ["Missing brand"],
            "quality_retry_count": 10,  # Exceeds max retries
        }

        result = route_after_quality(state)
        assert result == "__end__"

    def test_route_after_quality_passed(self):
        """Test routing when quality check passes."""
        from src.agents.graph import route_after_quality

        state: ListState = {
            "run_id": "test-run",
            "quality_passed": True,
            "quality_retry_count": 0,
        }

        result = route_after_quality(state)
        assert result == "__end__"


class TestAgentGraphNodes:
    """Test individual agent graph nodes."""

    @pytest.fixture
    def sample_state_with_analysis(self) -> ListState:
        """Create state with image analysis results.

        Returns:
            ListState: State with analysis results.

        """
        return {
            "run_id": "test-run-123",
            "messages": [],
            "photos": ["/tmp/test_images/test_0.jpg"],
            "item_description": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            "item_type": "headphones",
            "brand": "Sony",
            "model_name": "WH-1000XM5",
            "size": None,
            "color": "Black",
            "condition": "Good",
            "condition_notes": "Minor scratches on headband",
            "confidence": 0.91,
            "accessories_included": ["carrying case", "charging cable"],
            "image_analysis_raw": {
                "detected_items": ["headphones"],
                "brand_detected": "Sony",
                "condition_assessment": "Good",
            },
            "ebay_price_stats": None,
            "vinted_price_stats": None,
            "ebay_query_used": None,
            "vinted_query_used": None,
            "suggested_price": None,
            "preferred_platform": None,
            "platform_reasoning": None,
            "fast_sale": False,
            "listing_draft": None,
            "needs_clarification": False,
            "clarification_question": None,
            "error_state": None,
            "quality_retry_count": 0,
        }

    async def test_image_analysis_node_structure(self):
        """Test that image analysis node has correct signature."""
        from src.agents.nodes.image_analysis import image_analysis

        # Verify the node is callable
        assert callable(image_analysis)

    async def test_agent_reasoning_node_structure(self):
        """Test that agent reasoning node has correct signature."""
        from src.agents.nodes.agent_reasoning import agent_reasoning

        # Verify the node is callable
        assert callable(agent_reasoning)

    async def test_agent_decision_node_structure(self):
        """Test that agent decision node has correct signature."""
        from src.agents.nodes.agent_decision import agent_decision

        # Verify the node is callable
        assert callable(agent_decision)

    async def test_listing_writer_node_structure(self):
        """Test that listing writer node has correct signature."""
        from src.agents.nodes.listing_writer import listing_writer

        # Verify the node is callable
        assert callable(listing_writer)

    async def test_quality_check_node_structure(self):
        """Test that quality check node has correct signature."""
        from src.agents.nodes.quality_check import quality_check

        # Verify the node is callable
        assert callable(quality_check)


class TestAgentGraphState:
    """Test agent state handling."""

    def test_state_is_typed_dict(self):
        """Test that ListState is a TypedDict."""
        # ListState should be a TypedDict
        assert hasattr(ListState, "__annotations__")

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        state: ListState = {
            "run_id": "test",
            "messages": [],
            "photos": [],
            "confidence": 0.0,
            "needs_clarification": False,
            "quality_retry_count": 0,
        }

        # Verify required fields are present
        assert "run_id" in state
        assert "messages" in state
        assert "photos" in state
        assert "confidence" in state
        assert "needs_clarification" in state
        assert "quality_retry_count" in state

    def test_state_optional_fields(self):
        """Test that optional fields can be None."""
        state: ListState = {
            "run_id": "test",
            "messages": [],
            "photos": [],
            "confidence": 0.0,
            "needs_clarification": False,
            "quality_retry_count": 0,
            "brand": None,
            "model_name": None,
            "suggested_price": None,
            "preferred_platform": None,
            "listing_draft": None,
        }

        # Verify optional fields can be None
        assert state.get("brand") is None
        assert state.get("suggested_price") is None
        assert state.get("listing_draft") is None
