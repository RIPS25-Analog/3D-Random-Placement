import bpy   
import mathutils 
import bpy_extras
import os
import shutil


obj = bpy.data.objects["Cube"]
scene = bpy.context.scene
camera = bpy.data.objects["Camera"]

def get_viewpoints(center, radius):
    viewpoints = []

    for x in [-1, 0, 1]:
        #for y in [-1, 0, 1]:
            #for z in [-1, 0, 1]:
                y = 1
                z = 1
                #if x == 0 and y == 0 and z == 0:
                    #continue  # skip center
                pos = center + mathutils.Vector((x, y, z)).normalized() * radius
                viewpoints.append(pos)
                # TODO: I will add variations to viewpoints later
    
    return viewpoints