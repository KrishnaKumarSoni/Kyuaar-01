"""
QR Code Generation Service
Handles customizable QR code generation with various styling options
"""

import qrcode
from qrcode.image.styledpil import StyledPilImage
try:
    from qrcode.image.styles.moduledrawers.pil import (
        SquareModuleDrawer, 
        CircleModuleDrawer, 
        RoundedModuleDrawer,
        VerticalBarsDrawer,
        HorizontalBarsDrawer
    )
except ImportError:
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
# Eye drawers don't exist in the qrcode library
# The corner "eyes" are structural elements that cannot be customized
# with the standard qrcode library. Only module drawers (data dots) can be styled.
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

class CustomEyeStyler:
    """Custom eye corner styling for QR codes"""
    
    @staticmethod
    def find_finder_patterns(modules: list) -> list:
        """Find the positions and sizes of the three finder patterns (eyes)"""
        if not modules:
            return []
            
        size = len(modules)
        finder_size = 7  # Standard finder pattern is 7x7 modules
        
        # Define the three standard positions
        positions = [
            (0, 0),  # Top-left
            (size - finder_size, 0),  # Top-right  
            (0, size - finder_size),  # Bottom-left
        ]
        
        return [(x, y, finder_size) for x, y in positions]
    
    @staticmethod
    def draw_rounded_rectangle(draw: ImageDraw, bbox: Tuple[int, int, int, int], 
                             radius: int, fill: str = 'black') -> None:
        """Draw a rounded rectangle"""
        x1, y1, x2, y2 = bbox
        
        # Draw main rectangle body
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        
        # Draw rounded corners
        draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill)
        draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill)
    
    @staticmethod
    def draw_circle(draw: ImageDraw, bbox: Tuple[int, int, int, int], 
                   fill: str = 'black') -> None:
        """Draw a circle/ellipse"""
        draw.ellipse(bbox, fill=fill)
    
    @classmethod
    def style_eyes(cls, img: Image.Image, modules: list, eye_style: str = 'square',
                  fill_color = 'black', back_color = 'white',
                  box_size: int = 10, border: int = 4) -> Image.Image:
        """Apply custom styling to the finder patterns (eyes)"""
        
        if eye_style == 'square':
            return img  # No changes needed
            
        # Ensure colors are strings 
        fill_color = str(fill_color)
        back_color = str(back_color)
            
        eye_positions = cls.find_finder_patterns(modules)
        if not eye_positions:
            return img
        
        # Create a copy to work with
        styled_img = img.copy()
        draw = ImageDraw.Draw(styled_img)
        
        # Calculate border in pixels
        border_px = border * box_size
        
        for eye_x, eye_y, eye_size in eye_positions:
            # Convert module coordinates to pixel coordinates
            px_x = border_px + eye_x * box_size
            px_y = border_px + eye_y * box_size
            px_size = eye_size * box_size
            
            # Clear the existing eye area
            draw.rectangle([px_x, px_y, px_x + px_size, px_y + px_size], fill=back_color)
            
            if eye_style == 'rounded':
                # Draw outer rounded square
                cls.draw_rounded_rectangle(
                    draw, 
                    (px_x, px_y, px_x + px_size, px_y + px_size),
                    radius=box_size,
                    fill=fill_color
                )
                
                # Draw inner white rounded square
                inner_margin = box_size
                cls.draw_rounded_rectangle(
                    draw,
                    (px_x + inner_margin, px_y + inner_margin, 
                     px_x + px_size - inner_margin, px_y + px_size - inner_margin),
                    radius=box_size // 2,
                    fill=back_color
                )
                
                # Draw center rounded square
                center_margin = 2 * box_size
                cls.draw_rounded_rectangle(
                    draw,
                    (px_x + center_margin, px_y + center_margin,
                     px_x + px_size - center_margin, px_y + px_size - center_margin),
                    radius=box_size // 3,
                    fill=fill_color
                )
                
            elif eye_style == 'circle':
                # Draw outer circle
                cls.draw_circle(
                    draw,
                    (px_x, px_y, px_x + px_size, px_y + px_size),
                    fill=fill_color
                )
                
                # Draw inner white circle
                inner_margin = box_size
                cls.draw_circle(
                    draw,
                    (px_x + inner_margin, px_y + inner_margin,
                     px_x + px_size - inner_margin, px_y + px_size - inner_margin),
                    fill=back_color
                )
                
                # Draw center circle
                center_margin = 2 * box_size
                cls.draw_circle(
                    draw,
                    (px_x + center_margin, px_y + center_margin,
                     px_x + px_size - center_margin, px_y + px_size - center_margin),
                    fill=fill_color
                )
        
        return styled_img

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
    
    def _hex_to_rgb(self, hex_color) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        try:
            # Ensure hex_color is a string
            hex_color = str(hex_color)
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
        logger.info(f"Available module drawers: {list(self.style_options.MODULE_DRAWERS.keys())}")
        logger.info(f"Available eye drawers: {list(self.style_options.EYE_DRAWERS.keys())}")
        
        # Get module drawer (data dots)
        module_drawer_name = settings.get('module_drawer', 'square')
        logger.info(f"Requested module drawer: {module_drawer_name}")
        
        module_drawer = self.style_options.MODULE_DRAWERS.get(
            module_drawer_name, 
            self.style_options.MODULE_DRAWERS['square']
        )
        logger.info(f"Selected module drawer: {type(module_drawer).__name__}")
        
        # Get eye drawer (corner patterns)
        eye_drawer_name = settings.get('eye_drawer', 'square')
        logger.info(f"Requested eye drawer: {eye_drawer_name}")
        
        eye_drawer = self.style_options.EYE_DRAWERS.get(eye_drawer_name)
        if eye_drawer is None and self.style_options.EYE_DRAWERS:
            # Fallback to first available eye drawer
            eye_drawer = list(self.style_options.EYE_DRAWERS.values())[0]
            logger.info(f"Using fallback eye drawer: {type(eye_drawer).__name__ if eye_drawer else 'None'}")
        elif eye_drawer:
            logger.info(f"Selected eye drawer: {type(eye_drawer).__name__}")
        else:
            logger.info("No eye drawer available")
        
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
        
        # Apply custom eye styling if requested
        eye_style = settings.get('eye_drawer', 'square')
        if eye_style in ['rounded', 'circle']:
            logger.info(f"Applying custom eye styling: {eye_style}")
            img = CustomEyeStyler.style_eyes(
                img=img,
                modules=qr.modules,
                eye_style=eye_style,
                fill_color=settings.get('fill_color', '#000000'),
                back_color=settings.get('back_color', '#FFFFFF'),
                box_size=settings.get('box_size', 10),
                border=settings.get('border', 4)
            )
        
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
            # Check if Firebase is initialized
            if not firebase_admin._apps:
                logger.error("Firebase admin not initialized")
                return None
                
            bucket = storage.bucket()
            folder = packet_id if packet_id else "standalone"
            blob_path = f"qr_codes/{folder}/{filename}"
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
            logger.error(f"Firebase apps available: {len(firebase_admin._apps)}")
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
            
            # Check if Firebase is initialized
            if not firebase_admin._apps:
                logger.error("Firebase admin not initialized")
                return False
            
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
            logger.error(f"Firebase apps available: {len(firebase_admin._apps)}")
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