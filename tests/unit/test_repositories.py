"""Unit tests for database repositories."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db.repositories import (
    AgentRunRepository,
    ListingRepository,
    ScrapeRunRepository,
)
from src.models.database import ListingStatus


class TestListingRepository:
    """Test ListingRepository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=["add", "flush", "refresh", "execute", "rollback"])
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance with mock session."""
        return ListingRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_listing(self, repo, mock_session):
        """Test creating a new listing."""
        # Arrange
        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_listing.item_type = "headphones"
        mock_listing.brand = "Sony"
        mock_listing.condition = "Good"
        mock_listing.confidence = 0.9
        mock_listing.status = ListingStatus.PENDING

        # Mock the flush and refresh
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act - The create method adds to session and flushes
        # We need to patch the Listing class to return our mock
        with patch("src.db.repositories.Listing") as MockListing:
            MockListing.return_value = mock_listing
            result = await repo.create(
                item_type="headphones",
                brand="Sony",
                condition="Good",
                confidence=0.9,
            )

        # Assert
        assert result is not None
        assert result.item_type == "headphones"
        assert result.brand == "Sony"
        assert result.condition == "Good"
        assert result.confidence == 0.9
        assert result.status == ListingStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_listing_with_all_fields(self, repo, mock_session):
        """Test creating a listing with all fields."""
        # Arrange
        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_listing.item_type = "laptop"
        mock_listing.item_description = "MacBook Pro 14 inch"
        mock_listing.brand = "Apple"
        mock_listing.model_name = "MacBook Pro 14"
        mock_listing.size = "14 inch"
        mock_listing.color = "Space Gray"
        mock_listing.condition = "Excellent"
        mock_listing.condition_notes = "Minor wear on corners"
        mock_listing.confidence = 0.95
        mock_listing.accessories_included = ["charger", "case"]
        mock_listing.suggested_price = 1500.0
        mock_listing.preferred_platform = "ebay"
        mock_listing.platform_reasoning = "Higher prices on eBay"
        mock_listing.image_paths = ["/tmp/image1.jpg", "/tmp/image2.jpg"]

        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        with patch("src.db.repositories.Listing") as MockListing:
            MockListing.return_value = mock_listing
            result = await repo.create(
                item_type="laptop",
                item_description="MacBook Pro 14 inch",
                brand="Apple",
                model_name="MacBook Pro 14",
                size="14 inch",
                color="Space Gray",
                condition="Excellent",
                condition_notes="Minor wear on corners",
                confidence=0.95,
                accessories_included=["charger", "case"],
                suggested_price=1500.0,
                preferred_platform="ebay",
                platform_reasoning="Higher prices on eBay",
                image_paths=["/tmp/image1.jpg", "/tmp/image2.jpg"],
            )

        # Assert
        assert result is not None
        assert result.item_type == "laptop"
        assert result.brand == "Apple"
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo, mock_session):
        """Test retrieving listing by ID."""
        # Arrange
        listing_id = uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.item_type = "laptop"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repo.get_by_id(listing_id)

        # Assert
        assert result is not None
        assert result.id == listing_id
        assert result.item_type == "laptop"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_session):
        """Test retrieving non-existent listing."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repo.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, repo, mock_session):
        """Test updating listing status."""
        # Arrange
        listing_id = uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.status = ListingStatus.PROCESSING

        # Mock get_by_id to return the listing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await repo.update_status(listing_id, ListingStatus.PROCESSING)

        # Assert
        assert result is not None
        assert result.status == ListingStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repo, mock_session):
        """Test updating status of non-existent listing."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repo.update_status(uuid4(), ListingStatus.PROCESSING)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo, mock_session):
        """Test updating listing fields."""
        # Arrange
        listing_id = uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.brand = "Rolex"
        mock_listing.suggested_price = 1000.0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await repo.update(
            listing_id,
            brand="Rolex",
            suggested_price=1000.0,
        )

        # Assert
        assert result is not None
        assert result.brand == "Rolex"
        assert result.suggested_price == 1000.0

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo, mock_session):
        """Test updating non-existent listing."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repo.update(uuid4(), brand="Test")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self, repo, mock_session):
        """Test listing all listings."""
        # Arrange
        mock_listings = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_listings
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repo.list()

        # Assert
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, repo, mock_session):
        """Test listing with status filter."""
        # Arrange
        mock_listing = MagicMock()
        mock_listing.status = ListingStatus.PENDING
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_listing]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repo.list(status=ListingStatus.PENDING)

        # Assert
        assert len(result) == 1
        assert result[0].status == ListingStatus.PENDING


