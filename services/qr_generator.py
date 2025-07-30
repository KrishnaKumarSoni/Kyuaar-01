"""
QR Code Generation Service
Handles customizable QR code generation with various styling options
"""

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer, 
    CircleModuleDrawer, 
    RoundedModuleDrawer,
    VerticalBarsDrawer,
    HorizontalBarsDrawer
)
from qrcode.image.styles.colormasks import (
    SolidFillColorMask,
    RadialGradiantColorMask,
    SquareGradiantColorMask
)
try:
    from qrcode.image.styles.eyedrawers import (
        SquareEyeDrawer,
        CircleEyeDrawer,
        RoundedEyeDrawer
    )
except ImportError:
    # Fallback for older qrcode versions
    SquareEyeDrawer = None
    CircleEyeDrawer = None
    RoundedEyeDrawer = None
from PIL import Image, ImageDraw
import io
import base64
import logging
from typing import Dict, Any, Optional, Tuple
import firebase_admin
from firebase_admin import storage
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class QRStyleOptions:
    """Available QR code styling options"""
    
    # Module drawer types (data dots)
    MODULE_DRAWERS = {
        'square': SquareModuleDrawer(),
        'circle': CircleModuleDrawer(),
        'rounded': RoundedModuleDrawer(),
        'vertical_bars': VerticalBarsDrawer(),
        'horizontal_bars': HorizontalBarsDrawer()
    }
    
    # Eye drawer types (corner patterns)
    EYE_DRAWERS = {}
    if SquareEyeDrawer:
        EYE_DRAWERS['square'] = SquareEyeDrawer()
    if CircleEyeDrawer:
        EYE_DRAWERS['circle'] = CircleEyeDrawer()
    if RoundedEyeDrawer:
        EYE_DRAWERS['rounded'] = RoundedEyeDrawer()
    
    # Color mask types
    COLOR_MASKS = {
        'solid': SolidFillColorMask,
        'radial_gradient': RadialGradiantColorMask,
        'square_gradient': SquareGradiantColorMask
    }
    
    # Default colors
    DEFAULT_FILL_COLOR = '#000000'
    DEFAULT_BACK_COLOR = '#FFFFFF'
    DEFAULT_PRIMARY_COLOR = '#CC5500'  # Burnt orange theme

