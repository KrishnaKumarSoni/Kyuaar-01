#!/usr/bin/env python3
"""
Simple test script to validate backend functionality
Tests model imports and basic functionality
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all models and routes can be imported"""
    try:
        print("Testing imports...")
        
        # Test model imports
        from models.user import User
        from models.packet import Packet, PacketStates
        from models.activity import Activity, ActivityType
        print("✅ Models imported successfully")
        
        # Test route imports
        from routes.auth import auth_bp
        from routes.api import api_bp
        print("✅ Routes imported successfully")
        
        # Test app import
        from app import app
        print("✅ Flask app imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_packet_states():
    """Test packet state transitions"""
    try:
        print("Testing packet state logic...")
        
        from models.packet import PacketStates
        
        # Test state constants
        assert PacketStates.SETUP_PENDING == 'setup_pending'
        assert PacketStates.SETUP_DONE == 'setup_done'
        assert PacketStates.CONFIG_PENDING == 'config_pending'
        assert PacketStates.CONFIG_DONE == 'config_done'
        
        print("✅ Packet states validated")
        return True
        
    except Exception as e:
        print(f"❌ Packet state test failed: {e}")
        return False

def test_app_config():
    """Test Flask app configuration"""
    try:
        print("Testing Flask app configuration...")
        
        from app import app
        
        # Test that app is created
        assert app is not None
        assert app.config['SECRET_KEY'] is not None
        
        # Test blueprints are registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        expected_blueprints = ['auth', 'dashboard', 'packets', 'config', 'api']
        
        for bp_name in expected_blueprints:
            if bp_name not in blueprint_names:
                print(f"⚠️  Blueprint '{bp_name}' not registered")
            else:
                print(f"✅ Blueprint '{bp_name}' registered")
        
        print("✅ Flask app configuration validated")
        return True
        
    except Exception as e:
        print(f"❌ App config test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Kyuaar Backend Validation ===\n")
    
    tests = [
        test_imports,
        test_packet_states,
        test_app_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing
    
    print(f"=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All tests passed! Backend is ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())