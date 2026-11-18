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


def linear(channel):
    value = channel / 255
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055)**2.4


def build_object(data, name, location):
    count, _, start, end=layout(data)
    rows=[VERTEX.unpack_from(data,POSITIONS+i*VERTEX.size) for i in range(count)]
    points=[(p[0],-p[2],p[1]) for p in rows]
    faces=list(iter_unpack("<3H",data[start+20:end]))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(points,[],faces)
    item=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(item)
    item.location = location
    palette={}
    for poly, face in zip(mesh.polygons,faces):
        color=rows[face[0]][11:15]
        if color not in palette:
            material=bpy.data.materials.new(name+" surface")
            material.diffuse_color=(*map(linear, color[:3]), 1)
            material.use_nodes = True
            shader = material.node_tree.nodes.get("Principled BSDF")
            shader.inputs["Base Color"].default_value = material.diffuse_color
            shader.inputs["Roughness"].default_value = .76
            palette[color]=len(mesh.materials)
            mesh.materials.append(material)
        poly.material_index=palette[color]


def light(scene, name, location, size, power, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size, data.color = power, "DISK", size, color
    item = bpy.data.objects.new(name, data)
    scene.collection.objects.link(item)
    item.location = location
    item.rotation_euler = (-item.location).to_track_quat("-Z", "Y").to_euler()


def main(native, output):
    manifest=json.loads((native/"manifest.json").read_text(encoding="utf-8"))
    entries={row["name"]:row for row in manifest["archives"]["templates"]["entries"]}
    rows=manifest["endless"]["story"]["faultline"]["models"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    positions = ((-9.9,10.7,0), (9.9,10.7,0), (-9.9,-10.7,0), (9.9,-10.7,0))
    for location, row in zip(positions, rows, strict=True):
        data=gzip.decompress((native/"payload"/entries[row["path"]]["payload"]).read_bytes())
        build_object(data,row["name"],location)
    bpy.ops.mesh.primitive_plane_add(size=200)
    plane = bpy.context.object
    plane.location.z = -.009
    ground = bpy.data.materials.new("Blue-grey inspection ground")
    ground.use_nodes = True
    shader = ground.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (.117,.173,.218,1)
    shader.inputs["Roughness"].default_value = .96
    plane.data.materials.append(ground)
    scene=bpy.context.scene
    camera=bpy.data.objects.new("Asset inspection camera",bpy.data.cameras.new("Asset inspection camera"))
    scene.collection.objects.link(camera)
    camera.location=(11,-64,90)
    camera.rotation_euler=(Vector((0,0,2.8))-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.type="ORTHO"
    camera.data.ortho_scale=44
    scene.camera=camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.world = bpy.data.worlds.new("Overcast sky")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (.48,.62,.80,1)
    background.inputs[1].default_value = .44
    light(scene, "Key", (-20,-24,34), 22, 19200, (1,.86,.71))
    light(scene, "Snow bounce", (14,16,26), 18, 11600, (.67,.80,1))
    scene.render.resolution_x=1470
    scene.render.resolution_y=1150
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    output.parent.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(output.resolve())
    bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    native,output=map(Path,sys.argv[sys.argv.index("--")+1:])
    main(native,output)
