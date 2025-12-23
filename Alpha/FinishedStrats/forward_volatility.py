"""
    Title: Forward Volatility Trading Strategy Template
    Description: The forward volatility strategy is to take advantage of
    volatility anomaly between near expiry and far expiry.

    Data requirement: Data subscription to your local exchange is required
    for Futures and Options data feed.

    ############################# DISCLAIMER #############################
    This is a strategy template only and should not be
    used for live trading without appropriate backtesting and tweaking of
    the strategy parameters.
    ######################################################################
"""

# Import datetime package
from datetime import datetime

# To calculate implied volatility
import mibian as m

# Import pandas and numpy
import pandas as pd
import numpy as np


def initialize(context):

    # Define the position
    context.position = 0

    schedule_function(
        rebalance,
        date_rule=date_rules.every_day(),
        time_rule=time_rules.market_close(minutes=5)
    )

    '''
    ############################# ATTENTION ##############################
    The following parameters need to be changed as per your selection of
    the option and future contract.
    ######################################################################
    '''
    
    # Define the quantity
    context.quantity = 75

    # Define the symbol
    context.symbol = 'NIFTY50'

    # Define the strike price
    context.strike_price = 13000.0

    # Define the option type
    context.option_type = 'C'

    # Define the lookback
    context.lookback = 30

    # Expiry dates are in YYYYMMDD format
    context.near_expiry = "20201231"
    context.far_expiry = "20210128"

    # Near Future
    context.near_future = superSymbol(
        secType='FUT',
        symbol=context.symbol,
        exchange='NSE',
        currency='INR',
        expiry=context.near_expiry,
        includeExpired=True)

    # Far Future
    context.far_future = superSymbol(
        secType='FUT',
        symbol=context.symbol,
        exchange='NSE',
        currency='INR',
        expiry=context.far_expiry,
        includeExpired=True)

    # Near Option
    context.near_option = superSymbol(
        secType='OPT',
        symbol=context.symbol,
        exchange='NSE',
        currency='INR',
        expiry=context.near_expiry,
        strike=context.strike_price,
        right=context.option_type,
        includeExpired=True)

    # Far Option
    context.far_option = superSymbol(
        secType='OPT',
        symbol=context.symbol,
        exchange='NSE',
        currency='INR',
        expiry=context.far_expiry,
        strike=context.strike_price,
        right=context.option_type,
        includeExpired=True)


# Function to convert string date as a date time object
def datetimeobj(strdate):
    return datetime.strptime(strdate, '%Y%m%d').date()


def forward_volatality(df):
    nifty_data = df
    nifty_data['near_month_days_to_expiry'] = (
        nifty_data.near_month_expiry - nifty_data.index).dt.days

    nifty_data['far_month_days_to_expiry'] = (
        nifty_data.far_month_expiry - nifty_data.index).dt.days

    nifty_data['IV_near_month'] = 0
    nifty_data['IV_far_month'] = 0

    for row in range(len(nifty_data)):
        nifty_data.iloc[row, nifty_data.columns.get_loc('IV_near_month')] = m.BS([
            nifty_data.iloc[row]['fut_near_month_close'],
            nifty_data.iloc[row]['strike_price'],
            0,
            nifty_data.iloc[row]['near_month_days_to_expiry']
        ],
            callPrice=nifty_data.iloc[row]['LTP_near_month']
        ).impliedVolatility

        nifty_data.iloc[row, nifty_data.columns.get_loc('IV_far_month')] = m.BS([
            nifty_data.iloc[row]['fut_far_month_close'],
            nifty_data.iloc[row]['strike_price'],
            0,
            nifty_data.iloc[row]['far_month_days_to_expiry']
        ],
            callPrice=nifty_data.iloc[row]['LTP_far_month']
        ).impliedVolatility

    # Calculate the variance for near-month and far-month
    nifty_data['variance_near_month'] = (
        nifty_data.IV_near_month**2 / 365) * nifty_data.near_month_days_to_expiry
    nifty_data['variance_far_month'] = (
        nifty_data.IV_far_month**2 / 365) * nifty_data.far_month_days_to_expiry

    # Calculate the difference in far-month and near-month variance
    nifty_data['variance_diff'] = nifty_data.variance_far_month - \
        nifty_data.variance_near_month
    nifty_data['forward_variance_days'] = nifty_data.far_month_days_to_expiry - \
        nifty_data.near_month_days_to_expiry

    # Calculate forward volatility from forward varinace
    nifty_data['forward_volatility'] = (
        nifty_data.variance_diff * 365 / nifty_data.forward_variance_days)**0.5

    nifty_data['signal'] = np.where(
        nifty_data.forward_volatility > nifty_data.IV_near_month, -1, 1)

    return nifty_data


def rebalance(context, data):

    near_future_data = data.history(context.near_future,
                                    'close', context.lookback , '1d')

    far_future_data = data.history(context.far_future,
                                   'close', context.lookback , '1d')

    near_option_data = data.history(context.near_option,
                                    'close', context.lookback , '1d')

    far_option_data = data.history(context.far_option,
                                   'close', context.lookback , '1d')

    data_df = pd.DataFrame({'date': near_future_data.index,
                            'symbol': context.symbol,
                            'fut_near_month_close': near_future_data.values,
                            'fut_far_month_close': far_future_data.values,
                            'strike_price': context.strike_price,
                            'near_month_expiry': datetimeobj(context.near_expiry),
                            'LTP_near_month': near_option_data.values,
                            'far_month_expiry': datetimeobj(context.far_expiry),
                            'LTP_far_month': far_option_data.values},
                           index=[1])

    data_df.index = data_df['date']

    # Call the forward_volatality function with the latest data
    fv = forward_volatality(data_df)

    signal = fv['signal'][-1]

    # Taking position for options
    if signal == -1 and context.position != -1:
        order_target(context.near_option, context.quantity)
        order_target(context.far_option, -context.quantity)
        context.position = -1

    if signal == 1 and context.position != 1:
        order_target(context.near_option, -context.quantity)
        order_target(context.far_option, context.quantity)
        context.position = 1
