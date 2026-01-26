import os
import redis
import sys

# Get Redis connection details from environment variables
REDIS_HOST = os.getenv('REDIS_HOST', '192.168.1.209')
REDIS_PORT = int(os.getenv('REDIS_PORT', '32008'))
STREAM_NAME = os.getenv('REDIS_STREAM_NAME', 'quotes-stream')

def main():
    """Service to read quotes from Redis stream and print them for testing."""
    try:
        # Connect to Redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        
        # Test connection
        r.ping()
        print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        print(f"Reading from stream: {STREAM_NAME}")
        print("Waiting for quotes...\n")
        
        # Read from stream in real-time
        last_id = '0'  # Start from beginning, use '$' for new messages only
        
        while True:
            try:
                messages = r.xread({STREAM_NAME: last_id}, block=0, count=10)
                
                for stream_name, stream_messages in messages:
                    for message_id, data in stream_messages:
                        print(f"Quote: {data}")
                        last_id = message_id
            except redis.ConnectionError as e:
                print(f"Connection error: {e}", file=sys.stderr)
                break
            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error reading from stream: {e}", file=sys.stderr)
                continue
                
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()