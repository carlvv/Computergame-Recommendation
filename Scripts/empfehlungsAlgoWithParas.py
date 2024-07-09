import os
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Parameters
USER_PROFILE_FILENAME = "Carlos.json"  # profile name
NUM_RECOMMENDATIONS = 15
POPULARITY_FILTER = 'popular'  # Options: 'all', 'popular', 'niche'
POPULAR_THRESHOLD = 1000000  # Number of owners to classify as popular
REVIEW_RATIO_THRESHOLD = 0.85  # Minimum positive review ratio required
LIBRARY_FOLDER = "./userProfiles"
GAME_CATALOG_PATH = "./game_catalog_extended.csv"
COMBINED_LIBRARY_PATH = "./combined_libraries.csv"

# Load the game catalog
game_catalog = pd.read_csv(GAME_CATALOG_PATH)

# Convert 'owners' to a numerical value
def convert_owners_to_numeric(owners_str):
    try:
        if '..' in owners_str:
            return int(owners_str.split('..')[1].strip().replace(',', ''))
        return int(owners_str.replace(',', ''))
    except:
        return 0

game_catalog['owners'] = game_catalog['owners'].apply(convert_owners_to_numeric)

# Function to calculate cosine similarity
def calculate_similarity(profile_tags, game_tags):
    profile_vector = []
    game_vector = []
    
    # Collect all unique tags in both sets
    all_tags = list(set(profile_tags.keys()).union(set(game_tags.keys())))
    
    # Create vectors
    for tag in all_tags:
        profile_vector.append(profile_tags.get(tag, 0))
        game_vector.append(game_tags.get(tag, 0))
    
    # Calculate cosine similarity
    return cosine_similarity([profile_vector], [game_vector])[0][0]

# Function to perform collaborative filtering and determine cluster
def collaborative_filtering(user_profile_name, combined_library):
    # Load user profile
    user_profile_path = os.path.join(LIBRARY_FOLDER, f"{user_profile_name}.json")
    with open(user_profile_path, 'r') as profile_file:
        user_profile = json.load(profile_file)
    
    # Determine the most played genre for each user
    user_genres = combined_library.groupby('Benutzer')['Genre'].apply(lambda x: ','.join(x.dropna())).reset_index()
    
    def get_top_genre(genres_dict):
        return max(genres_dict, key=genres_dict.get)
    
    user_genres['Top1'] = user_genres['Benutzer'].apply(lambda user: get_top_genre(user_profile['Genres']))
    
    #print("Top genres for users:")
    #print(user_genres.head())
    
    combined_library = combined_library.merge(user_genres[['Benutzer', 'Top1']], on='Benutzer', how='left')
    
    # Create clusters based on the top genre
    primary_genres = user_genres['Top1'].unique()
    genre_clusters = {genre: idx for idx, genre in enumerate(primary_genres)}
    
    combined_library['Cluster'] = combined_library['Top1'].map(genre_clusters)
    
    return combined_library, genre_clusters

# Generate recommendations
def recommend_games(user_profile_path, game_catalog, combined_library, num_recommendations=NUM_RECOMMENDATIONS, popularity_filter=POPULARITY_FILTER, review_ratio_threshold=REVIEW_RATIO_THRESHOLD):
    with open(user_profile_path, 'r') as profile_file:
        user_profile = json.load(profile_file)
    
    recommendations = []
    total_games = 0
    skipped_games = 0
    
    owned_games = set(game[0] for game in user_profile.get('OwnedGames', []))
    
    for _, game in game_catalog.iterrows():
        total_games += 1
        if game['name'] in owned_games:
            continue
        try:
            game_tags = eval(game['tags'])  # Convert the string back to a dictionary
            if not isinstance(game_tags, dict):
                raise ValueError("Game tags is not a dictionary.")
        except Exception as e:
            skipped_games += 1
            continue
        
        similarity = calculate_similarity(user_profile['Tags'], game_tags)
        positive_ratio = game['positive'] / (game['positive'] + game['negative']) if (game['positive'] + game['negative']) > 0 else 0
        
        # Apply review ratio filter
        if positive_ratio < review_ratio_threshold:
            continue
        
        recommendations.append((game['name'], similarity, game['owners'], game['genre'], positive_ratio))
    
    # Sort the recommendations by similarity
    recommendations.sort(key=lambda x: x[1], reverse=True)
    
    # Apply popularity filter
    if popularity_filter == 'popular':
        recommendations = [rec for rec in recommendations if rec[2] > POPULAR_THRESHOLD]
    elif popularity_filter == 'niche':
        recommendations = [rec for rec in recommendations if rec[2] < POPULAR_THRESHOLD]
    
    # Extract user profile name from path
    user_profile_name = os.path.splitext(os.path.basename(user_profile_path))[0]
    
    # Collaborative filtering recommendations
    combined_library, genre_clusters = collaborative_filtering(user_profile_name, combined_library)
    
    user_cluster = combined_library[combined_library['Benutzer'] == user_profile_name]['Cluster'].iloc[0]
    
    cluster_recommendations = combined_library[combined_library['Cluster'] == user_cluster]
    
    cluster_genre = combined_library[combined_library['Benutzer'] == user_profile_name]['Top1'].iloc[0]
    
    cluster_recommendations = cluster_recommendations[~cluster_recommendations['Spiel'].isin(owned_games)]
    
    combined_recommendations = recommendations[:num_recommendations] + list(cluster_recommendations['Spiel'].unique())
    
    print(f"Total games processed: {total_games}")
    print(f"Games skipped due to invalid tags: {skipped_games}")
    
    return combined_recommendations[:num_recommendations], cluster_genre

# Directory containing user profiles
user_profiles_folder = LIBRARY_FOLDER
profiles = os.listdir(user_profiles_folder)

# Load combined library
combined_library = pd.read_csv(COMBINED_LIBRARY_PATH)

# Use an existing profile
user_profile_path = os.path.join(user_profiles_folder, USER_PROFILE_FILENAME)

if os.path.isfile(user_profile_path):
    print(f"Analyzing user profile: {os.path.splitext(os.path.basename(user_profile_path))[0]}")
    recommendations, cluster_genre = recommend_games(user_profile_path, game_catalog, combined_library, NUM_RECOMMENDATIONS, POPULARITY_FILTER, REVIEW_RATIO_THRESHOLD)
    
    print("Recommended Games:")
    print(f"{'Game Name':<50} {'Similarity':<15} {'Owners':<15} {'Pos. Review Ratio':<20} {'Genre':<15}")
    print("-" * 100)

    for game in recommendations:
        if isinstance(game, tuple):
            print(f"{game[0]:<50} {game[1]:<15.2f} {game[2]:<15} {game[4]:<20.2f} {game[3]}")
        else:
            print(f"{game:<40}")
    
    print(f"\nUser {os.path.splitext(os.path.basename(user_profile_path))[0]} is classified in cluster: {cluster_genre}")
else:
    print(f"User profile {user_profile_path} does not exist.")
