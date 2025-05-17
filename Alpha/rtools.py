import numpy  as np
import pandas as pd
import ta

class RTools():
    def __init__(self):
        self.info = "Tools Available: RSI"


    def RSI(self, df, period=14):
        series = df["Close"]
        delta = series.diff().dropna()
        u = delta * 0
        d = u.copy()
        u[delta > 0] = delta[delta > 0]
        d[delta < 0] = -delta[delta < 0]
        u[u.index[period-1]] = np.mean( u[:period] ) #first value is sum of avg gains
        u = u.drop(u.index[:(period-1)])
        d[d.index[period-1]] = np.mean( d[:period] ) #first value is sum of avg losses
        d = d.drop(d.index[:(period-1)])
        rs = pd.DataFrame.ewm(u, com=period-1, adjust=False).mean() / \
            pd.DataFrame.ewm(d, com=period-1, adjust=False).mean()
        return 100 - 100 / (1 + rs)

    def BBANDS(self, df, close_col='Close', window=20, std=2, fillna=False):
        """
        Adds Bollinger Bands (upper, lower, and middle) to a DataFrame.
        
        Parameters:
            df (pd.DataFrame): DataFrame containing a 'close' column.
            close_col (str): Column name for closing prices.
            window (int): Window period for Bollinger Bands.
            window_dev (int): Standard deviation factor.
            fillna (bool): Whether to fill NaN values.
        
        Returns:
            pd.DataFrame: DataFrame with new Bollinger Bands columns.
        """
        bb = ta.volatility.BollingerBands(close=df[close_col], window=window, window_dev=std, fillna=fillna)
        
        df["upperband"]= bb.bollinger_hband()
        df["lowerband"] = bb.bollinger_lband()
        df["middleband"] = bb.bollinger_mavg()
        df["pband"] = bb.bollinger_pband()
        df["wband"] = bb.bollinger_wband()
        

    def STD(self, df, window=20):
        series = df["Close"]
        std = series.rolling(window= window).std()

        return std

    def SMA(self, df, window):
        series = df["Close"]
        sma =  series.rolling(window=window).mean()

        return sma


    def VWAP(self, dataframe, label='vwap', window=3, fillna=True):
        data = ta.volume.VolumeWeightedAveragePrice(high=dataframe['High'], low=dataframe['Low'], close=dataframe["Close"], volume=dataframe['Volume'], window=window, fillna=fillna).volume_weighted_average_price()
        return data

    def ATR(self, df, high_col='High', low_col='Low', close_col='Close', window=14, fillna=False):

        atr = ta.volatility.AverageTrueRange(high=df[high_col], low=df[low_col], close=df[close_col], window=window, fillna=fillna).average_true_range()
        
        
        return atr
    
    def EMA(self, df, window=14):
        ema = ta.trend.EMAIndicator(close=df['Close'], window= window, fillna= True).ema_indicator()

        return ema

