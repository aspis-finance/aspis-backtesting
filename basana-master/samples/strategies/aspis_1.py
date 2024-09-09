from talipp.indicators import RSI, SMA

import basana as bs


class Strategy(bs.TradingSignalSource):
    def __init__(self, dispatcher: bs.EventDispatcher, period: int, oversold_level: float, overbought_level: float):
        super().__init__(dispatcher)
        self._oversold_level = oversold_level
        self._overbought_level = overbought_level
        self.rsi = RSI(period=period)
        self.sma = SMA(period=80)

    async def on_bar_event(self, bar_event: bs.BarEvent):
        # Feed the technical indicator.
        self.rsi.add(float(bar_event.bar.close))
        self.sma.add(float(bar_event.bar.close))

        # Is the indicator ready ?
        if len(self.rsi) < 2 or self.rsi[-2] is None:
            return

        # Go long when RSI crosses below oversold level.
        #and price > sma * 0.99
        if self.rsi[-1] < self._oversold_level and bar_event.bar.close > self.sma[-1] * 1.01:
            self.push(bs.TradingSignal(bar_event.when, bs.Position.LONG, bar_event.bar.pair))
        # Go short when RSI crosses above overbought level.
        elif self.rsi[-1] > self._overbought_level:
            self.push(bs.TradingSignal(bar_event.when, bs.Position.NEUTRAL, bar_event.bar.pair))
