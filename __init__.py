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
    "version": (1, 9, 13),
    "blender": (4, 2, 0),
    "location": "Object + Target + Q",
    "description": "Paint the selected object on top of the active one",
    "warning": "",
    "doc_url": "https://orencloud.art/secretpaint",
    "category": "Paint",
}

import hashlib
import importlib
import json
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
if auto_updater_status == True:
    try:
        _addon_updater_ops = importlib.import_module(".addon_updater_ops", __package__)
    except Exception as ex:
        auto_updater_status = False
        auto_updater_disabled_reason = "The bundled updater failed to initialize: {}".format(ex)
    else:
        addon_updater_ops = _addon_updater_ops

from .secret_paint_shared import *

class MyPropertiesClass(bpy.types.PropertyGroup):

    dropdownpanel: bpy.props.BoolProperty(default=False, update=update_collapsed_list)
    shared_material_index : bpy.props.IntProperty(name= "Shared Material Index", description="Choose which Shared node group get assigned to the selected objects", soft_min= 1, soft_max= 32, default= 1)
    checkboxImportWithoutPainting: bpy.props.BoolProperty(name="Import And Paint",description="When transfering a Biome to another mesh, also transfer the material of the target mesh",default=True)
    checkboxTransferMaterialWithBiome: bpy.props.BoolProperty(name="Terrain material with Biome",description="When transfering a Biome to another mesh, also transfer the material of the target mesh",default=False)




addon_keymaps = []
addon_keymap_defaults = []
_secret_paint_keymap_maintenance_enabled = False
_secret_paint_deferred_keymap_sync_attempts = 0
_secret_paint_keymap_preferences_sync_until = 0.0
_secret_paint_user_keymap_cleanup_attempts = 0
_external_shortcut_adoption_events = {}
_SECRET_PAINT_KEYMAP_MAINTENANCE_INTERVAL = 1.0
_SECRET_PAINT_DEFERRED_KEYMAP_SYNC_MAX_ATTEMPTS = 12
_SECRET_PAINT_KEYMAP_PREFERENCES_SYNC_INTERVAL = 0.25
_SECRET_PAINT_KEYMAP_PREFERENCES_SYNC_GRACE_SECONDS = 4.0
_SECRET_PAINT_USER_KEYMAP_CLEANUP_MAX_ATTEMPTS = 20
_SECRET_PAINT_USER_KEYMAP_CLEANUP_RETRY_INTERVAL = 0.1
_SECRET_PAINT_WORLD_DENSITY_RADIAL_PROPS = (
    ("data_path_primary", "tool_settings.curves_sculpt.brush.curves_sculpt_settings.minimum_distance"),
    ("data_path_secondary", ""),
    ("use_secondary", ""),
    ("rotation_path", "tool_settings.curves_sculpt.brush.texture_slot.angle"),
    ("color_path", "tool_settings.curves_sculpt.brush.cursor_color_add"),
    ("fill_color_path", ""),
    ("fill_color_override_path", ""),
    ("fill_color_override_test_path", ""),
    ("zoom_path", ""),
    ("image_id", "tool_settings.curves_sculpt.brush"),
    ("secondary_tex", False),
    ("release_confirm", False),
)


def _configure_secret_paint_world_density_radial_keymap(kmi):
    properties = getattr(kmi, "properties", None)
    if properties is None:
        return
    for property_name, property_value in _SECRET_PAINT_WORLD_DENSITY_RADIAL_PROPS:
        try:
            setattr(properties, property_name, property_value)
        except Exception:
            pass


def _disable_stale_secret_paint_world_density_adjust_keymaps(context):
    keyconfigs = getattr(getattr(context, "window_manager", None), "keyconfigs", None)
    if keyconfigs is None:
        return 0
    disabled = 0
    for keyconfig_name in ("addon",):
        keyconfig = getattr(keyconfigs, keyconfig_name, None)
        if keyconfig is None:
            continue
        for keymap_name in ("3D View", "Sculpt Curves"):
            keymap = keyconfig.keymaps.get(keymap_name)
            if keymap is None:
                continue
            for keymap_item in keymap.keymap_items:
                if not getattr(keymap_item, "active", False):
                    continue
                if getattr(keymap_item, "type", "") != "F":
                    continue
                if getattr(keymap_item, "value", "") != "PRESS":
                    continue
                if not bool(getattr(keymap_item, "alt", False)):
                    continue
                if bool(getattr(keymap_item, "shift", False)) or bool(getattr(keymap_item, "ctrl", False)):
                    continue
                idname = getattr(keymap_item, "idname", "")
                is_stale_strength = False
                if idname == "secret.world_paint_begin_adjust":
                    properties = getattr(keymap_item, "properties", None)
                    try:
                        is_stale_strength = properties is not None and getattr(properties, "adjust_mode", "") == "STRENGTH"
                    except Exception:
                        is_stale_strength = False
                if is_stale_strength:
                    keymap_item.active = False
                    disabled += 1
    return disabled

SECRET_PAINT_KEYMAP_EVENT_ATTRS = (
    "map_type",
    "type",
    "value",
    "any",
    "shift",
    "ctrl",
    "alt",
    "oskey",
    "hyper",
    "key_modifier",
    "direction",
    "repeat",
    "active",
)
SECRET_PAINT_KEYMAP_CONTROL_PROPERTY_NAMES = (
    "confirm_on_release",
    "release_confirm",
)
SECRET_PAINT_KEYMAP_CONTROL_OVERRIDE_PREFIX = "sp_kc_"
SECRET_PAINT_KEYMAP_EVENT_OVERRIDE_PREFIX = "sp_ke_"
SECRET_PAINT_MAIN_SHORTCUT_FAMILIES = {
    "PAINT": {
        "label": "Paint / Pick Source",
        "description": "Controls Q in the 3D View, Secret Paint mode, and Asset Browser paint import",
        "entries": (
            ("Object Mode", "secret.paint"),
            ("Sculpt Curves", "secret.paint"),
            ("Weight Paint", "secret.paint"),
            ("Curve", "secret.paint"),
            ("3D View", "secret.world_paint_pick_source"),
            ("Sculpt Curves", "secret.world_paint_pick_source"),
            ("File Browser Main", "secret.paint_from_library"),
        ),
    },
    "SWITCH": {
        "label": "Switch Source",
        "description": "Controls Shift+Q in the 3D View, Secret Paint mode, and Asset Browser source switching",
        "entries": (
            ("Object Mode", "secret.paintbrushswitch"),
            ("Sculpt Curves", "secret.paintbrushswitch"),
            ("Weight Paint", "secret.paintbrushswitch"),
            ("Curve", "secret.paintbrushswitch"),
            ("File Browser Main", "secret.paint_from_library_switch"),
        ),
    },
    "COLLECTION": {
        "label": "Collection",
        "description": "Controls the Collection shortcut in Object Mode and the Outliner",
        "entries": (
            ("Object Mode", "secret.group"),
            ("Outliner", "secret.group"),
        ),
    },
}
SECRET_PAINT_MAIN_SHORTCUT_DISPLAY_FAMILY_IDS = ("PAINT", "SWITCH")
SECRET_PAINT_DERIVED_SHORTCUT_LINKS = {
    "PAINT": (
        {
            "entries": (("File Browser Main", "secret.paint_from_library_justimport"),),
            "modifier_overrides": {"alt": True},
            "mode": "always",
        },
        {
            "family_id": "SWITCH",
            "modifier_overrides": {"shift": True},
            "mode": "when_target_matched_previous",
        },
    ),
}
SECRET_PAINTING_MODE_SHORTCUT_OPERATOR_IDS = {
    "secret.world_paint_set_tool",
    "secret.world_paint_tool_density",
    "secret.world_paint_tool_delete",
    "secret.world_paint_tool_single",
    "secret.world_paint_tool_bezier",
    "secret.world_paint_tool_slide",
    "secret.world_paint_tool_select",
    "secret.world_paint_tool_rotation",
    "secret.world_paint_tool_scale",
    "secret.world_paint_toggle_flag",
    "secret.world_paint_toggle_lock_surface",
    "secret.world_paint_toggle_target_surface",
    "secret.world_paint_toggle_wire_bounds_surfaces",
    "secret.world_paint_toggle_interpolate",
    "secret.world_paint_toggle_random_z",
    "secret.world_paint_toggle_align_to_normal",
    "secret.world_paint_begin_adjust",
    "secret.world_paint_adjust_strength",
    "secret.world_paint_pick_source",
    "secret.paintbrushswitch",
}
if SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED:
    SECRET_PAINTING_MODE_SHORTCUT_OPERATOR_IDS.add("secret.world_paint_adjust_size")
_SECRET_PAINT_DISABLED_SHORTCUTS_RESTORED_KEY = "secret_paint_disabled_shortcuts_restored_2000"
_SECRET_PAINT_DISABLED_SHORTCUT_RESTORE_THRESHOLD = 6
_SECRET_PAINT_MAIN_SHORTCUTS_Q_MIGRATED_KEY = "secret_paint_main_shortcuts_q_shift_q_migrated_202606"


def _keymap_identity(km):
    return (km.name, km.space_type, km.region_type, bool(km.is_modal))


def _find_matching_keymap(kconf, km_ref, create=False):
    for km in kconf.keymaps:
        if _keymap_identity(km) == _keymap_identity(km_ref):
            return km

    if not create:
        return None

    return kconf.keymaps.new(
        name=km_ref.name,
        space_type=km_ref.space_type,
        region_type=km_ref.region_type,
        modal=km_ref.is_modal,
    )


def _property_signature_value(value):
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    if hasattr(value, "bl_rna") and hasattr(value, "is_property_set"):
        return _operator_properties_signature(value)
    if hasattr(value, "to_list"):
        try:
            return tuple(_property_signature_value(item) for item in value.to_list())
        except Exception:
            pass
    if hasattr(value, "to_tuple"):
        try:
            return tuple(_property_signature_value(item) for item in value.to_tuple())
        except Exception:
            pass
    if hasattr(value, "items"):
        try:
            return tuple(
                sorted((str(key), _property_signature_value(item)) for key, item in value.items())
            )
        except Exception:
            pass
    try:
        return tuple(_property_signature_value(item) for item in value)
    except TypeError:
        pass
    except Exception:
        pass

    for attr_name in ("name_full", "name", "identifier"):
        if hasattr(value, attr_name):
            try:
                return (type(value).__name__, getattr(value, attr_name))
            except Exception:
                pass

    if hasattr(value, "as_pointer"):
        try:
            return (type(value).__name__, int(value.as_pointer()))
        except Exception:
            pass

    try:
        hash(value)
        return value
    except TypeError:
        return repr(value)


def _operator_properties_signature(properties):
    if properties is None:
        return ()

    try:
        rna_properties = properties.bl_rna.properties
    except Exception:
        return ()

    signature = []
    for prop in rna_properties:
        try:
            identifier = prop.identifier
        except Exception:
            continue
        if identifier in {"rna_type", "confirm_on_release", "release_confirm"}:
            continue
        try:
            if not properties.is_property_set(identifier):
                continue
        except Exception:
            continue
        try:
            value = getattr(properties, identifier)
        except Exception:
            continue
        signature.append((identifier, _property_signature_value(value)))
    return tuple(signature)


def _kmi_operator_identity(km, kmi):
    return (
        _keymap_identity(km),
        kmi.propvalue if km.is_modal else kmi.idname,
        () if km.is_modal else _operator_properties_signature(getattr(kmi, "properties", None)),
    )


def _kmi_operator_only_identity(km, kmi):
    return (
        kmi.propvalue if km.is_modal else kmi.idname,
        () if km.is_modal else _operator_properties_signature(getattr(kmi, "properties", None)),
    )


def _kmi_event_identity(kmi):
    return (
        kmi.map_type,
        kmi.type,
        kmi.value,
        kmi.any,
        kmi.shift,
        kmi.ctrl,
        kmi.alt,
        kmi.oskey,
        kmi.hyper,
        kmi.key_modifier,
        kmi.direction,
        kmi.repeat,
    )


def _keymap_item_event_snapshot(kmi):
    return {
        attr: getattr(kmi, attr)
        for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS
        if hasattr(kmi, attr)
    }


def _apply_keymap_item_event_snapshot(kmi, event_snapshot):
    for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS:
        if attr not in event_snapshot or not hasattr(kmi, attr):
            continue
        try:
            setattr(kmi, attr, event_snapshot[attr])
        except Exception:
            pass


def _operator_property_identifiers(properties):
    if properties is None:
        return set()

    try:
        rna_properties = properties.bl_rna.properties
    except Exception:
        return set()

    identifiers = set()
    for prop in rna_properties:
        try:
            identifiers.add(prop.identifier)
        except Exception:
            continue
    return identifiers


def _keymap_item_control_properties_snapshot(kmi):
    try:
        properties = getattr(kmi, "properties", None)
    except Exception:
        return {}
    if properties is None:
        return {}

    property_identifiers = _operator_property_identifiers(properties)
    snapshot = {}
    for property_name in SECRET_PAINT_KEYMAP_CONTROL_PROPERTY_NAMES:
        if property_name not in property_identifiers:
            continue
        try:
            snapshot[property_name] = bool(getattr(properties, property_name))
        except Exception:
            pass
    return snapshot


def _set_keymap_item_control_property(kmi, property_name, value):
    try:
        properties = getattr(kmi, "properties", None)
    except Exception:
        return False
    if properties is None:
        return False

    if property_name not in _operator_property_identifiers(properties):
        return False

    try:
        current_value = bool(getattr(properties, property_name))
    except Exception:
        return False
    if current_value == bool(value):
        return False

    try:
        setattr(properties, property_name, bool(value))
    except Exception:
        return False
    return True


def _apply_keymap_item_control_properties_snapshot(kmi, control_properties):
    changed = False
    for property_name, value in (control_properties or {}).items():
        if _set_keymap_item_control_property(kmi, property_name, value):
            changed = True
    return changed


