# Basana
#
# Copyright 2022 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from decimal import Decimal
from typing import Dict, Optional
import asyncio
import dataclasses
import datetime
import logging

from basana.core.logs import StructuredMessage
import basana as bs
import basana.backtesting.exchange as backtesting_exchange

import pandas as pd
import numpy as np

@dataclasses.dataclass
class PositionInfo:
    pair: bs.Pair
    initial: Decimal
    initial_avg_price: Decimal
    target: Decimal
    order: backtesting_exchange.OrderInfo

    @property
    def current(self) -> Decimal:
        delta = self.order.amount_filled if self.order.operation == bs.OrderOperation.BUY else -self.order.amount_filled
        return self.initial + delta

    @property
    def avg_price(self) -> Decimal:
        order_fill_price = Decimal(0) if self.order.fill_price is None else self.order.fill_price
        ret = order_fill_price

        if self.initial == 0:
            ret = order_fill_price
        # Transition from long to short, or viceversa, and already on the target side.
        elif self.initial * self.target < 0 and self.current * self.target > 0:
            ret = order_fill_price
        # Rebalancing on the same side.
        elif self.initial * self.target > 0:
            # Reducing the position.
            if self.target > 0 and self.order.operation == bs.OrderOperation.SELL \
                    or self.target < 0 and self.order.operation == bs.OrderOperation.BUY:
                ret = self.initial_avg_price
            # Increasing the position.
            else:
                ret = (abs(self.initial) * self.initial_avg_price + self.order.amount_filled * order_fill_price) \
                    / (abs(self.initial) + self.order.amount_filled)
        return ret

    @property
    def order_open(self) -> bool:
        return self.order.is_open

    @property
    def target_reached(self) -> bool:
        return self.current == self.target

    def calculate_unrealized_pnl_pct(self, bid: Decimal, ask: Decimal) -> Decimal:
        pnl_pct = Decimal(0)
        current = self.current
        avg_price = self.avg_price
        if current and avg_price:
            exit_price = bid if current > 0 else ask
            pnl = (exit_price - avg_price) * current
            pnl_pct = pnl / abs(avg_price * current) * Decimal(100)
        return pnl_pct


class History:
    '''sharpe
    max drawdown
    fees?'''
    def __init__(self) -> None:
        self.history = []
       
    def add(self, value):
        self.history.append(float(value))
   
    def calculate_returns(self, equity_values):
        if len(equity_values) < 2:
            return []
    
        returns = []
        for i in range(1, len(equity_values)):
            prev_equity = equity_values[i-1]
            curr_equity = equity_values[i]
            returns.append((curr_equity - prev_equity) / prev_equity)
    
        return returns

    def calc_sharpe(self, returns, risk_free_rate):
        if len(returns) < 2:
            return 0.0
    
        annualized_return = np.mean(returns) * 252
        annualized_volatility = np.std(returns) * np.sqrt(252)
    
        sharpe = (annualized_return - risk_free_rate) / annualized_volatility
    
        return round(sharpe, 2)
    
    def calculate_max_drawdown(self, equity_values):
        if len(equity_values) < 2:
            return Decimal(0)
        
        peak_value = equity_values[0]
        current_drawdown = Decimal(0)
        max_drawdown = Decimal(0)

        for equity in equity_values:
            if equity > peak_value:
                #peak updated
                peak_value = equity
            
            current_drawdown = (peak_value - equity) / peak_value
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown

            #print(f'debug. peak_value is {peak_value}, current_drawdown is {current_drawdown}, max drawdown is {max_drawdown}')
    
        return max_drawdown
    

    def calc_profit(self):
        profit = self.history[-1] / self.history[0]
        profit_pct = (profit - 1) * 100
        return round(profit_pct, 2)
        
    def run(self):
        profit = self.calc_profit()
        print(f'profit is {profit} %')
        returns = self.calculate_returns(self.history)
        #print(f'returns {returns}')
        sharpe = self.calc_sharpe(returns=returns, risk_free_rate=0)
        print(f'sharpe is {sharpe}')
        mdd = self.calculate_max_drawdown(self.history)
        print(f'max drawdown {mdd:.2%}')

        return profit, sharpe, mdd

