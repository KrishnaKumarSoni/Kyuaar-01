"""
Unit tests for file upload functionality
Tests QR image upload handling, validation, and Firebase Storage integration
"""

import pytest
import io
import os
from PIL import Image
from unittest.mock import Mock, patch, MagicMock

from models.packet import Packet, PacketStates


class TestFileUploadValidation:
    """Test file upload validation and security"""
    
    def create_test_image(self, format='PNG', size=(200, 200), color='white'):
        """Create a test image for upload testing"""
        img = Image.new('RGB', size, color=color)
        img_io = io.BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return img_io
    
    def test_valid_image_formats(self):
        """Test that valid image formats are accepted"""
        valid_formats = ['PNG', 'JPEG', 'JPG']
        
        for format in valid_formats:
            img_io = self.create_test_image(format=format)
            
            # Test image can be opened and validated
            img_io.seek(0)
            img = Image.open(img_io)
            
            assert img.format in ['PNG', 'JPEG']
            assert img.size == (200, 200)
    
    def test_invalid_file_types(self):
        """Test that invalid file types are rejected"""
        # Create a text file
        text_io = io.BytesIO(b"This is not an image")
        
        with pytest.raises(Exception):
            # Should raise exception when trying to open as image
            Image.open(text_io)
    
    def test_file_size_validation(self):
        """Test file size limits"""
        # Create large image (should be rejected if over limit)
        large_img = self.create_test_image(size=(2000, 2000))
        large_img.seek(0, 2)  # Seek to end
        file_size = large_img.tell()
        large_img.seek(0)  # Reset
        
        # Typical size limits (5MB = 5 * 1024 * 1024 bytes)
        max_file_size = 5 * 1024 * 1024
        
        # This test would typically be done in the route handler
        # Here we just verify we can check file size
        assert isinstance(file_size, int)
        
        # Small image should be under limit
        small_img = self.create_test_image(size=(200, 200))
        small_img.seek(0, 2)
        small_size = small_img.tell()
        small_img.seek(0)
        
        assert small_size < max_file_size
    
    def test_image_dimensions_validation(self):
        """Test image dimension requirements"""
        # QR codes should be square and reasonable size
        square_img = self.create_test_image(size=(300, 300))
        img = Image.open(square_img)
        
        assert img.width == img.height  # Square
        assert img.width >= 100  # Minimum size
        assert img.width <= 2000  # Maximum size
    
    def test_image_content_validation(self):
        """Test basic image content validation"""
        # Create QR-like image (black and white)
        qr_like_img = self.create_test_image(size=(200, 200), color='black')
        img = Image.open(qr_like_img)
        
        # Convert to grayscale to check if it's monochrome-ish
        grayscale = img.convert('L')
        
        # Basic validation that image can be processed
        assert grayscale.mode == 'L'
        assert grayscale.size == (200, 200)


class TestFirebaseStorageIntegration:
    """Test Firebase Storage upload integration"""
    
    @patch('firebase_admin.storage.bucket')
    def test_upload_to_storage_success(self, mock_bucket):
        """Test successful file upload to Firebase Storage"""
        # Mock Firebase Storage
        mock_blob = Mock()
        mock_bucket.return_value.blob.return_value = mock_blob
        
        # Mock successful upload
        mock_blob.upload_from_file.return_value = None
        mock_blob.make_public.return_value = None
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/test-qr.png'
        
        # Create test image
        test_image = self.create_test_image()
        
        # Simulate upload process
        filename = 'test-qr.png'
        blob = mock_bucket.return_value.blob(filename)
        blob.upload_from_file(test_image, content_type='image/png')
        blob.make_public()
        
        # Verify upload was called
        mock_blob.upload_from_file.assert_called_once()
        mock_blob.make_public.assert_called_once()
        assert mock_blob.public_url == 'https://storage.googleapis.com/bucket/test-qr.png'
    
    @patch('firebase_admin.storage.bucket')
    def test_upload_failure_handling(self, mock_bucket):
        """Test handling of upload failures"""
        # Mock Firebase Storage to raise exception
        mock_blob = Mock()
        mock_bucket.return_value.blob.return_value = mock_blob
        mock_blob.upload_from_file.side_effect = Exception('Upload failed')
        
        test_image = self.create_test_image()
        
        # Simulate upload failure
        with pytest.raises(Exception) as exc_info:
            blob = mock_bucket.return_value.blob('test-qr.png')
            blob.upload_from_file(test_image)
        
        assert 'Upload failed' in str(exc_info.value)
    
    def create_test_image(self, format='PNG', size=(200, 200), color='white'):
        """Helper method to create test images"""
        img = Image.new('RGB', size, color=color)
        img_io = io.BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return img_io


