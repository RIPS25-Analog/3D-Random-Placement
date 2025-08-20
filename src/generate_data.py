import bpy
import mathutils
import bpycv
import cv2
import numpy as np
import random

import os
import glob
import re
import sys
import argparse

import yaml
import time

# === ADJUSTABLE VARIABLES ===

HDRI_PATH = "/home/data/raw/[dataset_name]/backgrounds/HDRI" # Example
OBJ_PATH = "/home/data/raw/[dataset_name]/3d_models" # Example
OUTPUT_PATH = "/home/data/3D_RP/output" # Example

RANDOM_SEED = 0             # Set the random seed for reproducibility

ITERATION = 10              # Number of scene/backgrounds to generate
ARRANGEMENT = 10            # Number of arrangements per iteration
NUM_PICS = 10               # Number of pictures taken around per object

# === INTERNAL VARIABLES ===

TARGET_CLASSES = ["can", "toy_car"]
ALL_CLASSES = []            # Will be updated later in the script

MIN_TARGET_OBJ = 0          # Minimum target objects appearing in a scene
MAX_TARGET_OBJ = 2          # Maximum target objects appearing in a scene
MIN_TOTAL_OBJ = 3           # Minimum total objects appearing in a scene
MAX_TOTAL_OBJ = 6           # Maximum total objects appearing in a scene

MAX_LIGHT_ENERGY = 50       # Maximum light intensity for the scene
MIN_EXPOSURE = 0.5          # Minimum exposure rate for hdri backgrounds
MAX_EXPOSURE = 10           # Maximum exposure rate for hdri backgrounds

RESOLUTION_X = 1920 // 2
RESOLUTION_Y = 1080 // 2

SAMPLES = 16                # Number of samples per image. The higher the lesser artifacts (Renderer setup)
TILE_SIZE = 4096            # Tile size for rendering. The higher the faster and more GRU compute (Renderer setup)

SAVE_FILES = True

CENTER = mathutils.Vector((0, 0, 0)) # Center of the box where objects will be placed
X_RANGE = 0.4 # Range for X-axis
Y_RANGE = 0.4 # Range for Y-axis
Z_RANGE = 0.2 # Range for Z-axis

RESCALE_SIZE = 0.2 # Mean size for objects after scaling
EPS = 0.05 # Size deviation for randomness



# === DEFINE CAMERA BEHAVIOR ===

def get_viewpoint(center, max_dist):
    z = 2 * random.random() - 1  # z is in [-1, 1]
    theta = 2 * np.pi * random.random()
    r_xy = np.sqrt(1 - z * z)

    x = r_xy * np.cos(theta)
    y = r_xy * np.sin(theta)

    # Apply radius and center offset
    pos = (
        center[0] + max_dist * x,
        center[1] + max_dist * y,
        center[2] + max_dist * z
    )
    return pos

def look_at(obj, target):
    direction = (target - obj.location).normalized()
    quat = direction.to_track_quat('-Z', 'Y') 
    obj.rotation_euler = quat.to_euler()

def zoom_on_object(camera, center, bbox_corners, depsgraph):
    # Point camera at the target center
    look_at(camera, center)

    coords = [coord for corner in bbox_corners for coord in corner]
    
    # Zoom to where the entire object will fit in view
    bpy.context.view_layer.update()
    location, _scale = camera.camera_fit_coords(depsgraph, coords)
    camera.location = location

    # Find the line of sight from the camera to the center of the object
    forward = camera.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 0.0, -1.0))
    min_distance = (camera.location - center).length

    # Randomly zoom in or out
    fill_ratio = random.uniform(0.3, 1.3)  
    camera.location += forward - forward / fill_ratio

    # return the minimum distance for future checks
    return min_distance

def distance_too_close(camera, all_objects, min_distance):
    # Check if the camera is too close to any object
    for obj, _label in all_objects:
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
        distance = (camera.location - center).length
        
        if distance < min_distance:
            return True  # Camera is too close to an object
        
    return False  # Camera is at a safe distance from all objects



# === OBJECTS AUGMENTATION ===

