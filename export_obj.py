import bpy   
import os


EXPORT_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\objects"
OBJ_EXT = ".gltf"  # Change to the desired file extension

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
                )
            elif obj_ext == '.gltf':
                bpy.ops.export_scene.gltf(
                    filepath=file_path,
                    use_selection=True,
                    export_format='GLTF_SEPARATE',
                )
            elif obj_ext == '.glb':
                bpy.ops.export_scene.gltf(
                    filepath=file_path,
                    use_selection=True,
                    export_format='GLB',
                )
            else:
                raise ValueError(f"Unsupported file extension: {obj_ext}")
            
            # Deselect current object
            obj.select_set(False)
    

export_obj(scene, OBJ_EXT, EXPORT_PATH)