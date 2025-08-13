import requests
import os

# Path to your file with IDs
ids_file = "hdri_ids.txt"  # one asset id per line

# Output folder
save_folder = "downloads"
os.makedirs(save_folder, exist_ok=True)

# Function to download a file
def download_file(url, save_path):
    print(f"Downloading {url} ...")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved to {save_path}")

# Read IDs from file
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
