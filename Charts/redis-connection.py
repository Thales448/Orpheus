from redis.cluster import RedisCluster, ClusterNode
import redis

import websocket
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Connect to Redis Cluster

REDIS_URL = "redis://192.168.1.209:32008"
r = None

def connect_redis():
    """Establish Redis connection with retry logic"""
    global r
    max_retries = 5
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=5)
            # Test the connection
            r.ping()
            logging.info("Redis connection successful!")
            r.set('status', 'connected')
            logging.info(f"Status: {r.get('status')}")
            return True
        except Exception as e:
            logging.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error("Failed to connect to Redis after all retries")
                return False
    
    return False

# Initialize Redis connection
if not connect_redis():
    logging.error("Cannot proceed without Redis connection. Exiting.")
    exit(1)

def stream_quotes_to_redis():
    url = "ws://localhost:8765/v1/events"
    logging.info(f"Connecting to quote stream at {url}")
    
    def on_message(ws, message):
        """Handle incoming WebSocket messages"""
        global r
        max_redis_retries = 3
        
        for attempt in range(max_redis_retries):
            try:
                # Check if connection is alive, reconnect if needed
                try:
                    r.ping()
                except:
                    logging.warning("Redis connection lost, attempting to reconnect...")
                    if not connect_redis():
                        logging.error("Failed to reconnect to Redis")
                        return
                
                # Message is already a string from websocket-client
                r.xadd('webstream', {'data': message})
                logging.info(f"Added quote to Redis stream: {message}")
                return  # Success, exit retry loop
            except Exception as e:
                if attempt < max_redis_retries - 1:
                    logging.warning(f"Redis operation failed (attempt {attempt + 1}/{max_redis_retries}): {e}")
                    time.sleep(0.5)  # Brief delay before retry
                else:
                    logging.error(f"Error processing or inserting quote after {max_redis_retries} attempts: {e}")
    
    def on_error(ws, error):
        """Handle WebSocket errors"""
        logging.error(f"WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logging.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        logging.info("Will attempt to reconnect...")
    
    def on_open(ws):
        """Handle WebSocket open"""
        logging.info("Successfully connected to the quote stream.")
    
    while True:
        try:
            # Create WebSocket connection
            ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Run forever (will reconnect on close)
            ws.run_forever()
            
        except Exception as e:
            logging.error(f"Connection error: {e}")
            logging.info("Retrying in 3 seconds...")
            time.sleep(3)

if __name__ == "__main__":
    logging.info("Starting stream -> Redis process.")
    stream_quotes_to_redis()


