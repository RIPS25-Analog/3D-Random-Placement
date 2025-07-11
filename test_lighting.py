import bpy
import random
from mathutils import Vector

# Settings
num_lights = 5
scene_center = Vector((0, 0, 0))  # target for directional lights
location_range = 10  # max offset from center for random placement

# Light types to choose from
light_types = ['POINT', 'SUN', 'SPOT', 'AREA']

# Delete existing lights (optional)
for obj in bpy.data.objects:
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# Function to aim light at target
def look_at(obj, target):
    direction = (target - obj.location).normalized()
    quat = direction.to_track_quat('-Z', 'Y')  # Blender's default light direction
    obj.rotation_euler = quat.to_euler()

# Create random lights
for i in range(num_lights):
    light_type = random.choice(light_types)
    light_data = bpy.data.lights.new(name=f"Light_{i}", type=light_type)
    
    # Vary intensity and color
    light_data.energy = random.uniform(500, 5000)
    light_data.color = (random.random(), random.random(), random.random())
    
    # Create object and assign random position
    light_obj = bpy.data.objects.new(name=f"Light_{i}", object_data=light_data)
    light_obj.location = (
        random.uniform(-location_range, location_range),
        random.uniform(-location_range, location_range),
        random.uniform(1, location_range)
    )
    bpy.context.collection.objects.link(light_obj)

    # For SUN (directional) lights, point toward the center
    if light_type == 'SUN':
        look_at(light_obj, scene_center)
