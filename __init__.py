import os
import shutil

import bpy
import bpy_extras
from bpy.props import (BoolProperty, CollectionProperty, IntProperty,
                       StringProperty, PointerProperty)
from bpy.types import Menu, Operator, Panel, PropertyGroup, UIList
from bpy_extras import node_shader_utils
from . import comfyui_api
import tempfile
import shutil

temp_directory = tempfile.TemporaryDirectory("Auto_Tex", ignore_cleanup_errors=True)
auto_tex_render_tex_name = "auto_tex_render_tex.png"

bl_info = {
    "name": "auto tex",
    "author": "gamegccltb",
    "version": (0, 1, 0),
    "blender": (2, 93, 0),
    "location": "",
    "description": "",
    "warning": "",
    "wiki_url": "",
    "support": 'TESTING',
    "category": "Material"
}

is_setup = None


def set_up_render():
    format = "PNG"
    color_depth = "8"
    depth_scale = 1.4

    # Set up rendering
    context = bpy.context
    scene = bpy.context.scene
    render = bpy.context.scene.render

    render.engine = 'BLENDER_EEVEE'
    render.image_settings.color_mode = 'RGBA'  # ('RGB', 'RGBA', ...)
    render.image_settings.color_depth = color_depth  # ('8', '16')
    render.image_settings.file_format = format  # ('PNG', 'OPEN_EXR', 'JPEG, ...)
    render.resolution_x = 512
    render.resolution_y = 512
    render.resolution_percentage = 100
    render.film_transparent = True

    scene.use_nodes = True
    scene.view_layers["View Layer"].use_pass_normal = True
    scene.view_layers["View Layer"].use_pass_diffuse_color = True
    scene.view_layers["View Layer"].use_pass_object_index = True

    nodes = bpy.context.scene.node_tree.nodes
    links = bpy.context.scene.node_tree.links

    # Clear default nodes
    for n in nodes:
        nodes.remove(n)

    # Create input render layer node
    render_layers = nodes.new('CompositorNodeRLayers')

    # Create depth output nodes
    depth_file_output = nodes.new(type="CompositorNodeOutputFile")
    depth_file_output.label = 'Depth Output'
    depth_file_output.base_path = ''
    depth_file_output.file_slots[0].use_node_format = True
    depth_file_output.format.file_format = format
    depth_file_output.format.color_depth = color_depth
    if format == 'OPEN_EXR':
        links.new(render_layers.outputs['Depth'], depth_file_output.inputs[0])
    else:
        depth_file_output.format.color_mode = "BW"

        # Remap as other types can not represent the full range of depth.
        map = nodes.new(type="CompositorNodeNormalize")

        links.new(render_layers.outputs['Depth'], map.inputs[0])

        inv = nodes.new(type="CompositorNodeInvert")

        links.new(map.outputs[0], inv.inputs[1])

        links.new(inv.outputs[0], depth_file_output.inputs[0])

    # Create normal output nodes
    scale_node = nodes.new(type="CompositorNodeMixRGB")
    scale_node.blend_type = 'MULTIPLY'
    # scale_node.use_alpha = True
    scale_node.inputs[2].default_value = (0.5, 0.5, 0.5, 1)
    links.new(render_layers.outputs['Normal'], scale_node.inputs[1])

    bias_node = nodes.new(type="CompositorNodeMixRGB")
    bias_node.blend_type = 'ADD'
    # bias_node.use_alpha = True
    bias_node.inputs[2].default_value = (0.5, 0.5, 0.5, 0)
    links.new(scale_node.outputs[0], bias_node.inputs[1])

    normal_file_output = nodes.new(type="CompositorNodeOutputFile")
    normal_file_output.label = 'Normal Output'
    normal_file_output.base_path = ''
    normal_file_output.file_slots[0].use_node_format = True
    normal_file_output.format.file_format = format
    links.new(bias_node.outputs[0], normal_file_output.inputs[0])

    # Create albedo output nodes
    alpha_albedo = nodes.new(type="CompositorNodeSetAlpha")
    links.new(render_layers.outputs['DiffCol'], alpha_albedo.inputs['Image'])
    links.new(render_layers.outputs['Alpha'], alpha_albedo.inputs['Alpha'])

    albedo_file_output = nodes.new(type="CompositorNodeOutputFile")
    albedo_file_output.label = 'Albedo Output'
    albedo_file_output.base_path = ''
    albedo_file_output.file_slots[0].use_node_format = True
    albedo_file_output.format.file_format = format
    albedo_file_output.format.color_mode = 'RGBA'
    albedo_file_output.format.color_depth = color_depth
    links.new(alpha_albedo.outputs['Image'], albedo_file_output.inputs[0])

    # Create id map output nodes
    id_file_output = nodes.new(type="CompositorNodeOutputFile")
    id_file_output.label = 'ID Output'
    id_file_output.base_path = ''
    id_file_output.file_slots[0].use_node_format = True
    id_file_output.format.file_format = format
    id_file_output.format.color_depth = color_depth

    if format == 'OPEN_EXR':
        links.new(render_layers.outputs['IndexOB'], id_file_output.inputs[0])
    else:
        id_file_output.format.color_mode = 'BW'

        divide_node = nodes.new(type='CompositorNodeMath')
        divide_node.operation = 'DIVIDE'
        divide_node.use_clamp = False
        divide_node.inputs[1].default_value = 2**int(color_depth)

        links.new(render_layers.outputs['IndexOB'], divide_node.inputs[0])
        links.new(divide_node.outputs[0], id_file_output.inputs[0])

    return (depth_file_output, normal_file_output, albedo_file_output, id_file_output)


