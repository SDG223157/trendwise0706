/**
 * 🔥 CHART CALCULATION WEB WORKER
 * 
 * High-performance technical indicator calculations running in background thread.
 * Prevents UI blocking for CPU-intensive operations.
 * 
 * Supported Indicators:
 * ✅ Simple Moving Average (SMA)
 * ✅ Exponential Moving Average (EMA)
 * ✅ Relative Strength Index (RSI)
 * ✅ Bollinger Bands
 * ✅ MACD (Moving Average Convergence Divergence)
 * ✅ Stochastic Oscillator
 */

class ChartCalculator {
    constructor() {
        this.calculators = {
            sma: this.calculateSMA.bind(this),
            ema: this.calculateEMA.bind(this),
            rsi: this.calculateRSI.bind(this),
            bollinger: this.calculateBollingerBands.bind(this),
            macd: this.calculateMACD.bind(this),
            stochastic: this.calculateStochastic.bind(this),
            atr: this.calculateATR.bind(this),
            obv: this.calculateOBV.bind(this)
        };
        
        console.log('📊 Chart Calculator initialized with indicators:', Object.keys(this.calculators));
    }
    
    /**
     * Simple Moving Average
     */
    calculateSMA(data, period = 20) {
        if (!Array.isArray(data) || data.length === 0) {
            throw new Error('Invalid data array for SMA calculation');
        }
        
        if (period <= 0 || period > data.length) {
            throw new Error(`Invalid period ${period} for SMA calculation`);
        }
        
        const result = [];
        
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
                continue;
            }
            
