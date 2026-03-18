"""Pricing service for calculations and recommendations."""


from src.config import Settings
from src.models.state import PriceStats


class PricingService:
    """Service for pricing calculations and recommendations."""

    def __init__(self, settings: Settings):
        """Initialize pricing service.

        Args:
            settings: Application settings

        """
        self.settings = settings

    def calculate_suggested_price(
        self,
        ebay_stats: PriceStats | None,
        vinted_stats: PriceStats | None,
        fast_sale: bool = True,
    ) -> tuple[float, str]:
        """Calculate suggested price and determine preferred platform.

        Args:
            ebay_stats: eBay price statistics
            vinted_stats: Vinted price statistics
            fast_sale: Whether to apply the quick sale discount

        Returns:
            Tuple of (suggested_price, preferred_platform)

        """
        prices = []
        volumes = {"ebay": 0, "vinted": 0}

        if ebay_stats:
            prices.append(ebay_stats["median_price"])
            volumes["ebay"] = ebay_stats["num_listings"]

        if vinted_stats:
            prices.append(vinted_stats["median_price"])
            volumes["vinted"] = vinted_stats["num_listings"]

        if not prices:
            # No data available
            return 0.0, "both"

        # Calculate average of available medians if multiple exist, else use the single available median
        overall_median = sum(prices) / len(prices)

        # Apply discount for quick sale if requested
        if fast_sale:
            discount_factor = 1 - (self.settings.price_discount_pct / 100)
            suggested_price = round(overall_median * discount_factor, 2)
        else:
            suggested_price = round(overall_median, 2)

        # Determine preferred platform
        if volumes["ebay"] > volumes["vinted"] * 2:
            preferred_platform = "ebay"
        elif volumes["vinted"] > volumes["ebay"] * 2:
            preferred_platform = "vinted"
        else:
            preferred_platform = "both"

        return suggested_price, preferred_platform
