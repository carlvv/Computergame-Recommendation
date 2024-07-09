import os
import pandas as pd
from fuzzywuzzy import process
from fuzzywuzzy import fuzz

def create_game_lookup_dicts(game_list_df):
    # Create dictionaries for quick lookup
    genre_dict = pd.Series(game_list_df.genre.values, index=game_list_df.name).to_dict()
    tags_dict = pd.Series(game_list_df.tags.values, index=game_list_df.name).to_dict()
    return genre_dict, tags_dict

def match_and_add_tags_genre(extracted_df, game_list_df, genre_dict, tags_dict):
    matched_games = []
    game_names = game_list_df['name'].tolist()

    for index, row in extracted_df.iterrows():
        game_name = str(row['Game']) if pd.notna(row['Game']) else ""  # Ensure game_name is a string
        playtime = row['PlaytimeInHours']
        
        # Only proceed if the game name is not empty
        if game_name:
            # Find the best match for the game name in the game list
            best_match = process.extractOne(game_name, game_names, scorer=fuzz.token_sort_ratio)
            if best_match:
                matched_game = best_match[0]
                genre = genre_dict.get(matched_game, None)
                tags = tags_dict.get(matched_game, None)
                matched_games.append([game_name, playtime, genre, tags])
            else:
                matched_games.append([game_name, playtime, None, None])
        else:
            matched_games.append([game_name, playtime, None, None])

    # Create a new DataFrame with the matched games and additional columns
    matched_df = pd.DataFrame(matched_games, columns=['Game', 'PlaytimeInHours', 'Genre', 'Tags'])
    return matched_df

def process_csv_files(input_folder, output_folder, game_list_df, genre_dict, tags_dict):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for csv_file in os.listdir(input_folder):
        if csv_file.endswith(".csv"):
            csv_file_path = os.path.join(input_folder, csv_file)
            new_csv_file_name = f"{csv_file.replace('.csv', '')}_library.csv"
            new_csv_file_path = os.path.join(output_folder, new_csv_file_name)

            # Check if the result file already exists
            if os.path.exists(new_csv_file_path):
                print(f"Result file '{new_csv_file_path}' already exists. Skipping...")
                continue

            print(f"Processing '{csv_file_path}'...")

            extracted_df = pd.read_csv(csv_file_path)
            print(f"Extracted data from '{csv_file_path}':\n{extracted_df.head()}")

            # Match and add tags and genres
            matched_df = match_and_add_tags_genre(extracted_df, game_list_df, genre_dict, tags_dict)
            print(f"Matched data:\n{matched_df.head()}")

            # Save the result to a new CSV file
            matched_df.to_csv(new_csv_file_path, index=False)
            print(f"Processed and saved to '{new_csv_file_path}'")

def main():
    input_folder = "libraryCSVs"
    output_folder = "libraryFinished"
    
    # Load the existing game list with tags and genres
    game_list_df = pd.read_csv('steam_games_final_combined_filtered.csv')
    print("Loaded game list with tags and genres")

    # Create lookup dictionaries for genres and tags
    genre_dict, tags_dict = create_game_lookup_dicts(game_list_df)

    # Process each CSV in the input folder
    process_csv_files(input_folder, output_folder, game_list_df, genre_dict, tags_dict)

if __name__ == "__main__":
    main()