def do_render(render_file_path, render_file_name, depth_file_output, normal_file_output, albedo_file_output, id_file_output):
    scene = bpy.context.scene

    depth_file_output.base_path = render_file_path
    normal_file_output.base_path = render_file_path
    albedo_file_output.base_path = render_file_path
    id_file_output.base_path = render_file_path

    scene.render.filepath = os.path.join(render_file_path, render_file_name)

    depth_file_output.file_slots[0].path = render_file_name + "_depth"
    normal_file_output.file_slots[0].path = render_file_name + "_normal"
    albedo_file_output.file_slots[0].path = render_file_name + "_albedo"
    id_file_output.file_slots[0].path = render_file_name + "_id"

    bpy.ops.render.render(write_still=True)  # render still


def do_obj_render(obj):
    mesh = obj.data
    mesh_name = mesh.name

    def get_image(name):
        tex = bpy.data.images.get(name)
        if tex is None:
            tex = bpy.data.images.new(name=name, width=4096, height=4096, alpha=True)
        return tex

    auto_tex_albedo_tex_name = "auto_tex_albedo_tex_" + mesh_name
    auto_tex_albedo_tex = get_image(auto_tex_albedo_tex_name)
    auto_tex_albedo_mask_tex_name = "auto_tex_albedo_mask_tex_" + mesh_name
    auto_tex_albedo_mask_tex = get_image(auto_tex_albedo_mask_tex_name)

    auto_tex_mtl_name = "auto_tex_mtl_" + mesh_name

    # Get material
    auto_tex_mtl = bpy.data.materials.get(auto_tex_mtl_name)
    if auto_tex_mtl is None:
        # create material
        auto_tex_mtl = bpy.data.materials.new(name=auto_tex_mtl_name)
        auto_tex_mtl.use_backface_culling = True
        auto_tex_mtl.blend_method = "CLIP"
        auto_tex_mtl.shadow_method = "NONE"
        PrincipleBSDF = node_shader_utils.PrincipledBSDFWrapper(auto_tex_mtl, is_readonly=False)
        PrincipleBSDF.use_nodes = True
        PrincipleBSDF.base_color_texture.image = auto_tex_albedo_tex
        PrincipleBSDF.base_color_texture.texcoords = 'UV'
        PrincipleBSDF.base_color_texture.node_image.name = "auto_tex_albedo_tex"

        mPBSDF = PrincipleBSDF.node_principled_bsdf
        mPBSDF.inputs["Specular"].default_value = 0
        mPBSDF.inputs["Roughness"].default_value = 1

        alpha_texture_node = auto_tex_mtl.node_tree.nodes.new(type="ShaderNodeTexImage")
        alpha_texture_node.name = "auto_tex_albedo_mask_tex"
        auto_tex_mtl.node_tree.links.new(alpha_texture_node.outputs[0], mPBSDF.inputs["Alpha"])
    else:
        PrincipleBSDF = node_shader_utils.PrincipledBSDFWrapper(auto_tex_mtl, is_readonly=False)
        mPBSDF = PrincipleBSDF.node_principled_bsdf

    if mesh.materials:
        mesh.materials[0] = auto_tex_mtl
    else:
        mesh.materials.append(auto_tex_mtl)

    auto_tex_albedo_tex_node = auto_tex_mtl.node_tree.nodes["auto_tex_albedo_tex"]
    auto_tex_albedo_mask_tex_node = auto_tex_mtl.node_tree.nodes["auto_tex_albedo_mask_tex"]

    # 1 . 首先无蒙版渲染以获得全部表面的深度与法向
    auto_tex_albedo_tex_node.image = auto_tex_albedo_tex

    for l in auto_tex_albedo_mask_tex_node.outputs[0].links:
        auto_tex_mtl.node_tree.links.remove(l)
    auto_tex_albedo_mask_tex_node.image = None

    global temp_directory
    image_path = temp_directory.name

    image_name = "no_mask"
    do_render(image_path, image_name, *is_setup)

    auto_tex_mtl.node_tree.links.new(auto_tex_albedo_mask_tex_node.outputs[0], mPBSDF.inputs["Alpha"])
    auto_tex_albedo_mask_tex_node.image = auto_tex_albedo_mask_tex

    image_name = "mask"
    do_render(image_path, image_name, *is_setup)

    auto_tex_no_mask_depth_path = None
    auto_tex_mask_albedo_path = None
    render_outputs = os.listdir(image_path)
    for file_name in render_outputs:
        if file_name.startswith("no_mask_depth"):
            auto_tex_no_mask_depth_path = os.path.join(image_path, file_name)
        elif file_name.startswith("mask_albedo"):
            auto_tex_mask_albedo_path = os.path.join(image_path, file_name)

    comfyui_api.do_rander(auto_tex_no_mask_depth_path=auto_tex_no_mask_depth_path,auto_tex_mask_albedo_path=auto_tex_mask_albedo_path)

    temp_directory.cleanup()
    temp_directory = tempfile.TemporaryDirectory("Auto_Tex", ignore_cleanup_errors=True)


