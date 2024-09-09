from decimal import Decimal
import asyncio
from itertools import product
import matplotlib.pyplot as plt
import pandas as pd
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import os

from samples.aspis_2 import backtest as backtest_function

strategy_name = '_aspis_2' #input strat name to load configs

class MassBacktest:
    def __init__(self, backtest_function):
        self.backtest_function = backtest_function
        self.results = []

    async def run(self, parameter_sets):
        cpu_count = multiprocessing.cpu_count() - 4
        print(f"Running on {cpu_count} CPU cores")

        with ProcessPoolExecutor(max_workers=cpu_count) as executor:
            futures = []
            for params in parameter_sets:
                future = executor.submit(self.run_single_sync, params)
                futures.append((future, params))  # Store both future and params
        
            for future, params in futures:
                result = future.result()
                if result is not None:
                    self.results.append({**params, **result})
                else:
                    print(f"Warning: backtest returned None for params: {params}")
   
    def run_single_sync(self, params):
        return asyncio.run(backtest_function(**params))


    def print_results(self):
        for i, result in enumerate(self.results):
            print(f"Backtest {i + 1}:")
            print(result)
            print("-" * 30)

    def get_best_result(self, key='profit'):
        return max(self.results, key=lambda x: x[key])
    
    def visualize_results(self):
        if not self.results:
            print("No results to visualize.")
            return

        # Convert results to DataFrame
        df = pd.DataFrame(self.results)

        df['sharpe'] = pd.to_numeric(df['sharpe'], errors='coerce')
        df = df.dropna(subset=['sharpe'])
        df['profit'] = pd.to_numeric(df['profit'], errors='coerce')
        df['max_drawdown'] = pd.to_numeric(df['max_drawdown'], errors='coerce')

        # Create scatter plot matrix
        fig, axs = plt.subplots(3, 3, figsize=(15, 15))
        fig.suptitle('Backtest Results Visualization', fontsize=16)

        params = ['profit', 'sharpe', 'max_drawdown']
        for i, param1 in enumerate(params):
            for j, param2 in enumerate(params):
                ax = axs[i, j]
                if i != j:
                    ax.scatter(df[param2], df[param1])
                    ax.set_xlabel(param2)
                    ax.set_ylabel(param1)
                else:
                    ax.hist(df[param1], bins=20)
                    ax.set_xlabel(param1)
                    ax.set_ylabel('Frequency')

        plt.tight_layout()

        # Create table of top 10 results
        top_10 = df.nlargest(20, 'sharpe')
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axis('off')
        ax.table(cellText=top_10[['symbol', 'timeframe', 'profit', 'sharpe', 'max_drawdown', 'stop_loss', 'sizing', 'rsi_threshold', 'ma_short', 'ma_long']].values,
                 colLabels=['Symbol', 'Timeframe', 'Profit', 'Sharpe', 'Max Drawdown', 'Stop Loss', 'Sizing', 'RSI threshold', 'MA short', 'MA long'],
                 cellLoc='center', loc='center')
        
        ax.set_title('Top 20 Results (Sorted by Sharpe Ratio)')

        plt.show()

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def decimal_decoder(dict_item):
    for key, value in dict_item.items():
        if isinstance(value, list):
            dict_item[key] = [Decimal(str(item)) if isinstance(item, (int, float)) else item for item in value]
        elif isinstance(value, (int, float)):
            dict_item[key] = Decimal(str(value))
    return dict_item

def generate_parameter_sets():
    #config_dir = Path('config')
    config_dir = 'config'

    # Load data from JSON files
    symbol_data = load_json(config_dir + os.sep + 'symbol_data' + strategy_name + '.json')
    constant_params = load_json(config_dir + os.sep + 'constant_params' + strategy_name + '.json')
    varying_params = load_json(config_dir + os.sep + 'varying_params' + strategy_name + '.json')

    # Convert numeric values to Decimal
    constant_params = decimal_decoder(constant_params)
    varying_params = decimal_decoder(varying_params)

    # Generate all combinations of varying parameters
    varying_combinations = list(product(*varying_params.values()))
    print(f"Number of varying combinations: {len(varying_combinations)}")

    parameter_sets = []
    for symbol_info in symbol_data:
        print(f"Processing symbol: {symbol_info['symbol']}")
        for combo in varying_combinations:
            params = {
                **constant_params,
                **symbol_info,
                **dict(zip(varying_params.keys(), combo))
            }
            parameter_sets.append(params)

    print(f"Total number of parameter sets: {len(parameter_sets)}")
    return parameter_sets


# Generate the parameter sets
parameter_sets = generate_parameter_sets()

async def main():

    # Initialize and run mass backtest
    mass_backtest = MassBacktest(backtest_function)
    results = await mass_backtest.run(parameter_sets)

    # Print all results
    mass_backtest.print_results()

    mass_backtest.visualize_results()

    # Get the best result based on total return
    best_result = mass_backtest.get_best_result()
    print("Best result:", best_result)

    for i in mass_backtest.results:
        print(f'profit: {i["profit"]}, sharpe: {i["sharpe"]}, mdd: {i["max_drawdown"]}')

if __name__ == "__main__":
    asyncio.run(main())