class QRGenerator:
    """QR Code Generator with customization options"""
    
    def __init__(self):
        self.style_options = QRStyleOptions()
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        try:
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except (ValueError, IndexError):
            # Return black as default
            return (0, 0, 0)
    
    def generate_qr_code(
        self,
        data: str,
        packet_id: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a customized QR code
        
        Args:
            data: The data to encode in the QR code
            packet_id: Optional packet ID to associate with the QR code
            settings: Customization settings
        
        Returns:
            Dict containing QR code image data and metadata
        """
        try:
            # Default settings
            default_settings = {
                'version': 1,
                'error_correction': qrcode.constants.ERROR_CORRECT_M,
                'box_size': 10,
                'border': 4,
                'fill_color': self.style_options.DEFAULT_FILL_COLOR,
                'back_color': self.style_options.DEFAULT_BACK_COLOR,
                'module_drawer': 'square',
                'color_mask': 'solid',
                'eye_drawer': 'square',
                'gradient_colors': [self.style_options.DEFAULT_PRIMARY_COLOR, self.style_options.DEFAULT_FILL_COLOR]
            }
            
            # Merge with provided settings
            if settings:
                default_settings.update(settings)
            
            # Create QR code instance
            qr = qrcode.QRCode(
                version=default_settings['version'],
                error_correction=default_settings['error_correction'],
                box_size=default_settings['box_size'],
                border=default_settings['border'],
            )
            
            qr.add_data(data)
            qr.make(fit=True)
            
            # Generate styled image
            img = self._create_styled_image(qr, default_settings)
            
            # Convert to base64 for preview
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Prepare result
            result = {
                'success': True,
                'image_base64': img_base64,
                'image_data_url': f"data:image/png;base64,{img_base64}",
                'settings': default_settings,
                'data': data,
                'packet_id': packet_id,
                'size': img.size,
                'format': 'PNG'
            }
            
            logger.info(f"Generated QR code for data: {data[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_styled_image(self, qr: qrcode.QRCode, settings: Dict[str, Any]) -> Image.Image:
        """Create a styled QR code image based on settings"""
        
        logger.info(f"Creating styled image with settings: {settings}")
        
        # Get module drawer (data dots)
        module_drawer = self.style_options.MODULE_DRAWERS.get(
            settings['module_drawer'], 
            self.style_options.MODULE_DRAWERS['square']
        )
        
        # Get eye drawer (corner patterns)
        eye_drawer_name = settings.get('eye_drawer', 'square')
        eye_drawer = self.style_options.EYE_DRAWERS.get(eye_drawer_name)
        if eye_drawer is None and self.style_options.EYE_DRAWERS:
            # Fallback to first available eye drawer
            eye_drawer = list(self.style_options.EYE_DRAWERS.values())[0]
        
        # Create color mask
        color_mask_class = self.style_options.COLOR_MASKS.get(
            settings['color_mask'],
            self.style_options.COLOR_MASKS['solid']
        )
        
        if settings['color_mask'] == 'solid':
            # Convert hex colors to RGB tuples
            fill_color = self._hex_to_rgb(settings['fill_color'])
            back_color = self._hex_to_rgb(settings['back_color'])
            
            color_mask = color_mask_class(
                front_color=fill_color,
                back_color=back_color
            )
        elif settings['color_mask'] in ['radial_gradient', 'square_gradient']:
            # Use gradient colors - convert hex to RGB
            gradient_colors = settings.get('gradient_colors', [
                self.style_options.DEFAULT_PRIMARY_COLOR,
                self.style_options.DEFAULT_FILL_COLOR
            ])
            center_color = self._hex_to_rgb(gradient_colors[0])
            edge_color = self._hex_to_rgb(gradient_colors[1])
            
            back_color = self._hex_to_rgb(settings.get('back_color', '#FFFFFF'))
            color_mask = color_mask_class(
                center_color=center_color,
                edge_color=edge_color,
                back_color=back_color
            )
        else:
            # Fallback to solid with converted colors
            fill_color = self._hex_to_rgb(settings['fill_color'])
            back_color = self._hex_to_rgb(settings['back_color'])
            
            color_mask = color_mask_class(
                front_color=fill_color,
                back_color=back_color
            )
        
        # Generate styled image
        make_image_args = {
            'image_factory': StyledPilImage,
            'module_drawer': module_drawer,
            'color_mask': color_mask
        }
        
        # Only add eye_drawer if available
        if eye_drawer is not None:
            make_image_args['eye_drawer'] = eye_drawer
            
        img = qr.make_image(**make_image_args)
        
        return img
    
    def save_to_firebase(
        self,
        image_data: bytes,
        filename: str,
        packet_id: str,
        settings: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save QR code image to Firebase Storage
        
        Args:
            image_data: Image data as bytes
            filename: Filename for the image
            packet_id: Associated packet ID
            settings: QR code settings
        
        Returns:
            Public URL of the saved image or None if failed
        """
        try:
            bucket = storage.bucket()
            blob_path = f"qr_codes/{packet_id}/{filename}"
            blob = bucket.blob(blob_path)
            
            # Upload image
            blob.upload_from_string(
                image_data,
                content_type='image/png'
            )
            
            # Make publicly accessible
            blob.make_public()
            
            logger.info(f"Saved QR code to Firebase: {blob_path}")
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error saving QR code to Firebase: {e}")
            return None
    
    def save_qr_record_to_firestore(
        self,
        packet_id: str,
        url: str,
        settings: Dict[str, Any],
        image_url: Optional[str] = None
    ) -> bool:
        """
        Save QR code record to Firestore
        
        Args:
            packet_id: Associated packet ID
            url: The URL encoded in the QR code
            settings: QR code settings
            image_url: Firebase Storage URL of the image
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from firebase_admin import firestore
            
            db = firestore.client()
            
            qr_data = {
                'packet_id': packet_id,
                'url': url,
                'settings': settings,
                'image_url': image_url,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Save to qr_codes collection
            doc_ref = db.collection('qr_codes').add(qr_data)
            
            logger.info(f"Saved QR code record to Firestore for packet {packet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving QR code record to Firestore: {e}")
            return False
    
    def get_style_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined style presets for common QR code styles"""
        return {
            'default': {
                'module_drawer': 'square',
                'eye_drawer': 'square',
                'fill_color': '#000000',
                'back_color': '#FFFFFF',
                'color_mask': 'solid'
            },
            'rounded': {
                'module_drawer': 'rounded',
                'eye_drawer': 'rounded',
                'fill_color': '#CC5500',
                'back_color': '#FFFFFF',
                'color_mask': 'solid'
            },
            'circular': {
                'module_drawer': 'circle',
                'eye_drawer': 'circle',
                'fill_color': '#000000',
                'back_color': '#FFFFFF',
                'color_mask': 'solid'
            },
            'gradient_radial': {
                'module_drawer': 'square',
                'eye_drawer': 'square',
                'color_mask': 'radial_gradient',
                'gradient_colors': ['#CC5500', '#FF6600'],
                'back_color': '#FFFFFF'
            },
            'gradient_square': {
                'module_drawer': 'rounded',
                'eye_drawer': 'rounded',
                'color_mask': 'square_gradient',
                'gradient_colors': ['#CC5500', '#000000'],
                'back_color': '#FFFFFF'
            },
            'bars_vertical': {
                'module_drawer': 'vertical_bars',
                'eye_drawer': 'square',
                'fill_color': '#CC5500',
                'back_color': '#FFFFFF',
                'color_mask': 'solid'
            }
        }


# Global instance
qr_generator = QRGenerator()