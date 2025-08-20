import requests
import os

save_folder = "/home/data/raw/[dataset_name]/backgrounds/HDRI" # xample
ids_file = "hdri_ids.txt"   

os.makedirs(save_folder, exist_ok=True)

def download_file(url, save_path):
    print(f"Downloading {url} ...")

    r = requests.get(url, stream=True)
    r.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Saved to {save_path}")

def download_all_files():
    # ids_file ocntains one asset id per line
    with open(ids_file, "r", encoding="utf-8") as f:
        ids = [line.strip() for line in f if line.strip()]

    for asset_id in ids:
        api_url = f"https://api.polyhaven.com/files/{asset_id}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            # Get 8k EXR URL
            exr_url = data["hdri"]["8k"]["exr"]["url"]
            filename = os.path.basename(exr_url)
            save_path = os.path.join(save_folder, filename)

            download_file(exr_url, save_path)

        except Exception as e:
            print(f"Failed for {asset_id}: {e}")

download_all_files()