#!/usr/bin/env python3
"""
Test script to debug QR generation issues
"""

import qrcode
from qrcode.image.styledpil import StyledPilImage

try:
    print(f"QRCode version: {qrcode.__version__}")
except:
    print("QRCode version: unknown")

# Test imports
try:
    from qrcode.image.styles.moduledrawers.pil import (
        SquareModuleDrawer, 
        CircleModuleDrawer, 
        RoundedModuleDrawer,
        VerticalBarsDrawer,
        HorizontalBarsDrawer
    )
    print("✅ Module drawers imported from .pil")
except ImportError as e:
    print(f"❌ Failed to import module drawers from .pil: {e}")
    try:
        from qrcode.image.styles.moduledrawers import (
            SquareModuleDrawer, 
            CircleModuleDrawer, 
            RoundedModuleDrawer,
            VerticalBarsDrawer,
            HorizontalBarsDrawer
        )
        print("✅ Module drawers imported from base")
    except ImportError as e2:
        print(f"❌ Failed to import module drawers from base: {e2}")

try:
    from qrcode.image.styles.eyedrawers.pil import (
        SquareEyeDrawer,
        CircleEyeDrawer,
        RoundedEyeDrawer
    )
    print("✅ Eye drawers imported from .pil")
except ImportError as e:
    print(f"❌ Failed to import eye drawers from .pil: {e}")
    try:
        from qrcode.image.styles.eyedrawers import (
            SquareEyeDrawer,
            CircleEyeDrawer,
            RoundedEyeDrawer
        )
        print("✅ Eye drawers imported from base")
    except ImportError as e2:
        print(f"❌ Failed to import eye drawers from base: {e2}")

# Test QR generation with different shapes
test_data = "https://example.com"

print(f"\n--- Testing QR Generation ---")

# Test 1: Square (baseline)
print("Test 1: Square module drawer")
qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr.add_data(test_data)
qr.make(fit=True)

try:
    img1 = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=SquareModuleDrawer()
    )
    print("✅ Square QR generated successfully")
    img1.save("test_square.png")
except Exception as e:
    print(f"❌ Square QR failed: {e}")

# Test 2: Circle module drawer  
print("Test 2: Circle module drawer")
qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr.add_data(test_data)
qr.make(fit=True)

try:
    img2 = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=CircleModuleDrawer()
    )
    print("✅ Circle QR generated successfully")
    img2.save("test_circle.png")
except Exception as e:
    print(f"❌ Circle QR failed: {e}")

# Test 3: Rounded module drawer
print("Test 3: Rounded module drawer")
qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr.add_data(test_data)
qr.make(fit=True)

try:
    img3 = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer()
    )
    print("✅ Rounded QR generated successfully")
    img3.save("test_rounded.png")
except Exception as e:
    print(f"❌ Rounded QR failed: {e}")

# Test 4: With eye drawers (if available)
if 'SquareEyeDrawer' in globals() and 'CircleEyeDrawer' in globals():
    print("Test 4: Circle eye drawer")
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(test_data)
    qr.make(fit=True)

    try:
        img4 = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            eye_drawer=CircleEyeDrawer()
        )
        print("✅ QR with circle eyes generated successfully")
        img4.save("test_circle_eyes.png")
    except Exception as e:
        print(f"❌ QR with circle eyes failed: {e}")
else:
    print("❌ Eye drawers not available")

print("\n--- Test Complete ---")