#!/usr/bin/env python3
"""
Quick Runner for AI Model Comparison Test

This script demonstrates how to run the AI model comparison test
with separate API keys for DeepSeek V3 and Claude Sonnet 3.5.

Usage:
    python run_ai_comparison_test.py
"""

import subprocess
import sys
import os

def main():
    print("🤖 Running AI Model Comparison Test")
    print("="*50)
    print("Testing DeepSeek V3 vs Claude Sonnet 3.5 compatibility...")
    print()
    
    # Check if the test script exists
    if not os.path.exists('test_ai_model_comparison.py'):
        print("❌ Error: test_ai_model_comparison.py not found!")
        print("Make sure the test script is in the current directory.")
        sys.exit(1)
    
    try:
        # Run the test with verbose output
        print("Running test with verbose output...")
        result = subprocess.run([
            sys.executable, 
            'test_ai_model_comparison.py', 
            '--verbose',
            '--save-results'
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("Error output:")
            print(result.stderr)
        
        # Check exit code
        if result.returncode == 0:
            print("\n✅ Test completed successfully!")
            print("DeepSeek V3 is compatible with Claude Sonnet 3.5 format.")
        else:
            print(f"\n⚠️ Test completed with issues (exit code: {result.returncode})")
            print("Check the detailed output above for specific failures.")
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 5 minutes")
        print("This may indicate API issues or network problems.")
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
        
    except FileNotFoundError:
        print("❌ Python interpreter not found")
        sys.exit(1)

if __name__ == "__main__":
    main() 