def rescale_object(obj, target_size=RESCALE_SIZE, eps=EPS, apply=True): 
    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    # Get size in each axis
    min_corner = mathutils.Vector(map(min, zip(*bbox_corners)))
    max_corner = mathutils.Vector(map(max, zip(*bbox_corners)))
    dimensions = max_corner - min_corner

    # Calculate and apply the scale factor
    current_size = max(dimensions)
    final_size = target_size + random.uniform(-eps, eps)
    scale_factor = final_size / current_size
    obj.scale *= scale_factor

    if apply:
        bpy.context.view_layer.update()
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def translate_object(obj, center=CENTER, x_range=X_RANGE, y_range=Y_RANGE, z_range=Z_RANGE):
    '''
    Randomly place the object inside a cube-shaped area.
    '''
    x = random.uniform(center.x - x_range, center.x + x_range)
    y = random.uniform(center.y - y_range, center.y + y_range)
    z = random.uniform(center.z - z_range, center.z + z_range)
    obj.location = (x, y, z)

def translate_object_on_surface(obj, x_range, y_range, z_range, center=CENTER):
    '''
    Randomly place the object on the surface of a cube-shaped area.
    '''
    # Compute min and max bounds
    x_min, x_max = center.x - x_range, center.x + x_range
    y_min, y_max = center.y - y_range, center.y + y_range
    z_min, z_max = center.z - z_range, center.z + z_range

    # Randomly choose one face of the cube (6 faces = 3 axes × 2 sides)
    face = random.choice(['x-', 'x+', 'y-', 'y+', 'z-', 'z+'])

    # Set the coordinate for the selected face to min or max
    if face == 'x-':
        x = x_min
        y = random.uniform(y_min, y_max)
        z = random.uniform(z_min, z_max)
    elif face == 'x+':
        x = x_max
        y = random.uniform(y_min, y_max)
        z = random.uniform(z_min, z_max)
    elif face == 'y-':
        x = random.uniform(x_min, x_max)
        y = y_min
        z = random.uniform(z_min, z_max)
    elif face == 'y+':
        x = random.uniform(x_min, x_max)
        y = y_max
        z = random.uniform(z_min, z_max)
    elif face == 'z-':
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        z = z_min
    elif face == 'z+':
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        z = z_max

    obj.location = (x, y, z)

def rotate_object(obj):
    # Make sure the rotation mode is Euler
    obj.rotation_mode = 'XYZ'

    # Apply random Euler rotation
    obj.rotation_euler = (
        random.uniform(0, 2 * np.pi),  # X axis
        random.uniform(0, 2 * np.pi),  # Y axis
        random.uniform(0, 2 * np.pi)   # Z axis
    )



# === ADD AND ADJUST HDRI BACKGROUND ===

def add_hdri_background(scene, selected_hdri):
    if scene.world is None:
        scene.world = bpy.data.worlds.new("GeneratedWorld")

    # Initial setup
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear existing nodes
    nodes.clear()
    
    # Create Texture Coordinate node
    tex_coord = nodes.new(type="ShaderNodeTexCoord")

    # Create Mapping node
    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.inputs['Rotation'].default_value[2] = -1  # Rotate around Z (in radians)

    # Create Environment Texture (HDRI)
    env_tex = nodes.new(type="ShaderNodeTexEnvironment")
    env_tex.name = "EnvironmentTexture"
    env_tex.image = bpy.data.images.load(selected_hdri)
    
    # Create Background node
    background = nodes.new(type="ShaderNodeBackground")
    background.inputs["Strength"].default_value = 1
    
    # Create output node
    world_output = nodes.new(type="ShaderNodeOutputWorld")
    
    # Multiply node for brightness adjustment
    multiply = nodes.new(type="ShaderNodeMixRGB")
    multiply.name = "HDRIMultiply"
    multiply.blend_type = 'MULTIPLY'
    multiply.inputs['Fac'].default_value = 1.0
    multiply.inputs['Color2'].default_value = (1, 1, 1, 1)

    # Arrange nodes neatly
    tex_coord.location = (-1200, 0)
    mapping.location = (-1000, 0)
    env_tex.location = (-800, 0)
    multiply.location = (-500, 0)
    background.location = (-200, 0)
    world_output.location = (0, 0)
    
    # Link nodes
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
    links.new(env_tex.outputs["Color"], multiply.inputs["Color1"])
    links.new(multiply.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], world_output.inputs["Surface"])
    
    scene.render.film_transparent = False

