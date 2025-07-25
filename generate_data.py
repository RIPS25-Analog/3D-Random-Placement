import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np
import glob
import re
import argparse

# Magic debug lines
# bpy.ops.mesh.primitive_cube_add(size=0.2, location=camera.location) 
# bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=camera.location)

# === ADJUSTABLE ARGUMENTS ===

OUTPUT_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data"
HDRI_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\background_hdri"

'''
Total picture = ITERATION * NUM_PICS * NUM_OBJ
'''
ITERATION = 1 # Number of scene/background, each with unique object arrangement
NUM_OBJ = 1 # Number of objects selected to be visible on the scene
NUM_PICS = 1 # Number of pictures taken around per object

NUM_DISTRACTOR = 3 # Number of distractors selected to be visible on the scene

LIGHT_ON = False # Set to true if we want additional lighting
LIGHT_ENERGY = 50 # How strong the light is
LIGHT_DISTANCE = 10 # How far the light is from the center of the scene

RENDER_PERCENTAGE = 50 # Original size is 1920 x 1080

SAVE_FILES = True # Set to true if we want to render the final images
USE_RAY_CAST = False # Set to true if use ray cast for occulsion detection (very slow)



# === INTERNAL VARIABLES ===

LABEL_NAMES = ["screwdriver", "wrench"] # TODO: make it automate as well

CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 0.4 # Range for X-axis
Y_RANGE = 0.4 # Range for Y-axis
Z_RANGE = 0.2 # Range for Z-axis

TARGET_SIZE = 0.2 # Target size for objects after scaling
EPS = 0.05 # Size deviation for randomness

ZOOM_DISTANCE = 1 # Distance to zoom the camera backward from an object



# === DEFINE CAMERA BEHAVIOR ===

def get_viewpoints(center, radius):
    viewpoints = []

    for i in range(NUM_PICS):
        z = 2 * random.random() - 1  # z ∈ [-1, 1]
        theta = 2 * np.pi * random.random()
        r_xy = np.sqrt(1 - z * z)

        x = r_xy * np.cos(theta)
        y = r_xy * np.sin(theta)

        # Apply radius and center offset
        pos = (
            center[0] + radius * x,
            center[1] + radius * y,
            center[2] + radius * z
        )
        viewpoints.append(pos)
    
    return viewpoints

def look_at(obj, target):
    direction = (target - obj.location).normalized()
    quat = direction.to_track_quat('-Z', 'Y') 
    obj.rotation_euler = quat.to_euler()


def zoom_on_object(camera, center, bbox_corners, depsgraph):
    # Point camera at the object
    look_at(camera, center)

    # Get object 3D bounding box
    coords = [coord for corner in bbox_corners for coord in corner]
    
    # Zoom to where the entire object will fit in view
    bpy.context.view_layer.update()
    location, _scale = camera.camera_fit_coords(depsgraph, coords)
    camera.location = location

    # Zoom away from the object
    forward = camera.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 0.0, -1.0))
    camera.location -= forward * ZOOM_DISTANCE



# === GET BOUNDING BOXES ===

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
    
    # Get the transformation matrix columns
    matrix = obj.matrix_world
    col0 = matrix.col[0]
    col1 = matrix.col[1]
    col2 = matrix.col[2]
    col3 = matrix.col[3]

    # Initialize min, max, and depth values for 2D bounding box
    minX = minY = 1
    maxX = maxY = 0
    depth = 0

    # Determine the number of vertices to iterate over
    mesh = obj.data
    numVertices = len(mesh.vertices)

    vertices_world_pos = []
    
    for t in range(0, numVertices):
        # Get the vertex position
        co = mesh.vertices[t].co

        # WorldPos = X - axis⋅x + Y- axis⋅y + Z - axis⋅z + Translation
        pos_hom = (col0 * co[0]) + (col1 * co[1]) + (col2 * co[2]) + col3
        pos = mathutils.Vector(pos_hom[:3])
        
        # Get the vertices that are visible from the camera
        if not is_obscured(scene, depsgraph, pos, camera.location):
            vertices_world_pos.append(pos)

    # Almost totally occluded, return invalid bounding boxes
    if len(vertices_world_pos) <= 1:
        return 0, 0, 0, 0, -1
    
    # Iterate through each vertex
    for pos in vertices_world_pos:

        # maps a 3D point in world space into normalized camera view coordinates
        pos = bpy_extras.object_utils.world_to_camera_view(scene, camera, pos)
        depth += pos.z

        # Update min and max values as needed
        if (pos.x < minX):
            minX = pos.x
        if (pos.y < minY):
            minY = pos.y
        if (pos.x > maxX):
            maxX = pos.x
        if (pos.y > maxY):
            maxY = pos.y

    # Average out depth
    depth /= numVertices 

    # Clamp to [0, 1]
    minX = max(0.0, min(minX, 1.0))
    minY = max(0.0, min(minY, 1.0))
    maxX = max(0.0, min(maxX, 1.0))
    maxY = max(0.0, min(maxY, 1.0))

    return minX, minY, maxX, maxY, depth



