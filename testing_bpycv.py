import cv2
import bpy
import bpycv
import random
import numpy as np
import mathutils 
import glob
import os

scene = bpy.context.scene
obj_path = r"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\objects"


# === INTERNAL VARIABLES ===

OBJ_EXT = ['.obj', '.stl', '.usd', '.usdc', '.usda', '.fbx', '.gltf', '.glb']

CENTER = mathutils.Vector((0, 0, 0))  # Center of the box where objects will be placed
X_RANGE = 0.4 # Range for X-axis
Y_RANGE = 0.4 # Range for Y-axis
Z_RANGE = 0.2 # Range for Z-axis

TARGET_SIZE = 0.2 # Target size for objects after scaling
EPS = 0.05 # Size deviation for randomness



def look_at(obj, target):
    direction = (target - obj.location).normalized()
    quat = direction.to_track_quat('-Z', 'Y') 
    obj.rotation_euler = quat.to_euler()

def rescale_object(obj, target_size=TARGET_SIZE, eps=EPS, apply=True): 
    # Get bounding box corners in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    # Get size in each axis
    min_corner = mathutils.Vector(map(min, zip(*bbox_corners)))
    max_corner = mathutils.Vector(map(max, zip(*bbox_corners)))
    dimensions = max_corner - min_corner

    # Calculate and apply the scale factor
    current_size = max(dimensions)
    final_size = target_size + random.uniform(-eps, eps)
    scale_factor = final_size / current_size
    obj.scale *= scale_factor

    if apply:
        bpy.context.view_layer.update()
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def translate_object(obj, center=CENTER, x_range=X_RANGE, y_range=Y_RANGE, z_range=Z_RANGE):
    x = random.uniform(center.x - x_range, center.x + x_range)
    y = random.uniform(center.y - y_range, center.y + y_range)
    z = random.uniform(center.z - z_range, center.z + z_range)
    obj.location = (x, y, z)

def import_obj(scene, obj_path):
    label_names = set()
    
    category_folders = glob.glob(f"{obj_path}/*/")

    # Iterate through all category folders under the objects folder
    for category_folder in category_folders:
        category_name = os.path.basename(os.path.dirname(category_folder))
        
        # Create new collection
        new_coll = bpy.data.collections.new(category_name)
        scene.collection.children.link(new_coll)

        # Exclude distractors from the categories
        if category_name.lower() not in {"distractor", "distractors"}:
            label_names.add(category_name)

        obj_folders = glob.glob(f"{category_folder}/*/")

        # Iterate through all object folders within same category
        for obj_folder in obj_folders:

            # Iterate through all files in the object folder and try to find the mesh file
            for file_path in glob.glob(f"{obj_folder}/*"):
                # Get the file extension
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                obj_ext = os.path.splitext(file_path)[1].lower()

                # Import the object based on its file extension
                if obj_ext in OBJ_EXT:
                    print(f"Importing {file_path}...")

                    if obj_ext == '.obj':
                        bpy.ops.wm.obj_import(filepath=file_path)
                    elif obj_ext == '.stl':
                        bpy.ops.wm.stl_import(filepath=file_path)
                    elif obj_ext in ('.usd', '.usdc', '.usda'):
                        bpy.ops.wm.usd_import(filepath=file_path)
                    elif obj_ext == '.fbx':
                        bpy.ops.import_scene.fbx(filepath=file_path)
                    elif obj_ext in ('.gltf', '.glb'):
                        bpy.ops.import_scene.gltf(filepath=file_path)
                    
                    # Rename the object to the file name
                    new_obj = bpy.context.view_layer.objects.active
                    new_obj.name = file_name  

                    # Set the origin to center
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

                    break  # Stop after the first valid file
            
            for coll in new_obj.users_collection:
                coll.objects.unlink(new_obj)
            
            # Link the object to the new collection
            new_coll.objects.link(new_obj)

            # Move the object away from the origin to avoid unintentional occlusion
            translate_object(new_obj, center=mathutils.Vector((100, 100, 100)))  
            rescale_object(new_obj)  

    return list(label_names)  # Return the list of label names for future processing

