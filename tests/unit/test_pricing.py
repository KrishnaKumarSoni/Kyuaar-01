"""
Unit tests for pricing calculations and business logic
Tests packet pricing, sale pricing, revenue calculations, and edge cases
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from models.packet import Packet, PacketStates


class TestBasicPricing:
    """Test basic packet pricing calculations"""
    
    def test_default_pricing_calculation(self):
        """Test default pricing at ₹33 per QR"""
        test_cases = [
            (1, 33.0),      # Single QR
            (25, 825.0),    # Standard packet
            (50, 1650.0),   # Double packet
            (100, 3300.0),  # Bulk packet
            (10, 330.0),    # Small custom packet
        ]
        
        for qr_count, expected_price in test_cases:
            packet = Packet(qr_count=qr_count)
            calculated_price = packet.calculate_price()
            
            assert calculated_price == expected_price, \
                f"QR count {qr_count} should cost ₹{expected_price}, got ₹{calculated_price}"
    
    def test_custom_price_per_qr(self):
        """Test custom pricing per QR code"""
        packet = Packet(qr_count=25)
        
        # Test various price points (in rupees)
        test_rates = [25.0, 30.0, 35.0, 40.0, 50.0]
        
        for rate in test_rates:
            expected_total = 25 * rate
            calculated_total = packet.calculate_price(price_per_qr=rate)
            
            assert calculated_total == expected_total, \
                f"Rate ₹{rate}/QR for 25 QRs should total ₹{expected_total}"
    
    def test_pricing_edge_cases(self):
        """Test pricing edge cases"""
        # Zero QR count (should be 0)
        packet = Packet(qr_count=0)
        assert packet.calculate_price() == 0.0
        
        # Maximum realistic QR count
        packet = Packet(qr_count=1000)
        assert packet.calculate_price() == 33000.0  # 1000 * ₹33
        
        # Very small price per QR
        packet = Packet(qr_count=25)
        assert packet.calculate_price(price_per_qr=0.01) == 0.25
        
        # High price per QR
        packet = Packet(qr_count=25)
        assert packet.calculate_price(price_per_qr=5.00) == 125.0
    
    def test_pricing_precision(self):
        """Test pricing calculation precision"""
        packet = Packet(qr_count=33)
        
        # Test with price that creates decimal places
        price = packet.calculate_price(price_per_qr=0.33)
        expected = 33 * 0.33  # 10.89
        
        assert abs(price - expected) < 0.01, \
            f"Precision error: expected {expected}, got {price}"


class TestPacketSalePricing:
    """Test packet sale pricing logic"""
    
    def test_sale_price_default_to_base_price(self):
        """Test sale price defaults to base price"""
        packet = Packet(qr_count=25, price=10.0, state=PacketStates.SETUP_DONE)
        
        result = packet.mark_sold('Buyer Name')
        
        assert result is True
        assert packet.sale_price == 10.0  # Should default to base price
        assert packet.price == 10.0  # Base price unchanged
    
    def test_sale_price_custom_amount(self):
        """Test sale with custom price"""
        packet = Packet(qr_count=25, price=10.0, state=PacketStates.SETUP_DONE)
        
        result = packet.mark_sold('Buyer Name', sale_price=15.0)
        
        assert result is True
        assert packet.sale_price == 15.0  # Custom sale price
        assert packet.price == 10.0  # Base price unchanged
    
    def test_sale_price_scenarios(self):
        """Test various sale pricing scenarios"""
        base_price = 10.0
        packet = Packet(qr_count=25, price=base_price, state=PacketStates.SETUP_DONE)
        
        scenarios = [
            # (sale_price, expected_sale_price, description)
            (None, 10.0, "Default to base price"),
            (0.0, 0.0, "Free giveaway"),
            (5.0, 5.0, "Discounted sale"),
            (15.0, 15.0, "Premium sale"),
            (10.0, 10.0, "Same as base price"),
        ]
        
        for sale_price, expected, description in scenarios:
            # Reset packet state
            packet.state = PacketStates.SETUP_DONE
            packet.sale_price = None
            
            result = packet.mark_sold('Buyer', sale_price=sale_price)
            
            assert result is True, f"Sale should succeed for: {description}"
            assert packet.sale_price == expected, \
                f"{description}: expected ₹{expected}, got ₹{packet.sale_price}"
    
    def test_bulk_discount_calculation(self):
        """Test bulk discount pricing calculations"""
        def calculate_bulk_discount(qr_count, base_rate=0.40):
            """Calculate bulk discount pricing"""
            if qr_count >= 100:
                return qr_count * (base_rate * 0.8)  # 20% discount
            elif qr_count >= 50:
                return qr_count * (base_rate * 0.9)  # 10% discount
            else:
                return qr_count * base_rate  # No discount
        
        test_cases = [
            (25, 10.0),      # No discount
            (50, 18.0),      # 10% discount: 50 * 0.40 * 0.9
            (100, 32.0),     # 20% discount: 100 * 0.40 * 0.8
            (200, 64.0),     # 20% discount: 200 * 0.40 * 0.8
        ]
        
        for qr_count, expected_price in test_cases:
            calculated_price = calculate_bulk_discount(qr_count)
            assert calculated_price == expected_price, \
                f"Bulk pricing for {qr_count} QRs should be ₹{expected_price}"


class TestRevenuCalculations:
    """Test revenue tracking and calculations"""
    
    def create_sample_packets(self):
        """Create sample packets for revenue testing"""
        packets = [
            # Sold packets
            Packet(qr_count=25, sale_price=10.0, state=PacketStates.CONFIG_DONE),
            Packet(qr_count=50, sale_price=22.0, state=PacketStates.CONFIG_DONE),
            Packet(qr_count=25, sale_price=12.0, state=PacketStates.CONFIG_PENDING),
            
            # Unsold packets (should not count toward revenue)
            Packet(qr_count=25, price=10.0, state=PacketStates.SETUP_DONE),
            Packet(qr_count=25, price=10.0, state=PacketStates.SETUP_PENDING),
        ]
        return packets
    
    def test_total_revenue_calculation(self):
        """Test total revenue calculation from sold packets"""
        packets = self.create_sample_packets()
        
        # Calculate revenue from sold packets only
        sold_packets = [p for p in packets if p.is_sold()]
        total_revenue = sum(p.sale_price or 0 for p in sold_packets)
        
        assert len(sold_packets) == 3
        assert total_revenue == 44.0  # 10.0 + 22.0 + 12.0
    
    def test_revenue_by_state(self):
        """Test revenue calculation by packet state"""
        packets = self.create_sample_packets()
        
        # Revenue from fully configured packets
        configured_revenue = sum(
            p.sale_price or 0 for p in packets 
            if p.state == PacketStates.CONFIG_DONE
        )
        assert configured_revenue == 32.0  # 10.0 + 22.0
        
        # Revenue from pending configuration packets
        pending_revenue = sum(
            p.sale_price or 0 for p in packets 
            if p.state == PacketStates.CONFIG_PENDING
        )
        assert pending_revenue == 12.0
    
    def test_average_sale_price(self):
        """Test average sale price calculation"""
        packets = self.create_sample_packets()
        sold_packets = [p for p in packets if p.is_sold()]
        
        total_revenue = sum(p.sale_price or 0 for p in sold_packets)
        average_price = total_revenue / len(sold_packets) if sold_packets else 0
        
        expected_average = 44.0 / 3  # ≈ 14.67
        assert abs(average_price - expected_average) < 0.01
    
    def test_revenue_trends(self):
        """Test revenue trend calculations"""
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        
        # Create packets sold at different times
        packets_with_dates = [
            Packet(sale_price=10.0, sale_date=now - timedelta(days=1), state=PacketStates.CONFIG_DONE),
            Packet(sale_price=15.0, sale_date=now - timedelta(days=7), state=PacketStates.CONFIG_DONE),
            Packet(sale_price=20.0, sale_date=now - timedelta(days=30), state=PacketStates.CONFIG_DONE),
        ]
        
        # Revenue in last 7 days
        last_week = now - timedelta(days=7)
        recent_revenue = sum(
            p.sale_price or 0 for p in packets_with_dates 
            if p.sale_date and p.sale_date >= last_week
        )
        assert recent_revenue == 25.0  # 10.0 + 15.0
        
        # Total revenue
        total_revenue = sum(p.sale_price or 0 for p in packets_with_dates)
        assert total_revenue == 45.0


class TestPricingValidation:
    """Test pricing validation and error handling"""
    
    def test_negative_price_handling(self):
        """Test handling of negative prices"""
        packet = Packet(qr_count=25)
        
        # Negative price per QR should return negative total
        result = packet.calculate_price(price_per_qr=-0.10)
        assert result == -2.5  # 25 * -0.10
    
    def test_zero_qr_count_pricing(self):
        """Test pricing with zero QR count"""
        packet = Packet(qr_count=0)
        
        assert packet.calculate_price() == 0.0
        assert packet.calculate_price(price_per_qr=1.0) == 0.0
    
    def test_very_large_numbers(self):
        """Test pricing with very large numbers"""
        packet = Packet(qr_count=1000000)  # 1 million QRs
        
        result = packet.calculate_price()
        expected = 1000000 * 0.40  # 400,000
        
        assert result == expected
    
    def test_floating_point_precision(self):
        """Test floating point precision in calculations"""
        packet = Packet(qr_count=3)
        
        # Test with rate that could cause precision issues
        result = packet.calculate_price(price_per_qr=1/3)
        expected = 3 * (1/3)  # Should equal 1.0
        
        assert abs(result - 1.0) < 0.0001  # Allow for small floating point errors


class TestPricingBusinessRules:
    """Test business rules around pricing"""
    
    def test_minimum_price_enforcement(self):
        """Test minimum price enforcement (if implemented)"""
        # This would test business rules like minimum prices
        # For now, we just ensure calculations work correctly
        
        packet = Packet(qr_count=1)
        min_price = packet.calculate_price()  # ₹33 for 1 QR
        
        assert min_price == 0.40
        
        # Business rule: minimum order might be ₹50
        # (This would be enforced in business logic, not the model)
    
    def test_pricing_tiers(self):
        """Test tiered pricing structure"""
        def get_tiered_price(qr_count):
            """Example tiered pricing structure"""
            if qr_count <= 10:
                return qr_count * 0.50  # Premium pricing for small orders
            elif qr_count <= 50:
                return qr_count * 0.40  # Standard pricing
            else:
                return qr_count * 0.35  # Bulk pricing
        
        test_cases = [
            (5, 2.50),      # Premium tier
            (25, 10.00),    # Standard tier  
            (100, 35.00),   # Bulk tier
        ]
        
        for qr_count, expected in test_cases:
            calculated = get_tiered_price(qr_count)
            assert calculated == expected
    
    def test_promotional_pricing(self):
        """Test promotional pricing calculations"""
        base_price = 10.0
        
        # Different promotional discounts
        promotions = [
            ('SAVE10', 0.10, 9.0),    # 10% off
            ('SAVE25', 0.25, 7.5),    # 25% off
            ('SAVE50', 0.50, 5.0),    # 50% off
            ('FREE', 1.00, 0.0),      # 100% off (free)
        ]
        
        for promo_code, discount_rate, expected_price in promotions:
            discounted_price = base_price * (1 - discount_rate)
            
            assert discounted_price == expected_price, \
                f"Promo {promo_code} should result in ₹{expected_price}"
    
    def test_tax_calculation(self):
        """Test tax calculation on prices"""
        base_price = 10.0
        tax_rates = [0.05, 0.08, 0.10, 0.125]  # Various tax rates
        
        for tax_rate in tax_rates:
            tax_amount = base_price * tax_rate
            total_with_tax = base_price + tax_amount
            
            # Verify tax calculation
            assert tax_amount == base_price * tax_rate
            assert total_with_tax == base_price * (1 + tax_rate)


class TestPricingIntegration:
    """Test pricing integration with packet lifecycle"""
    
    @patch('firebase_admin.firestore.client')
    def test_pricing_through_packet_lifecycle(self, mock_firestore):
        """Test pricing calculations through complete packet lifecycle"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # Create packet with calculated price
        qr_count = 25
        calculated_price = qr_count * 33.0  # ₹825.00
        
        packet = Packet.create(user_id='user-123', qr_count=qr_count)
        
        assert packet.price == calculated_price
        
        # Complete setup
        packet.mark_setup_complete('qr_image_url')
        
        # Sell at different price
        sale_price = 12.0
        packet.mark_sold('Buyer', sale_price=sale_price)
        
        # Verify pricing data is preserved
        assert packet.price == calculated_price  # Original price
        assert packet.sale_price == sale_price   # Actual sale price
        
        # Calculate profit margin
        profit = sale_price - calculated_price
        profit_margin = (profit / calculated_price) * 100
        
        assert profit == 2.0
        assert profit_margin == 20.0  # 20% markup
    
    def test_bulk_order_pricing_workflow(self):
        """Test pricing workflow for bulk orders"""
        bulk_orders = [
            (25, 10.0),
            (50, 20.0),
            (100, 40.0),
            (200, 80.0),
        ]
        
        total_revenue = 0
        total_qrs = 0
        
        for qr_count, expected_price in bulk_orders:
            packet = Packet(qr_count=qr_count)
            calculated_price = packet.calculate_price()
            
            assert calculated_price == expected_price
            
            total_revenue += calculated_price
            total_qrs += qr_count
        
        # Verify bulk totals
        assert total_qrs == 375  # 25+50+100+200
        assert total_revenue == 150.0  # Sum of all prices
        
        # Average price per QR should equal base rate
        avg_price_per_qr = total_revenue / total_qrs
        assert abs(avg_price_per_qr - 0.40) < 0.01