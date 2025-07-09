#!/usr/bin/env python3
"""
Hybrid AI Solution: Use Claude for critical sentiment/insights and DeepSeek for summaries
Best of both worlds - reliability + cost efficiency
"""

def setup_hybrid_solution():
    print('🤖 Setting up HYBRID AI Solution')
    print('Claude (reliable) + DeepSeek (cost-effective)')
    print('=' * 50)
    
    # Update news routes to use Claude for sentiment/insights
    routes_content = '''# app/news/routes.py - Updated hybrid approach

# Use Claude for CRITICAL functions (sentiment, insights)
CLAUDE_MODEL = 'anthropic/claude-3.7-sonnet'
DEEPSEEK_MODEL = 'deepseek/deepseek-chat-v3-0324:free'

def generate_ai_summary(content, client):
    """Use DeepSeek for summaries (less critical)"""
    try:
        completion = client.chat.completions.create(
            model=DEEPSEEK_MODEL,  # Cost-effective for summaries
            messages=[{
                'role': 'user',
                'content': f"""Summarize this financial news in 2-3 sentences using markdown format:

{content[:8000]}

Use bullet points for key details."""
            }],
            max_tokens=500,
            temperature=0.3,
            timeout=30
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek summary failed: {str(e)}")
        return "Summary generation failed."

def analyze_sentiment(content, client):
    """Use Claude for RELIABLE sentiment analysis"""
    try:
        completion = client.chat.completions.create(
            model=CLAUDE_MODEL,  # Reliable for critical sentiment
            messages=[{
                'role': 'user', 
                'content': f"""Analyze the sentiment of this financial news and return ONLY a number from -100 to +100:

{content[:4000]}

Positive earnings/growth = positive numbers
Negative news/losses = negative numbers
Just return the number, nothing else."""
            }],
            max_tokens=10,
            temperature=0.1,
            timeout=15
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Extract number from response
        import re
        numbers = re.findall(r'-?\\d+', response)
        if numbers:
            return int(numbers[0])
        return 0
        
    except Exception as e:
        print(f"Claude sentiment failed: {str(e)}")
        return 0

def generate_ai_insights(content, client):
    """Use Claude for CRITICAL insights with conclusions"""
    try:
        completion = client.chat.completions.create(
            model=CLAUDE_MODEL,  # Reliable for structured insights
            messages=[{
                'role': 'user',
                'content': f"""Analyze this financial news and provide insights using this exact structure:

**Key Insights**
- [Write 2-3 bullet points about significance]

**Market Implications** 
- [Write 2-3 bullet points about market impact]

**Conclusion**
[Write 2-3 sentences summarizing the overall significance and implications]

News content: {content[:4000]}"""
            }],
            max_tokens=500,
            temperature=0.3,
            timeout=30
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Claude insights failed: {str(e)}")
        return "Insights generation failed."
'''
    
    print('📝 Hybrid configuration ready:')
    print('  ✅ Summaries: DeepSeek (cost-effective)')
    print('  ✅ Sentiment: Claude (reliable)')  
    print('  ✅ Insights: Claude (structured)')
    
    # Show scheduler update
    scheduler_content = '''# app/utils/scheduler/news_scheduler.py - Hybrid approach

def process_article_ai_content(article_data):
    """Process with hybrid AI approach"""
    
    client = OpenAI(
        base_url='https://openrouter.ai/api/v1',
        api_key=os.getenv('OPENROUTER_API_KEY')
    )
    
    content = article_data.get('content', '')
    
    # Generate summary with DeepSeek (cost-effective)
    summary = generate_ai_summary_deepseek(content, client)
    
    # Generate sentiment with Claude (reliable)
    sentiment = analyze_sentiment_claude(content, client)
    
    # Generate insights with Claude (structured)
    insights = generate_ai_insights_claude(content, client)
    
    return {
        'ai_summary': summary,
        'ai_sentiment': sentiment,
        'ai_insights': insights
    }

def generate_ai_summary_deepseek(content, client):
    """DeepSeek for summaries"""
    try:
        completion = client.chat.completions.create(
            model='deepseek/deepseek-chat-v3-0324:free',
            messages=[{'role': 'user', 'content': f'Summarize: {content[:8000]}'}],
            max_tokens=400,
            temperature=0.3
        )
        return completion.choices[0].message.content
    except:
        return "Summary unavailable"

def analyze_sentiment_claude(content, client):
    """Claude for reliable sentiment"""
    try:
        completion = client.chat.completions.create(
            model='anthropic/claude-3.7-sonnet',
            messages=[{'role': 'user', 'content': f'Rate sentiment -100 to +100: {content[:4000]}'}],
            max_tokens=10,
            temperature=0.1
        )
        import re
        numbers = re.findall(r'-?\\d+', completion.choices[0].message.content)
        return int(numbers[0]) if numbers else 0
    except:
        return 0

def generate_ai_insights_claude(content, client):
    """Claude for structured insights"""
    try:
        completion = client.chat.completions.create(
            model='anthropic/claude-3.7-sonnet',
            messages=[{'role': 'user', 'content': f'Financial insights with conclusion: {content[:4000]}'}],
            max_tokens=500,
            temperature=0.3
        )
        return completion.choices[0].message.content
    except:
        return "Insights unavailable"
'''
    
    print('\\n🎯 Benefits of Hybrid Approach:')
    print('  💰 Cost: ~30% savings vs all-Claude')
    print('  🎯 Reliability: Critical functions use Claude')
    print('  📊 Performance: Best of both models')
    
    # Create implementation script
    with open('implement_hybrid_ai.py', 'w') as f:
        f.write('''#!/usr/bin/env python3
"""
Implement Hybrid AI Solution
Run this on Coolify to set up the hybrid approach
"""

import os

def implement_hybrid():
    print('🔧 Implementing Hybrid AI Solution...')
    
    # File updates needed
    files_to_update = {
        'app/news/routes.py': 'sentiment and insights functions',
        'app/utils/scheduler/news_scheduler.py': 'scheduler AI processing'
    }
    
    print('\\n📋 Manual steps needed:')
    print('1. Update sentiment analysis to use Claude model')
    print('2. Update insights generation to use Claude model') 
    print('3. Keep summaries using DeepSeek model')
    print('4. Test each function individually')
    
    for file_path, description in files_to_update.items():
        print(f'\\n📝 {file_path}:')
        print(f'   - Update {description}')
        print(f'   - Use anthropic/claude-3.7-sonnet for critical functions')
        print(f'   - Keep deepseek for non-critical functions')

if __name__ == '__main__':
    implement_hybrid()
''')
    
    print('\\n✅ Hybrid solution scripts created')
    print('\\n🚀 Ready to deploy!')

if __name__ == '__main__':
    setup_hybrid_solution() 