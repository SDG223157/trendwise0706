/**
 * 🚀 OPTIMIZED CHART RENDERER FOR TRENDWISE ANALYSIS
 * 
 * Performance Features:
 * ✅ Dynamic Plotly loading (saves 3MB on initial load)
 * ✅ Request cancellation with AbortController
 * ✅ Performance monitoring and metrics
 * ✅ Memory management and cleanup
 * ✅ Graceful error handling and recovery
 * ✅ Progressive chart rendering
 */

class OptimizedChartRenderer {
    constructor(ticker, lookbackDays, endDate) {
        this.ticker = ticker;
        this.lookbackDays = lookbackDays;
        this.endDate = endDate;
        this.currentPhase = 'initial';
        
        // Request management
        this.activeRequests = new Map();
        this.abortController = new AbortController();
        
        // Performance tracking
        this.performanceMetrics = {
            startTime: performance.now(),
            phaseTimings: {},
            memoryUsage: {},
            errors: []
        };
        
        // Chart instances
        this.chartInstances = new Map();
        this.plotlyLoaded = false;
        this.plotlyPromise = null;
        
        // Feature detection
        this.supportsWebGL = this.detectWebGLSupport();
        this.supportsWorkers = typeof Worker !== 'undefined';
        
        // GPU acceleration settings
        this.gpuAccelerated = true;
        this.willChange = 'transform, opacity';
        
        // Initialize worker if available
        this.chartWorker = null;
        if (this.supportsWorkers) {
            this.initializeWorker();
        }
        
        console.log('🚀 OptimizedChartRenderer initialized', {
            ticker: this.ticker,
            webgl: this.supportsWebGL,
            workers: this.supportsWorkers
        });
    }
    
    /**
     * Dynamic Plotly loading - only load when needed
     */
    async loadPlotly() {
        if (this.plotlyLoaded) {
            return window.Plotly;
        }
        
        if (this.plotlyPromise) {
            return this.plotlyPromise;
        }
        
        const loadStart = performance.now();
        console.log('📦 Loading Plotly.js dynamically...');
        
        this.plotlyPromise = new Promise((resolve, reject) => {
            // Check if Plotly is already loaded
            if (window.Plotly) {
                this.plotlyLoaded = true;
                resolve(window.Plotly);
                return;
            }
            
            // Create script element
            const script = document.createElement('script');
            script.src = 'https://cdn.plot.ly/plotly-2.26.0.min.js';
            script.async = true;
            
            script.onload = () => {
                this.plotlyLoaded = true;
                const loadTime = performance.now() - loadStart;
                console.log(`✅ Plotly.js loaded in ${loadTime.toFixed(1)}ms`);
                this.trackMetric('plotly_load_time', loadTime);
                resolve(window.Plotly);
            };
            
            script.onerror = () => {
                const error = new Error('Failed to load Plotly.js');
                this.trackError('plotly_load_failed', error);
                reject(error);
            };
            
            document.head.appendChild(script);
        });
        
        return this.plotlyPromise;
    }
    
    /**
     * Initialize Web Worker for calculations
     */
    initializeWorker() {
        try {
            this.chartWorker = new Worker('/static/js/chart-worker.js');
            
            this.chartWorker.onmessage = (e) => {
                const { taskId, success, result, error } = e.data;
                const taskResolver = this.activeRequests.get(`worker_${taskId}`);
                
                if (taskResolver) {
                    if (success) {
                        taskResolver.resolve(result);
                    } else {
                        taskResolver.reject(new Error(error));
                    }
                    this.activeRequests.delete(`worker_${taskId}`);
                }
            };
            
            this.chartWorker.onerror = (error) => {
                console.error('📊 Chart worker error:', error);
                this.trackError('worker_error', error);
            };
            
            console.log('👷 Chart worker initialized');
        } catch (error) {
            console.warn('⚠️ Chart worker not available:', error.message);
            this.chartWorker = null;
        }
    }
    
