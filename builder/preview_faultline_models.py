"""Render the compiled Faultline meshes through Blender without starting Frostpunk."""
import gzip
import json
from pathlib import Path
from struct import iter_unpack
import sys

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from tools.native_mesh import POSITIONS, VERTEX, layout


def build_object(data, name, x):
    count, _, start, end=layout(data)
    rows=[VERTEX.unpack_from(data,POSITIONS+i*VERTEX.size) for i in range(count)]
    points=[(p[0],-p[2],p[1]) for p in rows]
    faces=list(iter_unpack("<3H",data[start+20:end]))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(points,[],faces)
    item=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(item)
    item.location.x=x
    palette={}
    for poly, face in zip(mesh.polygons,faces):
        color=rows[face[0]][11:15]
        if color not in palette:
            material=bpy.data.materials.new(name+" surface")
            material.diffuse_color=tuple(c/255 for c in color)
            palette[color]=len(mesh.materials)
            mesh.materials.append(material)
        poly.material_index=palette[color]


def main(native, output):
    manifest=json.loads((native/"manifest.json").read_text(encoding="utf-8"))
    entries={row["name"]:row for row in manifest["archives"]["templates"]["entries"]}
    rows=manifest["endless"]["story"]["faultline"]["models"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for i,row in enumerate(rows):
        data=gzip.decompress((native/"payload"/entries[row["path"]]["payload"]).read_bytes())
        build_object(data,row["name"],(i-1.5)*11)
    scene=bpy.context.scene
    camera=bpy.data.objects.new("Asset inspection camera",bpy.data.cameras.new("Asset inspection camera"))
    scene.collection.objects.link(camera)
    camera.location=(5,-39,32)
    camera.rotation_euler=(Vector((0,0,1.9))-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.type="ORTHO"
    camera.data.ortho_scale=46
    scene.camera=camera
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="BOTH"
    scene.display.shading.background_type="WORLD"
    scene.world=bpy.data.worlds.new("Inspection backdrop")
    scene.world.color=(0.12,0.17,0.23)
    scene.render.resolution_x=1600
    scene.render.resolution_y=540
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    output.parent.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(output.resolve())
    bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    native,output=map(Path,sys.argv[sys.argv.index("--")+1:])
    main(native,output)
