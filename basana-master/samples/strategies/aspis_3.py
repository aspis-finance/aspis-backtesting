from talipp.indicators import SMA, BB

import basana as bs

class Strategy(bs.TradingSignalSource):
    '''scalp / statarb
    buy
    ma short > ma long
    and
    close < lower bb
    sell
    ma_short < ma_long
    '''
    def __init__(self, dispatcher: bs.EventDispatcher, ma_short: float, ma_long: float, bb_period: int, bb_std_dev: float):
        super().__init__(dispatcher)
        self.sma_short = SMA(period=int(ma_short))
        self.sma_long = SMA(period=int(ma_long))
        self.bb = BB(period=int(bb_period), std_dev_mult=float(bb_std_dev))

    async def on_bar_event(self, bar_event: bs.BarEvent):
        # Feed the technical indicator.
        self.bb.add(float(bar_event.bar.close))
        self.sma_short.add(float(bar_event.bar.close))
        self.sma_long.add(float(bar_event.bar.close))

        # Is the indicator ready ?
        if len(self.bb) < 2 or self.bb[-2] is None:
            return

        if bar_event.bar.close < self.bb[-1].lb and self.sma_short[-1] > self.sma_long[-1]:
            self.push(bs.TradingSignal(bar_event.when, bs.Position.LONG, bar_event.bar.pair))
        # Go short when RSI crosses above overbought level.
        elif self.sma_short[-1] < self.sma_long[-1]:
            self.push(bs.TradingSignal(bar_event.when, bs.Position.NEUTRAL, bar_event.bar.pair))

