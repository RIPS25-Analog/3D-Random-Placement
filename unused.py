import bpy

MASK_PASS_IDX = 1 # Pass index for objects we want to generate masks on
DEFAULT_PASS_IDX = 0 # Default pass index for all other objects

GET_MASK = False  # Set to True if you want to generate mask for each object the camera focuses on

# === RENDER MASK ===

def set_compositor_for_masks(scene):
    # Enable compositing with nodes
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()

    # Add necessary nodes
    render_layers = tree.nodes.new(type='CompositorNodeRLayers')    # Render layers
    composite = tree.nodes.new(type='CompositorNodeComposite')      # Composite
    id_mask = tree.nodes.new(type='CompositorNodeIDMask')           # ID Mask
    viewer = tree.nodes.new(type='CompositorNodeViewer')            # Viewer

    # Set Pass Index to match the object
    id_mask.index = MASK_PASS_IDX
    
    # Create Links between nodes
    tree.links.new(render_layers.outputs['IndexOB'], id_mask.inputs['ID value'])
    tree.links.new(id_mask.outputs['Alpha'], viewer.inputs['Image'])
    tree.links.new(id_mask.outputs['Alpha'], composite.inputs['Image'])

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



# === ADD 2D BACKGROUND ===

def add_2d_background(scene, bg_image_path):
    # Enable compositing with nodes
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()

    nodes = tree.nodes
    links = tree.links

    # Create nodes
    render_layers = nodes.new(type='CompositorNodeRLayers')
    composite_node = nodes.new(type='CompositorNodeComposite')
    bg_image_node = nodes.new(type='CompositorNodeImage')
    alpha_over = nodes.new(type='CompositorNodeAlphaOver')

    # Set background scale to match the render size
    scale_node = nodes.new(type='CompositorNodeScale')
    scale_node.space = 'RENDER_SIZE'

    # Load your image
    bg_image = bpy.data.images.load(bg_image_path)
    bg_image_node.image = bg_image

    # Link nodes
    links.new(bg_image_node.outputs['Image'], scale_node.inputs['Image'])
    links.new(scale_node.outputs['Image'], alpha_over.inputs[1])       # Background
    links.new(render_layers.outputs['Image'], alpha_over.inputs[2])    # Foreground
    links.new(alpha_over.outputs['Image'], composite_node.inputs['Image'])

    # Set render settings for transparency
    bpy.context.scene.render.film_transparent = True