def update_hdri_settings(scene, hdri_path=None, brightness=1):
    world = scene.world
    nodes = world.node_tree.nodes

    env_tex = nodes.get("EnvironmentTexture")
    multiply = nodes.get("HDRIMultiply")

    if hdri_path:
        env_tex.image = bpy.data.images.load(hdri_path)

    multiply.inputs['Color2'].default_value = (brightness, brightness, brightness, 1.0)



# === RENDER AND SAVE FILES ===

def get_bounding_box_for_all(all_objects):
    # Initialize min and max coordinates
    min_coord = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_coord = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

    # Loop through all mesh objects
    for obj, _label in all_objects:
        for vertex in obj.bound_box:
            world_vertex = obj.matrix_world @ mathutils.Vector(vertex)
            min_coord.x = min(min_coord.x, world_vertex.x)
            min_coord.y = min(min_coord.y, world_vertex.y)
            min_coord.z = min(min_coord.z, world_vertex.z)

            max_coord.x = max(max_coord.x, world_vertex.x)
            max_coord.y = max(max_coord.y, world_vertex.y)
            max_coord.z = max(max_coord.z, world_vertex.z)

    # Calculate the corners of the bounding box
    all_corners = [
        mathutils.Vector((min_coord.x, min_coord.y, min_coord.z)),
        mathutils.Vector((min_coord.x, min_coord.y, max_coord.z)),
        mathutils.Vector((min_coord.x, max_coord.y, min_coord.z)),
        mathutils.Vector((min_coord.x, max_coord.y, max_coord.z)),
        mathutils.Vector((max_coord.x, min_coord.y, min_coord.z)),
        mathutils.Vector((max_coord.x, min_coord.y, max_coord.z)),
        mathutils.Vector((max_coord.x, max_coord.y, min_coord.z)),
        mathutils.Vector((max_coord.x, max_coord.y, max_coord.z)),
    ]

    return all_corners

