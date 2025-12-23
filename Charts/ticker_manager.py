#!/usr/bin/env python3
"""
Simple web service to manage ticker symbols in public.alpha_list.
Shows both public.tickers and public.alpha_list, allows adding/deleting from alpha_list only.
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
            
            # Test public.alpha_list
            cursor.execute("SELECT COUNT(*) FROM public.alpha_list")
            alpha_count = cursor.fetchone()[0]
            
        conn.close()
        return True, tickers_count, alpha_count
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False, 0, 0

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

def get_alpha_list():
    """Get all tickers in public.alpha_list with their symbols"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT a.ticker_id, t.ticker, t.id
                FROM public.alpha_list a
                JOIN public.tickers t ON a.ticker_id = t.id
                ORDER BY t.ticker
            """)
            alpha_tickers = cursor.fetchall()
        conn.close()
        return [dict(row) for row in alpha_tickers]
    except Exception as e:
        logger.error(f"Error fetching alpha_list: {e}")
        return []

def add_to_alpha_list(ticker_symbol):
    """Add a ticker to alpha_list. Creates ticker in public.tickers if it doesn't exist."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # First, get or create the ticker
            ticker_symbol = ticker_symbol.upper().strip()
            
            # Check if ticker exists
            cursor.execute("SELECT id FROM public.tickers WHERE ticker = %s", (ticker_symbol,))
            result = cursor.fetchone()
            
            if result:
                ticker_id = result[0]
            else:
                # Create new ticker
                cursor.execute("""
                    INSERT INTO public.tickers (ticker)
                    VALUES (%s)
                    RETURNING id
                """, (ticker_symbol,))
                ticker_id = cursor.fetchone()[0]
                logger.info(f"Created new ticker: {ticker_symbol} (id: {ticker_id})")
            
            # Check if already in alpha_list (by ticker_id or symbol to be safe)
            cursor.execute("""
                SELECT ticker_id FROM public.alpha_list 
                WHERE ticker_id = %s OR symbol = %s
            """, (ticker_id, ticker_symbol))
            if cursor.fetchone():
                conn.close()
                return False, f"Ticker {ticker_symbol} is already in alpha_list"
            
            # Add to alpha_list - include both ticker_id and symbol columns
            # Handle potential primary key sequence issues by using a subquery approach
            # or let PostgreSQL handle the sequence, but catch and handle the error
            try:
                cursor.execute("""
                    INSERT INTO public.alpha_list (ticker_id, symbol)
                    VALUES (%s, %s)
                """, (ticker_id, ticker_symbol))
                conn.commit()
                conn.close()
                logger.info(f"Added {ticker_symbol} to alpha_list (ticker_id: {ticker_id})")
                return True, f"Successfully added {ticker_symbol} to alpha_list"
            except IntegrityError as e:
                # If it's a duplicate key error on the primary key, the sequence is out of sync
                # Try to fix the sequence and retry
                if "duplicate key value violates unique constraint" in str(e) and "alpha_list_pkey" in str(e):
                    logger.warning(f"Primary key sequence out of sync, attempting to fix...")
                    conn.rollback()
                    # Reset the sequence to the max ID + 1
                    cursor.execute("""
                        SELECT setval(
                            pg_get_serial_sequence('public.alpha_list', 'id'),
                            COALESCE((SELECT MAX(id) FROM public.alpha_list), 0) + 1,
                            false
                        )
                    """)
                    # Now retry the insert
                    cursor.execute("""
                        INSERT INTO public.alpha_list (ticker_id, symbol)
                        VALUES (%s, %s)
                    """, (ticker_id, ticker_symbol))
                    conn.commit()
                    conn.close()
                    logger.info(f"Added {ticker_symbol} to alpha_list (ticker_id: {ticker_id}) after sequence fix")
                    return True, f"Successfully added {ticker_symbol} to alpha_list"
                else:
                    # Re-raise if it's a different integrity error
                    raise
            
    except Exception as e:
        logger.error(f"Error adding to alpha_list: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False, f"Error: {str(e)}"

def remove_from_alpha_list(ticker_id):
    """Remove a ticker from alpha_list"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get ticker symbol for logging
            cursor.execute("SELECT ticker FROM public.tickers WHERE id = %s", (ticker_id,))
            result = cursor.fetchone()
            ticker_symbol = result[0] if result else "Unknown"
            
            # Remove from alpha_list
            cursor.execute("DELETE FROM public.alpha_list WHERE ticker_id = %s", (ticker_id,))
            if cursor.rowcount == 0:
                conn.close()
                return False, f"Ticker not found in alpha_list"
            
            conn.commit()
            conn.close()
            logger.info(f"Removed {ticker_symbol} from alpha_list")
            return True, f"Successfully removed {ticker_symbol} from alpha_list"
            
    except Exception as e:
        logger.error(f"Error removing from alpha_list: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False, f"Error: {str(e)}"

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Ticker Manager - Alpha List</title>
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
        <h1>📊 Ticker Manager - Alpha List</h1>
        
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
                ✅ Connected | Tickers: {{ tickers_count }} | Alpha List: {{ alpha_count }}
            {% else %}
                ❌ Connection Failed
            {% endif %}
        </div>

        <div class="section">
            <h2>Add Ticker to Alpha List</h2>
            <div class="add-form">
                <form method="POST" action="/add">
                    <input type="text" name="ticker" placeholder="Enter ticker symbol (e.g., AAPL)" 
                           required pattern="[A-Za-z0-9]+" title="Alphanumeric characters only">
                    <button type="submit">Add to Alpha List</button>
                </form>
            </div>
        </div>

        <div class="section">
            <h2>Alpha List <span class="count">({{ alpha_tickers|length }} tickers)</span></h2>
            {% if alpha_tickers %}
            <table>
                <thead>
                    <tr>
                        <th>Ticker Symbol</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in alpha_tickers %}
                    <tr>
                        <td>{{ item.ticker }}</td>
                        <td>
                            <form method="POST" action="/delete" style="display: inline;">
                                <input type="hidden" name="ticker_id" value="{{ item.ticker_id }}">
                                <button type="submit" class="delete-btn" 
                                        onclick="return confirm('Remove {{ item.ticker }} from alpha list?')">
                                    Delete
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p>No tickers in alpha list.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>All Tickers in Database <span class="count">({{ all_tickers|length }} tickers)</span></h2>
            <p><em>Read-only view of all tickers in public.tickers</em></p>
            {% if all_tickers %}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Ticker Symbol</th>
                    </tr>
                </thead>
                <tbody>
                    {% for ticker in all_tickers %}
                    <tr>
                        <td>{{ ticker.id }}</td>
                        <td>{{ ticker.ticker }}</td>
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
    """Main page showing both lists"""
    db_ok, tickers_count, alpha_count = test_db_connection()
    
    if db_ok:
        all_tickers = get_tickers_list()
        alpha_tickers = get_alpha_list()
    else:
        all_tickers = []
        alpha_tickers = []
    
    return render_template_string(HTML_TEMPLATE,
                                 db_ok=db_ok,
                                 tickers_count=tickers_count,
                                 alpha_count=alpha_count,
                                 all_tickers=all_tickers,
                                 alpha_tickers=alpha_tickers)

@app.route('/add', methods=['POST'])
def add_ticker():
    """Add a ticker to alpha_list"""
    ticker = request.form.get('ticker', '').strip().upper()
    
    if not ticker:
        flash('Please enter a ticker symbol', 'error')
        return redirect(url_for('index'))
    
    success, message = add_to_alpha_list(ticker)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_ticker():
    """Remove a ticker from alpha_list"""
    ticker_id = request.form.get('ticker_id')
    
    if not ticker_id:
        flash('Invalid ticker ID', 'error')
        return redirect(url_for('index'))
    
    try:
        ticker_id = int(ticker_id)
    except ValueError:
        flash('Invalid ticker ID format', 'error')
        return redirect(url_for('index'))
    
    success, message = remove_from_alpha_list(ticker_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Test database connection on startup
    logger.info("Starting Ticker Manager web service...")
    db_ok, tickers_count, alpha_count = test_db_connection()
    
    if db_ok:
        logger.info(f"✅ Database connected - Tickers: {tickers_count}, Alpha List: {alpha_count}")
    else:
        logger.error("❌ Database connection failed. Check your environment variables.")
        sys.exit(1)
    
    # Get port from environment or default to 5000
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=True)

