#!/usr/bin/env python3
"""
Custom QR Code Generator with Eye Corner Styling
No external dependencies beyond standard qrcode + PIL
"""

import qrcode
from PIL import Image, ImageDraw, ImageFilter
import io
import base64
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CustomQRGenerator:
    """Custom QR generator with eye corner styling capabilities"""
    
    def __init__(self):
        self.eye_positions = []  # Will store (x, y, size) for each eye
    
    def find_finder_patterns(self, modules: list) -> list:
        """
        Find the positions and sizes of the three finder patterns (eyes)
        QR codes have finder patterns at: top-left, top-right, bottom-left
        """
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
    
    def generate_base_qr(self, data: str, **kwargs) -> Tuple[Image.Image, list]:
        """Generate base QR code and return image + module matrix"""
        
        # Create QR code with specified parameters
        qr = qrcode.QRCode(
            version=kwargs.get('version', 1),
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{kwargs.get('error_correction', 'M')}"),
            box_size=kwargs.get('box_size', 10),
            border=kwargs.get('border', 4),
        )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        # Generate base image
        img = qr.make_image(
            fill_color=kwargs.get('fill_color', 'black'),
            back_color=kwargs.get('back_color', 'white')
        ).convert('RGB')
        
        # Get module matrix for eye detection
        modules = qr.modules
        
        # Find finder pattern positions
        self.eye_positions = self.find_finder_patterns(modules)
        
        return img, modules
    
    def draw_rounded_rectangle(self, draw: ImageDraw, bbox: Tuple[int, int, int, int], 
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
    
    def draw_circle(self, draw: ImageDraw, bbox: Tuple[int, int, int, int], 
                   fill: str = 'black') -> None:
        """Draw a circle/ellipse"""
        draw.ellipse(bbox, fill=fill)
    
    def apply_eye_styling(self, img: Image.Image, eye_style: str = 'rounded',
                         fill_color: str = 'black', back_color: str = 'white') -> Image.Image:
        """Apply custom styling to the finder patterns (eyes)"""
        
        if not self.eye_positions:
            return img
        
        # Create a copy to work with
        styled_img = img.copy()
        draw = ImageDraw.Draw(styled_img)
        
        # Get box size from image dimensions and QR matrix
        # Assuming border=4 and standard QR dimensions
        border_px = 40  # Approximate border in pixels (will calculate properly)
        qr_size = min(img.width - 2*border_px, img.height - 2*border_px)
        
        # Calculate module size in pixels
        module_count = len(self.eye_positions) * 10  # Rough estimate, will improve
        if module_count > 0:
            box_size = qr_size / module_count
        else:
            box_size = 10  # Fallback
            
        box_size = max(int(box_size), 5)  # Ensure minimum size
        
        for eye_x, eye_y, eye_size in self.eye_positions:
            # Convert module coordinates to pixel coordinates
            px_x = border_px + eye_x * box_size
            px_y = border_px + eye_y * box_size
            px_size = eye_size * box_size
            
            # Clear the existing eye area
            draw.rectangle([px_x, px_y, px_x + px_size, px_y + px_size], fill=back_color)
            
            if eye_style == 'rounded':
                # Draw outer rounded square
                self.draw_rounded_rectangle(
                    draw, 
                    (px_x, px_y, px_x + px_size, px_y + px_size),
                    radius=box_size,
                    fill=fill_color
                )
                
                # Draw inner white rounded square
                inner_margin = box_size
                self.draw_rounded_rectangle(
                    draw,
                    (px_x + inner_margin, px_y + inner_margin, 
                     px_x + px_size - inner_margin, px_y + px_size - inner_margin),
                    radius=box_size // 2,
                    fill=back_color
                )
                
                # Draw center rounded square
                center_margin = 2 * box_size
                self.draw_rounded_rectangle(
                    draw,
                    (px_x + center_margin, px_y + center_margin,
                     px_x + px_size - center_margin, px_y + px_size - center_margin),
                    radius=box_size // 3,
                    fill=fill_color
                )
                
            elif eye_style == 'circle':
                # Draw outer circle
                self.draw_circle(
                    draw,
                    (px_x, px_y, px_x + px_size, px_y + px_size),
                    fill=fill_color
                )
                
                # Draw inner white circle
                inner_margin = box_size
                self.draw_circle(
                    draw,
                    (px_x + inner_margin, px_y + inner_margin,
                     px_x + px_size - inner_margin, px_y + px_size - inner_margin),
                    fill=back_color
                )
                
                # Draw center circle
                center_margin = 2 * box_size
                self.draw_circle(
                    draw,
                    (px_x + center_margin, px_y + center_margin,
                     px_x + px_size - center_margin, px_y + px_size - center_margin),
                    fill=fill_color
                )
            
            # 'square' style = do nothing (keep original)
        
        return styled_img
    
    def generate_styled_qr(self, data: str, eye_style: str = 'rounded', 
                          **kwargs) -> Dict[str, Any]:
        """Generate QR code with custom eye styling"""
        try:
            # Generate base QR code
            img, modules = self.generate_base_qr(data, **kwargs)
            
            # Apply eye styling
            if eye_style != 'square':
                img = self.apply_eye_styling(
                    img, 
                    eye_style=eye_style,
                    fill_color=kwargs.get('fill_color', 'black'),
                    back_color=kwargs.get('back_color', 'white')
                )
            
            # Convert to base64 for API response
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            return {
                'success': True,
                'image_base64': img_base64,
                'image_data_url': f"data:image/png;base64,{img_base64}",
                'size': img.size,
                'eye_style': eye_style,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Error generating styled QR: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Test the custom solution
if __name__ == "__main__":
    generator = CustomQRGenerator()
    
    # Test different eye styles
    styles = ['square', 'rounded', 'circle']
    
    for style in styles:
        print(f"Testing {style} eye style...")
        result = generator.generate_styled_qr(
            "https://example.com",
            eye_style=style,
            box_size=10,
            border=4
        )
        
        if result['success']:
            # Save test image
            img_data = base64.b64decode(result['image_base64'])
            with open(f'custom_qr_{style}.png', 'wb') as f:
                f.write(img_data)
            print(f"✅ Generated {style} QR successfully")
        else:
            print(f"❌ Failed to generate {style} QR: {result['error']}")