import glob
import shutil
from pathlib import Path

def combine():
    # Paths
    base_dir = Path(r"/home/data/3d_render/output")
    combined_dir = Path(r"/home/data/3d_render/combined_output")

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

    print("✅ Files combined successfully!")

ls = glob.glob(r"/home/data/3d_render/combined_output/labels/*")
print(len(ls))