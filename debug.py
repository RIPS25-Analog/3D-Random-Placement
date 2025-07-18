import bpy
import bpy_extras
import mathutils
import numpy as np
import os

def bilerp(p00, p10, p11, p01, u, v):
    """
    Bilinear interpolation of a quad.
    Points:
        p00 = bottom_left
        p10 = bottom_right
        p11 = top_right
        p01 = top_left
    u: horizontal fraction (0 = left, 1 = right)
    v: vertical fraction (0 = bottom, 1 = top)
    """
    return (
        (1 - u) * (1 - v) * p00 +
        u       * (1 - v) * p10 +
        u       * v       * p11 +
        (1 - u) * v       * p01
    )


camera = bpy.data.objects["Camera.002"]
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()


mat_world = camera.matrix_world

focal_length = 1 if camera.type == 'ORTHO' else camera.data.display_size

cam_corners = [mat_world @ (focal_length * point) for point in camera.data.view_frame(scene=scene)]

p11, p10, p00, p01 = cam_corners

WIDTH = 1920 // 5
HEIGHT = 1080 // 5

scene.render.resolution_x = WIDTH
scene.render.resolution_y = HEIGHT

labels = ["A", "B"]
pass_index_to_label = dict()

pass_index = 1
for label in labels:
    collection = bpy.data.collections[label]
    for obj in collection.objects:
        obj.pass_index = pass_index
        pass_index_to_label.update({pass_index : label})
        pass_index += 1


image_mask = np.zeros((WIDTH+1, HEIGHT+1), dtype=np.uint8) 
visible_obj_index = set()
visible_bboxes = dict()

for i in range(WIDTH+1):
    for j in range(HEIGHT+1):
        u = i / WIDTH
        v = j / HEIGHT
        pos = bilerp(p00, p10, p11, p01, u, v)

        direction = (pos - camera.location).normalized()
        hit_bool, _location, _normal, _index, hit_obj, _matrix = scene.ray_cast(depsgraph, camera.location, direction)
        if hit_bool:
            image_mask[i, j] = hit_obj.pass_index
            visible_obj_index.add(hit_obj.pass_index)    

# for each object, find bounding box scaled to 0, 1
for obj_index in visible_obj_index:
    minX = minY = 1
    maxX = maxY = 0

    for i in range(WIDTH):
        for j in range(HEIGHT):
            index = image_mask[i, j]
            if index == obj_index:
                pos = mathutils.Vector((
                    i / WIDTH, 
                    j / HEIGHT
                ))
                if (pos.x < minX):
                    minX = pos.x
                if (pos.y < minY):
                    minY = pos.y
                if (pos.x > maxX):
                    maxX = pos.x
                if (pos.y > maxY):
                    maxY = pos.y

    label = pass_index_to_label[obj_index]

    # Convert to YOLO format
    x_center = (minX + maxX) / 2
    y_center = 1 - (minY + maxY) / 2 # flip y-axis
    width = maxX - minX
    height = maxY - minY

    visible_bboxes.update({
        (x_center, y_center, width, height) : label
    })

img_path = rf"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\test\images\boxes.jpg"
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = img_path
bpy.ops.render.render(write_still=True)

# Save the annotation file
os.makedirs(rf"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\test\labels", exist_ok=True)
label_path = rf"C:\Users\xlmq4\Documents\GitHub\3D-Data-Generation\data\test\labels\boxes.txt"

with open(label_path, "w") as f:
    for bbox, label_idx in visible_bboxes.items():
        x_center, y_center, width, height = bbox
        f.write(f"{label_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")