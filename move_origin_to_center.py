import bpy

# Ensure we have an object selected
collection_name = "distractors"

# Get the collection
my_collection = bpy.data.collections.get(collection_name)

# Check if collection exists
if my_collection:
    for obj in my_collection.objects:
        
        # Example: select the object
        obj.select_set(True)
else:
    print(f"Collection '{collection_name}' not found.")

obj = bpy.context.active_object
if obj is not None:
    # Set the origin to the object's geometry center
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')