def _sync_keymap_item_control_properties(source_kmi, target_kmi):
    return _apply_keymap_item_control_properties_snapshot(
        target_kmi,
        _keymap_item_control_properties_snapshot(source_kmi),
    )


def _clear_secret_paint_world_keymap_caches():
    try:
        from . import secret_paint_world_paint
        secret_paint_world_paint._clear_world_keymap_lookup_caches()
        return True
    except Exception:
        return False


def _keymap_item_shortcut_snapshot(kmi, *, include_control_properties=True):
    snapshot = {"event": _keymap_item_event_snapshot(kmi)}
    if include_control_properties:
        snapshot["control_properties"] = _keymap_item_control_properties_snapshot(kmi)
    return snapshot


def _keymap_item_differs_from_default(kmi, default_snapshot):
    if default_snapshot is None:
        return False

    default_event = default_snapshot.get("event")
    if default_event:
        current_event = _keymap_item_event_snapshot(kmi)
        if any(current_event.get(attr) != default_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            return True

    default_control_properties = default_snapshot.get("control_properties", {})
    if default_control_properties:
        current_control_properties = _keymap_item_control_properties_snapshot(kmi)
        for property_name, default_value in default_control_properties.items():
            if current_control_properties.get(property_name) != default_value:
                return True

    return False


def _apply_operator_properties_signature(properties, signature):
    if properties is None or not hasattr(properties, "bl_rna"):
        return

    for identifier, value in signature:
        try:
            setattr(properties, identifier, value)
        except Exception:
            pass


def _capture_addon_keymap_defaults():
    addon_keymap_defaults.clear()
    for km_add, kmi_add in addon_keymaps:
        addon_keymap_defaults.append({
            "keymap": _keymap_identity(km_add),
            "operator": kmi_add.propvalue if km_add.is_modal else kmi_add.idname,
            "properties": () if km_add.is_modal else _operator_properties_signature(getattr(kmi_add, "properties", None)),
            "event": _keymap_item_event_snapshot(kmi_add),
            "control_properties": _keymap_item_control_properties_snapshot(kmi_add),
        })


def _default_snapshot_identity(default_snapshot):
    return (
        tuple(default_snapshot.get("keymap", ())),
        default_snapshot.get("operator", ""),
        tuple(default_snapshot.get("properties", ())),
    )


def _addon_keymap_item_default_identity(km, kmi):
    try:
        operator_id = kmi.propvalue if km.is_modal else kmi.idname
    except Exception:
        return None
    properties_signature = () if km.is_modal else _operator_properties_signature(getattr(kmi, "properties", None))
    return (
        _keymap_identity(km),
        operator_id,
        tuple(properties_signature),
    )


def _find_default_snapshot_for_addon_item(addon_keymap_index, km, kmi):
    item_identity = _addon_keymap_item_default_identity(km, kmi)
    indexed_snapshot = None
    if addon_keymap_index is not None and 0 <= addon_keymap_index < len(addon_keymap_defaults):
        indexed_snapshot = addon_keymap_defaults[addon_keymap_index]
        if item_identity is not None and _default_snapshot_identity(indexed_snapshot) == item_identity:
            return indexed_snapshot

    if item_identity is None:
        return indexed_snapshot

    matching_snapshots = [
        default_snapshot
        for default_snapshot in addon_keymap_defaults
        if _default_snapshot_identity(default_snapshot) == item_identity
    ]
    if not matching_snapshots:
        return None
    if len(matching_snapshots) == 1:
        return matching_snapshots[0]

    current_event = _keymap_item_event_snapshot(kmi)
    for default_snapshot in matching_snapshots:
        if default_snapshot.get("event") == current_event:
            return default_snapshot
    return matching_snapshots[0]


def _keymap_item_is_alive(km, kmi):
    try:
        keymap_item_pointer = kmi.as_pointer()
    except Exception:
        return False

    for item in km.keymap_items:
        try:
            if item.as_pointer() == keymap_item_pointer:
                return True
        except Exception:
            pass
    return False


def _keymap_item_matches_default(km, kmi, default_snapshot):
    return _addon_keymap_item_default_identity(km, kmi) == _default_snapshot_identity(default_snapshot)


def _new_keymap_item_from_default_snapshot(km, default_snapshot):
    event = default_snapshot["event"]
    if km.is_modal:
        kmi = km.keymap_items.new_modal(
            default_snapshot["operator"],
            event["type"],
            event["value"],
            any=event.get("any", False),
            shift=event.get("shift", False),
            ctrl=event.get("ctrl", False),
            alt=event.get("alt", False),
            oskey=event.get("oskey", False),
            hyper=event.get("hyper", False),
            key_modifier=event.get("key_modifier", 'NONE'),
            direction=event.get("direction", 'ANY'),
            repeat=event.get("repeat", False),
        )
    else:
        kmi = km.keymap_items.new(
            default_snapshot["operator"],
            event["type"],
            event["value"],
            any=event.get("any", False),
            shift=event.get("shift", False),
            ctrl=event.get("ctrl", False),
            alt=event.get("alt", False),
            oskey=event.get("oskey", False),
            hyper=event.get("hyper", False),
            key_modifier=event.get("key_modifier", 'NONE'),
            direction=event.get("direction", 'ANY'),
            repeat=event.get("repeat", False),
        )
        _apply_operator_properties_signature(kmi.properties, default_snapshot["properties"])
        _apply_keymap_item_control_properties_snapshot(
            kmi,
            default_snapshot.get("control_properties", {}),
        )

    _apply_keymap_item_event_snapshot(kmi, event)
    return kmi


def _new_user_keymap_item_from_addon_item(km_user, km_add, kmi_add):
    event = _keymap_item_event_snapshot(kmi_add)
    if km_user.is_modal:
        kmi_user = km_user.keymap_items.new_modal(
            kmi_add.propvalue if km_add.is_modal else getattr(kmi_add, "propvalue", ""),
            event["type"],
            event["value"],
            any=event.get("any", False),
            shift=event.get("shift", False),
            ctrl=event.get("ctrl", False),
            alt=event.get("alt", False),
            oskey=event.get("oskey", False),
            hyper=event.get("hyper", False),
            key_modifier=event.get("key_modifier", 'NONE'),
            direction=event.get("direction", 'ANY'),
            repeat=event.get("repeat", False),
        )
    else:
        kmi_user = km_user.keymap_items.new(
            kmi_add.idname,
            event["type"],
            event["value"],
            any=event.get("any", False),
            shift=event.get("shift", False),
            ctrl=event.get("ctrl", False),
            alt=event.get("alt", False),
            oskey=event.get("oskey", False),
            hyper=event.get("hyper", False),
            key_modifier=event.get("key_modifier", 'NONE'),
            direction=event.get("direction", 'ANY'),
            repeat=event.get("repeat", False),
        )

    _apply_keymap_item_event_snapshot(kmi_user, event)
    return kmi_user


def _same_keymap_item_reference(kmi_a, kmi_b):
    if kmi_a is kmi_b:
        return True
    try:
        return kmi_a.as_pointer() == kmi_b.as_pointer()
    except Exception:
        return False


def _refresh_blender_keyconfigs(context):
    try:
        context.window_manager.keyconfigs.update()
    except Exception:
        pass


def _remove_user_keymap_items_for_addon_item(context, km_add, kmi_add):
    return _restore_user_keymap_items_for_addon_item(context, km_add, kmi_add)


def _restore_user_keymap_items_for_addon_item(context, km_add, kmi_add):
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    user_kc = getattr(keyconfigs, "user", None)
    if user_kc is None or not _secret_paint_owns_keymap_item(kmi_add):
        return 0

    km_user = _find_matching_keymap(user_kc, km_add, create=False)
    if km_user is None:
        return 0

    restored = 0
    for kmi_user in list(_matching_user_items_without_properties(km_user, km_add, kmi_add)):
        try:
            is_user_defined = bool(getattr(kmi_user, "is_user_defined", False))
            is_user_modified = bool(getattr(kmi_user, "is_user_modified", False))
        except Exception:
            continue
        if is_user_defined or not is_user_modified:
            continue
        try:
            km_user.restore_item_to_default(kmi_user)
            restored += 1
        except Exception:
            try:
                kmi_user.active = True
                restored += 1
            except Exception:
                pass
    return restored


def _restore_user_keymap_items_for_addon_indexes(context, addon_keymap_indexes):
    valid_indexes = [
        addon_keymap_index
        for addon_keymap_index in addon_keymap_indexes
        if 0 <= addon_keymap_index < len(addon_keymaps)
    ]
    if not valid_indexes:
        return 0

    restored = 0
    for addon_keymap_index in valid_indexes:
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        restored += _restore_user_keymap_items_for_addon_item(context, km_add, kmi_add)

    if restored:
        context.preferences.is_dirty = True
        _external_shortcut_adoption_events.clear()
        _refresh_blender_keyconfigs(context)
        _clear_secret_paint_world_keymap_caches()
    return restored


def _ensure_user_keymap_item_for_existing_keymap(context, km_add, kmi_add):
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    user_kc = getattr(keyconfigs, "user", None)
    if user_kc is None or not _secret_paint_owns_keymap_item(kmi_add):
        return 0

    km_user = _find_matching_keymap(user_kc, km_add, create=False)
    if km_user is None:
        return 0

    changed = 0
    matching_items = list(_matching_user_items_without_properties(km_user, km_add, kmi_add))
    if not matching_items:
        return 0

    event_snapshot = _keymap_item_event_snapshot(kmi_add)
    for kmi_user in matching_items:
        current_event = _keymap_item_event_snapshot(kmi_user)
        if any(current_event.get(attr) != event_snapshot.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            _apply_keymap_item_event_snapshot(kmi_user, event_snapshot)
            changed += 1
    return changed


def _remove_stale_secret_paint_user_defined_keymap_items_for_addon_item(context, km_add, kmi_add):
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    user_kc = getattr(keyconfigs, "user", None)
    if user_kc is None or not _secret_paint_owns_keymap_item(kmi_add):
        return 0

    km_user = _find_matching_keymap(user_kc, km_add, create=False)
    if km_user is None:
        return 0

    removed = 0
    for kmi_user in list(_matching_user_items_without_properties(km_user, km_add, kmi_add)):
        try:
            is_user_defined = bool(getattr(kmi_user, "is_user_defined", False))
        except Exception:
            continue
        if not is_user_defined:
            continue
        try:
            km_user.keymap_items.remove(kmi_user)
            removed += 1
        except Exception:
            pass
    return removed


def _sync_user_keymap_override_from_addon_item(context, km_add, kmi_add, default_snapshot=None):
    return _ensure_user_keymap_item_for_existing_keymap(context, km_add, kmi_add)


def _sync_user_keymap_overrides_from_addon_indexes(context, addon_keymap_indexes, *, only_customized=False):
    valid_indexes = [
        addon_keymap_index
        for addon_keymap_index in addon_keymap_indexes
        if 0 <= addon_keymap_index < len(addon_keymaps)
    ]
    if not valid_indexes:
        return 0

    _repair_addon_keymap_defaults(context)

    changed = 0
    for addon_keymap_index in valid_indexes:
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        if not _secret_paint_owns_keymap_item(kmi_add):
            continue
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            continue
        is_customized = _keymap_item_differs_from_default(kmi_add, default_snapshot)
        if only_customized and not is_customized:
            continue
        changed += _sync_user_keymap_override_from_addon_item(
            context,
            km_add,
            kmi_add,
            default_snapshot,
        )

    if changed:
        context.preferences.is_dirty = True
        _external_shortcut_adoption_events.clear()
        _refresh_blender_keyconfigs(context)
        _clear_secret_paint_world_keymap_caches()
    return changed


def _remove_user_keymap_overrides_for_addon_indexes(context, addon_keymap_indexes):
    restored = _restore_user_keymap_items_for_addon_indexes(context, addon_keymap_indexes)
    ensured = 0
    for addon_keymap_index in addon_keymap_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        ensured += _ensure_user_keymap_item_for_existing_keymap(
            context,
            km_add,
            kmi_add,
        )
    if ensured:
        context.preferences.is_dirty = True
        _external_shortcut_adoption_events.clear()
        _refresh_blender_keyconfigs(context)
        _clear_secret_paint_world_keymap_caches()
    return restored + ensured


def _reset_addon_keymap_events_to_defaults():
    reset = 0
    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            continue
        default_event = default_snapshot.get("event")
        if not default_event:
            continue
        current_event = _keymap_item_event_snapshot(kmi_add)
        if any(current_event.get(attr) != default_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            _apply_keymap_item_event_snapshot(kmi_add, default_event)
            reset += 1
        if _apply_keymap_item_control_properties_snapshot(
            kmi_add,
            default_snapshot.get("control_properties", {}),
        ):
            reset += 1
    if reset:
        try:
            from . import secret_paint_world_paint
            secret_paint_world_paint._clear_world_keymap_lookup_caches()
        except Exception:
            pass
    return reset


def _reset_addon_keymap_item_to_default(addon_keymap_index):
    if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
        return False

    km_add, kmi_add = addon_keymaps[addon_keymap_index]
    default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
    if default_snapshot is None:
        return False

    changed = False
    default_event = default_snapshot.get("event")
    if default_event:
        current_event = _keymap_item_event_snapshot(kmi_add)
        if any(current_event.get(attr) != default_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            _apply_keymap_item_event_snapshot(kmi_add, default_event)
            changed = True
    if _apply_keymap_item_control_properties_snapshot(
        kmi_add,
        default_snapshot.get("control_properties", {}),
    ):
        changed = True
    return changed


def _keymap_item_is_customized(addon_keymap_index, km_add, kmi_add):
    default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
    return _keymap_item_differs_from_default(kmi_add, default_snapshot)


def _linked_shortcut_indexes_for_index(addon_keymap_index):
    if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
        return set()

    linked_indexes = {addon_keymap_index}
    for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
        family_indexes = {
            current_index
            for current_index, _km_add, _kmi_add, _family_id
            in _main_shortcut_family_entries(family_id)
        }
        if addon_keymap_index in family_indexes:
            linked_indexes.update(family_indexes)
            break

    group = _shared_painting_mode_group_for_index(addon_keymap_index)
    if group:
        linked_indexes.update(current_index for current_index, _km_add, _kmi_add in group)

    return linked_indexes


def _store_and_dirty_keymap_customization(context, addon_keymap_indexes, *, force_control=False):
    changed = 0
    valid_indexes = [
        addon_keymap_index
        for addon_keymap_index in addon_keymap_indexes
        if 0 <= addon_keymap_index < len(addon_keymaps)
    ]
    for addon_keymap_index in valid_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        changed += _store_keymap_item_event_customization(context, km_add, kmi_add, default_snapshot)
        if not force_control:
            changed += _store_keymap_item_control_customization(context, km_add, kmi_add, default_snapshot)

    changed += _persist_user_keymaps_from_addon_shortcut_customizations(context)
    changed += _sync_user_keymap_overrides_from_addon_indexes(context, valid_indexes)
    if force_control:
        for addon_keymap_index in valid_indexes:
            km_add, kmi_add = addon_keymaps[addon_keymap_index]
            default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
            changed += _store_keymap_item_control_customization(
                context,
                km_add,
                kmi_add,
                default_snapshot,
                force=True,
            )
    if changed:
        context.preferences.is_dirty = True
    _clear_secret_paint_world_keymap_caches()
    return changed


def _apply_keymap_event_customization_to_indexes(context, addon_keymap_indexes, event_snapshot):
    _repair_addon_keymap_defaults(context)
    changed = 0
    valid_indexes = {
        addon_keymap_index
        for addon_keymap_index in addon_keymap_indexes
        if 0 <= addon_keymap_index < len(addon_keymaps)
    }

    source_family_ids = _source_family_ids_for_indexes(valid_indexes)
    previous_source_events = {}
    for source_family_id in source_family_ids:
        _source_index, _source_km, source_kmi = _main_shortcut_master_entry(source_family_id)
        if source_kmi is not None:
            previous_source_events[source_family_id] = _keymap_item_event_snapshot(source_kmi)

    for addon_keymap_index in valid_indexes:
        _km_add, kmi_add = addon_keymaps[addon_keymap_index]
        current_event = _keymap_item_event_snapshot(kmi_add)
        if any(current_event.get(attr) != event_snapshot.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            _apply_keymap_item_event_snapshot(kmi_add, event_snapshot)
            changed += 1

    derived_changed, derived_indexes = _apply_derived_shortcut_links_for_source_families(
        context,
        source_family_ids,
        previous_source_events=previous_source_events,
    )
    changed += derived_changed
    changed += _store_and_dirty_keymap_customization(context, valid_indexes.union(derived_indexes))
    return changed


def _apply_keymap_control_customization_to_indexes(context, addon_keymap_indexes, property_name, value):
    _repair_addon_keymap_defaults(context)
    changed = 0
    valid_indexes = {
        addon_keymap_index
        for addon_keymap_index in addon_keymap_indexes
        if 0 <= addon_keymap_index < len(addon_keymaps)
    }
    for addon_keymap_index in valid_indexes:
        _km_add, kmi_add = addon_keymaps[addon_keymap_index]
        if _set_keymap_item_control_property(kmi_add, property_name, value):
            changed += 1

    changed += _store_and_dirty_keymap_customization(
        context,
        valid_indexes,
        force_control=True,
    )
    return changed


def _reset_shortcut_indexes_to_defaults(context, addon_keymap_indexes):
    _repair_addon_keymap_defaults(context)
    valid_indexes = {
        addon_keymap_index
        for addon_keymap_index in addon_keymap_indexes
        if 0 <= addon_keymap_index < len(addon_keymaps)
    }
    if not valid_indexes:
        return 0

    source_family_ids = _source_family_ids_for_indexes(valid_indexes)
    previous_source_events = {}
    for source_family_id in source_family_ids:
        _source_index, _source_km, source_kmi = _main_shortcut_master_entry(source_family_id)
        if source_kmi is not None:
            previous_source_events[source_family_id] = _keymap_item_event_snapshot(source_kmi)

    changed = 0
    for addon_keymap_index in valid_indexes:
        if _reset_addon_keymap_item_to_default(addon_keymap_index):
            changed += 1
    derived_changed, derived_indexes = _apply_derived_shortcut_links_for_source_families(
        context,
        source_family_ids,
        previous_source_events=previous_source_events,
    )
    changed += derived_changed
    reset_indexes = valid_indexes.union(derived_indexes)
    changed += _clear_stored_keymap_event_customizations(context, reset_indexes)
    changed += _clear_stored_keymap_control_customizations(context, reset_indexes)
    changed += _remove_user_keymap_overrides_for_addon_indexes(context, reset_indexes)

    if changed:
        context.preferences.is_dirty = True
        _external_shortcut_adoption_events.clear()
        _refresh_blender_keyconfigs(context)
        _clear_secret_paint_world_keymap_caches()
    return changed


def _sync_user_override_from_addon_keymap_edit(context, km_add, kmi_add):
    # Compatibility hook only; automatic repair must not write user keymaps.
    return False


def _ensure_user_override_from_addon_keymap(context, km_add, kmi_add):
    return None, None, False


def _external_shortcut_source_key(km_user, kmi_user):
    return (
        _keymap_identity(km_user),
        _kmi_operator_id_without_properties(km_user, kmi_user),
    )


def _main_shortcut_family_ids_for_operator(operator_id):
    family_ids = []
    for family_id, family in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES.items():
        for _keymap_name, entry_operator_id in family.get("entries", ()):
            if entry_operator_id == operator_id:
                family_ids.append(family_id)
                break
    return family_ids


def _addon_keymap_indexes_for_operator_id(operator_id):
    return [
        addon_keymap_index
        for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps)
        if (
            _secret_paint_owns_keymap_item(kmi_add)
            and _kmi_operator_id_without_properties(km_add, kmi_add) == operator_id
        )
    ]


def _external_shortcut_target_indexes(km_user, kmi_user):
    operator_id = _kmi_operator_id_without_properties(km_user, kmi_user)
    if not operator_id.startswith(("secret.", "oren.")):
        return []

    family_ids = _main_shortcut_family_ids_for_operator(operator_id)
    if family_ids:
        return sorted({
            addon_keymap_index
            for family_id in family_ids
            for addon_keymap_index, _km_add, _kmi_add, _family_id in _main_shortcut_family_entries(family_id)
        })

    target_indexes = _addon_keymap_indexes_for_operator_id(operator_id)
    grouped_indexes = set()
    for addon_keymap_index in target_indexes:
        group = _shared_painting_mode_group_for_index(addon_keymap_index)
        if group:
            grouped_indexes.update(index for index, _km_add, _kmi_add in group)

    if grouped_indexes:
        return sorted(grouped_indexes)
    return target_indexes


def _keymap_identity_matches_any_target(km_user, target_indexes):
    source_keymap_identity = _keymap_identity(km_user)
    for addon_keymap_index in target_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, _kmi_add = addon_keymaps[addon_keymap_index]
        if _keymap_identity(km_add) == source_keymap_identity:
            return True
    return False


def _target_user_keymaps_have_customization(context, target_indexes):
    user_kc = context.window_manager.keyconfigs.user
    for addon_keymap_index in target_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            continue
        km_user = _find_matching_keymap(user_kc, km_add, create=False)
        if km_user is None:
            continue
        for kmi_user in _matching_user_items(km_user, km_add, kmi_add):
            default_event = default_snapshot.get("event")
            if not default_event:
                continue
            user_event = _keymap_item_event_snapshot(kmi_user)
            if any(user_event.get(attr) != default_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
                return True
    return False


def _source_shortcut_matches_target_defaults(source_kmi, target_indexes):
    source_event = _keymap_item_event_snapshot(source_kmi)

    for addon_keymap_index in target_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            return False

        default_event = default_snapshot.get("event", {})
        if any(source_event.get(attr) != default_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            return False

    return bool(target_indexes)


def _apply_user_shortcut_to_addon_and_user_targets(context, target_indexes, source_kmi):
    source_event = _keymap_item_event_snapshot(source_kmi)
    updated = 0

    for addon_keymap_index in target_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        if not _secret_paint_owns_keymap_item(kmi_add):
            continue

        current_event = _keymap_item_event_snapshot(kmi_add)
        if any(current_event.get(attr) != source_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
            _apply_keymap_item_event_snapshot(kmi_add, source_event)
            updated += 1
        updated += _store_keymap_item_event_customization(context, km_add, kmi_add)

    if updated:
        context.preferences.is_dirty = True
    return updated


def _adopt_external_user_shortcuts(context):
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    user_kc = getattr(keyconfigs, "user", None)
    if user_kc is None or not addon_keymap_defaults:
        return 0

    adopted = 0
    observed_user_shortcut_change = False
    for km_user in list(user_kc.keymaps):
        for kmi_user in list(km_user.keymap_items):
            if not bool(getattr(kmi_user, "active", True)):
                continue
            target_indexes = _external_shortcut_target_indexes(km_user, kmi_user)
            if not target_indexes:
                continue

            source_key = _external_shortcut_source_key(km_user, kmi_user)
            source_snapshot = _keymap_item_shortcut_snapshot(kmi_user, include_control_properties=False)
            previous_snapshot = _external_shortcut_adoption_events.get(source_key)
            if previous_snapshot == source_snapshot:
                continue

            observed_user_shortcut_change = True
            _external_shortcut_adoption_events[source_key] = source_snapshot

            if _keymap_identity_matches_any_target(km_user, target_indexes):
                continue

            target_has_customization = _target_user_keymaps_have_customization(context, target_indexes)
            if (
                not target_has_customization
                and _source_shortcut_matches_target_defaults(kmi_user, target_indexes)
            ):
                continue

            if target_has_customization and previous_snapshot is None:
                continue

            adopted += _apply_user_shortcut_to_addon_and_user_targets(
                context,
                target_indexes,
                kmi_user,
            )

    if adopted or observed_user_shortcut_change:
        _clear_secret_paint_world_keymap_caches()
    return adopted



def _remove_legacy_pick_source_space_shortcuts(context):
    # Legacy migration hook kept inert to avoid silent user-keymap edits.
    return 0


def _remove_wrong_space_file_browser_main_shortcuts(context):
    # Legacy migration hook kept inert to avoid silent user-keymap edits.
    return 0


def _addon_preferences_storage(context):
    try:
        addon_entry = context.preferences.addons.get(__package__)
    except Exception:
        addon_entry = None
    return getattr(addon_entry, "preferences", None)


def _keymap_control_override_storage_key(km, kmi, property_name):
    item_identity = _addon_keymap_item_default_identity(km, kmi)
    if item_identity is None:
        return ""
    digest = hashlib.sha1(repr((item_identity, property_name)).encode("utf-8")).hexdigest()
    return f"{SECRET_PAINT_KEYMAP_CONTROL_OVERRIDE_PREFIX}{digest}"


def _keymap_event_override_storage_key(km, kmi):
    item_identity = _addon_keymap_item_default_identity(km, kmi)
    if item_identity is None:
        return ""
    digest = hashlib.sha1(repr(item_identity).encode("utf-8")).hexdigest()
    return f"{SECRET_PAINT_KEYMAP_EVENT_OVERRIDE_PREFIX}{digest}"


def _keymap_control_override_data(addon_preferences):
    try:
        raw_data = getattr(addon_preferences, "secret_paint_keymap_control_overrides", "") or "{}"
        data = json.loads(raw_data)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _set_keymap_control_override_data(context, addon_preferences, data):
    try:
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        if getattr(addon_preferences, "secret_paint_keymap_control_overrides", "") == serialized:
            return False
        addon_preferences.secret_paint_keymap_control_overrides = serialized
        context.preferences.is_dirty = True
        return True
    except Exception:
        return False


def _keymap_event_override_data(addon_preferences):
    try:
        raw_data = getattr(addon_preferences, "secret_paint_keymap_event_overrides", "") or "{}"
        data = json.loads(raw_data)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _set_keymap_event_override_data(context, addon_preferences, data):
    try:
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        if getattr(addon_preferences, "secret_paint_keymap_event_overrides", "") == serialized:
            return False
        addon_preferences.secret_paint_keymap_event_overrides = serialized
        context.preferences.is_dirty = True
        return True
    except Exception:
        return False


def _event_snapshot_differs_from_default(event_snapshot, default_event):
    if not event_snapshot or not default_event:
        return False
    return any(
        event_snapshot.get(attr) != default_event.get(attr)
        for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS
    )


def _json_safe_keymap_event_snapshot(event_snapshot):
    json_safe = {}
    for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS:
        if attr not in event_snapshot:
            continue
        value = event_snapshot.get(attr)
        if isinstance(value, bool):
            json_safe[attr] = value
        elif isinstance(value, (int, float)):
            json_safe[attr] = value
        elif value is None:
            json_safe[attr] = None
        else:
            json_safe[attr] = str(value)
    return json_safe


def _store_keymap_item_event_customization(context, km, kmi, default_snapshot=None):
    addon_preferences = _addon_preferences_storage(context)
    if addon_preferences is None:
        return 0

    default_snapshot = default_snapshot or _find_default_snapshot_for_addon_item(None, km, kmi)
    default_event = default_snapshot.get("event") if default_snapshot else None
    if not default_event:
        return 0

    storage_key = _keymap_event_override_storage_key(km, kmi)
    if not storage_key:
        return 0

    override_data = _keymap_event_override_data(addon_preferences)
    current_event = _json_safe_keymap_event_snapshot(_keymap_item_event_snapshot(kmi))
    changed = False

    if _event_snapshot_differs_from_default(current_event, default_event):
        if override_data.get(storage_key) != current_event:
            override_data[storage_key] = current_event
            changed = True
    elif storage_key in override_data:
        del override_data[storage_key]
        changed = True

    return 1 if changed and _set_keymap_event_override_data(context, addon_preferences, override_data) else 0


def _apply_stored_keymap_event_customizations(context):
    addon_preferences = _addon_preferences_storage(context)
    if addon_preferences is None:
        return 0

    override_data = _keymap_event_override_data(addon_preferences)
    if not override_data:
        return 0

    applied = 0
    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        default_event = default_snapshot.get("event") if default_snapshot else None
        if not default_event:
            continue

        storage_key = _keymap_event_override_storage_key(km_add, kmi_add)
        if not storage_key:
            continue

        event_snapshot = override_data.get(storage_key)
        if not isinstance(event_snapshot, dict):
            continue
        if not _event_snapshot_differs_from_default(event_snapshot, default_event):
            continue

        current_event = _keymap_item_event_snapshot(kmi_add)
        if _event_snapshot_differs_from_default(current_event, event_snapshot):
            _apply_keymap_item_event_snapshot(kmi_add, event_snapshot)
            applied += 1

    if applied:
        _clear_secret_paint_world_keymap_caches()
    return applied


def _clear_stored_keymap_event_customizations(context, addon_keymap_indexes):
    addon_preferences = _addon_preferences_storage(context)
    if addon_preferences is None:
        return 0

    override_data = _keymap_event_override_data(addon_preferences)
    if not override_data:
        return 0

    cleared = False
    for addon_keymap_index in addon_keymap_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        storage_key = _keymap_event_override_storage_key(km_add, kmi_add)
        if not storage_key:
            continue
        if storage_key in override_data:
            del override_data[storage_key]
            cleared = True

    return 1 if cleared and _set_keymap_event_override_data(context, addon_preferences, override_data) else 0


def _store_keymap_item_control_customization(context, km, kmi, default_snapshot=None, *, force=False):
    addon_preferences = _addon_preferences_storage(context)
    if addon_preferences is None:
        return 0

    default_snapshot = default_snapshot or _find_default_snapshot_for_addon_item(None, km, kmi)
    default_control_properties = default_snapshot.get("control_properties", {}) if default_snapshot else {}
    if not default_control_properties:
        return 0

    override_data = _keymap_control_override_data(addon_preferences)
    current_control_properties = _keymap_item_control_properties_snapshot(kmi)
    changed = False
    for property_name, default_value in default_control_properties.items():
        storage_key = _keymap_control_override_storage_key(km, kmi, property_name)
        if not storage_key:
            continue
        current_value = bool(current_control_properties.get(property_name, default_value))
        if force or current_value != bool(default_value):
            if override_data.get(storage_key) != current_value:
                override_data[storage_key] = current_value
                changed = True
        else:
            if storage_key in override_data:
                if bool(override_data.get(storage_key)) != current_value:
                    del override_data[storage_key]
                    changed = True

    return 1 if changed and _set_keymap_control_override_data(context, addon_preferences, override_data) else 0


def _apply_stored_keymap_control_customizations(context):
    addon_preferences = _addon_preferences_storage(context)
    if addon_preferences is None:
        return 0

    override_data = _keymap_control_override_data(addon_preferences)
    if not override_data:
        return 0

    applied = 0
    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        default_control_properties = default_snapshot.get("control_properties", {}) if default_snapshot else {}
        for property_name in default_control_properties:
            storage_key = _keymap_control_override_storage_key(km_add, kmi_add, property_name)
            if not storage_key:
                continue
            if storage_key not in override_data:
                continue
            value = bool(override_data.get(storage_key))
            if _set_keymap_item_control_property(kmi_add, property_name, value):
                applied += 1

    if applied:
        _clear_secret_paint_world_keymap_caches()
    return applied


def _clear_stored_keymap_control_customizations(context, addon_keymap_indexes):
    addon_preferences = _addon_preferences_storage(context)
    if addon_preferences is None:
        return 0

    override_data = _keymap_control_override_data(addon_preferences)
    if not override_data:
        return 0

    cleared = False
    for addon_keymap_index in addon_keymap_indexes:
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        default_control_properties = default_snapshot.get("control_properties", {}) if default_snapshot else {}
        for property_name in default_control_properties:
            storage_key = _keymap_control_override_storage_key(km_add, kmi_add, property_name)
            if not storage_key:
                continue
            if storage_key in override_data:
                del override_data[storage_key]
                cleared = True

    return 1 if cleared and _set_keymap_control_override_data(context, addon_preferences, override_data) else 0


_SECRET_PAINT_KEYMAP_MAINTENANCE_UNSAFE_MODES = {
    "EDIT",
    "EDIT_ARMATURE",
    "EDIT_CURVE",
    "EDIT_CURVES",
    "EDIT_GPENCIL",
    "EDIT_LATTICE",
    "EDIT_MESH",
    "EDIT_METABALL",
    "EDIT_TEXT",
    "PAINT_GPENCIL",
    "PAINT_TEXTURE",
    "PAINT_VERTEX",
    "PARTICLE_EDIT",
    "SCULPT",
    "SCULPT_CURVES",
    "SCULPT_GPENCIL",
    "VERTEX_PAINT",
    "WEIGHT_PAINT",
}


def _secret_paint_keymap_maintenance_safe_context(context=None):
    context = context if context is not None else bpy.context
    try:
        from . import secret_paint_world_paint
        if secret_paint_world_paint.is_world_paint_running():
            return False
    except Exception:
        pass

    try:
        mode = getattr(context, "mode", "") or ""
    except Exception:
        mode = ""
    if mode in _SECRET_PAINT_KEYMAP_MAINTENANCE_UNSAFE_MODES:
        return False

    try:
        active_object = getattr(context, "active_object", None)
        active_mode = getattr(active_object, "mode", "") if active_object is not None else ""
    except Exception:
        active_mode = ""
    if active_mode in _SECRET_PAINT_KEYMAP_MAINTENANCE_UNSAFE_MODES:
        return False

    return True


def _kmi_operator_id_without_properties(km, kmi):
    try:
        return kmi.propvalue if km.is_modal else kmi.idname
    except Exception:
        return ""


def _matching_user_items_without_properties(km_user, km_add, kmi_add):
    operator_id = _kmi_operator_id_without_properties(km_add, kmi_add)
    if not operator_id:
        return []
    return [
        kmi for kmi in list(km_user.keymap_items)
        if _kmi_operator_id_without_properties(km_user, kmi) == operator_id
    ]


def _restore_mass_disabled_secret_paint_shortcuts(context):
    # Keep migration hooks inert: automatic user-keymap edits can corrupt preferences.
    return 0


_STALE_BLENDER_ENUM_KEYMAP_PROPS = {
    "paint.hide_show": ("area",),
    "outliner.id_operation": ("type",),
    "outliner.lib_operation": ("type",),
}


def _enum_property_identifiers(operator_properties, prop_name):
    try:
        rna_properties = operator_properties.bl_rna.properties
    except Exception:
        return []

    prop_rna = None
    try:
        prop_rna = rna_properties[prop_name]
    except Exception:
        for candidate in rna_properties:
            if getattr(candidate, "identifier", "") == prop_name:
                prop_rna = candidate
                break

    if prop_rna is None or getattr(prop_rna, "type", "") != 'ENUM':
        return []

    identifiers = []
    try:
        enum_items = prop_rna.enum_items
    except Exception:
        enum_items = ()
    for enum_item in enum_items:
        identifier = getattr(enum_item, "identifier", "")
        if identifier:
            identifiers.append(identifier)
    return identifiers


def _keymap_item_has_invalid_enum_property(kmi, prop_name):
    operator_properties = getattr(kmi, "properties", None)
    if operator_properties is None:
        return False
    enum_identifiers = _enum_property_identifiers(operator_properties, prop_name)
    if not enum_identifiers:
        return False
    try:
        current_value = getattr(operator_properties, prop_name)
    except Exception:
        return True
    return current_value not in enum_identifiers


def _repair_stale_blender_enum_user_keymaps(context):
    # Never repair Blender-native keymaps from this add-on.
    return 0


def _repair_addon_keymap_defaults(context=None):
    if context is not None and not _secret_paint_keymap_maintenance_safe_context(context):
        return 0

    if not addon_keymap_defaults:
        return 0

    repaired = 0
    for addon_keymap_index, (km_add, kmi_add) in enumerate(list(addon_keymaps)):
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            continue
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        is_alive = _keymap_item_is_alive(km_add, kmi_add)
        matches_default_operator = is_alive and _keymap_item_matches_default(km_add, kmi_add, default_snapshot)

        if matches_default_operator:
            continue

        if is_alive:
            continue

        if addon_keymap_index < len(addon_keymap_defaults):
            default_snapshot = addon_keymap_defaults[addon_keymap_index]

        kmi_new = _new_keymap_item_from_default_snapshot(km_add, default_snapshot)
        addon_keymaps[addon_keymap_index] = (km_add, kmi_new)
        repaired += 1

    return repaired


def _sync_addon_keymap_item_from_user_item(kmi_add, kmi_user, *, sync_control_properties=True):
    changed = False
    user_event = _keymap_item_event_snapshot(kmi_user)
    current_event = _keymap_item_event_snapshot(kmi_add)
    if any(current_event.get(attr) != user_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
        _apply_keymap_item_event_snapshot(kmi_add, user_event)
        changed = True
    if sync_control_properties and _sync_keymap_item_control_properties(kmi_user, kmi_add):
        changed = True
    return changed


def _sync_addon_keymap_item_from_addon_item(kmi_target, kmi_source):
    changed = False
    source_event = _keymap_item_event_snapshot(kmi_source)
    current_event = _keymap_item_event_snapshot(kmi_target)
    if any(current_event.get(attr) != source_event.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
        _apply_keymap_item_event_snapshot(kmi_target, source_event)
        changed = True
    if _sync_keymap_item_control_properties(kmi_source, kmi_target):
        changed = True
    return changed


def _secret_paint_owns_keymap_item(kmi):
    idname = getattr(kmi, "idname", "")
    return idname.startswith(("secret.", "oren."))


def _secret_paint_owned_keymap_operator_ids():
    operator_ids = set()
    for km_add, kmi_add in addon_keymaps:
        if not _secret_paint_owns_keymap_item(kmi_add):
            continue
        operator_id = _kmi_operator_id_without_properties(km_add, kmi_add)
        if operator_id:
            operator_ids.add(operator_id)
    return operator_ids


def _remove_secret_paint_user_keymap_items(context, operator_ids=None):
    return 0


def _secret_paint_user_keymap_cleanup_timer():
    return None


def _register_secret_paint_user_keymap_cleanup_timer():
    global _secret_paint_user_keymap_cleanup_attempts
    _secret_paint_user_keymap_cleanup_attempts = 0


def _sync_user_keymaps_from_addon_customizations(context):
    if not addon_keymap_defaults:
        return 0

    synced = 0
    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        if not _secret_paint_owns_keymap_item(kmi_add):
            continue
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            continue
        default_event = default_snapshot.get("event")
        if not default_event:
            continue

        synced += _store_keymap_item_control_customization(context, km_add, kmi_add, default_snapshot)
        synced += _store_keymap_item_event_customization(context, km_add, kmi_add, default_snapshot)

    if synced:
        context.preferences.is_dirty = True
    return synced


def _sync_linked_addon_shortcut_groups_from_masters(context=None):
    synced = 0
    if context is None:
        context = bpy.context

    for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
        _master_index, _km_master_add, kmi_master_add = _main_shortcut_master_entry(family_id)
        if kmi_master_add is None:
            continue
        for _addon_keymap_index, _km_add, kmi_add, _family_id in _main_shortcut_family_entries(family_id):
            if kmi_add is kmi_master_add:
                continue
            if _sync_addon_keymap_item_from_addon_item(kmi_add, kmi_master_add):
                synced += 1

    for group in _shared_painting_mode_shortcut_groups():
        _master_index, _km_master_add, kmi_master_add = group[0]
        for _addon_keymap_index, _km_add, kmi_add in group[1:]:
            if _sync_addon_keymap_item_from_addon_item(kmi_add, kmi_master_add):
                synced += 1

    derived_synced, _derived_indexes = _apply_derived_shortcut_links_for_source_families(
        context,
        SECRET_PAINT_DERIVED_SHORTCUT_LINKS.keys(),
        store=True,
    )
    synced += derived_synced

    if synced:
        try:
            from . import secret_paint_world_paint
            secret_paint_world_paint._clear_world_keymap_lookup_caches()
        except Exception:
            pass

    return synced


def _sync_addon_keymaps_from_user_overrides(context, *, include_main_families=False):
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    user_kc = getattr(keyconfigs, "user", None)
    if user_kc is None or not addon_keymap_defaults:
        return 0

    override_sources = {}
    main_family_indexes = _main_shortcut_family_indexes()
    addon_preferences = _addon_preferences_storage(context)
    control_override_data = _keymap_control_override_data(addon_preferences) if addon_preferences else {}

    if include_main_families:
        for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
            family_source = None
            family_entries = _main_shortcut_family_entries(family_id)
            for _addon_keymap_index, km_add, kmi_add, _family_id in family_entries:
                kmi_user = _find_best_user_item_in_keyconfig(user_kc, km_add, kmi_add)
                if kmi_user is not None and _user_item_differs_from_addon_default(km_add, kmi_add, kmi_user):
                    family_source = kmi_user
                    break
                if family_source is None:
                    family_source = kmi_user
            if family_source is None:
                continue
            for addon_keymap_index, _km_add, _kmi_add, _family_id in family_entries:
                override_sources[addon_keymap_index] = family_source

    for group in _shared_painting_mode_shortcut_groups():
        _master_index, km_master_add, kmi_master_add = group[0]
        group_source = _find_best_user_item_in_keyconfig(user_kc, km_master_add, kmi_master_add)
        if group_source is None:
            for _addon_keymap_index, km_add, kmi_add in group[1:]:
                kmi_user = _find_best_user_item_in_keyconfig(user_kc, km_add, kmi_add)
                if kmi_user is not None:
                    group_source = kmi_user
                    break
        if group_source is None:
            continue
        for addon_keymap_index, _km_add, _kmi_add in group:
            if not include_main_families and addon_keymap_index in main_family_indexes:
                continue
            override_sources.setdefault(addon_keymap_index, group_source)

    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        if addon_keymap_index in override_sources:
            continue
        if not _secret_paint_owns_keymap_item(kmi_add):
            continue
        if not include_main_families and addon_keymap_index in main_family_indexes:
            continue
        kmi_user = _find_best_user_item_in_keyconfig(user_kc, km_add, kmi_add)
        if kmi_user is not None:
            override_sources[addon_keymap_index] = kmi_user

    synced = 0
    for addon_keymap_index, kmi_user in override_sources.items():
        if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
            continue
        _km_add, kmi_add = addon_keymaps[addon_keymap_index]
        if not _secret_paint_owns_keymap_item(kmi_add):
            continue
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, _km_add, kmi_add)
        if _sync_addon_keymap_item_from_user_item(kmi_add, kmi_user, sync_control_properties=False):
            synced += 1
            synced += _store_keymap_item_event_customization(context, _km_add, kmi_add, default_snapshot)

    if synced:
        try:
            from . import secret_paint_world_paint
            secret_paint_world_paint._clear_world_keymap_lookup_caches()
        except Exception:
            pass

    return synced


def _sync_addon_shortcuts_from_saved_user_overrides(context):
    _repair_addon_keymap_defaults(context)
    synced = _apply_stored_keymap_event_customizations(context)
    synced += _apply_stored_keymap_control_customizations(context)
    synced += _sync_linked_addon_shortcut_groups_from_masters(context)
    synced += _sync_user_keymap_overrides_from_addon_indexes(
        context,
        range(len(addon_keymaps)),
        only_customized=True,
    )
    return synced


def _persist_user_keymaps_from_addon_shortcut_customizations(context):
    synced = _sync_user_keymaps_from_addon_customizations(context)
    return synced


def _sync_secret_paint_keymap_customizations_now(context):
    if not _secret_paint_keymap_maintenance_safe_context(context):
        return 0

    synced = _persist_user_keymaps_from_addon_shortcut_customizations(context)
    synced += _sync_addon_shortcuts_from_saved_user_overrides(context)
    try:
        addon_keymaps_collection = context.window_manager.keyconfigs.addon.keymaps
        if sync_secret_paint_panel_drag_keymap(addon_keymaps, addon_keymaps_collection):
            _capture_addon_keymap_defaults()
            synced += 1
    except Exception:
        pass
    return synced


def _secret_paint_keymap_maintenance_timer():
    if not _secret_paint_keymap_maintenance_enabled:
        return None
    try:
        _sync_secret_paint_keymap_customizations_now(bpy.context)
    except Exception:
        pass
    return _SECRET_PAINT_KEYMAP_MAINTENANCE_INTERVAL


def _secret_paint_keymap_preferences_sync_timer():
    return None


def _request_secret_paint_keymap_preferences_sync():
    global _secret_paint_keymap_preferences_sync_until
    # Shortcut controls sync immediately from Preferences. Avoid deferred keymap
    # writes because Blender 5.1 can crash if keyconfigs are touched during
    # native curve-sculpt modal/radial-control event handling.
    _secret_paint_keymap_preferences_sync_until = 0.0


def _secret_paint_deferred_keymap_sync_timer():
    global _secret_paint_deferred_keymap_sync_attempts

    if not _secret_paint_keymap_maintenance_enabled:
        return None
    _secret_paint_deferred_keymap_sync_attempts += 1
    try:
        _sync_addon_shortcuts_from_saved_user_overrides(bpy.context)
    except Exception:
        pass
    if _secret_paint_deferred_keymap_sync_attempts < _SECRET_PAINT_DEFERRED_KEYMAP_SYNC_MAX_ATTEMPTS:
        return 0.25
    return None


def _register_secret_paint_keymap_maintenance_timer():
    # Shortcut sync now runs on add-on enable and when the preferences UI draws.
    # Keeping a persistent timer alive here causes object-mode slowdown.
    return _unregister_secret_paint_keymap_maintenance_timer()


def _unregister_secret_paint_keymap_maintenance_timer():
    global _secret_paint_keymap_maintenance_enabled, _secret_paint_deferred_keymap_sync_attempts
    global _secret_paint_keymap_preferences_sync_until
    global _secret_paint_user_keymap_cleanup_attempts
    _secret_paint_keymap_maintenance_enabled = False
    _secret_paint_deferred_keymap_sync_attempts = 0
    _secret_paint_keymap_preferences_sync_until = 0.0
    _secret_paint_user_keymap_cleanup_attempts = 0
    _external_shortcut_adoption_events.clear()
    if bpy.app.timers.is_registered(_secret_paint_user_keymap_cleanup_timer):
        bpy.app.timers.unregister(_secret_paint_user_keymap_cleanup_timer)
    if bpy.app.timers.is_registered(_secret_paint_keymap_preferences_sync_timer):
        bpy.app.timers.unregister(_secret_paint_keymap_preferences_sync_timer)
    if bpy.app.timers.is_registered(_secret_paint_deferred_keymap_sync_timer):
        bpy.app.timers.unregister(_secret_paint_deferred_keymap_sync_timer)
    if bpy.app.timers.is_registered(_secret_paint_keymap_maintenance_timer):
        bpy.app.timers.unregister(_secret_paint_keymap_maintenance_timer)
    return None


def _matching_user_items(km_user, km_add, kmi_add):
    operator_identity = _kmi_operator_identity(km_add, kmi_add)
    keymap_identity, operator_id, properties_signature = operator_identity
    if _keymap_identity(km_user) != keymap_identity:
        return []

    matches = []
    for kmi in list(km_user.keymap_items):
        if _kmi_operator_id_without_properties(km_user, kmi) != operator_id:
            continue
        if km_user.is_modal or not properties_signature:
            matches.append(kmi)
            continue
        matches.append(kmi)
    return matches


def _addon_keymap_default_event_snapshot(km_add, kmi_add):
    try:
        target_pointer = kmi_add.as_pointer()
    except Exception:
        target_pointer = None
    for addon_keymap_index, (candidate_km, candidate_kmi) in enumerate(addon_keymaps):
        if candidate_km is not km_add:
            continue
        try:
            same_item = candidate_kmi is kmi_add or (
                target_pointer is not None and candidate_kmi.as_pointer() == target_pointer
            )
        except Exception:
            same_item = candidate_kmi is kmi_add
        if not same_item:
            continue
        default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
        if default_snapshot is None:
            return None
        return default_snapshot.get("event")

    default_snapshot = _find_default_snapshot_for_addon_item(None, km_add, kmi_add)
    return default_snapshot.get("event") if default_snapshot is not None else None


def _find_best_user_item(km_user, km_add, kmi_add):
    candidates = _matching_user_items(km_user, km_add, kmi_add)
    if not candidates:
        return None

    default_event_snapshot = _addon_keymap_default_event_snapshot(km_add, kmi_add)
    if default_event_snapshot:
        for kmi in candidates:
            if _keymap_item_event_snapshot(kmi) != default_event_snapshot:
                return kmi

    addon_event_identity = _kmi_event_identity(kmi_add)
    for kmi in candidates:
        if _kmi_event_identity(kmi) == addon_event_identity:
            return kmi

    return candidates[0]


def _user_item_differs_from_addon_default(km_add, kmi_add, kmi_user):
    default_event_snapshot = _addon_keymap_default_event_snapshot(km_add, kmi_add)
    return bool(default_event_snapshot and _keymap_item_event_snapshot(kmi_user) != default_event_snapshot)


def _find_best_user_item_in_keyconfig(user_kc, km_add, kmi_add):
    if user_kc is None:
        return None

    km_user = _find_matching_keymap(user_kc, km_add, create=False)
    kmi_user = _find_best_user_item(km_user, km_add, kmi_add) if km_user is not None else None
    if kmi_user is not None:
        return kmi_user

    operator_id = _kmi_operator_id_without_properties(km_add, kmi_add)
    if not operator_id:
        return None

    candidates = []
    for candidate_km in user_kc.keymaps:
        if km_user is not None and _keymap_identity(candidate_km) == _keymap_identity(km_user):
            continue
        for candidate_kmi in candidate_km.keymap_items:
            if _kmi_operator_id_without_properties(candidate_km, candidate_kmi) == operator_id:
                candidates.append(candidate_kmi)

    if not candidates:
        return None

    for candidate_kmi in candidates:
        if _user_item_differs_from_addon_default(km_add, kmi_add, candidate_kmi):
            return candidate_kmi
    return candidates[0]


def _painting_mode_shortcut_indexes(*, exclude_indexes=None):
    exclude_indexes = set(exclude_indexes or ())
    return [
        addon_keymap_index
        for addon_keymap_index, (_km_add, kmi_add) in enumerate(addon_keymaps)
        if (
            addon_keymap_index not in exclude_indexes
            and _is_painting_mode_shortcut(kmi_add)
        )
    ]


def _shared_painting_mode_shortcut_groups(painting_mode_indexes=None):
    if painting_mode_indexes is None:
        painting_mode_indexes = _painting_mode_shortcut_indexes(
            exclude_indexes=_main_shortcut_family_indexes(),
        )

    groups_by_operator = {}
    for addon_keymap_index in painting_mode_indexes:
        km_add, kmi_add = addon_keymaps[addon_keymap_index]
        groups_by_operator.setdefault(
            _kmi_operator_only_identity(km_add, kmi_add),
            [],
        ).append((addon_keymap_index, km_add, kmi_add))

    return [
        group
        for group in groups_by_operator.values()
        if len(group) > 1
    ]


def _hidden_shared_painting_mode_shortcut_indexes(groups):
    return {
        addon_keymap_index
        for group in groups
        for addon_keymap_index, _km_add, _kmi_add in group[1:]
    }


def _shared_painting_mode_group_for_index(addon_keymap_index, groups=None):
    if groups is None:
        groups = _shared_painting_mode_shortcut_groups()
    for group in groups:
        if any(index == addon_keymap_index for index, _km_add, _kmi_add in group):
            return group
    return None


def _shared_painting_mode_group_has_user_master(context, group):
    if not group:
        return False
    _master_index, km_master_add, kmi_master_add = group[0]
    user_kc = context.window_manager.keyconfigs.user
    km_master_user = _find_matching_keymap(user_kc, km_master_add, create=False)
    if km_master_user is None:
        return False
    return _find_best_user_item(km_master_user, km_master_add, kmi_master_add) is not None


def _sync_shared_painting_mode_shortcut_groups(context, groups=None, *, create_missing_master=True):
    if groups is None:
        groups = _shared_painting_mode_shortcut_groups()
    if not groups:
        return 0

    updated = 0
    for group in groups:
        _master_index, _km_master_add, kmi_master_add = group[0]
        event_snapshot = _keymap_item_event_snapshot(kmi_master_add)
        active = bool(getattr(kmi_master_add, "active", True))
        for _addon_keymap_index, _km_add, kmi_add in group[1:]:
            changed = False
            current_snapshot = _keymap_item_event_snapshot(kmi_add)
            if any(current_snapshot.get(attr) != event_snapshot.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
                _apply_keymap_item_event_snapshot(kmi_add, event_snapshot)
                changed = True
            if bool(getattr(kmi_add, "active", True)) != active:
                kmi_add.active = active
                changed = True
            if changed:
                updated += 1

    if updated:
        _clear_secret_paint_world_keymap_caches()
    return updated


def _main_shortcut_family_entry_specs(family_id):
    family = SECRET_PAINT_MAIN_SHORTCUT_FAMILIES.get(family_id)
    return tuple(family.get("entries", ())) if family else ()


def _main_shortcut_family_entries(family_id=None):
    family_ids = (family_id,) if family_id else tuple(SECRET_PAINT_MAIN_SHORTCUT_FAMILIES.keys())
    family_specs = {
        current_family_id: set(_main_shortcut_family_entry_specs(current_family_id))
        for current_family_id in family_ids
    }
    entries = []
    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        entry_key = (km_add.name, getattr(kmi_add, "idname", ""))
        for current_family_id, specs in family_specs.items():
            if entry_key in specs:
                entries.append((addon_keymap_index, km_add, kmi_add, current_family_id))
                break
    return entries


def _addon_keymap_entries_for_specs(entry_specs):
    specs = set(entry_specs or ())
    if not specs:
        return []

    entries = []
    for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
        entry_key = (km_add.name, getattr(kmi_add, "idname", ""))
        if entry_key in specs:
            entries.append((addon_keymap_index, km_add, kmi_add))
    return entries


def _derived_shortcut_link_entries(link):
    family_id = link.get("family_id", "")
    if family_id:
        return [
            (addon_keymap_index, km_add, kmi_add)
            for addon_keymap_index, km_add, kmi_add, _family_id
            in _main_shortcut_family_entries(family_id)
        ]
    return _addon_keymap_entries_for_specs(link.get("entries", ()))


def _derive_keymap_event_snapshot(source_event, modifier_overrides):
    derived_event = dict(source_event or {})
    if not derived_event:
        return derived_event
    derived_event["any"] = False
    for modifier_name, modifier_value in (modifier_overrides or {}).items():
        if modifier_name in {"shift", "ctrl", "alt", "oskey", "hyper"}:
            derived_event[modifier_name] = bool(modifier_value)
    return derived_event


def _keymap_item_event_matches_snapshot(kmi, event_snapshot):
    current_event = _keymap_item_event_snapshot(kmi)
    return all(
        current_event.get(attr) == event_snapshot.get(attr)
        for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS
    )


def _apply_keymap_item_event_snapshot_if_changed(kmi, event_snapshot):
    if _keymap_item_event_matches_snapshot(kmi, event_snapshot):
        return False
    _apply_keymap_item_event_snapshot(kmi, event_snapshot)
    return True


def _source_family_ids_for_indexes(addon_keymap_indexes):
    valid_indexes = set(addon_keymap_indexes or ())
    family_ids = set()
    if not valid_indexes:
        return family_ids
    for family_id in SECRET_PAINT_DERIVED_SHORTCUT_LINKS:
        family_indexes = {
            addon_keymap_index
            for addon_keymap_index, _km_add, _kmi_add, _family_id
            in _main_shortcut_family_entries(family_id)
        }
        if valid_indexes.intersection(family_indexes):
            family_ids.add(family_id)
    return family_ids


def _apply_derived_shortcut_links_for_source_families(
    context,
    source_family_ids,
    *,
    previous_source_events=None,
    store=False,
):
    previous_source_events = previous_source_events or {}
    changed = 0
    target_indexes = set()

    for source_family_id in source_family_ids:
        _source_index, _source_km, source_kmi = _main_shortcut_master_entry(source_family_id)
        if source_kmi is None:
            continue
        source_event = _keymap_item_event_snapshot(source_kmi)

        for link in SECRET_PAINT_DERIVED_SHORTCUT_LINKS.get(source_family_id, ()):
            modifier_overrides = link.get("modifier_overrides", {})
            target_event = _derive_keymap_event_snapshot(source_event, modifier_overrides)
            if not target_event:
                continue

            previous_target_event = None
            previous_source_event = previous_source_events.get(source_family_id)
            if previous_source_event:
                previous_target_event = _derive_keymap_event_snapshot(previous_source_event, modifier_overrides)

            mode = link.get("mode", "always")
            for addon_keymap_index, km_add, kmi_add in _derived_shortcut_link_entries(link):
                should_update = mode == "always"
                if not should_update and previous_target_event:
                    should_update = _keymap_item_event_matches_snapshot(kmi_add, previous_target_event)
                if not should_update:
                    continue

                target_indexes.add(addon_keymap_index)
                if _apply_keymap_item_event_snapshot_if_changed(kmi_add, target_event):
                    changed += 1

    if store:
        for addon_keymap_index in target_indexes:
            if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
                continue
            km_add, kmi_add = addon_keymaps[addon_keymap_index]
            default_snapshot = _find_default_snapshot_for_addon_item(addon_keymap_index, km_add, kmi_add)
            changed += _store_keymap_item_event_customization(context, km_add, kmi_add, default_snapshot)

    if changed:
        _clear_secret_paint_world_keymap_caches()
    return changed, target_indexes


def _main_shortcut_family_indexes():
    return {addon_keymap_index for addon_keymap_index, _km_add, _kmi_add, _family_id in _main_shortcut_family_entries()}


def _main_shortcut_master_entry(family_id):
    family_entries = _main_shortcut_family_entries(family_id)
    specs = _main_shortcut_family_entry_specs(family_id)
    for keymap_name, operator_id in specs:
        for addon_keymap_index, km_add, kmi_add, _family_id in family_entries:
            if km_add.name == keymap_name and getattr(kmi_add, "idname", "") == operator_id:
                return addon_keymap_index, km_add, kmi_add
    return None, None, None


def _main_shortcut_current_item(context, family_id):
    _addon_keymap_index, km_add, kmi_add = _main_shortcut_master_entry(family_id)
    if km_add is None:
        return None

    return kmi_add


def _apply_main_shortcut_family(context, family_id, *, event_snapshot=None, active=True, create_missing=True):
    family_entries = _main_shortcut_family_entries(family_id)
    if not family_entries:
        return 0

    updated = 0
    for _addon_keymap_index, km_add, kmi_add, _family_id in family_entries:
        changed = False
        if event_snapshot is not None:
            current_snapshot = _keymap_item_event_snapshot(kmi_add)
            if any(current_snapshot.get(attr) != event_snapshot.get(attr) for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS):
                _apply_keymap_item_event_snapshot(kmi_add, event_snapshot)
                changed = True
        if bool(getattr(kmi_add, "active", True)) != bool(active):
            kmi_add.active = bool(active)
            changed = True
        if changed:
            updated += 1

    if updated:
        _clear_secret_paint_world_keymap_caches()
    return updated


def _main_shortcut_master_user_item(context, family_id, *, create=False):
    _addon_keymap_index, km_add, kmi_add = _main_shortcut_master_entry(family_id)
    if km_add is None:
        return None, None

    user_kc = context.window_manager.keyconfigs.user
    km_user = _find_matching_keymap(user_kc, km_add, create=False)
    if km_user is None:
        return None, None

    kmi_user = _find_best_user_item(km_user, km_add, kmi_add)
    return km_user, kmi_user


def _sync_main_shortcut_family_from_master(
    context,
    family_id,
    *,
    create_missing_master=False,
    create_linked_user_overrides=False,
):
    _master_index, _km_master_add, kmi_master_add = _main_shortcut_master_entry(family_id)
    if kmi_master_add is None:
        return 0

    event_snapshot = _keymap_item_event_snapshot(kmi_master_add)
    updated = _apply_main_shortcut_family(
        context,
        family_id,
        event_snapshot=event_snapshot,
        active=bool(getattr(kmi_master_add, "active", True)),
        create_missing=create_linked_user_overrides,
    )
    return updated


def _sync_main_shortcut_families_from_masters(context):
    updated = 0
    for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
        updated += _sync_main_shortcut_family_from_master(context, family_id)
    return updated


def _sync_linked_shortcut_groups_from_masters(context):
    updated = _sync_main_shortcut_families_from_masters(context)
    updated += _sync_shared_painting_mode_shortcut_groups(
        context,
        create_missing_master=False,
    )
    derived_updated, _derived_indexes = _apply_derived_shortcut_links_for_source_families(
        context,
        SECRET_PAINT_DERIVED_SHORTCUT_LINKS.keys(),
        store=True,
    )
    updated += derived_updated
    return updated


def _sync_user_main_shortcut_family_from_addon_master(context, family_id):
    master_index, km_master_add, kmi_master_add = _main_shortcut_master_entry(family_id)
    if kmi_master_add is None:
        return 0
    master_event = _keymap_item_event_snapshot(kmi_master_add)
    default_snapshot = _find_default_snapshot_for_addon_item(master_index, km_master_add, kmi_master_add)
    default_event = default_snapshot.get("event") if default_snapshot is not None else None
    master_is_default_event = bool(
        default_event
        and all(
            master_event.get(attr) == default_event.get(attr)
            for attr in SECRET_PAINT_KEYMAP_EVENT_ATTRS
        )
    )
    return _apply_main_shortcut_family(
        context,
        family_id,
        event_snapshot=master_event,
        active=bool(getattr(kmi_master_add, "active", True)),
        create_missing=not master_is_default_event,
    )


def _sync_user_main_shortcut_families_from_addon_masters(context):
    updated = 0
    for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
        updated += _sync_user_main_shortcut_family_from_addon_master(context, family_id)
    return updated


def _keymap_item_pointer(kmi):
    try:
        return kmi.as_pointer()
    except Exception:
        return id(kmi)


def _resolve_main_shortcut_family_conflicts(context, family_id):
    return 0


def _migrate_main_shortcuts_to_q_defaults(context):
    addon_preferences = _addon_preferences_storage(context)
    try:
        if addon_preferences and addon_preferences.get(_SECRET_PAINT_MAIN_SHORTCUTS_Q_MIGRATED_KEY, False):
            return 0
    except Exception:
        pass

    try:
        if addon_preferences is not None:
            addon_preferences[_SECRET_PAINT_MAIN_SHORTCUTS_Q_MIGRATED_KEY] = True
    except Exception:
        pass
    return 0


def _keymap_property_label(value):
    return str(value).replace("_", " ").title()


def _keymap_shortcut_label_from_event(event_snapshot):
    if not event_snapshot:
        return "Unassigned"

    key_type = event_snapshot.get("type", "")
    if not key_type or key_type == 'NONE':
        return "Unassigned"

    parts = []
    if bool(event_snapshot.get("shift", False)):
        parts.append("Shift")
    if bool(event_snapshot.get("ctrl", False)):
        parts.append("Ctrl")
    if bool(event_snapshot.get("alt", False)):
        parts.append("Alt")
    if bool(event_snapshot.get("oskey", False)):
        parts.append("Win")
    if bool(event_snapshot.get("hyper", False)):
        parts.append("Hyper")

    key_label = str(key_type).replace("_", " ").title()
    if len(key_type) == 1:
        key_label = key_type.upper()
    elif key_type.startswith("NUMPAD_"):
        key_label = "Numpad " + key_type[7:].replace("_", " ").title()
    elif key_type in {"GRLESS", "RET", "ESC", "DEL"}:
        key_label = {
            "GRLESS": "Grless",
            "RET": "Enter",
            "ESC": "Esc",
            "DEL": "Delete",
        }[key_type]
    parts.append(key_label)
    return " ".join(parts)


def _keymap_item_shortcut_label(kmi):
    try:
        label = kmi.to_string()
        if label:
            return label
    except Exception:
        pass
    return _keymap_shortcut_label_from_event(_keymap_item_event_snapshot(kmi))


def _keymap_item_control_property_label(kmi, property_name):
    try:
        prop = getattr(kmi.properties.bl_rna.properties, property_name)
        label = getattr(prop, "name", "")
        if label:
            return label
    except Exception:
        pass
    return _keymap_property_label(property_name)


_SECRET_PAINT_MODIFIER_EVENT_TYPES = {
    "LEFT_CTRL",
    "LEFT_ALT",
    "LEFT_SHIFT",
    "RIGHT_ALT",
    "RIGHT_CTRL",
    "RIGHT_SHIFT",
    "OSKEY",
    "HYPER",
}


def _keymap_capture_event_snapshot_from_event(kmi, event):
    event_type = getattr(event, "type", "")
    if not event_type:
        return None
    if event_type in _SECRET_PAINT_MODIFIER_EVENT_TYPES:
        return None

    event_value = getattr(event, "value", "PRESS")
    if event_value not in {'PRESS', 'CLICK', 'DOUBLE_CLICK'}:
        return None

    map_type = 'KEYBOARD'
    if event_type.endswith("MOUSE") or event_type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
        map_type = 'MOUSE'
    elif event_type.startswith("NDOF_"):
        map_type = 'NDOF'

    snapshot = _keymap_item_event_snapshot(kmi)
    snapshot.update({
        "map_type": map_type,
        "type": event_type,
        "value": 'PRESS' if event_value == 'PRESS' else event_value,
        "any": False,
        "shift": bool(getattr(event, "shift", False)),
        "ctrl": bool(getattr(event, "ctrl", False)),
        "alt": bool(getattr(event, "alt", False)),
        "oskey": bool(getattr(event, "oskey", False)),
        "hyper": False,
        "key_modifier": 'NONE',
        "direction": 'ANY',
        "repeat": False,
        "active": True,
    })
    return snapshot


_SECRET_PAINT_FIXED_KEYMAP_LABELS = {
    "secret.world_paint_tool_density": "Tool: Density",
    "secret.world_paint_tool_delete": "Tool: Delete",
    "secret.world_paint_tool_single": "Tool: Single",
    "secret.world_paint_tool_bezier": "Tool: Bezier",
    "secret.world_paint_tool_slide": "Tool: Slide",
    "secret.world_paint_tool_select": "Tool: Select",
    "secret.world_paint_tool_rotation": "Tool: Rotation",
    "secret.world_paint_tool_scale": "Tool: Scale",
    "secret.world_paint_toggle_lock_surface": "Toggle: Lock Terrain",
    "secret.world_paint_toggle_target_surface": "Toggle: Target Surface",
    "secret.world_paint_toggle_wire_bounds_surfaces": "Toggle: Wire",
    "secret.world_paint_toggle_interpolate": "Toggle: Interpolate",
    "secret.world_paint_toggle_random_z": "Toggle: Random Z",
    "secret.world_paint_toggle_align_to_normal": "Toggle: Align To Normal",
    "secret.world_paint_adjust_strength": "Adjust: Strength",
}
if SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED:
    _SECRET_PAINT_FIXED_KEYMAP_LABELS["secret.world_paint_adjust_size"] = "Adjust: Size"


def _keymap_item_display_name(kmi):
    fixed_label = _SECRET_PAINT_FIXED_KEYMAP_LABELS.get(kmi.idname)
    if fixed_label:
        return fixed_label
    if kmi.idname == "secret.world_paint_set_tool":
        tool_id = getattr(kmi.properties, "tool_id", "")
        if tool_id:
            return f"Tool: {_keymap_property_label(tool_id)}"
    if kmi.idname == "secret.world_paint_toggle_flag":
        flag_id = getattr(kmi.properties, "flag_id", "")
        if flag_id:
            return f"Toggle: {_keymap_property_label(flag_id)}"
    if kmi.idname == "secret.world_paint_begin_adjust":
        adjust_mode = getattr(kmi.properties, "adjust_mode", "")
        if adjust_mode:
            return f"Adjust: {_keymap_property_label(adjust_mode)}"
    if kmi.idname == "secret.world_paint_pick_source":
        return "Pick Source"
    if kmi.idname == "secret.paintbrushswitch":
        return "Switch Brush"
    return kmi.name or kmi.idname


def _is_painting_mode_shortcut(kmi):
    return kmi.idname in SECRET_PAINTING_MODE_SHORTCUT_OPERATOR_IDS


def _native_keymap_display_keymaps(kc):
    try:
        from bl_keymap_utils.io import keyconfig_merge
        return keyconfig_merge(kc, kc)
    except Exception:
        return [(km, kc) for km in getattr(kc, "keymaps", ())]


def _active_keymap_item_for_native_draw(km_user, kmi_user):
    try:
        km_draw = km_user.active()
    except Exception:
        return km_user, kmi_user

    try:
        target_pointer = kmi_user.as_pointer()
    except Exception:
        target_pointer = None

    if target_pointer is not None:
        for candidate in km_draw.keymap_items:
            try:
                if candidate.as_pointer() == target_pointer:
                    return km_draw, candidate
            except Exception:
                continue
    return km_draw, kmi_user


def _keymap_operator_available(kmi):
    try:
        return bool(rna_keymap_ui._is_operator_available(kmi.idname))
    except Exception:
        return True


def _draw_keymap_reset_button(row, addon_keymap_index, is_customized):
    if addon_keymap_index >= 0 and is_customized:
        props = row.operator("secret.keymap_reset_item", text="", icon='BACK')
        props.addon_keymap_index = addon_keymap_index
    else:
        row.separator(factor=1.0)


def _draw_keymap_item_event_settings(layout, kmi, map_type):
    if map_type == 'KEYBOARD':
        row = layout.row(align=True)
        row.prop(kmi, "type", text="", event=True)
        row.prop(kmi, "value", text="")
        repeat_row = row.row(align=True)
        repeat_row.active = kmi.value in {'ANY', 'PRESS'}
        repeat_row.prop(kmi, "repeat", text="Repeat")
    elif map_type in {'MOUSE', 'NDOF'}:
        row = layout.row(align=True)
        row.prop(kmi, "type", text="")
        row.prop(kmi, "value", text="")
    elif map_type == 'TWEAK':
        row = layout.row(align=True)
        row.prop(kmi, "type", text="")
        row.prop(kmi, "value", text="")
    elif map_type == 'TIMER':
        row = layout.row(align=True)
        row.prop(kmi, "type", text="")
        return
    else:
        return

    if map_type in {'KEYBOARD', 'MOUSE'} and kmi.value == 'CLICK_DRAG':
        row = layout.row()
        row.prop(kmi, "direction")

    row = layout.row()
    row.scale_x = 0.75
    row.prop(kmi, "any", toggle=True)
    row.prop(kmi, "shift_ui", text="Shift", toggle=True)
    row.prop(kmi, "ctrl_ui", text="Ctrl", toggle=True)
    row.prop(kmi, "alt_ui", text="Alt", toggle=True)
    row.prop(kmi, "oskey_ui", text="Win" if sys.platform == "win32" else "OS", toggle=True)
    try:
        if getattr(kmi, "hyper", 0) == 1:
            row.prop(kmi, "hyper_ui", text="Hyper", toggle=True)
    except Exception:
        pass
    row.prop(kmi, "key_modifier", text="", event=True)


def _draw_keymap_active_button(row, kmi, addon_keymap_index):
    icon = 'CHECKBOX_HLT' if bool(getattr(kmi, "active", True)) else 'CHECKBOX_DEHLT'
    if addon_keymap_index >= 0:
        props = row.operator("secret.keymap_toggle_active", text="", icon=icon, emboss=False)
        props.addon_keymap_index = addon_keymap_index
    else:
        row.prop(kmi, "active", text="", emboss=False)


def _draw_keymap_shortcut_capture_button(row, kmi, addon_keymap_index):
    row.prop(kmi, "type", text="", full_event=True)


def _draw_keymap_control_properties(layout, kmi, addon_keymap_index):
    control_properties = _keymap_item_control_properties_snapshot(kmi)
    if not control_properties:
        return False

    for property_name, value in control_properties.items():
        row = layout.row(align=True)
        icon = 'CHECKBOX_HLT' if bool(value) else 'CHECKBOX_DEHLT'
        if addon_keymap_index >= 0:
            props = row.operator(
                "secret.keymap_toggle_control_property",
                text=_keymap_item_control_property_label(kmi, property_name),
                icon=icon,
                emboss=False,
            )
            props.addon_keymap_index = addon_keymap_index
            props.property_name = property_name
        else:
            row.label(text=_keymap_item_control_property_label(kmi, property_name), icon=icon)
    return True


def _draw_keymap_operator_properties(layout, kmi, addon_keymap_index):
    try:
        properties = getattr(kmi, "properties", None)
    except Exception:
        properties = None
    if properties is None:
        return False

    handled = False
    try:
        rna_properties = properties.bl_rna.properties
    except Exception:
        rna_properties = ()

    for prop in rna_properties:
        try:
            identifier = prop.identifier
        except Exception:
            continue
        if identifier == "rna_type" or identifier in SECRET_PAINT_KEYMAP_CONTROL_PROPERTY_NAMES:
            continue
        try:
            if hasattr(properties, "is_property_set") and not properties.is_property_set(identifier):
                continue
        except Exception:
            continue
        try:
            row = layout.row(align=True)
            row.prop(properties, identifier)
            handled = True
        except Exception:
            pass

    if _draw_keymap_control_properties(layout, kmi, addon_keymap_index):
        handled = True
    return handled


def _draw_secret_paint_keymap_item(col, context, kc, km, kmi, addon_keymap_index=-1, display_name=None):
    col.context_pointer_set("keymap", km)
    map_type = getattr(kmi, "map_type", "")
    is_op_available = _keymap_operator_available(kmi)
    is_customized = _keymap_item_is_customized(addon_keymap_index, km, kmi)

    item_col = col.column(align=True) if getattr(kmi, "show_expanded", False) else col.column()
    box = item_col.box() if getattr(kmi, "show_expanded", False) else item_col.column()
    split = box.split()

    row = split.row(align=True)
    row.prop(kmi, "show_expanded", text="", emboss=False)
    _draw_keymap_active_button(row, kmi, addon_keymap_index)
    if km.is_modal:
        row.separator()
        row.alert = not getattr(kmi, "propvalue", "")
        row.prop(kmi, "propvalue", text="")
    elif is_op_available:
        row.label(text=display_name or getattr(kmi, "name", "") or getattr(kmi, "idname", ""))
    elif getattr(kmi, "idname", "") in {"none", ""}:
        row.alert = True
        row.label(text="(Unassigned)")
    else:
        row.alert = True
        row.label(text=f"{getattr(kmi, 'idname', '')} (unavailable)", icon='ERROR')

    row = split.row()
    if addon_keymap_index >= 0:
        props = row.operator(
            "secret.keymap_capture_shortcut",
            text=_keymap_item_shortcut_label(kmi),
            icon='KEYINGSET',
        )
        props.addon_keymap_index = addon_keymap_index
    else:
        row.prop(kmi, "map_type", text="")
        if map_type in {'KEYBOARD', 'MOUSE', 'NDOF'}:
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'TWEAK':
            subrow = row.row()
            subrow.prop(kmi, "type", text="")
            subrow.prop(kmi, "value", text="")
        elif map_type == 'TIMER':
            row.prop(kmi, "type", text="")
        else:
            row.label()
    _draw_keymap_reset_button(row, addon_keymap_index, is_customized)
    row.separator(factor=0.25 if getattr(kmi, "show_expanded", False) else 1.0)

    if not getattr(kmi, "show_expanded", False):
        return

    box = item_col.box()
    split = box.split(factor=0.4)
    sub = split.row()
    if km.is_modal:
        sub.alert = not getattr(kmi, "propvalue", "")
        sub.prop(kmi, "propvalue", text="")
    else:
        subrow = sub.row()
        subrow.alert = not is_op_available
        subrow.prop(kmi, "idname", text="", placeholder="Operator")

    shortcut_col = split.column()
    if addon_keymap_index >= 0:
        props = shortcut_col.operator(
            "secret.keymap_capture_shortcut",
            text=f"Set Shortcut: {_keymap_item_shortcut_label(kmi)}",
            icon='KEYINGSET',
        )
        props.addon_keymap_index = addon_keymap_index
    elif map_type not in {'TEXTINPUT', 'TIMER'}:
        _draw_keymap_item_event_settings(shortcut_col, kmi, map_type)
    if _keymap_item_control_properties_snapshot(kmi):
        _draw_keymap_operator_properties(box, kmi, addon_keymap_index)
    else:
        try:
            box.template_keymap_item_properties(kmi)
        except Exception:
            _draw_keymap_operator_properties(box, kmi, addon_keymap_index)


def _draw_keymap_entry(col, context, kc, km_add, kmi_add, addon_keymap_index=-1):
    _draw_secret_paint_keymap_item(
        col,
        context,
        kc,
        km_add,
        kmi_add,
        addon_keymap_index,
        display_name=_keymap_item_display_name(kmi_add),
    )


def _draw_main_shortcut_entry(col, context, kc, family_id):
    family = SECRET_PAINT_MAIN_SHORTCUT_FAMILIES[family_id]
    _addon_keymap_index, km_add, kmi_add = _main_shortcut_master_entry(family_id)
    if km_add is None or kmi_add is None:
        col.label(text=family["label"])
        col.label(text="Shortcut unavailable", icon='ERROR')
        return

    col.label(text=family["label"])
    _draw_secret_paint_keymap_item(col, context, kc, km_add, kmi_add, _addon_keymap_index)


class secret_keymap_capture_shortcut(bpy.types.Operator):
    bl_idname = "secret.keymap_capture_shortcut"
    bl_label = "Set Shortcut"
    bl_description = "Press the new shortcut for this Secret Paint action"

    addon_keymap_index: bpy.props.IntProperty(default=-1)

    def invoke(self, context, event):
        if self.addon_keymap_index < 0 or self.addon_keymap_index >= len(addon_keymaps):
            self.report({'ERROR'}, "Secret Paint shortcut is not available")
            return {'CANCELLED'}
        try:
            context.window_manager.modal_handler_add(self)
            context.workspace.status_text_set("Press a new shortcut, or Esc to cancel")
        except Exception:
            pass
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        event_type = getattr(event, "type", "")
        event_value = getattr(event, "value", "")

        if event_type in {'ESC', 'RIGHTMOUSE'} and event_value == 'PRESS':
            try:
                context.workspace.status_text_set(None)
            except Exception:
                pass
            return {'CANCELLED'}

        if event_type in {
            'MOUSEMOVE',
            'INBETWEEN_MOUSEMOVE',
            'TIMER',
            'TIMER_REPORT',
            'WINDOW_DEACTIVATE',
        }:
            return {'RUNNING_MODAL'}

        # Ignore the mouse release from clicking the Set Shortcut button.
        if event_type == 'LEFTMOUSE' and event_value == 'RELEASE':
            return {'RUNNING_MODAL'}

        _km_add, kmi_add = addon_keymaps[self.addon_keymap_index]
        event_snapshot = _keymap_capture_event_snapshot_from_event(kmi_add, event)
        if event_snapshot is None:
            return {'RUNNING_MODAL'}

        target_indexes = _linked_shortcut_indexes_for_index(self.addon_keymap_index)
        changed = _apply_keymap_event_customization_to_indexes(context, target_indexes, event_snapshot)
        try:
            context.workspace.status_text_set(None)
        except Exception:
            pass
        if changed:
            self.report({'INFO'}, f"Set shortcut to {_keymap_shortcut_label_from_event(event_snapshot)}")
        return {'FINISHED'}


class secret_keymap_toggle_active(bpy.types.Operator):
    bl_idname = "secret.keymap_toggle_active"
    bl_label = "Toggle Shortcut"
    bl_description = "Enable or disable this Secret Paint shortcut"

    addon_keymap_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        if self.addon_keymap_index < 0 or self.addon_keymap_index >= len(addon_keymaps):
            self.report({'ERROR'}, "Secret Paint shortcut is not available")
            return {'CANCELLED'}

        _repair_addon_keymap_defaults(context)
        _km_add, kmi_add = addon_keymaps[self.addon_keymap_index]
        active = not bool(getattr(kmi_add, "active", True))
        target_indexes = _linked_shortcut_indexes_for_index(self.addon_keymap_index)
        changed = 0
        for addon_keymap_index in target_indexes:
            if addon_keymap_index < 0 or addon_keymap_index >= len(addon_keymaps):
                continue
            _km_target, kmi_target = addon_keymaps[addon_keymap_index]
            if bool(getattr(kmi_target, "active", True)) != active:
                kmi_target.active = active
                changed += 1
        changed += _store_and_dirty_keymap_customization(context, target_indexes)
        self.report({'INFO'}, "Shortcut enabled" if active else "Shortcut disabled")
        return {'FINISHED'} if changed else {'CANCELLED'}


class secret_keymap_toggle_control_property(bpy.types.Operator):
    bl_idname = "secret.keymap_toggle_control_property"
    bl_label = "Toggle Shortcut Setting"
    bl_description = "Toggle this Secret Paint shortcut setting"

    addon_keymap_index: bpy.props.IntProperty(default=-1)
    property_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        if self.addon_keymap_index < 0 or self.addon_keymap_index >= len(addon_keymaps):
            self.report({'ERROR'}, "Secret Paint shortcut is not available")
            return {'CANCELLED'}
        if self.property_name not in SECRET_PAINT_KEYMAP_CONTROL_PROPERTY_NAMES:
            self.report({'ERROR'}, "Secret Paint shortcut setting is not supported")
            return {'CANCELLED'}

        _km_add, kmi_add = addon_keymaps[self.addon_keymap_index]
        current_values = _keymap_item_control_properties_snapshot(kmi_add)
        if self.property_name not in current_values:
            self.report({'ERROR'}, "Secret Paint shortcut setting is not available")
            return {'CANCELLED'}

        value = not bool(current_values.get(self.property_name))
        target_indexes = _linked_shortcut_indexes_for_index(self.addon_keymap_index)
        changed = _apply_keymap_control_customization_to_indexes(
            context,
            target_indexes,
            self.property_name,
            value,
        )
        return {'FINISHED'} if changed else {'CANCELLED'}


class secret_keymap_reset_item(bpy.types.Operator):
    bl_idname = "secret.keymap_reset_item"
    bl_label = "Reset Shortcut"
    bl_description = "Reset this Secret Paint shortcut to its default value"

    addon_keymap_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        if self.addon_keymap_index < 0 or self.addon_keymap_index >= len(addon_keymaps):
            self.report({'ERROR'}, "Secret Paint shortcut is not available")
            return {'CANCELLED'}

        reset_indexes = {self.addon_keymap_index}
        for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
            family_indexes = {
                addon_keymap_index
                for addon_keymap_index, _km_add, _kmi_add, _family_id
                in _main_shortcut_family_entries(family_id)
            }
            if self.addon_keymap_index in family_indexes:
                reset_indexes = family_indexes
                break

        group = _shared_painting_mode_group_for_index(self.addon_keymap_index)
        if group:
            reset_indexes.update(addon_keymap_index for addon_keymap_index, _km_add, _kmi_add in group)

        reset_count = _reset_shortcut_indexes_to_defaults(context, reset_indexes)
        _sync_addon_shortcuts_from_saved_user_overrides(context)
        self.report({'INFO'}, f"Reset {reset_count} Secret Paint shortcut override(s)")
        return {'FINISHED'}


class secret_keymap_create_override(bpy.types.Operator):
    bl_idname = "secret.keymap_create_override"
    bl_label = "Customize Shortcut"
    bl_description = "Store this Secret Paint shortcut override in the add-on preferences"

    addon_keymap_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        if self.addon_keymap_index < 0 or self.addon_keymap_index >= len(addon_keymaps):
            self.report({'ERROR'}, "Secret Paint shortcut is not available")
            return {'CANCELLED'}

        _repair_addon_keymap_defaults(context)
        target_indexes = _linked_shortcut_indexes_for_index(self.addon_keymap_index)
        _store_and_dirty_keymap_customization(context, target_indexes)
        _sync_linked_addon_shortcut_groups_from_masters(context)
        self.report({'INFO'}, "Stored Secret Paint shortcut override")
        return {'FINISHED'}


class secret_keymap_create_family_override(bpy.types.Operator):
    bl_idname = "secret.keymap_create_family_override"
    bl_label = "Customize Shortcut Group"
    bl_description = "Store this linked Secret Paint shortcut group in the add-on preferences"

    family_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        if self.family_id not in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
            self.report({'ERROR'}, "Secret Paint shortcut group is not available")
            return {'CANCELLED'}

        _repair_addon_keymap_defaults(context)
        _addon_keymap_index, km_add, kmi_add = _main_shortcut_master_entry(self.family_id)
        if km_add is None:
            self.report({'ERROR'}, "Secret Paint shortcut group is not registered")
            return {'CANCELLED'}

        family_indexes = {
            addon_keymap_index
            for addon_keymap_index, _km_add, _kmi_add, _family_id
            in _main_shortcut_family_entries(self.family_id)
        }
        _sync_main_shortcut_family_from_master(context, self.family_id)
        _store_and_dirty_keymap_customization(context, family_indexes)
        self.report({'INFO'}, "Stored Secret Paint shortcut group override")
        return {'FINISHED'}


class secret_keymap_reset_all(bpy.types.Operator):
    bl_idname = "secret.keymap_reset_all"
    bl_label = "Reset All Shortcut Overrides"
    bl_description = "Reset Secret Paint shortcut overrides stored in the add-on preferences."

    def execute(self, context):
        changed = 0
        _refresh_blender_keyconfigs(context)
        changed += _repair_addon_keymap_defaults(context)
        changed += _reset_addon_keymap_events_to_defaults()
        all_addon_keymap_indexes = range(len(addon_keymaps))
        changed += _clear_stored_keymap_event_customizations(context, all_addon_keymap_indexes)
        changed += _clear_stored_keymap_control_customizations(context, all_addon_keymap_indexes)
        changed += _remove_user_keymap_overrides_for_addon_indexes(
            context,
            range(len(addon_keymaps)),
        )
        if changed:
            context.preferences.is_dirty = True
            _external_shortcut_adoption_events.clear()
            _refresh_blender_keyconfigs(context)
            _clear_secret_paint_world_keymap_caches()
        self.report({'INFO'}, f"Reset {changed} Secret Paint shortcut override(s)")
        return {'FINISHED'}



# bpy.context.preferences.addons[__package__].preferences.checkboxKeepManualWhenTransferBiome
# layout.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxKeepManualWhenTransferBiome")
# row.prop(bpy.context.preferences.addons[__package__].preferences, "mocapfilename", expand=True)
import rna_keymap_ui
class secret_menu(bpy.types.AddonPreferences):
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
    secret_paint_keymap_control_overrides: bpy.props.StringProperty(
        name="Secret Paint Keymap Control Overrides",
        default="{}",
        options={'HIDDEN'},
    )
    secret_paint_keymap_event_overrides: bpy.props.StringProperty(
        name="Secret Paint Keymap Event Overrides",
        default="{}",
        options={'HIDDEN'},
    )

    def draw(self, context):
        layout = self.layout
        try:
            _refresh_blender_keyconfigs(context)
            _sync_addon_keymaps_from_user_overrides(context, include_main_families=True)
            _sync_addon_shortcuts_from_saved_user_overrides(context)
        except Exception:
            pass

        if addon_updater_ops is not None:
            addon_updater_ops.update_settings_ui(self, context)
        elif auto_updater_disabled_reason:
            box = layout.box()
            box.label(text="Updater Settings")
            box.label(text=auto_updater_disabled_reason, icon='INFO')

        draw_shared_secret_paint_preferences(layout, self)

        row = layout.row()
        row = layout.row()
        row = layout.row()
        

        kc = context.window_manager.keyconfigs.addon

        layout.operator("secret.keymap_reset_all", icon='FILE_REFRESH')

        box = layout.box()
        info_col = box.column(align=True)
        info_col.label(text="Main Secret Paint Shortcuts:", icon='INFO')
        for family_id in SECRET_PAINT_MAIN_SHORTCUT_DISPLAY_FAMILY_IDS:
            _draw_main_shortcut_entry(info_col, context, kc, family_id)
            info_col.separator()

        col = layout.column()
        grouped_keymap_indexes = {
            addon_keymap_index
            for family_id in SECRET_PAINT_MAIN_SHORTCUT_DISPLAY_FAMILY_IDS
            for addon_keymap_index, _km_add, _kmi_add, _family_id
            in _main_shortcut_family_entries(family_id)
        }
        for family_id in SECRET_PAINT_MAIN_SHORTCUT_FAMILIES:
            if family_id in SECRET_PAINT_MAIN_SHORTCUT_DISPLAY_FAMILY_IDS:
                continue
            master_index, _km_master_add, _kmi_master_add = _main_shortcut_master_entry(family_id)
            grouped_keymap_indexes.update(
                addon_keymap_index
                for addon_keymap_index, _km_add, _kmi_add, _family_id
                in _main_shortcut_family_entries(family_id)
                if addon_keymap_index != master_index
            )

        painting_mode_all_keymap_indexes = [
            addon_keymap_index
            for addon_keymap_index, (_km_add, kmi_add) in enumerate(addon_keymaps)
            if addon_keymap_index not in grouped_keymap_indexes and _is_painting_mode_shortcut(kmi_add)
        ]
        shared_painting_mode_groups = _shared_painting_mode_shortcut_groups(painting_mode_all_keymap_indexes)
        hidden_painting_mode_keymap_indexes = _hidden_shared_painting_mode_shortcut_indexes(shared_painting_mode_groups)
        painting_mode_keymap_indexes = [
            addon_keymap_index
            for addon_keymap_index in painting_mode_all_keymap_indexes
            if addon_keymap_index not in hidden_painting_mode_keymap_indexes
        ]

        if painting_mode_keymap_indexes:
            paint_box = col.box()
            paint_col = paint_box.column()
            paint_col.label(text="Painting Mode Shortcuts:", icon="BRUSH_DATA")
            paint_col.label(text="These shortcuts are active while Secret Paint mode is running.")
            old_paint_km_name = ""
            for addon_keymap_index in painting_mode_keymap_indexes:
                km_add, kmi_add = addon_keymaps[addon_keymap_index]
                if km_add.name != old_paint_km_name:
                    paint_col.label(text=str(km_add.name), icon="DOT")
                _draw_keymap_entry(paint_col, context, kc, km_add, kmi_add, addon_keymap_index)
                paint_col.separator()
                old_paint_km_name = km_add.name

            col.separator()
            col.separator()

        keymap_box = col.box()
        keymap_col = keymap_box.column()
        keymap_col.label(text="Keymap List:", icon="KEYINGSET")
        old_km_name = ""

        for addon_keymap_index, (km_add, kmi_add) in enumerate(addon_keymaps):
            if (
                addon_keymap_index in grouped_keymap_indexes
                or addon_keymap_index in painting_mode_all_keymap_indexes
            ):
                continue

            if km_add.name != old_km_name:
                keymap_col.label(text=str(km_add.name), icon="DOT")

            _draw_keymap_entry(keymap_col, context, kc, km_add, kmi_add, addon_keymap_index)
            keymap_col.separator()
            old_km_name = km_add.name














classes = [

    secret_menu,
    secret_keymap_capture_shortcut,
    secret_keymap_toggle_active,
    secret_keymap_toggle_control_property,
    secret_keymap_reset_item,
    secret_keymap_create_override,
    secret_keymap_create_family_override,
    secret_keymap_reset_all,
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
        except Exception:
            pass





def register():

    
    
    
    
    
    if addon_updater_ops is not None: addon_updater_ops.register(bl_info)

    

    unregister_secret_paint_disabled_world_paint_operator_stubs()
    _unregister_temp_disabled_secret_paint_classes()
    for cls in classes:
        bpy.utils.register_class(cls)
    register_secret_paint_panel_drag_property()



    bpy.types.Scene.mypropertieslist = bpy.props.PointerProperty(type= MyPropertiesClass)

    bpy.types.FILEBROWSER_HT_header.append(checkboxImportWithoutPainting_f)
    register_secret_paint_world_paint_runtime()
    register_secret_paint_object_mode_pie()

    


    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon.keymaps

    def addon_keymap(name, *, space_type='EMPTY', region_type='WINDOW'):
        for keymap in kc:
            if (
                keymap.name == name
                and keymap.space_type == space_type
                and keymap.region_type == region_type
            ):
                return keymap
        return kc.new(name, space_type=space_type, region_type=region_type)

    register_secret_paint_panel_drag_keymap(addon_keymaps, kc)

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.toggle_viewport_tab_bookmark", "W", "PRESS", shift=True)
    addon_keymaps.append((km, kmi))

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

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_density", "D", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_delete", "X", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_single", "K", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_slide", "G", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_select", "H", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_rotation", "R", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_scale", "S", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_tool_bezier", "B", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_toggle_lock_surface", "ONE", "PRESS")
    addon_keymaps.append((km, kmi))

    if SECRET_PAINT_WORLD_TARGET_SURFACE_ENABLED:
        km = kc.get("3D View")
        if not km:
            km = kc.new("3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new("secret.world_paint_toggle_target_surface", "I", "PRESS")
        addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_toggle_wire_bounds_surfaces", "TWO", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_toggle_interpolate", "THREE", "PRESS")
    addon_keymaps.append((km, kmi))

    if SECRET_PAINT_WORLD_RANDOM_Z_ENABLED:
        km = kc.get("3D View")
        if not km:
            km = kc.new("3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new("secret.world_paint_toggle_random_z", "T", "PRESS")
        addon_keymaps.append((km, kmi))

    if SECRET_PAINT_WORLD_ALIGN_TO_NORMAL_ENABLED:
        km = kc.get("3D View")
        if not km:
            km = kc.new("3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new("secret.world_paint_toggle_align_to_normal", "N", "PRESS")
        addon_keymaps.append((km, kmi))

    if SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED:
        km = kc.get("3D View")
        if not km:
            km = kc.new("3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new("secret.world_paint_adjust_size", "F", "PRESS")
        kmi.properties.confirm_on_release = False
        addon_keymaps.append((km, kmi))

    if SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED:
        km = kc.get("Sculpt Curves")
        if not km:
            km = kc.new("Sculpt Curves")
        kmi = km.keymap_items.new("secret.world_paint_adjust_size", "F", "PRESS")
        kmi.properties.confirm_on_release = False
        addon_keymaps.append((km, kmi))

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_adjust_strength", "F", "PRESS", alt=True)
    kmi.properties.confirm_on_release = False
    addon_keymaps.append((km, kmi))

    km = kc.get("Sculpt Curves")
    if not km:
        km = kc.new("Sculpt Curves")
    kmi = km.keymap_items.new("secret.world_paint_adjust_strength", "F", "PRESS", alt=True)
    kmi.properties.confirm_on_release = False
    addon_keymaps.append((km, kmi))
    _disable_stale_secret_paint_world_density_adjust_keymaps(bpy.context)

    km = kc.get("3D View")
    if not km:
        km = kc.new("3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("secret.world_paint_pick_source", "Q", "PRESS")
    addon_keymaps.append((km, kmi))

    km = kc.get("Sculpt Curves")
    if not km:
        km = kc.new("Sculpt Curves")
    kmi = km.keymap_items.new("secret.world_paint_pick_source", "Q", "PRESS")
    addon_keymaps.append((km, kmi))


    km = addon_keymap("File Browser Main", space_type='FILE_BROWSER')
    kmi = km.keymap_items.new("secret.paint_from_library", "Q", "PRESS")
    addon_keymaps.append((km, kmi))

    km = addon_keymap("File Browser Main", space_type='FILE_BROWSER')
    kmi = km.keymap_items.new("secret.paint_from_library_justimport", "Q", "PRESS", alt=True)
    addon_keymaps.append((km, kmi))

    km = addon_keymap("File Browser Main", space_type='FILE_BROWSER')
    kmi = km.keymap_items.new("secret.paint_from_library_switch", "Q", "PRESS", shift=True)
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

    _capture_addon_keymap_defaults()
    try:
        _sync_addon_shortcuts_from_saved_user_overrides(bpy.context)
    except Exception:
        pass
    _register_secret_paint_keymap_maintenance_timer()




def unregister():
    if addon_updater_ops is not None: addon_updater_ops.unregister()
    _unregister_secret_paint_keymap_maintenance_timer()
    unregister_secret_paint_world_paint_runtime()
    unregister_secret_paint_object_mode_pie()

    unregister_secret_paint_panel_drag_property()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    _unregister_temp_disabled_secret_paint_classes()

    del bpy.types.Scene.mypropertieslist

    bpy.types.FILEBROWSER_HT_header.remove(checkboxImportWithoutPainting_f)

    

    for km, kmi in addon_keymaps:
        if not _keymap_item_is_alive(km, kmi):
            continue
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()
    addon_keymap_defaults.clear()


if __name__ == "__main__":
    register()
