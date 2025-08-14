import bpy   
import mathutils 
import bpy_extras
import numpy as np
import random

import os
import glob
import re
import sys
import argparse
import yaml
import time

HDRI_PATH = r"/home/data/3d_render/background_hdri"
OBJ_PATH = r"/home/data/3d_render/objects"
OUTPUT_PATH = r"/home/data/3d_render/output"

r'''HDRI_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\background_hdri"
OBJ_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\objects"
OUTPUT_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\output"'''

RANDOM_SEED = 0 # For reproducibility

ITERATION = 1 # Number of scene/backgrounds to generate
ARRANGEMENT = 5 # Number of arrangements per iteration
NUM_PICS = 20 # Number of pictures taken around per object
LIGHT_ENERGY = 50 # Maximum light intensity for the scene

RENDER_PERCENTAGE = 0.5 # Downscales the image, original size is 1920 x 1080
SAMPLES = 16 # Number of samples per image
TILE_SIZE = 4096 # Tile size for rendering

VISIBLE_PERCENTAGE = 0.2 # Minimum percentage of visible bounding box to be considered valid
SAVE_FILES = True # Set to true to render the final images (for debugging, we can set it to False)



# === INTERNAL VARIABLES ===

OBJ_EXT = ['.obj', '.stl', '.usd', '.usdc', '.usda', '.fbx', '.gltf', '.glb']

CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 0.4 # Range for X-axis
Y_RANGE = 0.4 # Range for Y-axis
Z_RANGE = 0.2 # Range for Z-axis

TARGET_SIZE = 0.2 # Target size for objects after scaling
EPS = 0.05 # Size deviation for randomness



# === DEFINE CAMERA BEHAVIOR ===

def get_viewpoint(center, max_dist):
    z = 2 * random.random() - 1  # z ∈ [-1, 1]
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

def rescale_object(obj, target_size=TARGET_SIZE, eps=EPS, apply=True): 
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
    x = random.uniform(center.x - x_range, center.x + x_range)
    y = random.uniform(center.y - y_range, center.y + y_range)
    z = random.uniform(center.z - z_range, center.z + z_range)
    obj.location = (x, y, z)

def translate_object_on_surface(obj, x_range, y_range, z_range, center=CENTER):
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



# === ADD BACKGROUND ===

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
    multiply.location = (-600, 0)
    background.location = (-200, 0)
    world_output.location = (0, 0)
    
    # Link nodes
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
    links.new(env_tex.outputs["Color"], multiply.inputs["Color1"])
    links.new(multiply.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], world_output.inputs["Surface"])
    
    scene.render.film_transparent = False

def update_hdri_settings(scene, hdri_path, brightness):
    world = scene.world
    nodes = world.node_tree.nodes

    env_tex = nodes.get("EnvironmentTexture")
    multiply = nodes.get("HDRIMultiply")

    env_tex.image = bpy.data.images.load(hdri_path)

    multiply.inputs['Color2'].default_value = (brightness, brightness, brightness, 1.0)



# === GET BOUNDING BOXES ===

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

def is_obscured(scene, depsgraph, origin, destination):
    # get the direction
    direction = (destination - origin)
    distance = direction.length
    direction = direction.normalized()

    # Add small offset distance to avoid colliding with itself
    offset = 0.01  
    origin = origin + direction * offset

    # cast a ray from origin to destination
    hit_bool, _location, _normal, _index, _hit_obj, _matrix = scene.ray_cast(depsgraph, origin, direction, distance=distance)

    return hit_bool

