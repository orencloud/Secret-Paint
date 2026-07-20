bl_info = {
    "name": "Secret Paint",
    "author": "orencloud",
    "version": (2, 0, 5),
    "blender": (4, 2, 0),
    "location": "Object + Target + Q",
    "description": "Paint the selected object on top of the active one",
    "warning": "",
    "doc_url": "https://orencloud.art/secretpaint",
    "category": "Paint",
}

import importlib
import re
from pathlib import Path

import bpy

addon_utils = importlib.import_module("addon_utils")
blender_version = bpy.app.version_string


def _secret_paint_bl_info():
    metadata = globals().get("bl_info")
    if isinstance(metadata, dict):
        return metadata

    version = (0, 0, 0)
    try:
        manifest_text = (Path(__file__).resolve().parent / "blender_manifest.toml").read_text(encoding="utf-8")
        version_match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', manifest_text)
        if version_match:
            version = tuple(int(part) for part in version_match.group(1).split("."))
    except (OSError, ValueError):
        pass

    return {
        "name": "Secret Paint",
        "author": "orencloud",
        "version": version,
        "blender": (4, 2, 0),
        "location": "Object + Target + Q",
        "description": "Paint the selected object on top of the active one",
        "warning": "",
        "doc_url": "https://orencloud.art/secretpaint",
        "category": "Paint",
    }


addon_path = Path(__file__).resolve().parent
addon_is_an_extension = "extensions" in addon_path.parts
secret_paint_install_count = 0
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":
        secret_paint_install_count += 1

both_addon_and_extensions_are_installed = secret_paint_install_count > 1
auto_updater_disabled_reason = ""

auto_updater_status = True
addon_updater_ops = None
if auto_updater_status:
    try:
        _addon_updater_ops = importlib.import_module(".addon_updater_ops", __package__)
    except Exception as ex:
        auto_updater_status = False
        auto_updater_disabled_reason = "The bundled updater failed to initialize: {}".format(ex)
    else:
        addon_updater_ops = _addon_updater_ops

from .secret_paint_shared import (
    SECRET_PAINT_WORLD_ALIGN_TO_NORMAL_ENABLED,
    SECRET_PAINT_WORLD_RANDOM_Z_ENABLED,
    SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED,
    SECRET_PAINT_WORLD_TARGET_SURFACE_ENABLED,
    SHARED_SECRET_PAINT_CLASSES,
    checkboxImportWithoutPainting_f,
    draw_shared_secret_paint_preferences,
    export_unreal,
    register_secret_paint_cli_commands,
    register_secret_paint_object_mode_pie,
    register_secret_paint_panel_drag_property,
    register_secret_paint_world_paint_runtime,
    secretpaint_update_modifier,
    shared_secret_paint_preference_annotations,
    unregister_secret_paint_cli_commands,
    unregister_secret_paint_disabled_world_paint_operator_stubs,
    unregister_secret_paint_object_mode_pie,
    unregister_secret_paint_panel_drag_property,
    unregister_secret_paint_world_paint_runtime,
    update_collapsed_list,
)


class MyPropertiesClass(bpy.types.PropertyGroup):

    dropdownpanel: bpy.props.BoolProperty(default=False, update=update_collapsed_list)
    shared_material_index : bpy.props.IntProperty(name= "Shared Material Index", description="Choose which Shared node group get assigned to the selected objects", soft_min= 1, soft_max= 32, default= 1)
    checkboxImportWithoutPainting: bpy.props.BoolProperty(name="Import And Paint",description="When transfering a Biome to another mesh, also transfer the material of the target mesh",default=True)
    checkboxTransferMaterialWithBiome: bpy.props.BoolProperty(name="Terrain material with Biome",description="When transfering a Biome to another mesh, also transfer the material of the target mesh",default=False)


addon_keymaps = []

class SecretPaintPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    __annotations__ = shared_secret_paint_preference_annotations(
        hidden_assets_collection_name="Hidden Assets"
    )

    auto_check_update : bpy.props.BoolProperty(name="Auto-check for Update", description="If enabled, auto-check for updates using an interval", default=True)
    updater_interval_months : bpy.props.IntProperty(name='Months', description="Number of months between checking for updates", default=0, min=0)
    updater_interval_days : bpy.props.IntProperty(name='Days',description="Number of days between checking for updates",default=1,min=0,max=31)
    updater_interval_hours : bpy.props.IntProperty(name='Hours',description="Number of hours between checking for updates",default=0,min=0,max=23)
    updater_interval_minutes : bpy.props.IntProperty(name='Minutes',description="Number of minutes between checking for updates",default=0,min=0,max=59)
    all_libraries = [(lib.path,lib.name,"") for lib in bpy.context.preferences.filepaths.asset_libraries]

    if len(all_libraries) == 0: all_libraries = [("(No Library Found, create one first)","(No Library Found, create one first)","")]
    biome_library: bpy.props.EnumProperty(name="Library", description="Export the asset into this library",items=all_libraries )

    def draw(self, context):
        layout = self.layout

        if addon_updater_ops is not None:
            addon_updater_ops.update_settings_ui(self, context)
        elif auto_updater_disabled_reason:
            box = layout.box()
            box.label(text="Updater Settings")
            box.label(text=auto_updater_disabled_reason, icon='INFO')

        draw_shared_secret_paint_preferences(layout, self)


