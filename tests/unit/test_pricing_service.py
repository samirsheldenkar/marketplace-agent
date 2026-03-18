"""Unit tests for pricing service."""

import pytest

from src.models.state import PriceStats
from src.services.pricing_service import PricingService


class TestPricingService:
    """Test PricingService functionality."""

    @pytest.fixture
    def service(self, test_settings):
        """Create pricing service instance."""
        return PricingService(test_settings)

    @pytest.fixture
    def sample_ebay_stats(self) -> PriceStats:
        """Sample eBay price stats."""
        return PriceStats(
            num_listings=50,
            avg_price=150.0,
            median_price=145.0,
            min_price=100.0,
            max_price=200.0,
            items=[],
        )

    @pytest.fixture
    def sample_vinted_stats(self) -> PriceStats:
        """Sample Vinted price stats."""
        return PriceStats(
            num_listings=30,
            avg_price=130.0,
            median_price=125.0,
            min_price=80.0,
            max_price=200.0,
            items=[],
        )

    def test_calculate_suggested_price_ebay_only(self, service, sample_ebay_stats):
        """Test suggested price calculation with eBay data only."""
        # Arrange
        fast_sale = True

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=sample_ebay_stats,
            vinted_stats=None,
            fast_sale=fast_sale,
        )

        # Assert - Should be 10% below median (145 - 14.5 = 130.5)
        expected = round(145.0 * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)
        assert platform == "ebay"

    def test_calculate_suggested_price_vinted_only(self, service, sample_vinted_stats):
        """Test suggested price calculation with Vinted data only."""
        # Arrange
        fast_sale = True

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=None,
            vinted_stats=sample_vinted_stats,
            fast_sale=fast_sale,
        )

        # Assert - Should be 10% below median (125 - 12.5 = 112.5)
        expected = round(125.0 * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)
        assert platform == "vinted"

    def test_calculate_suggested_price_both_platforms(
        self, service, sample_ebay_stats, sample_vinted_stats
    ):
        """Test suggested price with both platforms."""
        # Arrange
        fast_sale = True

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=sample_ebay_stats,
            vinted_stats=sample_vinted_stats,
            fast_sale=fast_sale,
        )

        # Assert - Should use average of both medians, then discount
        avg_median = (145.0 + 125.0) / 2
        expected = round(avg_median * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)
        # Neither platform has > 2x volume (50 vs 30), so should be "both"
        assert platform == "both"

    def test_calculate_suggested_price_no_fast_sale(self, service, sample_ebay_stats):
        """Test suggested price without fast sale discount."""
        # Arrange
        fast_sale = False

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=sample_ebay_stats,
            vinted_stats=None,
            fast_sale=fast_sale,
        )

        # Assert - Should be median price without discount
        assert price == pytest.approx(145.0, 0.01)

    def test_calculate_suggested_price_no_data(self, service):
        """Test suggested price when no data is available."""
        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=None,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert
        assert price == 0.0
        assert platform == "both"

    def test_platform_preference_ebay_higher_volume(
        self, service, sample_ebay_stats, sample_vinted_stats
    ):
        """Test platform selection when volumes are similar."""
        # Arrange - eBay has 50 listings, Vinted has 30
        # Neither has > 2x the other's volume, so should be "both"

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=sample_ebay_stats,
            vinted_stats=sample_vinted_stats,
            fast_sale=False,
        )

        # Assert - Neither platform has > 2x volume
        assert platform == "both"

    def test_platform_preference_vinted_higher_volume(self, service):
        """Test platform selection favors Vinted when volume is much higher."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=10,
            avg_price=50.0,
            median_price=45.0,
            min_price=20.0,
            max_price=100.0,
            items=[],
        )
        vinted_stats = PriceStats(
            num_listings=100,
            avg_price=55.0,
            median_price=50.0,
            min_price=25.0,
            max_price=120.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=vinted_stats,
            fast_sale=False,
        )

        # Assert - Vinted has 100 listings, eBay has 10 (100 > 10 * 2)
        assert platform == "vinted"

    def test_platform_preference_balanced(self, service):
        """Test platform selection returns 'both' when volumes are similar."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=50,
            avg_price=100.0,
            median_price=95.0,
            min_price=50.0,
            max_price=150.0,
            items=[],
        )
        vinted_stats = PriceStats(
            num_listings=60,
            avg_price=105.0,
            median_price=100.0,
            min_price=55.0,
            max_price=160.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=vinted_stats,
            fast_sale=False,
        )

        # Assert - Neither platform has > 2x the volume
        assert platform == "both"

    def test_calculate_suggested_price_custom_discount(self, service):
        """Test suggested price with custom discount percentage."""
        # Arrange - Settings has price_discount_pct=10.0
        ebay_stats = PriceStats(
            num_listings=20,
            avg_price=100.0,
            median_price=100.0,
            min_price=80.0,
            max_price=120.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert - 10% discount from 100
        assert price == pytest.approx(90.0, 0.01)

    def test_calculate_suggested_price_rounding(self, service):
        """Test that suggested price is properly rounded."""
        # Arrange - Use median that would create many decimal places
        ebay_stats = PriceStats(
            num_listings=10,
            avg_price=100.0,
            median_price=99.99,
            min_price=80.0,
            max_price=120.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert - Should be rounded to 2 decimal places
        expected = round(99.99 * 0.9, 2)
        assert price == expected
        # Check it has at most 2 decimal places
        assert len(str(price).split(".")[-1]) <= 2

    def test_calculate_suggested_price_zero_median(self, service):
        """Test suggested price when median is zero."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=10,
            avg_price=0.0,
            median_price=0.0,
            min_price=0.0,
            max_price=0.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert
        assert price == 0.0

    def test_platform_preference_ebay_exactly_2x(self, service):
        """Test platform selection when eBay is exactly 2x Vinted volume."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=60,
            avg_price=100.0,
            median_price=100.0,
            min_price=80.0,
            max_price=120.0,
            items=[],
        )
        vinted_stats = PriceStats(
            num_listings=30,
            avg_price=100.0,
            median_price=100.0,
            min_price=80.0,
            max_price=120.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=vinted_stats,
            fast_sale=False,
        )

        # Assert - 60 > 30 * 2 is false, so should be "both"
        assert platform == "both"

    def test_platform_preference_vinted_exactly_2x(self, service):
        """Test platform selection when Vinted is exactly 2x eBay volume."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=30,
            avg_price=100.0,
            median_price=100.0,
            min_price=80.0,
            max_price=120.0,
            items=[],
        )
        vinted_stats = PriceStats(
            num_listings=60,
            avg_price=100.0,
            median_price=100.0,
            min_price=80.0,
            max_price=120.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=vinted_stats,
            fast_sale=False,
        )

        # Assert - 60 > 30 * 2 is false, so should be "both"
        assert platform == "both"


class TestPricingServicePriceCalculations:
    """Test price calculation edge cases."""

    @pytest.fixture
    def service(self, test_settings):
        """Create pricing service instance."""
        return PricingService(test_settings)

    def test_high_value_items(self, service):
        """Test pricing for high-value items."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=20,
            avg_price=5000.0,
            median_price=4800.0,
            min_price=4000.0,
            max_price=6000.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert
        expected = round(4800.0 * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)

    def test_low_value_items(self, service):
        """Test pricing for low-value items."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=100,
            avg_price=5.0,
            median_price=4.50,
            min_price=1.0,
            max_price=10.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert
        expected = round(4.50 * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)

    def test_single_listing(self, service):
        """Test pricing when only one listing exists."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=1,
            avg_price=100.0,
            median_price=100.0,
            min_price=100.0,
            max_price=100.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert
        expected = round(100.0 * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)

    def test_very_different_medians(self, service):
        """Test pricing when eBay and Vinted have very different medians."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=50,
            avg_price=200.0,
            median_price=200.0,
            min_price=150.0,
            max_price=250.0,
            items=[],
        )
        vinted_stats = PriceStats(
            num_listings=50,
            avg_price=50.0,
            median_price=50.0,
            min_price=30.0,
            max_price=80.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=vinted_stats,
            fast_sale=True,
        )

        # Assert - Average of medians: (200 + 50) / 2 = 125, then 10% discount
        avg_median = (200.0 + 50.0) / 2
        expected = round(avg_median * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)
        # Equal volumes, so "both"
        assert platform == "both"

    def test_fast_sale_false_no_discount(self, service):
        """Test that fast_sale=False applies no discount."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=50,
            avg_price=150.0,
            median_price=145.0,
            min_price=100.0,
            max_price=200.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=False,
        )

        # Assert - No discount applied
        assert price == pytest.approx(145.0, 0.01)

    def test_fast_sale_true_applies_discount(self, service):
        """Test that fast_sale=True applies discount."""
        # Arrange
        ebay_stats = PriceStats(
            num_listings=50,
            avg_price=150.0,
            median_price=145.0,
            min_price=100.0,
            max_price=200.0,
            items=[],
        )

        # Act
        price, platform = service.calculate_suggested_price(
            ebay_stats=ebay_stats,
            vinted_stats=None,
            fast_sale=True,
        )

        # Assert - 10% discount applied
        expected = round(145.0 * 0.9, 2)
        assert price == pytest.approx(expected, 0.01)
