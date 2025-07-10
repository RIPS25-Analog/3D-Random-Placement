import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np

scene = bpy.context.scene
camera = bpy.data.objects["Camera"]

collection = bpy.data.collections["screwdriver"]

'''
# Select objects that will be rendered
for obj in collection.objects:
    obj.select_set(False)
for obj in collection.objects:
    if not (obj.hide_get() or obj.hide_render):
        obj.select_set(True)
'''

depsgraph = bpy.context.evaluated_depsgraph_get()


CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 4 # Range for X-axis
Y_RANGE = 4 # Range for Y-axis
Z_RANGE = 2 # Range for Z-axis

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
    eps = 0.00000001
    minX = minY = 1 + eps
    maxX = maxY = 0 - eps


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

        if pos.z >= 0:
            # Update min and max values as needed
            if (pos.x < minX):
                minX = pos.x
            if (pos.y < minY):
                minY = pos.y
            if (pos.x > maxX):
                maxX = pos.x
            if (pos.y > maxY):
                maxY = pos.y

    return minX, minY, maxX, maxY
        


def get_viewpoints(center, radius):
    viewpoints = []

    # Iterate over x, y, z in -1, 0, 1 (for faces and edges of cube)
    for x in [-1, 0, 1]:
        #for y in [-1, 0, 1]:
            #for z in [-1, 0, 1]:
                # Skip the center point (0,0,0)
                #if x == 0 and y == 0 and z == 0:
                    #continue
                y = 1
                z = 1
                # Calculate position by adding offsets * direction sign
                pos = center + mathutils.Vector((x, y, z)).normalized() #* radius
                viewpoints.append(pos)
    return viewpoints


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



for obj in collection.objects:

    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]

    # Get center and size
    center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
    max_dist = max((corner - center).length for corner in bbox_corners)
    radius = max_dist + 10 

    viewpoints = get_viewpoints(center, radius)

    output_folder = r"C:\Users\xlmq4\Documents\GitHub\3D_Data_Generation\test"

    for i, pos in enumerate(viewpoints):
        # Move camera to position
        camera.location = pos

        # Point camera at the object
        direction = center - camera.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_quat.to_euler()

        #bpy.ops.view3d.camera_to_view_selected()
        coords = [co for corner in obj.bound_box for co in corner]
        cam_location, foo = camera.camera_fit_coords(depsgraph, coords)

        # Move camera to new location
        camera.location = cam_location

        
        
        label = dict()
        for obj2 in collection.objects:
            name = obj2.name
            mesh = obj2.data

            numVertices = len(obj.data.vertices)

            bbox = get_2d_bounding_box(obj2, camera, scene)
            print(obj2.name)
            print(bbox)

            cam_box = (0, 0, 1, 1)

            # minX, minY, maxX, maxY
            is_visible = is_overlapping_2D(bbox, cam_box)
            print(is_visible)

            label.update({
                name: str(is_visible).lower()
            })

        img_name = ', '.join(f'{k} - {v}' for k, v in label.items())
        img_name = ''

        # Save the image
        img_path = rf"{output_folder}\{obj.name}_view_{i+1}_{img_name}.jpg"
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.filepath = img_path
        bpy.ops.render.render(write_still=True)
            
            