import requests
from datetime import datetime
from Charts import config
class BrokerConnection:
    def __init__(self, token: str, account_id: str, sandbox: bool = False):
        self.token = token
        self.account_id = account_id
        self.host = "https://sandbox.tradier.com" if sandbox else "https://api.tradier.com"
        self.base_url = f"{self.host}/v1/accounts/{account_id}/orders"
        self.headers = config.HEADERS

    class trade:
        @staticmethod
        def _build_order_payload(class_type, symbol, order_type, duration, legs, price=None, tag=None):
            payload = {
                "class": class_type,
                "symbol": symbol,
                "type": order_type,
                "duration": duration
            }
            if price is not None:
                payload["price"] = str(price)
            if tag:
                payload["tag"] = tag

            for i, leg in enumerate(legs):
                payload[f"side[{i}]"] = leg['side']
                payload[f"quantity[{i}]"] = str(leg['quantity'])
                payload[f"option_symbol[{i}]"] = leg['option_symbol']

            return payload

        class Strategy:
            def __init__(self, broker, symbol, expiration, order_type, duration, price):
                self.broker = broker
                self.symbol = symbol
                self.expiration = expiration
                self.order_type = order_type
                self.duration = duration
                self.price = price
                self.legs = []

            def _send_request(self, preview=False):
                payload = BrokerConnection.trade._build_order_payload(
                    class_type="multileg",
                    symbol=self.symbol,
                    order_type=self.order_type,
                    duration=self.duration,
                    legs=self.legs,
                    price=self.price
                )
                if preview:
                    payload["preview"] = "true"
                response = requests.post(
                    self.broker.base_url,
                    headers=self.broker.headers,
                    data=payload
                )
                return response.json()

            def preview(self):
                return self._send_request(preview=True)

            def execute(self):
                return self._send_request(preview=False)

            def stats(self):
                return {
                    "max_profit": None,
                    "max_loss": None,
                    "breakevens": None,
                    "credit_or_debit": self.price,
                    "dte": (datetime.strptime(self.expiration, "%Y/%m/%d") - datetime.now()).days,
                    "greeks": {
                        "delta": None,
                        "theta": None,
                        "gamma": None
                    },
                    "IV": None,
                    "HV": None
                }

        @staticmethod
        def _occ(sym, exp, strike, typ):
            k = f"{int(strike*1000):08d}"
            return f"{sym}{exp}{'C' if typ == 'call' else 'P'}{k}"

        @staticmethod
        def iron_condor(broker, strikes, width, expiration, price, side='sell', quantity=1):
            short_put, short_call = sorted(strikes)
            long_put = short_put - width
            long_call = short_call + width
            exp = expiration.replace("/","")

            buy_leg = "buy_to_open" if side == 'sell' else "sell_to_open"
            sell_leg = "sell_to_open" if side == 'sell' else "buy_to_open"

            obj = BrokerConnection.trade.Strategy(
                broker, broker.symbol, expiration, order_type="credit", duration="day", price=price
            )
            obj.legs = [
                {"side": sell_leg, "quantity": quantity, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, short_put, 'put')},
                {"side": buy_leg, "quantity": quantity, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, long_put, 'put')},
                {"side": sell_leg, "quantity": quantity, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, short_call, 'call')},
                {"side": buy_leg, "quantity": quantity, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, long_call, 'call')},
            ]
            return obj

        @staticmethod
        def butterfly(broker, center_strike, width, expiration, price, option_type='call', side='buy', quantity=1):
            lower = center_strike - width
            upper = center_strike + width
            exp = expiration.replace("/","")

            buy_leg = "buy_to_open" if side == 'buy' else "sell_to_open"
            sell_leg = "sell_to_open" if side == 'buy' else "buy_to_open"

            obj = BrokerConnection.trade.Strategy(
                broker, broker.symbol, expiration, order_type="debit", duration="day", price=price
            )
            obj.legs = [
                {"side": buy_leg, "quantity": quantity, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, lower, option_type)},
                {"side": sell_leg, "quantity": quantity * 2, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, center_strike, option_type)},
                {"side": buy_leg, "quantity": quantity, "option_symbol": BrokerConnection.trade._occ(obj.symbol, exp, upper, option_type)},
            ]
            return obj