# === CHECK BOX OVERLAPPING ===

def is_overlapping_1D(box1, box2):
    # (min, max)
    return box1[1] >= box2[0] and box2[1] >= box1[0]

def is_overlapping_2D(box1, box2):
    # (minX, minY, maxX, maxY)
    box1_x = (box1[0], box1[2])
    box1_y = (box1[1], box1[3])
    box2_x = (box2[0], box2[2])
    box2_y = (box2[1], box2[3])
    return is_overlapping_1D(box1_x, box2_x) and is_overlapping_1D(box1_y, box2_y)



# === OBJECTS AUGMENTATION ===

def rescale_object(obj, target_size=TARGET_SIZE, eps=EPS, apply=True): 
    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    # Get size in each axis
    min_corner = mathutils.Vector(map(min, zip(*bbox_corners)))
    max_corner = mathutils.Vector(map(max, zip(*bbox_corners)))
    dimensions = max_corner - min_corner

    # Find largest dimension (width, height, depth)
    current_size = max(dimensions)

    final_size = target_size + random.uniform(-eps, eps)

    # Compute scale factor
    scale_factor = final_size / current_size

    # Apply uniform scaling to the object
    obj.scale *= scale_factor

    if apply:
        # Apply the scale to avoid future issues
        bpy.context.view_layer.update()  # update for bbox recalculation
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def translate_object(obj, center=CENTER, x_range=X_RANGE, y_range=Y_RANGE, z_range=Z_RANGE):
    x = random.uniform(center.x - x_range, center.x + x_range)
    y = random.uniform(center.y - y_range, center.y + y_range)
    z = random.uniform(center.z - z_range, center.z + z_range)
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

def add_hdri_background(scene, hdri_path):
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    hdri_files = glob.glob(hdri_path + r"\*.exr")
    print(hdri_path)

    selected_hdri = random.choice(hdri_files)

    print(f"Chosen background: {selected_hdri}")

    # Clear existing nodes
    nodes.clear()

    # Create nodes
    env_tex = nodes.new(type="ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(selected_hdri)
    env_tex.location = (-800, 0)

    background = nodes.new(type="ShaderNodeBackground")
    background.location = (-400, 0)

    world_output = nodes.new(type="ShaderNodeOutputWorld")
    world_output.location = (0, 0)

    # Link nodes
    links.new(env_tex.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], world_output.inputs["Surface"])

    # Add Texture Coordinate and Mapping nodes
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-1200, 0)

    # Rotate HDRI
    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-1000, 0)
    mapping.inputs['Rotation'].default_value[2] = 1.57  # Rotate around Z (in radians)

    # Link coordinate chain
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])

    scene.render.film_transparent = False



# === ARRANGE AND RENDER OBJECTS ===

def get_selected_objects(original_transforms, label_names, num_obj, num_distractor):
    all_objects = [] # (obj, label)
    all_distractors = [] # (obj, label)

    # Select all objects from the scene
    for label in label_names:
        collection = bpy.data.collections[label]
        for obj in collection.objects:
            if obj.type == 'MESH':
                obj.hide_render = True
                all_objects.append((obj, label))

    # Select all distractors from the scene
    distractors = bpy.data.collections["distractors"]
    for distractor in distractors.objects:
        if distractor.type == 'MESH':
            distractor.hide_render = True
            all_distractors.append((distractor, "distractors"))

    # Randomly select some of the objects
    selected_objects = random.sample(all_objects, min(num_obj, len(all_objects)))
    selected_distractors = random.sample(all_distractors, min(num_distractor, len(all_distractors)))

    for obj, _label in selected_objects + selected_distractors:
        obj.hide_render = False

        # Store initial states of the object
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

def get_visible_bbox(scene, camera, depsgraph, selected_objects):
    visible_bboxes = dict()

    for obj, label in selected_objects:
        # Get bounding box in camera's view
        minX, minY, maxX, maxY, depth = get_2d_bounding_box(obj, camera, scene, depsgraph)
        
        # Initialize visibility to be False
        is_visible = False

        # Check visibility from camera
        if depth > 0:
            bbox = (minX, minY, maxX, maxY)
            offset = 0.05
            cam_box = (0 + offset, 0 + offset, 1 - offset, 1 - offset)

            is_visible = is_overlapping_2D(bbox, cam_box)

        if is_visible:
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



