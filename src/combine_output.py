import os
import sys
import glob
import shutil
from pathlib import Path

output = "/home/data/3D_RP/output" # Example

combined_output = os.path.join(
    os.path.dirname(output), 
    "combined_" + os.path.basename(output)
)

def combine():
    # Paths
    base_dir = Path(output)
    combined_dir = Path(combined_output)

    # Create combined_output/images and combined_output/labels
    (combined_dir / "images").mkdir(parents=True, exist_ok=True)
    (combined_dir / "labels").mkdir(parents=True, exist_ok=True)

    # Loop through each attempt folder
    for attempt_folder in base_dir.glob("attempt_*"):
        for background_folder in attempt_folder.iterdir():
            if not background_folder.is_dir():
                continue

            images_dir = background_folder / "images"
            labels_dir = background_folder / "labels"

            # Copy images
            if images_dir.exists():
                for img_file in images_dir.iterdir():
                    if img_file.is_file():
                        shutil.copy(img_file, combined_dir / "images" / img_file.name)

            # Copy labels
            if labels_dir.exists():
                for label_file in labels_dir.iterdir():
                    if label_file.is_file():
                        shutil.copy(label_file, combined_dir / "labels" / label_file.name)

    print("Files combined successfully.")

combine()

img = glob.glob(os.path.join(combined_output, "images/*"))
lbl = glob.glob(os.path.join(combined_output, "labels/*"))

print(f"number of images: {len(img)}, number of labels: {len(lbl)}")