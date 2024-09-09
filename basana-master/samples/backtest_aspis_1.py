from decimal import Decimal
import asyncio
import logging

from basana.backtesting import charts
from basana.external.bitstamp import csv
import basana as bs
import basana.backtesting.exchange as backtesting_exchange

from samples.backtesting import position_manager
from samples.strategies import aspis_1 as rsi


'''

1. find a lot of data. 5 pairs, 5 timeframes, 1k-100k rows
2. parameter optimisation 

- BASANA - no sharpe and other portfolio statistics
- fees?
- position tracking

700$

requirements:
- strategy settings
- portfolio settings (size, etc)

TDL

1. select the lib for the backtest +
2. add features to the backtest lib +
3. download historical data +
4. preprocess data +
5. backtest 3 strategies 
6. hyperparameter optimization

- position storage
- calc max drawdown and sharpe ratio
- visuilization

stop loss? 0.025 +++
short? +

parameters:
- market
- stop loss
- strategy RSI / MA / etc
- timeframe
- fees?
- sizing


- create parameter sets +
- create a single backtest class +
- create mass backtest class +

- strategy
- backtest
- mass backtest

'''

filename = "AVAXUSDT4H.csv"

symbol = "AVAX"

async def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    event_dispatcher = bs.backtesting_dispatcher()
    pair = bs.Pair(symbol, "USD")
    exchange = backtesting_exchange.Exchange(
        event_dispatcher,
        initial_balances={symbol: Decimal(0), "USD": Decimal(10000)}
    )
    exchange.set_symbol_precision(pair.base_symbol, 8)
    exchange.set_symbol_precision(pair.quote_symbol, 2)

    # Connect the strategy to the bar events from the exchange.
    oversold_level = 30
    overbought_level = 75
    strategy = rsi.Strategy(event_dispatcher, 7, oversold_level, overbought_level)
    exchange.subscribe_to_bar_events(pair, strategy.on_bar_event)

    # Connect the position manager to the strategy signals and to bar events. Borrowing is disabled in this example.
    position_mgr = position_manager.PositionManager(
        exchange, position_amount=Decimal(2000), quote_symbol=pair.quote_symbol, stop_loss_pct=Decimal(5),
        borrowing_disabled=True
    )
    strategy.subscribe_to_trading_signals(position_mgr.on_trading_signal)
    exchange.subscribe_to_bar_events(pair, position_mgr.on_bar_event)

    # Load bars from the CSV file.
    exchange.add_bar_source(csv.BarSource(pair, filename, "1d"))

    # Setup chart.
    chart = charts.LineCharts(exchange)
    chart.add_pair(pair)
    chart.add_portfolio_value(pair.quote_symbol)
    #chart.add_custom("RSI", "RSI", charts.DataPointFromSequence(strategy.rsi))
    #chart.add_custom("SMA", "SMA", charts.DataPointFromSequence(strategy.sma))
    #chart.add_custom("RSI", "Overbought", lambda _: overbought_level)
    #chart.add_custom("RSI", "Oversold", lambda _: oversold_level)

    # Run the backtest.
    await event_dispatcher.run()

    # Log balances.
    balances = await exchange.get_balances()
    for currency, balance in balances.items():
        logging.info("%s balance: %s", currency, balance.available)

    #print(f'history; {position_mgr.history.history}')

    position_mgr.history.run() #!!!!!!!!!!!!!!!!!!!!!!!!
    #print(f'{position_mgr.history.df}')

    chart.show()        

if __name__ == "__main__":
    asyncio.run(main())
