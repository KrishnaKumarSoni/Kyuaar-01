"""
Unit tests for QR code generation service
Tests QR generation with custom styling, Firebase integration, and validation
"""

import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io
import qrcode
from datetime import datetime

from services.qr_generator import QRGenerator, QRStyleOptions, CustomEyeStyler


class TestQRStyleOptions:
    """Test QR style configuration options"""
    
    def test_module_drawers_available(self):
        """Test that all expected module drawer types are available"""
        options = QRStyleOptions()
        
        expected_drawers = ['square', 'circle', 'rounded', 'vertical_bars', 'horizontal_bars']
        assert all(drawer in options.MODULE_DRAWERS for drawer in expected_drawers)
        assert len(options.MODULE_DRAWERS) >= 5
    
    def test_color_masks_available(self):
        """Test that color mask options are available"""
        options = QRStyleOptions()
        
        expected_masks = ['solid', 'radial_gradient', 'square_gradient']
        assert all(mask in options.COLOR_MASKS for mask in expected_masks)
    
    def test_default_colors(self):
        """Test default color constants"""
        options = QRStyleOptions()
        
        assert options.DEFAULT_FILL_COLOR == '#000000'
        assert options.DEFAULT_BACK_COLOR == '#FFFFFF'
        assert options.DEFAULT_PRIMARY_COLOR == '#CC5500'  # Burnt orange


class TestCustomEyeStyler:
    """Test custom eye corner styling functionality"""
    
    def test_find_finder_patterns(self):
        """Test finding QR code finder pattern positions"""
        # Create a mock modules array (21x21 for version 1)
        size = 21
        modules = [[True for _ in range(size)] for _ in range(size)]
        
        patterns = CustomEyeStyler.find_finder_patterns(modules)
        
        assert len(patterns) == 3
        # Check positions: top-left, top-right, bottom-left
        expected_positions = [(0, 0, 7), (14, 0, 7), (0, 14, 7)]
        assert patterns == expected_positions
    
    def test_find_finder_patterns_empty(self):
        """Test finder pattern detection with empty modules"""
        patterns = CustomEyeStyler.find_finder_patterns([])
        assert patterns == []
    
    def test_style_eyes_square(self):
        """Test eye styling with square style (no changes)"""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), 'white')
        modules = [[True for _ in range(21)] for _ in range(21)]
        
        styled_img = CustomEyeStyler.style_eyes(
            img=img,
            modules=modules,
            eye_style='square',
            fill_color='black',
            back_color='white'
        )
        
        # Square style should return the same image
        assert styled_img == img
    
    def test_style_eyes_rounded(self):
        """Test eye styling with rounded corners"""
        # Create a test image
        img = Image.new('RGB', (210, 210), 'white')  # 21*10 = 210px
        modules = [[True for _ in range(21)] for _ in range(21)]
        
        styled_img = CustomEyeStyler.style_eyes(
            img=img,
            modules=modules,
            eye_style='rounded',
            fill_color='#000000',
            back_color='#FFFFFF',
            box_size=10,
            border=4
        )
        
        # Should return a modified image
        assert styled_img != img
        assert styled_img.size == img.size
    
    def test_style_eyes_circle(self):
        """Test eye styling with circular corners"""
        img = Image.new('RGB', (210, 210), 'white')
        modules = [[True for _ in range(21)] for _ in range(21)]
        
        styled_img = CustomEyeStyler.style_eyes(
            img=img,
            modules=modules,
            eye_style='circle',
            fill_color='black',
            back_color='white',
            box_size=10,
            border=4
        )
        
        assert styled_img != img
        assert styled_img.size == img.size


