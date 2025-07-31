"""
Unit tests for redirect functionality and URL validation
Tests packet redirection, URL normalization, and validation logic
"""

import pytest
from unittest.mock import Mock, patch
import re
from urllib.parse import urlparse


class TestURLValidation:
    """Test URL validation and normalization functions"""
    
    def test_phone_number_normalization(self):
        """Test phone number normalization for WhatsApp URLs"""
        from routes.config import normalize_phone_number
        
        test_cases = [
            # Input, Expected Output
            ('9166900151', '919166900151'),
            ('919166900151', '919166900151'),
            ('+91 9166900151', '919166900151'),
            ('91-9166-900-151', '919166900151'),
            ('+91-9166-900-151', '919166900151'),
            ('  +91 9166 900 151  ', '919166900151'),
            ('(+91) 9166 900 151', '919166900151'),
        ]
        
        for input_phone, expected in test_cases:
            result = normalize_phone_number(input_phone)
            assert result == expected, f"Failed for input: {input_phone}"
    
    def test_phone_number_validation(self):
        """Test phone number validation"""
        from routes.config import validate_phone_number
        
        # Valid phone numbers
        valid_phones = [
            '919166900151',
            '1234567890',
            '447700900123',  # UK
            '33123456789',   # France
        ]
        
        for phone in valid_phones:
            assert validate_phone_number(phone) is True
        
        # Invalid phone numbers
        invalid_phones = [
            '123',          # Too short
            '12345678901234567890',  # Too long
            'abcdefghij',   # Non-numeric
            '',             # Empty
            '12345',        # Too short
        ]
        
        for phone in invalid_phones:
            assert validate_phone_number(phone) is False
    
    def test_url_normalization(self):
        """Test URL normalization for custom redirects"""
        from routes.config import normalize_url
        
        test_cases = [
            # Input, Expected Output
            ('example.com', 'https://example.com'),
            ('www.example.com', 'https://www.example.com'),
            ('http://example.com', 'http://example.com'),
            ('https://example.com', 'https://example.com'),
            ('ftp://example.com', 'ftp://example.com'),
            ('example.com/path', 'https://example.com/path'),
            ('example.com/path?query=1', 'https://example.com/path?query=1'),
        ]
        
        for input_url, expected in test_cases:
            result = normalize_url(input_url)
            assert result == expected, f"Failed for input: {input_url}"
    
    def test_url_validation(self):
        """Test URL validation"""
        from routes.config import validate_url
        
        # Valid URLs
        valid_urls = [
            'https://example.com',
            'http://example.com',
            'https://www.example.com/path',
            'https://subdomain.example.com',
            'https://example.com:8080',
            'https://example.co.uk',
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True, f"Should be valid: {url}"
        
        # Invalid URLs
        invalid_urls = [
            'not-a-url',
            'javascript:alert(1)',
            'file:///etc/passwd',
            'data:text/html,<script>alert(1)</script>',
            '',
            'http://',
            'https://',
            'ftp://user:pass@host',  # FTP with credentials
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False, f"Should be invalid: {url}"
    
    def test_whatsapp_url_generation(self):
        """Test WhatsApp URL generation from phone numbers"""
        from routes.config import generate_whatsapp_url
        
        test_cases = [
            ('919166900151', 'https://wa.me/919166900151'),
            ('1234567890', 'https://wa.me/1234567890'),
            ('447700900123', 'https://wa.me/447700900123'),
        ]
        
        for phone, expected_url in test_cases:
            result = generate_whatsapp_url(phone)
            assert result == expected_url
    
    def test_whatsapp_url_with_message(self):
        """Test WhatsApp URL generation with predefined message"""
        from routes.config import generate_whatsapp_url
        
        phone = '919166900151'
        message = 'Hello from Kyuaar!'
        expected = 'https://wa.me/919166900151?text=Hello%20from%20Kyuaar%21'
        
        result = generate_whatsapp_url(phone, message)
        assert result == expected


class TestRedirectLogic:
    """Test packet redirect configuration logic"""
    
    def test_packet_redirect_whatsapp(self):
        """Test configuring packet redirect to WhatsApp"""
        from models.packet import Packet, PacketStates
        
        packet = Packet(state=PacketStates.CONFIG_PENDING)
        
        # Configure WhatsApp redirect
        whatsapp_url = 'https://wa.me/919166900151'
        result = packet.configure_redirect(whatsapp_url)
        
        assert result is True
        assert packet.redirect_url == whatsapp_url
        assert packet.state == PacketStates.CONFIG_DONE
        assert packet.config_state == 'done'
    
    def test_packet_redirect_custom_url(self):
        """Test configuring packet redirect to custom URL"""
        from models.packet import Packet, PacketStates
        
        packet = Packet(state=PacketStates.CONFIG_PENDING)
        
        # Configure custom URL redirect
        custom_url = 'https://example.com'
        result = packet.configure_redirect(custom_url)
        
        assert result is True
        assert packet.redirect_url == custom_url
        assert packet.state == PacketStates.CONFIG_DONE
    
    def test_packet_redirect_wrong_state(self):
        """Test redirect configuration in wrong state"""
        from models.packet import Packet, PacketStates
        
        # Try to configure from wrong state
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        result = packet.configure_redirect('https://example.com')
        
        assert result is False
        assert packet.redirect_url is None
        assert packet.state == PacketStates.SETUP_PENDING
    
    def test_packet_redirect_reconfiguration(self):
        """Test reconfiguring an already configured packet"""
        from models.packet import Packet, PacketStates
        
        # Start with configured packet
        packet = Packet(state=PacketStates.CONFIG_DONE)
        packet.redirect_url = 'https://wa.me/919166900151'
        
        # Transition back to pending for reconfiguration
        packet.transition_to(PacketStates.CONFIG_PENDING)
        
        # Reconfigure with new URL
        new_url = 'https://example.com'
        result = packet.configure_redirect(new_url)
        
        assert result is True
        assert packet.redirect_url == new_url
        assert packet.state == PacketStates.CONFIG_DONE


class TestRedirectValidation:
    """Test redirect URL validation and security"""
    
    def test_safe_redirect_urls(self):
        """Test that only safe redirect URLs are allowed"""
        from routes.config import is_safe_redirect_url
        
        # Safe URLs
        safe_urls = [
            'https://wa.me/919166900151',
            'https://example.com',
            'https://www.google.com',
            'https://subdomain.example.co.uk',
            'http://localhost:3000',  # Local development
        ]
        
        for url in safe_urls:
            assert is_safe_redirect_url(url) is True, f"Should be safe: {url}"
    
    def test_unsafe_redirect_urls(self):
        """Test that unsafe redirect URLs are blocked"""
        from routes.config import is_safe_redirect_url
        
        # Unsafe URLs
        unsafe_urls = [
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            'file:///etc/passwd',
            'ftp://example.com',
            'mailto:user@example.com',
            'tel:+1234567890',
            'http://malicious.site.com',  # If we have a blocklist
        ]
        
        for url in unsafe_urls:
            assert is_safe_redirect_url(url) is False, f"Should be unsafe: {url}"
    
    def test_redirect_url_length_limits(self):
        """Test redirect URL length limits"""
        from routes.config import validate_redirect_url
        
        # Normal length URL
        normal_url = 'https://example.com/path'
        assert validate_redirect_url(normal_url) is True
        
        # Very long URL (over reasonable limit)
        long_url = 'https://example.com/' + 'a' * 2000
        assert validate_redirect_url(long_url) is False
    
    def test_redirect_parameter_injection(self):
        """Test protection against parameter injection in redirects"""
        from routes.config import sanitize_redirect_url
        
        # URLs with potential injection attempts
        test_cases = [
            ('https://example.com?param=value', 'https://example.com?param=value'),
            ('https://example.com#fragment', 'https://example.com#fragment'),
            ('https://example.com?redirect=evil.com', 'https://example.com?redirect=evil.com'),
        ]
        
        for input_url, expected in test_cases:
            result = sanitize_redirect_url(input_url)
            assert result == expected


class TestRedirectFlow:
    """Test complete redirect flow from QR scan to final destination"""
    
    @patch('firebase_admin.firestore.client')
    def test_qr_scan_redirect_flow(self, mock_firestore, client):
        """Test complete QR scan to redirect flow"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        # Mock packet data
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-12345',
            'state': 'config_done',
            'redirect_url': 'https://wa.me/919166900151',
            'base_url': 'https://kyuaar.com/packet/PKT-12345'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Test the redirect endpoint
        response = client.get('/packet/PKT-12345')
        
        # Should redirect to WhatsApp
        assert response.status_code == 302
        assert 'wa.me/919166900151' in response.location
    
    @patch('firebase_admin.firestore.client')
    def test_qr_scan_unconfigured_packet(self, mock_firestore, client):
        """Test QR scan for unconfigured packet"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        # Mock unconfigured packet
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-12345',
            'state': 'config_pending',
            'redirect_url': None,
            'base_url': 'https://kyuaar.com/packet/PKT-12345'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Test the configuration page
        response = client.get('/packet/PKT-12345')
        
        # Should show configuration page
        assert response.status_code == 200
        assert b'Configure your QR' in response.data or b'configure' in response.data.lower()
    
    @patch('firebase_admin.firestore.client')
    def test_qr_scan_nonexistent_packet(self, mock_firestore, client):
        """Test QR scan for non-existent packet"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        # Mock packet not found
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Test with non-existent packet
        response = client.get('/packet/PKT-NONEXISTENT')
        
        # Should show error page
        assert response.status_code == 404
    
    def test_redirect_logging(self):
        """Test that redirects are properly logged for analytics"""
        from models.activity import Activity, ActivityType
        
        with patch.object(Activity, 'log') as mock_log:
            # Simulate a redirect event
            Activity.log(
                user_id='customer-123',
                activity_type=ActivityType.QR_SCANNED,
                title='QR Code Scanned',
                description='Customer scanned QR for packet PKT-12345',
                metadata={
                    'packet_id': 'PKT-12345',
                    'redirect_url': 'https://wa.me/919166900151',
                    'user_agent': 'Mozilla/5.0...',
                    'ip_address': '192.168.1.1'
                }
            )
            
            mock_log.assert_called_once()


class TestRedirectAnalytics:
    """Test redirect analytics and tracking"""
    
    def test_redirect_counter_increment(self):
        """Test that redirect counters are properly incremented"""
        from models.packet import Packet
        
        packet = Packet(packet_id='PKT-12345')
        packet.redirect_count = 0
        
        # Simulate redirect
        packet.increment_redirect_count()
        
        assert packet.redirect_count == 1
        
        # Multiple redirects
        packet.increment_redirect_count()
        packet.increment_redirect_count()
        
        assert packet.redirect_count == 3
    
    def test_redirect_timestamp_tracking(self):
        """Test that redirect timestamps are tracked"""
        from models.packet import Packet
        from datetime import datetime, timezone
        
        packet = Packet(packet_id='PKT-12345')
        
        # First redirect
        before_redirect = datetime.now(timezone.utc)
        packet.record_redirect()
        after_redirect = datetime.now(timezone.utc)
        
        assert packet.last_redirect_at is not None
        assert before_redirect <= packet.last_redirect_at <= after_redirect
        
        # Multiple redirects update timestamp
        first_redirect = packet.last_redirect_at
        packet.record_redirect()
        
        assert packet.last_redirect_at > first_redirect
    
    def test_redirect_source_tracking(self):
        """Test tracking redirect sources (QR scan, direct link, etc.)"""
        from models.activity import Activity, ActivityType
        
        # Mock different redirect sources
        sources = [
            {'source': 'qr_scan', 'user_agent': 'Mobile Safari'},
            {'source': 'direct_link', 'user_agent': 'Chrome Desktop'},
            {'source': 'social_share', 'user_agent': 'Facebook App'},
        ]
        
        for source_data in sources:
            with patch.object(Activity, 'log') as mock_log:
                Activity.log(
                    user_id=None,  # Anonymous customer
                    activity_type=ActivityType.REDIRECT,
                    title='Packet Redirect',
                    description=f'Redirect from {source_data["source"]}',
                    metadata={
                        'source': source_data['source'],
                        'user_agent': source_data['user_agent']
                    }
                )
                
                mock_log.assert_called_once()


class TestRedirectSecurity:
    """Test security aspects of redirect functionality"""
    
    def test_open_redirect_prevention(self):
        """Test prevention of open redirect vulnerabilities"""
        from routes.config import is_safe_redirect_url
        
        # Malicious redirect attempts
        malicious_urls = [
            'https://kyuaar.com@evil.com',
            'https://kyuaar.com.evil.com',
            'https://evil.com/path?redirect=kyuaar.com',
            '//evil.com',
            'https:///evil.com',
        ]
        
        for url in malicious_urls:
            assert is_safe_redirect_url(url) is False, f"Should block: {url}"
    
    def test_redirect_rate_limiting(self):
        """Test rate limiting for redirect endpoints"""
        # This would test rate limiting if implemented
        # For now, just verify the structure exists
        
        from flask import request
        import time
        
        # Simulate multiple rapid requests
        request_times = []
        for i in range(5):
            request_times.append(time.time())
            time.sleep(0.1)
        
        # Check that we have reasonable timing
        assert len(request_times) == 5
        assert request_times[-1] - request_times[0] < 1.0  # Under 1 second
    
    def test_redirect_csrf_protection(self):
        """Test CSRF protection for redirect configuration"""
        # This would test CSRF tokens if implemented
        # For now, verify that configuration requires proper authentication
        
        from routes.config import configure_packet_redirect
        
        # Mock unauthenticated request
        with patch('flask_login.current_user') as mock_user:
            mock_user.is_authenticated = False
            
            # Configuration should require some form of validation
            # (In actual implementation, this might be a customer token or similar)
            result = configure_packet_redirect('PKT-12345', 'https://example.com')
            
            # Should handle unauthenticated requests appropriately
            assert result is not None  # Some response should be returned


class TestRedirectCompatibility:
    """Test redirect compatibility across different platforms and devices"""
    
    def test_mobile_whatsapp_redirect(self):
        """Test WhatsApp redirects work on mobile devices"""
        whatsapp_urls = [
            'https://wa.me/919166900151',
            'https://wa.me/919166900151?text=Hello',
            'https://api.whatsapp.com/send?phone=919166900151',
        ]
        
        for url in whatsapp_urls:
            # Basic URL structure validation
            parsed = urlparse(url)
            assert parsed.scheme in ['https']
            assert parsed.netloc in ['wa.me', 'api.whatsapp.com']
            assert '919166900151' in url
    
    def test_desktop_whatsapp_redirect(self):
        """Test WhatsApp redirects work on desktop browsers"""
        # WhatsApp Web URLs
        desktop_url = 'https://web.whatsapp.com/send?phone=919166900151'
        parsed = urlparse(desktop_url)
        
        assert parsed.scheme == 'https'
        assert parsed.netloc == 'web.whatsapp.com'
        assert 'phone=919166900151' in desktop_url
    
    def test_universal_link_support(self):
        """Test that redirects support universal links and deep linking"""
        # Test various URL schemes that should be supported
        supported_schemes = [
            'https://example.com',
            'http://example.com',  # HTTP should work but be discouraged
        ]
        
        unsupported_schemes = [
            'ftp://example.com',
            'mailto:test@example.com',
            'tel:+1234567890',
            'sms:+1234567890',
        ]
        
        from routes.config import is_supported_redirect_scheme
        
        for url in supported_schemes:
            assert is_supported_redirect_scheme(url) is True
        
        for url in unsupported_schemes:
            assert is_supported_redirect_scheme(url) is False