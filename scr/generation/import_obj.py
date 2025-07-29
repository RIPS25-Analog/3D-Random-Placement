import bpy   
import os
import glob
import sys
import argparse


OBJ_PATH = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\objects"



def traverse_tree(t):
    yield t
    for child in t.children:
        yield from traverse_tree(child)



# === CLEAR STAGE ===

def clear_stage(scene):
    # Clear all collections
    for coll in traverse_tree(scene.collection):
        for obj in coll.objects:
            # Unlink from all collections to avoid dangling links
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
                
            # Remove the object from the scene
            bpy.data.objects.remove(obj, do_unlink=True)
        
        # Keep the default Scene Collection
        if coll.name != "Scene Collection":
            scene.collection.children.unlink(coll)

def add_default_obj(scene):
    # Add new camera
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_object = bpy.data.objects.new("Camera", camera_data)

    # Set camera location and rotation
    camera_object.location = (0, -5, 3)
    camera_object.rotation_euler = (1.1, 0, 0)

    # Link camera to scene
    bpy.context.collection.objects.link(camera_object)
    bpy.context.scene.camera = camera_object
    
    
    # Add new sunlight
    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    light_object = bpy.data.objects.new(name="Sun", object_data=light_data)

    # Set light location and rotation
    light_object.location = (5, -5, 10)
    light_object.rotation_euler = (0.7854, 0, 0.7854)  # 45 degrees down and to side

    # Link light to scene
    bpy.context.collection.objects.link(light_object)
    
    #bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 0, 0))



# === IMPORT OBJECTS ===

def import_obj(scene, obj_path):
    
    category_folders = glob.glob(f"{obj_path}/*/")

    for category_folder in category_folders:
        category_name = os.path.basename(os.path.dirname(category_folder))
        
        # Create new collection
        new_coll = bpy.data.collections.new(category_name)

        # Add collection to scene collection
        scene.collection.children.link(new_coll)

        obj_folders = glob.glob(f"{category_folder}/*/")

        for obj_folder in obj_folders:
            obj_name = os.path.basename(os.path.dirname(obj_folder))
            
            # Make path for current object
            file_path = os.path.join(obj_folder, f"{obj_name}.obj")
            
            # Import current object
            bpy.ops.wm.obj_import(filepath=file_path)
            
            # Get the imported object
            new_obj = bpy.context.view_layer.objects.active
            
            if not new_obj:
                continue
            
            for coll in new_obj.users_collection:
                coll.objects.unlink(new_obj)
            
            # Link the object to the new collection
            new_coll.objects.link(new_obj)



# === ARGUMENT PARSING ===

def parse_args(argv):
    '''Parse input arguments
    '''
    parser = argparse.ArgumentParser(description = "Create synthetic data with 3D objects.")

    parser.add_argument("--clear_stage",
        help = "Delete all collections and objects.", 
        action = "store_true")
    
    parser.add_argument("--add_default_obj",
        help = "Add Camera and sunlight.", 
        action = "store_true")
    
    parser.add_argument("--import_obj",
        help = "Import objects from directory.", 
        action = "store_true")
    
    parser.add_argument("--obj_path",
        help = "Path to the directory with objects.",
        type = str,
        default = OBJ_PATH)
    
    args = parser.parse_args(argv)
    return args

def handle_argv():
    argv = sys.argv
    # Only use args after '--' if running from CLI
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []  # Running from Blender UI -> don't parse anything
        argv.append("--clear_stage")
        argv.append("--add_default_obj")
        argv.append("--import_obj")

    return argv



# === MAIN FUNCTION ===

def main(args):
    scene = bpy.context.scene

    if args.clear_stage:
        clear_stage(scene)
    
    if args.add_default_obj:
        add_default_obj(scene)
    
    if args.import_obj:
        import_obj(scene, args.obj_path)



# === ENTRY POINT ===

if __name__ == "__main__":
    argv = handle_argv()
    args = parse_args(argv)
    main(args)