import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np


MARGIN = 10 # Margin to ensure the object is not cropped in the image

CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 4 # Range for X-axis
Y_RANGE = 4 # Range for Y-axis
Z_RANGE = 2 # Range for Z-axis

MASK_PASS_IDX = 1 # Pass index for objects we want to generate masks on
DEFAULT_PASS_IDX = 0 # Default pass index for all other objects

GET_MASK = False  # Set to True if you want to generate mask for each object the camera focuses on
GET_ALL_MASKS = False  # Set to True if you want to generate masks for all objects that appear in the scene

# Define output locations
categories = ["screwdriver"]
output_location = r"C:\Users\xlmq4\Documents\GitHub\3D_Data_Generation\data"

# Initial setups
scene = bpy.context.scene
camera = bpy.data.objects["Camera"]



# === SET UP COMPOSITOR TREE ===

def set_compositor_for_masks():
    # Enable compositing with nodes
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()

    # Add necessary nodes
    render_layers = tree.nodes.new(type='CompositorNodeRLayers')    # Render layers
    id_mask = tree.nodes.new(type='CompositorNodeIDMask')           # ID Mask
    viewer = tree.nodes.new(type='CompositorNodeViewer')            # Viewer
    composite = tree.nodes.new(type='CompositorNodeComposite')      # Composite

    # Set Pass Index to match the object
    id_mask.index = MASK_PASS_IDX
    
    # Create Links between nodes
    tree.links.new(render_layers.outputs['IndexOB'], id_mask.inputs['ID value'])
    tree.links.new(id_mask.outputs['Alpha'], viewer.inputs['Image'])
    tree.links.new(id_mask.outputs['Alpha'], composite.inputs['Image'])



# === DEFINE VIEWPOINTS ===

def get_viewpoints(center, radius):
    viewpoints = []

    for x in [-1, 0, 1]:
        #for y in [-1, 0, 1]:
            #for z in [-1, 0, 1]:
                y = 1
                z = 1
                #if x == 0 and y == 0 and z == 0:
                    #continue  # skip center
                pos = center - mathutils.Vector((x, y, z)).normalized() * radius
                viewpoints.append(pos)
                # TODO: I will add variations to viewpoints later
    
    return viewpoints



# === GET BOUNDING BOXES ===

def get_2d_bounding_box(obj, camera, scene, use_mesh=True):
    """Returns the 2D bounding box of an object in normalized YOLO format"""
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

    # Initialize min and max values for 2D bounding box
    minX = 1
    maxX = 0
    minY = 1
    maxY = 0

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
    
        # Update min and max values as needed
        if (pos.x < minX):
            minX = pos.x
        if (pos.y < minY):
            minY = pos.y
        if (pos.x > maxX):
            maxX = pos.x
        if (pos.y > maxY):
            maxY = pos.y
    
    # Save into YOLO format
    x_center = (minX + maxX) / 2
    y_center = 1 - (minY + maxY) / 2 # flip y-axis
    width = maxX - minX
    height = maxY - minY

    return x_center, y_center, width, height



# === RENDER INDIVIDUAL OBJECT ===

def get_object_mask(obj, scene, output_folder, num_of_view):
    # Enable compositor tree
    scene.use_nodes = True
    
    # Setup the object pass index
    obj.pass_index = MASK_PASS_IDX

    # Set output path and file format
    mask_path = rf"{output_folder}\images\{obj.name}_view_{num_of_view}.png"
    scene.render.filepath = mask_path
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'BW'  # Black & White mask

    # Render and save the result
    bpy.ops.render.render(write_still=True)

    # Reset index
    obj.pass_index = DEFAULT_PASS_IDX

    # Disable compositor tree
    scene.use_nodes = False

def capture_views(collection, label_idx, camera, scene, output_folder, get_mask):
    # Disable compositor tree
    scene.use_nodes = False

    for obj in collection.objects:
        if obj.type != 'MESH':
            continue

        # Get bounding box corners in world space
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]

        # Get center and size
        center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
        max_dist = max((corner - center).length for corner in bbox_corners)
        radius = max_dist + MARGIN 

        viewpoints = get_viewpoints(center, radius)

        # Iterate through all viewpoints around one object
        for i, pos in enumerate(viewpoints):
            # Move camera to position
            camera.location = pos

            # Point camera at the object
            direction = center - camera.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            camera.rotation_euler = rot_quat.to_euler()

            # Save the image
            img_path = rf"{output_folder}\images\{obj.name}_view_{i+1}.jpg"
            scene.render.image_settings.file_format = 'JPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.filepath = img_path
            bpy.ops.render.render(write_still=True)
            
            # Save the annotation in YOLO format
            x_c, y_c, w, h = get_2d_bounding_box(obj, camera, scene)
            label_path = rf"{output_folder}\labels\{obj.name}_view_{i+1}.txt"
            with open(label_path, "w") as f:
                f.write(f"{label_idx} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")
            
            # Save the object mask if needed
            if get_mask:
                get_object_mask(obj, scene, output_folder, i+1)



# === RENDER ALL OBJECTS ===
def get_all_object_masks(collection, scene, output_folder):
    pass

def capture_all_views(collection, label_idx, camera, scene, output_folder, get_all_mask):
    pass



# === OBJECTS AUGMENTATION ===

def rescale_object(obj, target_size, eps=0.1, apply=True): 
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


    # TODO: add variating lightings and shadows (using boxes)



# === RENDER LOOP FOR EACH COLLECTION ===

def render_loop(label_idx, collection_name, output_location, get_mask):    
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        print(f"Collection '{collection_name}' not found.")
        return
    
    # Create output folder for a category
    output_folder = os.path.join(output_location, collection_name)
    os.makedirs(output_folder, exist_ok=True)
    while os.path.exists(output_folder):
        output_folder = output_folder + "_new"

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
        if obj.type != 'MESH':
            continue

        rescale_object(obj, target_size=3.0, eps=1.0)
        translate_object(obj, CENTER, X_RANGE, Y_RANGE, Z_RANGE)
        rotate_object(obj)

    # Capture views for each object
    capture_views(collection, label_idx, camera, scene, output_folder, get_mask)

    # TODO: set up camera positions and take photos from multiple viewpoints
    # TODO: generate masks for all objects in the scene if GET_ALL_MASKS is True



# === MAIN ===

if __name__ == "__main__":
    # Renderer setup
    if GET_MASK or GET_ALL_MASKS:
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'GPU'

        # Enable object index pass
        bpy.context.view_layer.use_pass_object_index = True

        # Build compositor tree for masks
        set_compositor_for_masks()
    else:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    
    # Generate images for each category
    for label_idx in range(len(categories)):
        # Each category is a collection of meshes in Blender
        collection_name = categories[label_idx]
        render_loop(label_idx, collection_name, output_location, GET_MASK)
