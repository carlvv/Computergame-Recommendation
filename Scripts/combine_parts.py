import pandas as pd
import os

def load_existing_parts(folder_name):
    existing_files = [f for f in os.listdir(folder_name) if f.endswith('.csv')]
    all_game_details = []
    
    for file in existing_files:
        print(f"Loading {file}...")
        file_path = os.path.join(folder_name, file)
        part_data = pd.read_csv(file_path)
        all_game_details.append(part_data)
        
    if all_game_details:
        combined_df = pd.concat(all_game_details, ignore_index=True)
        print(f"Loaded {len(combined_df)} records from {len(existing_files)} parts.")
        return combined_df
    else:
        print("No parts found in the folder.")
        return pd.DataFrame()

def check_missing_games(df, combined_df):
    combined_appids = set(combined_df['appid'].tolist())
    original_appids = set(df['appid'].tolist())
    
    missing_appids = original_appids - combined_appids
    
    print(f"Total games in steam_games.csv: {len(original_appids)}")
    print(f"Total games in parts: {len(combined_appids)}")
    print(f"Missing games: {len(missing_appids)}")
    
    return missing_appids

def save_combined_csv(combined_df, output_file):
    combined_df.to_csv(output_file, index=False)
    print(f"Combined dataset saved to {output_file}")

def main():
    # Read the original CSV file to get the appids
    df = pd.read_csv('steam_games.csv')
    
    folder_name = 'separateData'
    combined_df = load_existing_parts(folder_name)
    
    if not combined_df.empty:
        missing_appids = check_missing_games(df, combined_df)
        
        if not missing_appids:
            save_combined_csv(combined_df, 'steam_games_final_combined.csv')
        else:
            print("Some games are missing in the parts. Please ensure all parts are downloaded.")
    else:
        print("No data to combine. Please ensure parts are available in the folder.")

if __name__ == "__main__":
    main()