# === OCCLUSION DETECTION WITH RAY CAST ===

def bilerp(p00, p10, p11, p01, u, v):
    """
    Bilinear interpolation of a quad.
    Points:
        p00 = bottom_left
        p10 = bottom_right
        p11 = top_right
        p01 = top_left
    u: horizontal fraction (0 = left, 1 = right)
    v: vertical fraction (0 = bottom, 1 = top)
    """
    return (
        (1 - u) * (1 - v) * p00 +
        u       * (1 - v) * p10 +
        u       * v       * p11 +
        (1 - u) * v       * p01
    )

def get_visible_bbox_using_ray_cast(scene, camera, depsgraph, pass_index_to_label):
    # Get camera's position and focal length
    mat_world = camera.matrix_world
    focal_length = 1 if camera.type == 'ORTHO' else camera.data.display_size

    # Get the corners of camera's visible area
    cam_corners = [mat_world @ (focal_length * point) for point in camera.data.view_frame(scene=scene)]
    p11, p10, p00, p01 = cam_corners

    img_width = scene.render.resolution_x 
    img_height = scene.render.resolution_y

    # Initialize an empty image mask with all zeros
    image_mask = np.zeros((img_width+1, img_height+1), dtype=np.uint8) 

    visible_obj_index = set()
    visible_bboxes = dict()

    #  the image mask
    for i in range(img_width+1):
        for j in range(img_height+1):
            u = i / img_width
            v = j / img_height
            pos = bilerp(p00, p10, p11, p01, u, v)

            # Use ray cast to determine if any object is visible in a particulat direction
            direction = (pos - camera.location).normalized()
            hit_bool, _location, _normal, _index, hit_obj, _matrix = scene.ray_cast(depsgraph, camera.location, direction)

            # We're only interested in objects with predefined indices
            if hit_bool and hit_obj.pass_index != 0:
                # Change the index in the image mask if the ray cast hits something
                image_mask[i, j] = hit_obj.pass_index

                # Store the object as a visible object
                visible_obj_index.add(hit_obj.pass_index)    

    # For each visible object, find bounding box scaled to [0, 1]
    for obj_index in visible_obj_index:
        if obj_index == 0:
            continue

        minX = minY = 1
        maxX = maxY = 0

        for i in range(img_width):
            for j in range(img_height):
                index = image_mask[i, j]
                if index == obj_index:
                    pos = mathutils.Vector((
                        i / img_width, 
                        j / img_height
                    ))
                    if (pos.x < minX):
                        minX = pos.x
                    if (pos.y < minY):
                        minY = pos.y
                    if (pos.x > maxX):
                        maxX = pos.x
                    if (pos.y > maxY):
                        maxY = pos.y

        label = pass_index_to_label[obj_index]

        # Convert to YOLO format
        x_center = (minX + maxX) / 2
        y_center = 1 - (minY + maxY) / 2 # flip y-axis
        width = maxX - minX
        height = maxY - minY

        visible_bboxes.update({
            (x_center, y_center, width, height) : label
        })



# === CAPTURE VIEWS ===