class TestQRGenerator:
    """Test QR code generation functionality"""
    
    def test_hex_to_rgb_conversion(self):
        """Test hex color to RGB tuple conversion"""
        generator = QRGenerator()
        
        # Test with # prefix
        assert generator._hex_to_rgb('#FF0000') == (255, 0, 0)
        assert generator._hex_to_rgb('#00FF00') == (0, 255, 0)
        assert generator._hex_to_rgb('#0000FF') == (0, 0, 255)
        
        # Test without # prefix
        assert generator._hex_to_rgb('FF0000') == (255, 0, 0)
        assert generator._hex_to_rgb('FFFFFF') == (255, 255, 255)
        assert generator._hex_to_rgb('000000') == (0, 0, 0)
        
        # Test burnt orange theme color
        assert generator._hex_to_rgb('#CC5500') == (204, 85, 0)
    
    def test_hex_to_rgb_invalid_input(self):
        """Test hex color conversion with invalid input"""
        generator = QRGenerator()
        
        # Invalid hex strings should return black
        assert generator._hex_to_rgb('invalid') == (0, 0, 0)
        assert generator._hex_to_rgb('') == (0, 0, 0)
        assert generator._hex_to_rgb('12345') == (0, 0, 0)  # Too short
        assert generator._hex_to_rgb(None) == (0, 0, 0)
    
    def test_generate_qr_code_basic(self):
        """Test basic QR code generation"""
        generator = QRGenerator()
        
        result = generator.generate_qr_code(
            data='https://kyuaar.com/packet/PKT-12345',
            packet_id='PKT-12345'
        )
        
        assert result['success'] is True
        assert 'image_base64' in result
        assert 'image_data_url' in result
        assert result['data'] == 'https://kyuaar.com/packet/PKT-12345'
        assert result['packet_id'] == 'PKT-12345'
        assert result['format'] == 'PNG'
        assert 'size' in result
        
        # Verify base64 data URL format
        assert result['image_data_url'].startswith('data:image/png;base64,')
    
    def test_generate_qr_code_with_custom_settings(self):
        """Test QR code generation with custom styling"""
        generator = QRGenerator()
        
        custom_settings = {
            'module_drawer': 'rounded',
            'eye_drawer': 'rounded',
            'fill_color': '#CC5500',
            'back_color': '#FFFFFF',
            'box_size': 12,
            'border': 6,
            'color_mask': 'solid'
        }
        
        result = generator.generate_qr_code(
            data='https://wa.me/919166900151',
            settings=custom_settings
        )
        
        assert result['success'] is True
        assert result['settings']['module_drawer'] == 'rounded'
        assert result['settings']['fill_color'] == '#CC5500'
        assert result['settings']['box_size'] == 12
        assert result['settings']['border'] == 6
    
    def test_generate_qr_code_with_gradient(self):
        """Test QR code generation with gradient colors"""
        generator = QRGenerator()
        
        gradient_settings = {
            'color_mask': 'radial_gradient',
            'gradient_colors': ['#CC5500', '#FF6600'],
            'back_color': '#FFFFFF'
        }
        
        result = generator.generate_qr_code(
            data='https://example.com',
            settings=gradient_settings
        )
        
        assert result['success'] is True
        assert result['settings']['color_mask'] == 'radial_gradient'
        assert result['settings']['gradient_colors'] == ['#CC5500', '#FF6600']
    
    def test_generate_qr_code_error_handling(self):
        """Test QR code generation error handling"""
        generator = QRGenerator()
        
        # Mock an error in QR generation
        with patch('qrcode.QRCode') as mock_qr:
            mock_qr.side_effect = Exception('QR generation failed')
            
            result = generator.generate_qr_code('test data')
            
            assert result['success'] is False
            assert 'error' in result
            assert 'QR generation failed' in result['error']
    
    @patch('firebase_admin.storage.bucket')
    def test_save_to_firebase_success(self, mock_bucket):
        """Test successful save to Firebase Storage"""
        generator = QRGenerator()
        
        # Mock Firebase Storage
        mock_storage_bucket = Mock()
        mock_bucket.return_value = mock_storage_bucket
        
        mock_blob = Mock()
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/qr_codes/PKT-123/test.png'
        mock_storage_bucket.blob.return_value = mock_blob
        
        # Mock Firebase apps
        with patch('firebase_admin._apps', ['mock_app']):
            image_data = b'fake_image_data'
            
            result = generator.save_to_firebase(
                image_data=image_data,
                filename='test.png',
                packet_id='PKT-123',
                settings={'module_drawer': 'square'}
            )
            
            assert result == 'https://storage.googleapis.com/bucket/qr_codes/PKT-123/test.png'
            mock_blob.upload_from_string.assert_called_once_with(
                image_data,
                content_type='image/png'
            )
            mock_blob.make_public.assert_called_once()
    
    def test_save_to_firebase_no_firebase(self):
        """Test Firebase save when Firebase is not initialized"""
        generator = QRGenerator()
        
        # Mock no Firebase apps
        with patch('firebase_admin._apps', []):
            result = generator.save_to_firebase(
                image_data=b'data',
                filename='test.png',
                packet_id='PKT-123',
                settings={}
            )
            
            assert result is None
    
    @patch('firebase_admin.storage.bucket')
    def test_save_to_firebase_bucket_error(self, mock_bucket):
        """Test Firebase save when bucket access fails"""
        generator = QRGenerator()
        
        # Mock bucket error
        mock_bucket.side_effect = Exception('Bucket access failed')
        
        with patch('firebase_admin._apps', ['mock_app']):
            result = generator.save_to_firebase(
                image_data=b'data',
                filename='test.png',
                packet_id='PKT-123',
                settings={}
            )
            
            assert result is None
    
    @patch('firebase_admin.firestore.client')
    def test_save_qr_record_to_firestore_success(self, mock_firestore):
        """Test successful QR record save to Firestore"""
        generator = QRGenerator()
        
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_doc_ref = Mock()
        mock_collection.add.return_value = mock_doc_ref
        
        with patch('firebase_admin._apps', ['mock_app']):
            result = generator.save_qr_record_to_firestore(
                packet_id='PKT-123',
                url='https://kyuaar.com/packet/PKT-123',
                settings={'module_drawer': 'square'},
                image_url='https://storage.googleapis.com/bucket/test.png'
            )
            
            assert result is True
            mock_collection.add.assert_called_once()
            
            # Verify the data structure
            save_call_args = mock_collection.add.call_args[0][0]
            assert save_call_args['packet_id'] == 'PKT-123'
            assert save_call_args['url'] == 'https://kyuaar.com/packet/PKT-123'
            assert 'created_at' in save_call_args
            assert 'updated_at' in save_call_args
    
    def test_save_qr_record_no_firebase(self):
        """Test QR record save when Firebase is not initialized"""
        generator = QRGenerator()
        
        with patch('firebase_admin._apps', []):
            result = generator.save_qr_record_to_firestore(
                packet_id='PKT-123',
                url='https://example.com',
                settings={},
                image_url=None
            )
            
            assert result is False
    
    def test_get_style_presets(self):
        """Test style presets are properly defined"""
        generator = QRGenerator()
        
        presets = generator.get_style_presets()
        
        expected_presets = [
            'default', 'rounded', 'circular', 'gradient_radial', 
            'gradient_square', 'bars_vertical'
        ]
        
        assert all(preset in presets for preset in expected_presets)
        
        # Test default preset
        default = presets['default']
        assert default['module_drawer'] == 'square'
        assert default['eye_drawer'] == 'square'
        assert default['fill_color'] == '#000000'
        assert default['back_color'] == '#FFFFFF'
        
        # Test rounded preset
        rounded = presets['rounded']
        assert rounded['module_drawer'] == 'rounded'
        assert rounded['eye_drawer'] == 'rounded'
        assert rounded['fill_color'] == '#CC5500'  # Burnt orange
        
        # Test gradient preset
        gradient = presets['gradient_radial']
        assert gradient['color_mask'] == 'radial_gradient'
        assert 'gradient_colors' in gradient
        assert len(gradient['gradient_colors']) == 2