classes = [
    SecretPaintPreferences,
    MyPropertiesClass,
    *SHARED_SECRET_PAINT_CLASSES,
    ]


_TEMP_DISABLED_SECRET_PAINT_CLASSES = (
    secretpaint_update_modifier,
    export_unreal,
)


def _unregister_temp_disabled_secret_paint_classes():
    for cls in _TEMP_DISABLED_SECRET_PAINT_CLASSES:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


def register_keymaps():
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is None:
        return

    def add_keymap(
        name,
        operator_id,
        event_type,
        event_value,
        *,
        space_type='EMPTY',
        region_type='WINDOW',
        properties=None,
        **event_options,
    ):
        keymap = keyconfig.keymaps.new(
            name=name,
            space_type=space_type,
            region_type=region_type,
        )
        keymap_item = keymap.keymap_items.new(
            operator_id,
            event_type,
            event_value,
            **event_options,
        )
        for property_name, property_value in (properties or {}).items():
            setattr(keymap_item.properties, property_name, property_value)
        addon_keymaps.append((keymap, keymap_item))

    add_keymap("User Interface", "secret.panel_keyboard_reorder", "G", "PRESS")
    add_keymap("User Interface", "secret.panel_keyboard_delete", "X", "PRESS")
    add_keymap("User Interface", "secret.panel_modified_click", "LEFTMOUSE", "PRESS", shift=True)
    add_keymap("User Interface", "secret.panel_modified_click", "LEFTMOUSE", "PRESS", alt=True)
    add_keymap(
        "User Interface",
        "secret.panel_modified_click",
        "LEFTMOUSE",
        "PRESS",
        shift=True,
        alt=True,
    )

    add_keymap("Object Mode", "secret.toggle_viewport_tab_bookmark", "W", "PRESS", shift=True)
    paint_keymap_properties = {
        "exit_paint_mode": False,
        "use_selected_source": False,
        "use_cursor_source": True,
    }
    for keymap_name in ("Object Mode", "Sculpt Curves", "Weight Paint", "Curve"):
        add_keymap(
            keymap_name,
            "secret.paint",
            "Q",
            "PRESS",
            properties=paint_keymap_properties,
        )
        add_keymap(keymap_name, "secret.paintbrushswitch", "Q", "PRESS", shift=True)
        add_keymap(
            keymap_name,
            "secret.world_paint_end_pick_source",
            "Q",
            "RELEASE",
            any=True,
        )

    world_keymaps = (
        ("secret.world_paint_tool_density", "D", {}),
        ("secret.world_paint_tool_delete", "X", {}),
        ("secret.world_paint_tool_single", "K", {}),
        ("secret.world_paint_tool_slide", "G", {}),
        ("secret.world_paint_tool_select", "H", {}),
        ("secret.world_paint_tool_rotation", "R", {}),
        ("secret.world_paint_tool_scale", "S", {}),
        ("secret.world_paint_tool_bezier", "B", {}),
        ("secret.world_paint_toggle_lock_surface", "ONE", {}),
        ("secret.world_paint_toggle_wire_bounds_surfaces", "TWO", {}),
        ("secret.world_paint_toggle_interpolate", "THREE", {}),
    )
    for world_operator_id, world_event_type, world_event_options in world_keymaps:
        add_keymap(
            "3D View",
            world_operator_id,
            world_event_type,
            "PRESS",
            space_type='VIEW_3D',
            **world_event_options,
        )

    for toggle_operator_id, toggle_event_type in (
        ("secret.world_paint_toggle_lock_surface", "ONE"),
        ("secret.world_paint_toggle_wire_bounds_surfaces", "TWO"),
        ("secret.world_paint_toggle_interpolate", "THREE"),
    ):
        add_keymap("Sculpt Curves", toggle_operator_id, toggle_event_type, "PRESS")

    if SECRET_PAINT_WORLD_TARGET_SURFACE_ENABLED:
        add_keymap(
            "3D View",
            "secret.world_paint_toggle_target_surface",
            "I",
            "PRESS",
            space_type='VIEW_3D',
        )
    if SECRET_PAINT_WORLD_RANDOM_Z_ENABLED:
        add_keymap(
            "3D View",
            "secret.world_paint_toggle_random_z",
            "T",
            "PRESS",
            space_type='VIEW_3D',
        )
    if SECRET_PAINT_WORLD_ALIGN_TO_NORMAL_ENABLED:
        add_keymap(
            "3D View",
            "secret.world_paint_toggle_align_to_normal",
            "N",
            "PRESS",
            space_type='VIEW_3D',
        )

    adjust_properties = {"confirm_on_release": True}
    if SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED:
        add_keymap(
            "3D View",
            "secret.world_paint_adjust_size",
            "F",
            "PRESS",
            space_type='VIEW_3D',
            properties=adjust_properties,
        )
        add_keymap(
            "Sculpt Curves",
            "secret.world_paint_adjust_size",
            "F",
            "PRESS",
            properties=adjust_properties,
        )
        for keymap_name, keymap_space_type in (("3D View", 'VIEW_3D'), ("Sculpt Curves", 'EMPTY')):
            add_keymap(
                keymap_name,
                "secret.world_paint_end_adjust",
                "F",
                "RELEASE",
                space_type=keymap_space_type,
                properties={"adjust_mode": "SIZE"},
            )
    else:
        for keymap_name, keymap_space_type in (("3D View", 'VIEW_3D'), ("Sculpt Curves", 'EMPTY')):
            for key_event_value in ("PRESS", "RELEASE"):
                add_keymap(
                    keymap_name,
                    "secret.world_paint_ignore_size_adjust",
                    "F",
                    key_event_value,
                    space_type=keymap_space_type,
                )
    add_keymap(
        "3D View",
        "secret.world_paint_adjust_strength",
        "F",
        "PRESS",
        space_type='VIEW_3D',
        properties=adjust_properties,
        alt=True,
    )
    add_keymap(
        "Sculpt Curves",
        "secret.world_paint_adjust_strength",
        "F",
        "PRESS",
        properties=adjust_properties,
        alt=True,
    )
    for keymap_name, keymap_space_type in (("3D View", 'VIEW_3D'), ("Sculpt Curves", 'EMPTY')):
        add_keymap(
            keymap_name,
            "secret.world_paint_end_adjust",
            "F",
            "RELEASE",
            space_type=keymap_space_type,
            properties={"adjust_mode": "STRENGTH"},
            alt=True,
        )
        for modifier_event_type in ("LEFT_ALT", "RIGHT_ALT"):
            add_keymap(
                keymap_name,
                "secret.world_paint_end_adjust",
                modifier_event_type,
                "RELEASE",
                space_type=keymap_space_type,
                properties={"adjust_mode": "STRENGTH"},
            )
        add_keymap(
            keymap_name,
            "secret.world_paint_undo_source_pick",
            "Z",
            "PRESS",
            space_type=keymap_space_type,
            ctrl=True,
        )
    add_keymap(
        "File Browser Main",
        "secret.paint_from_library",
        "Q",
        "PRESS",
        space_type='FILE_BROWSER',
    )
    add_keymap(
        "File Browser Main",
        "secret.paint_from_library_justimport",
        "Q",
        "PRESS",
        space_type='FILE_BROWSER',
        alt=True,
    )
    add_keymap(
        "File Browser Main",
        "secret.paint_from_library_switch",
        "Q",
        "PRESS",
        space_type='FILE_BROWSER',
        shift=True,
    )

    add_keymap("Object Mode", "secret.assembly", "D", "PRESS", ctrl=True)
    add_keymap("Object Mode", "secret.group", "M", "PRESS", alt=True)
    add_keymap("Outliner", "secret.group", "M", "PRESS", space_type='OUTLINER', alt=True)


