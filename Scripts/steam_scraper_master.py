import pandas as pd
import requests
import os
import time
import multiprocessing
from multiprocessing import Manager

# Function to fetch game details using the appid
def fetch_game_details(appid):
    url = f"http://steamspy.com/api.php?request=appdetails&appid={appid}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data for appid {appid}, status code: {response.status_code}")
        return None

def save_progress(data, part_num):
    folder_name = 'separateData'
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    file_name = os.path.join(folder_name, f'steam_games_part_{part_num}.csv')
    df = pd.DataFrame(data)
    df.to_csv(file_name, index=False)
    print(f"Progress saved to {file_name}")

def combine_csv_files(output_file):
    folder_name = 'separateData'
    all_files = [os.path.join(folder_name, f) for f in os.listdir(folder_name) if f.endswith('.csv')]
    combined_df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)
    combined_df.to_csv(output_file, index=False)
    print(f"All parts combined into {output_file}")

def get_existing_parts():
    folder_name = 'separateData'
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    existing_files = [f for f in os.listdir(folder_name) if f.endswith('.csv')]
    existing_parts = set(int(f.split('_')[-1].split('.')[0]) for f in existing_files)
    return existing_parts

def worker(shared_state, batch_size, lock, delay):
    time.sleep(delay)  # Add delay for each worker
    while True:
        with lock:
            if not shared_state['remaining_batches']:
                break
            batch_start = None
            for batch in shared_state['remaining_batches']:
                part_num = (batch // batch_size) + 1
                if part_num not in shared_state['existing_parts'] and part_num not in shared_state['processing_batches']:
                    batch_start = batch
                    shared_state['processing_batches'].append(part_num)
                    break
            
            if batch_start is None:
                continue
            shared_state['remaining_batches'].remove(batch_start)
        
        batch_end = batch_start + batch_size
        all_game_details = []
        part_num = (batch_start // batch_size) + 1
        
        for i in range(batch_start, batch_end):
            if i >= len(shared_state['appids']):
                break
            appid = shared_state['appids'][i]
            print(f"Fetching details for appid {appid} ({i+1}/{len(shared_state['appids'])})...")
            game_details = fetch_game_details(appid)
            if game_details:
                all_game_details.append(game_details)
            time.sleep(1)  # Respect rate limit of 1 request per second
        
        save_progress(all_game_details, part_num)
        
        with lock:
            shared_state['processing_batches'].remove(part_num)

def main(parallel_instances):
    # Read the existing CSV file to get the appids
    df = pd.read_csv('steam_games.csv')
    appids = df['appid'].tolist()

    manager = Manager()
    shared_state = manager.dict()
    shared_state['appids'] = appids
    shared_state['remaining_batches'] = manager.list(range(0, len(appids), 60))
    shared_state['existing_parts'] = get_existing_parts()
    shared_state['processing_batches'] = manager.list()
    
    lock = manager.Lock()
    batch_size = 60
    
    processes = []
    for idx in range(parallel_instances):
        delay = idx  # 1-second delay per worker
        p = multiprocessing.Process(target=worker, args=(shared_state, batch_size, lock, delay))
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()
    
    # Combine all parts into one final dataset
    combine_csv_files('steam_games_final.csv')

if __name__ == "__main__":
    parallel_instances = int(input("Enter number of parallel instances: "))
    main(parallel_instances)
