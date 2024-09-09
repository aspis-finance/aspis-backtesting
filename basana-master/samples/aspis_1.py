from decimal import Decimal
import asyncio
import logging

from basana.backtesting import charts
from basana.external.bitstamp import csv
import basana as bs
import basana.backtesting.exchange as backtesting_exchange

from samples.backtesting import position_manager
from samples.strategies import aspis_1 as rsi

import os

async def backtest(name, symbol, stop_loss, timeframe, initial_capital, sizing, filename, oversold_level, overbought_level):
    '''returns
    name, symbol, stop_loss, timeframe, sizing, filename, parameter_list
    profit, sharpe, max_drawdown'''
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    event_dispatcher = bs.backtesting_dispatcher()
    pair = bs.Pair(symbol, "USD")
    exchange = backtesting_exchange.Exchange(
        event_dispatcher,
        initial_balances={symbol: Decimal(0), "USD": Decimal(initial_capital)}
    )
    exchange.set_symbol_precision(pair.base_symbol, 8)
    exchange.set_symbol_precision(pair.quote_symbol, 2)

    # Connect the strategy to the bar events from the exchange.
    strategy = rsi.Strategy(event_dispatcher, 7, oversold_level, overbought_level)
    exchange.subscribe_to_bar_events(pair, strategy.on_bar_event)

    # Connect the position manager to the strategy signals and to bar events. Borrowing is disabled in this example.
    position_mgr = position_manager.PositionManager(
        exchange, position_amount=Decimal(sizing), quote_symbol=pair.quote_symbol, stop_loss_pct=Decimal(stop_loss),
        borrowing_disabled=True
    )
    strategy.subscribe_to_trading_signals(position_mgr.on_trading_signal)
    exchange.subscribe_to_bar_events(pair, position_mgr.on_bar_event)

    path = 'data' + os.sep + filename
    # Load bars from the CSV file.
    exchange.add_bar_source(csv.BarSource(pair, path, "1d"))

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

    profit, sharpe, mdd = position_mgr.history.run()
    
    chart.show()

    result = {
        'name': name, 
        'symbol':symbol, 
        'stop_loss': stop_loss, 
        'timeframe': timeframe,
        'initial_capital': initial_capital, 
        'sizing':sizing, 
        'filename': filename, 
        'oversold_level': oversold_level,
        'overbought_level': overbought_level,
        'profit': Decimal(round(profit, 2)),
        'sharpe': Decimal(round(sharpe, 2)),
        'max_drawdown': Decimal(round(mdd, 2))
            }

    return result     
