ACCESS_TOKEN= 'V2cMfR4LpGPXvAzGYSm7Z15Yy2DW'
PAPER_ACCOUNT_TOKEN = "3XcxpEAbjSMZZXzg0xi7PTVQ8TYT"

ACCOUNT_ID = '6YA43879'
PAPER_ACCOUNT_ID ="VA43419183"
MD_TOKEN = 'aTl6R2IwODl2TjBlQnBHbFNMaUhiWFlVVHJVQU5yM2NUaENuNnpya3EtMD0'
MD_TOKEN1 = 'm43RnpzZWVYeFhwaHVnRll1cUtzOGFwOUlhVkVVekNSTThSc2hnbE5kND0'
BASE_URL = 'https://api.tradier.com'
PAPER_URL = "https://sandbox.tradier.com"

HEADERS = {'Authorization': 'Bearer {}'.format(ACCESS_TOKEN), 'Accept': 'application/json'}
PPHEADERS= {"Authorization": 'Bearer {}'.format(PAPER_ACCOUNT_TOKEN), 'Accept': 'application/json'}

MD_HEADER =  {'Accept': 'application/json','Authorization': f'Bearer {MD_TOKEN}'}

OPTIONS_URL = '{}/v1/markets/options/chains'.format(BASE_URL)
HISTORY_URL = '{}/v1/markets/history'.format(BASE_URL)
EXPIRATION_URL = '{}/v1/markets/options/expirations'.format(BASE_URL)
MD_HISTORIC_URL = 'https://api.marketdata.app/v1/stocks/candles/'

PAPER_ORDER_URL = 'https://sandbox.tradier.com/v1/accounts/{}/orders'.format(PAPER_ACCOUNT_ID)
ORDER_URL = '{}/v1/accounts/{}/orders'.format(BASE_URL, ACCOUNT_ID)

jwkey = "asodfgaiosfgasnfhasilfhqwieugr2390487"

