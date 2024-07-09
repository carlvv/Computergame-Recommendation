import os
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler

# Parameters
USER_PROFILE_FILENAME = "Schiller.json"  # profile name
NUM_RECOMMENDATIONS = 30
POPULARITY_FILTER = 'popular'  # Options: 'all', 'popular', 'niche'
POPULAR_THRESHOLD = 2000000  # Number of owners to classify as popular
REVIEW_RATIO_THRESHOLD = 0.6  # Minimum positive review ratio required
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

# Print the columns to verify the presence of the 'tags' column
#print("Columns in game_catalog:", game_catalog.columns)

# Function to calculate cosine similarity
# Cosine similarity measures the cosine of the angle between two vectors.
# In this context, it is used to measure the similarity between the user's profile tags and the game's tags.
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

# Function to perform collaborative filtering
# Collaborative filtering recommends items (games) based on the preferences of similar users.
# In this context, it uses SVD (Singular Value Decomposition) to reduce dimensionality and find similar users based on their playtime data.
def collaborative_filtering(user_profile_name, combined_library, num_recommendations=NUM_RECOMMENDATIONS):
    # Create a pivot table for user-game playtime
    user_game_matrix = combined_library.pivot_table(index='Benutzer', columns='Spiel', values='SpielzeitInStunden', fill_value=0)
    
    # Normalize the data
    scaler = StandardScaler()
    user_game_matrix_normalized = scaler.fit_transform(user_game_matrix)
    
    # Apply SVD
    svd = TruncatedSVD(n_components=20)
    user_game_matrix_svd = svd.fit_transform(user_game_matrix_normalized)
    
    # Print index for debugging
    #print(f"Available users in matrix: {user_game_matrix.index.tolist()}")
    print(f"Searching for user: {user_profile_name}")
    
    # Get the user's index
    user_index = user_game_matrix.index.get_loc(user_profile_name)
    
    # Compute similarities
    user_similarity = cosine_similarity(user_game_matrix_svd[user_index].reshape(1, -1), user_game_matrix_svd).flatten()
    
    # Get similar users and their games
    similar_users = user_similarity.argsort()[::-1][1:num_recommendations+1]
    recommendations = user_game_matrix.iloc[similar_users].mean().sort_values(ascending=False).head(num_recommendations)
    
    return recommendations.index.tolist()

# Generate recommendations
def recommend_games(user_profile_path, game_catalog, combined_library, num_recommendations=NUM_RECOMMENDATIONS, popularity_filter=POPULARITY_FILTER, review_ratio_threshold=REVIEW_RATIO_THRESHOLD):
    with open(user_profile_path, 'r') as profile_file:
        user_profile = json.load(profile_file)
    
    recommendations = []
    total_games = 0
    skipped_games = 0
    
    print("Processing Games.")
    for _, game in game_catalog.iterrows():
        total_games += 1
        try:
            game_tags = eval(game['tags'])  # Convert the string back to a dictionary
            if not isinstance(game_tags, dict):
                raise ValueError("Game tags is not a dictionary.")
        except Exception as e:
            skipped_games += 1
            continue
        
        # Skip games already owned by the user
        if game['name'] in user_profile.get('OwnedGames', []):
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
        recommendations = [rec for rec in recommendations if rec[2] > POPULAR_THRESHOLD]  # Assuming owners > POPULAR_THRESHOLD is popular
    elif popularity_filter == 'niche':
        recommendations = [rec for rec in recommendations if rec[2] < POPULAR_THRESHOLD]  # Assuming owners < POPULAR_THRESHOLD is niche
    
    # Extract user profile name from path
    user_profile_name = os.path.splitext(os.path.basename(user_profile_path))[0]
    
    # Collaborative filtering recommendations
    collab_recommendations = collaborative_filtering(user_profile_name, combined_library, num_recommendations)
    
    # Combine both recommendations
    combined_recommendations = recommendations[:num_recommendations] + collab_recommendations
    
    print(f"Total games processed: {total_games}")
    print(f"Games skipped due to invalid tags: {skipped_games}")
    
    return combined_recommendations[:num_recommendations]

# Directory containing user profiles
user_profiles_folder = LIBRARY_FOLDER
profiles = os.listdir(user_profiles_folder)

# Load combined library
combined_library = pd.read_csv(COMBINED_LIBRARY_PATH)

# Use an existing profile
user_profile_path = os.path.join(user_profiles_folder, USER_PROFILE_FILENAME)

if os.path.isfile(user_profile_path):
    recommendations = recommend_games(user_profile_path, game_catalog, combined_library, NUM_RECOMMENDATIONS, POPULARITY_FILTER, REVIEW_RATIO_THRESHOLD)
    
    print("Recommended Games:")
    print(f"{'Game Name':<40} {'Similarity':<15} {'Owners':<15} {'Pos. Review Ratio':<20} {'Genre':<15}")
    print("-" * 100)

    for game in recommendations:
        truncated_game_name = (game[0][:37] + '...') if len(game[0]) > 40 else game[0]
        print(f"{truncated_game_name:<40} {game[1]:<15.2f} {game[2]:<15} {game[4]:<20.2f} {game[3]:<15}")
else:
    print(f"User profile {user_profile_path} does not exist.")
