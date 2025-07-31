# 3D-Data-Generation

Generate synthetic data from 3D assets for object detection tasks.

## Files and Software Needed

- Blender 4.0 (some functions do not exists in the previous versions)
- Python 3.11 (at least that's what I used)
- HDRI files for background
    - Supported format: ['.exr']
- 3D object in one of the formats:
    - Supported format: ['.obj', '.ply', '.stl', '.usd', '.usdc', '.usda', '.fbx', '.gltf', '.glb']
    - Has additional folder structure assumptions (see below)
        - If you run the script ```export_obj.py```, it will automatically generate the correct structure.

```
├── data/                            
|   ├── background_hdri/                    # stores HDRI files
|   ├── objects/                            # store 3D object models
|   |   ├── <category_1>/                   # category = class label for the objects inside this file
|   |   |   ├── <obj_1>/
|   |   |   |   ├── <obj_1>.gltf            # the name of the object must match the name of the folder
|   |   |   |   ├── <material>.png
|   |   |   |   └── <texture>.png
|   |   |   ├── <obj_2>/
|   |   |   |   └── ...
|   |   |   └── ...
|   |   ├── <category_2>/
|   |   ├── <category_3>/
|   |   ├── ...
|   |   └── distractors/                    # distractors will not be parsed as a label
|   output/   
|   ├── attempt_1_light_on/                 # one attempt = running the script once
|   |   ├── 1_<background_1>/               # images generated with the same background and scene layout are grouped together
|   |   |   ├── images/
|   |   |   |   ├── 1_<obj_1>_1.jpg
|   |   |   |   ├── 1_<obj_1>_2.jpg
|   |   |   |   ├── 1_<obj_1>_3.jpg
|   |   |   |   ├── ...
|   |   |   |   ├── 1_<obj_2>_1.jpg
|   |   |   |   ├── 1_<obj_2>_2.jpg
|   |   |   |   ├── 1_<obj_2>_3.jpg
|   |   |   |   └── ...
|   |   |   └── labels/
|   |   |   |   └── ...
|   |   ├── 2_<background_2>/
|   |   |   └── ...
|   |   └── ...
|   ├── attempt_2_light_off/
|   |   └── ...
|   └── ... 
```

## How to Generate Data

1. Open ```data_generation_and_processing.ipynb```, change the absolute paths, and run the first cell. Change parameters accordingly.
2. Open a Blender file, load ```generate_data.py```, change the absolute paths, and run the script. This script will clea the current active scene, so the best practice is to open a new file or create a new scene before running.

Note: Using absolute path is safer if we're not agreeing with where Blender is installed.

### Parameter explanations

I will add to it later.

## What the Other Scripts Do

- ```move_origin_to_center.py```: If the object's center is not at the center of the mesh, this script helps move the center to the center.
- ```scale_to_right_size.py```: If the mesh of a screwdriver is 2 meters tall, this script helps rescale it back to a reasonable size --- the purpose of this is for simulating natural lighting.
- ```export_obj.py```: Once we're done pre-editing the meshes, run this script to save the objects.
    - Supported format: ['.obj', '.gltf', '.glb']
    - Has additional structure assumptions for Blender scene collections (see below)
```
├── Scene/                            
|   ├── Scene Collection/
|   |   ├── <category_1>/
|   |   |   ├── <obj_1>
|   |   |   ├── <obj_2>
|   |   |   └── ...
|   |   ├── <category_2>/
|   |   ├── <category_3>/
|   |   ├── ...
|   |   └── distractors/
```
- ```unused.py```: Stores unused functions, including generating object mask and using regular 2D image as background instead of HDRI.

## Limitations

- Bounding box is not very accurate if the object is highly occulded.
- Objects flow in the air (we can eliminate this by using Blender's physical simulation and 3D scenes).