# 3D Random Placement

Generate synthetic data using 3D assets for object detection tasks.

## Required Packages

- bpy
    - Version: 4.1.0 (or 4.0.0 depending on the system)
    - ```pip install bpy==4.1.0 --extra-index-url https://download.blender.org/pypi/```

- mathutils
    - Version: 3.3.0
    - ```pip install mathutils```

- bpycv
    - Version: 1.0.0
    - ```pip install bpycv```
    
- cv2
    - Version: 4.11.0.86
    - ```pip install opencv-python```

- numpy
    - Version: 2.2.6
    - ```pip install numpy```

- pymeshlab
    - Version: 2025.7
    - ```pip install pymeshlab```

- yaml
    - Version: 6.0.2
    - ```pip install pyyaml```



## Data Preparation

### HDRI Files

- Run the script ```download_hdri.py``` to download HDRI files from [Poly Haven](https://polyhaven.com/hdris).

- This script utilizes Poly Haven's [API](https://redocly.github.io/redoc/?url=https://api.polyhaven.com/api-docs/swagger.json&nocors).

- The default downloading size is ```8k``` and the extension is ```.exr```.

### 3D Models

- The ```generate_data.py``` script only supports ```.obj``` format, which must be accompanied by ```.mtl``` and ```.png``` or ```.jpg``` files to define the model's material and texture.

1. Convert selected models from the PACE dataset:

    - Run the script ```convert_ply_to_obj.py```.

    - **Note**: This script is designed specifically for converting ```.ply``` models from the PACE dataset to ```.obj``` using ```pymeshlab```. Its behavior with other datasets or file types is not guaranteed.

2. Obtain 3D model using photogrammetry technology:

    - [RealityScan](https://www.realityscan.com/en-US) is a powerful 3D scanning software, available with a [mobile application](https://apps.apple.com/us/app/realityscan-mobile/id1584832280) that is free to use.

### File Structure Visualization

```                           
├── backgrounds/HDRI/                    
|   ├── bg_1_8k.exr                     # "moon_lab_8k"
|   ├── bg_2_8k.exr                     # "illovo_beach_balcony_8k"
|   └── ...
|
├── 3d_models/
|   ├── category_1/                     # "can"
|   |   ├── obj_1/                      # "red_can"
|   |   |   ├── obj_1.obj
|   |   |   ├── material.mtl
|   |   |   └── texture.png
|   |   ├── obj_2/                      # "white_can"
|   |   ├── obj_3/                      # "orange_can"
|   |   └── ...
|   ├── category_2/                     # "toy_car"
|   ├── ...
|   └── ...
```



## Data Generation

- Run the bash file ```run_generate_data.sh``` to generate data batch by batch using the following command:

    - ```bash run_generate_data.sh```

    - **Explanation:** The Python script ```generate_data.py``` can consume a large amount of memory during rendering, and if the number of generated images is too high, it will likely encounter the "GPU out of memory" issue and the program will terminate. To prevent this, we use a Bash file to run a for loop to execute the script multiple times, each with a different random seed.

- Variable explanation:

    - ```attempt```: One attempt corresponds to a single execution of the script. The bash file controls the number of attempts.
    
    - ```iteration```: Within each attempt, this specifies the number of backgrounds the script will use.
    
    - ```arrangement```: For each iteration, the objects will be re-selected and re-arranged this number of times.
    
    - ```num-pics```: For each arrangement, the camera captures this many images from different angles.

    - The total number of images is the product of all the above values. The default value is ```10``` for each.
    
- Naming convention for each picture:  

    - ```attempt(seed)_iteration_arrangement_num-pics.jpg```

### Ouput Structure

Inside each ```attempt_<num>``` folder, the output contain a  ```configs_<num>.yaml```file that stores the configurations for each generation.

```
output/
├── attempt_1/                          # attempt
|   ├── 1_background_1/                 # iteration
|   |   ├── images/                     # arrangement & num-pics
|   |   └── labels/
|   ├── 2_background_2/
|   ├── 3_background_3/
|   └── ...
├── attempt_2/
|   └── ...
└── ... 
```

## Post-processing

- After the generation cycle, run the Python script ```combine_output.py``` to combine everything in the output into one folder.

- The label for all objects in each image is stored as text strings that match the names of the category folders.