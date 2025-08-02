import bpy
import bmesh
import os
from mathutils import Vector
import math
import time

# Start timing the process
start_time = time.time()

# Clear existing mesh objects (but keep camera and lights)
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
bpy.ops.object.delete()

# List of GLTF files to import
gltf_files = [
    "/home/data/3d_render/objects/hammer/black_hammer/black_hammer.gltf",
    # "/home/data/3d_render/objects/other_object/other_object.gltf",
]

# Import multiple GLTF files
imported_objects = []
for i, gltf_filepath in enumerate(gltf_files):
    if os.path.exists(gltf_filepath):
        # Import the GLTF file
        bpy.ops.import_scene.gltf(filepath=gltf_filepath)
        
        # Get the imported objects (they will be selected after import)
        imported = [obj for obj in bpy.context.selected_objects]
        imported_objects.extend(imported)
        
        # Position objects so they don't overlap
        for obj in imported:
            obj.location.x += i * 3  # Spread objects along X-axis
            obj.scale = (2.0, 2.0, 2.0)  # Scale up objects by 2x
        
        print(f"GLTF model imported from {gltf_filepath} successfully!")

# Set up HDRI environment
world = bpy.context.scene.world
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_links = world.node_tree.links

# Clear existing nodes
world_nodes.clear()

# Add Environment Texture node
env_texture = world_nodes.new(type='ShaderNodeTexEnvironment')
# Add path to your HDRI file here
hdri_path = "/home/data/3d_render/background_hdri/DayEnvironmentHDRI004_8K-HDR.exr"  # Update this path
if os.path.exists(hdri_path):
    env_texture.image = bpy.data.images.load(hdri_path)

# Add Background shader
background = world_nodes.new(type='ShaderNodeBackground')
background.inputs[1].default_value = 1.0  # Strength

# Add World Output
world_output = world_nodes.new(type='ShaderNodeOutputWorld')

# Link nodes
world_links.new(env_texture.outputs[0], background.inputs[0])
world_links.new(background.outputs[0], world_output.inputs[0])

# Set up camera
camera = bpy.data.objects.get('Camera')
if not camera:
    # Create camera if it doesn't exist
    bpy.ops.object.camera_add(location=(0, -10, 5))
    camera = bpy.context.object
    camera.name = 'Camera'

# Set the camera as the active camera for the scene
bpy.context.scene.camera = camera

# Set render settings
scene = bpy.context.scene
scene.render.engine = 'CYCLES'

# Configure CUDA GPU rendering
preferences = bpy.context.preferences
cycles_preferences = preferences.addons['cycles'].preferences

cycles_preferences.compute_device_type = 'CUDA'

# Get available CUDA devices and enable them
cycles_preferences.get_devices()
for device in cycles_preferences.devices:
    if device.type == 'CUDA':
        device.use = True
        print(f"Enabled CUDA device: {device.name}")

# Set scene to use GPU compute
scene.cycles.device = 'GPU'

# scene.render.image_settings.file_format = 'PNG'
scene.cycles.samples = 1
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.tile_size = 4096
scene.cycles.use_progressive_refine = False
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.filepath = "/home/data/3d_render/output/render_"

# Calculate center point of all objects for camera targeting
if imported_objects:
    center = Vector((0, 0, 0))
    for obj in imported_objects:
        center += obj.location
    center /= len(imported_objects)
else:
    center = Vector((0, 0, 0))

# Define camera positions for different angles
camera_positions = [
    (8, -8, 5),   # Front-right view
    (-8, -8, 5),  # Front-left view
    (8, 8, 5),    # Back-right view
    (-8, 8, 5),   # Back-left view
    (0, -12, 8),  # Front view
    (12, 0, 5),   # Side view
    (0, 0, 15),   # Top view
]

# Render from different angles
for i, pos in enumerate(camera_positions):
    # Set camera position
    camera.location = pos
    
    # Point camera at the center of objects
    direction = center - camera.location
    # Calculate rotation to look at center
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    
    # Update scene
    bpy.context.view_layer.update()
    
    # Set output filename
    scene.render.filepath = f"/home/data/3d_render/output/render_angle_{i:02d}.png"
    
    # Render
    bpy.ops.render.render(write_still=True)
    print(f"Rendered angle {i+1}/{len(camera_positions)}: {scene.render.filepath}")

# Calculate and print total time
end_time = time.time()
total_time = end_time - start_time
minutes = int(total_time // 60)
seconds = total_time % 60

print("All renders completed successfully!")
print(f"Total generation time: {minutes}m {seconds:.2f}s")