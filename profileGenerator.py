import os
import pandas as pd
import json

# Einlesen der kombinierten Bibliothek
combined_library_path = "./combined_libraries.csv"
combined_library = pd.read_csv(combined_library_path)

# Entfernen von Duplikaten
combined_library.drop_duplicates(inplace=True)

# Funktion zur Überprüfung und Bereinigung der Genre- und Tag-Daten
def safe_split(data, delimiter=', '):
    if isinstance(data, str):
        return data.split(delimiter)
    return []

def safe_eval(data):
    if isinstance(data, str) and data.startswith("{") and data.endswith("}"):
        return eval(data)
    return {}

# Erstellen des Ordners für Benutzerprofile, falls dieser nicht existiert
user_profiles_folder = "./userProfiles"
if not os.path.exists(user_profiles_folder):
    os.makedirs(user_profiles_folder)

# Erstellen eines Nutzerspielprofils
user_profiles = {}

for user in combined_library['Benutzer'].unique():
    user_profile_path = os.path.join(user_profiles_folder, f"{user}.json")
    
    # Überprüfen, ob das Profil bereits existiert
    if os.path.exists(user_profile_path):
        continue
    
    user_data = combined_library[combined_library['Benutzer'] == user]
    
    # Initialisiere ein leeres Profil
    profile = {'Genres': {}, 'Tags': {}}
    
    for _, row in user_data.iterrows():
        genres = safe_split(row['Genre'])
        tags = safe_eval(row['Tags'])  # Konvertiere den String zurück zu einem Dictionary
        
        for genre in genres:
            if genre not in profile['Genres']:
                profile['Genres'][genre] = 0
            profile['Genres'][genre] += row['SpielzeitInStunden']
        
        for tag, count in tags.items():
            if tag not in profile['Tags']:
                profile['Tags'][tag] = 0
            profile['Tags'][tag] += count
    
    user_profiles[user] = profile

    # Speichern des Profils als JSON-Datei
    with open(user_profile_path, 'w') as profile_file:
        json.dump(profile, profile_file, indent=4)

print("Benutzerprofile wurden erfolgreich erstellt und gespeichert.")
