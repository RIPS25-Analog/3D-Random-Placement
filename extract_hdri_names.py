import os
import re

# Example: folder containing your files
folder_path = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\background_hdri"
output_file = "hdri_ids.txt"

names = []
for filename in os.listdir(folder_path):
    if os.path.isdir(os.path.join(folder_path, filename)):
        continue
    
    match = re.match(r"^(.*?)_8k", filename)
    if match:
        names.append(match.group(1))

with open(output_file, "w") as f:
    f.write("\n".join(names))