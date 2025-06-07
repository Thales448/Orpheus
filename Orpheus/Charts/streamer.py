import asyncio
import websockets
import requests
import json


class CreateStream:

    """
    This class opens a WebScoket Stream to Tradierto recieve back live data make sure you pass a complete watchlist of symbols you want to recieve live news on
    accepts tickers and option contract symbols
    """

    def __init__(self, watchlist, config):
        self.watchlist = watchlist
        self.session_id = None  # Initialize session_id
        self.get_session_id()

    def get_session_id(self):
        """
        Fetches a session ID from the Tradier API.
        """
        response = requests.post(
            'https://api.tradier.com/v1/markets/events/session',
            data={},
            headers=self.config.HEADERS
        )
        if response.status_code == 200:
            json_response = response.json()
            self.session_id = json_response['stream']['sessionid']
            print(f"Session ID fetched: {self.session_id}")
        else:
            print(f"Error fetching session ID: {response.status_code} - {response.text}")

    async def ws_connect(self):
        """
        Establishes a WebSocket connection and listens for messages.
        """
        if not self.session_id:
            print("Session ID is not available. Cannot connect to WebSocket.")
            return

        uri = "wss://ws.tradier.com/v1/markets/events"
        payload = json.dumps({
            "symbols": self.watchlist,
            "sessionid": self.session_id,
            "linebreak": True,
            "filter": ['quote']
        })

        async with websockets.connect(uri, ssl=True, compression=None) as websocket:
            await websocket.send(payload)
            print(f">>> {payload}")

            async for message in websocket:
                print(f"<<< {message}")

    def start_stream(self):
        """
        Starts the WebSocket connection by running the event loop.
        """
        if not self.session_id:
            print("Session ID is not available. Cannot start stream.")
            return

        # Use asyncio.run() to run the WebSocket connection
        asyncio.run(self.ws_connect())
