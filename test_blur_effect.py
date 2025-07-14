import bpy

# Set up compositor
scene = bpy.context.scene
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()

# Add Render Layers node
render_layers = tree.nodes.new(type='CompositorNodeRLayers')
render_layers.location = (-400, 300)

# Add ID Mask node
id_mask = tree.nodes.new(type='CompositorNodeIDMask')
id_mask.index = 1  # Pass index for foreground objects
id_mask.location = (-200, 100)

# Add Blur node
blur_node = tree.nodes.new(type='CompositorNodeBlur')
blur_node.size_x = 20
blur_node.size_y = 20
blur_node.use_relative = False
blur_node.location = (0, 100)

# Add Mix node
mix_node = tree.nodes.new(type='CompositorNodeMixRGB')
mix_node.blend_type = 'MIX'
mix_node.use_alpha = True
mix_node.location = (200, 200)

# Add Viewer node (optional)
viewer = tree.nodes.new(type='CompositorNodeViewer')
viewer.location = (400, 200)

# Add Composite node
composite = tree.nodes.new(type='CompositorNodeComposite')
composite.location = (400, 0)

# Connect nodes
tree.links.new(render_layers.outputs['Image'], mix_node.inputs[1])  # Original image
tree.links.new(render_layers.outputs['IndexOB'], id_mask.inputs['ID value'])  # Object Index
tree.links.new(render_layers.outputs['Image'], blur_node.inputs['Image'])  # Image to blur
tree.links.new(id_mask.outputs['Mask'], blur_node.inputs['Fac'])  # Blur only masked area
tree.links.new(blur_node.outputs['Image'], mix_node.inputs[2])  # Blurred image
tree.links.new(id_mask.outputs['Mask'], mix_node.inputs['Fac'])  # Use mask to mix
tree.links.new(mix_node.outputs['Image'], viewer.inputs['Image'])
tree.links.new(mix_node.outputs['Image'], composite.inputs['Image'])

print("Compositor setup complete.")
