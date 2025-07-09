#!/usr/bin/env python3
"""
Coolify AI Models Test Script
Tests AI functionality directly on Coolify deployment using production environment

Usage on Coolify:
    python test_coolify_ai_models.py
"""

import os
import sys
import json
from datetime import datetime
from openai import OpenAI

def log(message):
    """Simple logging with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def test_api_connection():
    """Test OpenRouter API connection"""
    log("🔍 Testing OpenRouter API Connection...")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        log("❌ OPENROUTER_API_KEY not found in environment")
        return None
    
    log(f"✅ API Key found: ...{api_key[-8:]}")
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        # Test with a simple free model
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",
                "X-Title": "TrendWise Coolify Test"
            },
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[{"role": "user", "content": "Say 'API Working' in exactly 2 words."}],
            max_tokens=10,
            temperature=0.1,
            timeout=15
        )
        
        response = completion.choices[0].message.content.strip()
        log(f"✅ API Connection Success: {response}")
        return client
        
    except Exception as e:
        log(f"❌ API Connection Failed: {str(e)}")
        return None

def test_deepseek_model(client):
    """Test DeepSeek model for AI summary generation"""
    log("🤖 Testing DeepSeek V3 Model...")
    
    test_content = """Apple Inc. reported strong Q4 earnings with revenue of $94.9 billion, up 6% year-over-year. iPhone revenue reached $46.2 billion, while services generated $22.3 billion with 12% growth."""
    
    prompt = f"""Create a brief summary with this format:

**Key Points**
- Main financial result
- Key product performance

**Context**
- Market significance

Article: {test_content}"""
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",
                "X-Title": "TrendWise DeepSeek Test"
            },
            model="deepseek/deepseek-r1-0528-qwen3-8b:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
            timeout=30
        )
        
        response = completion.choices[0].message.content.strip()
        log("✅ DeepSeek V3 Response:")
        print("---")
        print(response)
        print("---")
        return True
        
    except Exception as e:
        log(f"❌ DeepSeek V3 Failed: {str(e)}")
        return False

def test_claude_model(client):
    """Test Claude model for AI insights generation"""
    log("🧠 Testing Claude Sonnet 3.7 Model...")
    
    test_content = """Apple Inc. reported strong Q4 earnings with revenue of $94.9 billion, up 6% year-over-year. iPhone revenue reached $46.2 billion, while services generated $22.3 billion with 12% growth."""
    
    prompt = f"""Analyze this earnings report and provide insights:

**Market Implications**
- What this means for investors
- Key growth drivers

**Conclusion**
- Overall assessment

Article: {test_content}"""
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",
                "X-Title": "TrendWise Claude Test"
            },
            model="anthropic/claude-3.7-sonnet",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
            timeout=30
        )
        
        response = completion.choices[0].message.content.strip()
        log("✅ Claude Sonnet 3.7 Response:")
        print("---")
        print(response)
        print("---")
        return True
        
    except Exception as e:
        log(f"❌ Claude Sonnet 3.7 Failed: {str(e)}")
        return False

def test_sentiment_analysis(client):
    """Test sentiment analysis"""
    log("💭 Testing Sentiment Analysis...")
    
    test_content = """Apple Inc. reported strong Q4 earnings with revenue of $94.9 billion, up 6% year-over-year."""
    
    prompt = f"""Rate the sentiment of this news from -100 (very negative) to +100 (very positive). Return only the number.

News: {test_content}"""
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",
                "X-Title": "TrendWise Sentiment Test"
            },
            model="deepseek/deepseek-r1-0528-qwen3-8b:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1,
            timeout=15
        )
        
        response = completion.choices[0].message.content.strip()
        log(f"✅ Sentiment Score: {response}")
        return True
        
    except Exception as e:
        log(f"❌ Sentiment Analysis Failed: {str(e)}")
        return False

def test_keyword_extraction(client):
    """Test keyword extraction"""
    log("🔍 Testing Keyword Extraction...")
    
    test_content = """Apple Inc. reported strong Q4 earnings with revenue of $94.9 billion, up 6% year-over-year."""
    
    prompt = f"""Extract 3-5 key financial terms from this news as a JSON array:

[
  {{"keyword": "term", "category": "financial", "relevance": 0.9}},
  ...
]

News: {test_content}"""
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://trendwise.com",
                "X-Title": "TrendWise Keywords Test"
            },
            model="deepseek/deepseek-r1-0528-qwen3-8b:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
            timeout=20
        )
        
        response = completion.choices[0].message.content.strip()
        log("✅ Keywords Extracted:")
        print("---")
        print(response)
        print("---")
        return True
        
    except Exception as e:
        log(f"❌ Keyword Extraction Failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 TrendWise AI Models Test - Coolify Deployment")
    print("=" * 60)
    
    # Test API connection
    client = test_api_connection()
    if not client:
        print("\n❌ CRITICAL: Cannot connect to OpenRouter API")
        print("🔧 Action needed:")
        print("  1. Check OPENROUTER_API_KEY in Coolify environment")
        print("  2. Verify API key is valid in OpenRouter dashboard")
        print("  3. Check account status and credits")
        sys.exit(1)
    
    print("\n🧪 Running AI Model Tests...")
    print("-" * 40)
    
    # Run all tests
    tests = [
        ("DeepSeek V3 Summary", lambda: test_deepseek_model(client)),
        ("Claude Sonnet 3.7 Insights", lambda: test_claude_model(client)),
        ("Sentiment Analysis", lambda: test_sentiment_analysis(client)),
        ("Keyword Extraction", lambda: test_keyword_extraction(client))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Your AI models are working correctly on Coolify")
        print("💡 You can now proceed with confidence that AI functionality is operational")
    elif passed > 0:
        print("⚠️ PARTIAL SUCCESS")
        print("🔧 Some AI functions are working, others need attention")
        print("💡 Check the failed tests above for specific issues")
    else:
        print("❌ ALL TESTS FAILED")
        print("🚨 AI functionality is not working")
        print("🔧 Check OpenRouter API key and account status")
    
    print("\n🌐 OpenRouter Dashboard: https://openrouter.ai/dashboard")
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 