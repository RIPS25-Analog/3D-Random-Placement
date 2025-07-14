import bpy

scene = bpy.context.scene
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
camera = bpy.data.objects.get("Camera")

def aim_camera_at(obj, camera):
    # Point camera at the object
    direction = center - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()

    # Get object 3D bounding box
    corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    coords = [coord for corner in bbox_corners for coord in corner]
    
    # Zoom to where the entire object will fit in view
    bpy.context.view_layer.update()
    location, foo = camera.camera_fit_coords(depsgraph, coords)
    camera.location = location

    # Zoom away from the object
    forward = camera.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 0.0, -1.0))
    camera.location -= forward * zoom_distance
    
aim_camera_at(bpy.data.objects.get("black"), camera)

scene.camera = camera
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\test\t"
bpy.ops.render.render(write_still=True)