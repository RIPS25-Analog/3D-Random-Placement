import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np

# bpy.ops.mesh.primitive_cube_add(size=0.2, location=camera.location) 

TRANSLATE_CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 4 # Range for X-axis
Y_RANGE = 4 # Range for Y-axis
Z_RANGE = 2 # Range for Z-axis

SCALE_TARGET_SIZE = 3.0 # Target size for objects after scaling
SCALE_EPS = 0.2 # Size deviation for randomness

ZOOM_DISTANCE = 10 # Distance to zoom the camera backward from an object



# Define output locations
categories = ["screwdriver"]
output_location = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data"
bg_image_path = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\background\bg1.jpg"

# Initial setups
scene = bpy.context.scene
camera = bpy.data.objects["Camera"]

depsgraph = bpy.context.evaluated_depsgraph_get()

# Set rendering size and scale
'''scene.render.resolution_x = 800
scene.render.resolution_y = 600
scene.render.resolution_percentage = 50'''



# === DEFINE VIEWPOINTS ===

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



# === GET BOUNDING BOXES ===

def get_2d_bounding_box(obj, camera, scene, use_mesh=True):
    """Returns the 2D bounding box of an object in normalized YOLO format"""
    bpy.context.view_layer.update()
    matrix = obj.matrix_world
    
    # If use_mesh is True, we will use the mesh vertices, otherwise we will use the bounding box
    if use_mesh:
        mesh = obj.data
    else:
        mesh = obj.bound_box
    
    # Get the transformation matrix columns
    col0 = matrix.col[0]
    col1 = matrix.col[1]
    col2 = matrix.col[2]
    col3 = matrix.col[3]

    # Initialize min, max, and depth values for 2D bounding box
    minX = minY = 1
    maxX = maxY = 0
    depth = 0

    # Determine the number of vertices to iterate over
    if use_mesh:
        numVertices = len(obj.data.vertices)
    else:
        numVertices = len(mesh)
    
    # Iterate through each vertex
    for t in range(0, numVertices):
        # Get the vertex position
        if use_mesh:
            co = mesh.vertices[t].co
        else:
            co = mesh[t]

        # WorldPos = X - axis⋅x + Y- axis⋅y + Z - axis⋅z + Translation
        pos = (col0 * co[0]) + (col1 * co[1]) + (col2 * co[2]) + col3

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

def rescale_object(obj, target_size, eps, apply=True): 
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

def translate_object(obj, center, x_range, y_range, z_range):
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



def add_hdri_background(scene):
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    hdri_path = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\background_hdri\IndoorEnvironment.exr"

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



# === RENDER OBJECTS ===

def traverse_tree(t):
    yield t
    for child in t.children:
        yield from traverse_tree(child)

def capture_views(obj, camera, scene, output_folder, zoom_distance, get_mask):
    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]

    # Get center and size
    center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
    max_dist = max((corner - center).length for corner in bbox_corners)

    # Get a list of camera positions
    viewpoints = get_viewpoints(center, max_dist)

    print("Taking photos around " + obj.name + " --------------------\n")

    # Iterate through all viewpoints around one object
    for i, pos in enumerate(viewpoints):
        # Move camera to position
        camera.location = pos
        
        # Point camera at the object
        direction = center - camera.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_quat.to_euler()

        # Get object 3D bounding box
        corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        coords = [coord for corner in corners for coord in corner]
        
        # Zoom to where the entire object will fit in view
        bpy.context.view_layer.update()
        location, foo = camera.camera_fit_coords(depsgraph, coords)
        camera.location = location

        # Zoom away from the object
        forward = camera.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 0.0, -1.0))
        camera.location -= forward * zoom_distance

        visible_bboxes = dict()
        col_tree = scene.collection

        # Iterate through all collections
        #TODO: for i in range(len(categories))
        for col in traverse_tree(col_tree):
            if col.name not in categories:
                continue

            # Iterate through all objects inside one collection
            for inner_obj in col.objects:
                # Skip uninterested objects
                if inner_obj.type != 'MESH' or inner_obj.hide_render:
                    continue

                print("Checking visibility of " + inner_obj.name + ": ", end="")

                label_idx = categories.index(col.name)
                
                '''if label_idx is None:
                    print("Found object that's not supposed to be labeled: " + inner_obj.name)
                    continue'''

                # Get bounding box in camera's view
                minX, minY, maxX, maxY, depth = get_2d_bounding_box(inner_obj, camera, scene)
                
                # Initialize visibility to be False
                is_visible = False

                # Check visibility from camera
                if depth > 0:
                    bbox = (minX, minY, maxX, maxY)
                    eps = 0.1
                    cam_box = (0 + eps, 0 + eps, 1 - eps, 1 - eps)

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

        # Save the image
        img_path = rf"{output_folder}\images\{obj.name}_view_{i+1}.jpg"
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.filepath = img_path
        bpy.ops.render.render(write_still=True)
        
        # Save the annotation file
        label_path = rf"{output_folder}\labels\{obj.name}_view_{i+1}.txt"
        
        with open(label_path, "w") as f:
            for bbox, label_idx in visible_bboxes.items():
                x_center, y_center, width, height = bbox
                f.write(f"{label_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")



# === RENDER LOOP FOR EACH COLLECTION ===

def render_loop(collection_name, output_location, bg_image_path, zoom_distance, get_mask):    
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        print(f"Collection '{collection_name}' not found.")
        return
    
    # Create output folder for a category
    output_folder = os.path.join(output_location, collection_name)
    while os.path.exists(output_folder):
        output_folder = output_folder + "_new"
    os.makedirs(output_folder)

    # Make subfolders
    for subfolder in ["images", "labels"]:
        folder_path = os.path.join(output_folder, subfolder)
        os.makedirs(folder_path, exist_ok=True)

    # TODO: set up how many times we want to augment the objects for each collection
    # TODO: do we want distractors? 
    # - place them randomly or in a specific way? 
    # TODO: add random lighting and shadows (cubes or distractors) to the scene

    # Add augmentation to objects
    for obj in collection.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue

        if get_mask:
            obj.pass_index = MASK_PASS_IDX  

        rescale_object(obj, SCALE_TARGET_SIZE, SCALE_EPS)
        translate_object(obj, TRANSLATE_CENTER, X_RANGE, Y_RANGE, Z_RANGE)
        rotate_object(obj)

    # Capture views for each object
    for obj in collection.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        #add_background(scene, bg_image_path)
        capture_views(obj, camera, scene, output_folder, zoom_distance, get_mask)

    # Reset the pass index for the objects
    for obj in collection.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        obj.pass_index = DEFAULT_PASS_IDX  

    # TODO: set up camera positions and take photos from multiple viewpoints
    # TODO: generate masks for all objects in the scene if GET_ALL_MASKS is True



# === MAIN ===

if __name__ == "__main__":
    # Renderer setup
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    
    add_hdri_background(scene)

    # Generate images for each category
    for i in range(len(categories)):
        # Each category is a collection of meshes in Blender
        collection_name = categories[i]
        render_loop(collection_name, output_location, bg_image_path, ZOOM_DISTANCE, GET_MASK)