def unregister_keymaps():
    for keymap, keymap_item in addon_keymaps:
        keymap.keymap_items.remove(keymap_item)
    addon_keymaps.clear()


def register():
    addon_metadata = _secret_paint_bl_info()
    if addon_updater_ops is not None:
        addon_updater_ops.register(addon_metadata)
    register_secret_paint_cli_commands()

    unregister_secret_paint_disabled_world_paint_operator_stubs()
    _unregister_temp_disabled_secret_paint_classes()
    for cls in classes:
        bpy.utils.register_class(cls)
    register_secret_paint_panel_drag_property()

    bpy.types.Scene.mypropertieslist = bpy.props.PointerProperty(type=MyPropertiesClass)

    bpy.types.FILEBROWSER_HT_header.append(checkboxImportWithoutPainting_f)
    register_secret_paint_world_paint_runtime()
    register_secret_paint_object_mode_pie()
    register_keymaps()


def unregister():
    unregister_secret_paint_cli_commands()
    if addon_updater_ops is not None:
        addon_updater_ops.unregister()
    unregister_keymaps()
    unregister_secret_paint_world_paint_runtime()
    unregister_secret_paint_object_mode_pie()

    unregister_secret_paint_panel_drag_property()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    _unregister_temp_disabled_secret_paint_classes()

    if hasattr(bpy.types.Scene, "mypropertieslist"):
        del bpy.types.Scene.mypropertieslist

    try:
        bpy.types.FILEBROWSER_HT_header.remove(checkboxImportWithoutPainting_f)
    except ValueError:
        pass


if __name__ == "__main__":
    register()
