import bpy   
import mathutils 
import bpy_extras
import os
import shutil


MASK_PASS_IDX = 1
DEFAULT_PASS_IDX = 0



# === GET OBJECT LOCATION ===

def get_object_center(obj):
    # Bounding box corners are in object space → transform to world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    # Average the corners to get the center
    center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
    return center



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
                pos = center + mathutils.Vector((x, y, z)).normalized() * radius
                viewpoints.append(pos)
                # TODO: I will add variations to viewpoints later
    
    return viewpoints



# === SET UP COMPOSITOR TREE ===

def compositor_for_masks():
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
    


# === GET OBJECT MASK ===

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



# === TAKE PICTURES FROM MULTIPLE VIEW POINTS ===

def capture_views(viewpoints, obj, center, idx, camera, scene, output_folder, get_mask=True):
    # Iterate through all viewpoints around one object
    for i, pos in enumerate(viewpoints):
        # Move camera to position
        camera.location = pos

        # Point camera at the object
        direction = center - camera.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_quat.to_euler()

        # TODO: make the camera automatically zoom to fit

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
            f.write(f"{idx} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")
        
        # Save the object mask if needed
        if get_mask:
            get_object_mask(obj, scene, output_folder, i+1)



# TODO: select objects from a collection and rescale them to a standard size (????)
# TODO: add variating lightings
# TODO: add occlusion/distractors??????


# === RENDER LOOP FOR EACH CATEGORY ===

def render_loop(idx, collection_name, output_location):    
    # Get all objects under the same category
    collection = bpy.data.collections.get(collection_name)

    # Iterate through objects in the collection
    if collection is None:
        print(f"Collection '{collection_name}' not found.")
    else:
        # Create output folder
        output_folder = os.path.join(output_location, collection_name)
        os.makedirs(output_folder, exist_ok=True)

        # Make subfolders
        for subfolder in ["images", "labels"]:
            folder_path = os.path.join(output_folder, subfolder)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)  # Clear existing folder
            os.makedirs(folder_path, exist_ok=True)

        # Iterate through objects in the collection
        for _obj in collection.objects:
            obj_name = _obj.name
            obj = bpy.data.objects[obj_name]

            # Set up camera positions and orientations
            center = get_object_center(obj)
            radius = 10 # TODO: make it dynamic
            viewpoints = get_viewpoints(center, radius)
            
            capture_views(viewpoints, obj, center, idx, camera, scene, output_folder)



# === MAIN ===

if __name__ == "__main__":
    # Define output locations
    categories = ["screwdriver"]
    output_location = r"C:\Users\xlmq4\Desktop\3D-Data_Generation\data"
    
    # Initial setups
    scene = bpy.context.scene
    camera = bpy.data.objects["Camera"]
    
    # Renderer setup
    scene.render.engine = 'CYCLES'
    #scene.cycles.device = 'GPU'
    
    # Enable object index pass
    bpy.context.view_layer.use_pass_object_index = True

    # Set up compositor nodes --- !!!Call this function only once!!!
    #compositor_for_masks()
    
    # Generate images for each category
    for idx in range(len(categories)):
        # Each category is a collection of meshes in Blender
        collection_name = categories[idx]
        render_loop(idx, collection_name, output_location)
