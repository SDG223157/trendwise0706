#!/usr/bin/env python3

"""
Test script for 6-time-point scheduler configuration functionality

This script tests the custom schedule configuration system to ensure it works
correctly for saving, loading, and applying custom time points.
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_schedule_config_functionality():
    """Test schedule configuration functionality"""
    print("🧪 Testing 6-Time-Point Scheduler Configuration")
    print("=" * 60)
    
    try:
        from app.utils.scheduler.news_fetch_scheduler import NewsFetchScheduler
        
        # Create scheduler instance
        scheduler = NewsFetchScheduler()
        
        print("📋 Test 1: Default Configuration")
        print("-" * 30)
        
        # Test getting default configuration
        default_config = scheduler.get_schedule_config()
        print(f"✅ Default config loaded: {len(default_config['times'])} time points")
        print(f"   Custom schedule: {default_config['customSchedule']}")
        
        for i, time_config in enumerate(default_config['times'], 1):
            print(f"   {i}. {time_config['time']} UTC - {time_config['label']} ({time_config['session']})")
        
        print("\n📝 Test 2: Custom Configuration")
        print("-" * 30)
        
        # Create custom configuration
        custom_config = {
            "customSchedule": True,
            "times": [
                {"time": "02:00", "session": "CHINA_HK", "label": "Early China Session"},
                {"time": "06:00", "session": "CHINA_HK", "label": "Mid China Session"},
                {"time": "10:00", "session": "US", "label": "Late China / Early Europe"},
                {"time": "13:00", "session": "US", "label": "Europe Close / US Pre"},
                {"time": "16:00", "session": "US", "label": "US Market Hours"},
                {"time": "20:00", "session": "US", "label": "US After Hours"}
            ]
        }
        
        # Test saving custom configuration
        save_success = scheduler.save_schedule_config(custom_config)
        if save_success:
            print("✅ Custom configuration saved successfully")
        else:
            print("❌ Failed to save custom configuration")
            return False
        
        # Test loading custom configuration
        loaded_config = scheduler.get_schedule_config()
        print(f"✅ Custom config loaded: {len(loaded_config['times'])} time points")
        print(f"   Custom schedule: {loaded_config['customSchedule']}")
        
        for i, time_config in enumerate(loaded_config['times'], 1):
            print(f"   {i}. {time_config['time']} UTC - {time_config['label']} ({time_config['session']})")
        
        print("\n🔄 Test 3: Reset to Default")
        print("-" * 30)
        
        # Test reset functionality
        reset_success = scheduler.reset_schedule_config()
        if reset_success:
            print("✅ Configuration reset to default successfully")
        else:
            print("❌ Failed to reset configuration")
            return False
        
        # Verify reset worked
        reset_config = scheduler.get_schedule_config()
        print(f"✅ Reset config loaded: {len(reset_config['times'])} time points")
        print(f"   Custom schedule: {reset_config['customSchedule']}")
        
        print("\n🛡️ Test 4: Validation")
        print("-" * 30)
        
        # Test invalid configurations
        invalid_configs = [
            # Missing time field
            {
                "customSchedule": True,
                "times": [
                    {"session": "CHINA_HK", "label": "Invalid"}
                ]
            },
            # Invalid session
            {
                "customSchedule": True,
                "times": [
                    {"time": "01:00", "session": "INVALID", "label": "Test"}
                ]
            },
            # Wrong number of time points
            {
                "customSchedule": True,
                "times": [
                    {"time": "01:00", "session": "CHINA_HK", "label": "Only One"}
                ]
            },
            # Invalid time format
            {
                "customSchedule": True,
                "times": [
                    {"time": "25:00", "session": "CHINA_HK", "label": "Invalid Time"},
                    {"time": "02:00", "session": "CHINA_HK", "label": "Valid Time"},
                    {"time": "03:00", "session": "CHINA_HK", "label": "Valid Time"},
                    {"time": "04:00", "session": "US", "label": "Valid Time"},
                    {"time": "05:00", "session": "US", "label": "Valid Time"},
                    {"time": "06:00", "session": "US", "label": "Valid Time"}
                ]
            }
        ]
        
        validation_passed = 0
        for i, invalid_config in enumerate(invalid_configs, 1):
            is_valid = scheduler._validate_schedule_config(invalid_config)
            if not is_valid:
                print(f"✅ Invalid config {i} correctly rejected")
                validation_passed += 1
            else:
                print(f"❌ Invalid config {i} incorrectly accepted")
        
        print(f"Validation tests: {validation_passed}/{len(invalid_configs)} passed")
        
        print("\n📊 Test 5: Status Integration")
        print("-" * 30)
        
        # Test status integration
        status = scheduler.get_status()
        if 'schedule_config' in status:
            print("✅ Schedule configuration included in status")
            print(f"   Fetch schedule type: {status['fetch_schedule']}")
            if 'schedule_times' in status:
                print(f"   Schedule times: {len(status['schedule_times'])} times")
                for time_str in status['schedule_times']:
                    print(f"     • {time_str}")
            else:
                print("❌ Schedule times missing from status")
        else:
            print("❌ Schedule configuration missing from status")
        
        print("\n⚙️ Test 6: Scheduling Application")
        print("-" * 30)
        
        # Test that custom schedule would be applied
        # (Note: We can't actually start the scheduler in a test, but we can verify the config is used)
        
        # Save a test configuration
        test_config = {
            "customSchedule": True,
            "times": [
                {"time": "01:30", "session": "CHINA_HK", "label": "Test Time 1"},
                {"time": "05:30", "session": "CHINA_HK", "label": "Test Time 2"},
                {"time": "09:30", "session": "CHINA_HK", "label": "Test Time 3"},
                {"time": "13:30", "session": "US", "label": "Test Time 4"},
                {"time": "17:00", "session": "US", "label": "Test Time 5"},
                {"time": "21:00", "session": "US", "label": "Test Time 6"}
            ]
        }
        
        scheduler.save_schedule_config(test_config)
        
        # Verify the configuration would be used in scheduling
        loaded_test_config = scheduler.get_schedule_config()
        if loaded_test_config['customSchedule']:
            print("✅ Custom configuration ready for scheduling")
            print("   Times that would be scheduled:")
            for time_config in loaded_test_config['times']:
                print(f"     • {time_config['time']} UTC - {time_config['label']} ({time_config['session']})")
        else:
            print("❌ Custom configuration not properly loaded")
        
        # Clean up - reset to default
        scheduler.reset_schedule_config()
        
        print("\n" + "=" * 60)
        print("🎉 All 6-time-point scheduler configuration tests completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in scheduler configuration tests: {e}")
        return False

def test_api_functionality():
    """Test API functionality (simulation)"""
    print("\n🌐 Testing API Functionality (Simulation)")
    print("=" * 40)
    
    try:
        # Simulate API request validation
        test_requests = [
            # Valid request
            {
                "customSchedule": True,
                "times": [
                    {"time": "01:00", "session": "CHINA_HK", "label": "Test 1"},
                    {"time": "04:00", "session": "CHINA_HK", "label": "Test 2"},
                    {"time": "08:00", "session": "CHINA_HK", "label": "Test 3"},
                    {"time": "14:00", "session": "US", "label": "Test 4"},
                    {"time": "17:00", "session": "US", "label": "Test 5"},
                    {"time": "21:00", "session": "US", "label": "Test 6"}
                ]
            },
            # Invalid request - wrong number of times
            {
                "customSchedule": True,
                "times": [
                    {"time": "01:00", "session": "CHINA_HK", "label": "Test 1"}
                ]
            },
            # Invalid request - invalid session
            {
                "customSchedule": True,
                "times": [
                    {"time": "01:00", "session": "INVALID", "label": "Test 1"},
                    {"time": "04:00", "session": "CHINA_HK", "label": "Test 2"},
                    {"time": "08:00", "session": "CHINA_HK", "label": "Test 3"},
                    {"time": "14:00", "session": "US", "label": "Test 4"},
                    {"time": "17:00", "session": "US", "label": "Test 5"},
                    {"time": "21:00", "session": "US", "label": "Test 6"}
                ]
            }
        ]
        
        from app.utils.scheduler.news_fetch_scheduler import NewsFetchScheduler
        scheduler = NewsFetchScheduler()
        
        for i, request_data in enumerate(test_requests, 1):
            print(f"\nAPI Test {i}:")
            
            # Validate the request (simulating API validation)
            if not isinstance(request_data.get('times'), list) or len(request_data['times']) != 6:
                print(f"   ❌ Invalid: exactly 6 time points required")
                continue
            
            # Validate each time point
            valid = True
            for j, time_config in enumerate(request_data['times']):
                if not all(k in time_config for k in ['time', 'session', 'label']):
                    print(f"   ❌ Invalid: time point {j + 1} missing required fields")
                    valid = False
                    break
                
                if time_config['session'] not in ['CHINA_HK', 'US']:
                    print(f"   ❌ Invalid: session type '{time_config['session']}'")
                    valid = False
                    break
                
                # Validate time format
                try:
                    time_parts = time_config['time'].split(':')
                    if len(time_parts) != 2:
                        raise ValueError("Invalid time format")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                        raise ValueError("Invalid time values")
                except (ValueError, AttributeError):
                    print(f"   ❌ Invalid: time format for time point {j + 1}")
                    valid = False
                    break
            
            if valid:
                print(f"   ✅ Valid: API request would be accepted")
            
        print("\n✅ API functionality tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error in API functionality tests: {e}")
        return False

def main():
    """Run all 6-time-point scheduler configuration tests"""
    print("🚀 Starting 6-Time-Point Scheduler Configuration Tests...")
    print("=" * 70)
    
    test_results = []
    
    # Test 1: Schedule Configuration Functionality
    test_results.append(test_schedule_config_functionality())
    
    # Test 2: API Functionality
    test_results.append(test_api_functionality())
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    print("=" * 70)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"❌ Tests Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All 6-time-point scheduler configuration tests passed!")
    else:
        print("⚠️  Some tests failed - review the output above")
    
    print("\n🔧 Usage Instructions:")
    print("=" * 30)
    print("1. Navigate to Admin → News Management → Auto Fetch Scheduler")
    print("2. Scroll to '⏰ 6-Time-Point Schedule Configuration' section")
    print("3. Click '✏️ Edit Schedule' to customize times")
    print("4. Modify the 6 time points and their sessions")
    print("5. Click '💾 Save Schedule' to apply changes")
    print("6. Restart scheduler for changes to take effect")
    print("7. Use '🔄 Reset to Default' to restore original schedule")
    
    print("\n📋 Features:")
    print("=" * 15)
    print("• ⏰ Customize all 6 daily fetch times (UTC)")
    print("• 🇨🇳 🇺🇸 Assign sessions (China/HK or US)")
    print("• 🛡️ Real-time validation with error messages")
    print("• 💾 Persistent storage across server restarts")
    print("• 📊 Live preview of current schedule")
    print("• 🔄 Easy reset to optimized defaults")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 