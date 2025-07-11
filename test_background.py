import bpy   
import mathutils 
import bpy_extras
import os
import shutil
import random
import numpy as np


output_folder = r"C:\Users\xlmq4\Documents\GitHub\3D_Data_Generation\test"

bg_path = r"C:\Users\xlmq4\Documents\GitHub\3D_Data_Generation\data\background\bg.jpg"

scene = bpy.context.scene
camera = bpy.data.objects["Camera"]
obj = bpy.data.objects["Cube"]
depsgraph = bpy.context.evaluated_depsgraph_get()

bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]

center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
max_dist = max((corner - center).length for corner in bbox_corners)

viewpoints = []

for x in [-1, 0, 1]:
    for y in [-1, 0, 1]:
        #for z in [-1, 0, 1]:
            z=1
            if x == 0 and y == 0 and z == 0:
                continue
            pos = center + mathutils.Vector((x, y, z)).normalized() * max_dist
            viewpoints.append(pos)



def add_background():
    # Ensure you're using the Compositor and nodes are enabled
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree

    # Clear all nodes
    for node in tree.nodes:
        tree.nodes.remove(node)

    # Create nodes
    render_layers = tree.nodes.new(type='CompositorNodeRLayers')
    image_node = tree.nodes.new(type='CompositorNodeImage')
    alpha_over = tree.nodes.new(type='CompositorNodeAlphaOver')
    composite_node = tree.nodes.new(type='CompositorNodeComposite')

    # Load your image
    image_path = r"C:\Users\xlmq4\Documents\GitHub\3D_Data_Generation\data\background\bg1.jpg"
    image = bpy.data.images.load(image_path)
    image_node.image = image

    # Set node locations for neat layout
    render_layers.location = (0, 300)
    image_node.location = (0, 0)
    alpha_over.location = (200, 150)
    composite_node.location = (400, 150)

    # Link nodes
    links = tree.links
    links.new(image_node.outputs['Image'], alpha_over.inputs[1])      # Background
    links.new(render_layers.outputs['Image'], alpha_over.inputs[2])   # Foreground (render)
    links.new(alpha_over.outputs['Image'], composite_node.inputs['Image'])

    # Set render settings for transparency
    bpy.context.scene.render.film_transparent = True



for i, pos in enumerate(viewpoints):
    camera.location = pos
    
    direction = center - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    
    corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    coords = [coord for corner in corners for coord in corner]
    
    bpy.context.view_layer.update()
    location, foo = camera.camera_fit_coords(depsgraph, coords)

    camera.location = location

    add_background()
    
    
    img_path = rf"{output_folder}\{obj.name}_view_{i+1}.jpg"
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = img_path
    bpy.ops.render.render(write_still=True)