#!/usr/bin/env python3
"""
Live AI Model Comparison: DeepSeek V3 vs Claude Sonnet 3.5
Tests actual AI processing quality and format compatibility

Usage on Coolify:
    python ai_model_comparison_live.py
"""

import os
import sys
import json
import time
from datetime import datetime
from openai import OpenAI

def test_ai_summary_comparison():
    """Compare AI summary generation between models"""
    print("📰 Testing AI Summary Generation...")
    
    test_article = {
        'title': 'Apple Reports Strong Q4 Earnings Driven by iPhone Sales and Services Growth',
        'content': '''Apple Inc. (AAPL) reported fourth-quarter earnings that exceeded Wall Street expectations, driven by robust iPhone sales and continued growth in its services segment. The tech giant posted revenue of $94.9 billion, up 6% year-over-year, beating analyst estimates of $94.4 billion.

iPhone revenue reached $46.2 billion, representing a 3% increase from the previous year, despite concerns about softening demand in China. The services business, which includes the App Store, iCloud, and Apple Pay, generated $22.3 billion in revenue, marking a 12% year-over-year growth.

CEO Tim Cook highlighted the company's strong performance in emerging markets and the growing adoption of Apple's ecosystem products. "We're seeing incredible momentum across our product portfolio, particularly in services and wearables," Cook said during the earnings call.

The company's gross margin improved to 45.2%, up from 43.3% in the same quarter last year, reflecting better pricing strategies and cost management. Apple also announced a $90 billion share buyback program and raised its quarterly dividend by 4%.

Looking ahead, Apple provided guidance for Q1 2024 revenue between $89-93 billion, slightly below analyst expectations of $94.2 billion. The company cited potential headwinds from foreign exchange rates and economic uncertainty in key markets.'''
    }
    
    prompt = f"""Generate summary with STRICT markdown formatting:

**Key Concepts/Keywords**  
- [Extract 3-5 key financial/market concepts, company names, or important terms]
- [Each item should be a specific concept, not generic placeholders]

**Key Points**  
- [Extract 3-5 main factual points from the article]
- [Focus on concrete facts, numbers, events, or developments]

**Context**  
- [Provide 2-4 background context items that help understand the significance]
- [Include market conditions, historical context, or related developments]

Use proper line breaks between list items. Article: {test_article['content']}"""
    
    return test_both_models("AI Summary", prompt, max_tokens=750)

def test_ai_insights_comparison():
    """Compare AI insights generation between models"""
    print("🧠 Testing AI Insights Generation...")
    
    test_article = {
        'title': 'Apple Reports Strong Q4 Earnings Driven by iPhone Sales and Services Growth',
        'content': '''Apple Inc. (AAPL) reported fourth-quarter earnings that exceeded Wall Street expectations, driven by robust iPhone sales and continued growth in its services segment. The tech giant posted revenue of $94.9 billion, up 6% year-over-year, beating analyst estimates of $94.4 billion.

iPhone revenue reached $46.2 billion, representing a 3% increase from the previous year, despite concerns about softening demand in China. The services business, which includes the App Store, iCloud, and Apple Pay, generated $22.3 billion in revenue, marking a 12% year-over-year growth.

CEO Tim Cook highlighted the company's strong performance in emerging markets and the growing adoption of Apple's ecosystem products.'''
    }
    
    prompt = f"""Generate insights with STRICT markdown formatting:

**Key Insights**  
- [Extract 3-5 key financial insights, market trends, or strategic implications]
- [Focus on actionable insights for investors and traders]

**Market Implications**  
- [Identify 2-4 specific market implications or potential impacts]
- [Consider effects on sectors, competitors, or broader markets]

**Conclusion**  
- [Provide a clear, concise conclusion summarizing the overall significance]

Use proper line breaks between list items. Article: {test_article['content']}"""
    
    return test_both_models("AI Insights", prompt, max_tokens=750)

def test_sentiment_comparison():
    """Compare sentiment analysis between models"""
    print("💭 Testing Sentiment Analysis...")
    
    test_content = "Apple Inc. reported fourth-quarter earnings that exceeded Wall Street expectations, driven by robust iPhone sales and continued growth in its services segment. The tech giant posted revenue of $94.9 billion, up 6% year-over-year, beating analyst estimates."
    
    prompt = f"Analyze the market sentiment of this article and provide a single number rating from -100 (extremely bearish) to 100 (extremely bullish). Only return the number: {test_content}"
    
    return test_both_models("Sentiment Analysis", prompt, max_tokens=10, temperature=0.1)

def test_keyword_extraction_comparison():
    """Compare keyword extraction between models"""
    print("🔍 Testing Keyword Extraction...")
    
    test_content = "Apple Inc. reported fourth-quarter earnings that exceeded Wall Street expectations, driven by robust iPhone sales and continued growth in its services segment."
    
    prompt = f"""Analyze this financial news article and extract the most important keywords and concepts that users might search for.

Return ONLY a JSON array of objects with this exact format:
[
    {{"keyword": "keyword_text", "category": "category_name", "relevance": score}},
    ...
]

Categories should be one of: company, technology, financial, industry, concept, person, location
Relevance scores should be 0.0 to 1.0 (higher = more important for search)
Extract 5-10 keywords maximum.
Focus on searchable terms that users would actually type.

Article: {test_content}"""
    
    return test_both_models("Keyword Extraction", prompt, max_tokens=400)