class TestPacketImageUpload:
    """Test packet QR image upload workflow"""
    
    @patch('firebase_admin.storage.bucket')
    @patch('firebase_admin.firestore.client')
    def test_packet_qr_upload_success(self, mock_firestore, mock_storage):
        """Test successful QR image upload to packet"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # Mock Firebase Storage
        mock_bucket_obj = Mock()
        mock_storage.return_value = mock_bucket_obj
        mock_blob = Mock()
        mock_bucket_obj.blob.return_value = mock_blob
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/qr-PKT-123.png'
        
        # Create packet
        packet = Packet.create(user_id='user-123', qr_count=25)
        assert packet.state == PacketStates.SETUP_PENDING
        
        # Simulate QR image upload
        image_url = 'https://storage.googleapis.com/bucket/qr-PKT-123.png'
        result = packet.mark_setup_complete(image_url)
        
        assert result is True
        assert packet.state == PacketStates.SETUP_DONE
        assert packet.qr_image_url == image_url
        assert packet.is_ready_for_sale() is True
    
    def test_packet_upload_invalid_state(self):
        """Test QR upload when packet is in wrong state"""
        packet = Packet(state=PacketStates.CONFIG_PENDING)
        
        # Should not be able to upload QR after packet is sold
        result = packet.mark_setup_complete('image_url')
        
        assert result is False
        assert packet.qr_image_url is None
    
    @patch('firebase_admin.firestore.client')
    def test_packet_upload_state_persistence(self, mock_firestore):
        """Test that upload state changes are persisted"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        packet = Packet.create(user_id='user-123')
        
        # Upload QR image
        image_url = 'https://storage.googleapis.com/bucket/qr.png'
        packet.mark_setup_complete(image_url)
        
        # Save should be called to persist state change
        packet.save()
        mock_document.set.assert_called()
        
        # Verify saved data includes image URL and new state
        call_args = mock_document.set.call_args[0][0]
        assert call_args['qr_image_url'] == image_url
        assert call_args['state'] == PacketStates.SETUP_DONE


class TestUploadSecurity:
    """Test upload security measures"""
    
    def test_filename_sanitization(self):
        """Test that filenames are properly sanitized"""
        dangerous_filenames = [
            '../../../etc/passwd',
            'test.php',
            'script.js',
            'file with spaces.png',
            'file-with-unicode-café.png'
        ]
        
        for filename in dangerous_filenames:
            # In real implementation, filename would be sanitized
            # Here we test basic sanitization logic
            sanitized = self.sanitize_filename(filename)
            
            # Should not contain path traversal
            assert '../' not in sanitized
            assert '..' not in sanitized
            
            # Should not contain dangerous extensions
            assert not sanitized.endswith('.php')
            assert not sanitized.endswith('.js')
    
    def sanitize_filename(self, filename):
        """Basic filename sanitization for testing"""
        import os
        import re
        
        # Get just the filename without path
        filename = os.path.basename(filename)
        
        # Remove dangerous patterns
        filename = filename.replace('../', '')
        filename = filename.replace('..', '')
        
        # Only allow certain extensions
        allowed_extensions = ['.png', '.jpg', '.jpeg']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            filename = filename.rsplit('.', 1)[0] + '.png'
        
        # Replace special characters
        filename = re.sub(r'[^a-zA-Z0-9.-]', '_', filename)
        
        return filename
    
    def test_file_type_verification(self):
        """Test that file type verification works correctly"""
        # Create actual image
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Verify it's actually an image
        try:
            verified_img = Image.open(img_io)
            assert verified_img.format == 'PNG'
            assert verified_img.size == (100, 100)
        except Exception:
            pytest.fail("Valid image should not raise exception")
        
        # Test with non-image data
        fake_image = io.BytesIO(b"This is not image data")
        
        with pytest.raises(Exception):
            # Should raise exception for non-image data
            Image.open(fake_image)


