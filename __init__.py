# Copyright (C) 2024 orencloud

# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Secret Paint",
    "author": "orencloud",
    "version": (1, 7, 21),
    "blender": (4, 2, 0),
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







import bpy.types
from bpy.props import StringProperty

import subprocess







import bmesh
import re
blender_version = bpy.app.version_string








both_addon_and_extensions_are_installed = False
addon_is_an_extension=False
addon_path=None
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":
        if addon_path != None: both_addon_and_extensions_are_installed = True
        
        if hasattr(mod, '__file_manifest__'): addon_is_an_extension=True

        

addon_path = os.path.dirname(os.path.abspath(__file__))
auto_updater_status = True
if blender_version >= "4.2.0" and bpy.app.online_access == False or addon_is_an_extension or both_addon_and_extensions_are_installed: auto_updater_status = False
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

                if blender_version < "4.1.0":   
                    list_biomes(Bgroup, hair_in_bgroup,row = layout.row(align=True)) 
                    for hayr in hair_in_bgroup: list_hair(hayr[0],Bgroup)  
                elif blender_version >= "4.1.0":
                    header, panel = layout.panel(str(Bgroup), default_closed=False)
                    
                    list_biomes(Bgroup, hair_in_bgroup,header) 
                    if panel:
                        for hayr in hair_in_bgroup: list_hair(hayr[0],Bgroup)  



                
                
                
                
                
                
                
                

                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                



                row = layout.row()
                row = layout.row()
                row = layout.row()

            

class subpanelutils(bpy.types.Panel):
    bl_label = "Utilities"
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
        
        
        file_path = bpy.context.preferences.addons[__package__].preferences.biome_library + "/"+ biome_name    
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
        path = bpy.context.preferences.addons[__package__].preferences.biome_library + os.path.dirname(biome_name)      
        pass #print"111111111111111", path)
        try: os.startfile(path)
        except:self.report({'ERROR'}, "The folder doesn't exist. It will be created automatically once you export your Biome. You can also specify a pre-existing folder")
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
                        
                        if hair.modifiers[0]["Input_2"] and hair.modifiers[0]["Input_2"].library==None and hair.modifiers[0]["Input_2"].type in ["MESH", "CURVE", "CURVES"]:
                            hair.data.materials.clear()
                            for mat_slot in hair.modifiers[0]["Input_2"].material_slots:    
                                if mat_slot.material and mat_slot.material.name not in hair.data.materials: hair.data.materials.append(mat_slot.material)

                        
                        elif hair.modifiers[0]["Input_9"] and hair.modifiers[0]["Input_9"].library==None:
                            hair.data.materials.clear()
                            for obj in hair.modifiers[0]["Input_9"].all_objects:
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

    current_node_version = 28 
    pass #print"######################### secretpaint_update_modifier_f 
    
    activeobj = bpy.context.active_object
    objselection = bpy.context.selected_objects


    


    

    
    
    
    
    
    
    
    

    
    
    
    
    
    

    
    carry_through = False
    try:  
        if bpy.app.version_string >= "4.0.0":
            if bpy.data.node_groups.get("Secret Paint") == None      or bpy.data.node_groups.get("Secret Generator") == None      or ["secret paint with linked library found" for node_tree in bpy.data.node_groups if node_tree.name == "Secret Paint" and node_tree.library or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999" and node_tree.library]     or ["found multiple duplicates like Secret Paint.002 " for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999"]     or bpy.data.node_groups["Secret Paint"].interface.items_tree[1].default_value != current_node_version:    carry_through=True
        elif bpy.app.version_string < "4.0.0":
            if bpy.data.node_groups.get("Secret Paint") == None      or bpy.data.node_groups.get("Secret Generator") == None      or ["secret paint with linked library found" for node_tree in bpy.data.node_groups if node_tree.name == "Secret Paint" and node_tree.library or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999" and node_tree.library]     or ["found multiple duplicates like Secret Paint.002 " for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999"]     or bpy.data.node_groups["Secret Paint"].outputs[1].default_value != current_node_version:                 carry_through = True
    except:
        pass #print"FAILED, UPDATING")
        carry_through=True
    
    
    
    
    
    
    
    
    

    
    if carry_through:
        pass #print"######################### secretpaint_update_modifier_f CARRY THROUGH WITH REAPPEND UPDATE Update Triggered By: ", upadte_provenance)

        reupdate_hair_material(context, objselection=[ob for ob in bpy.data.objects])  



        nodes_to_switch = []
        cleanup_generator = []
        for node_tree in bpy.data.node_groups:
            
            if node_tree.name == "Secret Paint" or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":  
                if not node_tree.library: node_tree.name = "Secret Paint.001"  
                if node_tree not in nodes_to_switch: nodes_to_switch.append(node_tree)
            
            if node_tree.name == "Secret Generator" or node_tree.name.startswith("Secret Generator") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999": 
                if not node_tree.library: node_tree.name = "Secret Generator.001"  
                if node_tree not in cleanup_generator: cleanup_generator.append(node_tree)



        
        all_previous_nodes = set(bpy.data.node_groups)
        if blender_version < "4.1": file_path= addon_path + "/Secret Paint 4.0 and older.blend"
        elif blender_version < "4.2.0": file_path= addon_path + "/Secret Paint 4.1.blend"
        elif blender_version < "4.2.1": file_path= addon_path + "/Secret Paint 4.2.0.blend"
        elif blender_version >= "4.2.1": file_path= addon_path + "/Secret Paint.blend"
        inner_path = "NodeTree"
        object_name = "Secret Paint"
        
        
        try: bpy.ops.wm.append(filepath=os.path.join(file_path, inner_path, object_name),directory=os.path.join(file_path, inner_path),filename=object_name)
        except:pass #print"[[[[[[[[[[[[ SECRET PAINT UPDATE FAILED!! CRITICAL CORRUPTION WEIRD")

        for lib in bpy.data.libraries: 
            
            if lib.name in ["Secret Paint.blend","Secret Paint 4.0 and older.blend","Secret Paint 4.1.blend","Secret Paint 4.2.0.blend"]: bpy.data.libraries.remove(lib, do_unlink=True)

        
        
        for nod in bpy.data.node_groups:
            if nod not in all_previous_nodes and nod.name.startswith("Secret Paint"):
                orenpaintNode= nod
                break




        
        for obj in bpy.data.objects:
            
            if obj.type in ["CURVES","CURVE"]:
                for modif in obj.modifiers:
                    
                    
                    
                    if modif.type == 'NODES' and modif.node_group:
                        
                        if modif.node_group.name == "Secret Paint" or modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999" : modif.node_group = orenpaintNode  


        
        
        
        
        
        
        
        
        
        
        

        
        
        
        
        
        
        
            
            
            
            
            



        
        
        for nod in nodes_to_switch[:]:
            
            bpy.data.node_groups.remove(nod, do_unlink=True)
        
        for nod in cleanup_generator[:]:
            
            bpy.data.node_groups.remove(nod, do_unlink=True)

    
    for x in objselection: x.select_set(True)
    if activeobj: bpy.context.view_layer.objects.active = activeobj




















































































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
def apply_paint(self,context, **kwargs):
    pass #print"AAAAAAAAAAAPPPPPPPPPPPPPPLYYYYYYYYY")
    

    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj) 

    if "applyIDs" in kwargs:applyIDs = kwargs.get("applyIDs")
    else:applyIDs = False

    keep_active_brush = kwargs.get("keep_active_brush") if "keep_active_brush" in kwargs else False

    
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

    
    
    
    
    
    
    
    
    
    
    
    
    

    
    

    

    

    for obj in all_selected_hair:

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        

        
        
        
        


        
        
        node_to_use=[]
        if applyIDs or obj.modifiers[0]["Input_69"] == False:
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
        modifier["Input_2"] = obj.parent  
        modifier["Input_15"] = obj.modifiers[0]["Input_68"]*(obj.modifiers[0]["Input_100"]**2) 
        modifier["Input_14"] = obj.modifiers[0]["Input_83"] 
        modifier["Input_16"] = obj.modifiers[0]["Input_80"] 
        modifier["Input_19"] = obj.modifiers[0]["Input_79"] 
        modifier["Input_30"] = obj.modifiers[0]["Input_78"] 
        modifier["Input_33"] = obj.modifiers[0]["Input_70"]*obj.modifiers[0]["Input_100"] 
        modifier["Input_31"] = obj.modifiers[0]["Input_72"] 
        modifier["Input_32"] = obj.modifiers[0]["Input_82"] 
        modifier["Input_34"] = obj.modifiers[0]["Input_71"] 
        modifier["Input_39"] = obj.modifiers[0]["Input_89"] 
        modifier["Input_40"] = obj.modifiers[0]["Input_16"] 
        modifier["Input_41"] = obj.modifiers[0]["Input_86"] 
        modifier["Input_42"] = obj.modifiers[0]["Input_91"] 
        modifier["Input_43"] = obj.modifiers[0]["Input_92"] 
        modifier["Input_44"] = obj.modifiers[0]["Input_95"] 
        modifier["Input_45"] = obj.modifiers[0]["Input_85"] 
        if obj.modifiers[0]["Input_83_attribute_name"] and obj.modifiers[0]["Input_83_use_attribute"]:
            modifier["Input_14_attribute_name"] = obj.modifiers[0]["Input_83_attribute_name"] 
            modifier["Input_14_use_attribute"] = True 
        obj.modifiers[0]["Input_69"] = False 

        
        if bpy.app.version_string >= "4.0.0":
            obj.modifiers.move(len(obj.modifiers) - 1, 0)
        elif bpy.app.version_string < "4.0.0":
            
            
            bpy.ops.object.modifier_move_up({'object': obj}, modifier=modifier.name)

        

        
        successfully_applied_so_reimport_materials = False
        mats_before = [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material] 
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
                

        
        if successfully_applied_so_reimport_materials:
            for mat in mats_before:
                if mat.name not in obj.data.materials: obj.data.materials.append(mat)




        
        if obj.parent and obj.parent.modifiers:  
            for mod in obj.parent.modifiers: 
                if mod.type=="ARMATURE":

                    
                    
                    

                    
                    bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
                    

                    
                    


        

        


        

        
        
        
        
        
        
        
        
        
        
        
        
        


    

    
    for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
    bpy.context.view_layer.objects.active = activeobj
    context3sculptbrush(context, activeobj=activeobj, keep_active_brush=keep_active_brush)
    



    
    Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=objselection)  


        
        
        
        
        
        
        


    return{'FINISHED'}
class orenscatterinstancesmodifiers(bpy.types.Operator):
    """Convert Procedural Distribution into Manual Paint (or press Q with the paint system selected)"""
    bl_idname = "secret.applypaint"
    bl_label = "Apply and Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def invoke(self, context, event):
        if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        activeobj= bpy.data.objects.get(self.object_name)
        if bpy.context.active_object != activeobj: bpy.context.view_layer.objects.active = activeobj  
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        secretpaint_update_modifier_f(context,upadte_provenance="secret.applypaint")
        apply_paint(self,context,activeobj=activeobj, objselection=[activeobj])
        
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
        
        checkbox_state = activeobj.modifiers[0]["Input_69"]
        objselection = bpy.context.selected_objects
        if activeobj not in objselection: objselection.append(activeobj)

        
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]

        for obj in objselection:
            if obj.type == "CURVES" and obj.modifiers:
                for modif in obj.modifiers:  
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):

                        
                        if obj.type == "CURVES" and obj.modifiers[0]["Input_69"] == False and obj.modifiers[0]["Input_68"] > 0:
                            allTerrainArea = sum(face.area for face in obj.parent.data.polygons)  
                            
                            
                            
                            if (allTerrainArea/   (   (1/   ((obj.modifiers[0]["Input_68"] ** 0.5) * (obj.modifiers[0]["Input_100"]))   )   **2))   > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                                obj.modifiers[0]["Input_98"] = False  
                                obj.modifiers[0]["Input_97"] = None
                                secretpaint_viewport_mask_function(self, context, objselection=[obj], activeobj=obj)

                        obj.modifiers[0]["Input_69"] = not checkbox_state  
                        obj.location = obj.location 

        
        
        
        
        
        
        return {'FINISHED'}

