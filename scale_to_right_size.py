import bpy
import mathutils
import random

obj = bpy.context.object["metarig"]
origin = obj.matrix_world.translation
TRANSLATE_CENTER = mathutils.Vector(origin) 

X_RANGE = 0.4 # Range for X-axis
Y_RANGE = 0.4 # Range for Y-axis
Z_RANGE = 0.2 # Range for Z-axis

TARGET_SIZE = 0.3 
EPS = 0.05 

ZOOM_DISTANCE = 10 # Distance to zoom the camera backward from an object

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


# Ensure we have an object selected
collection_name = "wrench"

# Get the collection
my_collection = bpy.data.collections.get(collection_name)

# Check if collection exists
if my_collection:
    for obj in my_collection.objects:
        
        # Example: select the object
        obj.select_set(True)
        
        translate_object(obj, TRANSLATE_CENTER, X_RANGE, Y_RANGE, Z_RANGE)
        
        rescale_object(obj, SCALE_TARGET_SIZE, SCALE_EPS, apply=True)
else:
    print(f"Collection '{collection_name}' not found.")
    
    
