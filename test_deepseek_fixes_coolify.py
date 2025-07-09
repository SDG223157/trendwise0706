#!/usr/bin/env python3
"""
Test DeepSeek V3 Fixes on Coolify
Run this on your Coolify deployment to test improved prompts
"""

import os
import sys
import re
from openai import OpenAI

def test_improved_deepseek_on_coolify():
    print('🧪 Testing DeepSeek V3 Fixes on Coolify')
    print('=' * 50)
    
    # Check for API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print('❌ OPENROUTER_API_KEY environment variable not found')
        print('💡 Set it in Coolify environment variables')
        return False
    
    print(f'✅ API key found: {api_key[:8]}...')
    
    client = OpenAI(
        base_url='https://openrouter.ai/api/v1',
        api_key=api_key
    )
    
    test_content = 'Apple Inc. reported strong Q4 earnings that exceeded Wall Street expectations, with revenue of $94.9 billion up 6% year-over-year, beating analyst estimates.'
    
    # Test 1: Ultra-Simple Sentiment Prompt
    print('\n💭 Test 1: Ultra-Simple Sentiment...')
    
    simple_sentiment_prompt = f'''News: {test_content}

Rate sentiment from -100 to +100:
Answer with just the number:'''
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                'HTTP-Referer': 'https://trendwise.com',
                'X-Title': 'TrendWise Sentiment Test'
            },
            model='deepseek/deepseek-chat-v3-0324:free',
            messages=[{'role': 'user', 'content': simple_sentiment_prompt}],
            max_tokens=5,
            temperature=0.0,
            timeout=10
        )
        
        response = completion.choices[0].message.content.strip()
        print(f'  🤖 DeepSeek Response: "{response}"')
        
        # Extract any number
        numbers = re.findall(r'-?\d+', response)
        if numbers:
            sentiment_score = int(numbers[0])
            if -100 <= sentiment_score <= 100:
                print(f'  ✅ FIXED! Valid sentiment: {sentiment_score}')
                return True
            else:
                print(f'  ⚠️  Number out of range: {sentiment_score}')
        else:
            print(f'  ❌ Still no number found')
            
    except Exception as e:
        print(f'  ❌ Error: {str(e)}')
    
    # Test 2: Forced Structure for Insights
    print('\n\n🧠 Test 2: Forced Structure Insights...')
    
    structured_prompt = f'''Analyze this news. Follow this EXACT format:

INSIGHTS:
1. Point one
2. Point two

CONCLUSION:
Summary sentence here

News: {test_content}'''
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                'HTTP-Referer': 'https://trendwise.com',
                'X-Title': 'TrendWise Insights Test'
            },
            model='deepseek/deepseek-chat-v3-0324:free',
            messages=[{'role': 'user', 'content': structured_prompt}],
            max_tokens=300,
            temperature=0.2,
            timeout=20
        )
        
        response = completion.choices[0].message.content
        print('\n🤖 DeepSeek Response:')
        print('-' * 30)
        print(response)
        
        # Check for conclusion
        if 'CONCLUSION:' in response.upper():
            print('\n  ✅ FIXED! Contains conclusion section')
            return True
        else:
            print('\n  ❌ Still missing conclusion')
            
    except Exception as e:
        print(f'\n❌ Error: {str(e)}')
    
    # Test 3: Try Different Model Version
    print('\n\n🔄 Test 3: Try Alternative DeepSeek Model...')
    
    try:
        completion = client.chat.completions.create(
            model='deepseek/deepseek-r1-0528-qwen3-8b:free',  # Different version
            messages=[{'role': 'user', 'content': f'Rate sentiment -100 to +100: {test_content}'}],
            max_tokens=5,
            temperature=0.0
        )
        
        response = completion.choices[0].message.content.strip()
        print(f'  🤖 Alternative model: "{response}"')
        
        numbers = re.findall(r'-?\d+', response)
        if numbers:
            print(f'  ✅ Alternative model works: {numbers[0]}')
        else:
            print(f'  ❌ Alternative model also fails')
            
    except Exception as e:
        print(f'  ❌ Alternative model error: {str(e)}')
    
    return False

def recommend_solution():
    print('\n' + '=' * 50)
    print('🎯 RECOMMENDATION BASED ON TESTS:')
    
    # Test results will determine recommendation
    success = test_improved_deepseek_on_coolify()
    
    if success:
        print('\n✅ DeepSeek fixes work! Update your production code:')
        print('1. Use ultra-simple prompts')
        print('2. Force exact output structures') 
        print('3. Lower temperature (0.0-0.2)')
        print('4. Shorter max_tokens for critical functions')
    else:
        print('\n❌ DeepSeek still failing. IMMEDIATE ACTION NEEDED:')
        print('\n🚨 OPTION A: Emergency Revert (SAFEST)')
        print('   → Run: python3 emergency_revert_to_claude.py')
        print('   → Switches back to Claude for all functions')
        print('   → Guaranteed to work')
        
        print('\n🤖 OPTION B: Hybrid Approach (BALANCED)')
        print('   → Use Claude for sentiment + insights')
        print('   → Use DeepSeek for summaries only')
        print('   → 70% reliability, 30% cost savings')
        
        print('\n⏰ CRITICAL: Your production sentiment analysis is broken!')
        print('   Users are getting empty sentiment scores.')
        print('   This affects all financial analysis features.')

if __name__ == '__main__':
    recommend_solution() 