class SelectObjectOperator(bpy.types.Operator):
    """Ctrl+Click: select siblings; Shift: extend selection; Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; Alt+Click: duplicate a backup system"""
    bl_idname = "secret.select_object"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    
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
                    newobj.modifiers[0]["Input_99"] = True
                    obj.modifiers[0]["Input_99"] = False
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
                
                if obj in bpy.context.selected_objects: obj.select_set(False)
                else: obj.select_set(True)

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


        if obj:
            hair=[]
            parent = obj.parent
            if obj.type=="CURVES" and parent:   
                for hai in parent.children: 
                    if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                        for modifier in hai.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                                hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
            
            elif obj.type=="MESH" or obj.type=="EMPTY":
                for hayr in bpy.context.scene.objects:
                
                    if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                        for modifier in hayr.modifiers: 
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                                hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))

            all_bgroups=[]
            for hayr in hair[:]:
                if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]

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

        return {'FINISHED'}

class SelectBiomeOperator(bpy.types.Operator):
    """Shift+Click: extend selection, Alt+Click: duplicate a backup system, Ctrl+Click: rename biome"""
    
    bl_idname = "secret.select_biome"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty(name= "Custom Biome Name", default="")  

    def execute(self, context):  

        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - execute")

        for ob in self.hair_in_bgroup:
            ob.modifiers[0]["Socket_8"] = self.object_biome
        return {'FINISHED'}

    def invoke(self, context, event):

        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - invoke")

        obj = context.object
        if obj:
            hair = find_all_listed_paintsystems(context)
            all_bgroups=[]   
            for hayr in hair[:]:
                if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]


            
            
            

            

            
            

            
            



            
            
            

            
            
            
            
            
            
            
            



            
            
            
            
            
            
            
            
            

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
                        newobj.modifiers[0]["Socket_2"] = True
                        
                        obj.modifiers[0]["Socket_0"] = new_bgroup_number
                        obj.modifiers[0]["Socket_2"] = False
                        bpy.context.collection.objects.link(newobj)
                        bpy.data.objects[newobj.name].select_set(False)
                        obj.location=obj.location
                        bpy.context.view_layer.active_layer_collection = original_collection

            
            
            
            
            
            

            elif event.shift:
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                yet_to_be_selected = []
                for ob in hair_in_bgroup:
                    if not ob.select_get(): yet_to_be_selected.append(ob)

                if len(yet_to_be_selected) >=1:  
                    for ob in yet_to_be_selected:
                        if ob.name in bpy.context.view_layer.objects:
                            bpy.context.view_layer.objects.active = ob
                            ob.select_set(True)
                else: 
                    for ob in hair_in_bgroup:
                        if ob.name in bpy.context.view_layer.objects:
                            ob.select_set(False)
                            for x in bpy.context.selected_objects: bpy.context.view_layer.objects.active = x



            elif event.ctrl:    
                self.biom_temp_numb = int(self.object_biome)     
                self.hair_in_bgroup = hair_in_bgroup
                secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - invoke at the end") 
                return context.window_manager.invoke_props_dialog(self)



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
    try:
        if activeobj not in objselection: objselection.append(activeobj)
    except:pass  

    listed_hair=[]
    parent = activeobj.parent
    if activeobj.type=="CURVES" and parent:   
        for hai in parent.children: 
            if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                for modifier in hai.modifiers:
                    if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                        listed_hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
    
    elif activeobj.type=="MESH" or activeobj.type=="EMPTY":
        for hayr in bpy.context.scene.objects:
        
            if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                for modifier in hayr.modifiers: 
                    if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == activeobj \
                    or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == activeobj \
                    or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == activeobj:
                        listed_hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
    return listed_hair
