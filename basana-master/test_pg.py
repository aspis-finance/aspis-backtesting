from decimal import Decimal
from itertools import product

def generate_parameter_sets():
    # Symbol-specific parameters
    symbol_data = [
        {'symbol': 'ETH/USDT', 'filename': 'ETHUSDT1H.csv', 'timeframe': '1H'},
        {'symbol': 'BTC/USDT', 'filename': 'BTCUSDT1H.csv', 'timeframe': '1H'}
    ]

    # Constant parameters
    constant_params = {
        'name': 'aspis1',
        'initial_capital': Decimal('10000'),
    }

    # Varying parameters
    varying_params = {
        'stop_loss': [Decimal('2.5')],
        'sizing': [Decimal('2000')],
        'oversold_level': [70, 75],
        'overbought_level': [30, 25],
    }

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

# Example usage:
if __name__ == "__main__":
    params = generate_parameter_sets()
    for i, param_set in enumerate(params, 1):
        print(f"Parameter set {i}:")
        print(param_set)
        print()

    print(f"Total number of parameter sets: {len(params)}")
    
    # Count occurrences of each symbol
    symbol_counts = {}
    for param_set in params:
        symbol = param_set['symbol']
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
    
    print("\nSymbol counts:")
    for symbol, count in symbol_counts.items():
        print(f"{symbol}: {count}")