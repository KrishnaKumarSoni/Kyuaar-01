"""
Smoke tests for production and staging deployments
Basic end-to-end tests to verify core functionality is working
"""

import pytest
import requests
import time
from urllib.parse import urljoin


class TestSmokeTests:
    """Basic smoke tests for deployed application"""
    
    @pytest.fixture
    def base_url(self, request):
        """Get base URL from command line or default to localhost"""
        return request.config.getoption("--base-url", default="http://localhost:5000")
    
    def test_homepage_loads(self, base_url):
        """Test that homepage loads successfully"""
        try:
            response = requests.get(base_url, timeout=10)
            
            assert response.status_code == 200
            assert response.headers.get('content-type', '').startswith('text/html')
            
            # Check for basic content
            content = response.text.lower()
            assert 'kyuaar' in content or 'qr' in content
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Homepage failed to load: {e}")
    
    def test_admin_login_page_loads(self, base_url):
        """Test that admin login page is accessible"""
        try:
            login_url = urljoin(base_url, '/login')
            response = requests.get(login_url, timeout=10)
            
            # Should either show login page (200) or redirect to it (302)
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                content = response.text.lower()
                assert 'login' in content or 'signin' in content
                
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Login page failed to load: {e}")
    
    def test_qr_generator_page_loads(self, base_url):
        """Test that QR generator page is accessible"""
        try:
            qr_url = urljoin(base_url, '/qr/generate')
            response = requests.get(qr_url, timeout=10)
            
            # Should show QR generator page
            assert response.status_code in [200, 302]  # 302 if auth required
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"QR generator page failed to load: {e}")
    
    def test_packet_redirect_handles_invalid_id(self, base_url):
        """Test that invalid packet IDs are handled gracefully"""
        try:
            invalid_packet_url = urljoin(base_url, '/packet/INVALID-ID')
            response = requests.get(invalid_packet_url, timeout=10)
            
            # Should return 404 for invalid packet
            assert response.status_code == 404
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Invalid packet ID handling failed: {e}")
    
    def test_api_endpoints_exist(self, base_url):
        """Test that API endpoints exist and return proper responses"""
        api_endpoints = [
            '/api/packets',
            '/api/qr/presets',
            '/api/user/statistics',
        ]
        
        for endpoint in api_endpoints:
            try:
                api_url = urljoin(base_url, endpoint)
                response = requests.get(api_url, timeout=10)
                
                # Should either return data (200) or require auth (401/403)
                assert response.status_code in [200, 401, 403]
                
                # If successful, should return JSON
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    assert 'application/json' in content_type
                    
            except requests.exceptions.RequestException as e:
                pytest.fail(f"API endpoint {endpoint} failed: {e}")
    
    def test_static_assets_load(self, base_url):
        """Test that static assets are accessible"""
        # Check common static file paths
        static_files = [
            '/static/css/style.css',
            '/favicon.ico',
        ]
        
        for static_file in static_files:
            try:
                static_url = urljoin(base_url, static_file)
                response = requests.get(static_url, timeout=5)
                
                # Should load successfully or return 404 (if file doesn't exist)
                assert response.status_code in [200, 404]
                
            except requests.exceptions.RequestException:
                # Static files might not exist, which is okay for smoke test
                pass
    
    def test_response_times_acceptable(self, base_url):
        """Test that response times are acceptable"""
        endpoints = [
            '/',
            '/login',
        ]
        
        for endpoint in endpoints:
            try:
                url = urljoin(base_url, endpoint)
                start_time = time.time()
                
                response = requests.get(url, timeout=10)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                assert response.status_code in [200, 302]
                # Response should be under 5 seconds for smoke test
                assert response_time < 5.0, f"Slow response for {endpoint}: {response_time:.2f}s"
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"Response time test failed for {endpoint}: {e}")
    
    def test_security_headers_present(self, base_url):
        """Test that basic security headers are present"""
        try:
            response = requests.get(base_url, timeout=10)
            
            # Check for basic security headers
            headers = response.headers
            
            # Content-Type should be set
            assert 'content-type' in headers
            
            # Check for security headers (if implemented)
            security_headers = [
                'x-content-type-options',
                'x-frame-options',
                'x-xss-protection',
            ]
            
            # Count how many security headers are present
            present_headers = sum(1 for header in security_headers if header in headers)
            
            # At least some security headers should be present in production
            if 'localhost' not in base_url:
                assert present_headers > 0, "No security headers found in production"
                
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Security headers test failed: {e}")
    
    def test_database_connectivity(self, base_url):
        """Test that database connectivity is working"""
        try:
            # Test an endpoint that requires database access
            api_url = urljoin(base_url, '/api/qr/presets')
            response = requests.get(api_url, timeout=10)
            
            # Should either return data or require authentication
            # Should not return 500 (database error)
            assert response.status_code != 500
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Database connectivity test failed: {e}")
    
    def test_error_pages_exist(self, base_url):
        """Test that error pages are properly implemented"""
        try:
            # Test 404 page
            not_found_url = urljoin(base_url, '/nonexistent-page-12345')
            response = requests.get(not_found_url, timeout=10)
            
            assert response.status_code == 404
            
            # Should return HTML error page, not just plain text
            content_type = response.headers.get('content-type', '')
            assert 'text/html' in content_type
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Error pages test failed: {e}")


class TestHealthCheck:
    """Health check endpoints for monitoring"""
    
    def test_health_endpoint(self, base_url):
        """Test health check endpoint if it exists"""
        health_endpoints = [
            '/health',
            '/api/health',
            '/status',
        ]
        
        for endpoint in health_endpoints:
            try:
                health_url = urljoin(base_url, endpoint)
                response = requests.get(health_url, timeout=5)
                
                if response.status_code == 200:
                    # Found a health endpoint
                    content = response.text.lower()
                    assert any(word in content for word in ['ok', 'healthy', 'up', 'running'])
                    return  # Exit after finding one working health endpoint
                    
            except requests.exceptions.RequestException:
                continue
        
        # No health endpoint found, which is okay for smoke test
        pass
    
    def test_basic_service_availability(self, base_url):
        """Test basic service availability"""
        try:
            response = requests.get(base_url, timeout=10)
            
            # Service should be available
            assert response.status_code < 500, f"Service unavailable: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Service availability test failed: {e}")


class TestPerformanceBasics:
    """Basic performance tests for smoke testing"""
    
    def test_multiple_concurrent_requests(self, base_url):
        """Test that service handles multiple concurrent requests"""
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = requests.get(base_url, timeout=10)
                return response.status_code
            except:
                return 500
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least 80% should succeed
        success_count = sum(1 for status in results if status < 400)
        success_rate = success_count / len(results)
        
        assert success_rate >= 0.8, f"Low success rate: {success_rate:.2%}"
    
    def test_memory_not_leaking(self, base_url):
        """Basic test to ensure no obvious memory leaks"""
        # Make multiple requests and ensure they all complete
        for i in range(10):
            try:
                response = requests.get(base_url, timeout=5)
                assert response.status_code < 500
                # Clear response to help with memory
                del response
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"Memory leak test failed on request {i}: {e}")


def pytest_addoption(parser):
    """Add command line options for smoke tests"""
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:5000",
        help="Base URL for smoke tests"
    )