def biome_remove_gaps(context,biome_hair):
    all_biome_numbers=[]
    for hayr in biome_hair[:]:
        if hayr[0].modifiers[0]["Socket_0"] not in all_biome_numbers: all_biome_numbers.append(hayr[0].modifiers[0]["Socket_0"])
    all_biome_numbers.sort()
    loop = 1
    for biome_number in all_biome_numbers[:]:
        for hayr in biome_hair[:]:
            if hayr[0].modifiers[0]["Socket_0"] == biome_number:
                hayr[0].modifiers[0]["Socket_0"] = loop
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
            if hayr[0].modifiers[0]["Socket_0"] not in all_biome_numbers: all_biome_numbers.append(hayr[0].modifiers[0]["Socket_0"])
        if direction == -1: destination_biome = min(all_biome_numbers)-1
        elif direction == +1: destination_biome = max(all_biome_numbers)+1
    else: destination_biome = activeobj.modifiers[0]["Socket_0"] + direction



    
    
    
    
    hair_in_destination_biome = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == destination_biome]
    
    



    
    for obj in objselection:
        if obj.type == "CURVES" and obj.modifiers:
            for modif in obj.modifiers:  
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    modif["Socket_0"] = destination_biome
                    
                    modif["Socket_3"] = False 
                    modif["Socket_4"] = False
                    modif["Socket_5"] = False
                    modif["Socket_6"] = False
                    if len(hair_in_destination_biome) >=1:
                        modif["Socket_2"] = hair_in_destination_biome[0].modifiers[0]["Socket_2"] 
                        modif["Socket_15"] = hair_in_destination_biome[0].modifiers[0]["Socket_15"] 
                    
                    obj.location=obj.location
                    if hair_in_destination_biome: modif["Socket_8"] = hair_in_destination_biome[0].modifiers[0]["Socket_8"]   


    
    
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
        hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == buttonbiome]
        for ob in objselection[:]:  
            if ob not in hair_in_bgroup: objselection.remove(ob)
    




        
        if event.alt:

            
            if buttonobj.modifiers[0]["Socket_4"] == True:   
                for hayii in hair_in_bgroup:
                    if hayii.type == "CURVES":
                        for modif in hayii.modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if modif["Socket_3"]==True: modif["Input_99"] = not modif["Input_99"]  
                                modif["Socket_3"] = False  
                                modif["Socket_4"] = False  
                                hayii.location = hayii.location


            
            else:

                
                for hayyur in hair_in_bgroup:  
                    if hayyur.type == "CURVES":
                        for modif in hayyur.modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                modif["Socket_3"] = False  
                                modif["Socket_4"] = False  
                                hayyur.location = hayyur.location

                for hayii in hair_in_bgroup:
                    if hayii.type == "CURVES":
                        for modif in hayii.modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                                
                                if hayii in objselection:
                                    if modif["Input_99"] == True:                 
                                        modif["Input_99"] = False 
                                        modif["Socket_3"] = True  
                                    modif["Socket_4"] = True  

                                
                                else:
                                    if modif["Input_99"] == False: 
                                        modif["Socket_3"] = True 
                                        modif["Input_99"] = True  

                                hayii.location=hayii.location 

        
        elif event.shift:
            mute_visibility_render = buttonobj.modifiers[0]["Input_99"]
            mute_visibility_viewport = buttonobj.modifiers[0]["Socket_14"]

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
                            
                            modif["Input_99"] = mute_visibility_render_new
                            modif["Socket_14"] = mute_visibility_viewport_new
                            obj.location=obj.location



        
        else:
            mute_visibility_render = buttonobj.modifiers[0]["Input_99"]
            mute_visibility_viewport = buttonobj.modifiers[0]["Socket_14"]

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
                            
                            modif["Input_99"] = mute_visibility_render_new
                            modif["Socket_14"] = mute_visibility_viewport_new
                            obj.location=obj.location

            for hayyur in hair_in_bgroup:  
                if hayyur.type == "CURVES":
                    for modif in hayyur.modifiers:  
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            modif["Socket_3"] = False  
                            modif["Socket_4"] = False  
                            hayyur.location = hayyur.location


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    


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
            if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome): hair_in_bgroup.append(hayr[0])
            else: hair_in_OTHER_bgroups.append(hayr[0])
        







        if event.alt: 


            
            if True in [hairr.modifiers[0]["Socket_6"] for hairr in hair_in_bgroup]:
                
                for hayii in hair[:]:
                    if hayii[0].type == "CURVES":
                        for modif in hayii[0].modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if modif["Socket_5"]==True: modif["Socket_2"] = not modif["Socket_2"]  
                                modif["Socket_5"] = False  
                                modif["Socket_6"] = False  
                                hayii[0].location = hayii[0].location



            
            else:

                
                for hayyur in hair[:]:  
                    if hayyur[0].type == "CURVES":
                        for modif in hayyur[0].modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                modif["Socket_5"] = False  
                                modif["Socket_6"] = False  
                                hayyur[0].location = hayyur[0].location

                for hayii in hair[:]:
                    if hayii[0].type == "CURVES":
                        for modif in hayii[0].modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                                
                                if hayii[0] in hair_in_bgroup:
                                    if modif["Socket_2"] == True:                 
                                        modif["Socket_2"] = False 
                                        modif["Socket_5"] = True  
                                    modif["Socket_6"] = True  

                                
                                else:
                                    if modif["Socket_2"] == False: 
                                        modif["Socket_5"] = True 
                                        modif["Socket_2"] = True  

                                hayii[0].location=hayii[0].location 


        
        elif event.shift:
            mute_biome_visibility_render = False if False in [hairr.modifiers[0]["Socket_2"] for hairr in hair_in_bgroup] else True  
            mute_biome_visibility_viewport = False if False in [hairr.modifiers[0]["Socket_15"] for hairr in hair_in_bgroup] else True  

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
                            modif["Socket_2"] = mute_biome_visibility_render_new
                            modif["Socket_15"] = mute_biome_visibility_viewport_new
                            obj.location=obj.location



        
        else:
            mute_biome_visibility_render = False if False in [hairr.modifiers[0]["Socket_2"] for hairr in hair_in_bgroup] else True  
            mute_biome_visibility_viewport = False if False in [hairr.modifiers[0]["Socket_15"] for hairr in hair_in_bgroup] else True  

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
                            modif["Socket_2"] = mute_biome_visibility_render_new
                            modif["Socket_15"] = mute_biome_visibility_viewport_new
                            obj.location=obj.location

            for hayii in hair[:]:  
                if hayii[0].type == "CURVES":
                    for modif in hayii[0].modifiers:  
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            modif["Socket_5"] = False  
                            modif["Socket_6"] = False  
                            hayii[0].location = hayii[0].location
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
        hair = []
        parent = obj.parent
        if obj.type == "CURVES" and parent:  
            for hai in parent.children:  
                if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                    for modifier in hai.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                            hair.append((hai, hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
        
        elif obj.type == "MESH" or obj.type == "EMPTY":
            for hayr in bpy.context.scene.objects:
                
                if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                    for modifier in hayr.modifiers:  
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                            hair.append((hayr, hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
        
        
        
        hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]
        

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
        hair = []
        parent = obj.parent
        if obj.type == "CURVES" and parent:  
            for hai in parent.children:  
                if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                    for modifier in hai.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                            hair.append((hai, hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
        
        elif obj.type == "MESH" or obj.type == "EMPTY":
            for hayr in bpy.context.scene.objects:
                
                if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                    for modifier in hayr.modifiers:  
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                            hair.append((hayr, hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
        
        
        
        hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]
        

        maskobsel=None
        if hair_in_bgroup:

            if event.alt:  
                for x in bpy.context.selected_objects: x.select_set(False)  
                for hai in hair_in_bgroup:
                    if hai.modifiers[0]["Input_97"]: maskobsel = hai.modifiers[0]["Input_97"]
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



























class brush_density_while_painting(bpy.types.Operator):
    """While hovering with the mouse on the terrain, press the shortcut (D) to change the brush density. The Addon will remember the density you chose for each system independently"""
    bl_idname = "secret.brush_density_while_painting"
    bl_label = "Change Brush Density"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        
        context3sculptbrush(context)
        
        bpy.ops.sculpt_curves.min_distance_edit('INVOKE_DEFAULT')  
        context.window_manager.modal_handler_add(self)  
        self._cancel = False  
        return {'RUNNING_MODAL'}  

    def modal(self, context, event):
        if self._cancel:
            pass #print"FINN")
            return {'CANCELLED'}  
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE',"ESC"}:  
            try: bpy.context.active_object.modifiers[0]["Socket_11"] = context.tool_settings.curves_sculpt.brush.curves_sculpt_settings.minimum_distance  
            except: pass #print"obj has no secret paint modifier")
            bpy.app.timers.register(lambda: setattr(self, '_cancel', True), first_interval=0.001)  
        return {'PASS_THROUGH'}  




    
    
    
        






















def context3sculptbrush(context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    keep_active_brush = kwargs.get("keep_active_brush") if "keep_active_brush" in kwargs else False

    

    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    




    if activeobj.type == "CURVES":

        if activeobj.data.users >= 2 and activeobj.data.surface!=activeobj.parent: activeobj.data.surface = activeobj.parent  
        
        
        active_render_UV = None
        custom_uv = None
        for uvmap in activeobj.data.surface.data.uv_layers:  
            if uvmap.name == "Secret Paint UV": custom_uv = uvmap.name
            if uvmap.active_render: active_render_UV = uvmap.name
        if not activeobj.data.surface_uv_map or activeobj.data.surface_uv_map not in [custom_uv,active_render_UV]:
            if custom_uv: activeobj.data.surface_uv_map = custom_uv
            elif active_render_UV: activeobj.data.surface_uv_map = active_render_UV

        bpy.ops.object.mode_set(mode="SCULPT_CURVES")  

        if not keep_active_brush:
            try: 
                if bpy.app.version_string >= "4.3.0": bpy.ops.wm.tool_set_by_id(name="builtin_brush.density")
                else: bpy.ops.wm.tool_set_by_id(name="builtin_brush.Density")
            except: pass #print"FAILED BRUSH DENSITYYYYY")
            

        
        
        

        
        brush_density = []
        brush_grow = []
        brush_add = []
        brush_delete = []
        brush_puff = []
        brush_comb = []
        for brush in bpy.data.brushes:
            if brush.curves_sculpt_tool == 'DENSITY': brush_density.append(brush)
            elif brush.curves_sculpt_tool == 'GROW_SHRINK': brush_grow.append(brush)
            elif brush.curves_sculpt_tool == 'ADD': brush_add.append(brush)
            elif brush.curves_sculpt_tool == 'DELETE': brush_delete.append(brush)
            elif brush.curves_sculpt_tool == 'PUFF': brush_puff.append(brush)
            elif brush.curves_sculpt_tool == 'COMB': brush_comb.append(brush)



        if not brush_density:
            new_brush_density = bpy.data.brushes.new('Density Curvesss',mode="SCULPT_CURVES")
            new_brush_density.curves_sculpt_tool = 'DENSITY'
            new_brush_density.size = 150
            brush_density.append(new_brush_density)
            
        if not brush_grow:
            new_brush_grow = bpy.data.brushes.new('Grow /Shrink Curves',mode="SCULPT_CURVES")
            new_brush_grow.curves_sculpt_tool = 'GROW_SHRINK'
            new_brush_grow.size = 150
            brush_grow.append(new_brush_grow)
        if not brush_add:
            new_brush_add = bpy.data.brushes.new('Add Curves',mode="SCULPT_CURVES")
            new_brush_add.curves_sculpt_tool = 'ADD'
            new_brush_add.size = 150
            brush_add.append(new_brush_add)
        if not brush_delete:
            new_brush_delete = bpy.data.brushes.new('Delete Curves',mode="SCULPT_CURVES")
            new_brush_delete.curves_sculpt_tool = 'DELETE'
            new_brush_delete.size = 150
            brush_delete.append(new_brush_delete)
        if not brush_puff:
            new_brush_puff = bpy.data.brushes.new('Puff Curves',mode="SCULPT_CURVES")
            new_brush_puff.curves_sculpt_tool = 'PUFF'
            new_brush_puff.size = 150
            brush_puff.append(new_brush_puff)
        if not brush_comb:
            new_brush_comb = bpy.data.brushes.new('Comb Curves',mode="SCULPT_CURVES")
            new_brush_comb.curves_sculpt_tool = 'COMB'
            new_brush_comb.size = 150
            brush_comb.append(new_brush_comb)



        
        for bb in brush_density:
            
            if bpy.context.object.modifiers[0]: bb.curves_sculpt_settings.minimum_distance = bpy.context.object.modifiers[0]["Socket_11"]
            else: bb.curves_sculpt_settings.minimum_distance = 0.1
            if bpy.app.version_string >= "4.2.0":
                bb.curves_sculpt_settings.use_length_interpolate = True
                bb.curves_sculpt_settings.use_shape_interpolate = True
                bb.curves_sculpt_settings.use_point_count_interpolate = False
            elif bpy.app.version_string < "4.2.0":
                bb.curves_sculpt_settings.interpolate_length = True
                bb.curves_sculpt_settings.interpolate_shape = True
                bb.curves_sculpt_settings.interpolate_point_count = False
            bb.curves_sculpt_settings.curve_length = 0.32  
            bb.curves_sculpt_settings.points_per_curve = 2

        
        if bpy.context.preferences.addons[__package__].preferences.checkboxOverrideBrushes:

            
            for bb in brush_density:
                bb.curves_sculpt_settings.density_mode = 'AUTO'
                bb.strength = 1
                bb.falloff_shape = 'SPHERE'
                bb.curve_preset = 'SMOOTHER'
                bb.curves_sculpt_settings.density_add_attempts = 200

            
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
                    bb.curves_sculpt_settings.use_length_interpolate = True
                    bb.curves_sculpt_settings.use_shape_interpolate = True
                    bb.curves_sculpt_settings.use_point_count_interpolate = False
                elif bpy.app.version_string < "4.2.0":
                    bb.curves_sculpt_settings.interpolate_length = True
                    bb.curves_sculpt_settings.interpolate_shape = True
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






    elif activeobj.type=="CURVE":
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
                    temp_variable_for_mask_detection1.append(modifier["Input_98"])  
                    temp_variable_for_mask_detection2.append(modifier["Input_97"])


    all_hair_share_same_mask_settings = False
    if all_variables_are_equal(temp_variable_for_mask_detection1) and all_variables_are_equal(
        temp_variable_for_mask_detection2): all_hair_share_same_mask_settings = True

    biome_detected = False
    if len(all_found_parents) == 1: biome_detected = True

    all_sel_are_orencurves = False
    if N_Of_Selected == len(objs_with_orencurve): all_sel_are_orencurves = True

    

    
    if mask_found:
        for scattered_hair in objs_with_orencurve:
            scattered_hair.modifiers[0]["Input_98"] = True
            scattered_hair.modifiers[0]["Input_97"] = mask_found

            scattered_hair.hide_viewport = True  
            scattered_hair.hide_viewport = False  
            scattered_hair.location = scattered_hair.location  

    
    else:
        checkboxstatus = activeobj.modifiers[0]["Input_98"]
        maskstatus = activeobj.modifiers[0]["Input_97"]
        
        
        



        
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
                if checkboxstatus:
                    scattered_hair.modifiers[0]["Input_98"] = False  
                    scattered_hair.modifiers[0]["Input_97"] = None  

                elif checkboxstatus == False:
                    scattered_hair.modifiers[0]["Input_98"] = True  

                    if maskstatus:
                        scattered_hair.modifiers[0]["Input_97"] = maskstatus
                    elif maskstatus == None:
                        scattered_hair.modifiers[0]["Input_97"] = maskobj

                scattered_hair.hide_viewport = True  
                scattered_hair.hide_viewport = False  
                scattered_hair.location = scattered_hair.location  

        
        else:
            for scattered_hair in objs_with_orencurve:
                scattered_hair.modifiers[0]["Input_98"] = checkboxstatus
                scattered_hair.modifiers[0]["Input_97"] = maskstatus
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
                    if modifier["Input_97"] and modifier["Input_97"] not in all_used_masks_in_blendfile: all_used_masks_in_blendfile.append(modifier["Input_97"])
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
            if obbb.modifiers[0]["Input_97"]:
                bpy.context.view_layer.objects.active = obbb.modifiers[0]["Input_97"]
                obbb.modifiers[0]["Input_97"].select_set(True)
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
                    brushobj = activeobj.modifiers[0]["Input_2"]
                    brushcoll = activeobj.modifiers[0]["Input_9"]
    
    for obj in bpy.context.scene.objects:
        if obj.type == "CURVES":
            if obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and obj.modifiers[0]["Input_2"] == brushobj and obj.modifiers[0]["Input_9"] == brushcoll:
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
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and (sum(len(spline.points) for spline in obj.data.curves)) == 0 and obj.modifiers[0]["Input_99"] == False and obj.modifiers[0]["Input_69"] == False:
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
                if (mod.is_property_readonly(attr)): continue
                setattr(mod_copy, attr, getattr(mod, attr))
            try:
                for key, value in mod.items():
                    mod_copy[key] = value
            except: pass
    hairCurves.modifiers[0]["Input_99"] = True    
    hairCurves.modifiers[0]["Input_71"] = float(random.choice(range(0, 10)))  
    hairCurves.modifiers[0]["Input_73"] = targetOBJsurface 
    hairCurves.modifiers[0]["Input_100"] = abs(max(targetOBJsurface.scale))    
    
    
    if targetOBJsurface.modifiers:   
        for mod in targetOBJsurface.modifiers:
            if mod.type in ["ARMATURE","CAST","CURVE","DISPLACE","HOOK","LAPLACIANDEFORM","LATTICE","MESH_DEFORM","SHRINKWRAP","SIMPLE_DEFORM","SMOOTH","CORRECTIVE_SMOOTH","LAPLACIANSMOOTH","SURFACE_DEFORM","WARP","WAVE",]:
                hairCurves.modifiers[0]["Input_63"] = True 
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
                                if modif[input.identifier] and modif[input.identifier].type=="MESH":
                                    if max(smallest_obj.dimensions)==0\
                                    or max(modif[input.identifier].dimensions)>0 and modif[input.identifier].dimensions < smallest_obj.dimensions:
                                        smallest_obj = modif[input.identifier]
                                        thisobj_is_an_assembly = True
                                        break

            if not thisobj_is_an_assembly:
                if max(smallest_obj.dimensions)==0\
                or smallest_obj.type == "MESH" and max(obje.dimensions) > 0 and obje.dimensions < smallest_obj.dimensions: smallest_obj = obje
    if max(smallest_obj.dimensions)>0:  
        if smallest_obj.dimensions[0]/smallest_obj.scale[0] > smallest_obj.dimensions[1]/smallest_obj.scale[1]: dimensions_of_smallest_axis = 1 / ((smallest_obj.dimensions[1]/smallest_obj.scale[1]) **2) 
        else: dimensions_of_smallest_axis = 1 / ((smallest_obj.dimensions[0]/smallest_obj.scale[0]) **2) 
        if dimensions_of_smallest_axis < 10000: 
            hairCurves.modifiers[0]["Input_68"] = dimensions_of_smallest_axis
            hairCurves.modifiers[0]["Socket_11"] =     (0.5/((dimensions_of_smallest_axis ** 0.5) *hairCurves.modifiers[0]["Input_100"]))*2

        
        
        




    return hairCurves
    
def secretpaint_function(self,*args,**kwargs):  
    pass #print"###########-----  secretpaint_function(self,*args,**kwargs  ------############")
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
                    if oobjj.type == "CURVES" and oobjj.data.surface and oobjj.data.surface not in all_found_parents: all_found_parents.append(oobjj.data.surface)
                    if oobjj != activeobj and oobjj.type == "CURVES" and oobjj.data.surface and oobjj.data.surface not in all_found_parents_without_activeobj: all_found_parents_without_activeobj.append(oobjj.data.surface)
                    if modifier["Input_83_attribute_name"]:
                        all_hair_with_Vgroup.append(oobjj)
                        if modifier["Input_83_attribute_name"] not in all_Vgroups: all_Vgroups.append(modifier["Input_83_attribute_name"])

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
        pass #print"scatter sel obj on active surface")
        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj) 
        hairCurves = secretpaint_create_curve(self,context,targetOBJ=activeobj,targetCollection=Coll_of_Active, brushOBJ=selobj, transfer_modifier=False)

        
        hairCurves.modifiers[0]["Input_2"] = bpy.data.objects[selobj.name]  
        
        hairCurves.modifiers[0]["Input_16"] = 5 
        hairCurves.modifiers[0]["Input_6"][2] = 20  

        
        percentage_value = 0.75  
        
        
        
        

        hairCurves.modifiers[0]["Input_15"] = 0.25 
        hairCurves.modifiers[0]["Input_15"] = 0.25 
        hairCurves.modifiers[0]["Input_82"] = 1.04
        hairCurves.modifiers[0]["Input_62"] = 0.5 
        
        hairCurves.modifiers[0]["Input_60"] =   0.15*   ((hairCurves.modifiers[0]["Input_68"]    **0.5))     

        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value 
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except:pass

        
        
        
        
        
        
        
        
        
        
        

        
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        

        
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.data.polygons)  
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                hairCurves.modifiers[0]["Input_98"] = False  
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            context3sculptbrush(context)

        
        hairCurves.modifiers[0]["Input_99"] = False

        





    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    















    
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "MESH" and len(selobjs_without_active_with_orencurve)==0:
    
        pass #print"scatter sel collection on ACTIVE surface")

        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)  

        
        
        
        
        
        

        
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=False)

        
        

        
        
        
        
        
        

        
        
        hairCurves.modifiers[0]["Input_2"] = None  
        hairCurves.modifiers[0]["Input_9"] = bpy.data.collections[collection_of_one_of_selected.name]
        hairCurves.modifiers[0]["Input_16"] = 5 
        hairCurves.modifiers[0]["Input_6"][2] = 20  
        hairCurves.modifiers[0]["Input_15"] = 0.25 
        hairCurves.modifiers[0]["Input_62"] = 0.5 
        hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  

        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value 
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except:pass
        
        

        

        for x in objselection: x.select_set(False)


        
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.data.polygons)  
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                hairCurves.modifiers[0]["Input_98"] = False  
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            context3sculptbrush(context, activeobj=hairCurves)


        
        hairCurves.modifiers[0]["Input_99"] = False







    
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "CURVES" and selobj.type in ["MESH","EMPTY","CURVE"]:
        pass #print"-----------------------scatter selected coll with active hair settings on same surface")

        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)  

        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=True)

        
        
        
        
        
        
        
        

        
        
        
        
        
        

        
        
        
        
        

        
        
        
        
        
        
        
        


        
        hairCurves.modifiers[0]["Input_2"] = None 
        hairCurves.modifiers[0]["Input_9"] = bpy.data.collections[collection_of_one_of_selected.name]
        hairCurves.modifiers[0]["Input_39"] = False  
        hairCurves.modifiers[0]["Input_6"][2] = 20.0
        hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  

        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value 
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except:pass
        
        
        
        
        
        
        
        
        
        


        
        
        for x in objselection: x.select_set(False)

        
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)  
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                hairCurves.modifiers[0]["Input_98"] = False  
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            context3sculptbrush(context, activeobj=hairCurves)


        
        hairCurves.modifiers[0]["Input_99"] = False




























    
    elif N_Of_Selected >=2 and len(all_found_parents) == 1 and all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES":
        if activeobj.parent.data.library: 
            self.report({'WARNING'}, "Can't Weight Paint on an object with Linked Mesh Data: paint with hair or make the data local")
        else:
            vertexgrouppaint_function(self, context,NoMasksDetected=True)







    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    










    
    
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 2 and len(selobjs_without_active_with_orencurve)>=1:
    
    
    
    
    
        pass #print"many HAIR on MANY MESHES")
        newlycreated_hair=[]



        if activeobj.type == "CURVES" or len(all_meshes)==1: all_meshes_to_scatter_onto = [activeobj] 
        else: all_meshes_to_scatter_onto = all_meshes_that_are_not_parents


        for mesh in all_meshes_to_scatter_onto:

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
                if hayr.modifiers[0]["Socket_0"] not in all_bgroups_starter: all_bgroups_starter.append(hayr.modifiers[0]["Socket_0"])







            for parentt in all_found_parents:



                
                hair = find_all_listed_paintsystems(context, activeobj=mesh, objselection=[mesh])
                all_bgroups = []
                for hayr in hair[:]:
                    if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
                all_bgroups.sort()
                loop = 1
                for biome_number in all_bgroups[:]:
                    for hayr in hair[:]:
                        if hayr[0].modifiers[0]["Socket_0"] == biome_number:
                            hayr[0].modifiers[0]["Socket_0"] = loop
                            hair.remove(hayr)
                    loop += 1
                if all_bgroups: additional_biome_n = max(all_bgroups)
                else: additional_biome_n = 0  




                for hair in parentt.children:
                    if hair in selobjs_without_active_with_orencurve:
                        for modifier in hair.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):



                            
                                hairCurves = secretpaint_create_curve(self,context, targetOBJ=mesh, brushOBJ=hair, targetCollection=Coll_of_TaragetMesh, transfer_modifier=True)
                                newlycreated_hair.append(hairCurves)
                                
                                

                                
                                
                                
                                
                                


                                
                                
                                if bpy.context.preferences.addons[__package__].preferences.checkboxKeepManualWhenTransferBiome == False:
                                    if N_Of_Selected >= 3 or hair.modifiers[0]["Input_69"]: hairCurves.modifiers[0]["Input_69"] = True  

                                
                                hairCurves.modifiers[0]["Input_68"] = hair.modifiers[0]["Input_68"]  
                                hairCurves.modifiers[0]["Socket_11"] = hair.modifiers[0]["Socket_11"]  
                                hairCurves.modifiers[0]["Input_2"] = hair.modifiers[0]["Input_2"]
                                hairCurves.modifiers[0]["Input_9"] = hair.modifiers[0]["Input_9"]
                                hairCurves.modifiers[0]["Input_72"] = hair.modifiers[0]["Input_72"]  
                                hairCurves.modifiers[0]["Input_70"] = hair.modifiers[0]["Input_70"]  
                                hairCurves.modifiers[0]["Input_82"] = hair.modifiers[0]["Input_82"]  

                                hairCurves.modifiers[0]["Input_8"] = hair.modifiers[0]["Input_8"]  
                                hairCurves.modifiers[0]["Input_15"] = hair.modifiers[0]["Input_15"]  
                                hairCurves.modifiers[0]["Input_62"] = hair.modifiers[0]["Input_62"]  
                                hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  
                                hairCurves.modifiers[0]["Input_13"] = hair.modifiers[0]["Input_13"]  

                                hairCurves.modifiers[0]["Input_51"] = hair.modifiers[0]["Input_51"]  
                                hairCurves.modifiers[0]["Input_65"] = hair.modifiers[0]["Input_65"]  
                                hairCurves.modifiers[0]["Input_6"] = hair.modifiers[0]["Input_6"]  
                                hairCurves.modifiers[0]["Input_53"] = hair.modifiers[0]["Input_53"]  
                                hairCurves.modifiers[0]["Input_23"] = hair.modifiers[0]["Input_23"]  
                                hairCurves.modifiers[0]["Input_56"] = hair.modifiers[0]["Input_56"]  
                                hairCurves.modifiers[0]["Input_98"] = hair.modifiers[0]["Input_98"]  
                                hairCurves.modifiers[0]["Input_97"] = hair.modifiers[0]["Input_97"]  

                                hairCurves.modifiers[0]["Socket_0"] = hair.modifiers[0]["Socket_0"] + additional_biome_n  
                                if len(all_bgroups_starter) >= 2: hairCurves.modifiers[0]["Socket_2"] = hair.modifiers[0]["Socket_2"]

                                if mesh.data.library:  
                                    hairCurves.modifiers[0]["Input_83_attribute_name"] = ""
                                    hairCurves.modifiers[0]["Input_83_use_attribute"] = False
                                else:
                                    hairCurves.modifiers[0]["Input_83_attribute_name"] = hair.modifiers[0]["Input_83_attribute_name"]  
                                    hairCurves.modifiers[0]["Input_83_use_attribute"] = hair.modifiers[0]["Input_83_use_attribute"]  

                                
                                if hairCurves.modifiers[0]["Input_98"] \
                                or hairCurves.modifiers[0]["Input_97"]\
                                or (allTerrainArea/   (   (1/   ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))   )   **2))            > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask and hairCurves.modifiers[0]["Input_69"]:  
                                    if hairCurves not in hair_thatNeedA_mask: hair_thatNeedA_mask.append(hairCurves)
                                    
                                    hairCurves.modifiers[0]["Input_98"] = False  
                                    hairCurves.modifiers[0]["Input_97"] = None
                                

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
            vertexgrouppaint_function(self, context,NoMasksDetected,calledfrombutton=False, being_transferred_to_newmesh=True, objselection=newlycreated_hair, activeobj=newlycreated_hair[0], paint_the_vertex=paint_the_vertex)
            
            if NoMasksDetected==False: secretpaint_viewport_mask_function(self, context, objselection=hair_thatNeedA_mask, activeobj=hair_thatNeedA_mask[0])



        
        for ojgb in newlycreated_hair:
            ojgb.modifiers[0]["Input_99"] = False
            ojgb.location = ojgb.location 

        
        
        
        
            
        
        
        


        for x in bpy.context.selected_objects: x.select_set(False)
        
        if N_Of_Selected == 2 and newlycreated_hair[0].modifiers[0]["Input_69"] == False: context3sculptbrush(context, activeobj=newlycreated_hair[0])   

        
        
        







































































    
    elif ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "MESH" \
            or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "EMPTY" \
            or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "CURVE":

        
        
        
        
        
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobj, targetCollection=Coll_of_Active, transfer_modifier=True)


        
        
        
        
        
        
        
        

        
        
        
        
        
        
        hairCurves.modifiers[0]["Input_2"] = selobj
        hairCurves.modifiers[0]["Input_9"] = None 
        hairCurves.modifiers[0]["Input_39"] = False  
        hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  
        
        
        
        
        
        
        
        
        
        
        

        if bpy.app.version_string >= "4.0.0" and bpy.app.version_string < "4.3.0": hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value = hairCurves.modifiers[0].node_group.interface.items_tree[6].default_value 
        elif bpy.app.version_string < "4.0.0":
            try: hairCurves.modifiers[0].node_group.inputs[1].default_value = hairCurves.modifiers[0].node_group.inputs[1].default_value
            except: pass

        
        
        
        
        
        

        for x in objselection: bpy.data.objects[x.name].select_set(False)

        
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)  
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask:
                hairCurves.modifiers[0]["Input_98"] = False  
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            if not activeobj.modifiers[0]["Input_69"]: context3sculptbrush(context, activeobj=hairCurves) 
            

        
        

        
        hairCurves.modifiers[0]["Input_99"] = False

        pass #print"scatter selected obj with active hair settings on same surface")
















































    
    
    
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
                    elif modif["Input_69"] == True and modif["Input_83_attribute_name"]:
                        paint_type="WEIGHT_PAINT"
                        found_to_paint.append(hoverobj)
                    elif modif["Input_69"] == False:
                        paint_type="SCULPT_CURVES"
                        found_to_paint.append(hoverobj)
                    








        
        
        elif result != {'PASS_THROUGH'} and hoverobj.type == "MESH" and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
            pass #print"KKKKKKKKKKKKKKKKKKKK")
            
            siblings_with_same_weight_paint=[]
            
            all_brush_objs=[]
            all_brush_colls=[]
            if activeobj.type=="MESH" and ActiveMode == "WEIGHT_PAINT" and activeobj.children:
                for children in activeobj.children:
                    if children.type == "CURVES" and children.modifiers:
                        for modif in children.modifiers:  
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and activeobj.vertex_groups.active.name == children.modifiers[0]["Input_83_attribute_name"]:
                                siblings_with_same_weight_paint.append(children)
                                
                                if children.modifiers[0]["Input_2"] and children.modifiers[0]["Input_2"] not in all_brush_objs: all_brush_objs.append(children.modifiers[0]["Input_2"])
                                if children.modifiers[0]["Input_9"] and children.modifiers[0]["Input_9"] not in all_brush_colls: all_brush_colls.append(children.modifiers[0]["Input_9"])
            elif activeobj.type=="CURVES":
                
                
                siblings_with_same_weight_paint.append(activeobj)
                if activeobj.modifiers[0]["Input_2"] and activeobj.modifiers[0]["Input_2"] not in all_brush_objs: all_brush_objs.append(activeobj.modifiers[0]["Input_2"])
                if activeobj.modifiers[0]["Input_9"] and activeobj.modifiers[0]["Input_9"] not in all_brush_colls: all_brush_colls.append(activeobj.modifiers[0]["Input_9"])



            all_vgroups_in_hoverobjs_children =[]
            if hoverobj.children:
                for children in hoverobj.children:
                    if children.type == "CURVES" and children.modifiers:
                        for modif in children.modifiers:
                            
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                if modif["Input_2"] in all_brush_objs or modif["Input_9"] in all_brush_colls:


                                    
                                    if len(siblings_with_same_weight_paint) <= 1:
                                        
                                        
                                        
                                        if modif["Input_83_use_attribute"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_83_use_attribute"]:
                                            if modif["Input_69"] == True and modif["Input_83_use_attribute"]:
                                                paint_type = "WEIGHT_PAINT"
                                                found_to_paint = []  
                                                found_to_paint.append(children)
                                                pass #print"(((UUUUUUUUUUUUUUUUUUUUUUU")
                                            elif modif["Input_69"] == False:
                                                paint_type = "SCULPT_CURVES"
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                pass #print"(((lllllllllllllllllllllllllll")
                                            
                                        if modif["Input_69"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_69"]:
                                            if modif["Input_69"] == True and modif["Input_83_use_attribute"]:
                                                paint_type="WEIGHT_PAINT"
                                                found_to_paint=[] 
                                                found_to_paint.append(children)
                                                pass #print"(((IIIIIIIIIIIIIIIIII")
                                            elif modif["Input_69"] == False:
                                                paint_type="SCULPT_CURVES"
                                                found_to_paint=[]
                                                found_to_paint.append(children)
                                                pass #print"(((ooooooooooooooooooooo")
                                            
                                        if modif["Input_69"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_69"] and modif["Input_83_use_attribute"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_83_use_attribute"]:
                                            if modif["Input_69"] == True and modif["Input_83_use_attribute"]:
                                                paint_type = "WEIGHT_PAINT"
                                                pass #print"(((YYYYYYYYYYYYYYYY")
                                                found_to_paint = []  
                                                found_to_paint.append(children)
                                            elif modif["Input_69"] == False:
                                                paint_type = "SCULPT_CURVES"
                                                pass #print"(((TTTTTTTTTTTTTTTTTTT")
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                pass #print"(((9999999999999999999")
                                            
                                            

                                    
                                    elif len(siblings_with_same_weight_paint) >= 2:
                                        
                                        if modif["Input_83_attribute_name"] and modif["Input_83_attribute_name"] not in all_vgroups_in_hoverobjs_children: all_vgroups_in_hoverobjs_children.append(modif["Input_83_attribute_name"])
                                        if all_vgroups_in_hoverobjs_children and modif["Input_83_attribute_name"]==all_vgroups_in_hoverobjs_children[0]:
                                            paint_type="WEIGHT_PAINT"
                                            found_to_paint.append(children)


        
        
        
        
        

        
        if found_to_paint:
            bpy.context.view_layer.objects.active = found_to_paint[0]
            if paint_type=="EDIT": curve_draw_tool(context)
            elif paint_type=="WEIGHT_PAINT": vertexgrouppaint_function(self, context, NoMasksDetected=True)
            elif paint_type=="SCULPT_CURVES":
                
                if ActiveMode == "SCULPT_CURVES": apply_paint(self,context,activeobj=found_to_paint[0], objselection=[found_to_paint[0]],applyIDs=True,keep_active_brush=True)
                else: apply_paint(self,context,activeobj=found_to_paint[0], objselection=[found_to_paint[0]],applyIDs=True )
                pass #print"(((8888888888888888888888888")


        
        elif not found_to_paint and hoverobj and hoverobj.type=="MESH" and hoverobj!=activeobj.parent and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
            if bool(hoverobj.data.library) and ActiveMode=="WEIGHT_PAINT":
                bpy.context.view_layer.objects.active = activeobj
                bpy.ops.object.mode_set(mode=ActiveMode)
            else: secretpaint_function(self, context, event,objselection = siblings_with_same_weight_paint, activeobj=hoverobj)

        
        else:
            bpy.context.view_layer.objects.active = activeobj
            bpy.ops.object.mode_set(mode=ActiveMode)





        for ob in bpy.context.selected_objects: bpy.data.objects[ob.name].select_set(False) 

        
        
        
        
        
        
        
        
        
        

        pass #print"SWICTH WHICH HAIR TO PAINT FROM SCULPT MODE OR EDIT MODE OR WEIGHT PAINT MODE")

        
        






































    
    elif ActiveMode == "OBJECT" and N_Of_Selected == 1 and activeobj.type == "CURVE":
        curve_draw_tool(context)
        pass #print"RESUME DRAWING CURVE")

    
    
    
    elif len(all_found_parents)==1 and all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES" \
    or ActiveMode == "OBJECT" and N_Of_Selected == 0:
        
        
        secretpaint_update_modifier_f(context,upadte_provenance="RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS")  
        
        
        

        
        if N_Of_Selected == 0:
            result = bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))
            hoverobj = bpy.context.active_object
            if result != {'PASS_THROUGH'} and hoverobj.type == "CURVES" and hoverobj.modifiers:
                for modif in hoverobj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                        if modif["Input_69"] == True and modif["Input_83_use_attribute"] == True: vertexgrouppaint_function(self, context, NoMasksDetected=True)
                        elif modif["Input_69"] == False:
                            
                            apply_paint(self, context, activeobj=hoverobj, objselection=[hoverobj], applyIDs=True)
                        else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
                    else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
            else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
            bpy.data.objects[hoverobj.name].select_set(False)  

            for ob in objselection: 
                bpy.data.objects[ob.name].select_set(False)


        
        elif N_Of_Selected == 1: 
            if activeobj.modifiers[0]["Input_69"] == True and activeobj.modifiers[0]["Input_83_use_attribute"] == True:
                vertexgrouppaint_function(self, context,NoMasksDetected=True)

            elif activeobj.modifiers[0]["Input_69"] == True and activeobj.modifiers[0]["Input_83_use_attribute"] == False:
                apply_paint(self, context, activeobj=activeobj)

            
            elif activeobj.modifiers[0]["Input_69"] == False:
                
                apply_paint(self, context, activeobj=activeobj, objselection=[activeobj], applyIDs=True)


            
            
            
            
        
        
        

            
            
            
            

        
        
        
        
        
        
        
        
        


        for x in objselection: bpy.data.objects[x.name].select_set(False)

        pass #print"RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS")













    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

































    
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

        
        for material_slot in activeobj.material_slots:
            if material_slot.material and material_slot.material.name not in hairCurves.data.materials:
                hairCurves.data.materials.append(material_slot.material)

        
        
        
        obj_for_dimensions = activeobj
        if activeobj.type=="MESH" and activeobj.modifiers:  
            for modif in activeobj.modifiers:
                if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                    node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                    for input in node_group_inputs_temp:
                        if input.socket_type == "NodeSocketObject" and input.name == "Parent":
                            if modif[input.identifier] and modif[input.identifier].type == "MESH": obj_for_dimensions = modif[input.identifier]
        if max(obj_for_dimensions.dimensions)>0: hairCurves.modifiers[0]["Input_68"] = (1 / ( max(obj_for_dimensions.dimensions)  **2)  )   *2    


        dont_set_drawing_tool = False
        if circulararray or straightarray:  
            dont_set_drawing_tool =True
            hairCurves.modifiers[0]["Input_65"][0] = 1.5708
            hairCurves.modifiers[0]["Input_65"][1] = -1.5708

        curve_draw_tool(context, dont_set_drawing_tool=dont_set_drawing_tool)
        context3sculptbrush(context)
        hairCurves.modifiers[0]["Input_2"] = activeobj
        hairCurves.location= bpy.context.scene.cursor.location
        pass #print"DRAW CURVE, OBJ MODE, 1 or 2")

    










    
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
        bpy.context.object.modifiers[0]["Input_2"] = bpy.data.objects[selobj.name]
        pass #print"draw sel obj with settings of active curve")




    

    
