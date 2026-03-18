"""Database repository patterns."""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
        item_type: Optional[str] = None,
        item_description: Optional[str] = None,
        brand: Optional[str] = None,
        model_name: Optional[str] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        condition: Optional[str] = None,
        condition_notes: Optional[str] = None,
        confidence: Optional[float] = None,
        accessories_included: Optional[List[str]] = None,
        suggested_price: Optional[float] = None,
        preferred_platform: Optional[str] = None,
        platform_reasoning: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
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

    async def get_by_id(self, listing_id: UUID) -> Optional[Listing]:
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

    async def update(self, listing_id: UUID, **kwargs: Any) -> Optional[Listing]:
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

        listing.updated_at = datetime.utcnow()
        await self._session.flush()
        await self._session.refresh(listing)
        return listing

    async def update_status(
        self, listing_id: UUID, status: ListingStatus
    ) -> Optional[Listing]:
        """Update just the status field.

        Args:
            listing_id: UUID of the listing to update.
            status: New status value.

        Returns:
            Updated Listing instance or None if not found.
        """
        return await self.update(listing_id, status=status)

    async def update_raw_state(
        self, listing_id: UUID, raw_state: Dict[str, Any]
    ) -> Optional[Listing]:
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
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Listing]:
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
        stats: Optional[Dict[str, Any]] = None,
        raw_items: Optional[List[Dict[str, Any]]] = None,
        item_count: Optional[int] = None,
        duration_ms: Optional[int] = None,
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
        )
        self._session.add(scrape_run)
        await self._session.flush()
        await self._session.refresh(scrape_run)
        return scrape_run

    async def get_by_id(self, scrape_run_id: UUID) -> Optional[ScrapeRun]:
        """Get scrape run by UUID.

        Args:
            scrape_run_id: UUID of the scrape run.

        Returns:
            ScrapeRun instance or None if not found.
        """
        stmt = select(ScrapeRun).where(ScrapeRun.id == scrape_run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_listing(self, listing_id: UUID) -> List[ScrapeRun]:
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
        self, scrape_run_id: UUID, stats: Dict[str, Any]
    ) -> Optional[ScrapeRun]:
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
    ) -> Optional[ScrapeRun]:
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
        input_summary: Optional[Dict[str, Any]] = None,
        llm_model_used: Optional[str] = None,
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

    async def get_by_id(self, agent_run_id: UUID) -> Optional[AgentRun]:
        """Get agent run by UUID.

        Args:
            agent_run_id: UUID of the agent run.

        Returns:
            AgentRun instance or None if not found.
        """
        stmt = select(AgentRun).where(AgentRun.id == agent_run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_listing(self, listing_id: UUID) -> List[AgentRun]:
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
        output_summary: Optional[Dict[str, Any]] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> Optional[AgentRun]:
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
        agent_run.completed_at = datetime.utcnow()
        agent_run.output_summary = output_summary
        agent_run.token_usage = token_usage
        await self._session.flush()
        await self._session.refresh(agent_run)
        return agent_run

    async def mark_error(
        self, agent_run_id: UUID, error_message: str
    ) -> Optional[AgentRun]:
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
        agent_run.completed_at = datetime.utcnow()
        agent_run.error_message = error_message
        await self._session.flush()
        await self._session.refresh(agent_run)
        return agent_run