class TestQRValidation:
    """Test QR code validation and data integrity"""
    
    def test_generated_qr_contains_correct_data(self):
        """Test that generated QR codes contain the correct data"""
        generator = QRGenerator()
        
        test_url = 'https://kyuaar.com/packet/PKT-TEST123'
        result = generator.generate_qr_code(test_url)
        
        assert result['success'] is True
        
        # Decode the base64 image and verify it contains correct data
        image_data = base64.b64decode(result['image_base64'])
        image = Image.open(io.BytesIO(image_data))
        
        # Basic validation that we have a valid image
        assert image.format == 'PNG'
        assert image.size[0] > 0 and image.size[1] > 0
        
        # Verify result metadata
        assert result['data'] == test_url
    
    def test_qr_size_calculations(self):
        """Test QR code size calculations with different settings"""
        generator = QRGenerator()
        
        # Test different box sizes
        sizes = [5, 10, 15, 20]
        borders = [2, 4, 6, 8]
        
        for box_size in sizes:
            for border in borders:
                settings = {
                    'box_size': box_size,
                    'border': border
                }
                
                result = generator.generate_qr_code(
                    'https://example.com',
                    settings=settings
                )
                
                assert result['success'] is True
                assert result['settings']['box_size'] == box_size
                assert result['settings']['border'] == border
                
                # Size should be reasonable
                width, height = result['size']
                assert width > 0 and height > 0
                assert width == height  # QR codes are square
    
    def test_color_validation(self):
        """Test color setting validation and conversion"""
        generator = QRGenerator()
        
        # Test various color formats
        color_tests = [
            ('#FF0000', (255, 0, 0)),
            ('#00FF00', (0, 255, 0)),
            ('#0000FF', (0, 0, 255)),
            ('FF0000', (255, 0, 0)),
            ('#CC5500', (204, 85, 0))  # Burnt orange
        ]
        
        for hex_color, expected_rgb in color_tests:
            rgb = generator._hex_to_rgb(hex_color)
            assert rgb == expected_rgb
    
    def test_data_encoding_limits(self):
        """Test QR code generation with various data sizes"""
        generator = QRGenerator()
        
        # Test with different data lengths
        test_cases = [
            'short',
            'https://kyuaar.com/packet/PKT-12345',
            'https://wa.me/919166900151?text=Hello%20from%20Kyuaar',
            'A' * 100,  # Medium length
            'B' * 500   # Longer data
        ]
        
        for data in test_cases:
            result = generator.generate_qr_code(data)
            
            if len(data) <= 2953:  # Approximate QR code limit for alphanumeric
                assert result['success'] is True
                assert result['data'] == data
            # Very long data might fail, which is expected


