"""
Configuration file for visualization layout settings
"""

LAYOUT_CONFIG = {
    'chart_area': {
        'domain': {'x': [0.05, 0.95], 'y': [0.62, 0.95]},  # Main chart top 40%
    },
    'tables': {
        'analysis_summary': {
            'x': [0.05, 0.48],
            'y': [0.42, 0.55]
        },
        'trading_signals': {
            'x': [0.52, 0.95],
            'y': [0.42, 0.55]
        },
        'metrics': {
            'x': [0.05, 0.95],
            'y': [0.22, 0.35]
        },
        'growth': {
            'x': [0.05, 0.95],
            'y': [0.02, 0.15]
        }
    },
    'annotations': {
        'headers': {
            'chart': {'x': 0.05, 'y': 0.97},
            'analysis_summary': {'x': 0.05, 'y': 0.56},
            'trading_signals': {'x': 0.56, 'y': 0.56},
            'metrics': {'x': 0.05, 'y': 0.36},
            'growth': {'x': 0.05, 'y': 0.16}
        },
        'stats': {
            'price': {'x': 0.07, 'y': 0.92},
            'regression': {'x': 0.30, 'y': 0.92},
            'volatility': {'x': 0.53, 'y': 0.92},
            'signals': {'x': 0.76, 'y': 0.92}
        }
    },
    'spacing': {
        'vertical_gap': 0.07,
        'horizontal_gap': 0.04,
        'header_gap': 0.01,
        'margin': {
            'top': 0.05,
            'bottom': 0.05,
            'left': 0.05,
            'right': 0.05
        }
    }
}

# Chart style configuration
CHART_STYLE = {
    'colors': {
        'price_line': 'green',
        'regression_line': 'blue',
        'confidence_band': 'lightblue',
        'retracement_line': 'purple',
        'position_line': 'orange',
        'bullish_marker': 'green',
        'bearish_marker': 'red'
    },
    'line_styles': {
        'price': dict(width=3),
        'regression': dict(width=2, dash='dash'),
        'bands': dict(width=1),
        'retracement': dict(width=1),
        'position': dict(width=2, dash='dot')
    },
    'marker_styles': {
        'crossover': dict(
            symbol='star',
            size=12,
            line=dict(width=1)
        )
    }
}

# Table style configuration
TABLE_STYLE = {
    'header': {
        'fill_color': 'lightgrey',
        'font': dict(size=12),
        'align': 'left'
    },
    'cells': {
        'font': dict(size=11),
        'align': 'left'
    }
}
