#!/usr/bin/env python3
"""
AI Model Comparison Test Script
Tests DeepSeek V3 vs Claude Sonnet 3.5 output format compatibility

This script validates that DeepSeek V3 produces the same format and quality
of results as Claude Sonnet 3.5 for all AI processing tasks in TrendWise.

The script uses hardcoded API keys for each model (no environment variables needed).

Usage:
    python test_ai_model_comparison.py
    python test_ai_model_comparison.py --verbose
    python test_ai_model_comparison.py --save-results
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from openai import OpenAI
import requests
from typing import Dict, List, Any, Optional

class AIModelTester:
    """Test AI model output format compatibility"""
    
    def __init__(self, verbose: bool = False, save_results: bool = False):
        self.verbose = verbose
        self.save_results = save_results
        self.results = {
            'test_run_id': datetime.now().isoformat(),
            'deepseek_v3': {},
            'claude_sonnet_35': {},
            'comparison_results': {}
        }
        
        # Initialize AI clients with separate API keys for each model
        self.sonnet_api_key = "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"
        self.deepseek_api_key = "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"
        
        # Create separate clients for each model
        self.sonnet_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.sonnet_api_key
        )
        
        self.deepseek_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.deepseek_api_key
        )
        
        # Sample financial news article for testing
        self.test_article = {
            'title': 'Apple Reports Strong Q4 Earnings Driven by iPhone Sales and Services Growth',
            'content': '''Apple Inc. (AAPL) reported fourth-quarter earnings that exceeded Wall Street expectations, driven by robust iPhone sales and continued growth in its services segment. The tech giant posted revenue of $94.9 billion, up 6% year-over-year, beating analyst estimates of $94.4 billion.

iPhone revenue reached $46.2 billion, representing a 3% increase from the previous year, despite concerns about softening demand in China. The services business, which includes the App Store, iCloud, and Apple Pay, generated $22.3 billion in revenue, marking a 12% year-over-year growth.

CEO Tim Cook highlighted the company's strong performance in emerging markets and the growing adoption of Apple's ecosystem products. "We're seeing incredible momentum across our product portfolio, particularly in services and wearables," Cook said during the earnings call.

The company's gross margin improved to 45.2%, up from 43.3% in the same quarter last year, reflecting better pricing strategies and cost management. Apple also announced a $90 billion share buyback program and raised its quarterly dividend by 4%.

Looking ahead, Apple provided guidance for Q1 2024 revenue between $89-93 billion, slightly below analyst expectations of $94.2 billion. The company cited potential headwinds from foreign exchange rates and economic uncertainty in key markets.

Shares of Apple rose 3.2% in after-hours trading following the earnings announcement.'''
        }
        
        self.log("AI Model Comparison Test Initialized")
        self.log("Using separate API keys for each model:")
        self.log(f"- Sonnet 3.5: ...{self.sonnet_api_key[-8:]}")
        self.log(f"- DeepSeek V3: ...{self.deepseek_api_key[-8:]}")
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] {level}: {message}")
    
    def call_ai_model(self, model: str, prompt: str, max_tokens: int = 750, temperature: float = 0.3) -> Optional[str]:
        """Call AI model and return response"""
        try:
            # Select the appropriate client based on the model
            if "sonnet" in model.lower() or "claude" in model.lower() or "anthropic" in model.lower():
                client = self.sonnet_client
                self.log(f"Using Sonnet API key for model: {model}")
            elif "deepseek" in model.lower():
                client = self.deepseek_client
                self.log(f"Using DeepSeek API key for model: {model}")
            else:
                # Default to DeepSeek for unknown models
                client = self.deepseek_client
                self.log(f"Using DeepSeek API key (default) for model: {model}")
            
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://trendwise.com",
                    "X-Title": "TrendWise AI Model Test"
                },
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            self.log(f"Error calling {model}: {str(e)}", "ERROR")
            return None
    
    def test_ai_summary_generation(self) -> Dict[str, Any]:
        """Test AI summary generation format"""
        self.log("Testing AI Summary Generation...")
        
        prompt = f"""Analyze this news article and create a structured summary using EXACTLY this format:

**Key Concepts/Keywords**  
- [Extract 3-5 key financial/market concepts, company names, or important terms]
- [Each item should be a specific concept, not generic placeholders]

**Key Points**  
- [Extract 3-5 main factual points from the article]
- [Focus on concrete facts, numbers, events, or developments]

**Context**  
- [Provide 2-4 background context items that help understand the significance]
- [Include market conditions, historical context, or related developments]

IMPORTANT: Replace ALL bracketed placeholders with actual content from the article. Do not use generic terms like "Keyword 1" or "Point 1".

Title: {self.test_article['title']}
Content: {self.test_article['content']}"""
        
        # Test both models
        deepseek_result = self.call_ai_model("deepseek/deepseek-chat-v3-0324:free", prompt)
        claude_result = self.call_ai_model("anthropic/claude-3.5-sonnet", prompt)
        
        results = {
            'deepseek_v3': deepseek_result,
            'claude_sonnet_35': claude_result,
            'format_validation': self._validate_summary_format(deepseek_result),
            'content_comparison': self._compare_summary_content(deepseek_result, claude_result)
        }
        
        self.results['deepseek_v3']['summary'] = deepseek_result
        self.results['claude_sonnet_35']['summary'] = claude_result
        
        return results
    
    def test_ai_insights_generation(self) -> Dict[str, Any]:
        """Test AI insights generation format"""
        self.log("Testing AI Insights Generation...")
        
        prompt = f"""Analyze this news article and create structured financial insights using EXACTLY this format:

**Key Insights**  
- [Extract 3-5 key financial insights, market trends, or strategic implications]
- [Focus on actionable insights for investors and traders]

**Market Implications**  
- [Identify 2-4 specific market implications or potential impacts]
- [Consider effects on sectors, competitors, or broader markets]

**Conclusion**  
- [Provide a clear, concise conclusion summarizing the overall significance]

IMPORTANT: Replace ALL bracketed placeholders with actual insights from the article. Do not use generic terms like "Insight 1" or "Implication 1".

Title: {self.test_article['title']}
Content: {self.test_article['content']}"""
        
        # Test both models
        deepseek_result = self.call_ai_model("deepseek/deepseek-chat-v3-0324:free", prompt)
        claude_result = self.call_ai_model("anthropic/claude-3.5-sonnet", prompt)
        
        results = {
            'deepseek_v3': deepseek_result,
            'claude_sonnet_35': claude_result,
            'format_validation': self._validate_insights_format(deepseek_result),
            'content_comparison': self._compare_insights_content(deepseek_result, claude_result)
        }
        
        self.results['deepseek_v3']['insights'] = deepseek_result
        self.results['claude_sonnet_35']['insights'] = claude_result
        
        return results
    
    def test_sentiment_analysis(self) -> Dict[str, Any]:
        """Test sentiment analysis format"""
        self.log("Testing Sentiment Analysis...")
        
        prompt = f"""Analyze the market sentiment of this article and provide a single number rating from -100 (extremely bearish) to 100 (extremely bullish). Only return the number: 

Title: {self.test_article['title']}
Content: {self.test_article['content']}"""
        
        # Test both models
        deepseek_result = self.call_ai_model("deepseek/deepseek-chat-v3-0324:free", prompt, max_tokens=10, temperature=0.1)
        claude_result = self.call_ai_model("anthropic/claude-3.5-sonnet", prompt, max_tokens=10, temperature=0.1)
        
        results = {
            'deepseek_v3': deepseek_result,
            'claude_sonnet_35': claude_result,
            'format_validation': self._validate_sentiment_format(deepseek_result),
            'score_comparison': self._compare_sentiment_scores(deepseek_result, claude_result)
        }
        
        self.results['deepseek_v3']['sentiment'] = deepseek_result
        self.results['claude_sonnet_35']['sentiment'] = claude_result
        
        return results
    
    def test_keyword_extraction(self) -> Dict[str, Any]:
        """Test keyword extraction format"""
        self.log("Testing Keyword Extraction...")
        
        prompt = f"""Analyze this financial news article and extract the most important keywords and concepts that users might search for.