class orenscatter(bpy.types.Operator):
    """Select an object and a target, paint. Also works from the Asset Browser. Also Converts procedural generation into manual hair"""
    bl_idname = "secret.paint"
    bl_label = "Paint"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        
        
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        secretpaint_function(self, context, event)
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

    if "current_mode" in kwargs:current_mode = kwargs.get("current_mode")
    else: current_mode = bpy.context.object.mode
    if current_mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")

    saveactual_objselection = bpy.context.selected_objects
    saveactual_activeobj = bpy.context.active_object


    if current_mode == "WEIGHT_PAINT":
        for hair in ORIGINALactiveobj.children:
            if hair.modifiers[0]["Input_83_attribute_name"] == ORIGINALactiveobj.vertex_groups.active.name:
                bpy.context.view_layer.objects.active = hair
                hair_thatneeds_to_switch = hair
                break
    else:
        hair_thatneeds_to_switch = ORIGINALactiveobj

    if len(objselection) == 1 and hair_thatneeds_to_switch.type == "CURVES" or \
            len(objselection) == 1 and hair_thatneeds_to_switch.type == "CURVE":
        
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
    if N_Of_Selected:
        for obj in objselection: 

            if obj != hoverobj:
                randomselectedobj = obj
                selected_without_active.append(obj)

            
            if obj.type != "CURVES" and obj.type != "CURVE": randomselected_non_hair = obj
            

            if obj.type != "CURVES": all_objs_are_hair = False
            

            
            if obj.type == "CURVES": all_selected_hair.append(obj)

            
            if obj.type != "CURVES": all_selected_non_hair.append(obj)

    

    
    if N_Of_Selected == 2 and randomselectedobj.type == "CURVES" and hoverobj.type != "CURVES" \
            or N_Of_Selected == 2 and randomselectedobj.type == "CURVE" and hoverobj.type != "CURVES":

        pass #print"switch sel hair to active obj", )

        
        
        
        for hair in selected_without_active:
            hair.data.materials.clear()
            for mat_slot in hoverobj.material_slots:
                if mat_slot.material: hair.data.materials.append(mat_slot.material)

            
            
            
            hair.modifiers[0]["Input_2"] = hoverobj  
            hair.modifiers[0]["Input_9"] = None  
            
            hair.modifiers[0]["Input_39"] = False  
            
            
            
            
            
            
            
            

            bpy.context.active_object.select_set(False)
            for obj in bpy.context.selected_objects: bpy.context.view_layer.objects.active = obj

        for x in bpy.context.selected_objects: x.select_set(False)  
        bpy.context.view_layer.objects.active = saveactual_activeobj
        bpy.ops.object.mode_set(mode=current_mode)



    
    elif N_Of_Selected >= 2 and all_objs_are_hair:
        pass #print"all sel objs are hair and link modif from active", )

        for hair in selected_without_active:

            hair.data.materials.clear()
            for mat_slot in hoverobj.material_slots:
                if mat_slot.material: hair.data.materials.append(mat_slot.material)

            hair.modifiers[0]["Input_2"] = hoverobj.modifiers[0]["Input_2"]  
            hair.modifiers[0]["Input_9"] = hoverobj.modifiers[0]["Input_9"]  
            hair.modifiers[0]["Input_68"] = hoverobj.modifiers[0]["Input_68"]  
            
            hair.modifiers[0]["Input_39"] = False  
            hair.modifiers[0]["Input_86"] = hoverobj.modifiers[0]["Input_86"]  
            hair.modifiers[0]["Input_89"] = hoverobj.modifiers[0]["Input_89"]  
            hair.modifiers[0]["Input_91"] = hoverobj.modifiers[0]["Input_91"]  
            hair.modifiers[0]["Input_92"] = hoverobj.modifiers[0]["Input_92"]  
            
            
            
            
            
            hair.location = hair.location

        
        if N_Of_Selected == 2:
            bpy.context.active_object.select_set(False)
            for obj in bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = obj


    
    elif N_Of_Selected >= 3:
        pass #print"switch even multiple hair, use all non hair objs to switch to collection or a single", )

        
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

                hair.modifiers[0]["Input_2"] = None
                hair.modifiers[0]["Input_9"] = bpy.data.collections[layerColl.name]
                hair.modifiers[0]["Input_39"] = False  

                
                bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  
                bpy.ops.object.mode_set(mode=current_mode)
                hair.location = hair.location

        elif len(all_selected_non_hair) == 1:
            for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)

            
            
            
            

            for hair in all_selected_hair:
                hair.modifiers[0]["Input_2"] = bpy.data.objects[all_selected_non_hair[0].name]
                hair.modifiers[0]["Input_9"] = None
                hair.modifiers[0]["Input_39"] = False  
                
                
                
                
                
                
                
                

                
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
        pass #print"No active UV map found.")  
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
        
        pass #printf"Overlapping UVs found on faces")  
        bm.free()  
        return True
    else:
        pass #print"No overlapping UVs detected.")  
        bm.free()  
        return False

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    



