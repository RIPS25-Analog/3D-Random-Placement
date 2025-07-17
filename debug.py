import bpy
import bpy_extras
import mathutils

def is_obscured(scene, depsgraph, origin, destination):
    # get the direction
    direction = (destination - origin)
    distance = direction.length
    direction = direction.normalized()

    # Add small offset distance to avoid colliding with itself
    offset = 0.01  
    origin = origin + direction * offset  

    # cast a ray from origin to destination
    hit_bool, _location, _normal, _index, _hit_obj, _matrix = scene.ray_cast(depsgraph, origin, direction, distance=distance)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=_location) 
    #bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=origin) bro

    return hit_bool


def get_2d_bounding_box(obj, camera, scene, depsgraph):
    # Update view layer to get the most recent coordinates
    bpy.context.view_layer.update()
    
    # Get the transformation matrix columns
    matrix = obj.matrix_world
    col0 = matrix.col[0]
    col1 = matrix.col[1]
    col2 = matrix.col[2]
    col3 = matrix.col[3]

    # Initialize min, max, and depth values for 2D bounding box
    minX = minY = 1
    maxX = maxY = 0
    depth = 0

    # Determine the number of vertices to iterate over
    mesh = obj.data
    numVertices = len(mesh.vertices)

    vertices_world_pos = []
    
    for t in range(0, numVertices):
        # Get the vertex position
        co = mesh.vertices[t].co

        # WorldPos = X - axis⋅x + Y- axis⋅y + Z - axis⋅z + Translation
        pos_hom = (col0 * co[0]) + (col1 * co[1]) + (col2 * co[2]) + col3
        pos = mathutils.Vector(pos_hom[:3])
        
        # Get the vertices that are visible from the camera
        if not is_obscured(scene, depsgraph, pos, camera.location):
            vertices_world_pos.append(pos)

    # Very occluded, return invalid bounding boxes
    if len(vertices_world_pos) <= 1:
        return 0, 0, 0, 0, -1
    
    # Iterate through each vertex
    for pos in vertices_world_pos:
        # maps a 3D point in world space into normalized camera view coordinates
        pos = bpy_extras.object_utils.world_to_camera_view(scene, camera, pos)
        depth += pos.z

        # Update min and max values as needed
        if (pos.x < minX):
            minX = pos.x
        if (pos.y < minY):
            minY = pos.y
        if (pos.x > maxX):
            maxX = pos.x
        if (pos.y > maxY):
            maxY = pos.y

    # Average out depth
    depth /= numVertices 

    # Clamp to [0, 1]
    minX = max(0.0, min(minX, 1.0))
    minY = max(0.0, min(minY, 1.0))
    maxX = max(0.0, min(maxX, 1.0))
    maxY = max(0.0, min(maxY, 1.0))

    return minX, minY, maxX, maxY, depth


obj = bpy.data.objects["Cube.002"]
camera = bpy.data.objects["Camera.002"]
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()

minX, minY, maxX, maxY, depth = get_2d_bounding_box(obj, camera, scene, depsgraph)