def capture_views(obj, camera, scene, depsgraph, selected_objects, output_folder, pass_index_to_label, iter, save_files, use_ray_cast):
    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]

    # Get center and size
    center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
    max_dist = max((corner - center).length for corner in bbox_corners)

    # Get a list of camera positions
    viewpoints = get_viewpoints(center, max_dist)

    print(f"\n-------------------- Taking photos around {obj.name} --------------------\n")
    
    # Iterate through all viewpoints around one object
    for i, pos in enumerate(viewpoints):
        # Move camera to position
        camera.location = pos
        zoom_on_object(camera, center, bbox_corners, depsgraph)

        print(f"-------------------- View angle {i+1} --------------------")
        
        # Get bounding boxes for visible objects
        if use_ray_cast:
            visible_bboxes = get_visible_bbox_using_ray_cast(scene, camera, depsgraph, pass_index_to_label)
        else:
            visible_bboxes = get_visible_bbox(scene, camera, depsgraph, selected_objects)

        if save_files:
            # Save the image
            img_path = rf"{output_folder}\images\{iter+1}_{obj.name}_{i+1}.jpg"
            scene.render.image_settings.file_format = 'JPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.filepath = img_path
            bpy.ops.render.render(write_still=True)
            
            # Save the annotation file
            label_path = rf"{output_folder}\labels"
            label_file_path = rf"{label_path}\{iter+1}_{obj.name}_{i+1}.txt"
            os.makedirs(label_path, exist_ok=True)
            
            with open(label_file_path, "w") as f:
                for bbox, label in visible_bboxes.items():
                    x_center, y_center, width, height = bbox
                    f.write(f"{label} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        print()



# === SETUPS ===

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

def setup_output_folder(output_path):
    # Regex to match folders like: attempt_7_with_100_iterations
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

    return output_folder



# === MAIN ===

def main(args):
    # Common object setups
    scene = bpy.context.scene
    camera = bpy.data.objects["Camera"]
    light = bpy.data.objects["Light"]
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # Renderer setup
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_percentage = args.render_percentage
    
    label_names = LABEL_NAMES

    # Give each object a unique pass index and record their coresponding labels
    pass_index_to_label = {}
    if args.use_ray_cast:
        pass_index_to_label = setup_pass_index_to_label(label_names)

    # Switch light on or off
    if args.light_on:
        light.data.energy = args.light_energy
    else:
        light.data.energy = 0

    output_folder = setup_output_folder(args.output_path)

    print(args.hdri_path)
    
    original_transforms = {} # Stores initial object transforms

    for iter in range(args.iteration):
        print(f"\n======================================== Starting iteration {iter+1} ========================================\n")

        # Pick a background
        add_hdri_background(scene, args.hdri_path)

        # Make a subfolder for each iteration
        if args.iteration > 1:
            output_subfolder = os.path.join(output_folder, f"iter_{iter+1}")
        else:
            output_subfolder = output_folder
        
        # Randomly select objects to render
        selected_objects, selected_distractors = get_selected_objects(original_transforms, 
                                                                      label_names, 
                                                                      args.num_obj, args.num_distractor)

        # Add random lighting
        if args.light_on:
            translate_object(light, 
                             x_range = args.light_distance, 
                             y_range = args.light_distance, 
                             z_range = args.light_distance)
            look_at(light, CENTER)     

        bpy.context.view_layer.update()

        # Capture selected objects
        for obj, _label in selected_objects:
            capture_views(obj, camera, scene, depsgraph, 
                          selected_objects, output_subfolder, pass_index_to_label, iter, 
                          args.save_files, args.use_ray_cast)

        # Restore previous locations
        for obj, _label in selected_objects + selected_distractors:
            t = original_transforms[obj.name]
            obj.location = t['location']
            obj.rotation_euler = t['rotation']
            obj.scale = t['scale']

        # Clean up
        original_transforms.clear()
        bpy.context.view_layer.update()

    # Reset pass index
    for obj in bpy.data.objects:
        obj.pass_index = 0

    print("\n======================================== Render loop is finished ========================================\n")

def parse_args():
    '''Parse input arguments
    '''
    parser = argparse.ArgumentParser(description = "Create synthetic data with 3D objects.")

    parser.add_argument("--hdri_path",
        help = "The directory which contains hdri backgrounds.", 
        #nargs = "?", 
        default = HDRI_PATH)
    
    parser.add_argument("--output_path",
        help = "The directory where images and labels will be created and stored.", 
        #nargs = "?", 
        default = OUTPUT_PATH)
    
    parser.add_argument("--iteration",
        help = "Number of iteration, each with different background and object arrangement.", 
        #nargs = "?", 
        default = ITERATION, 
        type = int)
    
    parser.add_argument("--num_obj", 
        help = "Number of total objects visible in the 3D scene.", 
        #nargs = "?", 
        default = NUM_OBJ, 
        type = int)
    
    parser.add_argument("--num_pics", 
        help = "Number of objects visible in the 3D scene.", 
        #nargs = "?", 
        default = NUM_PICS, 
        type=int)
    
    parser.add_argument("--num_distractor", 
        help = "Number of distractors visible in the 3D scene.", 
        #nargs = "?", 
        default = NUM_DISTRACTOR, 
        type = int)
    
    parser.add_argument("--light_on",
        help = "Set to True if we want to add an additional light source. Default is False.", 
        action = "store_false")
    
    parser.add_argument("--light_energy", 
        help = "how strong the light is.", 
        default = LIGHT_ENERGY, 
        type = int)
    
    parser.add_argument("--light_distance", 
        help = "How far the light is from the center of the scene.", 
        default = LIGHT_DISTANCE, 
        type = int)
    
    parser.add_argument("--render_percentage", 
        help = "Scale down the rendered image to __%. Original size is 1920 x 1080.", 
        default = RENDER_PERCENTAGE, 
        type = int)
    
    parser.add_argument("--save_files",
        help = "Set to True if we want to store the images and labels. Default is True.", 
        action = "store_true")
    
    parser.add_argument("--use_ray_cast",
        help = "Set to True if we want to use ray cast for precise bbox detection (very slow). Default is false.", 
        action = "store_false")
    
    args = parser.parse_args()
    return args



if __name__ == "__main__":
    args = parse_args()
    print(args.hdri_path)
    main(args)