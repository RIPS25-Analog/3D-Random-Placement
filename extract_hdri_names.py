import os
import re

from defaults import *



folder_path = HDRI_PATH
output_file = "hdri_ids.txt"

def extract_names():
    names = []
    for filename in os.listdir(folder_path):
        if os.path.isdir(os.path.join(folder_path, filename)):
            continue
        
        match = re.match(r"^(.*?)_8k", filename)
        if match:
            names.append(match.group(1))

    with open(output_file, "w") as f:
        f.write("\n".join(names))

extract_names()