def get_selected_objects(original_transforms, label_names):
    objects = [] # (obj, label)
    distractors = [] # (obj, label)

    selected_objects = []
    selected_distractors = []

    # Select all objects with labels from the scene (excluding distractors)
    for label in label_names:
        collection = bpy.data.collections[label]
        for obj in collection.objects:
            if obj.type == 'MESH':
                obj.hide_render = True
                print(obj.name)
                objects.append((obj, label))
    
    # Randomly select some of the objects
    num_obj_ran = random.randint(1, 2)
    selected_objects = random.sample(objects, num_obj_ran)

    # Select all distractors from the scene
    if "distractors" in bpy.data.collections:
        collection = bpy.data.collections["distractors"]
        for distr in collection.objects:
            if distr.type == 'MESH':
                distr.hide_render = True
                distractors.append((distr, "distractors"))
        
        # Total objects is [3, 6]
        num_distractor_ran = random.randint(3, 6) - num_obj_ran
        selected_distractors = random.sample(distractors, num_distractor_ran)

    for obj, _label in selected_objects + selected_distractors:
        obj.hide_render = False

        # Store initial states of the object so that we can restore them later
        original_transforms[obj.name] = {
            'location': obj.location.copy(),
            'rotation': obj.rotation_euler.copy(),
            'scale': obj.scale.copy()
        }

        # Add augmentation to both target objects and distractors
        rescale_object(obj)
        translate_object(obj)

    return selected_objects, selected_distractors


# ===============================================






[bpy.data.objects.remove(obj) for obj in bpy.data.objects if obj.type == "MESH"]

# Import objects
label_names = import_obj(scene, obj_path)

# Randomly select objects to render
selected_objects, selected_distractors = get_selected_objects({}, label_names)

label_names.append("distractors")
scene.camera.location = mathutils.Vector((1, 1, 1))
look_at(scene.camera, CENTER)



# THIS ====
i = 0
for obj, label in selected_objects + selected_distractors:
    obj["inst_id"] = (label_names.index(label) + 1) * 1000 + i
    i += 1
# ====

for obj, label in selected_objects + selected_distractors:
    print(obj.name + ", " + label + ", " + str(obj["inst_id"]))


# THIS ====

# render image, instance annoatation and depth in one line code
result = bpycv.render_data()

inst_map = result["inst"]
h, w = inst_map.shape
bboxes = dict()

for obj, label in selected_objects + selected_distractors:
    inst_id = obj["inst_id"]

    ys, xs = np.where(inst_map == inst_id)
    minX, maxX = xs.min() / w, xs.max() / w
    minY, maxY = ys.min() / h, ys.max() / h

    # Convert to YOLO format
    x_center = (minX + maxX) / 2
    y_center = (minY + maxY) / 2
    width = maxX - minX
    height = maxY - minY

    # Store label {bbox : label}
    bboxes.update({
        (x_center, y_center, width, height) : label
    })

# save result
cv2.imwrite(
    "demo-rgb.jpg", result["image"][..., ::-1]
)  # transfer RGB image to opencv's BGR

with open("demo-rgb.txt", "w") as f:
    for bbox, label in bboxes.items():
        x_center, y_center, width, height = bbox
        f.write(f"{label} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

'''
# save result
cv2.imwrite(
    "demo-rgb.jpg", result["image"][..., ::-1]
)  # transfer RGB image to opencv's BGR

# save instance map as 16 bit png
cv2.imwrite("demo-inst.png", np.uint16(result["inst"] * 20))
# the value of each pixel represents the inst_id of the object

# visualization instance mask, RGB, depth for human
cv2.imwrite("demo-vis(inst_rgb_depth).jpg", result.vis()[..., ::-1])

print(f"Saving vis image to: 'demo-vis(inst_rgb_depth).jpg'")
'''
# ====