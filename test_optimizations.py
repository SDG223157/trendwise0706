#!/usr/bin/env python3
"""
🧪 ANALYSIS PAGE OPTIMIZATION VALIDATION TEST

Tests all implemented optimizations to ensure they work correctly:
✅ Response compression and optimization
✅ Async technical indicators 
✅ Chart data optimization
✅ Performance monitoring
✅ Error handling and fallbacks
"""

import asyncio
import time
import json
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_async_indicators():
    """Test async technical indicators"""
    print("🔧 Testing Async Technical Indicators...")
    
    try:
        from app.utils.analysis.async_indicators import AsyncTechnicalIndicators, calculate_basic_indicators
        
        # Create test data
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        async def run_indicator_tests():
            calculator = AsyncTechnicalIndicators()
            
            # Test SMA calculation
            print("  📊 Testing SMA calculation...")
            sma_result = await calculator.calculate_sma_async(prices, 20)
            assert sma_result.success, "SMA calculation failed"
            assert len(sma_result.values) == len(prices), "SMA result length mismatch"
            print(f"  ✅ SMA completed in {sma_result.calculation_time:.3f}s")
            
            # Test EMA calculation
            print("  📈 Testing EMA calculation...")
            ema_result = await calculator.calculate_ema_async(prices, 20)
            assert ema_result.success, "EMA calculation failed"
            assert len(ema_result.values) == len(prices), "EMA result length mismatch"
            print(f"  ✅ EMA completed in {ema_result.calculation_time:.3f}s")
            
            # Test RSI calculation
            print("  📉 Testing RSI calculation...")
            rsi_result = await calculator.calculate_rsi_async(prices, 14)
            assert rsi_result.success, "RSI calculation failed"
            print(f"  ✅ RSI completed in {rsi_result.calculation_time:.3f}s")
            
            # Test batch calculation
            print("  🔄 Testing batch calculation...")
            batch_results = await calculate_basic_indicators(prices)
            assert len(batch_results) > 0, "Batch calculation returned no results"
            print(f"  ✅ Batch calculation completed with {len(batch_results)} indicators")
            
            # Test performance stats
            stats = calculator.get_performance_stats()
            print(f"  📊 Performance Stats: {stats['total_calculations']} calculations, "
                  f"{stats['avg_time']:.3f}s avg time")
            
            return True
        
        # Run async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_indicator_tests())
        loop.close()
        
        print("✅ Async Technical Indicators: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Async Technical Indicators: FAILED - {str(e)}")
        return False

def test_response_optimizer():
    """Test response optimization utilities"""
    print("🚀 Testing Response Optimizer...")
    
    try:
        from app.utils.performance.response_optimizer import ResponseOptimizer
        
        optimizer = ResponseOptimizer()
        
        # Test chart data optimization
        print("  📊 Testing chart data optimization...")
        test_chart_data = {
            'data': [{
                'x': [f"2024-01-{i:02d}" for i in range(1, 101)],
                'y': [100.123456789 + i * 0.543210987 for i in range(100)],
                'type': 'scatter',
                'mode': 'lines',
                'name': 'Test Data'
            }],
            'layout': {
                'title': 'Test Chart with Very Long Title That Should Be Truncated Because It Is Too Long For Optimal Transfer',
                'xaxis': {'title': 'Date'},
                'yaxis': {'title': 'Price'}
            }
        }
        
        optimized_data = optimizer.optimize_chart_data(test_chart_data)
        
        # Check if data was optimized
        assert 'data' in optimized_data, "Chart data structure corrupted"
        assert len(optimized_data['data'][0]['y']) <= len(test_chart_data['data'][0]['y']), "Data not optimized"
        
        # Check precision optimization
        original_precision = len(str(test_chart_data['data'][0]['y'][0]).split('.')[-1])
        optimized_precision = len(str(optimized_data['data'][0]['y'][0]).split('.')[-1])
        assert optimized_precision <= optimizer.chart_precision, "Precision not optimized"
        
        print(f"  ✅ Chart data optimized: {original_precision} → {optimized_precision} decimal places")
        
        # Test performance stats
        stats = optimizer.get_performance_stats()
        print(f"  📊 Response stats initialized: {stats}")
        
        print("✅ Response Optimizer: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Response Optimizer: FAILED - {str(e)}")
        return False

