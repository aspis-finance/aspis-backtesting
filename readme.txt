Tech readme to run backtesting scripts.

General
File structure
Data download
Data preprocessing
Usage guide

General
This project allows to backtest various trading strategies on historical data. Uses basana as backtesting framework.

File structure
Data folder. Contains scripts to download data from data.binance.vision
Preprocessing folder. Copy the data downloaded from binance to this folder, unzip all files. Like this: BTCUSDT/1H/filaname.csv.
Preprocessing/read_data.py - read all csv files from the selected dir, creates a pandas df, saves all data as a single file, e.g. AVAXUSDT1H.csv
Basana. Backtesting lib folder. Edit/create files to test new strategies.
basana-master/data - copy your data files here 
basana-master/samples/strategies - the core trading strategy files
basana-master/samples/ - backtesting file, parses all the arguments into the strategy, runs events, etc.
basana-master/mass_backtest.py - runs many backtests with selected parameters
basana-master/config - mass backtesting settings

Data download

binance public data git:
https://github.com/binance/binance-public-data/tree/master/python

data download command:
python3 download-kline.py -t spot -s ETHUSDT BTCUSDT SOLUSDT -i 4h -skip-daily 1

-t = type of data. spot
-s = markets. ETHUSDT, BTCUSDT, etc
-i = timeframe. 1d, 4h, 1h, 15m, 5m, 1m. 
-skip-daily 1 = dont download a lot of separate files 


Data preprocessing
python3 read_data.py 

Usage guide

1. Select markets and symbols to perform backtests, choose timeframes download data from binance.
Go to aspis_backtesting/data/binance-public-data/python
Run download script in terminal, example: python3 download-kline.py -t spot -s ETHUSDT BTCUSDT -i 4h 1h -skip-daily 1
Your data is being downloaded to: aspis_backtesting/data/binance-public-data/python/data/spot/monthly/klines

2. Copy all data from aspis_backtesting/data/binance-public-data/python/data/spot/monthly/klines to preprocessing folder: aspis_backtesting/preprocessing. 
Unzip all files into the same folders.
Edit aspis_backtesting/preprocessing/read_data.py script(input_file, output_file). This script takes all data files from folder "symbol/timeframe", reads all csv files, transforms timeframes, saves all data into 1 file. Run this script for each symbol/timeframe.

3. Copy preprocessed csv files from aspis_backtesting/preprocessing to aspis_backtesting/basana-master/data. 

4. Go to aspis_backtesting/basana-master, edit mass_backtest_aspis_1.py. This file runs a series of backtests for strategy "aspis_1".
Edit strategy_name, in our example it's '_aspis_1'. This is required to load configs. Line 14.
Go to aspis_backtesting/basana-master/config. Each strategy has 3 configs: constant params(skip), symbol data(edit symbol, filename and timeframe), and varying params(Strategy settings for each strategy. Contains lists of parameters to test all possible combinations of parameters). 

5. OPTIONAL. Edit config files to choose another parameters.

6. OPTIONAL. Edit strategy files in aspis_backtesting/basana-master/samples if needed.
 
7. Go to aspis_backtesting/basana-master, run mass_backtest_aspis_1.py and get the visual representation of backtesting results, sorted by sharpe ratio. 