def test_search_suggestions_comparison():
    """Compare search suggestions between models"""
    print("🔎 Testing Search Suggestions...")
    
    test_query = "AI technology"
    prompt = f"""The user searched for "{test_query}" in a financial news database but got no results. 

Generate 5-8 alternative search terms that are more likely to find relevant financial news articles. Consider:
- Synonyms and related financial terms
- Company symbols vs company names
- Industry sectors and categories
- Financial events and terminology
- Broader or more specific terms

Return ONLY a JSON array of suggestions with this format:
[
    {{"term": "alternative search term", "type": "synonym", "reason": "brief explanation"}},
    {{"term": "another term", "type": "symbol", "reason": "brief explanation"}}
]

Types should be: "synonym", "symbol", "industry", "broader", "specific", "related"

Original query: "{test_query}" """
    
    return test_both_models("Search Suggestions", prompt, max_tokens=500, temperature=0.7)

def test_both_models(test_name, prompt, max_tokens=750, temperature=0.3):
    """Test both models with the same prompt and compare results"""
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found")
        return None
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    models = {
        'DeepSeek V3': 'deepseek/deepseek-r1-0528-qwen3-8b:free',
        'Claude Sonnet 3.7': 'anthropic/claude-3.7-sonnet'
    }
    
    results = {}
    
    for model_name, model_id in models.items():
        print(f"  🤖 Testing {model_name}...")
        
        try:
            start_time = time.time()
            
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://trendwise.com",
                    "X-Title": "TrendWise Model Comparison"
                },
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30
            )
            
            end_time = time.time()
            response = completion.choices[0].message.content
            
            results[model_name] = {
                'response': response,
                'response_time': round(end_time - start_time, 2),
                'tokens_used': getattr(completion.usage, 'total_tokens', 'N/A') if hasattr(completion, 'usage') else 'N/A',
                'success': True
            }
            
            print(f"    ✅ {model_name}: {len(response)} chars, {results[model_name]['response_time']}s")
            
        except Exception as e:
            print(f"    ❌ {model_name}: {str(e)}")
            results[model_name] = {
                'response': None,
                'error': str(e),
                'success': False
            }
    
    # Display comparison
    print(f"\n📊 {test_name} Comparison:")
    print("=" * 80)
    
    for model_name in models.keys():
        result = results[model_name]
        if result['success']:
            print(f"\n🤖 {model_name} ({result['response_time']}s, {result['tokens_used']} tokens):")
            print("-" * 60)
            print(result['response'])
        else:
            print(f"\n❌ {model_name}: {result['error']}")
    
    print("\n" + "=" * 80)
    return results

def analyze_comparison_results(all_results):
    """Analyze and compare overall performance"""
    print("\n📈 OVERALL COMPARISON ANALYSIS")
    print("=" * 80)
    
    models = ['DeepSeek V3', 'Claude Sonnet 3.7']
    
    # Success rates
    for model in models:
        successes = sum(1 for test_results in all_results.values() 
                       if model in test_results and test_results[model]['success'])
        total_tests = len(all_results)
        success_rate = (successes / total_tests) * 100
        print(f"📊 {model}: {successes}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    # Average response times
    print(f"\n⏱️ Average Response Times:")
    for model in models:
        times = [test_results[model]['response_time'] 
                for test_results in all_results.values() 
                if model in test_results and test_results[model]['success']]
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"  {model}: {avg_time:.2f}s")
    
    # Response length comparison
    print(f"\n📏 Average Response Lengths:")
    for model in models:
        lengths = [len(test_results[model]['response']) 
                  for test_results in all_results.values() 
                  if model in test_results and test_results[model]['success'] and test_results[model]['response']]
        
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            print(f"  {model}: {avg_length:.0f} characters")

def main():
    """Run comprehensive AI model comparison"""
    print("🔬 TrendWise AI Model Comparison: DeepSeek V3 vs Claude Sonnet 3.5")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API key
    if not os.getenv('OPENROUTER_API_KEY'):
        print("❌ OPENROUTER_API_KEY environment variable not found")
        print("💡 Make sure you're running this on Coolify with the proper environment")
        sys.exit(1)
    
    # Run all comparison tests
    all_results = {}
    
    try:
        print("\n🚀 Running AI Model Comparison Tests...")
        
        all_results['Summary'] = test_ai_summary_comparison()
        time.sleep(2)  # Brief pause between tests
        
        all_results['Insights'] = test_ai_insights_comparison()
        time.sleep(2)
        
        all_results['Sentiment'] = test_sentiment_comparison()
        time.sleep(2)
        
        all_results['Keywords'] = test_keyword_extraction_comparison()
        time.sleep(2)
        
        all_results['Suggestions'] = test_search_suggestions_comparison()
        
        # Overall analysis
        analyze_comparison_results(all_results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_comparison_results_{timestamp}.json"
        
        # Prepare results for JSON serialization
        json_results = {}
        for test_name, test_results in all_results.items():
            if test_results:
                json_results[test_name] = test_results
        
        with open(filename, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error during comparison: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 