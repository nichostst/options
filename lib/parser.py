import lib._paths as paths
from bs4 import BeautifulSoup

import abc
import requests
import pandas as pd


class YFinData(metaclass=abc.ABCMeta):
    def __init__(self):
        self._base_url = "https://finance.yahoo.com/quote/{}/options"

    @abc.abstractmethod
    def parse(self, ticker, **kwargs):
        pass


class DateOptionParser(YFinData):
    def __init__(self):
        super().__init__()

    def parse(self, ticker, **kwargs):
        url = self._base_url.format(ticker)
        req = requests.get(url)
        soup = BeautifulSoup(req.text, "html.parser")
        date_selector = soup.find_all("select")[0]
        opts = date_selector.find_all("option")
        opts = {opt['value']: opt.text for opt in opts}
        return opts


class OptionPriceParser(YFinData):
    def _init__(self):
        super().__init__()

    @staticmethod
    def _parse_table(table):
        '''
        Parse table element
        '''
        entries = table.find_all("tr")[1:]

        fields = ['name', 'last_trade', 'strike', 'last_price', 'bid',
                  'ask', 'change', 'pct_change', 'volume', 'open_interest',
                  'implied_vol']
        num_fields = fields[2:]

        def clean_num(x):
            '''
            Clean numeric strings for float parsing
            '''
            return x.replace('%', '').replace(',', '')

        df = []
        for entry in entries:
            dat = entry.find_all("td", text=True)
            data = {i: clean_num(d.get_text()) for i, d in zip(fields, dat)}
            df.append(data)

        df = pd.DataFrame(df)
        df['last_trade'] = pd.to_datetime(df['last_trade'])
        df['last_trade'] = df['last_trade'].dt.tz_localize('EST')
        df[num_fields] = df[num_fields].replace('-', '0').astype(float)
        return df

    def parse(self, ticker, **kwargs):
        t = kwargs.get('time')
        url = self._base_url.format(ticker) + f"?time={t}"
        req = requests.get(url)
        soup = BeautifulSoup(req.text, "html.parser")

        # Get underlying price
        f = filter(lambda x: x.get('data-reactid') == '32',
                   soup.find_all("span"))
        price = float(list(f)[0].text)

        # Get option prices
        call_table, put_table = soup.find_all("table")
        calls = OptionPriceParser._parse_table(call_table)
        puts = OptionPriceParser._parse_table(put_table)
        return (
            calls.assign(underlying=price, ticker=ticker),
            puts.assign(underlying=price, ticker=ticker)
        )


if __name__ == '__main__':
    print(paths.paths)