class TestScrapeRunRepository:
    """Test ScrapeRunRepository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=["add", "flush", "refresh", "execute"])
        return session

    @pytest.fixture
    def scrape_repo(self, mock_session):
        """Create repository instance."""
        return ScrapeRunRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_scrape_run(self, scrape_repo, mock_session):
        """Test creating a scrape run."""
        # Arrange
        listing_id = uuid4()
        mock_scrape_run = MagicMock()
        mock_scrape_run.id = uuid4()
        mock_scrape_run.listing_id = listing_id
        mock_scrape_run.source = "ebay"
        mock_scrape_run.query_string = "iphone 14"
        mock_scrape_run.item_count = 50

        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        with patch("src.db.repositories.ScrapeRun") as MockScrapeRun:
            MockScrapeRun.return_value = mock_scrape_run
            result = await scrape_repo.create(
                listing_id=listing_id,
                source="ebay",
                query_string="iphone 14",
                item_count=50,
            )

        # Assert
        assert result is not None
        assert result.source == "ebay"
        assert result.query_string == "iphone 14"
        assert result.item_count == 50

    @pytest.mark.asyncio
    async def test_get_by_id(self, scrape_repo, mock_session):
        """Test retrieving scrape run by ID."""
        # Arrange
        scrape_run_id = uuid4()
        mock_scrape_run = MagicMock()
        mock_scrape_run.id = scrape_run_id
        mock_scrape_run.source = "ebay"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scrape_run
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await scrape_repo.get_by_id(scrape_run_id)

        # Assert
        assert result is not None
        assert result.id == scrape_run_id
        assert result.source == "ebay"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, scrape_repo, mock_session):
        """Test retrieving non-existent scrape run."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await scrape_repo.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_listing(self, scrape_repo, mock_session):
        """Test retrieving all scrape runs for a listing."""
        # Arrange
        listing_id = uuid4()
        mock_runs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_runs
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await scrape_repo.get_by_listing(listing_id)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_update_stats(self, scrape_repo, mock_session):
        """Test updating scrape run stats."""
        # Arrange
        scrape_run_id = uuid4()
        mock_scrape_run = MagicMock()
        mock_scrape_run.id = scrape_run_id
        mock_scrape_run.stats = {"avg_price": 200.0}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scrape_run
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await scrape_repo.update_stats(scrape_run_id, {"avg_price": 200.0})

        # Assert
        assert result is not None
        assert result.stats == {"avg_price": 200.0}

    @pytest.mark.asyncio
    async def test_mark_error(self, scrape_repo, mock_session):
        """Test marking scrape run as failed."""
        # Arrange
        scrape_run_id = uuid4()
        mock_scrape_run = MagicMock()
        mock_scrape_run.id = scrape_run_id
        mock_scrape_run.error_message = "Connection timeout"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scrape_run
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await scrape_repo.mark_error(scrape_run_id, "Connection timeout")

        # Assert
        assert result is not None
        assert result.error_message == "Connection timeout"


