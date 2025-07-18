import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np
import glob

# Magic debug code lines :)))))
# bpy.ops.mesh.primitive_cube_add(size=0.2, location=camera.location) 
# bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=camera.location)

ITERATION = 2
SAVE_FILES = True # Set false for testing stage
RENDER_PERCENTAGE = 50 # Original size is 1920 x 1080

CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 0.4 # Range for X-axis
Y_RANGE = 0.4 # Range for Y-axis
Z_RANGE = 0.2 # Range for Z-axis

NUM_OBJ = 6
NUM_DISTRACTOR = 3
NUM_GEO = 10 

TARGET_SIZE = 0.2 # Target size for objects after scaling
EPS = 0.05 # Size deviation for randomness

ZOOM_DISTANCE = 1 # Distance to zoom the camera backward from an object

OUTPUT_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data"
HDRI_PATH_COL = glob.glob(r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\background_hdri\*.exr")
CATEGORIES = ["screwdriver", "wrench"]



# === DEFINE CAMERA BEHAVIOR ===

def get_viewpoints(center, radius):
    viewpoints = []

    for x in [-1, 0, 1]:
        #for y in [-1, 0, 1]:
            #for z in [-1, 0, 1]:
                y = 1
                z = 1
                if x == 0 and y == 0 and z == 0:
                    continue  # skip center
                pos = center + mathutils.Vector((x, y, z)).normalized() * radius
                viewpoints.append(pos)
    
    return viewpoints

def zoom_on_object(camera, center, bbox_corners, depsgraph):
    # Point camera at the object
    direction = center - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()

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

def rescale_object(obj, apply=True): 
    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    # Get size in each axis
    min_corner = mathutils.Vector(map(min, zip(*bbox_corners)))
    max_corner = mathutils.Vector(map(max, zip(*bbox_corners)))
    dimensions = max_corner - min_corner

    # Find largest dimension (width, height, depth)
    current_size = max(dimensions)

    final_size = TARGET_SIZE + random.uniform(-EPS, EPS)

    # Compute scale factor
    scale_factor = final_size / current_size

    # Apply uniform scaling to the object
    obj.scale *= scale_factor

    if apply:
        # Apply the scale to avoid future issues
        bpy.context.view_layer.update()  # update for bbox recalculation
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def translate_object(obj):
    x = random.uniform(CENTER.x - X_RANGE, CENTER.x + X_RANGE)
    y = random.uniform(CENTER.y - Y_RANGE, CENTER.y + Y_RANGE)
    z = random.uniform(CENTER.z - Z_RANGE, CENTER.z + Z_RANGE)
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

def add_hdri_background(scene):
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    hdri_path = random.choice(HDRI_PATH_COL)

    print(f"Chosen backgroundd: {hdri_path}")

    # === CLEAR EXISTING NODES ===
    nodes.clear()

    # === CREATE NODES ===
    env_tex = nodes.new(type="ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(hdri_path)
    env_tex.location = (-800, 0)

    background = nodes.new(type="ShaderNodeBackground")
    background.location = (-400, 0)

    world_output = nodes.new(type="ShaderNodeOutputWorld")
    world_output.location = (0, 0)

    # === LINK NODES ===
    links.new(env_tex.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], world_output.inputs["Surface"])

    # === OPTIONAL: ROTATE HDRI ===
    # Add Texture Coordinate and Mapping nodes
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-1200, 0)

    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-1000, 0)
    mapping.inputs['Rotation'].default_value[2] = 1.57  # Rotate around Z (in radians)

    # Link coordinate chain
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])

    scene.render.film_transparent = False



# === ARRANGE AND RENDER OBJECTS ===

def get_selected_objects():
    all_objects = [] # (obj, label)
    all_distractors = [] # (obj, label)

    # Select all objects from the scene
    for col_name in CATEGORIES:
        cur_col = bpy.data.collections[col_name]
        for obj in cur_col.objects:
            if obj.type == 'MESH':
                #obj.hide_render = True
                all_objects.append((obj, col_name))

    # Select all distractors from the scene
    distractors = bpy.data.collections["distractors"]
    for distractor in distractors.objects:
        if distractor.type == 'MESH':
            distractor.hide_render = True
            all_distractors.append((distractor, "distractors"))

    # Randomly select some of the objects
    selected_objects = random.sample(all_objects, min(NUM_OBJ, len(all_objects)))
    selected_distractors = random.sample(all_distractors, min(NUM_DISTRACTOR, len(all_distractors)))

    for obj, _label in selected_objects + selected_distractors:
        obj.hide_render = False

        # Add augmentation to both target objects and distractors
        #rescale_object(obj)
        translate_object(obj)
        rotate_object(obj)

    return selected_objects

def get_visible_bbox(scene, camera, depsgraph, selected_objects):
    visible_bboxes = dict()

    for obj, label in selected_objects:
        print("Checking visibility of " + obj.name + ": ", end="")

        # Get label_idx
        label_idx = CATEGORIES.index(label)

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
            print("visible")

            # Convert to YOLO format
            x_center = (minX + maxX) / 2
            y_center = 1 - (minY + maxY) / 2 # flip y-axis
            width = maxX - minX
            height = maxY - minY

            # Store label {bbox : label}
            visible_bboxes.update({
                (x_center, y_center, width, height) : label_idx
            })
        else:
            print("not visible")

    return visible_bboxes

def capture_views(obj, camera, scene, depsgraph, selected_objects, output_folder, iter):
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

        print(f"-------------------- View angle {i} --------------------")
        
        # Get bounding boxes for visible objects
        visible_bboxes = get_visible_bbox(scene, camera, depsgraph, selected_objects)

        if SAVE_FILES:
            # Save the image
            img_path = rf"{output_folder}\images\{iter}_{obj.name}_{i+1}.jpg"
            scene.render.image_settings.file_format = 'JPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.filepath = img_path
            bpy.ops.render.render(write_still=True)
            
            # Save the annotation file
            label_path = rf"{output_folder}\labels\{iter}_{obj.name}_{i+1}.txt"
            
            with open(label_path, "w") as f:
                for bbox, label_idx in visible_bboxes.items():
                    x_center, y_center, width, height = bbox
                    f.write(f"{label_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        print()



# === MAIN ===

def main():
    # Initial setups
    scene = bpy.context.scene
    camera = bpy.data.objects["Camera"]
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # Renderer setup
    scene.render.engine = 'BLENDER_EEVEE_NEXT'

    # Set rendering size and scale
    scene.render.resolution_percentage = RENDER_PERCENTAGE

    # Prepare output directories
    output_folder = os.path.join(OUTPUT_PATH, f"iteration_{7}")
    if SAVE_FILES:
        for subfolder in ["images", "labels"]:
            folder_path = os.path.join(output_folder, subfolder)
            os.makedirs(folder_path, exist_ok=True)

    # Ranger loop
    for iter in range(ITERATION):
        # Pick a background
        add_hdri_background(scene)
        
        # Randomly select objects to render
        selected_objects = get_selected_objects()
        bpy.context.view_layer.update()

        # TODO: add geometry and light

        print(f"\n======================================== Starting iteration {iter} ========================================\n")

        # Capture selected objects
        for obj, _label in selected_objects:
            capture_views(obj, camera, scene, depsgraph, selected_objects, output_folder, iter)



if __name__ == "__main__":
    main()