class PositionManager:
    # Responsible for managing orders and tracking positions in response to trading signals.
    def __init__(
            self, exchange: backtesting_exchange.Exchange, position_amount: Decimal, quote_symbol: str,
            stop_loss_pct: Decimal, borrowing_disabled: bool = False
    ):
        assert position_amount > 0
        assert stop_loss_pct > 0

        self._exchange = exchange
        self._position_amount = position_amount
        self._quote_symbol = quote_symbol
        self._positions: Dict[bs.Pair, PositionInfo] = {}
        self._stop_loss_pct = stop_loss_pct
        self._borrowing_disabled = borrowing_disabled
        self._last_check_loss: Optional[datetime.datetime] = None

        self.history = History()

        self.last_close = {}

    async def cancel_open_orders(self, pair: bs.Pair):
        open_orders = await self._exchange.get_open_orders(pair)
        await asyncio.gather(*[
            self._exchange.cancel_order(open_order.id)
            for open_order in open_orders
        ])

    async def get_position_info(self, pair: bs.Pair) -> Optional[PositionInfo]:
        pos_info = self._positions.get(pair)
        if pos_info and pos_info.order_open:
            pos_info.order = await self._exchange.get_order_info(pos_info.order.id)
        return pos_info

    async def check_loss(self):
        pairs = [pos_info.pair for pos_info in self._positions.values() if pos_info.current != 0]
        # For every pair get position information along with bid and ask prices.
        coros = [self.get_position_info(pair) for pair in pairs]
        coros.extend(self._exchange.get_bid_ask(pair) for pair in pairs)
        res = await asyncio.gather(*coros)
        midpoint = int(len(res) / 2)
        all_pos_info = res[0:midpoint]
        all_bid_ask = res[midpoint:]

        # Log each position an check PnL.
        for pos_info, (bid, ask) in zip(all_pos_info, all_bid_ask):
            pnl_pct = pos_info.calculate_unrealized_pnl_pct(bid, ask)
            logging.info(StructuredMessage(
                f"Position for {pos_info.pair}", current=pos_info.current, target=pos_info.target,
                avg_price=pos_info.avg_price, pnl_pct=pnl_pct, order_open=pos_info.order_open
            ))
            if pnl_pct <= self._stop_loss_pct * -1:
                logging.info(f"Stop loss for {pos_info.pair}")
                await self.switch_position(pos_info.pair, bs.Position.NEUTRAL, force=True)

    async def switch_position(self, pair: bs.Pair, target_position: bs.Position, force: bool = False):
        current_pos_info = await self.get_position_info(pair)
        # Unless force is set, we can ignore the request if we're already there.
        if not force and any([
                current_pos_info is None and target_position == bs.Position.NEUTRAL,
                (
                    current_pos_info is not None
                    and signed_to_position(current_pos_info.target) == target_position
                    and current_pos_info.target_reached
                )
        ]):
            return

        # Cancel the previous order.
        if current_pos_info and current_pos_info.order_open:
            await self._exchange.cancel_order(current_pos_info.order.id)
            current_pos_info.order = await self._exchange.get_order_info(current_pos_info.order.id)

        (bid, ask), pair_info = await asyncio.gather(
            self._exchange.get_bid_ask(pair),
            self._exchange.get_pair_info(pair),
        )

        # 1. Calculate the target balance.
        # If the target position is neutral, the target balance is 0, otherwise we need to convert
        # self._position_amount, which is expressed in self._quote_symbol units, into base units.
        if target_position == bs.Position.NEUTRAL:
            target = Decimal(0)
        else:
            if pair.quote_symbol == self._quote_symbol:
                target = self._position_amount / ((bid + ask) / 2)
            else:
                quote_bid, quote_ask = await self._exchange.get_bid_ask(bs.Pair(pair.base_symbol, self._quote_symbol))
                target = self._position_amount / ((quote_bid + quote_ask) / 2)

            if target_position == bs.Position.SHORT:
                target *= -1
            target = bs.truncate_decimal(target, pair_info.base_precision)

        # 2. Calculate the difference between the target balance and our current balance.
        current = Decimal(0) if current_pos_info is None else current_pos_info.current
        delta = target - current
        logging.info(StructuredMessage("Switch position", pair=pair, current=current, target=target, delta=delta))
        if delta == 0:
            return

        # 3. Create the order.
        order_size = abs(delta)
        operation = bs.OrderOperation.BUY if delta > 0 else bs.OrderOperation.SELL
        logging.info(StructuredMessage("Creating market order", operation=operation, pair=pair, order_size=order_size))
        created_order = await self._exchange.create_market_order(
            operation, pair, order_size, auto_borrow=True, auto_repay=True
        )
        order = await self._exchange.get_order_info(created_order.id)

        # 4. Keep track of the position.
        initial_avg_price = Decimal(0) if current_pos_info is None else current_pos_info.avg_price
        pos_info = PositionInfo(
            pair=pair, initial=current, initial_avg_price=initial_avg_price, target=target, order=order
        )
        self._positions[pair] = pos_info


        # 5. create stop order

        '''
        last_close = self.last_close[pair]
        stop_loss = round(last_close * Decimal(0.975), 2)
        stop_price = Decimal(stop_loss)

        created_order = await self._exchange.create_stop_order(
            operation, pair, order_size, stop_price=stop_price, auto_borrow=True, auto_repay=True
        )

        order = await self._exchange.get_order_info(created_order.id)
        '''
        #print(f'CHECK STOP LOSS> pair {pair}, last close {last_close}, stop price {stop_price}')

        
        

    async def on_trading_signal(self, trading_signal: bs.TradingSignal):
        pairs = list(trading_signal.get_pairs())
        logging.info(StructuredMessage("Trading signal", pairs=pairs))

        try:
            coros = []
            for pair, target_position in pairs:
                if self._borrowing_disabled and target_position == bs.Position.SHORT:
                    target_position = bs.Position.NEUTRAL
                coros.append(self.switch_position(pair, target_position))
            await asyncio.gather(*coros)
        except Exception as e:
            logging.exception(e)

    async def on_bar_event(self, bar_event: bs.BarEvent):
        bar = bar_event.bar
        logging.info(StructuredMessage(bar.pair, close=bar.close))
        if self._last_check_loss is None or self._last_check_loss < bar_event.when:
            self._last_check_loss = bar_event.when
            await self.check_loss()

        ''' add positions / balances handling here'''
        self.balance_history(bar_event)
        
        #save the last prices to calc stop losses
        self.last_close[bar_event.bar.pair] = bar_event.bar.close
        
    def balance_history(self, bar_event):
        #print(f'>>>>>>>>>>>>>>>>>>>>>>>> BALANCES {self._exchange._balances.balances}')
        #print(f'999999999999999 {self._positions}')
        #calc total value
        #print(f'{bar_event.bar.close}')
        total = 0
        for key, value in self._exchange._balances.balances.items():

            usd_value = 0

            if key == 'USD':
                usd_value = value
            else:
                usd_value = value * bar_event.bar.close

            #print(f'debug, key is {key}, value is {value}, usd_value is {usd_value}')

            total += usd_value

        #print(f'total {total}')

        self.history.add(total)

        

        


def signed_to_position(signed):
    if signed > 0:
        return bs.Position.LONG
    elif signed < 0:
        return bs.Position.SHORT
    else:
        return bs.Position.NEUTRAL