    /**
     * Enhanced request with cancellation and performance tracking
     */
    async makeRequest(url, data, requestId) {
        // Cancel previous request if exists
        if (this.activeRequests.has(requestId)) {
            const existing = this.activeRequests.get(requestId);
            if (existing.controller) {
                existing.controller.abort();
            }
        }
        
        const controller = new AbortController();
        const startTime = performance.now();
        
        const requestPromise = new Promise(async (resolve, reject) => {
            try {
                console.log(`🌐 Making request: ${requestId}`);
                
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Request-ID': requestId,
                        'Accept': 'application/json',
                        'Accept-Encoding': 'gzip, deflate'
                    },
                    body: JSON.stringify(data),
                    signal: controller.signal
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                // Track performance metrics
                const responseTime = performance.now() - startTime;
                this.trackMetric(`${requestId}_response_time`, responseTime);
                this.trackMemoryUsage(requestId);
                
                console.log(`✅ Request completed: ${requestId} (${responseTime.toFixed(1)}ms)`);
                resolve(result);
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    console.log(`🚫 Request cancelled: ${requestId}`);
                    resolve(null);
                } else {
                    console.error(`❌ Request failed: ${requestId}`, error);
                    this.trackError(requestId, error);
                    reject(error);
                }
            }
        });
        
        this.activeRequests.set(requestId, { 
            promise: requestPromise, 
            controller,
            startTime 
        });
        
        return requestPromise;
    }
    
    /**
     * Calculate technical indicators using worker or fallback
     */
    async calculateIndicator(type, data, options = {}) {
        if (!this.chartWorker) {
            // Fallback to synchronous calculation
            return this.calculateIndicatorSync(type, data, options);
        }
        
        const taskId = Math.random().toString(36).substr(2, 9);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Worker calculation timeout'));
            }, 5000);
            
            this.activeRequests.set(`worker_${taskId}`, { 
                resolve: (result) => {
                    clearTimeout(timeout);
                    resolve(result);
                },
                reject: (error) => {
                    clearTimeout(timeout);
                    reject(error);
                }
            });
            
            this.chartWorker.postMessage({
                taskId,
                type,
                data,
                options
            });
        });
    }
    
    /**
     * Fallback synchronous calculations
     */
    calculateIndicatorSync(type, data, options = {}) {
        switch (type) {
            case 'sma':
                return this.calculateSMA(data, options.period || 20);
            case 'ema':
                return this.calculateEMA(data, options.period || 20);
            case 'rsi':
                return this.calculateRSI(data, options.period || 14);
            default:
                throw new Error(`Unknown indicator type: ${type}`);
        }
    }
    
    calculateSMA(data, period) {
        const result = [];
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
                continue;
            }
            const sum = data.slice(i - period + 1, i + 1).reduce((acc, val) => acc + val, 0);
            result.push(sum / period);
        }
        return result;
    }
    
    calculateEMA(data, period) {
        const multiplier = 2 / (period + 1);
        const result = [data[0]];
        
        for (let i = 1; i < data.length; i++) {
            const ema = (data[i] * multiplier) + (result[i - 1] * (1 - multiplier));
            result.push(ema);
        }
        return result;
    }
    
    calculateRSI(data, period = 14) {
        const gains = [];
        const losses = [];
        
        for (let i = 1; i < data.length; i++) {
            const change = data[i] - data[i - 1];
            gains.push(change > 0 ? change : 0);
            losses.push(change < 0 ? -change : 0);
        }
        
        const result = new Array(period).fill(null);
        
        if (gains.length < period) return result;
        
        let avgGain = gains.slice(0, period).reduce((a, b) => a + b) / period;
        let avgLoss = losses.slice(0, period).reduce((a, b) => a + b) / period;
        
        for (let i = period; i < data.length - 1; i++) {
            const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
            const rsi = 100 - (100 / (1 + rs));
            result.push(rsi);
            
            // Update averages
            avgGain = (avgGain * (period - 1) + gains[i]) / period;
            avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
        }
        
        return result;
    }
    
    /**
     * Optimized chart rendering with WebGL support
     */
    async renderChart(elementId, chartData, chartType = 'basic') {
        try {
            await this.loadPlotly();
            
            const renderStart = performance.now();
            console.log(`📊 Rendering ${chartType} chart in #${elementId}`);
            
            // Optimize chart configuration
            const config = {
                responsive: true,
                displayModeBar: chartType !== 'basic',
                scrollZoom: chartType === 'full',
                staticPlot: false,
                toImageButtonOptions: {
                    format: 'png',
                    filename: `${this.ticker}_${chartType}_chart`,
                    height: 600,
                    width: 1000,
                    scale: 1
                }
            };
            
            // Enable WebGL for large datasets
            if (this.supportsWebGL && chartData.data && chartData.data[0]?.y?.length > 1000) {
                config.plotGlPixelRatio = 2;
                console.log('🔥 Using WebGL acceleration for large dataset');
            }
            
            // GPU acceleration hints
            if (this.gpuAccelerated) {
                // Add GPU acceleration CSS
                const element = document.getElementById(elementId);
                if (element) {
                    element.style.transform = 'translateZ(0)';
                    element.style.willChange = this.willChange;
                    element.style.backfaceVisibility = 'hidden';
                }
            }
            
            // Optimize layout for performance
            const optimizedLayout = {
                ...chartData.layout,
                font: { size: 12, family: 'Arial, sans-serif' },
                margin: { t: 40, r: 30, b: 40, l: 60 },
                hovermode: 'x unified',
                showlegend: chartData.data?.length > 1
            };
            
            // Create or update chart
            const element = document.getElementById(elementId);
            if (!element) {
                throw new Error(`Chart element #${elementId} not found`);
            }
            
            let chartInstance;
            if (this.chartInstances.has(elementId)) {
                // Update existing chart
                chartInstance = this.chartInstances.get(elementId);
                await window.Plotly.react(element, chartData.data, optimizedLayout, config);
            } else {
                // Create new chart
                chartInstance = await window.Plotly.newPlot(element, chartData.data, optimizedLayout, config);
                this.chartInstances.set(elementId, chartInstance);
            }
            
            const renderTime = performance.now() - renderStart;
            this.trackMetric(`${chartType}_render_time`, renderTime);
            
            console.log(`✅ Chart rendered in ${renderTime.toFixed(1)}ms`);
            return chartInstance;
            
        } catch (error) {
            console.error(`❌ Chart rendering failed:`, error);
            this.trackError(`${chartType}_render_failed`, error);
            this.showChartError(elementId, error.message);
            throw error;
        }
    }
    
    /**
     * Show error state in chart container
     */
    showChartError(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="chart-error" style="
                    padding: 40px;
                    text-align: center;
                    color: #dc3545;
                    border: 2px dashed #dc3545;
                    border-radius: 8px;
                    margin: 20px 0;
                ">
                    <h3 style="margin: 0 0 10px 0;">Chart Loading Failed</h3>
                    <p style="margin: 0; color: #6c757d;">${message}</p>
                    <button onclick="location.reload()" style="
                        margin-top: 15px;
                        padding: 8px 16px;
                        background: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    ">Try Again</button>
                </div>
            `;
        }
    }
    
    /**
     * Performance monitoring utilities
     */
    trackMetric(name, value) {
        this.performanceMetrics.phaseTimings[name] = value;
        
        // Send to analytics if available
        if (window.gtag) {
            window.gtag('event', 'performance_metric', {
                metric_name: name,
                metric_value: Math.round(value),
                ticker: this.ticker,
                lookback_days: this.lookbackDays
            });
        }
    }
    
    trackMemoryUsage(context) {
        if (performance.memory) {
            this.performanceMetrics.memoryUsage[context] = {
                used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
                total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
                timestamp: Date.now()
            };
        }
    }
    
    trackError(context, error) {
        this.performanceMetrics.errors.push({
            context,
            message: error.message,
            stack: error.stack,
            timestamp: Date.now()
        });
        
        // Send to error tracking if available
        if (window.gtag) {
            window.gtag('event', 'exception', {
                description: `${context}: ${error.message}`,
                fatal: false
            });
        }
    }
    
    /**
     * Feature detection
     */
    detectWebGLSupport() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            return !!gl;
        } catch (e) {
            return false;
        }
    }
    
    /**
     * Get performance report
     */
    getPerformanceReport() {
        const totalTime = performance.now() - this.performanceMetrics.startTime;
        
        return {
            total_time: totalTime,
            phase_timings: this.performanceMetrics.phaseTimings,
            memory_usage: this.performanceMetrics.memoryUsage,
            errors: this.performanceMetrics.errors,
            features: {
                webgl: this.supportsWebGL,
                workers: this.supportsWorkers,
                plotly_loaded: this.plotlyLoaded
            }
        };
    }
    
    /**
     * Cleanup and destroy
     */
    destroy() {
        console.log('🧹 Cleaning up OptimizedChartRenderer');
        
        // Cancel all active requests
        this.abortController.abort();
        this.activeRequests.forEach((request, id) => {
            if (request.controller) {
                request.controller.abort();
            }
        });
        this.activeRequests.clear();
        
        // Destroy chart instances
        this.chartInstances.forEach((instance, elementId) => {
            try {
                const element = document.getElementById(elementId);
                if (element && window.Plotly) {
                    window.Plotly.purge(element);
                }
            } catch (error) {
                console.warn(`Failed to purge chart ${elementId}:`, error);
            }
        });
        this.chartInstances.clear();
        
        // Terminate worker
        if (this.chartWorker) {
            this.chartWorker.terminate();
            this.chartWorker = null;
        }
        
        // Log final performance report
        const report = this.getPerformanceReport();
        console.log('📊 Final Performance Report:', report);
    }
}

// Enhanced Progressive Analysis Renderer using optimized chart renderer
class EnhancedProgressiveAnalysisRenderer extends OptimizedChartRenderer {
    constructor(ticker, lookbackDays, endDate) {
        super(ticker, lookbackDays, endDate);
        this.analysisData = null;
    }
    
    async startAnalysis() {
        try {
            console.log('🚀 Starting enhanced progressive analysis');
            
            // Phase 1: Check for cached summary
            await this.checkCachedSummary();
            
            // Phase 2: Load basic chart
            await this.loadBasicChart();
            
            // Phase 3: Load enhanced chart with indicators
            await this.loadEnhancedChart();
            
            // Phase 4: Load complete analysis
            await this.loadFullAnalysis();
            
            console.log('✅ Progressive analysis completed');
            
        } catch (error) {
            console.error('❌ Progressive analysis failed:', error);
            this.showError(error.message);
        }
    }
    
    async checkCachedSummary() {
        this.setLoadingPhase('initial');
        
        try {
            const summary = await this.makeRequest('/api/analysis-summary', {
                ticker: this.ticker,
                lookback_days: this.lookbackDays,
                end_date: this.endDate
            }, 'summary_check');
            
            if (summary && summary.cached) {
                this.showSummary(summary);
            }
        } catch (error) {
            console.log('No cached summary available');
        }
    }
    
    async loadBasicChart() {
        this.setLoadingPhase('data');
        this.updateProgress(20, 'Loading price data...');
        
        try {
            const chartData = await this.makeRequest('/api/basic-chart', {
                ticker: this.ticker,
                lookback_days: this.lookbackDays,
                end_date: this.endDate
            }, 'basic_chart');
            
            if (chartData) {
                await this.renderChart('basic-chart-plot', chartData, 'basic');
                this.showChart();
                this.updateProgress(40, 'Basic chart ready');
            }
        } catch (error) {
            throw new Error('Failed to load basic chart: ' + error.message);
        }
    }
    
    async loadEnhancedChart() {
        this.updateProgress(60, 'Adding technical indicators...');
        
        try {
            const chartData = await this.makeRequest('/api/enhanced-chart', {
                ticker: this.ticker,
                lookback_days: this.lookbackDays,
                end_date: this.endDate
            }, 'enhanced_chart');
            
            if (chartData) {
                // Calculate additional indicators using worker
                const priceData = chartData.data[0]?.y;
                if (priceData && priceData.length > 0) {
                    try {
                        const [rsi, ema20] = await Promise.all([
                            this.calculateIndicator('rsi', priceData, { period: 14 }),
                            this.calculateIndicator('ema', priceData, { period: 20 })
                        ]);
                        
                        // Add RSI subplot if calculated successfully
                        if (rsi && rsi.some(val => val !== null)) {
                            this.addRSISubplot(chartData, rsi);
                        }
                        
                        // Add EMA line if calculated successfully
                        if (ema20 && ema20.some(val => val !== null)) {
                            this.addEMATrace(chartData, ema20);
                        }
                    } catch (indicatorError) {
                        console.warn('Failed to calculate additional indicators:', indicatorError);
                    }
                }
                
                await this.renderChart('enhanced-chart-plot', chartData, 'enhanced');
                this.showEnhancedChart();
                this.updateProgress(80, 'Technical analysis ready');
            }
        } catch (error) {
            console.log('Enhanced chart failed, continuing with basic chart');
        }
    }
    
    async loadFullAnalysis() {
        this.setLoadingPhase('chart');
        
        try {
            const analysisData = await this.makeRequest('/api/full-analysis', {
                ticker: this.ticker,
                lookback_days: this.lookbackDays,
                end_date: this.endDate
            }, 'full_analysis');
            
            if (analysisData) {
                await this.renderChart('full-analysis-plot', analysisData, 'full');
                this.showFullAnalysis();
                this.hideLoading();
            }
        } catch (error) {
            console.log('Full analysis failed, keeping enhanced chart');
            this.hideLoading();
        }
    }
    
    addRSISubplot(chartData, rsiData) {
        // Add RSI trace
        chartData.data.push({
            x: chartData.data[0].x,
            y: rsiData,
            type: 'scatter',
            mode: 'lines',
            name: 'RSI',
            line: { color: '#9467bd', width: 1 },
            yaxis: 'y2'
        });
        
        // Update layout for subplot
        chartData.layout.yaxis2 = {
            title: 'RSI',
            side: 'right',
            overlaying: 'y',
            range: [0, 100]
        };
        
        // Add RSI reference lines
        chartData.data.push({
            x: chartData.data[0].x,
            y: new Array(chartData.data[0].x.length).fill(70),
            type: 'scatter',
            mode: 'lines',
            name: 'Overbought',
            line: { color: 'red', width: 1, dash: 'dash' },
            yaxis: 'y2',
            showlegend: false
        });
        
        chartData.data.push({
            x: chartData.data[0].x,
            y: new Array(chartData.data[0].x.length).fill(30),
            type: 'scatter',
            mode: 'lines',
            name: 'Oversold',
            line: { color: 'green', width: 1, dash: 'dash' },
            yaxis: 'y2',
            showlegend: false
        });
    }
    
    addEMATrace(chartData, emaData) {
        chartData.data.push({
            x: chartData.data[0].x,
            y: emaData,
            type: 'scatter',
            mode: 'lines',
            name: 'EMA 20',
            line: { color: '#17becf', width: 1 }
        });
    }
    
    // UI methods (same as original but with enhanced error handling)
    setLoadingPhase(phase) {
        document.querySelectorAll('.loading-phase').forEach(el => {
            el.classList.remove('active');
        });
        
        const currentPhaseEl = document.getElementById(phase + '-loading');
        if (currentPhaseEl) {
            currentPhaseEl.classList.add('active');
        }
        
        this.currentPhase = phase;
    }
    
    updateProgress(percentage, status) {
        const progressBar = document.getElementById('data-progress');
        const statusText = document.getElementById('data-status');
        
        if (progressBar) {
            progressBar.style.transform = `scaleX(${percentage / 100})`;
        }
        
        if (statusText) {
            statusText.textContent = status;
        }
    }
    
    showSummary(summary) {
        const summaryContainer = document.getElementById('analysis-summary');
        const summaryContent = document.getElementById('summary-content');
        
        if (summaryContent) {
            summaryContent.innerHTML = `
                <div class="summary-item">
                    <strong>Score:</strong> ${summary.score || 'N/A'}
                </div>
                <div class="summary-item">
                    <strong>Trend:</strong> ${summary.trend || 'N/A'}
                </div>
                <div class="summary-item">
                    <strong>Period:</strong> ${summary.period || 'N/A'}
                </div>
                <div class="summary-item">
                    <strong>Cached:</strong> <span class="cache-badge">✓ Fast Load</span>
                </div>
            `;
        }
        
        if (summaryContainer) {
            summaryContainer.style.display = 'block';
        }
    }
    
    showChart() {
        document.getElementById('chart-container').style.display = 'block';
        document.getElementById('basic-chart').style.display = 'block';
    }
    
    showEnhancedChart() {
        document.getElementById('enhanced-chart').style.display = 'block';
    }
    
    showFullAnalysis() {
        document.getElementById('full-analysis').style.display = 'block';
    }
    
    hideLoading() {
        document.getElementById('loading-states').style.display = 'none';
    }
    
    showError(message) {
        const container = document.getElementById('progressive-analysis-container');
        if (container) {
            container.innerHTML = `
                <div class="error-container" style="
                    text-align: center;
                    padding: 40px;
                    border: 2px solid #dc3545;
                    border-radius: 8px;
                    background: #f8d7da;
                    color: #721c24;
                ">
                    <h3>Analysis Failed</h3>
                    <p>${message}</p>
                    <button onclick="location.reload()" style="
                        padding: 10px 20px;
                        background: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-top: 15px;
                    ">Try Again</button>
                </div>
            `;
        }
    }
}

// Global exports
window.OptimizedChartRenderer = OptimizedChartRenderer;
window.EnhancedProgressiveAnalysisRenderer = EnhancedProgressiveAnalysisRenderer;

console.log('🚀 Optimized Chart Renderer loaded successfully');