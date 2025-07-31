# 3D-Data-Generation

Generate synthetic data for object detection tasks.

### Files and Software Needed

- Blender 4.0 (some functions do not exists in the previous versions)
- Blender 3.11 (at least that's what I used)
- HDRI files for background
    - Supported format: ['.exr']
- 3D object in one of the formats:
    - Supported format: ['.obj', '.ply', '.stl', '.usd', '.usdc', '.usda', '.fbx', '.gltf', '.glb']
    - Has additional structure assumptions (see below)

```
├── data/                            
|   ├── background_hdri/
|   ├── objects/
|   |   ├── <category_1>/
|   |   |   ├── <obj_1>/
|   |   |   |   ├── <obj_1>.gltf             # the name of the object must match the name of the folder
|   |   |   |   ├── <material>.png
|   |   |   |   └── <texture>.png
|   |   |   ├── <obj_2>/
|   |   |   |   └── ...
|   |   |   └── ...
|   |   ├── <category_2>/
|   |   ├── <category_3>/
|   |   ├── ...
|   |   └── distractors/
|   output/   
|   ├── attempt_1_light_on/
|   |   ├── 1_<background_1>/
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

### How to Generate Data

1. Open ```data_generation_and_processing.ipynb```, change the absolute paths, and run the first cell. Change parameters accordingly.
2. Open a Blender file, load ```generate_data.py```, change the absolute paths, and run the script. This script will clea the current active scene, so the best practice is to open a new file or create a new scene before running.

Note: Using absolute path is safer if we're not agreeing with where Blender is installed.

### What Does the Other Scripts Do

- ```move_origin_to_center.py```: If the object's center is not at the center of the mesh, this script helps move the center to the center.
- ```scale_to_right_size.py```: If the mesh of a screwdriver is 2 meters tall, this script helps rescale it back to a reasonable size --- the purpose of this is for simulating natural lighting.
- ```export_obj.py```: Once we're done pre-editing the meshes, run this script to save the objects.
    - Supported format: ['.obj', '.gltf', '.glb']
    - Has additional structure assumptions (see below)
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