def project_image(image_url=""):
    obj = bpy.context.selected_objects[0]
    mesh = obj.data
    mesh_name = mesh.name

    def get_image(name):
        tex = bpy.data.images.get(name)
        if tex is None:
            tex = bpy.data.images.new(name=name, width=4096, height=4096, alpha=True)
        return tex

    auto_tex_albedo_tex_name = "auto_tex_albedo_tex_" + mesh_name
    auto_tex_albedo_tex = get_image(auto_tex_albedo_tex_name)
    auto_tex_albedo_mask_tex_name = "auto_tex_albedo_mask_tex_" + mesh_name
    auto_tex_albedo_mask_tex = get_image(auto_tex_albedo_mask_tex_name)
    # 2 .
    # 向 auto_tex_albedo_tex 投射图片
    # 向 auto_tex_albedo_mask_tex 投射一张全白图片

    auto_tex_project_image_white_tex_name = "auto_tex_project_image_white_tex_name"
    auto_tex_project_image_white_tex = bpy.data.images.get(auto_tex_project_image_white_tex_name)
    if auto_tex_project_image_white_tex is None:
        auto_tex_project_image_white_tex = bpy.data.images.new(name=auto_tex_project_image_white_tex_name, width=512, height=512)
    pixels = [1.0] * (512*512*4)
    # set pixels
    auto_tex_project_image_white_tex.pixels = pixels
    auto_tex_project_image_white_tex.update()

    area = bpy.context.area
    old_type = area.type
    area.type = 'VIEW_3D'
    bpy.ops.paint.texture_paint_toggle()

    bpy.context.scene.tool_settings.image_paint.mode = 'IMAGE'
    bpy.context.scene.tool_settings.image_paint.canvas = auto_tex_albedo_mask_tex
    bpy.ops.paint.project_image(image=auto_tex_project_image_white_tex_name)

    tex_path = os.path.join(temp_directory.name, auto_tex_render_tex_name)
    comfyui_api.download_file(image_url, tex_path)
    if auto_tex_render_tex_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[auto_tex_render_tex_name])

    bpy.data.images.load(tex_path)

    bpy.context.scene.tool_settings.image_paint.canvas = auto_tex_albedo_tex
    bpy.ops.paint.project_image(image=auto_tex_render_tex_name)

    bpy.ops.paint.texture_paint_toggle()
    area.type = old_type


class AutotexPanel(Panel):
    bl_idname = "OBJECT_PT_Autotex"
    bl_label = "Autotex"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Autotex'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        flow = row.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=False)
        subrow = flow.row()
        subsubrow = subrow.row(align=True)
        subsubrow.operator("autotex.render", text="渲染")

        col = layout.column(align=True)
        col.label(text="图片地址 :")
        col.prop(scene, "AutoTexProjectImageURL", text="")

        row = layout.row()
        flow = row.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=False)
        subrow = flow.row()
        subsubrow = subrow.row(align=True)
        subsubrow.operator("autotex.project_image", text="投射图片")


class auto_render(Operator):
    bl_idname = "autotex.render"
    bl_label = "render"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        global is_setup
        if len(context.selected_objects) == 0:
            context.active_object.select_set(True)
        obj = context.selected_objects[0]
        if is_setup == None:
            is_setup = set_up_render()

        do_obj_render(obj)
        return {'FINISHED'}


class auto_render_project_image(Operator):
    bl_idname = "autotex.project_image"
    bl_label = "project_image"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if len(context.selected_objects) == 0:
            context.active_object.select_set(True)
        AutoTexProjectImageURL = str(context.scene.AutoTexProjectImageURL).strip()
        if len(AutoTexProjectImageURL) > 0:
            project_image(image_url=AutoTexProjectImageURL)
            context.scene.AutoTexProjectImageURL = ""
        return {'FINISHED'}


classes = (
    AutotexPanel,
    auto_render,
    auto_render_project_image
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.AutoTexProjectImageURL = StringProperty(name="URL", description="投射图片网址", default="")


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.AutoTexProjectImageURL


if __name__ == "__main__":
    register()