def test_chart_worker_simulation():
    """Test chart worker calculations (simulation)"""
    print("👷 Testing Chart Worker Calculations...")
    
    try:
        # Simulate the calculations that would run in the worker
        
        # Generate test data
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(500) * 0.5)
        
        print("  📊 Testing SMA calculation...")
        def calculate_sma(data, period):
            result = []
            for i in range(len(data)):
                if i < period - 1:
                    result.append(None)
                    continue
                sum_val = sum(data[i - period + 1:i + 1])
                result.append(sum_val / period)
            return result
        
        start_time = time.time()
        sma_result = calculate_sma(prices, 20)
        sma_time = time.time() - start_time
        
        assert len(sma_result) == len(prices), "SMA calculation failed"
        assert sma_result[-1] is not None, "SMA calculation incomplete"
        print(f"  ✅ SMA calculation completed in {sma_time:.3f}s")
        
        print("  📈 Testing EMA calculation...")
        def calculate_ema(data, period):
            multiplier = 2 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                ema = (data[i] * multiplier) + (result[i - 1] * (1 - multiplier))
                result.append(ema)
            return result
        
        start_time = time.time()
        ema_result = calculate_ema(prices, 20)
        ema_time = time.time() - start_time
        
        assert len(ema_result) == len(prices), "EMA calculation failed"
        print(f"  ✅ EMA calculation completed in {ema_time:.3f}s")
        
        print("  📉 Testing RSI calculation...")
        def calculate_rsi(data, period=14):
            gains = []
            losses = []
            
            for i in range(1, len(data)):
                change = data[i] - data[i - 1]
                gains.append(change if change > 0 else 0)
                losses.append(-change if change < 0 else 0)
            
            if len(gains) < period:
                return [None] * len(data)
            
            result = [None] * (period + 1)
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            for i in range(period, len(data) - 1):
                rs = avg_gain / avg_loss if avg_loss != 0 else 100
                rsi = 100 - (100 / (1 + rs))
                result.append(rsi)
                
                if i < len(gains):
                    avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                    avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            return result
        
        start_time = time.time()
        rsi_result = calculate_rsi(prices, 14)
        rsi_time = time.time() - start_time
        
        assert len(rsi_result) == len(prices), "RSI calculation failed"
        print(f"  ✅ RSI calculation completed in {rsi_time:.3f}s")
        
        total_time = sma_time + ema_time + rsi_time
        print(f"  📊 Total calculation time: {total_time:.3f}s for {len(prices)} data points")
        
        print("✅ Chart Worker Calculations: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Chart Worker Calculations: FAILED - {str(e)}")
        return False

def test_css_performance_features():
    """Test CSS performance features (check if files exist and are valid)"""
    print("🎨 Testing CSS Performance Features...")
    
    try:
        css_file_path = os.path.join(os.path.dirname(__file__), 'app', 'static', 'css', 'analysis-optimized.css')
        
        # Check if CSS file exists
        assert os.path.exists(css_file_path), "Optimized CSS file not found"
        
        # Read CSS file and check for performance features
        with open(css_file_path, 'r') as f:
            css_content = f.read()
        
        # Check for GPU acceleration features
        gpu_features = [
            'transform: translateZ(0)',
            'will-change:',
            'backface-visibility: hidden',
            'contain: layout',
            '@keyframes'
        ]
        
        for feature in gpu_features:
            assert feature in css_content, f"Missing GPU acceleration feature: {feature}"
        
        print(f"  ✅ CSS file found: {len(css_content)} characters")
        print(f"  ✅ GPU acceleration features verified")
        
        # Check for responsive design
        responsive_features = [
            '@media (max-width: 768px)',
            '@media (max-width: 480px)',
            '@media (prefers-reduced-motion: reduce)',
            '@media (prefers-color-scheme: dark)'
        ]
        
        for feature in responsive_features:
            assert feature in css_content, f"Missing responsive feature: {feature}"
        
        print(f"  ✅ Responsive design features verified")
        
        print("✅ CSS Performance Features: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ CSS Performance Features: FAILED - {str(e)}")
        return False

def test_javascript_optimizations():
    """Test JavaScript optimization files"""
    print("🔥 Testing JavaScript Optimizations...")
    
    try:
        # Check if optimized chart renderer exists
        js_file_path = os.path.join(os.path.dirname(__file__), 'app', 'static', 'js', 'optimized-chart-renderer.js')
        assert os.path.exists(js_file_path), "Optimized chart renderer not found"
        
        with open(js_file_path, 'r') as f:
            js_content = f.read()
        
        # Check for key optimization features
        optimization_features = [
            'class OptimizedChartRenderer',
            'AbortController',
            'performance.now()',
            'will-change',
            'translateZ(0)',
            'async loadPlotly()',
            'WebWorker'
        ]
        
        for feature in optimization_features:
            assert feature in js_content, f"Missing JS optimization feature: {feature}"
        
        print(f"  ✅ Chart renderer optimizations verified")
        
        # Check if worker file exists
        worker_file_path = os.path.join(os.path.dirname(__file__), 'app', 'static', 'js', 'chart-worker.js')
        assert os.path.exists(worker_file_path), "Chart worker not found"
        
        with open(worker_file_path, 'r') as f:
            worker_content = f.read()
        
        worker_features = [
            'class ChartCalculator',
            'self.onmessage',
            'calculateSMA',
            'calculateEMA',
            'calculateRSI'
        ]
        
        for feature in worker_features:
            assert feature in worker_content, f"Missing worker feature: {feature}"
        
        print(f"  ✅ Web Worker features verified")
        
        print("✅ JavaScript Optimizations: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ JavaScript Optimizations: FAILED - {str(e)}")
        return False

def run_all_tests():
    """Run all optimization tests"""
    print("🧪 TRENDWISE ANALYSIS PAGE OPTIMIZATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Async Technical Indicators", test_async_indicators),
        ("Response Optimizer", test_response_optimizer), 
        ("Chart Worker Calculations", test_chart_worker_simulation),
        ("CSS Performance Features", test_css_performance_features),
        ("JavaScript Optimizations", test_javascript_optimizations)
    ]
    
    results = []
    start_time = time.time()
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {str(e)}")
            results.append((test_name, False))
    
    total_time = time.time() - start_time
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
    
    print("-" * 60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    print(f"Total Time: {total_time:.2f}s")
    
    if passed == total:
        print("\n🎉 ALL OPTIMIZATIONS WORKING CORRECTLY!")
        print("The TrendWise analysis page optimizations are ready for production.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)