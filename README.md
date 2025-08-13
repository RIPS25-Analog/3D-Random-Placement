# 3D-Data-Generation

Generate synthetic data using 3D assets for object detection tasks.

## Files Needed

- HDRI files for background
    - Supported format: ['.exr']
- 3D object in one of the formats:
    - Supported format: ['.obj', '.stl', '.usd', '.usdc', '.usda', '.fbx', '.gltf', '.glb']
    - Has additional folder structure assumptions (see below)
        - If you run the script ```export_obj.py```, it will automatically generate the correct structure.

```                           
├── background_hdri/                    # stores HDRI files
├── objects/                            # store 3D object models
|   ├── <category_1>/                   # category = class label for the objects inside this file
|   |   ├── <obj_1>/
|   |   |   ├── <obj_1>.gltf            # the name of the object must match the name of the folder
|   |   |   ├── <material>.png
|   |   |   └── <texture>.png
|   |   ├── <obj_2>/
|   |   |   └── ...
|   |   └── ...
|   ├── <category_2>/
|   ├── ...
|   └── distractors/                    # distractors will not be parsed as a label
```

Output structure
```
output/
├── attempt_1/                          # one attempt: running the whole script once (assume seed=0)
|   ├── 1_<background_1>/               # images generated with the same background and scene layout are grouped together
|   |   ├── images/
|   |   |   ├── 1(0)_1_1_1.jpg
|   |   |   ├── 1(0)_1_1_2.jpg
|   |   |   ├── 1(0)_1_1_3.jpg
|   |   |   ├── ...
|   |   |   ├── 1(0)_1_2_1.jpg
|   |   |   ├── 1(0)_1_2_2.jpg
|   |   |   ├── 1(0)_1_2_3.jpg
|   |   |   └── ...
|   |   └── labels/
|   |   |   └── ...
|   ├── 2_<background_2>/
|   |   └── ...
|   └── ...
├── attempt_2/
|   └── ...
└── ... 

## How to Generate Data

1. Headless through Blender
    - ```blender --background --python "generate_data.py" -- <args>```
    - Requirements: Blender >= 4.0.0
2. Headless using the standalone ```bpy``` library
    - ```python "generate_data.py" <args>```
    - Requirements: bpy >= 4.0.0
    - Note: Best practice is to use CYCLES as the render engine. Might enter bugs that are not present if running through Blender.
3. Inside Blender UI
    - In the scripting section, load ```generate_data.py``` and run. 
    - Requirements: Blender >= 4.0.0
    - Note: This script will clean the current active scene, so the best practice is to open a new file or create a new scene before running.

Note: Use absolute paths.

## What the Other Scripts Do

- ```move_origin_to_center.py```: If the object's center is not at the center of the mesh, this script helps move the center to the center.
- ```scale_to_right_size.py```: If the mesh of a screwdriver is 2 meters tall, this script helps rescale it back to a reasonable size -- the purpose of this is to simulate natural lighting.
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

## Limitations

- Bounding box might be smaller than the actual visible object if the object is highly occluded and vertices are not high enough.