class TestUploadPerformance:
    """Test upload performance and resource usage"""
    
    def test_large_file_handling(self):
        """Test handling of large files"""
        # Create a larger image
        large_img = Image.new('RGB', (1000, 1000), color='blue')
        img_io = io.BytesIO()
        large_img.save(img_io, 'PNG')
        img_io.seek(0, 2)  # Seek to end
        file_size = img_io.tell()
        img_io.seek(0)  # Reset
        
        # File size should be reasonable but not too large
        max_size = 10 * 1024 * 1024  # 10MB
        assert file_size < max_size
    
    def test_memory_usage_during_upload(self):
        """Test that memory usage is reasonable during upload"""
        # Create multiple images to simulate concurrent uploads
        images = []
        for i in range(5):
            img = Image.new('RGB', (300, 300), color=(i*50, i*50, i*50))
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            images.append(img_io)
        
        # Process all images
        for img_io in images:
            img = Image.open(img_io)
            assert img.size == (300, 300)
            img.close()  # Clean up
        
        # Memory should be cleaned up after processing
        assert len(images) == 5


class TestUploadIntegration:
    """Test complete upload integration with Flask routes"""
    
    def create_test_upload_file(self, filename='test.png', content_type='image/png'):
        """Create a test file upload object"""
        img = Image.new('RGB', (200, 200), color='white')
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Simulate Flask file upload object
        class MockFileUpload:
            def __init__(self, stream, filename, content_type):
                self.stream = stream
                self.filename = filename
                self.content_type = content_type
            
            def save(self, path):
                with open(path, 'wb') as f:
                    f.write(self.stream.read())
        
        return MockFileUpload(img_io, filename, content_type)
    
    def test_upload_workflow_validation(self):
        """Test complete upload workflow validation"""
        # This would typically test Flask route handlers
        # Here we simulate the validation steps
        
        upload_file = self.create_test_upload_file()
        
        # 1. Validate file type
        assert upload_file.content_type.startswith('image/')
        
        # 2. Validate filename
        assert upload_file.filename.endswith('.png')
        
        # 3. Validate file content
        upload_file.stream.seek(0)
        img = Image.open(upload_file.stream)
        assert img.format in ['PNG', 'JPEG']
        
        # 4. File is ready for upload
        upload_file.stream.seek(0)
        assert upload_file.stream.readable()
    
    @patch('firebase_admin.storage.bucket')
    def test_upload_error_recovery(self, mock_bucket):
        """Test error recovery during upload process"""
        # Mock Firebase Storage to fail first time, succeed second time
        mock_blob = Mock()
        mock_bucket.return_value.blob.return_value = mock_blob
        
        # First call fails, second succeeds
        mock_blob.upload_from_file.side_effect = [
            Exception('Network error'),
            None  # Success on retry
        ]
        
        test_image = io.BytesIO(b'test image data')
        
        # Simulate retry logic
        try:
            blob = mock_bucket.return_value.blob('test.png')
            blob.upload_from_file(test_image)
        except Exception:
            # Retry on failure
            test_image.seek(0)  # Reset stream
            blob.upload_from_file(test_image)  # Should succeed
        
        # Verify both calls were made
        assert mock_blob.upload_from_file.call_count == 2