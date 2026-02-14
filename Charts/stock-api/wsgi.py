#!/usr/bin/env python3
"""
WSGI Entry Point for Production Deployment

This file provides a WSGI application entry point for production WSGI servers
like gunicorn, uwsgi, or waitress.

NOTE: This WSGI entry point only exposes the Flask API, not the full service
(scheduler, etc.). For full service functionality, use ingest_historical_stock.py directly.

Usage:
    # With gunicorn
    gunicorn -w 4 -b 0.0.0.0:8080 wsgi:app
    
    # With waitress
    waitress-serve --host=0.0.0.0 --port=8080 wsgi:app
    
    # With uwsgi
    uwsgi --http :8080 --wsgi-file wsgi.py --callable app
"""

import os
import sys

# Add the Charts directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and create the service to get the Flask app
from ingest_historical_stock import HistoricalStockIngestionService

# Create service instance and initialize
_service = HistoricalStockIngestionService()
_service.initialize()
_service.update_healthcheck()

# Start scheduler if enabled
if _service.schedule_enabled:
    _service.start_scheduler()

# Export the Flask app for WSGI servers
app = _service.app

if __name__ == '__main__':
    # If run directly, start the full service
    from ingest_historical_stock import main
    main()

