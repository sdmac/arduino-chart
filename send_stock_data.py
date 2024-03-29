#!/usr/local/bin/python3

from datetime import datetime, timedelta
from iexfinance.stocks import get_historical_intraday, get_historical_data
import argparse
import requests
import json
import time

def parse_args():
    parser = argparse.ArgumentParser(description='Send stock data')
    parser.add_argument('--host',
                        metavar='IP|HOSTNAME',
                        dest='host',
                        type=str,
                        required=True,
                        help='the host/IP to send to')
    parser.add_argument('--symbol',
                        metavar='STR',
                        dest='symbol',
                        type=str,
                        required=True,
                        help='the stock symbol')
    parser.add_argument('--date',
                        metavar='YYYY-MM-DD',
                        dest='date',
                        type=str,
                        default='',
                        help='the date')
    parser.add_argument('--interval',
                        metavar='STR',
                        dest='interval',
                        type=str,
                        default='30m',
                        help='the interval')
    parser.add_argument('--token',
                        metavar='STR',
                        dest='token',
                        type=str,
                        required=True,
                        help='the iexfinance token')
    args = parser.parse_args()
    return args

def find_latest_weekday(date):
    if date.isoweekday() > 5:
        return (date - timedelta(date.isoweekday() - 5))
    return date

def find_prev_date(date):
    prev = date - timedelta(1)
    return find_latest_weekday(prev)

def get_data(token, symbol, date):
    return get_historical_intraday(symbol, date, token=token)

def get_initial_data(token, symbol, date):
    close = get_historical_data(symbol, date, close_only=True, token=token)
    dt = str(date.date())
    if dt in close and 'close' in close[dt]:
        return close[dt]['close']
    raise RuntimeError('Cannot determine previous close')

def to_minutes(s):
    num = s[:-1]
    if s.endswith('s'):
        m = int(num)
        return (1 if m < 60 else int(m/60))
    elif s.endswith('m'):
        return int(num)
    elif s.endswith('h'):
        return int(num)*60
    else:
        return 1

def determine_chart_date(args):
    if args.date:
        yr_mt_dy = args.date.split('-')
        if len(yr_mt_dy) != 3:
            raise RuntimeError('Cannot parse date: {}'.format(args.date))
        return datetime(int(yr_mt_dy[0]),
                        int(yr_mt_dy[1]),
                        int(yr_mt_dy[2]))
    else:
        return datetime.today()

def send_data(host, **kwargs):
    if len(kwargs) == 4:
        message = ('{p0},{date},{interval},{symbol}'
                   .format(p0=kwargs['price'],
                           date=kwargs['date'],
                           interval=kwargs['interval'],
                           symbol=kwargs['symbol']))
    elif len(kwargs) == 2:
        message = ('{price},{time}'
                   .format(price=kwargs['price'],
                           time=kwargs['time']))
    print(message)
    #r = requests.get('http://{host}/?m={msg}'.format(host=host, msg=message))
    #print(r.status_code)


args = parse_args()

chart_date = find_latest_weekday(determine_chart_date(args))
prev_date = find_prev_date(chart_date)
interval_mins = to_minutes(args.interval)

init_price = get_initial_data(args.token, args.symbol, prev_date)
send_data( args.host, **{
    'price': init_price,
    'date': str(chart_date.date()),
    'interval': args.interval,
    'symbol': args.symbol
} )

realtime = (chart_date == datetime.today())

data = get_data(args.token, args.symbol, chart_date)

for index in range(0, 390, interval_mins):
    if realtime:
        while len(data) < (index + 1):
            time.sleep(60 * interval_mins)
            data = get_data(args.token, args.symbol, chart_date)
    price = data[index]
    send_data(args.host,
              price=(price['close'] if price['close'] is not None
                     else price['marketClose']),
              time=price['minute'])

exit(0)