Return ONLY a JSON array of objects with this exact format:
[
    {{"keyword": "keyword_text", "category": "category_name", "relevance": score}},
    ...
]

Categories should be one of: company, technology, financial, industry, concept, person, location
Relevance scores should be 0.0 to 1.0 (higher = more important for search)
Extract 5-15 keywords maximum.
Focus on searchable terms that users would actually type.

Title: {self.test_article['title']}
Content: {self.test_article['content'][:4000]}"""
        
        # Test both models
        deepseek_result = self.call_ai_model("deepseek/deepseek-chat-v3-0324:free", prompt, max_tokens=500)
        claude_result = self.call_ai_model("anthropic/claude-3.5-sonnet", prompt, max_tokens=500)
        
        results = {
            'deepseek_v3': deepseek_result,
            'claude_sonnet_35': claude_result,
            'format_validation': self._validate_keyword_format(deepseek_result),
            'content_comparison': self._compare_keyword_content(deepseek_result, claude_result)
        }
        
        self.results['deepseek_v3']['keywords'] = deepseek_result
        self.results['claude_sonnet_35']['keywords'] = claude_result
        
        return results
    
    def test_search_suggestions(self) -> Dict[str, Any]:
        """Test search suggestions format"""
        self.log("Testing Search Suggestions...")
        
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
        
        # Test both models
        deepseek_result = self.call_ai_model("deepseek/deepseek-chat-v3-0324:free", prompt, max_tokens=500, temperature=0.7)
        claude_result = self.call_ai_model("anthropic/claude-3.5-sonnet", prompt, max_tokens=500, temperature=0.7)
        
        results = {
            'deepseek_v3': deepseek_result,
            'claude_sonnet_35': claude_result,
            'format_validation': self._validate_suggestions_format(deepseek_result),
            'content_comparison': self._compare_suggestions_content(deepseek_result, claude_result)
        }
        
        self.results['deepseek_v3']['suggestions'] = deepseek_result
        self.results['claude_sonnet_35']['suggestions'] = claude_result
        
        return results
    
    def _validate_summary_format(self, response: str) -> Dict[str, bool]:
        """Validate summary format compliance"""
        if not response:
            return {'valid': False, 'reason': 'No response'}
        
        required_sections = ['**Key Concepts/Keywords**', '**Key Points**', '**Context**']
        validation = {
            'has_all_sections': all(section in response for section in required_sections),
            'has_bullet_points': '-' in response and response.count('-') >= 6,
            'no_generic_placeholders': not any(placeholder in response.lower() for placeholder in ['keyword 1', 'point 1', 'concept 1']),
            'proper_markdown': '**' in response,
            'reasonable_length': 200 <= len(response) <= 2000
        }
        
        validation['valid'] = all(validation.values())
        return validation
    
    def _validate_insights_format(self, response: str) -> Dict[str, bool]:
        """Validate insights format compliance"""
        if not response:
            return {'valid': False, 'reason': 'No response'}
        
        required_sections = ['**Key Insights**', '**Market Implications**', '**Conclusion**']
        validation = {
            'has_all_sections': all(section in response for section in required_sections),
            'has_bullet_points': '-' in response and response.count('-') >= 4,
            'no_generic_placeholders': not any(placeholder in response.lower() for placeholder in ['insight 1', 'implication 1']),
            'proper_markdown': '**' in response,
            'reasonable_length': 200 <= len(response) <= 2000
        }
        
        validation['valid'] = all(validation.values())
        return validation
    
    def _validate_sentiment_format(self, response: str) -> Dict[str, bool]:
        """Validate sentiment format compliance"""
        if not response:
            return {'valid': False, 'reason': 'No response'}
        
        try:
            # Extract number from response
            import re
            numbers = re.findall(r'-?\d+', response.strip())
            if numbers:
                sentiment = int(numbers[0])
                validation = {
                    'is_numeric': True,
                    'in_range': -100 <= sentiment <= 100,
                    'single_number': len(numbers) == 1,
                    'no_extra_text': len(response.strip()) <= 10
                }
            else:
                validation = {
                    'is_numeric': False,
                    'in_range': False,
                    'single_number': False,
                    'no_extra_text': False
                }
        except ValueError:
            validation = {
                'is_numeric': False,
                'in_range': False,
                'single_number': False,
                'no_extra_text': False
            }
        
        validation['valid'] = all(validation.values())
        return validation
    
    def _validate_keyword_format(self, response: str) -> Dict[str, bool]:
        """Validate keyword format compliance"""
        if not response:
            return {'valid': False, 'reason': 'No response'}
        
        try:
            # Extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                keywords = json.loads(json_str)
                
                validation = {
                    'is_json_array': isinstance(keywords, list),
                    'has_keywords': len(keywords) >= 3,
                    'not_too_many': len(keywords) <= 15,
                    'proper_structure': all(
                        isinstance(kw, dict) and 'keyword' in kw and 'category' in kw and 'relevance' in kw
                        for kw in keywords[:3]  # Check first 3
                    ),
                    'valid_categories': all(
                        kw.get('category') in ['company', 'technology', 'financial', 'industry', 'concept', 'person', 'location']
                        for kw in keywords[:3]
                    ),
                    'valid_relevance': all(
                        isinstance(kw.get('relevance'), (int, float)) and 0.0 <= kw.get('relevance', 0) <= 1.0
                        for kw in keywords[:3]
                    )
                }
            else:
                validation = {
                    'is_json_array': False,
                    'has_keywords': False,
                    'not_too_many': False,
                    'proper_structure': False,
                    'valid_categories': False,
                    'valid_relevance': False
                }
        except json.JSONDecodeError:
            validation = {
                'is_json_array': False,
                'has_keywords': False,
                'not_too_many': False,
                'proper_structure': False,
                'valid_categories': False,
                'valid_relevance': False
            }
        
        validation['valid'] = all(validation.values())
        return validation
    
    def _validate_suggestions_format(self, response: str) -> Dict[str, bool]:
        """Validate suggestions format compliance"""
        if not response:
            return {'valid': False, 'reason': 'No response'}
        
        try:
            # Extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                suggestions = json.loads(json_str)
                
                valid_types = ['synonym', 'symbol', 'industry', 'broader', 'specific', 'related']
                validation = {
                    'is_json_array': isinstance(suggestions, list),
                    'has_suggestions': len(suggestions) >= 3,
                    'not_too_many': len(suggestions) <= 10,
                    'proper_structure': all(
                        isinstance(sug, dict) and 'term' in sug and 'type' in sug and 'reason' in sug
                        for sug in suggestions[:3]
                    ),
                    'valid_types': all(
                        sug.get('type') in valid_types
                        for sug in suggestions[:3]
                    )
                }
            else:
                validation = {
                    'is_json_array': False,
                    'has_suggestions': False,
                    'not_too_many': False,
                    'proper_structure': False,
                    'valid_types': False
                }
        except json.JSONDecodeError:
            validation = {
                'is_json_array': False,
                'has_suggestions': False,
                'not_too_many': False,
                'proper_structure': False,
                'valid_types': False
            }
        
        validation['valid'] = all(validation.values())
        return validation
    
    def _compare_summary_content(self, deepseek: str, claude: str) -> Dict[str, Any]:
        """Compare summary content quality"""
        if not deepseek or not claude:
            return {'comparable': False, 'reason': 'Missing responses'}
        
        return {
            'length_similarity': abs(len(deepseek) - len(claude)) / max(len(deepseek), len(claude)) < 0.5,
            'both_have_company_mention': 'apple' in deepseek.lower() and 'apple' in claude.lower(),
            'both_have_financial_data': any(term in deepseek.lower() for term in ['billion', 'revenue', 'earnings']) and 
                                       any(term in claude.lower() for term in ['billion', 'revenue', 'earnings']),
            'similar_structure': deepseek.count('**') == claude.count('**')
        }
    
    def _compare_insights_content(self, deepseek: str, claude: str) -> Dict[str, Any]:
        """Compare insights content quality"""
        if not deepseek or not claude:
            return {'comparable': False, 'reason': 'Missing responses'}
        
        return {
            'length_similarity': abs(len(deepseek) - len(claude)) / max(len(deepseek), len(claude)) < 0.5,
            'both_mention_market_impact': any(term in deepseek.lower() for term in ['market', 'impact', 'investors']) and
                                          any(term in claude.lower() for term in ['market', 'impact', 'investors']),
            'similar_structure': deepseek.count('**') == claude.count('**')
        }
    
    def _compare_sentiment_scores(self, deepseek: str, claude: str) -> Dict[str, Any]:
        """Compare sentiment scores"""
        if not deepseek or not claude:
            return {'comparable': False, 'reason': 'Missing responses'}
        
        try:
            import re
            deepseek_nums = re.findall(r'-?\d+', deepseek.strip())
            claude_nums = re.findall(r'-?\d+', claude.strip())
            
            if deepseek_nums and claude_nums:
                deepseek_score = int(deepseek_nums[0])
                claude_score = int(claude_nums[0])
                
                return {
                    'both_numeric': True,
                    'score_difference': abs(deepseek_score - claude_score),
                    'same_sentiment_direction': (deepseek_score > 0) == (claude_score > 0),
                    'within_reasonable_range': abs(deepseek_score - claude_score) <= 30
                }
            else:
                return {'both_numeric': False}
        except:
            return {'both_numeric': False}
    
    def _compare_keyword_content(self, deepseek: str, claude: str) -> Dict[str, Any]:
        """Compare keyword extraction content"""
        if not deepseek or not claude:
            return {'comparable': False, 'reason': 'Missing responses'}
        
        try:
            # Parse both JSON responses
            def extract_keywords(response):
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                return []
            
            deepseek_keywords = extract_keywords(deepseek)
            claude_keywords = extract_keywords(claude)
            
            if deepseek_keywords and claude_keywords:
                deepseek_terms = set(kw.get('keyword', '').lower() for kw in deepseek_keywords)
                claude_terms = set(kw.get('keyword', '').lower() for kw in claude_keywords)
                
                overlap = len(deepseek_terms & claude_terms)
                total_unique = len(deepseek_terms | claude_terms)
                
                return {
                    'both_parsed': True,
                    'keyword_overlap': overlap,
                    'overlap_percentage': overlap / total_unique if total_unique > 0 else 0,
                    'similar_count': abs(len(deepseek_keywords) - len(claude_keywords)) <= 3,
                    'both_mention_apple': any('apple' in kw.get('keyword', '').lower() for kw in deepseek_keywords) and
                                          any('apple' in kw.get('keyword', '').lower() for kw in claude_keywords)
                }
            else:
                return {'both_parsed': False}
        except:
            return {'both_parsed': False}
    
    def _compare_suggestions_content(self, deepseek: str, claude: str) -> Dict[str, Any]:
        """Compare search suggestions content"""
        if not deepseek or not claude:
            return {'comparable': False, 'reason': 'Missing responses'}
        
        try:
            # Parse both JSON responses
            def extract_suggestions(response):
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                return []
            
            deepseek_suggestions = extract_suggestions(deepseek)
            claude_suggestions = extract_suggestions(claude)
            
            if deepseek_suggestions and claude_suggestions:
                deepseek_terms = set(sug.get('term', '').lower() for sug in deepseek_suggestions)
                claude_terms = set(sug.get('term', '').lower() for sug in claude_suggestions)
                
                overlap = len(deepseek_terms & claude_terms)
                total_unique = len(deepseek_terms | claude_terms)
                
                return {
                    'both_parsed': True,
                    'suggestion_overlap': overlap,
                    'overlap_percentage': overlap / total_unique if total_unique > 0 else 0,
                    'similar_count': abs(len(deepseek_suggestions) - len(claude_suggestions)) <= 2,
                    'both_suggest_ai_terms': any('artificial' in sug.get('term', '').lower() for sug in deepseek_suggestions) and
                                            any('artificial' in sug.get('term', '').lower() for sug in claude_suggestions)
                }
            else:
                return {'both_parsed': False}
        except:
            return {'both_parsed': False}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all AI model comparison tests"""
        self.log("Starting AI Model Comparison Tests...")
        start_time = time.time()
        
        # Run all tests
        test_results = {
            'summary': self.test_ai_summary_generation(),
            'insights': self.test_ai_insights_generation(),
            'sentiment': self.test_sentiment_analysis(),
            'keywords': self.test_keyword_extraction(),
            'suggestions': self.test_search_suggestions()
        }
        
        # Calculate overall compatibility score
        compatibility_scores = []
        for test_name, test_result in test_results.items():
            if 'format_validation' in test_result and test_result['format_validation'].get('valid'):
                compatibility_scores.append(1.0)
            else:
                compatibility_scores.append(0.0)
        
        overall_compatibility = sum(compatibility_scores) / len(compatibility_scores) if compatibility_scores else 0.0
        
        # Summary report
        summary_report = {
            'overall_compatibility_score': overall_compatibility,
            'total_tests': len(test_results),
            'passed_tests': sum(compatibility_scores),
            'failed_tests': len(test_results) - sum(compatibility_scores),
            'test_duration': time.time() - start_time,
            'recommendation': self._get_recommendation(overall_compatibility)
        }
        
        self.results['comparison_results'] = {
            'test_results': test_results,
            'summary_report': summary_report
        }
        
        # Save results if requested
        if self.save_results:
            self._save_results()
        
        # Print summary
        self._print_summary(summary_report, test_results)
        
        return self.results
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on compatibility score"""
        if score >= 0.8:
            return "EXCELLENT: DeepSeek V3 is fully compatible with Sonnet 3.5 format. Safe to deploy."
        elif score >= 0.6:
            return "GOOD: DeepSeek V3 is mostly compatible. Minor adjustments may be needed."
        elif score >= 0.4:
            return "MODERATE: Some format issues detected. Review and adjust prompts."
        else:
            return "POOR: Significant compatibility issues. Extensive prompt engineering required."
    
    def _save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_model_comparison_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        self.log(f"Results saved to {filename}")
    
    def _print_summary(self, summary: Dict[str, Any], test_results: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "="*60)
        print("🤖 AI MODEL COMPARISON TEST RESULTS")
        print("="*60)
        print(f"Overall Compatibility Score: {summary['overall_compatibility_score']:.1%}")
        print(f"Tests Passed: {int(summary['passed_tests'])}/{summary['total_tests']}")
        print(f"Test Duration: {summary['test_duration']:.1f} seconds")
        print(f"Recommendation: {summary['recommendation']}")
        
        print("\n📊 DETAILED TEST RESULTS:")
        print("-" * 40)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result.get('format_validation', {}).get('valid') else "❌ FAIL"
            print(f"{test_name.upper()}: {status}")
            
            if self.verbose and 'format_validation' in result:
                for key, value in result['format_validation'].items():
                    if key != 'valid':
                        icon = "✓" if value else "✗"
                        print(f"  {icon} {key}: {value}")
        
        print("\n💡 NEXT STEPS:")
        if summary['overall_compatibility_score'] >= 0.8:
            print("- ✅ DeepSeek V3 is ready for production use")
            print("- 🚀 You can confidently deploy the model switch")
        else:
            print("- 🔧 Review failed test details above")
            print("- 📝 Adjust prompts to improve format compliance")
            print("- 🧪 Re-run tests after prompt improvements")
        
        print("\n" + "="*60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test AI model compatibility')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--save-results', '-s', action='store_true', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    try:
        tester = AIModelTester(verbose=args.verbose, save_results=args.save_results)
        results = tester.run_all_tests()
        
        # Exit with appropriate code
        compatibility_score = results['comparison_results']['summary_report']['overall_compatibility_score']
        exit_code = 0 if compatibility_score >= 0.8 else 1
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 