from talipp.indicators import RSI, SMA

import basana as bs

class Strategy(bs.TradingSignalSource):
    '''trend following
    buy
    ma short > ma long
    and
    rsi < 30
    sell
    ma_short < ma_long
    and
    rsi > 30'''
    def __init__(self, dispatcher: bs.EventDispatcher, rsi_period: int, ma_short: float, ma_long: float, rsi_threshold: int):
        super().__init__(dispatcher)
        self.rsi = RSI(period=int(rsi_period)) #rsi period 7
        self.sma_short = SMA(period=int(ma_short))
        self.sma_long = SMA(period=int(ma_long))
        self.rsi_threshold = int(rsi_threshold)

    async def on_bar_event(self, bar_event: bs.BarEvent):
        # Feed the technical indicator.
        self.rsi.add(float(bar_event.bar.close))
        self.sma_short.add(float(bar_event.bar.close))
        self.sma_long.add(float(bar_event.bar.close))

        # Is the indicator ready ?
        if len(self.rsi) < 2 or self.rsi[-2] is None:
            return

        # Go long when RSI crosses below oversold level.
        #and price > sma * 0.99
        if self.rsi[-1] < self.rsi_threshold and self.sma_short[-1] > self.sma_long[-1]:
            self.push(bs.TradingSignal(bar_event.when, bs.Position.LONG, bar_event.bar.pair))
        # Go short when RSI crosses above overbought level.
        elif self.rsi[-1] > self.rsi_threshold and self.sma_short[-1] < self.sma_long[-1]:
            self.push(bs.TradingSignal(bar_event.when, bs.Position.NEUTRAL, bar_event.bar.pair))
