from flask import Blueprint, render_template, request, jsonify
from app.stock.dashboard import get_stock_analysis
from app.stock.optimized_dashboard import get_stock_analysis_cached
import plotly.utils
import json
import logging
import time

logger = logging.getLogger(__name__)

stock_bp = Blueprint('stock', __name__, url_prefix='/stock')

@stock_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Show the stock analysis dashboard with caching"""
    start_time = time.time()
    ticker = request.args.get('ticker', 'AAPL')
    period = request.args.get('period', '2y')
    
    logger.info(f"🔄 Dashboard request: {ticker} {period}")
    
    # Get cached analysis data
    fig, info = get_stock_analysis_cached(ticker, period)
    
    if fig is None:
        # Handle error case
        logger.error(f"❌ Dashboard error for {ticker}: {info}")
        return render_template('stock/dashboard.html', 
                               error=info, 
                               ticker=ticker, 
                               period=period)
    
    # Convert fig to JSON for the template
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    duration = time.time() - start_time
    logger.info(f"✅ Dashboard response for {ticker} {period} ({duration*1000:.1f}ms)")
    
    return render_template('stock/dashboard.html', 
                           graph_json=graph_json,
                           info=info,
                           ticker=ticker,
                           period=period)

@stock_bp.route('/analyze', methods=['POST'])
def analyze():
    """API endpoint to get analysis data with caching"""
    start_time = time.time()
    data = request.json
    ticker = data.get('ticker', 'AAPL')
    period = data.get('period', '2y')
    
    logger.info(f"🔄 API analyze request: {ticker} {period}")
    
    # Get cached analysis data
    fig, info = get_stock_analysis_cached(ticker, period)
    
    if fig is None:
        logger.error(f"❌ API analyze error for {ticker}: {info}")
        return jsonify({"error": info}), 400
    
    # Convert fig to JSON
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    duration = time.time() - start_time
    logger.info(f"✅ API analyze response for {ticker} {period} ({duration*1000:.1f}ms)")
    
    return jsonify({
        "graph": graph_json,
        "info": info,
        "performance": {
            "response_time_ms": round(duration * 1000, 1),
            "cache_enabled": True
        }
    })