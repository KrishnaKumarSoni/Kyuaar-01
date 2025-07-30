#!/usr/bin/env python3
"""
Test qrcode-styled library for eye corner styling
"""

from qrcode_styled import QRCodeStyled
import io

print("Testing qrcode-styled library...")

# Test different styles
styles = [
    ("straight", "Straight corners"),
    ("rounded", "Rounded corners"),
    ("extra-rounded", "Extra rounded corners"),
    ("dotted", "Dotted style")
]

test_data = "https://example.com"

for style_name, description in styles:
    try:
        print(f"\nTesting: {description} ({style_name})")
        
        # Create QR code with style
        qr = QRCodeStyled()
        
        # Generate image
        img = qr.get_image(test_data)
        
        # Save to file
        filename = f"test_styled_{style_name.replace('-', '_')}.png"
        img.save(filename)
        
        print(f"✅ Generated {filename} successfully")
        
    except Exception as e:
        print(f"❌ Failed to generate {style_name}: {e}")

# Test configuration options
print(f"\nTesting with custom configuration...")
try:
    qr = QRCodeStyled()
    
    # Try to find configuration options
    print("Available methods:")
    methods = [method for method in dir(qr) if not method.startswith('_')]
    for method in methods:
        print(f"  - {method}")
        
except Exception as e:
    print(f"❌ Error exploring API: {e}")

print("\n--- Test Complete ---")