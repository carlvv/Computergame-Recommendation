import os
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Laden des Spielkatalogs
game_catalog_path = "./game_catalog.csv"
game_catalog = pd.read_csv(game_catalog_path)

# Print the columns to verify the presence of the 'tags' column
print("Columns in game_catalog:", game_catalog.columns)

# Funktion zur Berechnung der Kosinus-Ähnlichkeit
def calculate_similarity(profile_tags, game_tags):
    profile_vector = []
    game_vector = []
    
    # Alle einzigartigen Tags in beiden Sätzen sammeln
    all_tags = list(set(profile_tags.keys()).union(set(game_tags.keys())))
    
    # Vektoren erstellen
    for tag in all_tags:
        profile_vector.append(profile_tags.get(tag, 0))
        game_vector.append(game_tags.get(tag, 0))
    
    # Kosinus-Ähnlichkeit berechnen
    return cosine_similarity([profile_vector], [game_vector])[0][0]

# Empfehlungen generieren
def recommend_games(user_profile_path, game_catalog, num_recommendations=5):
    with open(user_profile_path, 'r') as profile_file:
        user_profile = json.load(profile_file)
    
    recommendations = []
    total_games = 0
    skipped_games = 0
    
    for _, game in game_catalog.iterrows():
        total_games += 1
        try:
            game_tags = eval(game['tags'])  # Konvertiere den String zurück zu einem Dictionary
            if not isinstance(game_tags, dict):
                raise ValueError("Game tags is not a dictionary.")
        except Exception as e:
            skipped_games += 1
            print(f"Skipping game {game['name']} due to invalid tags: {e}")
            continue
        
        similarity = calculate_similarity(user_profile['Tags'], game_tags)
        recommendations.append((game['name'], similarity))
    
    # Sortiere die Empfehlungen nach Ähnlichkeit
    recommendations.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Total games processed: {total_games}")
    print(f"Games skipped due to invalid tags: {skipped_games}")
    
    return recommendations[:num_recommendations]

# Directory containing user profiles
user_profiles_folder = "./userProfiles"
profiles = os.listdir(user_profiles_folder)

print("Available user profiles:")
for profile in profiles:
    print(profile)

# Use an existing profile
user_profile_filename = "Janes.json"  # Update this to any valid profile name
user_profile_path = os.path.join(user_profiles_folder, user_profile_filename)

if os.path.isfile(user_profile_path):
    recommendations = recommend_games(user_profile_path, game_catalog)
    
    print("Empfohlene Spiele:")
    for game, score in recommendations:
        print(f"{game} (Ähnlichkeit: {score:.2f})")
else:
    print(f"User profile {user_profile_path} does not exist.")
