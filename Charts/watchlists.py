import requests
import logging
import Charts.config as config 
logger = logging.getLogger(__name__)


class WatchlistLogic():
    def __init__(self, config):
        self.config = config
        self.logger = logger
    def get_watchlists(self):
        """
        Returns a list of all Watchlists in the tradier account
        """
        response = requests.get('https://api.tradier.com/v1/watchlists',
        params={},
        headers=self.config.HEADERS
        )
        if response.status_code == 200:
            json_response = response.json()
            watchlists = [item['name'] for item in json_response['watchlists']['watchlist']]
        return watchlists

    def get_watched(self, watchlists = 'all'):

        """
        Params = (watchlist)

        Returns a list of all symbols in watchlist. 
        for all watchlists = 'all'

        """
        symbols = []
        if watchlists == 'all':
            watchlists = self.get_watchlists()

        else:
            pass
        for watchlist in watchlists:

            response = requests.get(f'https://api.tradier.com/v1/watchlists/{watchlist}',
                params={},
                headers=self.config.HEADERS
            )
           
            if response.status_code == 200:
                items = response.json().get("watchlist", {}).get("items", {}).get("item", [])

                # Ensure 'items' is a list before processing
                if isinstance(items, dict):  
                    items = [items]  # Convert single dict entry to a list

                symbols.extend([item["symbol"] for item in items if "symbol" in item])

        return symbols

    def create_watchlist(self, name, symbols):
        """
        params = (watchlist_name, symbols)

        Creates a watchlist with the given name and list of symbols
        """
        symbols = ','.join(symbols)
        response = requests.post('https://api.tradier.com/v1/watchlists',
        data={'name': name, 'symbols': symbols},
        headers=self.config.HEADERS
        )
        
        if response.status_code != 200:
            self.logger.error(f'Error creating watchlist {name} with symbols {symbols}')
            self.logger.error(f'Error message: {response.json()}')
        
        else:
            self.logger.info(f'Watchlist {name} created with symbols {symbols}')

        return response.json()
    
    def add_symbols(self, watchlist_id, symbols):
        """
        params = (watchlist_name, symbols)

        Adds symbols to a watchlist
        """


        response = requests.post(f'https://api.tradier.com/v1/watchlists/{watchlist_id}/symbols',
            data={'symbols': symbols},
            headers= self.config.HEADERS
        )
        json_response = response.json()
        if response.status_code != 200:
            self.logger.error(f'Error adding symbols {symbols} to watchlist {watchlist_id}')
            self.logger.error(f'Error message: {response.json()}')

        else:
            self.logger.info(f'Symbols {symbols} added to watchlist {watchlist_id}')

        return response.json()

    def delete_symbol(self, watchlist_id, symbols):
        """
        params = wathclist Id and list of symbols to delete
        """
        for symbol in symbols:
            response = requests.delete(f'https://api.tradier.com/v1/watchlists/{watchlist_id}/symbols/{symbol}',
                headers=self.config.HEADERS
                )
            if response.status_code !=200:
                self.logger.error(f'Error deleting symbol {symbol} from watchlist {watchlist_id}')
                self.logger.error(f'Error message: {response.json()}')
            else:
                self.logger.info(f'Symbol {symbol} deleted from watchlist {watchlist_id}')

    def delete_watchlist(self, watchlist_id):

        response=requests.delete(f'https://api.tradier.com/v1/watchlists/{watchlist_id}',
        data={},
        headers=self.config.HEADERS
        )

        if response.status_code != 200:
            logger.error(f'Error deleting watchlist {watchlist_id}')
            logger.error(f'Error message: {response.json()}')
        elif response.status_code == 200:
            logger.info(f'Watchlist {watchlist_id} deleted successfuly :)')
