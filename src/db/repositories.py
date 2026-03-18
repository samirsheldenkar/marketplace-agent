"""Database repository patterns."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.database import AgentRun, Listing, ListingStatus, ScrapeRun


class ListingRepository:
    """Repository for Listing model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.

        """
        self._session = session

    async def create(
        self,
        item_type: str | None = None,
        item_description: str | None = None,
        brand: str | None = None,
        model_name: str | None = None,
        size: str | None = None,
        color: str | None = None,
        condition: str | None = None,
        condition_notes: str | None = None,
        confidence: float | None = None,
        accessories_included: list[str] | None = None,
        suggested_price: float | None = None,
        preferred_platform: str | None = None,
        platform_reasoning: str | None = None,
        image_paths: list[str] | None = None,
    ) -> Listing:
        """Create a new listing with initial status 'pending'.

        Args:
            item_type: Type of item being listed.
            item_description: Description of the item.
            brand: Brand name.
            model_name: Model name.
            size: Size of the item.
            color: Color of the item.
            condition: Condition rating.
            condition_notes: Additional condition notes.
            confidence: Confidence score for item identification.
            accessories_included: List of included accessories.
            suggested_price: Suggested listing price.
            preferred_platform: Preferred marketplace platform.
            platform_reasoning: Reasoning for platform preference.
            image_paths: List of image file paths.

        Returns:
            Created Listing instance.

        """
        listing = Listing(
            status=ListingStatus.PENDING,
            item_type=item_type,
            item_description=item_description,
            brand=brand,
            model_name=model_name,
            size=size,
            color=color,
            condition=condition,
            condition_notes=condition_notes,
            confidence=confidence,
            accessories_included=accessories_included or [],
            suggested_price=suggested_price,
            preferred_platform=preferred_platform,
            platform_reasoning=platform_reasoning,
            image_paths=image_paths or [],
        )
        self._session.add(listing)
        await self._session.flush()
        await self._session.refresh(listing)
        return listing

    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        """Get listing by UUID.

        Args:
            listing_id: UUID of the listing.

        Returns:
            Listing instance or None if not found.

        """
        stmt = (
            select(Listing)
            .options(
                selectinload(Listing.scrape_runs), selectinload(Listing.agent_runs)
            )
            .where(Listing.id == listing_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, listing_id: UUID, **kwargs: Any) -> Listing | None:
        """Update listing fields.

        Args:
            listing_id: UUID of the listing to update.
            **kwargs: Fields to update with their new values.

        Returns:
            Updated Listing instance or None if not found.

        """
        listing = await self.get_by_id(listing_id)
        if listing is None:
            return None

        for key, value in kwargs.items():
            if hasattr(listing, key):
                setattr(listing, key, value)

        listing.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(listing)
        return listing

    async def update_status(
        self, listing_id: UUID, status: ListingStatus
    ) -> Listing | None:
        """Update just the status field.

        Args:
            listing_id: UUID of the listing to update.
            status: New status value.

        Returns:
            Updated Listing instance or None if not found.

        """
        return await self.update(listing_id, status=status)

    async def update_raw_state(
        self, listing_id: UUID, raw_state: dict[str, Any]
    ) -> Listing | None:
        """Store the full LangGraph state snapshot.

        Args:
            listing_id: UUID of the listing to update.
            raw_state: Full state dictionary to store.

        Returns:
            Updated Listing instance or None if not found.

        """
        return await self.update(listing_id, raw_state=raw_state)

    async def add_scrape_run(self, scrape_run: ScrapeRun) -> None:
        """Associate a ScrapeRun with the listing.

        Args:
            scrape_run: ScrapeRun instance to associate.

        """
        self._session.add(scrape_run)
        await self._session.flush()

    async def add_agent_run(self, agent_run: AgentRun) -> None:
        """Associate an AgentRun with the listing.

        Args:
            agent_run: AgentRun instance to associate.

        """
        self._session.add(agent_run)
        await self._session.flush()

    async def list(
        self,
        status: ListingStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Listing]:
        """List all listings with optional status filter and pagination.

        Args:
            status: Optional status filter.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Listing instances.

        """
        stmt = select(Listing)
        if status is not None:
            stmt = stmt.where(Listing.status == status)
        stmt = stmt.order_by(Listing.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ScrapeRunRepository:
    """Repository for ScrapeRun model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.

        """
        self._session = session

    async def create(
        self,
        listing_id: UUID,
        source: str,
        query_string: str,
        stats: dict[str, Any] | None = None,
        raw_items: list[dict[str, Any]] | None = None,
        item_count: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> ScrapeRun:
        """Create a scrape run record.

        Args:
            listing_id: UUID of the associated listing.
            source: Source platform ("ebay" or "vinted").
            query_string: Query string used for scraping.
            stats: Statistics dictionary.
            raw_items: Raw scraped items data.
            item_count: Number of items scraped.
            duration_ms: Duration of scrape in milliseconds.
            error_message: Optional error message if scrape failed.

        Returns:
            Created ScrapeRun instance.

        """
        scrape_run = ScrapeRun(
            listing_id=listing_id,
            source=source,
            query_string=query_string,
            stats=stats,
            raw_items=raw_items,
            item_count=item_count,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        self._session.add(scrape_run)
        await self._session.flush()
        await self._session.refresh(scrape_run)
        return scrape_run

    async def get_by_id(self, scrape_run_id: UUID) -> ScrapeRun | None:
        """Get scrape run by UUID.

        Args:
            scrape_run_id: UUID of the scrape run.

        Returns:
            ScrapeRun instance or None if not found.

        """
        stmt = select(ScrapeRun).where(ScrapeRun.id == scrape_run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_listing(self, listing_id: UUID) -> list[ScrapeRun]:
        """Get all scrape runs for a listing.

        Args:
            listing_id: UUID of the listing.

        Returns:
            List of ScrapeRun instances.

        """
        stmt = (
            select(ScrapeRun)
            .where(ScrapeRun.listing_id == listing_id)
            .order_by(ScrapeRun.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_stats(
        self, scrape_run_id: UUID, stats: dict[str, Any]
    ) -> ScrapeRun | None:
        """Update the stats JSONB field.

        Args:
            scrape_run_id: UUID of the scrape run to update.
            stats: Statistics dictionary to store.

        Returns:
            Updated ScrapeRun instance or None if not found.

        """
        scrape_run = await self.get_by_id(scrape_run_id)
        if scrape_run is None:
            return None

        scrape_run.stats = stats
        await self._session.flush()
        await self._session.refresh(scrape_run)
        return scrape_run

    async def mark_error(
        self, scrape_run_id: UUID, error_message: str
    ) -> ScrapeRun | None:
        """Mark scrape run as failed with error message.

        Args:
            scrape_run_id: UUID of the scrape run to update.
            error_message: Error message to store.

        Returns:
            Updated ScrapeRun instance or None if not found.

        """
        scrape_run = await self.get_by_id(scrape_run_id)
        if scrape_run is None:
            return None

        scrape_run.error_message = error_message
        await self._session.flush()
        await self._session.refresh(scrape_run)
        return scrape_run


class AgentRunRepository:
    """Repository for AgentRun model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.

        """
        self._session = session

    async def create(
        self,
        listing_id: UUID,
        node_name: str,
        input_summary: dict[str, Any] | None = None,
        llm_model_used: str | None = None,
    ) -> AgentRun:
        """Create an agent run audit record.

        Args:
            listing_id: UUID of the associated listing.
            node_name: Name of the agent node.
            input_summary: Summary of input data.
            llm_model_used: LLM model used for this run.

        Returns:
            Created AgentRun instance.

        """
        agent_run = AgentRun(
            listing_id=listing_id,
            node_name=node_name,
            input_summary=input_summary,
            llm_model_used=llm_model_used,
            status="running",
        )
        self._session.add(agent_run)
        await self._session.flush()
        await self._session.refresh(agent_run)
        return agent_run

    async def get_by_id(self, agent_run_id: UUID) -> AgentRun | None:
        """Get agent run by UUID.

        Args:
            agent_run_id: UUID of the agent run.

        Returns:
            AgentRun instance or None if not found.

        """
        stmt = select(AgentRun).where(AgentRun.id == agent_run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_listing(self, listing_id: UUID) -> list[AgentRun]:
        """Get all agent runs for a listing.

        Args:
            listing_id: UUID of the listing.

        Returns:
            List of AgentRun instances.

        """
        stmt = (
            select(AgentRun)
            .where(AgentRun.listing_id == listing_id)
            .order_by(AgentRun.started_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def complete(
        self,
        agent_run_id: UUID,
        output_summary: dict[str, Any] | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> AgentRun | None:
        """Mark run as completed with output summary and token usage.

        Args:
            agent_run_id: UUID of the agent run to update.
            output_summary: Summary of output data.
            token_usage: Token usage statistics.

        Returns:
            Updated AgentRun instance or None if not found.

        """
        agent_run = await self.get_by_id(agent_run_id)
        if agent_run is None:
            return None

        agent_run.status = "completed"
        agent_run.completed_at = datetime.now(UTC)
        agent_run.output_summary = output_summary
        agent_run.token_usage = token_usage
        await self._session.flush()
        await self._session.refresh(agent_run)
        return agent_run

    async def mark_error(
        self, agent_run_id: UUID, error_message: str
    ) -> AgentRun | None:
        """Mark run as failed with error message.

        Args:
            agent_run_id: UUID of the agent run to update.
            error_message: Error message to store.

        Returns:
            Updated AgentRun instance or None if not found.

        """
        agent_run = await self.get_by_id(agent_run_id)
        if agent_run is None:
            return None

        agent_run.status = "failed"
        agent_run.completed_at = datetime.now(UTC)
        agent_run.error_message = error_message
        await self._session.flush()
        await self._session.refresh(agent_run)
        return agent_run
