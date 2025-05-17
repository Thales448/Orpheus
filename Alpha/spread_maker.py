import psycopg2, pandas as pd, pprint, datetime, requests, pytz
from bs4 import BeautifulSoup
from urllib.parse import unquote
import pandas as pd



under, symbl, desc, strike, bid, ask, volu, l_volum,type, exp = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
delt, gamm, thet, veg, ro, iv =11, 12, 13, 14, 15,16

def main():
    for ticker in [ 'SPY', 'TSLA', 'NVDA', 'SPX', 'QQQ']:
        chains = get_latest_option_chain(conn, ticker)
        atm_strike = get_atm_strike(chains)
        chains = group_by_exp_date(chains)
        pprint.pprint(chains)
        x = create_bear_call(chains)
        print(x)

def select_option_chain(conn, ticker):
    query = """
    SELECT * FROM options.real_time
    WHERE underlying = %s
    """
    with conn.cursor() as cursor:
        cursor.execute(query, (ticker,))
        rows = cursor.fetchall()
    # Each row: (id, underlying, symbol, description, strike, bid, ask, volume, option_type, expiry_date last_volume, delta, gamma, theta, vega, rho, mid_iv)
    return rows

def create_bull_call( chain_dict_grouped_by_exp_dates):
   
    list =[]
    ticker = chain_dict_grouped_by_exp_dates[exp_date][1]

    for exp_date, chain in tsla_option_dict.items():
        dict = {}    

        print(f'Analyzing {ticker} {exp_date} chain')
        
        atm =  get_atm_strike(chain)
        
        atm__call_contract = [tup for tup in chain if tup[strike] == atm and tup[type] == 'call']
        atm_put_contract = [tup for tup in chain if tup[strike] == atm and tup[type] == 'put']

        dict['ticker'] = ticker
        dict['expiry_date'] = exp_date

        for cont in chain:
            if cont[type] == 'call':
                spread = (cont[strike] - atm)
                if (spread in [2.50, 5.0, 7.5 ]):
                    dict['spread_type'] = 'bull_call_spread'
                    dict['long_strike'] = atm
                    dict['short_strike'] = cont[strike]
                    dict['long_premium'] = (atm__call_contract[0][ask])
                    dict['short_premium'] = cont[bid] 
                    dict['net_cost'] = dict['long_premium'] - dict['short_premium']
                    dict['max_profit'] = spread - dict['net_cost']
                    dict['max_loss'] = dict['net_cost']
                    dict['break_even'] = dict['net_cost'] + atm 
                    dict['net_delta'] = atm__call_contract[0][delt] - cont[delt]
                    dict['net_gamma'] = atm__call_contract[0][gamm] - cont[gamm]
                    dict['net_vega'] = atm__call_contract[0][veg] - cont[veg]
                    dict['net_rho'] = atm__call_contract[0][ro] - cont[ro]
                    dict['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    dict['expected'] = dict['max_profit']* cont[delt] - dict['max_loss']* (1-cont[delt])
                    list.append(dict)
                    insert_spread(conn, dict)
    return list

def create_bear_call(chain_dict_grouped_by_exp_dates):
    results_list = []

    for exp_date, chain in chain_dict_grouped_by_exp_dates.items():

        ticker = chain_dict_grouped_by_exp_dates[exp_date][1][1]
        print(ticker)
        # Dictionary to store spread info for each combination found
        spread_dict = {}
        
        print(f'Analyzing {ticker} {exp_date} chain')
        atm = get_atm_strike(chain)

        # Grab the ATM call contract
        atm_call_contract = [
            opt for opt in chain 
            if (opt[strike] == atm and opt[type] == "call")
        ]
        
        # If for some reason no ATM call is found, skip
        if not atm_call_contract:
            continue
        
        atm_call = atm_call_contract[0]  
        short_strike = atm_call[strike]
        short_premium_bid = atm_call[bid]
        short_delta = atm_call[delt]
        short_gamma = atm_call[gamm]
        short_vega  = atm_call[veg]
        short_rho   = atm_call[ro]

        # Iterate through chain to find the higher strike calls
        for cont in chain:
            if cont[type] == "call":
                strike_diff = cont[strike] - short_strike
                
                if strike_diff in [2.5, 5.0, 7.5]:

                    spread_data = {}
                    spread_data["ticker"] = ticker
                    spread_data["expiry_date"] = exp_date
                    spread_data["spread_type"] = "bear_call_spread"
                    spread_data["short_strike"] = short_strike
                    spread_data["long_strike"] = cont[strike]
                    spread_data["short_premium"] = short_premium_bid
                    spread_data["long_premium"]  = cont[ask]
                    spread_data["net_cost"] = spread_data["long_premium"] - spread_data["short_premium"]

                    spread_data["spread_width"] = strike_diff
                    spread_data["max_profit"] = spread_data["net_cost"]
                    spread_data["max_loss"] = strike_diff - spread_data["net_cost"]
                    spread_data["break_even"] = short_strike + spread_data["net_cost"]

                    spread_data["net_delta"] = short_delta - cont[delt]
                    spread_data["net_gamma"] = short_gamma - cont[gamm]
                    spread_data["net_vega"]  = short_vega  - cont[veg]
                    spread_data["net_rho"]   = short_rho   - cont[ro]


                    spread_data["expected"] = (
                        spread_data["max_profit"] * cont[delt] 
                        - spread_data["max_loss"] * (1 - cont[delt])
                    )

                    spread_data["created_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    results_list.append(spread_data)
                    insert_spread(conn, spread_data)

    return results_list     


chains = get_latest_option_chain(conn, "TSLA")
chains = group_by_exp_date(chains)
x = create_bear_call(chains)
    
def insert_spread(conn, spread_dict):
    insert_query = """
    INSERT INTO options.spread (ticker, spread_type, expiry_date, long_strike, short_strike, long_premium, short_premium, net_cost, max_profit, max_loss, break_even, net_delta, net_gamma, net_vega, net_rho, created_at,expected)
    VALUES (%(ticker)s, %(spread_type)s, %(expiry_date)s, %(long_strike)s, %(short_strike)s, %(long_premium)s, %(short_premium)s, %(net_cost)s, %(max_profit)s, %(max_loss)s, %(break_even)s, %(net_delta)s, %(net_gamma)s, %(net_vega)s, %(net_rho)s, %(created_at)s, %(expected)s)
    ON CONFLICT(spread_type, expiry_date, long_strike, short_strike) DO UPDATE
    SET
        long_premium = EXCLUDED.long_premium,
        short_premium = EXCLUDED.short_premium,
        net_cost = EXCLUDED.net_cost,
        max_profit = EXCLUDED.max_profit,
        max_loss = EXCLUDED.max_loss,
        break_even = EXCLUDED.break_even,
        net_delta = EXCLUDED.net_delta,
        net_gamma = EXCLUDED.net_gamma,
        net_vega = EXCLUDED.net_vega,
        net_rho = EXCLUDED.net_rho,
        created_at = EXCLUDED.created_at,
        expected = EXCLUDED.expected
    WHERE options.spread.id = (
        SELECT id
        FROM options.spread
        WHERE spread_type = EXCLUDED.spread_type
        AND expiry_date = EXCLUDED.expiry_date
        AND long_strike = EXCLUDED.long_strike
        AND short_strike = EXCLUDED.short_strike
    )
    RETURNING id;
    """
    with conn.cursor() as cursor:
        cursor.execute(insert_query, spread_dict)
        conn.commit()
        print(f"Spread inserted successfully.")

def group_by_exp_date(list_of_contract_touples):
    ''' Takes a list query of option contracts and organizes it into a dictionary by expiration date so you have an expiration date key and a value of lists of touples,
    '''    
    chain_dict = {}
    current_exp = 0
    for cont in list_of_contract_touples:
        if cont[exp] != current_exp:
            current_exp = cont[exp]
        elif cont[exp] == current_exp:
            if current_exp not in chain_dict:
                chain_dict[current_exp] = []
            chain_dict[current_exp].append(cont)
    
    return chain_dict

    def get_atm_strike(contract_chain):
    ticker = contract_chain[0][1]
    response = requests.get(
        QUOTES_URL,
        params={'symbols': ticker },
        headers= HEADERS
    )
    quote_json = response.json()
    price = float(quote_json['quotes']['quote']['last'])

    atm = 0
    current_diff = 20
    for cont in contract_chain:
        diff = abs(float(cont[strike]) - price)
        if diff < current_diff:
            atm = cont[strike]
            current_diff = diff
    return atm

def get_dte(expiration_date_str):
    """
    Returns the number of days from now until a given expiration date using pandas.
    """
    exp_date = pd.to_datetime(expiration_date_str)
    today = pd.Timestamp.today().normalize()  # or just pd.to_datetime('today')
    return (exp_date - today).days