def get_2d_bounding_box(obj, camera, scene, depsgraph):
    # Update view layer to get the most recent coordinates
    bpy.context.view_layer.update()
    
    # Determine the number of vertices to iterate over
    obj_vertices = obj.data.vertices
    num_total_vertices = len(obj_vertices)
    
    vertices_in_cam = []
    vertices_visible_in_cam = []
    
    for i in range(0, num_total_vertices):
        # Get the vertex position
        local_pos = obj_vertices[i].co
        world_pos = obj.matrix_world @ local_pos

        # maps a 3D point in world space into normalized camera view coordinates
        cam_pos = bpy_extras.object_utils.world_to_camera_view(scene, camera, world_pos)
        
        is_visible = not is_obscured(scene, depsgraph, world_pos, camera.location)
        is_in_frustum = (0 <= cam_pos.x <= 1) and (0 <= cam_pos.y <= 1)
        is_in_front = cam_pos.z > 0
        
        # Get the vertices that are in front of the camera
        if is_in_front:
            vertices_in_cam.append(cam_pos)
            
            # Get the vertices that are actually visible
            if is_visible and is_in_frustum:
                vertices_visible_in_cam.append(cam_pos)
            
    num_visible_vertices = len(vertices_visible_in_cam)

    # If there are not enough visible vertices, return bounding box with no volume
    if num_visible_vertices * 10 < num_total_vertices:
        return 0, 0, 0, 0, 0
    
    # Initialize min, max for 2D bounding box
    minX = minY = minX_visible = minY_visible = 1
    maxX = maxY = maxX_visible = maxY_visible = 0
    
    # Iterate through vertices in front of the camera
    for pos in vertices_in_cam:
        if (pos.x < minX):
            minX = pos.x
        if (pos.y < minY):
            minY = pos.y
        if (pos.x > maxX):
            maxX = pos.x
        if (pos.y > maxY):
            maxY = pos.y
    
    area = (maxX - minX) * (maxY - minY)
    
    # Iterate through actually visible vertices
    for pos in vertices_visible_in_cam:
        if (pos.x < minX_visible):
            minX_visible = pos.x
        if (pos.y < minY_visible):
            minY_visible = pos.y
        if (pos.x > maxX_visible):
            maxX_visible = pos.x
        if (pos.y > maxY_visible):
            maxY_visible = pos.y
            
    visible_area = (maxX_visible - minX_visible) * (maxY_visible - minY_visible)
    
    # Determine the percentage of visible part v.s. whole part
    vis_percentage = visible_area / area

    return minX_visible, minY_visible, maxX_visible, maxY_visible, vis_percentage

def get_visible_bbox(scene, camera, depsgraph, selected_objects, visible_percentage):
    visible_bboxes = dict()

    for obj, label in selected_objects:
        # Get bounding box in camera's view
        minX, minY, maxX, maxY, vis_percentage = get_2d_bounding_box(obj, camera, scene, depsgraph)
        
        if vis_percentage > visible_percentage:
            # Convert to YOLO format
            x_center = (minX + maxX) / 2
            y_center = 1 - (minY + maxY) / 2 # flip y-axis
            width = maxX - minX
            height = maxY - minY

            # Store label {bbox : label}
            visible_bboxes.update({
                (x_center, y_center, width, height) : label
            })

    return visible_bboxes



# === RENDER AND SAVE FILES ===

