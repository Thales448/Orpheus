#!/usr/bin/env python3
"""
Simple web service to manage ticker symbols in public.tickers only.
Allows adding and deleting tickers from the single list.
"""

import os
import sys
import logging
from flask import Flask, render_template_string, request, redirect, url_for, flash
import psycopg2
from psycopg2 import extras
try:
    from psycopg2.errors import IntegrityError
except ImportError:
    # Fallback for older psycopg2 versions
    IntegrityError = psycopg2.IntegrityError
from dotenv import load_dotenv
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

def get_db_connection():
    """Get database connection using environment variables"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", os.environ.get("DB_NAME")),
            user=os.getenv("DB_USER", os.environ.get("DB_USER")),
            password=os.getenv("DB_PASSWORD", os.environ.get("DB_PASSWORD")),
            host=os.getenv("DB_HOST", os.environ.get("DB_HOST")),
            port=os.getenv("DB_PORT", os.environ.get("DB_PORT"))
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def test_db_connection():
    """Test database connection and return status"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Test public.tickers
            cursor.execute("SELECT COUNT(*) FROM public.tickers")
            tickers_count = cursor.fetchone()[0]
        conn.close()
        return True, tickers_count
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False, 0

def get_tickers_list():
    """Get all tickers from public.tickers"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("SELECT id, ticker FROM public.tickers ORDER BY ticker")
            tickers = cursor.fetchall()
        conn.close()
        return [dict(row) for row in tickers]
    except Exception as e:
        logger.error(f"Error fetching tickers: {e}")
        return []

def add_ticker_to_db(ticker_symbol):
    """Add a ticker to public.tickers, if it doesn't already exist."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            ticker_symbol = ticker_symbol.upper().strip()
            cursor.execute("SELECT id FROM public.tickers WHERE ticker = %s", (ticker_symbol,))
            result = cursor.fetchone()

            if result:
                conn.close()
                return False, f"Ticker {ticker_symbol} already exists."

            try:
                cursor.execute("""
                    INSERT INTO public.tickers (ticker)
                    VALUES (%s)
                    RETURNING id
                """, (ticker_symbol,))
                ticker_id = cursor.fetchone()[0]
                conn.commit()
                conn.close()
                logger.info(f"Added {ticker_symbol} to public.tickers (id: {ticker_id})")
                return True, f"Successfully added {ticker_symbol}."
            except IntegrityError as e:
                conn.rollback()
                conn.close()
                logger.error(f"IntegrityError on insert: {e}")
                return False, f"Could not add ticker: {ticker_symbol} (IntegrityError)"
    except Exception as e:
        logger.error(f"Error adding ticker: {e}")
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return False, f"Error: {str(e)}"

def remove_ticker_from_db(ticker_id):
    """Remove a ticker from public.tickers by ID."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT ticker FROM public.tickers WHERE id = %s", (ticker_id,))
            result = cursor.fetchone()
            ticker_symbol = result[0] if result else None
            if not ticker_symbol:
                conn.close()
                return False, "Ticker not found."

            cursor.execute("DELETE FROM public.tickers WHERE id = %s", (ticker_id,))
            if cursor.rowcount == 0:
                conn.close()
                return False, "Deletion failed. Ticker not found."

            conn.commit()
            conn.close()
            logger.info(f"Removed {ticker_symbol} from public.tickers")
            return True, f"Successfully removed {ticker_symbol}."
    except Exception as e:
        logger.error(f"Error removing ticker: {e}")
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return False, f"Error: {str(e)}"

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Ticker Manager</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .status {
            padding: 10px;
            margin: 20px 0;
            border-radius: 4px;
            background-color: #e8f5e9;
            border-left: 4px solid #4CAF50;
        }
        .error {
            background-color: #ffebee;
            border-left-color: #f44336;
        }
        .section {
            margin: 30px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .add-form {
            margin: 20px 0;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }
        input[type="text"] {
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 200px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        .delete-btn {
            background-color: #f44336;
            padding: 5px 15px;
            font-size: 14px;
        }
        .delete-btn:hover {
            background-color: #da190b;
        }
        .count {
            font-weight: bold;
            color: #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Ticker Manager</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="status {{ 'error' if category == 'error' else '' }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="status {{ 'error' if not db_ok else '' }}">
            <strong>Database Status:</strong> 
            {% if db_ok %}
                ✅ Connected | Tickers: {{ tickers_count }}
            {% else %}
                ❌ Connection Failed
            {% endif %}
        </div>

        <div class="section">
            <h2>Add Ticker</h2>
            <div class="add-form">
                <form method="POST" action="/add">
                    <input type="text" name="ticker" placeholder="Enter ticker symbol (e.g., AAPL)" 
                           required pattern="[A-Za-z0-9]+" title="Alphanumeric characters only">
                    <button type="submit">Add Ticker</button>
                </form>
            </div>
        </div>

        <div class="section">
            <h2>Ticker List <span class="count">({{ all_tickers|length }} tickers)</span></h2>
            {% if all_tickers %}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Ticker Symbol</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for ticker in all_tickers %}
                    <tr>
                        <td>{{ ticker.id }}</td>
                        <td>{{ ticker.ticker }}</td>
                        <td>
                            <form method="POST" action="/delete" style="display: inline;">
                                <input type="hidden" name="ticker_id" value="{{ ticker.id }}">
                                <button type="submit" class="delete-btn" 
                                        onclick="return confirm('Remove {{ ticker.ticker }} from list?')">
                                    Delete
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p>No tickers found in database.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page showing the ticker list"""
    db_ok, tickers_count = test_db_connection()

    if db_ok:
        all_tickers = get_tickers_list()
    else:
        all_tickers = []
    
    return render_template_string(HTML_TEMPLATE,
                                 db_ok=db_ok,
                                 tickers_count=tickers_count,
                                 all_tickers=all_tickers)

@app.route('/add', methods=['POST'])
def add_ticker():
    """Add a ticker to public.tickers"""
    ticker = request.form.get('ticker', '').strip().upper()
    
    if not ticker:
        flash('Please enter a ticker symbol', 'error')
        return redirect(url_for('index'))
    
    success, message = add_ticker_to_db(ticker)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_ticker():
    """Remove a ticker from public.tickers"""
    ticker_id = request.form.get('ticker_id')
    
    if not ticker_id:
        flash('Invalid ticker ID', 'error')
        return redirect(url_for('index'))
    
    try:
        ticker_id = int(ticker_id)
    except ValueError:
        flash('Invalid ticker ID format', 'error')
        return redirect(url_for('index'))
    
    success, message = remove_ticker_from_db(ticker_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Test database connection on startup
    logger.info("Starting Ticker Manager web service...")
    db_ok, tickers_count = test_db_connection()

    if db_ok:
        logger.info(f"✅ Database connected - Tickers: {tickers_count}")
    else:
        logger.error("❌ Database connection failed. Check your environment variables.")
        sys.exit(1)
    
    # Get port from environment or default to 5000
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=True)

