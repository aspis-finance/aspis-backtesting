import os
import pandas as pd

import matplotlib.pyplot as plt

input_file = '/UNIUSDT/4h'
output_file = 'UNIUSDT4H.csv'

def load_data_from_folder(folder_path):
    # Initialize an empty list to hold the dataframes
    df_list = []

    # Loop through all files in the folder
    for file_name in os.listdir(folder_path):
        # Check if the file is a CSV
        if file_name.endswith('.csv'):
            # Construct the full file path
            file_path = os.path.join(folder_path, file_name)

            # Read the CSV file into a dataframe
            df = pd.read_csv(file_path, names=['datetime', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'])
            
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')

            df['datetime'] = df['datetime'].dt.floor('S')

            df = df.iloc[::-1].reset_index(drop=True)

            # Append the dataframe to the list
            df_list.append(df)

    # Concatenate all dataframes in the list into a single dataframe
    df = pd.concat(df_list, ignore_index=True)

    df_sorted = df.sort_values(by='datetime')

    # Reset the index if needed
    df_sorted = df_sorted.reset_index(drop=True)

    return df_sorted

# Example usage

current_folder = os.getcwd()

folder_path = current_folder + input_file  # Replace with the path to your folder
data = load_data_from_folder(folder_path)

# Now `data` contains all the combined data from the CSV files
print(data)  # Display the first few rows of the combined dataframe


plt.figure(figsize=(10, 5))  # Optional: set the figure size
plt.plot(data['datetime'], data['high'], label='Close Price', color='blue')
plt.title('Close Price Over Time')
plt.xlabel('Date')
plt.ylabel('Close Price')
plt.legend()
plt.grid(True)
plt.show()

# Save the DataFrame to a CSV file
data.to_csv(output_file, index=False)


