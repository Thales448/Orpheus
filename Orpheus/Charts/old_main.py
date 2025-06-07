from Charts.__init__ import config, DatabaseConnection, CreateStream, WatchlistLogic, logging, os, DataCollector
import pandas as pd
import requests as rq
import logging

logger = logging.getLogger(__name__)


class Charts():
    def __init__(self):
        self.rqdata = None
        self.watchlists =  WatchlistLogic(config)
        self.conn = DatabaseConnection()
        self.datacollector = DataCollector(self.conn, config)

    def add_equity(self, ticker: str, resolution= "daily", start_time = None, end_time = None):
        
        data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
        
        if data:
            if len(data) != 0:
                df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
            else:
                return None 
        elif resolution in ["daily", "weekly", "monthly"]:
            self.datacollector.get_stocks_10year_daily(ticker)
            data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
        
        elif resolution in ["1m", "5m", "10m", "15m", "30m", "minute", "hourly"]:
            self.datacollector.get_stocks_minute(ticker)
            data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)

        
        df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df["Time"]=pd.to_datetime(df["Time"],format='%d.%m.%Y %H:%M:%S')
        df.set_index("Time", inplace=True)
        df["Close"] = df["Close"].astype(float)
        df["Open"] = df["Open"].astype(float)
        df["High"] = df["High"].astype(float)
        df["Low"] = df["Low"].astype(float)
        df["Volume"] = df["Volume"].astype(float)


        return df

    def add_crypto(self, coin: str, resolution = "daily"):
        data = self.conn.get_crypto_data(coin, resolution)
        return pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])

    def add_option_data(self, ticker=None, option_symbol=None, start_time=None, end_time=None, expiry=None, put=True, call= True, delta_away_from_atm=1, resolution = "daily", current=True):


        """
        Retrieve option data from the database.

        Parameters:
            ticker (str): The underlying symbol (Required if option_symbol is not provided.)
            
            start_time (str, optional): Start
              date in "YYYY-MM-DD" format.
            
            end_time (str, optional): End date in "YYYY-MM-DD" format. If not provided and start_time is given, assumes current date.
            
            expiry (str or int, optional): Either a specific expiry date (as a string in "YYYY-MM-DD") 
                or an integer representing the number of days from the base date (start_time if provided, else current date) to the expiry.
            
            put (bool): Whether to include put options. Default is True.
            
            call (bool): Whether to include call options. Default is True.
            
            delta_away_from_abs_1_ (float, optional): Tolerance from 1 for call delta or -1 for put delta.
            
            resolution (str): Data resolution; kept for compatibility.
            
            current (bool): If True, force retrieval from the options.realtime table (returning only current data).
        
        Returns:
            If start_time and/or end_time are provided (i.e. historical filtering is requested):
                pd.DataFrame: A MultiIndex DataFrame with index levels ["Time", "Expiry_date"],
                so you can slice per expiry date.
            Otherwise:
                pd.DataFrame: A DataFrame of option chain data (organized as rows).
        """
        if ticker and not option_symbol:

            
            data = self.conn.get_option_chain(ticker, start_time, end_time, expiry, put, call, delta_away_from_atm, resolution,current)
            
            if data:
                if len(data) != 0:
                    df = pd.DataFrame(data, columns=["Symbol", "Description", "Strike", "Bid", "Ask", "Volume", "Last_volume","Option_type", "Expiry_date", "Delta", "Gamma", "Theta", "Vega", "Rho", "Mid_iv", "Time"])
                else:
                    return None 
            elif resolution in ["daily", "weekly", "monthly"]:
                self.datacollector.get_options_chains(ticker)
                data = self.conn.get_option_chain(ticker, start_time, end_time, expiry, put, call, delta_away_from_atm, resolution,current)
        
            elif resolution in ["1m", "5m", "10m", "15m", "30m", "minute", "hourly"]:
                self.datacollector.get_options_chains(ticker)
                data = self.conn.get_option_chain(ticker, start_time, end_time, expiry, put, call, delta_away_from_atm, resolution,current)

            
            df = pd.DataFrame(data, columns =["Symbol", "Description", "Strike", "Bid", "Ask", "Volume", "Last_volume","Option_type", "Expiry_date", "Delta", "Gamma", "Theta", "Vega", "Rho", "Mid_iv", "Time"])
    
            df["Time"] = pd.to_datetime(df["Time"])
            
            decimal_columns = ["Bid", "Ask", "Volume", "Last_volume", "Delta", "Gamma", "Theta", "Vega", "Rho", "Mid_iv"]
            for col in decimal_columns:
                df[col] = df[col].astype(float)
            
            if  start_time:
                if not df.empty:
                    df_multi = df.copy()
                    df_multi.set_index(["Time", "Expiry_date"], inplace=True)
                return df_multi
            else:
                df.set_index("Time", inplace=True)
                return df

            
        elif option_symbol and not ticker:
            data = self.conn.get_option_symbol(option_symbol, start_time=start_time, end_time=end_time, resolution= resolution)
    
            df = pd.DataFrame(data, columns=["Bid", "Ask", "Volume", "Last_volume","Delta", "Gamma", "Theta", "Vega", "Rho", "Mid_iv", "Time"])
            df["Time"] = pd.to_datetime(df["Time"], format='%d.%m.%Y %H:%M:%S')
            df.set_index("Time", inplace=True)
            decimal_columns = ["Bid", "Ask", "Volume", "Last_volume", "Delta", "Gamma", "Theta", "Vega", "Rho", "Mid_iv"]
            for col in decimal_columns:
                df[col] = df[col].astype(float)
            return df
        