def Check_if_trigger_UV_Reprojection(self,context,**kwargs):

    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    objselection = kwargs.get("objselection") if "objselection" in kwargs else bpy.context.selected_objects
    if not isinstance(objselection, (list, tuple)): objselection = [objselection]  
    if activeobj not in objselection: objselection.append(activeobj)

    
    
    
    
    
    

    
    
    
    surface_to_reUV = []
    
    for obj in objselection:
        if obj.type == "CURVES":
            for modif in obj.modifiers:  
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    
                    if obj.parent and obj.parent.type == "MESH":
                        if obj.parent not in surface_to_reUV: surface_to_reUV.append(obj.parent)
                        
                        
                        
                        
                        
                        


        elif obj.type == "MESH":
            if obj not in surface_to_reUV: surface_to_reUV.append(obj)
            
            
            
            

    for terrain in surface_to_reUV:
        triangles = sum(polygon.loop_total // 3 for polygon in terrain.data.polygons)

        if triangles < bpy.context.preferences.addons[__package__].preferences.trigger_auto_uvs:
            
            reproject_function(self,context,automatically_triggererd=True,activeobj=terrain, objselection=[terrain])
            
            
            
            
            
            

    return{'FINISHED'}







































































def reproject_function(self,context,**kwargs):
    start_time = time.perf_counter()

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

    











    

    if surface_to_reUV:
        for surface in surface_to_reUV:
            

            
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

                
                
                
                pass #print"REPROJIIIIIII", surface)
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
                                    if restoremode != "EDIT": bpy.ops.object.mode_set(mode="EDIT")
                                    bpy.ops.mesh.select_all(action='SELECT')
                                    bpy.ops.uv.smart_project(angle_limit=1.20428, island_margin=0.01, area_weight=1, correct_aspect=True, scale_to_bounds=True)
                                    
                                    if restoremode != "EDIT": bpy.ops.object.mode_set(mode=restoremode)
                                    
                                break
                except: pass #print"FAILED TO REPROJECT THE UV")

                
                
                

                
                for UVV in surface.data.uv_layers:
                    if UVV.active_render:
                        UVV.active = True
                        break

            
            
            








    if hairlist:

        
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


        
        
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        changed_selected_objs_so_restore_is_needed = True
        loop = 0
        for ob in hairlist:
            if ob not in unselected_siblings_list:
                if loop == 0:
                    bpy.context.view_layer.objects.active = ob
                    changed_active_obj_so_restore_is_needed = True
                loop+=1 

                bpy.data.objects[ob.name].select_set(True)
                bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
        
        
        



    
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

    
    


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    

    end_time = time.perf_counter()

    pass #printf"@@@ Reprojected UVs: reproject_function,snap hair to closest surface:{not automatically_triggererd}", "Milliseconds:",(end_time - start_time) * 1000)
    
    return {'FINISHED'}
class clean_hair_orencurve(bpy.types.Operator):
    """When the terrain has incorrect UVs, for example after sculpting the terrain with dynamic topology, use this to quickly recreate the UVs. This is needed in order to be able to paint manually (geometry node hair limitation; only needed for manual painting, not for the procedural distribution). Also snaps hair to the closest surfaces"""
    bl_idname = "secret.fixdyntopo"
    bl_label = "Reproject"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        reproject_function(self, context)
        return {'FINISHED'}
def context283482(context,**kwargs):    


    if "coll_target" in kwargs:
        Importing_Into_Active = True
        coll_target = kwargs.get("coll_target")
    else:
        Importing_Into_Active = False
        coll_target = None

    activeobj = bpy.context.active_object
    objs = bpy.context.selected_objects


    for window in context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                with context.temp_override(window=window, area=area):

                    
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







                    
                    

                    
                    
                    
                    
                    




                    
                    


                    
                    
                    





                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    

                break

    return {"FINISHED"}
class orengroup(bpy.types.Operator):
    """Group selected objects in a subcollection of the active collection. Name it as the active object. Shortcut also works in the Outliner"""
    bl_idname = "secret.group"
    bl_label = "Collection"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        context283482(context)
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
    bpy.context.scene.tool_settings.unified_paint_settings.weight = 1
    bpy.ops.object.vertex_group_set_active(group=vertex_group)  
    
    

    activeobj.modifiers[0]["Input_69"] = True  
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

    biomeofactive=activeobj.modifiers[0]["Input_83_attribute_name"]
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
                                if modif["Input_83_attribute_name"] and modif["Input_83_attribute_name"] not in all_vertex_groups: all_vertex_groups.append(modif["Input_83_attribute_name"])
    

    
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
                    if vgroup == hair.modifiers[0]["Input_83_attribute_name"]:

                        hair.modifiers[0]["Input_83_attribute_name"] = biomename
                        hair.modifiers[0]["Input_69"] = True

                        if hair.modifiers[0]["Input_83_use_attribute"] == False: hair.modifiers[0]["Input_83_use_attribute"] =True 
                        
                        
                        
                        
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
            if hair.modifiers[0]["Input_83_attribute_name"] and hair.modifiers[0]["Input_83_attribute_name"] not in removed_vgroups: removed_vgroups.append(hair.modifiers[0]["Input_83_attribute_name"])
            hair.modifiers[0]["Input_83_attribute_name"] = ""
            if hair.modifiers[0]["Input_83_use_attribute"] == True: hair.modifiers[0]["Input_83_use_attribute"] = False  
            hair.location = hair.location
            if hair.parent: parent_of_hair=hair.parent

        
        all_Vgroups_used_in_biome=[]
        for child in parent_of_hair.children:
            if child.type == "CURVES" and child.modifiers or child.type == "CURVE" and child.modifiers:
                for modif in child.modifiers:  
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        if child.modifiers[0]["Input_83_attribute_name"] and child.modifiers[0]["Input_83_attribute_name"] not in all_Vgroups_used_in_biome: all_Vgroups_used_in_biome.append(child.modifiers[0]["Input_83_attribute_name"])
        for g in removed_vgroups:
            if g not in all_Vgroups_used_in_biome: parent_of_hair.vertex_groups.remove(parent_of_hair.vertex_groups.get(g))








    
    elif activeobj.modifiers[0]["Input_83_use_attribute"]==False:
    
    
    
        
        numb = 1
        while surfaceobj.vertex_groups.get("Biome"+str(numb)): numb += 1
        biomename = "Biome"+str(numb)
        surfaceobj.vertex_groups.new(name=biomename)

        
        
        for hair in only_hair_from_selected:
             
            hair.modifiers[0]["Input_83_attribute_name"] = biomename
            hair.modifiers[0]["Input_69"] = True
            if hair.modifiers[0]["Input_83_use_attribute"] == False: hair.modifiers[0]["Input_83_use_attribute"] = True  
            
            
            
            
            hair.location = hair.location  

        
        bpy.data.objects[surfaceobj.name].select_set(True)  
        bpy.context.view_layer.objects.active = surfaceobj  
        brush_vertex_paint(activeobj,objselection,biomename, context)

        


    
    elif len(all_vertex_groups) >= 1 and vertex_ofParent:
    
    
    
    

        
        if len(only_hair_from_selected)!=1:
            for hair in only_hair_from_selected:
                
                hair.modifiers[0]["Input_83_attribute_name"] = biomeofactive
                hair.modifiers[0]["Input_69"] = True
                if hair.modifiers[0]["Input_83_use_attribute"] == False: hair.modifiers[0]["Input_83_use_attribute"] = True  
                
                
                
                
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
            hair=[]
            parent = obj.parent
            if obj.type=="CURVES" and parent:   
                for hai in parent.children: 
                    if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                        for modifier in hai.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                                hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
            
            elif obj.type=="MESH" or obj.type=="EMPTY":
                for hayr in bpy.context.scene.objects:
                
                    if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                        for modifier in hayr.modifiers: 
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                                hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
            
            
            
            hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]


        if event.alt: remove_vgroup=True  
        else: remove_vgroup=False  
        vertexgrouppaint_function(self,context,NoMasksDetected=True,calledfrombutton=True, called_for_entire_biome=True, activeobj=hair_in_bgroup[0],objselection=hair_in_bgroup , remove_vgroup=remove_vgroup)
        return {'FINISHED'}
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
                                    if modif["Input_9"] and modif["Input_9"].name in all_colls_used_as_brush:
                                        
                                            
                                            bpy.data.objects[obj.name].select_set(True)
                                            bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]  
                                            
                                            
                                    if modif["Input_2"] and modif["Input_2"] in objselection:
                                        
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
                                    if modif["Input_9"]:
                                        for ob in bpy.data.collections[modif["Input_9"].name].all_objects:
                                            if len(objselection)>=2:
                                                ob.select_set(True)
                                                bpy.context.view_layer.objects.active = ob
                                                bpy.ops.view3d.view_selected(use_all_regions=True)
                                            elif len(objselection)==1:
                                                
                                                ob.select_set(True)
                                                bpy.context.view_layer.objects.active = ob
                                                bpy.ops.view3d.view_selected(use_all_regions=True)
                                                

                                    if modif["Input_2"]:
                                        if len(objselection)>=2:
                                            modif["Input_2"].select_set(True)
                                            bpy.context.view_layer.objects.active = modif["Input_2"]
                                            bpy.ops.view3d.view_selected(use_all_regions=True)
                                        elif len(objselection)==1:
                                            
                                            modif["Input_2"].select_set(True)
                                            bpy.context.view_layer.objects.active = modif["Input_2"]
                                            bpy.ops.view3d.view_selected(use_all_regions=True)
                                            

                                        
                                        
                                        
                                        
                                        











        

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        



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
                        obj.modifiers[0]["Input_50"] = True  
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
                        modif["Input_99"] = True

            
            for modif in obj.modifiers:  
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                    if modif["Input_2"] and modif["Input_2"] not in all_brush_coll_instans:
                        if modif["Input_2"].instance_collection: all_brush_coll_instans.append(modif["Input_2"])

                        
                        elif modif["Input_2"].modifiers and modif["Input_2"].modifiers[0].type == "NODES" and modif["Input_2"].modifiers[0].node_group and "ASSEMBLY" in modif["Input_2"].modifiers[0].node_group.name and modif["Input_2"].modifiers[0].show_viewport == True:
                            if modif["Input_2"].modifiers[0] not in all_assemblies_modifiers: all_assemblies_modifiers.append(modif["Input_2"].modifiers[0])
                            modif["Input_2"].modifiers[0].show_viewport = False

                    if modif["Input_9"]:
                        for obij in modif["Input_9"].all_objects:
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
                ob.parent = obj.parent  
                ob.matrix_parent_inverse = obj.parent.matrix_world.inverted()  
            else:
                ob.parent = obj.parent  
                ob.matrix_parent_inverse = obj.parent.matrix_world.inverted()  



        
        all_empties_coordinates = []
        for ob in new_obs:
            if ob.type == "EMPTY" and str(ob.location) not in all_empties_coordinates:
                
                all_empties_coordinates.append(str(ob.location))
            elif ob.type == "EMPTY" and str(ob.location) in all_empties_coordinates and ob not in objs_to_delete_afterwards:
                
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
        bpy.context.object.modifiers[0]["Input_2"] = bpy.data.objects[brushobj]
        

        
        
        
        
        
        
        

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
                    brushobj = obj.modifiers[0]["Input_2"]
                    custommaterial=None
                    if obj.modifiers[0]["Input_39"] and obj.modifiers[0]["Input_40"]: custommaterial = obj.modifiers[0]["Input_40"]

                    
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


                    obj.modifiers[0]["Input_2"] = brushobj
                    obj.modifiers[0]["Input_39"] = False
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
                        if modif["Input_2"] and modif["Input_2"] and modif["Input_2"] not in all_brush_objs: all_brush_objs.append(modif["Input_2"])
                        if modif["Input_9"] and modif["Input_9"] and modif["Input_9"] not in all_brush_objs: all_brush_collections.append(modif["Input_9"])
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
            if ob.modifiers[0]["Input_68"] < largest.modifiers[0]["Input_68"]: largest=ob
        
        
        
        
        

        xsize =  1 / ((largest.modifiers[0]["Input_68"] ** 0.5) * (largest.modifiers[0]["Input_100"]** 0.5))     
        
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
                    hair.modifiers[0]["Input_69"] = True
                    if hair.modifiers[0]["Input_83_use_attribute"] == True: hair.modifiers[0]["Input_83_use_attribute"] = False  
                    
                    
                    
                    hair.modifiers[0]["Input_83_attribute_name"] = ""
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
        folder = bpy.context.preferences.addons[__package__].preferences.biome_library + "/blender_assets.cats.txt"   
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
    path= bpy.context.preferences.addons[__package__].preferences.biome_library + os.path.dirname(biome_name) 
    if not os.path.exists(path): os.makedirs(path) 

    
    temp_blend=(path+ "\\tempSecretPaintExport.blend").replace("\\", "\\\\")
    bpy.ops.wm.save_as_mainfile(copy=True, filepath=temp_blend)

    

    
    
    
    
    
    finalpath = path + '/' + os.path.basename(biome_name)
    if not finalpath.endswith(".blend"): finalpath= finalpath+".blend" 
    
    
    
    
    
    
    if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={*bpy.data.masks}, fake_user=False, path_remap="ABSOLUTE")

    
    
    move_objects_script = path+"/tempSecretExportScript.py"  
    
    
    current_file = bpy.data.filepath.replace("\\", "\\\\")
    move_objects_script_content = f'''
import bpy
import os
import re




from pathlib import Path  
import addon_utils






bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection


source_file_path = "{temp_blend}" 
with bpy.data.libraries.load(source_file_path) as (data_from, data_to):
    data_to.collections = [name for name in data_from.collections if "{new_collection.name}"== name]  
    
    



    
    


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
                




blender_version = bpy.app.version_string
addon_path=[]
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":  
        addon_path = os.path.dirname(mod.__file__)
        break


nodes_to_switch = []
cleanup_generator = []
for node_tree in bpy.data.node_groups:
    
    if node_tree.name == "Secret Paint" or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":  
        if not node_tree.library: node_tree.name = "Secret Paint.001"  
        if node_tree not in nodes_to_switch: nodes_to_switch.append(node_tree)
    
    if node_tree.name == "Secret Generator" or node_tree.name.startswith("Secret Generator") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999": 
        if not node_tree.library: node_tree.name = "Secret Generator.001"  
        if node_tree not in cleanup_generator: cleanup_generator.append(node_tree)




all_previous_nodes = set(bpy.data.node_groups)
if blender_version < "4.1": file_path= addon_path + "/Secret Paint 4.0 and older.blend"
elif blender_version < "4.2.0": file_path= addon_path + "/Secret Paint 4.1.blend"
elif blender_version < "4.2.1": file_path= addon_path + "/Secret Paint 4.2.0.blend"
elif blender_version >= "4.2.1": file_path= addon_path + "/Secret Paint.blend"
inner_path = "NodeTree"
object_name = "Secret Paint"


try: bpy.ops.wm.append(filepath=os.path.join(file_path, inner_path, object_name),directory=os.path.join(file_path, inner_path),filename=object_name)
except:pass #print"[[[[[[[[[[[[ SECRET PAINT UPDATE FAILED!! CRITICAL CORRUPTION WEIRD")

for lib in bpy.data.libraries: 
    
    if lib.name in ["Secret Paint.blend","Secret Paint 4.0 and older.blend","Secret Paint 4.1.blend","Secret Paint 4.2.0.blend"]: bpy.data.libraries.remove(lib, do_unlink=True)



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
        "blender",
        
        
        "-b", finalpath,  
        "--python", move_objects_script
        
        
        
        
    ]
    subprocess.run(command)
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
def paint_from_library_function(self, context, event, **kwargs):

    justImport = kwargs.get("justImport") if "justImport" in kwargs else False
    switch_asset = kwargs.get("switch_asset") if "switch_asset" in kwargs else False
    activeobj = bpy.context.active_object
    current_mode = None

    if justImport == False:
        if activeobj == None or activeobj.type not in ["CURVES","CURVE","MESH"]:
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

    
    
    if justImport == False:
        if bpy.context.preferences.addons[__package__].preferences.checkboxHideImported: 
            all_collections = []
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection, all_collections)
            for coll in all_collections: 
                if coll.name.startswith("Secret Assets"):
                    pass #print"SEEEEEEE FOUNDDDDDDDDDDDDDDDDDDDDDDD")
                    FoundHiddenCollection = recurLayerCollection(bpy.context.view_layer.layer_collection, coll.name)
                    FoundHiddenCollection_status = coll.hide_viewport
                    coll.hide_viewport = False  
                    bpy.context.view_layer.active_layer_collection = FoundHiddenCollection
                    coll_to_hide = coll   
                    break
            if not bpy.context.view_layer.active_layer_collection.name.startswith("Secret Assets"): 
                pass #print"CREAAAAAAAAAAAAAAAAAATTTTTTT")
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




    pass #print"")
    pass #print"")
    pass #print"")
    pass #print"@@@@@@@@@@ new loop @@@@@@@@")
    pass #print"")
    pass #print"")
    pass #print"")


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


            
            if switch_asset:
                if asset_type == "Object": paintbrushswitch_f(self, context, activeobj=bpy.data.objects[asset_fullpath.name], objselection=[activeobj], current_mode=current_mode)   
                elif asset_type == "Collection":
                    
                    
                    
                    paintbrushswitch_f(self, context, activeobj=activeobj, objselection=[x for x in bpy.data.collections[asset_fullpath.name].all_objects], current_mode=current_mode)   

            else: 
                if asset_type == "Object": brush_to_paint_with=[bpy.data.objects[asset_fullpath.name]]
                elif asset_type == "Collection":
                    brush_to_paint_with=[]
                    for oibj in bpy.data.collections[asset_fullpath.name].all_objects:
                        if oibj.name.startswith("Secret Paint Biome"): brush_to_paint_with = [j for j in oibj.children if j.type=="CURVES" and j.modifiers and j.data.name.startswith("Secret Paint")]
                    if not brush_to_paint_with: brush_to_paint_with = [x for x in bpy.data.collections[asset_fullpath.name].all_objects]
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


            all_previous_objects = set(bpy.data.objects)  
            all_previous_nodes = set(bpy.data.node_groups)  
            all_previous_objectData = set(bpy.data.meshes) 
            
            all_previous_collections=[]
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection,all_previous_collections)


        

            if bpy.app.version_string >= "4.0.0": import_setting = bpy.context.space_data.params.import_method
            elif bpy.app.version_string < "4.0.0": import_setting = bpy.context.space_data.params.import_type

            try: 
                
                if import_setting == 'LINK':  
                    bpy.ops.wm.link(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                    directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                    instance_collections=False, active_collection=True,do_reuse_local_id=False)
                elif import_setting == 'APPEND':  
                    bpy.ops.wm.append(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                      directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                      instance_collections=False, active_collection=True)
                else: 
                    bpy.ops.wm.append(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                      directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                      instance_collections=False, active_collection=True, do_reuse_local_id=True)
            except: pass #print"---- ERROR IMPORTT")


            
            
            
            




            



            

            
            
            all_with_new_collections=[]
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection,all_with_new_collections)
            
            
            
            
            
            
            
            
            

            
            
            
            loop =0
            for coll in all_with_new_collections[:]:#bpy.data.collections: 
                if coll not in all_previous_collections[:] and coll.library:
                    
                    
                    newest_coll = coll.override_hierarchy_create(scene=bpy.context.scene, view_layer=bpy.context.view_layer, reference=coll, do_fully_editable=True) 
                    if loop == 0: all_with_new_collections.append(newest_coll)
                    all_with_new_collections.remove(coll)
                    bpy.data.collections.remove(coll, do_unlink=True)  
                    loop+=1
                    
                    
                    


            


            
            for top_level_collection in bpy.context.scene.collection.children[:]:
                
                
                

                
                if top_level_collection not in all_with_new_collections[:]:
                    
                    bpy.data.collections.remove(top_level_collection, do_unlink=True)  
                

            




            new_obs = list(set(bpy.data.objects) - all_previous_objects)  
            if not new_obs:
                pass #print"----ERROR no new_obs")
                return{'FINISHED'} 


            
            
            
            
            
            
            
            
            

            

            
            all_materials = []
            
            for ob in new_obs:
                

                ob.make_local()  

                
                if ob.name not in bpy.context.view_layer.objects:
                    pass #print"# Not in View layer", ob.name)
                    new_obs.remove(ob)
                    bpy.data.objects.remove(ob,do_unlink=True)
                    continue

                if ob.type in ["CURVES", "CURVE", "LIGHT"]: ob.data.make_local()  



                
                for mat_slot in ob.material_slots:
                    if mat_slot.material:
                        mat = mat_slot.material
                        
                        mat_slot.link = 'OBJECT'
                        
                        
                        try:
                            mat_slot.material = mat  
                        except:
                            
                            pass #print"---####### ERROR: ",ob.name, mat_slot.material )  
                        
                        if mat not in all_materials and mat != None: all_materials.append(mat)
            for matery in all_materials: matery.make_local()  


            
                
                
                
                
                
                    
                    

                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                


                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                










            
            

            
            new_nodes = list(set(bpy.data.node_groups) - all_previous_nodes)  
            for node in new_nodes:
                if node.library:
                    pass #printf"## LOCALIZED node: {node.name}")
                    node.make_local()



            
            copy_hair_settings = False
            moveinteration = 1
            all_coordinates = []
            for obj in bpy.context.scene.objects:
                all_coordinates.append(str(obj.location))



            
            
            activated_scatter = False
            if justImport:
                
                
                target_location = bpy.context.scene.cursor.location


            
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
            center = sum((obj.location for obj in new_obs), mathutils.Vector()) / len(new_obs) 
            
            for obj in new_obs:
                
                if not obj.parent and obj.visible_get() or obj.parent not in new_obs and obj.visible_get(): 
                    
                    
                    obj.location += target_location - Vector(center) 
                    obs_without_parent_for_recenter_coll_origin.append(obj)

                    

            
            
            
            


            
            biome_to_use_as_paint=[]
            terrains_with_hair=[]
            for obj in new_obs:
                if obj.type == "CURVES":
                    if obj.modifiers:
                        for modif in obj.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                if obj.parent not in terrains_with_hair: terrains_with_hair.append(obj.parent)  

            
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
            elif asset_type == "Object": biome_to_use_as_paint = [obs_without_parent_for_recenter_coll_origin[0]]
            



            
            
            secretpaint_update_modifier_f(context,upadte_provenance="def paint_from_library_function(self, context, event, **kwargs)")  

            
            
            

            
            
            
            


            
            importpainting_multiple_assets = True if len(sel_assets) >=2 else False
            if activated_scatter:
                pass #print"§§§§§§§§§§§§§ activated scatter", activeobj.name,"biome_to_use_as_paint", [x.name for x in biome_to_use_as_paint])
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



            
            
            
            
            
            
            
            
            


    if coll_to_hide: coll_to_hide.hide_viewport = FoundHiddenCollection_status 
    if new_coll_was_created_so_hide_viewport: 
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
        
        
        
        
        
        
        
        if blender_version < "4.1": file_path= addon_path + "/Secret Paint 4.0 and older.blend"
        elif blender_version < "4.2.0": file_path= addon_path + "/Secret Paint 4.1.blend"
        elif blender_version < "4.2.1": file_path= addon_path + "/Secret Paint 4.2.0.blend"
        elif blender_version >= "4.2.1": file_path= addon_path + "/Secret Paint.blend"
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

                        hair.modifiers[0]["Input_39"] = True
                        hair.modifiers[0]["Input_40"] = bpy.data.materials[newmat]
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


        if bpy.context.scene.tool_settings.unified_paint_settings.weight == 0:
            bpy.context.scene.tool_settings.unified_paint_settings.weight = 1
        else:
            bpy.context.scene.tool_settings.unified_paint_settings.weight = 0

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
                parent_of_current_object = activeobj.modifiers[0][input.identifier]
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
                            all_assemblies_and_their_parent.append((obj,modif[input.identifier]))
                            if modif[input.identifier] not in all_objs_used_as_parents: all_objs_used_as_parents.append(modif[input.identifier])



    
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
        for ob in final_assemblies_to_process: ob.select_set(True)
    else:
        self.report({'INFO'}, "Updated Existing Assembly")
        for ob in final_assemblies_to_process: ob.select_set(True)

    end_time = time.perf_counter()
    pass #print"Milliseconds 1111 (Ping):",(end_time - start_time) * 1000)
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
                        activeobj = modif[input.identifier]
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
                        if input.socket_type == "NodeSocketObject" and input.name == "Parent" and modif[input.identifier] == activeobj and modif not in all_modif_to_update:
                            
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
        node_group.links.new(SetInstanceTransform.outputs[0], JoinGeometry.inputs[0])
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
            node_group.links.new(SetInstanceTransform.outputs[0], JoinGeometry.inputs[0])
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
                            if loop == 3: modif[input.identifier] = activeobj
                            elif loop >= 4: modif[input.identifier] = all_children[loop - 4]
                            loop += 1


        node_group.links.new(realize_instances_node.outputs[0], output.inputs[0])  

    end_time = time.perf_counter()
    pass #print"Milliseconds 22222 (Ping):",(end_time - start_time_2) * 1000)
    start_time = time.perf_counter()
    return there_are_assemblies_to_update, processing_original_activeobj


class assembly(bpy.types.Operator):
    """Group the Active Object, its children and constraints into a non-destructive assembly. Alt + Click to merge into a mesh. You can add new objects to the assembly by simply parenting them to the original object. You can then update the assembly by pressing the button again. You can also create assemblies within assemblies to keep modelling procedurally. This works with everything, even complex rigs. It's a better version of collection instances with none of the drawbacks"""
    bl_idname = "secret.assembly"
    bl_label = "Secret Assembly_f"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        if blender_version < "4.2.0":
            self.report({'ERROR'}, "Secret Paint Assemblies are only available from Blender 4.2 due to a lack of nodes")
        elif event.alt: convert_and_join_f(self,context)
        else: assembly_1(self,context)
        return {'FINISHED'}






























































































































def export_unreal_f(self,context,export_textures):

    try:
        blend_file_path = bpy.data.filepath
        directory = os.path.dirname(blend_file_path)
        
        
        

        
        bpy.ops.wm.usd_export(
        filepath=directory + "\\" + os.path.basename(blend_file_path) + ".usdc",
        selected_objects_only=True,
        visible_objects_only=True,
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
        export_global_forward_selection='NEGATIVE_Z',
        export_global_up_selection='Y',
        export_textures=False,
        
        overwrite_textures=False,
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

    except:
        self.report({'ERROR'}, "Save this project before exporting. The objects will be exported next to the Blend file")
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




addon_keymaps = []





import rna_keymap_ui
class secret_menu(bpy.types.AddonPreferences):
    bl_idname = __package__



    auto_check_update : bpy.props.BoolProperty(name="Auto-check for Update", description="If enabled, auto-check for updates using an interval", default=True)
    updater_interval_months : bpy.props.IntProperty(name='Months', description="Number of months between checking for updates", default=0, min=0)
    updater_interval_days : bpy.props.IntProperty(name='Days',description="Number of days between checking for updates",default=1,min=0,max=31)
    updater_interval_hours : bpy.props.IntProperty(name='Hours',description="Number of hours between checking for updates",default=0,min=0,max=23)
    updater_interval_minutes : bpy.props.IntProperty(name='Minutes',description="Number of minutes between checking for updates",default=0,min=0,max=59)

    checkboxKeepManualWhenTransferBiome: bpy.props.BoolProperty(name="Keep Manual When Transferring Biomes", description="When transferring biomes from a terrain to another: keep the paint systems in manual mode instead of automatically switching everything to procedural", default=False)
    checkboxHideImported: bpy.props.BoolProperty(name="Hide Imported Paint Assets", description="When importing and painting objects from the asset browser (Q), hide them in a new collection called Hidden Assets (instead of having them visible next to the terrain)", default=False)
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
        layout.prop(self, "checkboxOverrideBrushes")
        layout.prop(self, "trigger_viewport_mask")
        layout.prop(self, "trigger_auto_uvs")

        row = layout.row()
        row = layout.row()
        row = layout.row()
        


        box = layout.box()
        col = box.column()
        col.label(text="Keymap List:", icon="KEYINGSET")

        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user
        old_km_name = ""
        get_kmi_l = []
        for km_add, kmi_add in addon_keymaps:
            for km_con in kc.keymaps:
                if km_add.name == km_con.name:
                    km = km_con
                    break

            for kmi_con in km.keymap_items:
                if kmi_add.idname == kmi_con.idname:
                    if kmi_add.name == kmi_con.name:
                        get_kmi_l.append((km, kmi_con))

        get_kmi_l = sorted(set(get_kmi_l), key=get_kmi_l.index)

        for km, kmi in get_kmi_l:
            if not km.name == old_km_name:
                col.label(text=str(km.name), icon="DOT")
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
            col.separator()
            old_km_name = km.name
















































































classes = [

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
    export_unreal,


    ]






def register():

    
    
    
    
    
    if auto_updater_status: addon_updater_ops.register(bl_info)

    

    for cls in classes:
        bpy.utils.register_class(cls)



    bpy.types.Scene.mypropertieslist = bpy.props.PointerProperty(type= MyPropertiesClass)

    bpy.types.FILEBROWSER_HT_header.append(checkboxImportWithoutPainting_f)

    


    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon.keymaps



    km = kc.get("Object Mode")
    if not km: km = kc.new("Object Mode")
    kmi = km.keymap_items.new("secret.paint", "Q", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("Sculpt Curves")
    if not km:
        km = kc.new("Sculpt Curves")
    kmi = km.keymap_items.new("secret.paint", "Q", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("Weight Paint")
    if not km:
        km = kc.new("Weight Paint")
    kmi = km.keymap_items.new("secret.paint", "Q", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("Curve")
    if not km:
        km = kc.new("Curve")
    kmi = km.keymap_items.new("secret.paint", "Q", "PRESS")
    addon_keymaps.append((km, kmi))


    km = kc.get("File Browser Main")
    if not km:
        km = kc.new("File Browser Main")
    kmi = km.keymap_items.new("secret.paint_from_library", "Q", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("File Browser Main")
    if not km:
        km = kc.new("File Browser Main")
    kmi = km.keymap_items.new("secret.paint_from_library_switch", "Q", "PRESS", shift=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("File Browser Main")
    if not km:
        km = kc.new("File Browser Main")
    kmi = km.keymap_items.new("secret.paint_from_library_justimport", "Q", "PRESS", alt=True)
    addon_keymaps.append((km, kmi))








    km = kc.get("Object Mode")
    if not km:
        km = kc.new("Object Mode")
    kmi = km.keymap_items.new("secret.paintbrushswitch", "Q", "PRESS", shift=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("Sculpt Curves")
    if not km:
        km = kc.new("Sculpt Curves")
    kmi = km.keymap_items.new("secret.paintbrushswitch", "Q", "PRESS", shift=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("Sculpt Curves")
    if not km:
        km = kc.new("Sculpt Curves")
    kmi = km.keymap_items.new("secret.brush_density_while_painting", "D", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("Weight Paint")
    if not km:
        km = kc.new("Weight Paint")
    kmi = km.keymap_items.new("secret.paintbrushswitch", "Q", "PRESS", shift=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("Curve")
    if not km:
        km = kc.new("Curve")
    kmi = km.keymap_items.new("secret.paintbrushswitch", "Q", "PRESS", shift=True)
    addon_keymaps.append((km, kmi))






    km = kc.get("Object Mode")
    if not km:
        km = kc.new("Object Mode")
    kmi = km.keymap_items.new("secret.assembly", "D", "PRESS", ctrl=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("Object Mode")
    if not km:
        km = kc.new("Object Mode")
    kmi = km.keymap_items.new("secret.group", "M", "PRESS", alt=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("Outliner")
    if not km:
        km = kc.new("Outliner", space_type="OUTLINER")
    kmi = km.keymap_items.new("secret.group", "M", "PRESS", alt=True)
    addon_keymaps.append((km, kmi))





    km = kc.get("Curve")
    if not km:
        km = kc.new("Curve")
    kmi = km.keymap_items.new("secret.curveseparate", "Q", "PRESS", ctrl=True)
    addon_keymaps.append((km, kmi))

    km = kc.get("Sculpt Curves")
    if not km:
        km = kc.new("Sculpt Curves")
    kmi = km.keymap_items.new("secret.curveseparate", "Q", "PRESS", ctrl=True)
    addon_keymaps.append((km, kmi))




    km = kc.get("Image Paint")
    if not km:
        km = kc.new("Image Paint")
    kmi = km.keymap_items.new("secret.switchtoerasealpha", "X", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("Weight Paint")
    if not km:
        km = kc.new("Weight Paint")
    kmi = km.keymap_items.new("secret.switchtoweightzero", "X", "PRESS")
    addon_keymaps.append((km, kmi))





def unregister():
    if auto_updater_status: addon_updater_ops.unregister()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mypropertieslist

    bpy.types.FILEBROWSER_HT_header.remove(checkboxImportWithoutPainting_f)

    

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()