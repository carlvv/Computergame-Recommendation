import os
import json
import pandas as pd
from bs4 import BeautifulSoup
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import process
from fuzzywuzzy import fuzz

# Step 1: Parsing HTML to CSV
def clean_playtime(playtime):
    playtime = playtime.replace("INSGESAMT GESPIELT", "").strip()
    if "Minuten" in playtime:
        minutes = float(playtime.replace("Minuten", "").strip().replace(",", "."))
        hours = minutes / 60
        playtime = f"{hours:.2f}"
    else:
        playtime = playtime.replace("Stunden", "").strip().replace(",", ".")
        if playtime.count('.') > 1:
            playtime = playtime.replace('.', '', 1)
    return playtime

def parse_steam_library(html_path):
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    games = []
    for game_block in soup.select('div._2-pQFn1G7dZ7667rrakcU3'):
        game_name_tag = game_block.select_one('span.w6q9piMq3gT16oj_lEvpy a')
        game_name = game_name_tag.text.strip() if game_name_tag else "Unknown"
        playtime_tag = game_block.select_one('span._26nl3MClDebGDV7duYjZVn')
        playtime = clean_playtime(playtime_tag.text.strip()) if playtime_tag else "0 Stunden"
        if playtime != "0 Stunden" and playtime != "0.00":
            games.append((game_name, playtime))
    return games

def html_to_csv(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for html_file in os.listdir(input_folder):
        if html_file.endswith(".html"):
            user_name = html_file.split('__')[1].strip()
            csv_file_name = f"{user_name}.csv"
            csv_file_path = os.path.join(output_folder, csv_file_name)
            if os.path.exists(csv_file_path):
                print(f"CSV for {html_file} already exists. Skipping conversion.")
                continue
            html_path = os.path.join(input_folder, html_file)
            print(f"Processing {html_path}...")
            games = parse_steam_library(html_path)
            df = pd.DataFrame(games, columns=['Game', 'PlaytimeInHours'])
            df.to_csv(csv_file_path, index=False)
            print(f"Library extracted and saved to {csv_file_path}")

# Step 2: Matching and Adding Tags and Genres
def create_game_lookup_dicts(game_list_df):
    genre_dict = pd.Series(game_list_df.genre.values, index=game_list_df.name).to_dict()
    tags_dict = pd.Series(game_list_df.tags.values, index=game_list_df.name).to_dict()
    return genre_dict, tags_dict

def match_and_add_tags_genre(extracted_df, game_list_df, genre_dict, tags_dict):
    matched_games = []
    game_names = game_list_df['name'].tolist()
    for index, row in extracted_df.iterrows():
        game_name = str(row['Game']) if pd.notna(row['Game']) else ""
        playtime = row['PlaytimeInHours']
        if game_name:
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
            if os.path.exists(new_csv_file_path):
                print(f"Result file '{new_csv_file_path}' already exists. Skipping...")
                continue
            print(f"Processing '{csv_file_path}'...")
            extracted_df = pd.read_csv(csv_file_path)
            print(f"Extracted data from '{csv_file_path}':\n{extracted_df.head()}")
            matched_df = match_and_add_tags_genre(extracted_df, game_list_df, genre_dict, tags_dict)
            print(f"Matched data:\n{matched_df.head()}")
            matched_df.to_csv(new_csv_file_path, index=False)
            print(f"Processed and saved to '{new_csv_file_path}'")

# Step 3: Combining Libraries
def combine_libraries(libraries_dir, output_file):
    library_files = [f for f in os.listdir(libraries_dir) if f.endswith('_library.csv')]
    if os.path.exists(output_file):
        combined_library = pd.read_csv(output_file)
    else:
        combined_library = pd.DataFrame()
    existing_users = combined_library['Benutzer'].unique() if not combined_library.empty else []
    for file in library_files:
        file_path = os.path.join(libraries_dir, file)
        username = file.split("_library")[0]
        if username in existing_users:
            print(f"Benutzerbibliothek {file} bereits enthalten. Überspringen...")
            continue
        library_df = pd.read_csv(file_path)
        library_df.rename(columns={"Game": "Spiel", "PlaytimeInHours": "SpielzeitInStunden"}, inplace=True)
        library_df["Benutzer"] = username
        combined_library = pd.concat([combined_library, library_df], ignore_index=True)
        print(f"Benutzerbibliothek {file} hinzugefügt.")
    combined_library = combined_library[["Benutzer", "Spiel", "SpielzeitInStunden", "Genre", "Tags"]]
    combined_library.to_csv(output_file, index=False)
    print(f"Die Benutzerbibliotheken wurden erfolgreich kombiniert und als {output_file} gespeichert.")

# Step 4: Creating User Profiles
def safe_split(data, delimiter=', '):
    if isinstance(data, str):
        return data.split(delimiter)
    return []

def safe_eval(data):
    if isinstance(data, str) and data.startswith("{") and data.endswith("}"):
        return eval(data)
    return {}

def create_user_profiles(combined_library_path, user_profiles_folder):
    combined_library = pd.read_csv(combined_library_path)
    combined_library.drop_duplicates(inplace=True)
    if not os.path.exists(user_profiles_folder):
        os.makedirs(user_profiles_folder)
    user_profiles = {}
    for user in combined_library['Benutzer'].unique():
        user_profile_path = os.path.join(user_profiles_folder, f"{user}.json")
        if os.path.exists(user_profile_path):
            continue
        user_data = combined_library[combined_library['Benutzer'] == user]
        profile = {'Genres': {}, 'Tags': {}, 'OwnedGames': []}
        for _, row in user_data.iterrows():
            genres = safe_split(row['Genre'])
            tags = safe_eval(row['Tags'])
            profile['OwnedGames'].append(row['Spiel'])
            for genre in genres:
                if genre not in profile['Genres']:
                    profile['Genres'][genre] = 0
                profile['Genres'][genre] += row['SpielzeitInStunden']
            for tag, count in tags.items():
                if tag not in profile['Tags']:
                    profile['Tags'][tag] = 0
                profile['Tags'][tag] += count
        user_profiles[user] = profile
        with open(user_profile_path, 'w') as profile_file:
            json.dump(profile, profile_file, indent=4)
    print("Benutzerprofile wurden erfolgreich erstellt und gespeichert.")

def main():
    # Step 1: Parse HTML to CSV
    html_input_folder = "libraryHtmls"
    csv_output_folder = "libraryCSVs"
    html_to_csv(html_input_folder, csv_output_folder)

    # Step 2: Match and Add Tags and Genres
    game_list_df = pd.read_csv('steam_games_final_combined_filtered.csv')
    genre_dict, tags_dict = create_game_lookup_dicts(game_list_df)
    library_output_folder = "libraryFinished"
    process_csv_files(csv_output_folder, library_output_folder, game_list_df, genre_dict, tags_dict)

    # Step 3: Combine Libraries
    combined_library_path = "./combined_libraries.csv"
    combine_libraries(library_output_folder, combined_library_path)

    # Step 4: Create User Profiles
    user_profiles_folder = "./userProfiles"
    create_user_profiles(combined_library_path, user_profiles_folder)

if __name__ == "__main__":
    main()