def capture_views(camera, scene, depsgraph, selected_objects, selected_distractors, 
                  atmpt, seed, arngmnt, iter, 
                  visible_percentage, num_pics, output_folder, save_files):
    
    # Get the bounding box for all objects (so that the camera can zoom out to fit)
    all_objects = selected_objects + selected_distractors
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

        while distance_too_close(camera, selected_objects + selected_distractors, min_distance * 0.4):
            # If the camera is too close to any object, get a new viewpoint
            camera.location = get_viewpoint(center, max_dist)
            min_distance = zoom_on_object(camera, center, all_corners, depsgraph)

        print(f"-------------------- Arrangment {arngmnt+1}; View angle {i+1} --------------------")
        
        # Get bounding boxes for visible objects
        visible_bboxes = get_visible_bbox(scene, camera, depsgraph, selected_objects, visible_percentage)

        if save_files:            
            file_name = f"{atmpt}({seed})_{iter+1}_{arngmnt+1}_{i+1}"

            # Save the image
            img_path = os.path.join(output_folder, "images", f"{file_name}.jpg")
            scene.render.image_settings.file_format = 'JPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.filepath = img_path
            bpy.ops.render.render(write_still=True)
            
            # Make sure the labels folder exists
            label_path = os.path.join(output_folder, "labels")
            os.makedirs(label_path, exist_ok=True)

            # Save the annotation file
            label_file_path = os.path.join(label_path, f"{file_name}.txt")
            
            with open(label_file_path, "w") as f:
                for bbox, label in visible_bboxes.items():
                    x_center, y_center, width, height = bbox
                    f.write(f"{label} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        print()



# === PRE-RENDER SETUP ===

def setup_pass_index_to_label(lable_names):
    pass_index_to_label = dict()
    pass_index = 1

    for label in lable_names:
        # Get the collection of objects belonging to the same label class
        collection = bpy.data.collections[label]

        # Assign each object a unique index
        for obj in collection.objects:
            obj.pass_index = pass_index
            pass_index_to_label.update({pass_index : label})
            pass_index += 1

    return pass_index_to_label

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

        yaml_path = os.path.join(output_folder, f"args_{next_attempt}.yaml")
        with open(yaml_path, "w") as f:
            yaml.dump(vars(args), f)

    return output_folder, yaml_path, next_attempt

def get_selected_objects(original_transforms, label_names):
    objects = [] # (obj, label)
    distractors = [] # (obj, label)

    selected_objects = []
    selected_distractors = []

    # Select all objects from the scene
    for label in label_names:
        collection = bpy.data.collections[label]
        for obj in collection.objects:
            if obj.type == 'MESH':
                obj.hide_render = True
                objects.append((obj, label))
    
    # Randomly select some of the objects
    num_obj_ran = random.randint(0, 2)
    selected_objects = random.sample(objects, num_obj_ran)

    # Select all distractors from the scene
    if "distractors" in bpy.data.collections:
        collection = bpy.data.collections["distractors"]
        for distr in collection.objects:
            if distr.type == 'MESH':
                distr.hide_render = True
                distractors.append((distr, "distractors"))
        
        # Total objects is [3, 6]
        num_distractor_ran = random.randint(3, 6) - num_obj_ran
        selected_distractors = random.sample(distractors, num_distractor_ran)

    for obj, _label in selected_objects + selected_distractors:
        obj.hide_render = False

        # Store initial states of the object so that we can restore them later
        original_transforms[obj.name] = {
            'location': obj.location.copy(),
            'rotation': obj.rotation_euler.copy(),
            'scale': obj.scale.copy()
        }

        # Add augmentation to both target objects and distractors
        rescale_object(obj)
        translate_object(obj)
        rotate_object(obj)

    return selected_objects, selected_distractors



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
    label_names = set()
    
    category_folders = glob.glob(f"{obj_path}/*/")

    # Iterate through all category folders under the objects folder
    for category_folder in category_folders:
        category_name = os.path.basename(os.path.dirname(category_folder))
        
        # Create new collection
        new_coll = bpy.data.collections.new(category_name)
        scene.collection.children.link(new_coll)

        # Exclude distractors from the categories
        if category_name.lower() not in {"distractor", "distractors"}:
            label_names.add(category_name)

        obj_folders = glob.glob(f"{category_folder}/*/")

        # Iterate through all object folders within same category
        for obj_folder in obj_folders:

            # Iterate through all files in the object folder and try to find the mesh file
            for file_path in glob.glob(f"{obj_folder}/*"):
                # Get the file extension
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                obj_ext = os.path.splitext(file_path)[1].lower()

                # Import the object based on its file extension
                if obj_ext in OBJ_EXT:
                    print(f"Importing {file_path}...")

                    if obj_ext == '.obj':
                        bpy.ops.wm.obj_import(filepath=file_path)
                    elif obj_ext == '.stl':
                        bpy.ops.wm.stl_import(filepath=file_path)
                    elif obj_ext in ('.usd', '.usdc', '.usda'):
                        bpy.ops.wm.usd_import(filepath=file_path)
                    elif obj_ext == '.fbx':
                        bpy.ops.import_scene.fbx(filepath=file_path)
                    elif obj_ext in ('.gltf', '.glb'):
                        bpy.ops.import_scene.gltf(filepath=file_path)
                    
                    # Rename the object to the file name
                    new_obj = bpy.context.view_layer.objects.active
                    new_obj.name = file_name  

                    # Set the origin to center
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

                    break  # Stop after the first valid file
            
            for coll in new_obj.users_collection:
                coll.objects.unlink(new_obj)
            
            # Link the object to the new collection
            new_coll.objects.link(new_obj)

            # Move the object away from the origin to avoid unintentional occlusion
            translate_object(new_obj, center=mathutils.Vector((100, 100, 100)))  
            rescale_object(new_obj)  

    return list(label_names)  # Return the list of label names for future processing

def render_setup(scene, render_percentage):
    # Renderer setup
    scene.render.engine = 'CYCLES'
    #scene.render.engine = 'BLENDER_EEVEE'

    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    prefs.get_devices()  # Populate available devices
    prefs.use_cuda = True

    # Activate all GPU devices (optional but common)
    for device in prefs.devices:
        device.use = True
    
    scene.cycles.samples = args.samples
    scene.cycles.tile_size = args.tile_size

    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.use_progressive_refine = False
    scene.cycles.device = "GPU"

    scene.render.use_persistent_data = False
    scene.render.resolution_percentage = int(render_percentage * 100)



# === MAIN FUNCTION ===

def main(args):
    random.seed(args.seed)  # Set the random seed for reproducibility

    start_time = time.time()

    print("Main is running")
    scene = bpy.context.scene

    clear_stage(scene)
    render_setup(scene, args.render_percentage)

    # Add default camera and light
    camera, light = add_default_obj(scene)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # Import objects
    label_names = import_obj(scene, args.obj_path)

    # Setup light energy
    light_energy_ran = random.randint(0, args.light_energy)
    light.data.energy = light_energy_ran

    # Set the output folder
    output_folder, yaml_path, atmpt = setup_output_folder(args.output_path, not args.dont_save) 

    # Collect hdri files and build the world tree
    hdri_files = glob.glob(args.hdri_path + r"/*.exr")
    add_hdri_background(scene, hdri_files[0])  # Add the first hdri as a default background

    # Stores the initial object transforms so that we can restore them later
    original_transforms = {} 

    # Iterate through the number of background we want to generate
    for iter in range(min(args.iteration, len(hdri_files))):
        print(f"\n======================================== Starting iteration {iter+1} ========================================\n")

        # Pick a background
        selected_hdri = random.choice(hdri_files)
        hdri_files.remove(selected_hdri)  # Remove the selected hdri to avoid repetition

        # Make a subfolder for each iteration
        hdri_name = os.path.basename(selected_hdri).split('.')[0]
        output_subfolder = os.path.join(output_folder, f"{iter+1}_{hdri_name}")

        # Iterate through different object arrangements of the same scene
        for arngmnt in range(args.arrangement):
            
            # Randomly select objects to render
            selected_objects, selected_distractors = get_selected_objects(original_transforms, label_names)

            # Adjust the background exposure
            brightness = random.uniform(0.5, 1) if random.random() < 0.5 else random.uniform(1, 10)
            update_hdri_settings(scene, selected_hdri, brightness)

            # Add random lighting
            translate_object_on_surface(light, 
                                    x_range = 6, 
                                    y_range = 6, 
                                    z_range = 6)
            look_at(light, CENTER)

            # Add cube to create shadow effects
            bpy.ops.mesh.primitive_cube_add(
                size=2,                # Cube edge length (default is 2)
                location=light.location,    # X, Y, Z coordinates
                rotation=(0, 0, 0)     # Rotation in radians
            )

            # Update the scene
            bpy.context.view_layer.update()

            # Capture selected objects
            capture_views(camera, scene, depsgraph, selected_objects, selected_distractors, 
                          atmpt, args.seed, arngmnt, iter, 
                          args.visible_percentage, args.num_pics, output_subfolder, not args.dont_save)
            
            # Restore previous locations so that the objects won't overlap in the next iteration
            # to create unintentional occlusion
            for obj, _label in selected_objects + selected_distractors:
                t = original_transforms[obj.name]
                obj.location = t['location']
                obj.rotation_euler = t['rotation']
                obj.scale = t['scale']

            # Clean up the storage and update the scene
            original_transforms.clear()
            bpy.context.view_layer.update()

            # Remove the dummy cube that was added for shadow effects
            obj = bpy.data.objects.get("Cube")
            bpy.data.objects.remove(obj, do_unlink=True)

        # End of arrangement loop

    # End of iteration loop

    print(f"Output folder: {output_folder}")
    print("\n======================================== Render loop is finished ========================================\n")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"\nTotal execution time: {execution_time:.2f} seconds")

    with open(yaml_path, "a") as f:
        yaml.dump(f"\n# Total execution time: {execution_time:.2f} seconds", f)



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
    
    parser.add_argument("--iteration",
        help = "Number of iteration, each with different background and object arrangement.", 
        default = ITERATION, 
        type = int)
    
    parser.add_argument("--num_pics", 
        help = "Number of objects visible in the 3D scene.", 
        default = NUM_PICS, 
        type=int)
    
    parser.add_argument("--arrangement",
        help = "Number of arrangements per iteration.", 
        default = ARRANGEMENT, 
        type = int)
    
    parser.add_argument("--light_energy", 
        help = "how strong the light is.", 
        default = LIGHT_ENERGY, 
        type = int)
    
    parser.add_argument("--visible_percentage",
        help = "Minimum percentage of visible bounding box to be considered valid.", 
        default = VISIBLE_PERCENTAGE, 
        type = float)
    
    parser.add_argument("--render_percentage", 
        help = "Scale down the rendered image to __%. Original size is 1920 x 1080.", 
        default = RENDER_PERCENTAGE, 
        type = float)
    
    parser.add_argument("--samples",
        help = "Number of samples per image.", 
        default = SAMPLES, 
        type = int)
    
    parser.add_argument("--tile_size",
        help = "Tile size for rendering.", 
        default = TILE_SIZE, 
        type = int)
    
    parser.add_argument("--dont_save",
        help = "Set to True if we don't want to store the images and labels.", 
        action = "store_true")
    
    parser.add_argument("--seed",
        help = "Set the random seed for reproducibility.", 
        default = RANDOM_SEED, 
        type = int)
    
    args = parser.parse_args(argv)
    return args

def handle_argv():
    argv = sys.argv

    if "--" in argv:
        # Running from CLI using Blender with arguments after "--"
        argv = argv[argv.index("--") + 1:]
    elif os.path.basename(__file__) in argv[0] and len(argv) > 1:
        # Running from CLI with the scripts alone (using bpy library)
        argv = argv[1:] # remove the script name from the arguments
        pass  
    else:
        argv = [] # don't parse anything and use default values
        if not SAVE_FILES:
            argv.append("--dont_save")

    print(f"Arguments: {argv}")
    return argv



# === ENTRY POINT ===

if __name__ == "__main__":
    argv = handle_argv()
    args = parse_args(argv)
    main(args)