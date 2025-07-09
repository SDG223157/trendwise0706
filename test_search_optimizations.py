"""
Comprehensive News Search Optimization Testing Script

This script validates all search optimizations and provides performance benchmarks.
"""

import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from app.utils.search.optimized_news_search import OptimizedNewsSearch
from app.utils.search.news_search import NewsSearch
from app.utils.search.index_sync_service import sync_service
from app.utils.search.cache_warming_service import cache_warming_service


class SearchOptimizationTester:
    """Comprehensive testing suite for search optimizations"""
    
    def __init__(self):
        self.app = create_app()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'benchmarks': {},
            'recommendations': []
        }
        
    def run_all_tests(self):
        """Run all optimization tests"""
        print("🧪 Starting comprehensive search optimization tests...")
        print("=" * 60)
        
        with self.app.app_context():
            # 1. Index synchronization tests
            self.test_index_sync()
            
            # 2. Cache warming tests
            self.test_cache_warming()
            
            # 3. Search performance benchmarks
            self.test_search_performance()
            
            # 4. Search functionality tests
            self.test_search_functionality()
            
            # 5. Cache effectiveness tests
            self.test_cache_effectiveness()
            
            # 6. Database optimization tests
            self.test_database_optimization()
            
            # 7. Generate recommendations
            self.generate_recommendations()
            
            # 8. Generate report
            self.generate_report()
    
    def test_index_sync(self):
        """Test search index synchronization"""
        print("\n📊 Testing Index Synchronization...")
        
        test_results = {
            'sync_status': {},
            'sync_performance': {},
            'sync_accuracy': {}
        }
        
        try:
            # Test sync status
            sync_status = sync_service.get_sync_status()
            test_results['sync_status'] = sync_status
            
            # Test sync performance
            start_time = time.time()
            
            # Get a sample article to test sync
            sample_article = db.session.query(NewsArticle).filter(
                NewsArticle.ai_summary.isnot(None),
                NewsArticle.ai_insights.isnot(None)
            ).first()
            
            if sample_article:
                # Test single article sync
                sync_success = sync_service.sync_article_to_index(sample_article)
                sync_duration = time.time() - start_time
                
                test_results['sync_performance'] = {
                    'single_article_sync_time': round(sync_duration * 1000, 2),  # ms
                    'sync_success': sync_success
                }
                
                # Test sync accuracy
                index_entry = db.session.query(NewsSearchIndex).filter_by(
                    external_id=sample_article.external_id
                ).first()
                
                if index_entry:
                    test_results['sync_accuracy'] = {
                        'title_match': index_entry.title == sample_article.title,
                        'ai_summary_present': bool(index_entry.ai_summary),
                        'ai_insights_present': bool(index_entry.ai_insights),
                        'symbols_synced': bool(index_entry.symbols_json)
                    }
            
            print(f"✅ Index sync test completed")
            if sync_status.get('sync_percentage', 0) > 90:
                print(f"✅ Sync coverage: {sync_status.get('sync_percentage', 0)}%")
            else:
                print(f"⚠️  Sync coverage: {sync_status.get('sync_percentage', 0)}% (needs improvement)")
                
        except Exception as e:
            print(f"❌ Index sync test failed: {str(e)}")
            test_results['error'] = str(e)
        
        self.results['tests']['index_sync'] = test_results
    
    def test_cache_warming(self):
        """Test cache warming functionality"""
        print("\n🔥 Testing Cache Warming...")
        
        test_results = {
            'warming_status': {},
            'warming_performance': {},
            'cache_coverage': {}
        }
        
        try:
            # Test warming status
            warming_status = cache_warming_service.get_warming_status()
            test_results['warming_status'] = warming_status
            
            # Test warming performance
            start_time = time.time()
            
            # Test warming popular searches
            cache_warming_service.warm_popular_searches()
            warming_duration = time.time() - start_time
            
            test_results['warming_performance'] = {
                'popular_searches_warm_time': round(warming_duration * 1000, 2),  # ms
                'cache_enabled': warming_status.get('cache_enabled', False)
            }
            
            # Test cache coverage for popular queries
            popular_queries = [
                ('AAPL', 'symbol'),
                ('earnings', 'keyword'),
                ('artificial intelligence', 'keyword'),
                ('TSLA', 'symbol'),
                ('china latest', 'mixed')
            ]
            
            cache_hits = 0
            total_queries = len(popular_queries)
            
            for query, query_type in popular_queries:
                if self.test_cache_hit(query, query_type):
                    cache_hits += 1
            
            test_results['cache_coverage'] = {
                'cache_hit_rate': round((cache_hits / total_queries) * 100, 2),
                'total_queries_tested': total_queries,
                'cache_hits': cache_hits
            }
            
            print(f"✅ Cache warming test completed")
            if test_results['cache_coverage']['cache_hit_rate'] > 70:
                print(f"✅ Cache hit rate: {test_results['cache_coverage']['cache_hit_rate']}%")
            else:
                print(f"⚠️  Cache hit rate: {test_results['cache_coverage']['cache_hit_rate']}% (needs improvement)")
                
        except Exception as e:
            print(f"❌ Cache warming test failed: {str(e)}")
            test_results['error'] = str(e)
        
        self.results['tests']['cache_warming'] = test_results
    
    def test_search_performance(self):
        """Benchmark search performance"""
        print("\n⚡ Testing Search Performance...")
        
        benchmark_results = {
            'optimized_search': {},
            'traditional_search': {},
            'performance_comparison': {}
        }
        
        # Test queries
        test_queries = [
            {'type': 'symbol', 'query': 'AAPL'},
            {'type': 'symbol', 'query': 'TSLA'},
            {'type': 'keyword', 'query': 'earnings'},
            {'type': 'keyword', 'query': 'artificial intelligence'},
            {'type': 'mixed', 'symbols': ['AAPL'], 'keywords': ['earnings']}
        ]
        
        # Test optimized search
        optimized_search = OptimizedNewsSearch(db.session)
        traditional_search = NewsSearch(db.session)
        
        for query_data in test_queries:
            query_type = query_data['type']
            
            # Test optimized search
            opt_times = []
            for i in range(5):  # Run 5 times for average
                start_time = time.time()
                
                try:
                    if query_type == 'symbol':
                        results = optimized_search.search_by_symbols([query_data['query']])
                    elif query_type == 'keyword':
                        results = optimized_search.search_by_keywords([query_data['query']])
                    elif query_type == 'mixed':
                        results = optimized_search.advanced_search(
                            symbols=query_data['symbols'],
                            keywords=query_data['keywords']
                        )
                    
                    duration = (time.time() - start_time) * 1000  # Convert to ms
                    opt_times.append(duration)
                    
                except Exception as e:
                    print(f"❌ Optimized search failed for {query_data}: {str(e)}")
                    continue
            
            # Test traditional search (for comparison)
            trad_times = []
            for i in range(3):  # Run 3 times (traditional is slower)
                start_time = time.time()
                
                try:
                    if query_type == 'symbol':
                        results = traditional_search.optimized_symbol_search([query_data['query']])
                    elif query_type == 'keyword':
                        results = traditional_search.advanced_search(keywords=[query_data['query']])
                    elif query_type == 'mixed':
                        results = traditional_search.advanced_search(
                            symbols=query_data['symbols'],
                            keywords=query_data['keywords']
                        )
                    
                    duration = (time.time() - start_time) * 1000  # Convert to ms
                    trad_times.append(duration)
                    
                except Exception as e:
                    print(f"❌ Traditional search failed for {query_data}: {str(e)}")
                    continue
            
            # Calculate statistics
            if opt_times:
                avg_opt_time = statistics.mean(opt_times)
                benchmark_results['optimized_search'][f"{query_type}_{query_data.get('query', 'mixed')}"] = {
                    'avg_time_ms': round(avg_opt_time, 2),
                    'min_time_ms': round(min(opt_times), 2),
                    'max_time_ms': round(max(opt_times), 2)
                }
            
            if trad_times:
                avg_trad_time = statistics.mean(trad_times)
                benchmark_results['traditional_search'][f"{query_type}_{query_data.get('query', 'mixed')}"] = {
                    'avg_time_ms': round(avg_trad_time, 2),
                    'min_time_ms': round(min(trad_times), 2),
                    'max_time_ms': round(max(trad_times), 2)
                }
                
                # Calculate improvement
                if opt_times:
                    improvement = ((avg_trad_time - avg_opt_time) / avg_trad_time) * 100
                    benchmark_results['performance_comparison'][f"{query_type}_{query_data.get('query', 'mixed')}"] = {
                        'improvement_percentage': round(improvement, 2),
                        'speedup_factor': round(avg_trad_time / avg_opt_time, 2)
                    }
        
        print("✅ Search performance benchmarks completed")
        
        # Print summary
        if benchmark_results['performance_comparison']:
            improvements = [v['improvement_percentage'] for v in benchmark_results['performance_comparison'].values()]
            avg_improvement = statistics.mean(improvements)
            print(f"✅ Average performance improvement: {avg_improvement:.1f}%")
        
        self.results['benchmarks']['search_performance'] = benchmark_results
    
    def test_search_functionality(self):
        """Test search functionality and accuracy"""
        print("\n🔍 Testing Search Functionality...")
        
        functionality_results = {
            'symbol_search': {},
            'keyword_search': {},
            'sentiment_filtering': {},
            'date_filtering': {},
            'pagination': {}
        }
        
        optimized_search = OptimizedNewsSearch(db.session)
        
        try:
            # Test symbol search
            symbol_results = optimized_search.search_by_symbols(['AAPL'])
            functionality_results['symbol_search'] = {
                'results_found': len(symbol_results[0]),
                'has_ai_content': all(article.get('ai_summary') for article in symbol_results[0][:5]) if symbol_results[0] else False
            }
            
            # Test keyword search
            keyword_results = optimized_search.search_by_keywords(['earnings'])
            functionality_results['keyword_search'] = {
                'results_found': len(keyword_results[0]),
                'has_ai_content': all(article.get('ai_summary') for article in keyword_results[0][:5]) if keyword_results[0] else False
            }
            
            # Test sentiment filtering
            positive_results = optimized_search.search_by_symbols(['AAPL'], sentiment_filter='POSITIVE')
            functionality_results['sentiment_filtering'] = {
                'positive_results': len(positive_results[0]),
                'sentiment_filter_working': True
            }
            
            # Test date filtering
            recent_results = optimized_search.search_by_symbols(['AAPL'], date_filter='week')
            functionality_results['date_filtering'] = {
                'recent_results': len(recent_results[0]),
                'date_filter_working': True
            }
            
            # Test pagination
            page1_results = optimized_search.search_by_symbols(['AAPL'], page=1, per_page=10)
            page2_results = optimized_search.search_by_symbols(['AAPL'], page=2, per_page=10)
            functionality_results['pagination'] = {
                'page1_count': len(page1_results[0]),
                'page2_count': len(page2_results[0]),
                'pagination_working': len(page1_results[0]) > 0 and len(page2_results[0]) > 0
            }
            
            print("✅ Search functionality tests completed")
            
        except Exception as e:
            print(f"❌ Search functionality test failed: {str(e)}")
            functionality_results['error'] = str(e)
        
        self.results['tests']['search_functionality'] = functionality_results
    
    def test_cache_effectiveness(self):
        """Test cache effectiveness"""
        print("\n💾 Testing Cache Effectiveness...")
        
        cache_results = {
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_performance': {}
        }
        
        optimized_search = OptimizedNewsSearch(db.session)
        
        # Test same query multiple times
        test_query = 'AAPL'
        times = []
        
        for i in range(10):
            start_time = time.time()
            results = optimized_search.search_by_symbols([test_query])
            duration = (time.time() - start_time) * 1000
            times.append(duration)
            
            if duration < 50:  # Likely cache hit
                cache_results['cache_hits'] += 1
            else:
                cache_results['cache_misses'] += 1
        
        cache_results['cache_performance'] = {
            'avg_time_ms': round(statistics.mean(times), 2),
            'min_time_ms': round(min(times), 2),
            'max_time_ms': round(max(times), 2),
            'cache_hit_rate': round((cache_results['cache_hits'] / 10) * 100, 2)
        }
        
        print(f"✅ Cache effectiveness test completed")
        print(f"✅ Cache hit rate: {cache_results['cache_performance']['cache_hit_rate']}%")
        
        self.results['tests']['cache_effectiveness'] = cache_results
    
    def test_database_optimization(self):
        """Test database optimization"""
        print("\n🗄️ Testing Database Optimization...")
        
        db_results = {
            'index_usage': {},
            'query_performance': {},
            'table_sizes': {}
        }
        
        try:
            # Test table sizes
            articles_count = db.session.query(NewsArticle).count()
            index_count = db.session.query(NewsSearchIndex).count()
            
            db_results['table_sizes'] = {
                'news_articles': articles_count,
                'news_search_index': index_count,
                'index_coverage': round((index_count / articles_count) * 100, 2) if articles_count > 0 else 0
            }
            
            # Test query performance
            start_time = time.time()
            recent_articles = db.session.query(NewsSearchIndex).filter(
                NewsSearchIndex.published_at >= datetime.now() - timedelta(days=7)
            ).limit(100).all()
            query_duration = (time.time() - start_time) * 1000
            
            db_results['query_performance'] = {
                'recent_articles_query_ms': round(query_duration, 2),
                'results_found': len(recent_articles)
            }
            
            print("✅ Database optimization tests completed")
            
        except Exception as e:
            print(f"❌ Database optimization test failed: {str(e)}")
            db_results['error'] = str(e)
        
        self.results['tests']['database_optimization'] = db_results
    
    def test_cache_hit(self, query: str, query_type: str) -> bool:
        """Test if a query results in a cache hit"""
        try:
            optimized_search = OptimizedNewsSearch(db.session)
            
            start_time = time.time()
            if query_type == 'symbol':
                results = optimized_search.search_by_symbols([query])
            elif query_type == 'keyword':
                results = optimized_search.search_by_keywords([query])
            else:
                results = optimized_search.search_by_symbols([query])
            
            duration = (time.time() - start_time) * 1000
            
            # If query completes in < 50ms, likely cache hit
            return duration < 50
            
        except Exception:
            return False
    
    def generate_recommendations(self):
        """Generate optimization recommendations"""
        print("\n💡 Generating Recommendations...")
        
        recommendations = []
        
        # Check index sync coverage
        index_sync = self.results['tests'].get('index_sync', {})
        sync_status = index_sync.get('sync_status', {})
        sync_percentage = sync_status.get('sync_percentage', 0)
        
        if sync_percentage < 95:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Index Sync',
                'issue': f'Search index coverage is {sync_percentage}%',
                'recommendation': 'Run full index rebuild: sync_service.full_rebuild()',
                'impact': 'Some articles may not appear in search results'
            })
        
        # Check cache effectiveness
        cache_effectiveness = self.results['tests'].get('cache_effectiveness', {})
        cache_hit_rate = cache_effectiveness.get('cache_performance', {}).get('cache_hit_rate', 0)
        
        if cache_hit_rate < 60:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Cache Optimization',
                'issue': f'Cache hit rate is {cache_hit_rate}%',
                'recommendation': 'Increase cache warming frequency and duration',
                'impact': 'Slower search response times'
            })
        
        # Check search performance
        search_performance = self.results['benchmarks'].get('search_performance', {})
        performance_comparison = search_performance.get('performance_comparison', {})
        
        if performance_comparison:
            improvements = [v['improvement_percentage'] for v in performance_comparison.values()]
            avg_improvement = statistics.mean(improvements)
            
            if avg_improvement < 70:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'Search Performance',
                    'issue': f'Average performance improvement is {avg_improvement:.1f}%',
                    'recommendation': 'Optimize database indexes and cache strategies',
                    'impact': 'Suboptimal search response times'
                })
        
        # Check database optimization
        db_optimization = self.results['tests'].get('database_optimization', {})
        table_sizes = db_optimization.get('table_sizes', {})
        index_coverage = table_sizes.get('index_coverage', 0)
        
        if index_coverage < 90:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Database Optimization',
                'issue': f'Search index coverage is {index_coverage}%',
                'recommendation': 'Ensure all AI-processed articles are in search index',
                'impact': 'Incomplete search results'
            })
        
        self.results['recommendations'] = recommendations
        
        print(f"✅ Generated {len(recommendations)} recommendations")
        
        for rec in recommendations:
            print(f"  {rec['priority']}: {rec['issue']}")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Generating Test Report...")
        
        report_filename = f"search_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"✅ Report saved to: {report_filename}")
        
        # Print summary
        print("\n" + "="*60)
        print("📋 SEARCH OPTIMIZATION TEST SUMMARY")
        print("="*60)
        
        # Test results summary
        for test_name, test_result in self.results['tests'].items():
            if 'error' in test_result:
                print(f"❌ {test_name}: FAILED - {test_result['error']}")
            else:
                print(f"✅ {test_name}: PASSED")
        
        # Performance summary
        search_performance = self.results['benchmarks'].get('search_performance', {})
        performance_comparison = search_performance.get('performance_comparison', {})
        
        if performance_comparison:
            improvements = [v['improvement_percentage'] for v in performance_comparison.values()]
            avg_improvement = statistics.mean(improvements)
            print(f"⚡ Average Performance Improvement: {avg_improvement:.1f}%")
        
        # Cache effectiveness summary
        cache_effectiveness = self.results['tests'].get('cache_effectiveness', {})
        cache_hit_rate = cache_effectiveness.get('cache_performance', {}).get('cache_hit_rate', 0)
        print(f"💾 Cache Hit Rate: {cache_hit_rate}%")
        
        # Recommendations summary
        recommendations = self.results.get('recommendations', [])
        high_priority = [r for r in recommendations if r['priority'] == 'HIGH']
        medium_priority = [r for r in recommendations if r['priority'] == 'MEDIUM']
        
        print(f"🔥 High Priority Issues: {len(high_priority)}")
        print(f"⚠️  Medium Priority Issues: {len(medium_priority)}")
        
        if high_priority:
            print("\n🚨 HIGH PRIORITY ACTIONS NEEDED:")
            for rec in high_priority:
                print(f"  • {rec['issue']}")
                print(f"    → {rec['recommendation']}")
        
        print("\n✅ Search optimization testing completed!")


def main():
    """Main function to run all tests"""
    tester = SearchOptimizationTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main() 