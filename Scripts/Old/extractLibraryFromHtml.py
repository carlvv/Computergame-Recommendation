import os
from bs4 import BeautifulSoup
import pandas as pd

def clean_playtime(playtime):
    # Remove "INSGESAMT GESPIELT" and any whitespace around the remaining text
    playtime = playtime.replace("INSGESAMT GESPIELT", "").strip()
    
    # Convert minutes to hours
    if "Minuten" in playtime:
        minutes = float(playtime.replace("Minuten", "").strip().replace(",", "."))
        hours = minutes / 60
        playtime = f"{hours:.2f}"  # Allow two decimal places
    else:
        # Remove "Stunden" and replace "," with "."
        playtime = playtime.replace("Stunden", "").strip().replace(",", ".")
        
        # Remove the first point in the numbers
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

def main():
    input_folder = "libraryHtmls"
    output_folder = "libraryCSVs"
    
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

if __name__ == "__main__":
    main()