def capture_views(camera, scene, depsgraph, selected_targets, selected_distractors, 
                  atmpt, iter, seed, arngmnt, all_classes, num_pics, 
                  min_exposure, max_exposure, output_folder, save_files):
    
    # Get the bounding box for all objects (so that the camera can zoom out to fit)
    all_objects = selected_targets + selected_distractors
    all_corners = get_bounding_box_for_all(all_objects)
    
    # Iterate through the number of pictures to take
    for i in range(num_pics):
        # Randomly select one object to focus on
        focus_obj, _label = random.choice(all_objects)

        # Get bounding box corners in world space
        bbox_corners = [focus_obj.matrix_world @ mathutils.Vector(corner) for corner in focus_obj.bound_box]

        # Get center and size
        center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
        max_dist = max((corner - center).length for corner in bbox_corners)

        # Get a random viewpoint and distance
        camera.location = get_viewpoint(center, max_dist)
        min_distance = zoom_on_object(camera, center, all_corners, depsgraph)

        # If the camera is too close to any object, get a new viewpoint
        while distance_too_close(camera, selected_targets + selected_distractors, min_distance * 0.4):
            camera.location = get_viewpoint(center, max_dist)
            min_distance = zoom_on_object(camera, center, all_corners, depsgraph)

        # Change the exposure of the background
        if random.random() < 0.5:
            brightness = random.uniform(min_exposure, 1)
        else:
            brightness = random.uniform(1, max_exposure)
        update_hdri_settings(scene, brightness=brightness)

        print(f"\n-------------------- Attempt {atmpt}; Iteration {iter+1}; Arrangment {arngmnt+1}; View angle {i+1} --------------------\n")
        
        # Set up objects isntance id
        index = 0
        for obj, label in selected_targets:
            obj["inst_id"] = (all_classes.index(label) + 1) * 1000 + index
            index += 1

        # render image, instance annoatation and depth
        result = bpycv.render_data()

        # Get instance map from the result
        inst_map = result["inst"]
        h, w = inst_map.shape

        bboxes = dict()

        # Get bounding box annotations
        for obj, label in selected_targets:
            inst_id = obj["inst_id"]

            ys, xs = np.where(inst_map == inst_id)
            if xs.size == 0 or ys.size == 0:
                # No pixels for this object — skip it
                continue
            minX, maxX = xs.min() / w, xs.max() / w
            minY, maxY = ys.min() / h, ys.max() / h

            # Convert to YOLO format
            x_center = (minX + maxX) / 2
            y_center = (minY + maxY) / 2
            width = maxX - minX
            height = maxY - minY

            # Store label {bbox : label}
            bboxes.update({
                (x_center, y_center, width, height) : label
            })

        if save_files:
            file_name = f"{atmpt}({seed})_{iter+1}_{arngmnt+1}_{i+1}"

            # === SAVE THE IMAGE ===

            # Make sure the image folder exists
            img_path = os.path.join(output_folder, "images")
            os.makedirs(img_path, exist_ok=True)

            # Save the image
            img_file_path = os.path.join(img_path, f"{file_name}.jpg")

            cv2.imwrite(
                img_file_path, result["image"][..., ::-1]
            )  # transfer RGB image to opencv's BGR

            # === SAVE THE LABEL ===

            # Make sure the labels folder exists
            label_path = os.path.join(output_folder, "labels")
            os.makedirs(label_path, exist_ok=True)

            # Save the annotation file
            label_file_path = os.path.join(label_path, f"{file_name}.txt")

            with open(label_file_path, "w") as f:
                for bbox, label in bboxes.items():
                    x_center, y_center, width, height = bbox
                    f.write(f"{label} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        print()



# === OBJECTS SETUP ===

def add_default_obj(scene):
    # Add new camera
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_object = bpy.data.objects.new("Camera", camera_data)

    # Set camera location and rotation
    camera_object.location = (0, -5, 3)
    camera_object.rotation_euler = (1.1, 0, 0)

    # Link camera to scene
    scene.collection.objects.link(camera_object)
    scene.camera = camera_object
    
    # Add new sunlight
    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    light_object = bpy.data.objects.new(name="Sun", object_data=light_data)

    # Set light location and rotation
    light_object.location = (5, -5, 10)
    light_object.rotation_euler = (0.7854, 0, 0.7854)  # 45 degrees down and to side

    # Link light to scene
    scene.collection.objects.link(light_object)

    return camera_object, light_object

def import_obj(scene, obj_path):
    all_classes = []
    
    # Get all object class folders
    class_folders = glob.glob(f"{obj_path}/*/")

    # Iterate through all the class folders under the objects folder
    for class_folder in class_folders:
        class_name = os.path.basename(os.path.dirname(class_folder))
        
        # Create new collection for each class
        class_coll = bpy.data.collections.new(class_name)
        scene.collection.children.link(class_coll)

        # Save the class name
        all_classes.add(class_name)

        # Get all object folders (instances of the same class)
        obj_folders = glob.glob(f"{class_folder}/*/")

        # Iterate through all the object folders within the same class
        for obj_folder in obj_folders:
            obj_name = os.path.basename(os.path.dirname(obj_folder))

            # Iterate through all files in the object folder and try to find the .obj file
            for file_path in glob.glob(f"{obj_folder}/*"):
                # Get the file extensio
                obj_ext = os.path.splitext(file_path)[1].lower()

                if obj_ext == ".obj":
                    # Import the object 
                    bpy.ops.wm.obj_import(filepath=file_path)
                    
                    # Rename the object to the folder name (optional)
                    new_obj = bpy.context.view_layer.objects.active
                    new_obj.name = obj_name  

                    # Set the origin to center  (optional)
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

                    break  # Stop the loop after finding the .obj file
            
            # Unlink from the default collection (if any)
            for coll in new_obj.users_collection:
                coll.objects.unlink(new_obj)
            
            # Link the object to its class collection
            class_coll.objects.link(new_obj)

            # Move the object away from the origin to avoid unintentional occlusion
            translate_object(new_obj, center=mathutils.Vector((100, 100, 100)))  
            rescale_object(new_obj)  

    # Update the global variable
    global ALL_CLASSES
    ALL_CLASSES = all_classes

def get_selected_objects():
    target_objects = [] # (obj, label)
    distractor_objects = [] # (obj, label)

    # Get all objects with labels from the scene (excluding distractors)
    for label in TARGET_CLASSES:
        # Get the collection of each label
        collection = bpy.data.collections[label]

        # Add the object to target list and hide from renderer
        for obj in collection.objects:
            if obj.type == 'MESH':
                obj.hide_render = True
                target_objects.append((obj, label))

    # Randomly select some of the target objects
    ran_num_target = random.randint(MIN_TARGET_OBJ, MAX_TARGET_OBJ)
    selected_targets = random.sample(target_objects, ran_num_target)

    # Get all other objects from the scene (act as distractors)
    for label in ALL_CLASSES:
        # Exclude target classes to avoid repetition
        if label not in TARGET_CLASSES:
            collection = bpy.data.collections[label]

            # Add the object to other list and hide from renderer
            for distr in collection.objects:
                if distr.type == 'MESH':
                    distr.hide_render = True
                    distractor_objects.append((distr, label))
        
    # Randomly determine a total object number select other objects to reach that number
    ran_num_distractors = random.randint(MIN_TOTAL_OBJ, MAX_TOTAL_OBJ) - ran_num_target
    selected_distractors = random.sample(distractor_objects, ran_num_distractors)

    # Let selected objects to be see in the renderer
    for obj, _label in selected_targets + selected_distractors:
        obj.hide_render = False

        # Add augmentation to both target objects and distractors
        rescale_object(obj)
        translate_object(obj)
        rotate_object(obj)

    return selected_targets, selected_distractors



# === INITIAL SETUPS ===

def traverse_tree(t):
    yield t
    for child in t.children:
        yield from traverse_tree(child)

def clear_stage(scene):
    # Clear all collections
    for coll in traverse_tree(scene.collection):
        for obj in coll.objects:
            # Unlink from all collections to avoid dangling links
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
                
            # Remove the object from the scene
            bpy.data.objects.remove(obj, do_unlink=True)
        
        # Keep the default Scene Collection
        if coll.name != "Scene Collection":
            scene.collection.children.unlink(coll)

    bpy.ops.outliner.orphans_purge()

def render_setup(scene):
    scene.render.engine = 'CYCLES' # Only this CYCLES supports headless rendering

    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    prefs.get_devices()  # Populate available devices
    prefs.use_cuda = True

    # Activate all GPU devices (optional but common)
    for device in prefs.devices:
        device.use = True
    
    scene.cycles.samples = SAMPLES
    scene.cycles.tile_size = TILE_SIZE

    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.use_progressive_refine = False
    scene.cycles.device = "GPU"

    scene.render.use_persistent_data = False # Set to True for faster render but more GPU usage
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y

def setup_output_folder(output_path, save_files):
    # Regex to match folders like: attempt_#
    pattern = re.compile(r"attempt_(\d+)")

    # Find the highest existing attempt number
    max_attempt = 0
    for name in os.listdir(output_path):
        match = pattern.fullmatch(name)
        if match:
            attempt_num = int(match.group(1))
            if attempt_num > max_attempt:
                max_attempt = attempt_num

    next_attempt = max_attempt + 1

    # Prepare output directories
    output_folder = os.path.join(output_path, f"attempt_{next_attempt}")

    if save_files:
        # Create the output folder
        os.makedirs(output_folder, exist_ok=True)

        yaml_path = os.path.join(output_folder, f"configs_{next_attempt}.yaml")

        basic_types = (int, float, str, bool, list, tuple, dict)
        current_module = sys.modules[__name__]
        all_vars = {k: v for k, v in vars(current_module).items() if not k.startswith("__") and isinstance(v, basic_types)}

        with open(yaml_path, "w") as f:
            yaml.dump(all_vars, f, sort_keys=False)

    return output_folder, yaml_path, next_attempt



# === MAIN FUNCTION ===

def main(args):
    start_time = time.time()
    random.seed(args.seed)  # Set the random seed for reproducibility
    scene = bpy.context.scene

    clear_stage(scene)
    render_setup(scene)
    
    # Import objects
    import_obj(scene, args.obj_path)

    # Collect hdri files and build the world tree
    hdri_files = glob.glob(os.path.join(args.hdri_path, "*.exr"))
    add_hdri_background(scene, hdri_files[0])  # Add the first hdri as a default background

    # Add default camera and light
    camera, light = add_default_obj(scene)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # Setup light energy
    light_energy_ran = random.randint(0, MAX_LIGHT_ENERGY)
    light.data.energy = light_energy_ran

    # Set the output folder
    output_folder, yaml_path, atmpt = setup_output_folder(args.output_path, SAVE_FILES) 

    # Iterate through the number of background we want to generate
    for iter in range(min(args.iteration, len(hdri_files))):
        # Pick a background
        selected_hdri = random.choice(hdri_files)
        hdri_files.remove(selected_hdri)  # Remove the selected hdri to avoid repetition

        # Make a subfolder for each iteration
        hdri_name = os.path.basename(selected_hdri).split('.')[0]
        output_subfolder = os.path.join(output_folder, f"{iter+1}_{hdri_name}")

        # Iterate through different object arrangements of the same scene
        for arngmnt in range(args.arrangement):
            
            # Randomly select target and distractor objects to render
            selected_targets, selected_distractors = get_selected_objects()

            # Update the background to the selected one
            update_hdri_settings(scene, hdri_path=selected_hdri)

            # Add random lighting
            translate_object_on_surface(light, 
                                    x_range = 6, 
                                    y_range = 6, 
                                    z_range = 6)
            look_at(light, CENTER)

            # Update the scene
            bpy.context.view_layer.update()

            # Capture selected objects
            capture_views(camera, scene, depsgraph, selected_targets, selected_distractors, 
                          atmpt, iter, args.seed, arngmnt, ALL_CLASSES, args.num_pics, 
                          MIN_EXPOSURE, MAX_EXPOSURE, output_subfolder, SAVE_FILES)
            
            # Move the objects away from the origin to avoid unintentional occlusion
            for obj, _label in selected_targets + selected_distractors:
                translate_object(obj, center=mathutils.Vector((100, 100, 100)))  

            # Clean up the storage and update the scene
            bpy.context.view_layer.update()

        # End of arrangement loop

    # End of iteration loop

    print(f"Output folder: {output_folder}")
    print("\n======================================== Render loop is finished ========================================\n")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Total execution time: {execution_time:.2f} seconds\n")

    with open(yaml_path, "a") as f:
        f.write(f"\n# Total execution time: {execution_time:.2f} seconds\n")



# === ARGUMENT PARSING ===

def parse_args(argv):
    '''Parse input arguments
    '''
    parser = argparse.ArgumentParser(description = "Create synthetic data with 3D objects.")

    parser.add_argument("--hdri_path",
        help = "The directory that contains hdri backgrounds.", 
        default = HDRI_PATH)

    parser.add_argument("--obj_path",
        help = "The directory which contains 3D object files.", 
        default = OBJ_PATH)
    
    parser.add_argument("--output_path",
        help = "The directory where images and labels will be created and stored.", 
        default = OUTPUT_PATH)
    
    parser.add_argument("--seed",
        help = "Set the random seed for reproducibility.", 
        default = RANDOM_SEED, 
        type = int)
    
    parser.add_argument("--iteration",
        help = "Number of scene/backgrounds to generate.", 
        default = ITERATION, 
        type = int)
    
    parser.add_argument("--arrangement",
        help = "Number of arrangements per iteration.", 
        default = ARRANGEMENT, 
        type = int)
    
    parser.add_argument("--num_pics", 
        help = "Number of pictures taken around per object", 
        default = NUM_PICS, 
        type=int)
    
    args = parser.parse_args(argv)
    return args

def handle_argv():
    argv = sys.argv

    if "--" in argv:
        # Running from CLI using Blender with arguments after "--"
        argv = argv[argv.index("--") + 1:]
    elif os.path.basename(__file__) in argv[0]:
        # Running from CLI with the scripts alone using the standalone bpy library
        argv = argv[1:] # remove the script name from the arguments
        pass  
    else:
        # e.g. running from Blender GUI
        argv = [] # don't parse anything and use default values

    print(f"Arguments: {argv}")
    return argv



# === ENTRY POINT ===

if __name__ == "__main__":
    argv = handle_argv()
    args = parse_args(argv)
    main(args)