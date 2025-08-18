import bpy   
import os



# Assuming this script is running inside Blender, then it will not have access
# to defaults.py
export_path = "/home/data/3d_render/objects"
obj_ext = ".gltf"
scene = bpy.context.scene



def traverse_tree(t):
    yield t
    for child in t.children:
        yield from traverse_tree(child)
    
def export_obj(scene, obj_ext, export_path):
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')
    
    for coll in traverse_tree(scene.collection):
        if coll.name == "Scene Collection":
            continue
        
        # Iterate through objects under each collection
        for obj in coll.objects:
            if obj.type != 'MESH':
                continue
            
            # Select current object
            obj.select_set(True)

            # Set the origin to center
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            
            # Make subfolder for current object
            file_folder = os.path.join(export_path, f"{coll.name}", f"{obj.name}")
            os.makedirs(file_folder, exist_ok=True)
            
            # Make path for current object
            file_path = os.path.join(file_folder, f"{obj.name}{obj_ext}")  # obj_ext includes the dot "."
            
            # Export current object based on extension
            if obj_ext == '.obj':
                bpy.ops.wm.obj_export(
                    filepath=file_path,
                    export_selected_objects=True, 
                    path_mode='COPY'
                )                                           # not tested
            elif obj_ext == '.gltf':
                bpy.ops.export_scene.gltf(
                    filepath=file_path,
                    use_selection=True,
                    export_format='GLTF_SEPARATE',
                )                                           # tested
            elif obj_ext == '.glb':
                bpy.ops.export_scene.gltf(
                    filepath=file_path,
                    use_selection=True,
                    export_format='GLB',
                )                                           # not tested
            else:
                raise ValueError(f"Unsupported file extension: {obj_ext}")
            
            # Deselect current object
            obj.select_set(False)
    


export_obj(scene, ".gltf", export_path)