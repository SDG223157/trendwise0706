"""
Configuration file for visualization layout settings
"""

LAYOUT_CONFIG = {
    'total_height': 1200,
    'lookback_days_ratio': 0.6,
    'chart_area': {
        'stock': {
            'domain': {'x': [0.05, 0.95], 'y': [0.65, 0.95]}  # Main chart top 33%
        },
        'non_stock': {
            'domain': {'x': [0.05, 0.95], 'y': [0.60, 0.95]}  # Main chart top 35%
        }
    },
    'tables': {
        'stock': {
            'company_info': {
                'x': [0.05, 0.48],
                'y': [0.48, 0.58]  # Length: 0.10
            },
            'analysis_summary': {
                'x': [0.52, 0.95],  # Horizontal space: 0.04 from company_info
                'y': [0.48, 0.58]  # Same length: 0.10
            },
            'trading_signals': {
                'x': [0.05, 0.95],
                'y': [0.34, 0.44]  # Vertical space: 0.04 from above tables
            },
            'metrics': {
                'x': [0.05, 0.95],
                'y': [0.20, 0.30]  # Vertical space: 0.04 from trading_signals
            },
            'growth': {
                'x': [0.05, 0.95],
                'y': [0.06, 0.16]  # Vertical space: 0.04 from metrics
            }
        },
        'non_stock': {
            'analysis_summary': {
                'x': [0.05, 0.48],  # Left half
                'y': [0.20, 0.50]  # Length of 0.3
            },
            'trading_signals': {
                'x': [0.52, 0.95],  # Right half, 0.04 gap from analysis_summary
                'y': [0.20, 0.50]  # Same length of 0.3
            }
        }
    },
    'annotations': {
        'stock': {
            'headers': {
                'chart': {'x': 0.05, 'y': 0.97},
                'company_info_title': {'x': 0.05, 'y': 0.59, 'text': 'Company Information'},  # 0.01 above table
                'analysis_summary': {'x': 0.55, 'y': 0.59},  # 0.01 above table
                'trading_signals': {'x': 0.05, 'y': 0.45},  # 0.01 above table
                'metrics': {'x': 0.05, 'y': 0.30},  # 0.01 above table
                'growth': {'x': 0.05, 'y': 0.16}  # 0.01 above table
            }
        },
        'non_stock': {
            'headers': {
                'chart': {'x': 0.05, 'y': 0.97},
                'analysis_summary': {'x': 0.05, 'y': 0.51},  # Just above analysis summary
                'trading_signals': {'x': 0.56, 'y': 0.51}  # Aligned with analysis_summary header
            }
        }
    },
    'spacing': {
        'vertical_gap': 0.05,
        'horizontal_gap': 0.04,
        'header_gap': 0.01,
        'margin': {
            'top': 0.05,
            'bottom': 0.05,
            'left': 0.01,
            'right': 0.01
        }
    },
    'legend': dict(
        yanchor="top",
        y=0.85,  # Move legend higher to align with top of chart
        xanchor="left",
        x=1.02,
        bgcolor='rgba(255, 255, 255, 0.8)',
        bordercolor='rgba(0, 0, 0, 0.2)',
        borderwidth=1,
        font=dict(size=8),  # Smaller font size
        itemsizing='constant',  # Keep marker sizes constant
        itemwidth=30,  # Reduce width of legend items
        yref='paper',  # Use paper coordinates to prevent chart movement
        itemclick=False,  # Disable clicking
        itemdoubleclick=False  # Disable double clicking
    )
}

# Table style configuration
TABLE_STYLE = {
    'stock': {
        'header': {
            'fill_color': 'lightgrey',
            'font': dict(size=12),
            'align': 'left',
            'height': 30
        },
        'cells': {
            'font': dict(size=11),
            'align': 'left',
            'height': 30
        }
    },
    'non_stock': {
        'header': {
            'fill_color': 'lightgrey',
            'font': dict(size=13),
            'align': 'left',
            'height': 35  # Double height for non-stocks
        },
        'cells': {
            'font': dict(size=12),
            'align': 'left',
            'height': 35  # Double height for non-stocks
        }
    }
}

# Chart style configuration
CHART_STYLE = {
    'colors': {
        'price_line': 'black',
        'regression_line': 'red',
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
        'retracement': dict(width=1, dash='dot'),
        'position': dict(width=1, dash='dot')
    },
    'marker_styles': {
        'crossover': dict(
            symbol='star',
            size=8,
            line=dict(width=1)
        )
    }
}