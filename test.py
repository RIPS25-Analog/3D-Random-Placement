import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np


obj = bpy.data.objects["Cube"]
scene = bpy.context.scene
camera = bpy.data.objects["Camera"]

collection = bpy.data.collections["screwdriver"]

CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 4 # Range for X-axis
Y_RANGE = 4 # Range for Y-axis
Z_RANGE = 2 # Range for Z-axis


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


for obj in collection.objects:
    rescale_object(obj, target_size=3.0, eps=1.0)
    translate_object(obj, X_RANGE, Y_RANGE, Z_RANGE)
    rotate_object(obj)