            const sum = data.slice(i - period + 1, i + 1)
                           .reduce((acc, val) => acc + (val || 0), 0);
            result.push(sum / period);
        }
        
        return result;
    }
    
    /**
     * Exponential Moving Average
     */
    calculateEMA(data, period = 20) {
        if (!Array.isArray(data) || data.length === 0) {
            throw new Error('Invalid data array for EMA calculation');
        }
        
        const multiplier = 2 / (period + 1);
        const result = [];
        
        // First value is just the price
        result[0] = data[0];
        
        for (let i = 1; i < data.length; i++) {
            if (data[i] == null || result[i - 1] == null) {
                result.push(null);
                continue;
            }
            
            const ema = (data[i] * multiplier) + (result[i - 1] * (1 - multiplier));
            result.push(ema);
        }
        
        return result;
    }
    
    /**
     * Relative Strength Index
     */
    calculateRSI(data, period = 14) {
        if (!Array.isArray(data) || data.length < period + 1) {
            throw new Error('Insufficient data for RSI calculation');
        }
        
        const gains = [];
        const losses = [];
        
        // Calculate price changes
        for (let i = 1; i < data.length; i++) {
            const change = data[i] - data[i - 1];
            gains.push(change > 0 ? change : 0);
            losses.push(change < 0 ? -change : 0);
        }
        
        if (gains.length < period) {
            return new Array(data.length).fill(null);
        }
        
        const result = new Array(period).fill(null);
        
        // Calculate initial average gain and loss
        let avgGain = gains.slice(0, period).reduce((a, b) => a + b) / period;
        let avgLoss = losses.slice(0, period).reduce((a, b) => a + b) / period;
        
        // Calculate RSI for each subsequent period
        for (let i = period; i < data.length; i++) {
            if (avgLoss === 0) {
                result.push(100);
            } else {
                const rs = avgGain / avgLoss;
                const rsi = 100 - (100 / (1 + rs));
                result.push(rsi);
            }
            
            // Update averages using smoothing
            if (i < gains.length) {
                avgGain = (avgGain * (period - 1) + gains[i]) / period;
                avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
            }
        }
        
        return result;
    }
    
    /**
     * Bollinger Bands
     */
    calculateBollingerBands(data, period = 20, stdDev = 2) {
        const sma = this.calculateSMA(data, period);
        const upper = [];
        const lower = [];
        const middle = sma;
        
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                upper.push(null);
                lower.push(null);
                continue;
            }
            
            // Calculate standard deviation for the period
            const slice = data.slice(i - period + 1, i + 1);
            const mean = sma[i];
            const variance = slice.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / period;
            const standardDeviation = Math.sqrt(variance);
            
            upper.push(mean + (standardDeviation * stdDev));
            lower.push(mean - (standardDeviation * stdDev));
        }
        
        return {
            upper,
            middle,
            lower
        };
    }
    
    /**
     * MACD (Moving Average Convergence Divergence)
     */
    calculateMACD(data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
        const fastEMA = this.calculateEMA(data, fastPeriod);
        const slowEMA = this.calculateEMA(data, slowPeriod);
        
        // Calculate MACD line
        const macdLine = [];
        for (let i = 0; i < data.length; i++) {
            if (fastEMA[i] == null || slowEMA[i] == null) {
                macdLine.push(null);
            } else {
                macdLine.push(fastEMA[i] - slowEMA[i]);
            }
        }
        
        // Calculate signal line (EMA of MACD)
        const signalLine = this.calculateEMA(macdLine.filter(v => v !== null), signalPeriod);
        
        // Pad signal line to match original data length
        const paddedSignalLine = new Array(macdLine.length).fill(null);
        let signalIndex = 0;
        for (let i = 0; i < macdLine.length; i++) {
            if (macdLine[i] !== null && signalIndex < signalLine.length) {
                paddedSignalLine[i] = signalLine[signalIndex];
                signalIndex++;
            }
        }
        
        // Calculate histogram
        const histogram = [];
        for (let i = 0; i < data.length; i++) {
            if (macdLine[i] == null || paddedSignalLine[i] == null) {
                histogram.push(null);
            } else {
                histogram.push(macdLine[i] - paddedSignalLine[i]);
            }
        }
        
        return {
            macd: macdLine,
            signal: paddedSignalLine,
            histogram
        };
    }
    
    /**
     * Stochastic Oscillator
     */
    calculateStochastic(highData, lowData, closeData, kPeriod = 14, dPeriod = 3) {
        if (!Array.isArray(highData) || !Array.isArray(lowData) || !Array.isArray(closeData)) {
            throw new Error('Invalid data arrays for Stochastic calculation');
        }
        
        if (highData.length !== lowData.length || lowData.length !== closeData.length) {
            throw new Error('Data arrays must have the same length');
        }
        
        const kPercent = [];
        const dPercent = [];
        
        for (let i = 0; i < closeData.length; i++) {
            if (i < kPeriod - 1) {
                kPercent.push(null);
                continue;
            }
            
            // Find highest high and lowest low in the period
            const periodHigh = Math.max(...highData.slice(i - kPeriod + 1, i + 1));
            const periodLow = Math.min(...lowData.slice(i - kPeriod + 1, i + 1));
            
            if (periodHigh === periodLow) {
                kPercent.push(50); // Avoid division by zero
            } else {
                const k = ((closeData[i] - periodLow) / (periodHigh - periodLow)) * 100;
                kPercent.push(k);
            }
        }
        
        // Calculate %D (moving average of %K)
        const kValues = kPercent.filter(v => v !== null);
        const dValues = this.calculateSMA(kValues, dPeriod);
        
        // Pad D values to match original data length
        let dIndex = 0;
        for (let i = 0; i < kPercent.length; i++) {
            if (kPercent[i] !== null && dIndex < dValues.length) {
                dPercent.push(dValues[dIndex]);
                dIndex++;
            } else {
                dPercent.push(null);
            }
        }
        
        return {
            k: kPercent,
            d: dPercent
        };
    }
    
    /**
     * Average True Range (ATR)
     */
    calculateATR(highData, lowData, closeData, period = 14) {
        if (!Array.isArray(highData) || !Array.isArray(lowData) || !Array.isArray(closeData)) {
            throw new Error('Invalid data arrays for ATR calculation');
        }
        
        const trueRanges = [];
        
        for (let i = 0; i < closeData.length; i++) {
            if (i === 0) {
                trueRanges.push(highData[i] - lowData[i]);
                continue;
            }
            
            const tr1 = highData[i] - lowData[i];
            const tr2 = Math.abs(highData[i] - closeData[i - 1]);
            const tr3 = Math.abs(lowData[i] - closeData[i - 1]);
            
            trueRanges.push(Math.max(tr1, tr2, tr3));
        }
        
        // Calculate ATR using SMA
        return this.calculateSMA(trueRanges, period);
    }
    
    /**
     * On-Balance Volume (OBV)
     */
    calculateOBV(closeData, volumeData) {
        if (!Array.isArray(closeData) || !Array.isArray(volumeData)) {
            throw new Error('Invalid data arrays for OBV calculation');
        }
        
        if (closeData.length !== volumeData.length) {
            throw new Error('Close and volume data must have the same length');
        }
        
        const obv = [volumeData[0] || 0];
        
        for (let i = 1; i < closeData.length; i++) {
            const previousOBV = obv[i - 1] || 0;
            const volume = volumeData[i] || 0;
            
            if (closeData[i] > closeData[i - 1]) {
                obv.push(previousOBV + volume);
            } else if (closeData[i] < closeData[i - 1]) {
                obv.push(previousOBV - volume);
            } else {
                obv.push(previousOBV);
            }
        }
        
        return obv;
    }
    
    /**
     * Batch calculation for multiple indicators
     */
    calculateBatch(indicators, data, options = {}) {
        const results = {};
        const errors = {};
        
        for (const indicator of indicators) {
            try {
                const calculator = this.calculators[indicator.type];
                if (!calculator) {
                    throw new Error(`Unknown indicator type: ${indicator.type}`);
                }
                
                const params = { ...options, ...indicator.options };
                
                if (indicator.type === 'bollinger' || indicator.type === 'macd') {
                    results[indicator.name || indicator.type] = calculator(data.close, params.period, params.period2, params.period3);
                } else if (indicator.type === 'stochastic') {
                    results[indicator.name || indicator.type] = calculator(data.high, data.low, data.close, params.kPeriod, params.dPeriod);
                } else if (indicator.type === 'atr') {
                    results[indicator.name || indicator.type] = calculator(data.high, data.low, data.close, params.period);
                } else if (indicator.type === 'obv') {
                    results[indicator.name || indicator.type] = calculator(data.close, data.volume);
                } else {
                    results[indicator.name || indicator.type] = calculator(data.close || data, params.period);
                }
            } catch (error) {
                errors[indicator.name || indicator.type] = error.message;
            }
        }
        
        return { results, errors };
    }
}