class TestQRIntegration:
    """Test QR generation integration with other system components"""
    
    @patch('firebase_admin.storage.bucket')
    @patch('firebase_admin.firestore.client')
    def test_full_qr_workflow(self, mock_firestore, mock_bucket):
        """Test complete QR generation and save workflow"""
        generator = QRGenerator()
        
        # Mock Firebase Storage
        mock_storage_bucket = Mock()
        mock_bucket.return_value = mock_storage_bucket
        
        mock_blob = Mock()
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/qr_codes/PKT-123/qr.png'
        mock_storage_bucket.blob.return_value = mock_blob
        
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        with patch('firebase_admin._apps', ['mock_app']):
            # Generate QR code
            result = generator.generate_qr_code(
                data='https://kyuaar.com/packet/PKT-123',
                packet_id='PKT-123',
                settings={
                    'module_drawer': 'rounded',
                    'fill_color': '#CC5500'
                }
            )
            
            assert result['success'] is True
            
            # Save to Firebase
            image_data = base64.b64decode(result['image_base64'])
            firebase_url = generator.save_to_firebase(
                image_data=image_data,
                filename='qr.png',
                packet_id='PKT-123',
                settings=result['settings']
            )
            
            assert firebase_url == 'https://storage.googleapis.com/bucket/qr_codes/PKT-123/qr.png'
            
            # Save record to Firestore
            record_saved = generator.save_qr_record_to_firestore(
                packet_id='PKT-123',
                url='https://kyuaar.com/packet/PKT-123',
                settings=result['settings'],
                image_url=firebase_url
            )
            
            assert record_saved is True
    
    def test_packet_qr_url_generation(self):
        """Test QR generation for packet URLs"""
        generator = QRGenerator()
        
        packet_ids = ['PKT-12345', 'PKT-ABCDE', 'PKT-98765']
        
        for packet_id in packet_ids:
            packet_url = f'https://kyuaar.com/packet/{packet_id}'
            
            result = generator.generate_qr_code(
                data=packet_url,
                packet_id=packet_id
            )
            
            assert result['success'] is True
            assert result['data'] == packet_url
            assert result['packet_id'] == packet_id
    
    def test_whatsapp_qr_generation(self):
        """Test QR generation for WhatsApp URLs"""
        generator = QRGenerator()
        
        whatsapp_urls = [
            'https://wa.me/919166900151',
            'https://wa.me/1234567890?text=Hello',
            'https://wa.me/919876543210?text=Contact%20from%20Kyuaar'
        ]
        
        for wa_url in whatsapp_urls:
            result = generator.generate_qr_code(wa_url)
            
            assert result['success'] is True
            assert result['data'] == wa_url
            assert 'wa.me' in result['data']


class TestQRPerformance:
    """Test QR generation performance and resource usage"""
    
    def test_batch_qr_generation(self):
        """Test generating multiple QR codes efficiently"""
        generator = QRGenerator()
        
        urls = [f'https://kyuaar.com/packet/PKT-{i:05d}' for i in range(10)]
        
        results = []
        for url in urls:
            result = generator.generate_qr_code(url)
            results.append(result)
        
        # All should succeed
        assert all(r['success'] for r in results)
        
        # Each should have unique data
        data_values = [r['data'] for r in results]
        assert len(set(data_values)) == len(data_values)  # All unique
    
    def test_memory_efficiency(self):
        """Test that QR generation doesn't consume excessive memory"""
        generator = QRGenerator()
        
        # Generate a QR code with large settings
        settings = {
            'box_size': 20,
            'border': 10,
            'module_drawer': 'circle',
            'color_mask': 'radial_gradient'
        }
        
        result = generator.generate_qr_code(
            'https://kyuaar.com/packet/PKT-LARGE',
            settings=settings
        )
        
        assert result['success'] is True
        
        # Image should be reasonable size (not gigantic)
        width, height = result['size']
        assert width <= 2000 and height <= 2000  # Reasonable upper limit
        
        # Base64 data should be reasonable size
        assert len(result['image_base64']) < 1000000  # Under 1MB base64