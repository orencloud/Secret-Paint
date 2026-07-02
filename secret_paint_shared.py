# Shared Secret Paint runtime used by the private add-on and the packaged public add-on.

# import bpy
import random   #orenbake procedural image names s
from bpy.types import Menu     # was necessary for orenbake, don't know what specifically
from bpy.app.handlers import persistent
from mathutils import Vector    # for creating texture in mouse position
from bpy.props import FloatVectorProperty       # for creating texture in mouse position

from bpy.utils import resource_path   # import nodegroup
from pathlib import Path  #paint_from_library(bpy.types.Operator)
import os        # import nodegroup and export point cache orenloop #export_and_relink_obj    >#orenscatterinstancesmodifiers    >ALSO: secret_menu  +

import addon_utils  #activate addon cell fracture AND #to find the path to the addon

from collections import  defaultdict #linked scene duplicate collections  orenSceneLinkFunction

import math #square root of temp empty p      ALSO   round temp resolution quick rendering ALSO math.sqrt(surface_area / (4 * math.pi))

# from os.path import dirname, join, normpath   # for framerate presets in performance capture
# from bpy.app import binary_path_python        # for framerate presets in performance capture

from mathutils import Matrix   #apply transformations at low level

#asset browser export asset, find library name
from bpy.types import Header, Panel, Menu, UIList #necessary for pie menu
from bpy_extras import (asset_utils,)

import bpy, os  #import images from folder  import_images_from_folder


import bpy_extras  #compositor_obj_tracker
import mathutils
import blf
import gpu

import datetime  #orenquickrender(bpy.types.Operator)
import time


from bpy_extras import view3d_utils  #class orenscatter_modal_operator(bpy.types.Operator):
from bpy.types import Operator
from gpu_extras.batch import batch_for_shader



import bpy.types  #SelectObjectOperator(bpy.types.Operator)   orenpaint siblings
from bpy.props import StringProperty

import subprocess   #marvelousexport(bpy.types.Operator)
import threading #avoid freezing blender when launching marvelous
# import os #necessary, but already imported
import ctypes
import platform
import shutil  #duplicate a file to new directory
# import clipboard #copy path to clipboard

import bmesh  #orenbakeimport_objs_from_scanfolder(bpy.types.Operator)
import re
import json
import numpy     #parent to closest bone
from importlib import import_module
from mathutils.bvhtree import BVHTree

blender_version = bpy.app.version_string

auto_updater_status = True
addon_path=[]
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":  # if mod.bl_info.get("name") == "Secret Paint":
        addon_path = os.path.dirname(mod.__file__)
        # if "extensions" not in addon_path:
        #     # from . import addon_updater_ops
        #     auto_updater_status = False
        break


def _secret_paint_source_blend_filename():
    if blender_version < "4.1":
        return "Secret Paint 4.0 and older.blend"
    if blender_version < "4.2.0":
        return "Secret Paint 4.1.blend"
    if blender_version < "4.2.1":
        return "Secret Paint 4.2.0.blend"
    return "Secret Paint.blend"


def _secret_paint_source_blend_path():
    filename = _secret_paint_source_blend_filename()
    candidate_dirs = [
        Path(resource_path('USER')) / "scripts" / "addons" / "Secret Paint",
    ]
    if addon_path:
        candidate_dirs.append(Path(addon_path))

    for candidate_dir in candidate_dirs:
        candidate_path = candidate_dir / filename
        if candidate_path.is_file():
            return str(candidate_path)

    return str(candidate_dirs[0] / filename)


_SIDE_PANEL_COUNT_CACHE = {}
_SIDE_PANEL_COUNT_CACHE_LOCK = threading.Lock()
_SIDE_PANEL_COUNT_CACHE_VERSION = 0
_SIDE_PANEL_LAYOUT_CACHE = {}
_SIDE_PANEL_LAYOUT_CACHE_VERSION = 0
_SIDE_PANEL_BIOME_RENAME_CURSOR = {
    "active": False,
    "anchor_name": "",
    "biome_number": 0,
    "visible": True,
    "timer_running": False,
}
SECRET_PAINT_PANEL_ORDER_PROP = "secret_paint_panel_order"
SECRET_PAINT_BIOME_PANEL_PREFIX = "secret_paint_biome_panel"
SECRET_PAINT_PANEL_DRAG_ROW_PIXELS = 18
SECRET_PAINT_PANEL_REORDER_DEADZONE_ROWS = 0.35
SECRET_PAINT_PANEL_BIOME_BOUNDARY_SNAP_ROWS = 0.45
SECRET_PAINT_PANEL_REORDER_PAINT_ROW_SCALE = 0.92
SECRET_PAINT_PANEL_REORDER_BIOME_HEADER_ROWS = 1.15 / SECRET_PAINT_PANEL_REORDER_PAINT_ROW_SCALE
SECRET_PAINT_PANEL_REORDER_BIOME_GAP_ROWS = 0.75
SECRET_PAINT_PANEL_ACTION_STRIP_UNITS = 6.0
SECRET_PAINT_PANEL_ACTION_SLOT_UNITS = 1.0
SECRET_PAINT_PANEL_SELECT_PROP = "secret_paint_panel_select"
SECRET_PAINT_PANEL_APPLY_PROP = "secret_paint_panel_apply_paint"
SECRET_PAINT_PANEL_PROCEDURAL_PROP = "secret_paint_panel_procedural"
SECRET_PAINT_PANEL_VERTEX_PROP = "secret_paint_panel_vertex_mask"
SECRET_PAINT_PANEL_RENDER_PROP = "secret_paint_panel_render_hidden"
SECRET_PAINT_PANEL_BOUNDS_PROP = "secret_paint_panel_display_bounds"
SECRET_PAINT_PANEL_MASK_PROP = "secret_paint_panel_viewport_mask"
SECRET_PAINT_WORLD_DENSITY_SPACING_PROP = "secret_paint_density_spacing"
SECRET_PAINT_PANEL_CHAIN_PROPS = (
    SECRET_PAINT_PANEL_SELECT_PROP,
    SECRET_PAINT_PANEL_APPLY_PROP,
    SECRET_PAINT_PANEL_PROCEDURAL_PROP,
    SECRET_PAINT_PANEL_VERTEX_PROP,
    SECRET_PAINT_PANEL_RENDER_PROP,
    SECRET_PAINT_PANEL_BOUNDS_PROP,
    SECRET_PAINT_PANEL_MASK_PROP,
)
SECRET_PAINT_BRUSH_SIZE_TRACE_PATH = None
SECRET_PAINT_BRUSH_SIZE_TRACE_ENABLED = False


def _secret_paint_trace_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    try:
        if hasattr(value, "name"):
            return getattr(value, "name", "")
    except Exception:
        pass
    try:
        return repr(value)
    except Exception:
        return str(type(value).__name__)


def _secret_paint_trace_brush_state(brush):
    if brush is None:
        return None
    state = {"name": getattr(brush, "name", "")}
    for prop_name in (
        "size",
        "use_locked_size",
        "unprojected_size",
        "strength",
    ):
        if not hasattr(brush, prop_name):
            continue
        try:
            state[prop_name] = _secret_paint_trace_value(getattr(brush, prop_name))
        except Exception:
            pass
    return state


def _secret_paint_trace_unified_state(context):
    try:
        curves_sculpt = context.scene.tool_settings.curves_sculpt
    except Exception:
        return None
    unified = getattr(curves_sculpt, "unified_paint_settings", None)
    if unified is None:
        return None
    state = {}
    for prop_name in (
        "use_unified_size",
        "size",
        "use_locked_size",
        "unprojected_size",
    ):
        if not hasattr(unified, prop_name):
            continue
        try:
            state[prop_name] = _secret_paint_trace_value(getattr(unified, prop_name))
        except Exception:
            pass
    return state


def _secret_paint_trace_operator_state(operator):
    if operator is None:
        return None
    state = {}
    for attr_name in (
        "tool_id",
        "adjust_mode",
        "brush_radius_setting",
        "brush_radius",
        "density_spacing",
        "_native_density_adjust_passthrough",
        "_native_density_adjust_confirm_on_release",
        "_native_density_adjust_confirm_pending",
        "_native_density_pending_adjust_mode",
        "_native_density_adjust_sync_token",
        "_native_size_adjust_commit_token",
        "_native_density_adjust_release_watch_running",
        "_native_density_adjust_release_watch_saw_shortcut_down",
        "_native_density_adjust_finalizing",
        "_native_density_stroke_erase",
        "_density_right_delete_button_down",
        "stroke_active",
    ):
        if not hasattr(operator, attr_name):
            continue
        try:
            state[attr_name] = _secret_paint_trace_value(getattr(operator, attr_name))
        except Exception:
            pass
    return state


def secret_paint_brush_size_trace_reset(reason=""):
    if not SECRET_PAINT_BRUSH_SIZE_TRACE_ENABLED or not SECRET_PAINT_BRUSH_SIZE_TRACE_PATH:
        return None
    try:
        with open(SECRET_PAINT_BRUSH_SIZE_TRACE_PATH, "w", encoding="utf-8") as trace_file:
            trace_file.write("Secret Paint brush size confirm trace\n")
            trace_file.write(f"path={SECRET_PAINT_BRUSH_SIZE_TRACE_PATH}\n")
            trace_file.write(f"reset_reason={reason}\n")
    except Exception:
        pass
    return None


def secret_paint_brush_size_trace_log(label, context=None, operator=None, brush=None, **details):
    if not SECRET_PAINT_BRUSH_SIZE_TRACE_ENABLED or not SECRET_PAINT_BRUSH_SIZE_TRACE_PATH:
        return None
    try:
        context = context or bpy.context
    except Exception:
        context = None
    try:
        if brush is None and context is not None:
            curves_sculpt = getattr(getattr(context, "tool_settings", None), "curves_sculpt", None)
            if curves_sculpt is None:
                curves_sculpt = getattr(getattr(getattr(context, "scene", None), "tool_settings", None), "curves_sculpt", None)
            brush = getattr(curves_sculpt, "brush", None) if curves_sculpt is not None else None
    except Exception:
        brush = brush
    row = {
        "time": datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "label": label,
        "context_mode": getattr(context, "mode", "") if context is not None else "",
        "active_object": getattr(getattr(context, "active_object", None), "name", "") if context is not None else "",
        "operator": _secret_paint_trace_operator_state(operator),
        "brush": _secret_paint_trace_brush_state(brush),
        "unified": _secret_paint_trace_unified_state(context) if context is not None else None,
        "details": {
            str(key): _secret_paint_trace_value(value)
            for key, value in details.items()
        },
    }
    try:
        with open(SECRET_PAINT_BRUSH_SIZE_TRACE_PATH, "a", encoding="utf-8") as trace_file:
            trace_file.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    except Exception:
        pass
    return None
SECRET_PAINT_PANEL_DRAG_RESTORE_SOCKETS = (
    "Socket_0",
    "Socket_2",
    "Socket_3",
    "Socket_4",
    "Socket_5",
    "Socket_6",
    "Socket_8",
    "Socket_15",
)
_SIDE_PANEL_DRAG_OBJECT_NAME = ""
_SECRET_PAINT_PANEL_BOUNDS_LAST_UPDATE_TIME = 0.0
_SECRET_PAINT_PANEL_ACTION_LAST_UPDATE_TIMES = {}
_SECRET_PAINT_PANEL_DEFERRED_APPLY_NAMES = []
_SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING = False
_SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_VALUES = {}
_SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING = False
_SECRET_PAINT_PANEL_DEFERRED_VERTEX_REQUESTS = []
_SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING = False
_SECRET_PAINT_SCULPT_CAGE_HIDDEN = False
_SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING = False
SECRET_PAINT_DENSITY_BRUSH_ASSET_NAME = "SP Density"
SECRET_PAINT_CURVES_BRUSH_ASSET_SPECS = (
    ("DENSITY", SECRET_PAINT_DENSITY_BRUSH_ASSET_NAME),
    ("GROW_SHRINK", "SP Scale"),
    ("SLIDE", "SP Slide"),
    ("ADD", "SP Add"),
    ("COMB", "SP Comb"),
    ("SELECTION_PAINT", "SP Select"),
    ("DELETE", "SP Delete"),
)
SECRET_PAINT_CURVES_BRUSH_ASSET_NAMES_BY_TYPE = dict(SECRET_PAINT_CURVES_BRUSH_ASSET_SPECS)
SECRET_PAINT_CURVES_BRUSH_DEFAULT_FALLOFF_SHAPE = 'PROJECTED'
SECRET_PAINT_CURVES_BRUSH_FALLOFF_INITIALIZED_PROP = "secret_paint_falloff_shape_initialized"
SECRET_PAINT_OBJECT_SIZE_DENSITY_MULTIPLIER_DEFAULT = 4.0
SECRET_PAINT_NATIVE_CURVES_TOOL_IDS_BY_TYPE = {
    "DENSITY": ("builtin_brush.density", "builtin_brush.Density"),
    "ADD": ("builtin_brush.add", "builtin_brush.Add"),
    "SELECTION_PAINT": ("builtin_brush.selection_paint", "builtin_brush.Selection Paint"),
    "GROW_SHRINK": ("builtin_brush.grow_shrink", "builtin_brush.Grow / Shrink"),
    "SLIDE": ("builtin_brush.slide", "builtin_brush.Slide"),
    "COMB": ("builtin_brush.comb", "builtin_brush.Comb"),
    "DELETE": ("builtin_brush.delete", "builtin_brush.Delete"),
}
SECRET_PAINT_NATIVE_CURVES_ESSENTIAL_BRUSH_ASSET_NAMES_BY_TYPE = {
    "ADD": "Add",
    "SELECTION_PAINT": "Select",
    "GROW_SHRINK": "Grow/Shrink",
    "SLIDE": "Slide",
    "COMB": "Comb",
    "DELETE": "Delete",
}


def secret_paint_blender_version_at_least(major, minor=0, patch=0):
    return tuple(bpy.app.version) >= (major, minor, patch)


def secret_paint_curves_brush_type(brush):
    if brush is None:
        return ""
    try:
        if secret_paint_blender_version_at_least(5, 0, 0) and hasattr(brush, "curves_sculpt_brush_type"):
            return brush.curves_sculpt_brush_type
        if hasattr(brush, "curves_sculpt_tool"):
            return brush.curves_sculpt_tool
    except Exception:
        return ""
    return ""


def secret_paint_set_curves_brush_type(brush, brush_type):
    if brush is None:
        return False
    try:
        if secret_paint_blender_version_at_least(5, 0, 0) and hasattr(brush, "curves_sculpt_brush_type"):
            brush.curves_sculpt_brush_type = brush_type
        elif hasattr(brush, "curves_sculpt_tool"):
            brush.curves_sculpt_tool = brush_type
        else:
            return False
        if hasattr(brush, "use_paint_sculpt_curves"):
            brush.use_paint_sculpt_curves = True
        return True
    except Exception:
        return False


def secret_paint_is_curves_brush_type(brush, brush_type):
    if brush is None:
        return False
    if hasattr(brush, "use_paint_sculpt_curves"):
        try:
            if not brush.use_paint_sculpt_curves:
                return False
        except Exception:
            pass
    return secret_paint_curves_brush_type(brush) == brush_type


def secret_paint_uses_curves_brush_assets():
    return secret_paint_blender_version_at_least(5, 1, 0)


def secret_paint_uses_density_brush_asset():
    return secret_paint_uses_curves_brush_assets()


def secret_paint_curves_brush_asset_name(brush_type):
    return SECRET_PAINT_CURVES_BRUSH_ASSET_NAMES_BY_TYPE.get(brush_type, "")


def _secret_paint_clear_managed_brush_asset_flag(brush):
    if brush is None:
        return
    try:
        if getattr(brush, "asset_data", None) is not None:
            brush.asset_clear()
    except Exception:
        pass


def secret_paint_brush_supports_falloff_shape(brush):
    return brush is not None and hasattr(brush, "falloff_shape")


def secret_paint_ensure_default_curves_brush_falloff(brush, *, force=False):
    if not secret_paint_brush_supports_falloff_shape(brush):
        return brush
    initialized = False
    try:
        initialized = bool(brush.get(SECRET_PAINT_CURVES_BRUSH_FALLOFF_INITIALIZED_PROP, False))
    except Exception:
        initialized = False
    if force or not initialized:
        try:
            brush.falloff_shape = SECRET_PAINT_CURVES_BRUSH_DEFAULT_FALLOFF_SHAPE
        except Exception:
            pass
    try:
        brush[SECRET_PAINT_CURVES_BRUSH_FALLOFF_INITIALIZED_PROP] = True
    except Exception:
        pass
    return brush


def secret_paint_set_curves_brush_falloff_shape(brush, falloff_shape):
    if not secret_paint_brush_supports_falloff_shape(brush):
        return False
    if falloff_shape not in {'SPHERE', 'PROJECTED'}:
        return False
    try:
        brush.falloff_shape = falloff_shape
        brush[SECRET_PAINT_CURVES_BRUSH_FALLOFF_INITIALIZED_PROP] = True
        return True
    except Exception:
        return False


def secret_paint_density_minimum_distance(context=None, activeobj=None):
    obj = activeobj
    if obj is None:
        try:
            obj = context.object if context is not None else bpy.context.object
        except Exception:
            obj = None
    if obj is None:
        return 0.1
    try:
        value = obj.get(SECRET_PAINT_WORLD_DENSITY_SPACING_PROP, None)
        if value is not None:
            return float(value)
    except Exception:
        pass
    curves_data = getattr(obj, "data", None)
    if curves_data is not None:
        try:
            value = curves_data.get(SECRET_PAINT_WORLD_DENSITY_SPACING_PROP, None)
            if value is not None:
                return float(value)
        except Exception:
            pass
    try:
        if obj.modifiers and obj.modifiers[0]:
            return obj.modifiers[0]["Socket_11"]
    except Exception:
        pass
    return 0.1


def secret_paint_apply_density_minimum_distance_to_brush(
    brush,
    context=None,
    activeobj=None,
    spacing=None,
    *,
    density_mode='AUTO',
):
    if not secret_paint_is_curves_brush_type(brush, 'DENSITY'):
        return False
    settings = getattr(brush, "curves_sculpt_settings", None)
    if settings is None:
        return False
    try:
        minimum_distance = (
            float(spacing)
            if spacing is not None
            else float(secret_paint_density_minimum_distance(context, activeobj))
        )
    except Exception:
        return False
    if minimum_distance <= 0.0:
        return False

    changed = False
    try:
        settings.minimum_distance = minimum_distance
        changed = True
    except Exception:
        pass
    if density_mode is not None:
        try:
            settings.density_mode = density_mode
            changed = True
        except Exception:
            pass
    return changed


def secret_paint_store_active_density_brush_spacing(context=None, activeobj=None):
    context = context or bpy.context
    obj = activeobj
    if obj is None:
        try:
            obj = context.active_object
        except Exception:
            obj = None
    modifier = _secret_paint_system_modifier(obj)
    if modifier is None:
        return False

    curves_sculpt = _secret_paint_curves_sculpt_settings(context)
    brush = getattr(curves_sculpt, "brush", None) if curves_sculpt is not None else None
    if not secret_paint_is_curves_brush_type(brush, 'DENSITY'):
        return False

    settings = getattr(brush, "curves_sculpt_settings", None)
    if settings is None:
        return False
    try:
        minimum_distance = float(getattr(settings, "minimum_distance"))
    except Exception:
        return False
    if minimum_distance <= 0.0:
        return False

    try:
        modifier["Socket_11"] = minimum_distance
    except Exception:
        return False

    return True


def _secret_paint_set_curves_interpolation_settings(settings, enabled=True, point_count=False):
    if settings is None:
        return
    try:
        if secret_paint_blender_version_at_least(4, 2, 0):
            settings.use_length_interpolate = enabled
            settings.use_shape_interpolate = enabled
            settings.use_point_count_interpolate = point_count
        else:
            settings.interpolate_length = enabled
            settings.interpolate_shape = enabled
            settings.interpolate_point_count = point_count
    except Exception:
        pass


def secret_paint_configure_density_brush(brush, context=None, activeobj=None, *, override_settings=False, size=None):
    if brush is None:
        return None
    secret_paint_set_curves_brush_type(brush, 'DENSITY')
    secret_paint_ensure_default_curves_brush_falloff(brush)
    if size is not None:
        old_size = getattr(brush, "size", None) if hasattr(brush, "size") else None
        secret_paint_brush_size_trace_log(
            "shared.configure_density_brush.size_write.before",
            context,
            brush=brush,
            requested_size=size,
            old_size=old_size,
            activeobj=activeobj,
            override_settings=override_settings,
        )
        try:
            brush.size = int(size)
        except Exception:
            pass
        secret_paint_brush_size_trace_log(
            "shared.configure_density_brush.size_write.after",
            context,
            brush=brush,
            requested_size=size,
            old_size=old_size,
            new_size=getattr(brush, "size", None) if hasattr(brush, "size") else None,
        )
    settings = getattr(brush, "curves_sculpt_settings", None)
    if settings is None:
        return brush
    secret_paint_apply_density_minimum_distance_to_brush(
        brush,
        context,
        activeobj,
        density_mode=None,
    )
    _secret_paint_set_curves_interpolation_settings(settings, enabled=True, point_count=False)
    try:
        settings.curve_length = 0.32
        settings.points_per_curve = 2
    except Exception:
        pass
    if override_settings:
        try:
            settings.density_mode = 'AUTO'
        except Exception:
            pass
        try:
            brush.strength = 1
        except Exception:
            pass
        try:
            if secret_paint_blender_version_at_least(5, 0, 0) and hasattr(brush, "curve_distance_falloff_preset"):
                brush.curve_distance_falloff_preset = 'SMOOTHER'
            elif hasattr(brush, "curve_preset"):
                brush.curve_preset = 'SMOOTHER'
        except Exception:
            pass
        try:
            if settings.density_add_attempts <= 100:
                settings.density_add_attempts = 3000
        except Exception:
            pass
    return brush


def secret_paint_configure_curves_brush_asset(brush, brush_type, context=None, activeobj=None, *, override_settings=False, size=None):
    if brush is None:
        return None
    if brush_type == 'DENSITY':
        return secret_paint_configure_density_brush(
            brush,
            context,
            activeobj,
            override_settings=override_settings,
            size=size,
        )
    secret_paint_set_curves_brush_type(brush, brush_type)
    secret_paint_ensure_default_curves_brush_falloff(brush)
    if size is not None:
        old_size = getattr(brush, "size", None) if hasattr(brush, "size") else None
        secret_paint_brush_size_trace_log(
            "shared.configure_curves_brush_asset.size_write.before",
            context,
            brush=brush,
            brush_type=brush_type,
            requested_size=size,
            old_size=old_size,
            activeobj=activeobj,
            override_settings=override_settings,
        )
        try:
            brush.size = int(size)
        except Exception:
            pass
        secret_paint_brush_size_trace_log(
            "shared.configure_curves_brush_asset.size_write.after",
            context,
            brush=brush,
            brush_type=brush_type,
            requested_size=size,
            old_size=old_size,
            new_size=getattr(brush, "size", None) if hasattr(brush, "size") else None,
        )

    settings = getattr(brush, "curves_sculpt_settings", None)
    if brush_type == 'ADD' and settings is not None:
        try:
            settings.add_amount = 1
        except Exception:
            pass
        _secret_paint_set_curves_interpolation_settings(settings, enabled=True, point_count=False)
        try:
            settings.curve_length = 0.32
            settings.points_per_curve = 2
        except Exception:
            pass
        try:
            brush.use_frontface = True
        except Exception:
            pass
    elif brush_type == 'GROW_SHRINK' and settings is not None:
        try:
            if secret_paint_blender_version_at_least(4, 2, 0):
                settings.use_uniform_scale = True
            else:
                settings.scale_uniform = True
        except Exception:
            pass

    if override_settings:
        if brush_type == 'GROW_SHRINK':
            try:
                brush.strength = 0.03
            except Exception:
                pass
        elif brush_type == 'COMB':
            try:
                brush.strength = 0.1
            except Exception:
                pass
    return brush


def secret_paint_ensure_sp_curves_brush_asset(brush_type, context=None, activeobj=None, *, configure=True, override_settings=False, size=150):
    if not secret_paint_uses_curves_brush_assets():
        return None
    secret_paint_brush_size_trace_log(
        "shared.ensure_sp_curves_brush_asset.enter",
        context,
        brush_type=brush_type,
        activeobj=activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
    )
    asset_name = secret_paint_curves_brush_asset_name(brush_type)
    if not asset_name:
        return None
    brush = None
    try:
        for candidate in bpy.data.brushes:
            if candidate.name == asset_name and getattr(candidate, "library", None) is None:
                brush = candidate
                break
    except Exception:
        brush = None
    if brush is None:
        try:
            brush = bpy.data.brushes.new(asset_name, mode="SCULPT_CURVES")
        except Exception:
            return None
    if not secret_paint_set_curves_brush_type(brush, brush_type):
        return None
    if configure:
        secret_paint_configure_curves_brush_asset(
            brush,
            brush_type,
            context,
            activeobj,
            override_settings=override_settings,
            size=size,
        )
    _secret_paint_clear_managed_brush_asset_flag(brush)
    return brush


def secret_paint_ensure_sp_curves_brush_assets(context=None, activeobj=None, *, configure=True, override_settings=False, size=150):
    brushes = {}
    if not secret_paint_uses_curves_brush_assets():
        return brushes
    secret_paint_brush_size_trace_log(
        "shared.ensure_sp_curves_brush_assets.enter",
        context,
        activeobj=activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
    )
    for brush_type, _asset_name in SECRET_PAINT_CURVES_BRUSH_ASSET_SPECS:
        brush = secret_paint_ensure_sp_curves_brush_asset(
            brush_type,
            context,
            activeobj,
            configure=configure,
            override_settings=override_settings,
            size=size,
        )
        if brush is not None:
            brushes[brush_type] = brush
    return brushes


def secret_paint_ensure_sp_density_brush_asset(context=None, activeobj=None, *, configure=True, override_settings=False, size=150):
    return secret_paint_ensure_sp_curves_brush_asset(
        'DENSITY',
        context,
        activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
    )


def secret_paint_activate_sp_curves_brush_asset(brush_type, context=None, activeobj=None, *, configure=True, override_settings=False, size=150):
    brush = secret_paint_ensure_sp_curves_brush_asset(
        brush_type,
        context,
        activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
    )
    if brush is None:
        return None
    _secret_paint_clear_managed_brush_asset_flag(brush)
    context = context or bpy.context
    _secret_paint_set_curves_workspace_tool(context, brush_type)
    if _secret_paint_assign_curves_sculpt_brush(context, brush, activeobj=activeobj):
        return brush
    return None


def secret_paint_activate_sp_density_brush_asset(context=None, activeobj=None, *, configure=True, override_settings=False, size=150):
    return secret_paint_activate_sp_curves_brush_asset(
        'DENSITY',
        context,
        activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
    )


def _secret_paint_operator_result_ok(result):
    return bool(result) and 'CANCELLED' not in result


def _secret_paint_view3d_context_data(context=None):
    context = context or bpy.context

    def area_data(window, screen, area):
        if area is None or getattr(area, "type", "") != 'VIEW_3D':
            return None
        space = area.spaces.active if getattr(area, "spaces", None) else None
        if space is None or getattr(space, "type", "") != 'VIEW_3D':
            return None
        region = None
        for candidate in getattr(area, "regions", []):
            if getattr(candidate, "type", "") == 'WINDOW':
                region = candidate
                break
        if region is None:
            return None
        return window, screen, area, region, space

    data = area_data(
        getattr(context, "window", None),
        getattr(context, "screen", None),
        getattr(context, "area", None),
    )
    if data is not None:
        return data

    window = getattr(context, "window", None)
    screen = getattr(context, "screen", None)
    if screen is not None:
        for area in screen.areas:
            data = area_data(window, screen, area)
            if data is not None:
                return data

    window_manager = getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return None
    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            data = area_data(window, screen, area)
            if data is not None:
                return data
    return None


def _secret_paint_call_view3d_operator(context, callback):
    context = context or bpy.context
    data = _secret_paint_view3d_context_data(context)
    if data is None:
        return callback()
    window, screen, area, region, space = data
    override = {
        "area": area,
        "region": region,
        "space_data": space,
    }
    if window is not None:
        override["window"] = window
    if screen is not None:
        override["screen"] = screen
    with context.temp_override(**override):
        return callback()


def _secret_paint_tag_redraw_view3d_areas(context=None):
    seen = set()

    def tag_screen(screen):
        if screen is None:
            return
        for area in screen.areas:
            if getattr(area, "type", "") != 'VIEW_3D':
                continue
            try:
                pointer = area.as_pointer()
            except Exception:
                pointer = id(area)
            if pointer in seen:
                continue
            seen.add(pointer)
            try:
                area.tag_redraw()
            except Exception:
                pass

    context = context or bpy.context
    tag_screen(getattr(context, "screen", None))
    window_manager = getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return
    for window in window_manager.windows:
        tag_screen(getattr(window, "screen", None))


def _secret_paint_curves_sculpt_settings(context=None):
    try:
        return (context or bpy.context).tool_settings.curves_sculpt
    except Exception:
        try:
            return bpy.context.tool_settings.curves_sculpt
        except Exception:
            return None


def _secret_paint_set_curves_workspace_tool(context=None, brush_type='DENSITY'):
    context = context or bpy.context
    for tool_id in SECRET_PAINT_NATIVE_CURVES_TOOL_IDS_BY_TYPE.get(brush_type, ()):
        try:
            result = _secret_paint_call_view3d_operator(
                context,
                lambda tool_id=tool_id: bpy.ops.wm.tool_set_by_id(name=tool_id),
            )
            if _secret_paint_operator_result_ok(result):
                return True
        except Exception:
            continue
    try:
        result = _secret_paint_call_view3d_operator(
            context,
            lambda: bpy.ops.wm.tool_set_by_brush_type(brush_type=brush_type),
        )
        if _secret_paint_operator_result_ok(result):
            return True
    except Exception:
        pass
    if brush_type != 'DENSITY':
        try:
            result = _secret_paint_call_view3d_operator(
                context,
                lambda: bpy.ops.wm.tool_set_by_id(name="builtin.brush"),
            )
            if _secret_paint_operator_result_ok(result):
                return True
        except Exception:
            pass
    return False


def _secret_paint_set_density_workspace_tool(context=None):
    return _secret_paint_set_curves_workspace_tool(context, 'DENSITY')


def secret_paint_set_native_curves_workspace_tool(brush_type, context=None):
    return _secret_paint_set_curves_workspace_tool(context, brush_type)


def secret_paint_activate_essential_curves_brush_asset(brush_type, context=None):
    asset_name = SECRET_PAINT_NATIVE_CURVES_ESSENTIAL_BRUSH_ASSET_NAMES_BY_TYPE.get(brush_type)
    if not asset_name:
        return None
    context = context or bpy.context
    relative_identifier = f"brushes/essentials_brushes-curve_sculpt.blend/Brush/{asset_name}"

    try:
        result = _secret_paint_call_view3d_operator(
            context,
            lambda: bpy.ops.brush.asset_activate(
                asset_library_type='ESSENTIALS',
                relative_asset_identifier=relative_identifier,
            ),
        )
    except Exception:
        return None
    if not _secret_paint_operator_result_ok(result):
        return None

    curves_sculpt = _secret_paint_curves_sculpt_settings(context)
    active_brush = getattr(curves_sculpt, "brush", None) if curves_sculpt is not None else None
    return active_brush if secret_paint_is_curves_brush_type(active_brush, brush_type) else None


def _secret_paint_assign_curves_sculpt_brush(context, brush, activeobj=None):
    curves_sculpt = _secret_paint_curves_sculpt_settings(context)
    if curves_sculpt is None or brush is None:
        return False
    if activeobj is None:
        try:
            activeobj = context.active_object
        except Exception:
            activeobj = None
    brush_type = secret_paint_curves_brush_type(brush)
    if brush_type == 'DENSITY':
        secret_paint_apply_density_minimum_distance_to_brush(
            brush,
            context,
            activeobj,
        )

    for prop_name in ("show_brush", "show_brush_on_surface"):
        if hasattr(curves_sculpt, prop_name):
            try:
                setattr(curves_sculpt, prop_name, True)
            except Exception:
                pass

    try:
        curves_sculpt.brush = brush
    except Exception:
        return False
    try:
        active_brush = curves_sculpt.brush
        if brush_type == 'DENSITY':
            secret_paint_apply_density_minimum_distance_to_brush(
                active_brush,
                context,
                activeobj,
            )
        return (
            active_brush == brush or
            (
                active_brush is not None and
                getattr(active_brush, "name", "") == getattr(brush, "name", "") and
                secret_paint_curves_brush_type(active_brush) == secret_paint_curves_brush_type(brush)
            )
        )
    except Exception:
        return True


def secret_paint_activate_native_curves_brush(brush_type, context=None, activeobj=None, *, configure=True, override_settings=False, size=150, defer=False):
    context = context or bpy.context
    secret_paint_brush_size_trace_log(
        "shared.activate_native_curves_brush.enter",
        context,
        brush_type=brush_type,
        activeobj=activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
        defer=defer,
    )
    brush = secret_paint_ensure_sp_curves_brush_asset(
        brush_type,
        context,
        activeobj,
        configure=configure,
        override_settings=override_settings,
        size=size,
    )
    if brush is None:
        return None

    tool_ok = _secret_paint_set_curves_workspace_tool(context, brush_type)
    native_asset_brush = (
        secret_paint_activate_essential_curves_brush_asset(brush_type, context)
        if brush_type != 'DENSITY'
        else None
    )
    if native_asset_brush is not None:
        _secret_paint_tag_redraw_view3d_areas(context)
        return native_asset_brush

    asset_brush = None
    try:
        asset_brush = secret_paint_activate_sp_curves_brush_asset(
            brush_type,
            context,
            activeobj,
            configure=False,
            override_settings=False,
            size=None,
        )
    except Exception:
        asset_brush = None
    if asset_brush is not None:
        brush = asset_brush
    brush_ok = _secret_paint_assign_curves_sculpt_brush(context, brush, activeobj=activeobj)
    if tool_ok:
        brush_ok = _secret_paint_assign_curves_sculpt_brush(context, brush, activeobj=activeobj) or brush_ok
    _secret_paint_tag_redraw_view3d_areas(context)

    if defer:
        brush_name = brush.name
        activeobj_name = activeobj.name if activeobj is not None else ""

        def _refresh_native_cursor():
            try:
                if bpy.context.mode != 'SCULPT_CURVES':
                    return None
                if activeobj_name:
                    active = bpy.context.active_object
                    if active is None or active.name != activeobj_name:
                        return None
                deferred_brush = bpy.data.brushes.get(brush_name)
                if deferred_brush is not None:
                    secret_paint_brush_size_trace_log(
                        "shared.activate_native_curves_brush.deferred_assign",
                        bpy.context,
                        brush=deferred_brush,
                        brush_type=brush_type,
                    )
                    _secret_paint_set_curves_workspace_tool(bpy.context, brush_type)
                    _secret_paint_assign_curves_sculpt_brush(
                        bpy.context,
                        deferred_brush,
                        activeobj=bpy.context.active_object,
                    )
                    _secret_paint_tag_redraw_view3d_areas(bpy.context)
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(_refresh_native_cursor, first_interval=0.01)
        except Exception:
            pass

    return brush if brush_ok else None


def _secret_paint_activate_density_brush_cursor(context, brush, activeobj=None, *, defer=False):
    if brush is None:
        return False
    context = context or bpy.context
    if not secret_paint_is_curves_brush_type(brush, 'DENSITY'):
        secret_paint_set_curves_brush_type(brush, 'DENSITY')

    tool_ok = _secret_paint_set_curves_workspace_tool(context, 'DENSITY')
    brush_ok = _secret_paint_assign_curves_sculpt_brush(context, brush, activeobj=activeobj)
    if tool_ok:
        brush_ok = _secret_paint_assign_curves_sculpt_brush(context, brush, activeobj=activeobj) or brush_ok
    _secret_paint_tag_redraw_view3d_areas(context)

    if defer:
        brush_name = brush.name
        activeobj_name = activeobj.name if activeobj is not None else ""

        def _refresh_density_cursor():
            try:
                if bpy.context.mode != 'SCULPT_CURVES':
                    return None
                if activeobj_name:
                    active = bpy.context.active_object
                    if active is None or active.name != activeobj_name:
                        return None
                deferred_brush = bpy.data.brushes.get(brush_name)
                if deferred_brush is not None:
                    _secret_paint_activate_density_brush_cursor(
                        bpy.context,
                        deferred_brush,
                        bpy.context.active_object,
                        defer=False,
                    )
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(_refresh_density_cursor, first_interval=0.01)
        except Exception:
            pass

    return tool_ok and brush_ok


def _clear_side_panel_count_cache(reason="manual"):
    global _SIDE_PANEL_COUNT_CACHE_VERSION, _SIDE_PANEL_LAYOUT_CACHE_VERSION
    try:
        with _SIDE_PANEL_COUNT_CACHE_LOCK:
            _SIDE_PANEL_COUNT_CACHE.clear()
            _SIDE_PANEL_LAYOUT_CACHE.clear()
            _SIDE_PANEL_COUNT_CACHE_VERSION += 1
            _SIDE_PANEL_LAYOUT_CACHE_VERSION += 1
    except Exception:
        pass


def _format_side_panel_instance_count_label(n_of_instances):
    if n_of_instances >= 1000:
        return f"{n_of_instances // 1000}.{(n_of_instances % 1000) // 100}k"
    return f"0.{n_of_instances // 100}k"


def _compute_side_panel_instance_count(sibling):
    try:
        modifier = sibling.modifiers[0]
        n_of_instances = 0
        if modifier["Input_69"] == False:
            n_of_instances = len(sibling.data.curves)
        elif modifier["Input_68"] > 0 and sibling.parent and getattr(sibling.parent, "data", None):
            spacing = (modifier["Input_68"] ** 0.5) * modifier["Input_100"]
            if spacing > 0:
                density_square = (1 / spacing) ** 2
                total_area = sum(face.area for face in sibling.parent.data.polygons)
                n_of_instances = int(total_area / density_square * modifier["Input_72"] / 100)
        return n_of_instances, _format_side_panel_instance_count_label(n_of_instances)
    except Exception:
        return 0, "0.0k"


def _iter_secret_paint_view3d_spaces(context=None):
    seen = set()

    if context is not None:
        area = getattr(context, "area", None)
        space_data = getattr(context, "space_data", None)
        if (
            area is not None and area.type == 'VIEW_3D' and
            space_data is not None and getattr(space_data, "type", "") == 'VIEW_3D'
        ):
            try:
                pointer = space_data.as_pointer()
            except Exception:
                pointer = id(space_data)
            seen.add(pointer)
            yield space_data

    window_manager = getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return

    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != 'VIEW_3D' or not area.spaces:
                continue
            space = area.spaces.active
            if space is None or getattr(space, "type", "") != 'VIEW_3D':
                continue
            try:
                pointer = space.as_pointer()
            except Exception:
                pointer = id(space)
            if pointer in seen:
                continue
            seen.add(pointer)
            yield space


def _set_secret_paint_sculpt_curves_cage_visibility(visible, context=None):
    updated_any = False
    for space in _iter_secret_paint_view3d_spaces(context):
        overlay = getattr(space, "overlay", None)
        if overlay is None or not hasattr(overlay, "show_sculpt_curves_cage"):
            continue
        try:
            overlay.show_sculpt_curves_cage = visible
            updated_any = True
        except Exception:
            pass
    return updated_any


def _ensure_secret_paint_sculpt_cage_restore_monitor():
    global _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING
    if _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING:
        return
    _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING = True

    def _run():
        global _SECRET_PAINT_SCULPT_CAGE_HIDDEN, _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING
        try:
            context = bpy.context
            if getattr(context, "window_manager", None) is None:
                return 0.25
            world_paint_running = False
            world_paint_cage_preview_active = False
            try:
                world_paint_module = _secret_paint_world_paint_module()
                world_paint_running = world_paint_module.is_world_paint_running()
                preview_active = getattr(world_paint_module, "is_world_paint_cage_preview_active", None)
                if preview_active is not None:
                    world_paint_cage_preview_active = bool(preview_active())
            except Exception:
                pass
            if not _SECRET_PAINT_SCULPT_CAGE_HIDDEN:
                _set_secret_paint_sculpt_curves_cage_visibility(True, context=context)
                _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING = False
                return None
            if (getattr(context, "mode", "") or "") == 'SCULPT_CURVES' or world_paint_running:
                if world_paint_cage_preview_active:
                    return 0.05
                _set_secret_paint_sculpt_curves_cage_visibility(False, context=context)
                return 0.25
            _SECRET_PAINT_SCULPT_CAGE_HIDDEN = False
            _set_secret_paint_sculpt_curves_cage_visibility(True, context=context)
        except Exception:
            pass
        _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING = False
        return None

    try:
        bpy.app.timers.register(_run, first_interval=0.1)
    except Exception:
        _SECRET_PAINT_SCULPT_CAGE_MONITOR_RUNNING = False


def secret_paint_disable_sculpt_curves_cage(context=None):
    global _SECRET_PAINT_SCULPT_CAGE_HIDDEN
    _SECRET_PAINT_SCULPT_CAGE_HIDDEN = True
    _set_secret_paint_sculpt_curves_cage_visibility(False, context=context)
    _ensure_secret_paint_sculpt_cage_restore_monitor()


def secret_paint_enable_sculpt_curves_cage(context=None):
    global _SECRET_PAINT_SCULPT_CAGE_HIDDEN
    _SECRET_PAINT_SCULPT_CAGE_HIDDEN = False
    _set_secret_paint_sculpt_curves_cage_visibility(True, context=context)


def _secret_paint_q_debug_log(label, context=None, *, keymaps=True, reset=False, **fields):
    return None


def _secret_paint_panel_exit_paint_mode(context):
    was_paint_mode = (getattr(context, "mode", "") or "") == 'SCULPT_CURVES'
    _secret_paint_q_debug_log("panel_exit.enter", context, was_paint_mode=was_paint_mode)

    try:
        world_paint_module = _secret_paint_world_paint_module()
        cleanup_exit_state = getattr(world_paint_module, "cleanup_world_paint_exit_state", None)
        if cleanup_exit_state is not None:
            was_paint_mode = bool(cleanup_exit_state(context)) or was_paint_mode
            _secret_paint_q_debug_log("panel_exit.cleanup_exit_state", context, was_paint_mode=was_paint_mode)
        else:
            operator = getattr(world_paint_module, "_world_operator", lambda: None)()
            if operator is not None:
                was_paint_mode = True
                _secret_paint_q_debug_log("panel_exit.finish_operator", context)
                operator.finish_world_paint(context)
            else:
                sanitize_exit_tool = getattr(world_paint_module, "_sanitize_sculpt_curves_tool_before_world_exit", None)
                if sanitize_exit_tool is not None:
                    _secret_paint_q_debug_log("panel_exit.sanitize_only", context)
                    sanitize_exit_tool(context)
        restore_shortcuts = getattr(world_paint_module, "_set_world_paint_shortcuts_enabled", None)
        if restore_shortcuts is not None:
            restore_shortcuts(context, True)
        restore_base_paint_shortcuts = getattr(world_paint_module, "restore_base_paint_shortcuts_for_exit", None)
        if restore_base_paint_shortcuts is not None:
            restore_base_paint_shortcuts(context)
    except Exception:
        pass

    try:
        if (getattr(context, "mode", "") or "") != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    _secret_paint_q_debug_log("panel_exit.exit", context, was_paint_mode=was_paint_mode)
    return was_paint_mode


def _secret_paint_panel_clear_world_paint_object_guard():
    try:
        state = getattr(_secret_paint_world_paint_module(), "_WORLD_STATE", None)
        if state is not None:
            state["object_mode_guard_system_names"] = set()
            state["object_mode_guard_until"] = 0.0
    except Exception:
        pass


def _secret_paint_panel_is_paint_mode(context):
    if (getattr(context, "mode", "") or "") == 'SCULPT_CURVES':
        return True
    try:
        world_paint_module = _secret_paint_world_paint_module()
        is_running = getattr(world_paint_module, "is_world_paint_running", None)
        if is_running is not None:
            return bool(is_running())
        return bool(getattr(world_paint_module, "_world_operator", lambda: None)())
    except Exception:
        return False


def _secret_paint_cleanup_stale_world_paint_state(context, world_paint_module=None):
    try:
        world_paint_module = world_paint_module or _secret_paint_world_paint_module()
        if getattr(world_paint_module, "_world_operator", lambda: None)() is not None:
            return False
        exit_state_active = getattr(world_paint_module, "world_paint_exit_state_active", None)
        cleanup_exit_state = getattr(world_paint_module, "cleanup_world_paint_exit_state", None)
        if exit_state_active is None or cleanup_exit_state is None:
            return False
        if not exit_state_active(context):
            return False
        return bool(cleanup_exit_state(context))
    except Exception:
        return False


def _secret_paint_system_modifier(obj):
    if obj is None or obj.type != "CURVES" or not obj.modifiers:
        return None
    for modifier in obj.modifiers:
        node_group = getattr(modifier, "node_group", None)
        if modifier.type == 'NODES' and node_group and node_group.name.startswith("Secret Paint"):
            return modifier
    return None


def _secret_paint_system_is_procedural(obj):
    modifier = _secret_paint_system_modifier(obj)
    if modifier is None:
        return False
    try:
        return bool(modifier["Input_69"])
    except Exception:
        return False


def _secret_paint_world_paint_enabled(context):
    return bool(not _secret_paint_pref("checkboxUseLegacyQPaint", False, context))


def _secret_paint_view3d_override(context):
    context = context if context is not None else bpy.context
    context_area = getattr(context, "area", None)
    context_region = getattr(context, "region", None)
    if (
        getattr(context_area, "type", None) == 'VIEW_3D' and
        getattr(context_region, "type", None) == 'WINDOW'
    ):
        return None

    window = getattr(context, "window", None)
    screen = getattr(window, "screen", None) if window else getattr(context, "screen", None)
    if screen is None:
        return None

    view3d_areas = []
    if getattr(context_area, "type", None) == 'VIEW_3D':
        view3d_areas.append(context_area)
    view3d_areas.extend(
        area for area in screen.areas
        if area.type == 'VIEW_3D' and area != context_area
    )

    for area in view3d_areas:
        if area.type != 'VIEW_3D':
            continue
        region = next((region for region in area.regions if region.type == 'WINDOW'), None)
        if region is None:
            continue
        override = {
            "screen": screen,
            "area": area,
            "region": region,
            "space_data": area.spaces.active,
        }
        region_data = getattr(area.spaces.active, "region_3d", None)
        if region_data is not None:
            override["region_data"] = region_data
        if window is not None:
            override["window"] = window
        return override
    return None


def _secret_paint_invoke_world_paint_mode(context):
    context = context if context is not None else bpy.context
    override = _secret_paint_view3d_override(context)
    if override:
        try:
            with context.temp_override(**override):
                return bpy.ops.secret.world_paint_mode('INVOKE_DEFAULT')
        except Exception:
            pass
    return bpy.ops.secret.world_paint_mode('INVOKE_DEFAULT')


def _secret_paint_start_world_paint_for_object(context, activeobj):
    context = context if context is not None else bpy.context
    if activeobj is None:
        return {'CANCELLED'}

    try:
        if getattr(context, "mode", "") != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    try:
        reupdate_hair_material(context, objselection=[activeobj])
    except Exception:
        pass

    try:
        for selected_obj in list(context.selected_objects):
            selected_obj.select_set(False)
        activeobj.select_set(True)
        context.view_layer.objects.active = activeobj
    except Exception:
        pass

    _secret_paint_panel_clear_world_paint_object_guard()

    return _secret_paint_invoke_world_paint_mode(context)


def _secret_paint_preview_world_paint_entry_source(context, source_obj, *, hold=False, event=None):
    if source_obj is None:
        return False
    context = context if context is not None else bpy.context
    try:
        world_paint_module = _secret_paint_world_paint_module()
        try:
            if event is not None:
                world_paint_module.remember_base_paint_shortcut_release(context, event)
        except Exception:
            pass
        override = _secret_paint_view3d_override(context)
        if override:
            with context.temp_override(**override):
                return bool(world_paint_module.preview_entry_source_pick(bpy.context, source_obj, hold=hold))
        return bool(world_paint_module.preview_entry_source_pick(context, source_obj, hold=hold))
    except Exception:
        return False


def _secret_paint_schedule_world_paint_for_object(activeobj):
    if activeobj is None:
        return {'CANCELLED'}
    object_name = activeobj.name

    def start_world_paint_after_asset_import():
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            return None
        try:
            if _secret_paint_panel_switch_running_world_source(bpy.context, obj):
                return None
            world_paint_module = _secret_paint_world_paint_module()
            if getattr(world_paint_module, "_world_operator", lambda: None)() is not None:
                return None
        except Exception:
            pass
        _secret_paint_start_world_paint_for_object(bpy.context, obj)
        return None

    bpy.app.timers.register(start_world_paint_after_asset_import, first_interval=0.05)
    return {'FINISHED'}


def _secret_paint_panel_switch_running_world_source(context, activeobj):
    if (
        activeobj is None or
        _secret_paint_system_modifier(activeobj) is None or
        _secret_paint_system_is_procedural(activeobj)
    ):
        return False

    try:
        world_paint_module = _secret_paint_world_paint_module()
        operator = getattr(world_paint_module, "_world_operator", lambda: None)()
        if operator is None:
            return False
        override = _secret_paint_view3d_override(context)
        if override:
            with context.temp_override(**override):
                if not operator._switch_source_to_system(bpy.context, activeobj):
                    return False
                operator._activate_picked_source_system(bpy.context, operator.source_data)
                world_paint_module.preview_entry_source_pick(bpy.context, activeobj, hold=False)
                return True
        if not operator._switch_source_to_system(context, activeobj):
            return False
        operator._activate_picked_source_system(context, operator.source_data)
        _secret_paint_preview_world_paint_entry_source(context, activeobj, hold=False)
        return True
    except Exception:
        return False


def _side_panel_instance_count_signature(sibling):
    try:
        modifier = sibling.modifiers[0]
        parent = sibling.parent
        parent_data = getattr(parent, "data", None) if parent else None
        return (
            sibling.name,
            sibling.data.as_pointer() if getattr(sibling, "data", None) else 0,
            parent.as_pointer() if parent else 0,
            parent_data.as_pointer() if parent_data else 0,
            bool(modifier.get("Input_69", False)),
            float(modifier.get("Input_68", 0.0)),
            float(modifier.get("Input_72", 0.0)),
            float(modifier.get("Input_100", 0.0)),
        )
    except Exception:
        return None


def _get_side_panel_instance_count_cached(sibling):
    cache_key = None
    try:
        cache_key = sibling.as_pointer()
        signature = _side_panel_instance_count_signature(sibling)
    except Exception:
        signature = None

    if cache_key is not None and signature is not None:
        try:
            with _SIDE_PANEL_COUNT_CACHE_LOCK:
                cached = _SIDE_PANEL_COUNT_CACHE.get(cache_key)
            if cached and cached["signature"] == signature:
                return cached["count"], cached["label"]
        except Exception:
            pass

    n_of_instances, n_of_instances_label = _compute_side_panel_instance_count(sibling)

    if cache_key is not None and signature is not None:
        try:
            with _SIDE_PANEL_COUNT_CACHE_LOCK:
                _SIDE_PANEL_COUNT_CACHE[cache_key] = {
                    "signature": signature,
                    "count": n_of_instances,
                    "label": n_of_instances_label,
                }
        except Exception:
            pass

    return n_of_instances, n_of_instances_label


def _safe_side_panel_modifier_value(modifier, key, default=None):
    try:
        value = modifier[key]
        if value is None:
            return default
        return value
    except Exception:
        return default


def _side_panel_order_value(obj):
    try:
        return int(obj.get(SECRET_PAINT_PANEL_ORDER_PROP))
    except Exception:
        return None


def _side_panel_text_sort_key(value):
    try:
        return str(value or "").casefold()
    except Exception:
        return ""


def _side_panel_bgroup_sort_key(bgroup):
    try:
        return (0, int(bgroup))
    except Exception:
        return (1, str(bgroup))


def _side_panel_panel_token(value):
    try:
        token = str(value)
    except Exception:
        token = "unknown"
    token = re.sub(r"[^0-9A-Za-z_]+", "_", token)
    return token.strip("_") or "unknown"


def _side_panel_object_pointer_token(obj):
    if obj is None:
        return "none"
    try:
        return str(obj.as_pointer())
    except Exception:
        return _side_panel_panel_token(getattr(obj, "name", "unknown"))


def _side_panel_rna_name(value, default=""):
    if value is None:
        return default
    try:
        return value.name
    except (ReferenceError, RuntimeError):
        return default
    except Exception:
        return default


def _side_panel_rna_type(value, default=""):
    if value is None:
        return default
    try:
        return getattr(value, "type", default)
    except (ReferenceError, RuntimeError):
        return default
    except Exception:
        return default


def _side_panel_object_alive(obj):
    if obj is None:
        return False
    name = _side_panel_rna_name(obj)
    if not name:
        return False
    try:
        return bpy.data.objects.get(name) is obj
    except (ReferenceError, RuntimeError):
        return False
    except Exception:
        return True


def _side_panel_biome_panel_owner(obj, row_entries):
    parent_by_pointer = {}
    for row_entry in row_entries:
        sibling = row_entry.get("object")
        if not _side_panel_object_alive(sibling):
            continue
        try:
            parent = getattr(sibling, "parent", None)
        except (ReferenceError, RuntimeError):
            continue
        if parent is None:
            continue
        try:
            parent_by_pointer[parent.as_pointer()] = parent
        except Exception:
            parent_by_pointer[getattr(parent, "name", "")] = parent

    if len(parent_by_pointer) == 1:
        return next(iter(parent_by_pointer.values()))
    if getattr(obj, "type", "") == "CURVES" and getattr(obj, "parent", None) is not None:
        return obj.parent
    return obj


def _side_panel_biome_panel_owner_key(obj, row_entries):
    return _side_panel_object_pointer_token(_side_panel_biome_panel_owner(obj, row_entries))


def _side_panel_biome_panel_id(layout_model, bgroup):
    owner_key = layout_model.get("biome_panel_owner_key", "none")
    bgroup_key = _side_panel_panel_token(bgroup)
    return f"{SECRET_PAINT_BIOME_PANEL_PREFIX}_{owner_key}_{bgroup_key}"


def _side_panel_row_sort_key(row_entry):
    panel_order = row_entry.get("panel_order")
    has_no_panel_order = panel_order is None
    if panel_order is None:
        panel_order = 0
    return (
        has_no_panel_order,
        panel_order,
        _side_panel_text_sort_key(row_entry.get("sort_name")),
        _side_panel_text_sort_key(row_entry.get("name")),
    )


def _build_side_panel_row_model(sibling):
    sibling_name = _side_panel_rna_name(sibling)
    if not sibling_name:
        return None
    try:
        modifier = sibling.modifiers[0]
    except (ReferenceError, RuntimeError, IndexError):
        return None
    input_2 = _safe_side_panel_modifier_value(modifier, "Input_2")
    input_9 = _safe_side_panel_modifier_value(modifier, "Input_9")
    input_2_name = _side_panel_rna_name(input_2)
    input_9_name = _side_panel_rna_name(input_9)

    if input_2_name:
        display_name = input_2_name
        icon = "EMPTY_AXIS" if _side_panel_rna_type(input_2) == "EMPTY" else "OBJECT_DATA"
        sort_name = input_2_name
    elif input_9_name:
        display_name = input_9_name
        icon = "OUTLINER_COLLECTION"
        sort_name = input_9_name
    else:
        display_name = "(empty)"
        icon = "OBJECT_DATA"
        sort_name = ""

    render_alert = False
    render_icon = "RESTRICT_RENDER_OFF"
    try:
        socket_15 = bool(modifier["Socket_15"])
        socket_14 = bool(modifier["Socket_14"])
        socket_2 = bool(modifier["Socket_2"])
        input_99 = bool(modifier["Input_99"])
        render_alert = socket_15 or socket_14 or socket_2 or input_99
        if input_99:
            render_icon = "RESTRICT_RENDER_ON"
        elif socket_14:
            render_icon = "RESTRICT_VIEW_ON"
    except Exception:
        socket_2 = bool(_safe_side_panel_modifier_value(modifier, "Socket_2", False))
        input_99 = bool(_safe_side_panel_modifier_value(modifier, "Input_99", False))
        render_alert = socket_2 or input_99
        if input_99:
            render_icon = "RESTRICT_RENDER_ON"

    display_type = getattr(sibling, "display_type", "TEXTURED")
    bounds_alert = display_type == "BOUNDS"
    bounds_icon = 'SHADING_BBOX' if bounds_alert else 'SHADING_SOLID'

    return {
        "object": sibling,
        "name": sibling_name,
        "sort_name": sort_name,
        "panel_order": _side_panel_order_value(sibling),
        "display_name": display_name,
        "icon": icon,
        "bgroup": _safe_side_panel_modifier_value(modifier, "Socket_0", 0),
        "biome_label_override": _safe_side_panel_modifier_value(modifier, "Socket_8", ""),
        "procedural_enabled": bool(_safe_side_panel_modifier_value(modifier, "Input_69", False)),
        "vertex_attribute_name": _safe_side_panel_modifier_value(modifier, "Input_83_attribute_name", "") or "",
        "vertex_use_attribute": bool(_safe_side_panel_modifier_value(modifier, "Input_83_use_attribute", False)),
        "render_alert": render_alert,
        "render_icon": render_icon,
        "display_type": display_type,
        "bounds_alert": bounds_alert,
        "bounds_icon": bounds_icon,
        "mask_alert": bool(_safe_side_panel_modifier_value(modifier, "Input_98", False)),
    }


def _secret_paint_panel_biome_rename_cursor_visible(bgroup, row_entries):
    state = _SIDE_PANEL_BIOME_RENAME_CURSOR
    if not state.get("visible"):
        return False
    return _secret_paint_panel_biome_rename_active(bgroup, row_entries)


def _secret_paint_panel_biome_rename_active(bgroup, row_entries):
    state = _SIDE_PANEL_BIOME_RENAME_CURSOR
    if not state.get("active"):
        return False
    try:
        if int(bgroup) != int(state.get("biome_number", 0)):
            return False
    except Exception:
        return False
    anchor_name = state.get("anchor_name", "")
    return any(row_entry.get("name") == anchor_name for row_entry in row_entries)


def _secret_paint_panel_biome_rename_cursor_tick():
    state = _SIDE_PANEL_BIOME_RENAME_CURSOR
    if not state.get("active"):
        state["timer_running"] = False
        return None
    state["visible"] = not bool(state.get("visible", True))
    _clear_side_panel_count_cache(reason="panel_rename_biome_cursor")
    _secret_paint_tag_redraw_view3d_areas()
    return 0.45


def _secret_paint_panel_begin_biome_rename_cursor(context, anchor_name, biome_number):
    state = _SIDE_PANEL_BIOME_RENAME_CURSOR
    state["active"] = True
    state["anchor_name"] = anchor_name
    state["biome_number"] = biome_number
    state["visible"] = True
    if not state.get("timer_running"):
        state["timer_running"] = True
        try:
            bpy.app.timers.register(_secret_paint_panel_biome_rename_cursor_tick, first_interval=0.45)
        except Exception:
            state["timer_running"] = False
    _clear_side_panel_count_cache(reason="panel_rename_biome_cursor_start")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_end_biome_rename_cursor(context):
    state = _SIDE_PANEL_BIOME_RENAME_CURSOR
    state["active"] = False
    state["anchor_name"] = ""
    state["biome_number"] = 0
    state["visible"] = False
    _clear_side_panel_count_cache(reason="panel_rename_biome_cursor_end")
    _secret_paint_tag_redraw_view3d_areas(context)


def _build_side_panel_biome_model(bgroup, row_entries):
    label_text = f"BIOME {bgroup}"
    rename_active = False
    if row_entries:
        override = row_entries[0]["biome_label_override"]
        if override not in ("", str(bgroup), None):
            label_text = override
        rename_active = _secret_paint_panel_biome_rename_active(bgroup, row_entries)
        if _secret_paint_panel_biome_rename_cursor_visible(bgroup, row_entries):
            label_text = f"{label_text}|"

        try:
            modifier = row_entries[0]["object"].modifiers[0]
        except (ReferenceError, RuntimeError, IndexError):
            modifier = None
        try:
            if modifier is not None and modifier["Socket_2"]:
                render_icon = "RESTRICT_RENDER_ON"
                render_alert = True
            elif modifier is not None and modifier["Socket_15"]:
                render_icon = "RESTRICT_VIEW_ON"
                render_alert = True
            else:
                render_icon = "RESTRICT_RENDER_OFF"
                render_alert = False
        except Exception:
            if _safe_side_panel_modifier_value(modifier, "Socket_2", False):
                render_icon = "RESTRICT_RENDER_ON"
                render_alert = True
            else:
                render_icon = "RESTRICT_RENDER_OFF"
                render_alert = False
    else:
        render_icon = "RESTRICT_RENDER_OFF"
        render_alert = False

    bounds_alert = not any(entry["display_type"] in ("WIRE", "SOLID", "TEXTURED") for entry in row_entries)
    mask_alert = all(entry["mask_alert"] for entry in row_entries) if row_entries else False

    return {
        "bgroup": bgroup,
        "label": label_text,
        "rename_active": rename_active,
        "rows": row_entries,
        "render_icon": render_icon,
        "render_alert": render_alert,
        "bounds_alert": bounds_alert,
        "mask_alert": mask_alert,
    }


def _build_side_panel_layout_model(context, obj):
    hair = []

    try:
        if obj.type == "CURVES" and obj.parent:
            for hai in obj.parent.children:
                if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                    for modifier in hai.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                            hair.append((hai, _safe_side_panel_modifier_value(hai.modifiers[0], "Input_2") if _safe_side_panel_modifier_value(hai.modifiers[0], "Input_2") else _safe_side_panel_modifier_value(hai.modifiers[0], "Input_9")))
        elif obj.type == "MESH" or obj.type == "EMPTY":
            for hayr in bpy.context.scene.objects:
                if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                    for modifier in hayr.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and hayr.modifiers[0]["Input_97"] == obj \
                        or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and hayr.modifiers[0]["Input_2"] == obj \
                        or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and hayr.modifiers[0]["Input_73"] == obj:
                            hair.append((hayr, _safe_side_panel_modifier_value(hayr.modifiers[0], "Input_2") if _safe_side_panel_modifier_value(hayr.modifiers[0], "Input_2") else _safe_side_panel_modifier_value(hayr.modifiers[0], "Input_9")))
    except ReferenceError:
        pass

    row_entries = []
    for hayr, _source in hair:
        if not _side_panel_object_alive(hayr):
            continue
        try:
            row_entry = _build_side_panel_row_model(hayr)
        except (ReferenceError, RuntimeError):
            continue
        if row_entry is not None:
            row_entries.append(row_entry)
    grouped_rows = defaultdict(list)
    for row_entry in row_entries:
        grouped_rows[row_entry["bgroup"]].append(row_entry)

    for bgroup_rows in grouped_rows.values():
        bgroup_rows.sort(key=_side_panel_row_sort_key)

    all_bgroups = sorted(grouped_rows.keys(), key=_side_panel_bgroup_sort_key)
    biome_models = [_build_side_panel_biome_model(bgroup, grouped_rows[bgroup]) for bgroup in all_bgroups]
    biome_panel_owner_key = _side_panel_biome_panel_owner_key(obj, row_entries)

    return {
        "hair_count": len(row_entries),
        "biome_count": len(biome_models),
        "biome_panel_owner_key": biome_panel_owner_key,
        "biomes": biome_models,
    }


def _get_side_panel_layout_model_cached(context, obj):
    try:
        cache_key = (
            context.scene.as_pointer() if context.scene else 0,
            context.view_layer.as_pointer() if context.view_layer else 0,
            obj.as_pointer(),
            getattr(obj, "type", ""),
        )
    except Exception:
        cache_key = None

    if cache_key is not None:
        try:
            with _SIDE_PANEL_COUNT_CACHE_LOCK:
                cached = _SIDE_PANEL_LAYOUT_CACHE.get(cache_key)
            if cached:
                return cached["model"]
        except Exception:
            pass

    model = _build_side_panel_layout_model(context, obj)

    if cache_key is not None:
        try:
            with _SIDE_PANEL_COUNT_CACHE_LOCK:
                _SIDE_PANEL_LAYOUT_CACHE[cache_key] = {"model": model}
        except Exception:
            pass

    return model


def _secret_paint_panel_world_target_object(context):
    try:
        world_paint_module = _secret_paint_world_paint_module()
        target_object = world_paint_module.world_paint_panel_target_object(context)
        if _side_panel_object_alive(target_object):
            return target_object
    except Exception:
        pass

    obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    if getattr(obj, "type", "") == "CURVES" and _side_panel_object_alive(getattr(obj, "parent", None)):
        return obj.parent
    return obj if _side_panel_object_alive(obj) else None


def _secret_paint_panel_surface_lock_enabled(context):
    try:
        world_paint_module = _secret_paint_world_paint_module()
        return bool(world_paint_module.world_paint_surface_lock_enabled(context))
    except Exception:
        pass
    preferences = _secret_paint_addon_preferences(context)
    return bool(preferences and getattr(preferences, "paint_only_current_surface", False))


@persistent
def _side_panel_count_cache_on_load_post(_dummy):
    _clear_side_panel_count_cache(reason="load_post")


def _secret_paint_scene_uses_secret_paint():
    try:
        for obj in bpy.data.objects:
            if getattr(obj, "type", "") not in {"CURVES", "CURVE"}:
                continue
            for modifier in getattr(obj, "modifiers", ()):
                if modifier.type != 'NODES':
                    continue
                node_group = getattr(modifier, "node_group", None)
                node_name = getattr(node_group, "name", "")
                if node_name == "Secret Paint" or node_name.startswith("Secret Paint."):
                    return True
        return bpy.data.node_groups.get("Secret Paint") is not None
    except Exception:
        return False


def _secret_paint_node_tree_needs_update():
    try:
        node_tree = bpy.data.node_groups.get("Secret Paint")
        generator_tree = _secret_paint_get_generator_node_group()
        if node_tree is None or generator_tree is None:
            return True
        version_needs_update = _secret_paint_node_tree_version(node_tree) != SECRET_PAINT_NODE_VERSION
        return (
            version_needs_update
            or not _secret_paint_generator_has_stable_id_nodes(generator_tree)
            or not _secret_paint_generator_uses_stable_id(generator_tree)
        )
    except Exception:
        return True


def _secret_paint_find_node_socket(sockets, socket_name):
    for socket in sockets:
        if getattr(socket, "name", "") == socket_name:
            return socket
    return None


def _secret_paint_node_tree_version(node_tree):
    if node_tree is None:
        return None

    try:
        if bpy.app.version_string >= "4.0.0":
            for item in node_tree.interface.items_tree:
                if getattr(item, "item_type", None) != 'SOCKET':
                    continue
                if getattr(item, "name", "") == "Node Version":
                    return getattr(item, "default_value", None)
    except Exception:
        pass

    try:
        if len(node_tree.outputs) > 1:
            return node_tree.outputs[1].default_value
    except Exception:
        pass
    return None


def _secret_paint_generator_node_groups():
    generator_groups = []
    exact_generator = bpy.data.node_groups.get("Secret Generator")
    if exact_generator is not None:
        generator_groups.append(exact_generator)

    for node_tree in bpy.data.node_groups:
        if not getattr(node_tree, "name", "").startswith("Secret Generator"):
            continue
        if exact_generator is not None and node_tree == exact_generator:
            continue
        generator_groups.append(node_tree)

    return generator_groups


def _secret_paint_get_generator_node_group():
    generator_groups = _secret_paint_generator_node_groups()
    if generator_groups:
        return generator_groups[0]
    return None


def _secret_paint_generator_has_stable_id_nodes(generator_tree):
    if generator_tree is None:
        return False

    try:
        return (
            generator_tree.nodes.get("Set ID") is not None
            and generator_tree.nodes.get("Stable Hash Z") is not None
        )
    except Exception:
        return False


def _secret_paint_generator_uses_stable_id(generator_tree):
    if not _secret_paint_generator_has_stable_id_nodes(generator_tree):
        return False

    try:
        set_id_node = generator_tree.nodes.get("Set ID")
        stable_hash_node = generator_tree.nodes.get("Stable Hash Z")
        if set_id_node is None or stable_hash_node is None:
            return False

        id_input = _secret_paint_find_node_socket(set_id_node.inputs, "ID")
        hash_output = _secret_paint_find_node_socket(stable_hash_node.outputs, "Hash")
        if id_input is None or hash_output is None:
            return False

        for link in getattr(id_input, "links", ()):
            from_node = getattr(link, "from_node", None)
            if from_node == stable_hash_node and getattr(link, "from_socket", None) == hash_output:
                return True
            if getattr(from_node, "name", "") == "Legacy Procedural ID Switch":
                return True
    except Exception:
        pass

    return False


def _secret_paint_generator_uses_legacy_random_id(generator_tree):
    try:
        set_id_node = generator_tree.nodes.get("Set ID")
        if set_id_node is None:
            return False
        id_input = _secret_paint_find_node_socket(set_id_node.inputs, "ID")
        if id_input is None:
            return False
        for link in getattr(id_input, "links", ()):
            from_node = getattr(link, "from_node", None)
            from_socket = getattr(link, "from_socket", None)
            if getattr(from_node, "name", "") == "Random Value.001" and getattr(from_socket, "name", "") == "Value":
                return True
    except Exception:
        pass
    return False


def _secret_paint_patch_runtime_node_groups():
    # Secret Paint node groups are versioned bundled assets. If a node tree is
    # stale, reimport it instead of mutating sockets, links, or version metadata.
    return False


def _secret_paint_ensure_generator_stable_ids(context, upadte_provenance="procedural to manual stable ids"):
    if _secret_paint_node_tree_needs_update():
        secretpaint_update_modifier_f(context, upadte_provenance=upadte_provenance)

    return _secret_paint_get_generator_node_group()


def _remove_secret_paint_node_update_load_handlers():
    for handler in list(bpy.app.handlers.load_post):
        if getattr(handler, "__name__", "") != "_secret_paint_node_update_on_load_post":
            continue
        if not getattr(handler, "__module__", "").endswith("secret_paint_shared"):
            continue
        try:
            bpy.app.handlers.load_post.remove(handler)
        except Exception:
            pass


@persistent
def _side_panel_count_cache_on_depsgraph_update_post(_scene, depsgraph):
    try:
        for update in depsgraph.updates:
            identifier = getattr(getattr(update.id, "bl_rna", None), "identifier", "")
            if identifier in {"Object", "Mesh", "Curves"}:
                _clear_side_panel_count_cache(reason=f"depsgraph:{identifier}")
                return
    except Exception:
        _clear_side_panel_count_cache(reason="depsgraph:error")


def _register_side_panel_count_cache_handlers():
    _clear_side_panel_count_cache(reason="register")
    if _side_panel_count_cache_on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_side_panel_count_cache_on_load_post)
    if _side_panel_count_cache_on_depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_side_panel_count_cache_on_depsgraph_update_post)
    _remove_secret_paint_node_update_load_handlers()


def _unregister_side_panel_count_cache_handlers():
    if _side_panel_count_cache_on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_side_panel_count_cache_on_load_post)
    if _side_panel_count_cache_on_depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_side_panel_count_cache_on_depsgraph_update_post)
    _remove_secret_paint_node_update_load_handlers()
    _clear_side_panel_count_cache(reason="unregister")


SECRET_PAINT_AUTO_UV_NAME = "Secret Paint UV"
SECRET_PAINT_AUTO_UV_CACHE_VERTS = ".secret_paint_auto_uv_vert_count"
SECRET_PAINT_AUTO_UV_CACHE_EDGES = ".secret_paint_auto_uv_edge_count"
SECRET_PAINT_AUTO_UV_CACHE_FACES = ".secret_paint_auto_uv_face_count"
SECRET_PAINT_ID_CACHE_CURVES = ".secret_paint_last_id_curve_count"
SECRET_PAINT_ID_CACHE_POINTS = ".secret_paint_last_id_point_count"
SECRET_PAINT_STABLE_ID_ATTRIBUTE = "secret_stable_curve_id"
SECRET_PAINT_STABLE_ROOT_POSITION_ATTRIBUTE = "secret_stable_root_position"
SECRET_PAINT_STABLE_IDS_MIGRATED_PROP = ".secret_paint_stable_ids_migrated"
SECRET_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP = ".secret_paint_stable_ids_migrated_curve_count"
SECRET_PAINT_MANUAL_LEGACY_IDS_PROP = ".secret_paint_manual_legacy_ids"
SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET = "Legacy Procedural IDs"
SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET = "Baked Procedural Transforms"
SECRET_PAINT_ENABLE_APPLY_IDS_MODIFIER = False
SECRET_PAINT_WORLD_STABLE_IDS_READY_PROP = "secret_paint_stable_ids_ready"
SECRET_PAINT_WORLD_NEXT_STABLE_ID_PROP = "secret_paint_next_stable_curve_id"
SECRET_PAINT_NODE_VERSION = 43
SECRET_PAINT_SKIP_AUTO_ASSEMBLY_ON_Q_PROP = ".secret_paint_skip_auto_assembly_on_q"


def _secret_paint_addon_preferences(context=None):
    context = context if context is not None else bpy.context
    try:
        addons = context.preferences.addons
    except Exception:
        return None

    module_candidates = []
    for module_name in (
        __package__,
        __name__.split(".")[0],
        "Secret Paint",
        "orencloud private",
        "bl_ext.blender_org.secret_paint",
    ):
        if module_name and module_name not in module_candidates:
            module_candidates.append(module_name)

    for module_name in module_candidates:
        try:
            addon_entry = addons.get(module_name)
        except Exception:
            addon_entry = None
        preferences = getattr(addon_entry, "preferences", None) if addon_entry else None
        if preferences is not None:
            return preferences

    try:
        for addon_entry in addons:
            preferences = getattr(addon_entry, "preferences", None)
            if (
                preferences is not None
                and hasattr(preferences, "checkboxUseLegacyQPaint")
                and hasattr(preferences, "trigger_viewport_mask")
            ):
                return preferences
    except Exception:
        pass
    return None


def _secret_paint_pref(name, default=None, context=None):
    preferences = _secret_paint_addon_preferences(context)
    if preferences is None:
        return default
    return getattr(preferences, name, default)


def secret_paint_object_size_density_multiplier(context=None):
    value = _secret_paint_pref(
        "object_size_density_multiplier",
        SECRET_PAINT_OBJECT_SIZE_DENSITY_MULTIPLIER_DEFAULT,
        context,
    )
    try:
        value = float(value)
    except Exception:
        value = SECRET_PAINT_OBJECT_SIZE_DENSITY_MULTIPLIER_DEFAULT
    return max(0.01, value)


def secret_paint_apply_object_size_density_multiplier(density, context=None):
    try:
        density = float(density)
    except Exception:
        return density
    return density * secret_paint_object_size_density_multiplier(context)


def secretpaint_mark_skip_auto_assembly_on_next_q(obj):
    if obj is None:
        return
    try:
        obj[SECRET_PAINT_SKIP_AUTO_ASSEMBLY_ON_Q_PROP] = True
    except Exception:
        pass


def _secretpaint_consume_skip_auto_assembly_on_q(obj):
    if obj is None:
        return False
    try:
        skip_auto_assembly = bool(obj.get(SECRET_PAINT_SKIP_AUTO_ASSEMBLY_ON_Q_PROP, False))
    except Exception:
        skip_auto_assembly = False
    if skip_auto_assembly:
        try:
            del obj[SECRET_PAINT_SKIP_AUTO_ASSEMBLY_ON_Q_PROP]
        except Exception:
            pass
    return skip_auto_assembly


def _get_pickup_trace():
    return None


def _begin_pickup_trace(trace_name, context=None, **meta):
    return None


def _finish_pickup_trace(trace, detail=""):
    return None


SECRET_PAINT_WORLD_PERF_LOG_PATH = None
SECRET_PAINT_WORLD_PERF_LOG_ENABLED = False
SECRET_PAINT_WORLD_PERF_FLUSH_INTERVAL = 0.5
SECRET_PAINT_WORLD_PERF_FLUSH_LINES = 64
_SECRET_PAINT_WORLD_PERF_BUFFER = []
_SECRET_PAINT_WORLD_PERF_LAST_FLUSH = 0.0
_SECRET_PAINT_WORLD_PERF_SEQUENCE = 0


def _secret_paint_perf_value(value):
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple, set)):
        return "[" + ",".join(_secret_paint_perf_value(item) for item in value) + "]"
    try:
        return str(value).replace("\n", " ").replace("\r", " ")
    except Exception:
        return repr(value)


def secret_paint_world_perf_log_reset(reason=""):
    return None


def secret_paint_world_perf_log_flush(force=False):
    return None


def secret_paint_world_perf_log(label, **fields):
    return None


class _SecretPaintWorldPerfSpan:
    def __init__(self, label, threshold_ms=1.0, **fields):
        self.label = label
        self.threshold_ms = float(threshold_ms)
        self.fields = fields
        self.start = 0.0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def secret_paint_world_perf_span(label, threshold_ms=1.0, **fields):
    if not SECRET_PAINT_WORLD_PERF_LOG_ENABLED:
        return _SecretPaintWorldPerfSpan("", threshold_ms=10**9)
    return _SecretPaintWorldPerfSpan(label, threshold_ms=threshold_ms, **fields)


def _secret_paint_modifier(obj):
    if obj is None:
        return None
    try:
        for modifier in obj.modifiers:
            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                return modifier
    except Exception:
        return None
    return None


def _secret_paint_node_group_input_identifier(node_group, socket_name):
    if node_group is None:
        return None

    try:
        for item in node_group.interface.items_tree:
            if getattr(item, "item_type", None) != 'SOCKET':
                continue
            if getattr(item, "in_out", None) != 'INPUT':
                continue
            if getattr(item, "name", "") == socket_name:
                return getattr(item, "identifier", None)
    except Exception:
        pass

    try:
        for socket in node_group.inputs:
            if getattr(socket, "name", "") == socket_name:
                return getattr(socket, "identifier", None)
    except Exception:
        pass
    return None


def _secret_paint_modifier_input_by_name(modifier, socket_name, default=None):
    identifier = _secret_paint_node_group_input_identifier(getattr(modifier, "node_group", None), socket_name)
    for key in (identifier, socket_name):
        if not key:
            continue
        try:
            return modifier[key]
        except Exception:
            pass
    return default


def _secret_paint_set_modifier_input_by_name(modifier, socket_name, value):
    identifier = _secret_paint_node_group_input_identifier(getattr(modifier, "node_group", None), socket_name)
    for key in (identifier, socket_name):
        if not key:
            continue
        try:
            modifier[key] = value
            return True
        except Exception:
            pass
    return False


def _secret_paint_modifier_legacy_procedural_ids(modifier):
    return bool(_secret_paint_modifier_input_by_name(
        modifier,
        SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
        False,
    ))


def _secret_paint_is_system(obj):
    return bool(obj and getattr(obj, "type", None) == "CURVES" and _secret_paint_modifier(obj))


def _secret_paint_system_uses_object_as_source(system_obj, source_obj):
    modifier = _secret_paint_modifier(system_obj)
    if modifier is None or source_obj is None:
        return False

    try:
        if modifier["Input_2"] == source_obj:
            return True
    except Exception:
        pass

    try:
        brush_collection = modifier["Input_9"]
    except Exception:
        brush_collection = None
    if brush_collection is None:
        return False

    try:
        return source_obj in brush_collection.all_objects[:]
    except Exception:
        return False


def _secret_paint_collection_contains_object(collection, obj):
    if collection is None or obj is None:
        return False
    try:
        return obj in collection.all_objects[:]
    except Exception:
        return False


def _secret_paint_object_is_source_for_any_system(source_obj):
    if source_obj is None:
        return False
    try:
        objects = bpy.context.scene.objects
    except Exception:
        objects = bpy.data.objects
    return any(
        _secret_paint_is_system(obj) and _secret_paint_system_uses_object_as_source(obj, source_obj)
        for obj in objects
    )


def _secret_paint_curve_root_world_positions(system_obj):
    curves_data = getattr(system_obj, "data", None)
    if curves_data is None:
        return []

    root_values = _secret_paint_curve_root_position_values(curves_data)
    if not root_values:
        return []

    world_matrix = getattr(system_obj, "matrix_world", None)
    if world_matrix is None:
        return []

    positions = []
    for index in range(0, len(root_values), 3):
        if index + 2 >= len(root_values):
            break
        try:
            positions.append(world_matrix @ Vector((root_values[index], root_values[index + 1], root_values[index + 2])))
        except Exception:
            continue
    return positions


def _secret_paint_nearest_system_root_distance(system_obj, location):
    if system_obj is None or location is None:
        return float("inf")

    distances = [
        (root_world - location).length
        for root_world in _secret_paint_curve_root_world_positions(system_obj)
        if root_world is not None
    ]
    if distances:
        return min(distances)

    try:
        return (system_obj.matrix_world.translation - location).length
    except Exception:
        return float("inf")


def _secret_paint_matrices_close(matrix_a, matrix_b, tolerance=1.0e-5):
    if matrix_a is None or matrix_b is None:
        return False
    try:
        for row_a, row_b in zip(matrix_a, matrix_b):
            for value_a, value_b in zip(row_a, row_b):
                if abs(value_a - value_b) > tolerance:
                    return False
        return True
    except Exception:
        return False


def _secret_paint_hit_matches_object_surface(obj, depsgraph, hit_location, hit_matrix=None, tolerance=0.01):
    if obj is None or getattr(obj, "type", "") != "MESH" or depsgraph is None or hit_location is None:
        return False

    if hit_matrix is not None and not _secret_paint_matrices_close(hit_matrix, obj.matrix_world):
        return False

    try:
        tolerance = max(tolerance, max(obj.dimensions) * 0.001)
    except Exception:
        tolerance = max(tolerance, 0.01)

    try:
        eval_obj = obj.evaluated_get(depsgraph)
        local_hit = eval_obj.matrix_world.inverted() @ hit_location
        try:
            hit, surface_location, _surface_normal, _surface_index = eval_obj.closest_point_on_mesh(
                local_hit,
                distance=max(tolerance * 4.0, 0.05),
            )
        except TypeError:
            hit, surface_location, _surface_normal, _surface_index = eval_obj.closest_point_on_mesh(local_hit)
        except Exception:
            return False
    except Exception:
        return False

    if not hit:
        return False

    world_surface_location = eval_obj.matrix_world @ surface_location
    return (world_surface_location - hit_location).length <= tolerance


def _secret_paint_system_from_hit_object(hit_obj, hit_location, depsgraph=None, hit_matrix=None):
    if hit_obj is None:
        return None
    if _secret_paint_is_system(hit_obj):
        return hit_obj

    candidates = [
        obj for obj in bpy.context.scene.objects
        if _secret_paint_is_system(obj) and _secret_paint_system_uses_object_as_source(obj, hit_obj)
    ]
    if not candidates:
        return None

    if getattr(hit_obj, "type", "") == "MESH" and _secret_paint_hit_matches_object_surface(hit_obj, depsgraph, hit_location, hit_matrix=hit_matrix):
        return None

    if len(candidates) == 1:
        return candidates[0]
    return min(candidates, key=lambda candidate: _secret_paint_nearest_system_root_distance(candidate, hit_location))


def _secret_paint_hover_object_from_mouse(context, event):
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None or event is None:
        return None, None

    mouse_coord = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(region, region_data, mouse_coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, region_data, mouse_coord)
    depsgraph = context.evaluated_depsgraph_get()
    current_origin = origin
    hit_epsilon = 0.001

    for _step in range(24):
        try:
            hit, location, _normal, _face_index, obj, matrix = context.scene.ray_cast(depsgraph, current_origin, direction)
        except TypeError:
            hit, location, _normal, _face_index, obj, matrix = context.scene.ray_cast(
                depsgraph,
                current_origin,
                direction,
                distance=1.0e12,
            )
        except Exception:
            return None, None

        if not hit or obj is None:
            return None, None

        if obj.name.startswith("Secret Paint Viewport Mask"):
            current_origin = location + direction * hit_epsilon
            continue

        system_obj = _secret_paint_system_from_hit_object(obj, location, depsgraph=depsgraph, hit_matrix=matrix)
        if system_obj is not None:
            return system_obj, location

        if getattr(obj, "type", "") in {"MESH", "CURVE", "CURVES", "EMPTY"}:
            return obj, location

        current_origin = location + direction * hit_epsilon

    return None, None


def _secret_paint_mesh_topology_signature(mesh):
    return (len(mesh.vertices), len(mesh.edges), len(mesh.polygons))


def _secret_paint_store_auto_uv_cache(mesh):
    vert_count, edge_count, face_count = _secret_paint_mesh_topology_signature(mesh)
    mesh[SECRET_PAINT_AUTO_UV_CACHE_VERTS] = vert_count
    mesh[SECRET_PAINT_AUTO_UV_CACHE_EDGES] = edge_count
    mesh[SECRET_PAINT_AUTO_UV_CACHE_FACES] = face_count


def _secret_paint_auto_uv_cache_matches(mesh):
    custom_uv = mesh.uv_layers.get(SECRET_PAINT_AUTO_UV_NAME)
    if custom_uv is None:
        return False
    vert_count, edge_count, face_count = _secret_paint_mesh_topology_signature(mesh)
    return (
        mesh.get(SECRET_PAINT_AUTO_UV_CACHE_VERTS) == vert_count and
        mesh.get(SECRET_PAINT_AUTO_UV_CACHE_EDGES) == edge_count and
        mesh.get(SECRET_PAINT_AUTO_UV_CACHE_FACES) == face_count
    )


def _secret_paint_get_curves_counts(curves_data):
    curve_count = len(curves_data.curves) if hasattr(curves_data, "curves") else 0
    point_count = len(curves_data.points) if hasattr(curves_data, "points") else 0
    return curve_count, point_count


def _secret_paint_stable_curve_values_are_usable(curves_data, stable_curve_values):
    if curves_data is None or not hasattr(curves_data, "curves"):
        return False

    curve_count = len(curves_data.curves)
    if curve_count <= 0:
        return False

    values = [int(value) for value in list(stable_curve_values or [])[:curve_count]]
    if len(values) != curve_count:
        return False

    if any(value != 0 for value in values):
        return True

    try:
        return bool(curves_data.get(SECRET_PAINT_STABLE_IDS_MIGRATED_PROP))
    except Exception:
        return False


def _secret_paint_curve_id_attribute_is_valid(curves_data, curve_count, point_count):
    try:
        id_attr = curves_data.attributes.get("id")
    except Exception:
        return False
    if id_attr is None:
        return False
    try:
        if id_attr.domain not in {'CURVE', 'POINT'}:
            return False
    except Exception:
        return False
    try:
        return len(id_attr.data) in {curve_count, point_count}
    except Exception:
        return False


def _secret_paint_store_id_cache(curves_data, curve_count, point_count):
    curves_data[SECRET_PAINT_ID_CACHE_CURVES] = int(curve_count)
    curves_data[SECRET_PAINT_ID_CACHE_POINTS] = int(point_count)


def _secret_paint_should_apply_ids(curves_obj):
    curve_count, point_count = _secret_paint_get_curves_counts(curves_obj.data)
    if not SECRET_PAINT_ENABLE_APPLY_IDS_MODIFIER:
        return False, curve_count, point_count, "feature_disabled"
    if curve_count == 0:
        return False, curve_count, point_count, "empty_curves"

    cached_curve_count = curves_obj.data.get(SECRET_PAINT_ID_CACHE_CURVES)
    cached_point_count = curves_obj.data.get(SECRET_PAINT_ID_CACHE_POINTS)
    if cached_curve_count is None or cached_point_count is None:
        return True, curve_count, point_count, "missing_cache"

    if not _secret_paint_curve_id_attribute_is_valid(curves_obj.data, curve_count, point_count):
        return True, curve_count, point_count, "missing_or_invalid_id_attr"

    if int(cached_curve_count) != curve_count or int(cached_point_count) != point_count:
        return True, curve_count, point_count, "counts_changed"

    return False, curve_count, point_count, "cache_match"


def _secret_paint_get_apply_ids_node_group():
    if "Secret Paint Apply IDs" in bpy.data.node_groups:
        node_to_use = bpy.data.node_groups.get("Secret Paint Apply IDs")
    else:
        node_to_use = bpy.data.node_groups.new(type='GeometryNodeTree', name='Secret Paint Apply IDs')
        if bpy.app.version_string >= "4.0.0":
            node_to_use.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
            node_to_use.interface.new_socket(name='Seed', in_out='INPUT', socket_type='NodeSocketInt')
            node_to_use.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        elif bpy.app.version_string < "4.0.0":
            node_to_use.outputs.new(type='NodeSocketGeometry', name='GEO')
            node_to_use.inputs.new(type='NodeSocketGeometry', name='GEO')
            node_to_use.inputs.new(type='NodeSocketInt', name='Seed')

    while node_to_use.nodes:
        node_to_use.nodes.remove(node_to_use.nodes[0])

    input = node_to_use.nodes.new('NodeGroupInput')
    output = node_to_use.nodes.new('NodeGroupOutput')
    stable_attr = node_to_use.nodes.new('GeometryNodeInputNamedAttribute')
    stable_attr.data_type = 'INT'
    stable_attr.inputs["Name"].default_value = SECRET_PAINT_STABLE_ID_ATTRIBUTE
    sample_curve = node_to_use.nodes.new('GeometryNodeSampleCurve')
    sample_curve.mode = 'FACTOR'
    curve_index = node_to_use.nodes.new('GeometryNodeInputIndex')
    separate_xyz = node_to_use.nodes.new('ShaderNodeSeparateXYZ')
    scale_x = node_to_use.nodes.new('ShaderNodeMath')
    scale_y = node_to_use.nodes.new('ShaderNodeMath')
    scale_z = node_to_use.nodes.new('ShaderNodeMath')
    for node in (scale_x, scale_y, scale_z):
        node.operation = 'MULTIPLY'
        node.inputs[1].default_value = 1000.0
    to_int_x = node_to_use.nodes.new('FunctionNodeFloatToInt')
    to_int_y = node_to_use.nodes.new('FunctionNodeFloatToInt')
    to_int_z = node_to_use.nodes.new('FunctionNodeFloatToInt')
    for node in (to_int_x, to_int_y, to_int_z):
        node.rounding_mode = 'ROUND'
    hash_x = node_to_use.nodes.new('FunctionNodeHashValue')
    hash_y = node_to_use.nodes.new('FunctionNodeHashValue')
    hash_z = node_to_use.nodes.new('FunctionNodeHashValue')
    for node in (hash_x, hash_y, hash_z):
        node.data_type = 'INT'
    resolve_stable_id = node_to_use.nodes.new('GeometryNodeSwitch')
    resolve_stable_id.input_type = 'INT'
    store_stable_attr = node_to_use.nodes.new('GeometryNodeStoreNamedAttribute')
    store_stable_attr.data_type = 'INT'
    store_stable_attr.domain = 'CURVE'
    store_stable_attr.inputs["Name"].default_value = SECRET_PAINT_STABLE_ID_ATTRIBUTE
    set_curve_id = node_to_use.nodes.new('GeometryNodeSetID')
    set_point_id = node_to_use.nodes.new('GeometryNodeSetID')

    node_to_use.links.new(input.outputs[0], store_stable_attr.inputs["Geometry"])
    node_to_use.links.new(input.outputs[0], sample_curve.inputs["Curves"])
    node_to_use.links.new(curve_index.outputs["Index"], sample_curve.inputs["Curve Index"])
    node_to_use.links.new(sample_curve.outputs["Position"], separate_xyz.inputs["Vector"])
    node_to_use.links.new(separate_xyz.outputs["X"], scale_x.inputs[0])
    node_to_use.links.new(separate_xyz.outputs["Y"], scale_y.inputs[0])
    node_to_use.links.new(separate_xyz.outputs["Z"], scale_z.inputs[0])
    node_to_use.links.new(scale_x.outputs["Value"], to_int_x.inputs["Float"])
    node_to_use.links.new(scale_y.outputs["Value"], to_int_y.inputs["Float"])
    node_to_use.links.new(scale_z.outputs["Value"], to_int_z.inputs["Float"])
    node_to_use.links.new(to_int_x.outputs["Integer"], hash_x.inputs["Value"])
    node_to_use.links.new(input.outputs["Seed"], hash_x.inputs["Seed"])
    node_to_use.links.new(to_int_y.outputs["Integer"], hash_y.inputs["Value"])
    node_to_use.links.new(hash_x.outputs["Hash"], hash_y.inputs["Seed"])
    node_to_use.links.new(to_int_z.outputs["Integer"], hash_z.inputs["Value"])
    node_to_use.links.new(hash_y.outputs["Hash"], hash_z.inputs["Seed"])
    node_to_use.links.new(stable_attr.outputs["Exists"], resolve_stable_id.inputs["Switch"])
    node_to_use.links.new(hash_z.outputs["Hash"], resolve_stable_id.inputs[1])
    node_to_use.links.new(stable_attr.outputs["Attribute"], resolve_stable_id.inputs[2])
    node_to_use.links.new(resolve_stable_id.outputs[0], store_stable_attr.inputs["Value"])
    node_to_use.links.new(store_stable_attr.outputs["Geometry"], set_curve_id.inputs["Geometry"])
    node_to_use.links.new(resolve_stable_id.outputs[0], set_curve_id.inputs["ID"])
    node_to_use.links.new(set_curve_id.outputs["Geometry"], set_point_id.inputs["Geometry"])
    node_to_use.links.new(resolve_stable_id.outputs[0], set_point_id.inputs["ID"])
    node_to_use.links.new(set_point_id.outputs["Geometry"], output.inputs[0])
    return node_to_use


def _secret_paint_datablock_exists(datablock, datablocks):
    if datablock is None:
        return False
    try:
        datablock_pointer = datablock.as_pointer()
    except Exception:
        return False
    for candidate in datablocks:
        try:
            if candidate.as_pointer() == datablock_pointer:
                return True
        except Exception:
            continue
    return False


def _secret_paint_id_key(datablock):
    if datablock is None:
        return None
    try:
        pointer = datablock.as_pointer()
    except Exception:
        pointer = 0
    if pointer:
        return ("PTR", pointer)
    library = getattr(datablock, "library", None)
    return (
        "NAME",
        getattr(datablock, "name", ""),
        getattr(library, "filepath", "") if library else "",
    )


def _secret_paint_find_local_material_copy(source_material):
    if source_material is None:
        return None
    source_library = getattr(getattr(source_material, "library", None), "filepath", "")
    source_name = getattr(source_material, "name", "")
    if not source_library and not getattr(source_material, "override_library", None):
        return None
    for material in bpy.data.materials:
        if getattr(material, "library", None) or getattr(material, "override_library", None):
            continue
        try:
            if (
                material.get("secret_paint_source_material_name") == source_name and
                material.get("secret_paint_source_material_library") == source_library
            ):
                return material
        except Exception:
            continue
    return None


def _secret_paint_safe_material_for_assignment(material, material_cache=None):
    if material is None or not _secret_paint_datablock_exists(material, bpy.data.materials):
        return None
    if not getattr(material, "library", None) and not getattr(material, "override_library", None):
        return material

    material_key = _secret_paint_id_key(material)
    if material_cache is not None and material_key in material_cache:
        cached_material = material_cache[material_key]
        if _secret_paint_datablock_exists(cached_material, bpy.data.materials):
            return cached_material

    local_material = _secret_paint_find_local_material_copy(material)
    if local_material is None:
        try:
            local_material = material.copy()
        except Exception:
            local_material = None
    if local_material is None:
        try:
            local_material = material.make_local()
        except Exception:
            local_material = None
    if local_material is None or not _secret_paint_datablock_exists(local_material, bpy.data.materials):
        return None

    try:
        local_material["secret_paint_source_material_name"] = material.name
        local_material["secret_paint_source_material_library"] = getattr(getattr(material, "library", None), "filepath", "")
    except Exception:
        pass
    if material_cache is not None:
        material_cache[material_key] = local_material
    return local_material


def _secret_paint_append_material_once(materials, material):
    if material is None or not _secret_paint_datablock_exists(material, bpy.data.materials):
        return False
    try:
        material_pointer = material.as_pointer()
    except Exception:
        material_pointer = 0
    try:
        for existing_material in materials:
            if existing_material is None:
                continue
            if material_pointer:
                try:
                    if existing_material.as_pointer() == material_pointer:
                        return False
                except Exception:
                    pass
            elif existing_material.name == material.name:
                return False
        materials.append(material)
        return True
    except Exception:
        return False


def _secret_paint_collect_safe_materials_from_object(obj, material_cache=None):
    if obj is None or not _secret_paint_datablock_exists(obj, bpy.data.objects):
        return []
    safe_materials = []
    for material_slot in getattr(obj, "material_slots", []):
        material = _secret_paint_safe_material_for_assignment(
            getattr(material_slot, "material", None),
            material_cache,
        )
        if material is None:
            continue
        if material not in safe_materials:
            safe_materials.append(material)
    return safe_materials


def _secret_paint_replace_curve_materials_from_sources(curve_obj, source_materials):
    if curve_obj is None or not _secret_paint_datablock_exists(curve_obj, bpy.data.objects):
        return False
    curve_data = getattr(curve_obj, "data", None)
    if curve_data is None:
        return False
    if (
        getattr(curve_obj, "library", None) or
        getattr(curve_obj, "override_library", None) or
        getattr(curve_data, "library", None) or
        getattr(curve_data, "override_library", None)
    ):
        return False

    try:
        curve_data.materials.clear()
    except Exception:
        return False
    for material in source_materials:
        _secret_paint_append_material_once(curve_data.materials, material)
    return True


def _secret_paint_apply_geometry_nodes_modifier(context, obj, modifier, restore_materials=False):
    successfully_applied = False
    shared_data_before_apply = bool(obj.data.users >= 2)
    material_count_before = 0
    same_data = []
    mats_before = []
    if restore_materials:
        mats_before = [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material]
        material_count_before = len(mats_before)

    if shared_data_before_apply:
        same_data = [other for other in bpy.data.objects if other.data == obj.data and other != obj]
        obj.data = obj.data.copy()

    try:
        if bpy.app.version_string >= "4.0.0":
            with context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            successfully_applied = True
        elif bpy.app.version_string < "4.0.0":
            bpy.ops.object.modifier_apply({'object': obj}, modifier=modifier.name)
            successfully_applied = True
    except Exception:
        try:
            obj.modifiers.remove(modifier)
        except Exception:
            pass
        obj.location = obj.location

    for other in same_data:
        other.data = obj.data

    if successfully_applied and restore_materials:
        for mat in mats_before:
            _secret_paint_append_material_once(obj.data.materials, mat)

    return successfully_applied, shared_data_before_apply, material_count_before


def _secret_paint_copy_modifier_properties(source_modifier, target_modifier):
    if source_modifier is None or target_modifier is None:
        return
    for key in source_modifier.keys():
        try:
            target_modifier[key] = source_modifier[key]
        except Exception:
            pass


def _secret_paint_create_procedural_curve_extract_node_group(source_modifier):
    source_tree = getattr(source_modifier, "node_group", None)
    if source_tree is None:
        return None

    extract_tree = None
    try:
        extract_tree = source_tree.copy()
        extract_tree.name = "Secret Paint Procedural Curve Extract"
        instance_node = extract_tree.nodes.get("Instance on Points")
        if instance_node is None:
            raise RuntimeError("Instance on Points node is missing")
        points_input = _secret_paint_find_node_socket(instance_node.inputs, "Points")
        if points_input is None or not points_input.links:
            raise RuntimeError("Procedural points input is not connected")

        output_node = next(
            node for node in extract_tree.nodes
            if node.bl_idname == "NodeGroupOutput"
        )
        geometry_output = _secret_paint_find_node_socket(output_node.inputs, "Geometry")
        if geometry_output is None:
            raise RuntimeError("Geometry output socket is missing")
        point_source = points_input.links[0].from_socket
        for link in list(geometry_output.links):
            extract_tree.links.remove(link)
        extract_tree.links.new(point_source, geometry_output)
        return extract_tree
    except Exception:
        if extract_tree is not None:
            try:
                bpy.data.node_groups.remove(extract_tree, do_unlink=True)
            except Exception:
                pass
        return None


def _secret_paint_set_apply_ids_seed(modifier, seed_value):
    if modifier is None:
        return
    try:
        modifier["Input_2"] = int(seed_value)
        return
    except Exception:
        pass

    node_group = getattr(modifier, "node_group", None)
    if node_group is None:
        return
    try:
        for item in node_group.interface.items_tree:
            if getattr(item, "item_type", None) != 'SOCKET':
                continue
            if getattr(item, "in_out", None) != 'INPUT':
                continue
            if getattr(item, "name", "") != "Seed":
                continue
            try:
                modifier[item.identifier] = int(seed_value)
                return
            except Exception:
                continue
    except Exception:
        pass


def _secret_paint_attribute_collection(attribute):
    if attribute is None:
        return None

    data = getattr(attribute, "data", None)
    if data is not None and hasattr(data, "foreach_get"):
        return data

    if hasattr(attribute, "foreach_get"):
        return attribute

    position_data = getattr(attribute, "position_data", None)
    if position_data is not None and hasattr(position_data, "foreach_get"):
        return position_data

    raise TypeError(f"Unsupported attribute container: {type(attribute).__name__}")


def _secret_paint_attribute_array(attribute, width=1):
    data = _secret_paint_attribute_collection(attribute)
    if data is None:
        return []

    values = [0.0] * (len(data) * width)
    field = "vector" if width == 3 else "value"
    if values:
        data.foreach_get(field, values)
    return values


def _secret_paint_set_attribute_array(attribute, values, width=1):
    data = _secret_paint_attribute_collection(attribute)
    if data is None:
        return

    field = "vector" if width == 3 else "value"
    if values:
        data.foreach_set(field, values)


def _secret_paint_curve_offsets(curves_data):
    curve_count = len(curves_data.curves)
    point_count = len(curves_data.points)
    if curve_count <= 0:
        return [0]

    values = [0] * (curve_count + 1)
    previous_end = 0
    fallback_points_length = 0
    if point_count > 0 and point_count % curve_count == 0:
        fallback_points_length = point_count // curve_count

    for curve_index, curve in enumerate(curves_data.curves):
        start = int(getattr(curve, "first_point_index", previous_end))
        points_length = int(getattr(curve, "points_length", fallback_points_length))

        if start < previous_end or start > point_count:
            start = previous_end
        if points_length < 0:
            points_length = 0

        end = min(point_count, start + points_length)
        if end < start:
            end = start

        values[curve_index] = start
        values[curve_index + 1] = end
        previous_end = end

    if values[-1] != point_count:
        values[-1] = point_count
    return values


def _secret_paint_sync_point_id_attribute(curves_data, curve_values):
    if curves_data is None or not hasattr(curves_data, "points"):
        return None

    point_count = len(curves_data.points)
    curve_count = len(curves_data.curves) if hasattr(curves_data, "curves") else 0
    if point_count <= 0 or curve_count <= 0:
        return None

    attribute = curves_data.attributes.get("id")
    if attribute is not None:
        try:
            if attribute.domain != 'POINT' or attribute.data_type != 'INT':
                curves_data.attributes.remove(attribute)
                attribute = None
        except Exception:
            attribute = None
    if attribute is None:
        try:
            attribute = curves_data.attributes.new("id", 'INT', 'POINT')
        except Exception:
            return None

    point_values = [0] * point_count
    offsets = _secret_paint_curve_offsets(curves_data)
    for curve_index in range(min(curve_count, len(curve_values))):
        stable_id = int(curve_values[curve_index])
        start = offsets[curve_index]
        end = offsets[curve_index + 1]
        for point_index in range(start, end):
            point_values[point_index] = stable_id
    _secret_paint_set_attribute_array(attribute, point_values, width=1)
    return attribute


def _secret_paint_curve_seed_values_from_attribute(curves_data, attribute_name):
    try:
        attribute = curves_data.attributes.get(attribute_name)
    except Exception:
        return []
    if attribute is None:
        return []

    try:
        domain = attribute.domain
    except Exception:
        domain = ""

    values = [int(value) for value in _secret_paint_attribute_array(attribute, width=1)]
    curve_count = len(curves_data.curves) if hasattr(curves_data, "curves") else 0
    if curve_count <= 0 or not values:
        return []

    if domain == 'CURVE':
        return values[:curve_count]

    if domain == 'POINT':
        offsets = _secret_paint_curve_offsets(curves_data)
        seeded_values = []
        for curve_index in range(curve_count):
            start = offsets[curve_index]
            if 0 <= start < len(values):
                seeded_values.append(values[start])
            else:
                seeded_values.append(0)
        return seeded_values

    if len(values) >= curve_count:
        return values[:curve_count]
    return []


def _secret_paint_curve_vector_values_from_attribute(curves_data, attribute_name):
    try:
        attribute = curves_data.attributes.get(attribute_name)
    except Exception:
        return None, []
    if attribute is None:
        return None, []

    try:
        if attribute.domain != 'CURVE' or attribute.data_type != 'FLOAT_VECTOR':
            return attribute, []
    except Exception:
        pass

    values = [float(value) for value in _secret_paint_attribute_array(attribute, width=3)]
    curve_count = len(curves_data.curves) if hasattr(curves_data, "curves") else 0
    needed_values = curve_count * 3
    if len(values) < needed_values:
        values.extend([0.0] * (needed_values - len(values)))
    elif len(values) > needed_values:
        values = values[:needed_values]
    return attribute, values


def _secret_paint_curve_root_position_values(curves_data):
    position_data = getattr(curves_data, "position_data", None)
    if position_data is None or not hasattr(curves_data, "curves"):
        return []

    positions = _secret_paint_attribute_array(position_data, width=3)
    offsets = _secret_paint_curve_offsets(curves_data)
    curve_count = len(curves_data.curves)
    root_values = [0.0] * (curve_count * 3)

    for curve_index in range(curve_count):
        start = offsets[curve_index]
        value_index = curve_index * 3
        position_index = start * 3
        if position_index + 2 >= len(positions):
            continue
        root_values[value_index:value_index + 3] = positions[position_index:position_index + 3]

    return root_values


def _secret_paint_sync_stable_root_position_attribute(curves_data, stable_curve_values=None):
    if curves_data is None or not hasattr(curves_data, "curves"):
        return []

    curve_count = len(curves_data.curves)
    if curve_count <= 0:
        return []

    if stable_curve_values is None or len(stable_curve_values) < curve_count:
        stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
            curves_data,
            SECRET_PAINT_STABLE_ID_ATTRIBUTE,
        )
    if len(stable_curve_values) < curve_count:
        stable_curve_values = list(stable_curve_values) + ([0] * (curve_count - len(stable_curve_values)))

    attribute, existing_values = _secret_paint_curve_vector_values_from_attribute(
        curves_data,
        SECRET_PAINT_STABLE_ROOT_POSITION_ATTRIBUTE,
    )
    if attribute is not None:
        try:
            if attribute.domain != 'CURVE' or attribute.data_type != 'FLOAT_VECTOR':
                curves_data.attributes.remove(attribute)
                attribute = None
                existing_values = []
        except Exception:
            attribute = None
            existing_values = []

    current_root_values = _secret_paint_curve_root_position_values(curves_data)
    existing_by_id = {}
    if existing_values:
        for curve_index in range(min(curve_count, len(stable_curve_values))):
            stable_id = int(stable_curve_values[curve_index])
            if stable_id == 0:
                continue
            value_index = curve_index * 3
            existing_by_id[stable_id] = tuple(existing_values[value_index:value_index + 3])

    final_values = [0.0] * (curve_count * 3)
    for curve_index in range(curve_count):
        stable_id = int(stable_curve_values[curve_index]) if curve_index < len(stable_curve_values) else 0
        value_index = curve_index * 3
        root_position = existing_by_id.get(stable_id)
        if root_position is None:
            root_position = current_root_values[value_index:value_index + 3]
        final_values[value_index:value_index + 3] = root_position

    if attribute is None:
        try:
            attribute = curves_data.attributes.new(
                SECRET_PAINT_STABLE_ROOT_POSITION_ATTRIBUTE,
                'FLOAT_VECTOR',
                'CURVE',
            )
        except Exception:
            return final_values

    _secret_paint_set_attribute_array(attribute, final_values, width=3)
    return final_values


def _secret_paint_apply_stable_curve_values(curves_data, stable_curve_values, sync_point_ids=True):
    if curves_data is None or not hasattr(curves_data, "curves"):
        return []

    curve_count = len(curves_data.curves)
    if curve_count <= 0:
        return []

    final_values = [int(value) for value in list(stable_curve_values or [])[:curve_count]]
    if len(final_values) < curve_count:
        final_values.extend([0] * (curve_count - len(final_values)))

    stable_attr = curves_data.attributes.get(SECRET_PAINT_STABLE_ID_ATTRIBUTE)
    if stable_attr is not None:
        try:
            if stable_attr.domain != 'CURVE' or stable_attr.data_type != 'INT':
                curves_data.attributes.remove(stable_attr)
                stable_attr = None
        except Exception:
            stable_attr = None
    if stable_attr is None:
        stable_attr = curves_data.attributes.new(SECRET_PAINT_STABLE_ID_ATTRIBUTE, 'INT', 'CURVE')

    _secret_paint_set_attribute_array(stable_attr, final_values, width=1)
    if sync_point_ids:
        _secret_paint_sync_point_id_attribute(curves_data, final_values)
    _secret_paint_sync_stable_root_position_attribute(curves_data, final_values)
    curves_data[SECRET_PAINT_STABLE_IDS_MIGRATED_PROP] = True
    curves_data[SECRET_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP] = int(curve_count)
    curves_data[SECRET_PAINT_WORLD_STABLE_IDS_READY_PROP] = True

    positive_ids = [value for value in final_values if value > 0]
    if positive_ids:
        curves_data[SECRET_PAINT_WORLD_NEXT_STABLE_ID_PROP] = max(positive_ids) + 1

    try:
        curves_data.update_tag()
    except Exception:
        pass
    return final_values


def _secret_paint_remove_attribute_if_present(curves_data, attribute_name):
    if curves_data is None:
        return
    try:
        attribute = curves_data.attributes.get(attribute_name)
    except Exception:
        return
    if attribute is None:
        return
    try:
        curves_data.attributes.remove(attribute)
    except Exception:
        pass


def _secret_paint_curve_data_is_editable(curves_data):
    if curves_data is None:
        return False
    try:
        if curves_data.library is not None:
            return False
    except Exception:
        pass
    return True


def _secret_paint_legacy_manual_random_id_values(curves_data):
    if curves_data is None or not hasattr(curves_data, "curves"):
        return []

    curve_count = len(curves_data.curves)
    if curve_count <= 0:
        return []

    offsets = _secret_paint_curve_offsets(curves_data)
    fallback_values = [int(offsets[curve_index]) for curve_index in range(curve_count)]
    try:
        attribute = curves_data.attributes.get("id")
    except Exception:
        attribute = None
    if attribute is None:
        return fallback_values

    try:
        domain = attribute.domain
    except Exception:
        domain = ""

    raw_values = [int(value) for value in _secret_paint_attribute_array(attribute, width=1)]
    if not raw_values:
        return fallback_values

    final_values = []
    if domain == 'POINT':
        for curve_index in range(curve_count):
            start = offsets[curve_index]
            value = raw_values[start] if 0 <= start < len(raw_values) else 0
            final_values.append(int(value) if int(value) != 0 else fallback_values[curve_index])
        return final_values

    if domain == 'CURVE':
        for curve_index in range(curve_count):
            value = raw_values[curve_index] if curve_index < len(raw_values) else 0
            final_values.append(int(value) if int(value) != 0 else fallback_values[curve_index])
        return final_values

    return fallback_values


def _secret_paint_migrate_legacy_curve_ids(
    obj,
    allow_fallback=True,
    preserve_existing_id=False,
    use_legacy_manual_random_ids=False,
):
    if obj is None or getattr(obj, "type", "") != "CURVES":
        return False
    try:
        if obj.library is not None:
            return False
    except Exception:
        pass

    curves_data = getattr(obj, "data", None)
    if not _secret_paint_curve_data_is_editable(curves_data) or not hasattr(curves_data, "curves"):
        return False

    curve_count = len(curves_data.curves)
    if curve_count <= 0:
        return False

    if use_legacy_manual_random_ids:
        legacy_manual_values = _secret_paint_legacy_manual_random_id_values(curves_data)
        if len(legacy_manual_values) == curve_count:
            _secret_paint_apply_stable_curve_values(
                curves_data,
                legacy_manual_values,
                sync_point_ids=not preserve_existing_id,
            )
            return True

    stable_values = _secret_paint_curve_seed_values_from_attribute(
        curves_data,
        SECRET_PAINT_STABLE_ID_ATTRIBUTE,
    )
    if len(stable_values) == curve_count:
        curves_data[SECRET_PAINT_STABLE_IDS_MIGRATED_PROP] = True
        _secret_paint_apply_stable_curve_values(
            curves_data,
            stable_values,
            sync_point_ids=not preserve_existing_id,
        )
        return True

    legacy_values = _secret_paint_curve_seed_values_from_attribute(curves_data, "id")
    used_existing_id = len(legacy_values) == curve_count
    if len(legacy_values) == curve_count:
        final_values = [int(value) for value in legacy_values]
    else:
        if not allow_fallback:
            return False
        final_values = list(range(curve_count))

    _secret_paint_apply_stable_curve_values(
        curves_data,
        final_values,
        sync_point_ids=not (preserve_existing_id and used_existing_id),
    )
    return True


def _secret_paint_instance_transform_records(context, obj):
    try:
        obj.update_tag()
        obj.data.update_tag()
        context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
    except Exception:
        return []

    records = []
    try:
        instances = depsgraph.object_instances
    except Exception:
        return []
    for instance in instances:
        if not getattr(instance, "is_instance", False) or instance.parent is None:
            continue
        parent = getattr(instance.parent, "original", instance.parent)
        if parent != obj:
            continue
        source = getattr(instance.instance_object, "original", instance.instance_object)
        matrix = tuple(
            float(instance.matrix_world[row][column])
            for row in range(4)
            for column in range(4)
        )
        records.append((getattr(source, "name", ""), matrix))
    return sorted(records, key=lambda record: (record[0], record[1][3], record[1][7], record[1][11]))


def _secret_paint_instance_transform_delta(reference_records, candidate_records):
    if len(reference_records) != len(candidate_records):
        return float("inf")
    if not reference_records:
        return None
    max_delta = 0.0
    for (reference_source, reference_matrix), (candidate_source, candidate_matrix) in zip(
        reference_records,
        candidate_records,
    ):
        if reference_source != candidate_source:
            return float("inf")
        position_delta = max(
            abs(reference_matrix[index] - candidate_matrix[index])
            for index in (3, 7, 11)
        )
        if position_delta > 0.00002:
            return float("inf")
        max_delta = max(
            max_delta,
            max(abs(value - candidate) for value, candidate in zip(reference_matrix, candidate_matrix)),
        )
    return max_delta


def _secret_paint_baked_manual_uses_legacy_ids(context, obj, modifier):
    marker = getattr(obj, "data", {}).get(SECRET_PAINT_MANUAL_LEGACY_IDS_PROP, None)
    if marker is not None:
        return bool(marker)

    original_legacy = _secret_paint_modifier_legacy_procedural_ids(modifier)
    original_baked = bool(_secret_paint_modifier_input_by_name(
        modifier,
        SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
        False,
    ))
    stable_values = _secret_paint_curve_seed_values_from_attribute(
        obj.data,
        SECRET_PAINT_STABLE_ID_ATTRIBUTE,
    )
    has_legacy_sequential_ids = (
        bool(stable_values)
        and stable_values == list(range(len(stable_values)))
    )
    reference_records = _secret_paint_instance_transform_records(context, obj)
    if not reference_records:
        return has_legacy_sequential_ids

    modern_records = []
    legacy_records = []
    try:
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
            False,
        )
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
            False,
        )
        modern_records = _secret_paint_instance_transform_records(context, obj)
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
            True,
        )
        legacy_records = _secret_paint_instance_transform_records(context, obj)
    finally:
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
            original_legacy,
        )
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
            original_baked,
        )
        _secret_paint_instance_transform_records(context, obj)

    modern_delta = _secret_paint_instance_transform_delta(reference_records, modern_records)
    legacy_delta = _secret_paint_instance_transform_delta(reference_records, legacy_records)
    if legacy_delta is None:
        return False
    if modern_delta is None:
        return True
    if legacy_delta + 0.00002 < modern_delta:
        return True
    if modern_delta + 0.00002 < legacy_delta:
        return False
    return has_legacy_sequential_ids


def _secret_paint_prepare_legacy_node_upgrade(context):
    main_tree = bpy.data.node_groups.get("Secret Paint")
    old_version = _secret_paint_node_tree_version(main_tree)
    try:
        old_version_number = int(old_version)
    except Exception:
        old_version_number = 0

    should_migrate_curve_ids = old_version_number < 40
    generator_tree = _secret_paint_get_generator_node_group()
    should_mark_legacy_procedural = (
        old_version_number < SECRET_PAINT_NODE_VERSION
        and _secret_paint_generator_uses_legacy_random_id(generator_tree)
    )
    should_recover_baked_manual_conversion = old_version_number == 42
    if (
        not should_migrate_curve_ids
        and not should_mark_legacy_procedural
        and not should_recover_baked_manual_conversion
    ):
        return []

    legacy_objects = []
    try:
        objects = list(bpy.data.objects)
    except Exception:
        objects = []

    for obj in objects:
        if getattr(obj, "type", "") != "CURVES":
            continue
        modifier = _secret_paint_modifier(obj)
        if modifier is None:
            continue
        try:
            is_procedural = bool(modifier["Input_69"])
        except Exception:
            is_procedural = False
        if should_migrate_curve_ids:
            _secret_paint_migrate_legacy_curve_ids(
                obj,
                allow_fallback=not is_procedural,
                preserve_existing_id=should_mark_legacy_procedural and is_procedural,
                use_legacy_manual_random_ids=not is_procedural,
            )
        if should_mark_legacy_procedural and is_procedural:
            legacy_objects.append(obj)
        if should_recover_baked_manual_conversion and not is_procedural:
            was_baked = bool(_secret_paint_modifier_input_by_name(
                modifier,
                SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
                False,
            ))
            if not was_baked:
                continue
            ensure_secret_paint_system_stable_root_positions(obj)
            recovered_legacy_ids = _secret_paint_baked_manual_uses_legacy_ids(context, obj, modifier)
            obj.data[SECRET_PAINT_MANUAL_LEGACY_IDS_PROP] = bool(recovered_legacy_ids)
            if recovered_legacy_ids:
                legacy_objects.append(obj)

    return legacy_objects


def _secret_paint_apply_legacy_procedural_flags(legacy_objects):
    for obj in list(legacy_objects or []):
        try:
            if obj is None or obj.name not in bpy.data.objects:
                continue
        except Exception:
            continue
        modifier = _secret_paint_modifier(obj)
        if modifier is None:
            continue
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
            True,
        )


def _secret_paint_disable_obsolete_manual_baked_transforms():
    for obj in list(bpy.data.objects):
        if getattr(obj, "type", "") != "CURVES":
            continue
        modifier = _secret_paint_modifier(obj)
        if modifier is None:
            continue
        try:
            is_procedural = bool(modifier["Input_69"])
        except Exception:
            is_procedural = False
        if is_procedural:
            continue
        has_obsolete_bake = bool(_secret_paint_modifier_input_by_name(
            modifier,
            SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
            False,
        ))
        has_legacy_flag = _secret_paint_modifier_legacy_procedural_ids(modifier)
        if not has_obsolete_bake and not has_legacy_flag:
            continue
        _secret_paint_set_modifier_input_by_name(
            modifier,
            SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
            False,
        )
        ensure_secret_paint_system_stable_root_positions(obj)


def ensure_secret_paint_system_stable_root_positions(system_obj, stable_curve_values=None):
    curves_data = getattr(system_obj, "data", None) if system_obj is not None else None
    if curves_data is None:
        return []
    return _secret_paint_sync_stable_root_position_attribute(curves_data, stable_curve_values)


def _secret_paint_evaluated_curve_int_attribute_values(context, system_obj, attribute_name):
    if context is None or system_obj is None:
        return []

    try:
        if getattr(context, "view_layer", None) is not None:
            context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = system_obj.evaluated_get(depsgraph)
        eval_data = getattr(eval_obj, "data", None)
        eval_attributes = getattr(eval_data, "attributes", None)
        if eval_attributes is None:
            return []
        attribute = eval_attributes.get(attribute_name)
        if attribute is None:
            return []
        try:
            if attribute.domain != 'CURVE':
                return []
        except Exception:
            pass
        return [int(value) for value in _secret_paint_attribute_array(attribute, width=1)]
    except Exception:
        return []


def _secret_paint_evaluated_curve_seed_values_from_attribute(context, system_obj, attribute_name):
    if context is None or system_obj is None:
        return []

    try:
        if getattr(context, "view_layer", None) is not None:
            context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = system_obj.evaluated_get(depsgraph)
        eval_data = getattr(eval_obj, "data", None)
        eval_attributes = getattr(eval_data, "attributes", None)
        if eval_attributes is None:
            return []
        attribute = eval_attributes.get(attribute_name)
        if attribute is None:
            return []

        try:
            domain = attribute.domain
        except Exception:
            domain = ""

        values = [int(value) for value in _secret_paint_attribute_array(attribute, width=1)]
        curve_count = len(eval_data.curves) if hasattr(eval_data, "curves") else 0
        if curve_count <= 0 or not values:
            return []

        if domain == 'CURVE':
            return values[:curve_count]

        if domain == 'POINT':
            offsets = _secret_paint_curve_offsets(eval_data)
            seeded_values = []
            for curve_index in range(curve_count):
                start = offsets[curve_index]
                if 0 <= start < len(values):
                    seeded_values.append(values[start])
                else:
                    seeded_values.append(0)
            return seeded_values

        if len(values) >= curve_count:
            return values[:curve_count]
    except Exception:
        return []
    return []


def _secret_paint_evaluated_curves_counts(context, system_obj):
    if context is None or system_obj is None:
        return 0, 0

    try:
        if getattr(context, "view_layer", None) is not None:
            context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = system_obj.evaluated_get(depsgraph)
        eval_data = getattr(eval_obj, "data", None)
        if eval_data is None:
            return 0, 0
        curve_count = len(eval_data.curves) if hasattr(eval_data, "curves") else 0
        point_count = len(eval_data.points) if hasattr(eval_data, "points") else 0
        return curve_count, point_count
    except Exception:
        return 0, 0


def _secret_paint_evaluated_curve_root_position_values(context, system_obj):
    if context is None or system_obj is None:
        return []

    try:
        if getattr(context, "view_layer", None) is not None:
            context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = system_obj.evaluated_get(depsgraph)
        eval_data = getattr(eval_obj, "data", None)
        if eval_data is None:
            return []
        return _secret_paint_curve_root_position_values(eval_data)
    except Exception:
        return []


def _secret_paint_curve_root_positions_match(raw_values, eval_values, curve_count, tolerance=0.00001):
    needed_values = int(curve_count) * 3
    if curve_count <= 0:
        return False
    if len(raw_values) < needed_values or len(eval_values) < needed_values:
        return False

    for value_index in range(needed_values):
        if abs(float(raw_values[value_index]) - float(eval_values[value_index])) > tolerance:
            return False
    return True


def _secret_paint_seed_stable_curve_attribute(context, obj, prefer_evaluated=False, sync_point_ids=True):
    curves_data = getattr(obj, "data", None)
    if curves_data is None or not hasattr(curves_data, "curves"):
        return []

    curve_count = len(curves_data.curves)
    if curve_count <= 0:
        return []

    final_values = [0] * curve_count
    used_ids = set()
    invalid_indices = list(range(curve_count))

    candidate_sources = [
        _secret_paint_curve_seed_values_from_attribute(curves_data, SECRET_PAINT_STABLE_ID_ATTRIBUTE),
        _secret_paint_evaluated_curve_int_attribute_values(context, obj, SECRET_PAINT_STABLE_ID_ATTRIBUTE)[:curve_count],
        _secret_paint_curve_seed_values_from_attribute(curves_data, "id"),
    ]
    if prefer_evaluated:
        candidate_sources[0], candidate_sources[1] = candidate_sources[1], candidate_sources[0]

    for candidate_values in candidate_sources:
        if not candidate_values:
            continue
        for curve_index in list(invalid_indices):
            if curve_index >= len(candidate_values):
                continue
            candidate_id = int(candidate_values[curve_index])
            if candidate_id == 0 or candidate_id in used_ids:
                continue
            final_values[curve_index] = candidate_id
            used_ids.add(candidate_id)
            invalid_indices.remove(curve_index)

    next_id = max(1, (max(used_ids) + 1) if used_ids else 1)
    for curve_index in invalid_indices:
        while next_id in used_ids:
            next_id += 1
        final_values[curve_index] = next_id
        used_ids.add(next_id)
        next_id += 1

    stable_attr = curves_data.attributes.get(SECRET_PAINT_STABLE_ID_ATTRIBUTE)
    if stable_attr is None:
        stable_attr = curves_data.attributes.new(SECRET_PAINT_STABLE_ID_ATTRIBUTE, 'INT', 'CURVE')
    _secret_paint_set_attribute_array(stable_attr, final_values, width=1)
    if sync_point_ids:
        _secret_paint_sync_point_id_attribute(curves_data, final_values)
    _secret_paint_sync_stable_root_position_attribute(curves_data, final_values)
    curves_data[SECRET_PAINT_STABLE_IDS_MIGRATED_PROP] = True
    curves_data[SECRET_PAINT_WORLD_STABLE_IDS_READY_PROP] = True
    positive_ids = [int(value) for value in final_values if int(value) > 0]
    if positive_ids:
        curves_data[SECRET_PAINT_WORLD_NEXT_STABLE_ID_PROP] = max(positive_ids) + 1
    try:
        curves_data.update_tag()
    except Exception:
        pass
    return final_values


def _secret_paint_snap_curves_to_surface_if_armature(obj, pickup_trace=None):
    if not obj.parent or not obj.parent.modifiers:
        return
    for mod in obj.parent.modifiers:
        if mod.type == "ARMATURE":
            snap_to_surface_start = time.perf_counter()
            bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
            if pickup_trace:
                pickup_trace.action("apply_paint.snap_curves_to_surface", snap_to_surface_start, label=obj.name)
            break


def _secret_paint_reapply_conversion_stable_ids(context, converted_objects):
    converted_objects = [obj for obj in converted_objects if obj is not None and obj.name in bpy.data.objects]
    if not converted_objects:
        return

    try:
        if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    apply_ids_node = _secret_paint_get_apply_ids_node_group()
    for obj in converted_objects:
        if getattr(obj, "type", "") != "CURVES" or not getattr(obj, "modifiers", None):
            continue
        keep_legacy_procedural_ids = _secret_paint_modifier_legacy_procedural_ids(obj.modifiers[0])
        try:
            bpy.context.view_layer.objects.active = obj
            for selected in bpy.context.selected_objects:
                selected.select_set(False)
            obj.select_set(True)
        except Exception:
            pass

        stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
            obj.data,
            SECRET_PAINT_STABLE_ID_ATTRIBUTE,
        )
        if not _secret_paint_stable_curve_values_are_usable(obj.data, stable_curve_values):
            _secret_paint_remove_attribute_if_present(obj.data, SECRET_PAINT_STABLE_ID_ATTRIBUTE)
            _secret_paint_remove_attribute_if_present(obj.data, SECRET_PAINT_STABLE_ROOT_POSITION_ATTRIBUTE)
            apply_ids_modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
            apply_ids_modifier.node_group = bpy.data.node_groups.get(apply_ids_node.name)
            _secret_paint_set_apply_ids_seed(apply_ids_modifier, obj.modifiers[0]["Input_80"])
            if bpy.app.version_string >= "4.0.0":
                obj.modifiers.move(len(obj.modifiers) - 1, 0)
            elif bpy.app.version_string < "4.0.0":
                bpy.ops.object.modifier_move_up({'object': obj}, modifier=apply_ids_modifier.name)
            _secret_paint_apply_geometry_nodes_modifier(
                context,
                obj,
                apply_ids_modifier,
                restore_materials=False,
            )
            stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
                obj.data,
                SECRET_PAINT_STABLE_ID_ATTRIBUTE,
            )
        if not _secret_paint_stable_curve_values_are_usable(obj.data, stable_curve_values):
            stable_curve_values = _secret_paint_seed_stable_curve_attribute(context, obj)
        if stable_curve_values:
            _secret_paint_apply_stable_curve_values(obj.data, stable_curve_values)
        try:
            _secret_paint_set_modifier_input_by_name(
                obj.modifiers[0],
                SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
                keep_legacy_procedural_ids,
            )
            obj.modifiers[0]["Input_98"] = False
            obj.modifiers[0]["Input_97"] = None
        except Exception:
            pass
        curve_count, point_count = _secret_paint_get_curves_counts(obj.data)
        _secret_paint_store_id_cache(obj.data, curve_count, point_count)


def _secret_paint_face_projection_axes(normal):
    abs_x = abs(normal.x)
    abs_y = abs(normal.y)
    abs_z = abs(normal.z)
    if abs_x >= abs_y and abs_x >= abs_z:
        return (1, 2)
    if abs_y >= abs_x and abs_y >= abs_z:
        return (0, 2)
    return (0, 1)


def _secret_paint_fast_reproject_surface_uvs(surface):
    mesh = surface.data
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.normal_update()
        uv_layer = bm.loops.layers.uv.get(SECRET_PAINT_AUTO_UV_NAME)
        if uv_layer is None:
            uv_layer = bm.loops.layers.uv.new(SECRET_PAINT_AUTO_UV_NAME)

        bm.faces.ensure_lookup_table()
        face_count = len(bm.faces)
        if face_count == 0:
            bm.to_mesh(mesh)
            mesh.update()
            _secret_paint_store_auto_uv_cache(mesh)
            return

        grid_size = max(1, math.ceil(math.sqrt(face_count)))
        cell_size = 1.0 / grid_size
        margin = cell_size * 0.05
        usable_size = max(cell_size - (margin * 2.0), 1e-6)

        for face_index, face in enumerate(bm.faces):
            axis_u, axis_v = _secret_paint_face_projection_axes(face.normal)
            coords = [Vector((loop.vert.co[axis_u], loop.vert.co[axis_v])) for loop in face.loops]
            min_u = min(coord.x for coord in coords)
            max_u = max(coord.x for coord in coords)
            min_v = min(coord.y for coord in coords)
            max_v = max(coord.y for coord in coords)
            span_u = max(max_u - min_u, 1e-9)
            span_v = max(max_v - min_v, 1e-9)

            cell_x = face_index % grid_size
            cell_y = face_index // grid_size
            base_u = (cell_x * cell_size) + margin
            base_v = (cell_y * cell_size) + margin

            for loop, coord in zip(face.loops, coords):
                local_u = 0.5 if span_u <= 1e-8 else (coord.x - min_u) / span_u
                local_v = 0.5 if span_v <= 1e-8 else (coord.y - min_v) / span_v
                loop[uv_layer].uv = Vector((
                    base_u + (local_u * usable_size),
                    base_v + (local_v * usable_size),
                ))

        bm.to_mesh(mesh)
        mesh.update()
        _secret_paint_store_auto_uv_cache(mesh)
    finally:
        bm.free()
# file_path = Path(resource_path('USER')) / "scripts/addons" / "Secret Paint" / "Secret Paint.blend"       #C:\Users\loren\AppData\Roaming\Blender Foundation\Blender\4.0\scripts\addons\orenpaint\orenpaint.blend
# for mod in addon_utils.modules():
#     if mod.bl_info.get("name") == "Secret Paint":
#         file_path = os.path.dirname(mod.__file__) + "\Secret Paint.blend"
#         break

# auto_updater_status = True
# if blender_version >= "4.2.0" and bpy.app.online_access == False: auto_updater_status = False
# if auto_updater_status == True: from . import addon_updater_ops
# import bpy.utils.previews  # CUSTOM ICONS VIEW_MT_PIE_orencloudpie




# # #IMPORT SIDECAR .PY (metdhod 2, registers classes but can't reload addon while developing)
# # from . import paint
# # modul = (paint,)
# # IMPORT SIDECAR .PY (method1: allows reloading, but doesn't register the classes)
# # from . import paint
# import importlib
# addon_folder = 'orencloud private'
# modules = ("paint",)  #('.paint',)
# def import_modules():
#     for mod in modules:
#         importlib.import_module("."+mod, addon_folder)
# def reimport_modules(): # Reimporting modules during addon development
#     for mod in modules:
#         # want_reload_module = importlib.import_module(mod, addon_folder)
#         want_reload_module = importlib.import_module("."+mod, addon_folder)
#         importlib.reload(want_reload_module)
# import_modules()
# reimport_modules() #only for developing addon, reloading addon re imports all classes










































































class orencurvepanel(bpy.types.Panel):
    bl_label = "Secret Paint"
    bl_idname = "OREN_PT_OrencurvePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Secret"

    def draw(self, context):
        layout = self.layout
        active_object = context.active_object
        selected_objects = context.selected_objects
        active_weight_group_name = ""
        try:
            if context.object and context.object.mode == "WEIGHT_PAINT" and active_object and active_object.vertex_groups.active:
                active_weight_group_name = active_object.vertex_groups.active.name
        except Exception:
            active_weight_group_name = ""

        # row = layout.row()
        # row.label(text= "Draw curve from object", icon= 'OBJECT_ORIGIN')

        paint_mode_active = _secret_paint_panel_is_paint_mode(context)
        paint_button = layout.column(align=True)
        paint_button.scale_y = 2.2  # Adjust the height of the button
        paint_button_row = paint_button.row(align=True)
        paint_button_row.operator_context = 'INVOKE_DEFAULT'
        paint_button_row.alert = paint_mode_active
        paint_op = paint_button_row.operator(
            "secret.paint",
            icon='BRUSH_DATA',
            text="Exit Paint" if paint_mode_active else "Paint",
        ) #GP_MULTIFRAME_EDITING
        paint_op.exit_paint_mode = paint_mode_active
        paint_op.use_selected_source = paint_mode_active
        # if bl_info["name"] == "orencloud private":
        #     row.scale_y = 1.3  # Adjust the height of the button
        #     row.operator("oren.shared_material", icon= 'MATERIAL')
        #     row.scale_x = 0.3  # Adjust the height of the button
        #     row.prop(context.scene.mypropertieslist, "shared_material_index", expand=True, text="")
        layout.separator()



        # CREATE ROWS IN PANEL  #0.4 milliseconds in total
        def configure_side_panel_row(outer_row, *, scale_y):
            outer_row.scale_y = scale_y
            label_row = outer_row.row(align=True)
            action_row = outer_row.row(align=True)
            action_row.ui_units_x = SECRET_PAINT_PANEL_ACTION_STRIP_UNITS
            return outer_row, label_row, action_row

        def split_side_panel_row(parent_layout, *, scale_y):
            return configure_side_panel_row(parent_layout.row(align=True), scale_y=scale_y)

        def action_slot(action_row):
            slot = action_row.row(align=True)
            slot.ui_units_x = SECRET_PAINT_PANEL_ACTION_SLOT_UNITS
            return slot

        def action_button(alert_row, action_row, operator_id, *, icon, text=""):
            slot = action_slot(action_row)
            slot.alert = alert_row.alert
            return slot.operator(operator_id, text=text, icon=icon)

        def action_prop(alert_row, action_row, data, property_name, *, icon, text=""):
            slot = action_slot(action_row)
            slot.alert = alert_row.alert
            try:
                slot.prop(data, property_name, text=text, icon=icon, toggle=True)
            except (ReferenceError, RuntimeError):
                slot.enabled = False
                slot.label(text="", icon='BLANK1')

        def action_spacer(alert_row, action_row):
            slot = action_slot(action_row)
            slot.alert = alert_row.alert
            slot.enabled = False
            slot.label(text="", icon='BLANK1')

        def list_hair(row_entry, bgroup, parent_layout):
            sibling = row_entry.get("object")
            sibling_name = row_entry.get("name") or _side_panel_rna_name(sibling)
            if not sibling_name or not _side_panel_object_alive(sibling):
                return
            # if sibling.name in bpy.context.view_layer.objects and sibling.type == 'CURVES' and sibling.modifiers:
            #     for modifier in sibling.modifiers:
            #         if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("orenpaint"): #modifier.node_group.name == "orenpaint":


            row, label_row, action_row = split_side_panel_row(parent_layout, scale_y=0.92)

            dragging_this_row = _SIDE_PANEL_DRAG_OBJECT_NAME == sibling_name

            namerow = row_entry["display_name"]
            icon = row_entry["icon"]

            if active_object:
                try:
                    row_selected = sibling in selected_objects
                    row_active = sibling == active_object
                except (ReferenceError, RuntimeError):
                    return
                if row_selected or \
                        row_active or \
                        context.object.mode == "WEIGHT_PAINT" and row_entry["vertex_attribute_name"] == active_weight_group_name or \
                        dragging_this_row:
                    # icon = "RESTRICT_SELECT_ON"
                    row.alert = True
                else: row.alert = False
            else:
                row.alert = dragging_this_row

            try:
                n_of_instances, n_of_instancesFinal = _get_side_panel_instance_count_cached(sibling)
            except (ReferenceError, RuntimeError):
                return
            label_row.alert = row.alert
            select_button = label_row.operator(
                "secret.panel_select_object",
                text=str(namerow)+" ["+str(n_of_instancesFinal)+"]",
                icon=icon,
            )
            select_button.object_name = sibling_name

            # # Toggle hair button ALT CLICK TO SWITCH
            # if not sibling.modifiers["GeometryNodes"]["Input_69"]: row.alert = True
            # else: row.alert = False
            # hair_button = row.operator("oren.applypaint", text="", icon='CURVES_DATA' if row.alert else 'SHADERFX')  #BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL
            # hair_button.object_name = sibling.name

            if not row_entry["procedural_enabled"]: row.alert = True
            else: row.alert = False
            action_prop(row, action_row, sibling, SECRET_PAINT_PANEL_APPLY_PROP, icon='CURVES_DATA')  # BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL

            if not row_entry["procedural_enabled"]: row.alert = False
            else: row.alert = True
            action_prop(row, action_row, sibling, SECRET_PAINT_PANEL_PROCEDURAL_PROP, icon='SHADERFX')  # BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL

            if row_entry["vertex_attribute_name"] and row_entry["procedural_enabled"]: row.alert = True
            else: row.alert = False
            # Toggle vertex button
            action_prop(row, action_row, sibling, SECRET_PAINT_PANEL_VERTEX_PROP, icon='MOD_VERTEX_WEIGHT' if row_entry["vertex_use_attribute"] else 'GROUP_VERTEX')

            row.alert = row_entry["render_alert"]
            render_icon = row_entry["render_icon"]
            action_prop(row, action_row, sibling, SECRET_PAINT_PANEL_RENDER_PROP, icon=render_icon)

            row.alert = row_entry["bounds_alert"]
            action_prop(row, action_row, sibling, SECRET_PAINT_PANEL_BOUNDS_PROP, icon=row_entry["bounds_icon"])

            row.alert = row_entry["mask_alert"]
            # Toggle mask button
            action_prop(row, action_row, sibling, SECRET_PAINT_PANEL_MASK_PROP, icon='CLIPUV_HLT' if row.alert else "CLIPUV_DEHLT")


            # #DENSITY SLIDER
            # # row.scale_x = 1.2  # Adjust the height of the button
            # row.prop(context.scene.mypropertieslist, "seltoactiveextrusion")

            # PANEL WITH SEPARATION
            # import bpy
            #
            # class OBJECT_PT_CollapsibleListPanel(bpy.types.Panel):
            #     bl_label = "Collapsible List Panel"
            #     bl_idname = "OBJECT_PT_collapsible_list_panel"
            #     bl_space_type = "VIEW_3D"
            #     bl_region_type = "UI"
            #     bl_category = "Custom Panel"
            #
            #     def draw(self, context):
            #         layout = self.layout
            #         scene = context.scene
            #
            #         # Create a collapsible list with selected objects
            #         box = layout.box()
            #         box.prop(scene, "is_collapsed", text="Selected Objects", icon="TRIA_DOWN" if scene.is_collapsed else "TRIA_RIGHT")
            #
            #         if scene.is_collapsed:
            #             for obj in bpy.context.selected_objects:
            #                 box.label(text=obj.name)
            #
            #
            # def update_collapsed_list(self, context):
            #     # Empty function to be used as a callback for the property update
            #     pass
            #
            # def register():
            #     bpy.types.Scene.is_collapsed = bpy.props.BoolProperty(default=False, update=update_collapsed_list)
            #     bpy.utils.register_class(OBJECT_PT_CollapsibleListPanel)
            #
            # def unregister():
            #     bpy.utils.unregister_class(OBJECT_PT_CollapsibleListPanel)
            #     del bpy.types.Scene.is_collapsed
            #
            # if __name__ == "__main__":
            #     register()

        def list_biomes(biome_entry,row):
            bgroup = biome_entry["bgroup"]
            hair_in_bgroup = biome_entry["rows"]
            # if bgroup.name in bpy.context.view_layer.objects and bgroup.type == 'CURVES' and bgroup.modifiers:
            #     for modifier in bgroup.modifiers:
            #         if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("orenpaint"): #modifier.node_group.name == "orenpaint":

            # row = layout.row(align=True) #PASSED FROM ARGUMENT
            # row.scale_y = 1.4  # Adjust the height of the button
            row, label_row, action_row = configure_side_panel_row(row, scale_y=1.15)
            row.scale_x = 0.99  # Adjust the height of the button


            # ## Display bgroup's name as a label and make it selectable
            # # if bgroup == bpy.context.active_object: namerow = "(ACTIVE) " + bgroup.name
            # # else:namerow = bgroup.name
            # if bgroup.modifiers[0]["Input_2"]:
            #     namerow = bgroup.modifiers[0]["Input_2"].name
            #     if bgroup.modifiers[0]["Input_2"].type == "EMPTY":
            #         icon = "EMPTY_AXIS"
            #     else:
            #         icon = "OBJECT_DATA"
            # elif bgroup.modifiers[0]["Input_9"]:
            #     namerow = bgroup.modifiers[0]["Input_9"].name
            #     icon = "OUTLINER_COLLECTION"
            # else:
            #     namerow = "(empty)"
            #     icon = "OBJECT_DATA"
            #     # continue #if no brush obj, don't list
            # if bgroup in bpy.context.selected_objects or bgroup == bpy.context.active_object or \
            #         bpy.context.object.mode == "WEIGHT_PAINT" and bgroup.modifiers[0]["Input_83_attribute_name"] == bpy.context.active_object.vertex_groups.active.name:
            #     # icon = "RESTRICT_SELECT_ON"
            #     row.alert = True
            # else:
            #     row.alert = False
            # select_button = row.operator("object.select_object", text=str(namerow.name), icon=icon)

            #"TRY" BECAUSE WHEN OPENING AN OLD BLEND FILE, THE CODE WON'T FIND THE SOCKET FOR THE CUSTOM BIOME NAME UNTIL REIMPORTING THE NEW NODE TREE
            rename_active = bool(biome_entry.get("rename_active", False))
            row.alert = False
            label_row.alert = rename_active
            select_button = label_row.operator("secret.select_biome", text=biome_entry["label"])
            select_button.object_biome = str(bgroup)
            # select_button.object_biome = hair_in_bgroup

            delete_button = action_button(row, action_row, "secret.biome_delete", icon='TRASH')
            delete_button.object_biome = str(bgroup)
            action_spacer(row, action_row)

            # # Toggle hair button ALT CLICK TO SWITCH
            # if not bgroup.modifiers["GeometryNodes"]["Input_69"]: row.alert = True
            # else: row.alert = False
            # hair_button = row.operator("oren.applypaint", text="", icon='CURVES_DATA' if row.alert else 'SHADERFX')  #BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL
            # hair_button.object_name = bgroup.name

            # # if not bgroup.modifiers[0]["Input_69"]: row.alert = True
            # # else: row.alert = False
            # hair_button = row.operator("oren.applypaint", text="", icon='CURVES_DATA')  # BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL
            # # hair_button.object_name = bgroup.name

            # # if not bgroup.modifiers[0]["Input_69"]: row.alert = True
            # # else: row.alert = False
            # hair_button = row.operator("oren.applypaint", text="", icon='DUPLICATE')  # BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL
            # # hair_button.object_name = bgroup.name

            # if not bgroup.modifiers[0]["Input_69"]: row.alert = False
            # else: row.alert = True
            # procedural_button = row.operator("oren.toggle_procedural", text="", icon='SHADERFX')  # BRUSH_DATA  #OUTLINER_OB_CURVES #BRUSHES_ALL
            # procedural_button.object_name = bgroup.name


            #VERTEX BUTTON
            # if bgroup.modifiers[0]["Input_83_attribute_name"] and bgroup.modifiers[0]["Input_69"]: row.alert = True
            # else: row.alert = False
            # vertex_button = row.operator("oren.vertexgrouppaint", text="", icon='MOD_VERTEX_WEIGHT' if bgroup.modifiers[0]["Input_83_use_attribute"] else 'GROUP_VERTEX')
            vertex_button = action_button(row, action_row, "secret.vertexgrouppaint_biome", icon='GROUP_VERTEX')
            vertex_button.object_biome = str(bgroup)


            #RENDER BUTTON
            render_icon = biome_entry["render_icon"]
            row.alert = biome_entry["render_alert"]

            hide_buttonre = action_button(row, action_row, "secret.toggle_visibilityrender_biome", icon=render_icon)
            hide_buttonre.object_biome = str(bgroup)




            #BOUNDS BUTTON
            # row.alert = False
            # bounds_button = row.operator("secret.toggle_display_bounds_biome", text="", icon='SHADING_SOLID')
            row.alert = biome_entry["bounds_alert"]
            bounds_button = action_button(row, action_row, "secret.toggle_display_bounds_biome", icon='SHADING_BBOX' if row.alert else 'SHADING_SOLID')
            bounds_button.object_biome = str(bgroup)


            #MASK BUTTON
            row.alert = biome_entry["mask_alert"]
            mask_button = action_button(row, action_row, "object.secretpaint_viewport_mask_biome", icon='CLIPUV_HLT' if row.alert else "CLIPUV_DEHLT")
            mask_button.object_biome = str(bgroup)


        obj = context.object
        # global obj_parent
        # if obj and obj.type=="CURVES" and obj.parent: obj_parent = obj.parent
        # if bpy.context.active_object == None: obj = obj_parent

        if obj:
            layout_model = _get_side_panel_layout_model_cached(context, obj)



            # VISUALLY SEPARATE BIOMES BY VERTEX GROUP
            # all_vgroups=[]
            # hair_with_vgroups=[]
            # for hayr in hair[:]:
            #     if hayr[0].modifiers[0]["Input_83_attribute_name"]:
            #         if hayr[0].modifiers[0]["Input_83_attribute_name"] not in all_vgroups: all_vgroups.append(hayr[0].modifiers[0]["Input_83_attribute_name"])
            #         hair_with_vgroups.append(hayr)
            # for vgroup in all_vgroups:
            #     hair_with_this_vgroup = 0
            #     for hayr in hair_with_vgroups:
            #         if hayr[0].modifiers[0]["Input_83_attribute_name"]==vgroup: hair_with_this_vgroup += 1
            #     if hair_with_this_vgroup >= 2:
            #         for hayr in hair_with_vgroups:
            #             if hayr[0].modifiers[0]["Input_83_attribute_name"] == vgroup:
            #                 hair.remove(hayr)  # so that it doesn't get listed twice (afterwards with regular siblings)
            #                 list_hair(hayr[0])
            #         row = layout.row()
            #         row = layout.row()
            #         row = layout.row()
            #
            # #REGULAR SIBLINGS
            # for sibling in hair:
            #     list_hair(sibling[0])


            # # VISUALLY SEPARATE BIOMES BY BIOME GROUP
            # # all_bgroups=[hayr[0].modifiers[0]["Socket_0"] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups]
            # all_bgroups=[]
            # hair_in_bgroup = []
            # for hayr in hair[:]:        #hayr[0] because I'm using a tuple while listing object name and its brush paint system
            #     if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups:
            #         all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            # all_bgroups.sort()
            # for Bgroup in all_bgroups:
            #     list_biomes(Bgroup,hair_in_bgroup) #create biome commands row
            #     for hayr in hair[:]:
            #         if hayr[0].modifiers[0]["Socket_0"] == Bgroup: list_hair(hayr[0])
            #     row = layout.row()
            #     row = layout.row()
            #     row = layout.row()
            #     row = layout.row()
            # VISUALLY SEPARATE BIOMES BY BIOME GROUP
            # all_bgroups=[hayr[0].modifiers[0]["Socket_0"] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups]

            biome_models = layout_model["biomes"]
            for biome_model in biome_models:     #CREATE BGROUPS AND INDIVIDUAL ROWS INSIDE
                Bgroup = biome_model["bgroup"]
                hair_in_bgroup = biome_model["rows"]
                if blender_version < "4.1.0":   #NEW SUBPANEL IS ONLY COMPATIBLE WITH 4.1, otherwise use the old method without collapsing
                    biome_box = layout.box()
                    list_biomes(biome_model,row = biome_box.row(align=True)) #create biome commands row           #if len(hair_in_bgroup) >=2:
                    biome_rows = biome_box.column(align=True)
                    for row_entry in hair_in_bgroup: list_hair(row_entry,Bgroup,biome_rows)  #create individual hair rows
                elif blender_version >= "4.1.0":
                    biome_box = layout.box()
                    header, panel = biome_box.panel(
                        _side_panel_biome_panel_id(layout_model, Bgroup),
                        default_closed=False,
                    )
                    # panel.scale_y = 2  # Adjust the height of the button
                    list_biomes(biome_model,header) #create biome commands row           #if len(hair_in_bgroup) >=2:
                    if panel:
                        biome_rows = panel.column(align=True)
                        for row_entry in hair_in_bgroup: list_hair(row_entry,Bgroup,biome_rows)  #create individual hair rows



                # box = layout.box()
                # box.prop(context.scene.mypropertieslist, "dropdownpanel", text="BIOME 1", icon="TRIA_DOWN" if context.scene.mypropertieslist.dropdownpanel else "TRIA_RIGHT")
                # # box.label.scale_y = 3  # Adjust the height of the button # ['__call__', '__class__', '__delattr__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__']
                # if context.scene.mypropertieslist.dropdownpanel:
                #     for hayr in hair_in_bgroup:
                #         box.label(text=hayr[0].name)
                #         # biomegroupreorder = box.operator("secret.biomegroupreorder", text="", icon='TRIA_UP')  # REORDER ROW UPWARDS by triggering the function "secret.biomegroupreorder"
                #         # biomegroupreorder2 = box.operator("secret.biomegroupreorder2", text="", icon='TRIA_DOWN')

                # layout = self.layout
                # layout.label("Fourth row", icon='ACTION')
                # row = layout.row()
                # box = row.box()
                # box.operator("my.button", text="11", emboss=False).loc = "4 11"
                # box.operator("my.button", text="12", emboss=False).loc = "4 12"
                # col = row.column()
                # subrow = col.row()
                # subrow.operator("my.button", text="13").loc = "4 13"
                # subrow.operator("my.button", text="14").loc = "4 14"
                # subrow = col.row(align=True)
                # subrow.operator("my.button", text="15").loc = "4 15"
                # subrow.operator("my.button", text="16").loc = "4 16"
                # box = row.box()
                # box.operator("my.button", text="17").number = 17
                # box.separator()
                # box.operator("my.button", text="18")
                # box.operator("my.button", text="19")
                layout.separator()

            # hayr[0].modifiers[0]["Socket_2"]

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

        button_group = layout.column(align=True)
        target_object = _secret_paint_panel_world_target_object(context)
        if target_object is not None:
            row = button_group.row(align=True)
            row.operator_context = 'INVOKE_DEFAULT'
            row.scale_y = 1.35
            lock_enabled = _secret_paint_panel_surface_lock_enabled(context)
            row.alert = lock_enabled
            target_name = _side_panel_rna_name(target_object, "Terrain")
            row.operator(
                "secret.world_paint_toggle_lock_surface",
                icon='VIEW_LOCKED' if lock_enabled else 'VIEW_UNLOCKED',
                text=f"Lock Terrain: {target_name}",
            )

        row = button_group.row(align=True)
        row.scale_y = 1.35
        row.operator("secret.toggle_viewport_tab_bookmark", icon='CAMERA_DATA', text="Toggle View Bookmark")

        row = button_group.row(align=True)
        row.scale_y = 1.35
        row.operator("secret.assembly", icon="MOD_EXPLODE", text="Assembly")
        row.operator("secret.realize_instances", icon="LIBRARY_DATA_OVERRIDE_NONEDITABLE", text="Realize")
        row = button_group.row(align=True)
        row.scale_y = 1.35
        row.operator("secret.paintbrushswitch", icon='BRUSHES_ALL', text="Switch")
        row.operator("secret.fixdyntopo", icon="GROUP_UVS", text="Reproject")
        layout.separator()
        layout.separator()

        # if bl_info["name"] != "orencloud private": addon_updater_ops.check_for_update_background()
        # row = layout.row()
        # row = layout.row()
        # row.prop(context.scene.mypropertieslist, "paint_default", expand=True)
        utility_group = layout.column(align=True)
        row = utility_group.row(align=True)
        row.scale_y = 1.0
        # if bl_info["name"] == "orenpaint":
        row.operator("secret.circular_array", icon="CURVE_BEZCIRCLE")
        row.operator("secret.straight_array", icon="CURVE_PATH")
        row = utility_group.row(align=True)
        row.scale_y = 1.0
        row.operator("secret.shared_material", icon= 'MATERIAL')
        row.scale_x = 0.25  # Adjust the height of the button
        row.prop(context.scene.mypropertieslist, "shared_material_index", expand=True, text="")
        row = utility_group.row(align=True)
        row.scale_y = 1  # Adjust the height of the button
        row.operator("secret.group", icon= 'COLLECTION_NEW')
        # Temporarily disabled; keep operator code below for future re-enable.
        # row.operator("secret.export_unreal", icon= 'EXPORT')
        # row.operator("secret.secretpaint_update_modifier", icon="GEOMETRY_NODES")
        # row.operator("oren.orengrouprecentercollectionobj", icon="ORIENTATION_CURSOR", text= "Recenter Collection Instance")
        # row.operator("oren.orenscatterduplicatehair")
        # row.operator("oren.orenpaintswitchtoweightzero", icon='OUTLINER_OB_GROUP_INSTANCE')
        # row.operator("oren.orencurveselectobj", icon= 'RESTRICT_SELECT_OFF')
        # row.operator("oren.select_biome", icon= 'RESTRICT_SELECT_OFF')
        # row.operator("oren.select_biome_all", icon= 'RESTRICT_SELECT_OFF')
        # row.operator("oren.orenpaint_viewport_mask")
        # layout.prop(context.scene.mypropertieslist, "checkboxTransferMaterialWithBiome")


class subpanelexportbiome(bpy.types.Panel):
    bl_label = "Export Biome To Asset Library"
    bl_idname = "OREN_PT_subpanelexportbiome"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Secret"
    bl_parent_id = 'OREN_PT_subpanelutils'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        preferences = _secret_paint_addon_preferences(context)
        if preferences is None:
            return

        row = layout.row()
        row.prop(preferences, "biomeAssetName")
        row = layout.row()
        row.prop(preferences, "biome_library")
        row = layout.row()
        row.prop(preferences, "biomename")
        row = layout.row()
        row.prop(preferences, "biomenamecategory")
        row = layout.row()
        biome_name = preferences.biomename
        if not biome_name.endswith(".blend"): biome_name = biome_name + ".blend"  # optionally have the folder path with .blend
        blend_file_name= os.path.basename(biome_name)  #Secret Biome
        # file_path2 = bpy.context.preferences.filepaths.asset_libraries[-1].path + biome_name + ".blend"    #C:\Users\loren\Assets\3D\objects/Biomes/Secret Biome.blend
        # print(file_path2)
        file_path = preferences.biome_library + "/"+ biome_name    #bpy.context.preferences.filepaths.asset_libraries[-1].path          C:\Users\loren\Assets\3D\objects/Biomes/Secret Biome.blend
        blend_found=False
        if os.path.exists(file_path):
            blend_found = True
            row.label(text=f"{blend_file_name} already exists,")
            row = layout.row()
            row.label(text="everything will be imported inside of it.")
            row = layout.row()
        row.operator("secret.export_obj_to_asset_library", text=f"Export into {blend_file_name}" if blend_found else "Export Biome to Asset Library")
        row.operator("secret.open_folder", icon="FILE_FOLDER", text="")
        # row.operator("oren.export_obj_to_asset_library")


class open_folder(bpy.types.Operator):
    """Open Destination Folder with file explorer"""
    bl_idname = "secret.open_folder"
    bl_label = "Open Destination Folder"
    # bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        preferences = _secret_paint_addon_preferences(context)
        if preferences is None or preferences.biome_library == "(No Library Found, create one first)":
            self.report({'ERROR'}, "No Library Found, create one first")
            return {'FINISHED'}
        biome_name = preferences.biomename  # context.scene.mypropertieslist.biomename
        path = preferences.biome_library + os.path.dirname(biome_name)      #bpy.context.preferences.filepaths.asset_libraries[-1].path
        print("111111111111111", path)
        try: os.startfile(path)
        except:self.report({'ERROR'}, "The folder doesn't exist. It will be created automatically once you export your Biome. You can also specify a pre-existing folder")
        return {'FINISHED'}



## UNIVERSAL
def reupdate_hair_material(context,**kwargs):
    # if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    # else:activeobj = bpy.context.active_object
    # if activeobj == None: activeobj = bpy.context.active_object

    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj == None: activeobj = objselection[0]
    if activeobj not in objselection: objselection.append(activeobj)


    material_cache = {}

    # if len(objselection)>=1:  #might be empty if called from   "export_to_asset_library_function"
    for hair in objselection:
        if hair != None:
            if hair.type not in {"CURVES", "CURVE"} or not hair.modifiers:
                continue
            for modif in hair.modifiers:  # modifier.name == "GeometryNodes"
                if not (modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint"):
                    continue

                source_materials = []
                source_obj = None
                source_collection = None
                try:
                    source_obj = modif["Input_2"]
                except Exception:
                    source_obj = None
                try:
                    source_collection = modif["Input_9"]
                except Exception:
                    source_collection = None

                if (
                    source_obj is not None and
                    _secret_paint_datablock_exists(source_obj, bpy.data.objects) and
                    source_obj.type in {"MESH", "CURVE", "CURVES"}
                ):
                    source_materials = _secret_paint_collect_safe_materials_from_object(source_obj, material_cache)
                elif source_collection is not None and _secret_paint_datablock_exists(source_collection, bpy.data.collections):
                    for obj in source_collection.all_objects:
                        if obj != hair and obj.type in {"MESH", "CURVE", "CURVES"}:
                            for material in _secret_paint_collect_safe_materials_from_object(obj, material_cache):
                                if material not in source_materials:
                                    source_materials.append(material)

                _secret_paint_replace_curve_materials_from_sources(hair, source_materials)

    return {'FINISHED'}
def contextorencurveappend(context,**kwargs):  #paint. conversion
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object

    # print("UPDAAAAAAAAAAAT contextorencurveappend")
    secretpaint_update_modifier_f(context,upadte_provenance="def contextorencurveappend(context,**kwargs):") #cleanup .002, then update only executes if version number is different

    modifier = activeobj.modifiers.new(name="Secret Paint", type='NODES')
    modifier.node_group = bpy.data.node_groups.get("Secret Paint")
    return {"FINISHED"}
def secretpaint_update_modifier_f(context, cant_remove_this_argument=0, **kwargs):
# def orenpaint_update_modifier_f(context,**kwargs):

    pickup_trace = _get_pickup_trace()
    update_trace_start = time.perf_counter()
    upadte_provenance = kwargs.get("upadte_provenance") if "upadte_provenance" in kwargs else None

    print("######################### secretpaint_update_modifier_f ######################### Update Triggered By: ", upadte_provenance)
    #appending objects with operator ruins selection, so restore it later
    activeobj = bpy.context.active_object
    objselection = bpy.context.selected_objects


    # Forced_Update = kwargs.get("Forced_Update") if "Forced_Update" in kwargs else False


    # if Forced_Update: reupdate_hair_material(context, objselection= [ob for ob in bpy.data.objects]) #RELINK MATERIALS FOR ALL ORENPAINT HAIR IN BLEND FILE

    # if "check_for_dupli_nodes" in kwargs:
    #     if kwargs.get("check_for_dupli_nodes") == True:
    #         for node_tree in bpy.data.node_groups:
    #             if node_tree.name.startswith("Secret Paint") and not node_tree.name.endswith("Secret Paint") or node_tree.name.startswith("orenpaint") or node_tree.name.startswith("Secret Paint").library:
    #                 Forced_Update = True  #update_because_dupli_nodes_found
    #                 print("update_because_dupli_nodes_found")
    #                 break
    ######################################################################

    # print("11111111111111",bpy.data.node_groups.get("Secret Paint") == None)
    # print("4444444444",bpy.data.node_groups.get("Secret Generator") == None)
    # print("Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹Ã¹",["secret paint with linked library found" for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and node_tree.library])
    # print("222222222222222",["found multiple duplicates like Secret Paint.002 " for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999"])
    # print("222222222222222",["found multiple duplicates like Secret Paint.002 " for node_tree in bpy.data.node_groups if node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999" and node_tree.library])
    #CHECK IF REAPPEND NODE IS NEEDED        check if node or generator is present, if there's a linked library node, if there are secret paint.002 duplicates, finally if the bundled node asset is stale
    carry_through = False
    try:  #if fails, means it's an old node group before I even introduced the update number
        linked_secret_paint_nodes = [
            node_tree
            for node_tree in bpy.data.node_groups
            if (
                node_tree.name == "Secret Paint"
                or (
                    node_tree.name.startswith("Secret Paint")
                    and re.search(r"\.\d{3}$", node_tree.name)
                    and ".001" <= node_tree.name[-4:] <= ".999"
                )
            )
            and node_tree.library
        ]
        duplicate_secret_paint_nodes = [
            node_tree
            for node_tree in bpy.data.node_groups
            if (
                node_tree.name.startswith("Secret Paint")
                and re.search(r"\.\d{3}$", node_tree.name)
                and ".001" <= node_tree.name[-4:] <= ".999"
            )
        ]
        if _secret_paint_node_tree_needs_update() or linked_secret_paint_nodes or duplicate_secret_paint_nodes:
            carry_through = True
    except:
        print("FAILED, UPDATING")
        carry_through=True

    # print("BEFORE CARRYING THROUGH")
    legacy_upgrade_objects = []
    if carry_through:
        legacy_upgrade_objects = _secret_paint_prepare_legacy_node_upgrade(context)

    if carry_through:
        if pickup_trace:
            pickup_trace.note(f"update_modifier carry_through=True | provenance={upadte_provenance}")
        print("######################### secretpaint_update_modifier_f CARRY THROUGH WITH REAPPEND UPDATE Update Triggered By: ", upadte_provenance)

        reupdate_hair_material_start = time.perf_counter()
        reupdate_hair_material(context, objselection=[ob for ob in bpy.data.objects])  # RELINK MATERIALS FOR ALL ORENPAINT HAIR IN BLEND FILE
        if pickup_trace:
            pickup_trace.action("update_modifier.reupdate_hair_material", reupdate_hair_material_start, detail=f"objects={len(bpy.data.objects)}")



        nodes_to_switch = []
        cleanup_generator = []
        collect_nodes_start = time.perf_counter()
        for node_tree in bpy.data.node_groups:
            # if not node_tree.library and node_tree.name.startswith("Secret Paint") and "ASSEMBLY" not in node_tree.name:
            if node_tree.name == "Secret Paint" or node_tree.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":  # if node_tree.name.startswith("Secret Paint") and "ASSEMBLY" not in node_tree.name:
                if not node_tree.library: node_tree.name = "Secret Paint.001"  # new_name = node_tree.name.replace('orenpaint', 'orenpaint OLD')
                if node_tree not in nodes_to_switch: nodes_to_switch.append(node_tree)
            # if not node_tree.library and node_tree.name.startswith("Secret Generator"):
            if node_tree.name == "Secret Generator" or node_tree.name.startswith("Secret Generator") and re.search(r"\.\d{3}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999": #if node_tree.name.startswith("Secret Generator"):
                if not node_tree.library: node_tree.name = "Secret Generator.001"  # new_name = node_tree.name.replace('orenpaint', 'orenpaint OLD')
                if node_tree not in cleanup_generator: cleanup_generator.append(node_tree)
        if pickup_trace:
            pickup_trace.action(
                "update_modifier.collect_nodes",
                collect_nodes_start,
                detail=f"nodes_to_switch={len(nodes_to_switch)}; generators={len(cleanup_generator)}",
            )



        #REAPPEND ORENPAINT NODE
        all_previous_nodes = set(bpy.data.node_groups)
        file_path = _secret_paint_source_blend_path()
        inner_path = "NodeTree"
        object_name = "Secret Paint"
        # bpy.ops.wm.append( filepath=os.path.join(file_path, inner_path, object_name), directory=os.path.join(file_path, inner_path), filename=object_name)
        # FOR SOME REASON IT FAILS (critical corruption?????? but it works anyway) #Error: Critical blend-file corruption: Conflicts and/or otherwise invalid data-blocks names
        append_node_start = time.perf_counter()
        try: bpy.ops.wm.append(filepath=os.path.join(file_path, inner_path, object_name),directory=os.path.join(file_path, inner_path),filename=object_name)
        except:print("[[[[[[[[[[[[ SECRET PAINT UPDATE FAILED!! CRITICAL CORRUPTION WEIRD")
        if pickup_trace:
            pickup_trace.action("update_modifier.append_node_tree", append_node_start, detail=f"file={os.path.basename(file_path)}")

        cleanup_libraries_start = time.perf_counter()
        for lib in bpy.data.libraries: #for some reason, appending anything creates an empty library link, which is error prone
            # if lib.name == "Secret Paint.blend": bpy.data.libraries.remove(lib, do_unlink=True)
            if lib.name in ["Secret Paint.blend","Secret Paint 4.0 and older.blend","Secret Paint 4.1.blend","Secret Paint 4.2.0.blend"]: bpy.data.libraries.remove(lib, do_unlink=True)
        if pickup_trace:
            pickup_trace.action("update_modifier.cleanup_libraries", cleanup_libraries_start)

        # FIND orenpaint NODE THAT'S LOCAL AND NOT THE LINKED ONE (for some reason, when linking a biome with orenpaint node, they share the same node.name so you can't reference it with bpy.data.node_groups.get(
        # orenpaintNode = [nod for nod in bpy.data.node_groups if nod not in all_previous_nodes and nod.name.startswith("Secret Paint")]
        for nod in bpy.data.node_groups:
            if nod not in all_previous_nodes and nod.name.startswith("Secret Paint"):
                orenpaintNode= nod
                break

        _secret_paint_patch_runtime_node_groups()




        #SWITCH ALL MODIFIERS
        switch_modifiers_start = time.perf_counter()
        for obj in bpy.data.objects:
            # if obj.type in ["CURVES","CURVE"] and obj.modifiers and not obj.library:  #can't edit modifiers of linked objects
            if obj.type in ["CURVES","CURVE"]:
                for modif in obj.modifiers:
                    # if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith(("Secret Paint","orenpaint")): modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
                    # if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint": modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
                    # if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith(("Secret Paint","orenpaint")) and "ASSEMBLY" not in modif.node_group.name: modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
                    if modif.type == 'NODES' and modif.node_group:
                        # print(modif.node_group.name)
                        if modif.node_group.name == "Secret Paint" or modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999" : modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
        if pickup_trace:
            pickup_trace.action("update_modifier.switch_all_modifiers", switch_modifiers_start, detail=f"objects={len(bpy.data.objects)}")

        _secret_paint_apply_legacy_procedural_flags(legacy_upgrade_objects)
        _secret_paint_disable_obsolete_manual_baked_transforms()

        # print("################################## SECRET PAINT INFO ##################################")
        # print("INIT PATH: ", os.path.abspath(__file__))
        # print("ADDON PATH: ", addon_path)
        # print("BLENDER VERSION: ", blender_version)
        # print("FILE PATH B VERS: ", file_path)
        # print("Does File exists: ",os.path.isfile(file_path))
        # print("LIST OF FILES",os.listdir(addon_path))
        # print("--------")
        # # print("FULL LIST OF FILES",[os.path.join(addon_path, f) for f in os.listdir(addon_path)])
        # # print("DID IT FAIL IMPORTING",status)
        # print("################################## SECRET PAINT INFO ##################################")

        # # DELETE OLD NODES (cleanup orenpaint.002 when appending biomes)
        # for node_tree in bpy.data.node_groups:
        #     if node_tree.name.startswith('orenpaint') and not node_tree.name.endswith('orenpaint'): nodes_to_switch.append(node_tree)
        #     if node_tree.name.startswith('orengenerator') and not node_tree.name.endswith('orengenerator'): cleanup_orengenerator.append(node_tree)
        # for node in bpy.data.node_groups.get("orenpaint").nodes:
        #     if node.type == 'GROUP' and node.node_tree and node.node_tree.name.startswith("orengenerator"): node.node_tree = bpy.data.node_groups.get("orengenerator")
        # if nodes_to_switch[:]:
            # for obj in bpy.data.objects:
            #     if obj.type == "CURVES" or obj.type == "CURVE" and obj.modifiers:
            #         for modif in obj.modifiers:
            #             if modif.type == 'NODES' and modif.node_group and modif.node_group in nodes_to_switch:
            #                 modif.node_group = orenpaintNode #bpy.data.node_groups.get("orenpaint")



        # DELETE OLD NODES
        # if nodes_to_switch[:]:
        for nod in nodes_to_switch[:]:
            # if nod:
            bpy.data.node_groups.remove(nod, do_unlink=True)
        # if cleanup_generator[:]:
        for nod in cleanup_generator[:]:
            # if nod:
            bpy.data.node_groups.remove(nod, do_unlink=True)

    _secret_paint_disable_obsolete_manual_baked_transforms()

    #RESELECT ORIGINAL OBJS (appending objects with operator ruins selection)
    for x in objselection: x.select_set(True)
    if activeobj: bpy.context.view_layer.objects.active = activeobj


#     toggleAdvancedModifier() #UPDATE SOCKETS VISIBILITY
#     # return {'FINISHED'}
# def toggleAdvancedModifier():    #UPDATE SOCKETS VISIBILITY
#     if bpy.data.node_groups.get("Secret Paint"):
#
#         #    or input.name == "SIMULATION MODE" \
#         #    or input.name == "Spawn Per Frame" \
#         #    or input.name == "Particles Speed" \
#         #    or input.name == "Spawn Radius" \
#         #    or input.name == "Spawn Radius Z" \
#         #    or input.name == "Non Sim Continuity" \
#         #    or input.name == "Non Sim Offset" \
#         if bpy.app.version_string >= "4.0.0": x = bpy.data.node_groups["Secret Paint"].interface.items_tree
#         elif bpy.app.version_string < "4.0.0": x= bpy.data.node_groups["Secret Paint"].inputs
#
#         #DISABLED:  or input.name=="Faster Viewport Mask"\
#
#
#         for input in x:          #['__bool__', '__contains__', '__delattr__', '__delitem__', '__doc__', '__getattribute__', '__getitem__', '__iter__', '__len__', '__setattr__', '__setitem__', 'find', 'foreach_get', 'foreach_set', 'get', 'items', 'keys', 'values']
#
#             if bpy.app.version_string >= "4.0.0" and not hasattr(input, 'default_closed'): #if it's a panel skip it because error: doesn't have .socket_type
#                 if input.name=="Scale"\
#                 or input.name=="Edge Blur"\
#                 or input.name=="Noise W"\
#                 or input.name=="MASK Weight"\
#                 or input.name=="MASK Object"\
#                 or input.name=="MASK Viewport"\
#                 or input.name=="MASK Obj in Viewport"\
#                 or input.name=="MASK Texture"\
#                 or input.name=="UV for Texture" \
#                 or input.name=="Scale of Surface" \
#                 or input.name=="Move origin"\
#                 or input.name=="Strenght"\
#                 or input.name=="Wind Scale"\
#                 or input.name=="Speed"\
#                 or input.name=="Viewport Density"\
#                 or input.socket_type == "NodeSocketString" and input.default_value == "LOCATION"\
#                 or input.socket_type == "NodeSocketString" and input.default_value == "Wind"\
#                 or input.name=="Clump Radius"\
#                 or input.name=="Clump Density"\
#                 or input.name=="Proxy Convex Hull"\
#                 or input.name=="Proxy Bounding Box"\
#                 or input.name=="Material Custom"\
#                 or input.name=="Material Original /Custom"\
#                 or input.name=="Surface"\
#                 or input.name=="Real Instances"\
#                 or input.name=="Distribution Seed"\
#                 or input.name=="TURN OFF SYSTEM":
#                     if bpy.context.preferences.addons[__package__].preferences.checkboxAdvancedModifier and input.hide_in_modifier: input.hide_in_modifier = False
#                     elif not bpy.context.preferences.addons[__package__].preferences.checkboxAdvancedModifier and not input.hide_in_modifier: input.hide_in_modifier = True
#
#             elif bpy.app.version_string < "4.0.0" and not hasattr(input, 'default_closed'): #if it's a panel skip it because error: doesn't have .socket_type
#                 if input.name=="Scale"\
#                 or input.name=="Edge Blur"\
#                 or input.name=="Noise W"\
#                 or input.name=="MASK Weight"\
#                 or input.name=="MASK Object"\
#                 or input.name=="MASK Viewport"\
#                 or input.name=="MASK Obj in Viewport"\
#                 or input.name=="MASK Texture"\
#                 or input.name=="UV for Texture" \
#                 or input.name=="Scale of Surface" \
#                 or input.name=="Move origin"\
#                 or input.name=="Strenght"\
#                 or input.name=="Wind Scale"\
#                 or input.name=="Speed"\
#                 or input.name=="Viewport Density"\
#                 or input.type == "STRING" and input.default_value == "LOCATION"\
#                 or input.type == "STRING" and input.default_value == "Wind"\
#                 or input.name=="Clump Radius"\
#                 or input.name=="Clump Density"\
#                 or input.name=="Proxy Convex Hull"\
#                 or input.name=="Proxy Bounding Box"\
#                 or input.name=="Material Custom"\
#                 or input.name=="Material Original /Custom"\
#                 or input.name=="Surface"\
#                 or input.name=="Real Instances"\
#                 or input.name=="Distribution Seed"\
#                 or input.name=="TURN OFF SYSTEM":
#                     if bpy.context.preferences.addons[__package__].preferences.checkboxAdvancedModifier and input.hide_in_modifier: input.hide_in_modifier = False
#                     elif not bpy.context.preferences.addons[__package__].preferences.checkboxAdvancedModifier and not input.hide_in_modifier: input.hide_in_modifier = True
#     # toggleAdvancedModifier() #execute on Blender Startup
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
    print("AAAAAAAAAAAPPPPPPPPPPPPPPLYYYYYYYYY")
    # print("apply_paint")
    pickup_trace = _get_pickup_trace()
    apply_paint_start = time.perf_counter()
    converted_from_procedural = []

    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    else:objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj) ##############

    start_world_paint_after_apply = (
        (
            kwargs.get("force_world_paint", False) or
            _secret_paint_world_paint_enabled(context)
        )
        and _secret_paint_system_modifier(activeobj) is not None
        and not kwargs.get("keep_legacy_paint_mode", False)
    )

    if "applyIDs" in kwargs:applyIDs = kwargs.get("applyIDs")
    else:applyIDs = False

    keep_active_brush = kwargs.get("keep_active_brush") if "keep_active_brush" in kwargs else False

    #when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object
    if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]


    # orig_hair_selection = bpy.context.selected_objects
    # coll_original = bpy.context.view_layer.active_layer_collection

    # activeobj = bpy.context.active_object
    # objselection = bpy.context.selected_objects
    N_Of_Selected = len(objselection)
    randomselectedobj = []
    randomselected_non_hair = []
    all_objs_are_hair = True

    all_objs_are_orencurves = True
    all_selected_hair = []
    all_selected_non_hair = []
    selected_without_active = []
    if N_Of_Selected:
        classify_selection_start = time.perf_counter()
        for obj in objselection:

            if obj != activeobj:
                randomselectedobj = obj
                selected_without_active.append(obj)

            # if "orenpaint" not in obj.modifiers.node_tree: randomselected_non_hair = obj
            if obj.type != "CURVES" and obj.type != "CURVE": randomselected_non_hair = obj
            # if obj.type != "CURVES": randomselected_non_hair = obj

            if obj.type != "CURVES": all_objs_are_hair = False

            # if obj.type == "CURVES" or obj.type == "CURVE": all_selected_hair.append(obj)
            if obj.type == "CURVES":
                all_selected_hair.append(obj)
                if obj.modifiers:
                    for modif in obj.modifiers:
                        if modif.type == 'NODES':  # modifier.name == "GeometryNodes"
                            if modif.node_group:
                                if modif.node_group.name == "Secret Paint": pass
                                else: all_objs_are_orencurves = False
                            else: all_objs_are_orencurves = False
                        else: all_objs_are_orencurves = False
                else: all_objs_are_orencurves = False
            else: all_objs_are_orencurves = False


            # if obj.type != "CURVES" or obj.type != "CURVE": all_selected_non_hair.append(obj)
            if obj.type != "CURVES": all_selected_non_hair.append(obj)
        if pickup_trace:
            pickup_trace.action(
                "apply_paint.classify_selection",
                classify_selection_start,
                detail=f"selected={N_Of_Selected}; hair={len(all_selected_hair)}; non_hair={len(all_selected_non_hair)}; apply_ids={applyIDs}",
            )

    # # for obj in orig_hair_selection:
    # for obj in objselection:
    #     applied_instances = []
    #     obj_as_pivot = []
    #     applied_instances = []  # resets for next loop
    #     CollInstance_used_as_brush =[]
    #     try:
    #         CollInstance_used_as_brush = obj.modifiers["GeometryNodes"]["Input_2"]  # resets for next loop
    #         coll_of_collinstance = CollInstance_used_as_brush.instance_collection #bpy.data.collections["Cube"]
    #         coll_of_collinstance_origin = coll_of_collinstance.instance_offset
    #         for objecc in coll_of_collinstance.all_objects:
    #             if objecc.location == coll_of_collinstance_origin: obj_as_pivot = objecc   #find object closest to collection origin
    #     except: pass

    # saveMode= bpy.context.object.mode
    # bpy.ops.object.mode_set(mode="OBJECT")

    ###############################################   v    ###############################################################################

    # Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=objselection)  # SLOW FOR HIGHPOLY OBJECTS

    for obj in all_selected_hair:
        object_total_start = time.perf_counter()
        prepare_modifier_start = time.perf_counter()
        curve_count = 0
        point_count = 0
        apply_ids_reason = "not_requested"
        extracted_procedural_curves = False
        temporary_conversion_node_tree = None
        was_procedural_before_apply = bool(obj.modifiers[0]["Input_69"])
        use_legacy_procedural_ids = _secret_paint_modifier_legacy_procedural_ids(obj.modifiers[0])
        procedural_ids_before_apply = []
        if (
            was_procedural_before_apply
            and not use_legacy_procedural_ids
        ):
            procedural_ids_before_apply = _secret_paint_evaluated_curve_seed_values_from_attribute(
                context,
                obj,
                SECRET_PAINT_STABLE_ID_ATTRIBUTE,
            )
            if not procedural_ids_before_apply:
                procedural_ids_before_apply = _secret_paint_evaluated_curve_seed_values_from_attribute(
                    context,
                    obj,
                    "id",
                )
        # #COLL INSTANCE EMPTY scattered as brush
        # if CollInstance_used_as_brush and CollInstance_used_as_brush.type == "EMPTY":
        #     # print("111111111111111111111111")
        #     # operate inside collection of activeobj in this loop
        #     for i in obj.users_collection:
        #         layer_collection = bpy.context.view_layer.layer_collection
        #         collection_of_activeobj = recurLayerCollection(layer_collection, i.name)
        #     bpy.context.view_layer.active_layer_collection = collection_of_activeobj
        #
        #
        #     bpy.ops.object.select_all(action='DESELECT') #select only hair obj
        #     bpy.data.objects[obj.name].select_set(True)
        #     bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]  # make active
        #     bpy.ops.object.duplicates_make_real()
        #     bpy.data.objects.remove(obj, do_unlink=True) #delete hair obj
        #     applied_instances = bpy.context.selected_objects
        #
        #     for ob in applied_instances:
        #         if ob.type == "EMPTY" and ob.name.startswith(os.path.splitext(CollInstance_used_as_brush.name)[0]):
        #             ob.instance_type = 'COLLECTION'
        #             ob.instance_collection = coll_of_collinstance  #bpy.data.collections[coll_of_collinstance.name]
        #         else: bpy.data.objects.remove(ob, do_unlink=True)  # delete hair obj
        #
        #     bpy.context.view_layer.active_layer_collection = coll_original

        ##IF PROCEDURAL SCATTER: APPLY HAIR GENERATOR
        ## elif all_objs_are_orencurves and obj.modifiers["GeometryNodes"]["Input_69"] == True:
        ## elif obj.modifiers["GeometryNodes"]["Input_69"] == True and (sum(len(spline.points) for spline in obj.data.curves)) >= 1:
        ## if obj.modifiers["GeometryNodes"]["Input_69"] == True and (sum(len(spline.points) for spline in obj.data.curves)) >= 1:  #CAN'T APPLY IF there are no curve hair in edit mode so delete modif.


        # if obj.modifiers[0]["Input_69"] == True:  #ONLY TRY TO APPLY MODIFIER IF PROCEDURAL MODE IS TURNED ON (there are no curve hair in edit mode so delete modif.)
        #APPLY ID MODIFIER ELSE GENERATOR MODIFIER
        node_to_use = None
        if applyIDs:
            should_apply_ids, curve_count, point_count, apply_ids_reason = _secret_paint_should_apply_ids(obj)
            if not should_apply_ids:
                _secret_paint_store_id_cache(obj.data, curve_count, point_count)
                if pickup_trace:
                    pickup_trace.action(
                        "apply_paint.skip_apply_ids",
                        prepare_modifier_start,
                        label=obj.name,
                        detail=f"reason={apply_ids_reason}; curves={curve_count}; points={point_count}",
                    )
                    pickup_trace.action(
                        "apply_paint.object_total",
                        object_total_start,
                        label=obj.name,
                        detail=f"skipped_apply_ids=True; reason={apply_ids_reason}",
                    )
                continue
        if not applyIDs and obj.modifiers[0]["Input_69"] == False and not SECRET_PAINT_ENABLE_APPLY_IDS_MODIFIER:
            curve_count, point_count = _secret_paint_get_curves_counts(obj.data)
            _secret_paint_store_id_cache(obj.data, curve_count, point_count)
            apply_ids_reason = "feature_disabled"
            if pickup_trace:
                pickup_trace.action(
                    "apply_paint.skip_apply_ids_modifier",
                    prepare_modifier_start,
                    label=obj.name,
                    detail=f"reason={apply_ids_reason}; curves={curve_count}; points={point_count}",
                )
            _secret_paint_snap_curves_to_surface_if_armature(obj, pickup_trace=pickup_trace)
            if pickup_trace:
                pickup_trace.action(
                    "apply_paint.object_total",
                    object_total_start,
                    label=obj.name,
                    detail=f"skipped_apply_ids_modifier=True; reason={apply_ids_reason}",
                )
            continue

        if (
            not applyIDs
            and was_procedural_before_apply
            and not use_legacy_procedural_ids
        ):
            raw_curve_count, _raw_point_count = _secret_paint_get_curves_counts(obj.data)
            eval_curve_count, _eval_point_count = _secret_paint_evaluated_curves_counts(context, obj)
            raw_matches_evaluated = False
            if raw_curve_count > 0 and eval_curve_count == raw_curve_count:
                raw_matches_evaluated = _secret_paint_curve_root_positions_match(
                    _secret_paint_curve_root_position_values(obj.data),
                    _secret_paint_evaluated_curve_root_position_values(context, obj),
                    raw_curve_count,
                )
            can_convert_existing_curves = (
                raw_curve_count > 0 and raw_matches_evaluated
            ) or (
                raw_curve_count == 0 and eval_curve_count == 0
            )
            if can_convert_existing_curves:
                stable_curve_values = []
                if len(procedural_ids_before_apply) == raw_curve_count:
                    stable_curve_values = [int(value) for value in procedural_ids_before_apply]

                procedural_ids_are_authoritative = bool(
                    raw_curve_count > 0 and len(stable_curve_values) == raw_curve_count
                )

                if (
                    not procedural_ids_are_authoritative
                    and not _secret_paint_stable_curve_values_are_usable(obj.data, stable_curve_values)
                ):
                    stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
                        obj.data,
                        SECRET_PAINT_STABLE_ID_ATTRIBUTE,
                    )
                if (
                    not procedural_ids_are_authoritative
                    and not _secret_paint_stable_curve_values_are_usable(obj.data, stable_curve_values)
                ):
                    stable_curve_values = _secret_paint_curve_seed_values_from_attribute(obj.data, "id")
                if raw_curve_count > 0 and len(stable_curve_values) != raw_curve_count:
                    stable_curve_values = list(range(raw_curve_count))

                try:
                    obj.modifiers[0]["Input_69"] = False
                    obj.modifiers[0]["Input_98"] = False
                    obj.modifiers[0]["Input_97"] = None
                except Exception:
                    pass

                stable_attr_seed_count = len(stable_curve_values)
                if stable_curve_values:
                    _secret_paint_apply_stable_curve_values(obj.data, stable_curve_values)
                    if obj not in converted_from_procedural:
                        converted_from_procedural.append(obj)
                _secret_paint_set_modifier_input_by_name(
                    obj.modifiers[0],
                    SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
                    False,
                )
                _secret_paint_set_modifier_input_by_name(
                    obj.modifiers[0],
                    SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
                    False,
                )
                obj.data[SECRET_PAINT_MANUAL_LEGACY_IDS_PROP] = False
                use_legacy_procedural_ids = False

                curve_count, point_count = _secret_paint_get_curves_counts(obj.data)
                _secret_paint_store_id_cache(obj.data, curve_count, point_count)
                if pickup_trace:
                    pickup_trace.action(
                        "apply_paint.convert_existing_procedural_curves",
                        prepare_modifier_start,
                        label=obj.name,
                        detail=f"curves={curve_count}; eval_curves={eval_curve_count}; stable_attr_seed_count={stable_attr_seed_count}; legacy_ids={use_legacy_procedural_ids}",
                    )
                _secret_paint_snap_curves_to_surface_if_armature(obj, pickup_trace=pickup_trace)
                if pickup_trace:
                    pickup_trace.action(
                        "apply_paint.object_total",
                        object_total_start,
                        label=obj.name,
                        detail="converted_existing_procedural_curves=True",
                    )
                continue
        if applyIDs or obj.modifiers[0]["Input_69"] == False:
            node_to_use = _secret_paint_get_apply_ids_node_group()

        elif applyIDs == False:
            if was_procedural_before_apply:
                node_to_use = _secret_paint_create_procedural_curve_extract_node_group(
                    obj.modifiers[0],
                )
                if node_to_use is not None:
                    extracted_procedural_curves = True
                    temporary_conversion_node_tree = node_to_use
                else:
                    node_to_use = _secret_paint_ensure_generator_stable_ids(
                        context,
                        upadte_provenance="apply_paint procedural to manual stable ids",
                    )
            if node_to_use is None:
                node_to_use = _secret_paint_get_generator_node_group()
        modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
        modifier.node_group = node_to_use
        is_apply_ids_node = bool(node_to_use and node_to_use.name == "Secret Paint Apply IDs")
        if is_apply_ids_node:
            _secret_paint_set_apply_ids_seed(modifier, obj.modifiers[0]["Input_80"])
        elif extracted_procedural_curves:
            _secret_paint_copy_modifier_properties(obj.modifiers[0], modifier)
            _secret_paint_set_modifier_input_by_name(
                modifier,
                SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
                False,
            )
        else:
            _secret_paint_set_modifier_input_by_name(
                modifier,
                SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
                use_legacy_procedural_ids,
            )
            modifier["Input_2"] = obj.parent  #.data.surface #surface
            modifier["Input_15"] = obj.modifiers[0]["Input_68"]*(obj.modifiers[0]["Input_100"]**2) #scatterdensity + compensate for scale
            modifier["Input_14"] = obj.modifiers[0]["Input_83"] #attribute mask
            modifier["Input_16"] = obj.modifiers[0]["Input_80"] #seed
            modifier["Input_19"] = obj.modifiers[0]["Input_79"] #mask texture
            modifier["Input_30"] = obj.modifiers[0]["Input_78"] #uvmap
            modifier["Input_33"] = obj.modifiers[0]["Input_70"]*obj.modifiers[0]["Input_100"] #noise scale + compensate for scale
            modifier["Input_31"] = obj.modifiers[0]["Input_72"] #spread
            modifier["Input_32"] = obj.modifiers[0]["Input_82"] #blur
            modifier["Input_34"] = obj.modifiers[0]["Input_71"] #noiseW
            modifier["Input_39"] = obj.modifiers[0]["Input_89"] #slope inverted
            modifier["Input_40"] = obj.modifiers[0]["Input_16"] #curvetype
            modifier["Input_41"] = obj.modifiers[0]["Input_86"] #slope
            modifier["Input_42"] = obj.modifiers[0]["Input_91"] #height
            modifier["Input_43"] = obj.modifiers[0]["Input_92"] #height inverted
            modifier["Input_44"] = obj.modifiers[0]["Input_95"] #mask obj
            modifier["Input_45"] = obj.modifiers[0]["Input_85"] #viewport
            modifier["Input_47"] = obj.modifiers[0]["Input_98"] #mask obj in viewport
            modifier["Input_48"] = obj.modifiers[0]["Input_97"] #mask viewport obj
            modifier["Socket_0"] = bool(obj.modifiers[0]["Socket_0"]) #faster viewport mask
            if obj.modifiers[0]["Input_83_attribute_name"] and obj.modifiers[0]["Input_83_use_attribute"]:
                modifier["Input_14_attribute_name"] = obj.modifiers[0]["Input_83_attribute_name"] #weight mask
                modifier["Input_14_use_attribute"] = True #weight mask turn on
            obj.modifiers[0]["Input_69"] = False #turn off noise scattering

        #MOVE MODIFIER AT THE TOP OF THE STACK
        if bpy.app.version_string >= "4.0.0":
            obj.modifiers.move(len(obj.modifiers) - 1, 0)
        elif bpy.app.version_string < "4.0.0":
            # while obj.modifiers[0] != modifier:
            #     bpy.ops.object.modifier_move_up({'object': obj}, modifier=modifier.name)
            bpy.ops.object.modifier_move_up({'object': obj}, modifier=modifier.name)

        # return{'FINISHED'}

        if pickup_trace:
            pickup_trace.action(
                "apply_paint.prepare_modifier",
                prepare_modifier_start,
                label=obj.name,
                detail=f"apply_ids={applyIDs}; reason={apply_ids_reason}; node={node_to_use.name if node_to_use else 'None'}",
            )


        #APPLY MODIF - make single user data first, reassign all the others, FAILS IF NO HAIR BECAUSE LOW DENSITY
        modifier_apply_start = time.perf_counter()
        successfully_applied_so_reimport_materials, shared_data_before_apply, material_count_before = _secret_paint_apply_geometry_nodes_modifier(
            context,
            obj,
            modifier,
            restore_materials=True,
        )
        if temporary_conversion_node_tree is not None:
            try:
                if temporary_conversion_node_tree.users == 0:
                    bpy.data.node_groups.remove(temporary_conversion_node_tree, do_unlink=True)
            except Exception:
                pass
        if pickup_trace:
            pickup_trace.action(
                "apply_paint.modifier_apply",
                modifier_apply_start,
                label=obj.name,
                detail=f"shared_data={shared_data_before_apply}; applied={successfully_applied_so_reimport_materials}; reason={apply_ids_reason}",
            )

        # REAPPEND MATERIALS (for some reason, applying GENERATOR modif deletes all materials, not necessary for APPLY ID modifier)
        if successfully_applied_so_reimport_materials:
            restore_materials_start = time.perf_counter()
            stable_ids_applied_for_conversion = False
            stable_attr_seed_count = 0
            if applyIDs:
                _secret_paint_store_id_cache(obj.data, curve_count, point_count)
            else:
                if was_procedural_before_apply and extracted_procedural_curves:
                    obj.modifiers[0]["Input_69"] = False
                    curve_count, _point_count = _secret_paint_get_curves_counts(obj.data)
                    stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
                        obj.data,
                        SECRET_PAINT_STABLE_ID_ATTRIBUTE,
                    )
                    if use_legacy_procedural_ids:
                        legacy_baked_values = _secret_paint_curve_seed_values_from_attribute(
                            obj.data,
                            "id",
                        )
                        if len(legacy_baked_values) == curve_count:
                            stable_curve_values = [int(value) for value in legacy_baked_values]
                            use_legacy_procedural_ids = False
                    stable_attr_seed_count = len(stable_curve_values)
                    if stable_curve_values:
                        _secret_paint_apply_stable_curve_values(obj.data, stable_curve_values)
                        stable_ids_applied_for_conversion = True
                        if obj not in converted_from_procedural:
                            converted_from_procedural.append(obj)
                    _secret_paint_set_modifier_input_by_name(
                        obj.modifiers[0],
                        SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
                        use_legacy_procedural_ids,
                    )
                    _secret_paint_set_modifier_input_by_name(
                        obj.modifiers[0],
                        SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
                        False,
                    )
                    obj.data[SECRET_PAINT_MANUAL_LEGACY_IDS_PROP] = bool(use_legacy_procedural_ids)
                    ensure_secret_paint_system_stable_root_positions(obj)
                    curve_count, point_count = _secret_paint_get_curves_counts(obj.data)
                    _secret_paint_store_id_cache(obj.data, curve_count, point_count)
                elif was_procedural_before_apply:
                    curve_count_after_apply, _point_count_after_apply = _secret_paint_get_curves_counts(obj.data)
                    stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
                        obj.data,
                        SECRET_PAINT_STABLE_ID_ATTRIBUTE,
                    )
                    procedural_ids_are_authoritative = False
                    if (
                        curve_count_after_apply > 0 and
                        len(procedural_ids_before_apply) == curve_count_after_apply
                    ):
                        stable_curve_values = [int(value) for value in procedural_ids_before_apply]
                        procedural_ids_are_authoritative = True
                    if (
                        not procedural_ids_are_authoritative
                        and not _secret_paint_stable_curve_values_are_usable(obj.data, stable_curve_values)
                    ):
                        _secret_paint_remove_attribute_if_present(obj.data, SECRET_PAINT_STABLE_ID_ATTRIBUTE)
                        _secret_paint_remove_attribute_if_present(obj.data, SECRET_PAINT_STABLE_ROOT_POSITION_ATTRIBUTE)
                        apply_ids_node = _secret_paint_get_apply_ids_node_group()
                        apply_ids_modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
                        apply_ids_modifier.node_group = bpy.data.node_groups.get(apply_ids_node.name)
                        _secret_paint_set_apply_ids_seed(apply_ids_modifier, obj.modifiers[0]["Input_80"])
                        if bpy.app.version_string >= "4.0.0":
                            obj.modifiers.move(len(obj.modifiers) - 1, 0)
                        elif bpy.app.version_string < "4.0.0":
                            bpy.ops.object.modifier_move_up({'object': obj}, modifier=apply_ids_modifier.name)
                        _secret_paint_apply_geometry_nodes_modifier(
                            context,
                            obj,
                            apply_ids_modifier,
                            restore_materials=False,
                        )
                        stable_curve_values = _secret_paint_curve_seed_values_from_attribute(
                            obj.data,
                            SECRET_PAINT_STABLE_ID_ATTRIBUTE,
                        )
                    if (
                        not procedural_ids_are_authoritative
                        and not _secret_paint_stable_curve_values_are_usable(obj.data, stable_curve_values)
                    ):
                        stable_curve_values = _secret_paint_seed_stable_curve_attribute(context, obj)
                    stable_attr_seed_count = len(stable_curve_values)
                    if stable_curve_values:
                        _secret_paint_apply_stable_curve_values(obj.data, stable_curve_values)
                        stable_ids_applied_for_conversion = True
                        if obj not in converted_from_procedural:
                            converted_from_procedural.append(obj)
                    _secret_paint_set_modifier_input_by_name(
                        obj.modifiers[0],
                        SECRET_PAINT_LEGACY_PROCEDURAL_IDS_SOCKET,
                        use_legacy_procedural_ids,
                    )
                    _secret_paint_set_modifier_input_by_name(
                        obj.modifiers[0],
                        SECRET_PAINT_BAKED_PROCEDURAL_TRANSFORMS_SOCKET,
                        False,
                    )
                    obj.data[SECRET_PAINT_MANUAL_LEGACY_IDS_PROP] = bool(use_legacy_procedural_ids)
                    ensure_secret_paint_system_stable_root_positions(obj)
                    try:
                        obj.modifiers[0]["Input_98"] = False
                        obj.modifiers[0]["Input_97"] = None
                    except Exception:
                        pass
                    curve_count, point_count = _secret_paint_get_curves_counts(obj.data)
                    _secret_paint_store_id_cache(obj.data, curve_count, point_count)
            if pickup_trace:
                pickup_trace.action(
                    "apply_paint.restore_materials",
                    restore_materials_start,
                    label=obj.name,
                    detail=f"materials={material_count_before}; stable_attr_seed_count={stable_attr_seed_count}; stable_ids_after_conversion={stable_ids_applied_for_conversion}",
                )
        # #SNAP TO CLOSES SURFACE FOR ARMATURE DEFORMED OBJECTS ###ONLY IF OBJECT HAS ARMATURE MODIFIER
        _secret_paint_snap_curves_to_surface_if_armature(obj, pickup_trace=pickup_trace)


        # if not applyIDs: self.report({'INFO'}, "Procedural Distribution converted into Manual Paint")  # need to add (self, context) in the function

        # if N_Of_Selected==1 or saveMode=="SCULPT_CURVES": context3sculptbrush(context)


        # print("=======")

        # #REALIZE INSTANCES
        # elif all_objs_are_orencurves and obj.modifiers["GeometryNodes"]["Input_69"] == False:
        #     bpy.ops.object.mode_set(mode="OBJECT")
        #     bpy.ops.object.select_all(action='DESELECT')
        #     bpy.data.objects[obj.name].select_set(True)
        #     bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]  # make active
        #
        #     newly_duplicated_curve = curveseparate_function(context)
        #     bpy.ops.object.mode_set(mode="OBJECT")
        #
        #     bpy.ops.object.duplicates_make_real()
        #     bpy.data.objects.remove(newly_duplicated_curve, do_unlink=True)
        #     for x in bpy.context.selected_objects: bpy.context.view_layer.objects.active = bpy.data.objects[x.name]
        if pickup_trace:
            pickup_trace.action("apply_paint.object_total", object_total_start, label=obj.name)


    # bpy.ops.object.mode_set(mode="OBJECT")

    # for x in objselection: bpy.data.objects[x.name].select_set(False)
    clear_selection_start = time.perf_counter()
    for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
    if pickup_trace:
        pickup_trace.action("apply_paint.clear_selection", clear_selection_start)
    set_active_start = time.perf_counter()
    bpy.context.view_layer.objects.active = activeobj
    try:
        if activeobj is not None:
            activeobj.select_set(True)
    except Exception:
        pass
    if pickup_trace:
        pickup_trace.action("apply_paint.restore_active", set_active_start, detail=f"active={activeobj.name if activeobj else 'None'}")
    if not start_world_paint_after_apply:
        context3sculptbrush_start = time.perf_counter()
        context3sculptbrush(context, activeobj=activeobj, keep_active_brush=keep_active_brush)
        if pickup_trace:
            pickup_trace.action("apply_paint.context3sculptbrush", context3sculptbrush_start, detail=f"keep_active_brush={keep_active_brush}")
    # print("-----------------------------------------------------------")



    # reproject_function(self, context) #WORKS BUT TWICE
    auto_uv_start = time.perf_counter()
    Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=objselection)  # SLOW FOR HIGHPOLY OBJECTS
    if pickup_trace:
        pickup_trace.action("apply_paint.auto_uv_check", auto_uv_start)

    if converted_from_procedural:
        reapply_conversion_stable_ids_start = time.perf_counter()
        _secret_paint_reapply_conversion_stable_ids(context, converted_from_procedural)
        if not start_world_paint_after_apply:
            try:
                for selected in bpy.context.selected_objects:
                    selected.select_set(False)
                if activeobj is not None:
                    bpy.context.view_layer.objects.active = activeobj
                    activeobj.select_set(True)
            except Exception:
                pass
            context3sculptbrush(context, activeobj=activeobj, keep_active_brush=keep_active_brush)
        if pickup_trace:
            pickup_trace.action(
                "apply_paint.reapply_conversion_stable_ids",
                reapply_conversion_stable_ids_start,
                detail=f"objects={len(converted_from_procedural)}",
            )


        # #REAL INSTANCES
        # else:
        #     bpy.ops.object.select_all(action='DESELECT')
        #     bpy.data.objects[obj.name].select_set(True)
        #     bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]  # make active
        #     bpy.ops.object.duplicates_make_real()
        #     bpy.data.objects.remove(obj, do_unlink=True)

    if start_world_paint_after_apply:
        world_paint_start = time.perf_counter()
        world_paint_result = _secret_paint_start_world_paint_for_object(context, activeobj)
        if pickup_trace:
            pickup_trace.action(
                "apply_paint.world_paint_mode",
                world_paint_start,
                detail=f"active={activeobj.name if activeobj else 'None'}; result={world_paint_result}",
            )

    if pickup_trace:
        pickup_trace.action("apply_paint.total", apply_paint_start, detail=f"hair={len(all_selected_hair)}; apply_ids={applyIDs}")
    return{'FINISHED'}
class orenscatterinstancesmodifiers(bpy.types.Operator):
    """Convert Procedural Distribution into Manual Paint (or press Q with the paint system selected)"""
    bl_idname = "secret.applypaint"
    bl_label = "Apply and Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()

    def _run(self, context):
        activeobj= bpy.data.objects.get(self.object_name)
        if activeobj is None:
            self.report({'ERROR'}, f"Secret Paint object not found: {self.object_name}")
            return {'CANCELLED'}
        if _secret_paint_panel_switch_running_world_source(context, activeobj):
            return {'FINISHED'}
        _secret_paint_panel_exit_paint_mode(context)
        if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        for selected_obj in list(getattr(context, "selected_objects", [])):
            selected_obj.select_set(False)
        activeobj.select_set(True)
        bpy.context.view_layer.objects.active = activeobj
        # for x in bpy.context.selected_objects: x.select_set(False) #objselection
        # selection_list_only_for_active=[activeobj]
        # if event.alt:  #SWITCH PROCEDURAL
        #     checkbox_state = activeobj.modifiers["GeometryNodes"]["Input_69"]
        #     objselection = bpy.context.selected_objects
        #     if activeobj not in objselection: objselection.append(activeobj)
        #     for obj in objselection:
        #         if obj.type == "CURVES" and obj.modifiers:
        #             for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
        #                 if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "orenpaint":
        #                     obj.modifiers["GeometryNodes"]["Input_69"] = not checkbox_state
        #                     obj.location = obj.location
        # else: #CONVERT TO HAIR AND PAINT
        #     selection_list_only_for_active=[]
        #     selection_list_only_for_active.append(activeobj)
        #     # objselection.append(activeobj)
        #     apply_paint(self,context,activeobj=activeobj,objselection=selection_list_only_for_active)
        #     # apply_paint(self,context,activeobj=activeobj,objselection=list(activeobj))
        # objselection.append(activeobj)
        # apply_paint(self,context,activeobj=activeobj,objselection=selection_list_only_for_active)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.applypaint")
        _secret_paint_panel_clear_world_paint_object_guard()
        apply_paint(self,context,activeobj=activeobj, objselection=[activeobj], force_world_paint=True)
        _secret_paint_preview_world_paint_entry_source(context, activeobj, hold=False)
        # apply_paint(self,context,activeobj=activeobj,objselection=list(activeobj))
        return {'FINISHED'}

    def execute(self, context):
        return self._run(context)

    def invoke(self, context, event):
        return self._run(context)
class toggle_procedural(bpy.types.Operator):
    """Switch between Manual Paint and Procedural Distribution"""
    bl_idname = "secret.toggle_procedural"
    bl_label = "Toggle Procedural"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    # def invoke(self, context, event):
    def execute(self, context):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.toggle_procedural")

        if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        # if event.alt:  #SWITCH PROCEDURAL
        activeobj= bpy.data.objects.get(self.object_name)
        # if bpy.context.active_object != activeobj: bpy.context.view_layer.objects.active = activeobj
        checkbox_state = activeobj.modifiers[0]["Input_69"]
        objselection = bpy.context.selected_objects
        if activeobj not in objselection: objselection.append(activeobj)

        # when called from button: if the button references an object that was not selected or active: disregard selection and just use the panel row object
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]

        for obj in objselection:
            if obj.type == "CURVES" and obj.modifiers:
                for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):

                        #WHEN ENABLING PROCEDURAL, CALCULATE DENSITY AND TURN ON MASK FOR HUGE TERRAINS (only if switching TO procedural, not to manual)
                        if obj.type == "CURVES" and obj.modifiers[0]["Input_69"] == False and obj.modifiers[0]["Input_68"] > 0:
                            allTerrainArea = sum(face.area for face in obj.parent.data.polygons)  #area of mesh surface
                            # print("Number of instances ---------",(allTerrainArea/   (   (1/   ((obj.modifiers[0]["Input_68"] ** 0.5) * (obj.modifiers[0]["Input_100"]))   )   **2)))
                            # (0.5 / ((bpy.context.object.modifiers[0]["Input_68"] ** 0.5) * bpy.context.object.modifiers[0]["Input_100"])) * 2
                            # if allTerrainArea / (1 / ((obj.modifiers[0]["Input_68"] ** 0.5) * (obj.modifiers[0]["Input_100"] ** 2))) / 2 > 10000:  # (0.5/(hairCurves.modifiers["GeometryNodes"]["Input_68"]*hairCurves.modifiers["GeometryNodes"]["Input_100"]))
                            if (allTerrainArea/   (   (1/   ((obj.modifiers[0]["Input_68"] ** 0.5) * (obj.modifiers[0]["Input_100"]))   )   **2))   > _secret_paint_pref("trigger_viewport_mask", 15000):
                                obj.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
                                obj.modifiers[0]["Input_97"] = None
                                secretpaint_viewport_mask_function(self, context, objselection=[obj], activeobj=obj)

                        obj.modifiers[0]["Input_69"] = not checkbox_state  #invert procedural vs manual
                        obj.location = obj.location #update modifier

        # else: #CONVERT TO HAIR AND PAINT
        #     selection_list_only_for_active=[]
        #     selection_list_only_for_active.append(activeobj)
        #     # objselection.append(activeobj)
        #     apply_paint(self,context,activeobj=activeobj,objselection=selection_list_only_for_active)
        #     # apply_paint(self,context,activeobj=activeobj,objselection=list(activeobj))
        return {'FINISHED'}

class SelectObjectOperator(bpy.types.Operator):
    """G to reorder; Ctrl+Click: select siblings; Shift: extend selection; Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; Alt+Click: duplicate a backup system"""
    bl_idname = "secret.select_object"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    # object_biome: StringProperty()
    def invoke(self, context, event):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_object")

        activeobj = bpy.context.active_object
        objselection = bpy.context.selected_objects
        try:
            if activeobj and bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass

        ##################################################################

        if event.alt & event.ctrl:
            # if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
            for x in objselection: bpy.data.objects[x.name].select_set(False)
            obj = bpy.data.objects.get(self.object_name)
            if obj and obj.name in bpy.context.view_layer.objects:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj  # make active
                select_biome_all_function(context)

        elif event.alt:  #duplicate system
            obj= bpy.data.objects.get(self.object_name)
            if obj not in objselection: objselection=[obj]           #if obj not in objselection: objselection.append(obj)
            for obj in objselection:
                if obj.name in bpy.context.view_layer.objects:
                    Coll_of_Active = []
                    original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
                    ucol = obj.users_collection
                    for i in ucol:
                        layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
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
            # for x in objselection: bpy.data.objects[x.name].select_set(False)
            oob = bpy.data.objects.get(self.object_name)
            if oob.name in bpy.context.view_layer.objects:
                if oob not in objselection: objselection.append(bpy.data.objects.get(self.object_name))
                orencurveselectobj_function(self,context, activeobj=activeobj,objselection=objselection)

        elif event.shift:
            if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
            obj = bpy.data.objects.get(self.object_name)
            if obj and obj.name in bpy.context.view_layer.objects:
                # bpy.context.view_layer.objects.active = obj
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

        # def execute(self, context):
        #     for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
        #     if self.object_name and self.object_name in bpy.context.view_layer.objects:
        #         bpy.context.view_layer.objects.active = bpy.data.objects[self.object_name]
        #         bpy.data.objects[self.object_name].select_set(True)
        #     return {'FINISHED'}

        try:
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass

        return {'FINISHED'}
class selectbrush(bpy.types.Operator):
    """Ctrl+Click: select siblings; Shift: extend selection; Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; Alt+Click: duplicate a backup system"""
    bl_idname = "secret.selectbrush"
    bl_label = "Select Brush"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def invoke(self, context, event):
        selectbr = [b for b in bpy.data.brushes if b.name == self.object_name]  # if b.use_paint_image and b.blend == 'ERASE_ALPHA']
        context.tool_settings.image_paint.brush = selectbr[0]

        return {'FINISHED'}


class biome_delete(bpy.types.Operator):
    """Delete this biome. Shift+Click to only delete the selected hair within this biome"""
    bl_idname = "secret.biome_delete"
    bl_label = "Delete Biome"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: StringProperty()  # bpy.props.PointerProperty()
    # def execute(self, context):
    def invoke(self, context, event):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context, upadte_provenance="secret.biome_delete")

        if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")

        obj = context.object
        hair_in_bgroup = []


        if obj:
            hair=[]
            parent = obj.parent
            if obj.type=="CURVES" and parent:   #IF CURVE SELECTED
                for hai in parent.children: # hair = getChildren(parent)
                    if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                        for modifier in hai.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                                hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
            #ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
            elif obj.type=="MESH" or obj.type=="EMPTY":
                for hayr in bpy.context.scene.objects:
                # for hayr in obj.children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
                    if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                        for modifier in hayr.modifiers: #if mask selected, if brush obj selected, if terrain selected
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                                hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))

            all_bgroups=[]
            for hayr in hair[:]:
                if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]

        if not hair_in_bgroup:
            _clear_side_panel_count_cache(reason="biome_delete_empty")
            _secret_paint_tag_redraw_view3d_areas(context)
            return {'CANCELLED'}

        parent_surface = hair_in_bgroup[0].parent
        #DELETE
        if obj in hair_in_bgroup:  # select parent surface if the active object is about to be deleted, so that the panel still displays the same surface
            parent_surface.select_set(True)
            bpy.context.view_layer.objects.active = parent_surface

        if event.shift:
            for x in hair_in_bgroup:
                if x in bpy.context.selected_objects: bpy.data.objects.remove(x, do_unlink=True)
        else:
            for x in hair_in_bgroup:
                bpy.data.objects.remove(x, do_unlink=True)

        hair = find_all_listed_paintsystems(context, activeobj=parent_surface)
        biome_remove_gaps(context,hair) #REORDER BIOMES AND REMOVE GAPS
        _clear_side_panel_count_cache(reason="biome_delete")
        _secret_paint_tag_redraw_view3d_areas(context)

        return {'FINISHED'}

class SelectBiomeOperator(bpy.types.Operator):
    """Shift+Click: extend selection, Alt+Click: duplicate a backup system, Ctrl+Click: rename biome"""
    # """Ctrl: select siblings; Shift: extend selection; Alt+CTRL: select similar hair; Shift+Ctrl: Select Brush Objs; Alt: duplicate a backup system, Shift+Ctrl+Alt: delete biome"""
    bl_idname = "secret.select_biome"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty(name= "Custom Biome Name", default="")  #StringProperty()  #bpy.props.PointerProperty()
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
        hair = find_all_listed_paintsystems(context, activeobj=anchor)
        updated = False
        for ob, _brush in hair:
            modifier = _secret_paint_system_modifier(ob)
            if modifier is None:
                continue
            try:
                if int(modifier["Socket_0"]) != self.rename_biome_number:
                    continue
                modifier["Socket_8"] = name
                ob.location = ob.location
                updated = True
            except Exception:
                pass
        if updated:
            _clear_side_panel_count_cache(reason="panel_rename_biome")
            _secret_paint_tag_redraw_view3d_areas(context)
        return updated

    def _set_rename_status(self, context):
        try:
            context.workspace.status_text_set(
                text='Rename biome: "{}"  Enter confirm, Esc cancel'.format(self.object_biome)
            )
        except Exception:
            pass

    def _finish_rename_modal(self, context):
        _secret_paint_panel_end_biome_rename_cursor(context)
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

    def execute(self, context):  #ONLY FOR RENAMING BIOME ctrl+click

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - execute")

        if self._apply_biome_name(context, self.object_biome):
            return {'FINISHED'}
        return {'CANCELLED'}

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
            'LEFT_SHIFT',
            'RIGHT_SHIFT',
            'LEFT_CTRL',
            'RIGHT_CTRL',
            'LEFT_ALT',
            'RIGHT_ALT',
            'OSKEY',
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

    def invoke(self, context, event):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - invoke")

        obj = context.object
        if obj:
            hair = find_all_listed_paintsystems(context)
            all_bgroups=[]   # all_bgroups=[hayr[0].modifiers[0]["Socket_0"] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups]
            for hayr in hair[:]:
                if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]


            # activeobj = bpy.data.objects.get(self.object_biome)
            # objselection = bpy.context.selected_objects
            # if activeobj not in objselection: objselection.append(activeobj)

            # buttonbiome = bpy.data.objects.get(self.object_name)

            # objselection = bpy.context.selected_objects
            # if buttonobj not in objselection: objselection.append(buttonobj)

            # # when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object
            # if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]



            # activeobj = bpy.context.active_object
            # objselection = bpy.context.selected_objects
            ##################################################################

            # #DELETE
            # if event.shift & event.ctrl & event.alt:
            #     #select parent surface
            #     hair_in_bgroup[0].parent.select_set(True)
            #     bpy.context.view_layer.objects.active = hair_in_bgroup[0].parent
            #
            #     for x in hair_in_bgroup:
            #         bpy.data.objects.remove(x, do_unlink=True)



            # # ALL BIOMES WITH SAME BRUSH OBJS
            # elif event.alt & event.ctrl: pass
            #     # if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
            #     for x in hair: bpy.data.objects[x.name].select_set(False)
            #     obj = bpy.data.objects.get(self.object_biome)
            #     if obj and obj.name in bpy.context.view_layer.objects:
            #         obj.select_set(True)
            #         bpy.context.view_layer.objects.active = obj  # make active
            #         select_biome_all_function(context)

            if event.alt:  #duplicate system
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                new_bgroup_number = 1
                while new_bgroup_number in all_bgroups: new_bgroup_number +=1

                for obj in hair_in_bgroup:
                    if obj.name in bpy.context.view_layer.objects:
                        Coll_of_Active = []
                        original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
                        ucol = obj.users_collection
                        for i in ucol:
                            layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                            Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                            bpy.context.view_layer.active_layer_collection = Coll_of_Active
                        newobj = obj.copy()
                        newobj.data = obj.data.copy()
                        newobj.modifiers[0]["Socket_2"] = True
                        # obj.modifiers[0]["Input_99"] = False
                        obj.modifiers[0]["Socket_0"] = new_bgroup_number
                        obj.modifiers[0]["Socket_2"] = False
                        bpy.context.collection.objects.link(newobj)
                        bpy.data.objects[newobj.name].select_set(False)
                        obj.location=obj.location
                        bpy.context.view_layer.active_layer_collection = original_collection
                _clear_side_panel_count_cache(reason="duplicate_biome")
                _secret_paint_tag_redraw_view3d_areas(context)

            # elif event.shift & event.ctrl:
            #     # for x in hair: bpy.data.objects[x.name].select_set(False)
            #     oob = bpy.data.objects.get(self.object_name)
            #     if oob.name in bpy.context.view_layer.objects:
            #         if oob not in hair: hair.append(bpy.data.objects.get(self.object_name))
            #         orencurveselectobj_function(self,context, activeobj=activeobj,hair=hair)

            elif event.shift:
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                yet_to_be_selected = []
                for ob in hair_in_bgroup:
                    if not ob.select_get(): yet_to_be_selected.append(ob)

                if len(yet_to_be_selected) >=1:  #SELECT IF BIOME IS NOT COMPLETELY SELECTED
                    for ob in yet_to_be_selected:
                        if ob.name in bpy.context.view_layer.objects:
                            bpy.context.view_layer.objects.active = ob
                            ob.select_set(True)
                else: #DESELECT IF BIOME IS COMPLETELY SELECTED
                    for ob in hair_in_bgroup:
                        if ob.name in bpy.context.view_layer.objects:
                            ob.select_set(False)
                            for x in bpy.context.selected_objects: bpy.context.view_layer.objects.active = x



            elif event.ctrl:    #RENAME BIOME
                if not hair_in_bgroup:
                    return {'CANCELLED'}
                self.rename_biome_number = int(self.object_biome)
                self.rename_anchor_name = hair_in_bgroup[0].name
                try:
                    current_name = hair_in_bgroup[0].modifiers[0]["Socket_8"]
                except Exception:
                    current_name = ""
                self.object_biome = (
                    str(current_name)
                    if current_name not in ("", str(self.rename_biome_number), None)
                    else ""
                )
                self.rename_original_name = self.object_biome
                self._rename_replace_on_type = True
                secretpaint_update_modifier_f(context,upadte_provenance="secret.select_biome - invoke at the end") #might be an old version
                _secret_paint_panel_begin_biome_rename_cursor(
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
                _secret_paint_tag_redraw_view3d_areas(context)
                return {'RUNNING_MODAL'}



            else:
                if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
                for ob in hair_in_bgroup:
                    if ob.name in bpy.context.view_layer.objects:
                        bpy.context.view_layer.objects.active = ob
                        ob.select_set(True)
                # return self.execute(context)

            # def execute(self, context):
            #     for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
            #     if self.object_name and self.object_name in bpy.context.view_layer.objects:
            #         bpy.context.view_layer.objects.active = bpy.data.objects[self.object_name]
            #         bpy.data.objects[self.object_name].select_set(True)
            #     return {'FINISHED'}
        return {'FINISHED'}
# # Custom operator class for hiding/showing objects
# class ToggleVisibilityOperator(bpy.types.Operator):
#     bl_idname = "object.toggle_visibility"
#     bl_label = "Toggle Visibility"
#     object_name: bpy.props.StringProperty()
#     def execute(self, context):
#         obj = bpy.data.objects.get(self.object_name)
#         if obj:
#             obj.hide_viewport = not obj.hide_viewport
#         return {'FINISHED'}
#     def invoke(self, context, event):
#         if event.alt:
#             selected_objects = bpy.context.selected_objects
#             for obj in selected_objects:
#                 obj.hide_viewport = not obj.hide_viewport
#         elif event.ctrl:
#             obj = bpy.data.objects.get(self.object_name)
#             if obj:
#                 viewportstatus = obj.hide_viewport
#                 parent = obj.parent
#                 if parent:
#                     siblings = parent.children
#                     for sibling in siblings:
#                         sibling.hide_viewport = not viewportstatus
#         else:
#             return self.execute(context)
#         return {'FINISHED'}
# Custom operator class for hiding/showing objects
def find_all_listed_paintsystems(context,**kwargs):
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    if "objselection" in kwargs:objselection = kwargs.get("objselection")
    # else:objselection = bpy.context.selected_objects
    else:objselection = bpy.context.scene.objects
    try:
        if activeobj not in objselection: objselection.append(activeobj)
    except:pass  #MIGHT DELETED ACTIVE OBJECT

    listed_hair=[]
    parent = activeobj.parent
    if activeobj.type=="CURVES" and parent:   #IF CURVE SELECTED
        for hai in parent.children: # listed_hair = getChildren(parent)
            if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                for modifier in hai.modifiers:
                    if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                        listed_hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
    #ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
    elif activeobj.type=="MESH" or activeobj.type=="EMPTY":
        for hayr in bpy.context.scene.objects:
        # for hayr in activeobj.children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
            if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                for modifier in hayr.modifiers: #if mask selected, if brush activeobj selected, if terrain selected
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

    #FIND DESTINAITON BIOME (+1 or to the extreme of the stack)
    hair = find_all_listed_paintsystems(context, activeobj=activeobj, objselection=objselection)
    if move_to_extreme:
        all_biome_numbers = []
        for hayr in hair[:]:
            if hayr[0].modifiers[0]["Socket_0"] not in all_biome_numbers: all_biome_numbers.append(hayr[0].modifiers[0]["Socket_0"])
        if direction == -1: destination_biome = min(all_biome_numbers)-1
        elif direction == +1: destination_biome = max(all_biome_numbers)+1
    else: destination_biome = activeobj.modifiers[0]["Socket_0"] + direction



    # hair = find_all_listed_paintsystems(context, activeobj=activeobj, objselection=objselection)
    # they_are_all_hidden = True
    # for hayr in hair[:]:
    #     if hayr[0].modifiers[0]["Socket_0"] == destination_biome and hayr[0].modifiers[0]["Socket_2"] == False: they_are_all_hidden = False
    hair_in_destination_biome = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == destination_biome]
    # viewport_visibility_mute = True if True in [hairr.modifiers[0]["Socket_15"] for hairr in hair_in_destination_biome] else False
    ################################################################ v



    #REASSIGN + INHERIT VISIBILITY STATUS + TEMP "SOLO VISIBILITY" STATUS + INHERIT BIOME NAME
    for obj in objselection:
        if obj.type == "CURVES" and obj.modifiers:
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    modif["Socket_0"] = destination_biome
                    # if they_are_all_hidden and len(hair_in_destination_biome) >=1: modif["Socket_2"] = True
                    modif["Socket_3"] = False #reset temp visibility
                    modif["Socket_4"] = False
                    modif["Socket_5"] = False
                    modif["Socket_6"] = False
                    if len(hair_in_destination_biome) >=1:
                        modif["Socket_2"] = hair_in_destination_biome[0].modifiers[0]["Socket_2"] #inherit biome visibility viewport from the destination biome that the hair is being transferred to. but only if it's not an empty biome, otherwise don't update and keep current state
                        modif["Socket_15"] = hair_in_destination_biome[0].modifiers[0]["Socket_15"] #inherit biome visibility viewport from the destination biome that the hair is being transferred to. but only if it's not an empty biome, otherwise don't update and keep current state
                    # modif["Input_99"] = not checkbox_state
                    obj.location=obj.location
                    if hair_in_destination_biome: modif["Socket_8"] = hair_in_destination_biome[0].modifiers[0]["Socket_8"]   #BIOME NAME


    #REMOVE GAPS (change biomes from 1,3,5 into 1,2,3)
    # hair = find_all_listed_paintsystems(context,activeobj=activeobj,objselection=objselection)
    biome_remove_gaps(context, hair)



    return{'FINISHED'}


def _secret_paint_panel_flat_rows(context, activeobj):
    if activeobj is None:
        return []
    layout_model = _build_side_panel_layout_model(context, activeobj)
    flat_rows = []
    for biome_entry in layout_model["biomes"]:
        flat_rows.extend(biome_entry["rows"])
    return flat_rows


def _secret_paint_panel_set_row_order(flat_rows):
    order_by_bgroup = defaultdict(int)
    for row_entry in flat_rows:
        obj = row_entry.get("object")
        modifier = _secret_paint_system_modifier(obj)
        if modifier is None:
            continue
        try:
            bgroup = int(modifier["Socket_0"])
        except Exception:
            bgroup = modifier.get("Socket_0", 0)
        try:
            obj[SECRET_PAINT_PANEL_ORDER_PROP] = order_by_bgroup[bgroup]
            order_by_bgroup[bgroup] += 10
        except Exception:
            pass


def _secret_paint_panel_apply_biome_state(obj, destination_biome, reference_obj=None):
    modifier = _secret_paint_system_modifier(obj)
    if modifier is None:
        return False

    try:
        modifier["Socket_0"] = int(destination_biome)
    except Exception:
        modifier["Socket_0"] = destination_biome

    for socket_name in ("Socket_3", "Socket_4", "Socket_5", "Socket_6"):
        try:
            modifier[socket_name] = False
        except Exception:
            pass

    reference_modifier = _secret_paint_system_modifier(reference_obj)
    if reference_modifier is not None:
        for socket_name in ("Socket_2", "Socket_15", "Socket_8"):
            try:
                modifier[socket_name] = reference_modifier[socket_name]
            except Exception:
                pass
    return True


def _secret_paint_panel_reorder_targets(context, buttonobj, flat_rows):
    if buttonobj is None:
        return set()

    listed_objects = {
        row_entry.get("object")
        for row_entry in flat_rows
        if row_entry.get("object") is not None
    }
    if buttonobj not in listed_objects:
        return set()

    selected_targets = {
        obj
        for obj in getattr(context, "selected_objects", [])
        if obj in listed_objects and _secret_paint_system_modifier(obj) is not None
    }
    if buttonobj in selected_targets and len(selected_targets) > 1:
        return selected_targets
    return {buttonobj}


def _secret_paint_panel_reorder_flat_rows_for_object(context, buttonobj):
    if buttonobj is None:
        return None, []

    activeobj = context.object if context.object is not None else buttonobj
    flat_rows = _secret_paint_panel_flat_rows(context, activeobj)
    if any(row_entry.get("object") == buttonobj for row_entry in flat_rows):
        return activeobj, flat_rows

    if activeobj != buttonobj:
        activeobj = buttonobj
        flat_rows = _secret_paint_panel_flat_rows(context, activeobj)
        if any(row_entry.get("object") == buttonobj for row_entry in flat_rows):
            return activeobj, flat_rows
    return activeobj, flat_rows


def _secret_paint_panel_keyboard_anchor_object(context):
    basis_obj = context.object if context.object is not None else context.active_object
    if basis_obj is None:
        basis_obj = next(
            (
                obj
                for obj in getattr(context, "selected_objects", [])
                if _secret_paint_system_modifier(obj) is not None
            ),
            None,
        )
    if basis_obj is None:
        return None

    _activeobj, flat_rows = _secret_paint_panel_reorder_flat_rows_for_object(context, basis_obj)
    selected_objects = set(getattr(context, "selected_objects", []))
    selected_panel_rows = [
        row_entry.get("object")
        for row_entry in flat_rows
        if row_entry.get("object") in selected_objects
        and _secret_paint_system_modifier(row_entry.get("object")) is not None
    ]
    if not selected_panel_rows:
        return None

    activeobj = context.object if context.object is not None else context.active_object
    if activeobj in selected_panel_rows:
        return activeobj
    return selected_panel_rows[0]


def _secret_paint_panel_make_reorder_snapshot(context, object_name):
    buttonobj = bpy.data.objects.get(object_name)
    activeobj, flat_rows = _secret_paint_panel_reorder_flat_rows_for_object(context, buttonobj)
    snapshot_rows = []

    for row_entry in flat_rows:
        obj = row_entry.get("object")
        modifier = _secret_paint_system_modifier(obj)
        if obj is None or modifier is None:
            continue

        socket_values = {}
        for socket_name in SECRET_PAINT_PANEL_DRAG_RESTORE_SOCKETS:
            try:
                socket_values[socket_name] = modifier[socket_name]
            except Exception:
                pass

        try:
            has_panel_order = SECRET_PAINT_PANEL_ORDER_PROP in obj
        except Exception:
            has_panel_order = False

        snapshot_rows.append({
            "object_name": obj.name,
            "has_panel_order": has_panel_order,
            "panel_order": obj.get(SECRET_PAINT_PANEL_ORDER_PROP) if has_panel_order else None,
            "sockets": socket_values,
        })

    return {
        "active_object_name": activeobj.name if activeobj else "",
        "rows": snapshot_rows,
    }


def _secret_paint_panel_restore_reorder_snapshot(context, snapshot):
    if not snapshot:
        return

    for row_state in snapshot.get("rows", []):
        obj = bpy.data.objects.get(row_state.get("object_name", ""))
        if obj is None:
            continue

        modifier = _secret_paint_system_modifier(obj)
        if modifier is not None:
            for socket_name, socket_value in row_state.get("sockets", {}).items():
                try:
                    modifier[socket_name] = socket_value
                except Exception:
                    pass

        try:
            if row_state.get("has_panel_order", False):
                obj[SECRET_PAINT_PANEL_ORDER_PROP] = row_state.get("panel_order")
            elif SECRET_PAINT_PANEL_ORDER_PROP in obj:
                del obj[SECRET_PAINT_PANEL_ORDER_PROP]
        except Exception:
            pass

    _clear_side_panel_count_cache(reason="panel_drag_reorder_restore")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_biome_name_values(flat_rows):
    name_values = {}
    for row_entry in flat_rows:
        bgroup = row_entry.get("bgroup")
        if bgroup in name_values:
            continue
        override = row_entry.get("biome_label_override", "")
        name_values[bgroup] = (
            str(override)
            if override not in ("", str(bgroup), None)
            else ""
        )
    return name_values


def _secret_paint_panel_biome_runs(row_entries):
    runs = []
    for index, row_entry in enumerate(row_entries):
        bgroup = row_entry.get("bgroup")
        if not runs or runs[-1]["bgroup"] != bgroup:
            runs.append({"bgroup": bgroup, "start": index, "end": index + 1})
        else:
            runs[-1]["end"] = index + 1
    return runs


def _secret_paint_panel_nearest_biome_boundary(row_entries, position):
    runs = _secret_paint_panel_biome_runs(row_entries)
    if len(runs) < 2:
        return None
    boundaries = [run["end"] for run in runs[:-1]]
    return min(boundaries, key=lambda boundary: abs(position - boundary))


def _secret_paint_panel_visual_insert_positions(row_entries):
    positions = []
    visual_position = 0.0
    for index in range(len(row_entries) + 1):
        if index == 0:
            if row_entries:
                visual_position += SECRET_PAINT_PANEL_REORDER_BIOME_HEADER_ROWS
        elif index < len(row_entries) and row_entries[index]["bgroup"] != row_entries[index - 1]["bgroup"]:
            visual_position += SECRET_PAINT_PANEL_REORDER_BIOME_GAP_ROWS
            visual_position += SECRET_PAINT_PANEL_REORDER_BIOME_HEADER_ROWS

        positions.append(visual_position)

        if index < len(row_entries):
            visual_position += 1.0
    return positions


def _secret_paint_panel_visual_insert_index(row_entries, source_insert_index, visual_delta):
    positions = _secret_paint_panel_visual_insert_positions(row_entries)
    if not positions:
        return 0.0, 0.0, 0

    source_insert_index = max(0, min(len(positions) - 1, source_insert_index))
    source_visual_position = positions[source_insert_index]
    target_visual_position = source_visual_position + float(visual_delta)
    target_insert_index = min(
        range(len(positions)),
        key=lambda index: abs(positions[index] - target_visual_position),
    )
    return (
        target_visual_position,
        positions[-1],
        target_insert_index,
    )


def _secret_paint_panel_clamp_insert_index(row_entries, insertion_index):
    try:
        insertion_index = int(insertion_index)
    except Exception:
        insertion_index = 0
    return max(0, min(len(row_entries), insertion_index))


def _secret_paint_panel_reorder_entries(context, activeobj, flat_rows, buttonobj, row_delta):
    moving_objects = _secret_paint_panel_reorder_targets(context, buttonobj, flat_rows)
    if not moving_objects:
        return False

    moving_entries = [
        row_entry
        for row_entry in flat_rows
        if row_entry.get("object") in moving_objects
    ]
    remaining_entries = [
        row_entry
        for row_entry in flat_rows
        if row_entry.get("object") not in moving_objects
    ]
    if not moving_entries or not remaining_entries:
        return False

    try:
        anchor_index = next(
            index
            for index, row_entry in enumerate(flat_rows)
            if row_entry.get("object") == buttonobj
        )
    except StopIteration:
        return False

    source_insert_index = sum(
        1
        for index, row_entry in enumerate(flat_rows)
        if index < anchor_index and row_entry.get("object") not in moving_objects
    )
    target_visual_position, bottom_visual_position, insertion_index = (
        _secret_paint_panel_visual_insert_index(
            remaining_entries,
            source_insert_index,
            row_delta,
        )
    )
    insertion_index = _secret_paint_panel_clamp_insert_index(remaining_entries, insertion_index)
    move_to_top_biome = target_visual_position <= 0
    move_to_bottom_biome = target_visual_position >= bottom_visual_position
    moving_bgroups = {row_entry["bgroup"] for row_entry in moving_entries}
    moving_complete_biome = (
        len(moving_bgroups) == 1
        and not any(row_entry["bgroup"] in moving_bgroups for row_entry in remaining_entries)
    )

    if move_to_top_biome or move_to_bottom_biome:
        if move_to_top_biome:
            already_at_edge = all(
                row_entry.get("object") in moving_objects
                for row_entry in flat_rows[:len(moving_entries)]
            )
            insertion_index = 0
        else:
            already_at_edge = all(
                row_entry.get("object") in moving_objects
                for row_entry in flat_rows[-len(moving_entries):]
            )
            insertion_index = len(remaining_entries)
        if moving_complete_biome and already_at_edge:
            return False

        biome_numbers = []
        for row_entry in flat_rows:
            try:
                biome_numbers.append(int(row_entry["bgroup"]))
            except (TypeError, ValueError):
                pass
        if not biome_numbers:
            return False
        destination_biome = (
            min(biome_numbers) - 1
            if move_to_top_biome
            else max(biome_numbers) + 1
        )
        reference_obj = moving_entries[0].get("object")
    else:
        boundary_index = None
        if moving_complete_biome:
            visual_insert_positions = _secret_paint_panel_visual_insert_positions(remaining_entries)
            nearest_boundary = _secret_paint_panel_nearest_biome_boundary(
                remaining_entries,
                insertion_index,
            )
            if (
                nearest_boundary is not None
                and abs(target_visual_position - visual_insert_positions[nearest_boundary]) <= SECRET_PAINT_PANEL_BIOME_BOUNDARY_SNAP_ROWS
            ):
                boundary_index = nearest_boundary

        if boundary_index is not None:
            insertion_index = _secret_paint_panel_clamp_insert_index(remaining_entries, boundary_index)
        else:
            insertion_index = _secret_paint_panel_clamp_insert_index(remaining_entries, insertion_index)

        if insertion_index == source_insert_index:
            return False
        moving_bgroup = next(iter(moving_bgroups), None)
        reorder_complete_biome = (
            moving_complete_biome
            and moving_bgroup is not None
            and 0 < insertion_index < len(remaining_entries)
            and remaining_entries[insertion_index - 1]["bgroup"] != remaining_entries[insertion_index]["bgroup"]
        )
        if reorder_complete_biome:
            new_flat_rows = (
                remaining_entries[:insertion_index]
                + moving_entries
                + remaining_entries[insertion_index:]
            )
            name_by_bgroup = _secret_paint_panel_biome_name_values(flat_rows)
            ordered_bgroups = []
            for row_entry in new_flat_rows:
                bgroup = row_entry["bgroup"]
                if bgroup not in ordered_bgroups:
                    ordered_bgroups.append(bgroup)
            bgroup_numbers = {bgroup: index + 1 for index, bgroup in enumerate(ordered_bgroups)}
            for row_entry in new_flat_rows:
                obj = row_entry.get("object")
                modifier = _secret_paint_system_modifier(obj)
                if modifier is None:
                    continue
                try:
                    modifier["Socket_0"] = bgroup_numbers[row_entry["bgroup"]]
                except Exception:
                    continue
                try:
                    modifier["Socket_8"] = name_by_bgroup[row_entry["bgroup"]]
                except Exception:
                    pass
                if row_entry.get("object") in moving_objects:
                    for socket_name in ("Socket_3", "Socket_4", "Socket_5", "Socket_6"):
                        try:
                            modifier[socket_name] = False
                        except Exception:
                            pass
            _secret_paint_panel_set_row_order(new_flat_rows)
            _clear_side_panel_count_cache(reason="panel_drag_reorder")
            _secret_paint_tag_redraw_view3d_areas(context)
            return True

        target_reference_index = min(
            _secret_paint_panel_clamp_insert_index(remaining_entries, insertion_index),
            len(remaining_entries) - 1,
        )
        target_reference = remaining_entries[target_reference_index]
        destination_biome = target_reference["bgroup"]
        reference_obj = target_reference.get("object")

    for moving_entry in moving_entries:
        _secret_paint_panel_apply_biome_state(
            moving_entry.get("object"),
            destination_biome,
            reference_obj=reference_obj,
        )

    new_flat_rows = (
        remaining_entries[:insertion_index]
        + moving_entries
        + remaining_entries[insertion_index:]
    )

    biome_hair = find_all_listed_paintsystems(context, activeobj=activeobj, objselection=bpy.context.scene.objects)
    biome_remove_gaps(context, biome_hair)
    _secret_paint_panel_set_row_order(new_flat_rows)
    _clear_side_panel_count_cache(reason="panel_drag_reorder")
    _secret_paint_tag_redraw_view3d_areas(context)
    return True


def _secret_paint_panel_reorder_object(context, object_name, row_delta, *, update_modifier=True):
    if abs(float(row_delta)) < SECRET_PAINT_PANEL_REORDER_DEADZONE_ROWS:
        return False

    buttonobj = bpy.data.objects.get(object_name)
    if buttonobj is None:
        return False

    if update_modifier:
        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context, upadte_provenance="secret.panel_drag_reorder")

    activeobj, flat_rows = _secret_paint_panel_reorder_flat_rows_for_object(context, buttonobj)
    source_index = next(
        (index for index, row_entry in enumerate(flat_rows) if row_entry.get("object") == buttonobj),
        -1,
    )
    if source_index < 0 or len(flat_rows) <= 1:
        return False

    return _secret_paint_panel_reorder_entries(context, activeobj, flat_rows, buttonobj, row_delta)


class _SecretPaintPanelReportSink:
    def report(self, *_args, **_kwargs):
        pass


_SECRET_PAINT_PANEL_REPORT_SINK = _SecretPaintPanelReportSink()


def _secret_paint_panel_select_row(context, obj, *, extend=False):
    if obj is None or not _secret_paint_panel_object_is_in_view_layer(obj):
        return False

    _secret_paint_panel_exit_paint_mode(context)
    _secret_paint_panel_update_action_dependencies(context, "secret_paint_panel_select")
    _secret_paint_panel_set_object_mode(context)

    if extend:
        deselect = obj.select_get()
        obj.select_set(not deselect)
        if deselect and context.view_layer.objects.active == obj:
            context.view_layer.objects.active = next(iter(context.selected_objects), None)
        elif not deselect:
            context.view_layer.objects.active = obj
    else:
        for selected_obj in list(getattr(context, "selected_objects", [])):
            if selected_obj != obj:
                selected_obj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

    _secret_paint_tag_redraw_view3d_areas(context)
    return True


def _secret_paint_panel_select_row_range(context, obj):
    if obj is None or not _secret_paint_panel_object_is_in_view_layer(obj):
        return False

    _secret_paint_panel_exit_paint_mode(context)
    _secret_paint_panel_update_action_dependencies(context, "secret_paint_panel_select_range")
    _secret_paint_panel_set_object_mode(context)

    _activeobj, flat_rows = _secret_paint_panel_reorder_flat_rows_for_object(context, obj)
    row_objects = [
        row_entry.get("object")
        for row_entry in flat_rows
        if row_entry.get("object") is not None
    ]
    if obj not in row_objects:
        return _secret_paint_panel_select_row(context, obj)

    selected_objects = set(getattr(context, "selected_objects", []))
    anchor = getattr(context.view_layer.objects, "active", None)
    if anchor not in row_objects or anchor not in selected_objects:
        anchor = next((row_obj for row_obj in row_objects if row_obj in selected_objects), None)
    if anchor is None:
        return _secret_paint_panel_select_row(context, obj)

    start_index = row_objects.index(anchor)
    end_index = row_objects.index(obj)
    if start_index > end_index:
        start_index, end_index = end_index, start_index
    range_objects = set(row_objects[start_index:end_index + 1])

    for selected_obj in list(getattr(context, "selected_objects", [])):
        if selected_obj not in range_objects:
            selected_obj.select_set(False)
    for row_obj in range_objects:
        row_obj.select_set(True)
    context.view_layer.objects.active = obj

    _secret_paint_tag_redraw_view3d_areas(context)
    return True


def _secret_paint_panel_duplicate_backup_system(context, obj):
    if not _secret_paint_panel_select_row(context, obj):
        return False

    source_modifier = _secret_paint_system_modifier(obj)
    if source_modifier is None:
        return False

    try:
        newobj = obj.copy()
        newobj.data = obj.data.copy()
    except Exception:
        return False

    linked = False
    for collection in list(getattr(obj, "users_collection", [])):
        try:
            collection.objects.link(newobj)
            linked = True
        except Exception:
            pass
    if not linked:
        try:
            context.collection.objects.link(newobj)
            linked = True
        except Exception:
            return False

    backup_modifier = _secret_paint_system_modifier(newobj)
    if backup_modifier is not None:
        try:
            backup_modifier["Input_99"] = True
        except Exception:
            pass
    try:
        source_modifier["Input_99"] = False
        obj.location = obj.location
    except Exception:
        pass

    try:
        newobj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
    except Exception:
        pass
    _clear_side_panel_count_cache(reason="panel_duplicate_backup_system")
    _secret_paint_tag_redraw_view3d_areas(context)
    return True


class secret_paint_panel_select_object(bpy.types.Operator):
    """G to reorder, X to delete. Select this Paint System. Ctrl+click selects a range. Shift+click extends. Alt+click duplicates a disabled backup."""
    bl_idname = "secret.panel_select_object"
    bl_label = "Select Paint System"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: StringProperty()

    def _select(self, context, *, extend=False):
        obj = bpy.data.objects.get(self.object_name)
        if not _secret_paint_panel_select_row(context, obj, extend=extend):
            return {'CANCELLED'}
        return {'FINISHED'}

    def execute(self, context):
        return self._select(context)

    def invoke(self, context, event):
        if bool(getattr(event, "alt", False)):
            obj = bpy.data.objects.get(self.object_name)
            if not _secret_paint_panel_duplicate_backup_system(context, obj):
                return {'CANCELLED'}
            return {'FINISHED'}
        if bool(getattr(event, "ctrl", False)):
            obj = bpy.data.objects.get(self.object_name)
            if not _secret_paint_panel_select_row_range(context, obj):
                return {'CANCELLED'}
            return {'FINISHED'}
        return self._select(context, extend=bool(getattr(event, "shift", False)))


def _secret_paint_panel_button_target_objects(context, buttonobj):
    if buttonobj is None:
        return []

    selected_objects = [
        obj
        for obj in getattr(context, "selected_objects", [])
        if _secret_paint_system_modifier(obj) is not None
    ]
    if buttonobj not in selected_objects:
        selected_objects.append(buttonobj)

    active_object = getattr(context, "active_object", None)
    if active_object is None:
        active_object = getattr(context, "object", None)
    if buttonobj != active_object and buttonobj not in getattr(context, "selected_objects", []):
        return [buttonobj]
    return selected_objects


def _secret_paint_panel_update_action_dependencies(context, provenance, minimum_interval=0.25):
    now = time.monotonic()
    last_update_time = _SECRET_PAINT_PANEL_ACTION_LAST_UPDATE_TIMES.get(provenance, 0.0)
    if now - last_update_time < minimum_interval:
        return
    _SECRET_PAINT_PANEL_ACTION_LAST_UPDATE_TIMES[provenance] = now
    try:
        secretpaint_update_modifier_f(context, upadte_provenance=provenance)
    except Exception:
        pass


def _secret_paint_panel_set_object_mode(context):
    try:
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass


def _secret_paint_panel_modifier_bool(obj, socket_name, default=False):
    modifier = _secret_paint_system_modifier(obj)
    if modifier is None:
        return default
    try:
        return bool(modifier[socket_name])
    except Exception:
        return default


def _secret_paint_panel_modifier_value(obj, socket_name, default=None):
    modifier = _secret_paint_system_modifier(obj)
    if modifier is None:
        return default
    try:
        return modifier[socket_name]
    except Exception:
        return default


def _secret_paint_panel_modifier_key_down(virtual_key):
    if platform.system() != "Windows":
        return False
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(virtual_key) & 0x8000)
    except Exception:
        return False


def _secret_paint_panel_object_is_in_view_layer(obj):
    if obj is None:
        return False
    try:
        return obj.name in bpy.context.view_layer.objects
    except Exception:
        return True


def _secret_paint_panel_select_prop_get(self):
    return False


def _secret_paint_panel_select_prop_set(self, value):
    if not value or not _secret_paint_panel_object_is_in_view_layer(self):
        return

    _secret_paint_panel_select_row(bpy.context, self)


def _secret_paint_panel_apply_prop_get(self):
    return False


def _secret_paint_panel_run_deferred_apply():
    global _SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING
    if _secret_paint_panel_modifier_key_down(0x01):
        return 0.05
    try:
        while _SECRET_PAINT_PANEL_DEFERRED_APPLY_NAMES:
            object_name = _SECRET_PAINT_PANEL_DEFERRED_APPLY_NAMES.pop(0)
            if bpy.data.objects.get(object_name) is None:
                continue
            try:
                bpy.ops.secret.applypaint(object_name=object_name)
            except Exception:
                pass
    finally:
        _SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING = False
    return None


def _secret_paint_panel_apply_prop_set(self, value):
    global _SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING
    if not value:
        return
    try:
        object_name = self.name
    except (ReferenceError, RuntimeError):
        return
    if object_name not in _SECRET_PAINT_PANEL_DEFERRED_APPLY_NAMES:
        _SECRET_PAINT_PANEL_DEFERRED_APPLY_NAMES.append(object_name)
    if _SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING:
        return
    _SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING = True
    try:
        bpy.app.timers.register(_secret_paint_panel_run_deferred_apply, first_interval=0.01)
    except Exception:
        _SECRET_PAINT_PANEL_DEFERRED_APPLY_TIMER_RUNNING = False
        _SECRET_PAINT_PANEL_DEFERRED_APPLY_NAMES.clear()


def _secret_paint_panel_procedural_prop_get(self):
    return _secret_paint_panel_modifier_bool(self, "Input_69", False)


def _secret_paint_panel_apply_procedural_value(value, object_names):
    context = bpy.context
    _secret_paint_panel_exit_paint_mode(context)
    _secret_paint_panel_update_action_dependencies(context, "secret_paint_panel_procedural")
    _secret_paint_panel_set_object_mode(context)

    for object_name in object_names:
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            continue
        modifier = _secret_paint_system_modifier(obj)
        if modifier is None:
            continue
        try:
            if bool(value) and not bool(modifier["Input_69"]) and modifier["Input_68"] > 0 and obj.parent:
                all_terrain_area = sum(face.area for face in obj.parent.data.polygons)
                density_estimate = all_terrain_area / ((1 / ((modifier["Input_68"] ** 0.5) * modifier["Input_100"])) ** 2)
                if density_estimate > _secret_paint_pref("trigger_viewport_mask", 15000):
                    modifier["Input_98"] = False
                    modifier["Input_97"] = None
                    secretpaint_viewport_mask_function(
                        _SECRET_PAINT_PANEL_REPORT_SINK,
                        context,
                        objselection=[obj],
                        activeobj=obj,
                    )
            modifier["Input_69"] = bool(value)
            obj.location = obj.location
        except Exception:
            pass
    _clear_side_panel_count_cache(reason="panel_procedural_prop")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_run_deferred_procedural():
    global _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING
    if _secret_paint_panel_modifier_key_down(0x01):
        return 0.05
    try:
        pending_values = dict(_SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_VALUES)
        _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_VALUES.clear()
        grouped_targets = {}
        for object_name, value in pending_values.items():
            grouped_targets.setdefault(bool(value), []).append(object_name)
        for value, object_names in grouped_targets.items():
            _secret_paint_panel_apply_procedural_value(value, object_names)
    finally:
        _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING = False
    return None


def _secret_paint_panel_procedural_prop_set(self, value):
    global _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING
    context = bpy.context
    try:
        target_names = [
            obj.name for obj in _secret_paint_panel_button_target_objects(context, self)
            if _secret_paint_system_modifier(obj) is not None
        ]
    except (ReferenceError, RuntimeError):
        return
    for object_name in target_names:
        _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_VALUES[object_name] = bool(value)
    if not target_names or _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING:
        return
    _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING = True
    try:
        bpy.app.timers.register(_secret_paint_panel_run_deferred_procedural, first_interval=0.01)
    except Exception:
        _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_TIMER_RUNNING = False
        _SECRET_PAINT_PANEL_DEFERRED_PROCEDURAL_VALUES.clear()


def _secret_paint_panel_vertex_prop_get(self):
    return False


def _secret_paint_panel_run_deferred_vertex():
    global _SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING
    if _secret_paint_panel_modifier_key_down(0x01):
        return 0.05
    context = bpy.context
    try:
        pending_requests = list(_SECRET_PAINT_PANEL_DEFERRED_VERTEX_REQUESTS)
        _SECRET_PAINT_PANEL_DEFERRED_VERTEX_REQUESTS.clear()
        for object_name, target_names, remove_vgroup in pending_requests:
            activeobj = bpy.data.objects.get(object_name)
            if activeobj is None:
                continue
            target_objects = [
                obj for name in target_names
                if (obj := bpy.data.objects.get(name)) is not None
            ]
            if activeobj not in target_objects:
                target_objects.append(activeobj)
            _secret_paint_panel_exit_paint_mode(context)
            _secret_paint_panel_update_action_dependencies(context, "secret_paint_panel_vertex_mask")
            try:
                vertexgrouppaint_function(
                    _SECRET_PAINT_PANEL_REPORT_SINK,
                    context,
                    NoMasksDetected=True,
                    calledfrombutton=True,
                    activeobj=activeobj,
                    objselection=target_objects,
                    remove_vgroup=remove_vgroup,
                )
            except Exception:
                pass
        _clear_side_panel_count_cache(reason="panel_vertex_prop")
        _secret_paint_tag_redraw_view3d_areas(context)
    finally:
        _SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING = False
    return None


def _secret_paint_panel_queue_vertex_action(context, buttonobj, *, remove_vgroup=False):
    global _SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING
    try:
        object_name = buttonobj.name
        target_names = tuple(
            obj.name for obj in _secret_paint_panel_button_target_objects(context, buttonobj)
            if _secret_paint_system_modifier(obj) is not None
        )
    except (ReferenceError, RuntimeError):
        return
    request = (object_name, target_names, bool(remove_vgroup))
    if request not in _SECRET_PAINT_PANEL_DEFERRED_VERTEX_REQUESTS:
        _SECRET_PAINT_PANEL_DEFERRED_VERTEX_REQUESTS.append(request)
    if _SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING:
        return
    _SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING = True
    try:
        bpy.app.timers.register(_secret_paint_panel_run_deferred_vertex, first_interval=0.01)
    except Exception:
        _SECRET_PAINT_PANEL_DEFERRED_VERTEX_TIMER_RUNNING = False
        _SECRET_PAINT_PANEL_DEFERRED_VERTEX_REQUESTS.clear()


def _secret_paint_panel_vertex_prop_set(self, value):
    if not value:
        return
    _secret_paint_panel_queue_vertex_action(
        bpy.context,
        self,
        remove_vgroup=_secret_paint_panel_modifier_key_down(0x12),
    )


def _secret_paint_panel_render_prop_get(self):
    return (
        _secret_paint_panel_modifier_bool(self, "Input_99", False)
        or _secret_paint_panel_modifier_bool(self, "Socket_14", False)
    )


def _secret_paint_panel_render_targets(context, buttonobj):
    button_biome = _secret_paint_panel_modifier_value(buttonobj, "Socket_0", None)
    targets = _secret_paint_panel_button_target_objects(context, buttonobj)
    try:
        hair = find_all_listed_paintsystems(context, activeobj=context.object if context.object else buttonobj)
    except Exception:
        hair = []
    hair_in_bgroup = [
        entry[0]
        for entry in hair
        if _secret_paint_panel_modifier_value(entry[0], "Socket_0", None) == button_biome
    ]
    if hair_in_bgroup:
        targets = [obj for obj in targets if obj in hair_in_bgroup] or [buttonobj]
    return targets, hair_in_bgroup


def _secret_paint_panel_render_prop_set(self, value):
    context = bpy.context
    if _secret_paint_panel_modifier_key_down(0x12):
        _secret_paint_panel_render_modified_click(context, self, alt=True)
        return
    if _secret_paint_panel_modifier_key_down(0x10):
        _secret_paint_panel_render_modified_click(context, self, shift=True)
        return

    targets, hair_in_bgroup = _secret_paint_panel_render_targets(context, self)

    for obj in targets:
        modifier = _secret_paint_system_modifier(obj)
        if modifier is None:
            continue
        try:
            modifier["Input_99"] = bool(value)
            modifier["Socket_14"] = False
            obj.location = obj.location
        except Exception:
            pass

    for obj in hair_in_bgroup:
        modifier = _secret_paint_system_modifier(obj)
        if modifier is None:
            continue
        try:
            modifier["Socket_3"] = False
            modifier["Socket_4"] = False
            obj.location = obj.location
        except Exception:
            pass

    _clear_side_panel_count_cache(reason="panel_render_prop")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_render_modified_click(context, buttonobj, *, alt=False, shift=False):
    targets, hair_in_bgroup = _secret_paint_panel_render_targets(context, buttonobj)

    if alt:
        if _secret_paint_panel_modifier_bool(buttonobj, "Socket_4", False):
            for obj in hair_in_bgroup:
                modifier = _secret_paint_system_modifier(obj)
                if modifier is None:
                    continue
                try:
                    if bool(modifier["Socket_3"]):
                        modifier["Input_99"] = not bool(modifier["Input_99"])
                    modifier["Socket_3"] = False
                    modifier["Socket_4"] = False
                    obj.location = obj.location
                except Exception:
                    pass
        else:
            for obj in hair_in_bgroup:
                modifier = _secret_paint_system_modifier(obj)
                if modifier is None:
                    continue
                try:
                    modifier["Socket_3"] = False
                    modifier["Socket_4"] = False
                    obj.location = obj.location
                except Exception:
                    pass

            for obj in hair_in_bgroup:
                modifier = _secret_paint_system_modifier(obj)
                if modifier is None:
                    continue
                try:
                    if obj in targets:
                        if bool(modifier["Input_99"]):
                            modifier["Input_99"] = False
                            modifier["Socket_3"] = True
                        modifier["Socket_4"] = True
                    elif not bool(modifier["Input_99"]):
                        modifier["Socket_3"] = True
                        modifier["Input_99"] = True
                    obj.location = obj.location
                except Exception:
                    pass
    elif shift:
        render_hidden = _secret_paint_panel_modifier_bool(buttonobj, "Input_99", False)
        viewport_hidden = _secret_paint_panel_modifier_bool(buttonobj, "Socket_14", False)
        viewport_hidden = not viewport_hidden if not render_hidden else True
        for obj in targets:
            modifier = _secret_paint_system_modifier(obj)
            if modifier is None:
                continue
            try:
                modifier["Input_99"] = False
                modifier["Socket_14"] = viewport_hidden
                obj.location = obj.location
            except Exception:
                pass

    _clear_side_panel_count_cache(reason="panel_render_modified_click")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_bounds_prop_get(self):
    return getattr(self, "display_type", 'TEXTURED') == 'BOUNDS'


def _secret_paint_panel_bounds_prop_set(self, value):
    context = bpy.context
    target_display_type = 'BOUNDS' if value else 'TEXTURED'
    for obj in _secret_paint_panel_button_target_objects(context, self):
        try:
            obj.display_type = target_display_type
        except Exception:
            pass
    _clear_side_panel_count_cache(reason="panel_bounds_prop")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_mask_prop_get(self):
    return _secret_paint_panel_modifier_bool(self, "Input_98", False)


def _secret_paint_panel_mask_prop_set(self, value):
    context = bpy.context
    if _secret_paint_panel_modifier_key_down(0x12):
        _secret_paint_panel_mask_modified_click(context, self, alt=True)
        return
    if _secret_paint_panel_modifier_key_down(0x10):
        _secret_paint_panel_mask_modified_click(context, self, shift=True)
        return

    _secret_paint_panel_update_action_dependencies(context, "secret_paint_panel_viewport_mask")
    for obj in _secret_paint_panel_button_target_objects(context, self):
        if _secret_paint_panel_mask_prop_get(obj) == bool(value):
            continue
        try:
            if bool(value) and _secret_paint_viewport_mask_click_creates_temp_mask(context, obj):
                _secret_paint_panel_exit_paint_mode(context)
            secretpaint_viewport_mask_function(
                _SECRET_PAINT_PANEL_REPORT_SINK,
                context,
                objselection=[obj],
                activeobj=obj,
            )
        except Exception:
            pass
    _clear_side_panel_count_cache(reason="panel_mask_prop")
    _secret_paint_tag_redraw_view3d_areas(context)


def _secret_paint_panel_mask_modified_click(context, buttonobj, *, alt=False, shift=False):
    _secret_paint_panel_exit_paint_mode(context)
    try:
        secretpaint_update_modifier_f(context, upadte_provenance="secret.secretpaint_viewport_mask")
    except Exception:
        pass

    if alt:
        for obj in list(getattr(context, "selected_objects", [])):
            obj.select_set(False)
        mask_obj = _secret_paint_panel_modifier_value(buttonobj, "Input_97", None)
        if mask_obj is None:
            mask_obj = next(
                (obj for obj in context.scene.objects if obj.name.startswith("Secret Paint Viewport Mask")),
                None,
            )
        if mask_obj is not None:
            context.view_layer.objects.active = mask_obj
            mask_obj.select_set(True)
    elif shift:
        secretpaint_viewport_mask_function(
            _SECRET_PAINT_PANEL_REPORT_SINK,
            context,
            activeobj=buttonobj,
            force_new_maskObj=True,
        )

    _clear_side_panel_count_cache(reason="panel_mask_modified_click")
    _secret_paint_tag_redraw_view3d_areas(context)


def register_secret_paint_panel_drag_property():
    panel_chain_properties = (
        (
            SECRET_PAINT_PANEL_SELECT_PROP,
            bpy.props.BoolProperty(
                name="Select Paint System",
                description="G to reorder; drag vertically to select paint systems",
                get=_secret_paint_panel_select_prop_get,
                set=_secret_paint_panel_select_prop_set,
            ),
        ),
        (
            SECRET_PAINT_PANEL_APPLY_PROP,
            bpy.props.BoolProperty(
                name="Apply and Paint",
                description="Convert Procedural Distribution into Manual Paint",
                get=_secret_paint_panel_apply_prop_get,
                set=_secret_paint_panel_apply_prop_set,
            ),
        ),
        (
            SECRET_PAINT_PANEL_PROCEDURAL_PROP,
            bpy.props.BoolProperty(
                name="Toggle Procedural",
                description="Switch between Manual Paint and Procedural Distribution",
                get=_secret_paint_panel_procedural_prop_get,
                set=_secret_paint_panel_procedural_prop_set,
            ),
        ),
        (
            SECRET_PAINT_PANEL_VERTEX_PROP,
            bpy.props.BoolProperty(
                name="Weight Paint",
                description="Weight Paint Mask. Share it with all selected; Alt-click removes it",
                get=_secret_paint_panel_vertex_prop_get,
                set=_secret_paint_panel_vertex_prop_set,
            ),
        ),
        (
            SECRET_PAINT_PANEL_RENDER_PROP,
            bpy.props.BoolProperty(
                name="Toggle Visibility",
                description="Turn off Paint System; Shift-click hides only in the viewport; Alt-click solos it",
                get=_secret_paint_panel_render_prop_get,
                set=_secret_paint_panel_render_prop_set,
            ),
        ),
        (
            SECRET_PAINT_PANEL_BOUNDS_PROP,
            bpy.props.BoolProperty(
                name="Display as Bounds",
                description="Display as Bounds is the most efficient way to preserve viewport performance when displaying a large number of individual objects",
                get=_secret_paint_panel_bounds_prop_get,
                set=_secret_paint_panel_bounds_prop_set,
            ),
        ),
        (
            SECRET_PAINT_PANEL_MASK_PROP,
            bpy.props.BoolProperty(
                name="Temporary Viewport Mask",
                description="Mask vast landscapes; Shift-click creates a new mask; Alt-click selects the mask object",
                get=_secret_paint_panel_mask_prop_get,
                set=_secret_paint_panel_mask_prop_set,
            ),
        ),
    )

    for property_name, property_definition in panel_chain_properties:
        if hasattr(bpy.types.Object, property_name):
            continue
        setattr(
            bpy.types.Object,
            property_name,
            property_definition,
        )

    for property_name in ("secret_paint_panel_drag_handle", "secret_paint_panel_drag_pad"):
        if not hasattr(bpy.types.Object, property_name):
            continue
        try:
            delattr(bpy.types.Object, property_name)
        except Exception:
            return


def unregister_secret_paint_panel_drag_property():
    for property_name in (*SECRET_PAINT_PANEL_CHAIN_PROPS, "secret_paint_panel_drag_handle", "secret_paint_panel_drag_pad"):
        if not hasattr(bpy.types.Object, property_name):
            continue
        try:
            delattr(bpy.types.Object, property_name)
        except Exception:
            pass


def _secret_paint_panel_drag_object_from_context(context):
    try:
        button_operator = getattr(context, "button_operator", None)
    except Exception:
        button_operator = None
    try:
        button_operator_id = getattr(getattr(button_operator, "bl_rna", None), "identifier", "")
    except Exception:
        button_operator_id = ""
    if button_operator is not None and button_operator_id not in {"SECRET_OT_panel_drag_reorder", ""}:
        return None
    try:
        object_name = getattr(button_operator, "object_name", "")
    except Exception:
        object_name = ""
    if object_name:
        buttonobj = bpy.data.objects.get(object_name)
        if buttonobj is not None:
            return buttonobj

    try:
        button_prop = getattr(context, "button_prop", None)
    except Exception:
        button_prop = None
    if getattr(button_prop, "identifier", "") not in {"secret_paint_panel_drag_pad", "secret_paint_panel_drag_handle"}:
        return None

    try:
        button_pointer = getattr(context, "button_pointer", None)
    except Exception:
        button_pointer = None
    if isinstance(button_pointer, bpy.types.Object):
        return button_pointer

    id_data = getattr(button_pointer, "id_data", None)
    if isinstance(id_data, bpy.types.Object):
        return id_data
    return None


def _secret_paint_panel_property_object_from_context(context, property_names):
    try:
        button_prop = getattr(context, "button_prop", None)
    except Exception:
        return "", None
    property_name = getattr(button_prop, "identifier", "")
    if property_name not in property_names:
        return property_name, None

    try:
        button_pointer = getattr(context, "button_pointer", None)
    except Exception:
        button_pointer = None
    if isinstance(button_pointer, bpy.types.Object):
        return property_name, button_pointer

    id_data = getattr(button_pointer, "id_data", None)
    if isinstance(id_data, bpy.types.Object):
        return property_name, id_data
    return property_name, None


class panel_modified_click(bpy.types.Operator):
    """Run alternate actions for modified clicks on drag-capable panel toggles."""
    bl_idname = "secret.panel_modified_click"
    bl_label = "Paint System Alternate Toggle"
    bl_options = {'UNDO', 'INTERNAL'}

    def invoke(self, context, event):
        if getattr(getattr(context, "area", None), "type", "") != 'VIEW_3D':
            return {'PASS_THROUGH'}
        if getattr(getattr(context, "region", None), "type", "") != 'UI':
            return {'PASS_THROUGH'}

        property_name, buttonobj = _secret_paint_panel_property_object_from_context(
            context,
            {SECRET_PAINT_PANEL_VERTEX_PROP, SECRET_PAINT_PANEL_RENDER_PROP, SECRET_PAINT_PANEL_MASK_PROP},
        )
        if buttonobj is None:
            return {'PASS_THROUGH'}

        alt = bool(getattr(event, "alt", False))
        shift = bool(getattr(event, "shift", False))
        if property_name == SECRET_PAINT_PANEL_VERTEX_PROP:
            if not alt:
                return {'PASS_THROUGH'}
            _secret_paint_panel_queue_vertex_action(context, buttonobj, remove_vgroup=True)
        elif property_name == SECRET_PAINT_PANEL_RENDER_PROP:
            _secret_paint_panel_render_modified_click(context, buttonobj, alt=alt, shift=shift)
        elif property_name == SECRET_PAINT_PANEL_MASK_PROP:
            _secret_paint_panel_mask_modified_click(context, buttonobj, alt=alt, shift=shift)
        else:
            return {'PASS_THROUGH'}
        return {'FINISHED'}


def _secret_paint_keymap_item_modifier_value(kmi, modifier_name):
    try:
        value = getattr(kmi, modifier_name)
    except Exception:
        return False
    return bool(value) if value != -1 else False


def _secret_paint_panel_preferred_key_spec(specs, *, preferred_type=""):
    if not specs:
        return []

    def has_no_modifiers(spec):
        return (
            len(spec) >= 7
            and not bool(spec[2])
            and not bool(spec[3])
            and not bool(spec[4])
            and not bool(spec[5])
            and (spec[6] or "NONE") == "NONE"
        )

    if preferred_type:
        for spec in specs:
            if spec[0] == preferred_type and has_no_modifiers(spec):
                return [spec]
        for spec in specs:
            if spec[0] == preferred_type:
                return [spec]

    for spec in specs:
        if has_no_modifiers(spec):
            return [spec]
    return [specs[0]]


def _secret_paint_panel_translate_key_specs():
    wm = getattr(bpy.context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None) if wm else None
    keymap_names = ("Object Mode", "3D View")
    mouse_event_types = {
        "LEFTMOUSE", "MIDDLEMOUSE", "RIGHTMOUSE",
        "BUTTON4MOUSE", "BUTTON5MOUSE", "BUTTON6MOUSE", "BUTTON7MOUSE",
        "MOUSEMOVE", "INBETWEEN_MOUSEMOVE",
        "WHEELUPMOUSE", "WHEELDOWNMOUSE", "WHEELINMOUSE", "WHEELOUTMOUSE",
        "WHEELLEFTMOUSE", "WHEELRIGHTMOUSE",
        "TRACKPADPAN", "TRACKPADZOOM", "MOUSEROTATE", "MOUSESMARTZOOM",
    }
    skip_property_names = {"translate_origin", "texture_space"}

    def keyconfig_specs(kconf):
        if kconf is None:
            return []
        specs = []
        seen = set()
        for keymap_name in keymap_names:
            km = kconf.keymaps.get(keymap_name)
            if km is None:
                continue
            for kmi in km.keymap_items:
                if getattr(kmi, "idname", "") != "transform.translate":
                    continue
                if not getattr(kmi, "active", False):
                    continue
                if getattr(kmi, "value", "") != "PRESS":
                    continue
                event_type = getattr(kmi, "type", "")
                if event_type in mouse_event_types:
                    continue

                skip_item = False
                properties = getattr(kmi, "properties", None)
                for property_name in skip_property_names:
                    try:
                        if bool(getattr(properties, property_name)):
                            skip_item = True
                            break
                    except Exception:
                        pass
                if skip_item:
                    continue

                spec = (
                    event_type,
                    "PRESS",
                    _secret_paint_keymap_item_modifier_value(kmi, "shift"),
                    _secret_paint_keymap_item_modifier_value(kmi, "ctrl"),
                    _secret_paint_keymap_item_modifier_value(kmi, "alt"),
                    _secret_paint_keymap_item_modifier_value(kmi, "oskey"),
                    getattr(kmi, "key_modifier", "NONE") or "NONE",
                )
                if spec in seen:
                    continue
                seen.add(spec)
                specs.append(spec)
        return specs

    if keyconfigs is not None:
        user_specs = keyconfig_specs(getattr(keyconfigs, "user", None))
        if user_specs:
            return _secret_paint_panel_preferred_key_spec(user_specs)

        active_specs = keyconfig_specs(getattr(keyconfigs, "active", None))
        if active_specs:
            return _secret_paint_panel_preferred_key_spec(active_specs)

        default_specs = keyconfig_specs(getattr(keyconfigs, "default", None))
        if default_specs:
            return _secret_paint_panel_preferred_key_spec(default_specs)

    return [("G", "PRESS", False, False, False, False, "NONE")]


def _secret_paint_panel_delete_key_specs():
    wm = getattr(bpy.context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None) if wm else None
    mouse_event_types = {
        "LEFTMOUSE", "MIDDLEMOUSE", "RIGHTMOUSE",
        "BUTTON4MOUSE", "BUTTON5MOUSE", "BUTTON6MOUSE", "BUTTON7MOUSE",
        "MOUSEMOVE", "INBETWEEN_MOUSEMOVE",
        "WHEELUPMOUSE", "WHEELDOWNMOUSE", "WHEELINMOUSE", "WHEELOUTMOUSE",
        "WHEELLEFTMOUSE", "WHEELRIGHTMOUSE",
        "TRACKPADPAN", "TRACKPADZOOM", "MOUSEROTATE", "MOUSESMARTZOOM",
    }

    def keyconfig_specs(kconf):
        if kconf is None:
            return []
        specs = []
        seen = set()
        for keymap_name in ("Object Mode", "3D View"):
            km = kconf.keymaps.get(keymap_name)
            if km is None:
                continue
            for kmi in km.keymap_items:
                if getattr(kmi, "idname", "") != "object.delete":
                    continue
                if not getattr(kmi, "active", False):
                    continue
                event_type = getattr(kmi, "type", "")
                if event_type in mouse_event_types:
                    continue
                spec = (
                    event_type,
                    getattr(kmi, "value", "PRESS") or "PRESS",
                    _secret_paint_keymap_item_modifier_value(kmi, "shift"),
                    _secret_paint_keymap_item_modifier_value(kmi, "ctrl"),
                    _secret_paint_keymap_item_modifier_value(kmi, "alt"),
                    _secret_paint_keymap_item_modifier_value(kmi, "oskey"),
                    getattr(kmi, "key_modifier", "NONE") or "NONE",
                )
                if spec not in seen:
                    seen.add(spec)
                    specs.append(spec)
        return specs

    if keyconfigs is not None:
        user_specs = keyconfig_specs(getattr(keyconfigs, "user", None))
        if user_specs:
            return _secret_paint_panel_preferred_key_spec(user_specs, preferred_type="X")

        active_specs = keyconfig_specs(getattr(keyconfigs, "active", None))
        if active_specs:
            return _secret_paint_panel_preferred_key_spec(active_specs, preferred_type="X")

        default_specs = keyconfig_specs(getattr(keyconfigs, "default", None))
        if default_specs:
            return _secret_paint_panel_preferred_key_spec(default_specs, preferred_type="X")

    return [("X", "PRESS", False, False, False, False, "NONE")]


def _secret_paint_panel_shortcut_item_spec(kmi):
    return (
        getattr(kmi, "type", ""),
        getattr(kmi, "value", "PRESS") or "PRESS",
        _secret_paint_keymap_item_modifier_value(kmi, "shift"),
        _secret_paint_keymap_item_modifier_value(kmi, "ctrl"),
        _secret_paint_keymap_item_modifier_value(kmi, "alt"),
        _secret_paint_keymap_item_modifier_value(kmi, "oskey"),
        getattr(kmi, "key_modifier", "NONE") or "NONE",
    )


def _secret_paint_panel_shortcut_target_id(km):
    if (
        getattr(km, "name", "") == "3D View"
        and getattr(km, "space_type", "") == 'VIEW_3D'
        and getattr(km, "region_type", "") == 'UI'
    ):
        return "VIEW3D_UI"
    if getattr(km, "name", "") == "User Interface":
        return "USER_INTERFACE"
    return ""


def _secret_paint_panel_registered_shortcut_specs(addon_keymaps, operator_id):
    registered_specs = []
    for km, kmi in addon_keymaps:
        try:
            if getattr(kmi, "idname", "") != operator_id:
                continue
        except (ReferenceError, RuntimeError):
            continue
        target_id = _secret_paint_panel_shortcut_target_id(km)
        if target_id:
            registered_specs.append((target_id, _secret_paint_panel_shortcut_item_spec(kmi)))
    return registered_specs


def _secret_paint_panel_desired_shortcut_specs(source_specs):
    return [
        ("USER_INTERFACE", spec)
        for spec in source_specs
    ]


def _secret_paint_panel_add_keyboard_shortcuts(addon_keymaps, keymaps, operator_id, source_specs):
    for event_type, event_value, shift, ctrl, alt, oskey, key_modifier in source_specs:
        km = keymaps.new("User Interface")
        kmi = km.keymap_items.new(
            operator_id,
            event_type,
            event_value,
            shift=shift,
            ctrl=ctrl,
            alt=alt,
            oskey=oskey,
            key_modifier=key_modifier,
            head=True,
        )
        addon_keymaps.append((km, kmi))


def sync_secret_paint_panel_drag_keymap(addon_keymaps, keymaps):
    source_specs_by_operator = {
        "secret.panel_keyboard_reorder": _secret_paint_panel_translate_key_specs(),
        "secret.panel_keyboard_delete": _secret_paint_panel_delete_key_specs(),
    }
    changed_operator_ids = {
        operator_id
        for operator_id, source_specs in source_specs_by_operator.items()
        if _secret_paint_panel_registered_shortcut_specs(addon_keymaps, operator_id)
        != _secret_paint_panel_desired_shortcut_specs(source_specs)
    }
    if not changed_operator_ids:
        return False

    for index in range(len(addon_keymaps) - 1, -1, -1):
        km, kmi = addon_keymaps[index]
        try:
            operator_id = getattr(kmi, "idname", "")
        except (ReferenceError, RuntimeError):
            operator_id = ""
        if operator_id not in changed_operator_ids:
            continue
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
        del addon_keymaps[index]

    for operator_id in ("secret.panel_keyboard_reorder", "secret.panel_keyboard_delete"):
        if operator_id in changed_operator_ids:
            _secret_paint_panel_add_keyboard_shortcuts(
                addon_keymaps,
                keymaps,
                operator_id,
                source_specs_by_operator[operator_id],
            )
    return True


def register_secret_paint_panel_drag_keymap(addon_keymaps, keymaps):
    sync_secret_paint_panel_drag_keymap(addon_keymaps, keymaps)

    if platform.system() != "Windows":
        for shift, alt in ((True, False), (False, True), (True, True)):
            for keymap_name, keymap_kwargs in (
                ("3D View", {"space_type": 'VIEW_3D', "region_type": 'UI'}),
                ("User Interface", {}),
            ):
                km = keymaps.new(keymap_name, **keymap_kwargs)
                kmi = km.keymap_items.new(
                    "secret.panel_modified_click",
                    "LEFTMOUSE",
                    "PRESS",
                    shift=shift,
                    alt=alt,
                    head=True,
                )
                addon_keymaps.append((km, kmi))


class panel_keyboard_reorder(bpy.types.Operator):
    """Use the Move shortcut to reorder selected Paint Systems from the side panel"""
    bl_idname = "secret.panel_keyboard_reorder"
    bl_label = "Move Paint Systems in Panel"
    bl_options = {'UNDO', 'BLOCKING', 'GRAB_CURSOR_Y', 'MODAL_PRIORITY'}

    def invoke(self, context, event):
        if getattr(getattr(context, "area", None), "type", "") != 'VIEW_3D':
            return {'PASS_THROUGH'}
        if getattr(getattr(context, "region", None), "type", "") != 'UI':
            return {'PASS_THROUGH'}

        anchor_obj = _secret_paint_panel_keyboard_anchor_object(context)
        if anchor_obj is None:
            return {'PASS_THROUGH'}

        global _SIDE_PANEL_DRAG_OBJECT_NAME
        self.object_name = anchor_obj.name
        self._start_mouse_y = event.mouse_y
        self._reorder_snapshot = _secret_paint_panel_make_reorder_snapshot(context, self.object_name)
        self._updated_modifier = False
        self._moved = False
        self._last_reorder_delta = 0.0
        _SIDE_PANEL_DRAG_OBJECT_NAME = self.object_name
        _clear_side_panel_count_cache(reason="panel_keyboard_reorder_start")
        _secret_paint_tag_redraw_view3d_areas(context)

        try:
            context.workspace.status_text_set(text="Move mouse up or down to reorder selected paint systems")
        except Exception:
            pass
        try:
            context.window.cursor_modal_set('SCROLL_Y')
        except Exception:
            pass
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return self._finish(context, cancelled=True)

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'EVT_TWEAK_L'}:
            row_delta = self._row_delta_from_anchor(event)
            if abs(row_delta - getattr(self, "_last_reorder_delta", 0.0)) >= 0.1:
                self._apply_live_delta(context, row_delta)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value in {'PRESS', 'RELEASE'}:
            return self._finish(context, cancelled=False)

        return {'RUNNING_MODAL'}

    def _row_delta_from_anchor(self, event):
        return (self._start_mouse_y - event.mouse_y) / SECRET_PAINT_PANEL_DRAG_ROW_PIXELS

    def _apply_live_delta(self, context, row_delta):
        _secret_paint_panel_restore_reorder_snapshot(context, getattr(self, "_reorder_snapshot", None))
        if abs(float(row_delta)) < SECRET_PAINT_PANEL_REORDER_DEADZONE_ROWS:
            self._last_reorder_delta = row_delta
            return False
        moved = _secret_paint_panel_reorder_object(
            context,
            self.object_name,
            row_delta,
            update_modifier=not self._updated_modifier,
        )
        self._last_reorder_delta = row_delta
        if not moved:
            return False
        self._updated_modifier = True
        self._moved = True
        return True

    def _finish(self, context, cancelled=False):
        global _SIDE_PANEL_DRAG_OBJECT_NAME
        if cancelled:
            _secret_paint_panel_restore_reorder_snapshot(context, getattr(self, "_reorder_snapshot", None))
        _SIDE_PANEL_DRAG_OBJECT_NAME = ""
        _clear_side_panel_count_cache(reason="panel_keyboard_reorder_finish")
        _secret_paint_tag_redraw_view3d_areas(context)
        try:
            context.window.cursor_modal_restore()
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text=None)
        except Exception:
            pass
        return {'CANCELLED'} if cancelled else {'FINISHED'}


class panel_keyboard_delete(bpy.types.Operator):
    """Use the Object Delete shortcut to delete selected Paint Systems from the side panel."""
    bl_idname = "secret.panel_keyboard_delete"
    bl_label = "Delete Paint Systems in Panel"
    bl_options = {'UNDO'}

    def invoke(self, context, _event):
        if getattr(getattr(context, "area", None), "type", "") != 'VIEW_3D':
            return {'PASS_THROUGH'}
        if getattr(getattr(context, "region", None), "type", "") != 'UI':
            return {'PASS_THROUGH'}

        systems_to_delete = [
            obj
            for obj in list(getattr(context, "selected_objects", []))
            if (
                _secret_paint_system_modifier(obj) is not None
                and _secret_paint_panel_object_is_in_view_layer(obj)
            )
        ]
        if not systems_to_delete:
            return {'PASS_THROUGH'}

        _secret_paint_panel_exit_paint_mode(context)
        _secret_paint_panel_set_object_mode(context)

        active_obj = getattr(context.view_layer.objects, "active", None)
        anchor_obj = active_obj if active_obj in systems_to_delete else systems_to_delete[0]
        affected_surfaces = []
        for system_obj in systems_to_delete:
            surface_obj = getattr(system_obj, "parent", None)
            if surface_obj is None:
                modifier = _secret_paint_system_modifier(system_obj)
                try:
                    surface_obj = modifier["Input_73"] if modifier is not None else None
                except Exception:
                    surface_obj = None
            if surface_obj is not None and surface_obj not in affected_surfaces:
                affected_surfaces.append(surface_obj)

        replacement_obj = getattr(anchor_obj, "parent", None)
        if replacement_obj is None:
            modifier = _secret_paint_system_modifier(anchor_obj)
            try:
                replacement_obj = modifier["Input_73"] if modifier is not None else None
            except Exception:
                replacement_obj = None

        for system_obj in systems_to_delete:
            try:
                bpy.data.objects.remove(system_obj, do_unlink=True)
            except Exception:
                pass

        for surface_obj in affected_surfaces:
            try:
                hair = find_all_listed_paintsystems(context, activeobj=surface_obj)
                biome_remove_gaps(context, hair)
            except Exception:
                pass

        if replacement_obj is not None and _secret_paint_panel_object_is_in_view_layer(replacement_obj):
            try:
                for selected_obj in list(getattr(context, "selected_objects", [])):
                    selected_obj.select_set(False)
                replacement_obj.select_set(True)
                context.view_layer.objects.active = replacement_obj
            except Exception:
                pass

        _clear_side_panel_count_cache(reason="panel_keyboard_delete")
        _secret_paint_tag_redraw_view3d_areas(context)
        return {'FINISHED'}


class panel_drag_reorder_press(bpy.types.Operator):
    """Click-drag this grip to reorder a Paint System"""
    bl_idname = "secret.panel_drag_reorder_press"
    bl_label = "Drag Reorder"
    bl_options = {'UNDO', 'BLOCKING', 'GRAB_CURSOR_Y', 'MODAL_PRIORITY'}

    def invoke(self, context, event):
        buttonobj = _secret_paint_panel_drag_object_from_context(context)
        if buttonobj is None:
            return {'PASS_THROUGH'}

        global _SIDE_PANEL_DRAG_OBJECT_NAME
        self.object_name = buttonobj.name
        self._start_mouse_y = self._previous_mouse_y(event) if self._is_drag_start_event(event) else event.mouse_y
        self._reorder_snapshot = _secret_paint_panel_make_reorder_snapshot(context, self.object_name)
        self._updated_modifier = False
        self._moved = False
        self._last_reorder_delta = 0.0
        _SIDE_PANEL_DRAG_OBJECT_NAME = self.object_name
        _clear_side_panel_count_cache(reason="panel_drag_press_start")
        _secret_paint_tag_redraw_view3d_areas(context)

        first_delta = self._row_delta_from_anchor(event) if self._is_drag_start_event(event) else 0
        if first_delta != 0:
            self._apply_live_delta(context, first_delta)

        try:
            context.window.cursor_modal_set('SCROLL_Y')
        except Exception:
            pass
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return self._finish(context, cancelled=True)

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'EVT_TWEAK_L'}:
            row_delta = self._row_delta_from_anchor(event)
            if abs(row_delta - getattr(self, "_last_reorder_delta", 0.0)) >= 0.1:
                self._apply_live_delta(context, row_delta)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value in {'PRESS', 'RELEASE'}:
            return self._finish(context, cancelled=False)

        return {'RUNNING_MODAL'}

    def _row_delta_from_anchor(self, event):
        return (self._start_mouse_y - event.mouse_y) / SECRET_PAINT_PANEL_DRAG_ROW_PIXELS

    def _is_drag_start_event(self, event):
        return event.type in {'EVT_TWEAK_L'} or getattr(event, "value", "") == 'CLICK_DRAG'

    def _previous_mouse_y(self, event):
        try:
            return event.mouse_prev_y
        except Exception:
            return event.mouse_y

    def _apply_live_delta(self, context, row_delta):
        _secret_paint_panel_restore_reorder_snapshot(context, getattr(self, "_reorder_snapshot", None))
        if abs(float(row_delta)) < SECRET_PAINT_PANEL_REORDER_DEADZONE_ROWS:
            self._last_reorder_delta = row_delta
            return False
        moved = _secret_paint_panel_reorder_object(
            context,
            self.object_name,
            row_delta,
            update_modifier=not self._updated_modifier,
        )
        self._last_reorder_delta = row_delta
        if not moved:
            return False
        self._updated_modifier = True
        self._moved = True
        return True

    def _finish(self, context, cancelled=False):
        global _SIDE_PANEL_DRAG_OBJECT_NAME
        if cancelled:
            _secret_paint_panel_restore_reorder_snapshot(context, getattr(self, "_reorder_snapshot", None))
        _SIDE_PANEL_DRAG_OBJECT_NAME = ""
        _clear_side_panel_count_cache(reason="panel_drag_press_finish")
        _secret_paint_tag_redraw_view3d_areas(context)
        try:
            context.window.cursor_modal_restore()
        except Exception:
            pass
        return {'CANCELLED'} if cancelled else {'FINISHED'}


class panel_drag_reorder(bpy.types.Operator):
    """Drag up or down to reorder this Paint System. Drag across rows to move it to another biome"""
    bl_idname = "secret.panel_drag_reorder"
    bl_label = "Drag Reorder"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR_Y', 'MODAL_PRIORITY'}
    object_name: bpy.props.StringProperty()

    def invoke(self, context, event):
        global _SIDE_PANEL_DRAG_OBJECT_NAME
        self._start_mouse_y = self._previous_mouse_y(event) if self._is_drag_start_event(event) else event.mouse_y
        self._reorder_snapshot = _secret_paint_panel_make_reorder_snapshot(context, self.object_name)
        self._updated_modifier = False
        self._moved = False
        self._last_reorder_delta = 0.0
        _SIDE_PANEL_DRAG_OBJECT_NAME = self.object_name
        _clear_side_panel_count_cache(reason="panel_drag_start")
        _secret_paint_tag_redraw_view3d_areas(context)

        first_delta = self._row_delta_from_anchor(event) if self._is_drag_start_event(event) else 0
        if first_delta != 0:
            self._apply_live_delta(context, first_delta)

        try:
            context.workspace.status_text_set(text="Drag up or down to reorder this paint system")
        except Exception:
            pass
        try:
            context.window.cursor_modal_set('SCROLL_Y')
        except Exception:
            pass
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return self._finish(context, cancelled=True)

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'EVT_TWEAK_L'}:
            row_delta = self._row_delta_from_anchor(event)
            if abs(row_delta - getattr(self, "_last_reorder_delta", 0.0)) >= 0.1:
                self._apply_live_delta(context, row_delta)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value in {'PRESS', 'RELEASE'}:
            return self._finish(context, cancelled=False)

        return {'RUNNING_MODAL'}

    def _is_drag_start_event(self, event):
        return event.type in {'EVT_TWEAK_L'} or getattr(event, "value", "") == 'CLICK_DRAG'

    def _previous_mouse_y(self, event):
        try:
            return event.mouse_prev_y
        except Exception:
            return event.mouse_y

    def _row_delta_from_anchor(self, event):
        return (self._start_mouse_y - event.mouse_y) / SECRET_PAINT_PANEL_DRAG_ROW_PIXELS

    def _apply_live_delta(self, context, row_delta):
        _secret_paint_panel_restore_reorder_snapshot(context, getattr(self, "_reorder_snapshot", None))
        if abs(float(row_delta)) < SECRET_PAINT_PANEL_REORDER_DEADZONE_ROWS:
            self._last_reorder_delta = row_delta
            return False
        moved = _secret_paint_panel_reorder_object(
            context,
            self.object_name,
            row_delta,
            update_modifier=not self._updated_modifier,
        )
        self._last_reorder_delta = row_delta
        if not moved:
            return False
        self._updated_modifier = True
        self._moved = True
        return True

    def _finish(self, context, cancelled=False):
        global _SIDE_PANEL_DRAG_OBJECT_NAME
        if cancelled:
            _secret_paint_panel_restore_reorder_snapshot(context, getattr(self, "_reorder_snapshot", None))
        _SIDE_PANEL_DRAG_OBJECT_NAME = ""
        _clear_side_panel_count_cache(reason="panel_drag_finish")
        _secret_paint_tag_redraw_view3d_areas(context)
        try:
            context.window.cursor_modal_restore()
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text=None)
        except Exception:
            pass
        return {'CANCELLED'} if cancelled else {'FINISHED'}


class biomegroupreorder(bpy.types.Operator):
    """Change Biome for the selected Paint Systems, Alt+Click to move at the top of the stack"""
    bl_idname = "secret.biomegroupreorder"
    bl_label = "Move Up"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    # def execute(self, context):
    def invoke(self, context, event):
        _secret_paint_panel_exit_paint_mode(context)
        buttonobj = bpy.data.objects.get(self.object_name)
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj] # when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object

        if event.alt: move_to_extreme=True # move_to_extreme=True if event.alt else move_to_extreme=False
        else: move_to_extreme=False
        biomegroupreorder_f(context, direction= -1, activeobj = buttonobj, objselection=objselection, move_to_extreme=move_to_extreme)
        return{'FINISHED'}
class biomegroupreorder2(bpy.types.Operator):
    """Change Biome for the selected Paint Systems, Alt+Click to move at the bottom of the stack"""
    bl_idname = "secret.biomegroupreorder2"
    bl_label = "Move Down"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    # def execute(self, context):
    def invoke(self, context, event):
        _secret_paint_panel_exit_paint_mode(context)
        buttonobj = bpy.data.objects.get(self.object_name)
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj] # when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object

        if event.alt: move_to_extreme = True  # move_to_extreme=True if event.alt else move_to_extreme=False
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
    # def execute(self, context):
    def invoke(self, context, event):
        buttonbiome = int(self.object_biome)
        buttonobj = bpy.data.objects.get(self.object_name)
        if buttonobj is None:
            return {'CANCELLED'}
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj) #sometimes the active object might not be selected
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]   #when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object


        # # all_bgroups=[]
        # for hayr in hair[:]:
        #     # if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
        hair = find_all_listed_paintsystems(context, activeobj=context.object)
        hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == buttonbiome]
        for ob in objselection[:]:  #constrain the selected objects to the active biome from where you pressed the button
            if ob not in hair_in_bgroup: objselection.remove(ob)
    ############################## varaibles 1 (main)




        #SOLO THIS LAYER  (the original selection becomes visible and marked as original "Socket_4", everything else gets turned off and marked as a temporary turn off "Socket_3"; this way I'm not affecting and toggling systems that were turned off by hand)
        if event.alt:

            #IF CLICKING FROM THE ORIGINAL SYSTEM THAT YOU PREVIOUSLY SOLOED:  RESET EVERYTHING TO ORIGINAL STATE
            if buttonobj.modifiers[0]["Socket_4"] == True:   # if True in [hairr.modifiers[0]["Socket_3"] for hairr in hair_in_bgroup]:
                for hayii in hair_in_bgroup:
                    if hayii.type == "CURVES":
                        for modif in hayii.modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if modif["Socket_3"]==True: modif["Input_99"] = not modif["Input_99"]  #TOGGLE BACK TO ORIGINAL STATE
                                modif["Socket_3"] = False  # RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                                modif["Socket_4"] = False  # RESET THE MARKED AS ORIGINAL CHECKBOX
                                hayii.location = hayii.location


            #IF YOU'SOLOING A SYSTEM THAT WASN'T THE ORIGINAL SYSTEM YOU SOLOED BEFORE: RESET ALL CHECKBOXES AND SOLO FROM SCRATCH
            else:

                #RESET ALL TEMPORARY CHECKBOXES ("TURN OFF SOLOED TEMP")
                for hayyur in hair_in_bgroup:  #hair[:]:
                    if hayyur.type == "CURVES":
                        for modif in hayyur.modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                modif["Socket_3"] = False  # RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                                modif["Socket_4"] = False  # RESET THE MARKED AS ORIGINAL CHECKBOX
                                hayyur.location = hayyur.location

                for hayii in hair_in_bgroup:
                    if hayii.type == "CURVES":
                        for modif in hayii.modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                                #MARK OBJSELECTION AS ORIGINAL, IF ONE OF THE SYSTEMS IS HIDDEN: ENABLE, AND MARK   (IF WE'RE PROCESSING THE SYSTEM FROM WHICH WE CLICKED THE BUTTON, IT WILL BE MADE VISIBLE)
                                if hayii in objselection:
                                    if modif["Input_99"] == True:                 # if modif["Input_99"] == False: modif["Socket_3"] = True  #IF IT WAS ALREADY HIDDEN, MARK FOR TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP") (in order to toggle back and forth exactly as everything was)
                                        modif["Input_99"] = False #enable
                                        modif["Socket_3"] = True  #MARK FOR TOGGLE
                                    modif["Socket_4"] = True  #MARK AS ORIGINAL SOLOED

                                #IF WE'RE PROCESSING ANY OTHER SYSTEM THAT WASN'T SELECTED:
                                else:
                                    if modif["Input_99"] == False: #CHECK IF THE SYSTEM WAS ALREADY ENABLED (because a system might already be manually hidden)
                                        modif["Socket_3"] = True #ONLY MARK THE SYSTEMS THAT WE'RE HIDING  (in order to avoid toggling visibility of systems that were turned off by hand)
                                        modif["Input_99"] = True  #HIDE IT

                                hayii.location=hayii.location #update paint system

        #HIDE IN THE VIEWPORT
        elif event.shift:
            mute_visibility_render = buttonobj.modifiers[0]["Input_99"]
            mute_visibility_viewport = buttonobj.modifiers[0]["Socket_14"]

            if mute_visibility_render == True:    #EVEN IF IT'S THE WRONG BEHAVIOR, IT'S MORE INTUITIVE TO TOGGLE THE CURRENT STATE BACK TO EVERYTHING VISIBLE
                mute_visibility_render_new = False
                mute_visibility_viewport_new = True
            elif mute_visibility_viewport == True and mute_visibility_render == False: # re enable both
                mute_visibility_render_new = False
                mute_visibility_viewport_new = False
            elif mute_visibility_viewport == False and mute_visibility_render == False:
                mute_visibility_render_new = False
                mute_visibility_viewport_new = True

            for obj in objselection:
                if obj.type == "CURVES":
                    for modif in obj.modifiers:
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            # modif["Socket_14"] = not mute_visibility_viewport
                            modif["Input_99"] = mute_visibility_render_new
                            modif["Socket_14"] = mute_visibility_viewport_new
                            obj.location=obj.location



        #ONLY HIDE SELECTED, also reset all other "TURN OFF SOLOED TEMP" checkboxes
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
                    for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            # modif["Input_99"] = not mute_visibility_render
                            modif["Input_99"] = mute_visibility_render_new
                            modif["Socket_14"] = mute_visibility_viewport_new
                            obj.location=obj.location

            for hayyur in hair_in_bgroup:  #hair[:]:  #RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                if hayyur.type == "CURVES":
                    for modif in hayyur.modifiers:  # modifier.name == "GeometryNodes"
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            modif["Socket_3"] = False  #RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                            modif["Socket_4"] = False  # RESET THE MARKED AS ORIGINAL CHECKBOX
                            hayyur.location = hayyur.location


    # def invoke(self, context, event):
    #     if event.alt:
    #         obj = bpy.data.objects.get(self.object_name)
    #         viewportstatus = obj.hide_render
    #         selected_objects = bpy.context.selected_objects
    #         for obj in selected_objects:
    #             obj.hide_render = not viewportstatus
    #     elif event.ctrl:
    #         obj = bpy.data.objects.get(self.object_name)
    #         viewportstatus = obj.hide_render
    #         parent = obj.parent
    #         if parent:
    #             siblings = parent.children
    #             for sibling in siblings:
    #                 sibling.hide_render = not viewportstatus
    #     else:
    #         return self.execute(context)
    #     return {'FINISHED'}


        _clear_side_panel_count_cache(reason="toggle_visibilityrender")
        _secret_paint_tag_redraw_view3d_areas(context)
        return {'FINISHED'}
class ToggleVisibilityOperatorRenderBiome(bpy.types.Operator):
    """Turn off The entire biome. Shift+Click to Disable in the Viewport. Alt+Click to 'Solo' a Biome and mute the other ones"""
    bl_idname = "secret.toggle_visibilityrender_biome"
    bl_label = "Toggle Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty()
    # def execute(self, context):
    def invoke(self, context, event):
        hair = find_all_listed_paintsystems(context, activeobj=context.object)
        hair_in_bgroup =[]
        hair_in_OTHER_bgroups =[]
        for hayr in hair[:]:
            if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome): hair_in_bgroup.append(hayr[0])
            else: hair_in_OTHER_bgroups.append(hayr[0])
        ################################################ v







        if event.alt: #SOLO THIS BIOME


            #IF CLICKING FROM THE ORIGINAL BIOME THAT YOU SOLOED:  RESET EVERYTHING TO ORIGINAL STATE
            if True in [hairr.modifiers[0]["Socket_6"] for hairr in hair_in_bgroup]:
                # mute_system = True if False in [hairr.modifiers[0]["Socket_2"] for hairr in hair_in_OTHER_bgroups] else False  # IF THERE'S A SINGLE ACTIVE SYSTEM, DISABLE EVERYTHING. ELSE ENABLE EVERYTHING
                for hayii in hair[:]:
                    if hayii[0].type == "CURVES":
                        for modif in hayii[0].modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                if modif["Socket_5"]==True: modif["Socket_2"] = not modif["Socket_2"]  #TOGGLE BACK TO ORIGINAL STATE
                                modif["Socket_5"] = False  # RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                                modif["Socket_6"] = False  # RESET THE MARKED AS ORIGINAL CHECKBOX
                                hayii[0].location = hayii[0].location



            #IF YOU'SOLOING A BIOME THAT WASN'T THE ORIGINAL SYSTEM YOU SOLOED BEFORE: RESET ALL CHECKBOXES AND SOLO FROM SCRATCH
            else:

                #RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                for hayyur in hair[:]:  # RESET THE BIOME TEMPORARY CHECKBOXES ("TURN OFF SOLOED TEMP")
                    if hayyur[0].type == "CURVES":
                        for modif in hayyur[0].modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                                modif["Socket_5"] = False  # RESET THE TEMPORARY BIOME CHECKBOX ("TURN OFF SOLOED TEMP")
                                modif["Socket_6"] = False  # RESET THE MARKED BIOME AS ORIGINAL CHECKBOX
                                hayyur[0].location = hayyur[0].location

                for hayii in hair[:]:
                    if hayii[0].type == "CURVES":
                        for modif in hayii[0].modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                                #MARK CLICKED BIOME AS ORIGINAL, IF ONE OF THE SYSTEMS IS HIDDEN: ENABLE, AND MARK   (IF WE'RE PROCESSING THE SYSTEM FROM WHICH WE CLICKED THE BUTTON, IT WILL BE MADE VISIBLE)
                                if hayii[0] in hair_in_bgroup:
                                    if modif["Socket_2"] == True:                 # if modif["Input_99"] == False: modif["Socket_3"] = True  #IF IT WAS ALREADY HIDDEN, MARK FOR TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP") (in order to toggle back and forth exactly as everything was)
                                        modif["Socket_2"] = False #enable biome
                                        modif["Socket_5"] = True  #MARK FOR TOGGLE
                                    modif["Socket_6"] = True  #MARK AS ORIGINAL SOLOED

                                #IF WE'RE PROCESSING ANY OTHER SYSTEM THAT WASN'T SELECTED:
                                else:
                                    if modif["Socket_2"] == False: #CHECK IF THE SYSTEM WAS ALREADY ENABLED (because a system might already be manually hidden)
                                        modif["Socket_5"] = True #ONLY MARK THE SYSTEMS THAT WE'RE HIDING  (in order to avoid toggling visibility of systems that were turned off by hand)
                                        modif["Socket_2"] = True  #HIDE IT

                                hayii[0].location=hayii[0].location #update paint system


        #HIDE IN THE VIEWPORT
        elif event.shift:
            mute_biome_visibility_render = False if False in [hairr.modifiers[0]["Socket_2"] for hairr in hair_in_bgroup] else True  # IF THERE'S A SINGLE ACTIVE SYSTEM, DISABLE EVERYTHING. ELSE ENABLE EVERYTHING
            mute_biome_visibility_viewport = False if False in [hairr.modifiers[0]["Socket_15"] for hairr in hair_in_bgroup] else True  # IF THERE'S A SINGLE ACTIVE SYSTEM, DISABLE EVERYTHING. ELSE ENABLE EVERYTHING

            if mute_biome_visibility_render == True:    #EVEN IF IT'S THE WRONG BEHAVIOR, IT'S MORE INTUITIVE TO TOGGLE THE CURRENT STATE BACK TO EVERYTHING VISIBLE
                mute_biome_visibility_render_new = False
                mute_biome_visibility_viewport_new = True
            elif mute_biome_visibility_viewport == True and mute_biome_visibility_render == False: # re enable both
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



        #ONLY HIDE SELECTED BIOME, also reset all other "TURN OFF SOLOED TEMP" checkboxes
        else:
            mute_biome_visibility_render = False if False in [hairr.modifiers[0]["Socket_2"] for hairr in hair_in_bgroup] else True  # IF THERE'S A SINGLE ACTIVE SYSTEM, DISABLE EVERYTHING. ELSE ENABLE EVERYTHING
            mute_biome_visibility_viewport = False if False in [hairr.modifiers[0]["Socket_15"] for hairr in hair_in_bgroup] else True  # IF THERE'S A SINGLE ACTIVE SYSTEM, DISABLE EVERYTHING. ELSE ENABLE EVERYTHING

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

            for hayii in hair[:]:  #RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                if hayii[0].type == "CURVES":
                    for modif in hayii[0].modifiers:  # modifier.name == "GeometryNodes"
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                            modif["Socket_5"] = False  # RESET THE TEMPORARY CHECKBOX ("TURN OFF SOLOED TEMP")
                            modif["Socket_6"] = False  # RESET THE MARKED AS ORIGINAL CHECKBOX
                            hayii[0].location = hayii[0].location
        _clear_side_panel_count_cache(reason="toggle_visibilityrender_biome")
        _secret_paint_tag_redraw_view3d_areas(context)
        return {'FINISHED'}
# Custom operator class for toggling display as bounds
class toggle_display_bounds(bpy.types.Operator):
    """Display as Bounds is the most efficient way to preserve the viewport performance when diplaying a large number of individual objects"""
    bl_idname = "secret.toggle_display_bounds"
    bl_label = "Toggle Display as Bounds"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: StringProperty()
    def invoke(self, context, event):
        buttonobj = bpy.data.objects.get(self.object_name)
        if buttonobj is None:
            return {'CANCELLED'}
        objselection = bpy.context.selected_objects
        if buttonobj not in objselection: objselection.append(buttonobj)
        # selected_objects = [obj for obj in bpy.context.selected_objects] #if obj.type == 'MESH']

        # when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object
        if buttonobj != bpy.context.active_object and buttonobj not in bpy.context.selected_objects: objselection = [buttonobj]


        buttonobj_status= buttonobj.display_type
        for obj in objselection:
            obj.display_type = 'BOUNDS' if buttonobj_status != 'BOUNDS' else 'TEXTURED'
        _clear_side_panel_count_cache(reason="toggle_display_bounds")
        _secret_paint_tag_redraw_view3d_areas(context)
        return {'FINISHED'}

    #     if event.alt:
    #         selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    #         for obj in selected_objects:
    #             obj.display_type = 'BOUNDS' if obj.display_type != 'BOUNDS' else 'TEXTURED'
    #     elif event.ctrl:
    #         obj = bpy.data.objects.get(self.object_name)
    #         if obj.display_type == "BOUNDS": viewportstatus = "TEXTURED"
    #         else: viewportstatus = "BOUNDS"
    #         parent = obj.parent
    #         if parent:
    #             siblings = parent.children
    #             for sibling in siblings:
    #                 sibling.display_type = viewportstatus
    #     else:
    #         return self.execute(context)
    #     return {'FINISHED'}
    #
    # def execute(self, context):
    #     obj = bpy.data.objects.get(self.object_name)
    #     if obj:
    #         obj.display_type = 'BOUNDS' if obj.display_type != 'BOUNDS' else 'TEXTURED'
    #     return {'FINISHED'}
class toggle_display_bounds_biome(bpy.types.Operator):
    """Display as Bounds is the most efficient way to preserve the viewport performance when diplaying a large number of individual objects"""
    bl_idname = "secret.toggle_display_bounds_biome"
    bl_label = "Toggle Display as Bounds"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: StringProperty()
    def invoke(self, context, event):
        obj = bpy.context.active_object
        if obj is None:
            return {'CANCELLED'}
        hair = []
        parent = obj.parent
        if obj.type == "CURVES" and parent:  # IF CURVE SELECTED
            for hai in parent.children:  # hair = getChildren(parent)
                if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                    for modifier in hai.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                            hair.append((hai, hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
        # ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
        elif obj.type == "MESH" or obj.type == "EMPTY":
            for hayr in bpy.context.scene.objects:
                # for hayr in obj.children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
                if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                    for modifier in hayr.modifiers:  # if mask selected, if brush obj selected, if terrain selected
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                            hair.append((hayr, hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
        # # hair_in_bgroup = []
        # for hayr in hair[:]:
        #     # if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
        hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]
        ####################################################

        if hair_in_bgroup:
            buttonobj_status= hair_in_bgroup[0].display_type
            for obj in hair_in_bgroup:
                obj.display_type = 'BOUNDS' if buttonobj_status != 'BOUNDS' else 'TEXTURED'
        _clear_side_panel_count_cache(reason="toggle_display_bounds_biome")
        _secret_paint_tag_redraw_view3d_areas(context)
        return {'FINISHED'}
class secretpaint_viewport_mask_biome(bpy.types.Operator):
    """Toggle Mask for the entire Biome"""
    bl_idname = "object.secretpaint_viewport_mask_biome"
    bl_label = "Temporary Viewport Mask"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: StringProperty()
    def invoke(self, context, event):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="object.secretpaint_viewport_mask_biome")

        obj = bpy.context.active_object
        hair = []
        parent = obj.parent
        if obj.type == "CURVES" and parent:  # IF CURVE SELECTED
            for hai in parent.children:  # hair = getChildren(parent)
                if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                    for modifier in hai.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                            hair.append((hai, hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
        # ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
        elif obj.type == "MESH" or obj.type == "EMPTY":
            for hayr in bpy.context.scene.objects:
                # for hayr in obj.children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
                if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                    for modifier in hayr.modifiers:  # if mask selected, if brush obj selected, if terrain selected
                        if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                            hair.append((hayr, hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
        # # hair_in_bgroup = []
        # for hayr in hair[:]:
        #     # if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
        hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]
        ####################################################

        maskobsel=None
        if hair_in_bgroup:

            if event.alt:  # select only mask object
                for x in bpy.context.selected_objects: x.select_set(False)  #deselect everything
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

#########################1111111111111111111111111111111111111##########################


#########   UNIV   FUNCTIONS  ######
def context3sculptbrush(context,**kwargs):
    pickup_trace = _get_pickup_trace()
    context3sculptbrush_start = time.perf_counter()
    if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
    else:activeobj = bpy.context.active_object
    if activeobj == None: activeobj = bpy.context.active_object
    keep_active_brush = kwargs.get("keep_active_brush") if "keep_active_brush" in kwargs else False
    brush_setup_mode = kwargs.get("brush_setup_mode", "legacy")
    use_native_brush_setup = brush_setup_mode == "native" and secret_paint_uses_curves_brush_assets()

    if (
        brush_setup_mode != "native"
        and activeobj
        and _secret_paint_system_modifier(activeobj) is not None
        and _secret_paint_world_paint_enabled(context)
    ):
        return _secret_paint_start_world_paint_for_object(context, activeobj)

    # bpy.context.tool_settings.curves_sculpt.brush = bpy.data.brushes["Density Curves"]

    #CONTEXT AREA TO 3D VIEWPORT
    # viewport_area = None
    # for area in bpy.context.screen.areas:
    #     if area.type == 'VIEW_3D':
    #         viewport_area = area
    #         break
    # if viewport_area:
    #     bpy.context.screen.areas[0] = viewport_area
    #     bpy.context.space_data = viewport_area.spaces.active

    # # For every screen in the file...
    # for screen in bpy.data.screens:
    #     for area in (a for a in screen.areas if a.type == 'VIEW_3D'):      # Find all the 3d viewports...
    #         for region in (r for r in area.regions if r.type == 'WINDOW'): # Now find the Window region too for that area...
    #             # Ok, we found the data we need to override
    #             # at minimum the 'area' and 'region' needs to be set, but here I set all 3 as an example
    #             override = {'screen': screen, 'area': area, 'region': region}
    #             # bpy.ops.view3d.view_center_cursor(override)
    #             bpy.ops.wm.tool_set_by_id(name="builtin_brush.Density")  # builtin_brush.density")

    # for area in bpy.context.screen.areas:  # add hair tool  #DEACTIVATED FOR paint_from_library
    #     if area.type == "VIEW_3D":
    #         override = bpy.context.copy()
    #         override["space_data"] = area.spaces[0]
    #         override["area"] = area
    #         # bpy.ops.wm.tool_set_by_id(name="builtin_brush.Density")  #builtin_brush.density")
    # # bpy.ops.wm.tool_set_by_id(override, name="builtin_brush.add")
    # # bpy.ops.wm.tool_set_by_id(name="builtin_brush.Density")  #builtin_brush.density")




    if activeobj.type == "CURVES":
        prepare_surface_start = time.perf_counter()

        if _secret_paint_node_tree_needs_update():
            secretpaint_update_modifier_f(context, upadte_provenance="context3sculptbrush")

        if activeobj.data.users >= 2 and activeobj.data.surface!=activeobj.parent: activeobj.data.surface = activeobj.parent  # REASSIGN SURFACE WHEN PAINTING SHIFT+D LINKED DUPLI HAIR
        try:
            _secret_paint_world_paint_module().ensure_secret_paint_system_stable_ids(context, activeobj)
        except Exception:
            pass
        try:
            ensure_secret_paint_system_stable_root_positions(activeobj)
        except Exception:
            pass
        #REASSIGN UVS
        # if not activeobj.data.surface_uv_map:
        active_render_UV = None
        custom_uv = None
        for uvmap in activeobj.data.surface.data.uv_layers:  # bpy.context.object.data.uv_layers['UVMap.001'].active = True
            if uvmap.name == "Secret Paint UV": custom_uv = uvmap.name
            if uvmap.active_render: active_render_UV = uvmap.name
        if not activeobj.data.surface_uv_map or activeobj.data.surface_uv_map not in [custom_uv,active_render_UV]:
            if custom_uv: activeobj.data.surface_uv_map = custom_uv
            elif active_render_UV: activeobj.data.surface_uv_map = active_render_UV
        if pickup_trace:
            pickup_trace.action(
                "context3sculptbrush.prepare_surface",
                prepare_surface_start,
                detail=f"active={activeobj.name if activeobj else 'None'}; uv_layers={len(activeobj.data.surface.data.uv_layers)}",
            )

        mode_set_sculpt_start = time.perf_counter()
        bpy.ops.object.mode_set(mode="SCULPT_CURVES")  # edit mode
        secret_paint_disable_sculpt_curves_cage(context)
        if pickup_trace:
            pickup_trace.action("context3sculptbrush.mode_set_sculpt_curves", mode_set_sculpt_start)

        density_asset_brush = None
        try:
            override_brush_settings = _secret_paint_pref("checkboxOverrideBrushes", True)
        except Exception:
            override_brush_settings = False
        if use_native_brush_setup:
            native_brush_setup_start = time.perf_counter()
            native_setup_size = None if keep_active_brush else 150
            try:
                secret_paint_ensure_sp_curves_brush_assets(
                    context,
                    activeobj,
                    configure=True,
                    override_settings=override_brush_settings,
                    size=native_setup_size,
                )
            except Exception:
                pass
            native_density_brush = None
            if not keep_active_brush:
                try:
                    native_density_brush = secret_paint_activate_native_curves_brush(
                        'DENSITY',
                        context,
                        activeobj,
                        configure=True,
                        override_settings=override_brush_settings,
                        size=native_setup_size,
                        defer=True,
                    )
                except Exception:
                    native_density_brush = None
                if native_density_brush is None:
                    print("FAILED SP NATIVE DENSITY BRUSH")
            if pickup_trace:
                pickup_trace.action(
                    "context3sculptbrush.native_brush_setup",
                    native_brush_setup_start,
                    detail=(
                        f"brush={native_density_brush.name if native_density_brush else 'None'}; "
                        f"keep_active_brush={keep_active_brush}"
                    ),
                )
                pickup_trace.action(
                    "context3sculptbrush.total",
                    context3sculptbrush_start,
                    detail=(
                        f"active={activeobj.name if activeobj else 'None'}; "
                        f"type={activeobj.type if activeobj else 'None'}; "
                        f"keep_active_brush={keep_active_brush}; brush_setup_mode=native"
                    ),
                )
            try:
                curves_sculpt = _secret_paint_curves_sculpt_settings(context)
                active_brush = getattr(curves_sculpt, "brush", None) if curves_sculpt is not None else None
                if secret_paint_is_curves_brush_type(active_brush, 'DENSITY'):
                    secret_paint_configure_density_brush(
                        active_brush,
                        context,
                        activeobj,
                        override_settings=override_brush_settings,
                        size=None,
                    )
            except Exception:
                pass
            return{'FINISHED'}

        if not keep_active_brush:
            set_density_tool_start = time.perf_counter()
            if not _secret_paint_set_density_workspace_tool(context):
                print("FAILED BRUSH DENSITYYYYY")
            if pickup_trace:
                pickup_trace.action("context3sculptbrush.set_density_tool", set_density_tool_start)
            # bpy.ops.wm.tool_set_by_id(name="builtin_brush.Density")

        # bpy.data.brushes["Density Curves"].curves_sculpt_brush_type =
        # bpy.data.brushes["Curves Snake Hook"].curves_sculpt_brush_type =
        # bpy.data.brushes["Grow / Shrink Curves"].curves_sculpt_brush_type =

        #CREATE THEN REFERENCE BRUSHES        #'DELETE' 'DENSITY'  'SNAKE_HOOK'   'GROW_SHRINK'  'ADD'
        brush_density = []
        brush_grow = []
        brush_add = []
        brush_delete = []
        brush_puff = []
        brush_comb = []
        scan_brushes_start = time.perf_counter()
        for brush in bpy.data.brushes:
            if secret_paint_is_curves_brush_type(brush, 'DENSITY'):
                brush_density.append(brush)
            elif secret_paint_is_curves_brush_type(brush, 'GROW_SHRINK'):
                brush_grow.append(brush)
            elif secret_paint_is_curves_brush_type(brush, 'ADD'):
                brush_add.append(brush)
            elif secret_paint_is_curves_brush_type(brush, 'DELETE'):
                brush_delete.append(brush)
            elif secret_paint_is_curves_brush_type(brush, 'PUFF'):
                brush_puff.append(brush)
            elif secret_paint_is_curves_brush_type(brush, 'COMB'):
                brush_comb.append(brush)
        if density_asset_brush is not None:
            brush_density = [density_asset_brush]
        if pickup_trace:
            pickup_trace.action(
                "context3sculptbrush.scan_brushes",
                scan_brushes_start,
                detail=(
                    f"brushes={len(bpy.data.brushes)}; density={len(brush_density)}; grow={len(brush_grow)}; "
                    f"add={len(brush_add)}; delete={len(brush_delete)}; puff={len(brush_puff)}; comb={len(brush_comb)}"
                ),
            )

        create_missing_brushes_start = time.perf_counter()
        if not brush_density:
            new_brush_density = bpy.data.brushes.new('Density Curvesss',mode="SCULPT_CURVES")
            secret_paint_set_curves_brush_type(new_brush_density, 'DENSITY')
            new_brush_density.size = 150
            brush_density.append(new_brush_density)
            # brush_density = [brush_density] #convert to a list if only one density brush was found
        if not brush_grow:
            new_brush_grow = bpy.data.brushes.new('Grow /Shrink Curves',mode="SCULPT_CURVES")
            secret_paint_set_curves_brush_type(new_brush_grow, 'GROW_SHRINK')
            new_brush_grow.size = 150
            brush_grow.append(new_brush_grow)
        if not brush_add:
            new_brush_add = bpy.data.brushes.new('Add Curves',mode="SCULPT_CURVES")
            secret_paint_set_curves_brush_type(new_brush_add, 'ADD')
            new_brush_add.size = 150
            brush_add.append(new_brush_add)
        if not brush_delete:
            new_brush_delete = bpy.data.brushes.new('Delete Curves',mode="SCULPT_CURVES")
            secret_paint_set_curves_brush_type(new_brush_delete, 'DELETE')
            new_brush_delete.size = 150
            brush_delete.append(new_brush_delete)
        if not brush_puff:
            new_brush_puff = bpy.data.brushes.new('Puff Curves',mode="SCULPT_CURVES")
            secret_paint_set_curves_brush_type(new_brush_puff, 'PUFF')
            new_brush_puff.size = 150
            brush_puff.append(new_brush_puff)
        if not brush_comb:
            new_brush_comb = bpy.data.brushes.new('Comb Curves',mode="SCULPT_CURVES")
            secret_paint_set_curves_brush_type(new_brush_comb, 'COMB')
            new_brush_comb.size = 150
            brush_comb.append(new_brush_comb)
        if pickup_trace:
            pickup_trace.action(
                "context3sculptbrush.create_missing_brushes",
                create_missing_brushes_start,
                detail=(
                    f"density={len(brush_density)}; grow={len(brush_grow)}; add={len(brush_add)}; "
                    f"delete={len(brush_delete)}; puff={len(brush_puff)}; comb={len(brush_comb)}"
                ),
            )



        #density brush always gets updated
        sync_density_start = time.perf_counter()
        density_minimum_distance = secret_paint_density_minimum_distance(context, activeobj)
        for bb in brush_density:
            # if bpy.context.object.modifiers[0] and bpy.context.object.modifiers[0]["Input_68"] > 0: bb.curves_sculpt_settings.minimum_distance =    (0.5/((bpy.context.object.modifiers[0]["Input_68"] ** 0.5) *bpy.context.object.modifiers[0]["Input_100"]))*1.5     #(0.314 / ((bpy.context.object.modifiers[0]["Input_68"] ** 0.5) * bpy.context.object.modifiers[0]["Input_100"] ** 0.5))     ## brush_density.curves_sculpt_settings.minimum_distance = 0.5/(bpy.context.object.modifiers["GeometryNodes"]["Input_68"]*bpy.context.object.modifiers["GeometryNodes"]["Input_100"])        # if bpy.context.object.modifiers[0]: brush_density.curves_sculpt_settings.minimum_distance =  bpy.context.object.modifiers[0]["Socket_11"]
            bb.curves_sculpt_settings.minimum_distance = density_minimum_distance
            if bpy.app.version_string >= "4.2.0":
                bb.curves_sculpt_settings.use_length_interpolate = True
                bb.curves_sculpt_settings.use_shape_interpolate = True
                bb.curves_sculpt_settings.use_point_count_interpolate = False
            elif bpy.app.version_string < "4.2.0":
                bb.curves_sculpt_settings.interpolate_length = True
                bb.curves_sculpt_settings.interpolate_shape = True
                bb.curves_sculpt_settings.interpolate_point_count = False
            bb.curves_sculpt_settings.curve_length = 0.32  #was 0.3
            bb.curves_sculpt_settings.points_per_curve = 2
        if pickup_trace:
            pickup_trace.action("context3sculptbrush.sync_density_brush", sync_density_start, detail=f"density_brushes={len(brush_density)}")

        #OVERRIDE ALL BRUSH SETTINGS
        if override_brush_settings:
            override_brush_settings_start = time.perf_counter()

            #DENSITY BRUSH
            for bb in brush_density:
                bb.curves_sculpt_settings.density_mode = 'AUTO'
                bb.strength = 1
                # bb.falloff_shape = 'SPHERE'
                if bpy.app.version_string >= "5.0.0": bb.curve_distance_falloff_preset = 'SMOOTHER'
                elif bpy.app.version_string < "5.0.0": bb.curve_preset = 'SMOOTHER'
                if bb.curves_sculpt_settings.density_add_attempts <= 100: bb.curves_sculpt_settings.density_add_attempts = 3000

            #growshrink brush
            for bb in brush_grow:
                bb.strength = 0.03
                if bpy.app.version_string >= "4.2.0":
                    bb.curves_sculpt_settings.use_uniform_scale = True
                elif bpy.app.version_string < "4.2.0":
                    bb.curves_sculpt_settings.scale_uniform = True

            #add brush
            for bb in brush_add:
                bb.curves_sculpt_settings.add_amount = 1
                # bb.falloff_shape = 'SPHERE'
                bb.use_frontface = True
                if bpy.app.version_string >= "4.2.0":
                    bb.curves_sculpt_settings.use_length_interpolate = True
                    bb.curves_sculpt_settings.use_shape_interpolate = True
                    bb.curves_sculpt_settings.use_point_count_interpolate = False
                elif bpy.app.version_string < "4.2.0":
                    bb.curves_sculpt_settings.interpolate_length = True
                    bb.curves_sculpt_settings.interpolate_shape = True
                    bb.curves_sculpt_settings.interpolate_point_count = False
                bb.curves_sculpt_settings.curve_length = 0.32  #was 0.3
                # brush_add.curves_sculpt_settings.curve_length = 1.32  #was 0.3
                bb.curves_sculpt_settings.points_per_curve = 2

            # #delete brush
            # for bb in brush_delete:
            #     bb.falloff_shape = 'PROJECTED'

            #puff brush
            for bb in brush_puff:
                bb.strength = 10
                # bb.falloff_shape = 'PROJECTED'

            #comb brush
            for bb in brush_comb:
                bb.strength = 0.1
                # bb.falloff_shape = 'PROJECTED'
            if pickup_trace:
                pickup_trace.action(
                    "context3sculptbrush.override_brush_settings",
                    override_brush_settings_start,
                detail=f"override=True; brushes={len(bpy.data.brushes)}",
                )



        if not keep_active_brush:
            activate_density_cursor_start = time.perf_counter()
            active_density_brush = brush_density[0] if brush_density else None
            _secret_paint_activate_density_brush_cursor(
                context,
                active_density_brush,
                activeobj,
                defer=True,
            )
            if pickup_trace:
                pickup_trace.action(
                    "context3sculptbrush.activate_density_cursor",
                    activate_density_cursor_start,
                    detail=f"brush={active_density_brush.name if active_density_brush else 'None'}",
                )





    elif activeobj.type=="CURVE":
        curve_edit_setup_start = time.perf_counter()
        bpy.ops.object.mode_set(mode="EDIT")  # edit mode
        for area in bpy.context.screen.areas:  # add hair tool
            if area.type == "VIEW_3D":
                override = bpy.context.copy()
                override["space_data"] = area.spaces[0]
                override["area"] = area
                # bpy.ops.wm.tool_set_by_id(override, name="builtin_brush.add")
                # bpy.ops.wm.tool_set_by_id(override, name="builtin_brush.density")
                # if bpy.context.object.modifiers["GeometryNodes"]:
                #     bpy.data.brushes["Density Curves"].curves_sculpt_settings.minimum_distance = bpy.context.object.modifiers["GeometryNodes"]["Input_68"]
                # else: bpy.data.brushes["Density Curves"].curves_sculpt_settings.minimum_distance = 0.1

                # bpy.ops.wm.tool_set_by_id(override, name="builtin.draw")
                bpy.ops.wm.tool_set_by_id(name="builtin.draw")

                if _secret_paint_pref("checkboxOverrideBrushes", True):
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
        if pickup_trace:
            pickup_trace.action("context3sculptbrush.curve_edit_setup", curve_edit_setup_start, detail=f"active={activeobj.name if activeobj else 'None'}")


            # bpy.data.brushes["Add Curves"].add_amount = 2
    if pickup_trace:
        pickup_trace.action(
            "context3sculptbrush.total",
            context3sculptbrush_start,
            detail=f"active={activeobj.name if activeobj else 'None'}; type={activeobj.type if activeobj else 'None'}; keep_active_brush={keep_active_brush}",
        )
    return{'FINISHED'}
def curve_draw_tool(context,**kwargs):
    if "dont_set_drawing_tool" in kwargs:dont_set_drawing_tool = kwargs.get("dont_set_drawing_tool")
    else:dont_set_drawing_tool = False

    bpy.ops.object.mode_set(mode="EDIT")  # edit mode
    # for area in bpy.context.screen.areas:  # draw tool
    #     if area.type == "VIEW_3D":
    #         override = bpy.context.copy()
    #         override["space_data"] = area.spaces[0]
    #         override["area"] = area
    #         if dont_set_drawing_tool: bpy.ops.wm.tool_set_by_id(override, name="builtin.select_box")
    #         else: bpy.ops.wm.tool_set_by_id(override, name="builtin.draw")
    if not dont_set_drawing_tool:
        bpy.ops.wm.tool_set_by_id(name="builtin.draw")

    # return{'FINISHED'}
def recurLayerCollection(layerColl, collName):  #paint. conversion
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
# def orenpaint_viewport_mask_function(self,context,objselection=bpy.context.selected_objects,activeobj=bpy.context.active_object):  #DOESN'T WORK???
def secretpaint_viewport_mask_function(*args,**kwargs): #objselection,activeobj,calledfrom_button=False, force_new_maskObj=False

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

    # print(activeobj)
    # print(objselection)

    #when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object
    if called_for_entire_biome == False:  #ignore if called for the entire biome, because the active obj is improbable to match the randomly picked hair_in_bgroup[0]
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]



    # activeobj_BoundingBox_State = activeobj.display_type
    N_Of_Selected = len(objselection)  # bpy.context.selected_objects
    # ActiveMode = bpy.context.object.mode
    selobjs_without_active = []
    objs_with_orencurve = []
    selobjs_without_active_with_orencurve = []
    temp_variable_for_mask_detection1 = []
    temp_variable_for_mask_detection2 = []
    mask_found = []
    all_found_parents = []
    for oobjj in objselection:  # bpy.context.selected_objects
        if oobjj != activeobj:
            selobjs_without_active.append(oobjj)
        if oobjj.name.startswith("Secret Paint Viewport Mask"): mask_found = oobjj
        if oobjj.modifiers:
            for modifier in oobjj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint":  # modifier.name == "GeometryNodes"
                    if oobjj not in objs_with_orencurve: objs_with_orencurve.append(oobjj)
                    if oobjj != activeobj and oobjj not in selobjs_without_active_with_orencurve: selobjs_without_active_with_orencurve.append(
                        oobjj)
                    if oobjj.parent and oobjj.parent not in all_found_parents: all_found_parents.append(
                        oobjj.parent)
                    temp_variable_for_mask_detection1.append(modifier["Input_98"])  # checkbox for mask
                    temp_variable_for_mask_detection2.append(modifier["Input_97"])


    all_hair_share_same_mask_settings = False
    if all_variables_are_equal(temp_variable_for_mask_detection1) and all_variables_are_equal(
        temp_variable_for_mask_detection2): all_hair_share_same_mask_settings = True

    biome_detected = False
    if len(all_found_parents) == 1: biome_detected = True

    all_sel_are_orencurves = False
    if N_Of_Selected == len(objs_with_orencurve): all_sel_are_orencurves = True

    ######################   v

    # if mask and biome are selected, share mask:
    if mask_found:
        for scattered_hair in objs_with_orencurve:
            scattered_hair.modifiers[0]["Input_98"] = True
            scattered_hair.modifiers[0]["Input_97"] = mask_found

            scattered_hair.hide_viewport = True  # refresh
            scattered_hair.hide_viewport = False  # refresh
            scattered_hair.location = scattered_hair.location  # best way to update the scene ;update scene

    # toggle or share settings:
    else:
        checkboxstatus = activeobj.modifiers[0]["Input_98"]
        maskstatus = activeobj.modifiers[0]["Input_97"]
        # print(checkboxstatus)
        # print(maskstatus)
        # return {'FINISHED'}



        # if all selected hair share same mask settings:
        if all_hair_share_same_mask_settings:
            #TOGGLE MASK SETTINGS IF THEY'RE ALL THE SAME
            maskobj = None #[]
            if maskstatus == None:
                Coll_of_Active = []  # CREATE MASK IN COLLECTION OF ACTIVE
                original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
                ucol = activeobj.users_collection
                for i in ucol:
                    layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                    # bpy.context.view_layer.active_layer_collection = Coll_of_Active

                # ONLY USE ONE MASK FOR THE SAME SCENE
                for ob in bpy.context.scene.objects:
                    if ob.name.startswith("Secret Paint Viewport Mask"):
                        maskobj = ob
                        break
                # CREATE THE MASAK IF NOT FOUND
                if not maskobj or force_new_maskObj:
                    if bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")


                    mesh = bpy.data.meshes.new("Secret Paint Viewport Mask")  # Create new mesh
                    maskobj = bpy.data.objects.new("Secret Paint Viewport Mask", mesh)  # Create new object with the mesh
                    masksize=5
                    half_x = masksize / 2  # Half of the dimension for symmetry around the origin
                    verts = [(-half_x, -half_x, -half_x), (half_x, -half_x, -half_x), (half_x, half_x, -half_x), (-half_x, half_x, -half_x), (-half_x, -half_x, half_x), (half_x, -half_x, half_x), (half_x, half_x, half_x), (-half_x, half_x, half_x)]  # Cube vertices scaled by x
                    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 3, 7, 4), (1, 2, 6, 5)]  # Faces that define the cube
                    mesh.from_pydata(verts, [], faces)  # Use verts and faces to generate geometry    # mesh.update()  # Update the mesh with new geometry
                    maskobj.location = activeobj.location
                    if Coll_of_Active.name == "Scene Collection": bpy.context.scene.collection.objects.link(maskobj)  # LINK TO MAIN SCENE COLLECTION (the command for a common collection needs to be different for some reason)
                    else: bpy.data.collections[Coll_of_Active.name].objects.link(maskobj)  # LINK TO COLLECTION

                    if importpainting_multiple_assets ==False:
                        for obbb in bpy.context.selected_objects: obbb.select_set(False)
                        maskobj.select_set(True)
                        bpy.context.view_layer.objects.active = maskobj

                    # bpy.ops.mesh.primitive_cube_add(size=5, enter_editmode=False, align='WORLD',location=activeobj.location)
                    # maskobj = bpy.context.active_object
                    # maskobj.name = "Secret Paint Viewport Mask"

                    # bpy.ops.mesh.select_all(action='DESELECT')
                    # mesh = bmesh.from_edit_mesh(maskobj.data)
                    # for vertex in mesh.verts:
                    #     if vertex.co.z > 2:
                    #         vertex.select = True
                    # bpy.ops.mesh.delete(type='VERT')
                    # # bpy.ops.mesh.select_all(action='SELECT')
                    # # bpy.ops.mesh.subdivide(number_cuts=1, smoothness=1.0)
                    # bpy.ops.object.mode_set(mode='OBJECT')

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
                    scattered_hair.modifiers[0]["Input_98"] = False  # checkbox
                    scattered_hair.modifiers[0]["Input_97"] = None  # mask

                elif checkboxstatus == False:
                    scattered_hair.modifiers[0]["Input_98"] = True  # checkbox

                    if maskstatus:
                        scattered_hair.modifiers[0]["Input_97"] = maskstatus
                    elif maskstatus == None:
                        scattered_hair.modifiers[0]["Input_97"] = maskobj

                scattered_hair.hide_viewport = True  # refresh
                scattered_hair.hide_viewport = False  # refresh
                scattered_hair.location = scattered_hair.location  # best way to update the scene ;update scene

        # else different settings: copy active hair's mask settings, wether empty or full
        else:
            for scattered_hair in objs_with_orencurve:
                scattered_hair.modifiers[0]["Input_98"] = checkboxstatus
                scattered_hair.modifiers[0]["Input_97"] = maskstatus
                scattered_hair.hide_viewport = True  # refresh
                scattered_hair.hide_viewport = False  # refresh
                scattered_hair.location = scattered_hair.location  # best way to update the scene ;update scene


    #DELETE UNUSED MASKS     #RESELECT SYSTEM AFTER DELETING MASK
    all_used_masks_in_blendfile=[]
    all_masks_in_blendfile=[]
    for obj in bpy.data.objects:
        if obj.name.startswith("Secret Paint Viewport Mask"): all_masks_in_blendfile.append(obj)
        if obj.modifiers:
            for modifier in obj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint":  # modifier.name == "GeometryNodes"
                    if modifier["Input_97"] and modifier["Input_97"] not in all_used_masks_in_blendfile: all_used_masks_in_blendfile.append(modifier["Input_97"])
    for mask in all_masks_in_blendfile:
        if mask not in all_used_masks_in_blendfile:
            flag_make_row_object_active_after_deleting_mask = True if mask == bpy.context.active_object else False
            bpy.data.objects.remove(mask, do_unlink=True)
            if flag_make_row_object_active_after_deleting_mask: bpy.context.view_layer.objects.active = activeobj



    #
    # elif all_sel_are_orencurves:
    #     Coll_of_Active = []   #CREATE MASK IN COLLECTION OF ACTIVE
    #     original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
    #     ucol = activeobj.users_collection
    #     for i in ucol:
    #         layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
    #         Coll_of_Active = recurLayerCollection(layer_collection, i.name)
    #         bpy.context.view_layer.active_layer_collection = Coll_of_Active
    #     bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=True, align='WORLD',location=activeobj.location, scale=(5, 5, 5))
    #     bpy.context.view_layer.active_layer_collection = original_collection
    #     maskobj = bpy.context.active_object
    #     maskobj.name = "Orenpaint Viewport Mask"
    #
    #     bpy.ops.mesh.select_all(action='DESELECT')
    #     mesh = bmesh.from_edit_mesh(maskobj.data)
    #     for vertex in mesh.verts:
    #         if vertex.co.z > 2:
    #             vertex.select = True
    #     bpy.ops.mesh.delete(type='VERT')
    #     # bpy.ops.mesh.select_all(action='SELECT')
    #     # bpy.ops.mesh.subdivide(number_cuts=1, smoothness=1.0)
    #     bpy.ops.object.mode_set(mode='OBJECT')
    #
    #     maskobj.visible_camera = False
    #     maskobj.visible_diffuse = False
    #     maskobj.visible_glossy = False
    #     maskobj.visible_transmission = False
    #     maskobj.visible_volume_scatter = False
    #     maskobj.visible_shadow = False
    #     maskobj.display_type = 'WIRE'
    #
    #     for scattered_hair in objs_with_orencurve:
    #         scattered_hair.modifiers["GeometryNodes"]["Input_97"] = maskobj
    #         scattered_hair.modifiers["GeometryNodes"]["Input_98"] = True
    #
    #         scattered_hair.hide_viewport=True #refresh
    #         scattered_hair.hide_viewport=False #refresh
    #         scattered_hair.location = scattered_hair.location  # best way to update the scene ;update scene
    return {'FINISHED'}


def _secret_paint_viewport_mask_click_creates_temp_mask(context, activeobj):
    if activeobj is None or not getattr(activeobj, "modifiers", None):
        return False

    objselection = list(getattr(context, "selected_objects", []))
    if activeobj not in objselection:
        objselection.append(activeobj)
    try:
        if activeobj != context.active_object and activeobj not in context.selected_objects:
            objselection = [activeobj]
    except Exception:
        objselection = [activeobj]

    for obj in objselection:
        if getattr(obj, "name", "").startswith("Secret Paint Viewport Mask"):
            return False

    objs_with_orencurve = []
    mask_enabled_values = []
    mask_object_values = []
    for obj in objselection:
        if not getattr(obj, "modifiers", None):
            continue
        for modifier in obj.modifiers:
            node_group = getattr(modifier, "node_group", None)
            if modifier.type == 'NODES' and node_group and node_group.name == "Secret Paint":
                objs_with_orencurve.append(obj)
                mask_enabled_values.append(modifier["Input_98"])
                mask_object_values.append(modifier["Input_97"])

    if not objs_with_orencurve:
        return False
    if not (all_variables_are_equal(mask_enabled_values) and all_variables_are_equal(mask_object_values)):
        return False

    try:
        maskstatus = activeobj.modifiers[0]["Input_97"]
    except Exception:
        return False
    if maskstatus is not None:
        return False

    for obj in bpy.context.scene.objects:
        if obj.name.startswith("Secret Paint Viewport Mask"):
            return False
    return True


class secretpaint_viewport_mask(bpy.types.Operator):
    """Mask vast landscapes for viewport performance; Shift+Click to create a new mask; Alt+Click to select the mask object"""
    bl_idname = "secret.secretpaint_viewport_mask"
    bl_label = "Temporary Viewport Mask"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    def invoke(self, context, event):

        obbb= bpy.data.objects.get(self.object_name)
        if event.alt or event.shift:
            _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.secretpaint_viewport_mask")

        if event.alt: #select mask object
            for x in bpy.context.selected_objects: x.select_set(False) #objselection
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
        else:
            if _secret_paint_viewport_mask_click_creates_temp_mask(context, obbb):
                _secret_paint_panel_exit_paint_mode(context)
            secretpaint_viewport_mask_function(self, context,activeobj=obbb)
        self.object_name = ("")
        return {'FINISHED'}
    # def execute(self, context):
    #     orenpaint_viewport_mask_function(self, context,activeobj=bpy.data.objects.get(self.object_name))
    #     return {'FINISHED'}
def selcollectionofactive(layerColl, collName):   # make active the parent collection of active object
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
    # SELECT BIOMES WITH SAME BRUSH
    for obj in bpy.context.scene.objects:
        if obj.type == "CURVES":
            if obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and obj.modifiers[0]["Input_2"] == brushobj and obj.modifiers[0]["Input_9"] == brushcoll:
                        bpy.data.objects[obj.name].select_set(True)
                        # print(obj.name)
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
    # bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": True})

    dupliobj = activeobj.copy()
    bpy.context.scene.collection.objects.link(dupliobj)

    while str(dupliobj.location) in allCoordinates:
        dupliobj.location[2] = dupliobj.location[2] + (((dupliobj.dimensions[2]) / 2) * 2.15)

    return dupliobj









#EXPOSED BUTTONS

# def orenpaint_base_function(*args,**kwargs):
#     if "surfaceOBJ" in kwargs:surfaceOBJ = kwargs.get("surfaceOBJ")
#     else:surfaceOBJ = bpy.context.active_object
#     if surfaceOBJ == None: surfaceOBJ = bpy.context.active_object
#     if "objselection" in kwargs:objselection = kwargs.get("objselection")
#     else:objselection = bpy.context.selected_objects
#     if surfaceOBJ not in objselection: objselection.append(surfaceOBJ)
#
#     bpy.context.view_layer.active_layer_collection = Coll_of_Active  # SELECT COLLECTION
#     bpy.ops.object.curves_empty_hair_add(align='WORLD', location=bpy.context.scene.cursor.location, scale=(1, 1, 1))
#     hairCurves = bpy.context.active_object
#
#     bpy.ops.object.modifier_remove(modifier="Surface Deform")
#     contextorencurveappend(context)
#     hairCurves.modifiers["GeometryNodes"]["Input_2"] = bpy.data.objects[brushOBJ.name]  # ["GeometryNodes"] #objinstance
#     # bpy.context.object.modifiers["GeometryNodes"]["Input_9"] = None  #reset collection
#     hairCurves.modifiers["GeometryNodes"][
#         "Input_16"] = 5  # MODE scatter  (ignore radius, different scale and rot nodes)
#     hairCurves.modifiers["GeometryNodes"]["Input_6"][2] = 20  # random z rot
#     hairCurves.modifiers["GeometryNodes"]["Input_15"] = 0.25  # random scale
#     hairCurves.modifiers["GeometryNodes"]["Input_62"] = 0.5  # world noise scale
#     # bpy.context.object.modifiers["GeometryNodes"]["Input_52"] = 1 # show original curve
#
#     if brushOBJ.type != "MESH":
#         density_large = 1.0  # can't calculate the density from an empty object
#     else:
#         if brushOBJ.dimensions[0] > brushOBJ.dimensions[1]:
#             density_large = 0.5 / (brushOBJ.dimensions[0] / 2 / brushOBJ.scale[0])
#         else:
#             density_large = 0.5 / (brushOBJ.dimensions[1] / 2 / brushOBJ.scale[1])
#     hairCurves.modifiers["GeometryNodes"]["Input_68"] = density_large  # DENSITY SCATTER
#     hairCurves.modifiers["GeometryNodes"]["Input_100"] = surfaceOBJ.scale[0]  # OBJ SCALE COMPENSATION
#     hairCurves.modifiers["GeometryNodes"]["Input_73"] = surfaceOBJ  # SURFACE DENSITY SCATTER
#
#     # LINK MATERIALS
#     for material_slot in brushOBJ.material_slots:
#         if material_slot.material and material_slot.material.name not in hairCurves.data.materials:
#             hairCurves.data.materials.append(material_slot.material)
#
#     bpy.data.objects[hairCurves.name].select_set(False)  # deselect in order to see better what it's being painted
#     bpy.context.view_layer.active_layer_collection = original_collection
#     context3sculptbrush(context)
#
#     return {'FINISHED'}
#     return {'FINISHED'}
#     return {'FINISHED'}
# def orenpaint_function(self,context, event):
def secretpaint_cleanup_empty_systems(self,context):
    # cleanup empty hair systems in scene, for misclicks
    for obj in bpy.context.scene.objects:
        if obj.type == "CURVES" and obj.modifiers and obj != bpy.context.active_object and obj not in bpy.context.selected_objects:
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and (sum(len(spline.points) for spline in obj.data.curves)) == 0 and obj.modifiers[0]["Input_99"] == False and obj.modifiers[0]["Input_69"] == False:
                    bpy.data.objects.remove(obj, do_unlink=True)
                #CLEANUP VGROUPS AS WELL??
def secretpaint_create_curve(self,context,**kwargs):
    if "targetOBJ" in kwargs:targetOBJ = kwargs.get("targetOBJ")
    else:targetOBJ = bpy.context.active_object
    if targetOBJ.type=="CURVES": targetOBJsurface= targetOBJ.parent #targetOBJ.data.surface
    else: targetOBJsurface=targetOBJ

    if "brushOBJ" in kwargs:
        brushOBJ= kwargs.get("brushOBJ")
        if not isinstance(brushOBJ, (list, tuple)): brushOBJ=[brushOBJ]  #CONVERT TO LIST only if it's not, otherwise it creates a list inside a list
    else: brushOBJ=None

    hair_to_copyModifs_from = targetOBJ if targetOBJ.type == "CURVES" else brushOBJ[0]


    targetCollection = kwargs.get("targetCollection") if "targetCollection" in kwargs else bpy.context.collection
    transfer_modifier = kwargs.get("transfer_modifier") if "transfer_modifier" in kwargs else False
    # if "append_orenpaint" in kwargs:append_orenpaint = kwargs.get("append_orenpaint")
    # else:append_orenpaint = False
    ################################################


    #CREATE NEW CURVE
    hairCurves = bpy.data.objects.new("Secret Paint", bpy.data.hair_curves.new("Secret Paint"))
    if targetCollection.name =="Scene Collection": bpy.context.scene.collection.objects.link(hairCurves) #LINK TO MAIN SCENE COLLECTION (the command for a common collection needs to be different for some reason)
    else: bpy.data.collections[targetCollection.name].objects.link(hairCurves) #LINK TO COLLECTION
    if transfer_modifier:
        # print("UPDAAAAAAAAAAAT secretpaint_create_curve")
        secretpaint_update_modifier_f(context,upadte_provenance="def secretpaint_create_curve(self,context,**kwargs)") #no need to append the node tree, just update and copy the existing modifier
    else: contextorencurveappend(context,activeobj=hairCurves)
    # if append_orenpaint: contextorencurveappend(context,activeobj=hairCurves)
    # else: orenpaint_update_modifier_f(context)
    hairCurves.data.surface = targetOBJsurface

    #USE CUSTOM UV IF FOUND, ELIF THE RENDER ACTIVE UV, ELSE CREATE IT
    active_render_UV = None
    custom_uv = None
    for uvmap in targetOBJsurface.data.uv_layers:    #bpy.context.object.data.uv_layers['UVMap.001'].active = True
        if uvmap.name == "Secret Paint UV":custom_uv = uvmap.name
        if uvmap.active_render: active_render_UV = uvmap.name
    if custom_uv: hairCurves.data.surface_uv_map = custom_uv
    elif active_render_UV: hairCurves.data.surface_uv_map = active_render_UV
    # else: hairCurves.data.surface_uv_map = secret_paint_new_uvs(self, context, activeobj=targetOBJsurface).name


    hairCurves.rotation_euler = targetOBJsurface.matrix_world.to_euler('XYZ')  # rotation_euler
    hairCurves.scale = targetOBJsurface.scale
    hairCurves.location = targetOBJsurface.matrix_world.to_translation()  # location
    hairCurves.parent = targetOBJsurface
    hairCurves.matrix_parent_inverse = targetOBJsurface.matrix_world.inverted()
    hairCurves.display_type = hair_to_copyModifs_from.display_type #LINK BOUNDING BOX STATE  #brushOBJ[0]

    # LINK MATERIALS
    if brushOBJ:
        material_cache = {}
        for brushh in brushOBJ:
            for material in _secret_paint_collect_safe_materials_from_object(brushh, material_cache):
                _secret_paint_append_material_once(hairCurves.data.materials, material)



    #LINK MODIFIERS
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
            # try:
                for key, value in mod.items():
                    try:
                        mod_copy[key] = value
                    except: print("failllllllllll", value)
            # except: print("failllllllllll")
    hairCurves.modifiers[0]["Input_99"] = True    #ALWAYS TURN OFF SYSTEM, CALCULATE IF MASK IS NEEDED, THEN TURN IT ON FOR EACH INDIVIDUAL SCATTER SCENARIO
    hairCurves.modifiers[0]["Input_71"] = float(random.choice(range(0, 10)))  # random noise W
    hairCurves.modifiers[0]["Input_73"] = targetOBJsurface #surface
    hairCurves.modifiers[0]["Input_100"] = abs(max(targetOBJsurface.scale))    # OBJ SCALE COMPENSATION calculated from max dimension
    # hairCurves.modifiers[0]["Input_99"] = False    #ALWAYS TURN ON SYSTEM
    # if bpy.context.preferences.addons[__package__].preferences.checkboxFasterViewportMask: hairCurves.modifiers[0]["Socket_10"] = True
    if targetOBJsurface.modifiers:   #if armature modifier detected, turn on deform on surface
        for mod in targetOBJsurface.modifiers:
            if mod.type in ["ARMATURE","CAST","CURVE","DISPLACE","HOOK","LAPLACIANDEFORM","LATTICE","MESH_DEFORM","SHRINKWRAP","SIMPLE_DEFORM","SMOOTH","CORRECTIVE_SMOOTH","LAPLACIANSMOOTH","SURFACE_DEFORM","WARP","WAVE",]:
                hairCurves.modifiers[0]["Input_63"] = True #DEFORM ON SURFACE
                targetOBJsurface.add_rest_position_attribute = True

    #RECALCULATE PROCEDURAL DENSITY IF BRUSHOBJ IS A MESH, if brushobj is a paint system or empty, doesn't need to recalculate
    smallest_obj = brushOBJ[0]   #FIND SMALLES OBJECT WHEN PAINTING WITH A COLLECTION, when having similar flowers variations it's better to find the smallest one and calculate the density based on that rather than having spaces with the biggest one
    for obje in brushOBJ:
        if obje.type == "MESH":

            #Check if it's an ASSEMBLY: then use its parent to calculate dimensions (geonode assemblies have 0 dimensions)
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
    if max(smallest_obj.dimensions)>0:  #assemblies or empties fail   #if smallest_obj.type == "MESH":
        if smallest_obj.dimensions[0]/smallest_obj.scale[0] > smallest_obj.dimensions[1]/smallest_obj.scale[1]: dimensions_of_smallest_axis = 1 / ((smallest_obj.dimensions[1]/smallest_obj.scale[1]) **2) # / smallest_obj.scale[0])
        else: dimensions_of_smallest_axis = 1 / ((smallest_obj.dimensions[0]/smallest_obj.scale[0]) **2) #smallest_obj.scale[1])
        if dimensions_of_smallest_axis < 10000: #if it's more than 10000 it's because it's an infinitely thin plane, so ignore it and leave modifier default density value of 0.2
            density_value = secret_paint_apply_object_size_density_multiplier(dimensions_of_smallest_axis, context)
            hairCurves.modifiers[0]["Input_68"] = density_value
            hairCurves.modifiers[0]["Socket_11"] =     (0.5/((density_value ** 0.5) *hairCurves.modifiers[0]["Input_100"]))*2

        # else:
        #     if smallest_obj.dimensions[0] == (0,0,0) and smallest_obj.scale[0] > (0,0,0): hairCurves.modifiers[0]["Input_68"] = 1 / ((smallest_obj.dimensions[0]/smallest_obj.scale[0]) **2) #smallest_obj.scale[1])
        #     else: hairCurves.modifiers[0]["Input_68"] = 5




    return hairCurves
    # return {'FINISHED'}

def auto_assembly_print(*parts):
    print("Secret Paint Auto Assembly:", *parts)

def secret_assembly_parent_input(modif):
    if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
        node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
        for input in node_group_inputs_temp:
            if getattr(input, "socket_type", None) == "NodeSocketObject" and input.name == "Parent":
                return input
    return None

def secret_assembly_parent_object(obj):
    if obj and obj.type == "MESH" and obj.modifiers:
        for modif in obj.modifiers:
            parent_input = secret_assembly_parent_input(modif)
            if parent_input:
                return modif[parent_input.identifier]
    return None

def find_secret_assembly_for_parent(parent_obj):
    if parent_obj == None:
        return None
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.modifiers:
            for modif in obj.modifiers:
                parent_input = secret_assembly_parent_input(modif)
                if parent_input and modif[parent_input.identifier] == parent_obj:
                    return obj
    return None

def get_secret_assembly_hierarchy_height(parent_obj):
    if parent_obj == None:
        return 0.0

    hierarchy = [parent_obj]
    stack = [parent_obj]
    while stack:
        obj = stack.pop()
        for child in obj.children:
            if child not in hierarchy:
                hierarchy.append(child)
                stack.append(child)

    min_z = None
    max_z = None
    for obj in hierarchy:
        try:
            corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        except:
            corners = [obj.matrix_world.to_translation()]
        for corner in corners:
            if min_z == None or corner.z < min_z:
                min_z = corner.z
            if max_z == None or corner.z > max_z:
                max_z = corner.z

    if min_z == None or max_z == None:
        return max(parent_obj.dimensions[2], 0.0)
    return max(max_z - min_z, parent_obj.dimensions[2], 0.0)

def move_secret_assembly_upwards(assembly_obj, parent_obj):
    if assembly_obj == None or parent_obj == None:
        return

    z_offset = get_secret_assembly_hierarchy_height(parent_obj) * 1.075
    if z_offset <= 0:
        z_offset = 1.0

    allCoordinates = []
    for obj in bpy.context.scene.objects:
        if obj != assembly_obj:
            allCoordinates.append(str(obj.location))

    assembly_obj.location[2] += z_offset
    while str(assembly_obj.location) in allCoordinates:
        assembly_obj.location[2] += z_offset

def secretpaint_prepare_q_brush_object(self, context, brushobj, *, allow_auto_assembly=True):
    if brushobj == None or blender_version < "4.2.0":
        return brushobj
    if (
        not allow_auto_assembly
        or _secretpaint_consume_skip_auto_assembly_on_q(brushobj)
        or _secret_paint_pref("checkboxAutoAssemblyOnQ", False) == False
    ):
        return brushobj

    assembly_parent = secret_assembly_parent_object(brushobj)
    if assembly_parent == None and not brushobj.children:
        return brushobj
    if assembly_parent == None:
        assembly_parent = brushobj

    auto_assembly_print("prepare", "brush=", brushobj.name, "parent=", assembly_parent.name, "children=", len(assembly_parent.children))
    assembly_obj, final_assemblies_to_process, created_new_assembly, updated_existing_assembly = build_secret_assembly_direct(self, context, assembly_parent, skip_select_new_assembly=True)

    if assembly_obj:
        if created_new_assembly:
            move_secret_assembly_upwards(assembly_obj, assembly_parent)
        auto_assembly_print(
            "ready",
            "parent=", assembly_parent.name,
            "assembly=", assembly_obj.name,
            "created=", created_new_assembly,
            "updated=", updated_existing_assembly,
            "process=",
            [obj.name for obj in final_assemblies_to_process],
        )
        return assembly_obj

    if assembly_parent.children:
        auto_assembly_print("failed", "parent=", assembly_parent.name, "process=", [obj.name for obj in final_assemblies_to_process])
        self.report({'ERROR'}, "Auto Assembly On Q could not create the assembly")
        return None

    return brushobj

def secretpaint_function(self,*args,**kwargs):  #paint. conversion
    print("###########-----  secretpaint_function(self,*args,**kwargs  ------############")
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
    defer_enter_paint_mode = kwargs.get("defer_enter_paint_mode", False)
    allow_auto_assembly_on_q = kwargs.get("allow_auto_assembly_on_q", True)

    if activeobj == None: return {'FINISHED'}

    # activeobj = bpy.context.active_object
    activeobj_BoundingBox_State = activeobj.display_type
    # objselection = bpy.context.selected_objects
    N_Of_Selected = len(objselection)  #len(bpy.context.selected_objects)
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
    for oobjj in objselection:    #bpy.context.selected_objects:
        if oobjj.type=="MESH": all_meshes.append(oobjj)
        if oobjj != activeobj:
            selobjs_without_active.append(oobjj)
        if oobjj.modifiers:
            for modifier in oobjj.modifiers:
                # if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"): #modifier.node_group.name == "orenpaint":
                if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" \
                or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modifier.node_group.name) and ".001" <= modifier.node_group.name[-4:] <= ".999" : #modifier.node_group.name == "orenpaint":
                    if oobjj not in objs_with_orencurve: objs_with_orencurve.append(oobjj)
                    if oobjj != activeobj and oobjj not in selobjs_without_active_with_orencurve: selobjs_without_active_with_orencurve.append(oobjj)
                    if oobjj.type == "CURVES" and oobjj.parent and oobjj.parent not in all_found_parents: all_found_parents.append(oobjj.parent) #oobjj.data.surface CANT WORK BECAUSE OF SHIFT+D LINKED DUPLICATE MESHES
                    if oobjj != activeobj and oobjj.type == "CURVES" and oobjj.parent and oobjj.parent not in all_found_parents_without_activeobj: all_found_parents_without_activeobj.append(oobjj.parent)
                    if modifier["Input_83_attribute_name"]:
                        all_hair_with_Vgroup.append(oobjj)
                        if modifier["Input_83_attribute_name"] not in all_Vgroups: all_Vgroups.append(modifier["Input_83_attribute_name"])

    for mesh in all_meshes:
        if mesh not in all_found_parents: all_meshes_that_are_not_parents.append(mesh)

    biome_detected = False
    if len(all_found_parents)==1: biome_detected=True #measured without activeobj

    all_sel_are_orencurves = False
    if N_Of_Selected == len(objs_with_orencurve): all_sel_are_orencurves = True

    # print(len(selobjs_without_active_with_orencurve))
    # print(len(selobjs_without_active))

    # get second selected object
    selobj=[]
    selobj_BoundingBox_State=[]
    if N_Of_Selected >=2:
        for obj in objselection: #bpy.context.selected_objects:
            if obj != activeobj:
                selobj = obj
                break
                selobj_BoundingBox_State = selobj.display_type

    # FIND COLLECTION OF ACTIVE
    Coll_of_Active=[]
    original_collection = bpy.context.view_layer.active_layer_collection   #bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
    # ucol = activeobj.users_collection
    # for i in ucol:
    for i in activeobj.users_collection:
        layer_collection = bpy.context.view_layer.layer_collection   #bpy.context.scene.collection
        Coll_of_Active = recurLayerCollection(layer_collection, i.name)

    # FIND COLLECTION OF ONE OF SELECTED
    collection_of_one_of_selected=[]
    if N_Of_Selected >=3:
        # ucol = selobj.users_collection
        # ucol = selobjs_without_active[0].users_collection
        # for i in ucol:
        for i in selobj.users_collection:
        # for i in selobjs_without_active[0].users_collection:
            layer_collection = bpy.context.view_layer.layer_collection #bpy.context.scene.collection
            collection_of_one_of_selected = recurLayerCollection(layer_collection, i.name)

    # # find a geohair obj when many sel objects  UNUSED FOR NOW
    # surface_for_hair = []
    # if N_Of_Selected >= 3:
    #     for obj in bpy.context.selected_objects:
    #         if obj.type == "CURVES" and obj.modifiers:
    #             for modif in obj.modifiers:
    #                 if modif.type == "NODES":
    #                     try:
    #                         if obj.modifiers[modif.name]["Input_16"] == 5:
    #                             surface_for_hair = obj
    #                     except: pass


    ######################################################### v  ######################################################### v






    if ActiveMode == "OBJECT" and N_Of_Selected == 2 and selobj and selobj.type in ["MESH","EMPTY","CURVE"]:
        selobj = secretpaint_prepare_q_brush_object(self, context, selobj, allow_auto_assembly=allow_auto_assembly_on_q)
        if selobj == None:
            auto_assembly_print("abort q", "active=", activeobj.name if activeobj else None)
            return {'FINISHED'}

    #scatter sel obj on active surface
    if ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "MESH" and selobj.type in ["MESH","EMPTY","CURVE"]:
        print("scatter sel obj on active surface")
        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj) #SLOW FOR HIGHPOLY OBJECTS
        hairCurves = secretpaint_create_curve(self,context,targetOBJ=activeobj,targetCollection=Coll_of_Active, brushOBJ=selobj, transfer_modifier=False)
        if hairCurves is None:
            return {'FINISHED'}

        # contextorencurveappend(context,activeobj=hairCurves)
        hairCurves.modifiers[0]["Input_2"] = bpy.data.objects[selobj.name]  #["GeometryNodes"] #objinstance
        # bpy.context.object.modifiers["GeometryNodes"]["Input_9"] = None  #reset collection
        hairCurves.modifiers[0]["Input_16"] = 5 #MODE scatter  (ignore radius, different scale and rot nodes)
        hairCurves.modifiers[0]["Input_6"][2] = 20  # random z rot

        # print("YYYYYYYYY",hairCurves.modifiers["GeometryNodes"]["Input_15"])
        percentage_value = 0.75  # This represents 75%
        # percentage_string = f"{percentage_value}%"
        # percentage_string = f"{percentage_value * 100:.2f}%"
        # percentage_string = "{:.2%}".format(percentage_value)
        # hairCurves.modifiers["GeometryNodes"]["Input_15"] = percentage_string # random scale

        hairCurves.modifiers[0]["Input_15"] = 0.25 # random scale
        hairCurves.modifiers[0]["Input_15"] = 0.25 # random scale
        hairCurves.modifiers[0]["Input_82"] = 1.04
        hairCurves.modifiers[0]["Input_62"] = 0.5 #scale random world
        # hairCurves.modifiers[0]["Input_60"] =   0.3*   (0.5/       ((0.5/((hairCurves.modifiers[0]["Input_68"] ** 0.5) *hairCurves.modifiers[0]["Input_100"]))*2)  )     #world noise scale
        hairCurves.modifiers[0]["Input_60"] =   0.15*   ((hairCurves.modifiers[0]["Input_68"]    **0.5))     #world noise scale

        # bpy.context.object.modifiers["GeometryNodes"]["Input_52"] = 1 # show original curve
        # if selobj.type!="MESH": density_large = 1.0 #can't calculate the density from an empty object
        # else:
        #     if selobj.dimensions[0] > selobj.dimensions[1]: density_large= 0.5/( selobj.dimensions[0]/2/selobj.scale[0])
        #     else: density_large= 0.5/( selobj.dimensions[1]/2/selobj.scale[1])
        # hairCurves.modifiers["GeometryNodes"]["Input_68"] =density_large  #DENSITY SCATTER
        # hairCurves.modifiers["GeometryNodes"]["Input_100"] = abs(activeobj.scale[0])  # OBJ SCALE COMPENSATION
        # hairCurves.modifiers["GeometryNodes"]["Input_73"] = activeobj #SURFACE DENSITY SCATTER
        # if activeobj.modifiers:   #if armature modifier detected, turn on deform on surface
        #     for mod in activeobj.modifiers:
        #         if mod.type=="ARMATURE": hairCurves.modifiers["GeometryNodes"]["Input_63"] = True

        # bpy.data.objects[hairCurves.name].select_set(False)  #deselect in order to see better what it's being painted
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        # bpy.context.view_layer.active_layer_collection = original_collection

        #IF PAINTIMPORT FROM ASSET LIBRARY: shouldn't get into paint mode if importing multiple assets, but turn on procedural, also keep the terrain as the active object
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.data.polygons)  # area of mesh surface
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > _secret_paint_pref("trigger_viewport_mask", 15000):
                hairCurves.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            if not defer_enter_paint_mode:
                context3sculptbrush(context)

        #TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
        hairCurves.modifiers[0]["Input_99"] = False

        #RESELECT ORIGINAL COLLECTION





    # #scatter sel hair on active surface     (MERGED TO MANY HAIR)
    # elif ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "MESH" and selobj.type == "CURVES" \
    #         or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "MESH" and selobj.type == "CURVE":
    #
    #     hairCurves = orenpaint_create_curve(self,context, targetOBJ=activeobj, brushOBJ=selobj, targetCollection=Coll_of_Active, transfer_modifier=True)
    #     # contextorencurveappend(context,activeobj=hairCurves)
    #     # orenpaint_update_modifier_f(context) #check version number: assigns to all obj in blend file
    #
    #     # hairCurves.modifiers["GeometryNodes"]["Input_73"] = activeobj #SURFACE
    #     # hairCurves.modifiers["GeometryNodes"]["Input_71"] = float(random.choice(range(0, 999999)))  # random noise W
    #     # hairCurves.modifiers["GeometryNodes"]["Input_100"] = abs(activeobj.scale[0])  # OBJ SCALE COMPENSATION
    #     # if activeobj.modifiers:   #if armature modifier detected, turn on deform on surface
    #     #     for mod in activeobj.modifiers:
    #     #         if mod.type=="ARMATURE": hairCurves.modifiers["GeometryNodes"]["Input_63"] = True
    #     # for modifier in hairCurves.modifiers:
    #     #     if modifier.type == 'NODES':  # modifier.name == "GeometryNodes"
    #     #         if modifier.node_group and modifier.node_group.name == "Generate Hair Curves":
    #     #             hairCurves.modifiers["Generate Hair Curves"]["Input_2"] = activeobj
    #
    #     hair_thatNeedA_mask=[]
    #     allTerrainArea = sum(face.area for face in activeobj.data.polygons)  # activeobj.dimensions[0]*activeobj.dimensions[1]
    #     if hairCurves.modifiers["GeometryNodes"]["Input_98"] \
    #             or hairCurves.modifiers["GeometryNodes"]["Input_97"] \
    #             or allTerrainArea / (0.5/(hairCurves.modifiers["GeometryNodes"]["Input_68"]*hairCurves.modifiers["GeometryNodes"]["Input_100"])) > 10000 and hairCurves.modifiers["GeometryNodes"]["Input_69"]:   #if masks, or density too high
    #         if hairCurves not in hair_thatNeedA_mask: hair_thatNeedA_mask.append(hairCurves)
    #         # if allTerrainArea / hairCurves.modifiers["GeometryNodes"]["Input_68"] > 10000: hairCurves.display_type = 'BOUNDS'  # bounds for hair with huge density
    #         hairCurves.modifiers["GeometryNodes"]["Input_98"] = False  # MASK1 clean mask slots so that the function doesn't toggle the mask settings
    #         hairCurves.modifiers["GeometryNodes"]["Input_97"] = None  #mask2
    #
    #     for x in objselection: bpy.data.objects[x.name].select_set(False)
    #     bpy.context.view_layer.objects.active = hairCurves
    #
    #
    #     # if hair_thatNeedA_mask: NoMasksDetected = False
    #     # else: NoMasksDetected=True
    #     NoMasksDetected = True
    #     if len(all_hair_with_Vgroup) == len(selobjs_without_active) and len(all_Vgroups) == 1:NoMasksDetected=True  # if all hair to scatter are with same vgroup, skip mask because we'll start painting right away
    #     elif hair_thatNeedA_mask: NoMasksDetected = False
    #     # #fix vertex group
    #     if hairCurves.modifiers["GeometryNodes"]["Input_69"]: vertexgrouppaint_function(self, context,NoMasksDetected, calledfrombutton=False, being_transferred_to_newmesh=True, activeobj=hairCurves)
    #     # fix viewport masks only if modifier has a mask and it has procedural scattering
    #     if NoMasksDetected==False and hairCurves.modifiers["GeometryNodes"]["Input_69"]: orenpaint_viewport_mask_function(self, context, objselection=hair_thatNeedA_mask, activeobj=hair_thatNeedA_mask[0])
    #
    #
    #     if hairCurves.modifiers["GeometryNodes"]["Input_69"] == False: context3sculptbrush(context)
    #
    #
    #     print("scatter sel hair on active surface")















    # scatter SEL COLLECTION on active surface  (risk conflicts with above "DUPLI BIOME ON A NEW OBJ")
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "MESH" and len(selobjs_without_active_with_orencurve)==0:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "MESH" and not biome_detected:  # and len(selobjs_without_active_with_orencurve)!= len(bpy.context.selected_objects):
        print("scatter sel collection on ACTIVE surface")

        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)  # SLOW FOR HIGHPOLY OBJECTS

        # all_materials = []
        # for ob in selobjs_without_active:  # make mats linked to obj and local
        #     if ob.type != "CURVES" and ob != activeobj:
        #         for mat_slot in ob.material_slots:
        #             mat = mat_slot.material
        #             if mat not in all_materials: all_materials.append(mat)

        # hairCurves = orenpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=True, append_orenpaint=True)
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=False)
        if hairCurves is None:
            return {'FINISHED'}

        # bpy.context.view_layer.active_layer_collection = Coll_of_Active  #SELECT COLLECTION
        # bpy.ops.object.curves_empty_hair_add(align='WORLD', location=bpy.context.scene.cursor.location, scale=(1, 1, 1))

        # hairCurves = bpy.context.active_object
        # #APPLY SCALE
        # bpy.ops.object.select_all(action='DESELECT')
        # bpy.data.objects[hairCurves.name].select_set(True) #reselect original
        # bpy.context.view_layer.objects.active = bpy.data.objects[hairCurves.name]  #make active
        # bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # bpy.ops.object.modifier_remove(modifier="Surface Deform")
        # contextorencurveappend(context)
        hairCurves.modifiers[0]["Input_2"] = None  # reset obj brush
        hairCurves.modifiers[0]["Input_9"] = bpy.data.collections[collection_of_one_of_selected.name]
        hairCurves.modifiers[0]["Input_16"] = 5 #MODE scatter  (ignore radius, different scale and rot nodes)
        hairCurves.modifiers[0]["Input_6"][2] = 20  # random z rot
        hairCurves.modifiers[0]["Input_15"] = 0.25 # random scale
        hairCurves.modifiers[0]["Input_62"] = 0.5 #world noise scale
        hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  # world noise scale

        # hairCurves.modifiers["GeometryNodes"]["Input_73"] = activeobj #SURFACE DENSITY SCATTER
        # hairCurves.modifiers["GeometryNodes"]["Input_52"] = 1 # show original curve

        # for matteriall in all_materials: hairCurves.data.materials.append(matteriall) # #LINK MATERIALS

        for x in objselection: x.select_set(False)


        #IF PAINTIMPORT FROM ASSET LIBRARY: shouldn't get into paint mode if importing multiple assets, but turn on procedural and calculate mask, also keep the terrain as active object
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.data.polygons)  # area of mesh surface
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > _secret_paint_pref("trigger_viewport_mask", 15000):
                hairCurves.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            if not defer_enter_paint_mode:
                context3sculptbrush(context, activeobj=hairCurves)


        #TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
        hairCurves.modifiers[0]["Input_99"] = False







    # scatter selected coll with active hair settings on same surface
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and activeobj.type == "CURVES" and selobj.type in ["MESH","EMPTY","CURVE"]:
        print("-----------------------scatter selected coll with active hair settings on same surface")

        Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)  #SLOW FOR HIGHPOLY OBJECTS

        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobjs_without_active, targetCollection=Coll_of_Active, transfer_modifier=True)
        if hairCurves is None:
            return {'FINISHED'}

        # orenpaint_update_modifier_f(context)  # check version number: assigns to all obj in blend file
        # #LINK MATERIALS
        # all_materials = []
        # for ob in bpy.context.selected_objects:  # make mats linked to obj and local
        #     if ob.type != "CURVES" and ob != activeobj:
        #         for mat_slot in ob.material_slots:
        #             mat = mat_slot.material
        #             if mat not in all_materials: all_materials.append(mat)

        # bpy.context.view_layer.active_layer_collection = Coll_of_Active  #SELECT COLLECTION
        # bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.data.surface.name]  # make active
        # bpy.ops.object.curves_empty_hair_add(align='WORLD', location=bpy.data.objects[activeobj.name].location, scale=(1, 1, 1))
        # hairCurves = bpy.context.active_object
        # hairCurves.display_type = activeobj_BoundingBox_State #bounding box state
        # bpy.ops.object.modifier_remove(modifier="Surface Deform")

        # #APPLY SCALE
        # bpy.ops.object.select_all(action='DESELECT')
        # bpy.data.objects[hairCurves.name].select_set(True) #reselect original
        # bpy.context.view_layer.objects.active = bpy.data.objects[hairCurves.name]  #make active
        # bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # bpy.ops.object.select_all(action='DESELECT')
        # bpy.data.objects[hairCurves.name].select_set(True) #reselect original
        # bpy.data.objects[activeobj.name].select_set(True) #reselect original
        # bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]  # make active
        # bpy.ops.object.make_links_data(type='MODIFIERS')
        # bpy.context.active_object.select_set(False)
        # for obj in bpy.context.selected_objects:
        #     bpy.context.view_layer.objects.active = obj


        # contextorencurveappend(context)
        hairCurves.modifiers[0]["Input_2"] = None #reset obj brush
        hairCurves.modifiers[0]["Input_9"] = bpy.data.collections[collection_of_one_of_selected.name]
        hairCurves.modifiers[0]["Input_39"] = False  # deactivate custom material
        hairCurves.modifiers[0]["Input_6"][2] = 20.0
        hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  # world noise scale

        # bpy.context.object.modifiers["GeometryNodes"]["Input_16"] = 5 #MODE scatter  (ignore radius, different scale and rot nodes)
        # bpy.context.object.modifiers["GeometryNodes"]["Input_6"][2] = 20  # random z rot
        # bpy.context.object.modifiers["GeometryNodes"]["Input_15"] = 0.25 # random scale
        # bpy.context.object.modifiers["GeometryNodes"]["Input_62"] = 0.5 #world noise scale
        # # bpy.context.object.modifiers["GeometryNodes"]["Input_52"] = 1 # show original curve
        # if activeobj.data.surface.modifiers:   #if armature modifier detected, turn on deform on surface
        #     for mod in activeobj.data.surface.modifiers:
        #         if mod.type=="ARMATURE": hairCurves.modifiers["GeometryNodes"]["Input_63"] = True
        #
        # for matteriall in all_materials: hairCurves.data.materials.append(matteriall)        #LINK MATERIALS


        # context3sculptbrush(context)
        # bpy.context.view_layer.active_layer_collection = original_collection #RESELECT ORIGINAL COLLECTION
        for x in objselection: x.select_set(False)

        #IF PAINTIMPORT FROM ASSET LIBRARY: shouldn't get into paint mode if importing multiple assets, but turn on procedural and calculate mask, also keep the terrain as active object
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)  # area of mesh surface
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > _secret_paint_pref("trigger_viewport_mask", 15000):
                hairCurves.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            if not defer_enter_paint_mode:
                context3sculptbrush(context, activeobj=hairCurves)


        #TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
        hairCurves.modifiers[0]["Input_99"] = False




























    #MERGE VGROUPS for hair in same surface
    elif N_Of_Selected >=2 and len(all_found_parents) == 1 and all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES":
        if activeobj.parent.data.library: #.data.surface  # CAN'T WEIGHT PAINT IF SURFACE HAS LINKED MESH DATA (can't weight paint on linked data)
            self.report({'WARNING'}, "Can't Weight Paint on an object with Linked Mesh Data: paint with hair or make the data local")
        else:
            vertexgrouppaint_function(self, context,NoMasksDetected=True)







    # #SHOULD DELETE AND MERGE FUNCTIONALITY INTO "many HAIR on MANY MESHES"
    # #MANY HAIR on single MESH or HAIR (multiple hair + 1 target)  (risk conflicts with below "scatter sel collection on active surface")
    # # elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and len(all_found_parents_without_activeobj)==1:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 2 and len(all_found_parents_without_activeobj)==1:
    #     # print("MANY HAIR on single MESH or HAIR")
    #     # print("UPDAAAAAAAAAAAT MANY HAIR on single MESH or HAIR")
    #
    #     secretpaint_update_modifier_f(context)   #update first because node version might not have biomes yet
    #
    #     Check_if_trigger_UV_Reprojection(self, context, activeobj=activeobj, objselection=activeobj)  # SLOW FOR HIGHPOLY OBJECTS
    #
    #     #SET TO NEW BIOME, adjusted to avoid intersecting with existing biome in target mesh
    #     #FIND ALL BIOMES FOR STARTER BRUSH
    #     # hair=[]
    #     # parent = selobjs_without_active_with_orencurve[0].parent
    #     # if selobjs_without_active_with_orencurve[0].type=="CURVES" and parent:   #IF CURVE SELECTED
    #     #     for hai in parent.children: # hair = getChildren(parent)
    #     #         if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
    #     #             for modifier in hai.modifiers:
    #     #                 if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("orenpaint"):
    #     #                     hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
    #     # #ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
    #     # elif selobjs_without_active_with_orencurve[0].type=="MESH" or selobjs_without_active_with_orencurve[0].type=="EMPTY":
    #     #     for hayr in bpy.context.scene.objects:
    #     #     # for hayr in selobjs_without_active_with_orencurve[0].children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
    #     #         if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
    #     #             for modifier in hayr.modifiers: #if mask selected, if brush selobjs_without_active_with_orencurve[0] selected, if terrain selected
    #     #                 if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "orenpaint" and modifier["Input_97"] == selobjs_without_active_with_orencurve[0] \
    #     #                 or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "orenpaint" and modifier["Input_2"] == selobjs_without_active_with_orencurve[0] \
    #     #                 or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "orenpaint" and modifier["Input_73"] == selobjs_without_active_with_orencurve[0]:
    #     #                     hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
    #     all_bgroups_starter=[]
    #     for hayr in selobjs_without_active:
    #         if hayr.modifiers[0]["Socket_0"] not in all_bgroups_starter: all_bgroups_starter.append(hayr.modifiers[0]["Socket_0"])
    #
    #     # #FIND ALL BIOMES FOR TARGET
    #     # hair=[]
    #     # parent = activeobj.parent
    #     # if activeobj.type=="CURVES" and parent:   #IF CURVE SELECTED
    #     #     for hai in parent.children: # hair = getChildren(parent)
    #     #         if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
    #     #             for modifier in hai.modifiers:
    #     #                 if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
    #     #                     hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
    #     # #ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
    #     # elif activeobj.type=="MESH" or activeobj.type=="EMPTY":
    #     #     for hayr in bpy.context.scene.objects:
    #     #     # for hayr in activeobj.children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
    #     #         if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
    #     #             for modifier in hayr.modifiers: #if mask selected, if brush activeobj selected, if terrain selected
    #     #                 if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == activeobj \
    #     #                 or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == activeobj \
    #     #                 or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == activeobj:
    #     #                     hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
    #     # all_bgroups=[]
    #     # for hayr in hair[:]:
    #     #     if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
    #     #     # hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]
    #
    #     #LIST ALL ORIGINAL BIOMES ON THE ACTIVE OBJECT SURFACE AND REMOVE GAPS (change biomes from 1,3,5 into 1,2,3); trying to find out the starting number for the biomes to import, if biome1 and 2 are already on the active surface, it should start from 3
    #     hair = find_all_listed_paintsystems(context, activeobj=activeobj, objselection=objselection)
    #     all_bgroups = []
    #     for hayr in hair[:]:
    #         if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
    #     all_bgroups.sort()
    #     loop = 1
    #     for biome_number in all_bgroups[:]:
    #         for hayr in hair[:]:
    #             if hayr[0].modifiers[0]["Socket_0"] == biome_number:
    #                 hayr[0].modifiers[0]["Socket_0"] = loop
    #                 hair.remove(hayr)
    #         loop += 1
    #
    #
    #     if all_bgroups: additional_biome_n = max(all_bgroups)
    #     else: additional_biome_n= 0 #  -(min(all_bgroups_starter)-1)
    #
    #     #######################################################
    #     #######################################################
    #
    #
    #     highest_distribution_density=0  #create a mask if terrain is too big
    #     newlycreated_hair=[]
    #     hair_thatNeedA_mask=[] #for huge terrains, automatically add
    #     if activeobj.type == "MESH": allTerrainArea = sum(face.area for face in activeobj.data.polygons)
    #     elif activeobj.type == "CURVES": allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)  #activeobj.data.surface
    #     # print("") #WITHOUTH PRINTING SOMETHING IT CRASHES BLENDER???????????????????????
    #     for hair in selobjs_without_active_with_orencurve:
    #
    #         hairCurves = secretpaint_create_curve(self,context, targetOBJ=activeobj, brushOBJ=hair, targetCollection=Coll_of_Active, transfer_modifier=True)
    #         newlycreated_hair.append(hairCurves)
    #
    #         #LINK MODIFIERS
    #         if N_Of_Selected >= 3 or hair.modifiers[0]["Input_69"]: hairCurves.modifiers[0]["Input_69"] = True  # generate hair
    #         #re-copy from original brush hair
    #         hairCurves.modifiers[0]["Input_68"] = hair.modifiers[0]["Input_68"]  # density
    #         hairCurves.modifiers[0]["Input_2"] = hair.modifiers[0]["Input_2"]
    #         hairCurves.modifiers[0]["Input_9"] = hair.modifiers[0]["Input_9"]
    #         hairCurves.modifiers[0]["Input_72"] = hair.modifiers[0]["Input_72"]  # spread
    #         hairCurves.modifiers[0]["Input_70"] = hair.modifiers[0]["Input_70"]  # noise scale
    #         hairCurves.modifiers[0]["Input_82"] = hair.modifiers[0]["Input_82"]  # edge blur
    #
    #         hairCurves.modifiers[0]["Input_60"] = hair.modifiers[0]["Input_60"]  # world noise scale
    #         hairCurves.modifiers[0]["Input_8"] = hair.modifiers[0]["Input_8"]  # scale universal
    #         hairCurves.modifiers[0]["Input_15"] = hair.modifiers[0]["Input_15"]  # scale random
    #         hairCurves.modifiers[0]["Input_62"] = hair.modifiers[0]["Input_62"]  # scale random world
    #         hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  # world noise scale
    #         hairCurves.modifiers[0]["Input_13"] = hair.modifiers[0]["Input_13"]  # scale separate
    #
    #         hairCurves.modifiers[0]["Input_51"] = hair.modifiers[0]["Input_51"]  # global Z
    #         hairCurves.modifiers[0]["Input_65"] = hair.modifiers[0]["Input_65"]  # rot
    #         hairCurves.modifiers[0]["Input_6"] = hair.modifiers[0]["Input_6"]  # random rot
    #         hairCurves.modifiers[0]["Input_53"] = hair.modifiers[0]["Input_53"]  # rot increments
    #         hairCurves.modifiers[0]["Input_23"] = hair.modifiers[0]["Input_23"]  # loc
    #         hairCurves.modifiers[0]["Input_56"] = hair.modifiers[0]["Input_56"]  # wind
    #         hairCurves.modifiers[0]["Input_98"] = hair.modifiers[0]["Input_98"]  # mask check
    #         hairCurves.modifiers[0]["Input_97"] = hair.modifiers[0]["Input_97"]  # mask
    #
    #         hairCurves.modifiers[0]["Socket_0"] = hair.modifiers[0]["Socket_0"] + additional_biome_n  # BIOME NUMBER, adjusted to avoid intersecting with existing biome in target mesh
    #         if len(all_bgroups_starter)>=2: hairCurves.modifiers[0]["Socket_2"] = hair.modifiers[0]["Socket_2"]
    #
    #         if activeobj.data.library: #REMOVE WEIGHT IF SURFACE HAS LINKED MESH DATA (can't weight paint on linked data)
    #             hairCurves.modifiers[0]["Input_83_attribute_name"] = None
    #             hairCurves.modifiers[0]["Input_83_use_attribute"]=0
    #         else:
    #             hairCurves.modifiers[0]["Input_83_attribute_name"] = hair.modifiers[0]["Input_83_attribute_name"]  # VGROUP
    #             hairCurves.modifiers[0]["Input_83_use_attribute"] = hair.modifiers[0]["Input_83_use_attribute"]  # VGROUP
    #
    #         # VIEWPORT MASK
    #         if hairCurves.modifiers[0]["Input_98"] \
    #         or hairCurves.modifiers[0]["Input_97"] \
    #         or (allTerrainArea/   (   (1/   ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))   )   **2))     > bpy.context.preferences.addons[__package__].preferences.trigger_viewport_mask and hairCurves.modifiers[0]["Input_69"]:      #(0.5/(hairCurves.modifiers["GeometryNodes"]["Input_68"]*hairCurves.modifiers["GeometryNodes"]["Input_100"]))             # or allTerrainArea /         (1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5)   * (hairCurves.modifiers[0]["Input_100"]**2)))       /2          > 10000 and hairCurves.modifiers[0]["Input_69"]:      #(0.5/(hairCurves.modifiers["GeometryNodes"]["Input_68"]*hairCurves.modifiers["GeometryNodes"]["Input_100"]))
    #             if hairCurves not in hair_thatNeedA_mask: hair_thatNeedA_mask.append(hairCurves)
    #             hairCurves.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
    #             hairCurves.modifiers[0]["Input_97"] = None
    #
    #
    #     #TERRAIN MATERIAL (only if there are no materials)
    #     if len([slot.material for slot in activeobj.material_slots if slot.material != None]) == 0:
    #         for i, mat_slot in enumerate(all_found_parents_without_activeobj[0].material_slots):
    #             if mat_slot.material:
    #                 if activeobj.material_slots and activeobj.material_slots[i]: activeobj.material_slots[i].material = mat_slot.material  # IF SLOT EXISTS
    #                 else: activeobj.data.materials.append(mat_slot.material)
    #
    #     for x in objselection: bpy.data.objects[x.name].select_set(False)
    #     for ojgb in newlycreated_hair: #RESELECT
    #         if ojgb.name in bpy.context.view_layer.objects:
    #             ojgb.select_set(True)  # select it
    #             bpy.context.view_layer.objects.active = ojgb  # make active
    #
    #     NoMasksDetected = True
    #     if len(all_hair_with_Vgroup) == len(selobjs_without_active) and len(all_Vgroups) == 1: NoMasksDetected=True  #skip mask because we'll start painting right away (if all hair to scatter are with same vgroup)
    #     elif hair_thatNeedA_mask: NoMasksDetected = False
    #     else: NoMasksDetected=True
    #     if auto_Mask_Optimization == False: NoMasksDetected=True  #DISABLE MASK WHEN EXPORTING BIOME SPHERE, it should not have masks, it interferes with selection handling
    #
    #     # fix vertex group mask
    #     vertexgrouppaint_function(self, context,NoMasksDetected,calledfrombutton=False, being_transferred_to_newmesh=True, paint_the_vertex=True)
    #
    #     if N_Of_Selected >= 2 and hairCurves.modifiers[0]["Input_69"] == False:
    #         for x in newlycreated_hair: x.select_set(False) #objselection
    #         context3sculptbrush(context, activeobj=newlycreated_hair[0])
    #         NoMasksDetected = True #no need to mask if going to paint right away
    #
    #     #FIX VIEWPORT MASK:  after vertex group because when creating a mask it becomes active object ready to be moved
    #     if NoMasksDetected==False: secretpaint_viewport_mask_function(self, context, objselection=hair_thatNeedA_mask, activeobj=hair_thatNeedA_mask[0])
    #
    #     #TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
    #     for ojgb in newlycreated_hair:
    #         ojgb.modifiers[0]["Input_99"] = False
    #
    #     print("MANY HAIR on single MESH or HAIR")











    #many HAIR on MANY MESHES (multiple hair + multiple surfaces)  (risk conflicts with below "scatter sel collection on active surface")      ######SUBSTITUTED  MANY HAIR on single MESH or HAIR    and become "many HAIR BIOMES from MANY SURFACES to ALL MESHES (multiple hair + 1 surface)"
    elif ActiveMode == "OBJECT" and N_Of_Selected >= 2 and len(selobjs_without_active_with_orencurve)>=1:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 2 and len(all_meshes_that_are_not_parents) >=1 and len(selobjs_without_active_with_orencurve)>=1:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and len(all_meshes) >=2 and len(selobjs_without_active_with_orencurve)>=1:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and len(all_found_parents_without_activeobj)==1:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 3 and all_meshes >=2 and len(all_found_parents)==1:
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 2:
        print("many HAIR on MANY MESHES")
        newlycreated_hair=[]



        if activeobj.type == "CURVES": all_meshes_to_scatter_onto = [activeobj.parent]     #WHEN SELECTING HAIR, THEN ANOTHER HAIR TO USE ITS TERRAIN, IGNORE THE LIST OF PARENT MESHES
        elif len(all_meshes)==1:all_meshes_to_scatter_onto = [activeobj]                   #WHEN SELECTING HAIR, THEN ITS OWN TERRAIN TO CREATE A DUPLICATE SYSTEM
        else: all_meshes_to_scatter_onto = all_meshes_that_are_not_parents

        print("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",all_meshes_to_scatter_onto)
        for mesh in all_meshes_to_scatter_onto:
            newlycreated_hair_for_currentlyprocessing_mesh = []
            Coll_of_TaragetMesh = []
            for i in mesh.users_collection:
                Coll_of_TaragetMesh = recurLayerCollection(bpy.context.view_layer.layer_collection, i.name)

            # secretpaint_update_modifier_f(context)  # update first because node version might not have biomes yet
            Check_if_trigger_UV_Reprojection(self, context, activeobj=mesh, objselection=[mesh])  # SLOW FOR HIGHPOLY OBJECTS



            #CHECK IF MASK IS NEEDED
            highest_distribution_density=0  #create a mask if terrain is too big
            hair_thatNeedA_mask=[] #for huge terrains, automatically add
            if mesh.type == "MESH": allTerrainArea = sum(face.area for face in mesh.data.polygons)
            elif mesh.type == "CURVES": allTerrainArea = sum(face.area for face in mesh.parent.data.polygons)  #activeobj.data.surface




            #Wether or not to reset biome visibility based on how many biomes are being transferred
            all_bgroups_starter = []
            for hayr in selobjs_without_active_with_orencurve:
                if hayr.modifiers[0]["Socket_0"] not in all_bgroups_starter: all_bgroups_starter.append(hayr.modifiers[0]["Socket_0"])







            for parentt in all_found_parents:



                #LIST ALL EXISTING BIOMES ON THE TARGET SURFACE AND REMOVE GAPS (change biomes from 1,3,5 into 1,2,3); trying to find out the starting number for the biomes to import, if biome1 and 2 are already on the active surface, it should start from 3.   it does that for every parent so that each of the parent's children don't merge biomes with samae number
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
                else: additional_biome_n = 0  # -(min(all_bgroups_starter)-1)




                for hair in parentt.children:
                    if hair in selobjs_without_active_with_orencurve:
                        for modifier in hair.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):



                            # for hair in selobjs_without_active_with_orencurve:
                                hairCurves = secretpaint_create_curve(self,context, targetOBJ=mesh, brushOBJ=hair, targetCollection=Coll_of_TaragetMesh, transfer_modifier=True)
                                if hairCurves is None:
                                    continue
                                newlycreated_hair.append(hairCurves)
                                newlycreated_hair_for_currentlyprocessing_mesh.append(hairCurves)
                                # contextorencurveappend(context,targetOBJ=hairCurves)
                                # orenpaint_update_modifier_f(context) #check version number: assigns to all obj in blend file

                                # bpy.ops.object.curves_empty_hair_add(align='WORLD', location=targetOBJ.location)
                                # hairCurves = bpy.context.active_object
                                # hairCurves.display_type = hair.display_type #selobj_BoundingBox_State  # bounding box state
                                # #APPLY SCALE
                                # bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


                                #LINK MODIFIERS
                                # if N_Of_Selected >= 3 or hair.modifiers[0]["Input_69"]: hairCurves.modifiers[0]["Input_69"] = True  # generate hair
                                if _secret_paint_pref("checkboxKeepManualWhenTransferBiome", False) == False:
                                    if N_Of_Selected >= 3 or hair.modifiers[0]["Input_69"]: hairCurves.modifiers[0]["Input_69"] = True  # generate hair

                                #recopy from original brush hair #NOT NEEDED, automatically happens when creating new curve and copying the modifier value per value
                                hairCurves.modifiers[0]["Input_68"] = hair.modifiers[0]["Input_68"]  # density
                                hairCurves.modifiers[0]["Socket_11"] = hair.modifiers[0]["Socket_11"]  # density
                                hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  # world noise scale
                                # hairCurves.modifiers[0]["Input_2"] = hair.modifiers[0]["Input_2"]
                                # hairCurves.modifiers[0]["Input_9"] = hair.modifiers[0]["Input_9"]
                                # hairCurves.modifiers[0]["Input_72"] = hair.modifiers[0]["Input_72"]  # spread
                                # hairCurves.modifiers[0]["Input_70"] = hair.modifiers[0]["Input_70"]  # noise scale
                                # hairCurves.modifiers[0]["Input_82"] = hair.modifiers[0]["Input_82"]  # edge blur
                                #
                                # hairCurves.modifiers[0]["Input_8"] = hair.modifiers[0]["Input_8"]  # scale universal
                                # hairCurves.modifiers[0]["Input_15"] = hair.modifiers[0]["Input_15"]  # scale random
                                # hairCurves.modifiers[0]["Input_62"] = hair.modifiers[0]["Input_62"]  # scale random world
                                # hairCurves.modifiers[0]["Input_13"] = hair.modifiers[0]["Input_13"]  # scale separate
                                #
                                # hairCurves.modifiers[0]["Input_51"] = hair.modifiers[0]["Input_51"]  # global Z
                                # hairCurves.modifiers[0]["Input_65"] = hair.modifiers[0]["Input_65"]  # rot
                                # hairCurves.modifiers[0]["Input_6"] = hair.modifiers[0]["Input_6"]  # random rot
                                # hairCurves.modifiers[0]["Input_53"] = hair.modifiers[0]["Input_53"]  # rot increments
                                # hairCurves.modifiers[0]["Input_23"] = hair.modifiers[0]["Input_23"]  # loc
                                # hairCurves.modifiers[0]["Input_56"] = hair.modifiers[0]["Input_56"]  # wind
                                # hairCurves.modifiers[0]["Input_98"] = hair.modifiers[0]["Input_98"]  # mask check
                                # hairCurves.modifiers[0]["Input_97"] = hair.modifiers[0]["Input_97"]  # mask

                                hairCurves.modifiers[0]["Socket_0"] = hair.modifiers[0]["Socket_0"] + additional_biome_n  # BIOME NUMBER, adjusted to avoid intersecting with existing biome in target mesh
                                if len(all_bgroups_starter) >= 2: hairCurves.modifiers[0]["Socket_2"] = hair.modifiers[0]["Socket_2"]

                                if mesh.data.library:  # REMOVE WEIGHT IF SURFACE HAS LINKED MESH DATA (can't weight paint on linked data)
                                    hairCurves.modifiers[0]["Input_83_attribute_name"] = ""
                                    hairCurves.modifiers[0]["Input_83_use_attribute"] = False
                                else:
                                    hairCurves.modifiers[0]["Input_83_attribute_name"] = hair.modifiers[0]["Input_83_attribute_name"]  # VGROUP
                                    # hairCurves.modifiers[0]["Input_83_use_attribute"] = hair.modifiers[0]["Input_83_use_attribute"]  # VGROUP
                                    if hair.modifiers[0]["Input_83_use_attribute"] == 1 or hair.modifiers[0]["Input_83_use_attribute"] == True: new_attribute_status_convert_int_to_boolean = True
                                    elif hair.modifiers[0]["Input_83_use_attribute"] == 0 or hair.modifiers[0]["Input_83_use_attribute"] == False: new_attribute_status_convert_int_to_boolean = False
                                    hairCurves.modifiers[0]["Input_83_use_attribute"] = new_attribute_status_convert_int_to_boolean # VGROUP

                                #VIEWPORT MASK
                                if hairCurves.modifiers[0]["Input_98"] \
                                or hairCurves.modifiers[0]["Input_97"]\
                                or (allTerrainArea/   (   (1/   ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))   )   **2))            > _secret_paint_pref("trigger_viewport_mask", 15000) and hairCurves.modifiers[0]["Input_69"]:  # or allTerrainArea / (0.5/(hairCurves.modifiers["GeometryNodes"]["Input_68"]*hairCurves.modifiers["GeometryNodes"]["Input_100"])) > 10000 and hairCurves.modifiers["GeometryNodes"]["Input_69"]:
                                    if hairCurves not in hair_thatNeedA_mask: hair_thatNeedA_mask.append(hairCurves)
                                    # if allTerrainArea / hairCurves.modifiers["GeometryNodes"]["Input_68"] > 10000: hairCurves.display_type = 'BOUNDS'  # bounds for hair with huge density
                                    hairCurves.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
                                    hairCurves.modifiers[0]["Input_97"] = None
                                # hairCurves.location = hairCurves.location  # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))

                                # hairCurves.modifiers["GeometryNodes"]["Input_86"] = targetOBJ.modifiers["GeometryNodes"]["Input_86"] #mask slope
                                # hairCurves.modifiers["GeometryNodes"]["Input_89"] = targetOBJ.modifiers["GeometryNodes"]["Input_89"] #mask slope inverted
                                # hairCurves.modifiers["GeometryNodes"]["Input_91"] = targetOBJ.modifiers["GeometryNodes"]["Input_91"] #mask height
                                # hairCurves.modifiers["GeometryNodes"]["Input_92"] = targetOBJ.modifiers["GeometryNodes"]["Input_92"] #mask height inverted
                                # hairCurves.modifiers["GeometryNodes"]["Input_95"] = targetOBJ.modifiers["GeometryNodes"]["Input_95"] #mask obj
                                # hairCurves.modifiers["GeometryNodes"]["Input_97"] = targetOBJ.modifiers["GeometryNodes"]["Input_97"] #mask obj
                                # hairCurves.modifiers["GeometryNodes"]["Input_98"] = targetOBJ.modifiers["GeometryNodes"]["Input_98"] #mask viewport checkbox
                                # hairCurves.modifiers["GeometryNodes"]["Input_83_attribute_name"] = targetOBJ.modifiers["GeometryNodes"]["Input_83_attribute_name"] #vgroup name
                                # if targetOBJ.modifiers["GeometryNodes"]["Input_83_use_attribute"]==1 and hairCurves.modifiers["GeometryNodes"]["Input_83_use_attribute"]==0: bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")
                                # elif targetOBJ.modifiers["GeometryNodes"]["Input_83_use_attribute"] == 0 and hairCurves.modifiers["GeometryNodes"]["Input_83_use_attribute"]==1: bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")


                                hairCurves.select_set(True)  # select it
                                bpy.context.view_layer.objects.active = hairCurves  # make active





            # # TERRAIN MATERIAL (only if there are no materials)
            # for target_surface in all_meshes_that_are_not_parents:
            #     if len([slot.material for slot in target_surface.material_slots if slot.material != None]) == 0 and all_found_parents[0]:
            #         for i, mat_slot in enumerate(all_found_parents[0].material_slots):
            #             if mat_slot.material:
            #
            #                 if target_surface.material_slots and target_surface.material_slots[i]:
            #                     target_surface.material_slots[i].material = mat_slot.material  # IF SLOT EXISTS
            #                 else:
            #                     target_surface.data.materials.append(mat_slot.material)
            #
            #                 # if activeobj.material_slots and activeobj.material_slots[i]: activeobj.material_slots[i].material = mat_slot.material  # IF SLOT EXISTS
            #                 # else: activeobj.data.materials.append(mat_slot.material)


            NoMasksDetected = True
            if len(all_hair_with_Vgroup) == len(selobjs_without_active) and len(all_Vgroups) == 1: NoMasksDetected=True  #skip mask because we'll start painting right away (if all hair to scatter are with same vgroup)
            elif hair_thatNeedA_mask: NoMasksDetected = False  #paint mask if objs that need it are found
            else: NoMasksDetected=True
            paint_the_vertex=False #AVOID VERTEX PAINT because we're transferring on multiple meshes
            # vertexgrouppaint_function(self, context,NoMasksDetected,calledfrombutton=False, being_transferred_to_newmesh=True, objselection=newlycreated_hair, activeobj=newlycreated_hair[0], paint_the_vertex=paint_the_vertex)
            vertexgrouppaint_function(self, context,NoMasksDetected,calledfrombutton=False, being_transferred_to_newmesh=True, objselection=newlycreated_hair_for_currentlyprocessing_mesh, activeobj=newlycreated_hair_for_currentlyprocessing_mesh[0], paint_the_vertex=paint_the_vertex)
            # FIX VIEWPORT MASK:  after vertex group because when creating a mask it becomes active object ready to be moved
            if NoMasksDetected==False: secretpaint_viewport_mask_function(self, context, objselection=hair_thatNeedA_mask, activeobj=hair_thatNeedA_mask[0])



        #TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
        for ojgb in newlycreated_hair:
            ojgb.modifiers[0]["Input_99"] = False
            ojgb.location = ojgb.location #update

        # for x in objselection: bpy.data.objects[x.name].select_set(False)
        # for ojgb in newlycreated_hair:
        #     ojgb.select_set(True)  # select it
        #     bpy.context.view_layer.objects.active = ojgb  # make active
            # ojgb.location = ojgb.location # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))
        # bpy.context.object.modifiers["GeometryNodes"]["Input_2"] = bpy.data.objects[targetOBJ.name]
        # bpy.context.object.modifiers["GeometryNodes"]["Input_9"] = None
        # context3sculptbrush(context)


        for x in bpy.context.selected_objects: x.select_set(False)
        # if N_Of_Selected >= 2 and newlycreated_hair[0].modifiers[0]["Input_69"] == False: context3sculptbrush(context, activeobj=newlycreated_hair[0])   #hairCurves
        if N_Of_Selected == 2 and newlycreated_hair[0].modifiers[0]["Input_69"] == False and not defer_enter_paint_mode: context3sculptbrush(context, activeobj=newlycreated_hair[0])   #hairCurves

        # #TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
        # for ojgb in newlycreated_hair:
        #     ojgb.modifiers[0]["Input_99"] = False







































































    # scatter selected obj with active hair's settings on same surface
    elif ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "MESH" \
            or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "EMPTY" \
            or ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVES" and selobj.type == "CURVE":

        # orenpaint_update_modifier_f(context)  # check version number: assigns to all obj in blend file
        # for x in objselection: bpy.data.objects[x.name].select_set(False)        #bpy.ops.object.select_all(action='DESELECT')
        # bpy.data.objects[activeobj.name].select_set(True)  # select it
        # bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]  # make active
        # surfaceobj = activeobj.data.surface
        hairCurves = secretpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=selobj, targetCollection=Coll_of_Active, transfer_modifier=True)
        if hairCurves is None:
            return {'FINISHED'}


        # bpy.ops.object.select_all(action='DESELECT')
        # bpy.data.objects[surfaceobj.name].select_set(True)  # select it
        # bpy.context.view_layer.objects.active = bpy.data.objects[surfaceobj.name]  # make active
        # bpy.context.view_layer.active_layer_collection = Coll_of_Active #SELECT COLLECTION OF ACTIVE OBJ
        # bpy.ops.object.curves_empty_hair_add(align='WORLD', location=bpy.data.objects[activeobj.name].location, scale=(1, 1, 1))
        # hairCurves = bpy.context.active_object
        # hairCurves.display_type = activeobj_BoundingBox_State #bounding box state
        # # bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # bpy.data.objects[activeobj.name].select_set(True)  # select it
        # bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]  # make active
        # bpy.ops.object.make_links_data(type='MODIFIERS')
        # bpy.context.active_object.select_set(False)
        # for obj in bpy.context.selected_objects:
        #     bpy.context.view_layer.objects.active = obj
        hairCurves.modifiers[0]["Input_2"] = selobj
        hairCurves.modifiers[0]["Input_9"] = None #clean collection
        hairCurves.modifiers[0]["Input_39"] = False  # deactivate custom material
        hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))  # world noise scale
        # hairCurves.modifiers[0]["Input_99"] = False  # TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains; refer to function "secretpaint_create_curve" line 2768
        # hairCurves.modifiers["GeometryNodes"]["Input_71"] = float(random.choice(range(0, 999999)))  # random noise W
        # hairCurves.modifiers["GeometryNodes"]["Input_73"] = hairCurves.data.surface
        # # bpy.ops.transform.translate(value=(0, 0, 0))  # best way to update the scene ;update scene
        # if selobj.dimensions[0] > selobj.dimensions[1]: density_large = 0.5/( selobj.dimensions[0]/2)   #*selobj.modifiers["GeometryNodes"]["Input_100"] #/ hairCurves.scale[0]
        # else: density_large = 0.5/( selobj.dimensions[1]/2)  #*selobj.modifiers["GeometryNodes"]["Input_100"] #/ hairCurves.scale[1]  # /2
        # hairCurves.modifiers["GeometryNodes"]["Input_68"] = density_large  # DENSITY SCATTER
        # # hairCurves.modifiers["GeometryNodes"]["Input_100"] = surfaceobj.scale[0]  # OBJ SCALE COMPENSATION
        # if hairCurves.data.surface.modifiers:   #if armature modifier detected, turn on deform on surface
        #     for mod in hairCurves.data.surface.modifiers:
        #         if mod.type=="ARMATURE": hairCurves.modifiers["GeometryNodes"]["Input_63"] = True

        # #LINK MATERIALS
        # bpy.data.objects[selobj.name].select_set(True)  # reselect original
        # bpy.context.view_layer.objects.active = bpy.data.objects[selobj.name]  # make active
        # bpy.ops.object.make_links_data(type='MATERIAL')
        # bpy.data.objects[selobj.name].select_set(False)  # reselect original
        # bpy.context.view_layer.objects.active = bpy.data.objects[hairCurves.name]  # make active

        for x in objselection: bpy.data.objects[x.name].select_set(False)

        #IF PAINTIMPORT FROM ASSET LIBRARY: shouldn't get into paint mode if importing multiple assets, but turn on procedural and calculate mask, also keep the terrain as active object
        if importpainting_multiple_assets:
            allTerrainArea = sum(face.area for face in activeobj.parent.data.polygons)  # area of mesh surface
            if (allTerrainArea / ((1 / ((hairCurves.modifiers[0]["Input_68"] ** 0.5) * (hairCurves.modifiers[0]["Input_100"]))) ** 2)) > _secret_paint_pref("trigger_viewport_mask", 15000):
                hairCurves.modifiers[0]["Input_98"] = False  # clean mask slots so that the function doesn't toggle the mask settings
                hairCurves.modifiers[0]["Input_97"] = None
                secretpaint_viewport_mask_function(self, context, objselection=[hairCurves], activeobj=hairCurves, importpainting_multiple_assets=importpainting_multiple_assets)
            hairCurves.modifiers[0]["Input_69"] = True
        else:
            bpy.context.view_layer.objects.active = hairCurves
            if not activeobj.modifiers[0]["Input_69"] and not defer_enter_paint_mode: context3sculptbrush(context, activeobj=hairCurves) #don't enter hair sculpt mode if noise scatter detected
            # context3sculptbrush(context, activeobj=hairCurves)

        # bpy.context.view_layer.objects.active = hairCurves
        # bpy.context.view_layer.active_layer_collection = original_collection  # SELECT COLLECTION

        # TURN ON SYSTEM, it's turned off by default to allow for viewport mask calculation first when transfering biomes to huge terrains (and other modifier interactions); refer to function "secretpaint_create_curve" line 2768
        hairCurves.modifiers[0]["Input_99"] = False

        print("scatter selected obj with active hair settings on same surface")
















































    # SWICTH WHICH HAIR SYSTEM TO PAINT FROM SCULPT MODE OR EDIT MODE OR WEIGHT PAINT MODE  (avoid it when import-painting multiple assets from File Browser "Q")
    # elif all_sel_are_orencurves and ActiveMode == "SCULPT_CURVES" and activeobj.type == "CURVES":
    # elif ActiveMode == "SCULPT_CURVES" and activeobj.type == "CURVES":
    elif ActiveMode in ["SCULPT_CURVES", "WEIGHT_PAINT", "EDIT"]:
        pickup_trace_owner = None
        if _get_pickup_trace() is None:
            pickup_trace_owner = _begin_pickup_trace(
                "q_pickup_existing_terrain",
                context,
                active_mode=ActiveMode,
                selected_objects=N_Of_Selected,
            )
        pickup_trace = _get_pickup_trace()
        hoverobj = None
        pickup_outcome = "no_match"
        found_to_paint = []
        paint_type = []
        siblings_with_same_weight_paint = []
        hover_is_brush_source = False
        # print("UPDAAAAAAAAAAAT SWICTH WHICH HAIR TO PAINT FROM SCULPT MODE OR EDIT MODE OR WEIGHT PAINT MODE")
        update_modifier_start = time.perf_counter()
        secretpaint_update_modifier_f(context,upadte_provenance="SWICTH WHICH HAIR SYSTEM TO PAINT FROM SCULPT MODE OR EDIT MODE OR WEIGHT PAINT MODE")  # check version number: assigns to all obj in blend file
        if pickup_trace:
            pickup_trace.action("q_pickup.update_modifier", update_modifier_start, detail=f"active_mode={ActiveMode}")

        store_density_start = time.perf_counter()
        stored_density_spacing = secret_paint_store_active_density_brush_spacing(context, activeobj)
        if pickup_trace:
            pickup_trace.action(
                "q_pickup.store_active_density_spacing",
                store_density_start,
                detail=(
                    f"stored={stored_density_spacing}; "
                    f"active={activeobj.name if activeobj else 'None'}"
                ),
            )

        mode_object_start = time.perf_counter()
        bpy.ops.object.mode_set(mode="OBJECT")
        if pickup_trace:
            pickup_trace.action("q_pickup.mode_set_object", mode_object_start, detail=f"from={ActiveMode}")
        select_hover_start = time.perf_counter()
        hoverobj, _hover_location = _secret_paint_hover_object_from_mouse(context, event)
        hover_label = f"{hoverobj.name}<{hoverobj.type}>" if hoverobj else "None"
        if pickup_trace:
            pickup_trace.set_meta("hover", hover_label)
            pickup_trace.action("q_pickup.hover_select", select_hover_start, detail=f"hover={hover_label}")

        #not needed, applypaint already calls it # Check_if_trigger_UV_Reprojection(self, context, activeobj=hoverobj, objselection=hoverobj)  # SLOW FOR HIGHPOLY OBJECTS

        #IF HOVEROBJ IS CURVES: mark to paint later
        if hoverobj and hoverobj.type in ["CURVE","CURVES"] and hoverobj.modifiers:
            inspect_curve_start = time.perf_counter()
            secret_paint_modifiers = 0
            # bpy.ops.object.mode_set(mode="SCULPT_CURVES")  # without this, the modal map for selecting obj makes it so that when going back to obj mode and selecting a hai obj: weirdly jumps to paint mode
            for modif in hoverobj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                    secret_paint_modifiers += 1
                    if hoverobj.type == "CURVE":
                        paint_type="EDIT"
                        found_to_paint.append(hoverobj)
                    elif modif["Input_69"] == True and modif["Input_83_attribute_name"]:
                        paint_type="WEIGHT_PAINT"
                        found_to_paint.append(hoverobj)
                    elif modif["Input_69"] == False:
                        paint_type="SCULPT_CURVES"
                        found_to_paint.append(hoverobj)
                    # elif modif["Input_69"] == True and not modif["Input_83_attribute_name"]: paint_type="SCULPT_CURVES"    #don't select hair with procedural that still needs to be applied
            if pickup_trace:
                pickup_trace.action(
                    "q_pickup.inspect_hover_curve",
                    inspect_curve_start,
                    detail=f"secret_modifiers={secret_paint_modifiers}; matches={len(found_to_paint)}; paint_type={paint_type if paint_type else 'none'}",
                )








        #ELIF MESH: FIND HAIR WITH SAME BRUSH
        # elif result != {'PASS_THROUGH'} and hoverobj.type == "MESH" and hoverobj != activeobj.parent and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
        elif hoverobj and hoverobj.type == "MESH" and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
            print("KKKKKKKKKKKKKKKKKKKK")
            #LIST ALL HAIR THAT ARE USING THE ACTIVE WEIGHT PAINT GROUP (only useful when creating the same vertex biome on another mesh)
            siblings_with_same_weight_paint=[]
            # hair_to_sample=[]
            all_brush_objs=[]
            all_brush_colls=[]
            collect_sources_start = time.perf_counter()
            if activeobj.type=="MESH" and ActiveMode == "WEIGHT_PAINT" and activeobj.children:
                for children in activeobj.children:
                    if children.type == "CURVES" and children.modifiers:
                        for modif in children.modifiers:  # modifier.name == "GeometryNodes"
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" and activeobj.vertex_groups.active.name == children.modifiers[0]["Input_83_attribute_name"]:
                                siblings_with_same_weight_paint.append(children)
                                # hair_to_sample.append(children)
                                if children.modifiers[0]["Input_2"] and children.modifiers[0]["Input_2"] not in all_brush_objs: all_brush_objs.append(children.modifiers[0]["Input_2"])
                                if children.modifiers[0]["Input_9"] and children.modifiers[0]["Input_9"] not in all_brush_colls: all_brush_colls.append(children.modifiers[0]["Input_9"])
            elif activeobj.type=="CURVES":
                # hair_to_sample=[]
                # hair_to_sample.append(activeobj)
                siblings_with_same_weight_paint.append(activeobj)
                if activeobj.modifiers[0]["Input_2"] and activeobj.modifiers[0]["Input_2"] not in all_brush_objs: all_brush_objs.append(activeobj.modifiers[0]["Input_2"])
                if activeobj.modifiers[0]["Input_9"] and activeobj.modifiers[0]["Input_9"] not in all_brush_colls: all_brush_colls.append(activeobj.modifiers[0]["Input_9"])
            hover_is_brush_source = (
                hoverobj in all_brush_objs
                or any(_secret_paint_collection_contains_object(brush_coll, hoverobj) for brush_coll in all_brush_colls)
                or _secret_paint_object_is_source_for_any_system(hoverobj)
            )
            if pickup_trace:
                pickup_trace.action(
                    "q_pickup.collect_active_sources",
                    collect_sources_start,
                    detail=f"siblings={len(siblings_with_same_weight_paint)}; brush_objs={len(all_brush_objs)}; brush_colls={len(all_brush_colls)}; hover_is_brush_source={hover_is_brush_source}",
                )



            all_vgroups_in_hoverobjs_children =[]
            scan_hover_children_start = time.perf_counter()
            hover_children_scanned = 0
            hover_secret_paint_children = 0
            if hoverobj.children:
                for children in hoverobj.children:
                    if children.type == "CURVES" and children.modifiers:
                        hover_children_scanned += 1
                        for modif in children.modifiers:
                            # if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("orenpaint") and modif["Input_2"]==hair_to_sample[0].modifiers["GeometryNodes"]["Input_2"] and modif["Input_9"]==hair_to_sample[0].modifiers["GeometryNodes"]["Input_9"]:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                hover_secret_paint_children += 1
                                if modif["Input_2"] in all_brush_objs or modif["Input_9"] in all_brush_colls:


                                    # find the most similar hair to the original
                                    if len(siblings_with_same_weight_paint) <= 1:
                                        # print("########siblinnnnnnnnnnnnggggggggggggg",children.name)
                                        # print("MMMMMMMMMMMMMMM-----------------",modif["Input_69"])
                                        # print("KKKKKKKKKKKKKKKKKKK-----------------",modif["Input_83_use_attribute"])

                                        # if hair.modifiers[0]["Input_83_use_attribute"] == 1 or hair.modifiers[0]["Input_83_use_attribute"] == True: new_attribute_status_convert_int_to_boolean = True
                                        # elif hair.modifiers[0]["Input_83_use_attribute"] == 0 or hair.modifiers[0]["Input_83_use_attribute"] == False: new_attribute_status_convert_int_to_boolean = False
                                        # hairCurves.modifiers[0]["Input_83_use_attribute"] = new_attribute_status_convert_int_to_boolean  # VGROUP
                                        #
                                        # if modif["Input_83_use_attribute"]==new_attribute_status_convert_int_to_boolean:
                                        if modif["Input_83_use_attribute"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_83_use_attribute"]:
                                            if modif["Input_69"] == True and modif["Input_83_use_attribute"]:
                                                paint_type = "WEIGHT_PAINT"
                                                found_to_paint = []  # reset in order to add only the current child, can't have a single variable because later i iterate with found_to_paint[0] and it gets mixed up with the paint type of previous loop
                                                found_to_paint.append(children)
                                                print("(((UUUUUUUUUUUUUUUUUUUUUUU")
                                            elif modif["Input_69"] == False:
                                                paint_type = "SCULPT_CURVES"
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                print("(((lllllllllllllllllllllllllll")
                                            # elif modif["Input_69"] == True and not modif["Input_83_attribute_name"]: paint_type="SCULPT_CURVES"    #don't select hair with procedural that still needs to be applied
                                        if modif["Input_69"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_69"]:
                                            if modif["Input_69"] == True and modif["Input_83_use_attribute"]:
                                                paint_type="WEIGHT_PAINT"
                                                found_to_paint=[] #reset in order to add only the current child, can't have a single variable because later i iterate with found_to_paint[0] and it gets mixed up with the paint type of previous loop
                                                found_to_paint.append(children)
                                                print("(((IIIIIIIIIIIIIIIIII")
                                            elif modif["Input_69"] == False:
                                                paint_type="SCULPT_CURVES"
                                                found_to_paint=[]
                                                found_to_paint.append(children)
                                                print("(((ooooooooooooooooooooo")
                                            #elif modif["Input_69"] == True and not modif["Input_83_attribute_name"]: paint_type="SCULPT_CURVES"    #don't select hair with procedural that still needs to be applied
                                        if modif["Input_69"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_69"] and modif["Input_83_use_attribute"]==siblings_with_same_weight_paint[0].modifiers[0]["Input_83_use_attribute"]:
                                            if modif["Input_69"] == True and modif["Input_83_use_attribute"]:
                                                paint_type = "WEIGHT_PAINT"
                                                print("(((YYYYYYYYYYYYYYYY")
                                                found_to_paint = []  # reset in order to add only the current child, can't have a single variable because later i iterate with found_to_paint[0] and it gets mixed up with the paint type of previous loop
                                                found_to_paint.append(children)
                                            elif modif["Input_69"] == False:
                                                paint_type = "SCULPT_CURVES"
                                                print("(((TTTTTTTTTTTTTTTTTTT")
                                                found_to_paint = []
                                                found_to_paint.append(children)
                                                print("(((9999999999999999999")
                                            # elif modif["Input_69"] == True and not modif["Input_83_attribute_name"]: paint_type="SCULPT_CURVES"    #don't select hair with procedural that still needs to be applied
                                            # break

                                    # find same vgroup on new terrain
                                    elif len(siblings_with_same_weight_paint) >= 2:
                                        # print("222222",)
                                        if modif["Input_83_attribute_name"] and modif["Input_83_attribute_name"] not in all_vgroups_in_hoverobjs_children: all_vgroups_in_hoverobjs_children.append(modif["Input_83_attribute_name"])
                                        if all_vgroups_in_hoverobjs_children and modif["Input_83_attribute_name"]==all_vgroups_in_hoverobjs_children[0]:
                                            paint_type="WEIGHT_PAINT"
                                            found_to_paint.append(children)
            if pickup_trace:
                pickup_trace.action(
                    "q_pickup.scan_hover_children",
                    scan_hover_children_start,
                    detail=(
                        f"hover_children={len(hoverobj.children)}; scanned_curves={hover_children_scanned}; "
                        f"secret_modifiers={hover_secret_paint_children}; matches={len(found_to_paint)}; "
                        f"paint_type={paint_type if paint_type else 'none'}"
                    ),
                )


        # #IF HOVEROBJ IS THE SURFACE OF THE ACTIVE PAINT SYSTEM
        # elif result != {'PASS_THROUGH'} and hoverobj.type == "MESH" and hoverobj == activeobj.parent and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
        #     print("MMMMMMMMMMMMMMMMMMMM", activeobj.name)
        #     apply_paint(self, context, activeobj=activeobj, objselection=[activeobj], applyIDs=True)
        # # return{'FINISHED'}

        # #PAINT WHATEVER WAS FOUND
        if found_to_paint:
            pickup_outcome = "paint_existing"
            if pickup_trace:
                pickup_trace.set_meta("paint_type", paint_type if paint_type else "none")
                pickup_trace.set_meta("match_count", len(found_to_paint))
            set_active_start = time.perf_counter()
            bpy.context.view_layer.objects.active = found_to_paint[0]
            if pickup_trace:
                pickup_trace.action("q_pickup.set_active_found", set_active_start, detail=f"target={found_to_paint[0].name}")
            if paint_type=="EDIT":
                route_start = time.perf_counter()
                curve_draw_tool(context)
                if pickup_trace:
                    pickup_trace.action("q_pickup.route_curve_edit", route_start, detail=f"target={found_to_paint[0].name}")
            elif paint_type=="WEIGHT_PAINT":
                route_start = time.perf_counter()
                vertexgrouppaint_function(self, context, NoMasksDetected=True)
                if pickup_trace:
                    pickup_trace.action("q_pickup.route_weight_paint", route_start, detail=f"target={found_to_paint[0].name}")
            elif paint_type=="SCULPT_CURVES":
                route_start = time.perf_counter()
                #APPLY PAINT BUT KEEP THE ACTIVE BRUSH IF WE WERE IN CURVE SCULPT MODE
                if ActiveMode == "SCULPT_CURVES": apply_paint(self,context,activeobj=found_to_paint[0], objselection=[found_to_paint[0]],applyIDs=True,keep_active_brush=True)
                else: apply_paint(self,context,activeobj=found_to_paint[0], objselection=[found_to_paint[0]],applyIDs=True )
                if pickup_trace:
                    pickup_trace.action(
                        "q_pickup.route_sculpt_curves",
                        route_start,
                        detail=f"target={found_to_paint[0].name}; keep_active_brush={bool(ActiveMode == 'SCULPT_CURVES')}",
                    )
                print("(((8888888888888888888888888")


        #IF NO BRUSH FOUND: CREATE IT
        elif not found_to_paint and hoverobj and hoverobj.type=="MESH" and hoverobj!=activeobj.parent and not hoverobj.name.startswith("Secret Paint Viewport Mask"):
            if bool(hoverobj.data.library) and ActiveMode=="WEIGHT_PAINT":
                pickup_outcome = "restore_linked_hover"
                restore_linked_start = time.perf_counter()
                bpy.context.view_layer.objects.active = activeobj
                bpy.ops.object.mode_set(mode=ActiveMode)
                if pickup_trace:
                    pickup_trace.action("q_pickup.restore_linked_hover", restore_linked_start, detail=f"hover={hoverobj.name}; mode={ActiveMode}")
            else:
                pickup_outcome = "create_new_system"
                create_new_start = time.perf_counter()
                secretpaint_function(self, context, event,objselection = siblings_with_same_weight_paint, activeobj=hoverobj)
                if pickup_trace:
                    pickup_trace.action(
                        "q_pickup.create_new_system",
                        create_new_start,
                        detail=f"hover={hoverobj.name}; siblings={len(siblings_with_same_weight_paint)}",
                    )

        #IF NOTHING FOUND OR CREATED: GO BACK TO ORIGINAL STATE
        else:
            pickup_outcome = "restore_original"
            restore_state_start = time.perf_counter()
            bpy.context.view_layer.objects.active = activeobj
            bpy.ops.object.mode_set(mode=ActiveMode)
            if pickup_trace:
                pickup_trace.action("q_pickup.restore_original_state", restore_state_start, detail=f"mode={ActiveMode}")


        clear_selection_start = time.perf_counter()
        for ob in bpy.context.selected_objects: bpy.data.objects[ob.name].select_set(False) #paint better without selection
        if pickup_trace:
            pickup_trace.action("q_pickup.clear_selection", clear_selection_start)

        #cleanup empty hair systems in scene, for misclicks, if have no curve and were visible and not procedural
        # orenpaint_cleanup_empty_systems(self, context)
        # for obj in bpy.context.scene.objects:
        #     if obj.type == "CURVES" and obj.modifiers and obj!=bpy.context.active_object:
        #         for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
        #             if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "orenpaint" and  (sum(len(spline.points) for spline in obj.data.curves)) ==0 and obj.modifiers["GeometryNodes"]["Input_99"] == False and obj.modifiers["GeometryNodes"]["Input_69"] == False:
        #                 bpy.data.objects.remove(obj, do_unlink=True)
        #                 # print("DELEEEEEEETED",)
        #
        #             #CLEANUP VGROUPS AS WELL

        print("SWICTH WHICH HAIR TO PAINT FROM SCULPT MODE OR EDIT MODE OR WEIGHT PAINT MODE")

        # end_time = time.time()
        # print("Milliseconds (Ping):",(end_time - start_time) * 1000)
        if pickup_trace_owner is not None:
            detail_hover = f"{hoverobj.name}<{hoverobj.type}>" if hoverobj else "None"
            detail_paint_type = paint_type if paint_type else "none"
            _finish_pickup_trace(
                pickup_trace_owner,
                detail=f"outcome={pickup_outcome}; hover={detail_hover}; matches={len(found_to_paint)}; paint_type={detail_paint_type}",
            )






































    #RESUME DRAWING CURVE
    elif ActiveMode == "OBJECT" and N_Of_Selected == 1 and activeobj.type == "CURVE":
        curve_draw_tool(context)
        print("RESUME DRAWING CURVE")

    #RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS   -ALSO MERGE VGROUP FOR SEL HAIR IN SAME SURFACE                              #overrides draw curve, but users are very unlikely to want to draw with a paint system
    # elif all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES" \
    #         or all_sel_are_orencurves and ActiveMode == "SCULPT_CURVES" and activeobj.type == "CURVES":
    elif len(all_found_parents)==1 and all_sel_are_orencurves and ActiveMode == "OBJECT" and activeobj.type == "CURVES" \
    or ActiveMode == "OBJECT" and N_Of_Selected == 0:
        #not needed, called automatically from apply_paint function  #Check_if_trigger_UV_Reprojection(self, context, activeobj=all_found_parents[0], objselection=all_found_parents[0])  # SLOW FOR HIGHPOLY OBJECTS
        # print("UPDAAAAAAAAAAAT RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS")
        secretpaint_update_modifier_f(context,upadte_provenance="RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS")  # check version number: assigns to all obj in blend file
        # for ob in objselection: #deselect everythig, easier to see what you're painting
        #     bpy.data.objects[ob.name].select_set(False)
        # return{'FINISHED'}

        # UNDER MOUSE CURSOR: SELECT HAIR AND PAINT
        if N_Of_Selected == 0:
            hoverobj, _hover_location = _secret_paint_hover_object_from_mouse(context, event)
            if hoverobj and hoverobj.type == "CURVES" and hoverobj.modifiers:
                for modif in hoverobj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                        if modif["Input_69"] == True and modif["Input_83_use_attribute"] == True: vertexgrouppaint_function(self, context, NoMasksDetected=True)
                        elif modif["Input_69"] == True and modif["Input_83_use_attribute"] == False:
                            apply_paint(self, context, activeobj=hoverobj, objselection=[hoverobj])
                        elif modif["Input_69"] == False:
                            # context3sculptbrush(context)
                            apply_paint(self, context, activeobj=hoverobj, objselection=[hoverobj], applyIDs=True)
                        else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
                    else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
            else: self.report({'WARNING'}, "Try again while hovering with the mouse on a hair system")
            if hoverobj:
                bpy.data.objects[hoverobj.name].select_set(False)  # select it   #BONES bpy.data.objects[c.id_data.name].pose.bones[bone.name].bone.select = False

            for ob in objselection: #deselect everythig, easier to see what you're painting
                bpy.data.objects[ob.name].select_set(False)


        #TRADITIONAL SELECTION
        elif N_Of_Selected == 1: #paint vertex or hair
            if activeobj.modifiers[0]["Input_69"] == True:
                apply_paint(self, context, activeobj=activeobj, objselection=[activeobj])

            # elif activeobj.modifiers["GeometryNodes"]["Input_69"] == False and not activeobj.modifiers["GeometryNodes"]["Input_83_use_attribute"]:
            elif activeobj.modifiers[0]["Input_69"] == False:
                # context3sculptbrush(context)
                apply_paint(self, context, activeobj=activeobj, objselection=[activeobj], applyIDs=True)


            # if activeobj.modifiers["GeometryNodes"]["Input_69"] == True:
            #     vertexgrouppaint_function(self, context,NoMasksDetected=True)
            # else:
            #     context3sculptbrush(context)
        # #TRADITIONAL SELECTION
        # elif N_Of_Selected >= 2: #paint vertex
        #     vertexgrouppaint_function(self, context,NoMasksDetected=True)

            # multiple with same parent:
            # if share save vgroup: paint mode
            #different vgroup: share active one or create new > paint
            #different parent: scatter with same settings

        # cleanup empty hair systems in scene, for misclicks
        # orenpaint_cleanup_empty_systems(self, context)
        # for obj in bpy.context.scene.objects:
        #     if obj.type == "CURVES" and obj.modifiers and obj not bpy.context.active_object and obj not in :bpy.context.selected_objects
        #         for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
        #             if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "orenpaint":
        #                 if (sum(len(spline.points) for spline in obj.data.curves)) == 0 and \
        #                         obj.modifiers["GeometryNodes"]["Input_99"] == False and \
        #                         obj.modifiers["GeometryNodes"]["Input_69"] == False: bpy.data.objects.remove(obj,do_unlink=True)


        for x in objselection: bpy.data.objects[x.name].select_set(False)

        print("RESUME PAINTING SELECTED HAIR, HOVER IF NO SELECTED OBJS")













    # #scatter SEL HAIRS with ACTIVE HAIR settings            (MERGED TO MANY HAIR)                                #should unite with 3 above        or on ACTIVE SURFACE
    # elif ActiveMode == "OBJECT" and N_Of_Selected >= 2 and all_sel_are_orencurves and len(all_found_parents)>=1:
    #
    #     # orenpaint_update_modifier_f(context)  # check version number: assigns to all obj in blend file
    #
    #
    #     hair_thatNeedA_mask=[] #for huge terrains, automatically add
    #     allTerrainArea = sum(face.area for face in activeobj.data.surface.data.polygons)
    #     all_new_hair = []
    #     for hair in selobjs_without_active:
    #         hairCurves = orenpaint_create_curve(self, context, targetOBJ=activeobj, brushOBJ=hair, targetCollection=Coll_of_Active, transfer_modifier=True)
    #         all_new_hair.append(hairCurves)
    #
    #         # bpy.context.view_layer.objects.active = activeobj.data.surface
    #         # bpy.context.view_layer.active_layer_collection = Coll_of_Active #SELECT COLLECTION OF ACTIVE OBJ
    #         # bpy.ops.object.curves_empty_hair_add(align='WORLD', location=bpy.data.objects[activeobj.name].location, scale=(1, 1, 1))
    #         # hairCurves = bpy.context.active_object
    #         # hairCurves.display_type = selobj_BoundingBox_State  # bounding box state
    #         # all_new_hair.append(hairCurves)
    #
    #         # bpy.ops.object.select_all(action='DESELECT')
    #         # bpy.data.objects[hairCurves.name].select_set(True)  # select it
    #         # bpy.context.view_layer.objects.active = bpy.data.objects[hairCurves.name]  # make active
    #         # #APPLY SCALE
    #         # bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    #
    #         #LINK GEONODES + MATERIALS
    #         # bpy.data.objects[hair.name].select_set(True)  # select it
    #         # bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  # make active
    #         # bpy.ops.object.make_links_data(type='MODIFIERS')
    #         # bpy.ops.object.make_links_data(type='MATERIAL')
    #         hairCurves.modifiers["GeometryNodes"]["Input_73"] = activeobj.data.surface #surface
    #         hairCurves.modifiers["GeometryNodes"]["Input_68"] = hair.modifiers["GeometryNodes"]["Input_68"]
    #         hairCurves.modifiers["GeometryNodes"]["Input_2"] = hair.modifiers["GeometryNodes"]["Input_2"]
    #         hairCurves.modifiers["GeometryNodes"]["Input_9"] = hair.modifiers["GeometryNodes"]["Input_9"]
    #         hairCurves.modifiers["GeometryNodes"]["Input_83_attribute_name"] = hair.modifiers["GeometryNodes"]["Input_83_attribute_name"]
    #         hairCurves.modifiers["GeometryNodes"]["Input_83_use_attribute"] = hair.modifiers["GeometryNodes"]["Input_83_use_attribute"]
    #         if N_Of_Selected >=3: hairCurves.modifiers["GeometryNodes"]["Input_69"] = True #generate hair
    #         # hairCurves.modifiers["GeometryNodes"]["Input_71"] = float(random.choice(range(0, 999999)))  # random noise W
    #         # hairCurves.modifiers["GeometryNodes"]["Input_86"] = activeobj.modifiers["GeometryNodes"]["Input_86"] #mask slope
    #         # hairCurves.modifiers["GeometryNodes"]["Input_89"] = activeobj.modifiers["GeometryNodes"]["Input_89"] #mask slope inverted
    #         # hairCurves.modifiers["GeometryNodes"]["Input_91"] = activeobj.modifiers["GeometryNodes"]["Input_91"] #mask height
    #         # hairCurves.modifiers["GeometryNodes"]["Input_92"] = activeobj.modifiers["GeometryNodes"]["Input_92"] #mask height inverted
    #         # hairCurves.modifiers["GeometryNodes"]["Input_95"] = activeobj.modifiers["GeometryNodes"]["Input_95"] #mask obj
    #         # hairCurves.modifiers["GeometryNodes"]["Input_97"] = activeobj.modifiers["GeometryNodes"]["Input_97"] #mask obj
    #         # hairCurves.modifiers["GeometryNodes"]["Input_98"] = activeobj.modifiers["GeometryNodes"]["Input_98"] #mask viewport checkbox
    #         # if activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"] and not hairCurves.modifiers["GeometryNodes"]["Input_83_attribute_name"]: bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")
    #         # elif not activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"] and hairCurves.modifiers["GeometryNodes"]["Input_83_attribute_name"]: bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")  #Input_83_use_attribute
    #         # hairCurves.modifiers["GeometryNodes"]["Input_83_attribute_name"] = activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"] #vgroup name
    #         # if activeobj.data.surface.modifiers:   #if armature modifier detected, turn on deform on surface
    #         #     for mod in activeobj.data.surface.modifiers:
    #         #         if mod.type=="ARMATURE": hairCurves.modifiers["GeometryNodes"]["Input_63"] = True
    #         # # hairCurves.modifiers["GeometryNodes"]["Input_73"] = hairCurves.object.data.surface
    #         # # hairCurves.modifiers["GeometryNodes"]["Input_68"] = hair.modifiers["GeometryNodes"]["Input_68"]#density
    #
    #         # scales = activeobj.data.surface.scale
    #         # max_scale = max(scales)
    #         # if max_scale == scales[0]: largest_axis = activeobj.data.surface.scale[0]
    #         # elif max_scale == scales[1]: largest_axis = activeobj.data.surface.scale[1]
    #         # else: largest_axis = activeobj.data.surface.scale[2]
    #         # hairCurves.modifiers["GeometryNodes"]["Input_100"] = abs(largest_axis) #activeobj.data.surface.scale[0]  # OBJ SCALE COMPENSATION
    #         # for modifier in hairCurves.modifiers:
    #         #     if modifier.type == 'NODES':  # modifier.name == "GeometryNodes"
    #         #         if modifier.node_group and modifier.node_group.name == "Generate Hair Curves":
    #         #             hairCurves.modifiers["Generate Hair Curves"]["Input_2"] = activeobj
    #
    #         if hairCurves.modifiers["GeometryNodes"]["Input_98"] \
    #                 or hairCurves.modifiers["GeometryNodes"]["Input_97"] \
    #                 or allTerrainArea / (0.5/(hairCurves.modifiers["GeometryNodes"]["Input_68"]*hairCurves.modifiers["GeometryNodes"]["Input_100"])) > 10000 and hairCurves.modifiers["GeometryNodes"]["Input_69"]:
    #             if hairCurves not in hair_thatNeedA_mask: hair_thatNeedA_mask.append(hairCurves)
    #             # if allTerrainArea / hairCurves.modifiers["GeometryNodes"]["Input_68"] > 10000: hairCurves.display_type = 'BOUNDS'  # bounds for hair with huge density
    #             hairCurves.modifiers["GeometryNodes"]["Input_97"] = None  # clean mask slots so that the function doesn't toggle the mask settings
    #             hairCurves.modifiers["GeometryNodes"]["Input_98"] = False
    #         # hairCurves.location = hairCurves.location  # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))
    #
    #
    #     # bpy.ops.object.select_all(action='DESELECT')
    #     for x in objselection: bpy.data.objects[x.name].select_set(False)
    #     for obj in all_new_hair:
    #         bpy.data.objects[obj.name].select_set(True)
    #         bpy.context.view_layer.objects.active = obj
    #         # obj.location = obj.location
    #
    #
    #
    #
    #     NoMasksDetected = True
    #     if len(all_hair_with_Vgroup) == len(selobjs_without_active) and len(all_Vgroups) == 1:NoMasksDetected=True  # if all hair to scatter are with same vgroup, skip mask because we'll start painting right away
    #     elif hair_thatNeedA_mask: NoMasksDetected = False
    #     # else: NoMasksDetected=True
    #     # fix vertex group mask
    #     vertexgrouppaint_function(self, context,NoMasksDetected,calledfrombutton=False, being_transferred_to_newmesh=True)
    #     # FIX VIEWPORT MASK:  after vertex group because when creating a mask it becomes active object ready to be moved
    #     if NoMasksDetected==False: orenpaint_viewport_mask_function(self, context, objselection=hair_thatNeedA_mask, activeobj=hair_thatNeedA_mask[0])
    #
    #
    #     # bpy.context.object.modifiers["GeometryNodes"]["Input_2"] = bpy.data.objects[activeobj.name]
    #     # bpy.context.object.modifiers["GeometryNodes"]["Input_9"] = None
    #     # bpy.ops.transform.translate(value=(0, 0, 0))  # best way to update the scene  # ojgb.location = ojgb.location  # best way to update the scene
    #     if N_Of_Selected == 2 and selobj.modifiers["GeometryNodes"]["Input_69"] == False: context3sculptbrush(context)
    #     # bpy.context.view_layer.active_layer_collection = original_collection #restore COLLECTION
    #
    #     print("scatter SEL HAIRS with ACTIVE HAIR settings")

































    #DRAW CURVE, OBJ MODE, 1 or 2
    elif ActiveMode == "OBJECT" and N_Of_Selected == 1:
        if "circulararray" in kwargs: circulararray = kwargs.get("circulararray")
        else:circulararray = False
        if "straightarray" in kwargs: straightarray = kwargs.get("straightarray")
        else:straightarray = False

        if not circulararray and not straightarray and activeobj.type in {"MESH", "EMPTY"}:
            hoverobj, _hover_location = _secret_paint_hover_object_from_mouse(context, event)
            if hoverobj is None or hoverobj == activeobj or getattr(hoverobj, "type", "") != "MESH":
                self.report({'WARNING'}, "Hover a terrain or select it together with the brush object before pressing Q")
                return {'CANCELLED'}

            Check_if_trigger_UV_Reprojection(self, context, activeobj=hoverobj, objselection=[hoverobj])
            target_collection = context.collection
            try:
                if hoverobj.users_collection:
                    target_collection = hoverobj.users_collection[0]
            except Exception:
                pass

            hairCurves = secretpaint_create_curve(
                self,
                context,
                targetOBJ=hoverobj,
                targetCollection=target_collection,
                brushOBJ=activeobj,
                transfer_modifier=False,
            )
            if hairCurves is None:
                return {'FINISHED'}

            hairCurves.modifiers[0]["Input_2"] = activeobj
            hairCurves.modifiers[0]["Input_16"] = 5
            hairCurves.modifiers[0]["Input_6"][2] = 20
            hairCurves.modifiers[0]["Input_15"] = 0.25
            hairCurves.modifiers[0]["Input_62"] = 0.5
            hairCurves.modifiers[0]["Input_60"] = 0.15 * ((hairCurves.modifiers[0]["Input_68"] ** 0.5))
            for x in objselection:
                x.select_set(False)
            bpy.context.view_layer.objects.active = hairCurves
            if not defer_enter_paint_mode:
                context3sculptbrush(context, activeobj=hairCurves)
            hairCurves.modifiers[0]["Input_99"] = False
            print("DRAW CURVE, OBJ MODE, 1 source on hover target")
            return {'FINISHED'}

        curve_data = bpy.data.curves.new(name="Secret Paint", type="CURVE")
        curve_data.dimensions = '3D'
        # curve_data.resolution_u = 64  # Number of points to approximate the circle

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
                p.co = (new_co + [1.0])  # (add nurbs
                p.select = True

        hairCurves = bpy.data.objects.new("Secret Paint", curve_data)
        bpy.context.collection.objects.link(hairCurves)    #LINK OBJ TO COLLECTION
        for x in bpy.context.selected_objects: x.select_set(False)   # activeobj.select_set(False)
        bpy.context.view_layer.objects.active = hairCurves
        hairCurves.select_set(True)
        contextorencurveappend(context)  # append and assign orenpaint geonode

        #LINK MATERIALS
        material_cache = {}
        for material in _secret_paint_collect_safe_materials_from_object(activeobj, material_cache):
            _secret_paint_append_material_once(hairCurves.data.materials, material)

        #DENSITY
        # if activeobj.type in ["MESH","CURVE"] and activeobj.dimensions > (0,0,0): hairCurves.modifiers[0]["Input_68"] = (1 / ( max(activeobj.dimensions)  **2)  )   *2
        # else:density_large = 1.0  #can't calculate the density from anything that's not a mesh
        obj_for_dimensions = activeobj
        if activeobj.type=="MESH" and activeobj.modifiers:  #IF IT'S AN ASSEMBLY USE ITS PARENT
            for modif in activeobj.modifiers:
                if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                    node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                    for input in node_group_inputs_temp:
                        if input.socket_type == "NodeSocketObject" and input.name == "Parent":
                            if modif[input.identifier] and modif[input.identifier].type == "MESH": obj_for_dimensions = modif[input.identifier]
        if max(obj_for_dimensions.dimensions)>0:
            hairCurves.modifiers[0]["Input_68"] = secret_paint_apply_object_size_density_multiplier(
                (1 / (max(obj_for_dimensions.dimensions) ** 2)) * 2,
                context,
            )    #can't calculate the density from anything that's not a mesh


        dont_set_drawing_tool = False
        if circulararray or straightarray:  # 90 degrees rotation for circular array (buildings etc)
            dont_set_drawing_tool =True
            hairCurves.modifiers[0]["Input_65"][0] = 1.5708
            hairCurves.modifiers[0]["Input_65"][1] = -1.5708

        hairCurves.modifiers[0]["Input_2"] = activeobj
        hairCurves.location= bpy.context.scene.cursor.location
        curve_draw_tool(context, dont_set_drawing_tool=dont_set_drawing_tool)
        context3sculptbrush(context)
        print("DRAW CURVE, OBJ MODE, 1 or 2")

    # draw stretched curve










    #draw sel obj with settings of active curve
    elif ActiveMode == "OBJECT" and N_Of_Selected == 2 and activeobj.type == "CURVE":
        selobj.select_set(False)
        bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},TRANSFORM_OT_translate={})
        curveobj = bpy.context.active_object

        #link materials
        selobj.select_set(True)  # select it
        bpy.context.view_layer.objects.active = bpy.data.objects[selobj.name]  # make active
        bpy.ops.object.make_links_data(type='MATERIAL')
        selobj.select_set(False)
        bpy.context.view_layer.objects.active = bpy.data.objects[curveobj.name]  # make active

        #delete curves in edit mode
        bpy.ops.object.editmode_toggle()
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.curve.dissolve_verts()

        curve_draw_tool(context)
        bpy.context.object.modifiers[0]["Input_2"] = bpy.data.objects[selobj.name]
        print("draw sel obj with settings of active curve")




    # secretpaint_cleanup_empty_systems(self, context)

    # return {'FINISHED'}
class orenscatter(bpy.types.Operator):
    """Select the object you want to paint with, press Q, paint on multiple terrains at once. Also works from the asset browser. Also converts procedural paint systems into manual mode."""
    bl_idname = "secret.paint"
    bl_label = "Paint"
    bl_options = {'REGISTER', 'UNDO'}
    exit_paint_mode: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    use_selected_source: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    # def execute(self, context):
    #     orenpaint_function(self,context)
    #     return {'FINISHED'}

    def execute(self, context):
        use_selected_source = bool(getattr(self, "use_selected_source", False))
        _secret_paint_q_debug_log(
            "secret.paint.execute.enter",
            context,
            reset=use_selected_source,
            exit_paint_mode=bool(getattr(self, "exit_paint_mode", False)),
            use_selected_source=use_selected_source,
        )
        if self.exit_paint_mode:
            _secret_paint_q_debug_log("secret.paint.execute.exit_property", context)
            _secret_paint_panel_exit_paint_mode(context)
            return {'FINISHED'}
        return self.invoke(context, None)

    def invoke(self, context, event):
        raw_exit_paint_mode = bool(getattr(self, "exit_paint_mode", False))
        raw_use_selected_source = bool(getattr(self, "use_selected_source", False))
        exit_paint_mode = raw_exit_paint_mode
        use_selected_source = raw_use_selected_source
        secret_paint_world_paint_module = None
        base_paint_shortcut_event = False
        retired_stale_object_mode_operator = False
        keyboard_shortcut_event = False
        try:
            from . import secret_paint_world_paint as secret_paint_world_paint_module
            if event is not None:
                base_paint_shortcut_event = bool(
                    secret_paint_world_paint_module.is_base_paint_shortcut_event(context, event)
                )
        except Exception:
            secret_paint_world_paint_module = None
            base_paint_shortcut_event = False
        if event is not None:
            event_type = getattr(event, "type", "")
            keyboard_shortcut_event = bool(
                event_type
                and getattr(event, "value", "") in {'PRESS', 'CLICK', 'CLICK_DRAG'}
                and event_type not in {
                    'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE',
                    'ACTIONMOUSE', 'SELECTMOUSE', 'EVT_TWEAK_L',
                    'EVT_TWEAK_M', 'EVT_TWEAK_R', 'MOUSEMOVE',
                    'INBETWEEN_MOUSEMOVE', 'WHEELUPMOUSE',
                    'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
                    'WINDOW_ACTIVATE', 'WINDOW_DEACTIVATE',
                    'WINDOW_ENTER', 'WINDOW_LEAVE', 'TIMER', 'NONE',
                }
            )
        if (base_paint_shortcut_event or keyboard_shortcut_event) and raw_exit_paint_mode:
            exit_paint_mode = False
            use_selected_source = False
            try:
                self.exit_paint_mode = False
                self.use_selected_source = False
            except Exception:
                pass
            _secret_paint_q_debug_log(
                "secret.paint.invoke.clear_stale_panel_props_for_shortcut",
                context,
                raw_exit_paint_mode=raw_exit_paint_mode,
                raw_use_selected_source=raw_use_selected_source,
                event_type=getattr(event, "type", ""),
                event_value=getattr(event, "value", ""),
                keyboard_shortcut_event=keyboard_shortcut_event,
            )
        _secret_paint_q_debug_log(
            "secret.paint.invoke.enter",
            context,
            reset=use_selected_source,
            exit_paint_mode=exit_paint_mode,
            raw_exit_paint_mode=raw_exit_paint_mode,
            raw_use_selected_source=raw_use_selected_source,
            use_selected_source=use_selected_source,
            event_type=getattr(event, "type", ""),
            event_value=getattr(event, "value", ""),
        )
        if exit_paint_mode:
            _secret_paint_q_debug_log("secret.paint.invoke.exit_property", context)
            _secret_paint_panel_exit_paint_mode(context)
            return {'FINISHED'}

        try:
            if secret_paint_world_paint_module is None:
                from . import secret_paint_world_paint as secret_paint_world_paint_module
            running_operator = getattr(secret_paint_world_paint_module, "_world_operator", lambda: None)()
            _secret_paint_q_debug_log(
                "secret.paint.invoke.running_check",
                context,
                running=running_operator is not None,
                use_selected_source=use_selected_source,
            )
            if running_operator is not None:
                running_in_object_mode = (getattr(context, "mode", "") or "") == 'OBJECT'
                if running_in_object_mode:
                    _secret_paint_q_debug_log(
                        "secret.paint.invoke.finish_stale_object_mode_operator",
                        context,
                        use_selected_source=use_selected_source,
                    )
                    running_operator.finish_world_paint(context)
                    try:
                        restore_base_paint_shortcuts = getattr(
                            secret_paint_world_paint_module,
                            "restore_base_paint_shortcuts_for_exit",
                            None,
                        )
                        if restore_base_paint_shortcuts is not None:
                            restore_base_paint_shortcuts(context)
                    except Exception:
                        pass
                    if use_selected_source:
                        return {'FINISHED'}
                    retired_stale_object_mode_operator = True
                    running_operator = None
                else:
                    _secret_paint_q_debug_log(
                        "secret.paint.invoke.running_operator_not_stale",
                        context,
                        use_selected_source=use_selected_source,
                    )
            if running_operator is not None:
                if use_selected_source:
                    _secret_paint_q_debug_log("secret.paint.invoke.finish_running_use_selected", context)
                    running_operator.finish_world_paint(context)
                    try:
                        restore_base_paint_shortcuts = getattr(
                            secret_paint_world_paint_module,
                            "restore_base_paint_shortcuts_for_exit",
                            None,
                        )
                        if restore_base_paint_shortcuts is not None:
                            restore_base_paint_shortcuts(context)
                    except Exception:
                        pass
                    _secret_paint_q_debug_log("secret.paint.invoke.finish_running_use_selected.exit", context)
                    return {'FINISHED'}
                try:
                    if not hasattr(running_operator, "_event_is_in_world_paint_view") or running_operator._event_is_in_world_paint_view(context, event):
                        _secret_paint_q_debug_log("secret.paint.invoke.pick_source_once", context)
                        running_operator._pick_source_once(context, event)
                except Exception:
                    pass
                return {'FINISHED'}
        except Exception:
            pass

        stale_default_paint_shortcut_event = False
        if (
            keyboard_shortcut_event
            and not base_paint_shortcut_event
            and not retired_stale_object_mode_operator
            and not raw_exit_paint_mode
            and not raw_use_selected_source
            and getattr(event, "type", "") == 'Q'
            and not any(bool(getattr(event, modifier_name, False)) for modifier_name in ("shift", "ctrl", "alt", "oskey", "hyper"))
        ):
            active_keyboard_base_items = []
            try:
                if secret_paint_world_paint_module is None:
                    from . import secret_paint_world_paint as secret_paint_world_paint_module
                active_keyboard_base_items = [
                    keymap_item
                    for keymap_item in secret_paint_world_paint_module._base_paint_keymap_items(context)
                    if (
                        bool(getattr(keymap_item, "active", False))
                        and getattr(keymap_item, "map_type", "") == 'KEYBOARD'
                    )
                ]
            except Exception:
                active_keyboard_base_items = []
            configured_plain_q = any(
                getattr(keymap_item, "type", "") == 'Q'
                and not any(bool(getattr(keymap_item, modifier_name, False)) for modifier_name in ("shift", "ctrl", "alt", "oskey", "hyper"))
                for keymap_item in active_keyboard_base_items
            )
            stale_default_paint_shortcut_event = bool(active_keyboard_base_items and not configured_plain_q)

        if stale_default_paint_shortcut_event:
            _secret_paint_q_debug_log(
                "secret.paint.invoke.cancel_stale_default_shortcut",
                context,
                event_type=getattr(event, "type", ""),
                event_value=getattr(event, "value", ""),
            )
            return {'CANCELLED'}

        if not use_selected_source and secret_paint_world_paint_module is not None:
            if _secret_paint_cleanup_stale_world_paint_state(context, secret_paint_world_paint_module):
                _secret_paint_q_debug_log("secret.paint.invoke.cleaned_stale_world_state_before_start", context)

        if use_selected_source and secret_paint_world_paint_module is not None:
            try:
                exit_state_active = getattr(secret_paint_world_paint_module, "world_paint_exit_state_active", None)
                if exit_state_active is not None and exit_state_active(context):
                    _secret_paint_q_debug_log("secret.paint.invoke.exit_stale_world_state", context)
                    _secret_paint_panel_exit_paint_mode(context)
                    return {'FINISHED'}
            except Exception:
                pass

        if use_selected_source and (getattr(context, "mode", "") or "") == 'SCULPT_CURVES':
            _secret_paint_q_debug_log("secret.paint.invoke.exit_stale_sculpt_mode", context)
            _secret_paint_panel_exit_paint_mode(context)
            return {'FINISHED'}

        preferences = _secret_paint_addon_preferences(context)

        if preferences and not getattr(preferences, "checkboxUseLegacyQPaint", False):
            if secret_paint_world_paint_module is None:
                _secret_paint_q_debug_log("secret.paint.invoke.world_module_none", context)
                return _secret_paint_invoke_world_paint_mode(context)

            selected_objects = list(context.selected_objects)
            entry_raycast_preview_source = None
            shortcut_invocation = False
            if not use_selected_source:
                try:
                    shortcut_invocation = bool(
                        secret_paint_world_paint_module.is_base_paint_shortcut_event(context, event)
                    )
                except Exception:
                    shortcut_invocation = False
                if not shortcut_invocation:
                    event_type = getattr(event, "type", "")
                    event_value = getattr(event, "value", "")
                    pointer_events = {
                        'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE',
                        'ACTIONMOUSE', 'SELECTMOUSE', 'EVT_TWEAK_L',
                        'EVT_TWEAK_M', 'EVT_TWEAK_R', 'MOUSEMOVE',
                        'INBETWEEN_MOUSEMOVE', 'WHEELUPMOUSE',
                        'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
                        'WINDOW_ACTIVATE', 'WINDOW_DEACTIVATE',
                        'WINDOW_ENTER', 'WINDOW_LEAVE', 'TIMER', 'NONE',
                    }
                    shortcut_invocation = bool(
                        getattr(getattr(context, "area", None), "type", None) == 'VIEW_3D'
                        and event_type
                        and event_type not in pointer_events
                        and event_value in {'PRESS', 'CLICK', 'CLICK_DRAG'}
                    )

            selected_single_procedural_system = bool(
                getattr(context, "mode", "") == 'OBJECT'
                and len(selected_objects) == 1
                and _secret_paint_system_is_procedural(selected_objects[0])
            )
            raycast_over_single_selection = bool(
                shortcut_invocation
                and
                getattr(preferences, "checkboxRaycastQWhenSingleSelected", False)
                and len(selected_objects) == 1
                and not selected_single_procedural_system
            )
            if (
                shortcut_invocation
                and not retired_stale_object_mode_operator
                and (not selected_objects or raycast_over_single_selection)
            ):
                _secret_paint_q_debug_log(
                    "secret.paint.invoke.shortcut_pick_source",
                    context,
                    selected_count=len(selected_objects),
                    raycast_over_single_selection=raycast_over_single_selection,
                )
                picked_source = None
                try:
                    picked_source = secret_paint_world_paint_module.pick_entry_source_object(
                        context,
                        event,
                        allow_procedural_systems=getattr(context, "mode", "") == 'OBJECT',
                    )
                except Exception:
                    picked_source = None
                if picked_source is None:
                    if raycast_over_single_selection:
                        picked_source = (
                            context.active_object
                            if context.active_object in selected_objects
                            else selected_objects[0] if selected_objects else None
                        )
                    if picked_source is None:
                        if raycast_over_single_selection:
                            self.report({'WARNING'}, "No paint source found under the mouse")
                        else:
                            self.report({'WARNING'}, "Hover an object to paint with, or select one object")
                        _secret_paint_q_debug_log("secret.paint.invoke.cancel_no_pick_source", context)
                        return {'CANCELLED'}

                try:
                    if getattr(context, "mode", "") != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass
                try:
                    for selected_obj in list(context.selected_objects):
                        selected_obj.select_set(False)
                    picked_source.select_set(True)
                    context.view_layer.objects.active = picked_source
                except Exception:
                    pass
                selected_objects = [picked_source]
                entry_raycast_preview_source = picked_source

            entry_hold_preview_source = entry_raycast_preview_source
            if (
                entry_hold_preview_source is None
                and shortcut_invocation
                and getattr(context, "mode", "") == 'OBJECT'
                and len(selected_objects) == 1
                and _secret_paint_system_modifier(selected_objects[0]) is None
            ):
                entry_hold_preview_source = selected_objects[0]

            if (
                getattr(context, "mode", "") == 'OBJECT'
                and len(selected_objects) >= 2
                and any(_secret_paint_system_modifier(obj) is not None for obj in selected_objects)
                and any(obj.type == "MESH" for obj in selected_objects)
            ):
                source_systems = [
                    obj for obj in selected_objects
                    if _secret_paint_system_modifier(obj) is not None
                ]
                single_manual_source = (
                    len(source_systems) == 1
                    and not _secret_paint_system_is_procedural(source_systems[0])
                )
                existing_system_names = {
                    obj.name for obj in bpy.data.objects
                    if _secret_paint_system_modifier(obj) is not None
                }
                transfer_meshes = [obj for obj in selected_objects if obj.type == "MESH"]
                if transfer_meshes and context.active_object not in transfer_meshes:
                    try:
                        context.view_layer.objects.active = transfer_meshes[0]
                    except Exception:
                        pass
                result = secretpaint_function(
                    self,
                    context,
                    event,
                    defer_enter_paint_mode=True,
                )
                created_systems = [
                    obj for obj in bpy.data.objects
                    if (
                        obj.name not in existing_system_names
                        and _secret_paint_system_modifier(obj) is not None
                    )
                ]
                if (
                    single_manual_source
                    and len(created_systems) == 1
                    and not _secret_paint_system_is_procedural(created_systems[0])
                ):
                    return _secret_paint_start_world_paint_for_object(context, created_systems[0])
                return result if result is not None else {'FINISHED'}

            if len(selected_objects) == 1 and _secret_paint_system_is_procedural(selected_objects[0]):
                _secret_paint_q_debug_log("secret.paint.invoke.apply_procedural", context)
                activeobj = selected_objects[0]
                if context.view_layer.objects.active != activeobj:
                    context.view_layer.objects.active = activeobj
                secretpaint_update_modifier_f(context, upadte_provenance="secret.paint.world_paint_apply_procedural")
                _secret_paint_panel_clear_world_paint_object_guard()
                result = apply_paint(self, context, activeobj=activeobj, objselection=[activeobj])
                _secret_paint_preview_world_paint_entry_source(
                    context,
                    entry_hold_preview_source,
                    hold=True,
                    event=event,
                )
                return result

            # With legacy Q disabled, do not fall back into the old sculpt/weight-paint routing.
            # World Paint owns validation and user-facing warnings until the preference is enabled again.
            _secret_paint_q_debug_log(
                "secret.paint.invoke.start_world_paint_mode",
                context,
                selected_count=len(selected_objects),
                shortcut_invocation=shortcut_invocation,
                use_selected_source=use_selected_source,
            )
            result = _secret_paint_invoke_world_paint_mode(context)
            _secret_paint_preview_world_paint_entry_source(
                context,
                entry_hold_preview_source,
                hold=True,
                event=event,
            )
            return result

        window_manager = getattr(context, "window_manager", None)
        try:
            if window_manager is None:
                raise AttributeError("context has no window_manager")
            window_manager.modal_handler_add(self)
        except (AttributeError, TypeError):
            if isinstance(self, bpy.types.Operator):
                raise
            _secret_paint_q_debug_log("secret.paint.invoke.legacy_modal_add.fake_operator", context)
            return {'RUNNING_MODAL'}
        _secret_paint_q_debug_log("secret.paint.invoke.legacy_modal_add", context)
        # orenpaint_function(self, context, event) #only executes on first loop
        # self.timer = context.window_manager.event_timer_add(0.1, window=context.window)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        secretpaint_function(self, context, event)
        return {'FINISHED'}

        # logging.info("awyo")
        # start_time = time.time()
        # if event.type == 'GRLESS':  #LEFTMOUSE   # if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        #     orenpaint_function(self, context, event)
    #     return {'PASS_THROUGH'}
        #
        # # if event.type == 'LEFTMOUSE' and event.value == 'PRESS':  # if event.type == 'GRLESS'\
        # #     activeobj = bpy.context.active_object
        # #     current_mode = bpy.context.object.mode
        # #     bpy.ops.object.mode_set(mode="OBJECT")
        # #     result = bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))  # SELECT HOVEROBJ
        # #     hoverobj = []
        # #     if result != {'PASS_THROUGH'} and hoverobj!=activeobj:
        # #         hoverobj = bpy.context.active_object
        # #         bpy.data.objects[hoverobj.name].select_set(False)
        # #         bpy.context.view_layer.objects.active = activeobj
        # #         orenpaint_function(self,context, event)
        # #     return {'PASS_THROUGH'}
        #
        # acceptable_modes=["SCULPT_CURVES","WEIGHT_PAINT"]
        # if event.type == 'RIGHTMOUSE' or event.type == 'ESC' or bpy.context.object.mode not in acceptable_modes:
        #     print("ENDED",)
        #     return {'FINISHED'}
        #
        # end_time = time.time()
        # print("Milliseconds (Ping):",(end_time - start_time) * 1000)
        # return {'PASS_THROUGH'}


class secretpaint_mode_pie(bpy.types.Operator):
    """Switch to Object Mode and start Secret Paint"""
    bl_idname = "secret.paint_mode_pie"
    bl_label = "Secret Paint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        active_object = context.active_object
        if active_object and active_object.mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except RuntimeError as exc:
                self.report({'ERROR'}, f"Could not switch to Object Mode: {exc}")
                return {'CANCELLED'}

        return bpy.ops.secret.paint('INVOKE_DEFAULT', use_selected_source=True)


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
    material_cache = {}


    if current_mode == "WEIGHT_PAINT":
        for hair in ORIGINALactiveobj.children:
            if hair.modifiers[0]["Input_83_attribute_name"] == ORIGINALactiveobj.vertex_groups.active.name:
                bpy.context.view_layer.objects.active = hair
                hair_thatneeds_to_switch = hair
                break
    else:
        hair_thatneeds_to_switch = ORIGINALactiveobj

    # if len(objselection) == 1 and hair_thatneeds_to_switch.type == "CURVES" or \
    #         len(objselection) == 1 and hair_thatneeds_to_switch.type == "CURVE":

    all_selected_are_meshes = True
    for obj in objselection: #bpy.context.selected_objects:
        if obj.type != "MESH": all_selected_are_meshes=False

    if len(objselection) == 1 or all_selected_are_meshes:
        hoverobj, _hover_location = _secret_paint_hover_object_from_mouse(context, event)

        if hoverobj and hoverobj.type in ["MESH", "CURVES", "CURVE", "EMPTY"] and hoverobj != hair_thatneeds_to_switch and hoverobj != hair_thatneeds_to_switch.parent:
            if hoverobj not in objselection: objselection.append(hoverobj)
        else:
            for x in bpy.context.selected_objects: x.select_set(False)  # objselection
            bpy.context.view_layer.objects.active = ORIGINALactiveobj
            bpy.ops.object.mode_set(mode=current_mode)
            return {'FINISHED'}
    else:
        hoverobj = hair_thatneeds_to_switch

    # activeobj = bpy.context.active_object
    # objselection = bpy.context.selected_objects
    N_Of_Selected = len(objselection)
    randomselectedobj = []
    randomselected_non_hair = []
    all_objs_are_hair = True

    all_selected_hair = []
    all_selected_non_hair = []
    selected_without_active = []
    all_selected_are_meshes = True
    if N_Of_Selected:
        for obj in objselection: #bpy.context.selected_objects:

            if obj.type != "MESH": all_selected_are_meshes=False

            if obj != hoverobj:
                randomselectedobj = obj
                selected_without_active.append(obj)

            # if "orenpaint" not in obj.modifiers.node_tree: randomselected_non_hair = obj
            if obj.type != "CURVES" and obj.type != "CURVE": randomselected_non_hair = obj
            # if obj.type != "CURVES": randomselected_non_hair = obj

            if obj.type != "CURVES": all_objs_are_hair = False
            # if obj.type != "CURVE": all_objs_are_hair = False

            # if obj.type == "CURVES" or obj.type == "CURVE": all_selected_hair.append(obj)
            if obj.type == "CURVES": all_selected_hair.append(obj)

            # if obj.type != "CURVES" or obj.type != "CURVE": all_selected_non_hair.append(obj)
            if obj.type != "CURVES": all_selected_non_hair.append(obj)

    ################################### v
    # bpy.context.view_layer.objects.active = ORIGINALactiveobj
    # ORIGINALactiveobj.select_set(True)
    # for x in ORIGINALobjselection: x.select_set(True)

    if all_selected_are_meshes:

        for ob in selected_without_active:
            print(ob)
            ob.select_set(True)
            ob.data = hoverobj.data

            for i, mat_slot in enumerate(hoverobj.material_slots):
                if mat_slot.material:
                    safe_material = _secret_paint_safe_material_for_assignment(mat_slot.material, material_cache)
                    if safe_material is None:
                        continue
                    if ob.material_slots and ob.material_slots[i]:
                        ob.material_slots[i].link = mat_slot.link
                        ob.material_slots[i].material = safe_material  # IF SLOT EXISTS
                    else: _secret_paint_append_material_once(ob.data.materials, safe_material)

            #copy modifiers
            for m in ob.modifiers:  # iterate over modifiers
                ob.modifiers.remove(m)  # delete modifier
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



    # switch sel hair to active obj
    if N_Of_Selected == 2 and randomselectedobj.type == "CURVES" and hoverobj.type != "CURVES" \
            or N_Of_Selected == 2 and randomselectedobj.type == "CURVE" and hoverobj.type != "CURVES":

        print("switch sel hair to active obj", )

        # delete materials and link from obj
        # for i in range(len(randomselectedobj.material_slots)): bpy.ops.object.material_slot_remove({'object': randomselectedobj})
        # bpy.ops.object.make_links_data(type='MATERIAL')
        for hair in selected_without_active:
            _secret_paint_replace_curve_materials_from_sources(
                hair,
                _secret_paint_collect_safe_materials_from_object(hoverobj, material_cache),
            )

            # next(m for m in bpy.context.active_object.modifiers if m.type == 'NODES').node_group = bpy.data.node_groups.get("orenpaint")
            # set brush object
            # hair.modifiers["GeometryNodes"]["Input_2"] = bpy.data.objects[selection1Name]
            hair.modifiers[0]["Input_2"] = hoverobj  # bursh obj
            hair.modifiers[0]["Input_9"] = None  # clean collection
            # hair.modifiers["GeometryNodes"]["Input_68"] = activeobj.modifiers["GeometryNodes"]["Input_68"]  # density
            hair.modifiers[0]["Input_39"] = False  # deactivate custom material
            # hair.modifiers["GeometryNodes"]["Input_100"] = randomselectedobj.scale[0]  # OBJ SCALE COMPENSATION
            # if activeobj.type=="MESH":  #avoid for empty obj
            #     if activeobj.dimensions[0] > activeobj.dimensions[1]:
            #         density_large = 0.5/( (activeobj.dimensions[0] / 2) / activeobj.scale[0])
            #     else:
            #         density_large = 0.5/( (activeobj.dimensions[1] / 2) / activeobj.scale[1])
            #     hair.modifiers["GeometryNodes"]["Input_68"] = density_large  # DENSITY SCATTER
            # hair.location = hair.location

            bpy.context.active_object.select_set(False)
            for obj in bpy.context.selected_objects: bpy.context.view_layer.objects.active = obj

        for x in bpy.context.selected_objects: x.select_set(False)  # objselection
        bpy.context.view_layer.objects.active = saveactual_activeobj
        bpy.ops.object.mode_set(mode=current_mode)



    # all sel objs are hair and link modif from active
    elif N_Of_Selected >= 2 and all_objs_are_hair:
        print("all sel objs are hair and link modif from active", )

        for hair in selected_without_active:

            _secret_paint_replace_curve_materials_from_sources(
                hair,
                _secret_paint_collect_safe_materials_from_object(hoverobj, material_cache),
            )

            hair.modifiers[0]["Input_2"] = hoverobj.modifiers[0]["Input_2"]  # bursh obj
            hair.modifiers[0]["Input_9"] = hoverobj.modifiers[0]["Input_9"]  # clean collection
            hair.modifiers[0]["Input_68"] = hoverobj.modifiers[0]["Input_68"]  # density
            # hair.modifiers["GeometryNodes"]["Input_69"] = activeobj.modifiers["GeometryNodes"]["Input_69"]  # procedural checkbox
            hair.modifiers[0]["Input_39"] = False  # deactivate custom material
            hair.modifiers[0]["Input_86"] = hoverobj.modifiers[0]["Input_86"]  # slope
            hair.modifiers[0]["Input_89"] = hoverobj.modifiers[0]["Input_89"]  # slope inverted
            hair.modifiers[0]["Input_91"] = hoverobj.modifiers[0]["Input_91"]  # height
            hair.modifiers[0]["Input_92"] = hoverobj.modifiers[0]["Input_92"]  # height inverted
            # hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] = hoverobj.modifiers["GeometryNodes"]["Input_83_use_attribute"]     #weight group
            # hair.modifiers["GeometryNodes"]["Input_83_attribute_name"] = hoverobj.modifiers["GeometryNodes"]["Input_83_attribute_name"]    #weight attribute
            # hair.modifiers["GeometryNodes"]["Input_95"] = hoverobj.modifiers["GeometryNodes"]["Input_95"]        #mask object
            # hair.modifiers["GeometryNodes"]["Input_98"] = hoverobj.modifiers["GeometryNodes"]["Input_98"]        #mask viewport checkbox
            # hair.modifiers["GeometryNodes"]["Input_97"] = hoverobj.modifiers["GeometryNodes"]["Input_97"] #mask viewpoer
            hair.location = hair.location

        # if only 2 curves, reselect original
        if N_Of_Selected == 2:
            bpy.context.active_object.select_set(False)
            for obj in bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = obj


    # switch even multiple hair, use all non hair objs to switch to collection or a single obj
    elif N_Of_Selected >= 3:
        print("switch even multiple hair, use all non hair objs to switch to collection or a single", )

        # ALL MATERIALS FROM NON HAIR OBJS
        all_materials_from_non_hair_objs = []
        for ob in all_selected_non_hair:  # make mats linked to obj and local
            for mat in _secret_paint_collect_safe_materials_from_object(ob, material_cache):
                if mat not in all_materials_from_non_hair_objs: all_materials_from_non_hair_objs.append(mat)

        if len(all_selected_non_hair) >= 2:
            # FIND COLLECTION FROM ONE OF THE NON HAIR OBJS
            ucol = randomselected_non_hair.users_collection
            for i in ucol:
                layer_collection = bpy.context.view_layer.layer_collection
                layerColl = recurLayerCollection(layer_collection, i.name)

            for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
            for hair in all_selected_hair:
                # MATERIALS
                hair.active_material_index = 0
                _secret_paint_replace_curve_materials_from_sources(hair, all_materials_from_non_hair_objs)

                hair.modifiers[0]["Input_2"] = None
                hair.modifiers[0]["Input_9"] = bpy.data.collections[layerColl.name]
                hair.modifiers[0]["Input_39"] = False  # deactivate custom material

                # bpy.data.objects[hair.name].select_set(True)  # select it
                bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  # make active
                bpy.ops.object.mode_set(mode=current_mode)
                hair.location = hair.location

        elif len(all_selected_non_hair) == 1:
            for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)

            # all_materials=[]
            # for mat_slot in all_selected_non_hair[0].material_slots:
            #     mat = mat_slot.material
            #     if mat not in all_materials: all_materials.append(mat)

            for hair in all_selected_hair:
                hair.modifiers[0]["Input_2"] = bpy.data.objects[all_selected_non_hair[0].name]
                hair.modifiers[0]["Input_9"] = None
                hair.modifiers[0]["Input_39"] = False  # deactivate custom material
                # if bpy.data.objects[all_selected_non_hair[0].name].dimensions[0] > \
                #         bpy.data.objects[all_selected_non_hair[0].name].dimensions[1]:
                #     density_large = 0.5/( (bpy.data.objects[all_selected_non_hair[0].name].dimensions[0])/2 / \
                #                     bpy.data.objects[all_selected_non_hair[0].name].scale[0])
                # else:
                #     density_large = 0.5/( (bpy.data.objects[all_selected_non_hair[0].name].dimensions[1])/2 / \
                #                     bpy.data.objects[all_selected_non_hair[0].name].scale[1])
                # hair.modifiers["GeometryNodes"]["Input_68"] = density_large  # DENSITY SCATTER

                # bpy.data.objects[hair.name].select_set(True)  # select it
                bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  # make active
                bpy.ops.object.mode_set(mode=current_mode)

                hair.active_material_index = 0  # CLEAN MATERIALS
                _secret_paint_replace_curve_materials_from_sources(hair, all_materials_from_non_hair_objs)
                hair.location = hair.location


        # bpy.ops.transform.translate(value=(0, 0, 0))  # best way to update the scene
    # for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
    # # for x in saveactual_objselection: x.select_set(True)
    # bpy.context.view_layer.objects.active = saveactual_activeobj
    # bpy.ops.object.mode_set(mode=current_mode)

    # return{'FINISHED'}
class orencurveswitch(bpy.types.Operator):
    """Use the active mesh or collection as Brush for the selected Paint System"""
    bl_idname = "secret.paintbrushswitch"
    bl_label = "Switch"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        try:
            from . import secret_paint_world_paint
            if secret_paint_world_paint.is_world_paint_running():
                if secret_paint_world_paint.is_world_paint_event_in_view(context, event):
                    if secret_paint_world_paint.switch_active_system_brush_under_mouse(context, event):
                        return {'FINISHED'}
                    return {'CANCELLED'}
        except Exception:
            pass
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):      #reference:  orenscatter_modal_operator(bpy.types.Operator)
        paintbrushswitch_f(self, context, event)
        return{'FINISHED'}

def check_overlapping_uvs(self,context,**kwargs):
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object

    # if activeobj.type != 'MESH': return print("Active object is not a mesh.")  # Ensure it's a mesh
    if activeobj.type != 'MESH': return False

    mesh = activeobj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active  # Get the active UV layer
    if not uv_layer:
        print("No active UV map found.")  # Ensure a UV map exists
        return

    face_uv_sets = {}  # Dictionary to track UV sets of faces
    overlapping_faces = set()  # Set to collect overlapping face indices

    for face in bm.faces:
        uv_set = frozenset(tuple(loop[uv_layer].uv) for loop in face.loops)  # Get unique UVs for the face
        if uv_set in face_uv_sets:
            overlapping_faces.add(face.index)  # Add the current face index
            overlapping_faces.add(face_uv_sets[uv_set])  # Add the face it overlaps with
        else:
            face_uv_sets[uv_set] = face.index  # Store UV set and face index

    if overlapping_faces:
        # print(f"Overlapping UVs found on faces: {sorted(overlapping_faces)}")  # Print result
        print(f"Overlapping UVs found on faces")  # Print result
        bm.free()  # Free the BMesh
        return True
    else:
        print("No overlapping UVs detected.")  # Print result
        bm.free()  # Free the BMesh
        return False

    # #FASTER VERSION
    # if activeobj.type != 'MESH': return print("Active object is not a mesh.")  # Ensure it's a mesh
    #
    # mesh = activeobj.data
    # bm = bmesh.new()
    # bm.from_mesh(mesh)
    # uv_layer = bm.loops.layers.uv.active  # Get the active UV layer
    # if not uv_layer: return print("No active UV map found.")  # Ensure a UV map exists
    #
    # face_uv_hashes = {}  # Dictionary to track hashed UV sets of faces
    # overlapping_faces = set()  # Set to collect overlapping face indices
    #
    # for face in bm.faces:
    #     uv_set = tuple(sorted(tuple(loop[uv_layer].uv) for loop in face.loops))  # Create a sorted tuple of UVs
    #     uv_hash = hash(uv_set)  # Hash the UV set for faster lookup
    #     if uv_hash in face_uv_hashes:
    #         overlapping_faces.add(face.index)  # Add the current face index
    #         overlapping_faces.add(face_uv_hashes[uv_hash])  # Add the face it overlaps with
    #     else:
    #         face_uv_hashes[uv_hash] = face.index  # Store UV hash and face index
    #
    # if overlapping_faces:
    #     # print(f"Overlapping UVs found on faces: {sorted(overlapping_faces)}")  # Print result
    #     print("Overlapping UVs found on faces:")  # Print result
    #     bm.free()  # Free the BMesh
    #     return True
    # else:
    #     print("No overlapping UVs detected.")  # Print result
    #     bm.free()  # Free the BMesh
    #     return False



def Check_if_trigger_UV_Reprojection(self,context,**kwargs):
    pickup_trace = _get_pickup_trace()
    auto_uv_total_start = time.perf_counter()
    trigger_auto_uvs = _secret_paint_pref("trigger_auto_uvs", 150000)

    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    objselection = kwargs.get("objselection") if "objselection" in kwargs else bpy.context.selected_objects
    if not isinstance(objselection, (list, tuple)): objselection = [objselection]  #CONVERT TO A LIST IF IT'S A SINGLE OBJ
    if activeobj not in objselection: objselection.append(activeobj)
    if trigger_auto_uvs <= 0:
        if pickup_trace:
            pickup_trace.action("auto_uv.total", auto_uv_total_start, detail="disabled_by_preference")
        return{'FINISHED'}

    # print("OOOOOOOOO",activeobj, objselection)
    # context = None
    # event = None
    # for i in args:
    #     if type(i).__name__ == "Context": context = i
    #     elif type(i).__name__ == "Event": event = i

    # current_mode = bpy.context.object.mode
    # hairlist = []
    # unselected_siblings_list = []
    surface_to_reUV = []
    collect_surfaces_start = time.perf_counter()
    # IF ITS A CURVE, GET SIBLINGS FROM PARENT. IF IT'S A MESH: GET CHILDREN
    for obj in objselection:
        if obj.type == "CURVES":
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    # if obj not in hairlist: hairlist.append(obj)
                    if obj.parent and obj.parent.type == "MESH":
                        if obj.parent not in surface_to_reUV: surface_to_reUV.append(obj.parent)
                        # for child in obj.parent.children:
                        #     if child.type == "CURVES":
                        #         for modif in child.modifiers:  # modifier.name == "GeometryNodes"
                        #             if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                        #                 if child not in hairlist: hairlist.append(child)
                        #                 if child not in objselection and child not in unselected_siblings_list: unselected_siblings_list.append(child)


        elif obj.type == "MESH":
            if obj not in surface_to_reUV: surface_to_reUV.append(obj)
            # for child in obj.children:
            #     if child.type == "CURVES":
            #         for modif in child.modifiers:  # modifier.name == "GeometryNodes"
            #             if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint") and child not in hairlist: hairlist.append(child)
    if pickup_trace:
        pickup_trace.action("auto_uv.collect_surfaces", collect_surfaces_start, detail=f"surfaces={len(surface_to_reUV)}")

    for terrain in surface_to_reUV:
        terrain_scan_start = time.perf_counter()
        face_count = len(terrain.data.polygons)
        if pickup_trace:
            pickup_trace.action("auto_uv.face_count_scan", terrain_scan_start, label=terrain.name, detail=f"faces={face_count}")

        if face_count < trigger_auto_uvs:
            if _secret_paint_auto_uv_cache_matches(terrain.data):
                if pickup_trace:
                    pickup_trace.action("auto_uv.cached_uv_reuse", terrain_scan_start, label=terrain.name, detail=f"faces={face_count}")
                continue
            # reproject_function(self,context,automatically_triggererd=True,activeobj=activeobj, objselection=objselection)
            reproject_start = time.perf_counter()
            reproject_function(self,context,automatically_triggererd=True,activeobj=terrain, objselection=[terrain])
            if pickup_trace:
                pickup_trace.action("auto_uv.reproject_function", reproject_start, label=terrain.name, detail=f"faces={face_count}")
            # print("111111111")
            # if check_overlapping_uvs(self,context,activeobj=terrain) == True: #VERY SLOW TO PROCESS, twice as slow as reprojecting, so migh as well do that by default, MOMENTARILY FREEZER INTERFACE FOR HIGHPOLY
            # start_time = time.perf_counter()
            # end_time = time.perf_counter()
            # print("@@REPROJECT Milliseconds (Ping):",(end_time - start_time) * 1000)
            # print("#### TRIGGERED REPROJECTING UVS ###")

    if pickup_trace:
        pickup_trace.action("auto_uv.total", auto_uv_total_start, detail=f"surfaces={len(surface_to_reUV)}")
    return{'FINISHED'}
# def secret_paint_new_uvs(self,context,**kwargs):
#     if "activeobj" in kwargs:activeobj = kwargs.get("activeobj")
#     else:activeobj = bpy.context.active_object
#     if activeobj == None: activeobj = bpy.context.active_object
#     actual_activeobj=bpy.context.active_object
#
#     # context = None
#     # event = None
#     # for i in args:
#     #     if type(i).__name__ == "Context": context = i
#     #     elif type(i).__name__ == "Event": event = i
#
#     # SEARCH FOR THE CUSTOM UV AND THE CURRENTLY ACTIVE UV
#     previously_active_UV = None
#     previously_active_UV_rendering = None
#     custom_uv = None
#     for UV in activeobj.data.uv_layers:
#         if UV.active: previously_active_UV = UV  # saves performance: no need to set the active uv again if the custom auto uv was already the active one
#         if UV.active_render: previously_active_UV_rendering = UV  # saves performance: no need to set the active uv again if the custom auto uv was already the active one
#         if UV.name == "Secret Paint Auto UV": custom_uv = UV
#
#     uv_to_reproject = previously_active_UV_rendering
#
#
#     if activeobj.data.library:
#         self.report({'INFO'}, "Snapped the hair to the closest surface, but couldn't create new UVs since the object's geometry is linked from another .Blend file")
#
#     else:
#
#         bpy.context.view_layer.objects.active = activeobj #make active the one that needs to be edited
#
#         #CREATE IT IF NECESSARY
#         if custom_uv==None: custom_uv = activeobj.data.uv_layers.new(name="Secret Paint Auto UV")
#
#         ####### IF THE CUSTOM UV IS STILL "NONE" IS BECAUSE IT COULDN'T BE CREATED SINCE THERE WERE ALREADY 8 UVS, BLENDER OBJECTS LIMITATION
#         if custom_uv == None: uv_to_reproject = previously_active_UV_rendering
#         else: uv_to_reproject = custom_uv
#
#
#         #CHANGE ACTIVE UV BEFORE REPROJECTING
#         changed_active_uv_so_restore_is_needed = False
#         if previously_active_UV != uv_to_reproject:
#             # print("22222222",previously_active_UV.name,"<previous .  changing active UV, uv to reproj:", uv_to_reproject.name)
#             uv_to_reproject.active=True #only need to activate it if there was another active UV
#             changed_active_uv_so_restore_is_needed =True
#
#         #AUTO REPROJECT THE ACTIVE UV
#         bpy.context.view_layer.objects.active = activeobj
#         for x in bpy.context.selected_objects: x.select_set(False)
#         for window in context.window_manager.windows:
#             screen = window.screen
#             for area in screen.areas:
#                 if area.type == 'VIEW_3D':
#                     with context.temp_override(window=window, area=area):
#                         # bpy.ops.uv.smart_project(angle_limit=1.20428, island_margin=0.01, area_weight=1, correct_aspect=True, scale_to_bounds=True)
#                         restoremode = bpy.context.object.mode
#                         if restoremode != "EDIT": bpy.ops.object.mode_set(mode="EDIT")
#                         bpy.ops.mesh.select_all(action='SELECT')
#                         bpy.ops.uv.smart_project(angle_limit=1.20428, island_margin=0.01, area_weight=1, correct_aspect=True, scale_to_bounds=True)
#                         # bpy.ops.uv.smart_project(angle_limit=1.7, island_margin=0.1, area_weight=1, correct_aspect=True, scale_to_bounds=True)
#                         if restoremode != "EDIT": bpy.ops.object.mode_set(mode=restoremode)
#                         # self.report({'INFO'}, "Smart UV Project 2")
#                     break
#         bpy.context.view_layer.objects.active = actual_activeobj
#
#         if changed_active_uv_so_restore_is_needed and previously_active_UV:
#             previously_active_UV.active=True #restore previously active uv (only if it wasn't the custom uv, just to save performance) doesn't need to restore anything if there were no UVS before this function was executed
#             # print("KKKKKKKKKKKKKKK",previously_active_UV.name,previously_active_UV.active)
#
#
#     return uv_to_reproject
def reproject_function(self,context,**kwargs):
    start_time = time.perf_counter()

    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    objselection = kwargs.get("objselection") if "objselection" in kwargs else bpy.context.selected_objects
    if not isinstance(objselection, (list, tuple)): objselection = [objselection]  #CONVERT TO A LIST IF IT'S A SINGLE OBJ
    if activeobj not in objselection: objselection.append(activeobj)
    automatically_triggererd = kwargs.get("automatically_triggererd") if "automatically_triggererd" in kwargs else False


    actualobjselection = bpy.context.selected_objects
    actualactiveobj = bpy.context.active_object
    changed_active_obj_so_restore_is_needed = False
    changed_selected_objs_so_restore_is_needed = False

    # context = None
    # event = None
    # for i in args:
    #     if type(i).__name__ == "Context": context = i
    #     elif type(i).__name__ == "Event": event = i

    current_mode = bpy.context.object.mode
    dyntopo_status = activeobj.use_dynamic_topology_sculpting
    hairlist = []
    unselected_siblings_list = []
    surface_to_reUV = []

    # IF ITS A CURVE, GET SIBLINGS FROM PARENT. IF IT'S A MESH: GET CHILDREN
    for obj in objselection:
        if obj.type == "CURVES":
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    if obj not in hairlist: hairlist.append(obj)
                    if obj.parent and obj.parent.type == "MESH":
                        if obj.parent not in surface_to_reUV: surface_to_reUV.append(obj.parent)
                        for child in obj.parent.children:
                            if child.type == "CURVES":
                                for modif in child.modifiers:  # modifier.name == "GeometryNodes"
                                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                        if child not in hairlist: hairlist.append(child)
                                        if child not in objselection and child not in unselected_siblings_list: unselected_siblings_list.append(child)


        elif obj.type == "MESH":
            if obj not in surface_to_reUV: surface_to_reUV.append(obj)
            for child in obj.children:
                if child.type == "CURVES":
                    for modif in child.modifiers:  # modifier.name == "GeometryNodes"
                        if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint") and child not in hairlist: hairlist.append(child)

    ########################################











    ########  CREATE NEW UVS  ########   (changes active object and selection)

    if surface_to_reUV:
        for surface in surface_to_reUV:
            # secret_paint_new_uvs(self, context, activeobj=surface)

            # SEARCH FOR THE CUSTOM UV AND THE CURRENTLY ACTIVE UV
            previously_active_UV = None
            previously_active_UV_rendering = None
            custom_uv = None
            for UV in surface.data.uv_layers:
                if UV.active: previously_active_UV = UV  # saves performance: no need to set the active uv again if the custom auto uv was already the active one
                if UV.active_render: previously_active_UV_rendering = UV  # saves performance: no need to set the active uv again if the custom auto uv was already the active one
                if UV.name == SECRET_PAINT_AUTO_UV_NAME: custom_uv = UV

            uv_to_reproject = previously_active_UV_rendering

            #CAN'T CREATE NEW UVS IF THE MESH DATA IS LINKED
            if surface.data.library:
                if not automatically_triggererd: self.report({'INFO'}, "Snapped the hair to the closest surface, but couldn't create new UVs since the object's geometry is linked from another .Blend file")

            else:

                # CREATE IT IF NECESSARY
                if custom_uv == None: custom_uv = surface.data.uv_layers.new(name=SECRET_PAINT_AUTO_UV_NAME)

                ####### IF THE CUSTOM UV IS STILL "NONE" IS BECAUSE IT COULDN'T BE CREATED SINCE THERE WERE ALREADY 8 UVS, BLENDER OBJECTS LIMITATION
                if custom_uv == None:
                    uv_to_reproject = previously_active_UV_rendering
                else:
                    uv_to_reproject = custom_uv

                if automatically_triggererd:
                    try:
                        _secret_paint_fast_reproject_surface_uvs(surface)
                    except:
                        print("FAILED TO FAST REPROJECT THE UV")
                    custom_uv = surface.data.uv_layers.get(SECRET_PAINT_AUTO_UV_NAME)
                    if custom_uv:
                        uv_to_reproject = custom_uv
                else:
                    # CHANGE ACTIVE UV BEFORE REPROJECTING
                    changed_active_uv_so_restore_is_needed = False
                    if previously_active_UV != uv_to_reproject:
                        # print("22222222",previously_active_UV.name,"<previous .  changing active UV, uv to reproj:", uv_to_reproject.name)
                        uv_to_reproject.active = True  # only need to activate it if there was another active UV
                        changed_active_uv_so_restore_is_needed = True

                    # AUTO REPROJECT THE ACTIVE UV
                    # bpy.context.view_layer.objects.active = activeobj
                    # for x in bpy.context.selected_objects: x.select_set(False)
                    print("REPROJIIIIIII", surface)
                    manual_reproject_succeeded = False
                    try:   # FAILS WHEN PAINTING FROM THE ASSET LIBRARY
                        for window in context.window_manager.windows:
                            screen = window.screen
                            for area in screen.areas:
                                if area.type == 'VIEW_3D':
                                    with context.temp_override(window=window, area=area):
                                        for x in actualobjselection: x.select_set(False)
                                        changed_selected_objs_so_restore_is_needed = True
                                        if bpy.context.active_object != surface:
                                            bpy.context.view_layer.objects.active = surface  # make active the one that needs to be edited
                                            changed_active_obj_so_restore_is_needed =True
                                        # bpy.ops.uv.smart_project(angle_limit=1.20428, island_margin=0.01, area_weight=1, correct_aspect=True, scale_to_bounds=True)
                                        restoremode = bpy.context.object.mode
                                        if restoremode != "EDIT": bpy.ops.object.mode_set(mode="EDIT")
                                        bpy.ops.mesh.select_all(action='SELECT')
                                        bpy.ops.uv.smart_project(angle_limit=1.20428, island_margin=0.01, area_weight=1, correct_aspect=True, scale_to_bounds=True)
                                        # bpy.ops.uv.smart_project(angle_limit=1.7, island_margin=0.1, area_weight=1, correct_aspect=True, scale_to_bounds=True)
                                        if restoremode != "EDIT": bpy.ops.object.mode_set(mode=restoremode)
                                        # self.report({'INFO'}, "Smart UV Project 2")
                                    break
                        manual_reproject_succeeded = True
                    except: print("FAILED TO REPROJECT THE UV")

                    if manual_reproject_succeeded:
                        _secret_paint_store_auto_uv_cache(surface.data)

                    # if changed_active_uv_so_restore_is_needed and previously_active_UV:
                    #     previously_active_UV.active = True  # restore previously active uv (only if it wasn't the custom uv, just to save performance) doesn't need to restore anything if there were no UVS before this function was executed
                    #     # print("KKKKKKKKKKKKKKK",previously_active_UV.name,previously_active_UV.active)

                    # previously_active_UV_rendering.active = True  #CREATING NEW UVS INVALIDATES THE UV VARIABLES PREVIOUSLY SAVED???????? FOR NOW BRUTE FORCE CYCLE THROUGH AND ACTIVATE
                    for UVV in surface.data.uv_layers:
                        if UVV.active_render:
                            UVV.active = True
                            break

            # if changed_active_uv_so_restore_is_needed and previously_active_UV:
            #     previously_active_UV.active = True  # restore previously active uv (only if it wasn't the custom uv, just to save performance) doesn't need to restore anything if there were no UVS before this function was executed
            #     # print("KKKKKKKKKKKKKKK",previously_active_UV.name,previously_active_UV.active)








    if hairlist:

        # RESET SURFACE HAIR FROM PARENT
        for ob in hairlist:
            ob.data.surface = ob.parent

            # RESET UVS
            active_render_UV = None
            custom_uv = None
            for uvmap in ob.data.surface.data.uv_layers:  # bpy.context.object.data.uv_layers['UVMap.001'].active = True
                if uvmap.name == SECRET_PAINT_AUTO_UV_NAME: custom_uv = uvmap.name
                if uvmap.active_render: active_render_UV = uvmap.name
            if custom_uv:
                ob.data.surface_uv_map = custom_uv
            elif active_render_UV:
                ob.data.surface_uv_map = active_render_UV


        #SNAP HAIR TO CLOSEST SURFACE (changes active object and selection)    (only if called manually. don't want to snap hair automatically)
        # if not automatically_triggererd:
        for x in objselection: bpy.data.objects[x.name].select_set(False)
        changed_selected_objs_so_restore_is_needed = True
        loop = 0
        for ob in hairlist:
            if ob not in unselected_siblings_list:
                if loop == 0:
                    bpy.context.view_layer.objects.active = ob
                    changed_active_obj_so_restore_is_needed = True
                loop+=1 #only change active object once to optimize

                bpy.data.objects[ob.name].select_set(True)
                bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
        # RESTORE SELECTION
        # for x in objselection: bpy.data.objects[x.name].select_set(True)
        # if activeobj != bpy.context.view_layer.objects.active: bpy.context.view_layer.objects.active = activeobj



    #RESTORE SELECTION and ACTIVE OBJ
    if not automatically_triggererd:
        if current_mode == "SCULPT_CURVES":
            for ob in hairlist: ob.select_set(False)
        elif current_mode == "SCULPT":
            if dyntopo_status: bpy.ops.sculpt.dynamic_topology_toggle()
            for ob in hairlist: ob.select_set(False)


    else:
        if changed_active_obj_so_restore_is_needed: bpy.context.view_layer.objects.active = actualactiveobj
        if changed_selected_objs_so_restore_is_needed:
            # for xx in actualobjselection: xx.select_set(False)
            for ob in bpy.context.selected_objects:
                if ob not in actualobjselection: ob.select_set(False)
            for xx in actualobjselection: xx.select_set(True)

    # for UVV in surface.data.uv_layers:
    #     UVV.active = True


    # APPLYING SCALE AT LOW LEVEL HAS STRANGE EFFECT ON SCALE, PROBABLY BECAUSE OF REFERENCE MATRIX
    # mw = ob.matrix_world
    # mb = ob.matrix_basis
    # loc, rot, scale = mb.decompose()
    # # rotation
    # T = Matrix.Translation(loc)
    # R = rot.to_matrix().to_4x4()
    # S = Matrix.Diagonal(scale).to_4x4()
    #
    # if hasattr(ob.data, "transform"):
    #     # ob.data.transform(R)
    #     ob.data.transform(S)
    #
    # for c in ob.children:
    #     # c.matrix_local = R @ c.matrix_local
    #     c.matrix_local = S @ c.matrix_local
    #
    # # ob.matrix_basis = T @ S
    # ob.matrix_basis = R @ T

    # bpy.ops.object.select_all(action='DESELECT')
    # RESTORE SELECTION
    # bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]  # make active
    # bpy.data.objects[activeobj.name].select_set(True)
    # for x in objselection:  # for x in bpy.context.selected_objects:
    #     bpy.data.objects[x.name].select_set(True)

    end_time = time.perf_counter()

    print(f"@@@ Reprojected UVs: reproject_function,snap hair to closest surface:{not automatically_triggererd}", "Milliseconds:",(end_time - start_time) * 1000)
    # self.report({'INFO'}, "Reprojected UVs")  # need to add (self, context) in the function
    return {'FINISHED'}
class clean_hair_orencurve(bpy.types.Operator):
    """When the terrain has incorrect UVs, for example after sculpting the terrain with dynamic topology, use this to quickly recreate the UVs. This is needed in order to be able to paint manually (geometry node hair limitation; only needed for manual painting, not for the procedural distribution). Also snaps hair to the closest surfaces"""
    bl_idname = "secret.fixdyntopo"
    bl_label = "Reproject"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        reproject_function(self, context)
        return {'FINISHED'}
def context283482(self,context,**kwargs):    #### orengroup ###


    if "coll_target" in kwargs:
        Importing_Into_Active = True
        coll_target = kwargs.get("coll_target")
    else:
        Importing_Into_Active = False
        coll_target = None

    activeobj = bpy.context.active_object
    objs = bpy.context.selected_objects



    # for window in context.window_manager.windows:
    #     screen = window.screen
    #     for area in screen.areas:
    #         if area.type == 'VIEW_3D':
    #             with context.temp_override(window=window, area=area):

    # List of object references
    if Importing_Into_Active:
        objs.remove(activeobj) #avoid reprocessing the active object if we're just bringing other objects into the active's collection
        activeobj.select_set(False)


    # # fix axis brush obj for selected objects
    # for x in bpy.context.selected_objects:
    #     x.track_axis = 'POS_Z'
    # # x is replacing:   bpy.context.object

    # if bpy.context.view_layer.objects.active == None:
    #     for x in bpy.context.selected_objects:
    #         bpy.context.view_layer.objects.active = x


    # save name of active obect to rename collection later
    orengroupfirst = bpy.context.active_object
    orengroupfirstName = orengroupfirst.name

    # # cursor to active object
    # bpy.ops.view3d.snap_cursor_to_active()

    # select collection that contains current active object // just use active collection for now
    C = bpy.context
    active_coll = C.view_layer.active_layer_collection.collection

    # # save name of active collection for instancing later
    # reselparentcoll = bpy.context.view_layer.active_layer_collection
    # #other method
    # #colselection1=bpy.context.view_layer.active_layer_collection.collection
    # #colselection1Name = bpy.data.collections.get(colselection1.name)
    # #print(colselection1Name)

    if Importing_Into_Active == False:
        coll_target = bpy.data.collections.new(orengroupfirstName) # create children collection named as active object  #orengroupfirstnewcoll
        active_coll.children.link(coll_target) # link collection to make it appear in the parent

        # #select orengroupfirstnewcoll as active collection
        # bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.active_layer_collection.children[orengroupfirstnewcoll.name]

        # coll_target = bpy.context.collection          # Set target collection based on the collection in context (selected)
        #  = orengroupfirstnewcoll          # Set target collection based on the collection in context (selected)
        #coll_target = C.scene.collection.children.get("new")  # other method: Set target collection to a known collection


    # If target found and object list not empty
    if coll_target and objs:

        # # Loop through all objects and their children
        # for ob in objs[:]:
        #     for children in ob.children_recursive:
        #         if children not in objs: objs.append(children)

        for ob in objs:
            for coll in ob.users_collection:
                coll.objects.unlink(ob) # Unlink the object
            coll_target.objects.link(ob) # Link each object to the target collection
            ob.select_set(True)







    # # RECENTER COLLECTION INSTANCES
    # if Importing_Into_Active == False: orengrouprecentercollectionobj_function(context, objselection=objs)

    # # set instance offset from cursor, force outliner context command?
    # #bpy.ops.object.instance_offset_from_cursor
    # bpy.data.collections[orengroupfirstnewcoll.name].instance_offset[0] = bpy.context.scene.cursor.location[0]
    # bpy.data.collections[orengroupfirstnewcoll.name].instance_offset[1] = bpy.context.scene.cursor.location[1]
    # bpy.data.collections[orengroupfirstnewcoll.name].instance_offset[2] = bpy.context.scene.cursor.location[2]




    # # reselect original coll as active collection
    # bpy.context.view_layer.active_layer_collection = reselparentcoll


    # #reselect original object
    # bpy.context.view_layer.objects.active = bpy.data.objects[orengroupfirstName]
    # bpy.data.objects[orengroupfirstName].select_set(True)





    # if context.scene.mypropertieslist.checkboxorengroupinstance:  #INSTANCE COLL WHILE GROUPING
    #
    #
    #     # create and select collection instance
    #     source_collection = bpy.data.collections[orengroupfirstnewcoll.name]
    #     instance_obj = bpy.data.objects.new(name=orengroupfirstName, object_data=None)
    #     instance_obj.location = bpy.context.scene.cursor.location # snap to cursor
    #     instance_obj.instance_collection = source_collection
    #     instance_obj.instance_type = 'COLLECTION'
    #     parent_collection = bpy.context.view_layer.active_layer_collection
    #     parent_collection.collection.objects.link(instance_obj)
    #
    #     # deselect all objs
    #     bpy.ops.object.select_all(action='DESELECT')
    #     # select instance object
    #     # bpy.context.view_layer.objects.active = bpy.data.objects[orengroupfirstnewcoll.name]
    #     # instance_obj.select_set(True)
    #     bpy.data.objects[instance_obj.name].select_set(True) #select it
    #     bpy.context.view_layer.objects.active = bpy.data.objects[instance_obj.name]  #make active
    #
    #     # enter translate mode
    #     # bpy.ops.transform.translate('INVOKE_DEFAULT')
    #
    #     ### end of orengroup ###
    #
    #     bpy.data.objects[instance_obj.name].location = (orengroupfirst.location[0], orengroupfirst.location[1], orengroupfirst.location[2]+orengroupfirst.dimensions[2])

# break
    self.report({'INFO'}, "Added to collection of active")

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
def _tool_settings_from_context(context):
    scene = getattr(context, "scene", None)
    if scene == None:
        scene = getattr(bpy.context, "scene", None)
    return getattr(scene, "tool_settings", None)


def _set_weight_paint_value(context, value):
    # Blender has moved this value between tool settings and the active brush across versions.
    tool_settings = _tool_settings_from_context(context)
    if tool_settings == None:
        return False

    updated = False

    if hasattr(tool_settings, "vertex_group_weight"):
        tool_settings.vertex_group_weight = value
        updated = True

    unified_settings = getattr(tool_settings, "unified_paint_settings", None)
    if unified_settings != None and hasattr(unified_settings, "weight"):
        unified_settings.weight = value
        updated = True

    weight_paint = getattr(tool_settings, "weight_paint", None)
    brush = getattr(weight_paint, "brush", None)
    if brush != None and hasattr(brush, "weight"):
        brush.weight = value
        updated = True

    return updated


def _get_weight_paint_value(context, default=1.0):
    tool_settings = _tool_settings_from_context(context)
    if tool_settings == None:
        return default

    if hasattr(tool_settings, "vertex_group_weight"):
        return tool_settings.vertex_group_weight

    unified_settings = getattr(tool_settings, "unified_paint_settings", None)
    if unified_settings != None and hasattr(unified_settings, "weight"):
        return unified_settings.weight

    weight_paint = getattr(tool_settings, "weight_paint", None)
    brush = getattr(weight_paint, "brush", None)
    if brush != None and hasattr(brush, "weight"):
        return brush.weight

    return default


def brush_vertex_paint(activeobj,objselection,vertex_group,context):
    # print(vertex_group)
    pickup_trace = _get_pickup_trace()
    brush_vertex_paint_start = time.perf_counter()
    mode_set_start = time.perf_counter()
    bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    if pickup_trace:
        pickup_trace.action("brush_vertex_paint.mode_set_weight_paint", mode_set_start, detail=f"group={vertex_group}")
    tool_set_start = time.perf_counter()
    bpy.ops.wm.tool_set_by_id(name="builtin_brush.Draw")
    if pickup_trace:
        pickup_trace.action("brush_vertex_paint.set_draw_brush", tool_set_start)
    set_weight_start = time.perf_counter()
    _set_weight_paint_value(context, 1)
    if pickup_trace:
        pickup_trace.action("brush_vertex_paint.set_weight_value", set_weight_start)
    set_group_start = time.perf_counter()
    bpy.ops.object.vertex_group_set_active(group=vertex_group)  # bpy.context.scene.tool_settings.vertex_group_weight = surfaceobj.vertex_groups.get(biomename).index
    if pickup_trace:
        pickup_trace.action("brush_vertex_paint.set_active_group", set_group_start, detail=f"group={vertex_group}")
    # active_object.vertex_groups.active.name
    # bpy.ops.object.vertex_group_set_active(group="Biome1")  # bpy.context.scene.tool_settings.vertex_group_weight = surfaceobj.vertex_groups.get(biomename).index

    activeobj.modifiers[0]["Input_69"] = True  # ENABLE NOISE SCATTER
    activeobj.location = activeobj.location  # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))
    if pickup_trace:
        pickup_trace.action("brush_vertex_paint.total", brush_vertex_paint_start, detail=f"group={vertex_group}; active={activeobj.name if activeobj else 'None'}")
def vertexgrouppaint_function(self,context,NoMasksDetected=True,calledfrombutton=False, being_transferred_to_newmesh=False,**kwargs):
    # print("JOOOOOOOOOOOOOOOOOOOOOO",NoMasksDetected)
    pickup_trace = _get_pickup_trace()
    vertexgrouppaint_start = time.perf_counter()
    if bpy.context.object.mode != "OBJECT":
        mode_set_object_start = time.perf_counter()
        bpy.ops.object.mode_set(mode="OBJECT")
        if pickup_trace:
            pickup_trace.action("vertexgrouppaint.mode_set_object", mode_set_object_start)
    if "activeobj" in kwargs: activeobj = kwargs.get("activeobj")
    else: activeobj = bpy.context.active_object
    if activeobj==None: activeobj = bpy.context.active_object

    if "objselection" in kwargs: objselection = kwargs.get("objselection")
    else: objselection = bpy.context.selected_objects
    if activeobj not in objselection: objselection.append(activeobj)

    if "called_for_entire_biome" in kwargs: called_for_entire_biome = kwargs.get("called_for_entire_biome")
    else: called_for_entire_biome = False

    #when called from button: if the button references an object that was not selected or active: disregard selection and just use the row object
    if called_for_entire_biome == False: #IGNORE WHEN CALLED FOR THE ENTIRE BIOME (hair_in_bgroup[0] might not correspond with actual active object)
        if activeobj != bpy.context.active_object and activeobj not in bpy.context.selected_objects: objselection = [activeobj]


    if "remove_vgroup" in kwargs: remove_vgroup = kwargs.get("remove_vgroup")
    else: remove_vgroup = False

    if "paint_the_vertex" in kwargs: paint_the_vertex = kwargs.get("paint_the_vertex")
    else: paint_the_vertex = True

    # objselection = bpy.context.selected_objects
    # activeobj = bpy.context.active_object  #   bpy.data.objects["armature"]     bpy.context.object["armature"]     <bpy_struct, Object("left") at 0x000001C2D10E5608>


    # if activeobj.type=="CURVES": surfaceobj = activeobj.data.surface
    # else: surfaceobj = activeobj
    if activeobj.type!="CURVES":
        self.report({'WARNING'}, "Active object is not a hair curve")
        return {"CANCELLED"}
    surfaceobj = activeobj.parent   #.data.surface

    biomeofactive=activeobj.modifiers[0]["Input_83_attribute_name"]
    if biomeofactive and being_transferred_to_newmesh == False: vertex_ofParent=surfaceobj.vertex_groups.get(biomeofactive).name #when transferring to a new mesh: the vertex group of the terrain will not match the hair
    else: vertex_ofParent=[]

    only_hair_from_selected=[]
    all_vertex_groups=[]
    collect_selection_start = time.perf_counter()
    for ob in objselection:
        if ob.type=="CURVES":
            if ob.modifiers:
                for modif in ob.modifiers:
                    if modif.type == 'NODES':  # modifier.name == "GeometryNodes"
                        if modif.node_group:
                            if modif.node_group.name == "Secret Paint":
                                only_hair_from_selected.append(ob)
                                if modif["Input_83_attribute_name"] and modif["Input_83_attribute_name"] not in all_vertex_groups: all_vertex_groups.append(modif["Input_83_attribute_name"])
    if pickup_trace:
        pickup_trace.action(
            "vertexgrouppaint.collect_selection",
            collect_selection_start,
            detail=f"selected_hair={len(only_hair_from_selected)}; vertex_groups={len(all_vertex_groups)}; remove={remove_vgroup}; transfer={being_transferred_to_newmesh}",
        )
    #############################################################################################

    #TRANSFERRED BIOME, deal with vertex groups
    if being_transferred_to_newmesh:
        # print("---------vertexgrouppaint_functin TRANSFERRRR")

        if all_vertex_groups: #if there are any vertex groups
            sameVgroup_forAllHair = True
            for vgroup in all_vertex_groups:

                # create vgroup incrementally, with all vertex assigned
                numb = 1
                while surfaceobj.vertex_groups.get("Biome" + str(numb)): numb += 1
                biomename = "Biome" + str(numb)
                new_vertex_group = surfaceobj.vertex_groups.new(name=biomename)
                for i in range(len(surfaceobj.data.vertices)):
                    new_vertex_group.add([i], 1.0, 'REPLACE')

                loopN=1
                for hair in only_hair_from_selected[:]:
                # for hair in only_hair_from_selected:
                    loopN += 1
                    if vgroup == hair.modifiers[0]["Input_83_attribute_name"]:

                        hair.modifiers[0]["Input_83_attribute_name"] = biomename
                        hair.modifiers[0]["Input_69"] = True

                        if hair.modifiers[0]["Input_83_use_attribute"] == False: hair.modifiers[0]["Input_83_use_attribute"] =True #1 # TURN ON ATTRIBUTE
                        # if hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] == False:  # TURN ON ATTRIBUTE
                        #     bpy.data.objects[hair.name].select_set(True)
                        #     bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  # make active
                        #     bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")  # hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] = True
                        hair.location = hair.location  # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))
                        only_hair_from_selected.remove(hair) #remove processed hair from list for future vgroup loops, possiblity of overlapping names (biome1 gets created but it already existed in one of hair, so it worngfully matches with the newly created vgroup)
                    else: sameVgroup_forAllHair=False
            # print("KKKKKKKKKKKKKKKKKKKKKKK",)
            if sameVgroup_forAllHair and NoMasksDetected and paint_the_vertex:   #go to paint mode if all hair have same vgroup: and no masks detected
                bpy.data.objects[surfaceobj.name].select_set(True)
                bpy.context.view_layer.objects.active = surfaceobj #select terrain
                for i in range(len(surfaceobj.data.vertices)):
                    new_vertex_group.add([i], 0.0, 'REPLACE')
                brush_vertex_paint(activeobj, objselection, biomename, context)
        ############################variables






    #BUTTON: if one selected hair: remove vertex
    # elif calledfrombutton and len(objselection)==1 and activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"] and activeobj.modifiers["GeometryNodes"]["Input_69"]==True:       #activeobj.modifiers["GeometryNodes"]["Input_83_use_attribute"]:
    elif remove_vgroup:
        remove_vgroup_start = time.perf_counter()
        removed_vgroups=[]
        parent_of_hair=None
        for hair in only_hair_from_selected:
            if hair.modifiers[0]["Input_83_attribute_name"] and hair.modifiers[0]["Input_83_attribute_name"] not in removed_vgroups: removed_vgroups.append(hair.modifiers[0]["Input_83_attribute_name"])
            hair.modifiers[0]["Input_83_attribute_name"] = ""
            if hair.modifiers[0]["Input_83_use_attribute"] == True: hair.modifiers[0]["Input_83_use_attribute"] = False  # TURN OFF ATTRIBUTE
            hair.location = hair.location
            if hair.parent: parent_of_hair=hair.parent

        #CLEANUP UNUSED VGROUPS     # if parent_of_hair:
        all_Vgroups_used_in_biome=[]
        for child in parent_of_hair.children:
            if child.type == "CURVES" and child.modifiers or child.type == "CURVE" and child.modifiers:
                for modif in child.modifiers:  # modifier.name == "GeometryNodes"
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        if child.modifiers[0]["Input_83_attribute_name"] and child.modifiers[0]["Input_83_attribute_name"] not in all_Vgroups_used_in_biome: all_Vgroups_used_in_biome.append(child.modifiers[0]["Input_83_attribute_name"])
        for g in removed_vgroups:
            if g not in all_Vgroups_used_in_biome: parent_of_hair.vertex_groups.remove(parent_of_hair.vertex_groups.get(g))
        if pickup_trace:
            pickup_trace.action("vertexgrouppaint.remove_vgroup", remove_vgroup_start, detail=f"removed={len(removed_vgroups)}")








    #scatter Q SHORTCUT: vgroup NOT USED in modifier: create, share, paint
    elif activeobj.modifiers[0]["Input_83_use_attribute"]==False:
    # elif len(objselection) >=2 and activeobj.modifiers["GeometryNodes"]["Input_83_use_attribute"]==0: #and activeobj.modifiers["GeometryNodes"]["Input_69"]==False:
    # elif activeobj.modifiers["GeometryNodes"]["Input_83_use_attribute"]==0 and activeobj.modifiers["GeometryNodes"]["Input_69"]==True:
    #     print("---------vertexgrouppaint_functon 1111111111111111111")
        create_vgroup_start = time.perf_counter()
        #create vgroup
        numb = 1
        while surfaceobj.vertex_groups.get("Biome"+str(numb)): numb += 1
        biomename = "Biome"+str(numb)
        surfaceobj.vertex_groups.new(name=biomename)

        #assign it
        # print("ooooooooo",only_hair_from_selected)
        for hair in only_hair_from_selected:
             #TURN ON ATTRIBUTE
            hair.modifiers[0]["Input_83_attribute_name"] = biomename
            hair.modifiers[0]["Input_69"] = True
            if hair.modifiers[0]["Input_83_use_attribute"] == False: hair.modifiers[0]["Input_83_use_attribute"] = True  # TURN ON ATTRIBUTE
            # if hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] == False: #TURN ON ATTRIBUTE
            #     bpy.data.objects[hair.name].select_set(True)
            #     bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  # make active
            #     bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")   # hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] = True
            hair.location = hair.location  # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))

        # paint mode
        bpy.data.objects[surfaceobj.name].select_set(True)  # select it   #BONES bpy.data.objects[c.id_data.name].pose.bones[bone.name].bone.select = False
        bpy.context.view_layer.objects.active = surfaceobj  # make active
        brush_vertex_paint(activeobj,objselection,biomename, context)
        if pickup_trace:
            pickup_trace.action(
                "vertexgrouppaint.create_vgroup_and_paint",
                create_vgroup_start,
                detail=f"group={biomename}; assigned_hair={len(only_hair_from_selected)}",
            )

        #clean unassigned biomes by checking siblings?


    #scatter Q SHORTCUT: share active vgroup, paint
    elif len(all_vertex_groups) >= 1 and vertex_ofParent:
    # elif len(all_vertex_groups) >= 1 and activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"] and surfaceobj.vertex_groups.get(activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"]):
    # elif len(all_vertex_groups) >= 1 and surfaceobj.vertex_groups.get(activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"]):
    # elif len(all_vertex_groups) >= 1 and surfaceobj.vertex_groups.get(biomeofactive):
    #     print("---------vertexgrouppaint_funcion 222222222222")
        share_vgroup_start = time.perf_counter()

        #share vgroup from active (not needed if only one selected)
        if len(only_hair_from_selected)!=1:
            for hair in only_hair_from_selected:
                # hair.modifiers["GeometryNodes"]["Input_83_attribute_name"] = activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"]
                hair.modifiers[0]["Input_83_attribute_name"] = biomeofactive
                hair.modifiers[0]["Input_69"] = True
                if hair.modifiers[0]["Input_83_use_attribute"] == False: hair.modifiers[0]["Input_83_use_attribute"] = True  # TURN ON ATTRIBUTE
                # if hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] == False: #TURN ON ATTRIBUTE
                #     bpy.data.objects[hair.name].select_set(True)
                #     bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]  # make active
                #     bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")
                hair.location = hair.location  # best way to update the scene ;update scene        # bpy.ops.transform.translate(value=(0, 0, 0))

        # go to paint mode with the found vertex group
        # bpy.data.objects[surfaceobj.name].eselect_set(True)  # select it   #BONES bpy.data.objects[c.id_data.name].pose.bones[bone.name].bone.select = False
        for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
        bpy.context.view_layer.objects.active = surfaceobj  # make active
        # brush_vertex_paint(activeobj,objselection,activeobj.modifiers["GeometryNodes"]["Input_83_attribute_name"], context)
        brush_vertex_paint(activeobj,objselection,biomeofactive,context)
        if pickup_trace:
            pickup_trace.action(
                "vertexgrouppaint.share_vgroup_and_paint",
                share_vgroup_start,
                detail=f"group={biomeofactive}; selected_hair={len(only_hair_from_selected)}",
            )
            pickup_trace.action("vertexgrouppaint.total", vertexgrouppaint_start, detail=f"group={biomeofactive}; mode=share_existing")
        return {'FINISHED'}
    if pickup_trace:
        pickup_trace.action(
            "vertexgrouppaint.total",
            vertexgrouppaint_start,
            detail=f"group={biomeofactive if biomeofactive else 'none'}; created={bool(activeobj.modifiers[0]['Input_83_use_attribute'] == False)}",
        )
class vertexgrouppaint(bpy.types.Operator):
    """Weight Paint Mask. Share it with all selected (or press Q in the viewport). Alt+Click to remove it"""
    bl_idname = "secret.vertexgrouppaint"
    bl_label = "Weight Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    # def execute(self, context):
    def invoke(self, context, event):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.vertexgrouppaint")

        if event.alt: remove_vgroup=True  #REMOVE VGROUP
        else: remove_vgroup=False  #REMOVE VGROUP
        vertexgrouppaint_function(self,context,NoMasksDetected=True,calledfrombutton=True, activeobj=bpy.data.objects.get(self.object_name), remove_vgroup=remove_vgroup)
        return {'FINISHED'}
class vertexgrouppaint_biome(bpy.types.Operator):
    """Weight Paint Mask. Share it with all Biome (or press Q in the viewport). Alt+Click to remove it"""
    bl_idname = "secret.vertexgrouppaint_biome"
    bl_label = "Weight Paint"
    bl_options = {'REGISTER', 'UNDO'}
    object_biome: bpy.props.StringProperty()
    # def execute(self, context):
    def invoke(self, context, event):

        _secret_paint_panel_exit_paint_mode(context)
        secretpaint_update_modifier_f(context,upadte_provenance="secret.vertexgrouppaint_biome")

        obj = context.object
        if obj:
            hair=[]
            parent = obj.parent
            if obj.type=="CURVES" and parent:   #IF CURVE SELECTED
                for hai in parent.children: # hair = getChildren(parent)
                    if hai.name in bpy.context.view_layer.objects and hai.type == 'CURVES' and hai.modifiers:
                        for modifier in hai.modifiers:
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                                hair.append((hai,hai.modifiers[0]["Input_2"] if hai.modifiers[0]["Input_2"] else hai.modifiers[0]["Input_9"] if hai.modifiers[0]["Input_9"] else None))
            #ELIF MASK or BRUSH SELECTED or PARENTED TO TERRAIN
            elif obj.type=="MESH" or obj.type=="EMPTY":
                for hayr in bpy.context.scene.objects:
                # for hayr in obj.children:  #only terrain selected, lighter to calculate bc doesn't have to iterate in whole scene, but can't select mask and brushobj
                    if hayr.type == 'CURVES' and hayr.modifiers and hayr.name in bpy.context.view_layer.objects:
                        for modifier in hayr.modifiers: #if mask selected, if brush obj selected, if terrain selected
                            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_97"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_2"] == obj \
                            or modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name == "Secret Paint" and modifier["Input_73"] == obj:
                                hair.append((hayr,hayr.modifiers[0]["Input_2"] if hayr.modifiers[0]["Input_2"] else hayr.modifiers[0]["Input_9"] if hayr.modifiers[0]["Input_9"] else None))
            # # all_bgroups=[]
            # for hayr in hair[:]:
            #     # if hayr[0].modifiers[0]["Socket_0"] not in all_bgroups: all_bgroups.append(hayr[0].modifiers[0]["Socket_0"])
            hair_in_bgroup = [hayr[0] for hayr in hair[:] if hayr[0].modifiers[0]["Socket_0"] == int(self.object_biome)]


        if event.alt: remove_vgroup=True  #REMOVE VGROUP
        else: remove_vgroup=False  #REMOVE VGROUP
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
        if obj.type in ["CURVES","CURVE"] and obj.modifiers: # if obj.type == "CURVES" and obj.modifiers or obj.type == "CURVE" and obj.modifiers:
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    all_selected_curves.append(obj)
        elif obj.type == "MESH":
            all_selected_meshes.append(obj)
            Coll_of_Active = []
            ucol = obj.users_collection
            for i in ucol:
                layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                if Coll_of_Active and Coll_of_Active.name not in all_colls_used_as_brush: all_colls_used_as_brush.append(Coll_of_Active.name)
    ####################################################################


    #GET HAIR FROM MESH or drawn curve
    if len(all_selected_meshes)==len(objselection):
        for obj in bpy.context.scene.objects:
            if obj.type in ["CURVES","CURVE"]:  #if obj.type == "CURVES":
                if obj.modifiers:
                    for modif in obj.modifiers:
                        if modif.type == 'NODES':  # modifier.name == "GeometryNodes"
                            if modif.node_group:
                                if modif.node_group.name.startswith("Secret Paint"):
                                    if modif["Input_9"] and modif["Input_9"].name in all_colls_used_as_brush:
                                        # if modif["Input_9"].name == Coll_of_Active.name:
                                            # bpy.data.objects[activeobj.name].select_set(False)
                                            bpy.data.objects[obj.name].select_set(True)
                                            bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]  # make active
                                            # bpy.ops.view3d.view_selected(use_all_regions=True)
                                            # bpy.data.objects[activeobj.name].select_set(True)
                                    if modif["Input_2"] and modif["Input_2"] in objselection:
                                        # bpy.data.objects[activeobj.name].select_set(False)
                                        bpy.data.objects[obj.name].select_set(True)
                                        bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]  # make active
                                        # bpy.ops.view3d.view_selected(use_all_regions=True)
                                        # bpy.data.objects[activeobj.name].select_set(True)

    #GET MESH FROM HAIR or drawn curve
    elif len(all_selected_curves)==len(objselection):
        for objj in objselection: objj.select_set(False) #DESELECT ORIGINAL
        for obj in objselection:
            if obj.type in ["CURVES","CURVE"]:  #if obj.type == "CURVES":
                if obj.modifiers:
                    for modif in obj.modifiers:
                        if modif.type == 'NODES':  # modifier.name == "GeometryNodes"
                            if modif.node_group:
                                if modif.node_group.name.startswith("Secret Paint"):
                                    if modif["Input_9"]:
                                        for ob in bpy.data.collections[modif["Input_9"].name].all_objects:
                                            if len(objselection)>=2:
                                                ob.select_set(True)
                                                bpy.context.view_layer.objects.active = ob
                                                bpy.ops.view3d.view_selected(use_all_regions=True)
                                            elif len(objselection)==1:
                                                # activeobj.select_set(False)
                                                ob.select_set(True)
                                                bpy.context.view_layer.objects.active = ob
                                                bpy.ops.view3d.view_selected(use_all_regions=True)
                                                # activeobj.select_set(True)

                                    if modif["Input_2"]:
                                        if len(objselection)>=2:
                                            modif["Input_2"].select_set(True)
                                            bpy.context.view_layer.objects.active = modif["Input_2"]
                                            bpy.ops.view3d.view_selected(use_all_regions=True)
                                        elif len(objselection)==1:
                                            # activeobj.select_set(False)
                                            modif["Input_2"].select_set(True)
                                            bpy.context.view_layer.objects.active = modif["Input_2"]
                                            bpy.ops.view3d.view_selected(use_all_regions=True)
                                            # activeobj.select_set(True)

                                        # # bpy.data.objects[activeobj.name].select_set(False)
                                        # bpy.context.view_layer.objects.active = modif["Input_2"]
                                        # bpy.data.objects[modif["Input_2"].name].select_set(True)  # select it
                                        # # bpy.ops.view3d.view_selected(use_all_regions=True)
                                        # # bpy.data.objects[activeobj.name].select_set(True)











        # SELECT BAKE EMPTY TEMP

        # elif activeobj.type == "EMPTY" and activeobj.name.startswith("oren"):
        #     activeobj = bpy.context.active_object
        #
        #     #LIST ALL BONES IN SCENE
        #     objsReferencingEmpty =[]
        #     armaturesReferencingEmpty =[]
        #     bonesReferencingEmpty =[]
        #     allBonesinfile =[]
        #     try:  # try because there might not be any armatures in the scene
        #         bpy.ops.object.select_all(action='DESELECT')  # find all bones in the scene for booleanlist
        #         for obj in bpy.context.scene.objects:
        #             obj.select_set(obj.type == "ARMATURE")
        #             for obj in bpy.context.selected_objects:
        #                 bpy.context.view_layer.objects.active = obj
        #         bpy.ops.object.posemode_toggle()  # enter pose mode
        #         allBonesinfile = bpy.context.visible_pose_bones  # all visible bones in blend file
        #
        #         for bone in allBonesinfile: #select all bones with orenconstraint if they reference active empty
        #             for c in bone.constraints:
        #                 if c.name.startswith("orenChild") and bone.constraints[c.name].target == activeobj:  # if 'oren' in c.name:   #if 'oren' not in c.name:
        #                     # bpy.data.objects[c.id_data.name].pose.bones[c.name].bone.select = True
        #                     bonesReferencingEmpty.append(bone)
        #                     armaturesReferencingEmpty.append(bpy.data.objects[c.id_data.name])
        #
        #         bpy.ops.object.posemode_toggle()  # enter pose mode
        #         bpy.ops.object.select_all(action='DESELECT')
        #     except: pass
        #
        #
        #
        #     #select all obj with orenconstraint referencing active empty
        #     for ob in bpy.context.scene.objects:
        #         for c in ob.constraints:
        #             if c.name.startswith("orenChild") and ob.constraints[c.name].target == activeobj:  # if 'oren' in c.name:   #if 'oren' not in c.name:
        #                 bpy.data.objects[ob.name].select_set(True)
        #                 objsReferencingEmpty.append(ob)
        #                 bpy.context.view_layer.objects.active = ob
        #                 # allEmptiesActiveafterCleanup.append(ob.constraints[c.name].target)
        #
        #     #select armatures if any, deselect only their bones and select pertinent ones (preserving selection of other armatures)
        #     if armaturesReferencingEmpty:
        #         for armat in armaturesReferencingEmpty:
        #             bpy.data.objects[armat.name].select_set(True)
        #             bpy.context.view_layer.objects.active = armat
        #         bpy.ops.object.mode_set(mode="POSE")
        #         bpy.ops.pose.select_all(action='DESELECT')
        #         for bone in bonesReferencingEmpty:
        #             # bpy.data.objects[c.id_data.name].pose.bones[c.name].bone.select = True
        #             bone.bone.select = True
        #
        #     # print("bones", bonesReferencingEmpty)
        #     # print("armatures", armaturesReferencingEmpty)
        #     # print("objs", objsReferencingEmpty)
        #     if objsReferencingEmpty or bonesReferencingEmpty:   #reselect original if nothing is found
        #         self.report({'INFO'}, "Selected obj and bones constrained to this empty")
        #     else:
        #         self.report({'WARNING'}, "No constraints are using this empty")
        #         bpy.ops.object.select_all(action='DESELECT')  # bpy.ops.pose.select_all(action='DESELECT')
        #         bpy.data.objects[activeobj.name].select_set(True)  # select it
        #         bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]  # make active



    return {'FINISHED'}
class orencurveselectobj(bpy.types.Operator):
    """For orenpaint and Hair scattering: selects brush object. If mesh selected: select all biomes that are using it"""
    bl_idname = "secret.orencurveselectobj"
    bl_label = "Select Brush obj"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        orencurveselectobj_function(self,context)
        return {'FINISHED'}








#####UTILS





def convert_and_join_f(self,context):
    activeobj = bpy.context.active_object
    if activeobj.type == "MESH": objtype = "MESH"
    if activeobj.type == "CURVE": objtype = "BEZ"
    if activeobj.type == "CURVES": objtype = "HAI"
    activeobjDATANAME = activeobj.data.name

    bpy.ops.object.select_grouped(extend=True, type='CHILDREN_RECURSIVE')  #SELECT CHILDREN
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False})
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    activeobjlocation = tuple(bpy.context.active_object.location)
    objselection = bpy.context.selected_objects  # bpy.context.selected_objects[0]   #bpy.context.scene.objects

    # if activeobj == None: bpy.context.view_layer.objects.active = objselection[0]

    # return{'FINISHED'}

    # REMOVE ORIGINAL BEZIER CURVES (after applying instances, the bezier curves need to be deleted, both normal and secret paint curves)
    linked_detected_will_cause_dupli_everything = False
    all_curves=[]
    for obj in objselection:
        if obj.type in ["CURVES", "CURVE"]:
            all_curves.append(obj)   #even normal bezier curves get duplicated when applying instances
            if obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                        obj.modifiers[0]["Input_50"] = True  # realize instances modifier
                        obj.location = obj.location #update
        # if obj.type in ["CURVES", "CURVE"]:
        #     all_curves.append(obj)
        # try:
        #     obj.modifiers[0]["Input_50"] = True  #realize instances modifier
        #     obj.location = obj.location
        # except:pass
    bpy.ops.object.duplicates_make_real()

    #REMOVE ALL CURVES
    for ob in all_curves:
        bpy.data.objects.remove(ob, do_unlink=True)
    newobjselection = bpy.context.selected_objects

    #REMOVE EMPTIES
    for ob in newobjselection:
        if ob.type == "EMPTY":
            newobjselection.remove(ob)
            bpy.data.objects.remove(ob, do_unlink=True)




    #detect if there are LIBRARY LINKS because they will create duplis to delete after it's converted to mesh
    for ob in newobjselection:
        bpy.context.view_layer.objects.active = ob  #need a random active object before converting to mesh, will change to accurate one later
        if ob.data.library: linked_detected_will_cause_dupli_everything = True

    #CONVERT TO MESH
    bpy.ops.object.make_single_user(object=True, obdata=True)   #make everything single user
    bpy.ops.object.convert(target='MESH')

    #REMOVE DUPLIS THAT WERE CREATED WHEN CONVERTING TO MESH IF THE MESH HAD A LIBRARY LINK
    if linked_detected_will_cause_dupli_everything:
        for ob in newobjselection:
            newobjselection.remove(ob)
            bpy.data.objects.remove(ob, do_unlink=True)
        newobjselection = bpy.context.selected_objects #after deleting the old ones, redefine the selection with new one




    #NEW ACTIVE BASED ON LOCATION
    center_found = False
    for ob in newobjselection:
        if tuple(ob.location) == activeobjlocation:
            bpy.context.view_layer.objects.active = ob
            center_found = True
            break

    bpy.ops.object.join()
    if not center_found:     #RECENTER ORIGIN
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        bpy.ops.object.align_tools(subject='1', active_too=True, advanced=True, loc_z=True, ref1='0', ref2='0', self_or_active='0')

    #UPDATE EXISTING MESH
    reupdating_existing_mesh=False
    ob_to_update=[]
    data_to_update = []
    for ob in bpy.data.objects:
        if ob.type=="MESH" and ob.data.name == activeobjDATANAME +"ASSEMBLY-"+objtype:        #CHECK IF THE BLEND FILE CONTAINS THE DATA ALREADY
            ob_to_update.append(ob)
            data_to_update = ob.data
            reupdating_existing_mesh=True
    if data_to_update:
        data_to_update.name = "OLDTODELETE"
        bpy.context.view_layer.objects.active.data.name = activeobjDATANAME +"ASSEMBLY-"+objtype
        for ob in ob_to_update: ob.data = bpy.context.view_layer.objects.active.data #SWITCH EVERY OBJECT



    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


    #DELETE ACTIVE IF JUST UPDATING EXISTING, else keep it anad rename it
    if reupdating_existing_mesh:
        bpy.data.objects.remove(bpy.context.view_layer.objects.active, do_unlink=True)
        self.report({'INFO'}, "Updated Existing Mesh Assembly")  # need to add (self, context) in the function
    else:
        bpy.context.view_layer.objects.active.name = bpy.context.view_layer.objects.active.data.name = activeobjDATANAME +"ASSEMBLY-"+objtype
        self.report({'INFO'}, "Created a new Mesh Assembly")  # need to add (self, context) in the function
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
    # bpy.ops.object.mode_set(mode="OBJECT")
    activeobj = bpy.context.active_object
    activeobj.select_set(True)
    objselection = bpy.context.selected_objects  # if activeobj not in objselection: objselection.append(activeobj)


    # for ob in new_obs:
    #     if ob.type=="EMPTY": print("EMPTYYYYYYY",ob.name)
    # KB3D_CBD_BldgMdBusStop_A_grp building cyberdistrict.002
    # KB3D_CBD_BldgMdBusStop_A_grp building cyberdistrict.003
    # if activeobj.type =="CURVE":surface_to_parent_to = activeobj
    # else: surface_to_parent_to = activeobj.parent

    for obj in objselection:
        all_brush_coll_instans = []  # FIND ALL REFERENCED EMPTY INSTANCES, both from brushOBJ and brushCOll with collInstance inside
        all_assemblies_modifiers = []  # FIND ALL REFERENCED EMPTY INSTANCES, both from brushOBJ and brushCOll with collInstance inside
        realized_partial_hair = False
        objs_to_delete_afterwards = []

        for x in bpy.context.selected_objects: x.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        if obj.type in ["CURVES","CURVE"] and obj.modifiers:
            # REALIZE SELECTED HAIR STRANDS   IF IN EDIT MODE ONLY (by duplicating and deleting the inversly selected
            hide_original_paint_system = True
            if bpy.context.object.mode != "OBJECT" and obj.type == "CURVES":
                realized_partial_hair =True

                apply_paint(self, context)

                #CREATE NEW HAIR OBJECT
                Coll_of_Active = []
                original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
                ucol = obj.users_collection
                for i in ucol:
                    layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                    # bpy.context.view_layer.active_layer_collection = Coll_of_Active
                newobj = obj.copy()
                objs_to_delete_afterwards.append(newobj)
                # bpy.context.view_layer.active_layer_collection = original_collection
                newobj.data = obj.data.copy()
                bpy.context.collection.objects.link(newobj)
                # newobj.modifiers[0]["Input_99"] = True
                # obj.modifiers[0]["Input_99"] = False

                #DELETE THE SELECTED HAIR CURVES IN THE ORIGINAL PAINT SYSTEM
                newobj.select_set(False)
                bpy.ops.object.mode_set(mode="EDIT")
                try: bpy.ops.curves.select_linked() #only works if in point select mode, not hair select mode
                except:pass
                bpy.ops.curves.delete()
                bpy.ops.curves.select_all(action='SELECT') #reselect all curves

                #DELETE THE INVERSE IN THE NEWLY CREATED HAIR SYSTEM
                # obj.select_set(False)
                newobj.select_set(True)
                bpy.context.view_layer.objects.active = newobj
                bpy.ops.object.mode_set(mode="EDIT")
                try:bpy.ops.curves.select_linked()  #only works if in point select mode, not hair select mode
                except:pass
                bpy.ops.curves.select_all(action='INVERT')
                bpy.ops.curves.delete()
                bpy.ops.object.mode_set(mode="OBJECT")
                # activeobj = newobj
                # objselection = [activeobj]

                #DO NOT DISABLE THE ORIGINAL PAINT SYSTEM BECAUSE A NEW ONE WAS CREATED
                hide_original_paint_system = False

            # DISABLE ORIGINAL PAINT SYSTEM, but not the draw curve, that one is better to disable just from the actual modifier, not the TURN OFF SYSTEM checkbox
            if hide_original_paint_system and obj.type == "CURVES":
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint" \
                    or modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999":
                        modif["Input_99"] = True

            #TURN OFF ASSEMBLIES MODIFIER FOR THE BRUSH OBJECT OF THE PAINT SYSTEM
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                    if modif["Input_2"] and modif["Input_2"] not in all_brush_coll_instans:
                        if modif["Input_2"].instance_collection: all_brush_coll_instans.append(modif["Input_2"])

                        #ASSEMBLY
                        elif modif["Input_2"].modifiers and modif["Input_2"].modifiers[0].type == "NODES" and modif["Input_2"].modifiers[0].node_group and "ASSEMBLY" in modif["Input_2"].modifiers[0].node_group.name and modif["Input_2"].modifiers[0].show_viewport == True:
                            if modif["Input_2"].modifiers[0] not in all_assemblies_modifiers: all_assemblies_modifiers.append(modif["Input_2"].modifiers[0])
                            modif["Input_2"].modifiers[0].show_viewport = False

                    if modif["Input_9"]:
                        for obij in modif["Input_9"].all_objects:
                            if obij.instance_collection and obij not in all_brush_coll_instans: all_brush_coll_instans.append(obij)  # LIST EMPTIES THAT ARE INSTANCING

                            #ASSEMBLIES turn off in order to apply instances correctly, turn modifier on afterwards
                            elif obij.modifiers and obij.modifiers[0].type=="NODES" and obij.modifiers[0].node_group and "ASSEMBLY" in obij.modifiers[0].node_group.name and obij.modifiers[0].show_viewport == True:
                                if obij.modifiers[0] not in all_assemblies_modifiers: all_assemblies_modifiers.append(obij.modifiers[0])
                                obij.modifiers[0].show_viewport = False


        all_data = []
        if all_brush_coll_instans:
            for instance in all_brush_coll_instans:
                # print("INSTTTTTTTTTTTTT",instance.name)
                for x in instance.instance_collection.all_objects:
                    if x.data not in all_data: all_data.append(x.data)





        all_previous_objects = set(bpy.context.scene.objects)


        bpy.ops.object.duplicates_make_real()

        for ob in objselection:
            if ob.type == "EMPTY" and not ob.instance_collection:
                # if ob in objs_to_delete_afterwards: objs_to_delete_afterwards.remove(ob)
                bpy.data.objects.remove(ob, do_unlink=True)  # WHEN CONVERTING A COLL INSTANCE TO INDIVIDAUL OBJECTS, delete the new empty that gets created
        #IF BEZIER CURVE DISABLE MODIFIER
        if obj.type == "CURVE":
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                    obj.modifiers[0].show_viewport = False
                    obj.modifiers[0].show_render = False
                    obj.location = obj.location  # update scene

        if obj.type == "MESH" and obj.modifiers and obj.modifiers[0].type == "NODES" and obj.modifiers[0].node_group and "ASSEMBLY" in obj.modifiers[0].node_group.name and obj.modifiers[0].show_viewport == True:
            bpy.data.objects.remove(obj, do_unlink=True)
            objselection.remove(obj)
            continue


        #TURN ASSEMBLIES BACK ON FOR THE BRUSH OBJ, NOT THE NEWLY REALIZED INSTANCES
        for modif in all_assemblies_modifiers: modif.show_viewport = True
        # return{'FINISHED'}

        new_obs = list(set(bpy.context.scene.objects) - all_previous_objects)

        # inverted_matrix = None
        # for ob in new_obs:
        #     if ob.matrix_world[0][0]!=0:
        #         bezier_parent = ob
        #         inverted_matrix = ob.matrix_world.inverted()
        #         break

        # CONVERT EMPTIES TO COLL INSTANCE
        for ob in new_obs:

            #HANDLE REALIZED ASSEMBLIES
            if ob.modifiers and ob.modifiers[0].type == "NODES" and ob.modifiers[0].node_group and "ASSEMBLY" in ob.modifiers[0].node_group.name and ob.modifiers[0].show_viewport == False:
                ob.modifiers[0].show_viewport = True #TURN ON MODIFIER
                # continue #don't use the rest of the script for assemblies



            if ob.type == "EMPTY":
                for instance in all_brush_coll_instans:
                    if ob.name.startswith(instance.name.rsplit('.', 1)[0]):  # IF EMPTY IS NAMED LIKE A PAINTED COLLINSTANCE: reference that collinstance's actual collection       (name without .005)
                        ob.instance_type = 'COLLECTION'
                        ob.instance_collection = instance.instance_collection  # bpy.data.collections[coll_of_collinstance.name]
                if not ob.instance_collection: objs_to_delete_afterwards.append(ob)  # DELETE IF IT WASN'T TRANSFORMED (because it's an empty used as parent or something)
            elif ob.type != "EMPTY" and ob.data and ob.data in all_data and ob not in objs_to_delete_afterwards:
                objs_to_delete_afterwards.append(ob)

            if obj.type == "CURVE":
                # if ob != bezier_parent: ob.parent = bezier_parent
                # ob.matrix_parent_inverse = inverted_matrix  # .data.surface
                ob.parent = obj
                ob.matrix_parent_inverse = obj.matrix_world.inverted()  # .data.surface
            elif obj.type == "CURVES":
                if obj.parent:
                    ob.parent = obj.parent  # activeobj.parent   #.data.surface
                    ob.matrix_parent_inverse = obj.parent.matrix_world.inverted()  # .data.surface
            else:
                if obj.parent:
                    ob.parent = obj.parent  # activeobj.parent   #.data.surface
                    ob.matrix_parent_inverse = obj.parent.matrix_world.inverted()  # .data.surface




        # DELETE OVERLAPPING EMPTIES and remove from list "new_obs"
        all_empties_coordinates = []
        for ob in new_obs:
            if ob.type == "EMPTY" and str(ob.location) not in all_empties_coordinates:
                # print("FIRST ONE MEANT TO SURVIVE", ob.name, str(ob.location))
                all_empties_coordinates.append(str(ob.location))
            elif ob.type == "EMPTY" and str(ob.location) in all_empties_coordinates and ob not in objs_to_delete_afterwards:
                # print("SECOND MEANT FOR DELETION", ob.name, str(ob.location))
                objs_to_delete_afterwards.append(ob)

        # DELETE OVERLAPPING MESHES with same mesh data and identical transforms (from bezier curve duplicates)
        # Key: (mesh_data_name, location_tuple, rotation_tuple, scale_tuple) -> first object seen
        mesh_instances_seen = {}
        for ob in new_obs:
            if ob.type == "MESH" and ob.data and ob not in objs_to_delete_afterwards:
                # Create a unique key based on mesh data and transform (rounded to avoid float precision issues)
                # Use 2 decimal places (~1cm) for location to catch floating-point duplicates from geometry nodes
                # (e.g., -8126.250488 vs -8126.249023 both round to -8126.25)
                # Rotation and scale use 4 decimal places for adequate precision
                loc = tuple(round(v, 2) for v in ob.location)
                rot = tuple(round(v, 4) for v in ob.rotation_euler)
                scale = tuple(round(v, 4) for v in ob.scale)
                instance_key = (ob.data.name, loc, rot, scale)

                if instance_key not in mesh_instances_seen:
                    mesh_instances_seen[instance_key] = ob
                else:
                    # Duplicate found - mark for deletion
                    objs_to_delete_afterwards.append(ob)



        # DELETE REMAINING INDIVIDUAL OBJECTS (to only leave empties)
        for objj in objs_to_delete_afterwards:
            bpy.data.objects.remove(objj, do_unlink=True)  # delete hair obj



    return {'FINISHED'}
class realize_instances(bpy.types.Operator):
    """Make instances real, mute Paint System. If executed from Edit mode or Hair Sculpt mode, it will only realize the selected hair strands. So you can choose which instance will be converted to an object and keep the rest as a Paint System"""
    bl_idname = "secret.realize_instances"
    bl_label = "Realize Instances"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        realize_instances_f(self,context)
        return {'FINISHED'}


# def contextduplicatehaircurves(Coll_of_Active,context):
#
#     bpy.ops.object.mode_set(mode="OBJECT")
#     curveobj = bpy.context.active_object
#     curveobj_BoundingBox_State = bpy.context.object.display_type
#     surfaceobj = bpy.context.object.data.surface
#
#     # FIND COLLECTION OF ACTIVE
#     original_collection = bpy.context.view_layer.active_layer_collection   #bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
#     # ucol = curveobj.users_collection
#     # for i in ucol:
#     #     layer_collection = bpy.context.view_layer.layer_collection   #bpy.context.scene.collection
#     #     Coll_of_Active = recurLayerCollection(layer_collection, i.name)
#     bpy.context.view_layer.active_layer_collection = Coll_of_Active  # SELECT COLLECTION OF ACTIVE OBJ
#
#     bpy.ops.object.select_all(action='DESELECT')
#     bpy.data.objects[surfaceobj.name].select_set(True)  # select it
#     bpy.context.view_layer.objects.active = bpy.data.objects[surfaceobj.name]  # make active
#     bpy.ops.object.curves_empty_hair_add(align='WORLD', location=bpy.data.objects[surfaceobj.name].location, scale=(1, 1, 1))
#     bpy.context.object.display_type = curveobj_BoundingBox_State  # bounding box state
#
#     # #APPLY SCALE
#     # hairCurves = bpy.context.active_object
#     # bpy.ops.object.select_all(action='DESELECT')
#     # bpy.data.objects[hairCurves.name].select_set(True)  # reselect original
#     # bpy.context.view_layer.objects.active = bpy.data.objects[hairCurves.name]  # make active
#     # bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
#
#     bpy.data.objects[curveobj.name].select_set(True)  # select it
#     bpy.context.view_layer.objects.active = bpy.data.objects[curveobj.name]  # make active
#     bpy.ops.object.make_links_data(type='MODIFIERS')
#     bpy.ops.object.make_links_data(type='MATERIAL')
#
#     bpy.context.active_object.select_set(False)
#     for obj in bpy.context.selected_objects:
#         bpy.context.view_layer.objects.active = obj
#
#     if bpy.context.object.modifiers["GeometryNodes"]: #don't enter hair sculpt mode if noise scatter detected
#         if bpy.context.object.modifiers["GeometryNodes"]["Input_69"] == False:
#             context3sculptbrush(context)
#         else:
#             bpy.context.object.modifiers["GeometryNodes"]["Input_71"] = float(random.choice(range(0, 999999)))  # random noise W
#             bpy.context.object.location = bpy.context.object.location  # best way to update the scene ;update scene
#
#     else: context3sculptbrush(context)
#
#     bpy.context.view_layer.active_layer_collection = original_collection
#     return {'FINISHED'}
# # def context238441(context):
# #     bpy.ops.object.mode_set(mode="OBJECT")
# #     curveobj = bpy.context.active_object.name
# #     surfaceobj = bpy.context.object.data.surface
# #
# #     bpy.data.objects[surfaceobj.name].select_set(True) #select it
# #     bpy.context.view_layer.objects.active = bpy.data.objects[surfaceobj.name]  #make active
# #
# #     bpy.ops.object.curves_empty_hair_add(align='WORLD', location= bpy.data.objects[surfaceobj.name].location, scale=(1, 1, 1))
# #
# #     bpy.data.objects[curveobj].select_set(True) #select it
# #     bpy.context.view_layer.objects.active = bpy.data.objects[curveobj]  #make active
# #     bpy.ops.object.make_links_data(type='MODIFIERS')
# #
# #     bpy.context.active_object.select_set(False)
# #     for obj in bpy.context.selected_objects:
# #         bpy.context.view_layer.objects.active = obj
# #     bpy.ops.object.mode_set(mode="SCULPT_CURVES")
# #
# #     # obj = bpy.context.active_object
# #     # for mod in [m for m in obj.modifiers if m.type == 'PARTICLE_SYSTEM']:
# #     #     bpy.ops.object.modifier_remove( modifier = mod.name )
# #     return {'FINISHED'}
# class orenscatterduplicatehair(bpy.types.Operator):
#     """duplicate"""
#     bl_idname = "oren.orenscatterduplicatehair"
#     bl_label = "duplicate hair"
#     def execute(self, context):
#         # context238441(context)
#
#         original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
#         ucol = bpy.context.object.users_collection
#         for i in ucol:
#             layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
#             Coll_of_Active = recurLayerCollection(layer_collection, i.name)
#
#         contextduplicatehaircurves(Coll_of_Active,context)
#         return {'FINISHED'}
def context237411(context):
    if len (bpy.context.selected_objects ) == 2:
        brushobj = bpy.context.active_object.name

        bpy.context.active_object.select_set(False)  #invert selection
        for obj in bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = obj
        originalcurveobj = bpy.context.active_object.name

        bpy.ops.object.duplicate_move_linked(OBJECT_OT_duplicate={"linked":True, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={})
        bpy.context.object.modifiers[0]["Input_2"] = bpy.data.objects[brushobj]
        # newcurveobj = bpy.context.active_object.name

        # bpy.data.objects[originalcurveobj].select_set(True) #select it
        # bpy.context.view_layer.objects.active = bpy.data.objects[originalcurveobj]  #make active
        # bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        #
        # bpy.context.active_object.select_set(False)
        # for obj in bpy.context.selected_objects:
        #     bpy.context.view_layer.objects.active = obj

        bpy.ops.object.mode_set(mode="EDIT")
        for area in bpy.context.screen.areas:   # draw tool
            if area.type == "VIEW_3D":
                override = bpy.context.copy()
                override["space_data"] = area.spaces[0]
                override["area"] = area
                bpy.ops.wm.tool_set_by_id(override, name="builtin.draw")
        bpy.ops.object.mode_set(mode="OBJECT")


    # elif len (bpy.context.selected_objects ) == 1:    # if two obj selected,
    #     curveobj = bpy.context.active_object.name


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
    # create material
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
            # activeobj.active_material = bpy.data.materials[mat.name]
            activeobj.data.materials.append(mat)
        self.report({'INFO'}, "A new material was created since there was none.")
def newmaterial_f(self, context):

    new_duplis=[]
    material_cache = {}
    for obj in bpy.context.selected_objects:
        bpy.data.objects[obj.name].select_set(False)

        if obj.type == "CURVES" and obj.modifiers or obj.type == "CURVE" and obj.modifiers:
            for modif in obj.modifiers:  # modifier.name == "GeometryNodes"
                if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":
                    brushobj = obj.modifiers[0]["Input_2"]
                    custommaterial=None
                    if obj.modifiers[0]["Input_39"] and obj.modifiers[0]["Input_40"]: custommaterial = obj.modifiers[0]["Input_40"]

                    #dupli brush obj
                    brushobj=dupliObjCheckCoordinates(self, context, activeobj=brushobj)  # bpy.ops.transform.translate(value=(0, 0, finaltranslationAmount), orient_axis_ortho='X', orient_type='GLOBAL',orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL',constraint_axis=(False, False, True), mirror=False, use_proportional_edit=False,proportional_edit_falloff='SMOOTH', proportional_size=1,use_proportional_connected=False, use_proportional_projected=False)
                    createMaterialIfNone(self, context, activeobj = brushobj)

                    obj.data.materials.clear()
                    #dupli materials
                    for mat_slot in brushobj.material_slots:
                        if mat_slot.material:
                            mat = mat_slot.material
                            mat_slot.link = 'OBJECT'
                            if custommaterial: mat_slot.material = _secret_paint_safe_material_for_assignment(custommaterial, material_cache)
                            else: mat_slot.material = _secret_paint_safe_material_for_assignment(mat, material_cache)
                            if mat_slot.material is None:
                                continue
                            if mat_slot.material.users >= 2: mat_slot.material = mat_slot.material.copy()
                            _secret_paint_append_material_once(obj.data.materials, mat_slot.material)


                    obj.modifiers[0]["Input_2"] = brushobj
                    obj.modifiers[0]["Input_39"] = False
                    new_duplis.append(brushobj)



        elif obj.type=="MESH":  #if no geo nodes found, then just make a duplicate with new mat
            createMaterialIfNone(self, context, activeobj = obj)
            dupliobj = dupliObjCheckCoordinates(self, context,activeobj = obj)
            new_duplis.append(dupliobj)

            obj.data.materials.clear()
            for mat_slot in dupliobj.material_slots:
                if mat_slot.material:
                    mat = mat_slot.material
                    mat_slot.link = 'OBJECT'
                    mat_slot.material = _secret_paint_safe_material_for_assignment(mat, material_cache)
                    if mat_slot.material is None:
                        continue
                    if mat_slot.material.users >= 2: mat_slot.material = mat_slot.material.copy()
                    _secret_paint_append_material_once(obj.data.materials, mat_slot.material)

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
        # contex39482(context)
        return {'FINISHED'}
def export_to_asset_library_function(self,context,event): #paint. conversion

    # if bpy.data.is_saved:
    #     bpy.ops.wm.save_mainfile()
    # if not bpy.data.is_saved:
    #     self.report({'ERROR'}, "Save current blend file first")
    #     return{'CANCELLED'}

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
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):  # modifier.name == "GeometryNodes"
                        all_selected_hair.append(obj)
                        if modif["Input_2"] and modif["Input_2"] and modif["Input_2"] not in all_brush_objs: all_brush_objs.append(modif["Input_2"])
                        if modif["Input_9"] and modif["Input_9"] and modif["Input_9"] not in all_brush_objs: all_brush_collections.append(modif["Input_9"])
                        if obj.parent and obj.parent not in all_parent_surfaces: all_parent_surfaces.append(obj.parent)
    if len(all_parent_surfaces)==1: biome_detected = True
    else: biome_detected = False
    if len(objselection)==len(all_selected_hair): all_sel_are_hair=True
    else: all_sel_are_hair=False
    ########################################################################################



    #BIOME SPHERE
    # new_collection=[]
    # CREATE TEMP COLLECTION
    asset_name = bpy.context.preferences.addons[__package__].preferences.biomeAssetName  # biome_name = bpy.context.preferences.addons[__package__].preferences.biomename #context.scene.mypropertieslist.biomename
    if not asset_name and activeobj: asset_name = activeobj.name
    new_collection = bpy.data.collections.new(asset_name)
    bpy.context.scene.collection.children.link(new_collection)

    newobjs_toDelete=[]
    if biome_detected and all_parent_surfaces == all_meshes and len(all_meshes)==1\
    or all_sel_are_hair:





        #FIND LEAST DENSE PAINT SYSTEM (for biome plane right zize)
        largest = all_selected_hair[0]
        for ob in all_selected_hair:
            if ob.modifiers[0]["Input_68"] < largest.modifiers[0]["Input_68"]: largest=ob
        # # #RESIZE BALL TO SHOW AT LEAST 20 UNITS OF LEAST DENSE SYSTEM (more accurate thumbnail)
        # # surface_area = (((1 / ((largest.modifiers["GeometryNodes"]["Input_68"] ** 0.5) * (largest.modifiers["GeometryNodes"]["Input_100"] ** 2))) / 2) **2 )      *    (50*math.pi) #number of objects i want around the sphere
        # #RESIZE BALL TO SHOW AT LEAST 5 UNITS OF LEAST DENSE SYSTEM (more accurate thumbnail)
        # surface_area = (((1 / ((largest.modifiers[0]["Input_68"] ** 0.5) * (largest.modifiers[0]["Input_100"] ** 2))) / 2) **2 )      *    (12*math.pi) #number of objects i want around the sphere
        # radius = math.sqrt(surface_area / (4 * math.pi))

        xsize =  1 / ((largest.modifiers[0]["Input_68"] ** 0.5) * (largest.modifiers[0]["Input_100"]** 0.5))     # xsize =  1 / ((largest.modifiers[0]["Input_68"] ** 0.5) * largest.modifiers[0]["Input_100"])
        # xsize =  allTerrainArea/   (   (   (0.5/   ((bpy.context.object.modifiers[0]["Input_68"] ** 0.5) *bpy.context.object.modifiers[0]["Input_100"])   )   *2)   **2)     # xsize =  1 / ((largest.modifiers[0]["Input_68"] ** 0.5) * largest.modifiers[0]["Input_100"])
        number_instaces_to_show = 12
        radius = (number_instaces_to_show * (xsize * xsize)) ** 0.5   #lenght of one of the sides of the plane

        #BIOME PLANE
        subdivisions = 4
        meshhh = bpy.data.meshes.new("Secret Paint Biome")
        bm = bmesh.new()
        v = [bm.verts.new((x, y, 0)) for x, y in [(-radius / 2, -radius / 2), (radius / 2, -radius / 2), (radius / 2, radius / 2), (-radius / 2, radius / 2)]]
        f = bm.faces.new(v)
        for _ in range(subdivisions):
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)  # bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1)
        bm.to_mesh(meshhh)
        bm.free()
        cubeOBJ = bpy.data.objects.new("Secret Paint Biome", meshhh)
        new_collection.objects.link(cubeOBJ)  #bpy.context.collection.objects.link(cubeOBJ)  # Link the object to the scene collection

        # meshhh = bpy.data.meshes.new("Secret Paint Biome")  # Create a new mesh data block
        # cubeOBJ = bpy.data.objects.new("Secret Paint Biome", meshhh)  # Create a new object with the mesh data
        # new_collection.objects.link(cubeOBJ)  #bpy.context.collection.objects.link(cubeOBJ)  # Link the object to the scene collection
        # verts = [ (-radius / 2, -radius / 2, 0), (radius / 2, -radius / 2, 0), (radius / 2, radius / 2, 0), (-radius / 2, radius / 2, 0)]
        # edges = []  # Define edges (none needed for this plane)
        # faces = [(0, 1, 2, 3)]  # Define a single face with four vertices
        # meshhh.from_pydata(verts, edges, faces)  # Assign vertices and faces to the mesh
        # meshhh.update()  # Update the mesh with the new data
        # # bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, enter_editmode=False, align='WORLD', location=(0, 0, 0),scale=(1, 1, 1))
        # # cubeOBJ = bpy.context.active_object

        cubeOBJ.use_fake_user = 1
        # bpy.context.object.name = "Biome sphere"
        # for ob in objselection:
        #     bpy.data.objects[ob.name].select_set(True)
        # orenpaint_function(self, context, event) #orenscatter biome on sphere
        all_previous_objects = set(bpy.context.scene.objects)
        secretpaint_function(self, context, event, activeobj=cubeOBJ, objselection=objselection, auto_Mask_Optimization=False) #orenscatter biome on sphere
        newobjs_toDelete = list(set(bpy.context.scene.objects) - all_previous_objects) #if a single biome is detected, just export that
        newobjs_toDelete.append(cubeOBJ)
        objselection = newobjs_toDelete






        #MATERIAL OF TERRAIN
        # if activeobj.parent.material_slots:
        if all_parent_surfaces[0].material_slots:
            for source_mat_slot in all_parent_surfaces[0].material_slots:  #.data.surface
                source_mat = source_mat_slot.material
                if source_mat:
                    target_mat_slot = cubeOBJ.material_slots.get(source_mat.name)
                    if not target_mat_slot: target_mat_slot = cubeOBJ.data.materials.append(source_mat) #.append(source_mat.copy())
                    if target_mat_slot: target_mat_slot.material = source_mat

        bpy.data.objects[cubeOBJ.name].select_set(True)
        if cubeOBJ.children:
            for hair in cubeOBJ.children:
                if len(cubeOBJ.children)==1:
                    hair.modifiers[0]["Input_69"] = True
                    if hair.modifiers[0]["Input_83_use_attribute"] == True: hair.modifiers[0]["Input_83_use_attribute"] = False  # TURN OFF ATTRIBUTE
                    # if hair.modifiers["GeometryNodes"]["Input_83_use_attribute"] == True:
                    #     bpy.context.view_layer.objects.active = bpy.data.objects[hair.name]
                    #     bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_83_use_attribute\"]",modifier_name="GeometryNodes")
                    hair.modifiers[0]["Input_83_attribute_name"] = ""
                    bpy.ops.object.mode_set(mode="OBJECT")
                # bpy.data.objects[hair.name].select_set(True)
                if hair not in objselection: objselection.append(hair)

        #RESTORE SELECTION
        for x in bpy.context.selected_objects: x.select_set(False) #objselection
        if activeobj: bpy.context.view_layer.objects.active = activeobj
        for x in ORIG_objselection: x.select_set(True)
        bpy.ops.object.mode_set(mode=ActiveMode)


    # #UNMARK OTHER ASSETS and fake users
    # for o in bpy.data.objects:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.collections:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.materials:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.textures:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    #
    # for o in bpy.data.node_groups:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.texts:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.masks:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.images:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.worlds:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.particles:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.meshes:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.hair_curves:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.lights:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.cameras:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.brushes:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.screens:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    # for o in bpy.data.workspaces:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False
    #     # try: bpy.data.workspaces.remove(o, do_unlink=True)
    #     # except:pass
    # for o in bpy.data.paint_curves:
    #     if o.asset_data: o.asset_clear()
    #     if o.use_fake_user: o.use_fake_user = False




    # #LINK TO NEW COLLECTION
    # # biome_name = bpy.context.preferences.addons[__package__].preferences.biomename #context.scene.mypropertieslist.biomename
    # asset_name = bpy.context.preferences.addons[__package__].preferences.biomeAssetName
    # if not asset_name and activeobj: asset_name=activeobj.name
    # # else: asset_name= os.path.basename(biome_name)
    # # new_collection = bpy.data.collections.new(os.path.basename(biome_name)) #only the last element of the path
    # new_collection = bpy.data.collections.new(asset_name) #only the last element of the path
    # bpy.context.scene.collection.children.link(new_collection)
    # print("SSSSSSSSSSSSSSSSSSSS",new_collection)
    for obj in objselection:
        # new_collection.objects.link(obj)
        if obj.name not in new_collection.all_objects: new_collection.objects.link(obj)
        # if obj.parent not in new_collection: new_collection.objects.link(obj.parent)
    new_collection.asset_mark()  #generate preview before adding brush objects
    new_collection.asset_generate_preview()
    for obj in all_brush_objs: #new_collection.objects.link(obj)
        # # if obj not in new_collection.all_objects: new_collection.objects.link(obj)
        # try:new_collection.objects.link(obj)
        # except:pass
        if obj.name not in new_collection.all_objects: new_collection.objects.link(obj)
    for coll in all_brush_collections: new_collection.children.link(coll)
    # return
    # time.sleep(10)
    # preview = new_collection.preview
    # print(preview)
    # bpy.data.images['PreviewImageName'].save_render(filepath=preview_path)  #SAVE PREVIEW EXTERNALLY?

    # return{'FINISHED'}







    #CATALOG ASSIGNMENT OR CREATION
    target_catalog = bpy.context.preferences.addons[__package__].preferences.biomenamecategory #= "Biomes/Nature/Short Grass"
    if target_catalog:
        folder = bpy.context.preferences.addons[__package__].preferences.biome_library + "/blender_assets.cats.txt"   # folder = Path(bpy.data.filepath).parent.parent     bpy.context.preferences.filepaths.asset_libraries[-1].path
        with open(folder, 'a+') as f:
            f.seek(0) # Move the file pointer to the beginning to read its contents
            existingID=False
            for line in f.readlines(): #FIND TARGET CATALOG ID
                if line.startswith(("#", "VERSION", "\n")):
                    continue
                name = line.split(":")[1].split("\n")[0] #name = line.split(":")[2].split("\n")[0]  # Each line contains : 'uuid:catalog_tree:catalog_name' + eol ('\n')
                if name.lower() == target_catalog.lower(): #make both lower case for checking purposes
                    existingID=True
                    uuid=line.split(":")[0]
                    break

            if not existingID: #CREATE TARGET CATALOG
                distinct_chars = "abcdef0123456789" #"abcdefghijklmnopqrstuvwxyz0123456789"
                part1 = ''.join(random.choice(distinct_chars) for _ in range(8))
                part2 = ''.join(random.choice(distinct_chars) for _ in range(4))
                part3 = ''.join(random.choice(distinct_chars) for _ in range(4))
                part4 = ''.join(random.choice(distinct_chars) for _ in range(4))
                part5 = ''.join(random.choice(distinct_chars) for _ in range(12))
                uuid = part1+"-"+part2+"-"+part3+"-"+part4+"-"+part5
                final = uuid +":"+target_catalog+":"+target_catalog.replace('/', '-')
                f.write("\n"+final)

            #ASSIGN FOUND OR CREATED
            # obj=bpy.data.objects["c1"]
            new_collection.asset_data.catalog_id = uuid







    #GET FOLDER OR CREATE IT
    biome_name = bpy.context.preferences.addons[__package__].preferences.biomename #context.scene.mypropertieslist.biomename
    path= bpy.context.preferences.addons[__package__].preferences.biome_library + os.path.dirname(biome_name) #path without the last element     bpy.context.preferences.filepaths.asset_libraries[-1].path
    if not os.path.exists(path): os.makedirs(path) #create folder if it doesn't exist

    #CREATE TEMP .BLEND FROM CURRENTLY OPENED (to make data transferable) #create temp file in order to append the biome ball without having to save the opened scene
    temp_blend=(path+ "\\tempSecretPaintExport.blend").replace("\\", "\\\\")
    bpy.ops.wm.save_as_mainfile(copy=True, filepath=temp_blend)

    # return{'FINISHED'}

    #CHECK IF TARGET EXPORT .blend ALREADY EXISTS
    # numb = 1  #INCREMENTAL NAMING
    # while os.path.exists(path + '/' + os.path.basename(biome_name) + ".blend" if numb==1 else path + '/' + os.path.basename(biome_name) + ' ' + str(numb) + ".blend"): numb += 1
    # finalpath = path + '/' + os.path.basename(biome_name) + ".blend" if numb==1 else path + '/' + os.path.basename(biome_name) + ' ' + str(numb) + ".blend"
    # finalpath = path + '/' + os.path.basename(biome_name) + ".blend"
    finalpath = path + '/' + os.path.basename(biome_name)
    if not finalpath.endswith(".blend"): finalpath= finalpath+".blend" #optionally have the folder path with .blend
    #CREATE EMPTY.BLEND IF IT DOESN'T EXIST
    # if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks = {*bpy.data.window_managers}, fake_user=False, path_remap="ABSOLUTE")
    # if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={bpy.context.active_object}, fake_user=False, path_remap="ABSOLUTE")
    # if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={*bpy.data.worlds}, fake_user=False, path_remap="ABSOLUTE")
    # if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={new_collection}, fake_user=False, path_remap="ABSOLUTE")
    # if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={*bpy.data.workspaces}, fake_user=False, path_remap="ABSOLUTE")
    if not os.path.exists(finalpath): bpy.data.libraries.write(finalpath, datablocks ={*bpy.data.masks}, fake_user=False, path_remap="ABSOLUTE")

    # return{'FINISHED'}
    # blend_path = "C:/Users/loren/AppData/Roaming/Blender Foundation/Blender/3.6/scripts/addons/orenpaint/orenpaint.blend"
    move_objects_script = path+"/tempSecretExportScript.py"  #"C:/Users/loren/AppData/Roaming/Blender Foundation/Blender/3.6/scripts/addons/orenpaint/script.py"
    # move_objects_script = os.path.dirname(blend_path)
    # Save move_objects.py script
    current_file = bpy.data.filepath.replace("\\", "\\\\")
    move_objects_script_content = f'''
import bpy
import os
import re

# bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), major_radius=1, minor_radius=0.25, abso_major_rad=1.25, abso_minor_rad=0.75)

# from bpy.utils import resource_path   # import nodegroup
from pathlib import Path  #paint_from_library(bpy.types.Operator)
import addon_utils


# for o in bpy.context.scene.objects:
#     o.location[0]=o.location[0]+5.0

#select scene collection
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

# source_file_path = "C:\\\\Users\\\\loren\\\\Assets\\\\3D\\\\objects\\\\Biomes\\\\tempSecretPaintExport.blend"
source_file_path = "{temp_blend}" 
with bpy.data.libraries.load(source_file_path) as (data_from, data_to):
    data_to.collections = [name for name in data_from.collections if "{new_collection.name}"== name]  #in name]
    # data_to.objects = [name for name in data_from.objects if "human" == name]
    # data_to.collections = [name for name in data_from.collections if "ui" == name]
# for coll in data_to.collections: context.collection.objects.link(coll)
# for coll in data_to.collections: bpy.context.scene.collection.children.link(coll)
# for obj in data_to.objects: context.collection.objects.link(obj)
    # context.view_layer.objects.active = obj  # select appended objects
    # obj.select_set(True)


hidden_to_restore=[]
for coll in data_to.collections:     #LINK COLL TO SCENE
    bpy.context.collection.children.link(coll)

    if {newobjs_toDelete}:           #IF TRUE THEN WE'RE IMPORTING A BIOME SPHERE
        for oob in coll.all_objects:
            # print(oob.name,oob.type)            
            if oob.type!="CURVES" and not oob.name.startswith("Secret Paint Biome"):
                hidden_to_restore.append(oob) 
                oob.location=(0,0,0) 
                oob.scale=(0,0,0)                 #TEMPORARY HIDE FOR ACCURATE THUMBNAIL
                if oob.asset_data: oob.asset_clear()
                if oob.use_fake_user: oob.use_fake_user = False
                # oob.hide_viewport=True




blender_version = bpy.app.version_string
addon_path=[]
for mod in addon_utils.modules():
    if hasattr(mod, 'bl_info') and mod.bl_info.get("name") == "Secret Paint":  # if mod.bl_info.get("name") == "Secret Paint":
        addon_path = os.path.dirname(mod.__file__)
        break

# ######### UPDATE NODE ########## # bpy.ops.secret.secretpaint_update_modifier() #secretpaint_update_modifier_f(context, Forced_Update=True)
nodes_to_switch = []
cleanup_generator = []
for node_tree in bpy.data.node_groups:
    # if not node_tree.library and node_tree.name.startswith("Secret Paint") and "ASSEMBLY" not in node_tree.name:
    if node_tree.name == "Secret Paint" or node_tree.name.startswith("Secret Paint") and re.search(r"\\.\\d{{3}}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999":  # if node_tree.name.startswith("Secret Paint") and "ASSEMBLY" not in node_tree.name:
        if not node_tree.library: node_tree.name = "Secret Paint.001"  # new_name = node_tree.name.replace('orenpaint', 'orenpaint OLD')
        if node_tree not in nodes_to_switch: nodes_to_switch.append(node_tree)
    # if not node_tree.library and node_tree.name.startswith("Secret Generator"):
    if node_tree.name == "Secret Generator" or node_tree.name.startswith("Secret Generator") and re.search(r"\\.\\d{{3}}$", node_tree.name) and ".001" <= node_tree.name[-4:] <= ".999": #if node_tree.name.startswith("Secret Generator"):
        if not node_tree.library: node_tree.name = "Secret Generator.001"  # new_name = node_tree.name.replace('orenpaint', 'orenpaint OLD')
        if node_tree not in cleanup_generator: cleanup_generator.append(node_tree)



#REAPPEND ORENPAINT NODE
all_previous_nodes = set(bpy.data.node_groups)
if blender_version < "4.1": file_path= addon_path + "/Secret Paint 4.0 and older.blend"
elif blender_version < "4.2.0": file_path= addon_path + "/Secret Paint 4.1.blend"
elif blender_version < "4.2.1": file_path= addon_path + "/Secret Paint 4.2.0.blend"
elif blender_version >= "4.2.1": file_path= addon_path + "/Secret Paint.blend"
inner_path = "NodeTree"
object_name = "Secret Paint"
# bpy.ops.wm.append( filepath=os.path.join(file_path, inner_path, object_name), directory=os.path.join(file_path, inner_path), filename=object_name)
# FOR SOME REASON IT FAILS (critical corruption?????? but it works anyway) #Error: Critical blend-file corruption: Conflicts and/or otherwise invalid data-blocks names
try: bpy.ops.wm.append(filepath=os.path.join(file_path, inner_path, object_name),directory=os.path.join(file_path, inner_path),filename=object_name)
except:print("[[[[[[[[[[[[ SECRET PAINT UPDATE FAILED!! CRITICAL CORRUPTION WEIRD")

for lib in bpy.data.libraries: #for some reason, appending anything creates an empty library link, which is error prone
    # if lib.name == "Secret Paint.blend": bpy.data.libraries.remove(lib, do_unlink=True)
    if lib.name in ["Secret Paint.blend","Secret Paint 4.0 and older.blend","Secret Paint 4.1.blend","Secret Paint 4.2.0.blend"]: bpy.data.libraries.remove(lib, do_unlink=True)

# FIND orenpaint NODE THAT'S LOCAL AND NOT THE LINKED ONE (for some reason, when linking a biome with orenpaint node, they share the same node.name so you can't reference it with bpy.data.node_groups.get(
# orenpaintNode = [nod for nod in bpy.data.node_groups if nod not in all_previous_nodes and nod.name.startswith("Secret Paint")]
for nod in bpy.data.node_groups:
    if nod not in all_previous_nodes and nod.name.startswith("Secret Paint"):
        orenpaintNode= nod
        break




#SWITCH ALL MODIFIERS
for obj in bpy.data.objects:
    # if obj.type in ["CURVES","CURVE"] and obj.modifiers and not obj.library:  #can't edit modifiers of linked objects
    if obj.type in ["CURVES","CURVE"]:
        for modif in obj.modifiers:
            # if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith(("Secret Paint","orenpaint")): modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
            # if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint": modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith(("Secret Paint","orenpaint")) and "ASSEMBLY" not in modif.node_group.name: modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")
            # if modif.type == 'NODES' and modif.node_group:
            #     # print(modif.node_group.name)
            #     if modif.node_group.name == "Secret Paint" or modif.node_group.name.startswith("Secret Paint") and re.search(r"\\.\\d{{3}}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999" : modif.node_group = orenpaintNode  #bpy.data.node_groups.get("orenpaint")



# DELETE OLD NODES
# if nodes_to_switch[:]:
for nod in nodes_to_switch[:]:
    # if nod:
    bpy.data.node_groups.remove(nod, do_unlink=True)
# if cleanup_generator[:]:
for nod in cleanup_generator[:]:
    # if nod:
    bpy.data.node_groups.remove(nod, do_unlink=True)
    
######### UPDATE NODE END ##########





for mask in bpy.data.masks: bpy.data.masks.remove(mask, do_unlink=True)  
for o in bpy.data.collections:
    if o.asset_data: o.asset_generate_preview()
for oob in hidden_to_restore: oob.scale=(1,1,1) #RESTORE SIZE 
# for o in bpy.data.objects:
#     if o.asset_data: o.asset_generate_preview()


# bpy.ops.wm.memory_cleanup()
bpy.ops.wm.save_mainfile()
# bpy.ops.wm.quit_blender()
    '''
    with open(move_objects_script, 'w') as move_script_file:
        move_script_file.write(move_objects_script_content)
    command = [
        "blender",
        # "C:/Program Files/Blender Foundation/Blender 3.6/blender.exe",
        # "C:/Program Files/Blender Foundation/Blender 4.0/blender.exe",
        "-b", finalpath,  #blend_path # blend file as asset import target
        "--python", move_objects_script
        # #    f'del "{output_bat_path}"\n'
        # #    f'del "{move_objects_script}"\n'
        # f'echo Finished executing Blender script, saving file, and cleaning up files!\n'
        # f'pause\n'
    ]
    subprocess.run(command)
    os.remove(move_objects_script)
    os.remove(temp_blend)  # bpy.ops.file.unpack_all()       # bpy.ops.wm.open_mainfile(filepath=path)
    # bpy.ops.wm.revert_mainfile(use_scripts=True)  # bpy.ops.file.unpack_all()       # bpy.ops.wm.open_mainfile(filepath=path)









    #RESTORE the working .blend scene by deleting newly created stuff after export is successfull
    for o in newobjs_toDelete:
        # print(o.name,o.type)
        if o.type=="MESH":
            bpy.data.meshes.remove(o.data, do_unlink=True)
            continue #can't check next o.type=="CURVES" if the mesh is deleted
        if o.type=="CURVES":
            bpy.data.hair_curves.remove(o.data, do_unlink=True)
            continue
        # bpy.data.objects.remove(o, do_unlink=True)

    bpy.data.collections.remove(new_collection, do_unlink=True)









    # else: #CREATE .BLEND BY DUPLICATING ACTIVE FILE
    #     # #METHOD 1 SAVE CURRENT BLEND FILE: respects linked data
    #     # new_scene = bpy.data.scenes.new("Biome")
    #     # new_scene.collection.children.link(new_collection)
    #     # # # Copy scene settings
    #     # # existing_scene = bpy.data.scenes.get("Existing Scene")
    #     # # if existing_scene:
    #     # #     new_scene.frame_start = existing_scene.frame_start
    #     # #     new_scene.frame_end = existing_scene.frame_end
    #     # #     new_scene.render.resolution_x = existing_scene.render.resolution_x
    #     # #     new_scene.render.resolution_y = existing_scene.render.resolution_y
    #     #     # Add more settings as needed
    #     # # for obj in bpy.data.objects:
    #     # #     if obj not in objselection: bpy.data.objects.remove(obj, do_unlink=True)
    #     # # for obj in objselection:
    #     # #     new_scene.collection.objects.link(obj)
    #     # #     #also brush objs found in modifier
    #     #
    #     # for scene in bpy.data.scenes:
    #     #     if scene != new_scene:
    #     #         bpy.data.scenes.remove(scene)
    #     # bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    #     # bpy.ops.wm.save_as_mainfile(copy=True, filepath=finalpath)
    #
    #     # bpy.data.libraries.write(finalpath, datablocks=data,path_remap="ABSOLUTE")
    #
    #     # bpy.ops.wm.new_mainfile(filepath="")
    #     # bpy.ops.wm.save_as_mainfile(filepath="path/to/your/new_file.blend")
    #     # data_blocks = {}
    #     # IMPORT LINKED DATA???? this way it's all appended geometry, not linked
    #     # bpy.data.libraries.write(finalpath, data_blocks, fake_user=True)
    #     # bpy.data.libraries.write(finalpath, data_blocks = *bpy.data.window_managers, fake_user=False, path_remap="ABSOLUTE")













    # #REGENERATE THUMBNAILS (code works perfectly, but thumbnail generation doesn't work, it works on its own as a separate button operator)
    # move_objects_script = os.path.dirname(finalpath)
    # # Save move_objects.py script
    # move_objects_script_content = '''
    # import bpy
    # for o in bpy.data.objects:
    #     if o.asset_data: o.asset_generate_preview()
    # for o in bpy.data.collections:
    #     if o.asset_data: o.asset_generate_preview()
    # bpy.ops.wm.save_mainfile()
    # #bpy.ops.wm.quit_blender()
    # '''
    # with open(move_objects_script, 'w') as move_script_file:
    #     move_script_file.write(move_objects_script_content)
    # command = [
    #     "blender",
    #     "-b", finalpath, #blend file that needs new previews
    #     "--python", move_objects_script
    #     # #    f'del "{output_bat_path}"\n'
    #     # #    f'del "{move_objects_script}"\n'
    #     # f'echo Finished executing Blender script, saving file, and cleaning up files!\n'
    #     # f'pause\n'
    # ]
    # subprocess.run(command)
    # os.remove(move_objects_script)












    # #METHOD 2 SAVE NEW BLEND FILE: automatic inclusion of dependencies data, excluded unused data automatically, can import into existing .blend
    # # data_blocks = {*objselection,
    # # data_blocks = {*bpy.context.selected_objects,
    # data_blocks = {new_collection,
    #                # bpy.data.images['PreviewImageName'],
    #                # preview,
    #                # bpy.data.images[new_collection.preview],
    #                # new_collection.preview,
    #                # bpy.data.materials[mat.name],
    #                # *bpy.data.window_managers,
    #                # *bpy.data.workspaces,
    #                # *bpy.data.worlds
    #                # *bpy.data.scenes,
    #                # *bpy.context.scene.render.engine
    #                }
    # #IMPORT LINKED DATA???? this way it's all appended geometry, not linked
    # #bpy.data.libraries.write(finalpath, data_blocks, fake_user=True)
    # bpy.data.libraries.write(finalpath, data_blocks, fake_user=True, path_remap="ABSOLUTE")
    # # remove the created collection and biome sphere
    # if biome_detected:
    # #     for ob in bpy.context.selected_objects:
    # #         bpy.data.objects.remove(ob, do_unlink=True)
    # #     bpy.data.collections.remove(new_collection, do_unlink=True)
    # #     bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    #     bpy.data.objects.remove(cubeOBJ, do_unlink=True)
    #     if new_hairpaint:
    #         for hair in new_hairpaint: bpy.data.objects.remove(hair, do_unlink=True)
    # bpy.data.collections.remove(new_collection, do_unlink=True)
    # bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    #
    # if activeobj: bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]  # make active
    # for x in objselection: bpy.data.objects[x.name].select_set(True)

















    # if should_it_save: bpy.ops.wm.save_mainfile()

    #save collection in the outliner

    # objselection = bpy.context.selected_objects
    # new_scene = bpy.data.scenes.new("Biome")
    # # for obj in bpy.data.objects:
    # #     if obj not in objselection: bpy.data.objects.remove(obj, do_unlink=True)
    # for obj in objselection:
    #     # new_scene.objects.link(obj)
    #     new_scene.collection.objects.link(obj)
    #     #also brush objs found in modifier
    #
    # for scene in bpy.data.scenes:
    #     if scene != new_scene:
    #         bpy.data.scenes.remove(scene)
    #
    # path= bpy.context.preferences.filepaths.asset_libraries[-1].path + '/Biomes'
    # if not os.path.exists(path): os.makedirs(path)
    #
    # numb = 1
    # while os.path.exists(path + '/Biome ' + str(numb) + ".blend"): numb += 1
    # finalpath = path + '/Biome ' + str(numb) + ".blend"
    #
    # print(finalpath)
    # bpy.ops.wm.save_as_mainfile(copy=True, filepath=finalpath)
    # # bpy.ops.wm.revert_mainfile(use_scripts=True)  # bpy.ops.file.unpack_all()       # bpy.ops.wm.open_mainfile(filepath=path)


    #save obj or collection as asset

    # bpy.ops.object.select_all(action='INVERT')
    # I = bpy.context.selected_objects
    # for ob in I:
    #     bpy.data.objects.remove(ob, do_unlink=True)
    #
    # bpy.context.window.workspace = bpy.data.workspaces['1monitor'] #doesn't get transfered to the newly saved and created blend file
    # bpy.data.batch_remove(ids=bpy.data.workspaces['2monitors'], ) #delete useless id data
    #
    # if not should_it_save:



    #FROM EMPTY BLEND FILE INSTEAD OF COPY OF OPENED BLEND FILE
    # #NEW METHOD FROM OFFICIAL BLENDER
    # scene doesn't display objects properly (import collections and link everything to scene)
    # render settings, hdri
    # import 1 monitor workspace?
    # write all materials, textures and node groups to a library  #  https://docs.blender.org/api/blender_python_api_2_77_1/bpy.types.BlendData.html#bpy.types.BlendData.libraries
    # data_blocks = {*bpy.context.selected_objects,
    #                # *bpy.data.window_managers,
    #                *bpy.data.workspaces,
    #                *bpy.data.worlds,
    #                # *bpy.data.scenes,
    #                *bpy.context.scene.render.engine
    #                }
    # bpy.data.libraries.write("//new_library.blend", data_blocks)

    self.report({'INFO'}, f"Successfully exported to {finalpath}")

    return {'FINISHED'}
class export_obj_to_asset_library(bpy.types.Operator):
    """Export the selected hair objects as a Biome to the currently open Asset Library. Works for regular objects as well as Biome Systems"""
    bl_idname = "secret.export_obj_to_asset_library"
    bl_label = "Export Biome to Asset Library"
    bl_options = {'REGISTER', 'UNDO'}

    # def execute(self, context):
    #     should_it_save=True
    #     export_to_asset_library_function(should_it_save,self, context)
    #     return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):      #reference:  orenscatter_modal_operator(bpy.types.Operator)
        export_to_asset_library_function(self, context,event)
        return {'FINISHED'}
class switchtoerasealpha(bpy.types.Operator):   # example of potential simple command
    """In Texture paint mode, press the shortcut to toggle between painting mode and erase mode"""
    bl_idname = "secret.switchtoerasealpha"
    bl_label = "Toggle Erase Alpha /Mix"
    # bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):

        # command for sculpt mode, just in case bpy.context.tool_settings.sculpt.brush
        if bpy.context.tool_settings.image_paint.brush.blend == 'ERASE_ALPHA':
            bpy.context.tool_settings.image_paint.brush.blend = 'MIX'
        else:
            bpy.context.tool_settings.image_paint.brush.blend = 'ERASE_ALPHA'

        return {'FINISHED'}

def add_collections_to_list(collection,all_collections):
    all_collections.append(collection)  # Add the current collection to the list

    # Recursively add collections within this collection to the list
    for sub_collection in collection.children:
        add_collections_to_list(sub_collection,all_collections)
def paint_from_library_function(self, context, event, **kwargs):

    justImport = kwargs.get("justImport") if "justImport" in kwargs else False
    switch_asset = kwargs.get("switch_asset") if "switch_asset" in kwargs else False
    defer_world_paint_start = (
        not justImport
        and not switch_asset
        and _secret_paint_world_paint_enabled(context)
    )
    world_paint_active_system = None
    try:
        world_paint_module = _secret_paint_world_paint_module()
        running_world_paint = getattr(world_paint_module, "_world_operator", lambda: None)()
        if running_world_paint is not None:
            active_system_name = getattr(running_world_paint, "active_system_name", "")
            world_paint_active_system = bpy.data.objects.get(active_system_name) if active_system_name else None
            if world_paint_active_system is None:
                try:
                    world_paint_active_system = running_world_paint._current_system()
                except Exception:
                    world_paint_active_system = None
            running_world_paint.finish_world_paint(context)
    except Exception:
        world_paint_active_system = None

    if world_paint_active_system is not None:
        try:
            if getattr(context, "mode", "") != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        try:
            for selected_obj in list(context.selected_objects):
                selected_obj.select_set(False)
            world_paint_active_system.select_set(True)
            context.view_layer.objects.active = world_paint_active_system
        except Exception:
            pass

    activeobj = bpy.context.active_object
    current_mode = None
    targetless_world_paint_import = False
    asset_browser_world_paint_source = None

    def mark_asset_browser_q_sources(objects):
        for obj in objects or []:
            secretpaint_mark_skip_auto_assembly_on_next_q(obj)

    def asset_browser_world_paint_source_from_objects(objects):
        candidates = []
        for obj in objects or []:
            if obj is None or not hasattr(obj, "type"):
                continue
            if obj not in candidates:
                candidates.append(obj)
        if not candidates:
            return None

        for obj in candidates:
            if _secret_paint_system_modifier(obj) is not None and not _secret_paint_system_is_procedural(obj):
                return obj
        for obj in candidates:
            if _secret_paint_system_modifier(obj) is not None:
                return obj

        root_candidates = [
            obj for obj in candidates
            if getattr(obj, "parent", None) is None or getattr(obj, "parent", None) not in candidates
        ]
        for obj in root_candidates + candidates:
            if getattr(obj, "type", None) in {"MESH", "EMPTY", "CURVE"}:
                return obj
        return None

    def remember_asset_browser_world_paint_source(objects):
        nonlocal asset_browser_world_paint_source
        mark_asset_browser_q_sources(objects)
        if asset_browser_world_paint_source is None:
            asset_browser_world_paint_source = asset_browser_world_paint_source_from_objects(objects)

    def imported_object_bounds(objects):
        min_corner = Vector((float("inf"), float("inf"), float("inf")))
        max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))
        found_any = False
        for obj in objects:
            if obj.type in {"EMPTY", "LIGHT", "CAMERA"}:
                corners = [obj.matrix_world.translation.copy()]
            else:
                try:
                    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                except:
                    corners = [obj.matrix_world.translation.copy()]

            for corner in corners:
                found_any = True
                min_corner.x = min(min_corner.x, corner.x)
                min_corner.y = min(min_corner.y, corner.y)
                min_corner.z = min(min_corner.z, corner.z)
                max_corner.x = max(max_corner.x, corner.x)
                max_corner.y = max(max_corner.y, corner.y)
                max_corner.z = max(max_corner.z, corner.z)

        if not found_any:
            return None

        return {
            "min": min_corner,
            "max": max_corner,
            "center": (min_corner + max_corner) / 2,
        }

    def imported_root_objects(objects):
        object_set = set(objects)
        return [obj for obj in objects if obj.parent not in object_set]

    def is_imported_secret_paint_curve(obj):
        if obj.type != "CURVES" or not obj.modifiers:
            return False
        for modif in obj.modifiers:
            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                return True
        return False

    geometry_data_object_types = {"MESH", "CURVE", "CURVES", "SURFACE", "META", "FONT", "POINTCLOUD", "VOLUME"}

    def imported_root_collections(collections):
        collection_set = set(collections)
        nested_collections = set()
        for parent in collections:
            for child in parent.children:
                if child in collection_set:
                    nested_collections.add(child)
        return [coll for coll in collections if coll not in nested_collections]

    def collection_parent_map(collections):
        parent_map = {}
        collection_set = set(collections)
        for parent in collections:
            for child in parent.children:
                if child in collection_set:
                    parent_map[child] = parent
        return parent_map

    def collection_depth(collection, parent_map):
        depth = 0
        while collection in parent_map:
            collection = parent_map[collection]
            depth += 1
        return depth

    def datablock_exists(datablock, datablocks):
        if datablock is None:
            return False
        try:
            datablock_pointer = datablock.as_pointer()
        except:
            return False
        for candidate in datablocks:
            try:
                if candidate.as_pointer() == datablock_pointer:
                    return True
            except:
                continue
        return False

    def make_import_local(datablock, label):
        if datablock is None:
            return None
        try:
            return datablock.make_local()
        except TypeError:
            try:
                return datablock.make_local(clear_liboverride=True)
            except Exception as ex:
                print(f"---####### LOCALIZE ERROR {label}: {ex}")
        except Exception as ex:
            print(f"---####### LOCALIZE ERROR {label}: {ex}")
        return datablock

    def collection_is_in_scene(collection, root_collection=None):
        if collection is None:
            return False
        if root_collection is None:
            root_collection = bpy.context.scene.collection
        if root_collection == collection:
            return True
        for child in root_collection.children:
            if collection_is_in_scene(collection, child):
                return True
        return False

    def remove_unused_hidden_override_collections(collections):
        for coll in collections:
            if not datablock_exists(coll, bpy.data.collections):
                continue
            if not coll.name.startswith("OVERRIDE_HIDDEN"):
                continue
            if collection_is_in_scene(coll):
                continue

            has_parent = False
            for parent in bpy.data.collections:
                try:
                    if coll in parent.children:
                        has_parent = True
                        break
                except:
                    continue

            if has_parent:
                continue
            if len(coll.objects) == 0 and len(coll.children) == 0:
                try:
                    bpy.data.collections.remove(coll, do_unlink=True)
                except Exception as ex:
                    print(f"---####### REMOVE OVERRIDE HIDDEN ERROR {coll.name}: {ex}")

    def ensure_object_mode_for_import(obj, operation_label):
        if obj is None:
            return True
        try:
            obj_mode = obj.mode
        except Exception as ex:
            print(f"---####### READ MODE ERROR {operation_label} {getattr(obj, 'name', '<unknown>')}: {ex}")
            return False

        if obj_mode == "OBJECT":
            return True

        try:
            if bpy.context.view_layer.objects.active != obj:
                bpy.context.view_layer.objects.active = obj
        except Exception:
            pass

        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode="OBJECT")
                return True
        except RuntimeError as ex:
            print(f"---####### MODE SET ERROR {operation_label} {obj.name}: {ex}")
            return False
        except Exception as ex:
            print(f"---####### MODE SET ERROR {operation_label} {obj.name}: {ex}")
            return False

        print(f"---####### MODE SET POLL FAILED {operation_label} {obj.name} mode={obj_mode}")
        return False

    def localize_imported_secret_paint_curve(obj):
        if not is_imported_secret_paint_curve(obj):
            return obj

        localized_obj = obj

        if obj.library or obj.override_library:
            localized_obj_result = make_import_local(obj, f"Secret Paint curve object {obj.name}")
            if localized_obj_result is not None:
                localized_obj = localized_obj_result

        curve_data = getattr(localized_obj, "data", None)
        if curve_data and (curve_data.library or curve_data.override_library):
            localized_curve_data = make_import_local(curve_data, f"Secret Paint curves data {curve_data.name}")
            if localized_curve_data is not None and localized_curve_data != curve_data:
                try:
                    localized_obj.data = localized_curve_data
                except Exception as ex:
                    print(f"---####### REASSIGN LOCAL CURVES DATA ERROR {localized_obj.name}: {ex}")

        return localized_obj

    def localize_imported_object_instance(obj):
        if obj is None:
            return None
        if obj.library or obj.override_library:
            localized_obj = make_import_local(obj, f"object {obj.name}")
            if localized_obj is not None:
                return localized_obj
        return obj

    def localize_imported_collection_instance(coll):
        if coll is None:
            return None
        if coll.library or coll.override_library:
            localized_coll = make_import_local(coll, f"collection {coll.name}")
            if localized_coll is not None:
                return localized_coll
        return coll

    def copy_collection_settings(source_coll, target_coll):
        for attr_name in ("hide_viewport", "hide_render", "hide_select", "color_tag"):
            try:
                setattr(target_coll, attr_name, getattr(source_coll, attr_name))
            except:
                pass
        try:
            target_coll.instance_offset = source_coll.instance_offset.copy()
        except:
            pass

    def remap_pointers_rna(container, obj_map, id_map):
        try:
            for prop in container.bl_rna.properties:
                if prop.type != 'POINTER':
                    continue
                ident = prop.identifier
                try:
                    val = getattr(container, ident)
                except:
                    continue
                if isinstance(val, bpy.types.Object) and val in obj_map:
                    try:
                        setattr(container, ident, obj_map[val])
                    except:
                        pass
                elif isinstance(val, bpy.types.ID) and val in id_map:
                    try:
                        setattr(container, ident, id_map[val])
                    except:
                        pass
        except:
            pass

        try:
            if hasattr(container, "keys"):
                for key in list(container.keys()):
                    try:
                        value = container[key]
                    except:
                        continue
                    if isinstance(value, bpy.types.Object) and value in obj_map:
                        try:
                            container[key] = obj_map[value]
                        except:
                            pass
                    elif isinstance(value, bpy.types.ID) and value in id_map:
                        try:
                            container[key] = id_map[value]
                        except:
                            pass
                    elif isinstance(value, str):
                        for old_obj, new_obj in obj_map.items():
                            if value == old_obj.name:
                                try:
                                    container[key] = new_obj.name
                                except:
                                    pass
                                break
        except:
            pass

    def unique_datablocks(datablocks):
        unique_blocks = []
        seen_pointers = set()
        for datablock in datablocks:
            if datablock is None:
                continue
            try:
                datablock_pointer = datablock.as_pointer()
            except:
                continue
            if datablock_pointer in seen_pointers:
                continue
            seen_pointers.add(datablock_pointer)
            unique_blocks.append(datablock)
        return unique_blocks

    def collect_collection_hierarchy(root_collections):
        collected_collections = []
        for root_collection in unique_datablocks(root_collections):
            if not datablock_exists(root_collection, bpy.data.collections):
                continue
            add_collections_to_list(root_collection, collected_collections)
        return unique_datablocks([coll for coll in collected_collections if datablock_exists(coll, bpy.data.collections)])

    def collect_objects_from_collections(collections):
        collected_objects = []
        for coll in unique_datablocks(collections):
            if not datablock_exists(coll, bpy.data.collections):
                continue
            try:
                collected_objects.extend(list(coll.all_objects))
            except:
                try:
                    collected_objects.extend(list(coll.objects))
                except:
                    pass
        return unique_datablocks([obj for obj in collected_objects if datablock_exists(obj, bpy.data.objects)])

    def object_is_in_scene(obj):
        if obj is None or not datablock_exists(obj, bpy.data.objects):
            return False
        try:
            for coll in obj.users_collection:
                if collection_is_in_scene(coll):
                    return True
        except:
            pass
        return False

    def ensure_root_collection_parent(root_collection, target_parent_collection):
        if root_collection is None or target_parent_collection is None:
            return

        scene_root_collection = bpy.context.scene.collection
        if target_parent_collection != scene_root_collection:
            try:
                if root_collection in scene_root_collection.children:
                    scene_root_collection.children.unlink(root_collection)
            except:
                pass

        for parent_collection in bpy.data.collections:
            if parent_collection == target_parent_collection:
                continue
            try:
                if root_collection in parent_collection.children:
                    parent_collection.children.unlink(root_collection)
            except:
                pass

        try:
            if root_collection not in target_parent_collection.children:
                target_parent_collection.children.link(root_collection)
        except Exception as ex:
            print(f"---####### LINK ROOT COLLECTION ERROR {root_collection.name}: {ex}")

    def remove_imported_linked_collections(imported_collections):
        linked_imported_collections = [
            coll for coll in unique_datablocks(imported_collections)
            if datablock_exists(coll, bpy.data.collections) and coll.library
        ]
        linked_collection_parent_map = collection_parent_map(linked_imported_collections)
        for coll in sorted(linked_imported_collections, key=lambda item: collection_depth(item, linked_collection_parent_map), reverse=True):
            try:
                bpy.data.collections.remove(coll, do_unlink=True)
            except Exception as ex:
                print(f"---####### REMOVE LINKED COLLECTION ERROR {coll.name}: {ex}")

    def remove_zero_user_imported_linked_objects(imported_objects):
        for obj in unique_datablocks(imported_objects):
            if not datablock_exists(obj, bpy.data.objects):
                continue
            if not obj.library or obj.users != 0:
                continue
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception as ex:
                print(f"---####### REMOVE LINKED OBJECT ERROR {obj.name}: {ex}")

    def remove_imported_linked_objects_outside_scene(imported_objects):
        removed_data_blocks = []
        for obj in unique_datablocks(imported_objects):
            if not datablock_exists(obj, bpy.data.objects):
                continue
            if not obj.library or object_is_in_scene(obj):
                continue
            obj_data = getattr(obj, "data", None)
            if obj_data is not None:
                removed_data_blocks.append(obj_data)
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception as ex:
                print(f"---####### REMOVE OFFSCENE LINKED OBJECT ERROR {obj.name}: {ex}")
        return unique_datablocks(removed_data_blocks)

    def remove_zero_user_linked_data_blocks(data_blocks):
        for data_block in unique_datablocks(data_blocks):
            if data_block is None or not getattr(data_block, "library", None):
                continue
            if getattr(data_block, "users", 0) != 0:
                continue
            try:
                data_block_type = type(data_block).__name__
                if data_block_type == "Mesh":
                    bpy.data.meshes.remove(data_block, do_unlink=True)
                elif data_block_type in {"Curve", "TextCurve", "SurfaceCurve"}:
                    bpy.data.curves.remove(data_block, do_unlink=True)
                elif data_block_type == "Curves":
                    bpy.data.hair_curves.remove(data_block, do_unlink=True)
                elif data_block_type == "Lattice":
                    bpy.data.lattices.remove(data_block, do_unlink=True)
                elif data_block_type == "MetaBall":
                    bpy.data.metaballs.remove(data_block, do_unlink=True)
                elif data_block_type == "PointCloud":
                    bpy.data.pointclouds.remove(data_block, do_unlink=True)
                elif data_block_type == "Volume":
                    bpy.data.volumes.remove(data_block, do_unlink=True)
            except Exception as ex:
                print(f"---####### REMOVE LINKED DATA ERROR {data_block.name}: {ex}")

    def remove_zero_user_shape_key_owner_data(imported_objects, imported_shape_keys):
        imported_shape_key_pointers = set()
        for shape_key in unique_datablocks(imported_shape_keys):
            if not datablock_exists(shape_key, bpy.data.shape_keys):
                continue
            try:
                imported_shape_key_pointers.add(shape_key.as_pointer())
            except:
                continue

        if not imported_shape_key_pointers:
            return

        owner_data_blocks = []
        for obj in unique_datablocks(imported_objects):
            obj_data = getattr(obj, "data", None)
            if obj_data is None:
                continue
            obj_shape_keys = getattr(obj_data, "shape_keys", None)
            if obj_shape_keys is None:
                continue
            try:
                obj_shape_key_pointer = obj_shape_keys.as_pointer()
            except:
                continue
            if obj_shape_key_pointer in imported_shape_key_pointers:
                owner_data_blocks.append(obj_data)

        for data_block in unique_datablocks(owner_data_blocks):
            if not getattr(data_block, "library", None) or data_block.users != 0:
                continue
            try:
                if isinstance(data_block, bpy.types.Mesh):
                    bpy.data.meshes.remove(data_block, do_unlink=True)
                elif isinstance(data_block, bpy.types.Curve):
                    bpy.data.curves.remove(data_block, do_unlink=True)
                elif isinstance(data_block, bpy.types.Lattice):
                    bpy.data.lattices.remove(data_block, do_unlink=True)
            except Exception as ex:
                print(f"---####### REMOVE SHAPE KEY OWNER DATA ERROR {data_block.name}: {ex}")

    def localize_imported_shape_keys(imported_shape_keys):
        localized_shape_keys = []
        for shape_key in unique_datablocks(imported_shape_keys):
            if not datablock_exists(shape_key, bpy.data.shape_keys):
                continue
            localized_shape_key = shape_key
            if shape_key.library or shape_key.override_library:
                localized_shape_key_result = make_import_local(shape_key, f"shape key {shape_key.name}")
                if localized_shape_key_result is not None:
                    localized_shape_key = localized_shape_key_result
            localized_shape_keys.append(localized_shape_key)
        return unique_datablocks(localized_shape_keys)

    def find_shape_key_owner_data(shape_key):
        if shape_key is None or not datablock_exists(shape_key, bpy.data.shape_keys):
            return None
        try:
            shape_key_pointer = shape_key.as_pointer()
        except:
            return None

        data_collections = (
            bpy.data.meshes,
            bpy.data.curves,
            getattr(bpy.data, "hair_curves", []),
            bpy.data.lattices,
            getattr(bpy.data, "pointclouds", []),
            getattr(bpy.data, "volumes", []),
            getattr(bpy.data, "metaballs", []),
        )
        for data_collection in data_collections:
            for data_block in data_collection:
                owner_shape_keys = getattr(data_block, "shape_keys", None)
                if owner_shape_keys is None:
                    continue
                try:
                    if owner_shape_keys.as_pointer() == shape_key_pointer:
                        return data_block
                except:
                    continue
        return None

    def debug_print_linked_shape_key_owners(shape_keys, label):
        linked_shape_keys = [
            shape_key for shape_key in unique_datablocks(shape_keys)
            if datablock_exists(shape_key, bpy.data.shape_keys) and getattr(shape_key, "library", None)
        ]
        if not linked_shape_keys:
            print(f"### SHAPE KEY DEBUG {label}: no linked imported shape keys remain")
            return

        print(f"### SHAPE KEY DEBUG {label}: {len(linked_shape_keys)} linked shape keys remain")
        for shape_key in linked_shape_keys:
            owner_data = find_shape_key_owner_data(shape_key)
            if owner_data is None:
                print(f"### SHAPE KEY DEBUG {shape_key.name}: owner_data=<missing> users={getattr(shape_key, 'users', '?')} library={getattr(getattr(shape_key, 'library', None), 'filepath', None)}")
                continue

            owner_objects = []
            for obj in bpy.data.objects:
                if getattr(obj, "data", None) == owner_data:
                    owner_objects.append(obj)

            owner_object_labels = []
            for obj in owner_objects:
                owner_object_labels.append(
                    f"{obj.name}(obj_lib={bool(obj.library)}, override={bool(obj.override_library)}, in_scene={object_is_in_scene(obj)})"
                )

            print(
                "### SHAPE KEY DEBUG "
                f"{shape_key.name}: "
                f"owner_data={owner_data.name} "
                f"data_type={type(owner_data).__name__} "
                f"data_lib={bool(getattr(owner_data, 'library', None))} "
                f"data_users={getattr(owner_data, 'users', '?')} "
                f"shape_key_users={getattr(shape_key, 'users', '?')} "
                f"owners={owner_object_labels}"
            )

    def finalize_linked_import_as_local_hierarchy(imported_objects, imported_collections, target_parent_collection, asset_type, asset_name):
        imported_objects = unique_datablocks(imported_objects)
        imported_collections = unique_datablocks(imported_collections)

        if asset_type == "Collection" and imported_collections:
            linked_root_collections = imported_root_collections(imported_collections)
            targeted_root_collections = [coll for coll in linked_root_collections if coll.name == asset_name]
            if not targeted_root_collections:
                exact_name_collections = [coll for coll in imported_collections if coll.name == asset_name]
                if exact_name_collections:
                    targeted_root_collections = imported_root_collections(exact_name_collections)
                elif linked_root_collections:
                    targeted_root_collections = linked_root_collections[:1]
                else:
                    targeted_root_collections = imported_collections[:1]

            override_root_collections = []
            for linked_root_collection in unique_datablocks(targeted_root_collections):
                try:
                    override_root_collection = linked_root_collection.override_hierarchy_create(
                        scene=bpy.context.scene,
                        view_layer=bpy.context.view_layer,
                        reference=linked_root_collection,
                        do_fully_editable=True,
                    )
                except Exception as ex:
                    print(f"---####### OVERRIDE HIERARCHY ERROR {linked_root_collection.name}: {ex}")
                    continue
                if override_root_collection is not None:
                    override_root_collections.append(override_root_collection)

            override_root_collections = unique_datablocks(override_root_collections)
            if override_root_collections:
                override_collections = collect_collection_hierarchy(override_root_collections)
                override_parent_map = collection_parent_map(override_collections)
                localized_collection_map = {}
                for coll in sorted(override_collections, key=lambda item: collection_depth(item, override_parent_map), reverse=True):
                    localized_coll = localize_imported_collection_instance(coll)
                    localized_collection_map[coll] = localized_coll if localized_coll is not None else coll

                localized_root_collections = []
                for override_root_collection in override_root_collections:
                    localized_root_collection = localized_collection_map.get(override_root_collection, override_root_collection)
                    if localized_root_collection is None or not datablock_exists(localized_root_collection, bpy.data.collections):
                        continue
                    ensure_root_collection_parent(localized_root_collection, target_parent_collection)
                    localized_root_collections.append(localized_root_collection)

                localized_root_collections = unique_datablocks(localized_root_collections)
                imported_local_collections = collect_collection_hierarchy(localized_root_collections)
                imported_local_objects = []
                for obj in collect_objects_from_collections(imported_local_collections):
                    localized_obj = localize_imported_object_instance(obj)
                    if localized_obj is not None:
                        imported_local_objects.append(localized_obj)

                finalized_objects = []
                for obj in unique_datablocks(imported_local_objects):
                    localized_curve_obj = localize_imported_secret_paint_curve(obj)
                    if localized_curve_obj is not None:
                        finalized_objects.append(localized_curve_obj)

                remove_imported_linked_collections(imported_collections)

                imported_local_collections = collect_collection_hierarchy(localized_root_collections)
                imported_local_objects = collect_objects_from_collections(imported_local_collections)
                if finalized_objects:
                    imported_local_objects = collect_objects_from_collections(imported_local_collections)
                return imported_local_objects, imported_local_collections

        imported_local_objects = []
        for obj in imported_objects:
            localized_obj = localize_imported_object_instance(obj)
            if localized_obj is not None:
                imported_local_objects.append(localized_obj)

        finalized_objects = []
        for obj in unique_datablocks(imported_local_objects):
            localized_curve_obj = localize_imported_secret_paint_curve(obj)
            if localized_curve_obj is not None:
                finalized_objects.append(localized_curve_obj)

        imported_local_objects = unique_datablocks([obj for obj in finalized_objects if datablock_exists(obj, bpy.data.objects)])
        imported_local_collections = unique_datablocks([
            coll for obj in imported_local_objects
            for coll in obj.users_collection
            if datablock_exists(coll, bpy.data.collections)
        ])
        return imported_local_objects, imported_local_collections

    def ensure_custom_shape_collection(imported_objects, imported_collections, target_parent_collection=None, preferred_parent_collection=None):
        widget_parent_collection = preferred_parent_collection or target_parent_collection or bpy.context.view_layer.active_layer_collection.collection
        widget_collection = None
        for coll in imported_collections:
            if "widget" in coll.name.lower():
                widget_collection = coll
                break

        if widget_collection and not collection_is_in_scene(widget_collection):
            try:
                widget_parent_collection.children.link(widget_collection)
            except Exception as ex:
                print(f"---####### LINK WIDGET COLLECTION ERROR {widget_collection.name}: {ex}")

        orphan_custom_shapes = []
        seen_custom_shapes = set()
        for obj in imported_objects:
            if obj.type != "ARMATURE" or not getattr(obj, "pose", None):
                continue
            for pose_bone in obj.pose.bones:
                custom_shape = pose_bone.custom_shape
                if custom_shape is None:
                    continue
                try:
                    custom_shape_pointer = custom_shape.as_pointer()
                except Exception:
                    custom_shape_pointer = None
                if custom_shape_pointer and custom_shape_pointer in seen_custom_shapes:
                    continue
                if custom_shape_pointer:
                    seen_custom_shapes.add(custom_shape_pointer)
                if len(custom_shape.users_collection) == 0:
                    orphan_custom_shapes.append(custom_shape)

        if not orphan_custom_shapes:
            return

        if widget_collection is None or not datablock_exists(widget_collection, bpy.data.collections):
            widget_collection = bpy.data.collections.new("Widgets")
            widget_collection.hide_viewport = True
            widget_collection.hide_render = True
            widget_parent_collection.children.link(widget_collection)

        for custom_shape in orphan_custom_shapes:
            try:
                widget_collection.objects.link(custom_shape)
            except Exception as ex:
                print(f"---####### LINK CUSTOM SHAPE ERROR {custom_shape.name}: {ex}")

    def localize_widget_helper_data(imported_objects, imported_collections):
        helper_objects = []
        helper_pointer_set = set()

        def add_helper_object(obj):
            if obj is None or not datablock_exists(obj, bpy.data.objects):
                return
            try:
                obj_pointer = obj.as_pointer()
            except:
                obj_pointer = None
            if obj_pointer and obj_pointer in helper_pointer_set:
                return
            if obj_pointer:
                helper_pointer_set.add(obj_pointer)
            helper_objects.append(obj)

        for coll in imported_collections:
            if "widget" not in coll.name.lower():
                continue
            try:
                for obj in coll.all_objects:
                    if obj in imported_objects:
                        add_helper_object(obj)
            except:
                continue

        for obj in imported_objects:
            if obj.name.startswith("WGT-"):
                add_helper_object(obj)
            if obj.type != "ARMATURE" or not getattr(obj, "pose", None):
                continue
            for pose_bone in obj.pose.bones:
                add_helper_object(pose_bone.custom_shape)

        for helper_obj in helper_objects:
            helper_data = getattr(helper_obj, "data", None)
            if helper_data is None:
                continue
            helper_shape_keys = getattr(helper_data, "shape_keys", None)
            needs_local_data = (
                getattr(helper_data, "library", None)
                or getattr(helper_data, "override_library", None)
                or (helper_shape_keys and (getattr(helper_shape_keys, "library", None) or getattr(helper_shape_keys, "override_library", None)))
            )
            if not needs_local_data:
                continue
            try:
                helper_obj.data = helper_data.copy()
            except Exception as ex:
                print(f"---####### COPY HELPER DATA ERROR {helper_obj.name}: {ex}")

    if justImport == False:
        if activeobj == None or activeobj.type not in ["CURVES","CURVE","MESH"]:
            if not switch_asset and _secret_paint_world_paint_enabled(context):
                targetless_world_paint_import = True
                activeobj = None
                current_mode = "OBJECT"
            else:
                self.report({'ERROR'}, "Select a Mesh object first")
                return {'FINISHED'}
        else:
            current_mode = bpy.context.object.mode
            ensure_object_mode_for_import(activeobj, "paint_from_library")

    elif justImport:
        if activeobj:
            current_mode = bpy.context.object.mode
            ensure_object_mode_for_import(activeobj, "paint_from_library_justimport")



    # original_selection=bpy.context.selected_objects #to determine if going to paint mode or just importing the asset to the 3d cursor
    objselection = bpy.context.selected_objects
    # if activeobj not in objselection: objselection.append(activeobj)

    if bpy.app.version_string >= "4.0.0":
        current_library_name = context.area.spaces.active.params.asset_library_reference
    elif bpy.app.version_string < "4.0.0":
        current_library_name = context.area.spaces.active.params.asset_library_ref
        if current_library_name == "ALL":  # For some reason the relative path stops at the ID container in local file
            self.report({'ERROR'}, "Select an Asset Library in the side panel (can't be set to 'ALL') (fixed in Blender 4.0)")
            return {'FINISHED'}

    #SELECT COLLECTION OF ACTIVE OR put into hidden one (create hidden one if not found)
    original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
    new_coll_was_created_so_hide_viewport=False
    coll_to_hide = None

    # print("##########@@@@@@@@@@@@#############-----------------",bpy.context.view_layer.active_layer_collection)
    #CHOOSE COLLECTION DESTINATION BASED ON "HIDE IMPORTED CHECKBOX" (only needed if we're importing AND painting)   -- when just importing,put everything in active collection. when paint importing, use the terrain's collection. when hidden, create in already active collection, or reference existing wherever it is
    if justImport == False:
        if bpy.context.preferences.addons[__package__].preferences.checkboxHideImported: #if context.scene.mypropertieslist.checkboxHideImported: #make hidden collection active, or create it
            all_collections = []
            for top_level_collection in bpy.context.scene.collection.children:
                add_collections_to_list(top_level_collection, all_collections)
            for coll in all_collections: #all scene collections and subcollections
                if coll.name.startswith("Secret Assets"):
                    print("SEEEEEEE FOUNDDDDDDDDDDDDDDDDDDDDDDD")
                    FoundHiddenCollection = recurLayerCollection(bpy.context.view_layer.layer_collection, coll.name)
                    FoundHiddenCollection_status = coll.hide_viewport
                    coll.hide_viewport = False  # FoundHiddenCollection.hide_viewport = False #has to be visible in order to append the assets inside of it
                    bpy.context.view_layer.active_layer_collection = FoundHiddenCollection
                    coll_to_hide = coll   # can't use FoundHiddenCollection as variable because it's that weird "layer coll" version of the same collection
                    break
            if not bpy.context.view_layer.active_layer_collection.name.startswith("Secret Assets"): #CREATE HIDDEN COLLECTION
                print("CREAAAAAAAAAAAAAAAAAATTTTTTT")
                new_coll_was_created_so_hide_viewport =True
                new_coll = bpy.data.collections.new("Secret Assets")
                bpy.context.view_layer.active_layer_collection.collection.children.link(new_coll) #link into active collection    # bpy.context.scene.collection.children.link(new_coll) #link into scene
                bpy.context.view_layer.active_layer_collection = recurLayerCollection(bpy.context.view_layer.layer_collection, new_coll.name)
        else:
            if activeobj is not None:
                Coll_of_Active = []
                for i in activeobj.users_collection:
                    layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)
                    bpy.context.view_layer.active_layer_collection = Coll_of_Active




    print("")
    print("")
    print("")
    print("@@@@@@@@@@ new loop @@@@@@@@")
    print("")
    print("")
    print("")


    if bpy.app.version_string >= "4.0.0": sel_assets = context.selected_assets
    elif bpy.app.version_string < "4.0.0": sel_assets = context.selected_asset_files
    for asset_file in sel_assets:
        # print("--paint from library -- ACTIVE COLLECTION:",bpy.context.view_layer.active_layer_collection)
        # print(dir(asset_file))  #['__doc__', '__module__', '__slots__', 'bl_rna', 'full_library_path', 'full_path', 'id_type', 'local_id', 'metadata', 'name', 'rna_type']

        #IF LOCAL ASSETS: (already in blend file marked as assets)
        if current_library_name == "LOCAL":  # For some reason the relative path stops at the ID container in local file

            if bpy.app.version_string >= "4.0.0":
                asset_fullpath = asset_file.local_id  # Object\HumanRef_VeryLowPoly\HumanRef_VeryLowPoly   #Includes the path to the asset inside the .blend file
                asset_type = asset_file.id_type.lower().capitalize()  # "OBJECT" transformed into "Object"
            elif bpy.app.version_string < "4.0.0":
                library_path = Path(bpy.data.filepath)  # Will be "." if file has never been saved
                asset_fullpath = library_path / asset_file.relative_path
                asset_fullpath /= asset_file.local_id.name  # Includes the path to the asset inside the .blend file
                # asset_name = asset_fullpath.name  # humanmodel
                # asset_filepath = asset_fullpath  # //fjifg.blend
                asset_type = asset_fullpath.parent.parent.name  # whole path and then /object or /collection


            #PAINT OR SWITCH BRUSH ASSET
            if switch_asset:
                if asset_type == "Object": paintbrushswitch_f(self, context, activeobj=bpy.data.objects[asset_fullpath.name], objselection=[activeobj], current_mode=current_mode)   #(self, context, event)
                elif asset_type == "Collection":
                    # # STOP IF SWITCHING TO A COLLECTION THAT'S NOT PAINT BRUSH FRIENDLY (if it contains subcollections or other weird object you can't use it as brush for secret paint)
                    # if coll:
                    #     print("This collection is not usable as Brush for a Paint System.")
                    paintbrushswitch_f(self, context, activeobj=activeobj, objselection=[x for x in bpy.data.collections[asset_fullpath.name].all_objects], current_mode=current_mode)   #(self, context, event)

            else: #(if not switching asset, PAINT)
                if asset_type == "Object": brush_to_paint_with=[bpy.data.objects[asset_fullpath.name]]
                elif asset_type == "Collection":
                    brush_to_paint_with=[]
                    for oibj in bpy.data.collections[asset_fullpath.name].all_objects:
                        if oibj.name.startswith("Secret Paint Biome"): brush_to_paint_with = [j for j in oibj.children if j.type=="CURVES" and j.modifiers and j.data.name.startswith("Secret Paint")]
                    if not brush_to_paint_with: brush_to_paint_with = [x for x in bpy.data.collections[asset_fullpath.name].all_objects]
                if targetless_world_paint_import:
                    remember_asset_browser_world_paint_source(brush_to_paint_with)
                    bpy.context.view_layer.active_layer_collection = original_collection
                    continue
                mark_asset_browser_q_sources(brush_to_paint_with)
                secretpaint_function(
                    self,
                    context,
                    event,
                    activeobj=activeobj,
                    objselection=brush_to_paint_with,
                    defer_enter_paint_mode=defer_world_paint_start,
                    allow_auto_assembly_on_q=False,
                )
                bpy.context.view_layer.active_layer_collection = original_collection


        #ELSE IF EXTERNAL ASSET LIBRARY:
        else:
            if bpy.app.version_string >= "4.0.0":
                asset_filepath = asset_file.full_library_path  # prints this > C:\Users\loren\Assets\3D\objects\forest nature plants cabin evermotion.blend         but if manual mode it needs to be converted into this "C:/Users/loren/Assets/3D/objects/forest nature plants cabin evermotion.blend"
                asset_type = asset_file.id_type.lower().capitalize()   #"OBJECT" transformed into "Object"
                asset_name = asset_file.name  #AE_15TH_ROCK_04
            elif bpy.app.version_string < "4.0.0":
                library_path = Path(context.preferences.filepaths.asset_libraries.get(current_library_name).path)
                asset_fullpath = library_path / asset_file.relative_path  # Includes the path to the asset inside the .blend file
                asset_name = asset_fullpath.name  # humanmodel
                asset_filepath = asset_fullpath.parent.parent  # //fjifg.blend
                asset_type = asset_fullpath.parent.name  # object /collection     #os.path.basename(asset_fullpath.parent)


            all_previous_objects = set(bpy.data.objects)
            all_previous_nodes = set(bpy.data.node_groups)
            all_previous_materials = set(bpy.data.materials)
            all_previous_collections = set(bpy.data.collections)
            all_previous_shape_keys = set(bpy.data.shape_keys)


        ##########################################################################

            if bpy.app.version_string >= "4.0.0": import_setting = bpy.context.space_data.params.import_method
            elif bpy.app.version_string < "4.0.0": import_setting = bpy.context.space_data.params.import_type

            requested_link_import = import_setting == 'LINK'

            try: #FOR SOME REASON IT FAILS FOR STRANGE CONFLICT, BUT STILL WORKS
                if requested_link_import:  #import_type
                    bpy.ops.wm.link(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                    directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                    instance_collections=False, active_collection=True,do_reuse_local_id=False)
                elif import_setting == 'APPEND':  # link or append     #import_type
                    bpy.ops.wm.append(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                      directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                      instance_collections=False, active_collection=True)
                else: #append_reuse, follow preferences
                    bpy.ops.wm.append(filepath=os.path.join(asset_filepath, asset_type, asset_name),
                                      directory=os.path.join(asset_filepath, asset_type), filename=asset_name,
                                      instance_collections=False, active_collection=True, do_reuse_local_id=True)
            except: print("---- ERROR IMPORTT")


            # #RESTORE ORIGINAL SELECTION (importing objects changes selection)
            # for x in bpy.context.selected_objects: x.select_set(False)
            # for x in objselection: x.select_set(True)
            # if activeobj: bpy.context.view_layer.objects.active = activeobj




            # orenpaint_update_modifier_f(context, Forced_Update=True)



            imported_linked_objects = [obj for obj in bpy.data.objects if obj not in all_previous_objects and obj.library]
            imported_linked_collections = [coll for coll in bpy.data.collections if coll not in all_previous_collections and coll.library]
            imported_linked_materials = [mat for mat in bpy.data.materials if mat not in all_previous_materials and mat.library]
            imported_linked_shape_keys = [shape_key for shape_key in bpy.data.shape_keys if shape_key not in all_previous_shape_keys and shape_key.library]

            imported_all_objects = [obj for obj in bpy.data.objects if obj not in all_previous_objects]
            imported_all_collections = [coll for coll in bpy.data.collections if coll not in all_previous_collections]

            if requested_link_import:
                import_target_collection = bpy.context.view_layer.active_layer_collection.collection
                imported_all_objects, imported_all_collections = finalize_linked_import_as_local_hierarchy(
                    imported_linked_objects,
                    imported_linked_collections,
                    import_target_collection,
                    asset_type,
                    asset_name,
                )
                remove_unused_hidden_override_collections([coll for coll in bpy.data.collections if coll not in all_previous_collections])

            imported_root_local_collections = imported_root_collections(imported_all_collections) if imported_all_collections else []
            widget_parent_collection = imported_root_local_collections[0] if imported_root_local_collections else bpy.context.view_layer.active_layer_collection.collection
            ensure_custom_shape_collection(
                imported_all_objects,
                imported_all_collections,
                target_parent_collection=bpy.context.view_layer.active_layer_collection.collection,
                preferred_parent_collection=widget_parent_collection,
            )

            new_obs = [obj for obj in imported_all_objects if datablock_exists(obj, bpy.data.objects) and len(obj.users_collection) >= 1 and not obj.library]
            if not new_obs:
                print("----ERROR no new_obs")
                return{'FINISHED'} #with append-reuse: importing same collection doesn't work


            # #MARK COLLECTION AS ASSET (have to for loop twice because the first time it gets cancelled and transformed into lib override, so I have to find it again)
            # all_collections=[]
            # for top_level_collection in bpy.context.scene.collection.children:
            #     add_collections_to_list(top_level_collection,all_collections)
            # all_with_new_collections = all_collections
            # for coll in all_with_new_collections:#bpy.data.collections: #bpy.context.view_layer.layer_collection.children:  #bpy.context.scene.collection.children
            #     if coll not in all_previous_collections:
            #         coll.asset_mark()
            #         coll.asset_generate_preview()


            # #TEMPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
            # print("------------------", [x.name for x in new_obs])
            # for ob in new_obs:
            #     ob.make_local()
            # print("------------------",[x.name for x in new_obs])
            # for ob in new_obs:
            #     if ob.name not in bpy.context.view_layer.objects:
            #         print("# Not in View layer", ob.name)
            #
            # return{'FINISHED'}

            #LOCALIZE MATERIALS ON THE IMPORTED LOCAL OBJECTS ONLY.
            editable_new_obs = [obj for obj in new_obs if not obj.library]
            all_materials = []
            imported_material_cache = {}
            for ob in editable_new_obs:
                # print("Â§Â§Â§Â§Â§Â§Â§Â§Â§Â§ PROCESSING: ",ob)
                for mat_slot in ob.material_slots:
                    if mat_slot.material:
                        mat = _secret_paint_safe_material_for_assignment(mat_slot.material, imported_material_cache)
                        if mat is None:
                            continue
                        mat_slot.link = 'OBJECT'
                        try:
                            mat_slot.material = mat
                        except:
                            print("---####### ERROR: ",ob.name, mat_slot.material )
                        if mat not in all_materials and mat != None:
                            all_materials.append(mat)
            for matery in all_materials:
                if matery.library or matery.override_library:
                    make_import_local(matery, f"material {matery.name}")
            # for ob in new_obs:
                #REMOVE DUPLICATES
                # if ob.name in bpy.context.view_layer.objects:
                #     print("# Ã©Ã©Ã©Ã©Ã©Ã©Ã©Ã©Ã©Ã© INNNNNNNNN", ob.name)
                # if ob.name not in bpy.context.view_layer.objects: print("# Ã©Ã©Ã©Ã©Ã©Ã©Ã©Ã©Ã©Ã© Not in View layer", ob.name)
                # else: print("# @@@@@@@  INNN", ob.name)
                    # new_obs.remove(ob)
                    # bpy.data.objects.remove(ob,do_unlink=True)

                # ob.make_local()
                # # if ob.data.library:
                # ob['Secret Origin'] = ob.data.library
                # if ob.type in ["CURVES", "CURVE","LIGHT"]: ob.data.make_local()  # LOCALIZE HAIR CURVES and CURVE    ob.data = ob.data.copy()
                # secret_material_list=[]
                # for mat_slot in ob.material_slots:
                #     loop = 0
                #     if mat_slot.material:
                #         originalmat = mat_slot.material
                #         print("@@@@@@ MATERIAL:", originalmat, "matslot: ", mat_slot)
                #
                #         #CHECK IF THIS LINKED MATERIAL WAS MADE LOCAL BEFORE, if so: reference the localized material
                #         found_materiall=[]
                #         for obk in bpy.data.objects:
                #
                #         #     if "Secret Origin" in obk and "Secret Materials" in obk and obk['Secret Origin'] == ob.data.library:
                #         #         for matx in obk['Secret Materials']:
                #         #             if matx[0]==originalmat.name: found_materiall = bpy.data.materials[matx[1]]
                #         #             if found_materiall: break
                #         #     if found_materiall: break
                #
                #             for prop_name, _ in ob.items():
                #                 if prop_name.startswith("Secret Materials") and _[0] == originalmat and obk['Secret Origin'] == ob.data.library:
                #                     if _[0]==originalmat: found_materiall = _[1]
                #                 if found_materiall: break
                #             if found_materiall: break
                #
                #         #ASSIGN THE PREVIOUSLY LOCALIZED MATERIAL OR LOCALIZE IT NOW
                #         mat_slot.link = 'OBJECT'
                #         if found_materiall:
                #             try:mat_slot.material = found_materiall
                #             except:
                #                 print("------######## ERROR111")
                #                 # print("NOT MATERIALLL", ob,mat_slot.material.name, mat_slot )
                #         else:
                #             try:mat_slot.material = originalmat
                #             except:
                #                 print("------####### ERROR22222222")
                #                 # print("NOT MATERIALLL222", ob,mat_slot.material.name, mat_slot )
                #             originalmat.make_local()
                #         loop += 1
                #         ob['Secret Materials ' + str(loop)] = (originalmat,mat_slot.material)
                #         # ob['Secret Materials'+str(mat_slot.material)]=mat_slot.material
                #         # secret_material_list.append((originalmat, mat_slot.material))  #secret_material_list.append((originalmat.name, mat_slot.material.name))
                #
                # # print("Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°",secret_material_list)
                # # ob['Secret Materials'] = secret_material_list  #[(mat, newmat) for mat_slot in ob.material_slots if mat_slot.material]


                # if ob.data.library:
                #     ob.make_local()
                #     ob['Secret Origin'] = ob.data.library
                #     if ob.type in ["CURVES", "CURVE","LIGHT"] and ob.data.library: ob.data.make_local()  # LOCALIZE HAIR CURVES and CURVE    ob.data = ob.data.copy()
                #     secret_material_list=[]
                #     for mat_slot in ob.material_slots:
                #         if mat_slot.material:
                #             originalmat = mat_slot.material
                #
                #             #CHECK IF THIS LINKED MATERIAL WAS MADE LOCAL BEFORE, if so: reference the localized material
                #             found_materiall=[]
                #             for obk in bpy.data.objects:
                #                 if "Secret Origin" in obk and "Secret Materials" in obk and obk['Secret Origin'] == ob.data.library:
                #                     for matx in obk['Secret Materials']:
                #                         if matx[0]==originalmat.name: found_materiall = bpy.data.materials[matx[1]]
                #                         if found_materiall: break
                #                 if found_materiall: break
                #
                #             #ASSIGN THE PREVIOUSLY LOCALIZED MATERIAL OR LOCALIZE IT NOW
                #             mat_slot.link = 'OBJECT'
                #             if found_materiall: mat_slot.material = found_materiall
                #             else:
                #                 mat_slot.material = originalmat
                #                 originalmat.make_local()
                #             secret_material_list.append((originalmat.name, mat_slot.material.name))
                #
                #     ob['Secret Materials'] = secret_material_list  #[(mat, newmat) for mat_slot in ob.material_slots if mat_slot.material]










            # # UPDATE ORENPAINT (force it if there's an orenpaint.001: when appending biomes, it imports the node with orenpaint.001)
            # secretpaint_update_modifier_f(context, check_for_dupli_nodes=True, Forced_Update=True)  # forcing update because it might be the first

            #LOCALIZE ALL NODE TREES
            new_nodes = [node for node in bpy.data.node_groups if node not in all_previous_nodes]
            for node in new_nodes:
                if node.library or node.override_library:
                    make_import_local(node, f"node {node.name}")

            for matery in imported_linked_materials:
                if datablock_exists(matery, bpy.data.materials) and matery.users == 0:
                    try:
                        bpy.data.materials.remove(matery, do_unlink=True)
                    except Exception as ex:
                        print(f"---####### REMOVE LINKED MATERIAL ERROR {matery.name}: {ex}")

            for node in new_nodes:
                if datablock_exists(node, bpy.data.node_groups) and node.library and node.users == 0:
                    try:
                        bpy.data.node_groups.remove(node, do_unlink=True)
                    except Exception as ex:
                        print(f"---####### REMOVE LINKED NODE ERROR {node.name}: {ex}")

            offscene_removed_data_blocks = remove_imported_linked_objects_outside_scene(imported_linked_objects)
            remove_zero_user_linked_data_blocks(offscene_removed_data_blocks)
            localized_imported_shape_keys = localize_imported_shape_keys(imported_linked_shape_keys)

            remove_zero_user_imported_linked_objects(imported_linked_objects)
            remove_zero_user_shape_key_owner_data(imported_linked_objects, imported_linked_shape_keys)

            for shape_key in imported_linked_shape_keys:
                if datablock_exists(shape_key, bpy.data.shape_keys) and shape_key.users == 0:
                    try:
                        bpy.data.shape_keys.remove(shape_key, do_unlink=True)
                    except Exception as ex:
                        print(f"---####### REMOVE LINKED SHAPE KEY ERROR {shape_key.name}: {ex}")

            debug_print_linked_shape_key_owners(imported_linked_shape_keys, "post_import_cleanup")



            movable_import_roots = imported_root_objects(new_obs)
            if not movable_import_roots:
                movable_import_roots = new_obs[:]

            visible_import_roots = [obj for obj in movable_import_roots if obj.visible_get()]
            if not visible_import_roots:
                visible_import_roots = movable_import_roots[:]

            obs_without_parent_for_recenter_coll_origin = [obj for obj in visible_import_roots if obj.type != "EMPTY"]
            if not obs_without_parent_for_recenter_coll_origin:
                obs_without_parent_for_recenter_coll_origin = [obj for obj in new_obs if obj.visible_get() and obj.type != "EMPTY"]
            if not obs_without_parent_for_recenter_coll_origin:
                obs_without_parent_for_recenter_coll_origin = visible_import_roots[:] if visible_import_roots else new_obs[:]

            terrains_with_hair = []
            biome_to_use_as_paint = None
            imported_biome_surface = None
            for obj in new_obs:
                if is_imported_secret_paint_curve(obj) and obj.parent and obj.parent not in terrains_with_hair:
                    terrains_with_hair.append(obj.parent)

            for terrain in terrains_with_hair:
                current_biome = []
                for hairChild in terrain.children:
                    if is_imported_secret_paint_curve(hairChild) and hairChild not in current_biome:
                        current_biome.append(hairChild)
                if current_biome and (biome_to_use_as_paint is None or len(current_biome) > len(biome_to_use_as_paint)):
                    biome_to_use_as_paint = current_biome
                    imported_biome_surface = terrain

            reference_objects_for_move = [imported_biome_surface] if imported_biome_surface else obs_without_parent_for_recenter_coll_origin
            if not reference_objects_for_move:
                reference_objects_for_move = visible_import_roots[:] if visible_import_roots else new_obs[:]
            reference_bounds = imported_object_bounds(reference_objects_for_move)
            relocation_delta = Vector((0.0, 0.0, 0.0))


            #DECIDE WETHER TO PAINT OR JUST IMPORT OR SWITCH ASSET
            # # if len(original_selection) == 0 and current_mode == "OBJECT" or justImport:
            activated_scatter = False
            if justImport:
                if reference_bounds:
                    relocation_delta = bpy.context.scene.cursor.location - reference_bounds["center"]


            # if activeobj.type == "MESH" and current_mode == "OBJECT" \
            elif activeobj is not None and (
                activeobj.type == "MESH" and current_mode == "OBJECT"
                or activeobj.type == "CURVES" and current_mode == "OBJECT"
                or activeobj.type == "MESH" and current_mode == "WEIGHT_PAINT"
                or activeobj.type == "CURVES" and current_mode == "SCULPT_CURVES"
            ):     # and len(original_selection) >= 1

                if switch_asset == False: activated_scatter = True #DON'T PAINT IF SWITCHING ASSET

                if activeobj.type=="CURVES":
                    terrainobj = activeobj.parent if activeobj.parent else activeobj   #.data.surface
                else: terrainobj = activeobj

                target_bounds = imported_object_bounds([terrainobj])
                if target_bounds and reference_bounds:
                    relocation_delta = Vector((
                        target_bounds["max"].x - reference_bounds["min"].x,
                        target_bounds["center"].y - reference_bounds["center"].y,
                        target_bounds["min"].z - reference_bounds["min"].z,
                    ))


            # #LINK HIDDEN OBJECTS TO THE NEWEST COLLECTION
            # main_new_collection = None
            # for coll in all_with_new_collections[:]:  # bpy.data.collections: #bpy.context.view_layer.layer_collection.children:  #bpy.context.scene.collection.children
            #     if coll not in all_previous_collections: main_new_collection = coll
            # for obj in new_obs:
            #     if obj.name not in bpy.context.view_layer.objects: bpy.data.collections[main_new_collection.name].objects.link(obj)


            #MOVE TO CURSOR
            # selected_objects = bpy.context.selected_objects
            for obj in movable_import_roots:
                obj.location += relocation_delta
                # if not obj.padrent:
                if False:
                    # print("Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°Â°",obj.name)
                    # if obj.name.startswith("Rename this rig"): print("MOOOOOOVE", obj.name, obj.location)
                    obj.location += target_location - Vector(center) #ONLY MOVE OBJS THAT HAVE NO PARENT                    # print("JUST MOOVEEEEEED",obj.name)
                    obs_without_parent_for_recenter_coll_origin.append(obj)

                    # if obj.name.startswith("Rename this rig"): print("AFTEEEEEER", obj.name, obj.location)

            # #RECENTER COLLECTION INSTANCES
            # orengrouprecentercollectionobj_function(context, objselection=obs_without_parent_for_recenter_coll_origin)       #new_obs
            # # #INSTANCE COLL
            # # instancecollfromactiveobj_f(self,context, activeobj=new_obs[0])


            #LIST ALL BIOME SURFACES (if two of the imported objs are orencurves and share same parent: biome detected, select only those
            biome_to_use_as_paint=[]
            terrains_with_hair=[]
            for obj in new_obs:
                if obj.type == "CURVES":
                    if obj.modifiers:
                        for modif in obj.modifiers:
                            if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                if obj.parent and obj.parent not in terrains_with_hair: terrains_with_hair.append(obj.parent)  #and obj.parent.library == None

            #FIND BIOME WITH THE MOST HAIR OUT OF ALL FOUND BIOMES
            if len(terrains_with_hair) >=1:
                # for x in bpy.context.selected_objects: x.select_set(False) #objselection
                biome_to_use_as_paint = None
                for terrain in terrains_with_hair:

                    current_biome = []
                    for hairChild in terrain.children:
                        if hairChild.type == "CURVES" and hairChild.modifiers:
                                for modif in hairChild.modifiers:
                                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name.startswith("Secret Paint"):
                                        if hairChild not in current_biome: current_biome.append(hairChild)
                    if current_biome and biome_to_use_as_paint and len(current_biome) > len(biome_to_use_as_paint) or biome_to_use_as_paint==None: biome_to_use_as_paint = current_biome

                # print("KKKK")
                # for hair in terrains_with_hair[0].children:
                #     # bpy.data.objects[hair.name].select_set(True)
                #     biome_to_use_as_paint.append(hair)

            # USE THE SINGLE OBJECTS !!!!! if the object marked as asset has a parent (for example an empty as common pivot) then the painting function will get mulitple selected objects and try to scatter the collection, so when importing object asset types from asset browser only specity the one that doesn't have any parents
            # else: biome_to_use_as_paint = new_obs
            elif asset_type == "Collection": biome_to_use_as_paint = new_obs
            elif asset_type == "Object": biome_to_use_as_paint = [obs_without_parent_for_recenter_coll_origin[0]]
            # return{'FINISHED'}



            # UPDATE ORENPAINT (force it if there's an orenpaint.001: when appending biomes, it imports the node with orenpaint.001)
            # print("UPDAAAAAAAAAAAT IMPORTED")
            secretpaint_update_modifier_f(context,upadte_provenance="def paint_from_library_function(self, context, event, **kwargs)")  # forcing update because it might be the first    #check_for_dupli_nodes=True

            # print (biome_to_use_as_paint)
            # print (activeobj)
            # print(activated_scatter)

            # for obj in biome_to_use_as_paint:obj.select_set(True)
            # for obj in biome_to_use_as_paint:
            #     try:obj.select_set(True)
            #     except:pass


            # #PAINT else don't paint, then select the imported objects
            importpainting_multiple_assets = True if len(sel_assets) >=2 else False
            if targetless_world_paint_import:
                remember_asset_browser_world_paint_source(biome_to_use_as_paint if biome_to_use_as_paint else new_obs)

            elif activated_scatter:
                mark_asset_browser_q_sources(biome_to_use_as_paint)
                print("Â§Â§Â§Â§Â§Â§Â§Â§Â§Â§Â§Â§Â§ activated scatter", activeobj.name,"biome_to_use_as_paint", [x.name for x in biome_to_use_as_paint])
                secretpaint_function(
                    self,
                    context,
                    event,
                    activeobj=activeobj,
                    objselection=biome_to_use_as_paint,
                    importpainting_multiple_assets=importpainting_multiple_assets,
                    defer_enter_paint_mode=defer_world_paint_start,
                    allow_auto_assembly_on_q=False,
                )
                # return{'FINISHED'}


            elif switch_asset:
                if asset_type == "Object":
                    paintbrushswitch_f(self, context, activeobj=biome_to_use_as_paint[0], objselection=[activeobj], current_mode=current_mode)   #(self, context, event)
                elif asset_type == "Collection":
                    # # STOP IF SWITCHING TO A COLLECTION THAT'S NOT PAINT BRUSH FRIENDLY (if it contains subcollections or other weird object you can't use it as brush for secret paint)
                    # if coll:
                    #     print("This collection is not usable as Brush for a Paint System.")
                    paintbrushswitch_f(self, context, activeobj=activeobj, objselection=biome_to_use_as_paint, current_mode=current_mode)   #(self, context, event)

            elif justImport:   # SELECT NEWLY IMPORTED   #else
                for obj in new_obs:
                    try:
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                    except:pass



            # if activated_scatter:
            #     if copy_hair_settings: #reselect original hair to copy settings
            #         bpy.context.view_layer.objects.active = activeobj
            #         activeobj.select_set(True)
            #     else: #reselect plane
            #         bpy.context.view_layer.objects.active = bpy.data.objects[terrainobj.name]
            #         bpy.data.objects[terrainobj.name].select_set(True)
            #     orenpaint_function(self, context, event)
            # else: bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]


    if coll_to_hide: coll_to_hide.hide_viewport = FoundHiddenCollection_status #restore status, because it was activated in order to append assets inside of it
    if new_coll_was_created_so_hide_viewport: #hide the newly created collection at the end so that before I can append assets inside of it
        new_coll.hide_viewport = True
        new_coll.hide_render = True

    #ORIG COLLECTION
    # bpy.context.view_layer.active_layer_collection = original_collection


        # #UPDATE ORENPAINT (force it if there's an orenpaint.001: when appending biomes, it imports the node with orenpaint.001)
        # secretpaint_update_modifier_f(context, check_for_dupli_nodes=True,Forced_Update=True) #forcing update because it might be the first


    if targetless_world_paint_import:
        if asset_browser_world_paint_source is None:
            self.report({'WARNING'}, "Imported asset has no object that can be used as a paint source")
            return {'FINISHED'}
        secretpaint_mark_skip_auto_assembly_on_next_q(asset_browser_world_paint_source)
        return _secret_paint_schedule_world_paint_for_object(asset_browser_world_paint_source)

    if not justImport and _secret_paint_world_paint_enabled(context):
        active_after_import = context.active_object
        if _secret_paint_system_modifier(active_after_import) is not None:
            return _secret_paint_schedule_world_paint_for_object(active_after_import)

    return {'FINISHED'}
class paint_from_library(bpy.types.Operator):
    """Import and paint with the selected object or collection"""
    bl_idname = "secret.paint_from_library"
    bl_label = "Import Asset and Paint"
    bl_options = {'REGISTER', 'UNDO'}
    # @classmethod
    # def poll(cls, context):
    #     return context.selected_asset_files
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):  # reference:  orenscatter_modal_operator(bpy.types.Operator)
        # if event.shift: paint_from_library_function(self, context, event, switch_asset = True)
        # elif event.alt: paint_from_library_function(self, context, event, justImport = True)
        # else: paint_from_library_function(self, context, event)
        paint_from_library_function(self, context, event)
        return {'FINISHED'}
class paint_from_library_switch(bpy.types.Operator):
    """switch brush object from the asset library"""
    bl_idname = "secret.paint_from_library_switch"
    bl_label = "Import Asset and Switch"
    bl_options = {'REGISTER', 'UNDO'}
    # @classmethod
    # def poll(cls, context):
    #     return context.selected_asset_files
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def modal(self, context, event):  # reference:  orenscatter_modal_operator(bpy.types.Operator)
        paint_from_library_function(self, context, event, switch_asset = True)
        return {'FINISHED'}
class paint_from_library_justimport(bpy.types.Operator):
    """Just Import biome from library"""
    bl_idname = "secret.paint_from_library_justimport"
    bl_label = "Import Asset"
    bl_options = {'REGISTER', 'UNDO'}

    # @classmethod
    # def poll(cls, context):
    #     return context.selected_asset_files

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):  # reference:  orenscatter_modal_operator(bpy.types.Operator)
        paint_from_library_function(self, context, event, justImport = True)
        return {'FINISHED'}
def checkboxImportWithoutPainting_f(self, context):
    # self.layout.operator("secret.paint_from_library", icon= 'DECORATE_KEYFRAME', text="Paint")
    layout = self.layout
    row = layout.row(align=True)
    # layout.prop(context.scene.mypropertieslist, "checkboxImportWithoutPainting", text="", icon= 'BRUSH_DATA')
    # layout.operator("secret.importselected_assetfrombrowser", icon='BRUSH_DATA', text="Paint")
    # layout.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxHideImported", text="", icon='RESTRICT_RENDER_ON' if bpy.context.preferences.addons[__package__].preferences.checkboxHideImported else 'RESTRICT_RENDER_OFF')
    row.operator("secret.paint_from_library", icon='BRUSH_DATA', text="Paint")
    row.prop(bpy.context.preferences.addons[__package__].preferences, "checkboxHideImported", text="", icon='RESTRICT_RENDER_ON' if bpy.context.preferences.addons[__package__].preferences.checkboxHideImported else 'RESTRICT_RENDER_OFF')
    # layout.prop(context.scene.mypropertieslist, "checkboxTransferMaterialWithBiome", text="", icon= 'MATERIAL')
def shared_material_f(self,context):


    common_name = "Shared "+ str(context.scene.mypropertieslist.shared_material_index)

    if common_name not in bpy.data.node_groups:

        all_nodes_before_import =[node_tree for node_tree in bpy.data.node_groups]
        # all_nodes_before_import =set(node_tree for node_tree in bpy.data.node_groups)
        activeobj = bpy.context.active_object  # bpy.data.objects["armature"]     bpy.context.object["armature"]     <bpy_struct, Object("left") at 0x000001C2D10E5608>
        objselection = bpy.context.selected_objects  # bpy.context.selected_objects[0]   #bpy.context.scene.objects
        # USER = Path(resource_path('USER'))
        # src = USER / "scripts/addons" / "Secret Paint"
        # file_path = src / "Secret Paint.blend"
        # for mod in addon_utils.modules():
        #     if mod.bl_info.get("name") == "Secret Paint":
        #         file_path = os.path.dirname(mod.__file__) + "\Secret Paint.blend"
        #         break
        file_path = _secret_paint_source_blend_path()
        inner_path = "NodeTree"
        object_name = "Shared"
        bpy.ops.wm.append(
            filepath=os.path.join(file_path, inner_path, object_name),
            directory=os.path.join(file_path, inner_path),
            filename=object_name)
        all_nodes_after_import = [node_tree for node_tree in bpy.data.node_groups]
        # new_node= [all_nodes_after_import-all_nodes_before_import]
        new_node = [x for x in all_nodes_after_import if x not in all_nodes_before_import]
        # new_node= list(all_nodes_after_import-all_nodes_before_import)
        new_node[0].name = common_name
        bpy.context.view_layer.objects.active = activeobj
        for x in objselection: x.select_set(True)

        #CREATE NODE GROUP FROM SCRATCH
        # node_group = bpy.data.node_groups.new(name=common_name, type='ShaderNodeTree')
        #
        # ShaderNodeHueSaturation = node_group.nodes.new(type='ShaderNodeHueSaturation')
        # ShaderNodeHueSaturation.location = -200, 100
        #
        # ShaderNodeMixRGB1 = node_group.nodes.new(type='ShaderNodeMixRGB')
        # ShaderNodeMixRGB1.location = 0, 100
        # ShaderNodeMixRGB1.inputs[0].default_value = 1
        # ShaderNodeMixRGB1.blend_type = 'OVERLAY'
        # # ShaderNodeMixRGB1.hide_toggle
        # ShaderNodeRGB = node_group.nodes.new(type='ShaderNodeRGB')
        # ShaderNodeRGB.location = 0, 320
        # reroute_node = node_group.nodes.new(type='NodeReroute')
        # reroute_node.location = 200, 220
        #
        #
        # # # Add the HSV node to the node group
        # # hsv_node = node_group.nodes.new(type='ShaderNodeHueSaturation')
        # # hsv_node.location = (0, 0)  # Adjust the location as needed within the group
        #
        # # Add the HSV node to the node group
        # roughness_range = node_group.nodes.new(type='ShaderNodeMapRange')
        # roughness_range.location = (0, -150)  # Adjust the location as needed within the group
        # roughness_range.label="Roughness Map Range"
        #
        # # Connect the input and output of the node group
        # input_node = node_group.nodes.new(type='NodeGroupInput')
        # input_node.location = (-600, 0)  # You can adjust the location as needed
        # output_node = node_group.nodes.new(type='NodeGroupOutput')
        # output_node.location = (+300, 0)  # You can adjust the location as needed
        #
        # # Link the input and output sockets (updated socket names)
        # # node_group.inputs.new("NodeSocketColor", "Color")
        # # active_material.links.new(input_node.outputs[0], hsv_node.inputs["Color"])
        #
        # # node_group.inputs.new('NodeSocketColor', "Color")
        # # node_group.links.new(input_node.outputs["Color"], hsv_node.inputs["Color"])
        # # node_group.outputs.new('NodeSocketColor', "Base Color")
        # # node_group.links.new(hsv_node.outputs["Color"],output_node.inputs["Base Color"])
        # node_group.inputs.new('NodeSocketColor', "Color")
        # node_group.links.new(input_node.outputs["Color"], ShaderNodeHueSaturation.inputs["Color"])
        # node_group.outputs.new('NodeSocketColor', "Base Color")
        # node_group.links.new(ShaderNodeMixRGB1.outputs["Color"],output_node.inputs["Base Color"])
        #
        # node_group.inputs.new('NodeSocketFloat', "Roughness")
        # node_group.links.new(input_node.outputs["Roughness"], roughness_range.inputs["Value"])
        # node_group.outputs.new('NodeSocketFloat', "Roughness")
        # node_group.links.new(roughness_range.outputs["Result"],output_node.inputs["Roughness"])
        #
        #
        # # links.new(nodediffuse.outputs["Color"], ShaderNodeHueSaturation.inputs["Color"])
        # node_group.links.new(ShaderNodeHueSaturation.outputs["Color"], ShaderNodeMixRGB1.inputs["Color1"])
        # node_group.links.new(ShaderNodeRGB.outputs["Color"], reroute_node.inputs[0])
        # node_group.links.new(reroute_node.outputs[0], ShaderNodeMixRGB1.inputs["Color2"])
        # # node_group.links.new(ShaderNodeMixRGB1.outputs["Color"], node_principled.inputs["Base Color"])










    # FOLLOW THE STATUS OF THE ACTIVE OBJECT, TOGGLE FOR ALL SELECTED OBJECTS
    Remove_Enabled = False
    try: nodeys = bpy.context.active_object.active_material.node_tree.nodes
    except:
        self.report({'ERROR'}, "Select an object with at least one Material")
        return {'FINISHED'}
    for nod in nodeys:
        if nod.type=="GROUP" and nod.node_tree and nod.node_tree == bpy.data.node_groups.get(common_name): Remove_Enabled = True

    #ADD /UPDATE /TOGGLE REMOVE
    for obj in bpy.context.selected_objects:
        for mat_slot in obj.material_slots:
            if mat_slot.material:
                active_material=mat_slot.material

                for node in active_material.node_tree.nodes:
                    # node.select = False
                    if node.type == 'BSDF_PRINCIPLED':



                        #BASE COLOR
                        if node.inputs["Base Color"].links and node.inputs["Base Color"].links[0].from_node.type == "GROUP" and node.inputs["Base Color"].links[0].from_node.node_tree.name.startswith("Shared"):
                            if Remove_Enabled: #FOUND, SO TOGGLE REMOVE
                                output_sock = []
                                input_sock = []
                                for link in active_material.node_tree.links: # Store connections to the selected node
                                    if link.to_node == node.inputs["Base Color"].links[0].from_node: input_sock.append(link.from_socket)
                                    if link.from_node == node.inputs["Base Color"].links[0].from_node: output_sock.append(link.to_socket)
                                active_material.node_tree.nodes.remove(node.inputs["Base Color"].links[0].from_node) # Delete the selected node
                                for output in output_sock: # Reconnect input sockets to output sockets
                                    for input in input_sock:
                                        active_material.node_tree.links.new(output, input)

                            else: #FOUND BUT DIFFERENT INDEX SO UPDATE NODE INDEX
                                node.inputs["Base Color"].links[0].from_node.node_tree = bpy.data.node_groups.get(common_name)

                        elif not node.inputs["Base Color"].links and not Remove_Enabled: #NOTHING CONNECTED TO PRINCIPLEDbsdf
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y - 115)
                            active_material.node_tree.links.new(common_material_group.outputs["Base Color"], node.inputs["Base Color"])
                            common_material_group.inputs["Color"].default_value = node.inputs["Base Color"].default_value
                            common_material_group.select = True
                        elif not Remove_Enabled: #INSERT INBETWEEN EXISTING NODE CONNECTED TO PRINCIPLEDbsdf
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            # common_material_group.select = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)  # Replace "Common Material" with your actual node group name
                            common_material_group.location = (node.location.x - 160, node.location.y - 115) #(existing_node.location.x + (node.location.x - existing_node.location.x) / 2, existing_node.location.y)
                            existing_link = node.inputs["Base Color"].links[0]
                            existing_node = existing_link.from_node

                            output_sockets = []
                            for link in active_material.node_tree.links:  # Store connections to the selected node
                                if link.from_node == existing_node: output_sockets.append(link.to_socket)
                            if hasattr(existing_node, 'data_type') and existing_node.data_type=="RGBA": active_material.node_tree.links.new(existing_node.outputs[2], common_material_group.inputs["Color"])  #new mix node needs a special output link
                            else: active_material.node_tree.links.new(existing_node.outputs[existing_link.from_socket.name], common_material_group.inputs["Color"])
                            for output in output_sockets: # Reconnect input sockets to output sockets
                                active_material.node_tree.links.new(common_material_group.outputs["Base Color"], output)


                        #ROUGHNESS
                        if node.inputs["Roughness"].links and node.inputs["Roughness"].links[0].from_node.type == "GROUP" and node.inputs["Roughness"].links[0].from_node.node_tree.name.startswith("Shared"):
                            if Remove_Enabled: #FOUND, SO TOGGLE REMOVE
                                output_sock = []
                                input_sock = []
                                for link in active_material.node_tree.links: # Store connections to the selected node
                                    if link.to_node == node.inputs["Roughness"].links[0].from_node: input_sock.append(link.from_socket)
                                    if link.from_node == node.inputs["Roughness"].links[0].from_node: output_sock.append(link.to_socket)
                                active_material.node_tree.nodes.remove(node.inputs["Roughness"].links[0].from_node) # Delete the selected node
                                for output in output_sock: # Reconnect input sockets to output sockets
                                    for input in input_sock:
                                        active_material.node_tree.links.new(output, input)

                            else: #FOUND BUT DIFFERENT INDEX SO UPDATE NODE INDEX
                                node.inputs["Roughness"].links[0].from_node.node_tree = bpy.data.node_groups.get(common_name)

                        elif not node.inputs["Roughness"].links and not Remove_Enabled: #NOTHING CONNECTED TO PRINCIPLEDbsdf
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y - 304)
                            active_material.node_tree.links.new(common_material_group.outputs["Roughness"], node.inputs["Roughness"])
                            common_material_group.inputs["Roughness"].default_value = node.inputs["Roughness"].default_value
                            common_material_group.select = True
                        elif not Remove_Enabled: #INSERT INBETWEEN EXISTING NODE CONNECTED TO PRINCIPLEDbsdf
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            # common_material_group.select = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)  # Replace "Common Material" with your actual node group name
                            common_material_group.location = (node.location.x - 160, node.location.y - 280) #(existing_node.location.x + (node.location.x - existing_node.location.x) / 2, existing_node.location.y)
                            existing_link = node.inputs["Roughness"].links[0]
                            existing_node = existing_link.from_node

                            output_sockets = []
                            for link in active_material.node_tree.links:  # Store connections to the selected node
                                if link.from_node == existing_node: output_sockets.append(link.to_socket)
                            active_material.node_tree.links.new(existing_node.outputs[existing_link.from_socket.name], common_material_group.inputs["Roughness"])
                            for output in output_sockets: # Reconnect input sockets to output sockets
                                active_material.node_tree.links.new(common_material_group.outputs["Roughness"], output)


                        # #EMISSIVE


                    elif node.type == 'OUTPUT_MATERIAL':
                        #SHADER
                        if node.inputs["Surface"].links and node.inputs["Surface"].links[0].from_node.type == "GROUP" and node.inputs["Surface"].links[0].from_node.node_tree.name.startswith("Shared"):
                            if Remove_Enabled: #FOUND, SO TOGGLE REMOVE
                                output_sock = []
                                input_sock = []
                                for link in active_material.node_tree.links: # Store connections to the selected node
                                    if link.to_node == node.inputs["Surface"].links[0].from_node: input_sock.append(link.from_socket)
                                    if link.from_node == node.inputs["Surface"].links[0].from_node: output_sock.append(link.to_socket)
                                active_material.node_tree.nodes.remove(node.inputs["Surface"].links[0].from_node) # Delete the selected node
                                for output in output_sock: # Reconnect input sockets to output sockets
                                    for input in input_sock:
                                        active_material.node_tree.links.new(output, input)

                            else: #FOUND BUT DIFFERENT INDEX SO UPDATE NODE INDEX
                                node.inputs["Surface"].links[0].from_node.node_tree = bpy.data.node_groups.get(common_name)

                        elif not node.inputs["Surface"].links and not Remove_Enabled: #NOTHING CONNECTED TO MATERIAL OUTPUT
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)
                            common_material_group.location = (node.location.x - 160, node.location.y -38)
                            active_material.node_tree.links.new(common_material_group.outputs["Material Output"], node.inputs["Surface"])
                            # common_material_group.inputs["Color"].default_value = node.inputs["Base Color"].default_value
                            common_material_group.select = True
                        elif not Remove_Enabled: #INSERT INBETWEEN EXISTING NODE CONNECTED TO PRINCIPLEDbsdf
                            common_material_group = active_material.node_tree.nodes.new('ShaderNodeGroup')
                            common_material_group.hide = True
                            # common_material_group.select = True
                            common_material_group.node_tree = bpy.data.node_groups.get(common_name)  # Replace "Common Material" with your actual node group name
                            common_material_group.location = (node.location.x - 160, node.location.y -38) #(existing_node.location.x + (node.location.x - existing_node.location.x) / 2, existing_node.location.y)
                            existing_link = node.inputs["Surface"].links[0]
                            existing_node = existing_link.from_node

                            output_sockets = []
                            for link in active_material.node_tree.links:  # Store connections to the selected node
                                if link.from_node == existing_node: output_sockets.append(link.to_socket)
                            active_material.node_tree.links.new(existing_node.outputs[existing_link.from_socket.name], common_material_group.inputs["Shader"])
                            for output in output_sockets: # Reconnect input sockets to output sockets
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
        secretpaint_function(self, context,circulararray=True) # activeobj=bpy.context.active_object, objselection=[bpy.context.active_object])
        # bpy.ops.curve.primitive_bezier_circle_add(radius=1, enter_editmode=False, align='WORLD', location=bpy.context.scene.cursor.location, scale=(1, 1, 1))
        # bpy.context.object.modifiers["GeometryNodes"]["Input_65"][0] = 1.5708
        # bpy.context.object.modifiers["GeometryNodes"]["Input_65"][1] = 1.5708
        # bpy.context.object.location=bpy.context.object.location
        return {'FINISHED'}
class straight_array(bpy.types.Operator):
    """Quick Shortcut to create an instanced array with the selected object"""
    bl_idname = "secret.straight_array"
    bl_label = "Straight Array"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        secretpaint_function(self, context,straightarray=True) # activeobj=bpy.context.active_object, objselection=[bpy.context.active_object])
        # bpy.ops.curve.primitive_nurbs_path_add(radius=1, enter_editmode=False, align='WORLD', location=bpy.context.scene.cursor.location, scale=(1, 1, 1))
        return {'FINISHED'}
def context14438(self, context):
    activeobj = bpy.context.active_object
    objselection = bpy.context.selected_objects
    material_cache = {}

    if len(objselection) >=2:
        for hair in objselection:
            if hair.type == "CURVES" and hair.modifiers or hair.type == "CURVE" and hair.modifiers:
                for modif in hair.modifiers:  # modifier.name == "GeometryNodes"
                    if modif.type == 'NODES' and modif.node_group and modif.node_group.name == "Secret Paint":

                        try:
                            newmat = bpy.context.active_object.active_material.name
                        except AttributeError:
                            self.report({'ERROR'}, "There is no material to copy.") #actual pop up in mouse position
                            return {"CANCELLED"}

                        # bpy.ops.object.make_links_data(type='MATERIAL')
                        safe_materials = _secret_paint_collect_safe_materials_from_object(activeobj, material_cache)
                        _secret_paint_replace_curve_materials_from_sources(hair, safe_materials)
                                # hair.data.materials.append(None)
                                # hair.material_slots[i].material = mat_slot.material

                        bpy.context.view_layer.objects.active = hair

                        hair.modifiers[0]["Input_39"] = True
                        hair.modifiers[0]["Input_40"] = _secret_paint_safe_material_for_assignment(bpy.data.materials[newmat], material_cache)
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
def update_collapsed_list(self, context): # Empty function to be used as a callback for the property update
    pass
    return{'FINISHED'}
class switchtoweightzero(bpy.types.Operator):   # example of potential simple command
    """In Weight paint mode, press the shortcut to toggle between a value of 0 and 1"""
    bl_idname = "secret.switchtoweightzero"
    bl_label = "Toggle Weight 0/1"
    def execute(self, context):
        current_weight = _get_weight_paint_value(context, default=1)
        if current_weight == 0:
            _set_weight_paint_value(context, 1)
        else:
            _set_weight_paint_value(context, 0)

        return {'FINISHED'}
def curveseparate_function(context):

    activeobj = bpy.context.active_object
    activeobj.select_set(True)
    objselection = bpy.context.selected_objects
    # if activeobj not in objselection: objselection.append(activeobj)

    saveMode = bpy.context.object.mode
    material_cache = {}





    if bpy.context.object.mode == "OBJECT":
        if activeobj.type == "CURVES":
            for obj in objselection:

                Coll_of_Active = []
                for i in obj.users_collection:
                    layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)

                obj.select_set(False)
                newobj = obj.copy()
                bpy.data.collections[Coll_of_Active.name].objects.link(newobj)  # LINK TO COLLECTION
                newobj.data = bpy.data.hair_curves.new("Secret Paint")
                newobj.data.surface = obj.parent  #.data.surface
                for uvmap in newobj.parent.data.uv_layers:  #.data.surface   #bpy.context.object.data.uv_layers['UVMap.001'].active = True
                    if uvmap.active_render: newobj.data.surface_uv_map = uvmap.name
                bpy.context.view_layer.objects.active = newobj

                #link materials
                for material in _secret_paint_collect_safe_materials_from_object(obj, material_cache):
                    _secret_paint_append_material_once(newobj.data.materials, material)

            # for x in bpy.context.selected_objects: x.select_set(False) #objselection
            bpy.ops.object.mode_set(mode="SCULPT_CURVES")

        elif activeobj.type == "CURVE":
            for obj in objselection:

                Coll_of_Active = []
                for i in obj.users_collection:
                    layer_collection = bpy.context.view_layer.layer_collection  # bpy.context.scene.collection
                    Coll_of_Active = recurLayerCollection(layer_collection, i.name)

                obj.select_set(False)
                newobj = obj.copy()
                bpy.data.collections[Coll_of_Active.name].objects.link(newobj)  # LINK TO COLLECTION
                newobj.data = bpy.data.curves.new("Secret Paint", "CURVE")
                bpy.context.view_layer.objects.active = newobj

                #link materials
                for material in _secret_paint_collect_safe_materials_from_object(obj, material_cache):
                    _secret_paint_append_material_once(newobj.data.materials, material)

            # for x in bpy.context.selected_objects: x.select_set(False) #objselection
            bpy.ops.object.mode_set(mode="EDIT")

    else:
        if activeobj.type=="CURVES":
            bpy.ops.object.mode_set(mode="OBJECT")
            # bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'})
            bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False})
            newCurve = bpy.context.active_object
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.curves.select_linked()
            bpy.ops.curves.select_all(action='INVERT')
            bpy.ops.transform.resize(value=(0, 0, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False,
                                     snap_target='CENTER', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
            # bpy.ops.curves.delete()
            bpy.ops.curves.select_all(action='SELECT')

            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = bpy.data.objects[activeobj.name]
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.curves.select_linked()
            bpy.ops.transform.resize(value=(0, 0, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False,
                                     snap_target='CENTER', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
            # bpy.ops.curves.delete()
            bpy.ops.curves.select_all(action='SELECT')

            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action='DESELECT')
            # bpy.data.objects[newCurve.name].select_set(True)
            bpy.context.view_layer.objects.active = bpy.data.objects[newCurve.name]

            bpy.ops.object.mode_set(mode="SCULPT_CURVES")
            # bpy.ops.object.mode_set(mode=saveMode)




            # bpy.ops.object.mode_set(mode="EDIT")
            # bpy.ops.curves.select_linked()
            # bpy.ops.object.mode_set(mode="OBJECT")
            # bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False})
            # newCurve = bpy.context.active_object
            # bpy.ops.object.mode_set(mode="EDIT")
            # bpy.ops.curves.select_all(action='INVERT')
            # # bpy.ops.transform.resize(value=(0, 0, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False,
            # #                          snap_target='CENTER', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
            # bpy.ops.curves.delete()
            # bpy.ops.object.mode_set(mode="OBJECT")
            # newCurve.select_set(False)
            # bpy.context.view_layer.objects.active = activeobj.name
            # bpy.ops.object.mode_set(mode="EDIT")
            # bpy.ops.curves.delete()
            # bpy.ops.curves.select_all(action='SELECT')
            # bpy.ops.object.mode_set(mode="OBJECT")
            # bpy.context.view_layer.objects.active = newCurve
            # # newCurve.select_set(True)
            # bpy.ops.object.mode_set(mode="EDIT")
            # bpy.ops.curves.select_all(action='SELECT')
            # bpy.ops.object.mode_set(mode="SCULPT_CURVES")
            # for x in bpy.context.selected_objects: x.select_set(False) #objselection
            # print("-----------------",)

            return newCurve

        elif activeobj.type == "CURVE":
            try:
                bpy.ops.curve.select_all(action='INVERT')
                bpy.ops.curve.separate()
                bpy.ops.curve.select_all(action='SELECT')
                for x in bpy.context.selected_objects:bpy.data.objects[x.name].select_set(False)  # for x in bpy.context.selected_objects:
                activeobj.select_set(True)  # BONES bpy.data.objects[c.id_data.name].pose.bones[bone.name].bone.select = False
            except:  #fails bc there's only one curve and there are no points when inverting the selection
                bpy.ops.curve.select_all(action='SELECT')
                bpy.ops.curve.separate()
                bpy.ops.curve.select_all(action='SELECT')
                for x in bpy.context.selected_objects: bpy.data.objects[x.name].select_set(False)
                activeobj.select_set(True)  # BONES bpy.data.objects[c.id_data.name].pose.bones[bone.name].bone.select = False
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
        if children.visible_get(): all_children.append(children)  # if children.name in bpy.context.view_layer.objects: all_children.append(children)  #children.type not in ["ARMATURE"]
        get_all_children(children,all_children,context)
    return all_children

def get_all_DownwardsDependencies(activeobj, final_assemblies_to_process, all_assemblies_and_their_parent, context):
    for obj in all_assemblies_and_their_parent:
        if obj[1] == activeobj:
            if obj[0] not in final_assemblies_to_process: final_assemblies_to_process.append(obj[0])
            get_all_DownwardsDependencies(obj[0], final_assemblies_to_process, all_assemblies_and_their_parent, context)
    return final_assemblies_to_process
# def get_all_UpwardsDependencies(activeobj, final_assemblies_to_process, all_assemblies_and_their_parent, context):
#     for obj in all_assemblies_and_their_parent:
#         if obj[0] == activeobj:
#             if obj[1] not in final_assemblies_to_process: final_assemblies_to_process.append(obj[1])
#             # print(f"{obj[0].name} is the activeobj,{obj[1].name} is it's parent that's being appended to FINAL and reprocessed, here's final list so far {[x.name for x in final_assemblies_to_process]}")
#             get_all_UpwardsDependencies(obj[1], final_assemblies_to_process, all_assemblies_and_their_parent, context)
#     return final_assemblies_to_process

# def get_first_parent_Upwards(activeobj,first_parent, all_assemblies_and_their_parent, context):
#     for obj in all_assemblies_and_their_parent:
#         if obj[0] == activeobj:
#             first_parent = obj[1]
#             first_parent=get_first_parent_Upwards(obj[1], first_parent,all_assemblies_and_their_parent, context)
#     return first_parent
def get_first_parent_Upwards(activeobj, context):
    # parent_of_current_object = activeobj.modifiers[0]["Socket_1"] if activeobj.modifiers and activeobj.modifiers[0].name.startswith("Secret Assembly") and activeobj.modifiers[0].type=="NODES" and activeobj.modifiers[0].node_group and "ASSEMBLY" in activeobj.modifiers[0].node_group.name else None
    parent_of_current_object = secret_assembly_parent_object(activeobj)
    if parent_of_current_object != None: return get_first_parent_Upwards(parent_of_current_object, context)
    else: return activeobj

def get_secret_assemblies_to_process(activeobj, context):
    if activeobj == None:
        return []

    all_assemblies_and_their_parent = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.modifiers:
            for modif in obj.modifiers:
                parent_input = secret_assembly_parent_input(modif)
                if parent_input:
                    all_assemblies_and_their_parent.append((obj, modif[parent_input.identifier]))

    final_assemblies_to_process = []
    first_parent = get_first_parent_Upwards(activeobj, context)
    final_assemblies_to_process.append(first_parent)
    get_all_DownwardsDependencies(first_parent, final_assemblies_to_process, all_assemblies_and_their_parent, context)

    if activeobj in final_assemblies_to_process:
        final_assemblies_to_process.remove(activeobj)
    final_assemblies_to_process.append(activeobj)

    return final_assemblies_to_process

def build_secret_assembly_direct(self, context, activeobj, **kwargs):
    if activeobj == None:
        auto_assembly_print("build", "abort", "active=None")
        return None, [], False, False

    skip_select_new_assembly = kwargs.get("skip_select_new_assembly") if "skip_select_new_assembly" in kwargs else False
    final_assemblies_to_process = get_secret_assemblies_to_process(activeobj, context)
    auto_assembly_print("build", "active=", activeobj.name, "process=", [obj.name for obj in final_assemblies_to_process], "skip_select=", skip_select_new_assembly)

    assembly_obj = None
    created_new_assembly = False
    updated_existing_assembly = False
    for obj in final_assemblies_to_process:
        there_are_assemblies_to_update, processing_original_activeobj, processed_assembly_obj = assembly_2(
            self,
            context,
            activeobj=obj,
            original_activeobj=activeobj,
            skip_select_new_assembly=skip_select_new_assembly,
        )
        if processing_original_activeobj:
            updated_existing_assembly = there_are_assemblies_to_update
            if there_are_assemblies_to_update == False and processed_assembly_obj:
                created_new_assembly = True
            if processed_assembly_obj:
                assembly_obj = processed_assembly_obj

    if assembly_obj == None:
        assembly_obj = find_secret_assembly_for_parent(activeobj)

    auto_assembly_print(
        "build",
        "result",
        "active=", activeobj.name,
        "assembly=", assembly_obj.name if assembly_obj else None,
        "created=", created_new_assembly,
        "updated=", updated_existing_assembly,
    )
    return assembly_obj, final_assemblies_to_process, created_new_assembly, updated_existing_assembly


def assembly_1(self,context,**kwargs):
    start_time = time.perf_counter()

    original_activeobj = activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    skip_translate = kwargs.get("skip_translate") if "skip_translate" in kwargs else False
    quiet = kwargs.get("quiet") if "quiet" in kwargs else False
    if activeobj == None and bpy.context.selected_objects: activeobj = original_activeobj= bpy.context.selected_objects[0]  #bpy.context.view_layer.objects.active = activeobj = original_activeobj= bpy.context.selected_objects[0]
    if activeobj == None:
        if quiet == False:
            self.report({'ERROR'}, "Select the Parent Object. Its children will be automatically included in the Assembly")
        return{'FINISHED'}

    #when box selecting many objs, just pick the common parent
    parent_with_most_children = bpy.context.selected_objects[0]
    for ob in bpy.context.selected_objects:
        ob_childrens = [children for children in ob.children if children in bpy.context.selected_objects]
        parent_with_most_children_children = [children for children in parent_with_most_children.children if children in bpy.context.selected_objects]
        if not ob.parent and len(ob_childrens) > len(parent_with_most_children_children) \
        or ob.parent and ob.parent not in bpy.context.selected_objects and len(ob.children) > len(parent_with_most_children.children):
            parent_with_most_children = ob
    #IF THERE WAS NO COMMON PARENT, PROCESS ACTIVE OBJECT
    # activeobj = original_activeobj = parent_with_most_children
    common_parent_has_children_in_the_selected_objects = False
    for children in parent_with_most_children.children: #if the parent has no children in the selected objects, there was no common parent so PROCESS ACTIVE OBJECT
        if children in bpy.context.selected_objects:
            common_parent_has_children_in_the_selected_objects = True
            break
    if common_parent_has_children_in_the_selected_objects: activeobj = original_activeobj = parent_with_most_children
    else: activeobj = original_activeobj

    #all selected objects should be parented to the active object
    for ob in bpy.context.selected_objects:
        if ob != activeobj:
            if not ob.parent \
            or ob.parent and ob.parent not in bpy.context.selected_objects:
                ob_matrix_world = ob.matrix_world.copy()
                ob.parent=activeobj   #dupe.parent = parent
                ob.matrix_world = ob_matrix_world

    assembly_obj, final_assemblies_to_process, created_new_assembly, updated_existing_assembly = build_secret_assembly_direct(self, context, activeobj)
    main_loops = len(final_assemblies_to_process)

    if created_new_assembly:
        if quiet == False:
            if len(bpy.context.selected_objects) >= 2:
                self.report({'INFO'}, "Created a New Assembly.  You only need to select the Parent Object. Its children will be automatically included in the Assembly")
            else:
                self.report({'INFO'}, "Created a New Assembly")
        if skip_translate == False:
            bpy.ops.transform.translate('INVOKE_DEFAULT', use_proportional_edit=False)
    elif main_loops >= 3:
        if quiet == False:
            self.report({'INFO'}, "Updated Interdependent Assemblies")
        for ob in final_assemblies_to_process:
            try: ob.select_set(True)
            except: pass
    else:
        if quiet == False:
            self.report({'INFO'}, "Updated Existing Assembly")
        for ob in final_assemblies_to_process:
            try: ob.select_set(True)
            except: pass

    end_time = time.perf_counter()
    print("Milliseconds 1111 (Ping):",(end_time - start_time) * 1000)
    start_time = time.perf_counter()
    return{'FINISHED'}
def assembly_2(self,context,**kwargs):
    start_time_2 = time.perf_counter()

    original_activeobj = kwargs.get("original_activeobj") if "original_activeobj" in kwargs else bpy.context.active_object
    activeobj = kwargs.get("activeobj") if "activeobj" in kwargs else bpy.context.active_object
    skip_select_new_assembly = kwargs.get("skip_select_new_assembly") if "skip_select_new_assembly" in kwargs else False
    if activeobj == None: activeobj = bpy.context.active_object
    processing_original_activeobj = True if activeobj == original_activeobj else False


    there_are_assemblies_to_update = False
    all_children=[]
    all_materials_of_parent_and_children=[]
    material_cache = {}
    processed_assembly_obj = None



    #UPDATE THE ASSEMBLY INSTEAD OF CREATING A NEW ONE    (IF ORIGINALACTIVEOBJ IS ASSEMBLY WITHOUT CHILDREN (and is not referenced by constraints),  (by simply selecting the parent object and using same script)
    activeobj_referenced_by_constraint = False
    for ob in bpy.data.objects:
        if ob.constraints and not activeobj_referenced_by_constraint:
            for con in ob.constraints:
                if hasattr(con, 'target') and con.target == activeobj:
                    activeobj_referenced_by_constraint = True
                    break
    if activeobj.type == "MESH" and activeobj.modifiers and not activeobj.children and processing_original_activeobj and not activeobj_referenced_by_constraint:
        resolved_parent = secret_assembly_parent_object(activeobj)
        if resolved_parent:
            activeobj = resolved_parent




    #LIST MATERIALS OF ACTIVEOBJ BEING PROCESSED
    for material in _secret_paint_collect_safe_materials_from_object(activeobj, material_cache):
        if material not in all_materials_of_parent_and_children: all_materials_of_parent_and_children.append(material)


    #LIST ALL ASSEMBLIES THAT ARE USING ACTIVEOBJ (they have to reference the activeobj as parent in the modifier)
    all_modif_to_update =[]
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.modifiers:
            for modif in obj.modifiers:
                if modif.type == 'NODES' and modif.name == "Secret Assembly" and modif.node_group and "ASSEMBLY" in modif.node_group.name:
                    node_group_inputs_temp = modif.node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else modif.node_group.inputs
                    for input in node_group_inputs_temp:
                        if input.socket_type == "NodeSocketObject" and input.name == "Parent" and modif[input.identifier] == activeobj and modif not in all_modif_to_update:
                            all_modif_to_update.append((obj,modif))
                            if processed_assembly_obj == None:
                                processed_assembly_obj = obj
                            there_are_assemblies_to_update = True
                            break #no need to liip through other inputs #avoid looping through other inputs of the modifier since it just swapped node tree with different sockets



    #PROCEED OLY IF AN ASSEMBLY WAS FOUND OR WE'RE CREATING A NEW ASSEMBLY FOR THE ORIGINAL ACTIVEOBJ
    if there_are_assemblies_to_update or processing_original_activeobj:


        #ALL ASSEMBLIES WITH THE SAME PARENT SHOULD ALSO HAVE THE SAME DATA (needed for accurate material slots)
        if all_modif_to_update and len(all_modif_to_update) != all_modif_to_update[0][0].data.users: #if the number of mesh users is not the same as the number of modifiers to update, is because there's another assembly with the same data, so create a duplicate
            new_mesh_data = all_modif_to_update[0][0].data.copy()
            for obbb in all_modif_to_update:
                obbb[0].data = new_mesh_data


        #NEW NODE GROUP + ASSIGN, delete old one
        node_group = bpy.data.node_groups[activeobj.name + "ASSEMBLY"] if activeobj.name + "ASSEMBLY" in bpy.data.node_groups else None
        if node_group and node_group.users==0: bpy.data.node_groups.remove(node_group) #remove it if found and has no users
        node_group = bpy.data.node_groups.new("GeometryNodeGroup", 'GeometryNodeTree')
        node_group.name = activeobj.name + "ASSEMBLY"
        for modif in all_modif_to_update: modif[1].node_group = node_group #ASSIGN NODE TREE



        #ONLY CREATE A NEW ASSEMBLY IF THE ACTIVEOBJ IS THE ORIGINAL_ACTIVEOBJ AND THERE ARE NO EXISTING ASSEMBLIES TO UPDATE,   then proceed to fill THE NEW NODE TREE anyway
        if processing_original_activeobj and there_are_assemblies_to_update==False:

            # FIND COLLECTION OF ACTIVE TO CREATE NEW ASSEMBLY INSIDE OF IT
            Coll_of_Active = []
            original_collection = bpy.context.view_layer.active_layer_collection  # bpy.context.view_layer.active_layer_collection = layerColl  #SELECT COLLECTION
            for i in activeobj.users_collection:
                Coll_of_Active = recurLayerCollection(bpy.context.view_layer.layer_collection, i.name)
                bpy.context.view_layer.active_layer_collection = Coll_of_Active

            # Create a new mesh object
            mesh = bpy.data.meshes.new("Secret Assembly")  # create a new mesh
            obj = bpy.data.objects.new(activeobj.name + "ASSEMBLY", mesh)  # create a new object with the mesh
            obj.location = activeobj.matrix_world.to_translation()
            bpy.context.collection.objects.link(obj)  # link the object to the current collection
            processed_assembly_obj = obj
            if skip_select_new_assembly == False:
                for x in bpy.context.selected_objects: x.select_set(False)
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            modifier = obj.modifiers.new(name="Secret Assembly", type='NODES')  # create a Geometry Nodes modifier
            modifier.node_group = node_group  # set the Geometry Nodes modifier to use the new node group
            # obj["Secret Assembly"] = activeobj #CUSTOM PROPERTY

            #restore previous active collection
            bpy.context.view_layer.active_layer_collection = original_collection

        #CREATE NODE TREE WITH INPUTS AND OUTPUTS AND PARENT INFO
        input = node_group.nodes.new('NodeGroupInput')
        input.location = (-500,0)
        node_group.interface.clear()
        if bpy.app.version_string >= "4.0.0":
            node_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
            node_group.interface.new_socket(name='Realize Instances', in_out='INPUT', socket_type='NodeSocketBool')
            # tempx = node_group.interface.new_socket(name='Realize Instances Depth', in_out='INPUT', socket_type='NodeSocketInt')
            # tempx.min_value = 0  # node_group.interface.items_tree[2].min_value = 0
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
        # realize_instances_node.inputs[3].default_value = 1

        # node_group.links.new(JoinGeometry.outputs[0], output.inputs[0])




        #CREATE EACH NODE FOR PARENTS AND CHILDREN
        parent_info_node = node_group.nodes.new(type='GeometryNodeObjectInfo')
        parent_info_node.location = (-300,0)
        parent_info_node.inputs[0].default_value = activeobj #parent
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
        node_group.links.new(input.outputs[1], realize_instances_node.inputs[2]) #node_group.links.new(input.outputs[1], realize_instances_node.inputs[3])


        get_all_children(activeobj,all_children,context)

        #INCLUDE ALL CONSTRAINTS THAT REFERENCE THE CHILD OR PARENT
        for ob in bpy.data.objects:
            if ob.constraints: # if ob.constraints and ob.contraints[0].type in ["CLAMP_TO","DAMPED_TRACK","LOCKED_TRACK","STRETCH_TO","TRACK_TO","COPY_LOCATION","COPY_ROTATION","COPY_TRANSFORMS","TRANSFORMATION","OBJECT_SOLVER","CHILD_OF","FOLLOW_PATH","PIVOT","SHRINKWRAP"]: pass
                for con in ob.constraints:
                    if hasattr(con, 'target') and con.target == activeobj and ob not in all_children \
                    or hasattr(con, 'target') and con.target in all_children and ob not in all_children: all_children.append(ob)

        childloop = 2
        for children in all_children:

            #LIST ALL MATERIALS
            for material in _secret_paint_collect_safe_materials_from_object(children, material_cache):
                if material not in all_materials_of_parent_and_children: all_materials_of_parent_and_children.append(material)

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
            # VectorMath2 = node_group.nodes.new('ShaderNodeVectorMath')
            # VectorMath2.operation = 'SUBTRACT'
            # VectorMath2.location = (-100, (-300 *childloop)-100)

            node_group.links.new(input.outputs[childloop+1], children_info_node.inputs[0])
            node_group.links.new(children_info_node.outputs[1], VectorMath1.inputs[0])
            node_group.links.new(VectorMath1.outputs[0], CombineTransform.inputs[0])
            node_group.links.new(children_info_node.outputs[2], CombineTransform.inputs[1])  #node_group.links.new(VectorMath2.outputs[0], CombineTransform.inputs[1])
            #node_group.links.new(children_info_node.outputs[2], VectorMath2.inputs[0])
            # node_group.links.new(parent_info_node.outputs[2], VectorMath2.inputs[1])
            node_group.links.new(children_info_node.outputs[3], CombineTransform.inputs[2])
            node_group.links.new(children_info_node.outputs[4], SetInstanceTransform.inputs[0])
            node_group.links.new(CombineTransform.outputs[0], SetInstanceTransform.inputs[2])
            if children.type != "ARMATURE": node_group.links.new(SetInstanceTransform.outputs[0], JoinGeometry.inputs[0])
            node_group.links.new(parent_info_node.outputs[1], VectorMath1.inputs[1])

            childloop += 1




        #ASSIGN MODIFIER INPUTS AND MATERIALS
        node_group_inputs = node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else node_group.inputs
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.modifiers:
                for modif in obj.modifiers:
                    if modif.type == 'NODES' and modif.node_group and modif.node_group == node_group:
                        #CLEAR AND REASSIGN NEW MATERIALS
                        obj.data.materials.clear() #clear first
                        for mat in all_materials_of_parent_and_children:
                            _secret_paint_append_material_once(obj.data.materials, mat)
                        # for mat_slot in obj.material_slots: #MAKE SLOTS OBJECT DEPENDENT, SO THAT WHEN LINKED DUPLICATE FOR DIFFERENT VERSION THEY CAN STILL HAVE DIFFERENT MATS
                        #     mat = mat_slot.material
                        #     mat_slot.link = 'OBJECT'
                        #     mat_slot.material = mat
                        child_loop = 0
                        for input in node_group_inputs:
                            if getattr(input, "socket_type", None) == "NodeSocketObject" and input.name == "Parent":
                                modif[input.identifier] = activeobj
                            elif getattr(input, "socket_type", None) == "NodeSocketObject" and input.name == "Child" and child_loop < len(all_children):
                                modif[input.identifier] = all_children[child_loop]
                                child_loop += 1


        node_group.links.new(realize_instances_node.outputs[0], output.inputs[0])  #connect realize instances geometry to the output after calculating everything else, should help performance

    end_time = time.perf_counter()
    print("Milliseconds 22222 (Ping):",(end_time - start_time_2) * 1000)
    start_time = time.perf_counter()
    auto_assembly_print(
        "assembly_2",
        "active=", activeobj.name if activeobj else None,
        "processed=", processed_assembly_obj.name if processed_assembly_obj else None,
        "updates_existing=", there_are_assemblies_to_update,
        "processing_original=", processing_original_activeobj,
    )
    return there_are_assemblies_to_update, processing_original_activeobj, processed_assembly_obj


class assembly(bpy.types.Operator):
    """Group the Active Object, its children and constraints into a non-destructive assembly. Alt + Click to merge into a mesh. You can add new objects to the assembly by simply parenting them to the original object. You can then update the assembly by pressing the button again. You can also create assemblies within assemblies to keep modelling procedurally. This works with everything, even complex rigs. It's a better version of collection instances with none of the drawbacks"""
    bl_idname = "secret.assembly"
    bl_label = "Secret Assembly"
    bl_options = {'REGISTER', 'UNDO'}
    # def execute(self, context):
    def invoke(self, context, event):
        if blender_version < "4.2.0":
            self.report({'ERROR'}, "Secret Paint Assemblies are only available from Blender 4.2 due to a lack of nodes")
        elif event.alt: convert_and_join_f(self,context)
        else: assembly_1(self,context)
        return {'FINISHED'}


# def export_unreal_f(self,context,export_textures):
#     new_objects_to_delete =[]
#     # if export_textures: export_t = "JPEG"
#     # else: export_t = "NONE"
#     # blend_file_path = bpy.data.filepath
#     # directory = os.path.dirname(blend_file_path)
#
#     blend_file_path = bpy.data.filepath
#     directory = os.path.dirname(blend_file_path)
#     subfolder = os.path.join(directory, 'UE5 Export')
#     if not os.path.exists(subfolder):
#         os.makedirs(subfolder)
#
#     # try:
#     # except:self.report({'ERROR'}, "Save this project before exporting. The GLTF will be exported next to the Blend file")
#
#     activeobj = bpy.context.active_object  #   bpy.data.objects["armature"]     bpy.context.object["armature"]     <bpy_struct, Object("left") at 0x000001C2D10E5608>
#     objselection = bpy.context.selected_objects  #bpy.context.selected_objects[0]   #bpy.context.scene.objects
#
#
#     all_previous_objects = set(bpy.context.scene.objects)
#
#
# ############################################### v
#
#     for ob in objselection:
#         for x in bpy.context.selected_objects: x.select_set(False)
#
#         # realize assembly> delete assemblies > secret paint bezier
#         all_children = []
#         get_all_children(activeobj, all_children, context)
#         for child in all_children:
#             if child.type in ["MESH","CURVE"]: child.select_set(True)
#         ob.select_set(True)
#         bpy.context.view_layer.objects.active = ob
#
#         Main_Parent = bpy.data.objects.new("Main Parent", None)
#         # Main_Parent = bpy.data.objects.new(activeobj.data.name, bpy.data.meshes.new(activeobj.data.name))
#         Main_Parent.location = ob.location  # set location to scene cursor
#         context.collection.objects.link(Main_Parent)
#
#         bpy.ops.object.duplicates_make_real()
#
#         new_obs = list(set(bpy.context.scene.objects) - all_previous_objects)
#
#         #CLEAR ALL ASSEMBLIES AND SECRET PAINT EXTRA DATA
#         secret_paint_and_assemblies_to_delete =[]
#         for objj in new_obs[:]:
#             for modif in objj.modifiers:
#                 if modif.type == "NODES" and modif.node_group and "ASSEMBLY" in modif.node_group.name\
#                 or objj.type == "CURVE" and modif.type=="NODES" and modif.node_group and modif.node_group.name.startswith("Secret Paint")\
#                 or objj.type == "CURVE" and modif.type=="NODES" and modif.node_group and modif.node_group.name.startswith("Secret Paint") and re.search(r"\.\d{3}$", modif.node_group.name) and ".001" <= modif.node_group.name[-4:] <= ".999":
#                     secret_paint_and_assemblies_to_delete.append(objj)
#                     new_obs.remove(objj)
#
#             if objj!=Main_Parent:
#                 objj.parent = Main_Parent
#                 objj.matrix_parent_inverse = Main_Parent.matrix_world.inverted()
#
#         saved_parent= ob.parent
#         ob.parent = Main_Parent
#         ob.matrix_parent_inverse = Main_Parent.matrix_world.inverted()
#
#
#         for obk in secret_paint_and_assemblies_to_delete: bpy.data.objects.remove(obk, do_unlink=True)
#
#         #MODIFIERS + MATERIAL links to DATA (or unreal engine will split into different objects, same with modifiers)
#         # multi_user_obs_with_modifiers=[]
#         for x in bpy.context.selected_objects: x.select_set(False)
#         loop = 1
#         for obkk in all_children:
#             # if ob.modifiers and ob.data not in multi_user_obs_with_modifiers: multi_user_obs_with_modifiers.append(ob)
#             if obkk.type in ["MESH","CURVE"]:
#                 obkk.select_set(True)
#                 if loop == 1: bpy.context.view_layer.objects.active = obkk
#                 for mat_slot in obkk.material_slots: mat_slot.link = "DATA"
#             loop=+1
#         loop = 1
#         for obkk in new_obs:
#             # if ob.modifiers and ob.data not in multi_user_obs_with_modifiers: multi_user_obs_with_modifiers.append(ob)
#             if obkk.type in ["MESH","CURVE"]:
#                 obkk.select_set(True)
#                 if loop == 1: bpy.context.view_layer.objects.active = obkk
#                 for mat_slot in obkk.material_slots: mat_slot.link = "DATA"
#             loop=+1
#
#         # bpy.ops.object.convert(target='MESH')
#
#
#         # select main parent and all children > export fbx,
#         Main_Parent.location = (0,0,0)
#         # Main_Parent.scale = (100,100,100)
#
#         bpy.context.view_layer.objects.active = Main_Parent
#         Main_Parent.select_set(True)
#         ob.select_set(True)
#         # return{'FINISHED'}
#
#         bpy.ops.export_scene.fbx(filepath=subfolder + "\\" + ob.name + ".fbx", check_existing=True, filter_glob='*.fbx', use_selection=True, use_visible=False, use_active_collection=False, collection='',
#         global_scale=1.0,
#         apply_unit_scale=True,
#         apply_scale_options='FBX_SCALE_NONE',
#         use_space_transform=True,
#         bake_space_transform=True,
#         object_types={'ARMATURE', 'CAMERA', 'EMPTY', 'LIGHT', 'MESH', 'OTHER'},
#         use_mesh_modifiers=False,
#         use_mesh_modifiers_render=False,
#         mesh_smooth_type='OFF', colors_type='SRGB', prioritize_active_color=False, use_subsurf=False, use_mesh_edges=False, use_tspace=False, use_triangles=False, use_custom_props=False, add_leaf_bones=False,
#         primary_bone_axis='Y',
#         secondary_bone_axis='X', use_armature_deform_only=False, armature_nodetype='NULL',
#         bake_anim=False, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=True, bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=1.0, path_mode='AUTO', embed_textures=False, batch_mode='OFF', use_batch_own_dir=True, use_metadata=True,
#         axis_forward='Y',
#         axis_up='Z')
#
#
#         # restore status: delete all new objs
#         if saved_parent:
#             ob.parent = saved_parent
#             ob.matrix_parent_inverse = saved_parent.matrix_world.inverted()
#         for ob in new_obs: bpy.data.objects.remove(ob, do_unlink=True)
#         for x in objselection: x.select_set(True)
#         if activeobj: bpy.context.view_layer.objects.active = activeobj
#         self.report({'INFO'}, "Exported selected Assemblies to FBX next to this .blend file")
#     return {'FINISHED'}
def export_unreal_f(self,context,export_textures):

    # try:
    blend_file_path = bpy.data.filepath
    directory = os.path.dirname(blend_file_path)
    # subfolder = os.path.join(directory, 'UE5 Export')
    # if not os.path.exists(subfolder):
    #     os.makedirs(subfolder)

    #filepath=subfolder + "\\" + os.path.basename(blend_file_path) + ".usdc",
    bpy.ops.wm.usd_export(
    filepath=directory + "\\" + os.path.basename(blend_file_path) + ".usdc",
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
    # export_textures=False,  # Removed - not supported in Blender 5.0
    # export_textures_mode='NEW',
    # overwrite_textures=False,  # Removed - not supported in Blender 5.0
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
    # export_points=True,
    export_volumes=True,
    triangulate_meshes=False,
    quad_method='SHORTEST_DIAGONAL',
    ngon_method='BEAUTY',
    usdz_downscale_size='KEEP',
    usdz_downscale_custom_size=128)

    # except:
    # self.report({'ERROR'}, "Save this project before exporting. The objects will be exported next to the Blend file")
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

SECRET_PAINT_VIEW_BOOKMARKS_PROP = "secret_paint_view_bookmarks"
_SECRET_PAINT_LEGACY_VIEW_BOOKMARK_NEXT_PROP = "_oren_tab_view_next_slot"


def _viewport_tab_bookmark_prop(slot, suffix):
    return f"_oren_tab_view_bookmark_{slot}_{suffix}"


def _default_viewport_bookmark_data():
    return {
        "next_slot": 1,
        "bookmarks": {},
    }


def _normalize_viewport_bookmark_slot(value):
    try:
        return 2 if int(value) == 2 else 1
    except Exception:
        return 1


def _coerce_float_tuple(value, expected_length):
    values = tuple(float(item) for item in value)
    if len(values) != expected_length:
        raise ValueError("Unexpected viewport bookmark vector length")
    return values


def _bookmark_from_region_3d(region_3d):
    return {
        "view_location": tuple(float(item) for item in region_3d.view_location),
        "view_rotation": tuple(float(item) for item in region_3d.view_rotation),
        "view_distance": float(region_3d.view_distance),
        "view_perspective": str(region_3d.view_perspective),
        "view_camera_zoom": float(region_3d.view_camera_zoom),
        "view_camera_offset": tuple(float(item) for item in region_3d.view_camera_offset),
    }


def _bookmark_to_storage(bookmark):
    return {
        "location": list(_coerce_float_tuple(bookmark["view_location"], 3)),
        "rotation": list(_coerce_float_tuple(bookmark["view_rotation"], 4)),
        "distance": float(bookmark["view_distance"]),
        "perspective": str(bookmark["view_perspective"]),
        "camera_zoom": float(bookmark["view_camera_zoom"]),
        "camera_offset": list(_coerce_float_tuple(bookmark["view_camera_offset"], 2)),
    }


def _bookmark_from_storage(bookmark_data):
    if not isinstance(bookmark_data, dict):
        return None

    try:
        return {
            "view_location": _coerce_float_tuple(bookmark_data["location"], 3),
            "view_rotation": _coerce_float_tuple(bookmark_data["rotation"], 4),
            "view_distance": float(bookmark_data["distance"]),
            "view_perspective": str(bookmark_data["perspective"]),
            "view_camera_zoom": float(bookmark_data["camera_zoom"]),
            "view_camera_offset": _coerce_float_tuple(bookmark_data["camera_offset"], 2),
        }
    except Exception:
        return None


def _load_legacy_viewport_bookmark(scene, slot):
    legacy_keys = {
        "location": _viewport_tab_bookmark_prop(slot, "location"),
        "rotation": _viewport_tab_bookmark_prop(slot, "rotation"),
        "distance": _viewport_tab_bookmark_prop(slot, "distance"),
        "perspective": _viewport_tab_bookmark_prop(slot, "perspective"),
        "camera_zoom": _viewport_tab_bookmark_prop(slot, "camera_zoom"),
        "camera_offset": _viewport_tab_bookmark_prop(slot, "camera_offset"),
    }
    if any(key not in scene for key in legacy_keys.values()):
        return None

    return _bookmark_from_storage({
        storage_key: scene[legacy_key]
        for storage_key, legacy_key in legacy_keys.items()
    })


def _cleanup_legacy_viewport_bookmark_props(scene):
    legacy_props = [_SECRET_PAINT_LEGACY_VIEW_BOOKMARK_NEXT_PROP]
    for slot in (1, 2):
        for suffix in ("location", "rotation", "distance", "perspective", "camera_zoom", "camera_offset"):
            legacy_props.append(_viewport_tab_bookmark_prop(slot, suffix))

    removed = False
    for prop_name in legacy_props:
        if prop_name in scene:
            del scene[prop_name]
            removed = True
    return removed


def _viewport_bookmark_storage_owner(context):
    return getattr(context, "scene", None)


def _parse_viewport_bookmark_data(owner):
    raw_data = owner.get(SECRET_PAINT_VIEW_BOOKMARKS_PROP, "") if owner is not None else ""
    if not isinstance(raw_data, str) or not raw_data.strip():
        return None
    try:
        loaded_data = json.loads(raw_data)
    except Exception:
        return None
    return loaded_data if isinstance(loaded_data, dict) else None


def _load_viewport_bookmark_data(storage_owner, legacy_scene=None):
    data = _default_viewport_bookmark_data()
    loaded_from_single_prop = False

    loaded_data = _parse_viewport_bookmark_data(storage_owner)
    if loaded_data is None and legacy_scene is not None and legacy_scene != storage_owner:
        loaded_data = _parse_viewport_bookmark_data(legacy_scene)
    if loaded_data is not None:
        data.update(loaded_data)
        loaded_from_single_prop = True

    if not isinstance(data.get("bookmarks"), dict):
        data["bookmarks"] = {}
    data["next_slot"] = _normalize_viewport_bookmark_slot(data.get("next_slot", 1))

    for slot in (1, 2):
        slot_key = str(slot)
        if loaded_from_single_prop and slot_key in data["bookmarks"]:
            continue
        for legacy_owner in (storage_owner, legacy_scene):
            if legacy_owner is None:
                continue
            legacy_bookmark = _load_legacy_viewport_bookmark(legacy_owner, slot)
            if legacy_bookmark is not None:
                data["bookmarks"][slot_key] = _bookmark_to_storage(legacy_bookmark)
                break

    if not loaded_from_single_prop:
        for legacy_owner in (storage_owner, legacy_scene):
            if legacy_owner is None or _SECRET_PAINT_LEGACY_VIEW_BOOKMARK_NEXT_PROP not in legacy_owner:
                continue
            try:
                data["next_slot"] = _normalize_viewport_bookmark_slot(legacy_owner[_SECRET_PAINT_LEGACY_VIEW_BOOKMARK_NEXT_PROP])
                break
            except Exception:
                pass

    return data


def _save_viewport_bookmark_data(storage_owner, data):
    data["next_slot"] = _normalize_viewport_bookmark_slot(data.get("next_slot", 1))
    if not isinstance(data.get("bookmarks"), dict):
        data["bookmarks"] = {}
    storage_owner[SECRET_PAINT_VIEW_BOOKMARKS_PROP] = json.dumps(data, indent=2, sort_keys=True)


def _capture_viewport_bookmark(storage_owner, slot, region_3d, legacy_scene=None):
    _save_viewport_bookmark(storage_owner, slot, _bookmark_from_region_3d(region_3d), legacy_scene=legacy_scene)


def _save_viewport_bookmark(storage_owner, slot, bookmark, legacy_scene=None):
    data = _load_viewport_bookmark_data(storage_owner, legacy_scene=legacy_scene)
    data["bookmarks"][str(slot)] = _bookmark_to_storage(bookmark)
    _save_viewport_bookmark_data(storage_owner, data)


def _load_viewport_bookmark(storage_owner, slot, legacy_scene=None):
    data = _load_viewport_bookmark_data(storage_owner, legacy_scene=legacy_scene)
    return _bookmark_from_storage(data["bookmarks"].get(str(slot)))


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


def _screen_right_view_offset(region_3d, distance=10.0):
    try:
        view_right = region_3d.view_matrix.inverted().to_3x3() @ Vector((1.0, 0.0, 0.0))
    except Exception:
        view_right = region_3d.view_rotation @ Vector((1.0, 0.0, 0.0))

    if view_right.length_squared == 0.0:
        view_right = Vector((1.0, 0.0, 0.0))
    else:
        view_right.normalize()

    return view_right * distance


def _viewport_bookmark_offset_right(region_3d, bookmark, distance=10.0):
    shifted_bookmark = dict(bookmark)
    shifted_bookmark["view_location"] = tuple(Vector(bookmark["view_location"]) + _screen_right_view_offset(region_3d, distance))
    return shifted_bookmark


def _get_next_viewport_bookmark_slot(storage_owner, legacy_scene=None):
    data = _load_viewport_bookmark_data(storage_owner, legacy_scene=legacy_scene)
    return _normalize_viewport_bookmark_slot(data.get("next_slot", 1))


def _set_next_viewport_bookmark_slot(storage_owner, slot, legacy_scene=None):
    data = _load_viewport_bookmark_data(storage_owner, legacy_scene=legacy_scene)
    data["next_slot"] = 2 if slot == 2 else 1
    _save_viewport_bookmark_data(storage_owner, data)


def _viewport_bookmark_shortcut_text(context):
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None) if wm else None
    if keyconfigs is None:
        return "W"

    for keyconfig_name in ("user", "addon", "active"):
        keyconfig = getattr(keyconfigs, keyconfig_name, None)
        if keyconfig is None:
            continue
        for keymap in keyconfig.keymaps:
            for keymap_item in keymap.keymap_items:
                if (
                    getattr(keymap_item, "idname", "") != "secret.toggle_viewport_tab_bookmark"
                    or not getattr(keymap_item, "active", False)
                ):
                    continue
                try:
                    return keymap_item.to_string() or str(keymap_item.type)
                except Exception:
                    return str(getattr(keymap_item, "type", "W"))
    return "W"


class toggle_viewport_tab_bookmark(bpy.types.Operator):
    bl_idname = "secret.toggle_viewport_tab_bookmark"
    bl_label = "Toggle View Bookmark"
    bl_description = "Switch between two saved 3D View bookmarks. Use this to jump back to the nature assets you are painting with, like returning to a palette of colors, then press again to return to your paint target."
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        region_3d = context.region_data or getattr(context.space_data, "region_3d", None)
        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
            and context.space_data is not None
            and context.space_data.type == 'VIEW_3D'
            and region_3d is not None
        )

    def execute(self, context):
        return secret_paint_toggle_viewport_bookmark(context, report=self.report)


def secret_paint_toggle_viewport_bookmark(context, report=None):
    scene = context.scene
    storage_owner = _viewport_bookmark_storage_owner(context)
    if storage_owner is None:
        return {'CANCELLED'}
    legacy_scene = scene if scene != storage_owner else None
    region_3d = context.region_data or context.space_data.region_3d
    save_slot = _get_next_viewport_bookmark_slot(storage_owner, legacy_scene=legacy_scene)
    target_slot = 2 if save_slot == 1 else 1

    _capture_viewport_bookmark(storage_owner, save_slot, region_3d, legacy_scene=legacy_scene)
    target_bookmark = _load_viewport_bookmark(storage_owner, target_slot, legacy_scene=legacy_scene)
    _set_next_viewport_bookmark_slot(storage_owner, target_slot, legacy_scene=legacy_scene)

    if target_bookmark is None:
        saved_bookmark = _load_viewport_bookmark(storage_owner, save_slot, legacy_scene=legacy_scene)
        if saved_bookmark is not None:
            target_bookmark = _viewport_bookmark_offset_right(region_3d, saved_bookmark, 10.0)
            _save_viewport_bookmark(storage_owner, target_slot, target_bookmark, legacy_scene=legacy_scene)
            _apply_viewport_bookmark(region_3d, target_bookmark)
            context.area.tag_redraw()
            shortcut_text = _viewport_bookmark_shortcut_text(context)
            if report is not None:
                report({'INFO'}, f'Two View Bookmarks created, toggle with "{shortcut_text}"')
            return {'FINISHED'}
        if report is not None:
            report({'INFO'}, f"Saved viewport bookmark {save_slot} in this blend file. Move the view and run the shortcut again.")
        return {'FINISHED'}

    _apply_viewport_bookmark(region_3d, target_bookmark)
    context.area.tag_redraw()
    return {'FINISHED'}

# Keep the target-surface feature dormant without removing its implementation.
SECRET_PAINT_WORLD_TARGET_SURFACE_ENABLED = False
SECRET_PAINT_WORLD_RANDOM_Z_ENABLED = False
SECRET_PAINT_WORLD_ALIGN_TO_NORMAL_ENABLED = False
SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED = True

_SECRET_PAINT_WORLD_PAINT_CLASS_NAMES = (
    "secret_world_paint_mode",
    "secret_world_paint_tool_density",
    "secret_world_paint_tool_delete",
    "secret_world_paint_tool_single",
    "secret_world_paint_tool_bezier",
    "secret_world_paint_tool_slide",
    "secret_world_paint_tool_select",
    "secret_world_paint_tool_rotation",
    "secret_world_paint_tool_scale",
    "secret_world_paint_toggle_lock_surface",
    "secret_world_paint_toggle_target_surface",
    "secret_world_paint_toggle_wire_bounds_surfaces",
    "secret_world_paint_toggle_interpolate",
    "secret_world_paint_toggle_random_z",
    "secret_world_paint_toggle_align_to_normal",
    "secret_world_paint_adjust_size",
    "secret_world_paint_adjust_strength",
    "secret_world_paint_set_tool",
    "secret_world_paint_toggle_flag",
    "secret_world_paint_set_falloff_shape",
    "secret_world_paint_begin_adjust",
    "secret_world_paint_pick_source",
    "secret_world_paint_realize_selection",
    "secret_world_paint_exit",
    "SECRET_PT_world_paint_bezier_settings",
    "secret_world_paint_set_bezier_depth_mode",
)
_SECRET_PAINT_WORLD_PAINT_MODULE = None


def _secret_paint_world_paint_module():
    global _SECRET_PAINT_WORLD_PAINT_MODULE
    if _SECRET_PAINT_WORLD_PAINT_MODULE is None:
        _SECRET_PAINT_WORLD_PAINT_MODULE = import_module(".secret_paint_world_paint", __package__)
    return _SECRET_PAINT_WORLD_PAINT_MODULE


def _secret_paint_world_paint_classes():
    module = _secret_paint_world_paint_module()
    return tuple(getattr(module, class_name) for class_name in _SECRET_PAINT_WORLD_PAINT_CLASS_NAMES)


def register_secret_paint_world_paint_runtime():
    _secret_paint_world_paint_module().register_secret_paint_world_paint_runtime()


def unregister_secret_paint_world_paint_runtime():
    _secret_paint_world_paint_module().unregister_secret_paint_world_paint_runtime()


def unregister_secret_paint_disabled_world_paint_operator_stubs():
    return None


_SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED = False


def _secret_paint_object_mode_pie_builtin_mode_count(activeobj):
    object_type = getattr(activeobj, "type", "")
    if object_type in {"MESH", "GREASEPENCIL"}:
        return 6
    if object_type in {"CURVES", "ARMATURE"}:
        return 3
    if object_type in {"CURVE", "SURFACE", "META", "FONT", "LATTICE"}:
        return 2
    return 1


def secret_paint_object_mode_pie_draw(self, context):
    activeobj = context.active_object
    if activeobj is None:
        return

    pie = self.layout.menu_pie()
    # Blender compacts the built-in available modes; slot seven is bottom-left.
    native_mode_count = _secret_paint_object_mode_pie_builtin_mode_count(activeobj)
    for _slot in range(native_mode_count, 6):
        pie.separator()
    pie.operator("secret.paint_mode_pie", text="Secret Paint", icon='BRUSH_DATA')


def register_secret_paint_object_mode_pie():
    global _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED
    if _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED:
        return

    menu = getattr(bpy.types, "VIEW3D_MT_object_mode_pie", None)
    if menu is None:
        return

    try:
        menu.remove(secret_paint_object_mode_pie_draw)
    except Exception:
        pass

    menu.append(secret_paint_object_mode_pie_draw)
    _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED = True


def unregister_secret_paint_object_mode_pie():
    global _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED
    menu = getattr(bpy.types, "VIEW3D_MT_object_mode_pie", None)
    if menu is not None:
        try:
            menu.remove(secret_paint_object_mode_pie_draw)
        except Exception:
            pass

    _SECRET_PAINT_OBJECT_MODE_PIE_REGISTERED = False


SHARED_SECRET_PAINT_CLASSES = [
    orencurvepanel,
    toggle_display_bounds,
    subpanelutils,
    subpanelexportbiome,
    # Temporarily disabled; keep the operator class above for future re-enable.
    # secretpaint_update_modifier,
    orenscatterinstancesmodifiers,
    SelectObjectOperator,
    secret_paint_panel_select_object,
    ToggleVisibilityOperatorRender,
    orenscatter,
    secretpaint_mode_pie,
    orencurveswitch,
    clean_hair_orencurve,
    orengroup,
    vertexgrouppaint,
    realize_instances,
    export_obj_to_asset_library,
    select_biome_all,
    toggle_viewport_tab_bookmark,
    toggle_procedural,
    paint_from_library,
    paint_from_library_justimport,
    paint_from_library_switch,
    shared_material,
    open_folder,
    circular_array,
    straight_array,
    panel_modified_click,
    panel_keyboard_reorder,
    panel_keyboard_delete,
    # biomegroupreorder,
    # biomegroupreorder2,
    SelectBiomeOperator,
    ToggleVisibilityOperatorRenderBiome,
    toggle_display_bounds_biome,
    secretpaint_viewport_mask_biome,
    vertexgrouppaint_biome,
    biome_delete,
    assembly,
    # Temporarily disabled; keep the operator class above for future re-enable.
    # export_unreal,
    *_secret_paint_world_paint_classes(),
]


def _persist_world_paint_preference(_self, context):
    # Blender already dirties add-on preferences when an RNA value changes.
    # Saving synchronously from an update callback can serialize transient
    # keymap state while a modal interaction is still running.
    return None


def shared_secret_paint_preference_annotations(*, hidden_assets_collection_name="Hidden Assets"):
    return {
        "checkboxUseLegacyQPaint": bpy.props.BoolProperty(
            name="Use Legacy Q Painting",
            description="Keep the old Q behavior instead of using the new world paint modal mode",
            default=False,
        ),
        "checkboxKeepManualWhenTransferBiome": bpy.props.BoolProperty(
            name="Keep Manual When Transferring Biomes",
            description="When transferring biomes from a terrain to another: keep the paint systems in manual mode instead of automatically switching everything to procedural",
            default=False,
        ),
        "checkboxAutoAssemblyOnQ": bpy.props.BoolProperty(
            name="Auto Assembly On Q",
            description="When painting with Q using an object that has children, automatically create or update a Secret Assembly and paint with that assembly instead",
            default=False,
        ),
        "checkboxRaycastQWhenSingleSelected": bpy.props.BoolProperty(
            name="Q Raycast Ignores Single Selection",
            description="When enabled, pressing Q with exactly one selected object first uses the object under the mouse, then falls back to the active or selected object if nothing is found. With no selected objects, Q always uses the object under the mouse",
            default=False,
        ),
        "checkboxHideImported": bpy.props.BoolProperty(
            name="Hide Imported Paint Assets",
            description=f"When importing and painting objects from the asset browser (Q), hide them in a new collection called {hidden_assets_collection_name} (instead of having them visible next to the terrain)",
            default=False,
        ),
        "biomeAssetName": bpy.props.StringProperty(
            name="Asset Name",
            description="Leave empty to use the Active Object's name",
            default="Moss",
        ),
        "biomenamecategory": bpy.props.StringProperty(
            name="Catalog",
            description="Asset Browser Catalog for the asset that's being exported. Leave empty to not assign to any catalog",
            default="Biomes/Nature",
        ),
        "biomename": bpy.props.StringProperty(
            name="Folder",
            description="Export the .blend file to this path inside the currently open Asset Library. If .blend file aready exists: add the objects inside of it",
            default="/Biomes/All Biomes.blend",
        ),
        "trigger_viewport_mask": bpy.props.IntProperty(
            name="Trigger Viewport Mask",
            description="Automatically create the Viewport Mask whenever turning on the procedural distribution would create more than the specified number of instances. Useful to avoid slowing down the interface when working on huge terrains",
            default=15000,
        ),
        "trigger_auto_uvs": bpy.props.IntProperty(
            name="Trigger UV Reprojection",
            description="Set to 0 to disable. When the terrain has incorrect UVs, for example after sculpting the terrain with dynamic topology, the UVs will automatically be recreated on objects that have less than this approximate number of faces. This is needed in order to be able to paint manually (geometry node hair limitation; only needed for manual painting, not for the procedural distribution)",
            default=150000,
        ),
        "checkboxOverrideBrushes": bpy.props.BoolProperty(
            name="Override Brush Settings",
            description="Whenever jumping into paint mode with Q, the brush settings will be automatically set to optimal values",
            default=True,
        ),
        "object_size_density_multiplier": bpy.props.FloatProperty(
            name="Object Size Density Multiplier",
            description="Multiplies the automatic paint-system density calculated from the source object's size",
            default=SECRET_PAINT_OBJECT_SIZE_DENSITY_MULTIPLIER_DEFAULT,
            min=0.01,
            soft_min=0.25,
            soft_max=4.0,
            precision=2,
            update=_persist_world_paint_preference,
        ),
        "paint_only_current_surface": bpy.props.BoolProperty(
            name="Lock World Paint To Current Surface",
            description="When enabled, world paint stays locked to the current surface until toggled off with the modal shortcut. This preference is saved globally and reused in new projects",
            default=False,
            update=_persist_world_paint_preference,
        ),
        "allow_world_paint_wire_bounds_surfaces": bpy.props.BoolProperty(
            name="Allow World Paint On Wire/Bounds Surfaces",
            description="When enabled, world paint can target surfaces whose display type is set to Wire or Bounds. This preference is saved globally and reused in new projects",
            default=True,
            update=_persist_world_paint_preference,
        ),
        "always_use_2d_world_paint_brush_ui": bpy.props.BoolProperty(
            name="Always Use 2D World Paint Brush UI",
            description="When enabled, world paint always draws the brush as a 2D overlay circle. When disabled, it uses the 3D surface brush preview",
            default=False,
            update=_persist_world_paint_preference,
        ),
    }


def draw_shared_secret_paint_preferences(layout, preferences):
    for property_name in (
        "checkboxUseLegacyQPaint",
        "checkboxKeepManualWhenTransferBiome",
        "checkboxAutoAssemblyOnQ",
        "checkboxRaycastQWhenSingleSelected",
        "checkboxHideImported",
        "checkboxOverrideBrushes",
        "object_size_density_multiplier",
        "paint_only_current_surface",
        "allow_world_paint_wire_bounds_surfaces",
        "always_use_2d_world_paint_brush_ui",
        "trigger_viewport_mask",
        "trigger_auto_uvs",
    ):
        if hasattr(preferences, property_name):
            layout.prop(preferences, property_name)


_EXPORTED_GLOBALS_BLACKLIST = {
    "__all__",
    "_EXPORTED_GLOBALS_BLACKLIST",
}

__all__ = [
    name for name in globals()
    if name not in _EXPORTED_GLOBALS_BLACKLIST and not (name.startswith("__") and name.endswith("__"))
]
