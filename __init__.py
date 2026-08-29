bl_info = {
    "name": "Secret Paint",
    "author": "orencloud",
    "version": (2, 1, 8),
    "blender": (4, 5, 0),
    "location": "Object + Target + Q",
    "description": "Paint the selected object on top of the active one",
    "warning": "",
    "doc_url": "https://orencloud.art/secretpaint",
    "category": "Paint",
}
import random
from mathutils import Vector
from pathlib import Path
import addon_utils
import math
import bpy, os
import mathutils
import time
from bpy.props import StringProperty
import subprocess
import bmesh
import re
try:
    import numpy as np
except ImportError:
    np = None
from bpy.app.handlers import persistent
blender_version_tuple = bpy.app.version[:3]
both_addon_and_extensions_are_installed = False
addon_is_an_extension=False
addon_path=None
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":
        if addon_path != None: both_addon_and_extensions_are_installed = True
        if hasattr(mod, '__file_manifest__'): addon_is_an_extension=True
addon_path = os.path.dirname(os.path.abspath(__file__))
def _secret_paint_trace(message, **details):
    return None


def _secret_paint_trace_begin(action, **details):
    return None


def _secret_paint_trace_end(action, started_at, **details):
    return None


def _secret_paint_trace_session(action, **details):
    return None


_SECRET_PAINT_NODE_LIBRARY_NAMES = frozenset({
    "Secret Paint.blend",
    "Secret Paint 4.5-5.1.blend",
})
def _secret_paint_node_library_path():
    """Return the node library that the running Blender can read safely."""
    filename = (
        "Secret Paint 4.5-5.1.blend"
        if blender_version_tuple < (5, 2, 0)
        else "Secret Paint.blend"
    )
    return os.path.join(addon_path, filename)
auto_updater_status = True
if blender_version_tuple >= (4, 2, 0) and not bpy.app.online_access or addon_is_an_extension or both_addon_and_extensions_are_installed: auto_updater_status = False
if auto_updater_status == True: from . import addon_updater_ops
class orencurvepanel(bpy.types.Panel):
    bl_label = "Secret Paint"
    bl_idname = "OREN_PT_OrencurvePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Secret"
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.scale_y = 3
        if bpy.context.mode == 'SCULPT_CURVES':
            row.alert = True
            row.operator("secret.brush_density_while_painting", icon= 'LIGHTPROBE_VOLUME', text= "Change Density (D)")
        else: row.operator("secret.paint", icon= 'BRUSH_DATA', text= "Paint")
        row = layout.row()
        row = layout.row()
        row.scale_y = 1.7
        row.operator("secret.assembly", icon="MOD_EXPLODE", text= "Assembly")
        row.operator("secret.realize_instances", icon="LIBRARY_DATA_OVERRIDE_NONEDITABLE", text="Realize")
        row = layout.row()
        row.operator("secret.paintbrushswitch", icon= 'BRUSHES_ALL', text= "Switch")
        row.operator("secret.fixdyntopo", icon="GROUP_UVS")
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row = layout.row()
        def list_hair(sibling,bgroup):
            row = layout.row(align=True)
            row.scale_x = 0.7
            biomegroupreorder = row.operator("secret.biomegroupreorder", text="", icon='TRIA_UP')
            biomegroupreorder.object_name = sibling.name
            biomegroupreorder2 = row.operator("secret.biomegroupreorder2", text="", icon='TRIA_DOWN')
            biomegroupreorder2.object_name = sibling.name
            row.scale_x = 0.98
            if sibling.modifiers[0]["Input_2"]:
                namerow = sibling.modifiers[0]["Input_2"].name
                if sibling.modifiers[0]["Input_2"].type == "EMPTY":
                    icon = "EMPTY_AXIS"
                else:
                    icon = "OBJECT_DATA"
            elif sibling.modifiers[0]["Input_9"]:
                namerow = sibling.modifiers[0]["Input_9"].name
                icon = "OUTLINER_COLLECTION"
            else:
                namerow = "(empty)"
                icon = "OBJECT_DATA"
            if bpy.context.active_object:
                if sibling in bpy.context.selected_objects or \
                        sibling == bpy.context.active_object or \
                        bpy.context.object.mode == "WEIGHT_PAINT" and sibling.modifiers[0]["Input_83_attribute_name"] == bpy.context.active_object.vertex_groups.active.name:
                    row.alert = True
                else: row.alert = False
            if sibling.modifiers[0]["Input_69"] == False:
                n_of_instances = len(sibling.data.curves)
                n_of_instancesFinal = f"{n_of_instances // 1000}.{(n_of_instances % 1000) // 100}k" if n_of_instances >= 1000 else f"0.{n_of_instances // 100}k"
            elif sibling.modifiers[0]["Input_68"] > 0:
                n_of_instances = int(  (sum(face.area for face in sibling.parent.data.polygons)) /     (   (1/   ((sibling.modifiers[0]["Input_68"] ** 0.5) * (sibling.modifiers[0]["Input_100"]))   )   **2)       *sibling.modifiers[0]["Input_72"]/100   )
                n_of_instancesFinal = f"{n_of_instances // 1000}.{(n_of_instances % 1000) // 100}k" if n_of_instances >= 1000 else f"0.{n_of_instances // 100}k"
            else: n_of_instancesFinal = "0.0k"
            select_button = row.operator("secret.select_object", text=str(namerow)+" ["+str(n_of_instancesFinal)+"]", icon=icon)
            select_button.object_name = sibling.name
            if not sibling.modifiers[0]["Input_69"]: row.alert = True
            else: row.alert = False
            hair_button = row.operator("secret.applypaint", text="", icon='CURVES_DATA')
            hair_button.object_name = sibling.name
            if not sibling.modifiers[0]["Input_69"]: row.alert = False
            else: row.alert = True
            procedural_button = row.operator("secret.toggle_procedural", text="", icon='SHADERFX')
            procedural_button.object_name = sibling.name
            if sibling.modifiers[0]["Input_83_attribute_name"] and sibling.modifiers[0]["Input_69"]: row.alert = True
            else: row.alert = False
            vertex_button = row.operator("secret.vertexgrouppaint", text="", icon='MOD_VERTEX_WEIGHT' if sibling.modifiers[0]["Input_83_use_attribute"] else 'GROUP_VERTEX')
            vertex_button.object_name = sibling.name
            try:
                row.alert = True if sibling.modifiers[0]["Socket_15"] or sibling.modifiers[0]["Socket_14"] or sibling.modifiers[0]["Socket_2"] or sibling.modifiers[0]["Input_99"] else False
                render_icon = "RESTRICT_RENDER_OFF"
                if sibling.modifiers[0]["Input_99"]: render_icon = "RESTRICT_RENDER_ON"
                elif sibling.modifiers[0]["Socket_14"]: render_icon = "RESTRICT_VIEW_ON"
            except:
                row.alert = True if sibling.modifiers[0]["Socket_2"] or sibling.modifiers[0]["Input_99"] else False
                render_icon = "RESTRICT_RENDER_OFF"
                if sibling.modifiers[0]["Input_99"]: render_icon = "RESTRICT_RENDER_ON"
            hide_buttonre = row.operator("secret.toggle_visibilityrender", text="", icon=render_icon)
            hide_buttonre.object_name = sibling.name
            hide_buttonre.object_biome = str(bgroup)
            if sibling.display_type == "BOUNDS": row.alert = True
            else: row.alert = False
            bounds_button = row.operator("secret.toggle_display_bounds", text="", icon='SHADING_BBOX' if sibling.display_type == 'BOUNDS' else 'SHADING_SOLID')
            bounds_button.object_name = sibling.name
            if sibling.modifiers[0]["Input_98"]: row.alert = True
            else: row.alert = False
            mask_button = row.operator("secret.secretpaint_viewport_mask", text="", icon='CLIPUV_HLT' if row.alert else "CLIPUV_DEHLT")
            mask_button.object_name = sibling.name
        def list_biomes(bgroup,hair_in_bgroup,row):
            row.scale_y = 1.6
            row.scale_x = 0.99
            try: select_button = row.operator("secret.select_biome", text= "BIOME " + str(bgroup) if hair_in_bgroup[0][0].modifiers[0]["Socket_8"] == "" or hair_in_bgroup[0][0].modifiers[0]["Socket_8"] == str(bgroup) else hair_in_bgroup[0][0].modifiers[0]["Socket_8"])
            except: select_button = row.operator("secret.select_biome", text= "BIOME " + str(bgroup))
            select_button.object_biome = str(bgroup)
            delete_button = row.operator("secret.biome_delete", text="", icon='TRASH')
            delete_button.object_biome = str(bgroup)
            vertex_button = row.operator("secret.vertexgrouppaint_biome", text="", icon='GROUP_VERTEX')
            vertex_button.object_biome = str(bgroup)
            try:
                if hair_in_bgroup[0][0].modifiers[0]["Socket_2"]:
                    render_icon = "RESTRICT_RENDER_ON"
                    row.alert = True
                elif hair_in_bgroup[0][0].modifiers[0]["Socket_15"]:
                    render_icon = "RESTRICT_VIEW_ON"
                    row.alert = True
                else:
                    render_icon = "RESTRICT_RENDER_OFF"
                    row.alert = False
            except:
                if hair_in_bgroup[0][0].modifiers[0]["Socket_2"]:
                    render_icon = "RESTRICT_RENDER_ON"
                    row.alert = True
                else:
                    render_icon = "RESTRICT_RENDER_OFF"
                    row.alert = False
            hide_buttonre = row.operator("secret.toggle_visibilityrender_biome", text="", icon=render_icon)
            hide_buttonre.object_biome = str(bgroup)
            row.alert = False if any(listed_display_types in ("WIRE", "SOLID", "TEXTURED") for listed_display_types in [haa[0].display_type for haa in hair_in_bgroup]) else True
            bounds_button = row.operator("secret.toggle_display_bounds_biome", text="", icon='SHADING_BBOX' if row.alert else 'SHADING_SOLID')
            bounds_button.object_biome = str(bgroup)
            row.alert = True if False not in [haa[0].modifiers[0]["Input_98"] for haa in hair_in_bgroup] else False
            mask_button = row.operator("object.secretpaint_viewport_mask_biome", text="", icon='CLIPUV_HLT' if row.alert else "CLIPUV_DEHLT")
            mask_button.object_biome = str(bgroup)
        obj = context.object
        if obj:
            hair=[]
            try:
                if obj.type=="CURVES" and obj.parent:
                    for hai in obj.parent.children:
                        if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                            for modifier in hai.modifiers:
                                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                                    hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
                elif obj.type=="MESH" or obj.type=="EMPTY":
                    for hayr in bpy.context.scene.objects:
                        if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                            for modifier in hayr.modifiers:
                                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and hayr.modifiers[0]["Input_97"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and hayr.modifiers[0]["Input_2"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and hayr.modifiers[0]["Input_73"] == obj:
                                    hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
            except ReferenceError: pass
            try: hair.sort(key=lambda x: x[1].name)
            except:pass
            all_bgroups=[]
            for hayr in hair[:]:
                if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            all_bgroups.sort()
            for Bgroup in all_bgroups:
                hair_in_bgroup = [hayr for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == Bgroup]
                if blender_version_tuple < (4, 1, 0):
                    list_biomes(Bgroup, hair_in_bgroup,row = layout.row(align=True))
                    for hayr in hair_in_bgroup: list_hair(hayr[0],Bgroup)
                elif blender_version_tuple >= (4, 1, 0):
                    header, panel = layout.panel(str(Bgroup), default_closed=False)
                    list_biomes(Bgroup, hair_in_bgroup,header)
                    if panel:
                        for hayr in hair_in_bgroup: list_hair(hayr[0],Bgroup)
                row = layout.row()
                row = layout.row()
                row = layout.row()
class subpanelutils(bpy.types.Panel):
    bl_label = "Extra"
    bl_idname = "OREN_PT_subpanelutils"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Secret"
    bl_parent_id = 'OREN_PT_OrencurvePanel'
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("secret.circular_array", icon="CURVE_BEZCIRCLE")
        row.operator("secret.straight_array", icon="CURVE_PATH")
        row = layout.row()
        row.scale_y = 1.4
        row.operator("secret.shared_material", icon= 'MATERIAL')
        row.scale_x = 0.25
        row.prop(context.scene.mypropertieslist, "shared_material_index", expand=True, text="")
        row = layout.row()
        row.scale_y = 1
        row.operator("secret.group", icon= 'COLLECTION_NEW')
        row.operator("secret.export_unreal", icon= 'EXPORT')
        row.operator("secret.secretpaint_update_modifier", icon="GEOMETRY_NODES")
        row = layout.row()
        row = layout.row()
        row = layout.row()
        layout.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxKeepManualWhenTransferBiome", toggle = False, expand=False)
        layout.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxHideImported", toggle = False, expand=False)
        layout.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxOverrideBrushes", toggle = False, expand=False)
        layout.prop(bpy.context.preferences.addons[__package__].preferences, "trigger_viewport_mask", expand=False)
        layout.prop(bpy.context.preferences.addons[__package__].preferences, "trigger_auto_uvs", expand=False)
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row.prop(bpy.context.preferences.addons[__package__].preferences, "biomeAssetName")
        row = layout.row()
        row.prop(bpy.context.preferences.addons[__package__].preferences, "biome_library")
        row = layout.row()
        row.prop(bpy.context.preferences.addons[__package__].preferences, "biomename")
        row = layout.row()
        row.prop(bpy.context.preferences.addons[__package__].preferences, "biomenamecategory")
        row = layout.row()
        biome_name = bpy.context.preferences.addons[__package__].preferences.biomename
        if not biome_name.endswith(".blend"): biome_name = biome_name + ".blend"
        blend_file_name= os.path.basename(biome_name)
        file_path = os.path.join(bpy.context.preferences.addons[__package__].preferences.biome_library, biome_name.lstrip("/\\"))
        blend_found=False
        if os.path.exists(file_path):
            blend_found = True
            row.label(text=f"{blend_file_name} already exists,")
            row = layout.row()
            row.label(text="everything will be imported inside of it.")
            row = layout.row()
        row.operator("secret.export_obj_to_asset_library", text=f"Export into {blend_file_name}" if blend_found else "Export Biome to Asset Library")
        row.operator("secret.open_folder", icon="FILE_FOLDER", text="")
class open_folder(bpy.types.Operator):
    """Open Destination Folder with file explorer"""
    bl_idname = "secret.open_folder"
    bl_label = "Open Destination Folder"
    def execute(self, context):
        if bpy.context.preferences.addons[__package__].preferences.biome_library == "(No Library Found, create one first)":
            self.report({'ERROR'}, "No Library Found, create one first")
            return {'FINISHED'}
        biome_name = bpy.context.preferences.addons[__package__].preferences.biomename
        path = os.path.join(bpy.context.preferences.addons[__package__].preferences.biome_library, os.path.dirname(biome_name.lstrip("/\\")))
        try: bpy.ops.wm.path_open(filepath=path)
        except RuntimeError:self.report({'ERROR'}, "The folder doesn't exist. It will be created automatically once you export your Biome. You can also specify a pre-existing folder")
        return {'FINISHED'}
def reupdate_hair_material(context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj == None: activeobj = objselection[0]
    if activeobj not in objselection: objselection.append(activeobj)
    for hair in objselection:
        if hair != None:
            secretpaint_found=False
            if hair.type == "CURVES" and hair.modifiers or hair.type == "CURVE" and hair.modifiers:
                for modif in hair.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        secretpaint_found=True
            if secretpaint_found:
                for modif in hair.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        source_object = _secret_paint_1731_modifier_value(modif, "Input_2")
                        source_collection = _secret_paint_1731_modifier_value(modif, "Input_9")
                        if source_object and source_object.library==None and source_object.type in ["MESH", "CURVE", "CURVES"]:
                            hair.data.materials.clear()
                            for mat_slot in source_object.material_slots:
                                if mat_slot.material and mat_slot.material.name not in hair.data.materials: hair.data.materials.append(mat_slot.material)
                        elif source_collection and source_collection.library==None:
                            hair.data.materials.clear()
                            for obj in source_collection.all_objects:
                                if obj!=hair and obj.type in ["MESH", "CURVE", "CURVES"]:
                                    for mat_slot in obj.material_slots:
                                        if mat_slot.material and mat_slot.material.name not in hair.data.materials: hair.data.materials.append(mat_slot.material)
    return {'FINISHED'}
def contextorencurveappend(context,**kwargs):
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    secretpaint_update_modifier_f(context,upadte_provenance="def contextorencurveappend(context,**kwargs):")
    modifier = activeobj.modifiers.new(name="Secret Paint", type='NODES')
    modifier.node_group = bpy.data.node_groups.get("Secret Paint")
    return {"FINISHED"}
def secretpaint_update_modifier_f(context, cant_remove_this_argument=0, **kwargs):
    upadte_provenance = kwargs.get("upadte_provenance") if "upadte_provenance" in kwargs else None
    update_started = _secret_paint_trace_begin(
        "secretpaint_update_modifier_f",
        provenance=upadte_provenance,
        objects=len(bpy.data.objects),
        node_groups=len(bpy.data.node_groups),
    )
    current_node_version = 51
    pass
    activeobj = bpy.context.active_object
    objselection = bpy.context.selected_objects
    carry_through = False
    validation_started = time.perf_counter()
    try:
        if bpy.app.version_string >= "4.0.0":
            if bpy.data.node_groups.get("Secret Paint") == None      or bpy.data.node_groups.get("Secret Generator") == None      or ["secret paint with linked library found" for node_tree in bpy.data.node_groups if node_tree.name == "Secret Paint" and node_tree.library or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999" and node_tree.library]     or ["found multiple duplicates like Secret Paint.002 " for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999"]     or bpy.data.node_groups["Secret Paint"].interface.items_tree[1].default_value != current_node_version:    carry_through=True
        elif bpy.app.version_string < "4.0.0":
            if bpy.data.node_groups.get("Secret Paint") == None      or bpy.data.node_groups.get("Secret Generator") == None      or ["secret paint with linked library found" for node_tree in bpy.data.node_groups if node_tree.name == "Secret Paint" and node_tree.library or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999" and node_tree.library]     or ["found multiple duplicates like Secret Paint.002 " for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999"]     or bpy.data.node_groups["Secret Paint"].outputs[1].default_value != current_node_version:                 carry_through = True
    except:
        pass
        carry_through=True
    _secret_paint_trace_end(
        "update modifier validation",
        validation_started,
        reimport_required=carry_through,
    )
    if carry_through:
        pass
        material_started = time.perf_counter()
        reupdate_hair_material(context, objselection=[ob for ob in bpy.data.objects])
        _secret_paint_trace_end("update all hair materials", material_started)
        scan_started = time.perf_counter()
        nodes_to_switch = []
        cleanup_generator = []
        for node_tree in bpy.data.node_groups:
            if node_tree.name == "Secret Paint" or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":
                if not node_tree.library: node_tree.name = "Secret Paint.001"
                if node_tree not in nodes_to_switch: nodes_to_switch.append(node_tree)
            if node_tree.name == "Secret Generator" or node_tree.name.startswith("Secret Generator") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":
                if not node_tree.library: node_tree.name = "Secret Generator.001"
                if node_tree not in cleanup_generator: cleanup_generator.append(node_tree)
        _secret_paint_trace_end(
            "scan obsolete node groups",
            scan_started,
            paint_groups=len(nodes_to_switch),
            generator_groups=len(cleanup_generator),
        )
        all_previous_nodes = set(bpy.data.node_groups)
        file_path = _secret_paint_node_library_path()
        inner_path = "NodeTree"
        object_name = "Secret Paint"
        append_started = time.perf_counter()
        try: bpy.ops.wm.append(filepath=os.path.join(file_path, inner_path, object_name),directory=os.path.join(file_path, inner_path),filename=object_name)
        except:pass
        _secret_paint_trace_end("append current node library", append_started, library=file_path)
        relink_started = time.perf_counter()
        for lib in bpy.data.libraries:
            if lib.name in _SECRET_PAINT_NODE_LIBRARY_NAMES: bpy.data.libraries.remove(lib, do_unlink=True)
        for nod in bpy.data.node_groups:
            if nod not in all_previous_nodes and nod.name.startswith("Secret Paint"):
                orenpaintNode= nod
                break
        for obj in bpy.data.objects:
            if obj.type in ["CURVES","CURVE"]:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group:
                        if modif.node_group.name == "Secret Paint" or modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999" : modif.node_group = orenpaintNode
        _secret_paint_trace_end("relink paint modifiers", relink_started)
        cleanup_started = time.perf_counter()
        for nod in nodes_to_switch[:]:
            bpy.data.node_groups.remove(nod, do_unlink=True)
        for nod in cleanup_generator[:]:
            bpy.data.node_groups.remove(nod, do_unlink=True)
        _secret_paint_trace_end("remove obsolete node groups", cleanup_started)
    restore_started = time.perf_counter()
    for x in objselection: x.select_set(True)
    if activeobj: bpy.context.view_layer.objects.active = activeobj
    _secret_paint_trace_end("restore update selection", restore_started)
    _secret_paint_trace_end("secretpaint_update_modifier_f", update_started)
class secretpaint_update_modifier(bpy.types.Operator):
    """Reimport the Secret Paint node tree: Useful when opening older blend files. Blender developers often change how the Geometry Node tree calculates attributes. So when opening an old scene with a new blender version, reimport the latest Node Tree which will account for those changes"""
    bl_idname = "secret.secretpaint_update_modifier"
    bl_label = "Reimport Node Tree"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.secretpaint_update_modifier")
        return {'FINISHED'}
def all_variables_are_equal(variables):
    if not variables:
        return True
    first_value = variables[0]
    return all(value == first_value for value in variables)
def _secret_paint_apply_missing_ids(obj):
    """Materialize implicit point IDs without evaluating a Geometry Nodes modifier."""
    if obj is None or obj.type != "CURVES":
        _secret_paint_trace(
            "SKIP direct ID application",
            object=getattr(obj, "name", None),
            reason="not a Curves object",
        )
        return False
    id_started = _secret_paint_trace_begin(
        "direct ID application",
        object=obj.name,
        data=getattr(obj.data, "name", None),
    )
    curves = getattr(obj, "data", None)
    attributes = getattr(curves, "attributes", None)
    points = getattr(curves, "points", None)
    if attributes is None or points is None:
        _secret_paint_trace_end(
            "direct ID application", id_started, handled=False,
            reason="Curves attributes or points unavailable",
        )
        return False

    point_count = len(points)
    id_attribute = attributes.get("id")
    if id_attribute is None:
        try:
            id_attribute = attributes.new(name="id", type='INT', domain='POINT')
        except (RuntimeError, TypeError):
            _secret_paint_trace_end(
                "direct ID application", id_started, handled=False,
                reason="could not create point ID attribute",
            )
            return False
        if point_count:
            if np is not None:
                values = np.arange(point_count, dtype=np.int32)
            else:
                from array import array
                values = array('i', range(point_count))
            id_attribute.data.foreach_set("value", values)
            curves.update_tag()
        _secret_paint_trace_end(
            "direct ID application", id_started, handled=True,
            points=point_count, missing_ids=point_count,
            operation="created ID attribute",
        )
        return True

    if (id_attribute.data_type != 'INT' or id_attribute.domain != 'POINT' or
            len(id_attribute.data) != point_count):
        _secret_paint_trace_end(
            "direct ID application", id_started, handled=False,
            reason="incompatible ID attribute",
            data_type=id_attribute.data_type, domain=id_attribute.domain,
        )
        return False
    if point_count <= 1:
        _secret_paint_trace_end(
            "direct ID application", id_started, handled=True,
            points=point_count, missing_ids=0,
        )
        return True

    if np is not None:
        values = np.empty(point_count, dtype=np.int32)
        id_attribute.data.foreach_get("value", values)
        missing_indices = np.flatnonzero(values[1:] == 0) + 1
    else:
        from array import array
        values = array('i', [0]) * point_count
        id_attribute.data.foreach_get("value", values)
        missing_indices = [
            index for index, value in enumerate(values[1:], start=1)
            if value == 0
        ]

    if not len(missing_indices):
        _secret_paint_trace_end(
            "direct ID application", id_started, handled=True,
            points=point_count, missing_ids=0, operation="no write",
        )
        return True
    if len(missing_indices) <= 1024:
        for index in missing_indices:
            id_attribute.data[int(index)].value = int(index)
    else:
        if np is not None:
            values[missing_indices] = missing_indices
        else:
            for index in missing_indices:
                values[index] = index
        id_attribute.data.foreach_set("value", values)
    curves.update_tag()
    _secret_paint_trace_end(
        "direct ID application", id_started, handled=True,
        points=point_count, missing_ids=len(missing_indices),
        operation="updated missing IDs",
    )
    return True
_SECRET_PAINT_DENSITY_FALLBACK = 0.4
_SECRET_PAINT_ACCUMULATE_DISTANCE_SCALE = 0.1
_SECRET_PAINT_ACCUMULATE_FIRST_STROKE_FRACTION = 0.25
_SECRET_PAINT_DENSITY_ATTEMPTS_MAX = 2_147_483_647
_SECRET_PAINT_ACCUMULATE_ATTEMPTS_BACKUP = {}


def _secret_paint_accumulate_manual_paint(context=None):
    """Return whether repeated manual Density strokes should accumulate."""
    try:
        if context is None:
            context = bpy.context
        return bool(
            context.preferences.addons[__package__].preferences.accumulate_manual_paint
        )
    except (AttributeError, KeyError, TypeError):
        return True


def _secret_paint_automatic_density_multiplier(context=None):
    """Return the effective multiplier used for newly calculated densities."""
    try:
        if context is None:
            context = bpy.context
        density_scale = float(
            context.preferences.addons[__package__].preferences.automatic_density_multiplier
        )
        if density_scale > 0.0 and math.isfinite(density_scale):
            return density_scale * 4.0
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return 4.0


def _secret_paint_world_dimensions(obj, depsgraph=None):
    """Return evaluated world-space dimensions, even when Object.dimensions is zero."""
    if obj is None:
        return None
    try:
        if depsgraph is None:
            depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_obj = obj.evaluated_get(depsgraph)
    except (AttributeError, ReferenceError, RuntimeError):
        evaluated_obj = obj

    points = []
    try:
        bound_box = evaluated_obj.bound_box
        if bound_box:
            points = [evaluated_obj.matrix_world @ Vector(corner) for corner in bound_box]
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        points = []

    def measured_dimensions(world_points):
        if not world_points:
            return None
        dimensions = Vector((
            max(point[axis] for point in world_points)
            - min(point[axis] for point in world_points)
            for axis in range(3)
        ))
        if max(dimensions) > 1.0e-8 and all(math.isfinite(value) for value in dimensions):
            return dimensions
        return None

    dimensions = measured_dimensions(points)
    if dimensions is not None:
        return dimensions

    evaluated_mesh = None
    try:
        evaluated_mesh = evaluated_obj.to_mesh()
        matrix_world = evaluated_obj.matrix_world
        return measured_dimensions([
            matrix_world @ vertex.co for vertex in evaluated_mesh.vertices
        ])
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return None
    finally:
        if evaluated_mesh is not None:
            try:
                evaluated_obj.to_mesh_clear()
            except (AttributeError, ReferenceError, RuntimeError):
                pass


def _secret_paint_density_size(obj, depsgraph=None, smallest_horizontal=False):
    """Return the size used for density, falling back to evaluated world geometry."""
    try:
        dimensions = Vector(obj.dimensions)
        if max(dimensions) > 1.0e-8:
            unscaled = [
                abs(dimensions[axis] / obj.scale[axis])
                for axis in range(3)
                if abs(obj.scale[axis]) > 1.0e-8
            ]
            if unscaled:
                if smallest_horizontal and len(unscaled) >= 2:
                    return min(unscaled[0], unscaled[1])
                return max(unscaled)
    except (AttributeError, ReferenceError, TypeError, ValueError, ZeroDivisionError):
        pass
    world_dimensions = _secret_paint_world_dimensions(obj, depsgraph)
    if world_dimensions is None:
        return None
    if smallest_horizontal:
        size = min(abs(world_dimensions[0]), abs(world_dimensions[1]))
    else:
        size = max(world_dimensions)
    return size if size > 1.0e-8 and math.isfinite(size) else None


def _secret_paint_1731_recalculate_manual_density(modifier):
    """Derive Curves Sculpt spacing from Secret Paint's world density."""
    if modifier is None:
        return _SECRET_PAINT_DENSITY_FALLBACK
    try:
        density = float(
            _secret_paint_1731_modifier_value(modifier, "Input_68", 0) or 0
        )
        terrain_scale = abs(float(
            _secret_paint_1731_modifier_value(modifier, "Input_100", 1) or 1
        ))
        if density > 0.0 and terrain_scale > 0.0:
            minimum_distance = 1.0 / ((density ** 0.5) * terrain_scale)
            _secret_paint_1731_set_modifier_value(
                modifier,
                "Socket_11",
                minimum_distance,
            )
            return minimum_distance
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    _secret_paint_1731_set_modifier_value(
        modifier, "Socket_11", _SECRET_PAINT_DENSITY_FALLBACK
    )
    return _SECRET_PAINT_DENSITY_FALLBACK
def apply_paint(self,context, **kwargs):
    pass
    apply_started = _secret_paint_trace_begin(
        "apply_paint",
        requested_object=getattr(kwargs.get("activeobj"), "name", None),
        force_ids=bool(kwargs.get("applyIDs", False)),
        keep_active_brush=bool(kwargs.get("keep_active_brush", False)),
    )
    setup_started = time.perf_counter()
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    if "applyIDs" in kwargs:applyIDs = kwargs.get("applyIDs")
    else:applyIDs = False
    keep_active_brush = kwargs.get("keep_active_brush") if "keep_active_brush" in kwargs else False
    active_paint_modifier = _secret_paint_1731_paint_modifier(activeobj)
    preserve_sculpt_context = (
        activeobj is not None and
        bpy.context.active_object == activeobj and
        getattr(activeobj, "mode", None) == "SCULPT_CURVES" and
        (
            applyIDs or
            not _secret_paint_1731_modifier_value(active_paint_modifier, "Input_69", False)
        )
    )
    if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]
    N_Of_Selected = len(objselection)
    randomselectedobj = []
    randomselected_non_hair = []
    all_objs_are_hair = True
    all_objs_are_orencurves = True
    all_selected_hair = []
    all_selected_non_hair = []
    selected_without_active = []
    if N_Of_Selected:
        for obj in objselection:
            if obj != activeobj:
                randomselectedobj = obj
                selected_without_active.append(obj)
            if obj.type != "CURVES" and obj.type != "CURVE": randomselected_non_hair = obj
            if obj.type != "CURVES": all_objs_are_hair = False
            if obj.type == "CURVES":
                all_selected_hair.append(obj)
                if obj.modifiers:
                    for modif in obj.modifiers:
                        if modif.type == 'NODES':
                            if modif.node_group:
                                if modif.node_group.name == "Secret Paint": pass
                                else: all_objs_are_orencurves = False
                            else: all_objs_are_orencurves = False
                        else: all_objs_are_orencurves = False
                else: all_objs_are_orencurves = False
            else: all_objs_are_orencurves = False
            if obj.type != "CURVES": all_selected_non_hair.append(obj)
    _secret_paint_trace_end(
        "apply_paint selection classification",
        setup_started,
        selected=N_Of_Selected,
        hair_objects=len(all_selected_hair),
        non_hair_objects=len(all_selected_non_hair),
    )
    for obj in all_selected_hair:
        object_started = _secret_paint_trace_begin(
            "apply_paint object",
            object=obj.name,
            data=getattr(obj.data, "name", None),
            points=len(getattr(obj.data, "points", ())),
            curves=len(getattr(obj.data, "curves", ())),
            data_users=getattr(obj.data, "users", None),
        )
        node_to_use=[]
        paint_modifier = _secret_paint_1731_paint_modifier(obj)
        apply_id_only = (
            applyIDs or
            _secret_paint_1731_modifier_value(paint_modifier, "Input_69", False) == False
        )
        if not apply_id_only:
            _secret_paint_1731_recalculate_manual_density(paint_modifier)
        if apply_id_only and _secret_paint_apply_missing_ids(obj):
            _secret_paint_1731_set_modifier_value(paint_modifier, "Input_69", False)
            _secret_paint_trace_end(
                "apply_paint object", object_started,
                path="direct IDs", modifier_stack_unchanged=True,
            )
            continue
        modifier_setup_started = time.perf_counter()
        if apply_id_only:
            if "Secret Paint Apply IDs" in bpy.data.node_groups:
                node_to_use = bpy.data.node_groups.get("Secret Paint Apply IDs")
            else:
                node_to_use = bpy.data.node_groups.new(type='GeometryNodeTree', name='Secret Paint Apply IDs')
                input = node_to_use.nodes.new('NodeGroupInput')
                if bpy.app.version_string >= "4.0.0": node_to_use.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
                elif bpy.app.version_string < "4.0.0": node_to_use.outputs.new(type='NodeSocketGeometry', name='GEO')
                output = node_to_use.nodes.new('NodeGroupOutput')
                if bpy.app.version_string >= "4.0.0": node_to_use.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
                elif bpy.app.version_string < "4.0.0": node_to_use.inputs.new(type='NodeSocketGeometry', name='GEO')
                GeometryNodeSetID = node_to_use.nodes.new('GeometryNodeSetID')
                GeometryNodeSetID2 = node_to_use.nodes.new('GeometryNodeSetID')
                ID = node_to_use.nodes.new('GeometryNodeInputID')
                MATH = node_to_use.nodes.new('ShaderNodeMath')
                MATH.operation = 'COMPARE'
                MATH.inputs[1].default_value = MATH.inputs[2].default_value = 0
                node_to_use.links.new(input.outputs[0], GeometryNodeSetID.inputs[0])
                node_to_use.links.new(ID.outputs[0], MATH.inputs[0])
                node_to_use.links.new(MATH.outputs[0], GeometryNodeSetID.inputs[1])
                node_to_use.links.new(MATH.outputs[0], GeometryNodeSetID2.inputs[1])
                node_to_use.links.new(GeometryNodeSetID.outputs[0], GeometryNodeSetID2.inputs[0])
                node_to_use.links.new(GeometryNodeSetID2.outputs[0], output.inputs[0])
        elif applyIDs == False:
            for node in bpy.data.node_groups:
                if node.name.startswith("Secret Generator"):
                    node_to_use = node
                    break
        modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
        modifier.node_group =  bpy.data.node_groups.get(node_to_use.name)
        _secret_paint_1731_set_modifier_value(modifier, "Input_2", obj.parent)
        input_68 = float(_secret_paint_1731_modifier_value(paint_modifier, "Input_68", 0) or 0)
        input_100 = float(_secret_paint_1731_modifier_value(paint_modifier, "Input_100", 0) or 0)
        _secret_paint_1731_set_modifier_value(modifier, "Input_15", input_68 * (input_100 ** 2))
        for destination, source in (
            ("Input_14", "Input_83"),
            ("Input_16", "Input_80"),
            ("Input_19", "Input_79"),
            ("Input_30", "Input_78"),
            ("Input_31", "Input_72"),
            ("Input_32", "Input_82"),
            ("Input_34", "Input_71"),
            ("Input_39", "Input_89"),
            ("Input_40", "Input_16"),
            ("Input_41", "Input_86"),
            ("Input_42", "Input_91"),
            ("Input_43", "Input_92"),
            ("Input_44", "Input_95"),
            ("Input_45", "Input_85"),
        ):
            _secret_paint_1731_set_modifier_value(
                modifier, destination, _secret_paint_1731_modifier_value(paint_modifier, source)
            )
        _secret_paint_1731_set_modifier_value(
            modifier, "Input_33",
            float(_secret_paint_1731_modifier_value(paint_modifier, "Input_70", 0) or 0) * input_100,
        )
        input_83_name = _secret_paint_1731_modifier_value(paint_modifier, "Input_83_attribute_name", "")
        if input_83_name and _secret_paint_1731_modifier_value(paint_modifier, "Input_83_use_attribute", False):
            _secret_paint_1731_set_modifier_value(modifier, "Input_14_attribute_name", input_83_name)
            _secret_paint_1731_set_modifier_value(modifier, "Input_14_use_attribute", True)
        _secret_paint_1731_set_modifier_value(paint_modifier, "Input_69", False)
        if bpy.app.version_string >= "4.0.0":
            obj.modifiers.move(len(obj.modifiers) - 1, 0)
        elif bpy.app.version_string < "4.0.0":
            bpy.ops.object.modifier_move_up({'object': obj}, modifier=modifier.name)
        _secret_paint_trace_end(
            "create and configure apply modifier",
            modifier_setup_started,
            object=obj.name,
            node_group=getattr(modifier.node_group, "name", None),
            path="ID modifier fallback" if apply_id_only else "procedural generation",
        )
        successfully_applied_so_reimport_materials = False
        mats_before = [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material]
        modifier_apply_started = time.perf_counter()
        if obj.data.users >=2:
            same_data=[xx for xx in bpy.data.objects if xx.data==obj.data and xx!=obj]
            obj.data = obj.data.copy()
            try:
                if bpy.app.version_string >= "4.0.0":
                    with context.temp_override(**context.copy()): bpy.ops.object.modifier_apply(modifier=modifier.name)
                    successfully_applied_so_reimport_materials = True
                elif bpy.app.version_string < "4.0.0":
                    bpy.ops.object.modifier_apply({'object': obj}, modifier=modifier.name)
                    successfully_applied_so_reimport_materials = True
            except:
                obj.modifiers.remove(modifier)
                obj.location = obj.location
            for ojj in same_data: ojj.data=obj.data
        else:
            try:
                if bpy.app.version_string >= "4.0.0":
                    with context.temp_override(**context.copy()): bpy.ops.object.modifier_apply(modifier=modifier.name)
                    successfully_applied_so_reimport_materials = True
                elif bpy.app.version_string < "4.0.0":
                    bpy.ops.object.modifier_apply({'object': obj}, modifier=modifier.name)
                    successfully_applied_so_reimport_materials = True
            except:
                obj.modifiers.remove(modifier)
                obj.location=obj.location
        _secret_paint_trace_end(
            "bpy.ops.object.modifier_apply",
            modifier_apply_started,
            object=obj.name,
            success=successfully_applied_so_reimport_materials,
            path="ID modifier fallback" if apply_id_only else "procedural generation",
        )
        if successfully_applied_so_reimport_materials:
            for mat in mats_before:
                if mat.name not in obj.data.materials: obj.data.materials.append(mat)
        if obj.parent and obj.parent.modifiers:
            for mod in obj.parent.modifiers:
                if mod.type=="ARMATURE":
                    _secret_paint_trace(
                        "SKIP automatic curve snapping",
                        object=obj.name,
                        reason="snapping is reserved for the manual Reproject operator",
                    )
        _secret_paint_trace_end(
            "apply_paint object", object_started,
            path="ID modifier fallback" if apply_id_only else "procedural generation",
            modifier_applied=successfully_applied_so_reimport_materials,
        )
    selection_started = time.perf_counter()
    if preserve_sculpt_context:
        activeobj.select_set(True)
    else:
        for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
        bpy.context.view_layer.objects.active = activeobj
    _secret_paint_trace_end(
        "apply_paint selection reset", selection_started,
        sculpt_context_preserved=preserve_sculpt_context,
    )
    uv_check_started = time.perf_counter()
    Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=objselection)
    _secret_paint_trace_end("apply_paint UV check", uv_check_started)
    sculpt_context_started = time.perf_counter()
    if preserve_sculpt_context:
        _secret_paint_trace_end(
            "apply_paint sculpt context", sculpt_context_started,
            operation="preserved existing Sculpt Curves context",
        )
    else:
        context3sculptbrush(context, activeobj=activeobj, keep_active_brush=keep_active_brush)
        _secret_paint_trace_end(
            "apply_paint sculpt context", sculpt_context_started,
            operation="entered Sculpt Curves context",
        )
    _secret_paint_trace_end("apply_paint", apply_started)
    return{'FINISHED'}
class orenscatterinstancesmodifiers(bpy.types.Operator):
    """Convert Procedural Distribution into Manual Paint (or press Q with the paint system selected)"""
    bl_idname = "secret.applypaint"
    bl_label = "Apply and Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def invoke(self, context, event):
        operator_started = _secret_paint_trace_session(
            "operator secret.applypaint",
            object_name=self.object_name,
            current_mode=getattr(bpy.context.object, "mode", None),
        )
        activeobj= bpy.data.objects.get(self.object_name)
        paint_modifier = _secret_paint_1731_paint_modifier(activeobj)
        preserve_sculpt_mode = (
            activeobj is not None and
            bpy.context.active_object == activeobj and
            getattr(activeobj, "mode", None) == "SCULPT_CURVES" and
            not _secret_paint_1731_modifier_value(paint_modifier, "Input_69", False)
        )
        mode_started = time.perf_counter()
        if not preserve_sculpt_mode and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
            _secret_paint_trace_end("operator enter Object mode", mode_started)
        else:
            _secret_paint_trace_end(
                "operator preserve current mode", mode_started,
                mode=getattr(activeobj, "mode", None),
                direct_id_path=preserve_sculpt_mode,
            )
        activate_started = time.perf_counter()
        if bpy.context.active_object != activeobj: bpy.context.view_layer.objects.active = activeobj
        _secret_paint_trace_end("operator activate paint system", activate_started)
        update_started = time.perf_counter()
        secretpaint_update_modifier_f(context,upadte_provenance="secret.applypaint")
        _secret_paint_trace_end("operator update modifier", update_started)
        apply_started = time.perf_counter()
        apply_paint(self,context,activeobj=activeobj, objselection=[activeobj])
        _secret_paint_trace_end("operator apply_paint call", apply_started)
        _secret_paint_trace_end("operator secret.applypaint", operator_started)
        return {'FINISHED'}
class toggle_procedural(bpy.types.Operator):
    """Switch between Manual Paint and Procedural Distribution"""
    bl_idname = "secret.toggle_procedural"
    bl_label = "Toggle Procedural"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def execute(self, context):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.toggle_procedural")
        if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        activeobj= bpy.data.objects.get(self.object_name)
        active_modifier = _secret_paint_1731_paint_modifier(activeobj)
        checkbox_state = _secret_paint_1731_modifier_value(active_modifier, "Input_69", False)
        objselection = bpy.context.selected_objects
        if activeobj not in objselection: objselection.append(activeobj)
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]
        for obj in objselection:
            if obj.type == "CURVES" and obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                        modifier = _secret_paint_1731_paint_modifier(obj)
                        procedural_enabled = _secret_paint_1731_modifier_value(modifier, "Input_69", False)
                        density = float(_secret_paint_1731_modifier_value(modifier, "Input_68", 0) or 0)
                        if obj.type == "CURVES" and procedural_enabled == False and density > 0:
                            allTerrainArea = sum(face.area for face in obj.parent.data.polygons)
                            input_100 = float(_secret_paint_1731_modifier_value(modifier, "Input_100", 0) or 0)
                            if input_100 > 0 and (allTerrainArea / ((1 / ((density ** 0.5) * input_100)) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                                _secret_paint_1731_set_modifier_value(modifier, "Input_98", False)
                                _secret_paint_1731_set_modifier_value(modifier, "Input_97", None)
                                secretpaint_viewport_mask_function(self, context, objselection=[obj], activeobj=obj)
                        _secret_paint_1731_set_modifier_value(modifier, "Input_69", not checkbox_state)
                        obj.location = obj.location
        return {'FINISHED'}
def _secret_paint_1731_panel_objects(context, basis_object=None):
    """Return paint-system rows in the same order used by the compact panel."""
    basis_object = basis_object or context.active_object or context.object
    if basis_object is None:
        return []
    try:
        model = _secret_paint_1731_layout_model(context, basis_object)
    except Exception:
        return []
    return [
        row_entry["object"]
        for biome in model
        for row_entry in biome.get("rows", [])
        if row_entry.get("object") is not None
    ]
_SECRET_PAINT_1731_PANEL_ORDER_PROP = "_secret_paint_panel_order"
_SECRET_PAINT_1731_PANEL_COUNT_CACHE = {}
_SECRET_PAINT_1731_PANEL_LAYOUT_CACHE = {}
_SECRET_PAINT_1731_PANEL_CACHE_VERSION = 0
_SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP = "_secret_paint_collapsed_biomes"
_SECRET_PAINT_1731_BIOME_RENAME_STATE = {
    "active": False,
    "anchor_name": "",
    "biome_number": 0,
    "visible": True,
    "timer_running": False,
}
def _secret_paint_1731_biome_key(biome):
    try:
        number = float(biome)
        if number.is_integer():
            return str(int(number))
    except (TypeError, ValueError):
        pass
    return str(biome)
def _secret_paint_1731_collapsed_biomes(surface):
    if surface is None:
        return set()
    try:
        stored = str(surface.get(_SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP, ""))
    except (AttributeError, ReferenceError, TypeError):
        return set()
    return {key for key in stored.split(";") if key}
def _secret_paint_1731_store_collapsed_biomes(surface, collapsed):
    if surface is None:
        return
    keys = sorted(
        {_secret_paint_1731_biome_key(key) for key in collapsed},
        key=lambda key: (not key.lstrip("-").isdigit(), int(key) if key.lstrip("-").isdigit() else key),
    )
    surface[_SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP] = ";".join(keys)
def _secret_paint_1731_is_biome_collapsed(surface, biome):
    return _secret_paint_1731_biome_key(biome) in _secret_paint_1731_collapsed_biomes(surface)
def _secret_paint_1731_panel_surface(context, basis_object=None, model=None):
    """Resolve the terrain that owns the panel's per-surface UI state."""
    basis_object = basis_object or context.active_object or context.object
    if _secret_paint_1731_paint_modifier(basis_object) is not None:
        parent = getattr(basis_object, "parent", None)
        if parent is not None and getattr(parent, "type", "") == "MESH":
            return parent
    model = model if model is not None else _secret_paint_1731_layout_model(
        context, basis_object
    )
    parents = {
        getattr(row.get("object"), "parent", None)
        for biome in model or ()
        for row in biome.get("rows", ())
        if getattr(row.get("object"), "parent", None) is not None
    }
    if basis_object in parents:
        return basis_object
    if len(parents) == 1:
        return next(iter(parents))
    return basis_object
def _secret_paint_1731_terrain_biomes(terrain):
    biomes = []
    if terrain is None:
        return biomes
    for system in terrain.children:
        modifier = _secret_paint_1731_paint_modifier(system)
        if modifier is None:
            continue
        biome = _secret_paint_1731_modifier_value(modifier, "Socket_0", 1)
        if biome not in biomes:
            biomes.append(biome)
    def biome_sort_key(value):
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, str(value))
    return sorted(biomes, key=biome_sort_key)
def _secret_paint_1731_first_expanded_biome(terrain):
    biomes = _secret_paint_1731_terrain_biomes(terrain)
    for biome in biomes:
        if not _secret_paint_1731_is_biome_collapsed(terrain, biome):
            return biome
    numeric_biomes = []
    for biome in biomes:
        try:
            numeric_biomes.append(int(biome))
        except (TypeError, ValueError):
            pass
    return max(numeric_biomes, default=0) + 1
def _secret_paint_1731_reorder_selected_panel_rows(context, anchor_object, direction):
    """Move selected rows with the panel cursor, including biome boundaries."""
    panel_objects = _secret_paint_1731_panel_objects(context, anchor_object)
    selected_objects = {
        obj for obj in context.selected_objects
        if obj in panel_objects and _secret_paint_1731_paint_modifier(obj) is not None
    }
    if anchor_object not in selected_objects or not panel_objects:
        return False
    selected_biomes = {
        _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(obj), "Socket_0", 0
        )
        for obj in selected_objects
    }
    if len(selected_biomes) != 1:
        return False
    source_biome = next(iter(selected_biomes))
    moving = [obj for obj in panel_objects if obj in selected_objects]
    remaining = [obj for obj in panel_objects if obj not in selected_objects]
    first_selected_index = next(
        index for index, obj in enumerate(panel_objects) if obj in selected_objects
    )
    source_insert_index = sum(
        1 for index, obj in enumerate(panel_objects)
        if index < first_selected_index and obj not in selected_objects
    )
    last_selected_index = max(
        index for index, obj in enumerate(panel_objects) if obj in selected_objects
    )
    moving_complete_biome = all(
        obj in selected_objects
        for obj in panel_objects
        if _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(obj), "Socket_0", 0
        ) == source_biome
    )
    if moving_complete_biome and (
        (direction < 0 and first_selected_index == 0)
        or (direction > 0 and last_selected_index == len(panel_objects) - 1)
    ):
        return False
    target_insert_index = source_insert_index + (-1 if direction < 0 else 1)
    moving_outside = (
        (direction < 0 and source_insert_index == 0)
        or (direction > 0 and source_insert_index == len(remaining))
    )
    if moving_outside:
        biome_numbers = []
        for obj in panel_objects:
            try:
                biome_numbers.append(int(_secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(obj), "Socket_0", 0
                )))
            except (TypeError, ValueError):
                pass
        if not biome_numbers:
            return False
        destination_biome = min(biome_numbers) - 1 if direction < 0 else max(biome_numbers) + 1
        target_insert_index = 0 if direction < 0 else len(remaining)
    else:
        target_insert_index = max(0, min(len(remaining), target_insert_index))
        if target_insert_index == source_insert_index:
            return False
        if direction < 0:
            reference_object = remaining[target_insert_index]
        else:
            reference_object = remaining[target_insert_index - 1]
        destination_biome = _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(reference_object), "Socket_0", source_biome
        )
    if destination_biome != source_biome:
        for obj in moving:
            modifier = _secret_paint_1731_paint_modifier(obj)
            _secret_paint_1731_set_modifier_value(modifier, "Socket_0", int(destination_biome))
            for socket_name in ("Socket_3", "Socket_4", "Socket_5", "Socket_6"):
                _secret_paint_1731_set_modifier_value(modifier, socket_name, False)
            obj.location = obj.location
    reordered = (
        remaining[:target_insert_index]
        + moving
        + remaining[target_insert_index:]
    )
    next_order_by_biome = {}
    for obj in reordered:
        modifier = _secret_paint_1731_paint_modifier(obj)
        biome = _secret_paint_1731_modifier_value(modifier, "Socket_0", 0)
        order = next_order_by_biome.get(biome, 0)
        obj[_SECRET_PAINT_1731_PANEL_ORDER_PROP] = order
        next_order_by_biome[biome] = order + 1
    _secret_paint_1731_clear_panel_cache("reorder")
    for area in getattr(context.screen, "areas", []) if context.screen else []:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
    return True
def _secret_paint_1731_panel_reorder_plan(context, anchor_object):
    """Build cursor targets from only the rows that are visible in the panel."""
    model = _secret_paint_1731_layout_model(context, anchor_object)
    surface = _secret_paint_1731_panel_surface(
        context, anchor_object, model=model
    )
    panel_objects = [
        row["object"]
        for biome in model
        for row in biome.get("rows", ())
    ]
    selected = {
        obj for obj in context.selected_objects
        if obj in panel_objects and _secret_paint_1731_paint_modifier(obj) is not None
    }
    if anchor_object not in selected:
        return None
    selected_biomes = {
        _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(obj), "Socket_0", 0
        )
        for obj in selected
    }
    if len(selected_biomes) != 1:
        return None
    source_biome = next(iter(selected_biomes))
    groups = [
        {
            "key": biome["bgroup"],
            "objects": [row["object"] for row in biome.get("rows", ())],
            "original_index": index,
        }
        for index, biome in enumerate(model)
    ]
    moving = [obj for obj in panel_objects if obj in selected]
    source_objects = next(
        (group["objects"] for group in groups if group["key"] == source_biome),
        (),
    )
    nodes = []
    moving_node_added = False
    for group in groups:
        nodes.append({"kind": "HEADER", "biome": group["key"]})
        if _secret_paint_1731_is_biome_collapsed(surface, group["key"]):
            continue
        for obj in group["objects"]:
            if obj in selected:
                if not moving_node_added:
                    nodes.append({"kind": "MOVING"})
                    moving_node_added = True
                continue
            nodes.append({"kind": "ROW", "object": obj})
    nodes.append({"kind": "END"})
    if moving_node_added:
        anchor_index = next(
            index for index, node in enumerate(nodes)
            if node["kind"] == "MOVING"
        )
    else:
        anchor_index = next(
            index for index, node in enumerate(nodes)
            if node["kind"] == "HEADER" and node["biome"] == source_biome
        )
    return {
        "surface": surface,
        "groups": groups,
        "moving": moving,
        "source_biome": source_biome,
        "source_complete": bool(source_objects) and all(
            obj in selected for obj in source_objects
        ),
        "nodes": nodes,
        "anchor_index": anchor_index,
        "collapsed": _secret_paint_1731_collapsed_biomes(surface),
        "original_biomes": {
            obj: group["key"] for group in groups for obj in group["objects"]
        },
    }
def _secret_paint_1731_assign_panel_groups(context, plan, groups):
    """Apply ordered biome groups and keep collapsed state attached to its terrain."""
    collapsed = plan["collapsed"]
    collapsed_after = set()
    for new_biome, group in enumerate(groups, start=1):
        old_key = group.get("key")
        if old_key is not None and _secret_paint_1731_biome_key(old_key) in collapsed:
            collapsed_after.add(str(new_biome))
        for order, obj in enumerate(group["objects"]):
            modifier = _secret_paint_1731_paint_modifier(obj)
            if modifier is None:
                continue
            old_biome = plan["original_biomes"].get(obj, old_key)
            old_label = _secret_paint_1731_modifier_value(
                modifier, "Socket_8", ""
            )
            _secret_paint_1731_set_modifier_value(
                modifier, "Socket_0", new_biome
            )
            if old_label == _secret_paint_1731_biome_key(old_biome):
                _secret_paint_1731_set_modifier_value(
                    modifier, "Socket_8", str(new_biome)
                )
            if _secret_paint_1731_biome_key(old_biome) != str(new_biome):
                for socket_name in ("Socket_3", "Socket_4", "Socket_5", "Socket_6"):
                    _secret_paint_1731_set_modifier_value(
                        modifier, socket_name, False
                    )
            obj[_SECRET_PAINT_1731_PANEL_ORDER_PROP] = order
            obj.location = obj.location
    _secret_paint_1731_store_collapsed_biomes(
        plan["surface"], collapsed_after
    )
    _secret_paint_1731_clear_panel_cache("reorder_cursor_drop")
    _secret_paint_1731_tag_panel_redraw(context)
def _secret_paint_1731_apply_panel_drop(context, plan, target_index):
    """Move the selected systems to the visible row or biome boundary under the cursor."""
    nodes = plan["nodes"]
    target_index = max(0, min(len(nodes) - 1, target_index))
    node = nodes[target_index]
    if node["kind"] == "MOVING":
        return False
    moving = list(plan["moving"])
    moving_set = set(moving)
    groups = [
        {
            "key": group["key"],
            "objects": [obj for obj in group["objects"] if obj not in moving_set],
            "original_index": group["original_index"],
        }
        for group in plan["groups"]
    ]
    direction = target_index - plan["anchor_index"]
    if node["kind"] == "ROW":
        target_object = node["object"]
        target_group = next(
            group for group in groups if target_object in group["objects"]
        )
        insert_at = target_group["objects"].index(target_object)
        if direction > 0:
            insert_at += 1
        target_group["objects"][insert_at:insert_at] = moving
        groups = [group for group in groups if group["objects"]]
    else:
        if node["kind"] == "HEADER":
            boundary_index = next(
                group["original_index"] for group in plan["groups"]
                if group["key"] == node["biome"]
            )
        else:
            boundary_index = len(plan["groups"])
        groups = [group for group in groups if group["objects"]]
        insert_at = sum(
            group["original_index"] < boundary_index for group in groups
        )
        groups.insert(insert_at, {
            "key": plan["source_biome"] if plan["source_complete"] else None,
            "objects": moving,
            "original_index": boundary_index - 0.5,
        })
    _secret_paint_1731_assign_panel_groups(context, plan, groups)
    return True
def _secret_paint_1731_snapshot_panel_reorder_state(context, anchor_object):
    """Capture the panel state that a modal reorder can change."""
    snapshot = []
    panel_objects = _secret_paint_1731_panel_objects(context, anchor_object)
    surface = _secret_paint_1731_panel_surface(context, anchor_object)
    for obj in panel_objects:
        modifier = _secret_paint_1731_paint_modifier(obj)
        if modifier is None:
            continue
        try:
            has_order = _SECRET_PAINT_1731_PANEL_ORDER_PROP in obj
            order = obj.get(_SECRET_PAINT_1731_PANEL_ORDER_PROP)
        except Exception:
            has_order = False
            order = None
        snapshot.append({
            "object": obj,
            "has_order": has_order,
            "order": order,
            "socket_values": {
                socket_name: _secret_paint_1731_modifier_value(
                    modifier, socket_name
                )
                for socket_name in (
                    "Socket_0",
                    "Socket_3",
                    "Socket_4",
                    "Socket_5",
                    "Socket_6",
                )
            },
        })
    try:
        had_collapsed = (
            surface is not None and
            _SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP in surface
        )
        collapsed_value = surface.get(
            _SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP, ""
        ) if surface is not None else ""
    except (AttributeError, ReferenceError, TypeError):
        had_collapsed = False
        collapsed_value = ""
    return {
        "entries": snapshot,
        "surface": surface,
        "had_collapsed": had_collapsed,
        "collapsed_value": collapsed_value,
    }
def _secret_paint_1731_restore_panel_reorder_state(snapshot):
    """Restore a panel reorder snapshot after cancelling the modal drag."""
    entries = snapshot.get("entries", ()) if isinstance(snapshot, dict) else snapshot
    for entry in entries or ():
        obj = entry.get("object")
        if obj is None:
            continue
        try:
            if entry.get("has_order"):
                obj[_SECRET_PAINT_1731_PANEL_ORDER_PROP] = entry.get("order")
            elif _SECRET_PAINT_1731_PANEL_ORDER_PROP in obj:
                del obj[_SECRET_PAINT_1731_PANEL_ORDER_PROP]
            modifier = _secret_paint_1731_paint_modifier(obj)
            for socket_name, value in entry.get("socket_values", {}).items():
                _secret_paint_1731_set_modifier_value(modifier, socket_name, value)
        except Exception:
            continue
    if isinstance(snapshot, dict):
        surface = snapshot.get("surface")
        try:
            if surface is not None and snapshot.get("had_collapsed"):
                surface[_SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP] = snapshot.get(
                    "collapsed_value", ""
                )
            elif (surface is not None and
                    _SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP in surface):
                del surface[_SECRET_PAINT_1731_COLLAPSED_BIOMES_PROP]
        except (AttributeError, ReferenceError, TypeError):
            pass
    _secret_paint_1731_clear_panel_cache("reorder_cancel")
def _secret_paint_1731_select_panel_row_range(context, target_object):
    """Shift-click a system row to select the contiguous panel range."""
    if target_object is None:
        return False
    panel_objects = _secret_paint_1731_panel_objects(context, context.active_object or target_object)
    if target_object not in panel_objects:
        panel_objects = _secret_paint_1731_panel_objects(context, target_object)
    if target_object not in panel_objects:
        return False
    selected = set(context.selected_objects)
    anchor = context.view_layer.objects.active
    if anchor not in panel_objects or anchor not in selected:
        anchor = next((obj for obj in panel_objects if obj in selected), None)
    if anchor is None:
        for obj in list(context.selected_objects):
            obj.select_set(False)
        target_object.select_set(True)
        context.view_layer.objects.active = target_object
        return True
    start = panel_objects.index(anchor)
    end = panel_objects.index(target_object)
    if start > end:
        start, end = end, start
    range_objects = set(panel_objects[start:end + 1])
    for obj in list(context.selected_objects):
        if obj not in range_objects:
            obj.select_set(False)
    for obj in range_objects:
        obj.select_set(True)
    context.view_layer.objects.active = target_object
    return True
def _secret_paint_1731_select_biome_range(context, hair, all_bgroups, target_biome):
    """Shift-click a biome header to select the contiguous biome range."""
    if not hair:
        return False
    try:
        target_biome = int(target_biome)
    except (TypeError, ValueError):
        return False
    ordered_bgroups = sorted(set(all_bgroups), key=lambda value: int(value))
    if target_biome not in ordered_bgroups:
        return False
    selected = set(context.selected_objects)
    active = context.view_layer.objects.active
    active_biome = None
    for entry in hair:
        if entry[0] == active and active in selected:
            active_biome = _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(entry[0]), "Socket_0", None
            )
            break
    if active_biome not in ordered_bgroups:
        for entry in hair:
            if entry[0] in selected:
                active_biome = _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(entry[0]), "Socket_0", None
                )
                if active_biome in ordered_bgroups:
                    break
    if active_biome not in ordered_bgroups:
        active_biome = target_biome
    start = ordered_bgroups.index(active_biome)
    end = ordered_bgroups.index(target_biome)
    if start > end:
        start, end = end, start
    selected_biomes = set(ordered_bgroups[start:end + 1])
    selected_objects = [
        entry[0]
        for entry in hair
        if _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(entry[0]), "Socket_0", None
        ) in selected_biomes
    ]
    for obj in list(context.selected_objects):
        obj.select_set(False)
    for obj in selected_objects:
        if obj.name in context.view_layer.objects:
            obj.select_set(True)
    target_objects = [
        obj for obj in selected_objects
        if _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(obj), "Socket_0", None
        ) == target_biome
    ]
    if target_objects:
        context.view_layer.objects.active = target_objects[0]
    return True
class SelectObjectOperator(bpy.types.Operator):
    """Ctrl+Click: select siblings; Shift: extend selection; Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; Alt+Click: duplicate a backup system"""
    bl_idname = "secret.select_object"
    bl_label = "Select Object"
    bl_description = (
        "Ctrl+Click: select siblings; Shift: extend selection; "
        "Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; "
        "Alt+Click: duplicate a backup system. Use G to reorder or X to delete."
    )
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def execute(self, context):
        """Support direct bpy.ops calls as well as panel button invocation."""
        obj = bpy.data.objects.get(self.object_name)
        if obj is None or obj.name not in bpy.context.view_layer.objects:
            return {'CANCELLED'}
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for selected in list(context.selected_objects):
            selected.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        for area in getattr(context.screen, "areas", []) if context.screen else []:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_object")
        activeobj = bpy.context.active_object
        objselection = bpy.context.selected_objects
        if activeobj and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        if event.alt & event.ctrl:
            for x in objselection: bpy.data.objects[x.name].select_set(False)
            obj = bpy.data.objects.get(self.object_name)
            if obj and obj.name in bpy.context.view_layer.objects:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                select_biome_all_function(context)
        elif event.alt:
            obj= bpy.data.objects.get(self.object_name)
            if obj not in objselection: objselection=[obj]
            for obj in objselection:
                if obj.name in bpy.context.view_layer.objects:
                    Coll_of_Active = []
                    original_collection = bpy.context.view_layer.active_layer_collection
                    ucol = obj.users_collection
                    for i in ucol:
                        layer_collection = bpy.context.view_layer.layer_collection
                        Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                        bpy.context.view_layer.active_layer_collection = Coll_of_Active
                    newobj = obj.copy()
                    newobj.data = obj.data.copy()
                    _secret_paint_1731_set_modifier_value(
                        _secret_paint_1731_paint_modifier(newobj), "Input_99", True
                    )
                    _secret_paint_1731_set_modifier_value(
                        _secret_paint_1731_paint_modifier(obj), "Input_99", False
                    )
                    bpy.context.collection.objects.link(newobj)
                    bpy.data.objects[newobj.name].select_set(False)
                    obj.location=obj.location
                    bpy.context.view_layer.active_layer_collection = original_collection
        elif event.shift & event.ctrl:
            oob = bpy.data.objects.get(self.object_name)
            if oob.name in bpy.context.view_layer.objects:
                if oob not in objselection: objselection.append(bpy.data.objects.get(self.object_name))
                orencurveselectobj_function(self,context, activeobj=activeobj,objselection=objselection)
        elif event.shift:
            if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
            obj = bpy.data.objects.get(self.object_name)
            if obj and obj.name in bpy.context.view_layer.objects:
                _secret_paint_1731_select_panel_row_range(context, obj)
        elif event.ctrl:
            if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
            obj = bpy.data.objects.get(self.object_name)
            if obj:
                parent = obj.parent
                if parent:
                    siblings = parent.children
                    for sibling in siblings:
                        if sibling.type == "CURVES" and sibling.modifiers or sibling.type == "CURVE" and sibling.modifiers:
                            for modif in sibling.modifiers:
                                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and sibling.name in bpy.context.view_layer.objects:
                                    sibling.select_set(True)
        else:
            for x in objselection: bpy.data.objects[x.name].select_set(False)
            if self.object_name and self.object_name in bpy.context.view_layer.objects:
                bpy.context.view_layer.objects.active = bpy.data.objects[self.object_name]
                bpy.data.objects[self.object_name].select_set(True)
        return {'FINISHED'}
class selectbrush(bpy.types.Operator):
    """Ctrl+Click: select siblings; Shift: extend selection; Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; Alt+Click: duplicate a backup system"""
    bl_idname = "secret.selectbrush"
    bl_label = "Select Brush"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def invoke(self, context, event):
        selectbr = [b for b in bpy.data.brushes if b.name == self.object_name]
        context.tool_settings.image_paint.brush = selectbr[0]
        return {'FINISHED'}
class biome_delete(bpy.types.Operator):
    """Delete this biome. Shift+Click to only delete the selected hair within this biome"""
    bl_idname = "secret.biome_delete"
    bl_label = "Delete Biome"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context, upadte_provenance="secret.biome_delete")
        if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        obj = context.object
        hair = find_all_listed_paintsystems(context, activeobj=obj)
        hair_in_bgroup = [
            hayr[0]
            for hayr in hair[:]
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
            ) == int(self.object_biome)
        ]
        parent_surface = hair_in_bgroup[0].parent
        if obj in hair_in_bgroup:
            parent_surface.select_set(True)
            bpy.context.view_layer.objects.active = parent_surface
        if event.shift:
            for x in hair_in_bgroup:
                if x in bpy.context.selected_objects: bpy.data.objects.remove(x, do_unlink=True)
        else:
            for x in hair_in_bgroup:
                bpy.data.objects.remove(x, do_unlink=True)
        hair = find_all_listed_paintsystems(context, activeobj=parent_surface)
        biome_remove_gaps(context,hair)
        _secret_paint_1731_clear_panel_cache("biome_delete")
        return {'FINISHED'}
class SelectBiomeOperator(bpy.types.Operator):
    """Shift+Click: extend selection, Alt+Click: duplicate a backup system, Ctrl+Click: rename biome"""
    bl_idname = "secret.select_biome"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty(name= "Custom Biome Name", default="")
    rename_biome_number: bpy.props.IntProperty(default=0, options={'HIDDEN'})
    rename_anchor_name: bpy.props.StringProperty(default="", options={'HIDDEN'})
    rename_original_name: bpy.props.StringProperty(default="", options={'HIDDEN'})
    def draw(self, context):
        row = self.layout.row()
        row.activate_init = True
        row.prop(self, "object_biome", text="Biome Name")
    def _apply_biome_name(self, context, name):
        anchor = bpy.data.objects.get(self.rename_anchor_name)
        if anchor is None:
            return False
        updated = False
        for obj, modifier in _secret_paint_1731_collect_paint_systems(context, anchor):
            try:
                if int(_secret_paint_1731_modifier_value(modifier, "Socket_0", 0)) != self.rename_biome_number:
                    continue
            except (TypeError, ValueError):
                continue
            if _secret_paint_1731_set_modifier_value(modifier, "Socket_8", name):
                obj.location = obj.location
                updated = True
        if updated:
            _secret_paint_1731_clear_panel_cache("biome_rename")
            _secret_paint_1731_tag_panel_redraw(context)
        return updated
    def _set_rename_status(self, context):
        try:
            context.workspace.status_text_set(
                text=f'Rename biome: "{self.object_biome}"  Enter confirm, Esc cancel'
            )
        except Exception:
            pass
    def _finish_rename_modal(self, context):
        _secret_paint_1731_end_biome_rename(context)
        try:
            context.window.cursor_modal_restore()
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text=None)
        except Exception:
            pass
    def _confirm_rename_modal(self, context):
        self._apply_biome_name(context, self.object_biome)
        self._finish_rename_modal(context)
        return {'FINISHED'}
    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._apply_biome_name(context, self.rename_original_name)
            self._finish_rename_modal(context)
            return {'CANCELLED'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return self._confirm_rename_modal(context)
        if event.value != 'PRESS':
            return {'RUNNING_MODAL'}
        if event.type in {
            'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_CTRL', 'RIGHT_CTRL',
            'LEFT_ALT', 'RIGHT_ALT', 'OSKEY',
        }:
            return {'RUNNING_MODAL'}
        new_name = None
        replace_existing = getattr(self, "_rename_replace_on_type", False)
        if event.type == 'BACK_SPACE':
            new_name = "" if replace_existing else self.object_biome[:-1]
        elif event.type == 'DEL':
            new_name = ""
        elif event.ctrl and event.type == 'V':
            try:
                clipboard_text = context.window_manager.clipboard
            except Exception:
                clipboard_text = ""
            new_name = clipboard_text if replace_existing else self.object_biome + clipboard_text
        else:
            text = getattr(event, "unicode", "")
            if text and text.isprintable():
                new_name = text if replace_existing else self.object_biome + text
        if new_name is not None:
            self.object_biome = new_name
            self._rename_replace_on_type = False
            self._apply_biome_name(context, self.object_biome)
            self._set_rename_status(context)
            return {'RUNNING_MODAL'}
        return self._confirm_rename_modal(context)
    def execute(self, context):
        if self.rename_anchor_name and self._apply_biome_name(context, self.object_biome):
            return {'FINISHED'}
        return {'CANCELLED'}
    def invoke(self, context, event):
        try:
            if context.object and context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - invoke")
        obj = context.object
        if obj:
            hair = find_all_listed_paintsystems(context)
            all_bgroups=[]
            for hayr in hair[:]:
                biome_number = _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
                )
                if biome_number not in all_bgroups: all_bgroups.append(biome_number)
            hair_in_bgroup = [
                hayr[0]
                for hayr in hair[:]
                if _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
                ) == int(self.object_biome)
            ]
            if event.alt:
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                new_bgroup_number = 1
                while new_bgroup_number in all_bgroups: new_bgroup_number +=1
                for obj in hair_in_bgroup:
                    if obj.name in bpy.context.view_layer.objects:
                        Coll_of_Active = []
                        original_collection = bpy.context.view_layer.active_layer_collection
                        ucol = obj.users_collection
                        for i in ucol:
                            layer_collection = bpy.context.view_layer.layer_collection
                            Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                            bpy.context.view_layer.active_layer_collection = Coll_of_Active
                        newobj = obj.copy()
                        newobj.data = obj.data.copy()
                        _secret_paint_1731_set_modifier_value(
                            _secret_paint_1731_paint_modifier(newobj), "Socket_2", True
                        )
                        obj_modifier = _secret_paint_1731_paint_modifier(obj)
                        _secret_paint_1731_set_modifier_value(obj_modifier, "Socket_0", new_bgroup_number)
                        _secret_paint_1731_set_modifier_value(obj_modifier, "Socket_2", False)
                        bpy.context.collection.objects.link(newobj)
                        bpy.data.objects[newobj.name].select_set(False)
                        obj.location=obj.location
                        bpy.context.view_layer.active_layer_collection = original_collection
                _secret_paint_1731_clear_panel_cache("duplicate_biome")
            elif event.shift:
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                _secret_paint_1731_select_biome_range(context, hair, all_bgroups, self.object_biome)
            elif event.ctrl:
                if not hair_in_bgroup:
                    return {'CANCELLED'}
                self.rename_biome_number = int(self.object_biome)
                self.rename_anchor_name = hair_in_bgroup[0].name
                current_name = _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hair_in_bgroup[0]),
                    "Socket_8",
                    "",
                )
                self.object_biome = (
                    str(current_name)
                    if current_name not in ("", str(self.rename_biome_number), None)
                    else ""
                )
                self.rename_original_name = self.object_biome
                self._rename_replace_on_type = True
                _secret_paint_1731_begin_biome_rename(
                    context,
                    self.rename_anchor_name,
                    self.rename_biome_number,
                )
                self._set_rename_status(context)
                try:
                    context.window.cursor_modal_set('TEXT')
                except Exception:
                    pass
                context.window_manager.modal_handler_add(self)
                _secret_paint_1731_tag_panel_redraw(context)
                return {'RUNNING_MODAL'}
            else:
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
                for ob in hair_in_bgroup:
                    if ob.name in bpy.context.view_layer.objects:
                        bpy.context.view_layer.objects.active = ob
                        ob.select_set(True)
        return {'FINISHED'}
def find_all_listed_paintsystems(context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.scene.objects
    return [
        (paint_system, _secret_paint_1731_source_object(modifier))
        for paint_system, modifier in _secret_paint_1731_collect_paint_systems(context, activeobj)
    ]
def biome_remove_gaps(context,biome_hair):
    all_biome_numbers=[]
    for hayr in biome_hair[:]:
        biome_number = _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
        )
        if biome_number not in all_biome_numbers: all_biome_numbers.append(biome_number)
    all_biome_numbers.sort()
    loop = 1
    for biome_number in all_biome_numbers[:]:
        for hayr in biome_hair[:]:
            modifier = _secret_paint_1731_paint_modifier(hayr[0])
            if _secret_paint_1731_modifier_value(modifier, "Socket_0", 0) == biome_number:
                _secret_paint_1731_set_modifier_value(modifier, "Socket_0", loop)
                biome_hair.remove(hayr)
        loop += 1
    return{'FINISHED'}
def biomegroupreorder_f(context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    if "direction" in kwargs:direction = kwargs.get("direction")
    if "move_to_extreme" in kwargs:move_to_extreme = kwargs.get("move_to_extreme")
    else:move_to_extreme = False
    secretpaint_update_modifier_f(context,upadte_provenance="def biomegroupreorder_f(context,**kwargs):")
    hair = find_all_listed_paintsystems(context, activeobj=activeobj, objselection=objselection)
    if move_to_extreme:
        all_biome_numbers = []
        for hayr in hair[:]:
            biome_number = _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
            )
            if biome_number not in all_biome_numbers: all_biome_numbers.append(biome_number)
        if direction == -1: destination_biome = min(all_biome_numbers)-1
        elif direction == +1: destination_biome = max(all_biome_numbers)+1
    else:
        destination_biome = _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(activeobj), "Socket_0", 0
        ) + direction
    hair_in_destination_biome = [
        hayr[0]
        for hayr in hair[:]
        if _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
        ) == destination_biome
    ]
    for obj in objselection:
        if obj.type == "CURVES" and obj.modifiers:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    _secret_paint_1731_set_modifier_value(modif, "Socket_0", destination_biome)
                    _secret_paint_1731_set_modifier_value(modif, "Socket_3", False)
                    _secret_paint_1731_set_modifier_value(modif, "Socket_4", False)
                    _secret_paint_1731_set_modifier_value(modif, "Socket_5", False)
                    _secret_paint_1731_set_modifier_value(modif, "Socket_6", False)
                    if len(hair_in_destination_biome) >=1:
                        destination_modifier = _secret_paint_1731_paint_modifier(hair_in_destination_biome[0])
                        _secret_paint_1731_set_modifier_value(
                            modif, "Socket_2",
                            _secret_paint_1731_modifier_value(destination_modifier, "Socket_2", False),
                        )
                        _secret_paint_1731_set_modifier_value(
                            modif, "Socket_15",
                            _secret_paint_1731_modifier_value(destination_modifier, "Socket_15", False),
                        )
                    obj.location=obj.location
                    if hair_in_destination_biome:
                        destination_modifier = _secret_paint_1731_paint_modifier(hair_in_destination_biome[0])
                        _secret_paint_1731_set_modifier_value(
                            modif, "Socket_8",
                            _secret_paint_1731_modifier_value(destination_modifier, "Socket_8", ""),
                        )
    biome_remove_gaps(context, hair)
    return{'FINISHED'}
class biomegroupreorder(bpy.types.Operator):
    """Change Biome for the selected Paint Systems, Alt+Click to move at the top of the stack"""
    bl_idname = "secret.biomegroupreorder"
    bl_label = "Move Up"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    def invoke(self, context, event):
        buttonobj = bpy.data.objects.get(self.object_name)
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]
        if event.alt: move_to_extreme=True
        else: move_to_extreme=False
        biomegroupreorder_f(context, direction= -1, activeobj = buttonobj, objselection=objselection, move_to_extreme=move_to_extreme)
        return{'FINISHED'}
class biomegroupreorder2(bpy.types.Operator):
    """Change Biome for the selected Paint Systems, Alt+Click to move at the bottom of the stack"""
    bl_idname = "secret.biomegroupreorder2"
    bl_label = "Move Down"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    def invoke(self, context, event):
        buttonobj = bpy.data.objects.get(self.object_name)
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]
        if event.alt: move_to_extreme = True
        else: move_to_extreme = False
        biomegroupreorder_f(context, direction= +1, activeobj = buttonobj, objselection=objselection, move_to_extreme=move_to_extreme)
        return{'FINISHED'}
class legacy_panel_keyboard_delete(bpy.types.Operator):
    """Delete the selected Secret Paint rows when X is pressed over the panel."""
    bl_idname = "secret.panel_keyboard_delete"
    bl_label = "Delete Paint Systems in Panel"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        area = getattr(context, "area", None)
        region = getattr(context, "region", None)
        if (area is None or area.type != 'VIEW_3D' or
                region is None or region.type != 'UI'):
            return False
        return any(
            _secret_paint_1731_paint_modifier(obj) is not None
            for obj in context.selected_objects
        )
    def invoke(self, context, _event):
        selected_systems = [
            obj for obj in list(context.selected_objects)
            if _secret_paint_1731_paint_modifier(obj) is not None
        ]
        if not selected_systems:
            return {'PASS_THROUGH'}
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        affected_surfaces = []
        for obj in selected_systems:
            surface = getattr(obj, "parent", None)
            if surface is not None and surface not in affected_surfaces:
                affected_surfaces.append(surface)
        for obj in selected_systems:
            bpy.data.objects.remove(obj, do_unlink=True)
        for surface in affected_surfaces:
            try:
                biome_hair = find_all_listed_paintsystems(context, activeobj=surface)
                biome_remove_gaps(context, biome_hair)
            except Exception:
                pass
        if affected_surfaces:
            for obj in list(context.selected_objects):
                obj.select_set(False)
            replacement = affected_surfaces[0]
            replacement.select_set(True)
            context.view_layer.objects.active = replacement
        for area in getattr(context.screen, "areas", []) if context.screen else []:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}
class ToggleVisibilityOperatorRender(bpy.types.Operator):
    """Turn off Paint System. Shift+Click to Disable in the Viewport. Alt+Click to 'Solo' a paint system, like a photoshop layer"""
    bl_idname = "secret.toggle_visibilityrender"
    bl_label = "Toggle Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    object_biome: bpy.props.StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.toggle_visibilityrender")
        buttonbiome = int(self.object_biome)
        buttonobj = bpy.data.objects.get(self.object_name)
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]
        hair = find_all_listed_paintsystems(context, activeobj=context.object)
        hair_in_bgroup = [
            hayr[0]
            for hayr in hair[:]
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
            ) == buttonbiome
        ]
        for ob in objselection[:]:
            if ob not in hair_in_bgroup: objselection.remove(ob)
        if event.alt:
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(buttonobj), "Socket_4", False
            ) == True:
                for hayii in hair_in_bgroup:
                    if hayii.type == "CURVES":
                        for modif in hayii.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if _secret_paint_1731_modifier_value(modif, "Socket_3", False) == True:
                                    _secret_paint_1731_set_modifier_value(
                                        modif, "Input_99",
                                        not _secret_paint_1731_modifier_value(modif, "Input_99", False),
                                    )
                                _secret_paint_1731_set_modifier_value(modif, "Socket_3", False)
                                _secret_paint_1731_set_modifier_value(modif, "Socket_4", False)
                                hayii.location = hayii.location
            else:
                for hayyur in hair_in_bgroup:
                    if hayyur.type == "CURVES":
                        for modif in hayyur.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                _secret_paint_1731_set_modifier_value(modif, "Socket_3", False)
                                _secret_paint_1731_set_modifier_value(modif, "Socket_4", False)
                                hayyur.location = hayyur.location
                for hayii in hair_in_bgroup:
                    if hayii.type == "CURVES":
                        for modif in hayii.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if hayii in objselection:
                                    if _secret_paint_1731_modifier_value(modif, "Input_99", False) == True:
                                        _secret_paint_1731_set_modifier_value(modif, "Input_99", False)
                                        _secret_paint_1731_set_modifier_value(modif, "Socket_3", True)
                                    _secret_paint_1731_set_modifier_value(modif, "Socket_4", True)
                                else:
                                    if _secret_paint_1731_modifier_value(modif, "Input_99", False) == False:
                                        _secret_paint_1731_set_modifier_value(modif, "Socket_3", True)
                                        _secret_paint_1731_set_modifier_value(modif, "Input_99", True)
                                hayii.location=hayii.location
        elif event.shift:
            button_modifier = _secret_paint_1731_paint_modifier(buttonobj)
            mute_visibility_render = _secret_paint_1731_modifier_value(button_modifier, "Input_99", False)
            mute_visibility_viewport = _secret_paint_1731_modifier_value(button_modifier, "Socket_14", False)
            if mute_visibility_render == True:
                mute_visibility_render_new = False
                mute_visibility_viewport_new = True
            elif mute_visibility_viewport == True and mute_visibility_render == False:
                mute_visibility_render_new = False
                mute_visibility_viewport_new = False
            elif mute_visibility_viewport == False and mute_visibility_render == False:
                mute_visibility_render_new = False
                mute_visibility_viewport_new = True
            for obj in objselection:
                if obj.type == "CURVES":
                    for modif in obj.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            _secret_paint_1731_set_modifier_value(modif, "Input_99", mute_visibility_render_new)
                            _secret_paint_1731_set_modifier_value(modif, "Socket_14", mute_visibility_viewport_new)
                            obj.location=obj.location
        else:
            button_modifier = _secret_paint_1731_paint_modifier(buttonobj)
            mute_visibility_render = _secret_paint_1731_modifier_value(button_modifier, "Input_99", False)
            mute_visibility_viewport = _secret_paint_1731_modifier_value(button_modifier, "Socket_14", False)
            if mute_visibility_render == True or mute_visibility_viewport == True:
                mute_visibility_render_new = False
                mute_visibility_viewport_new = False
            else:
                mute_visibility_render_new = not mute_visibility_render
                mute_visibility_viewport_new = mute_visibility_viewport
            for obj in objselection:
                if obj.type == "CURVES":
                    for modif in obj.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            _secret_paint_1731_set_modifier_value(modif, "Input_99", mute_visibility_render_new)
                            _secret_paint_1731_set_modifier_value(modif, "Socket_14", mute_visibility_viewport_new)
                            obj.location=obj.location
            for hayyur in hair_in_bgroup:
                if hayyur.type == "CURVES":
                    for modif in hayyur.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            _secret_paint_1731_set_modifier_value(modif, "Socket_3", False)
                            _secret_paint_1731_set_modifier_value(modif, "Socket_4", False)
                            hayyur.location = hayyur.location
        _secret_paint_1731_clear_panel_cache("system_visibility")
        _secret_paint_1731_tag_panel_redraw(context)
        return {'FINISHED'}
class ToggleVisibilityOperatorRenderBiome(bpy.types.Operator):
    """Turn off The entire biome. Shift+Click to Disable in the Viewport. Alt+Click to 'Solo' a Biome and mute the other ones"""
    bl_idname = "secret.toggle_visibilityrender_biome"
    bl_label = "Toggle Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.toggle_visibilityrender_biome")
        hair = find_all_listed_paintsystems(context, activeobj=context.object)
        hair_in_bgroup =[]
        hair_in_OTHER_bgroups =[]
        for hayr in hair[:]:
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
            ) == int(self.object_biome):
                hair_in_bgroup.append(hayr[0])
            else: hair_in_OTHER_bgroups.append(hayr[0])
        if event.alt:
            if True in [
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hairr), "Socket_6", False
                )
                for hairr in hair_in_bgroup
            ]:
                for hayii in hair[:]:
                    if hayii[0].type == "CURVES":
                        for modif in hayii[0].modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if _secret_paint_1731_modifier_value(modif, "Socket_5", False) == True:
                                    _secret_paint_1731_set_modifier_value(
                                        modif, "Socket_2",
                                        not _secret_paint_1731_modifier_value(modif, "Socket_2", False),
                                    )
                                _secret_paint_1731_set_modifier_value(modif, "Socket_5", False)
                                _secret_paint_1731_set_modifier_value(modif, "Socket_6", False)
                                hayii[0].location = hayii[0].location
            else:
                for hayyur in hair[:]:
                    if hayyur[0].type == "CURVES":
                        for modif in hayyur[0].modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                _secret_paint_1731_set_modifier_value(modif, "Socket_5", False)
                                _secret_paint_1731_set_modifier_value(modif, "Socket_6", False)
                                hayyur[0].location = hayyur[0].location
                for hayii in hair[:]:
                    if hayii[0].type == "CURVES":
                        for modif in hayii[0].modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if hayii[0] in hair_in_bgroup:
                                    if _secret_paint_1731_modifier_value(modif, "Socket_2", False) == True:
                                        _secret_paint_1731_set_modifier_value(modif, "Socket_2", False)
                                        _secret_paint_1731_set_modifier_value(modif, "Socket_5", True)
                                    _secret_paint_1731_set_modifier_value(modif, "Socket_6", True)
                                else:
                                    if _secret_paint_1731_modifier_value(modif, "Socket_2", False) == False:
                                        _secret_paint_1731_set_modifier_value(modif, "Socket_5", True)
                                        _secret_paint_1731_set_modifier_value(modif, "Socket_2", True)
                                hayii[0].location=hayii[0].location
        elif event.shift:
            mute_biome_visibility_render = False if False in [
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hairr), "Socket_2", False
                ) for hairr in hair_in_bgroup
            ] else True
            mute_biome_visibility_viewport = False if False in [
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hairr), "Socket_15", False
                ) for hairr in hair_in_bgroup
            ] else True
            if mute_biome_visibility_render == True:
                mute_biome_visibility_render_new = False
                mute_biome_visibility_viewport_new = True
            elif mute_biome_visibility_viewport == True and mute_biome_visibility_render == False:
                mute_biome_visibility_render_new = False
                mute_biome_visibility_viewport_new = False
            elif mute_biome_visibility_viewport == False and mute_biome_visibility_render == False:
                mute_biome_visibility_render_new = False
                mute_biome_visibility_viewport_new = True
            for obj in hair_in_bgroup:
                if obj.type == "CURVES":
                    for modif in obj.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            _secret_paint_1731_set_modifier_value(modif, "Socket_2", mute_biome_visibility_render_new)
                            _secret_paint_1731_set_modifier_value(modif, "Socket_15", mute_biome_visibility_viewport_new)
                            obj.location=obj.location
        else:
            mute_biome_visibility_render = False if False in [
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hairr), "Socket_2", False
                ) for hairr in hair_in_bgroup
            ] else True
            mute_biome_visibility_viewport = False if False in [
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hairr), "Socket_15", False
                ) for hairr in hair_in_bgroup
            ] else True
            if mute_biome_visibility_render == True or mute_biome_visibility_viewport == True:
                mute_biome_visibility_render_new = False
                mute_biome_visibility_viewport_new = False
            else:
                mute_biome_visibility_render_new = not mute_biome_visibility_render
                mute_biome_visibility_viewport_new = mute_biome_visibility_viewport
            for obj in hair_in_bgroup:
                if obj.type == "CURVES":
                    for modif in obj.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            _secret_paint_1731_set_modifier_value(modif, "Socket_2", mute_biome_visibility_render_new)
                            _secret_paint_1731_set_modifier_value(modif, "Socket_15", mute_biome_visibility_viewport_new)
                            obj.location=obj.location
            for hayii in hair[:]:
                if hayii[0].type == "CURVES":
                    for modif in hayii[0].modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            _secret_paint_1731_set_modifier_value(modif, "Socket_5", False)
                            _secret_paint_1731_set_modifier_value(modif, "Socket_6", False)
                            hayii[0].location = hayii[0].location
        _secret_paint_1731_clear_panel_cache("biome_visibility")
        _secret_paint_1731_tag_panel_redraw(context)
        return {'FINISHED'}
class toggle_display_bounds(bpy.types.Operator):
    """Display as Bounds is the most efficient way to preserve the viewport performance when diplaying a large number of individual objects"""
    bl_idname = "secret.toggle_display_bounds"
    bl_label = "Toggle Display as Bounds"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.toggle_display_bounds")
        buttonobj = bpy.data.objects.get(self.object_name)
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]
        buttonobj_status= buttonobj.display_type
        for obj in objselection:
            obj.display_type = 'BOUNDS' if buttonobj_status != 'BOUNDS' else 'TEXTURED'
        return {'FINISHED'}
class toggle_display_bounds_biome(bpy.types.Operator):
    """Display as Bounds is the most efficient way to preserve the viewport performance when diplaying a large number of individual objects"""
    bl_idname = "secret.toggle_display_bounds_biome"
    bl_label = "Toggle Display as Bounds"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.toggle_display_bounds_biome")
        obj = bpy.context.active_object
        hair = find_all_listed_paintsystems(context, activeobj=obj)
        hair_in_bgroup = [
            hayr[0]
            for hayr in hair[:]
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
            ) == int(self.object_biome)
        ]
        if hair_in_bgroup:
            buttonobj_status= hair_in_bgroup[0].display_type
            for obj in hair_in_bgroup:
                obj.display_type = 'BOUNDS' if buttonobj_status != 'BOUNDS' else 'TEXTURED'
        return {'FINISHED'}
class secretpaint_viewport_mask_biome(bpy.types.Operator):
    """Toggle Mask for the entire Biome"""
    bl_idname = "object.secretpaint_viewport_mask_biome"
    bl_label = "Temporary Viewport Mask"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="object.secretpaint_viewport_mask_biome")
        obj = bpy.context.active_object
        hair = find_all_listed_paintsystems(context, activeobj=obj)
        hair_in_bgroup = [
            hayr[0]
            for hayr in hair[:]
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
            ) == int(self.object_biome)
        ]
        maskobsel=None
        if hair_in_bgroup:
            if event.alt:
                for x in bpy.context.selected_objects: x.select_set(False)
                for hai in hair_in_bgroup:
                    maskobsel = _secret_paint_1731_modifier_value(
                        _secret_paint_1731_paint_modifier(hai), "Input_97"
                    )
                    if maskobsel:
                        break
                if maskobsel:
                    bpy.context.view_layer.objects.active = maskobsel
                    maskobsel.select_set(True)
                else:
                    for ob in bpy.context.scene.objects:
                        if ob.name.startswith("Secret Paint Viewport Mask"):
                            bpy.context.view_layer.objects.active = ob
                            ob.select_set(True)
                            break
            elif event.shift: secretpaint_viewport_mask_function(self, context, activeobj=hair_in_bgroup[0], objselection=hair_in_bgroup, force_new_maskObj=True, called_for_entire_biome = True)
            else: secretpaint_viewport_mask_function(self, context, activeobj=hair_in_bgroup[0], objselection=hair_in_bgroup, called_for_entire_biome = True)
            self.object_name = ("")
        return {'FINISHED'}
_SECRET_PAINT_1731_SCULPT_BRUSH_STATE = None
_SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING = False
_SECRET_PAINT_1731_SCULPT_BRUSH_MSGBUS_OWNER = object()
_SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED = False
_SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = False
_SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
_SECRET_PAINT_1731_SCULPT_BRUSH_ACTIVE_INTERVAL = 0.05
_SECRET_PAINT_1731_SCULPT_BRUSH_IDLE_INTERVAL = 0.75
_SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE = False
_SECRET_PAINT_1731_RIGHT_DELETE_TOKEN = 0
class _SecretPaint1731SilentReporter:
    def report(self, *_args, **_kwargs):
        pass
_SECRET_PAINT_1731_SILENT_REPORTER = _SecretPaint1731SilentReporter()
def _secret_paint_1731_active_sculpt_paint_system(context):
    try:
        if getattr(context, "mode", "") != "SCULPT_CURVES":
            return None
        active_object = context.active_object
        if active_object is None or active_object.type not in {"CURVE", "CURVES"}:
            return None
        if active_object.parent is None or active_object.parent.type != "MESH":
            return None
        if _secret_paint_1731_paint_modifier(active_object) is None:
            return None
        return active_object
    except Exception:
        return None


def _secret_paint_1731_density_base_distance(system):
    """Return K, the non-accumulating minimum distance stored for a system."""
    modifier = _secret_paint_1731_paint_modifier(system)
    try:
        distance = float(
            _secret_paint_1731_modifier_value(
                modifier,
                "Socket_11",
                _SECRET_PAINT_DENSITY_FALLBACK,
            ) or _SECRET_PAINT_DENSITY_FALLBACK
        )
        if distance > 0.0 and math.isfinite(distance):
            return distance
    except (TypeError, ValueError):
        pass
    return _SECRET_PAINT_DENSITY_FALLBACK


def _secret_paint_1731_accumulate_attempt_count(brush_radius, base_distance):
    """Cap the first accumulating stroke at one quarter of K's brush count."""
    try:
        brush_area = math.pi * float(brush_radius) ** 2
        base_cell_area = float(base_distance) ** 2
        attempts = int(round(
            (brush_area / base_cell_area)
            * _SECRET_PAINT_ACCUMULATE_FIRST_STROKE_FRACTION
        ))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None
    return max(1, min(_SECRET_PAINT_DENSITY_ATTEMPTS_MAX, attempts))


def _secret_paint_1731_density_space_radius(system, world_radius):
    """Convert a world brush radius into the space used by minimum_distance."""
    try:
        terrain_scale = abs(float(
            _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(system),
                "Input_100",
                1.0,
            ) or 1.0
        ))
        radius = float(world_radius) / terrain_scale
        return radius if radius > 0.0 and math.isfinite(radius) else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _secret_paint_1731_density_brush_radius(
        context,
        event,
        system,
        brush,
):
    """Resolve the brush radius at the hit in minimum_distance space."""
    try:
        pressure = float(getattr(event, "pressure", 1.0) or 1.0)
    except (TypeError, ValueError):
        pressure = 1.0
    pressure = max(0.01, pressure) if getattr(brush, "use_pressure_size", False) else 1.0

    try:
        if getattr(brush, "use_locked_size", "VIEW") == 'SCENE':
            radius = float(brush.unprojected_size) * pressure * 0.5
            return _secret_paint_1731_density_space_radius(system, radius)
    except (AttributeError, TypeError, ValueError):
        return None

    try:
        _area, region, space_data, coord = _secret_paint_q_view_area_region_space(
            context,
            event,
        )
        if region is None or space_data is None or coord is None:
            return None
        center = _secret_paint_q_preview_mask_location(
            context,
            event,
            system,
            allow_depth_fallback=False,
        )
        if center is None:
            return None
        pixel_radius = max(0.5, float(brush.size) * pressure * 0.5)
        from bpy_extras import view3d_utils
        edge = view3d_utils.region_2d_to_location_3d(
            region,
            space_data.region_3d,
            (coord[0] + pixel_radius, coord[1]),
            center,
        )
        radius = (edge - center).length
        return _secret_paint_1731_density_space_radius(system, radius)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return None


def _secret_paint_1731_set_accumulate_density_attempts(
        context,
        event,
        system,
        brush=None,
        base_distance=None,
):
    """Set Count Max once for the Density stroke beginning at event."""
    if not _secret_paint_accumulate_manual_paint(context) or system is None:
        return False
    if brush is None:
        curves_sculpt = getattr(context.tool_settings, "curves_sculpt", None)
        brush = getattr(curves_sculpt, "brush", None)
    if _secret_paint_1731_curves_brush_type(brush) != "DENSITY":
        return False
    if base_distance is None:
        base_distance = _secret_paint_1731_density_base_distance(system)
    radius = _secret_paint_1731_density_brush_radius(
        context,
        event,
        system,
        brush,
    )
    attempts = _secret_paint_1731_accumulate_attempt_count(radius, base_distance)
    if attempts is None:
        return False
    try:
        brush_key = brush.as_pointer()
        _SECRET_PAINT_ACCUMULATE_ATTEMPTS_BACKUP.setdefault(
            brush_key,
            int(brush.curves_sculpt_settings.density_add_attempts),
        )
        brush.curves_sculpt_settings.density_add_attempts = attempts
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _secret_paint_update_accumulate_manual_paint(preferences, context):
    """Apply a preference toggle to the current Density brush immediately."""
    enabled = bool(preferences.accumulate_manual_paint)
    density_brushes = [
        brush for brush in bpy.data.brushes
        if _secret_paint_1731_curves_brush_type(brush) == "DENSITY"
    ]
    if not enabled:
        for brush in density_brushes:
            try:
                previous_attempts = _SECRET_PAINT_ACCUMULATE_ATTEMPTS_BACKUP.pop(
                    brush.as_pointer(),
                    None,
                )
                if previous_attempts is not None:
                    brush.curves_sculpt_settings.density_add_attempts = previous_attempts
            except (AttributeError, TypeError, ValueError):
                pass

    candidates = [
        getattr(context, "active_object", None),
        getattr(bpy.context, "active_object", None),
    ]
    try:
        candidates.extend(
            obj for obj in bpy.data.objects
            if getattr(obj, "mode", "") == "SCULPT_CURVES"
        )
    except (AttributeError, ReferenceError, RuntimeError):
        pass
    system = next(
        (
            obj for obj in candidates
            if obj is not None and
            obj.type in {"CURVE", "CURVES"} and
            _secret_paint_1731_paint_modifier(obj) is not None
        ),
        None,
    )
    if system is None:
        return
    minimum_distance = _secret_paint_1731_density_base_distance(system)
    if enabled:
        minimum_distance *= _SECRET_PAINT_ACCUMULATE_DISTANCE_SCALE
    for brush in density_brushes:
        try:
            brush.curves_sculpt_settings.minimum_distance = minimum_distance
        except (AttributeError, TypeError, ValueError):
            pass


def _secret_paint_1731_sculpt_brush_key(context, system):
    try:
        curves_sculpt = getattr(context.tool_settings, "curves_sculpt", None)
        brush = getattr(curves_sculpt, "brush", None)
        brush_pointer = brush.as_pointer() if brush is not None else 0
        brush_name = getattr(brush, "name_full", "") if brush is not None else ""
        brush_type = _secret_paint_1731_curves_brush_type(brush)
        try:
            workspace_tool = context.workspace.tools.from_space_view3d_mode(
                "SCULPT_CURVES",
                create=False,
            )
            tool_id = getattr(workspace_tool, "idname", "") or ""
        except Exception:
            tool_id = ""
        asset_reference = getattr(
            curves_sculpt,
            "brush_asset_reference",
            None,
        )
        asset_key = (
            getattr(asset_reference, "asset_library_type", ""),
            getattr(asset_reference, "asset_library_identifier", ""),
            getattr(asset_reference, "relative_asset_identifier", ""),
        )
        return (
            system.as_pointer(),
            brush_pointer,
            brush_name,
            brush_type,
            tool_id,
            asset_key,
        )
    except Exception:
        return None
def _secret_paint_1731_apply_sculpt_ids_silently(context, system):
    global _SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING
    if _SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING:
        return False
    if system is None:
        return False
    brush_change_started = _secret_paint_trace_session(
        "Sculpt Curves brush change",
        object_name=getattr(system, "name", None),
        current_mode=getattr(system, "mode", None),
    )
    view_layer = getattr(context, "view_layer", None)
    active_before = (
        getattr(getattr(view_layer, "objects", None), "active", None)
        if view_layer is not None
        else None
    )
    selected_before = tuple(getattr(context, "selected_objects", ()))
    try:
        _SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING = True
        paint_modifier = _secret_paint_1731_paint_modifier(system)
        procedural_enabled = bool(
            _secret_paint_1731_modifier_value(
                paint_modifier,
                "Input_69",
                False,
            )
        )
        if procedural_enabled:
            _secret_paint_q_apply_ids(
                _SECRET_PAINT_1731_SILENT_REPORTER,
                context,
                system,
            )
            handled = True
        else:
            handled = _secret_paint_apply_missing_ids(system)
            if handled:
                _secret_paint_1731_set_modifier_value(
                    paint_modifier,
                    "Input_69",
                    False,
                )
        _secret_paint_trace_end(
            "Sculpt Curves brush change",
            brush_change_started,
            handled=handled,
            procedural_conversion=procedural_enabled,
            mode_unchanged=getattr(system, "mode", None) == "SCULPT_CURVES",
        )
        return handled
    except Exception as error:
        _secret_paint_trace_end(
            "Sculpt Curves brush change",
            brush_change_started,
            handled=False,
            error=repr(error),
        )
        return False
    finally:
        if view_layer is not None:
            try:
                selected_before_set = set(selected_before)
                for obj in tuple(getattr(context, "selected_objects", ())):
                    if obj not in selected_before_set:
                        obj.select_set(False)
                view_objects = view_layer.objects
                for obj in selected_before:
                    if obj.name in view_objects:
                        obj.select_set(True)
                if (
                    active_before is not None and
                    active_before.name in view_objects
                ):
                    view_objects.active = active_before
            except (AttributeError, ReferenceError, RuntimeError):
                pass
        _SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING = False
def _secret_paint_1731_track_sculpt_brush(context, system=None, apply_on_change=True):
    global _SECRET_PAINT_1731_SCULPT_BRUSH_STATE
    if system is None:
        system = _secret_paint_1731_active_sculpt_paint_system(context)
    if system is None:
        _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = None
        return
    key = _secret_paint_1731_sculpt_brush_key(context, system)
    if key is None:
        return "NO_CONTEXT"
    previous_key = _SECRET_PAINT_1731_SCULPT_BRUSH_STATE
    if previous_key == key:
        return "UNCHANGED"
    if globals().get("_secret_paint_q_selection_mode") in {"PLANT", "TERRAIN"}:
        _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = key
        return "DEFERRED"
    if _SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE:
        _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = key
        return "DEFERRED"
    same_system_brush_changed = (
        apply_on_change and
        previous_key is not None and
        previous_key[0] == key[0] and
        previous_key[1:] != key[1:]
    )
    brush_identity_changed = (
        previous_key is not None and
        previous_key[1:4] != key[1:4]
    )
    applies_ids = (
        brush_identity_changed and
        key[3] in {"DENSITY", "DELETE"}
    )
    _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = key
    if same_system_brush_changed and applies_ids:
        if _secret_paint_1731_apply_sculpt_ids_silently(context, system):
            return "APPLIED"
        _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = previous_key
        return "RETRY"
    return "UPDATED"
def _secret_paint_1731_track_active_sculpt_context(apply_on_change):
    """Track the active paint system, scanning other windows only on demand."""
    try:
        system = _secret_paint_1731_active_sculpt_paint_system(bpy.context)
        if system is not None:
            return _secret_paint_1731_track_sculpt_brush(
                bpy.context,
                system,
                apply_on_change=apply_on_change,
            )
        window_manager = getattr(bpy.context, "window_manager", None)
        if window_manager is None:
            return None
        for window in tuple(window_manager.windows):
            screen = getattr(window, "screen", None)
            if screen is None:
                continue
            for area in screen.areas:
                if area.type != "VIEW_3D":
                    continue
                region = next(
                    (
                        candidate for candidate in area.regions
                        if candidate.type == "WINDOW"
                    ),
                    None,
                )
                if region is None:
                    continue
                try:
                    with bpy.context.temp_override(
                            window=window,
                            area=area,
                            region=region,
                    ):
                        system = _secret_paint_1731_active_sculpt_paint_system(
                            bpy.context
                        )
                        if system is None:
                            continue
                        return _secret_paint_1731_track_sculpt_brush(
                            bpy.context,
                            system,
                            apply_on_change=apply_on_change,
                        )
                except Exception:
                    continue
    except Exception:
        return None
    return None
def _secret_paint_1731_sculpt_brush_notify_dispatch():
    global _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING
    global _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT
    _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = False
    if not _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED:
        return None
    if not _SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING:
        result = _secret_paint_1731_track_active_sculpt_context(
            apply_on_change=True
        )
        if result in {None, "NO_CONTEXT", "RETRY"}:
            if _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT < 2:
                _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT += 1
                _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = True
                return 0.05
        else:
            _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
    return None
def _secret_paint_1731_sculpt_brush_changed():
    """Coalesce RNA notifications and apply IDs on the next safe main-loop tick."""
    global _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING
    global _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT
    if (_SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING or
            _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING):
        return
    _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = True
    _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
    try:
        bpy.app.timers.register(
            _secret_paint_1731_sculpt_brush_notify_dispatch,
            first_interval=0.0,
        )
    except Exception:
        _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = False
def _secret_paint_1731_sculpt_brush_monitor_tick():
    """Cheap fallback for Blender brush changes that publish no RNA event."""
    global _SECRET_PAINT_1731_SCULPT_BRUSH_STATE
    global _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT
    if not _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED:
        return None
    if _SECRET_PAINT_1731_SCULPT_BRUSH_APPLYING:
        return _SECRET_PAINT_1731_SCULPT_BRUSH_ACTIVE_INTERVAL
    result = _secret_paint_1731_track_active_sculpt_context(
        apply_on_change=True
    )
    if result in {None, "NO_CONTEXT"}:
        _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = None
        _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
        return _SECRET_PAINT_1731_SCULPT_BRUSH_IDLE_INTERVAL
    if result == "RETRY":
        _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT += 1
        return (
            _SECRET_PAINT_1731_SCULPT_BRUSH_ACTIVE_INTERVAL
            if _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT <= 2
            else _SECRET_PAINT_1731_SCULPT_BRUSH_IDLE_INTERVAL
        )
    _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
    return _SECRET_PAINT_1731_SCULPT_BRUSH_ACTIVE_INTERVAL
def _secret_paint_1731_start_sculpt_brush_monitor(force=False):
    global _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED
    global _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING
    global _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT
    if _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED and not force:
        return
    try:
        if bpy.app.timers.is_registered(
                _secret_paint_1731_sculpt_brush_notify_dispatch):
            bpy.app.timers.unregister(
                _secret_paint_1731_sculpt_brush_notify_dispatch
            )
        _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = False
        _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
        bpy.msgbus.clear_by_owner(
            _SECRET_PAINT_1731_SCULPT_BRUSH_MSGBUS_OWNER
        )
        if bpy.app.timers.is_registered(
                _secret_paint_1731_sculpt_brush_monitor_tick):
            bpy.app.timers.unregister(
                _secret_paint_1731_sculpt_brush_monitor_tick
            )
    except Exception:
        pass
    subscription_keys = [
        (bpy.types.CurvesSculpt, "brush"),
        (bpy.types.CurvesSculpt, "brush_asset_reference"),
    ]
    asset_reference_type = getattr(bpy.types, "AssetWeakReference", None)
    if asset_reference_type is not None:
        subscription_keys.extend((
            (asset_reference_type, "asset_library_type"),
            (asset_reference_type, "asset_library_identifier"),
            (asset_reference_type, "relative_asset_identifier"),
        ))
    subscription_count = 0
    for subscription_key in subscription_keys:
        try:
            bpy.msgbus.subscribe_rna(
                key=subscription_key,
                owner=_SECRET_PAINT_1731_SCULPT_BRUSH_MSGBUS_OWNER,
                args=(),
                notify=_secret_paint_1731_sculpt_brush_changed,
                options={'PERSISTENT'},
            )
            subscription_count += 1
        except Exception:
            continue
    timer_registered = False
    try:
        bpy.app.timers.register(
            _secret_paint_1731_sculpt_brush_monitor_tick,
            first_interval=_SECRET_PAINT_1731_SCULPT_BRUSH_ACTIVE_INTERVAL,
        )
        timer_registered = True
    except Exception:
        pass
    _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED = bool(
        subscription_count or timer_registered
    )
    if _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED:
        _secret_paint_1731_track_active_sculpt_context(apply_on_change=False)
def _secret_paint_1731_stop_sculpt_brush_monitor():
    global _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED
    global _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING
    global _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT
    global _SECRET_PAINT_1731_SCULPT_BRUSH_STATE
    try:
        if bpy.app.timers.is_registered(
                _secret_paint_1731_sculpt_brush_notify_dispatch):
            bpy.app.timers.unregister(
                _secret_paint_1731_sculpt_brush_notify_dispatch
            )
        if bpy.app.timers.is_registered(
                _secret_paint_1731_sculpt_brush_monitor_tick):
            bpy.app.timers.unregister(
                _secret_paint_1731_sculpt_brush_monitor_tick
            )
        bpy.msgbus.clear_by_owner(
            _SECRET_PAINT_1731_SCULPT_BRUSH_MSGBUS_OWNER
        )
    except Exception:
        pass
    _SECRET_PAINT_1731_SCULPT_BRUSH_SUBSCRIBED = False
    _SECRET_PAINT_1731_SCULPT_BRUSH_NOTIFY_PENDING = False
    _SECRET_PAINT_1731_SCULPT_BRUSH_RETRY_COUNT = 0
    _SECRET_PAINT_1731_SCULPT_BRUSH_STATE = None
@persistent
def _secret_paint_1731_sculpt_brush_load_post(_unused):
    _secret_paint_1731_start_sculpt_brush_monitor(force=True)
class brush_density_while_painting(bpy.types.Operator):
    """While hovering with the mouse on the terrain, press the shortcut (D) to change the brush density. The Addon will remember the density you chose for each system independently"""
    bl_idname = "secret.brush_density_while_painting"
    bl_label = "Change Brush Density"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        system = _secret_paint_1731_active_sculpt_paint_system(context)
        self._accumulate_manual_paint = _secret_paint_accumulate_manual_paint(context)
        self._system_name = getattr(system, "name", "")
        if system is not None:
            _secret_paint_1731_apply_sculpt_ids_silently(context, system)
            _secret_paint_1731_track_sculpt_brush(
                context,
                system,
                apply_on_change=False,
            )
        context3sculptbrush(context)
        if self._accumulate_manual_paint and system is not None:
            try:
                brush = context.tool_settings.curves_sculpt.brush
                brush.curves_sculpt_settings.minimum_distance = (
                    _secret_paint_1731_density_base_distance(system)
                )
            except (AttributeError, TypeError, ValueError):
                pass
        bpy.ops.sculpt_curves.min_distance_edit('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        self._cancel = False
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        if self._cancel:
            pass
            return {'CANCELLED'}
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE',"ESC"}:
            if getattr(self, "_accumulate_manual_paint", False):
                system = bpy.data.objects.get(getattr(self, "_system_name", ""))
                modifier = _secret_paint_1731_paint_modifier(system)
                try:
                    brush = context.tool_settings.curves_sculpt.brush
                    settings = brush.curves_sculpt_settings
                    if event.type == 'LEFTMOUSE':
                        base_distance = float(settings.minimum_distance)
                        _secret_paint_1731_set_modifier_value(
                            modifier,
                            "Socket_11",
                            base_distance,
                        )
                    else:
                        base_distance = _secret_paint_1731_density_base_distance(
                            system
                        )
                    settings.minimum_distance = (
                        base_distance * _SECRET_PAINT_ACCUMULATE_DISTANCE_SCALE
                    )
                    if event.type == 'LEFTMOUSE':
                        _secret_paint_1731_set_accumulate_density_attempts(
                            context,
                            event,
                            system,
                            brush=brush,
                            base_distance=base_distance,
                        )
                except (AttributeError, TypeError, ValueError):
                    pass
            else:
                try:
                    _secret_paint_1731_set_modifier_value(
                        _secret_paint_1731_paint_modifier(bpy.context.active_object),
                        "Socket_11",
                        context.tool_settings.curves_sculpt.brush.curves_sculpt_settings.minimum_distance,
                    )
                except: pass
            bpy.app.timers.register(lambda: setattr(self, '_cancel', True), first_interval=0.001)
        return {'PASS_THROUGH'}


class accumulate_density_stroke_start(bpy.types.Operator):
    """Calculate Count Max once before an accumulating Density stroke."""
    bl_idname = "secret.accumulate_density_stroke_start"
    bl_label = "Accumulate Density Stroke Start"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        if not _secret_paint_accumulate_manual_paint(context):
            return {'PASS_THROUGH'}
        system = _secret_paint_1731_active_sculpt_paint_system(context)
        _secret_paint_1731_set_accumulate_density_attempts(
            context,
            event,
            system,
        )
        return {'PASS_THROUGH'}


def _secret_paint_1731_curves_brush_type(brush):
    if brush is None:
        return ""
    try:
        if hasattr(brush, "curves_sculpt_brush_type"):
            return brush.curves_sculpt_brush_type
        return getattr(brush, "curves_sculpt_tool", "")
    except Exception:
        return ""


class right_click_delete_while_painting(bpy.types.Operator):
    """Right-drag with Density REMOVE, then restore the brush settings."""
    bl_idname = "secret.right_click_delete_while_painting"
    bl_label = "Right Click Delete While Painting"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        active_system = _secret_paint_1731_active_sculpt_paint_system(context)
        curves_sculpt = getattr(
            getattr(context, "tool_settings", None),
            "curves_sculpt",
            None,
        )
        brush = getattr(curves_sculpt, "brush", None)
        return (
            getattr(context, "area", None) is not None and
            context.area.type == 'VIEW_3D' and
            active_system is not None and
            _secret_paint_1731_curves_brush_type(brush) == "DENSITY"
        )

    def _restore_density_settings(self):
        global _SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE
        if self._token != _SECRET_PAINT_1731_RIGHT_DELETE_TOKEN:
            return None
        try:
            settings = self._density_brush.curves_sculpt_settings
            settings.density_mode = self._previous_density_mode
            settings.minimum_distance = self._previous_minimum_distance
        except Exception:
            pass
        finally:
            if self._token == _SECRET_PAINT_1731_RIGHT_DELETE_TOKEN:
                _SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE = False
        return None

    def invoke(self, context, event):
        global _SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE
        global _SECRET_PAINT_1731_RIGHT_DELETE_TOKEN
        if _SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE:
            return {'PASS_THROUGH'}

        system = _secret_paint_1731_active_sculpt_paint_system(context)
        if system is None:
            return {'PASS_THROUGH'}
        try:
            ids_applied = _secret_paint_apply_missing_ids(system)
        except Exception:
            ids_applied = False
        if ids_applied:
            _secret_paint_1731_set_modifier_value(
                _secret_paint_1731_paint_modifier(system),
                "Input_69",
                False,
            )
        _secret_paint_1731_track_sculpt_brush(
            context,
            system,
            apply_on_change=False,
        )

        curves_sculpt = getattr(context.tool_settings, "curves_sculpt", None)
        density_brush = getattr(curves_sculpt, "brush", None)
        if _secret_paint_1731_curves_brush_type(density_brush) != "DENSITY":
            return {'PASS_THROUGH'}

        settings = getattr(density_brush, "curves_sculpt_settings", None)
        if settings is None:
            return {'PASS_THROUGH'}

        self._density_brush = density_brush
        self._previous_density_mode = settings.density_mode
        self._previous_minimum_distance = settings.minimum_distance
        _SECRET_PAINT_1731_RIGHT_DELETE_TOKEN += 1
        self._token = _SECRET_PAINT_1731_RIGHT_DELETE_TOKEN
        _SECRET_PAINT_1731_RIGHT_DELETE_ACTIVE = True

        try:
            settings.density_mode = 'REMOVE'
            settings.minimum_distance = 9000
        except Exception:
            self._restore_density_settings()
            return {'CANCELLED'}

        try:
            stroke_poll = bpy.ops.sculpt_curves.brush_stroke.poll()
            if stroke_poll:
                stroke_result = bpy.ops.sculpt_curves.brush_stroke(
                    'INVOKE_DEFAULT',
                    mode='NORMAL',
                    brush_toggle='None',
                    pen_flip=False,
                )
            else:
                stroke_result = {'CANCELLED'}
        except Exception:
            stroke_result = {'CANCELLED'}

        if 'RUNNING_MODAL' not in stroke_result:
            self._restore_density_settings()
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
            self._restore_density_settings()
            return {'FINISHED', 'PASS_THROUGH'}
        if event.type in {'ESC', 'WINDOW_DEACTIVATE'}:
            self._restore_density_settings()
            return {'CANCELLED', 'PASS_THROUGH'}
        return {'PASS_THROUGH'}

    def cancel(self, _context):
        self._restore_density_settings()


def context3sculptbrush(context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    keep_active_brush = kwargs.get("keep_active_brush") if "keep_active_brush" in kwargs else False
    context_started = _secret_paint_trace_begin(
        "context3sculptbrush",
        object=getattr(activeobj, "name", None),
        object_type=getattr(activeobj, "type", None),
        starting_mode=getattr(activeobj, "mode", None),
        keep_active_brush=keep_active_brush,
    )
    if activeobj.type == "CURVES":
        surface_setup_started = time.perf_counter()
        if activeobj.data.users >= 2 and activeobj.data.surface!=activeobj.parent: activeobj.data.surface = activeobj.parent
        active_render_UV = None
        custom_uv = None
        for uvmap in activeobj.data.surface.data.uv_layers:
            if uvmap.name == "Secret Paint UV": custom_uv = uvmap.name
            if uvmap.active_render: active_render_UV = uvmap.name
        if not activeobj.data.surface_uv_map or activeobj.data.surface_uv_map not in [custom_uv,active_render_UV]:
            if custom_uv: activeobj.data.surface_uv_map = custom_uv
            elif active_render_UV: activeobj.data.surface_uv_map = active_render_UV
        _secret_paint_trace_end("sculpt context surface and UV setup", surface_setup_started)
        mode_started = time.perf_counter()
        if activeobj.mode != "SCULPT_CURVES":
            bpy.ops.object.mode_set(mode="SCULPT_CURVES")
            _secret_paint_trace_end("bpy.ops.object.mode_set SCULPT_CURVES", mode_started)
        else:
            _secret_paint_trace_end(
                "skip Sculpt Curves mode entry", mode_started,
                reason="target system is already in Sculpt Curves mode",
            )
        if not keep_active_brush:
            tool_started = time.perf_counter()
            try:
                if bpy.app.version_string >= "4.3.0": bpy.ops.wm.tool_set_by_id(name="builtin_brush.density")
                else: bpy.ops.wm.tool_set_by_id(name="builtin_brush.Density")
            except: pass
            _secret_paint_trace_end("set Density sculpt tool", tool_started)
        brush_setup_started = time.perf_counter()
        brush_density = []
        brush_grow = []
        brush_add = []
        brush_delete = []
        brush_puff = []
        brush_comb = []
        for brush in bpy.data.brushes:
            if bpy.app.version_string >= "5.0.0":
                if brush.curves_sculpt_brush_type == 'DENSITY':
                    brush_density.append(brush)
                elif brush.curves_sculpt_brush_type == 'GROW_SHRINK':
                    brush_grow.append(brush)
                elif brush.curves_sculpt_brush_type == 'ADD':
                    brush_add.append(brush)
                elif brush.curves_sculpt_brush_type == 'DELETE':
                    brush_delete.append(brush)
                elif brush.curves_sculpt_brush_type == 'PUFF':
                    brush_puff.append(brush)
                elif brush.curves_sculpt_brush_type == 'COMB':
                    brush_comb.append(brush)
            elif bpy.app.version_string < "5.0.0":
                if brush.curves_sculpt_tool  == 'DENSITY':
                    brush_density.append(brush)
                elif brush.curves_sculpt_tool == 'GROW_SHRINK':
                    brush_grow.append(brush)
                elif brush.curves_sculpt_tool == 'ADD':
                    brush_add.append(brush)
                elif brush.curves_sculpt_tool == 'DELETE':
                    brush_delete.append(brush)
                elif brush.curves_sculpt_tool == 'PUFF':
                    brush_puff.append(brush)
                elif brush.curves_sculpt_tool == 'COMB':
                    brush_comb.append(brush)
        if not brush_density:
            new_brush_density = bpy.data.brushes.new('Density Curvesss',mode="SCULPT_CURVES")
            if bpy.app.version_string >= "5.0.0":
                new_brush_density.curves_sculpt_brush_type = 'DENSITY'
            elif bpy.app.version_string < "5.0.0":
                new_brush_density.curves_sculpt_tool = 'DENSITY'
            new_brush_density.size = 150
            brush_density.append(new_brush_density)
        if not brush_grow:
            new_brush_grow = bpy.data.brushes.new('Grow /Shrink Curves',mode="SCULPT_CURVES")
            if bpy.app.version_string >= "5.0.0":
                new_brush_grow.curves_sculpt_brush_type = 'GROW_SHRINK'
            elif bpy.app.version_string < "5.0.0":
                new_brush_grow.curves_sculpt_tool = 'GROW_SHRINK'
            new_brush_grow.size = 150
            brush_grow.append(new_brush_grow)
        if not brush_add:
            new_brush_add = bpy.data.brushes.new('Add Curves',mode="SCULPT_CURVES")
            if bpy.app.version_string >= "5.0.0":
                new_brush_add.curves_sculpt_brush_type = 'ADD'
            elif bpy.app.version_string < "5.0.0":
                new_brush_add.curves_sculpt_tool = 'ADD'
            new_brush_add.size = 150
            brush_add.append(new_brush_add)
        if not brush_delete:
            new_brush_delete = bpy.data.brushes.new('Delete Curves',mode="SCULPT_CURVES")
            if bpy.app.version_string >= "5.0.0":
                new_brush_delete.curves_sculpt_brush_type = 'DELETE'
            elif bpy.app.version_string < "5.0.0":
                new_brush_delete.curves_sculpt_tool = 'DELETE'
            new_brush_delete.size = 150
            brush_delete.append(new_brush_delete)
        if not brush_puff:
            new_brush_puff = bpy.data.brushes.new('Puff Curves',mode="SCULPT_CURVES")
            if bpy.app.version_string >= "5.0.0":
                new_brush_puff.curves_sculpt_brush_type = 'PUFF'
            elif bpy.app.version_string < "5.0.0":
                new_brush_puff.curves_sculpt_tool = 'PUFF'
            new_brush_puff.size = 150
            brush_puff.append(new_brush_puff)
        if not brush_comb:
            new_brush_comb = bpy.data.brushes.new('Comb Curves',mode="SCULPT_CURVES")
            if bpy.app.version_string >= "5.0.0":
                new_brush_comb.curves_sculpt_brush_type = 'COMB'
            elif bpy.app.version_string < "5.0.0":
                new_brush_comb.curves_sculpt_tool = 'COMB'
            new_brush_comb.size = 150
            brush_comb.append(new_brush_comb)
        for bb in brush_delete:
            bb.falloff_shape = 'PROJECTED'
        for bb in brush_density:
            paint_modifier = _secret_paint_1731_paint_modifier(activeobj)
            if paint_modifier:
                minimum_distance = float(
                    _secret_paint_1731_modifier_value(
                        paint_modifier, "Socket_11", _SECRET_PAINT_DENSITY_FALLBACK
                    ) or _SECRET_PAINT_DENSITY_FALLBACK
                )
            else:
                minimum_distance = _SECRET_PAINT_DENSITY_FALLBACK
            if _secret_paint_accumulate_manual_paint(context):
                minimum_distance *= _SECRET_PAINT_ACCUMULATE_DISTANCE_SCALE
            bb.curves_sculpt_settings.minimum_distance = minimum_distance
            if bpy.app.version_string >= "4.2.0":
                bb.curves_sculpt_settings.use_length_interpolate = False
                bb.curves_sculpt_settings.use_shape_interpolate = False
                bb.curves_sculpt_settings.use_point_count_interpolate = False
            elif bpy.app.version_string < "4.2.0":
                bb.curves_sculpt_settings.interpolate_length = False
                bb.curves_sculpt_settings.interpolate_shape = False
                bb.curves_sculpt_settings.interpolate_point_count = False
            bb.curves_sculpt_settings.curve_length = 0.32
            bb.curves_sculpt_settings.points_per_curve = 2
        if bpy.context.preferences.addons[__package__].preferences.checkboxOverrideBrushes:
            for bb in brush_density:
                bb.curves_sculpt_settings.density_mode = 'AUTO'
                bb.strength = 1
                bb.falloff_shape = 'SPHERE'
                if bpy.app.version_string >= "5.0.0": bb.curve_distance_falloff_preset = 'SMOOTHER'
                elif bpy.app.version_string < "5.0.0": bb.curve_preset = 'SMOOTHER'
                bb.curves_sculpt_settings.density_add_attempts = 2000
            for bb in brush_grow:
                bb.strength = 0.03
                if bpy.app.version_string >= "4.2.0":
                    bb.curves_sculpt_settings.use_uniform_scale = True
                elif bpy.app.version_string < "4.2.0":
                    bb.curves_sculpt_settings.scale_uniform = True
            for bb in brush_add:
                bb.curves_sculpt_settings.add_amount = 1
                bb.falloff_shape = 'SPHERE'
                bb.use_frontface = True
                if bpy.app.version_string >= "4.2.0":
                    bb.curves_sculpt_settings.use_length_interpolate = False
                    bb.curves_sculpt_settings.use_shape_interpolate = False
                    bb.curves_sculpt_settings.use_point_count_interpolate = False
                elif bpy.app.version_string < "4.2.0":
                    bb.curves_sculpt_settings.interpolate_length = False
                    bb.curves_sculpt_settings.interpolate_shape = False
                    bb.curves_sculpt_settings.interpolate_point_count = False
                bb.curves_sculpt_settings.curve_length = 0.32
                bb.curves_sculpt_settings.points_per_curve = 2
            for bb in brush_delete:
                bb.falloff_shape = 'PROJECTED'
            for bb in brush_puff:
                bb.strength = 10
                bb.falloff_shape = 'PROJECTED'
            for bb in brush_comb:
                bb.strength = 0.1
                bb.falloff_shape = 'PROJECTED'
        _secret_paint_trace_end(
            "scan and configure Curves sculpt brushes",
            brush_setup_started,
            density=len(brush_density), add=len(brush_add),
            delete=len(brush_delete), grow=len(brush_grow),
            puff=len(brush_puff), comb=len(brush_comb),
        )
    elif activeobj.type=="CURVE":
        curve_mode_started = time.perf_counter()
        bpy.ops.object.mode_set(mode="EDIT")
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                override = bpy.context.copy()
                override["space_data"] = area.spaces[0]
                override["area"] = area
                bpy.ops.wm.tool_set_by_id(name="builtin.draw")
                if bpy.context.preferences.addons[__package__].preferences.checkboxOverrideBrushes:
                    bpy.context.scene.tool_settings.curve_paint_settings.depth_mode = 'SURFACE'
                    bpy.context.scene.tool_settings.curve_paint_settings.use_offset_absolute = True
                    bpy.context.scene.tool_settings.curve_paint_settings.use_stroke_endpoints = True
                    bpy.context.scene.tool_settings.curve_paint_settings.error_threshold = 8
                    bpy.context.scene.tool_settings.curve_paint_settings.fit_method = 'REFIT'
                    bpy.context.scene.tool_settings.curve_paint_settings.use_corners_detect = False
                    bpy.context.scene.tool_settings.curve_paint_settings.radius_taper_start = 1
                    bpy.context.scene.tool_settings.curve_paint_settings.radius_taper_end = 1
                    bpy.context.scene.tool_settings.curve_paint_settings.radius_min = 0
                    bpy.context.scene.tool_settings.curve_paint_settings.radius_max = 4
                    bpy.context.scene.tool_settings.curve_paint_settings.use_pressure_radius = False
                    bpy.context.scene.tool_settings.curve_paint_settings.surface_offset = 0.02
                    bpy.context.scene.tool_settings.curve_paint_settings.surface_plane = 'VIEW'
                    bpy.context.scene.tool_settings.curve_paint_settings.curve_type = 'BEZIER'
        _secret_paint_trace_end("configure legacy Curve edit context", curve_mode_started)
    if activeobj.type == "CURVES":
        track_started = time.perf_counter()
        _secret_paint_1731_track_sculpt_brush(
            context,
            activeobj,
            apply_on_change=False,
        )
        _secret_paint_trace_end("track active Curves sculpt brush", track_started)
    _secret_paint_trace_end("context3sculptbrush", context_started)
    return{'FINISHED'}
def curve_draw_tool(context,**kwargs):
    if "dont_set_drawing_tool" in kwargs:dont_set_drawing_tool = kwargs.get("dont_set_drawing_tool")
    else:dont_set_drawing_tool = False
    bpy.ops.object.mode_set(mode="EDIT")
    if dont_set_drawing_tool: bpy.ops.wm.tool_set_by_id(name="builtin.select_box")
    else: bpy.ops.wm.tool_set_by_id(name="builtin.draw")
def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found
def getChildren(parentobj):
    children = []
    for ob in bpy.data.objects:
        if ob.parent == parentobj:
            children.append(ob)
    return children
def secretpaint_viewport_mask_function(*args,**kwargs):
    importpainting_multiple_assets = kwargs.get("importpainting_multiple_assets") if "importpainting_multiple_assets" in kwargs else False
    if "activeobj" in kwargs: activeobj = kwargs.get("activeobj")
    else: activeobj = bpy.context.active_object
    if activeobj==None: activeobj = bpy.context.active_object
    if "objselection" in kwargs: objselection = kwargs.get("objselection")
    else: objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    if "force_new_maskObj" in kwargs: force_new_maskObj = kwargs.get("force_new_maskObj")
    else: force_new_maskObj = False
    if "called_for_entire_biome" in kwargs: called_for_entire_biome = kwargs.get("called_for_entire_biome")
    else: called_for_entire_biome = False
    if called_for_entire_biome == False:
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]
    N_Of_Selected = len(objselection)
    selobjs_without_active = []
    objs_with_orencurve = []
    selobjs_without_active_with_orencurve = []
    temp_variable_for_mask_detection1 = []
    temp_variable_for_mask_detection2 = []
    mask_found = []
    all_found_parents = []
    for oobjj in objselection:
        if oobjj != activeobj:
            selobjs_without_active.append(oobjj)
        if oobjj.name.startswith("Secret Paint Viewport Mask"): mask_found = oobjj
        if oobjj.modifiers:
            for modifier in oobjj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint":
                    if oobjj not in objs_with_orencurve: objs_with_orencurve.append(oobjj)
                    if oobjj != activeobj and oobjj not in selobjs_without_active_with_orencurve: selobjs_without_active_with_orencurve.append(
                        oobjj)
                    if oobjj.parent and oobjj.parent not in all_found_parents: all_found_parents.append(
                        oobjj.parent)
                    temp_variable_for_mask_detection1.append(
                        _secret_paint_1731_modifier_value(modifier, "Input_98", False)
                    )
                    temp_variable_for_mask_detection2.append(
                        _secret_paint_1731_modifier_value(modifier, "Input_97")
                    )
    all_hair_share_same_mask_settings = False
    if all_variables_are_equal(temp_variable_for_mask_detection1) and all_variables_are_equal(
        temp_variable_for_mask_detection2): all_hair_share_same_mask_settings = True
    biome_detected = False
    if len(all_found_parents) == 1: biome_detected = True
    all_sel_are_orencurves = False
    if N_Of_Selected == len(objs_with_orencurve): all_sel_are_orencurves = True
    if mask_found:
        for scattered_hair in objs_with_orencurve:
            scattered_modifier = _secret_paint_1731_paint_modifier(scattered_hair)
            _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_98", True)
            _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_97", mask_found)
            scattered_hair.hide_viewport = True
            scattered_hair.hide_viewport = False
            scattered_hair.location = scattered_hair.location
    else:
        active_modifier = _secret_paint_1731_paint_modifier(activeobj)
        checkboxstatus = _secret_paint_1731_modifier_value(active_modifier, "Input_98", False)
        maskstatus = _secret_paint_1731_modifier_value(active_modifier, "Input_97")
        if all_hair_share_same_mask_settings:
            maskobj = None
            if maskstatus == None:
                Coll_of_Active = []
                original_collection = bpy.context.view_layer.active_layer_collection
                ucol = activeobj.users_collection
                for i in ucol:
                    layer_collection = bpy.context.view_layer.layer_collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                for ob in bpy.context.scene.objects:
                    if ob.name.startswith("Secret Paint Viewport Mask"):
                        maskobj = ob
                        break
                if not maskobj or force_new_maskObj:
                    if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                    mesh = bpy.data.meshes.new("Secret Paint Viewport Mask")
                    maskobj = bpy.data.objects.new("Secret Paint Viewport Mask", mesh)
                    masksize=5
                    half_x = masksize / 2
                    verts = [(-half_x, -half_x, -half_x), (half_x, -half_x, -half_x), (half_x, half_x, -half_x), (-half_x, half_x, -half_x), (-half_x, -half_x, half_x), (half_x, -half_x, half_x), (half_x, half_x, half_x), (-half_x, half_x, half_x)]
                    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 3, 7, 4), (1, 2, 6, 5)]
                    mesh.from_pydata(verts, [], faces)
                    maskobj.location = activeobj.location
                    if Coll_of_Active.name == "Scene Collection": bpy.context.scene.collection.objects.link(maskobj)
                    else: bpy.data.collections[Coll_of_Active.name].objects.link(maskobj)
                    if importpainting_multiple_assets ==False:
                        for obbb in bpy.context.selected_objects: obbb.select_set(False)
                        maskobj.select_set(True)
                        bpy.context.view_layer.objects.active = maskobj
                    maskobj.visible_camera = False
                    maskobj.visible_diffuse = False
                    maskobj.visible_glossy = False
                    maskobj.visible_transmission = False
                    maskobj.visible_volume_scatter = False
                    maskobj.visible_shadow = False
                    maskobj.display_type = 'WIRE'
                    maskobj.show_name = True
            for scattered_hair in objs_with_orencurve:
                scattered_modifier = _secret_paint_1731_paint_modifier(scattered_hair)
                if checkboxstatus:
                    _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_98", False)
                    _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_97", None)
                elif checkboxstatus == False:
                    _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_98", True)
                    if maskstatus:
                        _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_97", maskstatus)
                    elif maskstatus == None:
                        _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_97", maskobj)
                scattered_hair.hide_viewport = True
                scattered_hair.hide_viewport = False
                scattered_hair.location = scattered_hair.location
        else:
            for scattered_hair in objs_with_orencurve:
                scattered_modifier = _secret_paint_1731_paint_modifier(scattered_hair)
                _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_98", checkboxstatus)
                _secret_paint_1731_set_modifier_value(scattered_modifier, "Input_97", maskstatus)
                scattered_hair.hide_viewport = True
                scattered_hair.hide_viewport = False
                scattered_hair.location = scattered_hair.location
    all_used_masks_in_blendfile=[]
    all_masks_in_blendfile=[]
    for obj in bpy.data.objects:
        if obj.name.startswith("Secret Paint Viewport Mask"): all_masks_in_blendfile.append(obj)
        if obj.modifiers:
            for modifier in obj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint":
                    mask_object = _secret_paint_1731_modifier_value(modifier, "Input_97")
                    if mask_object and mask_object not in all_used_masks_in_blendfile:
                        all_used_masks_in_blendfile.append(mask_object)
    for mask in all_masks_in_blendfile:
        if mask not in all_used_masks_in_blendfile:
            flag_make_row_object_active_after_deleting_mask = True if mask == bpy.context.active_object else False
            bpy.data.objects.remove(mask, do_unlink=True)
            if flag_make_row_object_active_after_deleting_mask: bpy.context.view_layer.objects.active = activeobj
    return {'FINISHED'}
class secretpaint_viewport_mask(bpy.types.Operator):
    """Mask vast landscapes for viewport performance; Shift+Click to create a new mask; Alt+Click to select the mask object"""
    bl_idname = "secret.secretpaint_viewport_mask"
    bl_label = "Temporary Viewport Mask"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.secretpaint_viewport_mask")
        obbb= bpy.data.objects.get(self.object_name)
        if event.alt:
            for x in bpy.context.selected_objects: x.select_set(False)
            mask_object = _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(obbb), "Input_97"
            )
            if mask_object:
                bpy.context.view_layer.objects.active = mask_object
                mask_object.select_set(True)
            else:
                for ob in bpy.context.scene.objects:
                    if ob.name.startswith("Secret Paint Viewport Mask"):
                        bpy.context.view_layer.objects.active = ob
                        ob.select_set(True)
                        break
        elif event.shift: secretpaint_viewport_mask_function(self, context,activeobj=obbb,force_new_maskObj=True)
        else: secretpaint_viewport_mask_function(self, context,activeobj=obbb)
        self.object_name = ("")
        return {'FINISHED'}
def selcollectionofactive(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = selcollectionofactive(layer, collName)
        if found:
            return found
class collectionofactiveobj(bpy.types.Operator):
    bl_idname = "secret.collectionofactiveobj"
    bl_label = "Select parent collection of active object"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(self, context):
        ar = context.screen.areas
        __class__.area = next(
            (a for a in ar if a.type == 'OUTLINER'), None)
        return __class__.area
    def execute(self, context):
        obj = bpy.context.object
        ucol = obj.users_collection
        for i in ucol:
            layer_collection = bpy.context.view_layer.layer_collection
            layerColl = selcollectionofactive(layer_collection, i.name)
            bpy.context.view_layer.active_layer_collection = layerColl
        return {'FINISHED'}
def getChildren(myObject):
    children = []
    for ob in bpy.data.objects:
        if ob.parent == myObject:
            children.append(ob)
    return children
def select_biome_all_function(context):
    activeobj = bpy.context.active_object
    brushobj = []
    brushcoll = []
    if activeobj.type == "CURVES":
        if activeobj.modifiers:
            for modif in activeobj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    brushobj = _secret_paint_1731_modifier_value(modif, "Input_2", None)
                    brushcoll = _secret_paint_1731_modifier_value(modif, "Input_9", None)
    for obj in bpy.context.scene.objects:
        if obj.type == "CURVES":
            if obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and _secret_paint_1731_modifier_value(modif, "Input_2", None) == brushobj and _secret_paint_1731_modifier_value(modif, "Input_9", None) == brushcoll:
                        bpy.data.objects[obj.name].select_set(True)
    return {'FINISHED'}
class select_biome_all(bpy.types.Operator):
    """Select all Biomes that share the same Brush object"""
    bl_idname = "secret.select_biome_all"
    bl_label = "Select Similar Biomes"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        select_biome_all_function(context)
        return {'FINISHED'}
def dupliObjCheckCoordinates(self, context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    allCoordinates = []
    for obj in bpy.context.scene.objects:
        allCoordinates.append(str(obj.location))
    dupliobj = activeobj.copy()
    bpy.context.scene.collection.objects.link(dupliobj)
    while str(dupliobj.location) in allCoordinates:
        dupliobj.location[2] = dupliobj.location[2] + (((dupliobj.dimensions[2]) / 2) * 2.15)
    return dupliobj
def secretpaint_cleanup_empty_systems(self,context):
    for obj in bpy.context.scene.objects:
        if obj.type == "CURVES" and obj.modifiers and obj != bpy.context.active_object and obj not in bpy.context.selected_objects:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and (sum(len(spline.points) for spline in obj.data.curves)) == 0 and _secret_paint_1731_modifier_value(modif, "Input_99", False) == False and _secret_paint_1731_modifier_value(modif, "Input_69", False) == False:
                    bpy.data.objects.remove(obj, do_unlink=True)
def secretpaint_create_curve(self,context,**kwargs):
    if "targetOBJ" in kwargs:targetOBJ = kwargs.get("targetOBJ")
    else:targetOBJ = bpy.context.active_object
    if targetOBJ.type=="CURVES": targetOBJsurface= targetOBJ.parent
    else: targetOBJsurface=targetOBJ
    if "brushOBJ" in kwargs:
        brushOBJ= kwargs.get("brushOBJ")
        if not isinstance(brushOBJ, (list, tuple)): brushOBJ=[brushOBJ]
    else: brushOBJ=None
    hair_to_copyModifs_from = targetOBJ if targetOBJ.type == "CURVES" else brushOBJ[0]
    targetCollection = kwargs.get("targetCollection") if "targetCollection" in kwargs else bpy.context.collection
    transfer_modifier = kwargs.get("transfer_modifier") if "transfer_modifier" in kwargs else False
    hairCurves = bpy.data.objects.new("Secret Paint", bpy.data.hair_curves.new("Secret Paint"))
    if targetCollection.name =="Scene Collection": bpy.context.scene.collection.objects.link(hairCurves)
    else: bpy.data.collections[targetCollection.name].objects.link(hairCurves)
    if transfer_modifier:
        secretpaint_update_modifier_f(context,upadte_provenance="def secretpaint_create_curve(self,context,**kwargs)")
    else: contextorencurveappend(context,activeobj=hairCurves)
    hairCurves.data.surface = targetOBJsurface
    active_render_UV = None
    custom_uv = None
    for uvmap in targetOBJsurface.data.uv_layers:
        if uvmap.name == "Secret Paint UV":custom_uv = uvmap.name
        if uvmap.active_render: active_render_UV = uvmap.name
    if custom_uv: hairCurves.data.surface_uv_map = custom_uv
    elif active_render_UV: hairCurves.data.surface_uv_map = active_render_UV
    hairCurves.rotation_euler = targetOBJsurface.matrix_world.to_euler('XYZ')
    hairCurves.scale = targetOBJsurface.scale
    hairCurves.location = targetOBJsurface.matrix_world.to_translation()
    hairCurves.parent = targetOBJsurface
    hairCurves.matrix_parent_inverse = targetOBJsurface.matrix_world.inverted()
    hairCurves.display_type = hair_to_copyModifs_from.display_type
    if brushOBJ:
        for brushh in brushOBJ:
            for material_slot in brushh.material_slots:
                if material_slot.material and material_slot.material.name not in hairCurves.data.materials:
                    hairCurves.data.materials.append(material_slot.material)
    if transfer_modifier:
        for mod in hair_to_copyModifs_from.modifiers:
            mod_copy = hairCurves.modifiers.new(mod.name, mod.type)
            for attr in sorted(dir(mod)):
                if (attr.startswith("_") or attr in ["bl_rna"]): continue
                try:
                    if (mod.is_property_readonly(attr)): continue
                except:
                    continue
                setattr(mod_copy, attr, getattr(mod, attr))
            try:
                modifier_items = list(mod.items())
            except Exception:
                modifier_items = []
            for key, value in modifier_items:
                try:
                    mod_copy[key] = value
                except: pass
            _secret_paint_1731_copy_modifier_inputs(mod, mod_copy)
    hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
    if hair_modifier is None:
        raise RuntimeError("Secret Paint Geometry Nodes modifier was not created")
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", True)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_71", float(random.choice(range(0, 10))))
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_73", targetOBJsurface)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_100", abs(max(targetOBJsurface.scale)))
    if targetOBJsurface.modifiers:
        for mod in targetOBJsurface.modifiers:
            if mod.type in ["ARMATURE","CAST","CURVE","DISPLACE","HOOK","LAPLACIANDEFORM","LATTICE","MESH_DEFORM","SHRINKWRAP","SIMPLE_DEFORM","SMOOTH","CORRECTIVE_SMOOTH","LAPLACIANSMOOTH","SURFACE_DEFORM","WARP","WAVE",]:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_63", True)
                targetOBJsurface.add_rest_position_attribute = True
    smallest_obj = brushOBJ[0]
    for obje in brushOBJ:
        if obje.type == "MESH":
            thisobj_is_an_assembly = False
            if obje.modifiers:
                for modif in obje.modifiers:
                    if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                        node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                        for input in node_group_inputs_temp:
                            if input.socket_type == "NodeSocketObject" and input.name == "Parent":
                                assembly_parent = _secret_paint_1731_modifier_value(modif, input.identifier)
                                if assembly_parent and assembly_parent.type=="MESH":
                                    if max(smallest_obj.dimensions)==0\
                                    or max(assembly_parent.dimensions)>0 and assembly_parent.dimensions < smallest_obj.dimensions:
                                        smallest_obj = assembly_parent
                                        thisobj_is_an_assembly = True
                                        break
            if not thisobj_is_an_assembly:
                if max(smallest_obj.dimensions)==0\
                or smallest_obj.type == "MESH" and max(obje.dimensions) > 0 and obje.dimensions < smallest_obj.dimensions: smallest_obj = obje
    density_size = _secret_paint_density_size(
        smallest_obj,
        context.evaluated_depsgraph_get(),
        smallest_horizontal=True,
    )
    if density_size is not None:
        dimensions_of_smallest_axis = (
            _secret_paint_automatic_density_multiplier(context) / (density_size ** 2)
        )
        if dimensions_of_smallest_axis < 10000:
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_68", dimensions_of_smallest_axis)
            input_100 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_100", 1.0) or 1.0)
            _secret_paint_1731_set_modifier_value(
                hair_modifier,
                "Socket_11",
                (0.5 / ((dimensions_of_smallest_axis ** 0.5) * input_100)) * 2,
            )
        else:
            _secret_paint_1731_set_modifier_value(
                hair_modifier, "Socket_11", _SECRET_PAINT_DENSITY_FALLBACK
            )
    else:
        _secret_paint_1731_set_modifier_value(
            hair_modifier, "Socket_11", _SECRET_PAINT_DENSITY_FALLBACK
        )
    return hairCurves
def secretpaint_function(self,*args,**kwargs):
    pass
    context=None
    event=None
    for i in args:
        if type(i).__name__ == "Context": context = i
        elif type(i).__name__ == "Event": event = i
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    objselection = kwargs.get("objselection") if "objselection" in kwargs else bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    auto_Mask_Optimization = kwargs.get("auto_Mask_Optimization") if "auto_Mask_Optimization" in kwargs else True
    importpainting_multiple_assets = kwargs.get("importpainting_multiple_assets") if "importpainting_multiple_assets" in kwargs else False
    if activeobj == None: return {'FINISHED'}
    activeobj_BoundingBox_State = activeobj.display_type
    N_Of_Selected = len(objselection)
    ActiveMode = bpy.context.object.mode
    all_meshes =[]
    all_meshes_that_are_not_parents =[]
    selobjs_without_active =[]
    objs_with_orencurve =[]
    selobjs_without_active_with_orencurve = []
    all_found_parents_without_activeobj=[]
    all_found_parents=[]
    all_hair_with_Vgroup =[]
    all_Vgroups =[]
    for oobjj in objselection:
        if oobjj.type=="MESH": all_meshes.append(oobjj)
        if oobjj != activeobj:
            selobjs_without_active.append(oobjj)
        if oobjj.modifiers:
            for modifier in oobjj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" \
                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modifier.node_group.name) and ".001" <= modifier.node_group.name[-4:] <= ".999" :
                    if oobjj not in objs_with_orencurve: objs_with_orencurve.append(oobjj)
                    if oobjj != activeobj and oobjj not in selobjs_without_active_with_orencurve: selobjs_without_active_with_orencurve.append(oobjj)
                    if oobjj.type == "CURVES" and oobjj.parent and oobjj.parent not in all_found_parents: all_found_parents.append(oobjj.parent)
                    if oobjj != activeobj and oobjj.type == "CURVES" and oobjj.parent and oobjj.parent not in all_found_parents_without_activeobj: all_found_parents_without_activeobj.append(oobjj.parent)
                    attribute_name = _secret_paint_1731_modifier_value(modifier, "Input_83_attribute_name", "")
                    if attribute_name:
                        all_hair_with_Vgroup.append(oobjj)
                        if attribute_name not in all_Vgroups: all_Vgroups.append(attribute_name)
    for mesh in all_meshes:
        if mesh not in all_found_parents: all_meshes_that_are_not_parents.append(mesh)
    biome_detected = False
    if len(all_found_parents)==1: biome_detected=True
    all_sel_are_orencurves = False
    if N_Of_Selected == len(objs_with_orencurve): all_sel_are_orencurves = True
    selobj=[]
    selobj_BoundingBox_State=[]
    if N_Of_Selected >=2:
        for obj in objselection:
            if obj != activeobj:
                selobj = obj
                break
                selobj_BoundingBox_State = selobj.display_type
    Coll_of_Active=[]
    original_collection = bpy.context.view_layer.active_layer_collection
    for i in activeobj.users_collection:
        layer_collection = bpy.context.view_layer.layer_collection
        Coll_of_Active = recurLayerCollection(layer_collection, i.name)
    collection_of_one_of_selected=[]
    if N_Of_Selected >=3:
        for i in selobj.users_collection:
            layer_collection = bpy.context.view_layer.layer_collection
            collection_of_one_of_selected = recurLayerCollection(layer_collection, i.name)
    if ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "MESH" and selobj.type in ["MESH","EMPTY","CURVE"]:
        pass
        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)
        hairCurves = secretpaint_create_curve(self,context,targetOBJ=activeobj,targetCollection=Coll_of_Active, brushOBJ=selobj, transfer_modifier=False)
        hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", bpy.data.objects[selobj.name])
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_16", 5)
        _secret_paint_1731_set_modifier_component(hair_modifier, "Input_6", 2, 20)
        percentage_value = 0.75
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_15", 0.25)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_15", 0.25)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_82", 1.04)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_62", 0.5)
        input_68 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_68", 0) or 0)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_60", 0.15 * (input_68 ** 0.5))
        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except:pass
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.data.polygons)
            input_100 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_100", 0) or 0)
            if input_68 > 0 and input_100 > 0 and (allTerrainArea / ((1 / ((input_68 ** 0.5) * input_100)) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_98", False)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_97", None)
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
        else:
            bpy.context.view_layer.objects.active = hairCurves
            context3sculptbrush(context)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", False)
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "MESH" and len(selobjs_without_active_with_orencurve)==0:
        pass
        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=False)
        hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", None)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_9", bpy.data.collections[collection_of_one_of_selected.name])
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_16", 5)
        _secret_paint_1731_set_modifier_component(hair_modifier, "Input_6", 2, 20)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_15", 0.25)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_62", 0.5)
        input_68 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_68", 0) or 0)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_60", 0.15 * (input_68 ** 0.5))
        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except:pass
        for x in objselection: x.select_set(False)
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.data.polygons)
            input_100 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_100", 0) or 0)
            if input_68 > 0 and input_100 > 0 and (allTerrainArea / ((1 / ((input_68 ** 0.5) * input_100)) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_98", False)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_97", None)
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
        else:
            bpy.context.view_layer.objects.active = hairCurves
            context3sculptbrush(context, activeobj=hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", False)
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "CURVES" and selobj.type in ["MESH","EMPTY","CURVE"]:
        pass
        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=True)
        hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", None)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_9", bpy.data.collections[collection_of_one_of_selected.name])
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", False)
        _secret_paint_1731_set_modifier_component(hair_modifier, "Input_6", 2, 20.0)
        input_68 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_68", 0) or 0)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_60", 0.15 * (input_68 ** 0.5))
        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except:pass
        for x in objselection: x.select_set(False)
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)
            input_100 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_100", 0) or 0)
            if input_68 > 0 and input_100 > 0 and (allTerrainArea / ((1 / ((input_68 ** 0.5) * input_100)) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_98", False)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_97", None)
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
        else:
            bpy.context.view_layer.objects.active = hairCurves
            context3sculptbrush(context, activeobj=hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", False)
    elif N_Of_Selected >=2 and len(all_found_parents) == 1 and all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES":
        if activeobj.parent.data.library:
            self.report({'WARNING'}, "Can't Weight Paint on an object with Linked Mesh Data: paint with hair or make the data local")
        else:
            vertexgrouppaint_function(self, context,NoMasksDetected=True)
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 2 and len(selobjs_without_active_with_orencurve)>=1:
        pass
        newlycreated_hair=[]
        if activeobj.type == "CURVES": all_meshes_to_scatter_onto = [activeobj.parent]
        elif len(all_meshes)==1:all_meshes_to_scatter_onto = [activeobj]
        else: all_meshes_to_scatter_onto = all_meshes_that_are_not_parents
        pass
        for mesh in all_meshes_to_scatter_onto:
            newlycreated_hair_for_currentlyprocessing_mesh = []
            Coll_of_TaragetMesh = []
            for i in mesh.users_collection:
                Coll_of_TaragetMesh = recurLayerCollection(bpy.context.view_layer.layer_collection, i.name)
            Check_if_trigger_UV_Reprojection(self, context, activeobj=mesh, objselection=[mesh])
            highest_distribution_density=0
            hair_thatNeedA_mask=[]
            if mesh.type == "MESH": allTerrainArea = sum(face.area for face in mesh.data.polygons)
            elif mesh.type == "CURVES": allTerrainArea = sum(face.area for face in mesh.parent.data.polygons)
            all_bgroups_starter = []
            for hayr in selobjs_without_active_with_orencurve:
                biome_number = _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hayr), "Socket_0", 0
                )
                if biome_number not in all_bgroups_starter: all_bgroups_starter.append(biome_number)
            for parentt in all_found_parents:
                hair = find_all_listed_paintsystems(context, activeobj=mesh, objselection=[mesh])
                all_bgroups = []
                for hayr in hair[:]:
                    biome_number = _secret_paint_1731_modifier_value(
                        _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
                    )
                    if biome_number not in all_bgroups: all_bgroups.append(biome_number)
                all_bgroups.sort()
                loop = 1
                for biome_number in all_bgroups[:]:
                    for hayr in hair[:]:
                        modifier = _secret_paint_1731_paint_modifier(hayr[0])
                        if _secret_paint_1731_modifier_value(modifier, "Socket_0", 0) == biome_number:
                            _secret_paint_1731_set_modifier_value(modifier, "Socket_0", loop)
                            hair.remove(hayr)
                    loop += 1
                if all_bgroups: additional_biome_n = max(all_bgroups)
                else: additional_biome_n = 0
                for hair in parentt.children:
                    if hair in selobjs_without_active_with_orencurve:
                        for modifier in hair.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                                hairCurves = secretpaint_create_curve(self,context, targetOBJ=mesh, brushOBJ=hair, targetCollection=Coll_of_TaragetMesh, transfer_modifier=True)
                                source_modifier = _secret_paint_1731_paint_modifier(hair)
                                new_hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
                                newlycreated_hair.append(hairCurves)
                                newlycreated_hair_for_currentlyprocessing_mesh.append(hairCurves)
                                if bpy.context.preferences.addons[__package__].preferences.checkboxKeepManualWhenTransferBiome == False:
                                    if N_Of_Selected >= 3 or _secret_paint_1731_modifier_value(source_modifier, "Input_69", False):
                                        _secret_paint_1731_set_modifier_value(new_hair_modifier, "Input_69", True)
                                input_68 = _secret_paint_1731_modifier_value(source_modifier, "Input_68", 0)
                                _secret_paint_1731_set_modifier_value(new_hair_modifier, "Input_68", input_68)
                                _secret_paint_1731_set_modifier_value(
                                    new_hair_modifier, "Socket_11",
                                    _secret_paint_1731_modifier_value(source_modifier, "Socket_11", 0),
                                )
                                _secret_paint_1731_set_modifier_value(
                                    new_hair_modifier, "Input_60", 0.15 * (float(input_68 or 0) ** 0.5)
                                )
                                _secret_paint_1731_set_modifier_value(
                                    new_hair_modifier, "Socket_0",
                                    _secret_paint_1731_modifier_value(source_modifier, "Socket_0", 0) + additional_biome_n,
                                )
                                if len(all_bgroups_starter) >= 2:
                                    _secret_paint_1731_set_modifier_value(
                                        new_hair_modifier, "Socket_2",
                                        _secret_paint_1731_modifier_value(source_modifier, "Socket_2", False),
                                    )
                                if mesh.data.library:
                                    _secret_paint_1731_set_modifier_value(new_hair_modifier, "Input_83_attribute_name", "")
                                    _secret_paint_1731_set_modifier_value(new_hair_modifier, "Input_83_use_attribute", False)
                                else:
                                    _secret_paint_1731_set_modifier_value(
                                        new_hair_modifier, "Input_83_attribute_name",
                                        _secret_paint_1731_modifier_value(source_modifier, "Input_83_attribute_name", ""),
                                    )
                                    new_attribute_status_convert_int_to_boolean = bool(
                                        _secret_paint_1731_modifier_value(source_modifier, "Input_83_use_attribute", False)
                                    )
                                    _secret_paint_1731_set_modifier_value(
                                        new_hair_modifier, "Input_83_use_attribute", new_attribute_status_convert_int_to_boolean
                                    )
                                new_input_68 = float(_secret_paint_1731_modifier_value(new_hair_modifier, "Input_68", 0) or 0)
                                new_input_100 = float(_secret_paint_1731_modifier_value(new_hair_modifier, "Input_100", 0) or 0)
                                mask_needed = (
                                    new_input_68 > 0 and new_input_100 > 0 and
                                    (allTerrainArea / ((1 / ((new_input_68 ** 0.5) * new_input_100)) ** 2))
                                    > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask
                                )
                                if _secret_paint_1731_modifier_value(new_hair_modifier, "Input_98", False) \
                                or _secret_paint_1731_modifier_value(new_hair_modifier, "Input_97", None) \
                                or mask_needed and _secret_paint_1731_modifier_value(new_hair_modifier, "Input_69", False):
                                    if hairCurves not in hair_thatNeedA_mask: hair_thatNeedA_mask.append(hairCurves)
                                    _secret_paint_1731_set_modifier_value(new_hair_modifier, "Input_98", False)
                                    _secret_paint_1731_set_modifier_value(new_hair_modifier, "Input_97", None)
                                if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value
                                elif bpy.app.version_string < "4.0.0":
                                    try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
                                    except:pass
                                hairCurves.select_set(True)
                                bpy.context.view_layer.objects.active = hairCurves
            NoMasksDetected = True
            if len(all_hair_with_Vgroup) == len(selobjs_without_active) and len(all_Vgroups) == 1: NoMasksDetected=True
            elif hair_thatNeedA_mask: NoMasksDetected = False
            else: NoMasksDetected=True
            paint_the_vertex=False
            vertexgrouppaint_function(self, context,NoMasksDetected,calledfrombutton=False, being_transferred_to_newmesh=True, objselection=newlycreated_hair_for_currentlyprocessing_mesh, activeobj=newlycreated_hair_for_currentlyprocessing_mesh[0], paint_the_vertex=paint_the_vertex)
            if NoMasksDetected==False: secretpaint_viewport_mask_function(self, context, objselection=hair_thatNeedA_mask, activeobj=hair_thatNeedA_mask[0])
        for ojgb in newlycreated_hair:
            _secret_paint_1731_set_modifier_value(
                _secret_paint_1731_paint_modifier(ojgb), "Input_99", False
            )
            ojgb.location = ojgb.location
        for x in bpy.context.selected_objects: x.select_set(False)
        if N_Of_Selected == 2 and _secret_paint_1731_modifier_value(
            _secret_paint_1731_paint_modifier(newlycreated_hair[0]), "Input_69", False
        ) == False:
            context3sculptbrush(context, activeobj=newlycreated_hair[0])
    elif ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "MESH" \
            or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "EMPTY" \
            or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "CURVE":
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobj, targetCollection=Coll_of_Active, transfer_modifier=True)
        hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", selobj)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_9", None)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", False)
        input_68 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_68", 0) or 0)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_60", 0.15 * (input_68 ** 0.5))
        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except: pass
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)
            input_100 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_100", 0) or 0)
            if input_68 > 0 and input_100 > 0 and (allTerrainArea / ((1 / ((input_68 ** 0.5) * input_100)) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_98", False)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_97", None)
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
        else:
            bpy.context.view_layer.objects.active = hairCurves
            if not _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(activeobj), "Input_69", False
            ):
                context3sculptbrush(context, activeobj=hairCurves)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", False)
        pass
    elif ActiveMode in ["SCULPT_CURVES", "WEIGHT_PAINT", "EDIT"]:
        secretpaint_update_modifier_f(context,upadte_provenance="SWICTH WHICH HAIR SYSTEM TO PAINT FROM SCULPT MODE OR EDIT MODE OR WEIGHT PAINT MODE")
        found_to_paint = []
        paint_type = []
        bpy.ops.object.mode_set(mode="OBJECT")
        result = bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))
        hoverobj = bpy.context.active_object
        if result != {'PASS_THROUGH'} and hoverobj.type in ["CURVE","CURVES"] and hoverobj.modifiers:
            for modif in hoverobj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                    if hoverobj.type == "CURVE":
                        paint_type="EDIT"
                        found_to_paint.append(hoverobj)
                    elif _secret_paint_1731_modifier_value(modif, "Input_69", False) and _secret_paint_1731_modifier_value(modif, "Input_83_attribute_name", ""):
                        paint_type="WEIGHT_PAINT"
                        found_to_paint.append(hoverobj)
                    elif not _secret_paint_1731_modifier_value(modif, "Input_69", False):
                        paint_type="SCULPT_CURVES"
                        found_to_paint.append(hoverobj)
        elif result != {'PASS_THROUGH'} and hoverobj.type == "MESH" and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
            pass
            siblings_with_same_weight_paint=[]
            all_brush_objs=[]
            all_brush_colls=[]
            if activeobj.type=="MESH" and ActiveMode == "WEIGHT_PAINT" and activeobj.children:
                for children in activeobj.children:
                    if children.type == "CURVES" and children.modifiers:
                        for modif in children.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and activeobj.vertex_groups.active.name == _secret_paint_1731_modifier_value(modif, "Input_83_attribute_name", ""):
                                siblings_with_same_weight_paint.append(children)
                                input_2 = _secret_paint_1731_modifier_value(modif, "Input_2", None)
                                input_9 = _secret_paint_1731_modifier_value(modif, "Input_9", None)
                                if input_2 and input_2 not in all_brush_objs: all_brush_objs.append(input_2)
                                if input_9 and input_9 not in all_brush_colls: all_brush_colls.append(input_9)
            elif activeobj.type=="CURVES":
                siblings_with_same_weight_paint.append(activeobj)
                active_modifier = _secret_paint_1731_paint_modifier(activeobj)
                input_2 = _secret_paint_1731_modifier_value(active_modifier, "Input_2", None)
                input_9 = _secret_paint_1731_modifier_value(active_modifier, "Input_9", None)
                if input_2 and input_2 not in all_brush_objs: all_brush_objs.append(input_2)
                if input_9 and input_9 not in all_brush_colls: all_brush_colls.append(input_9)
            all_vgroups_in_hoverobjs_children =[]
            if hoverobj.children:
                for children in hoverobj.children:
                    if children.type == "CURVES" and children.modifiers:
                        for modif in children.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                if _secret_paint_1731_modifier_value(modif, "Input_2", None) in all_brush_objs or _secret_paint_1731_modifier_value(modif, "Input_9", None) in all_brush_colls:
                                    if len(siblings_with_same_weight_paint) <= 1:
                                        sibling_modifier = _secret_paint_1731_paint_modifier(siblings_with_same_weight_paint[0])
                                        if _secret_paint_1731_modifier_value(modif, "Input_83_use_attribute", False) == _secret_paint_1731_modifier_value(sibling_modifier, "Input_83_use_attribute", False):
                                            if _secret_paint_1731_modifier_value(modif, "Input_69", False) and _secret_paint_1731_modifier_value(modif, "Input_83_use_attribute", False):
                                                paint_type = "WEIGHT_PAINT"
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                pass
                                            elif not _secret_paint_1731_modifier_value(modif, "Input_69", False):
                                                paint_type = "SCULPT_CURVES"
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                pass
                                        if _secret_paint_1731_modifier_value(modif, "Input_69", False) == _secret_paint_1731_modifier_value(sibling_modifier, "Input_69", False):
                                            if _secret_paint_1731_modifier_value(modif, "Input_69", False) and _secret_paint_1731_modifier_value(modif, "Input_83_use_attribute", False):
                                                paint_type="WEIGHT_PAINT"
                                                found_to_paint=[]
                                                found_to_paint.append(children)
                                                pass
                                            elif not _secret_paint_1731_modifier_value(modif, "Input_69", False):
                                                paint_type="SCULPT_CURVES"
                                                found_to_paint=[]
                                                found_to_paint.append(children)
                                                pass
                                        if _secret_paint_1731_modifier_value(modif, "Input_69", False) == _secret_paint_1731_modifier_value(sibling_modifier, "Input_69", False) and _secret_paint_1731_modifier_value(modif, "Input_83_use_attribute", False) == _secret_paint_1731_modifier_value(sibling_modifier, "Input_83_use_attribute", False):
                                            if _secret_paint_1731_modifier_value(modif, "Input_69", False) and _secret_paint_1731_modifier_value(modif, "Input_83_use_attribute", False):
                                                paint_type = "WEIGHT_PAINT"
                                                pass
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                            elif not _secret_paint_1731_modifier_value(modif, "Input_69", False):
                                                paint_type = "SCULPT_CURVES"
                                                pass
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                pass
                                    elif len(siblings_with_same_weight_paint) >= 2:
                                        attribute_name = _secret_paint_1731_modifier_value(modif, "Input_83_attribute_name", "")
                                        if attribute_name and attribute_name not in all_vgroups_in_hoverobjs_children: all_vgroups_in_hoverobjs_children.append(attribute_name)
                                        if all_vgroups_in_hoverobjs_children and attribute_name == all_vgroups_in_hoverobjs_children[0]:
                                            paint_type="WEIGHT_PAINT"
                                            found_to_paint.append(children)
        if found_to_paint:
            bpy.context.view_layer.objects.active = found_to_paint[0]
            if paint_type=="EDIT": curve_draw_tool(context)
            elif paint_type=="WEIGHT_PAINT": vertexgrouppaint_function(self, context, NoMasksDetected=True)
            elif paint_type=="SCULPT_CURVES":
                if ActiveMode == "SCULPT_CURVES": apply_paint(self,context,activeobj=found_to_paint[0], objselection=[found_to_paint[0]],applyIDs=True,keep_active_brush=True)
                else: apply_paint(self,context,activeobj=found_to_paint[0], objselection=[found_to_paint[0]],applyIDs=True )
                pass
        elif not found_to_paint and hoverobj and hoverobj.type=="MESH" and hoverobj!=activeobj.parent and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
            if bool(hoverobj.data.library) and ActiveMode=="WEIGHT_PAINT":
                bpy.context.view_layer.objects.active = activeobj
                bpy.ops.object.mode_set(mode=ActiveMode)
            else: secretpaint_function(self, context, event,objselection = siblings_with_same_weight_paint, activeobj=hoverobj)
        else:
            bpy.context.view_layer.objects.active = activeobj
            bpy.ops.object.mode_set(mode=ActiveMode)
        for ob in bpy.context.selected_objects: bpy.data.objects[ob.name].select_set(False)
        pass
    elif ActiveMode == "OBJECT" and N_Of_Selected == 1 and activeobj.type == "CURVE":
        curve_draw_tool(context)
        pass
    elif len(all_found_parents)==1 and all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES" \
    or ActiveMode == "OBJECT" and N_Of_Selected == 0:
        secretpaint_update_modifier_f(context,upadte_provenance="RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS")
        if N_Of_Selected == 0:
            result = bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))
            hoverobj = bpy.context.active_object
            if result != {'PASS_THROUGH'} and hoverobj.type == "CURVES" and hoverobj.modifiers:
                for modif in hoverobj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                        if _secret_paint_1731_modifier_value(modif, "Input_69", False) and _secret_paint_1731_modifier_value(modif, "Input_83_use_attribute", False): vertexgrouppaint_function(self, context, NoMasksDetected=True)
                        elif not _secret_paint_1731_modifier_value(modif, "Input_69", False):
                            apply_paint(self, context, activeobj=hoverobj, objselection=[hoverobj], applyIDs=True)
                        else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
                    else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
            else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
            bpy.data.objects[hoverobj.name].select_set(False)
            for ob in objselection:
                bpy.data.objects[ob.name].select_set(False)
        elif N_Of_Selected == 1:
            active_modifier = _secret_paint_1731_paint_modifier(activeobj)
            if _secret_paint_1731_modifier_value(active_modifier, "Input_69", False) and _secret_paint_1731_modifier_value(active_modifier, "Input_83_use_attribute", False):
                vertexgrouppaint_function(self, context,NoMasksDetected=True)
            elif _secret_paint_1731_modifier_value(active_modifier, "Input_69", False) and not _secret_paint_1731_modifier_value(active_modifier, "Input_83_use_attribute", False):
                apply_paint(self, context, activeobj=activeobj)
            elif not _secret_paint_1731_modifier_value(active_modifier, "Input_69", False):
                apply_paint(self, context, activeobj=activeobj, objselection=[activeobj], applyIDs=True)
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        pass
    elif ActiveMode == "OBJECT" and N_Of_Selected == 1:
        if "circulararray" in kwargs: circulararray = kwargs.get("circulararray")
        else:circulararray = False
        if "straightarray" in kwargs: straightarray = kwargs.get("straightarray")
        else:straightarray = False
        curve_data = bpy.data.curves.new(name="Secret Paint", type="CURVE")
        curve_data.dimensions = '3D'
        if circulararray:
            points = curve_data.splines.new(type='BEZIER')
            points.bezier_points.add(3)
            angle = 0
            radius = 2.0
            for i in range(4):
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                points.bezier_points[i].co = (x, y, 0)
                points.bezier_points[i].handle_left_type = 'AUTO'
                points.bezier_points[i].handle_right_type = 'AUTO'
                points.bezier_points[i].select_control_point = True
                angle += math.pi / 2
            curve_data.splines[0].use_cyclic_u = True
        elif straightarray:
            coords_list = [[0, 0, 0], [3, 0, 0]]
            spline = curve_data.splines.new(type='NURBS')
            spline.points.add(len(coords_list) - 1)
            for p, new_co in zip(spline.points, coords_list):
                p.co = (new_co + [1.0])
                p.select = True
        hairCurves = bpy.data.objects.new("Secret Paint", curve_data)
        bpy.context.collection.objects.link(hairCurves)
        for x in bpy.context.selected_objects: x.select_set(False)
        bpy.context.view_layer.objects.active = hairCurves
        hairCurves.select_set(True)
        contextorencurveappend(context)
        bezier_brush = kwargs.get("bezier_brush", activeobj)
        if bezier_brush is None:
            bezier_brush = activeobj
        for material_slot in bezier_brush.material_slots:
            if material_slot.material and material_slot.material.name not in hairCurves.data.materials:
                hairCurves.data.materials.append(material_slot.material)
        obj_for_dimensions = bezier_brush
        if bezier_brush.type == "MESH" and bezier_brush.modifiers:
            for modif in bezier_brush.modifiers:
                if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                        node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                        for input in node_group_inputs_temp:
                            if input.socket_type == "NodeSocketObject" and input.name == "Parent":
                                assembly_parent = _secret_paint_1731_modifier_value(modif, input.identifier)
                                if assembly_parent and assembly_parent.type == "MESH": obj_for_dimensions = assembly_parent
        hair_modifier = _secret_paint_1731_paint_modifier(hairCurves)
        density_size = _secret_paint_density_size(
            obj_for_dimensions, context.evaluated_depsgraph_get()
        )
        if density_size is not None:
            _secret_paint_1731_set_modifier_value(
                hair_modifier,
                "Input_68",
                (
                    (1 / (density_size ** 2))
                    * 2
                    * _secret_paint_automatic_density_multiplier(context)
                ),
            )
        else:
            _secret_paint_1731_set_modifier_value(
                hair_modifier, "Socket_11", _SECRET_PAINT_DENSITY_FALLBACK
            )
        dont_set_drawing_tool = False
        if circulararray or straightarray:
            dont_set_drawing_tool =True
            _secret_paint_1731_set_modifier_component(hair_modifier, "Input_65", 0, 1.5708)
            _secret_paint_1731_set_modifier_component(hair_modifier, "Input_65", 1, -1.5708)
        curve_draw_tool(context, dont_set_drawing_tool=dont_set_drawing_tool)
        context3sculptbrush(context)
        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", bezier_brush)
        hairCurves.location= bpy.context.scene.cursor.location
        pass
    elif ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVE":
        selobj.select_set(False)
        bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},TRANSFORM_OT_translate={})
        curveobj = bpy.context.active_object
        selobj.select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[selobj.name]
        bpy.ops.object.make_links_data(type='MATERIAL')
        selobj.select_set(False)
        bpy.context.view_layer.objects.active = bpy.data.objects[curveobj.name]
        bpy.ops.object.editmode_toggle()
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.curve.dissolve_verts()
        curve_draw_tool(context)
        _secret_paint_1731_set_modifier_value(
            _secret_paint_1731_paint_modifier(bpy.context.object),
            "Input_2",
            bpy.data.objects[selobj.name],
        )
        pass
_secret_paint_q_prompt = False
_secret_paint_q_prompt_text = "Choose a plant to paint with"
_secret_paint_q_selection_mode = None
def _secret_paint_q_begin_selection_mode(mode, prompt):
    global _secret_paint_q_selection_mode, _secret_paint_q_prompt_text
    _secret_paint_q_selection_mode = mode
    _secret_paint_q_prompt_text = prompt
def _secret_paint_q_end_selection_mode():
    global _secret_paint_q_selection_mode, _secret_paint_q_prompt_text
    _secret_paint_q_selection_mode = None
    _secret_paint_q_prompt_text = "Choose a plant to paint with"
def _secret_paint_q_enable_selection_overlays(context):
    """Enable overlays only in the 3D viewport that started the picker."""
    area = getattr(context, "area", None)
    context_space = getattr(context, "space_data", None)
    if area is None or area.type != 'VIEW_3D' or context_space is None:
        return []
    overlay = getattr(context_space, "overlay", None)
    if overlay is None:
        return []
    try:
        show_overlays = bool(overlay.show_overlays)
        overlay.show_overlays = True
        area.tag_redraw()
        return [(overlay, show_overlays)]
    except (AttributeError, ReferenceError, RuntimeError):
        return []
def _secret_paint_q_restore_selection_overlays(states):
    for overlay, show_overlays in states or ():
        try:
            overlay.show_overlays = show_overlays
        except (AttributeError, RuntimeError):
            continue
def _secret_paint_q_prompt_viewport(context):
    """Return pointer IDs for the invoking 3D viewport and its window region."""
    area = getattr(context, "area", None)
    if area is None or area.type != 'VIEW_3D':
        return None
    region = getattr(context, "region", None)
    if region is None or region.type != 'WINDOW':
        region = next(
            (candidate for candidate in area.regions
             if candidate.type == 'WINDOW'),
            None,
        )
    if region is None:
        return None
    try:
        return area.as_pointer(), region.as_pointer()
    except (AttributeError, ReferenceError, RuntimeError):
        return None
def _secret_paint_q_add_prompt_handler(context):
    viewport = _secret_paint_q_prompt_viewport(context)
    if viewport is None:
        return None
    return bpy.types.SpaceView3D.draw_handler_add(
        _secret_paint_q_prompt_draw,
        viewport,
        'WINDOW',
        'POST_PIXEL',
    )
def _secret_paint_q_prompt_draw(area_pointer, region_pointer):
    if not _secret_paint_q_prompt:
        return
    try:
        import blf
        area = bpy.context.area
        region = bpy.context.region
        if (area is None or region is None or
                area.as_pointer() != area_pointer or
                region.as_pointer() != region_pointer):
            return
        preferences = bpy.context.preferences.addons[__package__].preferences
        if not preferences.checkboxShowPaintPrompt:
            return
        space_data = bpy.context.space_data
        if not space_data or not getattr(space_data.overlay, "show_overlays", False):
            return
        font_id = 0
        text = _secret_paint_q_prompt_text
        blf.size(font_id, 28)
        width, _height = blf.dimensions(font_id, text)
        blf.position(font_id, max(12, (region.width - width) * 0.5), region.height - 90, 0)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        blf.draw(font_id, text)
    except Exception:
        pass
def _secret_paint_q_view_area_region_space(context, event):
    """Resolve the VIEW_3D actually containing the event's mouse position."""
    try:
        mouse_x = int(event.mouse_x)
        mouse_y = int(event.mouse_y)
    except (AttributeError, TypeError, ValueError):
        mouse_x = mouse_y = None
    window = getattr(context, "window", None)
    screen = getattr(window, "screen", None)
    if mouse_x is not None and mouse_y is not None and screen is not None:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space_data = getattr(getattr(area, "spaces", None), "active", None)
            for region in area.regions:
                if region.type != "WINDOW":
                    continue
                region_x = int(getattr(region, "x", area.x))
                region_y = int(getattr(region, "y", area.y))
                if not (
                        region_x <= mouse_x < region_x + region.width and
                        region_y <= mouse_y < region_y + region.height):
                    continue
                return (
                    area,
                    region,
                    space_data,
                    (mouse_x - region_x, mouse_y - region_y),
                )
    area = getattr(context, "area", None)
    if area is None or area.type != "VIEW_3D":
        return None, None, None, None
    region = next(
        (candidate for candidate in area.regions if candidate.type == "WINDOW"),
        None,
    )
    if region is None:
        return None, None, None, None
    try:
        coord = (
            int(event.mouse_x - region.x),
            int(event.mouse_y - region.y),
        )
    except (AttributeError, TypeError):
        coord = (event.mouse_region_x, event.mouse_region_y)
    if not (0 <= coord[0] < region.width and 0 <= coord[1] < region.height):
        return area, region, getattr(context, "space_data", None), None
    return area, region, getattr(context, "space_data", None), coord
def _secret_paint_q_window_region_and_coord(context, event):
    """Return the actual 3D window region and mouse coordinate in that region."""
    _area, region, _space_data, coord = _secret_paint_q_view_area_region_space(
        context,
        event,
    )
    return region, coord
def _secret_paint_q_system_brush_objects(system):
    """Return the source object(s) used by a paint system."""
    modifier = _secret_paint_1731_paint_modifier(system)
    if modifier is None:
        return []
    brush_objects = []
    brush_object = _secret_paint_1731_modifier_value(modifier, "Input_2", None)
    if brush_object is not None:
        brush_objects.append(brush_object)
    brush_collection = _secret_paint_1731_modifier_value(modifier, "Input_9", None)
    if brush_collection is not None and hasattr(brush_collection, "all_objects"):
        brush_objects.extend(brush_collection.all_objects)
    unique_objects = []
    for brush_object in brush_objects:
        if brush_object not in unique_objects:
            unique_objects.append(brush_object)
    return unique_objects
def _secret_paint_q_single_system_brush_object(system):
    """Return one source object for a system's temporary hover outline."""
    for brush_object in _secret_paint_q_system_brush_objects(system):
        if brush_object != system:
            return brush_object
    return None
def _secret_paint_q_system_or_brush_uses_bounds(system):
    """Return whether a system or its direct Input_2 brush is in bounds mode."""
    if not _secret_paint_q_is_paint_system(system):
        return False
    if getattr(system, "display_type", "SOLID") == "BOUNDS":
        return True
    modifier = _secret_paint_1731_paint_modifier(system)
    brush_object = _secret_paint_1731_modifier_value(
        modifier,
        "Input_2",
        None,
    )
    return (
        brush_object is not None
        and getattr(brush_object, "display_type", "SOLID") == "BOUNDS"
    )
def _secret_paint_q_is_paint_system(obj):
    return (
        obj is not None
        and obj.type in {"CURVE", "CURVES"}
        and obj.parent is not None
        and obj.parent.type == "MESH"
        and _secret_paint_1731_paint_modifier(obj) is not None
    )
def _secret_paint_q_instance_owner_cache(context, system_cache):
    """Cache a BVH of instances belonging to visible bounded systems."""
    if system_cache is None:
        system_cache = {}
    cached = system_cache.get("instance_owner_by_transform")
    if cached is not None:
        return cached
    owners = {}
    bounds_vertices = []
    bounds_faces = []
    bounds_face_instances = []
    bounds_instances = []
    bounded_instance_systems = set()
    try:
        depsgraph = context.evaluated_depsgraph_get()
        frozen_bounded_systems = set(
            _secret_paint_q_frozen_bounded_systems(context, system_cache)
        )
        paint_systems = {
            obj.as_pointer(): obj
            for obj in frozen_bounded_systems
        }
        visible_systems = {}
        for pointer, system in paint_systems.items():
            try:
                system_visible = (
                    system.name in context.view_layer.objects and
                    system.visible_get(view_layer=context.view_layer)
                )
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                system_visible = not getattr(system, "hide_viewport", False)
            if system_visible:
                visible_systems[pointer] = system
        box_faces = (
            (0, 1, 2, 3), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 7, 4), (1, 2, 6, 5),
        )
        for instance in depsgraph.object_instances:
            if not instance.is_instance or instance.parent is None:
                continue
            parent = getattr(instance.parent, "original", instance.parent)
            parent = visible_systems.get(parent.as_pointer())
            if parent is None:
                continue
            source = getattr(instance.object, "original", instance.object)
            if source is None:
                continue
            instance_object = instance.object
            instance_bounds = getattr(instance_object, "bound_box", None)
            if not instance_bounds:
                continue
            frozen_instance_bounds = tuple(
                Vector(corner) for corner in instance_bounds
            )
            base_index = len(bounds_vertices)
            instance_matrix = instance.matrix_world
            bounds_vertices.extend(
                instance_matrix @ Vector(corner)
                for corner in frozen_instance_bounds
            )
            bounds_instance_index = len(bounds_instances)
            bounds_instances.append((
                parent,
                source,
                instance_matrix.copy(),
                frozen_instance_bounds,
            ))
            for face in box_faces:
                bounds_faces.append(tuple(base_index + index for index in face))
                bounds_face_instances.append(bounds_instance_index)
            bounded_instance_systems.add(parent)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        owners = {}
        bounds_vertices = []
        bounds_faces = []
        bounds_face_instances = []
        bounds_instances = []
        bounded_instance_systems = set()
    system_cache["instance_owner_by_transform"] = owners
    bounds_bvh = None
    if bounds_faces:
        try:
            from mathutils.bvhtree import BVHTree
            bounds_bvh = BVHTree.FromPolygons(
                bounds_vertices,
                bounds_faces,
                all_triangles=False,
            )
        except (RuntimeError, TypeError, ValueError):
            bounds_bvh = None
            bounds_face_instances = []
            bounds_instances = []
            bounded_instance_systems = set()
    system_cache["bounded_instance_bvh"] = (
        bounds_bvh,
        bounds_face_instances,
        bounds_instances,
        bounded_instance_systems,
    )
    return owners
def _secret_paint_q_target_bounds_cache(context, system_cache, candidate_systems):
    """Build exact instance bounds only for the few systems relevant now."""
    cache = system_cache if system_cache is not None else {}
    frozen_systems = set(_secret_paint_q_frozen_bounded_systems(context, cache))
    candidates = []
    pointers = set()
    for system in candidate_systems or ():
        try:
            pointer = system.as_pointer()
        except (AttributeError, ReferenceError):
            continue
        if (pointer in pointers or system not in frozen_systems or
                not _secret_paint_q_is_paint_system(system)):
            continue
        try:
            visible = (
                system.name in context.view_layer.objects and
                system.visible_get(view_layer=context.view_layer)
            )
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            visible = not getattr(system, "hide_viewport", False)
        if not visible:
            continue
        pointers.add(pointer)
        candidates.append(system)
    cache_key = tuple(sorted(pointers))
    if not cache_key:
        return (None, [], [], set())
    targeted_caches = cache.setdefault("targeted_bounds_bvhs", {})
    cached = targeted_caches.get(cache_key)
    if cached is not None:
        return cached

    maximum_exact_instances = 2048
    try:
        manual_instance_count = sum(
            len(system.data.curves)
            for system in candidates
            if system.type == "CURVES"
        )
        expected_instance_count = (
            manual_instance_count
            if manual_instance_count and all(
                system.type == "CURVES" for system in candidates
            )
            else None
        )
    except (AttributeError, ReferenceError, TypeError):
        manual_instance_count = 0
        expected_instance_count = None
    if manual_instance_count > maximum_exact_instances:
        result = (None, [], [], set())
        targeted_caches[cache_key] = result
        return result

    candidate_by_pointer = {
        system.as_pointer(): system for system in candidates
    }
    bounds_vertices = []
    bounds_faces = []
    bounds_face_instances = []
    bounds_instances = []
    bounded_instance_systems = set()
    box_faces = (
        (0, 1, 2, 3), (4, 5, 6, 7),
        (0, 1, 5, 4), (2, 3, 7, 6),
        (0, 3, 7, 4), (1, 2, 6, 5),
    )
    too_large = False
    try:
        depsgraph = context.evaluated_depsgraph_get()
        for instance in depsgraph.object_instances:
            if not instance.is_instance or instance.parent is None:
                continue
            parent = getattr(instance.parent, "original", instance.parent)
            parent = candidate_by_pointer.get(parent.as_pointer())
            if parent is None:
                continue
            source = getattr(instance.object, "original", instance.object)
            instance_bounds = getattr(instance.object, "bound_box", None)
            if source is None or not instance_bounds:
                continue
            if len(bounds_instances) >= maximum_exact_instances:
                too_large = True
                break
            frozen_bounds = tuple(Vector(corner) for corner in instance_bounds)
            instance_matrix = instance.matrix_world.copy()
            base_index = len(bounds_vertices)
            bounds_vertices.extend(
                instance_matrix @ corner for corner in frozen_bounds
            )
            instance_index = len(bounds_instances)
            bounds_instances.append((
                parent,
                source,
                instance_matrix,
                frozen_bounds,
            ))
            for face in box_faces:
                bounds_faces.append(tuple(base_index + index for index in face))
                bounds_face_instances.append(instance_index)
            bounded_instance_systems.add(parent)
            if (expected_instance_count is not None and
                    len(bounds_instances) >= expected_instance_count):
                break
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        too_large = True

    bounds_bvh = None
    if bounds_faces and not too_large:
        try:
            from mathutils.bvhtree import BVHTree
            bounds_bvh = BVHTree.FromPolygons(
                bounds_vertices,
                bounds_faces,
                all_triangles=False,
            )
        except (RuntimeError, TypeError, ValueError):
            bounds_bvh = None
    if bounds_bvh is None:
        bounds_face_instances = []
        bounds_instances = []
        bounded_instance_systems = set()
    result = (
        bounds_bvh,
        bounds_face_instances,
        bounds_instances,
        bounded_instance_systems,
    )
    targeted_caches[cache_key] = result
    return result
def _secret_paint_q_source_instance_owner_cache(
        context,
        source,
        source_systems,
        system_cache,
):
    """Cache exact evaluated owners for one shared brush source only."""
    cache = system_cache if system_cache is not None else {}
    try:
        source_pointer = source.as_pointer()
    except (AttributeError, ReferenceError):
        return {}
    source_caches = cache.setdefault("instance_owners_by_source", {})
    owners = source_caches.get(source_pointer)
    if owners is not None:
        return owners
    owners = {}
    candidate_owners = {}
    for system in source_systems:
        try:
            candidate_owners[system.as_pointer()] = system
        except (AttributeError, ReferenceError):
            continue
    try:
        depsgraph = context.evaluated_depsgraph_get()
        for instance in depsgraph.object_instances:
            if not instance.is_instance or instance.parent is None:
                continue
            parent = getattr(instance.parent, "original", instance.parent)
            owner = candidate_owners.get(parent.as_pointer())
            if owner is None:
                continue
            instance_source = getattr(
                instance.object,
                "original",
                instance.object,
            )
            if (instance_source is None or
                    instance_source.as_pointer() != source_pointer):
                continue
            owners.setdefault(
                instance.matrix_world.copy().freeze(),
                owner,
            )
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        owners = {}
    source_caches[source_pointer] = owners
    return owners
def _secret_paint_q_instance_system_from_hit(
        context,
        hit_object,
        hit_matrix,
        system_cache,
        allow_cache_build=True,
        ray_origin=None,
        ray_direction=None,
):
    """Resolve a ray-hit generated instance to its owning paint system."""
    source = getattr(hit_object, "original", hit_object)
    if source is None or hit_matrix is None:
        return None
    try:
        if hit_matrix == source.matrix_world:
            return None
    except (AttributeError, ReferenceError, TypeError):
        pass
    source_systems = _secret_paint_q_cached_systems_for_brush(
        source,
        system_cache,
    )
    if not source_systems:
        return None
    if len(source_systems) == 1:
        return source_systems[0]
    if not allow_cache_build:
        return None
    if ray_origin is not None and ray_direction is not None:
        root_owner, _root_distance, roots_complete = (
            _secret_paint_q_curve_root_system_under_cursor(
                context,
                ray_origin,
                ray_direction,
                system_cache,
                candidate_systems=source_systems,
            )
        )
        if root_owner is not None and roots_complete:
            return root_owner
    try:
        key = hit_matrix.copy().freeze()
    except (AttributeError, ReferenceError, TypeError, ValueError):
        return None
    owner = _secret_paint_q_source_instance_owner_cache(
        context,
        source,
        source_systems,
        system_cache,
    ).get(key)
    return owner if _secret_paint_q_is_paint_system(owner) else None
def _secret_paint_q_ray_bounds_distance(
        bounds,
        matrix_world,
        ray_origin,
        ray_direction,
):
    """Return the exact world-ray distance to a frozen local bounds box."""
    try:
        if not bounds:
            return None
        matrix_inverse = matrix_world.inverted_safe()
        world_origin = Vector(ray_origin)
        world_direction = Vector(ray_direction).normalized()
        local_origin = matrix_inverse @ world_origin
        local_direction = matrix_inverse.to_3x3() @ world_direction
        minimum = [min(corner[index] for corner in bounds) for index in range(3)]
        maximum = [max(corner[index] for corner in bounds) for index in range(3)]
        near = -float("inf")
        far = float("inf")
        for index in range(3):
            origin_component = local_origin[index]
            direction_component = local_direction[index]
            if abs(direction_component) < 1.0e-8:
                if origin_component < minimum[index] or origin_component > maximum[index]:
                    return None
                continue
            first = (minimum[index] - origin_component) / direction_component
            second = (maximum[index] - origin_component) / direction_component
            if first > second:
                first, second = second, first
            near = max(near, first)
            far = min(far, second)
            if near > far:
                return None
        if far < 0.0:
            return None
        hit_parameter = near if near >= 0.0 else far
        local_hit = local_origin + local_direction * hit_parameter
        world_hit = matrix_world @ local_hit
        distance = (world_hit - world_origin).dot(world_direction)
        return distance if distance >= 0.0 else None
    except (AttributeError, IndexError, RuntimeError, TypeError, ValueError):
        return None
def _secret_paint_q_ray_box_distance(obj, ray_origin, ray_direction):
    """Return the world-ray distance to an object's local-space bound box."""
    try:
        return _secret_paint_q_ray_bounds_distance(
            obj.bound_box,
            obj.matrix_world,
            ray_origin,
            ray_direction,
        )
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return None
def _secret_paint_q_ray_box_exit_distance(
        obj,
        matrix_world,
        ray_origin,
        ray_direction,
):
    """Return the distance at which a world ray exits an object's bounds."""
    try:
        bounds = obj.bound_box
        if not bounds:
            return None
        matrix_inverse = matrix_world.inverted_safe()
        local_origin = matrix_inverse @ Vector(ray_origin)
        local_direction = matrix_inverse.to_3x3() @ Vector(ray_direction)
        minimum = [min(corner[index] for corner in bounds) for index in range(3)]
        maximum = [max(corner[index] for corner in bounds) for index in range(3)]
        near = -float("inf")
        far = float("inf")
        for index in range(3):
            origin_component = local_origin[index]
            direction_component = local_direction[index]
            if abs(direction_component) < 1.0e-8:
                if origin_component < minimum[index] or origin_component > maximum[index]:
                    return None
                continue
            first = (minimum[index] - origin_component) / direction_component
            second = (maximum[index] - origin_component) / direction_component
            if first > second:
                first, second = second, first
            near = max(near, first)
            far = min(far, second)
            if near > far:
                return None
        return far if far >= 0.0 else None
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return None
def _secret_paint_q_point_segment_distance_squared(point, first, second):
    segment_x = second[0] - first[0]
    segment_y = second[1] - first[1]
    length_squared = segment_x * segment_x + segment_y * segment_y
    if length_squared <= 1.0e-12:
        return (
            (point[0] - first[0]) ** 2 +
            (point[1] - first[1]) ** 2
        )
    factor = max(
        0.0,
        min(
            1.0,
            (
                (point[0] - first[0]) * segment_x +
                (point[1] - first[1]) * segment_y
            ) / length_squared,
        ),
    )
    nearest_x = first[0] + factor * segment_x
    nearest_y = first[1] + factor * segment_y
    return (point[0] - nearest_x) ** 2 + (point[1] - nearest_y) ** 2
def _secret_paint_q_projected_edges_hit(
        region,
        region_3d,
        coord,
        matrix_world,
        vertices,
        edges,
        threshold,
):
    """Return whether the cursor is close enough to a displayed screen edge."""
    try:
        from bpy_extras import view3d_utils
        projected = {}
        threshold_squared = threshold * threshold
        for first_index, second_index in edges:
            if first_index not in projected:
                projected[first_index] = view3d_utils.location_3d_to_region_2d(
                    region,
                    region_3d,
                    matrix_world @ Vector(vertices[first_index]),
                )
            if second_index not in projected:
                projected[second_index] = view3d_utils.location_3d_to_region_2d(
                    region,
                    region_3d,
                    matrix_world @ Vector(vertices[second_index]),
                )
            first = projected[first_index]
            second = projected[second_index]
            if first is None or second is None:
                continue
            if _secret_paint_q_point_segment_distance_squared(
                    coord,
                    first,
                    second,
            ) <= threshold_squared:
                return True
    except (AttributeError, IndexError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass
    return False
def _secret_paint_q_display_line_hit(
        context,
        region,
        region_3d,
        coord,
        evaluated_hit_object,
        original_hit_object,
        hit_matrix,
        face_index,
        display_owner,
        display_type,
):
    """Match Object Mode's WIRE/BOUNDS line-only selection behavior."""
    if region is None or region_3d is None or coord is None:
        return False
    try:
        ui_scale = float(context.preferences.system.ui_scale)
    except (AttributeError, TypeError, ValueError):
        ui_scale = 1.0
    threshold = max(5.0, 7.0 * ui_scale)
    if display_type == "BOUNDS":
        bounds_object = evaluated_hit_object or original_hit_object
        vertices = list(getattr(bounds_object, "bound_box", ()))
        bounds_matrix = hit_matrix
        if not vertices:
            vertices = list(getattr(display_owner, "bound_box", ()))
            bounds_matrix = getattr(display_owner, "matrix_world", hit_matrix)
        edges = (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        )
        return _secret_paint_q_projected_edges_hit(
            region,
            region_3d,
            coord,
            bounds_matrix,
            vertices,
            edges,
            threshold,
        )
    mesh = getattr(evaluated_hit_object, "data", None)
    polygons = getattr(mesh, "polygons", None)
    mesh_vertices = getattr(mesh, "vertices", None)
    if (polygons is not None and mesh_vertices is not None and
            0 <= face_index < len(polygons)):
        polygon_indices = tuple(polygons[face_index].vertices)
        if len(polygon_indices) >= 2:
            vertices = {
                index: mesh_vertices[index].co
                for index in polygon_indices
            }
            edges = tuple(
                (
                    polygon_indices[index],
                    polygon_indices[(index + 1) % len(polygon_indices)],
                )
                for index in range(len(polygon_indices))
            )
            return _secret_paint_q_projected_edges_hit(
                region,
                region_3d,
                coord,
                hit_matrix,
                vertices,
                edges,
                threshold,
            )
    vertices = list(original_hit_object.bound_box)
    edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    return _secret_paint_q_projected_edges_hit(
        region,
        region_3d,
        coord,
        hit_matrix,
        vertices,
        edges,
        threshold,
    )
def _secret_paint_q_frozen_bounded_systems(context, system_cache):
    """Freeze systems shown as bounds before temporary previews alter them."""
    cache = system_cache if system_cache is not None else {}
    systems = cache.get("bounded_root_systems")
    if systems is not None:
        return systems
    systems = []
    view_layer_objects = context.view_layer.objects
    for system in context.scene.objects:
        if (not _secret_paint_q_is_paint_system(system) or
                system.name not in view_layer_objects):
            continue
        try:
            if not system.visible_get(view_layer=context.view_layer):
                continue
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            if getattr(system, "hide_viewport", False):
                continue
        if _secret_paint_q_system_or_brush_uses_bounds(system):
            systems.append(system)
    systems = tuple(systems)
    cache["bounded_root_systems"] = systems
    return systems
def _secret_paint_q_curve_root_system_under_cursor(
        context,
        ray_origin,
        ray_direction,
        system_cache,
        candidate_systems=None,
):
    """Pick manual bounds systems from bulk Curves roots without a GN scan."""
    cache = system_cache if system_cache is not None else {}
    systems = _secret_paint_q_frozen_bounded_systems(context, cache)
    if candidate_systems is not None:
        try:
            candidate_pointers = {
                system.as_pointer() for system in candidate_systems
            }
            systems = tuple(
                system for system in systems
                if system.as_pointer() in candidate_pointers
            )
        except (AttributeError, ReferenceError, TypeError):
            systems = ()
    if not systems:
        return None, float("inf"), True
    if np is None:
        return None, float("inf"), False
    root_cache = cache.setdefault("curve_root_bounds", {})
    world_origin = np.asarray(tuple(Vector(ray_origin)), dtype=np.float64)
    world_direction = np.asarray(
        tuple(Vector(ray_direction).normalized()),
        dtype=np.float64,
    )
    nearest = None
    nearest_distance = float("inf")
    complete = True
    for system in systems:
        try:
            if _secret_paint_q_ray_box_distance(
                    system,
                    ray_origin,
                    ray_direction,
            ) is None:
                continue
            pointer = system.as_pointer()
            cached_roots = root_cache.get(pointer)
            if cached_roots is None:
                data = getattr(system, "data", None)
                curves = getattr(data, "curves", None)
                points = getattr(data, "points", None)
                attributes = getattr(data, "attributes", None)
                position_attribute = (
                    attributes.get("position") if attributes is not None else None
                )
                curve_count = len(curves) if curves is not None else 0
                point_count = len(points) if points is not None else 0
                if not curve_count or not point_count or position_attribute is None:
                    complete = False
                    continue
                positions = np.empty(point_count * 3, dtype=np.float32)
                position_attribute.data.foreach_get("vector", positions)
                positions = positions.reshape((-1, 3))
                if point_count == curve_count * 2:
                    roots = positions[::2]
                    tips = positions[1::2]
                else:
                    root_indices = np.fromiter(
                        (curve.first_point_index for curve in curves),
                        dtype=np.int32,
                        count=curve_count,
                    )
                    roots = positions[root_indices]
                    tip_indices = np.minimum(root_indices + 1, point_count - 1)
                    tips = positions[tip_indices]
                matrix = np.asarray(system.matrix_world, dtype=np.float64)
                roots_world = roots @ matrix[:3, :3].T + matrix[:3, 3]
                directions_world = (tips - roots) @ matrix[:3, :3].T
                direction_lengths = np.linalg.norm(
                    directions_world,
                    axis=1,
                )
                valid_directions = direction_lengths > 1.0e-8
                directions_world[valid_directions] /= (
                    direction_lengths[valid_directions, None]
                )
                if not np.all(valid_directions):
                    fallback_direction = matrix[:3, 2]
                    fallback_length = np.linalg.norm(fallback_direction)
                    if fallback_length > 1.0e-8:
                        fallback_direction = fallback_direction / fallback_length
                    else:
                        fallback_direction = np.array((0.0, 0.0, 1.0))
                    directions_world[~valid_directions] = fallback_direction
                modifier = _secret_paint_1731_paint_modifier(system)
                brush_objects = _secret_paint_q_system_brush_objects(system)
                envelope_lower = float("inf")
                envelope_upper = -float("inf")
                radial_radius = 0.0
                for brush_object in brush_objects:
                    brush_bounds = tuple(
                        Vector(corner)
                        for corner in getattr(brush_object, "bound_box", ())
                    )
                    if not brush_bounds:
                        continue
                    minimum = Vector(tuple(
                        min(corner[index] for corner in brush_bounds)
                        for index in range(3)
                    ))
                    maximum = Vector(tuple(
                        max(corner[index] for corner in brush_bounds)
                        for index in range(3)
                    ))
                    brush_center = (minimum + maximum) * 0.5
                    half_extents = (maximum - minimum) * 0.5
                    brush_radial = Vector((
                        half_extents.x,
                        half_extents.y,
                        0.0,
                    )).length
                    brush_radial += Vector((
                        brush_center.x,
                        brush_center.y,
                        0.0,
                    )).length
                    brush_scale = 1.0
                    try:
                        brush_scale = max(
                            abs(value)
                            for value in brush_object.matrix_world.to_scale()
                        )
                    except (AttributeError, RuntimeError, TypeError, ValueError):
                        pass
                    brush_radial *= brush_scale
                    brush_center_z = brush_center.z * brush_scale
                    brush_half_z = abs(half_extents.z * brush_scale)
                    radial_radius = max(radial_radius, brush_radial)
                    envelope_lower = min(
                        envelope_lower,
                        brush_center_z - brush_half_z,
                    )
                    envelope_upper = max(
                        envelope_upper,
                        brush_center_z + brush_half_z,
                    )
                if envelope_lower == float("inf"):
                    complete = False
                    continue
                center_offset = (envelope_lower + envelope_upper) * 0.5
                axial_half = (envelope_upper - envelope_lower) * 0.5
                system_scale = 1.0
                try:
                    system_scale = max(
                        abs(value) for value in system.matrix_world.to_scale()
                    )
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass
                random_scale_max = float(
                    _secret_paint_1731_modifier_value(
                        modifier,
                        "Input_82",
                        1.0,
                    ) or 1.0
                )
                total_scale = system_scale * max(1.0, abs(random_scale_max))
                center_offset *= total_scale
                axial_half *= total_scale
                radial_radius *= total_scale
                if axial_half <= 1.0e-8 or radial_radius <= 1.0e-8:
                    complete = False
                    continue
                centers_world = (
                    roots_world + directions_world * center_offset
                )
                cached_roots = (
                    centers_world,
                    directions_world,
                    radial_radius,
                    axial_half,
                )
                root_cache[pointer] = cached_roots
            centers_world, directions_world, radial_radius, axial_half = (
                cached_roots
            )
            origin_offsets = world_origin - centers_world
            axial_origin = np.einsum(
                "ij,ij->i",
                origin_offsets,
                directions_world,
            )
            axial_direction = directions_world @ world_direction
            origin_dot_ray = origin_offsets @ world_direction
            radial_origin_squared = np.maximum(
                0.0,
                np.einsum("ij,ij->i", origin_offsets, origin_offsets) -
                axial_origin * axial_origin,
            )
            radial_direction_squared = np.maximum(
                0.0,
                1.0 - axial_direction * axial_direction,
            )
            radial_origin_direction = (
                origin_dot_ray - axial_origin * axial_direction
            )
            count = len(centers_world)
            radial_near = np.full(count, -np.inf, dtype=np.float64)
            radial_far = np.full(count, np.inf, dtype=np.float64)
            radial_c = radial_origin_squared - radial_radius * radial_radius
            radial_parallel = radial_direction_squared <= 1.0e-12
            radial_valid = (~radial_parallel) | (radial_c <= 0.0)
            radial_solved = ~radial_parallel
            discriminant = (
                radial_origin_direction * radial_origin_direction -
                radial_direction_squared * radial_c
            )
            radial_valid &= (~radial_solved) | (discriminant >= 0.0)
            solved_indices = np.flatnonzero(
                radial_solved & (discriminant >= 0.0)
            )
            if solved_indices.size:
                square_root = np.sqrt(discriminant[solved_indices])
                denominator = radial_direction_squared[solved_indices]
                radial_near[solved_indices] = (
                    -radial_origin_direction[solved_indices] - square_root
                ) / denominator
                radial_far[solved_indices] = (
                    -radial_origin_direction[solved_indices] + square_root
                ) / denominator
            axial_near = np.full(count, -np.inf, dtype=np.float64)
            axial_far = np.full(count, np.inf, dtype=np.float64)
            axial_parallel = np.abs(axial_direction) <= 1.0e-12
            axial_valid = (~axial_parallel) | (
                np.abs(axial_origin) <= axial_half
            )
            axial_solved_indices = np.flatnonzero(~axial_parallel)
            if axial_solved_indices.size:
                first = (
                    -axial_half - axial_origin[axial_solved_indices]
                ) / axial_direction[axial_solved_indices]
                second = (
                    axial_half - axial_origin[axial_solved_indices]
                ) / axial_direction[axial_solved_indices]
                axial_near[axial_solved_indices] = np.minimum(first, second)
                axial_far[axial_solved_indices] = np.maximum(first, second)
            near = np.maximum(np.maximum(radial_near, axial_near), 0.0)
            far = np.minimum(radial_far, axial_far)
            valid_indices = np.flatnonzero(
                radial_valid & axial_valid & (far >= near)
            )
            if valid_indices.size:
                distance = float(near[valid_indices].min())
                if distance < nearest_distance:
                    nearest = system
                    nearest_distance = distance
        except (AttributeError, IndexError, ReferenceError, RuntimeError, TypeError, ValueError):
            complete = False
    return nearest, nearest_distance, complete
def _secret_paint_q_bounds_system_under_cursor(
        context,
        ray_origin,
        ray_direction,
        system_cache,
):
    """Raycast actual displayed instance boxes and return their exact owner."""
    cache = system_cache if system_cache is not None else {}
    root_candidate, root_distance, roots_complete = (
        _secret_paint_q_curve_root_system_under_cursor(
            context,
            ray_origin,
            ray_direction,
            cache,
        )
    )
    if roots_complete:
        return root_candidate, root_distance
    _secret_paint_q_instance_owner_cache(context, cache)
    (
        bounds_bvh,
        bounds_face_instances,
        bounds_instances,
        bounded_instance_systems,
    ) = cache.get(
        "bounded_instance_bvh",
        (None, [], [], set()),
    )
    nearest = None
    nearest_distance = float("inf")
    if bounds_bvh is not None:
        try:
            _location, _normal, face_index, distance = bounds_bvh.ray_cast(
                Vector(ray_origin),
                Vector(ray_direction).normalized(),
            )
            if (face_index is not None and
                    0 <= face_index < len(bounds_face_instances)):
                instance_index = bounds_face_instances[face_index]
                if 0 <= instance_index < len(bounds_instances):
                    nearest = bounds_instances[instance_index][0]
                    nearest_distance = distance
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            pass
    bounds_entries = cache.get("bounded_system_fallback_bounds")
    if bounds_entries is None:
        bounds_entries = []
        view_layer_objects = context.view_layer.objects
        for obj in context.scene.objects:
            if (getattr(obj, "display_type", "SOLID") != "BOUNDS" or
                    not _secret_paint_q_is_paint_system(obj) or
                    obj in bounded_instance_systems or
                    obj.name not in view_layer_objects):
                continue
            try:
                if not obj.visible_get(view_layer=context.view_layer):
                    continue
            except (AttributeError, RuntimeError, TypeError):
                if getattr(obj, "hide_viewport", False):
                    continue
            try:
                bounds_entries.append((
                    obj,
                    tuple(Vector(corner) for corner in obj.bound_box),
                    obj.matrix_world.copy(),
                ))
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                continue
        cache["bounded_system_fallback_bounds"] = bounds_entries
    for system, frozen_bounds, frozen_matrix in bounds_entries:
        try:
            distance = _secret_paint_q_ray_bounds_distance(
                frozen_bounds,
                frozen_matrix,
                ray_origin,
                ray_direction,
            )
            if distance is None:
                continue
            if distance < nearest_distance:
                nearest = system
                nearest_distance = distance
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            continue
    return nearest, nearest_distance
def _secret_paint_q_exact_bounds_system_under_cursor(
        context,
        ray_origin,
        ray_direction,
        system_cache,
        region,
        region_3d,
        coord,
        blocker_distance=None,
        candidate_systems=None,
):
    """Match Object Mode selection against exact evaluated bounds edges."""
    cache = system_cache if system_cache is not None else {}
    bounds_cache = _secret_paint_q_target_bounds_cache(
        context,
        cache,
        candidate_systems,
    )
    (
        bounds_bvh,
        bounds_face_instances,
        bounds_instances,
        _bounded_instance_systems,
    ) = bounds_cache
    if bounds_bvh is None:
        return None, float("inf"), False
    world_origin = Vector(ray_origin)
    world_direction = Vector(ray_direction).normalized()
    cast_origin = world_origin.copy()
    seen_instances = set()
    try:
        ui_scale = float(context.preferences.system.ui_scale)
    except (AttributeError, TypeError, ValueError):
        ui_scale = 1.0
    edge_threshold = max(5.0, 7.0 * ui_scale)
    bounds_edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    bounds_ray_intersected = False
    for _depth in range(128):
        try:
            location, _normal, face_index, _distance = bounds_bvh.ray_cast(
                cast_origin,
                world_direction,
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            break
        if location is None or face_index is None:
            break
        distance = (Vector(location) - world_origin).dot(world_direction)
        if blocker_distance is not None and distance > blocker_distance + 1.0e-4:
            break
        bounds_ray_intersected = True
        if 0 <= face_index < len(bounds_face_instances):
            instance_index = bounds_face_instances[face_index]
            if (instance_index not in seen_instances and
                    0 <= instance_index < len(bounds_instances)):
                seen_instances.add(instance_index)
                (
                    owner,
                    _source,
                    instance_matrix,
                    instance_bounds,
                ) = bounds_instances[instance_index]
                if _secret_paint_q_projected_edges_hit(
                        region,
                        region_3d,
                        coord,
                        instance_matrix,
                        instance_bounds,
                        bounds_edges,
                        edge_threshold,
                ):
                    return owner, distance, True
        cast_origin = Vector(location) + world_direction * 1.0e-4
    return None, float("inf"), bounds_ray_intersected
def _secret_paint_q_paint_system_from_ray(
        context,
        ray_origin,
        ray_direction,
        system_cache=None,
        ray_state=None,
        region=None,
        region_3d=None,
        coord=None,
        select_bounds_system_geometry=False,
        allow_instance_cache=True,
        ignored_objects=None,
):
    """Return the paint system represented by a viewport ray."""
    ray_origin = Vector(ray_origin)
    ray_direction = Vector(ray_direction).normalized()
    if ray_state is not None:
        ray_state.clear()
        ray_state["hit"] = False
    try:
        depsgraph = context.evaluated_depsgraph_get()
        cast_origin = ray_origin.copy()
        display_filtered = False
        for _depth in range(64):
            hit, location, _normal, face_index, evaluated_hit_object, hit_matrix = context.scene.ray_cast(
                depsgraph,
                cast_origin,
                ray_direction,
            )
            original_hit_object = getattr(
                evaluated_hit_object,
                "original",
                evaluated_hit_object,
            )
            if not hit or original_hit_object is None:
                if ray_state is not None:
                    ray_state.update(
                        hit=False,
                        object=None,
                        location=None,
                        display_filtered=display_filtered,
                    )
                return None
            if original_hit_object in (ignored_objects or ()):
                ignored_display_type = getattr(
                    original_hit_object,
                    "display_type",
                    "SOLID",
                )
                if ignored_display_type in {"WIRE", "BOUNDS"}:
                    ignored_line_hit = _secret_paint_q_display_line_hit(
                        context,
                        region,
                        region_3d,
                        coord,
                        evaluated_hit_object,
                        original_hit_object,
                        hit_matrix,
                        face_index,
                        original_hit_object,
                        ignored_display_type,
                    )
                    if not ignored_line_hit:
                        display_filtered = True
                        cast_origin = Vector(location) + ray_direction * 1.0e-4
                        continue
                if ray_state is not None:
                    ray_state.update(
                        hit=True,
                        object=original_hit_object,
                        location=location,
                        display_filtered=False,
                        display_line_hit=False,
                        ignored_solid_blocker=True,
                    )
                return None
            is_viewport_mask = (
                bool(original_hit_object.get(
                    "_secret_paint_q_preview_mask",
                    False,
                )) or
                getattr(original_hit_object, "name", "").startswith(
                    "Secret Paint Viewport Mask"
                )
            )
            if is_viewport_mask:
                display_filtered = True
                cast_origin = Vector(location) + ray_direction * 1.0e-4
                continue
            paint_system = None
            if _secret_paint_q_is_paint_system(original_hit_object):
                paint_system = original_hit_object
            else:
                paint_system = _secret_paint_q_instance_system_from_hit(
                    context,
                    original_hit_object,
                    hit_matrix,
                    system_cache,
                    allow_cache_build=allow_instance_cache,
                    ray_origin=ray_origin,
                    ray_direction=ray_direction,
                )
            unresolved_instance = False
            unresolved_instance_key = None
            if paint_system is None and system_cache is not None:
                try:
                    is_generated_instance = (
                        hit_matrix != original_hit_object.matrix_world
                    )
                except (AttributeError, ReferenceError, TypeError):
                    is_generated_instance = False
                if is_generated_instance:
                    unresolved_instance = bool(
                        _secret_paint_q_cached_systems_for_brush(
                            original_hit_object,
                            system_cache,
                        )
                    )
                    if unresolved_instance:
                        try:
                            unresolved_instance_key = (
                                original_hit_object.as_pointer(),
                                hit_matrix.copy().freeze(),
                            )
                        except (AttributeError, ReferenceError, TypeError, ValueError):
                            unresolved_instance_key = None
            display_owner = paint_system or original_hit_object
            frozen_bounds_systems = (
                system_cache.get("bounded_root_systems", ())
                if system_cache is not None else ()
            )
            paint_system_uses_bounds = (
                paint_system is not None and
                (
                    paint_system in frozen_bounds_systems or
                    _secret_paint_q_system_or_brush_uses_bounds(paint_system)
                )
            )
            display_type = (
                "BOUNDS" if paint_system_uses_bounds
                else getattr(display_owner, "display_type", "SOLID")
            )
            if ray_state is not None:
                ray_state.update(
                    hit=True,
                    object=original_hit_object,
                    location=location,
                    display_filtered=display_filtered,
                    display_line_hit=False,
                    unresolved_instance=unresolved_instance,
                    unresolved_instance_key=unresolved_instance_key,
                )
            if display_type not in {"WIRE", "BOUNDS"}:
                return paint_system
            display_filtered = True
            display_line_hit = _secret_paint_q_display_line_hit(
                context,
                region,
                region_3d,
                coord,
                evaluated_hit_object,
                original_hit_object,
                hit_matrix,
                face_index,
                display_owner,
                display_type,
            )
            if display_line_hit:
                if ray_state is not None:
                    ray_state["display_filtered"] = True
                    ray_state["display_line_hit"] = True
                return paint_system
            cast_origin = Vector(location) + ray_direction * 1.0e-4
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass
    return None
def _secret_paint_q_pick_object(
        context,
        event,
        terrain,
        preserve_active=None,
        system_cache=None,
        include_bounds_systems=False,
        exact_instance_targeting=True,
        ignored_objects=None,
        keep_candidate_on_miss=None,
):
    """Pick only the nearest visible object under the held-Q cursor."""
    picked = None
    active_to_preserve = preserve_active or context.view_layer.objects.active
    view_area, region, space_data, coord = _secret_paint_q_view_area_region_space(
        context,
        event,
    )
    if view_area is not None and region is not None and coord is not None:
        fast_candidate = None
        ray_state = {}
        ray_origin = None
        ray_direction = None
        try:
            from bpy_extras import view3d_utils
            region_3d = (space_data or context.space_data).region_3d
            ray_origin = view3d_utils.region_2d_to_origin_3d(
                region,
                region_3d,
                coord,
            )
            ray_direction = view3d_utils.region_2d_to_vector_3d(
                region,
                region_3d,
                coord,
            )
            fast_candidate = _secret_paint_q_paint_system_from_ray(
                context,
                ray_origin,
                ray_direction,
                system_cache=system_cache,
                ray_state=ray_state,
                region=region,
                region_3d=region_3d,
                coord=coord,
                select_bounds_system_geometry=include_bounds_systems,
                allow_instance_cache=exact_instance_targeting,
                ignored_objects=ignored_objects,
            )
            if fast_candidate is None and ray_state.get("hit"):
                ray_object = ray_state.get("object")
                if (
                    ray_object is not None
                    and ray_object not in (ignored_objects or ())
                    and ray_object != terrain
                    and not ray_state.get("unresolved_instance", False)
                    and not getattr(ray_object, "hide_viewport", False)
                    and not getattr(ray_object, "name", "").startswith(
                        "Secret Paint Viewport Mask"
                    )
                    and (
                        getattr(ray_object, "display_type", "SOLID") not in {
                            "WIRE",
                            "BOUNDS",
                        }
                        or ray_state.get("display_line_hit", False)
                    )
                ):
                    fast_candidate = ray_object
        except (AttributeError, RuntimeError, TypeError, ValueError):
            fast_candidate = None
        pick_cache = None
        if system_cache is not None:
            pick_cache = system_cache.setdefault("hover_pick", {})
        if pick_cache is None:
            pick_cache = {}
        ray_object = ray_state.get("object")
        display_object = ray_object or fast_candidate
        display_type = getattr(display_object, "display_type", "SOLID")
        fast_candidate_is_system = _secret_paint_q_is_paint_system(
            fast_candidate
        )
        needs_bounds_edge_pick = (
            include_bounds_systems and
            not fast_candidate_is_system
        )
        needs_bounds_object_pick = (
            include_bounds_systems and
            fast_candidate is None
        )
        needs_instance_object_pick = ray_state.get(
            "unresolved_instance",
            False,
        )
        if (needs_bounds_edge_pick and exact_instance_targeting and
                ray_origin is not None and ray_direction is not None):
            bounds_candidate_systems = []
            if (_secret_paint_q_is_paint_system(keep_candidate_on_miss) and
                    _secret_paint_q_system_or_brush_uses_bounds(
                        keep_candidate_on_miss
                    )):
                bounds_candidate_systems.append(keep_candidate_on_miss)
            if ray_object is not None and not bounds_candidate_systems:
                for candidate_system in _secret_paint_q_cached_systems_for_brush(
                        ray_object,
                        system_cache,
                ):
                    if _secret_paint_q_system_or_brush_uses_bounds(
                            candidate_system
                    ):
                        bounds_candidate_systems.append(candidate_system)
            blocker_distance = None
            blocker_location = ray_state.get("location")
            blocker_object = ray_state.get("object")
            if blocker_location is not None and blocker_object is not None:
                blocker_display = getattr(
                    blocker_object,
                    "display_type",
                    "SOLID",
                )
                if blocker_display not in {"WIRE", "BOUNDS"}:
                    blocker_distance = (
                        Vector(blocker_location) - Vector(ray_origin)
                    ).dot(Vector(ray_direction).normalized())
            (
                bounds_candidate,
                _bounds_distance,
                bounds_ray_intersected,
            ) = (
                _secret_paint_q_exact_bounds_system_under_cursor(
                    context,
                    ray_origin,
                    ray_direction,
                    system_cache,
                    region,
                    region_3d,
                    coord,
                    blocker_distance=blocker_distance,
                    candidate_systems=bounds_candidate_systems,
                )
            )
            if bounds_candidate is not None:
                fast_candidate = bounds_candidate
                fast_candidate_is_system = True
                needs_bounds_object_pick = False
                needs_instance_object_pick = False
            elif bounds_ray_intersected:
                needs_bounds_object_pick = False
        instance_pick_key = ray_state.get("unresolved_instance_key")
        requires_native_pick = (
            not fast_candidate_is_system
            and (
                keep_candidate_on_miss is None or
                needs_instance_object_pick
            )
            and (
                needs_bounds_object_pick
                or needs_instance_object_pick
                or (
                    not ray_state.get("display_filtered", False)
                    and
                    not ray_state.get("ignored_solid_blocker", False)
                    and (
                        fast_candidate is None
                        or display_type in {"WIRE", "BOUNDS"}
                        or fast_candidate.type in {
                            "EMPTY", "FONT", "META", "SURFACE",
                        }
                    )
                )
            )
        )
        now = time.perf_counter()
        last_native_time = pick_cache.get("native_time", -1.0e9)
        last_native_coord = pick_cache.get("native_coord")
        moved_for_native = (
            last_native_coord is None
            or abs(coord[0] - last_native_coord[0]) >= 2
            or abs(coord[1] - last_native_coord[1]) >= 2
        )
        instance_target_changed = (
            needs_instance_object_pick
            and instance_pick_key is not None
            and instance_pick_key != pick_cache.get("native_instance_key")
        )
        native_pick_due = (
            requires_native_pick
            and exact_instance_targeting
            and (
                instance_target_changed
                or (
                    moved_for_native
                    and now - last_native_time >= 0.20
                )
            )
        )
        if native_pick_due:
            native_candidate = None
            try:
                override = {
                    "area": view_area,
                    "region": region,
                    "space_data": space_data or context.space_data,
                }
                if context.window is not None:
                    override["window"] = context.window
                shading = getattr(space_data or context.space_data, "shading", None)
                saved_xray = getattr(shading, "show_xray", None)
                saved_xray_wireframe = getattr(
                    shading,
                    "show_xray_wireframe",
                    None,
                )
                try:
                    if shading is not None and saved_xray:
                        shading.show_xray = False
                    if shading is not None and saved_xray_wireframe:
                        shading.show_xray_wireframe = False
                    with context.temp_override(**override):
                        result = bpy.ops.view3d.select(
                            location=coord,
                            extend=False,
                            object=True,
                        )
                        selected = bpy.context.view_layer.objects.active
                finally:
                    if shading is not None and saved_xray is not None:
                        shading.show_xray = saved_xray
                    if shading is not None and saved_xray_wireframe is not None:
                        shading.show_xray_wireframe = saved_xray_wireframe
                if (
                    result == {'FINISHED'}
                    and selected is not None
                    and selected not in (ignored_objects or ())
                    and selected not in {terrain, preserve_active}
                ):
                    native_candidate = selected
            except (AttributeError, RuntimeError, TypeError):
                native_candidate = None
            pick_cache["native_time"] = now
            pick_cache["native_coord"] = coord
            pick_cache["native_candidate"] = native_candidate
            pick_cache["native_instance_key"] = instance_pick_key
        if requires_native_pick:
            picked = pick_cache.get("native_candidate")
            if picked in {None, preserve_active, terrain}:
                picked = fast_candidate
        else:
            picked = fast_candidate
            pick_cache["native_candidate"] = None
            pick_cache["native_instance_key"] = None
    if picked == terrain:
        picked = None
    if picked in (ignored_objects or ()):
        picked = None
    picked_is_valid_plant_target = (
        _secret_paint_q_is_paint_system(picked) or
        (
            picked is not None and
            getattr(picked, "type", None) in {"MESH", "EMPTY", "CURVE"}
        )
    )
    fallback_is_valid_plant_target = (
        _secret_paint_q_is_paint_system(keep_candidate_on_miss) or
        (
            keep_candidate_on_miss is not None and
            getattr(keep_candidate_on_miss, "type", None) in {
                "MESH", "EMPTY", "CURVE",
            }
        )
    )
    if (not picked_is_valid_plant_target and
            fallback_is_valid_plant_target):
        picked = keep_candidate_on_miss
    expected = []
    if picked is not None:
        expected.append(picked)
        is_paint_system = _secret_paint_q_is_paint_system(picked)
        if is_paint_system:
            brush_object = _secret_paint_q_single_system_brush_object(picked)
            if brush_object is not None:
                expected.append(brush_object)
    outline_changed = False
    current_selected = list(context.selected_objects)
    for obj in current_selected:
        if obj not in expected:
            obj.select_set(False)
            outline_changed = True
    for obj in expected:
        if not obj.select_get():
            obj.select_set(True)
            outline_changed = True
    if active_to_preserve is not None:
        if context.view_layer.objects.active != active_to_preserve:
            context.view_layer.objects.active = active_to_preserve
            outline_changed = True
        if (active_to_preserve not in expected and
                active_to_preserve.select_get()):
            active_to_preserve.select_set(False)
            outline_changed = True
    elif picked is not None and context.view_layer.objects.active != picked:
        context.view_layer.objects.active = picked
        outline_changed = True
    if outline_changed and context.area:
        context.area.tag_redraw()
    return picked
def _secret_paint_q_existing_system(terrain, brush_object):
    """Return a matching system from an expanded biome on this terrain."""
    systems = _secret_paint_q_existing_systems(terrain, brush_object)
    return next(
        (
            system for system in systems
            if not _secret_paint_1731_is_biome_collapsed(
                terrain,
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(system),
                    "Socket_0",
                    1,
                ),
            )
        ),
        None,
    )
def _secret_paint_q_existing_systems(terrain, brush_object):
    """Return all current-terrain systems that use the hovered brush object."""
    if terrain is None or brush_object is None:
        return []
    systems = []
    for child in terrain.children:
        if child.type not in {"CURVE", "CURVES"}:
            continue
        modifier = _secret_paint_1731_paint_modifier(child)
        if modifier is None:
            continue
        existing_brush = _secret_paint_1731_modifier_value(
            modifier, "Input_2", None
        )
        if (existing_brush == brush_object or
                (existing_brush and brush_object and
                 existing_brush.name == brush_object.name)):
            systems.append(child)
            continue
        brush_collection = _secret_paint_1731_modifier_value(
            modifier, "Input_9", None
        )
        if (brush_collection and hasattr(brush_collection, "all_objects") and
                any(obj.name == brush_object.name
                    for obj in brush_collection.all_objects)):
            systems.append(child)
    return systems
def _secret_paint_q_systems_for_brush(brush_object):
    """Return every paint system in the scene that uses this brush object."""
    if brush_object is None:
        return []
    systems = []
    for system in bpy.data.objects:
        if system.type not in {"CURVE", "CURVES"}:
            continue
        modifier = _secret_paint_1731_paint_modifier(system)
        if modifier is None:
            continue
        existing_brush = _secret_paint_1731_modifier_value(
            modifier,
            "Input_2",
            None,
        )
        if existing_brush == brush_object:
            systems.append(system)
            continue
        brush_collection = _secret_paint_1731_modifier_value(
            modifier,
            "Input_9",
            None,
        )
        if (brush_collection and hasattr(brush_collection, "all_objects") and
                any(obj == brush_object for obj in brush_collection.all_objects)):
            systems.append(system)
    return systems
def _secret_paint_q_cached_systems_for_brush(brush_object, cache=None):
    """Cache source-to-system relationships for one Q selection session."""
    if cache is None:
        return _secret_paint_q_systems_for_brush(brush_object)
    source_index = cache.get("source_system_index")
    if source_index is None:
        source_index = {}
        for system in bpy.data.objects:
            if not _secret_paint_q_is_paint_system(system):
                continue
            for source in _secret_paint_q_system_brush_objects(system):
                try:
                    key = source.as_pointer()
                except (AttributeError, ReferenceError):
                    continue
                owners = source_index.setdefault(key, [])
                if system not in owners:
                    owners.append(system)
        source_index = {
            key: tuple(systems) for key, systems in source_index.items()
        }
        cache["source_system_index"] = source_index
    try:
        return source_index.get(brush_object.as_pointer(), ())
    except (AttributeError, ReferenceError):
        return ()
def _secret_paint_q_activate_system(context, system):
    """Remove temporary pair highlighting and leave only system active."""
    for obj in context.selected_objects:
        obj.select_set(False)
    system.select_set(True)
    context.view_layer.objects.active = system
def _secret_paint_q_close_previous_system_mode(context, previous_system):
    """Leave the previous Sculpt Curves system before switching systems."""
    if previous_system is None or context.active_object != previous_system:
        return
    try:
        if context.object and context.object.mode == "SCULPT_CURVES":
            bpy.ops.object.mode_set(mode="OBJECT")
    except (AttributeError, RuntimeError):
        pass
def _secret_paint_q_clear_selection(context, keep_active=None):
    """Clear temporary outlines while optionally keeping the active system."""
    for obj in list(context.selected_objects):
        obj.select_set(False)
    if keep_active is not None:
        keep_active.select_set(True)
        context.view_layer.objects.active = keep_active
def _secret_paint_q_apply_ids(self, context, system):
    """Apply IDs, fully realizing a procedural system after Q confirmation."""
    switch_started = _secret_paint_trace_session(
        "Q brush switch apply IDs",
        object_name=getattr(system, "name", None),
        current_mode=getattr(context.object, "mode", None),
    )
    update_started = time.perf_counter()
    secretpaint_update_modifier_f(
        context,
        upadte_provenance="secret.applypaint",
    )
    _secret_paint_trace_end("Q switch update modifier", update_started)
    paint_modifier = _secret_paint_1731_paint_modifier(system)
    procedural_enabled = bool(
        _secret_paint_1731_modifier_value(
            paint_modifier,
            "Input_69",
            False,
        )
    )
    apply_started = time.perf_counter()
    apply_paint(
        self,
        context,
        activeobj=system,
        objselection=[system],
        applyIDs=not procedural_enabled,
        keep_active_brush=True,
    )
    _secret_paint_trace_end(
        "Q switch apply_paint call",
        apply_started,
        converted_procedural=procedural_enabled,
    )
    _secret_paint_trace_end("Q brush switch apply IDs", switch_started)
def _secret_paint_q_preview_mask_location(
        context,
        event,
        system,
        allow_depth_fallback=True,
):
    """Project the plant-picker cursor onto the hovered system's terrain."""
    terrain = getattr(system, "parent", None)
    if terrain is None or terrain.type != "MESH":
        return None
    _area, region, space_data, coord = _secret_paint_q_view_area_region_space(
        context,
        event,
    )
    if region is None or space_data is None or coord is None:
        return None
    try:
        from bpy_extras import view3d_utils
        region_3d = space_data.region_3d
        ray_origin = view3d_utils.region_2d_to_origin_3d(
            region,
            region_3d,
            coord,
        )
        ray_direction = view3d_utils.region_2d_to_vector_3d(
            region,
            region_3d,
            coord,
        ).normalized()
        evaluated_terrain = terrain.evaluated_get(
            context.evaluated_depsgraph_get()
        )
        matrix_world = evaluated_terrain.matrix_world
        matrix_inverse = matrix_world.inverted_safe()
        local_origin = matrix_inverse @ ray_origin
        local_direction = matrix_inverse.to_3x3() @ ray_direction
        if local_direction.length_squared > 1.0e-12:
            local_direction.normalize()
            hit, location, _normal, _face = evaluated_terrain.ray_cast(
                local_origin,
                local_direction,
            )
            if hit:
                return matrix_world @ location
        if not allow_depth_fallback:
            return None
        return view3d_utils.region_2d_to_location_3d(
            region,
            region_3d,
            coord,
            system.matrix_world.translation,
        )
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return None
def _secret_paint_q_preview_mask_size(context, modifier):
    """Return a cubic preview size five times the system brush object's size."""
    brush_object = _secret_paint_1731_modifier_value(
        modifier,
        "Input_2",
        None,
    )
    if brush_object is None:
        return None
    try:
        evaluated_brush = brush_object.evaluated_get(
            context.evaluated_depsgraph_get()
        )
        dimensions = evaluated_brush.dimensions
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        dimensions = getattr(brush_object, "dimensions", None)
    if dimensions is None:
        return None
    try:
        brush_size = max(abs(float(component)) for component in dimensions)
    except (TypeError, ValueError):
        return None
    return max(brush_size * 5.0, 1.0e-3)
def _secret_paint_q_create_preview_mask(context, system, modifier, location):
    """Create a brand-new mask used only by the plant picker."""
    mask_size = _secret_paint_q_preview_mask_size(context, modifier)
    if mask_size is None or location is None:
        return None
    try:
        mesh = bpy.data.meshes.new("Secret Paint Q Preview Mask")
        half = 0.5
        vertices = (
            (-half, -half, -half), (half, -half, -half),
            (half, half, -half), (-half, half, -half),
            (-half, -half, half), (half, -half, half),
            (half, half, half), (-half, half, half),
        )
        faces = (
            (0, 1, 2, 3), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 7, 4), (1, 2, 6, 5),
        )
        mesh.from_pydata(vertices, (), faces)
        mask_object = bpy.data.objects.new(
            "Secret Paint Viewport Mask Q Preview",
            mesh,
        )
        mask_object["_secret_paint_q_preview_mask"] = True
        collection = next(iter(getattr(system, "users_collection", ())), None)
        if collection is None:
            terrain = getattr(system, "parent", None)
            collection = next(
                iter(getattr(terrain, "users_collection", ())),
                context.scene.collection,
            )
        collection.objects.link(mask_object)
        mask_object.location = location
        mask_object.scale = (mask_size, mask_size, mask_size)
        mask_object.display_type = 'WIRE'
        mask_object.hide_select = True
        mask_object.hide_render = True
        mask_object.visible_camera = False
        mask_object.visible_diffuse = False
        mask_object.visible_glossy = False
        mask_object.visible_transmission = False
        mask_object.visible_volume_scatter = False
        mask_object.visible_shadow = False
        return mask_object
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        try:
            if 'mask_object' in locals() and mask_object is not None:
                bpy.data.objects.remove(mask_object, do_unlink=True)
            if 'mesh' in locals() and mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        except (AttributeError, ReferenceError, RuntimeError):
            pass
        return None
def _secret_paint_q_restore_preview_mask(operator):
    """Restore the exact mask state replaced by the plant-picker preview."""
    state = getattr(operator, "_q_mask_preview", None)
    operator._q_mask_preview = None
    if not state:
        return
    system = state.get("system")
    modifier = state.get("modifier")
    brush_object = state.get("brush_object")
    mask_object = state.get("mask_object")
    mask_mesh = getattr(mask_object, "data", None)
    try:
        if system is not None:
            original_system_display = state.get("original_system_display")
            if original_system_display is not None:
                system.display_type = original_system_display
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass
    try:
        if brush_object is not None:
            original_brush_display = state.get("original_brush_display")
            if original_brush_display is not None:
                brush_object.display_type = original_brush_display
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass
    try:
        if system is not None:
            system.location = system.location
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass
    try:
        if modifier is not None:
            original_enabled = state.get("original_enabled", False)
            original_mask = state.get("original_mask")
            if original_enabled:
                _secret_paint_1731_set_modifier_value(
                    modifier,
                    "Input_97",
                    original_mask,
                )
                _secret_paint_1731_set_modifier_value(
                    modifier,
                    "Input_98",
                    True,
                )
            else:
                _secret_paint_1731_set_modifier_value(
                    modifier,
                    "Input_98",
                    False,
                )
                _secret_paint_1731_set_modifier_value(
                    modifier,
                    "Input_97",
                    original_mask,
                )
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass
    try:
        if mask_object is not None and mask_object.name in bpy.data.objects:
            bpy.data.objects.remove(mask_object, do_unlink=True)
        if mask_mesh is not None and mask_mesh.users == 0:
            bpy.data.meshes.remove(mask_mesh)
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        pass
def _secret_paint_q_sync_preview_mask(operator, context, event, candidate):
    """Move, replace, or clear the bounded-system preview under the cursor."""
    state = getattr(operator, "_q_mask_preview", None)
    state_system = state.get("system") if state else None
    if candidate == state_system:
        preview_system = state_system
    else:
        preview_system = candidate if (
            _secret_paint_q_is_paint_system(candidate)
            and _secret_paint_q_system_or_brush_uses_bounds(candidate)
        ) else None
    if state and state.get("system") != preview_system:
        _secret_paint_q_restore_preview_mask(operator)
        state = None
    if preview_system is None:
        return
    location = _secret_paint_q_preview_mask_location(
        context,
        event,
        preview_system,
    )
    if location is None:
        return
    if state:
        mask_object = state.get("mask_object")
        try:
            if mask_object is not None:
                mask_object.location = location
                if context.area is not None:
                    context.area.tag_redraw()
        except (AttributeError, ReferenceError, RuntimeError):
            _secret_paint_q_restore_preview_mask(operator)
        return
    modifier = _secret_paint_1731_paint_modifier(preview_system)
    if modifier is None:
        return
    original_enabled = _secret_paint_1731_modifier_value(
        modifier,
        "Input_98",
        False,
    )
    original_mask = _secret_paint_1731_modifier_value(
        modifier,
        "Input_97",
        None,
    )
    brush_object = _secret_paint_1731_modifier_value(
        modifier,
        "Input_2",
        None,
    )
    original_system_display = getattr(
        preview_system,
        "display_type",
        None,
    )
    original_brush_display = getattr(
        brush_object,
        "display_type",
        None,
    ) if brush_object is not None else None
    mask_object = _secret_paint_q_create_preview_mask(
        context,
        preview_system,
        modifier,
        location,
    )
    if mask_object is None:
        return
    operator._q_mask_preview = {
        "system": preview_system,
        "modifier": modifier,
        "original_enabled": original_enabled,
        "original_mask": original_mask,
        "brush_object": brush_object,
        "original_system_display": original_system_display,
        "original_brush_display": original_brush_display,
        "mask_object": mask_object,
    }
    try:
        _secret_paint_1731_set_modifier_value(
            modifier,
            "Input_97",
            mask_object,
        )
        _secret_paint_1731_set_modifier_value(modifier, "Input_98", True)
        preview_system.location = preview_system.location
        if (brush_object is not None and
                getattr(brush_object, "display_type", "SOLID") == "BOUNDS"):
            brush_object.display_type = 'SOLID'
        preview_system.display_type = 'SOLID'
        if context.area is not None:
            context.area.tag_redraw()
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        _secret_paint_q_restore_preview_mask(operator)
def _secret_paint_q_create_system(
        self,
        context,
        terrain,
        brush_object,
        destination_biome=None,
):
    """Create a new plant system without leaving Sculpt Curves mode."""
    if terrain is None or brush_object is None or not terrain.users_collection:
        return None
    layer_collection = recurLayerCollection(
        context.view_layer.layer_collection,
        terrain.users_collection[0].name,
    )
    if layer_collection is None:
        return None
    Check_if_trigger_UV_Reprojection(
        self,
        context,
        activeobj=terrain,
        objselection=[terrain],
    )
    hair_curves = secretpaint_create_curve(
        self,
        context,
        targetOBJ=terrain,
        brushOBJ=brush_object,
        targetCollection=layer_collection,
        transfer_modifier=False,
    )
    hair_modifier = _secret_paint_1731_paint_modifier(hair_curves)
    if hair_modifier is None:
        return None
    if destination_biome is None:
        destination_biome = _secret_paint_1731_first_expanded_biome(terrain)
    _secret_paint_1731_set_modifier_value(
        hair_modifier, "Socket_0", destination_biome
    )
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", brush_object)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_16", 5)
    _secret_paint_1731_set_modifier_component(hair_modifier, "Input_6", 2, 20)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_15", 0.25)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_82", 1.04)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_62", 0.5)
    input_68 = float(_secret_paint_1731_modifier_value(hair_modifier, "Input_68", 0) or 0)
    _secret_paint_1731_set_modifier_value(
        hair_modifier,
        "Input_60",
        0.15 * (input_68 ** 0.5),
    )
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", False)
    for obj in context.selected_objects:
        obj.select_set(False)
    hair_curves.select_set(True)
    context.view_layer.objects.active = hair_curves
    context3sculptbrush(context, activeobj=hair_curves)
    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_99", False)
    _secret_paint_1731_clear_panel_cache("create_in_expanded_biome")
    return hair_curves
def _secret_paint_q_hold_delay(context):
    """Return the shortcut hold delay in seconds."""
    try:
        preferences = context.preferences.addons[__package__].preferences
        milliseconds = preferences.plant_selection_hold_ms
    except (AttributeError, KeyError, TypeError):
        milliseconds = 200
    return max(0, int(milliseconds)) / 1000.0
def _secret_paint_q_sculpt_system(context, preferred=None):
    """Resolve the paint system after Object Mode has deselected it."""
    candidates = [
        getattr(context, "object", None),
        getattr(context, "active_object", None),
        preferred,
    ]
    try:
        candidates.extend(
            obj for obj in context.scene.objects
            if getattr(obj, "mode", "") == "SCULPT_CURVES"
        )
    except (AttributeError, ReferenceError, RuntimeError):
        pass
    for candidate in candidates:
        if (candidate is not None and candidate.type == "CURVES" and
                candidate.parent is not None and
                candidate.parent.type == "MESH" and
                getattr(candidate, "mode", "") == "SCULPT_CURVES" and
                _secret_paint_1731_paint_modifier(candidate) is not None):
            return candidate
    return None
def _secret_paint_q_stop_hold_timer(self, context):
    timer = getattr(self, "_q_hold_timer", None)
    if timer is not None:
        try:
            context.window_manager.event_timer_remove(timer)
        except (AttributeError, RuntimeError):
            pass
    self._q_hold_timer = None
    self._q_hold_waiting = False
class _SecretPaintQMouseEvent:
    __slots__ = ("mouse_x", "mouse_y")

    def __init__(self, mouse_position):
        self.mouse_x, self.mouse_y = mouse_position
def _secret_paint_q_stop_hover_timer(self, context):
    timer = getattr(self, "_q_hover_timer", None)
    if timer is not None:
        try:
            context.window_manager.event_timer_remove(timer)
        except (AttributeError, RuntimeError):
            pass
    self._q_hover_timer = None
    self._q_pending_hover_mouse = None
def _secret_paint_q_update_plant_hover(self, context, event, force=False):
    """Resolve only the newest queued cursor position for the plant picker."""
    if not context.area or context.area.type != 'VIEW_3D':
        return
    mouse_position = (
        getattr(event, "mouse_x", None),
        getattr(event, "mouse_y", None),
    )
    if None in mouse_position:
        return
    if not force and mouse_position == self._q_last_hover_mouse:
        return
    self._q_last_hover_mouse = mouse_position
    picked = _secret_paint_q_pick_object(
        context,
        event,
        self._q_terrain,
        preserve_active=self._q_original_curve,
        system_cache=self._q_system_cache,
        include_bounds_systems=True,
        ignored_objects=self._q_ignored_terrains,
        keep_candidate_on_miss=self._q_candidate,
    )
    self._q_exact_pick_ready = True
    if _secret_paint_q_is_paint_system(picked):
        self._q_ignored_terrains.add(picked.parent)
    self._q_candidate = picked
    _secret_paint_q_sync_preview_mask(
        self,
        context,
        event,
        self._q_candidate,
    )
def _secret_paint_q_begin_plant_selection(
        self,
        context,
        event,
        active,
        shortcut_type=None,
):
    """Configure an existing operator instance as the plant picker."""
    global _secret_paint_q_prompt, _secret_paint_q_prompt_text
    valid_active = (
        active and active.type == "CURVES" and active.parent and
        active.parent.type == "MESH" and
        getattr(active, "mode", "") == "SCULPT_CURVES"
    )
    if not valid_active:
        return False
    self._q_shortcut_type = shortcut_type or event.type
    self._q_original_curve = active
    self._q_terrain = active.parent
    self._q_candidate = None
    self._q_system_cache = {}
    self._q_mask_preview = None
    self._q_ignored_terrains = set()
    self._q_last_hover_mouse = None
    self._q_pending_hover_mouse = None
    self._q_view_navigating = False
    self._q_navigation_button = None
    self._q_exact_pick_ready = False
    self._q_from_button = (
        getattr(context.region, "type", "WINDOW") != "WINDOW"
    )
    self._q_started_at = time.perf_counter()
    _secret_paint_q_frozen_bounded_systems(context, self._q_system_cache)
    self._q_draw_handler = _secret_paint_q_add_prompt_handler(context)
    _secret_paint_q_prompt = True
    _secret_paint_q_prompt_text = "Choose a plant to paint with"
    for obj in context.selected_objects:
        obj.select_set(False)
    active.select_set(True)
    context.view_layer.objects.active = active
    _secret_paint_q_begin_selection_mode(
        "PLANT", "Choose a plant to paint with"
    )
    self._q_overlay_states = _secret_paint_q_enable_selection_overlays(context)
    self._q_last_hover_mouse = (
        getattr(event, "mouse_x", None),
        getattr(event, "mouse_y", None),
    )
    self._q_candidate = _secret_paint_q_pick_object(
        context,
        event,
        self._q_terrain,
        preserve_active=self._q_original_curve,
        system_cache=self._q_system_cache,
        include_bounds_systems=True,
        exact_instance_targeting=False,
        ignored_objects=self._q_ignored_terrains,
    )
    if _secret_paint_q_is_paint_system(self._q_candidate):
        self._q_ignored_terrains.add(self._q_candidate.parent)
    try:
        self._q_hover_timer = context.window_manager.event_timer_add(
            1.0 / 45.0,
            window=context.window,
        )
    except (AttributeError, RuntimeError):
        self._q_hover_timer = None
    context.area.tag_redraw()
    return True
class orenscatter(bpy.types.Operator):
    """Select an object and a target, paint. Also works from the Asset Browser. Also Converts procedural generation into manual hair"""
    bl_idname = "secret.paint"
    bl_label = "Paint"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        global _secret_paint_q_prompt, _secret_paint_q_prompt_text
        active = context.active_object
        selected = list(context.selected_objects)
        if (
                context.mode == "OBJECT"
                and active is not None
                and len(selected) == 1
                and _secret_paint_1731_paint_modifier(active) is None
        ):
            self._q_object_brush = active
            self._q_candidate = None
            self._q_view_navigating = False
            self._q_navigation_button = None
            self._q_shortcut_type = event.type
            self._q_from_button = getattr(context.region, "type", "WINDOW") != "WINDOW"
            self._q_draw_handler = _secret_paint_q_add_prompt_handler(context)
            _secret_paint_q_prompt = True
            _secret_paint_q_begin_selection_mode(
                "TERRAIN", "Choose a terrain to paint on top of"
            )
            self._q_overlay_states = _secret_paint_q_enable_selection_overlays(
                context
            )
            _secret_paint_q_clear_selection(context)
            self._q_candidate = _secret_paint_q_pick_terrain(
                context,
                event,
                self._q_object_brush,
            )
            _secret_paint_q_clear_selection(context)
            if self._q_candidate is not None:
                self._q_candidate.select_set(True)
            context.view_layer.objects.active = self._q_object_brush
            context.window_manager.modal_handler_add(self)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if (active and active.type == "CURVES" and active.parent and
                active.parent.type == "MESH" and context.object.mode == "SCULPT_CURVES"):
            _secret_paint_q_begin_plant_selection(
                self, context, event, active, shortcut_type=event.type
            )
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        shortcut_type = event.type
        shortcut_started_at = time.perf_counter()
        from_button = getattr(context.region, "type", "WINDOW") != "WINDOW"
        secretpaint_function(self, context, event)
        active = _secret_paint_q_sculpt_system(context, preferred=active)
        entered_paint_mode = (
            not from_button and active is not None
        )
        if not entered_paint_mode:
            return {'FINISHED'}
        hold_delay = _secret_paint_q_hold_delay(context)
        if (hold_delay == 0 or
                time.perf_counter() - shortcut_started_at >= hold_delay):
            if _secret_paint_q_begin_plant_selection(
                    self,
                    context,
                    event,
                    active,
                    shortcut_type=shortcut_type,
            ):
                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}
            return {'FINISHED'}
        self._q_shortcut_type = shortcut_type
        self._q_hold_started_at = shortcut_started_at
        self._q_hold_delay = hold_delay
        self._q_hold_waiting = True
        self._q_hold_timer = context.window_manager.event_timer_add(
            0.01,
            window=context.window,
        )
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        global _secret_paint_q_prompt, _secret_paint_q_prompt_text
        if getattr(self, "_q_hold_waiting", False):
            shortcut_type = getattr(self, "_q_shortcut_type", None)
            if event.type == shortcut_type and event.value == 'RELEASE':
                _secret_paint_q_stop_hold_timer(self, context)
                return {'FINISHED'}
            if event.type in {'ESC', 'RIGHTMOUSE'}:
                _secret_paint_q_stop_hold_timer(self, context)
                return {'FINISHED'}
            if (time.perf_counter() - self._q_hold_started_at >=
                    self._q_hold_delay):
                _secret_paint_q_stop_hold_timer(self, context)
                active = _secret_paint_q_sculpt_system(context)
                if _secret_paint_q_begin_plant_selection(
                        self,
                        context,
                        event,
                        active,
                        shortcut_type=shortcut_type,
                ):
                    return {'RUNNING_MODAL'}
                return {'FINISHED'}
            if event.type == shortcut_type:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}
        if hasattr(self, "_q_object_brush"):
            modified_left = (
                event.type == 'LEFTMOUSE' and
                any((event.alt, event.ctrl, event.shift, event.oskey))
            )
            navigation_mouse = (
                event.type in {'MIDDLEMOUSE', 'RIGHTMOUSE'} or
                modified_left or
                event.type == getattr(self, "_q_navigation_button", None)
            )
            if navigation_mouse or modified_left:
                if event.value == 'PRESS':
                    self._q_view_navigating = True
                    self._q_navigation_button = event.type
                    _secret_paint_q_clear_selection(context)
                elif event.value == 'RELEASE':
                    self._q_view_navigating = False
                    self._q_navigation_button = None
                    if context.area and context.area.type == 'VIEW_3D':
                        picked = _secret_paint_q_pick_terrain(
                            context, event, self._q_object_brush
                        )
                        _secret_paint_q_clear_selection(context)
                        self._q_candidate = picked
                        if picked is not None:
                            picked.select_set(True)
                        context.view_layer.objects.active = self._q_object_brush
                        context.area.tag_redraw()
                return {'PASS_THROUGH'}
            if getattr(self, "_q_view_navigating", False):
                return {'PASS_THROUGH'}
            if event.type == 'MOUSEMOVE' or event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                if context.area and context.area.type == 'VIEW_3D':
                    picked = _secret_paint_q_pick_terrain(
                        context, event, self._q_object_brush
                    )
                    _secret_paint_q_clear_selection(context)
                    self._q_candidate = picked
                    if picked is not None:
                        picked.select_set(True)
                    context.view_layer.objects.active = self._q_object_brush
                if event.type == 'MOUSEMOVE':
                    return {'PASS_THROUGH'}
                if self._q_candidate is None:
                    return {'RUNNING_MODAL'}
                brush = self._q_object_brush
                terrain = self._q_candidate
                _secret_paint_q_prompt = False
                _secret_paint_q_end_selection_mode()
                _secret_paint_q_restore_selection_overlays(
                    getattr(self, '_q_overlay_states', None)
                )
                if getattr(self, '_q_draw_handler', None):
                    bpy.types.SpaceView3D.draw_handler_remove(self._q_draw_handler, 'WINDOW')
                    self._q_draw_handler = None
                existing_system = _secret_paint_q_existing_system(terrain, brush)
                _secret_paint_q_clear_selection(context)
                if existing_system:
                    _secret_paint_q_activate_system(context, existing_system)
                    _secret_paint_q_apply_ids(self, context, existing_system)
                else:
                    _secret_paint_q_create_system(
                        self,
                        context,
                        terrain,
                        brush,
                        destination_biome=(
                            _secret_paint_1731_first_expanded_biome(terrain)
                        ),
                    )
                stroke_ready = _secret_paint_q_sculpt_system(context) is not None
                _secret_paint_q_clear_selection(context)
                context.area.tag_redraw()
                if stroke_ready:
                    return {'FINISHED', 'PASS_THROUGH'}
                return {'FINISHED'}
            if event.type == 'ESC':
                _secret_paint_q_prompt = False
                _secret_paint_q_end_selection_mode()
                _secret_paint_q_restore_selection_overlays(
                    getattr(self, '_q_overlay_states', None)
                )
                if getattr(self, '_q_draw_handler', None):
                    bpy.types.SpaceView3D.draw_handler_remove(self._q_draw_handler, 'WINDOW')
                    self._q_draw_handler = None
                _secret_paint_q_clear_selection(context)
                context.area.tag_redraw()
                return {'CANCELLED'}
            if event.type == getattr(self, "_q_shortcut_type", None):
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}
        if hasattr(self, "_q_terrain"):
            button_confirm = (
                getattr(self, "_q_from_button", False) and
                event.type == 'LEFTMOUSE' and event.value == 'PRESS'
            )
            modified_left = (
                event.type == 'LEFTMOUSE' and
                any((event.alt, event.ctrl, event.shift, event.oskey))
            )
            navigation_mouse = (
                event.type == 'MIDDLEMOUSE' or
                modified_left or
                event.type == getattr(self, "_q_navigation_button", None)
            )
            if navigation_mouse:
                if event.value == 'PRESS':
                    self._q_view_navigating = True
                    self._q_navigation_button = event.type
                    self._q_pending_hover_mouse = None
                elif event.value == 'RELEASE':
                    self._q_view_navigating = False
                    self._q_navigation_button = None
                    self._q_pending_hover_mouse = (
                        getattr(event, "mouse_x", None),
                        getattr(event, "mouse_y", None),
                    )
                return {'PASS_THROUGH'}
            if getattr(self, "_q_view_navigating", False):
                return {'PASS_THROUGH'}
            if event.type == 'MOUSEMOVE':
                self._q_pending_hover_mouse = (
                    getattr(event, "mouse_x", None),
                    getattr(event, "mouse_y", None),
                )
                return {'PASS_THROUGH'}
            if (event.type == 'TIMER' and
                    getattr(self, "_q_hover_timer", None) is not None):
                pending_mouse = self._q_pending_hover_mouse
                self._q_pending_hover_mouse = None
                if pending_mouse is not None and None not in pending_mouse:
                    _secret_paint_q_update_plant_hover(
                        self,
                        context,
                        _SecretPaintQMouseEvent(pending_mouse),
                    )
                return {'PASS_THROUGH'}
            shortcut_type = getattr(self, '_q_shortcut_type', None)
            q_pressed_again = (
                event.type == shortcut_type and event.value == 'PRESS' and
                not getattr(event, 'is_repeat', False) and
                time.perf_counter() - getattr(self, '_q_started_at', 0) > 0.15
            )
            if ((event.type == shortcut_type and (event.value == 'RELEASE' or q_pressed_again))
                    or button_confirm):
                pending_mouse = (
                    getattr(event, "mouse_x", None),
                    getattr(event, "mouse_y", None),
                )
                if pending_mouse is None or None in pending_mouse:
                    pending_mouse = self._q_pending_hover_mouse
                if pending_mouse is not None and None not in pending_mouse:
                    _secret_paint_q_update_plant_hover(
                        self,
                        context,
                        _SecretPaintQMouseEvent(pending_mouse),
                        force=True,
                    )
                _secret_paint_q_stop_hover_timer(self, context)
                if (not getattr(self, "_q_exact_pick_ready", False) and
                        context.area and context.area.type == 'VIEW_3D'):
                    self._q_candidate = _secret_paint_q_pick_object(
                        context,
                        event,
                        self._q_terrain,
                        preserve_active=self._q_original_curve,
                        system_cache=self._q_system_cache,
                        include_bounds_systems=True,
                        ignored_objects=self._q_ignored_terrains,
                        keep_candidate_on_miss=self._q_candidate,
                    )
                    if _secret_paint_q_is_paint_system(self._q_candidate):
                        self._q_ignored_terrains.add(self._q_candidate.parent)
                    self._q_exact_pick_ready = True
                _secret_paint_q_restore_preview_mask(self)
                _secret_paint_q_prompt = False
                _secret_paint_q_end_selection_mode()
                _secret_paint_q_restore_selection_overlays(
                    getattr(self, '_q_overlay_states', None)
                )
                if getattr(self, '_q_draw_handler', None):
                    bpy.types.SpaceView3D.draw_handler_remove(self._q_draw_handler, 'WINDOW')
                    self._q_draw_handler = None
                candidate = self._q_candidate
                if candidate is None:
                    candidate = next(
                        (obj for obj in context.selected_objects
                         if obj not in {self._q_terrain, self._q_original_curve}),
                        None,
                    )
                self._q_system_cache.clear()
                terrain = self._q_terrain
                original_curve = self._q_original_curve
                if candidate == terrain or candidate == original_curve or candidate is None:
                    _secret_paint_q_clear_selection(context)
                    context.area.tag_redraw()
                    return {'FINISHED'}
                is_paint_system = (
                    candidate.type in {"CURVE", "CURVES"} and
                    candidate.parent is not None and
                    candidate.parent.type == "MESH" and
                    _secret_paint_1731_paint_modifier(candidate) is not None
                )
                _secret_paint_q_close_previous_system_mode(
                    context,
                    original_curve,
                )
                for obj in context.selected_objects:
                    obj.select_set(False)
                if is_paint_system:
                    _secret_paint_q_activate_system(context, candidate)
                    _secret_paint_q_apply_ids(self, context, candidate)
                elif candidate.type in {"MESH", "EMPTY", "CURVE"}:
                    existing_system = _secret_paint_q_existing_system(
                        terrain, candidate
                    )
                    if existing_system:
                        _secret_paint_q_activate_system(context, existing_system)
                        _secret_paint_q_apply_ids(self, context, existing_system)
                    else:
                        _secret_paint_q_create_system(
                            self,
                            context,
                            terrain,
                            candidate,
                        )
                else:
                    _secret_paint_q_clear_selection(context)
                _secret_paint_q_clear_selection(context)
                context.area.tag_redraw()
                return {'FINISHED'}
            if event.type in {'ESC', 'RIGHTMOUSE'}:
                _secret_paint_q_stop_hover_timer(self, context)
                _secret_paint_q_restore_preview_mask(self)
                _secret_paint_q_prompt = False
                _secret_paint_q_end_selection_mode()
                _secret_paint_q_restore_selection_overlays(
                    getattr(self, '_q_overlay_states', None)
                )
                if getattr(self, '_q_draw_handler', None):
                    bpy.types.SpaceView3D.draw_handler_remove(self._q_draw_handler, 'WINDOW')
                    self._q_draw_handler = None
                for obj in context.selected_objects:
                    obj.select_set(False)
                self._q_system_cache.clear()
                _secret_paint_q_clear_selection(context)
                return {'CANCELLED'}
            if event.type == getattr(self, "_q_shortcut_type", None):
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}
        secretpaint_function(self, context, event)
        return {'FINISHED'}
    def cancel(self, context):
        _secret_paint_q_stop_hold_timer(self, context)
        _secret_paint_q_stop_hover_timer(self, context)
        _secret_paint_q_restore_preview_mask(self)
def _secret_paint_q_pick_terrain(
        context,
        event,
        current_terrain,
        preserve_active=None,
        system_cache=None,
):
    """Use the plant picker and resolve a paint-system hit to its terrain."""
    picked = _secret_paint_q_pick_object(
        context,
        event,
        current_terrain,
        preserve_active=preserve_active,
        system_cache=system_cache,
        exact_instance_targeting=False,
    )
    if _secret_paint_q_is_paint_system(picked):
        target_terrain = picked.parent
    elif (picked is not None and picked.type == "MESH" and
            not picked.name.startswith("Secret Paint Viewport Mask")):
        target_terrain = picked
    else:
        target_terrain = None
    if target_terrain == current_terrain:
        return None
    return target_terrain
def _secret_paint_q_system_has_no_hair(system):
    """Return whether a paint system contains no stored manual curves."""
    data = getattr(system, "data", None)
    if data is None:
        return False
    if system.type == "CURVES":
        try:
            return len(data.curves) == 0
        except (AttributeError, TypeError):
            return False
    if system.type == "CURVE":
        try:
            return all(
                len(spline.points) == 0 and len(spline.bezier_points) == 0
                for spline in data.splines
            )
        except (AttributeError, TypeError):
            return False
    return False
def _secret_paint_q_cleanup_previous_terrain(terrain):
    """Delete empty manual paint systems left on the previous terrain."""
    if terrain is None:
        return 0
    empty_systems = []
    for system in list(terrain.children):
        modifier = _secret_paint_1731_paint_modifier(system)
        if modifier is None:
            continue
        procedural_enabled = _secret_paint_1731_modifier_value(
            modifier, "Input_69", None
        )
        if procedural_enabled is None or bool(procedural_enabled):
            continue
        if _secret_paint_q_system_has_no_hair(system):
            empty_systems.append(system)
    for system in empty_systems:
        bpy.data.objects.remove(system, do_unlink=True)
    if empty_systems:
        _secret_paint_1731_clear_panel_cache("terrain_switch_cleanup")
    return len(empty_systems)
def _secret_paint_q_transfer_to_terrain(self, context, source_system, target_terrain):
    """Run the Object Mode Q transfer for the confirmed system and terrain."""
    if (not source_system or not target_terrain or
            target_terrain.type != "MESH" or
            source_system.parent == target_terrain):
        return source_system
    source_modifier = _secret_paint_1731_paint_modifier(source_system)
    if source_modifier is None:
        return None
    brush_object = _secret_paint_1731_modifier_value(
        source_modifier, "Input_2", None
    )
    existing_systems = _secret_paint_q_existing_systems(
        target_terrain, brush_object
    ) if brush_object is not None else []
    existing_system = next(
        (
            system for system in existing_systems
            if not _secret_paint_1731_is_biome_collapsed(
                target_terrain,
                _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(system),
                    "Socket_0",
                    1,
                ),
            )
        ),
        None,
    )
    if existing_system is not None:
        try:
            for obj in list(context.selected_objects):
                obj.select_set(False)
            source_system.select_set(True)
            context.view_layer.objects.active = source_system
            _secret_paint_q_close_previous_system_mode(context, source_system)
            _secret_paint_q_activate_system(context, existing_system)
            _secret_paint_q_apply_ids(self, context, existing_system)
            _secret_paint_q_activate_system(context, existing_system)
            _secret_paint_q_clear_selection(context)
            return existing_system
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            self.report({'WARNING'}, f"Could not activate paint system: {error}")
            return None
    destination_biome = _secret_paint_1731_first_expanded_biome(
        target_terrain
    )
    systems_before = {
        child
        for child in target_terrain.children
        if _secret_paint_1731_paint_modifier(child) is not None
    }
    try:
        for obj in list(context.selected_objects):
            obj.select_set(False)
        source_system.select_set(True)
        context.view_layer.objects.active = source_system
        _secret_paint_q_close_previous_system_mode(context, source_system)
        source_system.select_set(True)
        target_terrain.select_set(True)
        context.view_layer.objects.active = target_terrain
        secretpaint_function(
            self,
            context,
            activeobj=target_terrain,
            objselection=[source_system, target_terrain],
        )
    except (AttributeError, RuntimeError, TypeError, ValueError) as error:
        self.report({'WARNING'}, f"Could not transfer paint system: {error}")
        return None
    transferred = context.view_layer.objects.active
    if not (
            transferred is not None and
            transferred not in systems_before and
            transferred.parent == target_terrain and
            _secret_paint_1731_paint_modifier(transferred) is not None):
        transferred = next(
            (
                child for child in reversed(list(target_terrain.children))
                if child not in systems_before and
                _secret_paint_1731_paint_modifier(child) is not None
            ),
            None,
        )
    if transferred is None:
        self.report({'WARNING'}, "The paint system was not transferred")
        return None
    transferred_modifier = _secret_paint_1731_paint_modifier(transferred)
    _secret_paint_1731_set_modifier_value(
        transferred_modifier,
        "Socket_0",
        destination_biome,
    )
    transferred.location = transferred.location
    _secret_paint_1731_clear_panel_cache("terrain_transfer")
    try:
        _secret_paint_q_activate_system(context, transferred)
        if _secret_paint_1731_modifier_value(
                transferred_modifier, "Input_69", False
        ):
            _secret_paint_q_apply_ids(self, context, transferred)
        elif not (context.object and context.object.mode == "SCULPT_CURVES"):
            context3sculptbrush(
                context,
                activeobj=transferred,
                keep_active_brush=True,
            )
    except (AttributeError, RuntimeError, TypeError, ValueError) as error:
        self.report({'WARNING'}, f"Could not enter manual painting: {error}")
        return None
    _secret_paint_q_clear_selection(context)
    return transferred
class paint_change_terrain(bpy.types.Operator):
    """Choose a new terrain while painting and transfer the active system."""
    bl_idname = "secret.paint_change_terrain"
    bl_label = "Change Terrain"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        global _secret_paint_q_prompt, _secret_paint_q_prompt_text
        source_system = context.active_object
        if not (source_system and source_system.type in {"CURVE", "CURVES"} and
                source_system.parent and source_system.parent.type == "MESH" and
                _secret_paint_1731_paint_modifier(source_system) is not None and
                context.object.mode == "SCULPT_CURVES"):
            return {'CANCELLED'}
        self._terrain_source_system = source_system
        self._terrain_current = source_system.parent
        self._terrain_candidate = None
        self._terrain_system_cache = {}
        self._terrain_shortcut_type = event.type
        self._terrain_from_button = getattr(context.region, "type", "WINDOW") != "WINDOW"
        self._terrain_started_at = time.perf_counter()
        self._terrain_draw_handler = _secret_paint_q_add_prompt_handler(context)
        _secret_paint_q_prompt = True
        _secret_paint_q_begin_selection_mode(
            "TERRAIN", "Choose a terrain to paint on top of"
        )
        self._terrain_overlay_states = _secret_paint_q_enable_selection_overlays(
            context
        )
        _secret_paint_q_clear_selection(context)
        context.view_layer.objects.active = self._terrain_source_system
        self._terrain_candidate = _secret_paint_q_pick_terrain(
            context,
            event,
            self._terrain_current,
            preserve_active=self._terrain_source_system,
            system_cache=self._terrain_system_cache,
        )
        _secret_paint_q_clear_selection(context)
        if self._terrain_candidate is not None:
            self._terrain_candidate.select_set(True)
        context.view_layer.objects.active = self._terrain_source_system
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        global _secret_paint_q_prompt, _secret_paint_q_prompt_text
        button_confirm = (
            getattr(self, "_terrain_from_button", False) and
            event.type == 'LEFTMOUSE' and event.value == 'PRESS'
        )
        if event.type == 'MOUSEMOVE' or (
                event.type == 'LEFTMOUSE' and not getattr(self, "_terrain_from_button", False)):
            if context.area and context.area.type == 'VIEW_3D':
                picked = _secret_paint_q_pick_terrain(
                    context,
                    event,
                    self._terrain_current,
                    preserve_active=self._terrain_source_system,
                    system_cache=self._terrain_system_cache,
                )
                _secret_paint_q_clear_selection(context)
                self._terrain_candidate = picked
                if picked and picked.type == "MESH":
                    picked.select_set(True)
                    context.view_layer.objects.active = self._terrain_source_system
                context.area.tag_redraw()
            if event.type == 'MOUSEMOVE':
                return {'PASS_THROUGH'}
            return {'PASS_THROUGH' if getattr(self, "_terrain_from_button", False) else 'RUNNING_MODAL'}
        shortcut_type = getattr(self, "_terrain_shortcut_type", None)
        shortcut_again = (
            event.type == shortcut_type and event.value == 'PRESS' and
            not getattr(event, 'is_repeat', False) and
            time.perf_counter() - getattr(self, '_terrain_started_at', 0) > 0.15
        )
        if ((event.type == shortcut_type and event.value == 'RELEASE') or
                shortcut_again or button_confirm):
            _secret_paint_q_prompt = False
            _secret_paint_q_end_selection_mode()
            _secret_paint_q_restore_selection_overlays(
                getattr(self, '_terrain_overlay_states', None)
            )
            if getattr(self, '_terrain_draw_handler', None):
                bpy.types.SpaceView3D.draw_handler_remove(self._terrain_draw_handler, 'WINDOW')
                self._terrain_draw_handler = None
            transferred = None
            if (self._terrain_candidate is not None and
                    self._terrain_candidate.type == "MESH" and
                    self._terrain_candidate != self._terrain_current):
                transferred = _secret_paint_q_transfer_to_terrain(
                    self,
                    context,
                    self._terrain_source_system,
                    self._terrain_candidate,
                )
                if transferred is not None:
                    _secret_paint_q_cleanup_previous_terrain(
                        self._terrain_current
                    )
            if transferred is None:
                _secret_paint_q_activate_system(
                    context,
                    self._terrain_source_system,
                )
                try:
                    if context.object.mode != "SCULPT_CURVES":
                        context3sculptbrush(
                            context,
                            activeobj=self._terrain_source_system,
                            keep_active_brush=True,
                        )
                except (AttributeError, RuntimeError):
                    pass
            _secret_paint_q_clear_selection(context)
            context.area.tag_redraw()
            return {'FINISHED'}
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            _secret_paint_q_prompt = False
            _secret_paint_q_end_selection_mode()
            _secret_paint_q_restore_selection_overlays(
                getattr(self, '_terrain_overlay_states', None)
            )
            if getattr(self, '_terrain_draw_handler', None):
                bpy.types.SpaceView3D.draw_handler_remove(self._terrain_draw_handler, 'WINDOW')
                self._terrain_draw_handler = None
            _secret_paint_q_activate_system(
                context,
                self._terrain_source_system,
            )
            _secret_paint_q_clear_selection(context)
            return {'CANCELLED'}
        if event.type == getattr(self, "_terrain_shortcut_type", None):
            return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}
class bezier_mode(bpy.types.Operator):
    """Enter the same Bezier drawing workflow as Q with one object selected."""
    bl_idname = "secret.bezier_mode"
    bl_label = "Bezier Mode"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        active = context.active_object
        active_modifier = _secret_paint_1731_paint_modifier(active)
        is_paint_system = (
            active is not None
            and active.type in {"CURVE", "CURVES"}
            and active.parent is not None
            and active.parent.type == "MESH"
            and active_modifier is not None
        )
        if is_paint_system:
            terrain = active.parent
            bezier_brush = _secret_paint_q_single_system_brush_object(active)
        else:
            bezier_brush = active
            terrain = active
        if terrain is None or bezier_brush is None:
            return {'CANCELLED'}
        for obj in context.selected_objects:
            obj.select_set(False)
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        terrain.select_set(True)
        context.view_layer.objects.active = terrain
        secretpaint_function(
            self,
            context,
            activeobj=terrain,
            objselection=[terrain],
            bezier_brush=bezier_brush,
        )
        return {'FINISHED'}
def paintbrushswitch_f(self, *args, **kwargs):
    context=None
    event=None
    for i in args:
        if type(i).__name__ == "Context": context = i
        elif type(i).__name__ == "Event": event = i
    if "activeobj" in kwargs:ORIGINALactiveobj = kwargs.get("activeobj")
    else:ORIGINALactiveobj = bpy.context.active_object
    if ORIGINALactiveobj == None: ORIGINALactiveobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else: objselection = bpy.context.selected_objects
    if ORIGINALactiveobj not in objselection: objselection.append(ORIGINALactiveobj)
    ORIGINALobjselection= objselection
    if "current_mode" in kwargs:current_mode = kwargs.get("current_mode")
    else: current_mode = bpy.context.object.mode
    if current_mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
    saveactual_objselection = bpy.context.selected_objects
    saveactual_activeobj = bpy.context.active_object
    if current_mode == "WEIGHT_PAINT":
        for hair in ORIGINALactiveobj.children:
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(hair), "Input_83_attribute_name", ""
            ) == ORIGINALactiveobj.vertex_groups.active.name:
                bpy.context.view_layer.objects.active = hair
                hair_thatneeds_to_switch = hair
                break
    else:
        hair_thatneeds_to_switch = ORIGINALactiveobj
    all_selected_are_meshes = True
    for obj in objselection:
        if obj.type != "MESH": all_selected_are_meshes=False
    if len(objselection) == 1 or all_selected_are_meshes:
        bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))
        if bpy.context.active_object.type in ["MESH", "CURVES", "CURVE", "EMPTY"] and bpy.context.active_object != hair_thatneeds_to_switch and bpy.context.active_object != hair_thatneeds_to_switch.parent:
            hoverobj = bpy.context.active_object
            if hoverobj not in objselection: objselection.append(hoverobj)
            bpy.data.objects[hair_thatneeds_to_switch.name].select_set(True)
        else:
            for x in bpy.context.selected_objects: x.select_set(False)
            bpy.context.view_layer.objects.active = ORIGINALactiveobj
            bpy.ops.object.mode_set(mode=current_mode)
            return {'FINISHED'}
    else:
        hoverobj = hair_thatneeds_to_switch
    N_Of_Selected = len(objselection)
    randomselectedobj = []
    randomselected_non_hair = []
    all_objs_are_hair = True
    all_selected_hair = []
    all_selected_non_hair = []
    selected_without_active = []
    all_selected_are_meshes = True
    if N_Of_Selected:
        for obj in objselection:
            if obj.type != "MESH": all_selected_are_meshes=False
            if obj != hoverobj:
                randomselectedobj = obj
                selected_without_active.append(obj)
            if obj.type != "CURVES" and obj.type != "CURVE": randomselected_non_hair = obj
            if obj.type != "CURVES": all_objs_are_hair = False
            if obj.type == "CURVES": all_selected_hair.append(obj)
            if obj.type != "CURVES": all_selected_non_hair.append(obj)
    if all_selected_are_meshes:
        for ob in selected_without_active:
            pass
            ob.select_set(True)
            ob.data = hoverobj.data
            for i, mat_slot in enumerate(hoverobj.material_slots):
                if mat_slot.material:
                    if ob.material_slots and ob.material_slots[i]:
                        ob.material_slots[i].link = mat_slot.link
                        ob.material_slots[i].material = mat_slot.material
                    else: ob.data.materials.append(mat_slot.material)
            for m in ob.modifiers:
                ob.modifiers.remove(m)
            for mod in hoverobj.modifiers:
                mod_copy = ob.modifiers.new(mod.name, mod.type)
                for attr in sorted(dir(mod)):
                    if (attr.startswith("_") or attr in ["bl_rna"]): continue
                    try:
                        if (mod.is_property_readonly(attr)): continue
                    except:
                        continue
                    setattr(mod_copy, attr, getattr(mod, attr))
                try:
                    for key, value in mod.items():
                        mod_copy[key] = value
                except: pass
        hoverobj.select_set(False)
        bpy.context.view_layer.objects.active = ORIGINALactiveobj
        return{'FINISHED'}
    if N_Of_Selected == 2 and randomselectedobj.type == "CURVES" and hoverobj.type != "CURVES" \
            or N_Of_Selected == 2 and randomselectedobj.type == "CURVE" and hoverobj.type != "CURVES":
        pass
        for hair in selected_without_active:
            hair.data.materials.clear()
            for mat_slot in hoverobj.material_slots:
                if mat_slot.material: hair.data.materials.append(mat_slot.material)
            hair_modifier = _secret_paint_1731_paint_modifier(hair)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", hoverobj)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_9", None)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", False)
            bpy.context.active_object.select_set(False)
            for obj in bpy.context.selected_objects: bpy.context.view_layer.objects.active = obj
        for x in bpy.context.selected_objects: x.select_set(False)
        bpy.context.view_layer.objects.active = saveactual_activeobj
        bpy.ops.object.mode_set(mode=current_mode)
    elif N_Of_Selected >= 2 and all_objs_are_hair:
        pass
        for hair in selected_without_active:
            hair.data.materials.clear()
            for mat_slot in hoverobj.material_slots:
                if mat_slot.material: hair.data.materials.append(mat_slot.material)
            hair_modifier = _secret_paint_1731_paint_modifier(hair)
            hover_modifier = _secret_paint_1731_paint_modifier(hoverobj)
            for input_name in ("Input_2", "Input_9", "Input_68", "Input_86", "Input_89", "Input_91", "Input_92"):
                _secret_paint_1731_set_modifier_value(
                    hair_modifier,
                    input_name,
                    _secret_paint_1731_modifier_value(hover_modifier, input_name, None),
                )
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", False)
            hair.location = hair.location
        if N_Of_Selected == 2:
            bpy.context.active_object.select_set(False)
            for obj in bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = obj
    elif N_Of_Selected >= 3:
        pass
        all_materials_from_non_hair_objs = []
        for ob in all_selected_non_hair:
            for mat_slot in ob.material_slots:
                mat = mat_slot.material
                if mat not in all_materials_from_non_hair_objs: all_materials_from_non_hair_objs.append(mat)
        if len(all_selected_non_hair) >= 2:
            ucol = randomselected_non_hair.users_collection
            for i in ucol:
                layer_collection = bpy.context.view_layer.layer_collection
                layerColl = recurLayerCollection(layer_collection, i.name)
            for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
            for hair in all_selected_hair:
                hair.active_material_index = 0
                hair.data.materials.clear()
                for matteriall in all_materials_from_non_hair_objs: hair.data.materials.append(matteriall)
                hair_modifier = _secret_paint_1731_paint_modifier(hair)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", None)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_9", bpy.data.collections[layerColl.name])
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", False)
                bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]
                bpy.ops.object.mode_set(mode=current_mode)
                hair.location = hair.location
        elif len(all_selected_non_hair) == 1:
            for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
            for hair in all_selected_hair:
                hair_modifier = _secret_paint_1731_paint_modifier(hair)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_2", bpy.data.objects[all_selected_non_hair[0].name])
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_9", None)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", False)
                bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]
                bpy.ops.object.mode_set(mode=current_mode)
                hair.active_material_index = 0
                for i in range(len(hair.material_slots)): bpy.ops.object.material_slot_remove({'object': hair})
                for matteriall in all_materials_from_non_hair_objs: hair.data.materials.append(matteriall)
                hair.location = hair.location
class orencurveswitch(bpy.types.Operator):
    """Use the active mesh or collection as Brush for the selected Paint System"""
    bl_idname = "secret.paintbrushswitch"
    bl_label = "Switch"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        paintbrushswitch_f(self, context, event)
        return{'FINISHED'}
def check_overlapping_uvs(self,context,**kwargs):
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    if activeobj.type != 'MESH': return False
    mesh = activeobj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        pass
        return
    face_uv_sets = {}
    overlapping_faces = set()
    for face in bm.faces:
        uv_set = frozenset(tuple(loop[uv_layer].uv) for loop in face.loops)
        if uv_set in face_uv_sets:
            overlapping_faces.add(face.index)
            overlapping_faces.add(face_uv_sets[uv_set])
        else:
            face_uv_sets[uv_set] = face.index
    if overlapping_faces:
        pass
        bm.free()
        return True
    else:
        pass
        bm.free()
        return False
_SECRET_PAINT_UV_TOPOLOGY_KEY = "_secret_paint_uv_topology"


def _secret_paint_mesh_topology_signature(mesh):
    return (
        len(mesh.vertices),
        len(mesh.edges),
        len(mesh.polygons),
        len(mesh.loops),
    )


def _secret_paint_auto_uv_status(surface):
    """Return whether automatic UV repair is necessary and why."""
    mesh = getattr(surface, "data", None)
    if mesh is None or surface.type != "MESH":
        return False, "not a mesh surface"
    if mesh.library:
        return False, "linked mesh data"
    if not len(mesh.loops):
        return False, "surface has no loops"

    uv_layer = mesh.uv_layers.get("Secret Paint UV")
    if uv_layer is None:
        return True, "Secret Paint UV is missing"
    uv_values = getattr(uv_layer, "uv", getattr(uv_layer, "data", None))
    if uv_values is None or len(uv_values) != len(mesh.loops):
        return True, "Secret Paint UV loop count is invalid"

    signature = _secret_paint_mesh_topology_signature(mesh)
    stored_signature = mesh.get(_SECRET_PAINT_UV_TOPOLOGY_KEY)
    if stored_signature is not None:
        if tuple(stored_signature) != signature:
            return True, "surface topology changed"
        return False, "UV and topology signature are current"

    if np is not None:
        coordinates = np.empty(len(uv_values) * 2, dtype=np.float32)
        uv_values.foreach_get("vector", coordinates)
        valid_coordinates = (
            bool(np.isfinite(coordinates).all()) and
            float(np.ptp(coordinates)) > 1e-7
        )
    else:
        from array import array
        coordinates = array('f', [0.0]) * (len(uv_values) * 2)
        uv_values.foreach_get("vector", coordinates)
        valid_coordinates = (
            all(math.isfinite(value) for value in coordinates) and
            max(coordinates) - min(coordinates) > 1e-7
        )
    if not valid_coordinates:
        return True, "Secret Paint UV is empty or degenerate"

    try:
        mesh[_SECRET_PAINT_UV_TOPOLOGY_KEY] = list(signature)
    except (AttributeError, RuntimeError, TypeError):
        pass
    return False, "existing Secret Paint UV accepted and signature initialized"


def _secret_paint_record_uv_topology(surface):
    mesh = getattr(surface, "data", None)
    if mesh is None or mesh.library:
        return
    try:
        mesh[_SECRET_PAINT_UV_TOPOLOGY_KEY] = list(
            _secret_paint_mesh_topology_signature(mesh)
        )
    except (AttributeError, RuntimeError, TypeError):
        pass


def Check_if_trigger_UV_Reprojection(self,context,**kwargs):
    check_started = _secret_paint_trace_begin("Check_if_trigger_UV_Reprojection")
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    objselection = kwargs.get("objselection") if "objselection" in kwargs else bpy.context.selected_objects
    if not isinstance(objselection, (list, tuple)): objselection = [objselection]
    if activeobj not in objselection: objselection.append(activeobj)
    collect_started = time.perf_counter()
    surface_to_reUV = []
    for obj in objselection:
        if obj.type == "CURVES":
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    if obj.parent and obj.parent.type == "MESH":
                        if obj.parent not in surface_to_reUV: surface_to_reUV.append(obj.parent)
        elif obj.type == "MESH":
            if obj not in surface_to_reUV: surface_to_reUV.append(obj)
    _secret_paint_trace_end(
        "collect UV reprojection surfaces", collect_started,
        surfaces=len(surface_to_reUV),
    )
    for terrain in surface_to_reUV:
        triangle_count_started = time.perf_counter()
        triangles = sum(polygon.loop_total // 3 for polygon in terrain.data.polygons)
        threshold = bpy.context.preferences.addons[__package__].preferences.trigger_auto_uvs
        eligible_for_reprojection = threshold > 0 and triangles < threshold
        if eligible_for_reprojection:
            will_reproject, reason = _secret_paint_auto_uv_status(terrain)
        else:
            will_reproject = False
            reason = "automatic UV repair disabled or above triangle threshold"
        _secret_paint_trace_end(
            "count terrain triangles",
            triangle_count_started,
            terrain=terrain.name,
            triangles=triangles,
            threshold=threshold,
            will_reproject=will_reproject,
            reason=reason,
        )
        if will_reproject:
            reproject_started = time.perf_counter()
            reproject_function(self,context,automatically_triggererd=True,activeobj=terrain, objselection=[terrain])
            _secret_paint_record_uv_topology(terrain)
            _secret_paint_trace_end(
                "automatic UV reprojection", reproject_started,
                terrain=terrain.name,
            )
    _secret_paint_trace_end("Check_if_trigger_UV_Reprojection", check_started)
    return{'FINISHED'}
def reproject_function(self,context,**kwargs):
    start_time = time.perf_counter()
    _secret_paint_trace(
        "BEGIN reproject_function",
        requested_object=getattr(kwargs.get("activeobj"), "name", None),
        automatic=bool(kwargs.get("automatically_triggererd", False)),
    )
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    objselection = kwargs.get("objselection") if "objselection" in kwargs else bpy.context.selected_objects
    if not isinstance(objselection, (list, tuple)): objselection = [objselection]
    if activeobj not in objselection: objselection.append(activeobj)
    automatically_triggererd = kwargs.get("automatically_triggererd") if "automatically_triggererd" in kwargs else False
    actualobjselection = bpy.context.selected_objects
    actualactiveobj = bpy.context.active_object
    changed_active_obj_so_restore_is_needed = False
    changed_selected_objs_so_restore_is_needed = False
    current_mode = bpy.context.object.mode
    dyntopo_status = activeobj.use_dynamic_topology_sculpting
    discovery_started = time.perf_counter()
    hairlist = []
    unselected_siblings_list = []
    surface_to_reUV = []
    for obj in objselection:
        if obj.type == "CURVES":
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    if obj not in hairlist: hairlist.append(obj)
                    if obj.parent and obj.parent.type == "MESH":
                        if obj.parent not in surface_to_reUV: surface_to_reUV.append(obj.parent)
                        for child in obj.parent.children:
                            if child.type == "CURVES":
                                for modif in child.modifiers:
                                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                        if child not in hairlist: hairlist.append(child)
                                        if child not in objselection and child not in unselected_siblings_list: unselected_siblings_list.append(child)
        elif obj.type == "MESH":
            if obj not in surface_to_reUV: surface_to_reUV.append(obj)
            for child in obj.children:
                if child.type == "CURVES":
                    for modif in child.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint") and child not in hairlist: hairlist.append(child)
    _secret_paint_trace_end(
        "discover reprojection dependencies",
        discovery_started,
        surfaces=len(surface_to_reUV),
        hair_systems=len(hairlist),
        unselected_siblings=len(unselected_siblings_list),
    )
    if surface_to_reUV:
        for surface in surface_to_reUV:
            surface_started = _secret_paint_trace_begin(
                "reproject surface", surface=surface.name,
                vertices=len(surface.data.vertices),
                polygons=len(surface.data.polygons),
            )
            uv_setup_started = time.perf_counter()
            previously_active_UV = None
            previously_active_UV_rendering = None
            custom_uv = None
            for UV in surface.data.uv_layers:
                if UV.active: previously_active_UV = UV
                if UV.active_render: previously_active_UV_rendering = UV
                if UV.name == "Secret Paint UV": custom_uv = UV
            uv_to_reproject = previously_active_UV_rendering
            if surface.data.library:
                if not automatically_triggererd: self.report({'INFO'}, "Snapped the hair to the closest surface, but couldn't create new UVs since the object's geometry is linked from another .Blend file")
            else:
                if custom_uv == None: custom_uv = surface.data.uv_layers.new(name="Secret Paint UV")
                if custom_uv == None:
                    uv_to_reproject = previously_active_UV_rendering
                else:
                    uv_to_reproject = custom_uv
                changed_active_uv_so_restore_is_needed = False
                if previously_active_UV != uv_to_reproject:
                    uv_to_reproject.active = True
                    changed_active_uv_so_restore_is_needed = True
                _secret_paint_trace_end(
                    "prepare surface UV layer",
                    uv_setup_started,
                    surface=surface.name,
                    uv_layer=getattr(uv_to_reproject, "name", None),
                )
                pass
                projection_started = time.perf_counter()
                try:
                    for window in context.window_manager.windows:
                        screen = window.screen
                        for area in screen.areas:
                            if area.type == 'VIEW_3D':
                                with context.temp_override(window=window, area=area):
                                    for x in actualobjselection: x.select_set(False)
                                    changed_selected_objs_so_restore_is_needed = True
                                    if bpy.context.active_object != surface:
                                        bpy.context.view_layer.objects.active = surface
                                        changed_active_obj_so_restore_is_needed =True
                                    restoremode = bpy.context.object.mode
                                    if restoremode != "EDIT":
                                        edit_mode_started = time.perf_counter()
                                        bpy.ops.object.mode_set(mode="EDIT")
                                        _secret_paint_trace_end(
                                            "UV projection enter Edit mode", edit_mode_started,
                                            surface=surface.name,
                                        )
                                    select_started = time.perf_counter()
                                    bpy.ops.mesh.select_all(action='SELECT')
                                    _secret_paint_trace_end(
                                        "UV projection select all", select_started,
                                        surface=surface.name,
                                    )
                                    smart_project_started = time.perf_counter()
                                    bpy.ops.uv.smart_project(angle_limit=1.20428, island_margin=0.01, area_weight=1, correct_aspect=True, scale_to_bounds=True)
                                    _secret_paint_trace_end(
                                        "bpy.ops.uv.smart_project", smart_project_started,
                                        surface=surface.name,
                                    )
                                    if restoremode != "EDIT":
                                        restore_mode_started = time.perf_counter()
                                        bpy.ops.object.mode_set(mode=restoremode)
                                        _secret_paint_trace_end(
                                            "UV projection restore mode", restore_mode_started,
                                            surface=surface.name, mode=restoremode,
                                        )
                                break
                except: pass
                _secret_paint_trace_end(
                    "surface UV projection context", projection_started,
                    surface=surface.name,
                )
                for UVV in surface.data.uv_layers:
                    if UVV.active_render:
                        UVV.active = True
                        break
            _secret_paint_trace_end("reproject surface", surface_started, surface=surface.name)
    if hairlist:
        hair_uv_started = time.perf_counter()
        for ob in hairlist:
            ob.data.surface = ob.parent
            active_render_UV = None
            custom_uv = None
            for uvmap in ob.data.surface.data.uv_layers:
                if uvmap.name == "Secret Paint UV": custom_uv = uvmap.name
                if uvmap.active_render: active_render_UV = uvmap.name
            if custom_uv:
                ob.data.surface_uv_map = custom_uv
            elif active_render_UV:
                ob.data.surface_uv_map = active_render_UV
        _secret_paint_trace_end(
            "update hair surface UV maps", hair_uv_started,
            hair_systems=len(hairlist),
        )
        if automatically_triggererd:
            _secret_paint_trace(
                "SKIP automatic curve snapping",
                reason="snapping is reserved for the manual Reproject operator",
                hair_systems=len(hairlist),
            )
        else:
            snap_setup_started = time.perf_counter()
            hair_to_snap = [
                ob for ob in hairlist
                if ob not in unselected_siblings_list and
                len(getattr(ob.data, "curves", ())) > 0
            ]
            for selected in list(bpy.context.selected_objects):
                selected.select_set(False)
            changed_selected_objs_so_restore_is_needed = True
            for ob in hair_to_snap:
                for selected in list(bpy.context.selected_objects):
                    selected.select_set(False)
                bpy.context.view_layer.objects.active = ob
                changed_active_obj_so_restore_is_needed = True
                ob.select_set(True)
                snap_started = time.perf_counter()
                bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
                _secret_paint_trace_end(
                    "bpy.ops.curves.snap_curves_to_surface", snap_started,
                    object=ob.name,
                    points=len(ob.data.points), curves=len(ob.data.curves),
                )
            _secret_paint_trace_end(
                "prepare and snap hair systems", snap_setup_started,
                snapped_systems=len(hair_to_snap),
                skipped_empty_or_unselected=len(hairlist) - len(hair_to_snap),
            )
    restore_started = time.perf_counter()
    if not automatically_triggererd:
        if current_mode == "SCULPT_CURVES":
            for ob in hairlist: ob.select_set(False)
        elif current_mode == "SCULPT":
            if dyntopo_status: bpy.ops.sculpt.dynamic_topology_toggle()
            for ob in hairlist: ob.select_set(False)
    else:
        if changed_active_obj_so_restore_is_needed: bpy.context.view_layer.objects.active = actualactiveobj
        if changed_selected_objs_so_restore_is_needed:
            for ob in bpy.context.selected_objects:
                if ob not in actualobjselection: ob.select_set(False)
            for xx in actualobjselection: xx.select_set(True)
    _secret_paint_trace_end("restore reprojection context", restore_started)
    end_time = time.perf_counter()
    _secret_paint_trace_end("reproject_function", start_time)
    pass
    return {'FINISHED'}
class clean_hair_orencurve(bpy.types.Operator):
    """When the terrain has incorrect UVs, for example after sculpting the terrain with dynamic topology, use this to quickly recreate the UVs. This is needed in order to be able to paint manually (geometry node hair limitation; only needed for manual painting, not for the procedural distribution). Also snaps hair to the closest surfaces"""
    bl_idname = "secret.fixdyntopo"
    bl_label = "Reproject"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        reproject_function(self, context)
        return {'FINISHED'}
def context283482(self,context,**kwargs):
    if "coll_target" in kwargs:
        Importing_Into_Active = True
        coll_target = kwargs.get("coll_target")
    else:
        Importing_Into_Active = False
        coll_target = None
    activeobj = bpy.context.active_object
    objs = bpy.context.selected_objects
    if Importing_Into_Active:
        objs.remove(activeobj)
        activeobj.select_set(False)
    orengroupfirst = bpy.context.active_object
    orengroupfirstName = orengroupfirst.name
    C = bpy.context
    active_coll = C.view_layer.active_layer_collection.collection
    if Importing_Into_Active == False:
        coll_target = bpy.data.collections.new(orengroupfirstName)
        active_coll.children.link(coll_target)
    if coll_target and objs:
        for ob in objs:
            for coll in ob.users_collection:
                coll.objects.unlink(ob)
            coll_target.objects.link(ob)
            ob.select_set(True)
    self.report({'INFO'}, "Added to collection of active")
    return {"FINISHED"}
def context283482(self, context, **kwargs):
    importing_into_active = "coll_target" in kwargs
    coll_target = kwargs.get("coll_target")
    activeobj = context.active_object
    if activeobj is None:
        self.report({'WARNING'}, "Select an active object first")
        return {"CANCELLED"}
    objs = list(context.selected_objects)
    if importing_into_active:
        if activeobj in objs:
            objs.remove(activeobj)
        activeobj.select_set(False)
    elif not objs:
        objs = [activeobj]
    if not importing_into_active:
        parent = context.view_layer.active_layer_collection.collection
        coll_target = bpy.data.collections.new(activeobj.name)
        parent.children.link(coll_target)
    if coll_target is None:
        self.report({'WARNING'}, "No target collection")
        return {"CANCELLED"}
    for ob in objs:
        for coll in list(ob.users_collection):
            coll.objects.unlink(ob)
        if ob.name not in coll_target.objects:
            coll_target.objects.link(ob)
        ob.select_set(True)
    if importing_into_active:
        self.report({'INFO'}, "Added to collection of active")
    else:
        self.report({'INFO'}, f"Created collection: {coll_target.name}")
    return {"FINISHED"}
class orengroup(bpy.types.Operator):
    """Group selected objects in a subcollection of the active collection. Name it as the active object. Shortcut also works in the Outliner"""
    bl_idname = "secret.group"
    bl_label = "Collection"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        context283482(self,context)
        return {'FINISHED'}
def context20398412(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = selcollectionofactive(layer, collName)
        if found:
            return found
def brush_vertex_paint(activeobj,objselection,vertex_group,context):
    bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    bpy.ops.wm.tool_set_by_id(name="builtin_brush.Draw")
    bpy.context.scene.tool_settings.vertex_group_weight = 1
    bpy.ops.object.vertex_group_set_active(group=vertex_group)
    _secret_paint_1731_set_modifier_value(
        _secret_paint_1731_paint_modifier(activeobj), "Input_69", True
    )
    activeobj.location = activeobj.location
def vertexgrouppaint_function(self,context,NoMasksDetected=True,calledfrombutton=False, being_transferred_to_newmesh=False,**kwargs):
    if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
    if "activeobj" in kwargs: activeobj = kwargs.get("activeobj")
    else: activeobj = bpy.context.active_object
    if activeobj==None: activeobj = bpy.context.active_object
    if "objselection" in kwargs: objselection = kwargs.get("objselection")
    else: objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    if "called_for_entire_biome" in kwargs: called_for_entire_biome = kwargs.get("called_for_entire_biome")
    else: called_for_entire_biome = False
    if called_for_entire_biome == False:
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]
    if "remove_vgroup" in kwargs: remove_vgroup = kwargs.get("remove_vgroup")
    else: remove_vgroup = False
    if "paint_the_vertex" in kwargs: paint_the_vertex = kwargs.get("paint_the_vertex")
    else: paint_the_vertex = True
    if activeobj.type!="CURVES":
        self.report({'WARNING'}, "Active object is not a hair curve")
        return {"CANCELLED"}
    surfaceobj = activeobj.parent
    active_modifier = _secret_paint_1731_paint_modifier(activeobj)
    biomeofactive = _secret_paint_1731_modifier_value(active_modifier, "Input_83_attribute_name", "")
    if biomeofactive and being_transferred_to_newmesh == False: vertex_ofParent=surfaceobj.vertex_groups.get(biomeofactive).name
    else: vertex_ofParent=[]
    only_hair_from_selected=[]
    all_vertex_groups=[]
    for ob in objselection:
        if ob.type=="CURVES":
            if ob.modifiers:
                for modif in ob.modifiers:
                    if modif.type == 'NODES':
                        if modif.node_group:
                            if modif.node_group.name == "Secret Paint":
                                only_hair_from_selected.append(ob)
                                attribute_name = _secret_paint_1731_modifier_value(modif, "Input_83_attribute_name", "")
                                if attribute_name and attribute_name not in all_vertex_groups:
                                    all_vertex_groups.append(attribute_name)
    if being_transferred_to_newmesh:
        if all_vertex_groups:
            sameVgroup_forAllHair = True
            for vgroup in all_vertex_groups:
                numb = 1
                while surfaceobj.vertex_groups.get("Biome" + str(numb)): numb += 1
                biomename = "Biome" + str(numb)
                new_vertex_group = surfaceobj.vertex_groups.new(name=biomename)
                for i in range(len(surfaceobj.data.vertices)):
                    new_vertex_group.add([i], 1.0, 'REPLACE')
                loopN=1
                for hair in only_hair_from_selected[:]:
                    loopN += 1
                    hair_modifier = _secret_paint_1731_paint_modifier(hair)
                    if vgroup == _secret_paint_1731_modifier_value(hair_modifier, "Input_83_attribute_name", ""):
                        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_attribute_name", biomename)
                        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
                        if _secret_paint_1731_modifier_value(hair_modifier, "Input_83_use_attribute", False) == False:
                            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_use_attribute", True)
                        hair.location = hair.location
                        only_hair_from_selected.remove(hair)
                    else: sameVgroup_forAllHair=False
            if sameVgroup_forAllHair and NoMasksDetected and paint_the_vertex:
                bpy.data.objects[surfaceobj.name].select_set(True)
                bpy.context.view_layer.objects.active = surfaceobj
                for i in range(len(surfaceobj.data.vertices)):
                    new_vertex_group.add([i], 0.0, 'REPLACE')
                brush_vertex_paint(activeobj, objselection, biomename, context)
    elif remove_vgroup:
        removed_vgroups=[]
        parent_of_hair=None
        for hair in only_hair_from_selected:
            hair_modifier = _secret_paint_1731_paint_modifier(hair)
            attribute_name = _secret_paint_1731_modifier_value(hair_modifier, "Input_83_attribute_name", "")
            if attribute_name and attribute_name not in removed_vgroups: removed_vgroups.append(attribute_name)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_attribute_name", "")
            if _secret_paint_1731_modifier_value(hair_modifier, "Input_83_use_attribute", False) == True:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_use_attribute", False)
            hair.location = hair.location
            if hair.parent: parent_of_hair=hair.parent
        all_Vgroups_used_in_biome=[]
        for child in parent_of_hair.children:
            if child.type == "CURVES" and child.modifiers or child.type == "CURVE" and child.modifiers:
                for modif in child.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        attribute_name = _secret_paint_1731_modifier_value(modif, "Input_83_attribute_name", "")
                        if attribute_name and attribute_name not in all_Vgroups_used_in_biome:
                            all_Vgroups_used_in_biome.append(attribute_name)
        for g in removed_vgroups:
            if g not in all_Vgroups_used_in_biome: parent_of_hair.vertex_groups.remove(parent_of_hair.vertex_groups.get(g))
    elif _secret_paint_1731_modifier_value(active_modifier, "Input_83_use_attribute", False) == False:
        numb = 1
        while surfaceobj.vertex_groups.get("Biome"+str(numb)): numb += 1
        biomename = "Biome"+str(numb)
        surfaceobj.vertex_groups.new(name=biomename)
        for hair in only_hair_from_selected:
            hair_modifier = _secret_paint_1731_paint_modifier(hair)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_attribute_name", biomename)
            _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
            if _secret_paint_1731_modifier_value(hair_modifier, "Input_83_use_attribute", False) == False:
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_use_attribute", True)
            hair.location = hair.location
        bpy.data.objects[surfaceobj.name].select_set(True)
        bpy.context.view_layer.objects.active = surfaceobj
        brush_vertex_paint(activeobj,objselection,biomename, context)
    elif len(all_vertex_groups) >= 1 and vertex_ofParent:
        if len(only_hair_from_selected)!=1:
            for hair in only_hair_from_selected:
                hair_modifier = _secret_paint_1731_paint_modifier(hair)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_attribute_name", biomeofactive)
                _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
                if _secret_paint_1731_modifier_value(hair_modifier, "Input_83_use_attribute", False) == False:
                    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_use_attribute", True)
                hair.location = hair.location
        for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
        bpy.context.view_layer.objects.active = surfaceobj
        brush_vertex_paint(activeobj,objselection,biomeofactive,context)
        return {'FINISHED'}
class vertexgrouppaint(bpy.types.Operator):
    """Weight Paint Mask. Share it with all selected (or press Q in the viewport). Alt+Click to remove it"""
    bl_idname = "secret.vertexgrouppaint"
    bl_label = "Weight Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.vertexgrouppaint")
        if event.alt: remove_vgroup=True
        else: remove_vgroup=False
        vertexgrouppaint_function(self,context,NoMasksDetected=True,calledfrombutton=True, activeobj=bpy.data.objects.get(self.object_name), remove_vgroup=remove_vgroup)
        return {'FINISHED'}
class vertexgrouppaint_biome(bpy.types.Operator):
    """Weight Paint Mask. Share it with all Biome (or press Q in the viewport). Alt+Click to remove it"""
    bl_idname = "secret.vertexgrouppaint_biome"
    bl_label = "Weight Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty()
    def invoke(self, context, event):
        secretpaint_update_modifier_f(context,upadte_provenance="secret.vertexgrouppaint_biome")
        obj = context.object
        if obj:
            hair = find_all_listed_paintsystems(context, activeobj=obj)
            hair_in_bgroup = [
                hayr[0]
                for hayr in hair[:]
                if _secret_paint_1731_modifier_value(
                    _secret_paint_1731_paint_modifier(hayr[0]), "Socket_0", 0
                ) == int(self.object_biome)
            ]
        if event.alt: remove_vgroup=True
        else: remove_vgroup=False
        vertexgrouppaint_function(self,context,NoMasksDetected=True,calledfrombutton=True, called_for_entire_biome=True, activeobj=hair_in_bgroup[0],objselection=hair_in_bgroup , remove_vgroup=remove_vgroup)
        return {'FINISHED'}
def _secret_paint_view_selected_if_view3d(context):
    """Frame the current selection only when a valid 3D View context exists."""
    candidates = []
    context_area = getattr(context, "area", None)
    context_window = getattr(context, "window", None)
    if context_area is not None and context_area.type == 'VIEW_3D':
        candidates.append((context_window, context_area))
    else:
        window_manager = getattr(context, "window_manager", None)
        for window in list(getattr(window_manager, "windows", ())):
            screen = getattr(window, "screen", None)
            if screen is None:
                continue
            candidates.extend(
                (window, area)
                for area in screen.areas
                if area.type == 'VIEW_3D'
            )
    for window, area in candidates:
        region = next(
            (candidate for candidate in area.regions if candidate.type == 'WINDOW'),
            None,
        )
        if region is None:
            continue
        override = {
            "area": area,
            "region": region,
            "space_data": area.spaces.active,
        }
        if window is not None:
            override["window"] = window
        try:
            with context.temp_override(**override):
                bpy.ops.view3d.view_selected(use_all_regions=True)
            return True
        except (AttributeError, RuntimeError, TypeError):
            continue
    return False
def orencurveselectobj_function(self,context, **kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    all_selected_curves=[]
    all_selected_meshes=[]
    all_colls_used_as_brush = []
    for obj in objselection:
        if obj.type in ["CURVES","CURVE"] and obj.modifiers:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    all_selected_curves.append(obj)
        elif obj.type == "MESH":
            all_selected_meshes.append(obj)
            Coll_of_Active = []
            ucol = obj.users_collection
            for i in ucol:
                layer_collection = bpy.context.view_layer.layer_collection
                Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                if Coll_of_Active and Coll_of_Active.name not in all_colls_used_as_brush: all_colls_used_as_brush.append(Coll_of_Active.name)
    if len(all_selected_meshes)==len(objselection):
        for obj in bpy.context.scene.objects:
            if obj.type in ["CURVES","CURVE"]:
                if obj.modifiers:
                    for modif in obj.modifiers:
                        if modif.type == 'NODES':
                            if modif.node_group:
                                if modif.node_group.name.startswith("Secret Paint"):
                                    input_9 = _secret_paint_1731_modifier_value(modif, "Input_9", None)
                                    input_2 = _secret_paint_1731_modifier_value(modif, "Input_2", None)
                                    if input_9 and input_9.name in all_colls_used_as_brush:
                                            bpy.data.objects[obj.name].select_set(True)
                                            bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]
                                    if input_2 and input_2 in objselection:
                                        bpy.data.objects[obj.name].select_set(True)
                                        bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]
    elif len(all_selected_curves)==len(objselection):
        for objj in objselection: objj.select_set(False)
        for obj in objselection:
            if obj.type in ["CURVES","CURVE"]:
                if obj.modifiers:
                    for modif in obj.modifiers:
                        if modif.type == 'NODES':
                            if modif.node_group:
                                if modif.node_group.name.startswith("Secret Paint"):
                                    input_9 = _secret_paint_1731_modifier_value(modif, "Input_9", None)
                                    input_2 = _secret_paint_1731_modifier_value(modif, "Input_2", None)
                                    if input_9:
                                        for ob in bpy.data.collections[input_9.name].all_objects:
                                            if len(objselection)>=2:
                                                ob.select_set(True)
                                                bpy.context.view_layer.objects.active = ob
                                                _secret_paint_view_selected_if_view3d(context)
                                            elif len(objselection)==1:
                                                ob.select_set(True)
                                                bpy.context.view_layer.objects.active = ob
                                                _secret_paint_view_selected_if_view3d(context)
                                    if input_2:
                                        if len(objselection)>=2:
                                            input_2.select_set(True)
                                            bpy.context.view_layer.objects.active = input_2
                                            _secret_paint_view_selected_if_view3d(context)
                                        elif len(objselection)==1:
                                            input_2.select_set(True)
                                            bpy.context.view_layer.objects.active = input_2
                                            _secret_paint_view_selected_if_view3d(context)
    return {'FINISHED'}
class orencurveselectobj(bpy.types.Operator):
    """For orenpaint and Hair scattering: selects brush object. If mesh selected: select all biomes that are using it"""
    bl_idname = "secret.orencurveselectobj"
    bl_label = "Select Brush obj"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        orencurveselectobj_function(self,context)
        return {'FINISHED'}
def convert_and_join_f(self,context):
    activeobj = bpy.context.active_object
    if activeobj.type == "MESH": objtype = "MESH"
    if activeobj.type == "CURVE": objtype = "BEZ"
    if activeobj.type == "CURVES": objtype = "HAI"
    activeobjDATANAME = activeobj.data.name
    bpy.ops.object.select_grouped(extend=True, type='CHILDREN_RECURSIVE')
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False})
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    activeobjlocation = tuple(bpy.context.active_object.location)
    objselection = bpy.context.selected_objects
    linked_detected_will_cause_dupli_everything = False
    all_curves=[]
    for obj in objselection:
        if obj.type in ["CURVES", "CURVE"]:
            all_curves.append(obj)
            if obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        _secret_paint_1731_set_modifier_value(modif, "Input_50", True)
                        obj.location = obj.location
    bpy.ops.object.duplicates_make_real()
    for ob in all_curves:
        bpy.data.objects.remove(ob, do_unlink=True)
    newobjselection = bpy.context.selected_objects
    for ob in newobjselection:
        if ob.type == "EMPTY":
            newobjselection.remove(ob)
            bpy.data.objects.remove(ob, do_unlink=True)
    for ob in newobjselection:
        bpy.context.view_layer.objects.active = ob
        if ob.data.library: linked_detected_will_cause_dupli_everything = True
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.convert(target='MESH')
    if linked_detected_will_cause_dupli_everything:
        for ob in newobjselection:
            newobjselection.remove(ob)
            bpy.data.objects.remove(ob, do_unlink=True)
        newobjselection = bpy.context.selected_objects
    center_found = False
    for ob in newobjselection:
        if tuple(ob.location) == activeobjlocation:
            bpy.context.view_layer.objects.active = ob
            center_found = True
            break
    bpy.ops.object.join()
    if not center_found:
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        bpy.ops.object.align_tools(subject='1', active_too=True, advanced=True, loc_z=True, ref1='0', ref2='0', self_or_active='0')
    reupdating_existing_mesh=False
    ob_to_update=[]
    data_to_update = []
    for ob in bpy.data.objects:
        if ob.type=="MESH" and ob.data.name == activeobjDATANAME +"ASSEMBLY-"+objtype:
            ob_to_update.append(ob)
            data_to_update = ob.data
            reupdating_existing_mesh=True
    if data_to_update:
        data_to_update.name = "OLDTODELETE"
        bpy.context.view_layer.objects.active.data.name = activeobjDATANAME +"ASSEMBLY-"+objtype
        for ob in ob_to_update: ob.data = bpy.context.view_layer.objects.active.data
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    if reupdating_existing_mesh:
        bpy.data.objects.remove(bpy.context.view_layer.objects.active, do_unlink=True)
        self.report({'INFO'}, "Updated Existing Mesh Assembly")
    else:
        bpy.context.view_layer.objects.active.name = bpy.context.view_layer.objects.active.data.name = activeobjDATANAME +"ASSEMBLY-"+objtype
        self.report({'INFO'}, "Created a new Mesh Assembly")
        bpy.ops.transform.translate('INVOKE_DEFAULT', use_proportional_edit=False)
    return {'FINISHED'}
class convert_and_join(bpy.types.Operator):
    """convert_and_join"""
    bl_idname = "secret.convert_and_join"
    bl_label = "convert_and_join curves into mesh"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        convert_and_join_f(self,context)
        return {'FINISHED'}
def realize_instances_f(self,context):
    activeobj = bpy.context.active_object
    activeobj.select_set(True)
    objselection = bpy.context.selected_objects
    for obj in objselection:
        all_brush_coll_instans = []
        all_assemblies_modifiers = []
        realized_partial_hair = False
        objs_to_delete_afterwards = []
        for x in bpy.context.selected_objects: x.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if obj.type in ["CURVES","CURVE"] and obj.modifiers:
            hide_original_paint_system = True
            if bpy.context.object.mode != "OBJECT" and obj.type == "CURVES":
                realized_partial_hair =True
                apply_paint(self, context)
                Coll_of_Active = []
                original_collection = bpy.context.view_layer.active_layer_collection
                ucol = obj.users_collection
                for i in ucol:
                    layer_collection = bpy.context.view_layer.layer_collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                newobj = obj.copy()
                objs_to_delete_afterwards.append(newobj)
                newobj.data = obj.data.copy()
                bpy.context.collection.objects.link(newobj)
                newobj.select_set(False)
                bpy.ops.object.mode_set(mode="EDIT")
                try: bpy.ops.curves.select_linked()
                except:pass
                bpy.ops.curves.delete()
                bpy.ops.curves.select_all(action='SELECT')
                newobj.select_set(True)
                bpy.context.view_layer.objects.active = newobj
                bpy.ops.object.mode_set(mode="EDIT")
                try:bpy.ops.curves.select_linked()
                except:pass
                bpy.ops.curves.select_all(action='INVERT')
                bpy.ops.curves.delete()
                bpy.ops.object.mode_set(mode="OBJECT")
                hide_original_paint_system = False
            if hide_original_paint_system and obj.type == "CURVES":
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" \
                    or modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999":
                        _secret_paint_1731_set_modifier_value(modif, "Input_99", True)
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    source_object = _secret_paint_1731_modifier_value(modif, "Input_2")
                    if source_object and source_object not in all_brush_coll_instans:
                        if source_object.instance_collection: all_brush_coll_instans.append(source_object)
                        elif source_object.modifiers and source_object.modifiers[0].type == "NODES" and source_object.modifiers[0].node_group and "ASSEMBLY" in source_object.modifiers[0].node_group.name and source_object.modifiers[0].show_viewport == True:
                            if source_object.modifiers[0] not in all_assemblies_modifiers: all_assemblies_modifiers.append(source_object.modifiers[0])
                            source_object.modifiers[0].show_viewport = False
                    source_collection = _secret_paint_1731_modifier_value(modif, "Input_9")
                    if source_collection:
                        for obij in source_collection.all_objects:
                            if obij.instance_collection and obij not in all_brush_coll_instans: all_brush_coll_instans.append(obij)
                            elif obij.modifiers and obij.modifiers[0].type=="NODES" and obij.modifiers[0].node_group and "ASSEMBLY" in obij.modifiers[0].node_group.name and obij.modifiers[0].show_viewport == True:
                                if obij.modifiers[0] not in all_assemblies_modifiers: all_assemblies_modifiers.append(obij.modifiers[0])
                                obij.modifiers[0].show_viewport = False
        all_data = []
        if all_brush_coll_instans:
            for instance in all_brush_coll_instans:
                for x in instance.instance_collection.all_objects:
                    if x.data not in all_data: all_data.append(x.data)
        all_previous_objects = set(bpy.context.scene.objects)
        bpy.ops.object.duplicates_make_real()
        for ob in objselection:
            if ob.type == "EMPTY" and not ob.instance_collection:
                bpy.data.objects.remove(ob, do_unlink=True)
        if obj.type == "CURVE":
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                    obj.modifiers[0].show_viewport = False
                    obj.modifiers[0].show_render = False
                    obj.location = obj.location
        if obj.type == "MESH" and obj.modifiers and obj.modifiers[0].type == "NODES" and obj.modifiers[0].node_group and "ASSEMBLY" in obj.modifiers[0].node_group.name and obj.modifiers[0].show_viewport == True:
            bpy.data.objects.remove(obj, do_unlink=True)
            objselection.remove(obj)
            continue
        for modif in all_assemblies_modifiers: modif.show_viewport = True
        new_obs = list(set(bpy.context.scene.objects) - all_previous_objects)
        for ob in new_obs:
            if ob.modifiers and ob.modifiers[0].type == "NODES" and ob.modifiers[0].node_group and "ASSEMBLY" in ob.modifiers[0].node_group.name and ob.modifiers[0].show_viewport == False:
                ob.modifiers[0].show_viewport = True
            if ob.type == "EMPTY":
                for instance in all_brush_coll_instans:
                    if ob.name.startswith(instance.name.rsplit('.', 1)[0]):
                        ob.instance_type = 'COLLECTION'
                        ob.instance_collection = instance.instance_collection
                if not ob.instance_collection: objs_to_delete_afterwards.append(ob)
            elif ob.type != "EMPTY" and ob.data and ob.data in all_data and ob not in objs_to_delete_afterwards:
                objs_to_delete_afterwards.append(ob)
            if obj.type == "CURVE":
                ob.parent = obj
                ob.matrix_parent_inverse = obj.matrix_world.inverted()
            elif obj.type == "CURVES":
                if obj.parent:
                    ob.parent = obj.parent
                    ob.matrix_parent_inverse = obj.parent.matrix_world.inverted()
            else:
                if obj.parent:
                    ob.parent = obj.parent
                    ob.matrix_parent_inverse = obj.parent.matrix_world.inverted()
        all_empties_coordinates = []
        for ob in new_obs:
            if ob.type == "EMPTY" and str(ob.location) not in all_empties_coordinates:
                all_empties_coordinates.append(str(ob.location))
            elif ob.type == "EMPTY" and str(ob.location) in all_empties_coordinates and ob not in objs_to_delete_afterwards:
                objs_to_delete_afterwards.append(ob)
        mesh_instances_seen = {}
        for ob in new_obs:
            if ob.type == "MESH" and ob.data and ob not in objs_to_delete_afterwards:
                loc = tuple(round(v, 2) for v in ob.location)
                rot = tuple(round(v, 4) for v in ob.rotation_euler)
                scale = tuple(round(v, 4) for v in ob.scale)
                instance_key = (ob.data.name, loc, rot, scale)
                if instance_key not in mesh_instances_seen:
                    mesh_instances_seen[instance_key] = ob
                else:
                    objs_to_delete_afterwards.append(ob)
        for objj in objs_to_delete_afterwards:
            bpy.data.objects.remove(objj, do_unlink=True)
    return {'FINISHED'}
class realize_instances(bpy.types.Operator):
    """Make instances real, mute Paint System. If executed from Edit mode or Hair Sculpt mode, it will only realize the selected hair strands. So you can choose which instance will be converted to an object and keep the rest as a Paint System"""
    bl_idname = "secret.realize_instances"
    bl_label = "Realize Instances"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        realize_instances_f(self,context)
        return {'FINISHED'}
def context237411(context):
    if len (bpy.context.selected_objects ) == 2:
        brushobj = bpy.context.active_object.name
        bpy.context.active_object.select_set(False)
        for obj in bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = obj
        originalcurveobj = bpy.context.active_object.name
        bpy.ops.object.duplicate_move_linked(OBJECT_OT_duplicate={"linked":True, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={})
        _secret_paint_1731_set_modifier_value(
            _secret_paint_1731_paint_modifier(bpy.context.object),
            "Input_2",
            bpy.data.objects[brushobj],
        )
        bpy.ops.object.mode_set(mode="EDIT")
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                override = bpy.context.copy()
                override["space_data"] = area.spaces[0]
                override["area"] = area
                bpy.ops.wm.tool_set_by_id(override, name="builtin.draw")
        bpy.ops.object.mode_set(mode="OBJECT")
    return {'FINISHED'}
class microbiome(bpy.types.Operator):
    """Select an object, select a system. Create a microbiome around the active system"""
    bl_idname = "secret.microbiome"
    bl_label = "Microbiome"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        context237411(context)
        return {'FINISHED'}
def createMaterialIfNone(self, context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    mate = activeobj.active_material
    if mate is None:
        mat = bpy.data.materials.new(name="New Material")
        mat.use_nodes = True
        if activeobj.data.materials:
            activeobj.data.materials[0] = mat
        else:
            activeobj.data.materials.append(mat)
        self.report({'INFO'}, "A new material was created since there was none.")
def newmaterial_f(self, context):
    new_duplis=[]
    for obj in bpy.context.selected_objects:
        bpy.data.objects[obj.name].select_set(False)
        if obj.type == "CURVES" and obj.modifiers or obj.type == "CURVE" and obj.modifiers:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    brushobj = _secret_paint_1731_modifier_value(modif, "Input_2", None)
                    custommaterial=None
                    if _secret_paint_1731_modifier_value(modif, "Input_39", False):
                        custommaterial = _secret_paint_1731_modifier_value(modif, "Input_40", None)
                    brushobj=dupliObjCheckCoordinates(self, context, activeobj=brushobj)
                    createMaterialIfNone(self, context, activeobj = brushobj)
                    obj.data.materials.clear()
                    for mat_slot in brushobj.material_slots:
                        if mat_slot.material:
                            mat = mat_slot.material
                            mat_slot.link = 'OBJECT'
                            if custommaterial: mat_slot.material = custommaterial
                            else: mat_slot.material = mat
                            if mat_slot.material.users >= 2: mat_slot.material = mat_slot.material.copy()
                            obj.data.materials.append(mat_slot.material)
                    _secret_paint_1731_set_modifier_value(modif, "Input_2", brushobj)
                    _secret_paint_1731_set_modifier_value(modif, "Input_39", False)
                    new_duplis.append(brushobj)
        elif obj.type=="MESH":
            createMaterialIfNone(self, context, activeobj = obj)
            dupliobj = dupliObjCheckCoordinates(self, context,activeobj = obj)
            new_duplis.append(dupliobj)
            obj.data.materials.clear()
            for mat_slot in dupliobj.material_slots:
                if mat_slot.material:
                    mat = mat_slot.material
                    mat_slot.link = 'OBJECT'
                    mat_slot.material = mat
                    if mat_slot.material.users >= 2: mat_slot.material = mat_slot.material.copy()
                    obj.data.materials.append(mat_slot.material)
    for x in new_duplis:
        bpy.data.objects[x.name].select_set(True)
        bpy.context.view_layer.objects.active = x
    return {'FINISHED'}
class orencurvenewmaterial(bpy.types.Operator):
    """Creates a linked duplicate of the object used as brush, but with a new material"""
    bl_idname = "secret.newmaterial"
    bl_label = "New Material"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        newmaterial_f(self, context)
        return {'FINISHED'}
def export_to_asset_library_function(self,context,event):
    if bpy.context.preferences.addons[__package__].preferences.biome_library == "(No Library Found, create one first)":
        self.report({'ERROR'}, "No Library Found, create one first")
        return{'FINISHED'}
    try: ActiveMode = bpy.context.object.mode
    except:
        self.report({'ERROR'}, "Select a Mesh object first")
        return{'FINISHED'}
    activeobj = bpy.context.object
    ORIG_objselection = bpy.context.selected_objects
    objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)
    all_meshes=[]
    all_selected_hair=[]
    all_brush_objs=[]
    all_brush_collections=[]
    all_parent_surfaces=[]
    for obj in objselection:
        if obj.type == "MESH":all_meshes.append(obj)
        elif obj.type == "CURVES":
            if obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                        all_selected_hair.append(obj)
                        input_2 = _secret_paint_1731_modifier_value(modif, "Input_2", None)
                        input_9 = _secret_paint_1731_modifier_value(modif, "Input_9", None)
                        if input_2 and input_2 not in all_brush_objs: all_brush_objs.append(input_2)
                        if input_9 and input_9 not in all_brush_collections: all_brush_collections.append(input_9)
                        if obj.parent and obj.parent not in all_parent_surfaces: all_parent_surfaces.append(obj.parent)
    if len(all_parent_surfaces)==1: biome_detected = True
    else: biome_detected = False
    if len(objselection)==len(all_selected_hair): all_sel_are_hair=True
    else: all_sel_are_hair=False
    asset_name = bpy.context.preferences.addons[__package__].preferences.biomeAssetName
    if not asset_name and activeobj: asset_name = activeobj.name
    new_collection = bpy.data.collections.new(asset_name)
    bpy.context.scene.collection.children.link(new_collection)
    newobjs_toDelete=[]
    if biome_detected and all_parent_surfaces == all_meshes and len(all_meshes)==1\
    or all_sel_are_hair:
        largest = all_selected_hair[0]
        for ob in all_selected_hair:
            if _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(ob), "Input_68", 0
            ) < _secret_paint_1731_modifier_value(
                _secret_paint_1731_paint_modifier(largest), "Input_68", 0
            ):
                largest = ob
        largest_modifier = _secret_paint_1731_paint_modifier(largest)
        largest_input_68 = _secret_paint_1731_modifier_value(largest_modifier, "Input_68", 0)
        largest_input_100 = _secret_paint_1731_modifier_value(largest_modifier, "Input_100", 0)
        xsize = 1 / ((largest_input_68 ** 0.5) * (largest_input_100 ** 0.5))
        number_instaces_to_show = 12
        radius = (number_instaces_to_show * (xsize * xsize)) ** 0.5
        subdivisions = 4
        meshhh = bpy.data.meshes.new("Secret Paint Biome")
        bm = bmesh.new()
        v = [bm.verts.new((x, y, 0)) for x, y in [(-radius / 2, -radius / 2), (radius / 2, -radius / 2), (radius / 2, radius / 2), (-radius / 2, radius / 2)]]
        f = bm.faces.new(v)
        for _ in range(subdivisions):
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)
        bm.to_mesh(meshhh)
        bm.free()
        cubeOBJ = bpy.data.objects.new("Secret Paint Biome", meshhh)
        new_collection.objects.link(cubeOBJ)
        cubeOBJ.use_fake_user = 1
        all_previous_objects = set(bpy.context.scene.objects)
        secretpaint_function(self, context, event, activeobj=cubeOBJ, objselection=objselection, auto_Mask_Optimization=False)
        newobjs_toDelete = list(set(bpy.context.scene.objects) - all_previous_objects)
        newobjs_toDelete.append(cubeOBJ)
        objselection = newobjs_toDelete
        if all_parent_surfaces[0].material_slots:
            for source_mat_slot in all_parent_surfaces[0].material_slots:
                source_mat = source_mat_slot.material
                if source_mat:
                    target_mat_slot = cubeOBJ.material_slots.get(source_mat.name)
                    if not target_mat_slot: target_mat_slot = cubeOBJ.data.materials.append(source_mat)
                    if target_mat_slot: target_mat_slot.material = source_mat
        bpy.data.objects[cubeOBJ.name].select_set(True)
        if cubeOBJ.children:
            for hair in cubeOBJ.children:
                if len(cubeOBJ.children)==1:
                    hair_modifier = _secret_paint_1731_paint_modifier(hair)
                    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_69", True)
                    if _secret_paint_1731_modifier_value(hair_modifier, "Input_83_use_attribute", False):
                        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_use_attribute", False)
                    _secret_paint_1731_set_modifier_value(hair_modifier, "Input_83_attribute_name", "")
                    bpy.ops.object.mode_set(mode="OBJECT")
                if hair not in objselection: objselection.append(hair)
        for x in bpy.context.selected_objects: x.select_set(False)
        if activeobj: bpy.context.view_layer.objects.active = activeobj
        for x in ORIG_objselection: x.select_set(True)
        bpy.ops.object.mode_set(mode=ActiveMode)
    for obj in objselection:
        if obj.name not in new_collection.all_objects: new_collection.objects.link(obj)
    new_collection.asset_mark()
    new_collection.asset_generate_preview()
    for obj in all_brush_objs:
        if obj.name not in new_collection.all_objects: new_collection.objects.link(obj)
    for coll in all_brush_collections: new_collection.children.link(coll)
    target_catalog = bpy.context.preferences.addons[__package__].preferences.biomenamecategory
    if target_catalog:
        folder = os.path.join(bpy.context.preferences.addons[__package__].preferences.biome_library, "blender_assets.cats.txt")
        with open(folder, 'a+') as f:
            f.seek(0)
            existingID=False
            for line in f.readlines():
                if line.startswith(("#", "VERSION", "\n")):
                    continue
                name = line.split(":")[1].split("\n")[0]
                if name.lower() == target_catalog.lower():
                    existingID=True
                    uuid=line.split(":")[0]
                    break
            if not existingID:
                distinct_chars = "abcdef0123456789"
                part1 = ''.join(random.choice(distinct_chars) for _ in range(8))
                part2 = ''.join(random.choice(distinct_chars) for _ in range(4))
                part3 = ''.join(random.choice(distinct_chars) for _ in range(4))
                part4 = ''.join(random.choice(distinct_chars) for _ in range(4))
                part5 = ''.join(random.choice(distinct_chars) for _ in range(12))
                uuid = part1+"-"+part2+"-"+part3+"-"+part4+"-"+part5
                final = uuid +":"+target_catalog+":"+target_catalog.replace('/', '-')
                f.write("\n"+final)
            new_collection.asset_data.catalog_id = uuid
    biome_name = bpy.context.preferences.addons[__package__].preferences.biomename
    relative_biome_name = biome_name.lstrip("/\\")
    path = os.path.join(bpy.context.preferences.addons[__package__].preferences.biome_library, os.path.dirname(relative_biome_name))
    if not os.path.exists(path): os.makedirs(path)
    temp_blend = os.path.join(path, "tempSecretPaintExport.blend")
    bpy.ops.wm.save_as_mainfile(copy=True, filepath=temp_blend)
    finalpath = os.path.join(path, os.path.basename(relative_biome_name))
    if not finalpath.endswith(".blend"): finalpath= finalpath+".blend"
    if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={*bpy.data.masks}, fake_user=False, path_remap="ABSOLUTE")
    move_objects_script = os.path.join(path, "tempSecretExportScript.py")
    move_objects_script_content = f'''
import bpy
import os
import re
import addon_utils
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection
source_file_path = {temp_blend!r}
with bpy.data.libraries.load(source_file_path) as (data_from, data_to):
    data_to.collections = [name for name in data_from.collections if {new_collection.name!r} == name]
hidden_to_restore=[]
for coll in data_to.collections:
    bpy.context.collection.children.link(coll)
    if {newobjs_toDelete}:
        for oob in coll.all_objects:
            if oob.type!="CURVES" and not oob.name.startswith("Secret Paint Biome"):
                hidden_to_restore.append(oob)
                oob.location=(0,0,0)
                oob.scale=(0,0,0)
                if oob.asset_data: oob.asset_clear()
                if oob.use_fake_user: oob.use_fake_user = False
blender_version_tuple = bpy.app.version[:3]
addon_path=[]
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":
        addon_path = os.path.dirname(mod.__file__)
        break
nodes_to_switch = []
cleanup_generator = []
for node_tree in bpy.data.node_groups:
    if node_tree.name == "Secret Paint" or node_tree.name.startswith("Secret Paint") and re.search(r"\\.\\d{{3}}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":
        if not node_tree.library: node_tree.name = "Secret Paint.001"
        if node_tree not in nodes_to_switch: nodes_to_switch.append(node_tree)
    if node_tree.name == "Secret Generator" or node_tree.name.startswith("Secret Generator") and re.search(r"\\.\\d{{3}}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":
        if not node_tree.library: node_tree.name = "Secret Generator.001"
        if node_tree not in cleanup_generator: cleanup_generator.append(node_tree)
all_previous_nodes = set(bpy.data.node_groups)
if blender_version_tuple < (5, 2, 0):
    file_path = os.path.join(addon_path, "Secret Paint 4.5-5.1.blend")
else:
    file_path = os.path.join(addon_path, "Secret Paint.blend")
inner_path = "NodeTree"
object_name = "Secret Paint"
try: bpy.ops.wm.append(filepath=os.path.join(file_path, inner_path, object_name),directory=os.path.join(file_path, inner_path),filename=object_name)
except:pass
for lib in bpy.data.libraries:
    if lib.name in ["Secret Paint.blend", "Secret Paint 4.5-5.1.blend"]: bpy.data.libraries.remove(lib, do_unlink=True)
for nod in bpy.data.node_groups:
    if nod not in all_previous_nodes and nod.name.startswith("Secret Paint"):
        orenpaintNode= nod
        break
for obj in bpy.data.objects:
    if obj.type in ["CURVES","CURVE"]:
        for modif in obj.modifiers:
            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith(("Secret Paint","orenpaint")) and "ASSEMBLY" not in modif.node_group.name: modif.node_group = orenpaintNode
for nod in nodes_to_switch[:]:
    bpy.data.node_groups.remove(nod, do_unlink=True)
for nod in cleanup_generator[:]:
    bpy.data.node_groups.remove(nod, do_unlink=True)
for mask in bpy.data.masks: bpy.data.masks.remove(mask, do_unlink=True)
for o in bpy.data.collections:
    if o.asset_data: o.asset_generate_preview()
for oob in hidden_to_restore: oob.scale=(1,1,1)
bpy.ops.wm.save_mainfile()
    '''
    with open(move_objects_script, 'w') as move_script_file:
        move_script_file.write(move_objects_script_content)
    command = [
        bpy.app.binary_path,
        "--background", finalpath,
        "--python", move_objects_script
    ]
    subprocess.run(command, check=True)
    os.remove(move_objects_script)
    os.remove(temp_blend)
    for o in newobjs_toDelete:
        if o.type=="MESH":
            bpy.data.meshes.remove(o.data, do_unlink=True)
            continue
        if o.type=="CURVES":
            bpy.data.hair_curves.remove(o.data, do_unlink=True)
            continue
    bpy.data.collections.remove(new_collection, do_unlink=True)
    self.report({'INFO'}, f"Successfully exported to {finalpath}")
    return {'FINISHED'}
class export_obj_to_asset_library(bpy.types.Operator):
    """Export the selected hair objects as a Biome to the currently open Asset Library. Works for regular objects as well as Biome Systems"""
    bl_idname = "secret.export_obj_to_asset_library"
    bl_label = "Export Biome to Asset Library"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        export_to_asset_library_function(self, context,event)
        return {'FINISHED'}
class switchtoerasealpha(bpy.types.Operator):
    """In Texture paint mode, press the shortcut to toggle between painting mode and erase mode"""
    bl_idname = "secret.switchtoerasealpha"
    bl_label = "Toggle Erase Alpha /Mix"
    def execute(self, context):
        if bpy.context.tool_settings.image_paint.brush.blend == 'ERASE_ALPHA':
            bpy.context.tool_settings.image_paint.brush.blend = 'MIX'
        else:
            bpy.context.tool_settings.image_paint.brush.blend = 'ERASE_ALPHA'
        return {'FINISHED'}
def add_collections_to_list(collection,all_collections):
    all_collections.append(collection)
    for sub_collection in collection.children:
        add_collections_to_list(sub_collection,all_collections)
_SECRET_PAINT_ASSET_IDENTIFIER_PROP = "_secret_paint_asset_identifier"
def _secret_paint_asset_identifier(library_name, asset_type, asset_path, asset_name):
    normalized_path = os.path.normcase(os.path.normpath(str(asset_path)))
    return f"{library_name}|{asset_type}|{normalized_path}|{asset_name}"
def _secret_paint_find_imported_asset_objects(identifier):
    if not identifier:
        return []
    return [
        obj for obj in bpy.data.objects
        if obj.get(_SECRET_PAINT_ASSET_IDENTIFIER_PROP) == identifier
        and obj.name in bpy.context.view_layer.objects
    ]
def _secret_paint_mark_imported_asset_objects(objects, identifier):
    if not identifier:
        return
    for obj in objects:
        try:
            obj[_SECRET_PAINT_ASSET_IDENTIFIER_PROP] = identifier
        except (AttributeError, TypeError, ValueError):
            pass
def _secret_paint_object_asset_paint_object(objects, root_objects=()):
    """Resolve the paintable object for a new or previously imported asset."""
    for candidates in (root_objects, objects):
        for obj in candidates or ():
            if (obj is not None and
                    not _secret_paint_q_is_paint_system(obj) and
                    obj.type in {"MESH", "EMPTY", "CURVE", "CURVES"}):
                return obj
    for obj in objects or ():
        if not _secret_paint_q_is_paint_system(obj):
            continue
        brush_object = _secret_paint_q_single_system_brush_object(obj)
        if brush_object is not None:
            return brush_object
    return None
def _secret_paint_asset_start_terrain_selection(self, context, brush_object):
    """Open a 3D View and invoke the terrain picker after Asset Browser import."""
    if brush_object is None:
        return False
    window_manager = getattr(context, "window_manager", None)
    if window_manager is None:
        return False
    current_window = getattr(context, "window", None)
    current_area = getattr(context, "area", None)
    windows = list(window_manager.windows)
    if current_window in windows:
        windows.remove(current_window)
        windows.insert(0, current_window)
    for window in windows:
        view_layer = getattr(window, "view_layer", None)
        if (view_layer is None or
                brush_object.name not in view_layer.objects):
            continue
        view_areas = sorted(
            (
                area for area in window.screen.areas
                if area.type == "VIEW_3D"
            ),
            key=lambda area: area.width * area.height,
            reverse=True,
        )
        for area in view_areas:
            region = next(
                (
                    candidate for candidate in area.regions
                    if candidate.type == "WINDOW"
                ),
                None,
            )
            if region is None:
                continue
            try:
                with bpy.context.temp_override(
                        window=window,
                        area=area,
                        region=region,
                        scene=window.scene,
                        view_layer=view_layer,
                ):
                    for obj in list(bpy.context.selected_objects):
                        obj.select_set(False)
                    brush_object.hide_set(False)
                    brush_object.select_set(True)
                    bpy.context.view_layer.objects.active = brush_object
                    result = bpy.ops.secret.paint('INVOKE_DEFAULT')
                return result == {'RUNNING_MODAL'}
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
    if (current_window is not None and
            current_area is not None and
            current_area in current_window.screen.areas):
        def start_selection_in_asset_area():
            try:
                if current_area not in current_window.screen.areas:
                    return None
                current_area.type = 'VIEW_3D'
                region = next(
                    (
                        candidate for candidate in current_area.regions
                        if candidate.type == "WINDOW"
                    ),
                    None,
                )
                view_layer = current_window.view_layer
                if (region is None or view_layer is None or
                        brush_object.name not in view_layer.objects):
                    return None
                with bpy.context.temp_override(
                        window=current_window,
                        area=current_area,
                        region=region,
                        scene=current_window.scene,
                        view_layer=view_layer,
                ):
                    for obj in list(bpy.context.selected_objects):
                        obj.select_set(False)
                    brush_object.hide_set(False)
                    brush_object.select_set(True)
                    bpy.context.view_layer.objects.active = brush_object
                    bpy.ops.secret.paint('INVOKE_DEFAULT')
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
            return None
        bpy.app.timers.register(start_selection_in_asset_area, first_interval=0.0)
        return True
    return False
def paint_from_library_function(self, context, event, **kwargs):
    justImport = kwargs.get("justImport") if "justImport" in kwargs else False
    switch_asset = kwargs.get("switch_asset") if "switch_asset" in kwargs else False
    activeobj = bpy.context.active_object
    select_terrain_after_import = False
    terrain_selection_started = False
    current_mode = None
    if justImport == False:
        if activeobj is None and not switch_asset:
            select_terrain_after_import = True
            current_mode = "OBJECT"
        elif activeobj == None or activeobj.type not in ["CURVES","CURVE","MESH"]:
            self.report({'ERROR'}, "Select a Mesh object first")
            return {'FINISHED'}
        else:
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode="OBJECT")
    elif justImport:
        if activeobj:
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode="OBJECT")
    objselection = bpy.context.selected_objects
    if bpy.app.version_string >= "4.0.0":
        current_library_name = context.area.spaces.active.params.asset_library_reference
    elif bpy.app.version_string < "4.0.0":
        current_library_name = context.area.spaces.active.params.asset_library_ref
        if current_library_name == "ALL":
            self.report({'ERROR'}, "Select an Asset Library in the side panel (can't be set to 'ALL') (fixed in Blender 4.0)")
            return {'FINISHED'}
    original_collection = bpy.context.view_layer.active_layer_collection
    new_coll_was_created_so_hide_viewport=False
    coll_to_hide = None
    if justImport == False and not select_terrain_after_import:
        if bpy.context.preferences.addons[__package__].preferences.checkboxHideImported:
            all_collections = []
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection, all_collections)
            for coll in all_collections:
                if coll.name.startswith("Secret Assets"):
                    pass
                    FoundHiddenCollection = recurLayerCollection(bpy.context.view_layer.layer_collection, coll.name)
                    FoundHiddenCollection_status = coll.hide_viewport
                    coll.hide_viewport = False
                    bpy.context.view_layer.active_layer_collection = FoundHiddenCollection
                    coll_to_hide = coll
                    break
            if not bpy.context.view_layer.active_layer_collection.name.startswith("Secret Assets"):
                pass
                new_coll_was_created_so_hide_viewport =True
                new_coll = bpy.data.collections.new("Secret Assets")
                bpy.context.view_layer.active_layer_collection.collection.children.link(new_coll)
                bpy.context.view_layer.active_layer_collection = recurLayerCollection(bpy.context.view_layer.layer_collection, new_coll.name)
        else:
            Coll_of_Active = []
            for i in activeobj.users_collection:
                layer_collection = bpy.context.view_layer.layer_collection
                Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                bpy.context.view_layer.active_layer_collection = Coll_of_Active
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    if bpy.app.version_string >= "4.0.0": sel_assets = context.selected_assets
    elif bpy.app.version_string < "4.0.0": sel_assets = context.selected_asset_files
    for asset_file in sel_assets:
        if current_library_name == "LOCAL":
            if bpy.app.version_string >= "4.0.0":
                asset_fullpath = asset_file.local_id
                asset_type = asset_file.id_type.lower().capitalize()
            elif bpy.app.version_string < "4.0.0":
                library_path = Path(bpy.data.filepath)
                asset_fullpath = library_path / asset_file.relative_path
                asset_fullpath /= asset_file.local_id.name
                asset_type = asset_fullpath.parent.parent.name
            asset_identifier = _secret_paint_asset_identifier(
                current_library_name,
                asset_type,
                "LOCAL",
                asset_fullpath.name,
            )
            if switch_asset:
                if asset_type == "Object": paintbrushswitch_f(self, context, activeobj=bpy.data.objects[asset_fullpath.name], objselection=[activeobj], current_mode=current_mode)
                elif asset_type == "Collection":
                    paintbrushswitch_f(self, context, activeobj=activeobj, objselection=[x for x in bpy.data.collections[asset_fullpath.name].all_objects], current_mode=current_mode)
            else:
                if asset_type == "Object":
                    brush_to_paint_with=[bpy.data.objects[asset_fullpath.name]]
                elif asset_type == "Collection":
                    brush_to_paint_with=[]
                    for oibj in bpy.data.collections[asset_fullpath.name].all_objects:
                        if oibj.name.startswith("Secret Paint Biome"): brush_to_paint_with = [j for j in oibj.children if j.type=="CURVES" and j.modifiers and j.data.name.startswith("Secret Paint")]
                    if not brush_to_paint_with: brush_to_paint_with = [x for x in bpy.data.collections[asset_fullpath.name].all_objects]
                _secret_paint_mark_imported_asset_objects(
                    brush_to_paint_with,
                    asset_identifier,
                )
                if select_terrain_after_import:
                    if not terrain_selection_started:
                        selection_object = _secret_paint_object_asset_paint_object(
                            brush_to_paint_with
                        )
                        if selection_object is None:
                            self.report({'WARNING'}, "The selected asset has no paintable object")
                        else:
                            terrain_selection_started = _secret_paint_asset_start_terrain_selection(
                                self,
                                context,
                                selection_object,
                            )
                else:
                    secretpaint_function(self, context, event, activeobj=activeobj, objselection=brush_to_paint_with)
                bpy.context.view_layer.active_layer_collection = original_collection
        else:
            if bpy.app.version_string >= "4.0.0":
                asset_filepath = asset_file.full_library_path
                asset_type = asset_file.id_type.lower().capitalize()
                asset_name = asset_file.name
            elif bpy.app.version_string < "4.0.0":
                library_path = Path(context.preferences.filepaths.asset_libraries.get(current_library_name).path)
                asset_fullpath = library_path / asset_file.relative_path
                asset_name = asset_fullpath.name
                asset_filepath = asset_fullpath.parent.parent
                asset_type = asset_fullpath.parent.name
            asset_identifier = _secret_paint_asset_identifier(
                current_library_name,
                asset_type,
                asset_filepath,
                asset_name,
            )
            reused_asset_objects = _secret_paint_find_imported_asset_objects(
                asset_identifier
            )
            reused_existing_asset = bool(reused_asset_objects)
            all_previous_objects = set(bpy.data.objects)
            all_previous_nodes = set(bpy.data.node_groups)
            all_previous_objectData = set(bpy.data.meshes)
            all_previous_collections=[]
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection,all_previous_collections)
            if bpy.app.version_string >= "4.0.0": import_setting = bpy.context.space_data.params.import_method
            elif bpy.app.version_string < "4.0.0": import_setting = bpy.context.space_data.params.import_type
            try:
                if import_setting == 'LINK' and not reused_existing_asset:
                    bpy.ops.wm.link(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                    directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                    instance_collections=False, active_collection=True,do_reuse_local_id=False)
                elif import_setting == 'APPEND' and not reused_existing_asset:
                    bpy.ops.wm.append(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                      directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                      instance_collections=False, active_collection=True)
                elif not reused_existing_asset:
                    bpy.ops.wm.append(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                      directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                      instance_collections=False, active_collection=True, do_reuse_local_id=True)
            except: pass
            all_with_new_collections=[]
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection,all_with_new_collections)
            loop =0
            for coll in all_with_new_collections[:]:
                if coll not in all_previous_collections[:] and coll.library:
                    newest_coll = coll.override_hierarchy_create(scene=bpy.context.scene, view_layer=bpy.context.view_layer, reference=coll, do_fully_editable=True)
                    if loop == 0: all_with_new_collections.append(newest_coll)
                    all_with_new_collections.remove(coll)
                    bpy.data.collections.remove(coll, do_unlink=True)
                    loop+=1
            for top_level_collection in bpy.context.scene.collection.children[:]:
                if top_level_collection not in all_with_new_collections[:]:
                    bpy.data.collections.remove(top_level_collection, do_unlink=True)
            new_obs = (
                reused_asset_objects
                if reused_existing_asset
                else list(set(bpy.data.objects) - all_previous_objects)
            )
            if not new_obs:
                pass
                return{'FINISHED'}
            all_materials = []
            imported_objects = () if reused_existing_asset else new_obs
            for ob in imported_objects:
                ob.make_local()
                if ob.type == "LIGHT": ob.data.make_local()
                elif ob.type in ["CURVES", "CURVE"]:
                    for modif in ob.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" \
                                or modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999":
                                    ob.data.make_local()
                pass
                for mat_slot in ob.material_slots:
                    if mat_slot.material:
                        mat = mat_slot.material
                        mat_slot.link = 'OBJECT'
                        try:
                            mat_slot.material = mat
                        except:
                            pass
                        if mat not in all_materials and mat != None: all_materials.append(mat)
            for matery in all_materials: matery.make_local()
            pass
            for ob in imported_objects:
                if ob.name not in bpy.context.view_layer.objects:
                    pass
                    new_obs.remove(ob)
                    bpy.data.objects.remove(ob,do_unlink=True)
            if not reused_existing_asset:
                _secret_paint_mark_imported_asset_objects(
                    new_obs,
                    asset_identifier,
                )
            new_nodes = list(set(bpy.data.node_groups) - all_previous_nodes)
            for node in new_nodes:
                if node.library:
                    pass
                    node.make_local()
            copy_hair_settings = False
            moveinteration = 1
            all_coordinates = []
            for obj in bpy.context.scene.objects:
                all_coordinates.append(str(obj.location))
            activated_scatter = False
            if justImport:
                target_location = bpy.context.scene.cursor.location
            elif select_terrain_after_import:
                target_location = Vector((0, 0, 0))
            elif activeobj.type == "MESH" and current_mode == "OBJECT" \
            or activeobj.type == "CURVES" and current_mode == "OBJECT" \
            or activeobj.type == "MESH" and current_mode == "WEIGHT_PAINT"\
            or activeobj.type == "CURVES" and current_mode == "SCULPT_CURVES":
                if switch_asset == False: activated_scatter = True
                if activeobj.type=="CURVES":
                    terrainobj = activeobj.parent
                    copy_hair_settings=True
                else: terrainobj = activeobj
                randomimported = new_obs[0]
                target_location = Vector((terrainobj.location[0] + ((terrainobj.dimensions[0]/2) + (randomimported.dimensions[0]*moveinteration)), terrainobj.location[1],terrainobj.location[2]))
            obs_without_parent_for_recenter_coll_origin =[]
            if reused_existing_asset:
                obs_without_parent_for_recenter_coll_origin = [
                    obj for obj in new_obs
                    if not obj.parent or obj.parent not in new_obs
                ]
            else:
                center = sum((obj.location for obj in new_obs), mathutils.Vector()) / len(new_obs)
                for obj in new_obs:
                    if not obj.parent and obj.visible_get() or obj.parent not in new_obs and obj.visible_get():
                        obj.location += target_location - Vector(center)
                        obs_without_parent_for_recenter_coll_origin.append(obj)
            if select_terrain_after_import and reused_existing_asset:
                for obj in new_obs:
                    try:
                        obj.hide_viewport = False
                        obj.hide_set(False)
                    except (AttributeError, RuntimeError):
                        pass
                    for collection in getattr(obj, "users_collection", ()):
                        try:
                            collection.hide_viewport = False
                        except (AttributeError, RuntimeError):
                            pass
            biome_to_use_as_paint=[]
            terrains_with_hair=[]
            for obj in new_obs:
                if obj.type == "CURVES":
                    if obj.modifiers:
                        for modif in obj.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                if obj.parent and obj.parent not in terrains_with_hair: terrains_with_hair.append(obj.parent)
            if len(terrains_with_hair) >=1:
                biome_to_use_as_paint = None
                for terrain in terrains_with_hair:
                    current_biome = []
                    for hairChild in terrain.children:
                        if hairChild.type == "CURVES" and hairChild.modifiers:
                                for modif in hairChild.modifiers:
                                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                        if hairChild not in current_biome: current_biome.append(hairChild)
                    if current_biome and biome_to_use_as_paint and len(current_biome) > len(biome_to_use_as_paint) or biome_to_use_as_paint==None: biome_to_use_as_paint = current_biome
            elif asset_type == "Collection": biome_to_use_as_paint = new_obs
            elif asset_type == "Object":
                paint_object = _secret_paint_object_asset_paint_object(
                    new_obs,
                    obs_without_parent_for_recenter_coll_origin,
                )
                biome_to_use_as_paint = [paint_object] if paint_object else []
            if not biome_to_use_as_paint and not justImport:
                self.report({'WARNING'}, "The selected asset has no paintable object")
                continue
            secretpaint_update_modifier_f(context,upadte_provenance="def paint_from_library_function(self, context, event, **kwargs)")
            importpainting_multiple_assets = True if len(sel_assets) >=2 else False
            if select_terrain_after_import:
                if terrain_selection_started:
                    continue
                selection_object = None
                for imported_system in biome_to_use_as_paint or ():
                    if not _secret_paint_q_is_paint_system(imported_system):
                        continue
                    selection_object = _secret_paint_q_single_system_brush_object(
                        imported_system
                    )
                    if selection_object in new_obs or reused_existing_asset:
                        break
                    selection_object = None
                if selection_object is None:
                    selection_object = next(
                        (
                            obj for obj in biome_to_use_as_paint or ()
                            if obj in new_obs and
                            not _secret_paint_1731_paint_modifier(obj) and
                            obj.type in {"MESH", "EMPTY", "CURVE", "CURVES"}
                        ),
                        None,
                    )
                if selection_object is None:
                    self.report({'WARNING'}, "The imported asset has no paintable object")
                else:
                    terrain_selection_started = _secret_paint_asset_start_terrain_selection(
                        self,
                        context,
                        selection_object,
                    )
            elif activated_scatter:
                pass
                secretpaint_function(self, context, event, activeobj=activeobj, objselection=biome_to_use_as_paint, importpainting_multiple_assets=importpainting_multiple_assets)
            elif switch_asset:
                if asset_type == "Object":
                    paintbrushswitch_f(self, context, activeobj=biome_to_use_as_paint[0], objselection=[activeobj], current_mode=current_mode)
                elif asset_type == "Collection":
                    paintbrushswitch_f(self, context, activeobj=activeobj, objselection=biome_to_use_as_paint, current_mode=current_mode)
            elif justImport:
                for obj in new_obs:
                    try:
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                    except:pass
    if coll_to_hide and not select_terrain_after_import:
        coll_to_hide.hide_viewport = FoundHiddenCollection_status
    if new_coll_was_created_so_hide_viewport and not select_terrain_after_import:
        new_coll.hide_viewport = True
        new_coll.hide_render = True
    return {'FINISHED'}
class paint_from_library(bpy.types.Operator):
    """Import and paint with the selected object or collection"""
    bl_idname = "secret.paint_from_library"
    bl_label = "Import Asset and Paint"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        paint_from_library_function(self, context, event)
        return {'FINISHED'}
class paint_from_library_switch(bpy.types.Operator):
    """switch brush object from the asset library"""
    bl_idname = "secret.paint_from_library_switch"
    bl_label = "Import Asset and Switch"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        paint_from_library_function(self, context, event, switch_asset = True)
        return {'FINISHED'}
class paint_from_library_justimport(bpy.types.Operator):
    """Just Import biome from library"""
    bl_idname = "secret.paint_from_library_justimport"
    bl_label = "Import Asset"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        paint_from_library_function(self, context, event, justImport = True)
        return {'FINISHED'}
def checkboxImportWithoutPainting_f(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.operator("secret.paint_from_library", icon='BRUSH_DATA', text="Paint")
    row.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxHideImported", text="", icon='RESTRICT_RENDER_ON' if bpy.context.preferences.addons[__package__].preferences.checkboxHideImported else 'RESTRICT_RENDER_OFF')
def shared_material_f(self,context):
    common_name = "Shared "+ str(context.scene.mypropertieslist.shared_material_index)
    if common_name not in bpy.data.node_groups:
        all_nodes_before_import =[node_tree for node_tree in bpy.data.node_groups]
        activeobj = bpy.context.active_object
        objselection = bpy.context.selected_objects
        file_path = _secret_paint_node_library_path()
        inner_path = "NodeTree"
        object_name = "Shared"
        bpy.ops.wm.append(
            filepath=os.path.join(file_path, inner_path, object_name),
            directory=os.path.join(file_path, inner_path),
            filename=object_name)
        all_nodes_after_import = [node_tree for node_tree in bpy.data.node_groups]
        new_node = [x for x in all_nodes_after_import if x not in all_nodes_before_import]
        new_node[0].name = common_name
        bpy.context.view_layer.objects.active = activeobj
        for x in objselection: x.select_set(True)
    Remove_Enabled = False
    try: nodeys = bpy.context.active_object.active_material.node_tree.nodes
    except:
        self.report({'ERROR'}, "Select an object with at least one Material")
        return {'FINISHED'}
    for nod in nodeys:
        if nod.type=="GROUP" and nod.node_tree and nod.node_tree == bpy.data.node_groups.get(common_name): Remove_Enabled = True
    for obj in bpy.context.selected_objects:
        for mat_slot in obj.material_slots:
            if mat_slot.material:
                active_material=mat_slot.material
                for node in active_material.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        if node.inputs["Base Color"].links and node.inputs["Base Color"].links[0].from_node.type == "GROUP" and node.inputs["Base Color"].links[0].from_node.node_tree.name.startswith("Shared"):
                            if Remove_Enabled:
                                output_sock = []
                                input_sock = []
                                for link in active_material.node_tree.links:
                                    if link.to_node == node.inputs["Base Color"].links[0].from_node: input_sock.append(link.from_socket)
                                    if link.from_node == node.inputs["Base Color"].links[0].from_node: output_sock.append(link.to_socket)
                                active_material.node_tree.nodes.remove(node.inputs["Base Color"].links[0].from_node)
                                for output in output_sock:
                                    for input in input_sock:
                                        active_material.node_tree.links.new(output, input)
                            else:
                                node.inputs["Base Color"].links[0].from_node.node_tree = bpy.data.node_groups.get(common_name)
                        elif not node.inputs["Base Color"].links and not Remove_Enabled:
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y - 115)
                            active_material.node_tree.links.new(common_material_group.outputs["Base Color"], node.inputs["Base Color"])
                            common_material_group.inputs["Color"].default_value = node.inputs["Base Color"].default_value
                            common_material_group.select = True
                        elif not Remove_Enabled:
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y - 115)
                            existing_link = node.inputs["Base Color"].links[0]
                            existing_node = existing_link.from_node
                            output_sockets = []
                            for link in active_material.node_tree.links:
                                if link.from_node == existing_node: output_sockets.append(link.to_socket)
                            if hasattr(existing_node, 'data_type') and existing_node.data_type=="RGBA": active_material.node_tree.links.new(existing_node.outputs[2], common_material_group.inputs["Color"])
                            else: active_material.node_tree.links.new(existing_node.outputs[existing_link.from_socket.name], common_material_group.inputs["Color"])
                            for output in output_sockets:
                                active_material.node_tree.links.new(common_material_group.outputs["Base Color"], output)
                        if node.inputs["Roughness"].links and node.inputs["Roughness"].links[0].from_node.type == "GROUP" and node.inputs["Roughness"].links[0].from_node.node_tree.name.startswith("Shared"):
                            if Remove_Enabled:
                                output_sock = []
                                input_sock = []
                                for link in active_material.node_tree.links:
                                    if link.to_node == node.inputs["Roughness"].links[0].from_node: input_sock.append(link.from_socket)
                                    if link.from_node == node.inputs["Roughness"].links[0].from_node: output_sock.append(link.to_socket)
                                active_material.node_tree.nodes.remove(node.inputs["Roughness"].links[0].from_node)
                                for output in output_sock:
                                    for input in input_sock:
                                        active_material.node_tree.links.new(output, input)
                            else:
                                node.inputs["Roughness"].links[0].from_node.node_tree = bpy.data.node_groups.get(common_name)
                        elif not node.inputs["Roughness"].links and not Remove_Enabled:
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y - 304)
                            active_material.node_tree.links.new(common_material_group.outputs["Roughness"], node.inputs["Roughness"])
                            common_material_group.inputs["Roughness"].default_value = node.inputs["Roughness"].default_value
                            common_material_group.select = True
                        elif not Remove_Enabled:
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y - 280)
                            existing_link = node.inputs["Roughness"].links[0]
                            existing_node = existing_link.from_node
                            output_sockets = []
                            for link in active_material.node_tree.links:
                                if link.from_node == existing_node: output_sockets.append(link.to_socket)
                            active_material.node_tree.links.new(existing_node.outputs[existing_link.from_socket.name], common_material_group.inputs["Roughness"])
                            for output in output_sockets:
                                active_material.node_tree.links.new(common_material_group.outputs["Roughness"], output)
                    elif node.type == 'OUTPUT_MATERIAL':
                        if node.inputs["Surface"].links and node.inputs["Surface"].links[0].from_node.type == "GROUP" and node.inputs["Surface"].links[0].from_node.node_tree.name.startswith("Shared"):
                            if Remove_Enabled:
                                output_sock = []
                                input_sock = []
                                for link in active_material.node_tree.links:
                                    if link.to_node == node.inputs["Surface"].links[0].from_node: input_sock.append(link.from_socket)
                                    if link.from_node == node.inputs["Surface"].links[0].from_node: output_sock.append(link.to_socket)
                                active_material.node_tree.nodes.remove(node.inputs["Surface"].links[0].from_node)
                                for output in output_sock:
                                    for input in input_sock:
                                        active_material.node_tree.links.new(output, input)
                            else:
                                node.inputs["Surface"].links[0].from_node.node_tree = bpy.data.node_groups.get(common_name)
                        elif not node.inputs["Surface"].links and not Remove_Enabled:
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y -38)
                            active_material.node_tree.links.new(common_material_group.outputs["Material Output"], node.inputs["Surface"])
                            common_material_group.select = True
                        elif not Remove_Enabled:
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y -38)
                            existing_link = node.inputs["Surface"].links[0]
                            existing_node = existing_link.from_node
                            output_sockets = []
                            for link in active_material.node_tree.links:
                                if link.from_node == existing_node: output_sockets.append(link.to_socket)
                            active_material.node_tree.links.new(existing_node.outputs[existing_link.from_socket.name], common_material_group.inputs["Shader"])
                            for output in output_sockets:
                                active_material.node_tree.links.new(common_material_group.outputs["Material Output"], output)
    return {'FINISHED'}
class shared_material(bpy.types.Operator):
    """Add or remove a shared node group in front of every PrincipledBSDF in order to control the Color and Roughness of all the selected objects at the same time. Doesn't work on custom node groups (there is no procedural way to know which socket controls what)"""
    bl_idname = "secret.shared_material"
    bl_label = "Toggle Shared Material"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        shared_material_f(self,context)
        return {'FINISHED'}
class circular_array(bpy.types.Operator):
    """Quick Shortcut to create a circular array with the selected object"""
    bl_idname = "secret.circular_array"
    bl_label = "Circular Array"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        secretpaint_function(self, context,circulararray=True)
        return {'FINISHED'}
class straight_array(bpy.types.Operator):
    """Quick Shortcut to create an instanced array with the selected object"""
    bl_idname = "secret.straight_array"
    bl_label = "Straight Array"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        secretpaint_function(self, context,straightarray=True)
        return {'FINISHED'}
def context14438(self, context):
    activeobj = bpy.context.active_object
    objselection = bpy.context.selected_objects
    if len(objselection) >=2:
        for hair in objselection:
            if hair.type == "CURVES" and hair.modifiers or hair.type == "CURVE" and hair.modifiers:
                for modif in hair.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        try:
                            newmat = bpy.context.active_object.active_material.name
                        except AttributeError:
                            self.report({'ERROR'}, "There is no material to copy.")
                            return {"CANCELLED"}
                        hair.data.materials.clear()
                        for mat_slot in activeobj.material_slots:
                            if mat_slot.material: hair.data.materials.append(mat_slot.material)
                        bpy.context.view_layer.objects.active = hair
                        hair_modifier = _secret_paint_1731_paint_modifier(hair)
                        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_39", True)
                        _secret_paint_1731_set_modifier_value(hair_modifier, "Input_40", bpy.data.materials[newmat])
                        hair.location = hair.location
        bpy.data.objects[activeobj.name].select_set(False)
    return {'FINISHED'}
class orencurvecopymat(bpy.types.Operator):
    """Changes the material assigned to the Brush object, without switching the object itself"""
    bl_idname = "secret.switchmaterial"
    bl_label = "Switch Material"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        context14438(self, context)
        return {'FINISHED'}
def update_collapsed_list(self, context):
    pass
    return{'FINISHED'}
class switchtoweightzero(bpy.types.Operator):
    """In Weight paint mode, press the shortcut to toggle between a value of 0 and 1"""
    bl_idname = "secret.switchtoweightzero"
    bl_label = "Toggle Weight 0/1"
    def execute(self, context):
        if bpy.context.scene.tool_settings.vertex_group_weight == 0:
            bpy.context.scene.tool_settings.vertex_group_weight = 1
        else:
            bpy.context.scene.tool_settings.vertex_group_weight = 0
        return {'FINISHED'}
def curveseparate_function(context):
    activeobj = bpy.context.active_object
    activeobj.select_set(True)
    objselection = bpy.context.selected_objects
    saveMode = bpy.context.object.mode
    if bpy.context.object.mode == "OBJECT":
        if activeobj.type == "CURVES":
            for obj in objselection:
                Coll_of_Active = []
                for i in obj.users_collection:
                    layer_collection = bpy.context.view_layer.layer_collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                obj.select_set(False)
                newobj = obj.copy()
                bpy.data.collections[Coll_of_Active.name].objects.link(newobj)
                newobj.data = bpy.data.hair_curves.new("Secret Paint")
                newobj.data.surface = obj.parent
                for uvmap in newobj.parent.data.uv_layers:
                    if uvmap.active_render: newobj.data.surface_uv_map = uvmap.name
                bpy.context.view_layer.objects.active = newobj
                for material_slot in obj.material_slots:
                    if material_slot.material and material_slot.material.name not in newobj.data.materials:
                        newobj.data.materials.append(material_slot.material)
            bpy.ops.object.mode_set(mode="SCULPT_CURVES")
        elif activeobj.type == "CURVE":
            for obj in objselection:
                Coll_of_Active = []
                for i in obj.users_collection:
                    layer_collection = bpy.context.view_layer.layer_collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                obj.select_set(False)
                newobj = obj.copy()
                bpy.data.collections[Coll_of_Active.name].objects.link(newobj)
                newobj.data = bpy.data.curves.new("Secret Paint", "CURVE")
                bpy.context.view_layer.objects.active = newobj
                for material_slot in obj.material_slots:
                    if material_slot.material and material_slot.material.name not in newobj.data.materials:
                        newobj.data.materials.append(material_slot.material)
            bpy.ops.object.mode_set(mode="EDIT")
    else:
        if activeobj.type=="CURVES":
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False})
            newCurve = bpy.context.active_object
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.curves.select_linked()
            bpy.ops.curves.select_all(action='INVERT')
            bpy.ops.transform.resize(value=(0, 0, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False,
                                     snap_target='CENTER', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
            bpy.ops.curves.select_all(action='SELECT')
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.curves.select_linked()
            bpy.ops.transform.resize(value=(0, 0, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False,
                                     snap_target='CENTER', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
            bpy.ops.curves.select_all(action='SELECT')
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = bpy.data.objects[newCurve.name]
            bpy.ops.object.mode_set(mode="SCULPT_CURVES")
            return newCurve
        elif activeobj.type == "CURVE":
            try:
                bpy.ops.curve.select_all(action='INVERT')
                bpy.ops.curve.separate()
                bpy.ops.curve.select_all(action='SELECT')
                for x in bpy.context.selected_objects:bpy.data.objects[x.name].select_set(False)
                activeobj.select_set(True)
            except:
                bpy.ops.curve.select_all(action='SELECT')
                bpy.ops.curve.separate()
                bpy.ops.curve.select_all(action='SELECT')
                for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
                activeobj.select_set(True)
    return {'FINISHED'}
class curveseparate(bpy.types.Operator):
    """Separate the selected curve or hair from the active object into a new one. If nothing is selected, duplicate the curve object"""
    bl_idname = "secret.curveseparate"
    bl_label = "Separate"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        curveseparate_function(context)
        return {'FINISHED'}
def get_all_children(parent,all_children,context):
    for children in parent.children:
        if children.visible_get(): all_children.append(children)
        get_all_children(children,all_children,context)
    return all_children
def get_all_DownwardsDependencies(activeobj, final_assemblies_to_process, all_assemblies_and_their_parent, context):
    for obj in all_assemblies_and_their_parent:
        if obj[1] == activeobj:
            if obj[0] not in final_assemblies_to_process: final_assemblies_to_process.append(obj[0])
            get_all_DownwardsDependencies(obj[0], final_assemblies_to_process, all_assemblies_and_their_parent, context)
    return final_assemblies_to_process
def get_first_parent_Upwards(activeobj, context):
    parent_of_current_object = None
    if activeobj.modifiers and activeobj.modifiers[0].name.startswith("Secret Assembly") and activeobj.modifiers[0].type=="NODES" and activeobj.modifiers[0].node_group and "ASSEMBLY" in activeobj.modifiers[0].node_group.name:
        for input in activeobj.modifiers[0].node_group.interface.items_tree:
            if input.name == "Parent":
                parent_of_current_object = _secret_paint_1731_modifier_value(
                    activeobj.modifiers[0], input.identifier, None
                )
                break
    if parent_of_current_object != None: return get_first_parent_Upwards(parent_of_current_object, context)
    else: return activeobj
def assembly_1(self,context,**kwargs):
    start_time = time.perf_counter()
    original_activeobj = activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    if activeobj == None and bpy.context.selected_objects: activeobj = original_activeobj= bpy.context.selected_objects[0]
    if activeobj == None:
        self.report({'ERROR'}, "Select the Parent Object. Its children will be automatically included in the Assembly")
        return{'FINISHED'}
    parent_with_most_children = bpy.context.selected_objects[0]
    for ob in bpy.context.selected_objects:
        ob_childrens = [children for children in ob.children if children in bpy.context.selected_objects]
        parent_with_most_children_children = [children for children in parent_with_most_children.children if children in bpy.context.selected_objects]
        if not ob.parent and len(ob_childrens) > len(parent_with_most_children_children) \
        or ob.parent and ob.parent not in bpy.context.selected_objects and len(ob.children) > len(parent_with_most_children.children):
            parent_with_most_children = ob
    common_parent_has_children_in_the_selected_objects = False
    for children in parent_with_most_children.children:
        if children in bpy.context.selected_objects:
            common_parent_has_children_in_the_selected_objects = True
            break
    if common_parent_has_children_in_the_selected_objects: activeobj = original_activeobj = parent_with_most_children
    else: activeobj = original_activeobj
    for ob in bpy.context.selected_objects:
        if ob != activeobj:
            if not ob.parent \
            or ob.parent and ob.parent not in bpy.context.selected_objects:
                ob_matrix_world = ob.matrix_world.copy()
                ob.parent=activeobj
                ob.matrix_world = ob_matrix_world
    all_objs_used_as_parents = []
    all_assemblies_and_their_parent = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.modifiers:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                    node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                    for input in node_group_inputs_temp:
                        if input.socket_type == "NodeSocketObject" and input.name == "Parent":
                            assembly_parent = _secret_paint_1731_modifier_value(modif, input.identifier, None)
                            all_assemblies_and_their_parent.append((obj, assembly_parent))
                            if assembly_parent not in all_objs_used_as_parents: all_objs_used_as_parents.append(assembly_parent)
    final_assemblies_to_process =[]
    first_parent = get_first_parent_Upwards(activeobj, context)
    final_assemblies_to_process.append(first_parent)
    get_all_DownwardsDependencies(first_parent, final_assemblies_to_process, all_assemblies_and_their_parent, context)
    if activeobj in final_assemblies_to_process:
        final_assemblies_to_process.remove(activeobj)
        final_assemblies_to_process.append(activeobj)
    else: final_assemblies_to_process.append(activeobj)
    main_loops=0
    for obj in final_assemblies_to_process:
        there_are_assemblies_to_update, processing_original_activeobj = assembly_2(self, context, activeobj=obj, original_activeobj=original_activeobj)
        main_loops+=1
    if processing_original_activeobj and there_are_assemblies_to_update==False:
        if len(bpy.context.selected_objects) >= 2: self.report({'INFO'}, "Created a New Assembly.  You only need to select the Parent Object. Its children will be automatically included in the Assembly")
        else: self.report({'INFO'}, "Created a New Assembly")
        bpy.ops.transform.translate('INVOKE_DEFAULT', use_proportional_edit=False)
    elif main_loops >=3:
        self.report({'INFO'}, "Updated Interdependent Assemblies")
        for ob in final_assemblies_to_process:
            try:ob.select_set(True)
            except:pass
    else:
        self.report({'INFO'}, "Updated Existing Assembly")
        for ob in final_assemblies_to_process:
            try:ob.select_set(True)
            except:pass
    end_time = time.perf_counter()
    pass
    start_time = time.perf_counter()
    return{'FINISHED'}
def assembly_2(self,context,**kwargs):
    start_time_2 = time.perf_counter()
    original_activeobj = kwargs.get("original_activeobj") if "original_activeobj" in kwargs else bpy.context.active_object
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    processing_original_activeobj = True if activeobj == original_activeobj else False
    there_are_assemblies_to_update = False
    all_children=[]
    all_materials_of_parent_and_children=[]
    activeobj_referenced_by_constraint = False
    for ob in bpy.data.objects:
        if ob.constraints and not activeobj_referenced_by_constraint:
            for con in ob.constraints:
                if hasattr(con, 'target') and con.target == activeobj:
                    activeobj_referenced_by_constraint = True
                    break
    if activeobj.type == "MESH" and activeobj.modifiers and not activeobj.children and processing_original_activeobj and not activeobj_referenced_by_constraint:
        for modif in activeobj.modifiers:
            if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                for input in node_group_inputs_temp:
                    if input.socket_type == "NodeSocketObject" and input.name == "Parent":
                        activeobj = _secret_paint_1731_modifier_value(modif, input.identifier, None)
                        break
    for material_slot in activeobj.material_slots:
        if material_slot.material and material_slot.material not in all_materials_of_parent_and_children: all_materials_of_parent_and_children.append(material_slot.material)
    all_modif_to_update =[]
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.modifiers:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                    node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                    for input in node_group_inputs_temp:
                        if input.socket_type == "NodeSocketObject" and input.name == "Parent" and _secret_paint_1731_modifier_value(modif, input.identifier, None) == activeobj and modif not in all_modif_to_update:
                            all_modif_to_update.append((obj,modif))
                            there_are_assemblies_to_update = True
                            break
    if there_are_assemblies_to_update or processing_original_activeobj:
        if all_modif_to_update and len(all_modif_to_update) != all_modif_to_update[0][0].data.users:
            new_mesh_data = all_modif_to_update[0][0].data.copy()
            for obbb in all_modif_to_update:
                obbb[0].data = new_mesh_data
        node_group = bpy.data.node_groups[activeobj.name + "ASSEMBLY"] if activeobj.name + "ASSEMBLY" in bpy.data.node_groups else None
        if node_group and node_group.users==0: bpy.data.node_groups.remove(node_group)
        node_group = bpy.data.node_groups.new("GeometryNodeGroup", 'GeometryNodeTree')
        node_group.name = activeobj.name + "ASSEMBLY"
        for modif in all_modif_to_update: modif[1].node_group = node_group
        if processing_original_activeobj and there_are_assemblies_to_update==False:
            Coll_of_Active = []
            original_collection = bpy.context.view_layer.active_layer_collection
            for i in activeobj.users_collection:
                Coll_of_Active = recurLayerCollection(bpy.context.view_layer.layer_collection, i.name)
                bpy.context.view_layer.active_layer_collection = Coll_of_Active
            mesh = bpy.data.meshes.new("Secret Assembly")
            obj = bpy.data.objects.new(activeobj.name + "ASSEMBLY", mesh)
            obj.location = activeobj.matrix_world.to_translation()
            bpy.context.collection.objects.link(obj)
            for x in bpy.context.selected_objects: x.select_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            modifier = obj.modifiers.new(name="Secret Assembly", type='NODES')
            modifier.node_group = node_group
            bpy.context.view_layer.active_layer_collection = original_collection
        input = node_group.nodes.new('NodeGroupInput')
        input.location = (-500,0)
        node_group.interface.clear()
        if bpy.app.version_string >= "4.0.0":
            node_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
            node_group.interface.new_socket(name='Realize Instances', in_out='INPUT', socket_type='NodeSocketBool')
            node_group.interface.new_socket(name='Parent', in_out='INPUT', socket_type='NodeSocketObject')
        elif bpy.app.version_string < "4.0.0":
            node_group.outputs.new(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
            node_group.outputs.new(type='NodeSocketGeometry', name='Geometry')
            node_group.outputs.new(type='NodeSocketObject', name='Parent')
        output = node_group.nodes.new('NodeGroupOutput')
        output.location = (+1200,0)
        if bpy.app.version_string >= "4.0.0": node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        elif bpy.app.version_string < "4.0.0": node_group.inputs.new(type='NodeSocketGeometry', name='GEO')
        JoinGeometry = node_group.nodes.new('GeometryNodeJoinGeometry')
        JoinGeometry.location = (+800,0)
        realize_instances_node = node_group.nodes.new(type='GeometryNodeRealizeInstances')
        realize_instances_node.location = (+1000,0)
        realize_instances_node.inputs[2].default_value = False
        parent_info_node = node_group.nodes.new(type='GeometryNodeObjectInfo')
        parent_info_node.location = (-300,0)
        parent_info_node.inputs[0].default_value = activeobj
        parent_info_node.inputs[1].default_value = True
        CombineTransform = node_group.nodes.new('FunctionNodeCombineTransform')
        CombineTransform.location = (-100,0)
        SetInstanceTransform = node_group.nodes.new('GeometryNodeSetInstanceTransform')
        SetInstanceTransform.location = (+400,0)
        node_group.links.new(CombineTransform.outputs[0], SetInstanceTransform.inputs[2])
        node_group.links.new(parent_info_node.outputs[4], SetInstanceTransform.inputs[0])
        node_group.links.new(parent_info_node.outputs[2], CombineTransform.inputs[1])
        node_group.links.new(parent_info_node.outputs[3], CombineTransform.inputs[2])
        if activeobj.type != "ARMATURE": node_group.links.new(SetInstanceTransform.outputs[0], JoinGeometry.inputs[0])
        node_group.links.new(input.outputs[2], parent_info_node.inputs[0])
        node_group.links.new(JoinGeometry.outputs[0], realize_instances_node.inputs[0])
        node_group.links.new(input.outputs[1], realize_instances_node.inputs[2])
        get_all_children(activeobj,all_children,context)
        for ob in bpy.data.objects:
            if ob.constraints:
                for con in ob.constraints:
                    if hasattr(con, 'target') and con.target == activeobj and ob not in all_children \
                    or hasattr(con, 'target') and con.target in all_children and ob not in all_children: all_children.append(ob)
        childloop = 2
        for children in all_children:
            for material_slot in children.material_slots:
                if material_slot.material and material_slot.material not in all_materials_of_parent_and_children: all_materials_of_parent_and_children.append(material_slot.material)
            if bpy.app.version_string >= "4.0.0": node_group.interface.new_socket(name='Child', in_out='INPUT', socket_type='NodeSocketObject')
            elif bpy.app.version_string < "4.0.0": node_group.outputs.new(type='NodeSocketObject', name='Object')
            children_info_node = node_group.nodes.new(type='GeometryNodeObjectInfo')
            children_info_node.location = (-300, -300 *childloop)
            children_info_node.inputs[0].default_value = children
            children_info_node.inputs[1].default_value = True
            CombineTransform = node_group.nodes.new('FunctionNodeCombineTransform')
            CombineTransform.location = (+200, -300 *childloop)
            SetInstanceTransform = node_group.nodes.new('GeometryNodeSetInstanceTransform')
            SetInstanceTransform.location = (+400, -300 *childloop)
            VectorMath1 = node_group.nodes.new('ShaderNodeVectorMath')
            VectorMath1.operation = 'SUBTRACT'
            VectorMath1.location = (-100, -300 *childloop)
            node_group.links.new(input.outputs[childloop+1], children_info_node.inputs[0])
            node_group.links.new(children_info_node.outputs[1], VectorMath1.inputs[0])
            node_group.links.new(VectorMath1.outputs[0], CombineTransform.inputs[0])
            node_group.links.new(children_info_node.outputs[2], CombineTransform.inputs[1])
            node_group.links.new(children_info_node.outputs[3], CombineTransform.inputs[2])
            node_group.links.new(children_info_node.outputs[4], SetInstanceTransform.inputs[0])
            node_group.links.new(CombineTransform.outputs[0], SetInstanceTransform.inputs[2])
            if children.type != "ARMATURE": node_group.links.new(SetInstanceTransform.outputs[0], JoinGeometry.inputs[0])
            node_group.links.new(parent_info_node.outputs[1], VectorMath1.inputs[1])
            childloop += 1
        node_group_inputs = node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else node_group.inputs
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group == node_group:
                        obj.data.materials.clear()
                        for mat in all_materials_of_parent_and_children:
                            if mat.name not in obj.data.materials: obj.data.materials.append(mat)
                        loop = 0
                        for input in node_group_inputs:
                            if loop == 3:
                                _secret_paint_1731_set_modifier_value(modif, input.identifier, activeobj)
                            elif loop >= 4:
                                _secret_paint_1731_set_modifier_value(modif, input.identifier, all_children[loop - 4])
                            loop += 1
        node_group.links.new(realize_instances_node.outputs[0], output.inputs[0])
    end_time = time.perf_counter()
    pass
    start_time = time.perf_counter()
    return there_are_assemblies_to_update, processing_original_activeobj
class assembly(bpy.types.Operator):
    """Group the Active Object, its children and constraints into a non-destructive assembly. Alt + Click to merge into a mesh. You can add new objects to the assembly by simply parenting them to the original object. You can then update the assembly by pressing the button again. You can also create assemblies within assemblies to keep modelling procedurally. This works with everything, even complex rigs. It's a better version of collection instances with none of the drawbacks"""
    bl_idname = "secret.assembly"
    bl_label = "Secret Assembly_f"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        if blender_version_tuple < (4, 2, 0):
            self.report({'ERROR'}, "Secret Paint Assemblies are only available from Blender 4.2 due to a lack of nodes")
        elif event.alt: convert_and_join_f(self,context)
        else: assembly_1(self,context)
        return {'FINISHED'}
def export_unreal_f(self,context,export_textures):
    blend_file_path = bpy.data.filepath
    directory = os.path.dirname(blend_file_path)
    bpy.ops.wm.usd_export(
    filepath=os.path.join(directory, os.path.basename(blend_file_path) + ".usdc"),
    selected_objects_only=True,
    export_animation=False,
    export_hair=True,
    export_uvmaps=True,
    rename_uvmaps=True,
    export_mesh_colors=True,
    export_normals=True,
    export_materials=True,
    export_subdivision='BEST_MATCH',
    export_armatures=True,
    only_deform_bones=True,
    export_shapekeys=True,
    use_instancing=True,
    evaluation_mode='VIEWPORT',
    generate_preview_surface=True,
    generate_materialx_network=False,
    convert_orientation=False,
    export_global_forward_selection='NEGAT'
    'IVE_Z',
    export_global_up_selection='Y',
    relative_paths=True,
    xform_op_mode='TOS',
    root_prim_path="/root",
    export_custom_properties=True,
    custom_properties_namespace="userProperties",
    author_blender_name=True,
    convert_world_material=False,
    allow_unicode=False,
    export_meshes=True,
    export_lights=False,
    export_cameras=True,
    export_curves=True,
    export_volumes=True,
    triangulate_meshes=False,
    quad_method='SHORTEST_DIAGONAL',
    ngon_method='BEAUTY',
    usdz_downscale_size='KEEP',
    usdz_downscale_custom_size=128)
    return{'FINISHED'}
    self.report({'INFO'}, "Exported Selected Objects as USD")
    return{'FINISHED'}
class export_unreal(bpy.types.Operator):
    """Export selected as USD. Works with Assemblies, Paint Systems or regular meshes. To import in Unreal Engine: DO NOT drag and drop the USD, instead go to: File > Import Into Level, this will import everything to the scene with correct location and rotation for each instanced object"""
    bl_idname = "secret.export_unreal"
    bl_label = "USD Export"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        export_textures = True
        export_unreal_f(self,context,export_textures)
        return {'FINISHED'}
class MyPropertiesClass(bpy.types.PropertyGroup):
    dropdownpanel: bpy.props.BoolProperty(default=False, update=update_collapsed_list)
    shared_material_index : bpy.props.IntProperty(name= "Shared Material Index", description="Choose which Shared node group get assigned to the selected objects", soft_min= 1, soft_max= 32, default= 1)
    checkboxImportWithoutPainting: bpy.props.BoolProperty(name="Import And Paint",description="When transfering a Biome to another mesh, also transfer the material of the target mesh",default=True)
    checkboxTransferMaterialWithBiome: bpy.props.BoolProperty(name="Terrain material with Biome",description="When transfering a Biome to another mesh, also transfer the material of the target mesh",default=False)
    checkboxatoncediffuse: bpy.props.BoolProperty(name="COL", description="Bake diffuse", default=True)
    checkboxatoncerough: bpy.props.BoolProperty(name="RGH", description="Bake roughness", default=True)
    checkboxatoncenorm: bpy.props.BoolProperty(name="NRM", description="Bake normal", default=True)
    checkboxatonceemit: bpy.props.BoolProperty(name="EMI", description="Bake emission", default=False)
    checkboxatoncecombined: bpy.props.BoolProperty(name="COMB", description="Bake combined direct and indirect", default=False)
_SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED = False


def _secret_paint_object_mode_pie_builtin_mode_count(active_object):
    object_type = getattr(active_object, "type", "")
    if object_type in {"MESH", "GREASEPENCIL"}:
        return 6
    if object_type in {"CURVES", "ARMATURE"}:
        return 3
    if object_type in {"CURVE", "SURFACE", "META", "FONT", "LATTICE"}:
        return 2
    return 1


def _secret_paint_object_mode_pie_draw(self, context):
    active_object = context.active_object
    if active_object is None:
        return
    pie = self.layout.menu_pie()
    native_mode_count = _secret_paint_object_mode_pie_builtin_mode_count(
        active_object
    )
    for _slot in range(native_mode_count, 6):
        pie.separator()
    pie.operator_context = 'INVOKE_DEFAULT'
    pie.operator(
        "secret.paint",
        text="Secret Paint",
        icon='BRUSH_DATA',
    )


def _secret_paint_register_object_mode_pie():
    global _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED
    if _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED:
        return
    menu = getattr(bpy.types, "VIEW3D_MT_object_mode_pie", None)
    if menu is None:
        return
    try:
        menu.remove(_secret_paint_object_mode_pie_draw)
    except Exception:
        pass
    menu.append(_secret_paint_object_mode_pie_draw)
    _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED = True


def _secret_paint_unregister_object_mode_pie():
    global _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED
    menu = getattr(bpy.types, "VIEW3D_MT_object_mode_pie", None)
    if menu is not None:
        try:
            menu.remove(_secret_paint_object_mode_pie_draw)
        except Exception:
            pass
    _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED = False


addon_keymaps = []
_SECRET_PAINT_KEYMAP_DEFINITIONS = (
    ("Object Mode", "EMPTY", "secret.toggle_viewport_tab_bookmark", "W", {"shift": True}),
    ("Sculpt Curves", "EMPTY", "secret.toggle_viewport_tab_bookmark", "W", {"shift": True}),
    ("User Interface", "EMPTY", "secret.panel_keyboard_reorder", "G", {}),
    ("User Interface", "EMPTY", "secret.panel_keyboard_delete", "X", {}),
    ("Object Mode", "EMPTY", "secret.paint", "Q", {}),
    ("Sculpt Curves", "EMPTY", "secret.paint", "Q", {}),
    ("Sculpt Curves", "EMPTY", "secret.paint_change_terrain", "Q", {"ctrl": True}),
    ("Weight Paint", "EMPTY", "secret.paint", "Q", {}),
    ("Curve", "EMPTY", "secret.paint", "Q", {}),
    ("File Browser Main", "FILE_BROWSER", "secret.paint_from_library", "Q", {}),
    ("File Browser Main", "FILE_BROWSER", "secret.paint_from_library_switch", "Q", {"shift": True}),
    ("File Browser Main", "FILE_BROWSER", "secret.paint_from_library_justimport", "Q", {"alt": True}),
    ("Object Mode", "EMPTY", "secret.paintbrushswitch", "Q", {"shift": True}),
    ("Sculpt Curves", "EMPTY", "secret.paintbrushswitch", "Q", {"shift": True}),
    ("Sculpt Curves", "EMPTY", "secret.brush_density_while_painting", "D", {}),
    ("Sculpt Curves", "EMPTY", "secret.accumulate_density_stroke_start", "LEFTMOUSE", {"head": True}),
    ("Sculpt Curves", "EMPTY", "secret.right_click_delete_while_painting", "RIGHTMOUSE", {"head": True}),
    ("Weight Paint", "EMPTY", "secret.paintbrushswitch", "Q", {"shift": True}),
    ("Curve", "EMPTY", "secret.paintbrushswitch", "Q", {"shift": True}),
    ("Object Mode", "EMPTY", "secret.assembly", "D", {"ctrl": True}),
    ("Object Mode", "EMPTY", "secret.group", "M", {"alt": True}),
    ("Outliner", "OUTLINER", "secret.group", "M", {"alt": True}),
    ("Curve", "EMPTY", "secret.curveseparate", "Q", {"ctrl": True, "alt": True}),
    ("Sculpt Curves", "EMPTY", "secret.curveseparate", "Q", {"ctrl": True, "alt": True}),
)
class SECRET_PAINT_OT_open_keymap_preferences(bpy.types.Operator):
    bl_idname = "secret.open_keymap_preferences"
    bl_label = "Edit Shortcuts"
    bl_description = "Open Blender's Keymap preferences and show Secret Paint shortcuts"
    bl_options = {'INTERNAL'}
    def execute(self, context):
        context.preferences.active_section = 'KEYMAP'
        space = context.space_data
        if space is not None and space.type == 'PREFERENCES':
            space.filter_type = 'NAME'
            space.filter_text = 'secret.'
        return {'FINISHED'}
class secret_menu(bpy.types.AddonPreferences):
    bl_idname = __package__
    auto_check_update : bpy.props.BoolProperty(name="Auto-check for Update", description="If enabled, auto-check for updates using an interval", default=True)
    updater_interval_months : bpy.props.IntProperty(name='Months', description="Number of months between checking for updates", default=0, min=0)
    updater_interval_days : bpy.props.IntProperty(name='Days',description="Number of days between checking for updates",default=1,min=0,max=31)
    updater_interval_hours : bpy.props.IntProperty(name='Hours',description="Number of hours between checking for updates",default=0,min=0,max=23)
    updater_interval_minutes : bpy.props.IntProperty(name='Minutes',description="Number of minutes between checking for updates",default=0,min=0,max=59)
    checkboxKeepManualWhenTransferBiome: bpy.props.BoolProperty(name="Keep Manual When Transferring Biomes", description="When transferring biomes from a terrain to another: keep the paint systems in manual mode instead of automatically switching everything to procedural", default=False)
    checkboxHideImported: bpy.props.BoolProperty(name="Hide Imported Paint Assets", description="When importing and painting objects from the asset browser (Q), hide them in a new collection called Hidden Assets (instead of having them visible next to the terrain)", default=False)
    checkboxShowPaintPrompt: bpy.props.BoolProperty(name="Show Paint Prompt", description="Show the prompt while choosing an object to paint with", default=True)
    accumulate_manual_paint: bpy.props.BoolProperty(name="Accumulate Manual Paint", description="Build density over repeated manual Density strokes. Each stroke adds one quarter of the normal density target while allowing closer curve spacing", default=True, update=_secret_paint_update_accumulate_manual_paint)
    plant_selection_hold_ms: bpy.props.IntProperty(name="Plant Selection Hold (ms)", description="How long the paint shortcut must remain held after entering paint mode before opening plant selection. Set to 0 to open plant selection immediately", default=200, min=0, soft_max=1000, max=5000)
    automatic_density_multiplier: bpy.props.FloatProperty(name="Automatic Density", description="Scale for the density calculated from the brush size when creating a new paint system. 1.0 is the default density", default=1.0, min=0.1, soft_min=0.25, soft_max=4.0, max=10.0, step=10, precision=2)
    biomeAssetName: bpy.props.StringProperty(name="Asset Name", description="Leave empty to use the Active Object's name", default="Moss")
    biomenamecategory: bpy.props.StringProperty(name="Catalog", description="Asset Browser Catalog for the asset that's being exported. Leave empty to not assign to any catalog", default="Biomes/Nature")
    biomename: bpy.props.StringProperty(name="Folder", description="Export the .blend file to this path inside the currently open Asset Library. If .blend file aready exists: add the objects inside of it", default="/Biomes/All Biomes.blend")
    trigger_viewport_mask: bpy.props.IntProperty(name="Trigger Viewport Mask", description="Automatically create the Viewport Mask whenever turning on the procedural distribution would create more than the specified number of instances. Useful to avoid slowing down the interface when working on huge terrains", default=15000)
    trigger_auto_uvs: bpy.props.IntProperty(name="Trigger UV Reprojection", description="Set to 0 to disable. When the terrain has incorrect UVs, for example after sculpting the terrain with dynamic topology,the UVs will automatically be recreated on objects that have less than this specified number of triangles. This is needed in order to be able to paint manually (geometry node hair limitation; only needed for manual painting, not for the procedural distribution)", default=150000)
    checkboxOverrideBrushes: bpy.props.BoolProperty(name="Override Brush Settings", description="Whenever jumping into paint mode with Q, the brush settings will be automatically set to optimal values", default=True)
    all_libraries = [(lib.path,lib.name,"") for lib in bpy.context.preferences.filepaths.asset_libraries]
    if len(all_libraries) == 0: all_libraries = [("(No Library Found, create one first)","(No Library Found, create one first)","")]
    biome_library: bpy.props.EnumProperty(name="Library", description="Export the asset into this library",items=all_libraries )
    def draw(self, context):
        layout = self.layout
        mainrow = layout.row()
        col = mainrow.column()
        if auto_updater_status == True: addon_updater_ops.update_settings_ui(self, context)
        layout.prop(self, "checkboxKeepManualWhenTransferBiome")
        layout.prop(self, "checkboxHideImported")
        layout.prop(self, "checkboxShowPaintPrompt")
        layout.prop(self, "accumulate_manual_paint")
        layout.prop(self, "plant_selection_hold_ms", slider=True)
        layout.prop(self, "automatic_density_multiplier", slider=True)
        layout.prop(self, "checkboxOverrideBrushes")
        layout.prop(self, "trigger_viewport_mask")
        layout.prop(self, "trigger_auto_uvs")
        row = layout.row()
        row = layout.row()
        row = layout.row()
        box = layout.box()
        col = box.column()
        col.operator("secret.open_keymap_preferences", icon="PREFERENCES")
def _secret_paint_1731_node_group_input_identifier(node_group, socket_name):
    if node_group is None:
        return None
    try:
        for item in node_group.interface.items_tree:
            if getattr(item, "item_type", None) != 'SOCKET':
                continue
            if getattr(item, "in_out", None) != 'INPUT':
                continue
            if getattr(item, "name", "") == socket_name or getattr(item, "identifier", "") == socket_name:
                return getattr(item, "identifier", None)
    except Exception:
        pass
    try:
        for socket in node_group.inputs:
            if getattr(socket, "name", "") == socket_name or getattr(socket, "identifier", "") == socket_name:
                return getattr(socket, "identifier", None)
    except Exception:
        pass
    return None
def _secret_paint_1731_modifier_input_rna(modifier, socket_name):
    if modifier is None:
        return None
    identifier = _secret_paint_1731_node_group_input_identifier(
        getattr(modifier, "node_group", None), socket_name
    )
    identifiers = [value for value in (identifier, socket_name) if value]
    try:
        properties = getattr(modifier, "properties", None)
        inputs = getattr(properties, "inputs", None)
        if inputs is None:
            return None
        for input_identifier in identifiers:
            try:
                return getattr(inputs, input_identifier)
            except Exception:
                try:
                    candidate = inputs[input_identifier]
                    if hasattr(candidate, "value") or hasattr(candidate, "attribute_name"):
                        return candidate
                except Exception:
                    pass
    except Exception:
        pass
    return None
def _secret_paint_1731_copy_modifier_inputs(source_modifier, target_modifier):
    """Copy Geometry Nodes interface values, including Blender 5.2 RNA inputs."""
    node_group = getattr(source_modifier, "node_group", None)
    if node_group is None or getattr(target_modifier, "node_group", None) is None:
        return
    try:
        interface_items = node_group.interface.items_tree
    except Exception:
        return
    for item in interface_items:
        if getattr(item, "item_type", None) != 'SOCKET':
            continue
        if getattr(item, "in_out", None) != 'INPUT':
            continue
        identifier = getattr(item, "identifier", None)
        if not identifier:
            continue
        source_input = _secret_paint_1731_modifier_input_rna(
            source_modifier, identifier
        )
        target_input = _secret_paint_1731_modifier_input_rna(
            target_modifier, identifier
        )
        if source_input is None or target_input is None:
            continue
        try:
            target_input.type = source_input.type
        except Exception:
            pass
        try:
            target_input.attribute_name = source_input.attribute_name
        except Exception:
            pass
        try:
            target_input.value = source_input.value
        except Exception:
            pass
def _secret_paint_1731_modifier_value(modifier, property_name, default=None):
    """Read Geometry Nodes inputs on Blender 5.2 and legacy Blender versions."""
    if modifier is None:
        return default
    attribute_mode = property_name.endswith("_use_attribute")
    attribute_name = property_name.endswith("_attribute_name")
    base_name = property_name
    if attribute_mode:
        base_name = property_name[:-len("_use_attribute")]
    elif attribute_name:
        base_name = property_name[:-len("_attribute_name")]
    input_rna = _secret_paint_1731_modifier_input_rna(modifier, base_name)
    if input_rna is not None:
        try:
            if attribute_mode:
                return getattr(input_rna, "type") == 'ATTRIBUTE'
            if attribute_name:
                return getattr(input_rna, "attribute_name")
            return input_rna.value
        except Exception:
            pass
    identifier = _secret_paint_1731_node_group_input_identifier(
        getattr(modifier, "node_group", None), property_name
    )
    for key in (identifier, property_name):
        if not key:
            continue
        try:
            return modifier[key]
        except Exception:
            pass
    return default
def _secret_paint_1731_set_modifier_value(modifier, property_name, value):
    """Write Geometry Nodes inputs using Blender 5.2 RNA or legacy IDProperties."""
    if modifier is None:
        return False
    attribute_mode = property_name.endswith("_use_attribute")
    attribute_name = property_name.endswith("_attribute_name")
    base_name = property_name
    if attribute_mode:
        base_name = property_name[:-len("_use_attribute")]
    elif attribute_name:
        base_name = property_name[:-len("_attribute_name")]
    input_rna = _secret_paint_1731_modifier_input_rna(modifier, base_name)
    if input_rna is not None:
        try:
            if attribute_mode:
                input_rna.type = 'ATTRIBUTE' if bool(value) else 'VALUE'
            elif attribute_name:
                input_rna.attribute_name = str(value or "")
            else:
                input_rna.value = value
            return True
        except Exception:
            pass
    identifier = _secret_paint_1731_node_group_input_identifier(
        getattr(modifier, "node_group", None), property_name
    )
    for key in (identifier, property_name):
        if not key:
            continue
        try:
            modifier[key] = value
            return True
        except Exception:
            pass
    return False
def _secret_paint_1731_set_modifier_component(modifier, property_name, index, value):
    current_value = _secret_paint_1731_modifier_value(modifier, property_name, None)
    try:
        updated_value = list(current_value)
        updated_value[index] = value
    except (IndexError, TypeError, ValueError):
        return False
    return _secret_paint_1731_set_modifier_value(modifier, property_name, updated_value)
def _secret_paint_1731_paint_modifier(obj):
    for modifier in getattr(obj, "modifiers", ()):
        try:
            node_group = modifier.node_group
            if (
                modifier.type == 'NODES'
                and node_group
                and node_group.name.startswith("Secret Paint")
            ):
                return modifier
        except Exception:
            continue
    return None
def _secret_paint_1731_source_object(modifier):
    source_object = _secret_paint_1731_modifier_value(modifier, "Input_2")
    if source_object:
        return source_object
    return _secret_paint_1731_modifier_value(modifier, "Input_9")
def _secret_paint_1731_collect_paint_systems(context, obj):
    if obj is None:
        return []
    candidates = []
    if getattr(obj, "type", "") == "CURVES" and getattr(obj, "parent", None):
        candidates = list(obj.parent.children)
    elif getattr(obj, "type", "") in {"MESH", "EMPTY"}:
        candidates = list(context.scene.objects)
    systems = []
    for candidate in candidates:
        if getattr(candidate, "type", "") != "CURVES":
            continue
        modifier = _secret_paint_1731_paint_modifier(candidate)
        if modifier is None:
            continue
        if getattr(obj, "type", "") in {"MESH", "EMPTY"}:
            if not (
                _secret_paint_1731_modifier_value(modifier, "Input_97") == obj
                or _secret_paint_1731_modifier_value(modifier, "Input_2") == obj
                or _secret_paint_1731_modifier_value(modifier, "Input_73") == obj
            ):
                continue
        systems.append((candidate, modifier))
    def panel_sort_key(item):
        obj, modifier = item
        try:
            order = float(obj.get(_SECRET_PAINT_1731_PANEL_ORDER_PROP, 1.0e12))
        except (AttributeError, TypeError, ValueError):
            order = 1.0e12
        return (order, getattr(_secret_paint_1731_source_object(modifier), "name", ""))
    systems.sort(key=panel_sort_key)
    return systems
def _secret_paint_1731_clear_panel_cache(reason="manual"):
    """Invalidate the compact panel's cached model and expensive counts."""
    global _SECRET_PAINT_1731_PANEL_CACHE_VERSION
    _SECRET_PAINT_1731_PANEL_COUNT_CACHE.clear()
    _SECRET_PAINT_1731_PANEL_LAYOUT_CACHE.clear()
    _SECRET_PAINT_1731_PANEL_CACHE_VERSION += 1
def _secret_paint_1731_tag_panel_redraw(context=None):
    windows = []
    try:
        if context is not None and context.area is not None:
            context.area.tag_redraw()
        windows = list(bpy.context.window_manager.windows)
    except Exception:
        return
    for window in windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
def _secret_paint_1731_panel_instance_signature(obj, modifier):
    try:
        parent = getattr(obj, "parent", None)
        parent_data = getattr(parent, "data", None) if parent else None
        data = getattr(obj, "data", None)
        manual_count = len(data.curves) if data is not None and hasattr(data, "curves") else 0
        return (
            getattr(obj, "name", ""),
            data.as_pointer() if data is not None else 0,
            parent.as_pointer() if parent else 0,
            parent_data.as_pointer() if parent_data else 0,
            manual_count,
            bool(_secret_paint_1731_modifier_value(modifier, "Input_69", False)),
            float(_secret_paint_1731_modifier_value(modifier, "Input_68", 0) or 0),
            float(_secret_paint_1731_modifier_value(modifier, "Input_72", 0) or 0),
            float(_secret_paint_1731_modifier_value(modifier, "Input_100", 0) or 0),
        )
    except Exception:
        return None
def _secret_paint_1731_compute_instance_label(obj, modifier):
    try:
        if not _secret_paint_1731_modifier_value(modifier, "Input_69", False):
            count = len(obj.data.curves)
        else:
            density = float(_secret_paint_1731_modifier_value(modifier, "Input_68", 0) or 0)
            size = float(_secret_paint_1731_modifier_value(modifier, "Input_100", 0) or 0)
            spread = float(_secret_paint_1731_modifier_value(modifier, "Input_72", 0) or 0)
            parent = getattr(obj, "parent", None)
            polygons = getattr(getattr(parent, "data", None), "polygons", ())
            area = sum(face.area for face in polygons)
            count = int(area / (1 / ((density ** 0.5) * size)) ** 2 * spread / 100) if density > 0 and size > 0 else 0
        return f"{count // 1000}.{(count % 1000) // 100}k" if count >= 1000 else f"0.{count // 100}k"
    except Exception:
        return "0.0k"
def _secret_paint_1731_instance_label(obj, modifier):
    cache_key = None
    signature = _secret_paint_1731_panel_instance_signature(obj, modifier)
    try:
        cache_key = obj.as_pointer()
        cached = _SECRET_PAINT_1731_PANEL_COUNT_CACHE.get(cache_key)
        if cached and cached["signature"] == signature:
            return cached["label"]
    except Exception:
        cache_key = None
    label = _secret_paint_1731_compute_instance_label(obj, modifier)
    if cache_key is not None and signature is not None:
        _SECRET_PAINT_1731_PANEL_COUNT_CACHE[cache_key] = {
            "signature": signature,
            "label": label,
        }
    return label
def _secret_paint_1731_build_layout_model(context, obj):
    grouped = {}
    for paint_system, modifier in _secret_paint_1731_collect_paint_systems(context, obj):
        biome = _secret_paint_1731_modifier_value(modifier, "Socket_0", 0)
        grouped.setdefault(biome, []).append((paint_system, modifier))
    biomes = []
    for biome in sorted(grouped, key=lambda value: str(value)):
        rows = []
        for paint_system, modifier in grouped[biome]:
            source_object = _secret_paint_1731_source_object(modifier)
            render_alert = any(
                bool(_secret_paint_1731_modifier_value(modifier, key, False))
                for key in ("Socket_15", "Socket_14", "Socket_2", "Input_99")
            )
            if _secret_paint_1731_modifier_value(modifier, "Input_99", False):
                render_icon = "RESTRICT_RENDER_ON"
            elif _secret_paint_1731_modifier_value(modifier, "Socket_14", False):
                render_icon = "RESTRICT_VIEW_ON"
            else:
                render_icon = "RESTRICT_RENDER_OFF"
            display_type = getattr(paint_system, "display_type", "TEXTURED")
            rows.append({
                "object": paint_system,
                "modifier": modifier,
                "display_name": getattr(source_object, "name", "(empty)"),
                "icon": (
                    "OUTLINER_COLLECTION"
                    if isinstance(source_object, bpy.types.Collection)
                    else "EMPTY_AXIS"
                    if getattr(source_object, "type", "") == "EMPTY"
                    else "OBJECT_DATA"
                ),
                "procedural_enabled": bool(_secret_paint_1731_modifier_value(modifier, "Input_69", False)),
                "vertex_attribute_name": _secret_paint_1731_modifier_value(modifier, "Input_83_attribute_name", "") or "",
                "vertex_use_attribute": bool(_secret_paint_1731_modifier_value(modifier, "Input_83_use_attribute", False)),
                "render_alert": render_alert,
                "render_icon": render_icon,
                "biome_render_disabled": bool(
                    _secret_paint_1731_modifier_value(
                        modifier, "Socket_2", False
                    )
                ),
                "biome_viewport_disabled": bool(
                    _secret_paint_1731_modifier_value(
                        modifier, "Socket_15", False
                    )
                ),
                "bounds_alert": display_type == "BOUNDS",
                "bounds_icon": "SHADING_BBOX" if display_type == "BOUNDS" else "SHADING_SOLID",
                "mask_alert": bool(_secret_paint_1731_modifier_value(modifier, "Input_98", False)),
            })
        label = f"BIOME {biome}"
        override = rows[0]["modifier"] if rows else None
        override = _secret_paint_1731_modifier_value(override, "Socket_8", "")
        if override not in (None, "", str(biome)):
            label = str(override)
        rename_active = _secret_paint_1731_biome_rename_active(biome, rows)
        if _secret_paint_1731_biome_rename_cursor_visible(biome, rows):
            label = f"{label}|"
        biomes.append({
            "bgroup": biome,
            "label": label,
            "rename_active": rename_active,
            "rows": rows,
            "render_alert": any(row["render_alert"] for row in rows),
            "render_icon": (
                "RESTRICT_RENDER_ON"
                if rows and all(
                    row["biome_render_disabled"] for row in rows
                )
                else "RESTRICT_VIEW_ON"
                if rows and all(
                    row["biome_viewport_disabled"] for row in rows
                )
                else "RESTRICT_RENDER_OFF"
            ),
            "bounds_alert": bool(rows) and all(row["bounds_alert"] for row in rows),
            "mask_alert": bool(rows) and all(row["mask_alert"] for row in rows),
        })
    return biomes
def _secret_paint_1731_biome_rename_active(biome, rows):
    state = _SECRET_PAINT_1731_BIOME_RENAME_STATE
    if not state.get("active"):
        return False
    try:
        if int(biome) != int(state.get("biome_number", 0)):
            return False
    except Exception:
        return False
    anchor_name = state.get("anchor_name", "")
    return any(getattr(row.get("object"), "name", "") == anchor_name for row in rows)
def _secret_paint_1731_biome_rename_cursor_visible(biome, rows):
    state = _SECRET_PAINT_1731_BIOME_RENAME_STATE
    return bool(state.get("visible")) and _secret_paint_1731_biome_rename_active(biome, rows)
def _secret_paint_1731_biome_rename_cursor_tick():
    state = _SECRET_PAINT_1731_BIOME_RENAME_STATE
    if not state.get("active"):
        state["timer_running"] = False
        return None
    state["visible"] = not bool(state.get("visible", True))
    _secret_paint_1731_clear_panel_cache("biome_rename_cursor")
    _secret_paint_1731_tag_panel_redraw()
    return 0.45
def _secret_paint_1731_begin_biome_rename(context, anchor_name, biome_number):
    state = _SECRET_PAINT_1731_BIOME_RENAME_STATE
    state["active"] = True
    state["anchor_name"] = anchor_name
    state["biome_number"] = int(biome_number)
    state["visible"] = True
    if not state.get("timer_running"):
        state["timer_running"] = True
        try:
            bpy.app.timers.register(
                _secret_paint_1731_biome_rename_cursor_tick,
                first_interval=0.45,
            )
        except Exception:
            state["timer_running"] = False
    _secret_paint_1731_clear_panel_cache("biome_rename_start")
    _secret_paint_1731_tag_panel_redraw(context)
def _secret_paint_1731_end_biome_rename(context):
    state = _SECRET_PAINT_1731_BIOME_RENAME_STATE
    state["active"] = False
    state["anchor_name"] = ""
    state["biome_number"] = 0
    state["visible"] = False
    _secret_paint_1731_clear_panel_cache("biome_rename_end")
    _secret_paint_1731_tag_panel_redraw(context)
def _secret_paint_1731_layout_model(context, obj):
    if obj is None:
        return []
    try:
        cache_key = (
            context.scene.as_pointer() if context.scene else 0,
            context.view_layer.as_pointer() if context.view_layer else 0,
            obj.as_pointer(),
            getattr(obj, "type", ""),
            _SECRET_PAINT_1731_PANEL_CACHE_VERSION,
        )
    except Exception:
        cache_key = None
    if cache_key is not None:
        cached = _SECRET_PAINT_1731_PANEL_LAYOUT_CACHE.get(cache_key)
        if cached is not None:
            return cached
    model = _secret_paint_1731_build_layout_model(context, obj)
    if cache_key is not None:
        _SECRET_PAINT_1731_PANEL_LAYOUT_CACHE[cache_key] = model
    return model
@persistent
def _secret_paint_1731_panel_cache_depsgraph_update_post(_scene, depsgraph):
    try:
        for update in depsgraph.updates:
            identifier = getattr(getattr(update.id, "bl_rna", None), "identifier", "")
            if identifier in {"Object", "Mesh", "Curves", "NodeTree"}:
                _secret_paint_1731_clear_panel_cache("depsgraph")
                return
    except Exception:
        _secret_paint_1731_clear_panel_cache("depsgraph_error")
class toggle_biome_panel_collapse(bpy.types.Operator):
    """Expand or collapse this biome only for its terrain surface."""
    bl_idname = "secret.toggle_biome_panel_collapse"
    bl_label = "Expand or Collapse Biome"
    bl_options = {'INTERNAL', 'UNDO'}
    surface_name: bpy.props.StringProperty(options={'HIDDEN'})
    biome_key: bpy.props.StringProperty(options={'HIDDEN'})
    def execute(self, context):
        surface = bpy.data.objects.get(self.surface_name)
        if surface is None:
            surface = _secret_paint_1731_panel_surface(context)
        if surface is None:
            return {'CANCELLED'}
        collapsed = _secret_paint_1731_collapsed_biomes(surface)
        biome_key = _secret_paint_1731_biome_key(self.biome_key)
        if biome_key in collapsed:
            collapsed.remove(biome_key)
        else:
            collapsed.add(biome_key)
        _secret_paint_1731_store_collapsed_biomes(surface, collapsed)
        _secret_paint_1731_tag_panel_redraw(context)
        return {'FINISHED'}
class legacy_panel_keyboard_reorder(bpy.types.Operator):
    """Move the active legacy paint system by dragging after pressing G."""
    bl_idname = "secret.panel_keyboard_reorder"
    bl_label = "Move Paint System"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        area = getattr(context, "area", None)
        region = getattr(context, "region", None)
        if (area is None or area.type != 'VIEW_3D' or
                region is None or region.type != 'UI'):
            return False
        active_object = context.active_object
        if _secret_paint_1731_paint_modifier(active_object) is not None:
            return True
        return any(
            _secret_paint_1731_paint_modifier(obj) is not None
            for obj in context.selected_objects
        )
    def invoke(self, context, event):
        active_object = context.active_object
        if _secret_paint_1731_paint_modifier(active_object) is None:
            active_object = next(
                (
                    obj for obj in context.selected_objects
                    if _secret_paint_1731_paint_modifier(obj) is not None
                ),
                None,
            )
        if active_object is None:
            return {'CANCELLED'}
        self._reorder_plan = _secret_paint_1731_panel_reorder_plan(
            context, active_object
        )
        if self._reorder_plan is None:
            return {'CANCELLED'}
        self._object_name = active_object.name
        self._start_mouse_y = event.mouse_y
        ui_scale = getattr(context.preferences.system, "ui_scale", 1.0)
        self._row_height = max(16.0, 20.0 * float(ui_scale))
        self._last_target_index = self._reorder_plan["anchor_index"]
        self._reorder_snapshot = _secret_paint_1731_snapshot_panel_reorder_state(
            context, active_object
        )
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            _secret_paint_1731_restore_panel_reorder_state(
                self._reorder_snapshot
            )
            _secret_paint_1731_tag_panel_redraw(context)
            return {'CANCELLED'}
        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return {'FINISHED'}
        if event.type != 'MOUSEMOVE':
            return {'RUNNING_MODAL'}
        cursor_offset = round(
            (self._start_mouse_y - event.mouse_y) / self._row_height
        )
        target_index = max(
            0,
            min(
                len(self._reorder_plan["nodes"]) - 1,
                self._reorder_plan["anchor_index"] + cursor_offset,
            ),
        )
        if target_index == self._last_target_index:
            return {'RUNNING_MODAL'}
        active_object = bpy.data.objects.get(self._object_name)
        if active_object is None:
            return {'CANCELLED'}
        _secret_paint_1731_restore_panel_reorder_state(
            self._reorder_snapshot
        )
        _secret_paint_1731_apply_panel_drop(
            context, self._reorder_plan, target_index
        )
        self._last_target_index = target_index
        return {'RUNNING_MODAL'}
def _secret_paint_1731_panel_row(parent, scale_y, action_units=6.0):
    outer = parent.row(align=True)
    outer.scale_y = scale_y
    label = outer.row(align=True)
    actions = outer.row(align=True)
    actions.ui_units_x = action_units
    return outer, label, actions
def _secret_paint_1731_action(row, actions, operator_id, icon, text=""):
    slot = actions.row(align=True)
    slot.ui_units_x = 1.0
    slot.alert = row.alert
    slot.operator_context = 'INVOKE_DEFAULT'
    return slot.operator(operator_id, text=text, icon=icon)
def _secret_paint_1731_spacer(row, actions):
    slot = actions.row(align=True)
    slot.ui_units_x = 1.0
    slot.enabled = False
    slot.label(text="", icon='BLANK1')
def _secret_paint_1731_compact_panel_draw(self, context):
    layout = self.layout
    active_object = context.active_object
    selected_objects = context.selected_objects
    active_weight_group = ""
    try:
        if context.object and context.object.mode == "WEIGHT_PAINT" and active_object.vertex_groups.active:
            active_weight_group = active_object.vertex_groups.active.name
    except Exception:
        pass
    paint_column = layout.column(align=True)
    paint_row = paint_column.row(align=True)
    paint_row.operator_context = 'INVOKE_DEFAULT'
    if _secret_paint_q_selection_mode in {"PLANT", "TERRAIN"}:
        paint_column.scale_y = 3.0
        paint_row.alert = True
        if _secret_paint_q_selection_mode == "TERRAIN":
            paint_row.operator(
                "secret.paint",
                icon='MESH_GRID',
                text="Change Terrain",
            )
        else:
            paint_row.operator(
                "secret.paint",
                icon='BRUSH_DATA',
                text="Change Plant",
            )
    elif (
        getattr(context, "mode", "") == 'SCULPT_CURVES'
        and _secret_paint_1731_paint_modifier(active_object) is not None
    ):
        paint_row.scale_y = 1.5
        plant_shortcut = "Q"
        terrain_shortcut = "Ctrl+Q"
        density_shortcut = "D"
        paint_row.operator(
            "secret.paint",
            icon='BRUSH_DATA',
            text=f"Change Plant ({plant_shortcut})",
        )
        paint_row = paint_column.row(align=True)
        paint_row.scale_y = 1.5
        paint_row.operator_context = 'INVOKE_DEFAULT'
        paint_row.operator(
            "secret.paint_change_terrain",
            icon='MESH_GRID',
            text=f"Change Terrain ({terrain_shortcut})",
        )
        paint_row.operator(
            "secret.brush_density_while_painting",
            icon='LIGHTPROBE_VOLUME',
            text=f"Density ({density_shortcut})",
        )
    else:
        paint_column.scale_y = 3.0
        paint_row.operator("secret.paint", icon='BRUSH_DATA', text="Paint")
    layout.separator()
    def draw_system(row_entry, biome, parent):
        system = row_entry["object"]
        row, label_row, actions = _secret_paint_1731_panel_row(parent, 0.92)
        row_selected = bool(active_object and (system in selected_objects or system == active_object))
        row.alert = row_selected
        label_row.alert = row_selected
        try:
            if context.object.mode == "WEIGHT_PAINT" and row_entry["vertex_attribute_name"] == active_weight_group:
                row.alert = True
                label_row.alert = True
        except Exception:
            pass
        label_row.operator_context = 'INVOKE_DEFAULT'
        select_button = label_row.operator(
            "secret.select_object",
            text=f"{row_entry['display_name']} [{_secret_paint_1731_instance_label(system, row_entry['modifier'])}]",
            icon=row_entry["icon"],
        )
        select_button.object_name = system.name
        row.alert = not row_entry["procedural_enabled"]
        button = _secret_paint_1731_action(row, actions, "secret.applypaint", 'CURVES_DATA')
        button.object_name = system.name
        row.alert = row_entry["procedural_enabled"]
        button = _secret_paint_1731_action(row, actions, "secret.toggle_procedural", 'SHADERFX')
        button.object_name = system.name
        row.alert = bool(row_entry["vertex_attribute_name"] and row_entry["procedural_enabled"])
        button = _secret_paint_1731_action(row, actions, "secret.vertexgrouppaint", 'MOD_VERTEX_WEIGHT' if row_entry["vertex_use_attribute"] else 'GROUP_VERTEX')
        button.object_name = system.name
        row.alert = row_entry["render_alert"]
        button = _secret_paint_1731_action(row, actions, "secret.toggle_visibilityrender", row_entry["render_icon"])
        button.object_name = system.name
        button.object_biome = str(biome)
        row.alert = row_entry["bounds_alert"]
        button = _secret_paint_1731_action(row, actions, "secret.toggle_display_bounds", row_entry["bounds_icon"])
        button.object_name = system.name
        row.alert = row_entry["mask_alert"]
        button = _secret_paint_1731_action(row, actions, "secret.secretpaint_viewport_mask", 'CLIPUV_HLT' if row.alert else 'CLIPUV_DEHLT')
        button.object_name = system.name
    def draw_biome(biome, parent, surface, collapsed):
        row, label_row, actions = _secret_paint_1731_panel_row(parent, 1.15)
        row.alert = False
        label_row.alert = bool(biome.get("rename_active", False))
        label_row.operator_context = 'INVOKE_DEFAULT'
        collapse_button = label_row.operator(
            "secret.toggle_biome_panel_collapse",
            text="",
            icon='TRIA_RIGHT' if collapsed else 'TRIA_DOWN',
            emboss=False,
        )
        collapse_button.surface_name = getattr(surface, "name", "")
        collapse_button.biome_key = _secret_paint_1731_biome_key(
            biome["bgroup"]
        )
        select_button = label_row.operator("secret.select_biome", text=biome["label"])
        select_button.object_biome = str(biome["bgroup"])
        button = _secret_paint_1731_action(row, actions, "secret.biome_delete", 'TRASH')
        button.object_biome = str(biome["bgroup"])
        _secret_paint_1731_spacer(row, actions)
        biome_weight_names = [entry["vertex_attribute_name"] for entry in biome["rows"]]
        biome_weight_alert = bool(biome_weight_names) and all(
            entry["procedural_enabled"]
            and entry["vertex_use_attribute"]
            and entry["vertex_attribute_name"] == biome_weight_names[0]
            and bool(entry["vertex_attribute_name"])
            for entry in biome["rows"]
        )
        row.alert = biome_weight_alert
        button = _secret_paint_1731_action(row, actions, "secret.vertexgrouppaint_biome", 'GROUP_VERTEX')
        button.object_biome = str(biome["bgroup"])
        row.alert = biome["render_alert"]
        button = _secret_paint_1731_action(row, actions, "secret.toggle_visibilityrender_biome", biome["render_icon"])
        button.object_biome = str(biome["bgroup"])
        row.alert = biome["bounds_alert"]
        button = _secret_paint_1731_action(row, actions, "secret.toggle_display_bounds_biome", 'SHADING_BBOX' if row.alert else 'SHADING_SOLID')
        button.object_biome = str(biome["bgroup"])
        row.alert = biome["mask_alert"]
        button = _secret_paint_1731_action(row, actions, "object.secretpaint_viewport_mask_biome", 'CLIPUV_HLT' if row.alert else 'CLIPUV_DEHLT')
        button.object_biome = str(biome["bgroup"])
    panel_model = _secret_paint_1731_layout_model(context, context.object)
    panel_surface = _secret_paint_1731_panel_surface(
        context, context.object, model=panel_model
    )
    for biome in panel_model:
        biome_box = layout.box()
        collapsed = _secret_paint_1731_is_biome_collapsed(
            panel_surface, biome["bgroup"]
        )
        draw_biome(biome, biome_box.row(align=True), panel_surface, collapsed)
        if not collapsed:
            rows = biome_box.column(align=True)
            for row_entry in biome["rows"]:
                draw_system(row_entry, biome["bgroup"], rows)
def _secret_paint_1731_compact_extra_draw(self, context):
    layout = self.layout
    preferences = bpy.context.preferences.addons[__package__].preferences
    group = layout.column(align=True)
    row = group.row(align=True)
    row.scale_y = 1.35
    row.operator("secret.toggle_viewport_tab_bookmark", icon='CAMERA_DATA', text="Toggle View Bookmark")
    row = group.row(align=True)
    row.scale_y = 1.35
    row.operator("secret.assembly", icon="MOD_EXPLODE", text="Assembly")
    row.operator("secret.realize_instances", icon="LIBRARY_DATA_OVERRIDE_NONEDITABLE", text="Realize")
    row = group.row(align=True)
    row.scale_y = 1.35
    row.operator("secret.paintbrushswitch", icon='BRUSHES_ALL', text="Switch")
    row.operator("secret.fixdyntopo", icon="GROUP_UVS", text="Reproject")
    layout.separator()
    button_group = layout.column(align=True)
    row = button_group.row(align=True)
    row.operator("secret.bezier_mode", icon="CURVE_BEZCURVE", text="Bezier")
    row = button_group.row(align=True)
    row.operator("secret.circular_array", icon="CURVE_BEZCIRCLE", text="Circular Array")
    row.operator("secret.straight_array", icon="CURVE_PATH", text="Straight Array")
    row = button_group.row(align=True)
    shared_split = row.split(factor=0.8, align=True)
    shared_split.operator("secret.shared_material", icon='MATERIAL', text="Toggle Shared Material")
    shared_split.prop(context.scene.mypropertieslist, "shared_material_index", expand=True, text="")
    row = button_group.row(align=True)
    row.operator("secret.group", icon='COLLECTION_NEW', text="Collection")
    export_header, export_panel = layout.panel("secret_paint_export_biome", default_closed=True)
    export_header.label(text="Export Biome", icon='EXPORT')
    if export_panel:
        export_panel.prop(preferences, "biomeAssetName")
        export_panel.prop(preferences, "biome_library")
        export_panel.prop(preferences, "biomename")
        export_panel.prop(preferences, "biomenamecategory")
        biome_name = preferences.biomename
        if not biome_name.endswith(".blend"):
            biome_name = biome_name + ".blend"
        blend_file_name = os.path.basename(biome_name)
        file_path = os.path.join(preferences.biome_library, biome_name.lstrip("/\\"))
        if os.path.exists(file_path):
            export_panel.label(text=f"{blend_file_name} already exists")
            export_panel.label(text="Objects will be imported into it")
        export_row = export_panel.row(align=True)
        export_row.operator(
            "secret.export_obj_to_asset_library",
            text=f"Export into {blend_file_name}" if os.path.exists(file_path) else "Export Biome to Asset Library",
        )
        export_row.operator("secret.open_folder", icon="FILE_FOLDER", text="")
orencurvepanel.draw = _secret_paint_1731_compact_panel_draw
subpanelutils.draw = _secret_paint_1731_compact_extra_draw
def _viewport_tab_bookmark_prop(slot, suffix):
    return f"_oren_tab_view_bookmark_{slot}_{suffix}"
def _capture_viewport_bookmark(scene, slot, region_3d):
    scene[_viewport_tab_bookmark_prop(slot, "location")] = list(region_3d.view_location)
    scene[_viewport_tab_bookmark_prop(slot, "rotation")] = list(region_3d.view_rotation)
    scene[_viewport_tab_bookmark_prop(slot, "distance")] = float(region_3d.view_distance)
    scene[_viewport_tab_bookmark_prop(slot, "perspective")] = region_3d.view_perspective
    scene[_viewport_tab_bookmark_prop(slot, "camera_zoom")] = float(region_3d.view_camera_zoom)
    scene[_viewport_tab_bookmark_prop(slot, "camera_offset")] = list(region_3d.view_camera_offset)
def _load_viewport_bookmark(scene, slot):
    keys = {suffix: _viewport_tab_bookmark_prop(slot, suffix) for suffix in (
        "location", "rotation", "distance", "perspective", "camera_zoom", "camera_offset"
    )}
    if any(key not in scene for key in keys.values()):
        return None
    return {
        "view_location": tuple(scene[keys["location"]]),
        "view_rotation": tuple(scene[keys["rotation"]]),
        "view_distance": float(scene[keys["distance"]]),
        "view_perspective": scene[keys["perspective"]],
        "view_camera_zoom": float(scene[keys["camera_zoom"]]),
        "view_camera_offset": tuple(scene[keys["camera_offset"]]),
    }
def _apply_viewport_bookmark(region_3d, bookmark):
    region_3d.view_location = bookmark["view_location"]
    region_3d.view_rotation = bookmark["view_rotation"]
    region_3d.view_distance = bookmark["view_distance"]
    region_3d.view_camera_zoom = bookmark["view_camera_zoom"]
    region_3d.view_camera_offset = bookmark["view_camera_offset"]
    try:
        region_3d.view_perspective = bookmark["view_perspective"]
    except Exception:
        pass
class toggle_viewport_tab_bookmark(bpy.types.Operator):
    bl_idname = "secret.toggle_viewport_tab_bookmark"
    bl_label = "Toggle Viewport Tab Bookmark"
    bl_options = {'REGISTER'}
    @classmethod
    def poll(cls, context):
        region_3d = context.region_data or getattr(context.space_data, "region_3d", None)
        return (
            context.mode in {'OBJECT', 'SCULPT_CURVES'}
            and context.area is not None
            and context.area.type == 'VIEW_3D'
            and context.space_data is not None
            and context.space_data.type == 'VIEW_3D'
            and region_3d is not None
        )
    def execute(self, context):
        scene = context.scene
        region_3d = context.region_data or context.space_data.region_3d
        save_slot = 2 if int(scene.get("_oren_tab_view_next_slot", 1)) == 2 else 1
        target_slot = 2 if save_slot == 1 else 1
        _capture_viewport_bookmark(scene, save_slot, region_3d)
        target_bookmark = _load_viewport_bookmark(scene, target_slot)
        scene["_oren_tab_view_next_slot"] = target_slot
        if target_bookmark is None:
            self.report({'INFO'}, f"Saved viewport bookmark {save_slot}. Move the view and run the shortcut again.")
            return {'FINISHED'}
        _apply_viewport_bookmark(region_3d, target_bookmark)
        context.area.tag_redraw()
        return {'FINISHED'}
classes = [
    SECRET_PAINT_OT_open_keymap_preferences,
    secret_menu,
    MyPropertiesClass,
    orencurvepanel,
    toggle_display_bounds,
    subpanelutils,
    secretpaint_update_modifier,
    orenscatterinstancesmodifiers,
    SelectObjectOperator,
    ToggleVisibilityOperatorRender,
    secretpaint_viewport_mask,
    collectionofactiveobj,
    orenscatter,
    paint_change_terrain,
    bezier_mode,
    orencurveswitch,
    clean_hair_orencurve,
    orengroup,
    vertexgrouppaint,
    orencurveselectobj,
    realize_instances,
    orencurvenewmaterial,
    orencurvecopymat,
    export_obj_to_asset_library,
    select_biome_all,
    toggle_viewport_tab_bookmark,
    toggle_biome_panel_collapse,
    legacy_panel_keyboard_reorder,
    switchtoerasealpha,
    toggle_procedural,
    paint_from_library,
    paint_from_library_justimport,
    paint_from_library_switch,
    shared_material,
    open_folder,
    circular_array,
    straight_array,
    biomegroupreorder,
    biomegroupreorder2,
    legacy_panel_keyboard_delete,
    SelectBiomeOperator,
    ToggleVisibilityOperatorRenderBiome,
    toggle_display_bounds_biome,
    secretpaint_viewport_mask_biome,
    vertexgrouppaint_biome,
    switchtoweightzero,
    curveseparate,
    biome_delete,
    assembly,
    brush_density_while_painting,
    accumulate_density_stroke_start,
    right_click_delete_while_painting,
    export_unreal,
    ]
def register():
    if auto_updater_status: addon_updater_ops.register(bl_info)
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mypropertieslist = bpy.props.PointerProperty(type= MyPropertiesClass)
    bpy.types.FILEBROWSER_HT_header.append(checkboxImportWithoutPainting_f)
    _secret_paint_1731_clear_panel_cache("register")
    if _secret_paint_1731_panel_cache_depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(
            _secret_paint_1731_panel_cache_depsgraph_update_post
        )
    if _secret_paint_1731_sculpt_brush_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(
            _secret_paint_1731_sculpt_brush_load_post
        )
    _secret_paint_1731_start_sculpt_brush_monitor()
    _secret_paint_register_object_mode_pie()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is not None:
        for keymap_name, space_type, operator_id, event_type, modifiers in _SECRET_PAINT_KEYMAP_DEFINITIONS:
            km = kc.keymaps.get(keymap_name)
            if km is None:
                km = kc.keymaps.new(name=keymap_name, space_type=space_type, region_type="WINDOW")
            kmi = km.keymap_items.new(operator_id, event_type, "PRESS", **modifiers)
            addon_keymaps.append((km, kmi))
def unregister():
    if auto_updater_status: addon_updater_ops.unregister()
    _secret_paint_unregister_object_mode_pie()
    _secret_paint_1731_stop_sculpt_brush_monitor()
    if _secret_paint_1731_sculpt_brush_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(
            _secret_paint_1731_sculpt_brush_load_post
        )
    if _secret_paint_1731_panel_cache_depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(
            _secret_paint_1731_panel_cache_depsgraph_update_post
        )
    _secret_paint_1731_clear_panel_cache("unregister")
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mypropertieslist
    bpy.types.FILEBROWSER_HT_header.remove(checkboxImportWithoutPainting_f)
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
if __name__ == "__main__":
    register()