// Worker message handler
const calculator = new ChartCalculator();

self.onmessage = function(e) {
    const { taskId, type, data, options = {} } = e.data;
    
    try {
        let result;
        
        if (type === 'batch') {
            // Batch calculation
            result = calculator.calculateBatch(data.indicators, data.data, options);
        } else {
            // Single indicator calculation
            const calculatorFunction = calculator.calculators[type];
            
            if (!calculatorFunction) {
                throw new Error(`Unknown indicator type: ${type}`);
            }
            
            // Handle different parameter patterns
            if (type === 'bollinger') {
                result = calculatorFunction(data, options.period, options.stdDev);
            } else if (type === 'macd') {
                result = calculatorFunction(data, options.fastPeriod, options.slowPeriod, options.signalPeriod);
            } else if (type === 'stochastic') {
                result = calculatorFunction(data.high, data.low, data.close, options.kPeriod, options.dPeriod);
            } else if (type === 'atr') {
                result = calculatorFunction(data.high, data.low, data.close, options.period);
            } else if (type === 'obv') {
                result = calculatorFunction(data.close, data.volume);
            } else {
                result = calculatorFunction(data, options.period);
            }
        }
        
        // Send successful result
        self.postMessage({
            taskId,
            success: true,
            result: result,
            timestamp: Date.now()
        });
        
    } catch (error) {
        // Send error result
        self.postMessage({
            taskId,
            success: false,
            error: error.message,
            stack: error.stack,
            timestamp: Date.now()
        });
    }
};

// Worker initialization message
self.postMessage({
    type: 'init',
    message: 'Chart calculation worker initialized',
    supportedIndicators: Object.keys(calculator.calculators),
    timestamp: Date.now()
});

console.log('🔥 Chart Worker initialized with calculators:', Object.keys(calculator.calculators));