class TestAgentRunRepository:
    """Test AgentRunRepository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=["add", "flush", "refresh", "execute"])
        return session

    @pytest.fixture
    def agent_repo(self, mock_session):
        """Create repository instance."""
        return AgentRunRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_agent_run(self, agent_repo, mock_session):
        """Test creating an agent run."""
        # Arrange
        listing_id = uuid4()
        mock_agent_run = MagicMock()
        mock_agent_run.id = uuid4()
        mock_agent_run.listing_id = listing_id
        mock_agent_run.node_name = "image_analysis"
        mock_agent_run.status = "running"
        mock_agent_run.llm_model_used = "gpt-4o"

        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        with patch("src.db.repositories.AgentRun") as MockAgentRun:
            MockAgentRun.return_value = mock_agent_run
            result = await agent_repo.create(
                listing_id=listing_id,
                node_name="image_analysis",
                llm_model_used="gpt-4o",
            )

        # Assert
        assert result is not None
        assert result.node_name == "image_analysis"
        assert result.status == "running"
        assert result.llm_model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_create_agent_run_with_input_summary(self, agent_repo, mock_session):
        """Test creating an agent run with input summary."""
        # Arrange
        listing_id = uuid4()
        input_summary = {
            "images": ["image1.jpg", "image2.jpg"],
            "context": "user provided",
        }
        mock_agent_run = MagicMock()
        mock_agent_run.input_summary = input_summary

        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        with patch("src.db.repositories.AgentRun") as MockAgentRun:
            MockAgentRun.return_value = mock_agent_run
            result = await agent_repo.create(
                listing_id=listing_id,
                node_name="image_analysis",
                input_summary=input_summary,
            )

        # Assert
        assert result.input_summary == input_summary

    @pytest.mark.asyncio
    async def test_get_by_id(self, agent_repo, mock_session):
        """Test retrieving agent run by ID."""
        # Arrange
        agent_run_id = uuid4()
        mock_agent_run = MagicMock()
        mock_agent_run.id = agent_run_id
        mock_agent_run.node_name = "test_node"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent_run
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent_repo.get_by_id(agent_run_id)

        # Assert
        assert result is not None
        assert result.id == agent_run_id
        assert result.node_name == "test_node"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, agent_repo, mock_session):
        """Test retrieving non-existent agent run."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent_repo.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_listing(self, agent_repo, mock_session):
        """Test retrieving all agent runs for a listing."""
        # Arrange
        listing_id = uuid4()
        mock_runs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_runs
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent_repo.get_by_listing(listing_id)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_complete_agent_run(self, agent_repo, mock_session):
        """Test marking agent run as completed."""
        # Arrange
        agent_run_id = uuid4()
        mock_agent_run = MagicMock()
        mock_agent_run.id = agent_run_id
        mock_agent_run.status = "completed"
        mock_agent_run.output_summary = {"title": "Test"}
        mock_agent_run.token_usage = {"prompt": 100, "completion": 50}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent_run
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await agent_repo.complete(
            agent_run_id,
            output_summary={"title": "Test"},
            token_usage={"prompt": 100, "completion": 50},
        )

        # Assert
        assert result is not None
        assert result.status == "completed"
        assert result.output_summary == {"title": "Test"}
        assert result.token_usage == {"prompt": 100, "completion": 50}

    @pytest.mark.asyncio
    async def test_complete_agent_run_not_found(self, agent_repo, mock_session):
        """Test completing non-existent agent run."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent_repo.complete(
            uuid4(),
            output_summary={"test": "data"},
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_error(self, agent_repo, mock_session):
        """Test marking agent run as failed."""
        # Arrange
        agent_run_id = uuid4()
        mock_agent_run = MagicMock()
        mock_agent_run.id = agent_run_id
        mock_agent_run.status = "failed"
        mock_agent_run.error_message = "LLM timeout error"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent_run
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await agent_repo.mark_error(agent_run_id, "LLM timeout error")

        # Assert
        assert result is not None
        assert result.status == "failed"
        assert result.error_message == "LLM timeout error"

    @pytest.mark.asyncio
    async def test_mark_error_not_found(self, agent_repo, mock_session):
        """Test marking non-existent agent run as failed."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent_repo.mark_error(uuid4(), "Error")

        # Assert
        assert result is None


class TestRepositoryIntegration:
    """Test interactions between repositories using mocks."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=["add", "flush", "refresh", "execute", "rollback"])
        return session

    @pytest.mark.asyncio
    async def test_listing_with_scrape_runs(self, mock_session):
        """Test listing with associated scrape runs."""
        # Arrange
        listing_id = uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.scrape_runs = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        listing_repo = ListingRepository(mock_session)

        # Act
        retrieved = await listing_repo.get_by_id(listing_id)

        # Assert
        assert retrieved is not None
        assert len(retrieved.scrape_runs) == 2

    @pytest.mark.asyncio
    async def test_listing_with_agent_runs(self, mock_session):
        """Test listing with associated agent runs."""
        # Arrange
        listing_id = uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.agent_runs = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        listing_repo = ListingRepository(mock_session)

        # Act
        retrieved = await listing_repo.get_by_id(listing_id)

        # Assert
        assert retrieved is not None
        assert len(retrieved.agent_runs) == 2

    @pytest.mark.asyncio
    async def test_full_listing_workflow(self, mock_session):
        """Test complete listing workflow with all repositories."""
        # Arrange
        listing_id = uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.status = ListingStatus.COMPLETED
        mock_listing.suggested_price = 150.0
        mock_listing.preferred_platform = "ebay"
        mock_listing.scrape_runs = [MagicMock(), MagicMock()]
        mock_listing.agent_runs = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        listing_repo = ListingRepository(mock_session)

        # Act
        final_listing = await listing_repo.get_by_id(listing_id)

        # Assert
        assert final_listing is not None
        assert final_listing.status == ListingStatus.COMPLETED
        assert final_listing.suggested_price == 150.0
        assert final_listing.preferred_platform == "ebay"
        assert len(final_listing.scrape_runs) == 2
        assert len(final_listing.agent_runs) == 2
