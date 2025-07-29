import bpy   
import os


EXPORT_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\objects"
scene = bpy.context.scene

def traverse_tree(t):
    yield t
    for child in t.children:
        yield from traverse_tree(child)
    
def export_obj(scene, export_path):
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
            file_path = os.path.join(file_folder, f"{obj.name}.obj")
            
            # Export current object as OBJ
            bpy.ops.wm.obj_export(
                filepath=file_path,
                export_selected_objects=True
            )
            
            # Deselect current object
            obj.select_set(False)
    

export_obj(scene, EXPORT_PATH)