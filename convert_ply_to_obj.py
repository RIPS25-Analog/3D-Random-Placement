import pymeshlab
import os
import shutil
import tempfile


input_path = "/home/data/pace/models"
output_path = "/home/data/3d_render/objects"

models = {
    "can" : [74, 57, 58],
    "toy_car" : [456, 458, 461, 470], 
    "distractors" : [56, 82, 87, 101, 153, 207, 228, 229, 249, 257, 286, 317, 338, 361, 404, 410, 415, 434, 435, 436, 528, 543, 635, 636]
}



def rewrite_ply(input_ply):
    with open(input_ply, "r") as f:
        lines = f.readlines()

    # Prepare new lines
    new_lines = []

    for line in lines:
        if line.startswith("property float u"):
            # rename u -> texture_u
            new_lines.append("property float texture_u\n")
        elif line.startswith("property float v"):
            # rename v -> texture_v
            new_lines.append("property float texture_v\n")
        else:
            new_lines.append(line)

    ply_string = "".join(new_lines)

    # Create a temporary file for the converted PLY file
    with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tmp:
        tmp.write(ply_string.encode())
        tmp_path = tmp.name

    return tmp_path



def convert_ply_to_obj():
    # Clear output folder
    for filename in os.listdir(output_path):
        file_path = os.path.join(output_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    print(f"Cleared folder: {output_path}")

    for label, nums in models.items():
        # Make directory for the category
        output_folder = os.path.join(output_path, label)
        os.makedirs(output_folder, exist_ok=True)

        padded_nums = [str(n).zfill(6) for n in nums]
        
        for num in padded_nums:
            name = f"obj_{num}"

            # Make directory for the object
            output_obj_folder = os.path.join(output_folder, name)
            os.makedirs(output_obj_folder, exist_ok=True)

            # Input and output files
            input_ply = os.path.join(input_path, f"{name}.ply")
            output_obj = os.path.join(output_obj_folder, f"{name}.obj")

            # Convert PLY file into MeshLab-readable version
            tmp_path = rewrite_ply(input_ply)

            # Create a MeshSet object and load the PLY file
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(tmp_path)

            # Save as OBJ
            ms.save_current_mesh(
                output_obj,
                save_vertex_color=True,
                save_textures=True
            )

            # Remove temp file
            os.remove(tmp_path)

            # Remove dummy.png if present
            dummy_texture = os.path.join(output_obj_folder, "dummy.png")
            if os.path.exists(dummy_texture):
                os.remove(dummy_texture)

            # ---- Copy texture file to destination ----
            texture_file = f"{name}.png"
            src_texture = os.path.join(input_path, texture_file)
            dst_texture = os.path.join(output_obj_folder, texture_file)
            shutil.copy(src_texture, dst_texture)

            # ---- Add map_Kd line to MTL to ensure texture ----
            mtl_file = os.path.splitext(output_obj)[0] + ".obj.mtl"

            with open(mtl_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if line.startswith("newmtl "):
                        new_lines.append(f"\nmap_Kd {texture_file}\n")  # insert texture

                with open(mtl_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

            print(f"Converted {name}.ply -> {name}.obj")

convert_ply_to_obj()