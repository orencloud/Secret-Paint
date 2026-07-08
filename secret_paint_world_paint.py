import json
import math
import os
import random
import sys
import time

import blf
import bpy
import gpu
from bpy.app.handlers import persistent
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from . import secret_paint_shared as shared


WORLD_PAINT_TARGET_ENABLED_PROP = "secret_paint_target_surface_enabled"
WORLD_PAINT_TARGET_KIND_PROP = "secret_paint_target_kind"
WORLD_PAINT_TARGET_OWNER_PROP = "secret_paint_target_owner"
WORLD_PAINT_LOCKED_TERRAIN_PROP = "secret_paint_locked_terrain"
WORLD_PAINT_PROXY_PROP = "secret_paint_proxy"
WORLD_PAINT_CURVE_DRAW_PROP = "secret_paint_curve_draw"
WORLD_PAINT_CURVE_DRAW_NATIVE_PROP = "secret_paint_curve_draw_native"
WORLD_PAINT_SELECTION_ATTR = "secret_paint_selected"
WORLD_PAINT_STABLE_ID_ATTR = "secret_stable_curve_id"
WORLD_PAINT_BRUSH_RADIUS_PROP = "secret_paint_brush_radius"
WORLD_PAINT_DENSITY_SPACING_PROP = getattr(
    shared,
    "SECRET_PAINT_WORLD_DENSITY_SPACING_PROP",
    "secret_paint_density_spacing",
)
WORLD_PAINT_CACHE_REV_PROP = "secret_paint_curve_cache_rev"
WORLD_PAINT_STABLE_IDS_READY_PROP = "secret_paint_stable_ids_ready"
WORLD_PAINT_NEXT_STABLE_ID_PROP = "secret_paint_next_stable_curve_id"
WORLD_PAINT_STABLE_IDS_MIGRATED_PROP = getattr(
    shared,
    "SECRET_PAINT_STABLE_IDS_MIGRATED_PROP",
    ".secret_paint_stable_ids_migrated",
)
WORLD_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP = getattr(
    shared,
    "SECRET_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP",
    ".secret_paint_stable_ids_migrated_curve_count",
)
WORLD_LIVE_UPDATE_INTERVAL = 1.0 / 20.0
WORLD_PICK_SOURCE_HOLD_UPDATE_INTERVAL = 1.0 / 60.0
WORLD_PICK_SOURCE_HOLD_MIN_MOUSE_DELTA_PX = 4.0
WORLD_SCREEN_BRUSH_RADIUS_SCALE = 100.0
WORLD_MIN_OPERATION_RADIUS = 0.0001
WORLD_DENSITY_SPACING_EPSILON = 1.0e-6
WORLD_DENSITY_PREVIEW_MAX_VISIBLE_DOTS = 320
WORLD_DENSITY_PREVIEW_SOLID_STEPS = 48
WORLD_DENSITY_PREVIEW_SPARSE_RING_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))
WORLD_ADJUST_DRAG_SCALE = 0.008
WORLD_CUSTOM_ADJUST_UI_ENABLED = False
WORLD_SIZE_ADJUST_SHORTCUT_ENABLED = bool(getattr(shared, "SECRET_PAINT_WORLD_SIZE_ADJUST_ENABLED", False))
WORLD_NATIVE_DENSITY_MODAL_ADJUST_ENABLED = True

WORLD_TARGET_KIND_MESH = "MESH"
WORLD_TARGET_KIND_SECRET_INSTANCE = "SECRET_INSTANCE"

WORLD_TOOL_DENSITY = "DENSITY"
WORLD_TOOL_DELETE = "DELETE"
WORLD_TOOL_SINGLE = "SINGLE"
WORLD_TOOL_SLIDE = "SLIDE"
WORLD_TOOL_SELECT = "SELECT"
WORLD_TOOL_COMB = "COMB"
WORLD_TOOL_SCALE = "SCALE"
WORLD_TOOL_BEZIER = "BEZIER"
WORLD_ACTION_PICK_SOURCE = "PICK_SOURCE"
WORLD_ACTION_BRUSH_SWITCH = "BRUSH_SWITCH"

WORLD_TOOL_ITEMS = (
    (WORLD_TOOL_DENSITY, "Density", "Paint density"),
    (WORLD_TOOL_DELETE, "Delete", "Delete painted instances"),
    (WORLD_TOOL_SINGLE, "Single", "Place one hair per click"),
    (WORLD_TOOL_SLIDE, "Slide", "Slide nearby strands"),
    (WORLD_TOOL_SELECT, "Select", "Select strands"),
    (WORLD_TOOL_COMB, "Rotation", "Comb and rotate strands"),
    (WORLD_TOOL_SCALE, "Scale", "Scale strands"),
    (WORLD_TOOL_BEZIER, "Bezier", "Draw 3D Bezier curves"),
)

WORLD_TOOL_LABELS = {
    WORLD_TOOL_DENSITY: "Density",
    WORLD_TOOL_DELETE: "Delete",
    WORLD_TOOL_SINGLE: "Single",
    WORLD_TOOL_SLIDE: "Slide",
    WORLD_TOOL_SELECT: "Select",
    WORLD_TOOL_COMB: "Rotation",
    WORLD_TOOL_SCALE: "Scale",
    WORLD_TOOL_BEZIER: "Bezier",
}

WORLD_TOOLBAR_SPECS = (
    (WORLD_TOOL_DENSITY, "Density", "Paint instances up to the target density on the hovered surface.", "BRUSH_DATA"),
    (WORLD_TOOL_DELETE, "Delete", "Delete painted instances with the native delete brush.", "TRASH"),
    (WORLD_TOOL_SLIDE, "Slide", "Slide nearby strands across the surface.", "EMPTY_ARROWS"),
    (WORLD_TOOL_SCALE, "Scale", "Grow, shrink, normalize, or randomize strand length.", "ARROW_LEFTRIGHT"),
    (WORLD_TOOL_COMB, "Rotation", "Comb and rotate painted strands.", "FORCE_CURVE"),
    (WORLD_TOOL_SINGLE, "Single", "Place one instance per click on the hovered surface.", "ADD"),
    (WORLD_TOOL_SELECT, "Select", "Select or deselect painted strands.", "RESTRICT_SELECT_OFF"),
    (WORLD_TOOL_BEZIER, "Bezier", "Draw 3D Bezier curves on the hovered surface.", "CURVE_BEZCURVE"),
)

WORLD_WORKSPACE_TOOL_IDS = {
    tool_id: f"secret.world_paint_tool_{tool_id.lower()}"
    for tool_id, _label, _description, _icon in WORLD_TOOLBAR_SPECS
}
WORLD_TOOL_OPERATOR_IDS = {
    WORLD_TOOL_DENSITY: "secret.world_paint_tool_density",
    WORLD_TOOL_DELETE: "secret.world_paint_tool_delete",
    WORLD_TOOL_SINGLE: "secret.world_paint_tool_single",
    WORLD_TOOL_SLIDE: "secret.world_paint_tool_slide",
    WORLD_TOOL_SELECT: "secret.world_paint_tool_select",
    WORLD_TOOL_COMB: "secret.world_paint_tool_rotation",
    WORLD_TOOL_SCALE: "secret.world_paint_tool_scale",
    WORLD_TOOL_BEZIER: "secret.world_paint_tool_bezier",
}
WORLD_FLAG_OPERATOR_IDS = {
    "LOCK_SURFACE": "secret.world_paint_toggle_lock_surface",
    "TARGET_SURFACE": "secret.world_paint_toggle_target_surface",
    "ALLOW_WIRE_BOUNDS_SURFACES": "secret.world_paint_toggle_wire_bounds_surfaces",
    "INTERPOLATE": "secret.world_paint_toggle_interpolate",
    "RANDOM_Z": "secret.world_paint_toggle_random_z",
    "ALIGN_TO_NORMAL": "secret.world_paint_toggle_align_to_normal",
}
WORLD_ADJUST_OPERATOR_IDS = {
    "SIZE": "secret.world_paint_adjust_size",
    "STRENGTH": "secret.world_paint_adjust_strength",
}
WORLD_PAINT_STATUS_TEXT = "Secret Paint Mode: LMB paint, RMB remove, paint key picks source, F size, Alt+F density/strength"
WORLD_TOOL_FROM_WORKSPACE = {
    workspace_tool_id: tool_id
    for tool_id, workspace_tool_id in WORLD_WORKSPACE_TOOL_IDS.items()
}

WORLD_FLAG_ITEMS = (
    ("LOCK_SURFACE", "Lock Terrain", "Lock painting to the current terrain or all selected terrains; select multiple terrains before pressing the button to paint and target all of them"),
    ("TARGET_SURFACE", "Target Surface", "Allow the current Secret Paint system to be painted on as a target surface"),
    ("ALLOW_WIRE_BOUNDS_SURFACES", "Wire", "Allow painting on surfaces whose display type is Wire or Bounds"),
    ("INTERPOLATE", "Interpolate", "Toggle interpolation for Add/Density brushes"),
    ("RANDOM_Z", "Random Z", "Toggle random Z rotation on the active system"),
    ("ALIGN_TO_NORMAL", "Align To Normal", "Toggle align-to-normal on the active system"),
)

WORLD_SHORTCUT_ACTIONS = (
    ("TOOL", WORLD_TOOL_DENSITY, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_DENSITY], "", "", "D", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_DELETE, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_DELETE], "", "", "X", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_SINGLE, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_SINGLE], "", "", "ONE", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_SLIDE, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_SLIDE], "", "", "THREE", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_SELECT, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_SELECT], "", "", "FOUR", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_COMB, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_COMB], "", "", "R", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_SCALE, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_SCALE], "", "", "S", False, False, False, ("3D View",)),
    ("TOOL", WORLD_TOOL_BEZIER, WORLD_TOOL_OPERATOR_IDS[WORLD_TOOL_BEZIER], "", "", "FIVE", False, False, False, ("3D View",)),
    ("FLAG", "LOCK_SURFACE", WORLD_FLAG_OPERATOR_IDS["LOCK_SURFACE"], "", "", "TWO", False, False, False, ("3D View",)),
    ("FLAG", "TARGET_SURFACE", WORLD_FLAG_OPERATOR_IDS["TARGET_SURFACE"], "", "", "I", False, False, False, ("3D View",)),
    ("FLAG", "ALLOW_WIRE_BOUNDS_SURFACES", WORLD_FLAG_OPERATOR_IDS["ALLOW_WIRE_BOUNDS_SURFACES"], "", "", "NONE", False, False, False, ("3D View",)),
    ("FLAG", "INTERPOLATE", WORLD_FLAG_OPERATOR_IDS["INTERPOLATE"], "", "", "Y", False, False, False, ("3D View",)),
    ("FLAG", "RANDOM_Z", WORLD_FLAG_OPERATOR_IDS["RANDOM_Z"], "", "", "T", False, False, False, ("3D View",)),
    ("FLAG", "ALIGN_TO_NORMAL", WORLD_FLAG_OPERATOR_IDS["ALIGN_TO_NORMAL"], "", "", "N", False, False, False, ("3D View",)),
    ("ADJUST", "SIZE", WORLD_ADJUST_OPERATOR_IDS["SIZE"], "", "", "F", False, False, False, ("3D View", "Sculpt Curves")),
    ("ADJUST", "STRENGTH", WORLD_ADJUST_OPERATOR_IDS["STRENGTH"], "", "", "F", False, False, True, ("3D View", "Sculpt Curves")),
    ("ACTION", WORLD_ACTION_PICK_SOURCE, "secret.world_paint_pick_source", "", "", "Q", False, False, False, ("3D View", "Sculpt Curves")),
    ("ACTION", WORLD_ACTION_BRUSH_SWITCH, "secret.paintbrushswitch", "", "", "Q", True, False, False, ("Object Mode", "Sculpt Curves", "Weight Paint", "Curve")),
)

_WORLD_STATE = {
    "operator": None,
    "runtime_registered": False,
    "ui_hijacked": False,
    "header_draw_original": None,
    "tool_header_draw_original": None,
    "toolbar_draw_cls_original": None,
    "toolbar_original": None,
    "toolbar_temp_restore_depth": 0,
    "suppressed_keymap_items": [],
    "suppressed_world_paint_shortcut_items": [],
    "curve_data_cache": {},
    "curve_cache_signatures": {},
    "last_live_update_time": 0.0,
    "stable_id_sync_running": False,
    "object_mode_guard_until": 0.0,
    "object_mode_guard_system_names": set(),
    "object_mode_guard_timer_running": False,
    "exit_consume_paint_until": 0.0,
    "view3d_builtin_tool_entries_checked": False,
    "brush_debug_last_state": None,
    "shift_delete_debug_last_state": None,
    "source_curve_candidates_cache": {},
    "source_system_candidates_cache": {},
    "shortcut_event_types_cache": {},
    "base_paint_keymap_items_cache": None,
    "viewport_bookmark_keymap_item_groups_cache": None,
    "runtime_keymap_sync_signature": None,
    "runtime_keymap_sync_last_check": 0.0,
    "right_delete_brush_keymaps": [],
}

WORLD_Q_SHORTCUT_DEBUG_LOG_PATH = None
WORLD_Q_SHORTCUT_DEBUG_ENABLED = False


def reset_q_shortcut_debug_log(reason=""):
    return None


def _q_debug_value(value):
    try:
        if hasattr(value, "name"):
            return getattr(value, "name", "")
    except Exception:
        pass
    try:
        return repr(value)
    except Exception:
        return "<unrepr>"


def _q_debug_keymap_summary(context):
    wm = getattr(context, "window_manager", None) if context is not None else None
    keyconfigs = getattr(wm, "keyconfigs", None)
    if keyconfigs is None:
        return "no_keyconfigs"

    rows = []
    idnames = {"secret.paint", "secret.paintbrushswitch", "secret.world_paint_pick_source"}
    for keyconfig_name in ("user", "addon"):
        keyconfig = getattr(keyconfigs, keyconfig_name, None)
        if keyconfig is None:
            continue
        for keymap_name in ("Object Mode", "Sculpt Curves", "Weight Paint", "Curve", "3D View"):
            keymap = keyconfig.keymaps.get(keymap_name)
            if keymap is None:
                continue
            for keymap_item in keymap.keymap_items:
                try:
                    idname = getattr(keymap_item, "idname", "")
                    if idname not in idnames:
                        continue
                    rows.append(
                        "/".join(
                            (
                                keyconfig_name,
                                keymap_name,
                                idname,
                                str(getattr(keymap_item, "type", "")),
                                str(getattr(keymap_item, "value", "")),
                                "active=" + str(bool(getattr(keymap_item, "active", False))),
                                "shift=" + str(bool(getattr(keymap_item, "shift", False))),
                                "ctrl=" + str(bool(getattr(keymap_item, "ctrl", False))),
                                "alt=" + str(bool(getattr(keymap_item, "alt", False))),
                                "userdef=" + str(bool(getattr(keymap_item, "is_user_defined", False))),
                            )
                        )
                    )
                except Exception:
                    continue
    return "; ".join(rows) if rows else "none"


def _q_debug_log(label, context=None, **fields):
    return None


def _q_debug_log_keymaps(label, context=None, **fields):
    return None

WORLD_BLOCKED_SURFACE_DISPLAY_TYPES = {"BOUNDS", "WIRE"}
WORLD_SOURCE_VISIBLE_DISPLAY_TYPES = {"BOUNDS", "WIRE"}
WORLD_SOURCE_VISIBLE_HIT_DISTANCE_PX = 8.0
WORLD_SOURCE_CURVE_HIT_DISTANCE_PX = 12.0
WORLD_SOURCE_CURVE_MAX_SAMPLE_SEGMENTS = 192
WORLD_SOURCE_WIRE_MAX_EDGES = 6000
WORLD_ENTRY_SOURCE_HOLD_DELAY = 0.18
WORLD_BOUND_BOX_EDGE_INDICES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)
WORLD_NATIVE_DENSITY_TOOL_IDS = (
    "builtin_brush.density",
    "builtin_brush.Density",
)
WORLD_OBJECT_MODE_FALLBACK_TOOL_IDS = {
    "builtin.select_box",
    "builtin.select",
}
WORLD_NATIVE_TOOL_BRUSH_TYPES = {
    WORLD_TOOL_DELETE: "DELETE",
    WORLD_TOOL_SINGLE: "ADD",
    WORLD_TOOL_SLIDE: "SLIDE",
    WORLD_TOOL_SELECT: "SELECTION_PAINT",
    WORLD_TOOL_COMB: "COMB",
    WORLD_TOOL_SCALE: "GROW_SHRINK",
}
WORLD_NATIVE_STRENGTH_TOOL_IDS = {
    WORLD_TOOL_SLIDE,
    WORLD_TOOL_COMB,
    WORLD_TOOL_SCALE,
}
WORLD_NATIVE_TOOL_BY_BRUSH_TYPE = {
    brush_type: tool_id
    for tool_id, brush_type in WORLD_NATIVE_TOOL_BRUSH_TYPES.items()
}
WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE = dict(shared.SECRET_PAINT_NATIVE_CURVES_TOOL_IDS_BY_TYPE)
WORLD_PAINT_SHORTCUT_OPERATOR_IDNAMES = {
    "secret.paint",
    "secret.paintbrushswitch",
    "secret.world_paint_begin_adjust",
    "secret.world_paint_pick_source",
    "secret.world_paint_set_tool",
    "secret.world_paint_toggle_flag",
}
WORLD_PAINT_SHORTCUT_OPERATOR_IDNAMES.update(WORLD_TOOL_OPERATOR_IDS.values())
WORLD_PAINT_SHORTCUT_OPERATOR_IDNAMES.update(WORLD_FLAG_OPERATOR_IDS.values())
WORLD_PAINT_SHORTCUT_OPERATOR_IDNAMES.update(WORLD_ADJUST_OPERATOR_IDS.values())
WORLD_BASE_PAINT_SHORTCUT_OPERATOR_IDNAMES = {
    "secret.paint",
    "secret.paintbrushswitch",
}
WORLD_MODIFIER_NAMES = ("shift", "ctrl", "alt", "oskey", "hyper")
WORLD_MODIFIER_KEY_TYPES = {
    "LEFT_SHIFT": "shift",
    "RIGHT_SHIFT": "shift",
    "LEFT_CTRL": "ctrl",
    "RIGHT_CTRL": "ctrl",
    "LEFT_ALT": "alt",
    "RIGHT_ALT": "alt",
    "OSKEY": "oskey",
    "LEFT_OSKEY": "oskey",
    "RIGHT_OSKEY": "oskey",
    "HYPER": "hyper",
    "LEFT_HYPER": "hyper",
    "RIGHT_HYPER": "hyper",
}
WORLD_BRUSH_SWITCH_COPY_INPUTS = (
    "Input_2",
    "Input_9",
    "Input_68",
    "Input_86",
    "Input_89",
    "Input_91",
    "Input_92",
)
WORLD_SYSTEM_COPY_OBJECT_DISPLAY_ATTRS = (
    "display_type",
    "display_bounds_type",
)
WORLD_SURFACE_DEFORM_MODIFIER_TYPES = {
    "ARMATURE",
    "CAST",
    "CURVE",
    "DISPLACE",
    "HOOK",
    "LAPLACIANDEFORM",
    "LATTICE",
    "MESH_DEFORM",
    "SHRINKWRAP",
    "SIMPLE_DEFORM",
    "SMOOTH",
    "CORRECTIVE_SMOOTH",
    "LAPLACIANSMOOTH",
    "SURFACE_DEFORM",
    "WARP",
    "WAVE",
}
WORLD_PRIMARY_PAINT_EVENTS = {
    'LEFTMOUSE',
    'ACTIONMOUSE',
    'SELECTMOUSE',
}
WORLD_PRIMARY_PAINT_ACTIVE_VALUES = {'PRESS', 'CLICK_DRAG'}
WORLD_PRIMARY_PAINT_END_VALUES = {'RELEASE', 'CLICK', 'DOUBLE_CLICK', 'NOTHING'}
WORLD_UI_TOOL_SYNC_DELAY = 0.01
WORLD_NATIVE_TOOL_OVERRIDE_SECONDS = 0.75
WORLD_NATIVE_IDLE_SYNC_INTERVAL = 0.25
WORLD_NATIVE_IDLE_HOVER_RAYCAST_INTERVAL = 1.0 / 24.0
WORLD_NATIVE_IDLE_HOVER_RAYCAST_DISTANCE_PX = 5.0
WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE = True
WORLD_BRUSH_CURSOR_REENTRY_REFRESH_INTERVAL = 0.25
WORLD_BRUSH_CONTROL_SYNC_INTERVAL = 1.0 / 30.0
WORLD_NATIVE_ADJUST_LIVE_SLIDER_SYNC_ENABLED = False
WORLD_DEFERRED_BRUSH_SETTINGS_FLUSH_SECONDS = 0.035
WORLD_NATIVE_BRUSH_DEBUG_LOG_PATH = None
WORLD_NATIVE_BRUSH_DEBUG_ENABLED = False
WORLD_SHIFT_DELETE_DEBUG_LOG_PATH = None
WORLD_SHIFT_DELETE_DEBUG_ENABLED = False


def _world_float_equal(value, target, epsilon=1.0e-6):
    try:
        return abs(float(value) - float(target)) <= epsilon
    except Exception:
        return False


def _world_attr_value(owner, prop_name, default=None):
    if owner is None or not hasattr(owner, prop_name):
        return default
    try:
        return getattr(owner, prop_name)
    except Exception:
        return default


def _world_set_attr_if_different(owner, prop_name, value, *, epsilon=None):
    if owner is None or not hasattr(owner, prop_name):
        return False
    current = _world_attr_value(owner, prop_name)
    try:
        if epsilon is not None:
            if _world_float_equal(current, value, epsilon):
                return False
        elif current == value:
            return False
    except Exception:
        pass
    try:
        setattr(owner, prop_name, value)
        return True
    except Exception:
        return False


def _world_idprop_value(owner, key, default=None):
    if owner is None:
        return default
    try:
        value = owner.get(key, default)
    except Exception:
        value = default
    if value is default:
        try:
            value = owner[key]
        except Exception:
            value = default
    return value


def _world_set_idprop_if_different(owner, key, value, *, epsilon=None):
    if owner is None:
        return False
    current = _world_idprop_value(owner, key, None)
    try:
        if epsilon is not None:
            if _world_float_equal(current, value, epsilon):
                return False
        elif current == value:
            return False
    except Exception:
        pass
    try:
        owner[key] = value
        return True
    except Exception:
        return False


def _native_brush_debug_value(value):
    try:
        if isinstance(value, float):
            return f"{value:.6f}"
        if value is None:
            return "None"
        return str(value).replace("\n", "\\n").replace("\r", "\\r").replace("\t", " ")
    except Exception:
        return "<error>"


def _active_workspace_tool_id(context):
    if (getattr(context, "mode", "") or "") == 'SCULPT_CURVES':
        return ""
    try:
        return context.workspace.tools.from_space_view3d_mode(context.mode).idname
    except Exception:
        return ""


def _native_brush_debug_state(context, operator=None):
    state = {}
    try:
        state["mode"] = getattr(context, "mode", "")
    except Exception:
        state["mode"] = ""
    state["workspace"] = _active_workspace_tool_id(context)

    try:
        brush_container = _tool_settings_brush_container(context)
        brush = getattr(brush_container, "brush", None) if brush_container is not None else None
    except Exception:
        brush = None
    state["brush"] = getattr(brush, "name", "") if brush is not None else ""
    state["brush_type"] = shared.secret_paint_curves_brush_type(brush) if brush is not None else ""
    state["brush_size"] = getattr(brush, "size", "") if brush is not None else ""
    state["brush_falloff"] = getattr(brush, "falloff_shape", "") if brush is not None else ""
    settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
    state["brush_min_distance"] = getattr(settings, "minimum_distance", "") if settings is not None else ""
    state["brush_density_mode"] = getattr(settings, "density_mode", "") if settings is not None else ""

    try:
        state["wm_density"] = getattr(context.window_manager, "secret_paint_world_density_spacing", "")
        state["wm_size"] = getattr(context.window_manager, "secret_paint_world_brush_radius", "")
    except Exception:
        state["wm_density"] = ""
        state["wm_size"] = ""

    active_obj = getattr(context, "active_object", None)
    state["active_object"] = getattr(active_obj, "name", "") if active_obj is not None else ""
    state["active_object_type"] = getattr(active_obj, "type", "") if active_obj is not None else ""

    if operator is not None:
        state["tool_id"] = getattr(operator, "tool_id", "")
        state["density_spacing"] = getattr(operator, "density_spacing", "")
        state["brush_radius_setting"] = getattr(operator, "brush_radius_setting", "")
        state["stroke_active"] = getattr(operator, "stroke_active", "")
        state["native_session"] = getattr(operator, "_native_density_session_active", "")
        state["native_mode"] = getattr(operator, "_native_density_interaction_mode", "")
        state["erase"] = getattr(operator, "_native_density_stroke_erase", "")
        state["override_brush_type"] = getattr(operator, "_native_tool_override_brush_type", "")
        try:
            state["active_native_type"] = operator._active_native_brush_type()
        except Exception:
            state["active_native_type"] = ""
        state["active_system"] = getattr(operator, "active_system_name", "")
        try:
            system_obj = operator._current_system()
        except Exception:
            system_obj = None
        modifier = None
        try:
            modifier = _secret_modifier(system_obj)
        except Exception:
            modifier = None
        if modifier is not None:
            try:
                state["modifier_socket_11"] = modifier["Socket_11"]
            except Exception:
                state["modifier_socket_11"] = ""
        else:
            state["modifier_socket_11"] = ""

    return state


def _native_brush_debug_reset(reason=""):
    _WORLD_STATE["brush_debug_last_state"] = None
    return None


def _native_brush_debug_log(label, context=None, operator=None, force=False, **fields):
    return None


def _shift_delete_debug_reset(reason=""):
    _WORLD_STATE["shift_delete_debug_last_state"] = None
    return None


def _shift_delete_debug_log(label, context=None, operator=None, event=None, force=False, **fields):
    return None


def _world_operator():
    operator = _WORLD_STATE.get("operator")
    if operator is None:
        return None
    try:
        if getattr(operator, "_running", False):
            return operator
    except ReferenceError:
        _WORLD_STATE["operator"] = None
        return None
    _WORLD_STATE["operator"] = None
    return None

def is_world_paint_running():
    return _world_operator() is not None


def is_world_paint_event_in_view(context, event=None):
    operator = _world_operator()
    if operator is None:
        return False
    if event is None:
        return True
    try:
        return operator._event_is_in_world_paint_view(context, event)
    except Exception:
        return False


def is_base_paint_shortcut_event(context, event=None):
    if event is None:
        return False
    try:
        return _event_matches_base_paint_shortcut(context, event)
    except Exception:
        return False


def remember_base_paint_shortcut_release(context, event=None):
    operator = _world_operator()
    if operator is None or event is None:
        return False
    try:
        return operator._remember_paint_shortcut_release_chord(context, event)
    except Exception:
        return False


def switch_active_system_brush_under_mouse(context, event=None):
    operator = _world_operator()
    if operator is None:
        return False
    try:
        if not is_world_paint_event_in_view(context, event):
            return False
        return operator._switch_active_system_brush_under_mouse(context, event)
    except Exception:
        return False


def is_world_paint_cage_preview_active():
    operator = _world_operator()
    if operator is None:
        return False
    try:
        if not bool(getattr(operator, "_selection_preview_active", False)):
            return False
        if bool(getattr(operator, "_pick_source_hold_active", False)):
            return True
        return time.perf_counter() < float(getattr(operator, "_selection_preview_cage_until", 0.0) or 0.0)
    except Exception:
        return False


def preview_entry_source_pick(context, picked_obj, *, hold=False):
    operator = _world_operator()
    if operator is None or picked_obj is None:
        return False
    try:
        return operator._begin_entry_source_preview(context, picked_obj, hold=hold)
    except Exception:
        return False


def consume_recent_world_paint_exit():
    exit_until = float(_WORLD_STATE.get("exit_consume_paint_until", 0.0) or 0.0)
    if exit_until <= 0.0 or time.perf_counter() > exit_until:
        _WORLD_STATE["exit_consume_paint_until"] = 0.0
        return False
    _WORLD_STATE["exit_consume_paint_until"] = 0.0
    return True


def _world_target_surface_feature_enabled():
    return bool(getattr(shared, "SECRET_PAINT_WORLD_TARGET_SURFACE_ENABLED", False))


_WORLD_FLAG_FEATURE_SWITCHES = {
    "TARGET_SURFACE": "SECRET_PAINT_WORLD_TARGET_SURFACE_ENABLED",
    "RANDOM_Z": "SECRET_PAINT_WORLD_RANDOM_Z_ENABLED",
    "ALIGN_TO_NORMAL": "SECRET_PAINT_WORLD_ALIGN_TO_NORMAL_ENABLED",
}


def _world_flag_available(flag_id):
    feature_name = _WORLD_FLAG_FEATURE_SWITCHES.get(flag_id)
    return feature_name is None or bool(getattr(shared, feature_name, False))


def _world_shortcut_available(shortcut):
    if shortcut[0] == "ADJUST" and shortcut[1] == "SIZE":
        return WORLD_SIZE_ADJUST_SHORTCUT_ENABLED
    return shortcut[0] != "FLAG" or _world_flag_available(shortcut[1])


def _schedule_world_tool_sync():
    def _sync():
        operator = _world_operator()
        if operator is None:
            return None
        try:
            _native_brush_debug_log("timer.sync_workspace.before", bpy.context, operator, force=True)
            operator._sync_workspace_tool(bpy.context)
            _native_brush_debug_log("timer.sync_workspace.after", bpy.context, operator, force=True)
            _tag_redraw_view3d_areas(bpy.context)
        except Exception:
            pass
        return None

    try:
        bpy.app.timers.register(_sync, first_interval=WORLD_UI_TOOL_SYNC_DELAY)
    except Exception:
        pass


def _ensure_bl_ui_toolsystem():
    scripts_root = bpy.utils.system_resource('SCRIPTS')
    startup_path = os.path.join(scripts_root, "startup")
    bl_ui_path = os.path.join(startup_path, "bl_ui")
    if startup_path not in sys.path:
        sys.path.append(startup_path)
    if bl_ui_path not in sys.path:
        sys.path.append(bl_ui_path)

    from bl_ui.space_toolsystem_common import ToolDef
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active

    return ToolDef, VIEW3D_PT_tools_active


def _workspace_tool_id_for_world_tool(tool_id):
    return WORLD_WORKSPACE_TOOL_IDS.get(tool_id, "")


def _world_tool_from_workspace_id(workspace_tool_id):
    return WORLD_TOOL_FROM_WORKSPACE.get(workspace_tool_id)


def _native_brush_type_for_world_tool(tool_id):
    return WORLD_NATIVE_TOOL_BRUSH_TYPES.get(tool_id, "")


def _curves_brush_type_for_world_tool(tool_id):
    if tool_id == WORLD_TOOL_DENSITY:
        return "DENSITY"
    return _native_brush_type_for_world_tool(tool_id)


def _native_workspace_tool_id_for_world_tool(tool_id):
    brush_type = _curves_brush_type_for_world_tool(tool_id)
    if not brush_type:
        return ""
    tool_ids = WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.get(brush_type, ())
    return tool_ids[0] if tool_ids else ""


def _world_tool_from_native_brush_type(brush_type):
    return WORLD_NATIVE_TOOL_BY_BRUSH_TYPE.get(brush_type)


def _world_tool_uses_native_brush(tool_id):
    return bool(_native_brush_type_for_world_tool(tool_id))


def _world_tool_accepts_object_mode_fallback_tool(tool_id, workspace_tool_id):
    return (
        tool_id == WORLD_TOOL_BEZIER
        and workspace_tool_id in (WORLD_OBJECT_MODE_FALLBACK_TOOL_IDS | {"builtin.draw"})
    )


def _is_world_workspace_tool_id(workspace_tool_id):
    return bool(workspace_tool_id) and workspace_tool_id.startswith("secret.world_paint_tool_")


def _world_tool_spec(tool_id):
    for spec_tool_id, label, description, icon in WORLD_TOOLBAR_SPECS:
        if spec_tool_id == tool_id:
            return {
                "tool_id": spec_tool_id,
                "label": label,
                "description": description,
                "icon": icon,
            }
    return {
        "tool_id": tool_id,
        "label": WORLD_TOOL_LABELS.get(tool_id, tool_id),
        "description": WORLD_TOOL_LABELS.get(tool_id, tool_id),
        "icon": 'NONE',
    }


def _shortcut_keymap_active(context, keymap_name):
    if keymap_name == "Sculpt Curves":
        return getattr(context, "mode", "") == 'SCULPT_CURVES'
    return True


def _shortcut_operator_identities(shortcut):
    action_kind, action_value, idname, prop_name, prop_value, _key_type, _shift, _ctrl, _alt, _keymap_names = shortcut
    identities = [(idname, prop_name, prop_value)]
    if action_kind == "TOOL":
        identities.append(("secret.world_paint_set_tool", "tool_id", action_value))
    elif action_kind == "FLAG":
        identities.append(("secret.world_paint_toggle_flag", "flag_id", action_value))
    elif action_kind == "ADJUST":
        identities.append(("secret.world_paint_begin_adjust", "adjust_mode", action_value))
    return identities


def _keymap_item_matches_shortcut_identity(keymap_item, idname, prop_name, prop_value):
    if getattr(keymap_item, "idname", "") != idname:
        return False
    if not prop_name:
        return True

    properties = getattr(keymap_item, "properties", None)
    if properties is None:
        return False
    try:
        if hasattr(properties, "is_property_set") and not properties.is_property_set(prop_name):
            return False
        return getattr(properties, prop_name) == prop_value
    except Exception:
        return False


def _active_keyboard_shortcut_items(keymap_items):
    return [
        keymap_item
        for keymap_item in keymap_items
        if (
            bool(getattr(keymap_item, "active", False))
            and getattr(keymap_item, "map_type", "") == 'KEYBOARD'
        )
    ]


def _allow_default_shortcut_fallback(shortcut, keymap_items):
    if not keymap_items:
        return True
    if shortcut[0] == "ADJUST" and shortcut[1] in {"SIZE", "STRENGTH"}:
        return not _active_keyboard_shortcut_items(keymap_items)
    return False


def _clear_world_keymap_lookup_caches():
    _WORLD_STATE["shortcut_event_types_cache"] = {}
    _WORLD_STATE["base_paint_keymap_items_cache"] = None
    _WORLD_STATE["viewport_bookmark_keymap_item_groups_cache"] = None


def _shortcut_user_items(context, shortcut):
    _action_kind, _action_value, _idname, _prop_name, _prop_value, _key_type, _shift, _ctrl, _alt, keymap_names = shortcut
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    user_keyconfig = getattr(keyconfigs, "user", None)
    if user_keyconfig is None:
        return ()

    items = []
    operator_identities = _shortcut_operator_identities(shortcut)
    for keymap_name in keymap_names:
        if not _shortcut_keymap_active(context, keymap_name):
            continue
        keymap = user_keyconfig.keymaps.get(keymap_name)
        if keymap is None:
            continue
        for keymap_item in keymap.keymap_items:
            if any(
                _keymap_item_matches_shortcut_identity(keymap_item, identity_idname, identity_prop_name, identity_prop_value)
                for identity_idname, identity_prop_name, identity_prop_value in operator_identities
            ):
                items.append(keymap_item)
    if items:
        return tuple(items)

    for keymap in user_keyconfig.keymaps:
        if keymap.name in keymap_names:
            continue
        for keymap_item in keymap.keymap_items:
            if any(
                _keymap_item_matches_shortcut_identity(keymap_item, identity_idname, identity_prop_name, identity_prop_value)
                for identity_idname, identity_prop_name, identity_prop_value in operator_identities
            ):
                items.append(keymap_item)
    return tuple(items)


def _shortcut_addon_items(context, shortcut):
    _action_kind, _action_value, _idname, _prop_name, _prop_value, _key_type, _shift, _ctrl, _alt, keymap_names = shortcut
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    addon_keyconfig = getattr(keyconfigs, "addon", None)
    if addon_keyconfig is None:
        return ()

    items = []
    operator_identities = _shortcut_operator_identities(shortcut)
    for keymap_name in keymap_names:
        if not _shortcut_keymap_active(context, keymap_name):
            continue
        keymap = addon_keyconfig.keymaps.get(keymap_name)
        if keymap is None:
            continue
        for keymap_item in keymap.keymap_items:
            if any(
                _keymap_item_matches_shortcut_identity(keymap_item, identity_idname, identity_prop_name, identity_prop_value)
                for identity_idname, identity_prop_name, identity_prop_value in operator_identities
            ):
                items.append(keymap_item)
    return tuple(items)


def _shortcut_configured_items(context, shortcut, *, sync=True):
    user_items = _shortcut_user_items(context, shortcut)
    addon_items = _shortcut_addon_items(context, shortcut)
    return user_items or addon_items


def _world_runtime_keymap_sync_signature(private_impl):
    addon_keymaps = getattr(private_impl, "addon_keymaps", ()) or ()
    signature = []
    for addon_keymap_index, keymap_pair in enumerate(addon_keymaps):
        try:
            km_add, kmi_add = keymap_pair
        except Exception:
            continue
        try:
            signature.append((
                addon_keymap_index,
                getattr(km_add, "name", ""),
                getattr(km_add, "space_type", ""),
                getattr(km_add, "region_type", ""),
                bool(getattr(km_add, "is_modal", False)),
                getattr(kmi_add, "propvalue", "") if bool(getattr(km_add, "is_modal", False)) else getattr(kmi_add, "idname", ""),
                getattr(kmi_add, "map_type", ""),
                getattr(kmi_add, "type", ""),
                getattr(kmi_add, "value", ""),
                bool(getattr(kmi_add, "any", False)),
                bool(getattr(kmi_add, "shift", False)),
                bool(getattr(kmi_add, "ctrl", False)),
                bool(getattr(kmi_add, "alt", False)),
                bool(getattr(kmi_add, "oskey", False)),
                bool(getattr(kmi_add, "hyper", False)),
                getattr(kmi_add, "key_modifier", ""),
                getattr(kmi_add, "direction", ""),
                bool(getattr(kmi_add, "repeat", False)),
                bool(getattr(kmi_add, "active", False)),
            ))
        except Exception:
            continue
    return tuple(signature)


def _sync_world_runtime_keymaps_from_user_overrides(context, *, force=False, force_check=False):
    return 0


def _is_stale_secret_paint_density_adjust_keymap_item(keymap_item):
    if getattr(keymap_item, "type", "") != 'F':
        return False
    if getattr(keymap_item, "value", "") != 'PRESS':
        return False
    if not bool(getattr(keymap_item, "alt", False)):
        return False
    if bool(getattr(keymap_item, "shift", False)) or bool(getattr(keymap_item, "ctrl", False)):
        return False

    idname = getattr(keymap_item, "idname", "")
    if idname == "secret.world_paint_begin_adjust":
        properties = getattr(keymap_item, "properties", None)
        try:
            return properties is not None and getattr(properties, "adjust_mode", "") == "STRENGTH"
        except Exception:
            return False
    return False


def _disable_stale_secret_paint_density_adjust_keymaps_runtime(context):
    return 0


def _event_matches_keymap_item(event, keymap_item, *, ignore_value=False):
    if not getattr(keymap_item, "active", False):
        return False
    if getattr(keymap_item, "map_type", "") != 'KEYBOARD':
        return False
    if getattr(event, "type", "") != getattr(keymap_item, "type", ""):
        return False
    if not ignore_value:
        keymap_value = getattr(keymap_item, "value", "PRESS")
        if keymap_value != 'ANY' and getattr(event, "value", "") != keymap_value:
            return False

    if getattr(keymap_item, "any", False):
        return True

    for modifier_name in ("shift", "ctrl", "alt", "oskey", "hyper"):
        if bool(getattr(event, modifier_name, False)) != bool(getattr(keymap_item, modifier_name, False)):
            return False

    key_modifier = getattr(keymap_item, "key_modifier", 'NONE')
    return key_modifier in {'NONE', ''}


def _event_matches_default_shortcut(event, shortcut, *, ignore_value=False):
    _action_kind, _action_value, _idname, _prop_name, _prop_value, key_type, shift, ctrl, alt, _keymap_names = shortcut
    if key_type in {"", "NONE"}:
        return False
    if getattr(event, "type", "") != key_type:
        return False
    if not ignore_value and getattr(event, "value", "") != 'PRESS':
        return False
    if bool(getattr(event, "shift", False)) != bool(shift):
        return False
    if bool(getattr(event, "ctrl", False)) != bool(ctrl):
        return False
    if bool(getattr(event, "alt", False)) != bool(alt):
        return False
    if bool(getattr(event, "oskey", False)):
        return False
    if bool(getattr(event, "hyper", False)):
        return False
    return True


def _event_active_modifier_names(event):
    return {
        modifier_name
        for modifier_name in WORLD_MODIFIER_NAMES
        if bool(getattr(event, modifier_name, False))
    }


def _shortcut_chord_from_keymap_item(keymap_item, event=None):
    key_type = getattr(keymap_item, "type", "")
    if key_type in {"", "NONE"}:
        return None
    if getattr(keymap_item, "any", False) and event is not None:
        modifiers = _event_active_modifier_names(event)
    else:
        modifiers = {
            modifier_name
            for modifier_name in WORLD_MODIFIER_NAMES
            if bool(getattr(keymap_item, modifier_name, False))
        }
    return {
        "key_type": key_type,
        "modifiers": frozenset(modifiers),
    }


def _shortcut_chord_from_default(shortcut):
    _action_kind, _action_value, _idname, _prop_name, _prop_value, key_type, shift, ctrl, alt, _keymap_names = shortcut
    if key_type in {"", "NONE"}:
        return None
    modifiers = set()
    if shift:
        modifiers.add("shift")
    if ctrl:
        modifiers.add("ctrl")
    if alt:
        modifiers.add("alt")
    return {
        "key_type": key_type,
        "modifiers": frozenset(modifiers),
    }


def _shortcut_chord_from_event(event):
    event_type = getattr(event, "type", "")
    if event_type in {"", "NONE"} or event_type in WORLD_MODIFIER_KEY_TYPES:
        return None
    return {
        "key_type": event_type,
        "modifiers": frozenset(_event_active_modifier_names(event)),
    }


def _shortcut_chord_parts(chord):
    if not chord:
        return set()
    parts = set()
    key_type = chord.get("key_type", "")
    if key_type not in {"", "NONE"}:
        parts.add(("key", key_type))
    for modifier_name in chord.get("modifiers", ()) or ():
        parts.add(("modifier", modifier_name))
    return parts


def _shortcut_chord_release_part(event, chord):
    if getattr(event, "value", "") != 'RELEASE' or not chord:
        return None
    event_type = getattr(event, "type", "")
    if event_type == chord.get("key_type", ""):
        return ("key", event_type)
    modifier_name = WORLD_MODIFIER_KEY_TYPES.get(event_type)
    if modifier_name and modifier_name in (chord.get("modifiers", ()) or ()):
        return ("modifier", modifier_name)
    return None


def _base_paint_shortcut_chord_from_event(context, event):
    for keymap_item in _base_paint_keymap_items(context):
        try:
            if _event_matches_keymap_item(event, keymap_item, ignore_value=True):
                return _shortcut_chord_from_keymap_item(keymap_item, event)
        except Exception:
            continue
    return None


def _pick_source_shortcut_chord_from_event(context, event):
    shortcut = _world_action_shortcut(WORLD_ACTION_PICK_SOURCE)
    if shortcut is not None:
        configured_items = _shortcut_configured_items(context, shortcut)
        if configured_items:
            for keymap_item in configured_items:
                try:
                    if _event_matches_keymap_item(event, keymap_item, ignore_value=True):
                        return _shortcut_chord_from_keymap_item(keymap_item, event)
                except Exception:
                    continue
            return None
        if _event_matches_default_shortcut(event, shortcut, ignore_value=True):
            return _shortcut_chord_from_default(shortcut)
    return _base_paint_shortcut_chord_from_event(context, event)


def _world_paint_event_matches_shortcut(context, event, action_kind, action_value, *, ignore_value=False):
    if action_kind == "ACTION" and action_value == WORLD_ACTION_PICK_SOURCE:
        for shortcut in WORLD_SHORTCUT_ACTIONS:
            if shortcut[0] == "ACTION" and shortcut[1] == WORLD_ACTION_PICK_SOURCE:
                configured_items = _shortcut_configured_items(context, shortcut)
                if configured_items:
                    return any(
                        _event_matches_keymap_item(event, keymap_item, ignore_value=ignore_value)
                        for keymap_item in configured_items
                    )
                break
        return _event_matches_pick_source_shortcut(context, event, ignore_value=ignore_value)

    for shortcut in WORLD_SHORTCUT_ACTIONS:
        if not _world_shortcut_available(shortcut):
            continue
        shortcut_action_kind, shortcut_action_value = shortcut[0], shortcut[1]
        if shortcut_action_kind != action_kind or shortcut_action_value != action_value:
            continue

        configured_items = _shortcut_configured_items(context, shortcut)
        if configured_items:
            if any(
                _event_matches_keymap_item(event, keymap_item, ignore_value=ignore_value)
                for keymap_item in configured_items
            ):
                return True
            if not _allow_default_shortcut_fallback(shortcut, configured_items):
                return False
        return _event_matches_default_shortcut(event, shortcut, ignore_value=ignore_value)
    return False


def _world_paint_shortcut_from_event(context, event):
    if getattr(event, "value", "") != 'PRESS':
        return None

    for shortcut in WORLD_SHORTCUT_ACTIONS:
        if not _world_shortcut_available(shortcut):
            continue
        if shortcut[0] == "ACTION" and shortcut[1] == WORLD_ACTION_PICK_SOURCE:
            configured_items = _shortcut_configured_items(context, shortcut)
            if configured_items:
                if any(_event_matches_keymap_item(event, keymap_item) for keymap_item in configured_items):
                    return shortcut
                continue
            if _event_matches_pick_source_shortcut(context, event):
                return shortcut
            continue
        configured_items = _shortcut_configured_items(context, shortcut)
        if configured_items:
            if any(_event_matches_keymap_item(event, keymap_item) for keymap_item in configured_items):
                return shortcut
            if not _allow_default_shortcut_fallback(shortcut, configured_items):
                continue
        if _event_matches_default_shortcut(event, shortcut):
            return shortcut
    return None


def _world_adjust_shortcut_confirm_on_release(context, event, shortcut):
    def _read_confirm_on_release(keymap_item):
        try:
            properties = getattr(keymap_item, "properties", None)
            if properties is None:
                return False
            for property_name in ("confirm_on_release", "release_confirm"):
                if not hasattr(properties, property_name):
                    continue
                return bool(getattr(properties, property_name, False))
        except Exception:
            pass
        return False

    keyconfigs = getattr(getattr(context, "window_manager", None), "keyconfigs", None)
    addon_keyconfig = getattr(keyconfigs, "addon", None)

    matched_addon_items = []
    if addon_keyconfig is not None:
        operator_identities = _shortcut_operator_identities(shortcut)
        for keymap_name in shortcut[9]:
            keymap = addon_keyconfig.keymaps.get(keymap_name)
            if keymap is None:
                continue
            for keymap_item in keymap.keymap_items:
                if not any(
                    _keymap_item_matches_shortcut_identity(
                        keymap_item,
                        identity_idname,
                        identity_prop_name,
                        identity_prop_value,
                    )
                    for identity_idname, identity_prop_name, identity_prop_value in operator_identities
                ):
                    continue
                if _event_matches_keymap_item(event, keymap_item):
                    matched_addon_items.append(keymap_item)
    if matched_addon_items:
        confirm_on_release = any(_read_confirm_on_release(keymap_item) for keymap_item in matched_addon_items)
        shared.secret_paint_brush_size_trace_log(
            "world.adjust_shortcut.confirm_on_release.addon",
            context,
            event_type=getattr(event, "type", ""),
            event_value=getattr(event, "value", ""),
            matched_items=len(matched_addon_items),
            confirm_on_release=confirm_on_release,
        )
        return confirm_on_release

    matched_user_items = []
    for keymap_item in _shortcut_user_items(context, shortcut):
        try:
            if _event_matches_keymap_item(event, keymap_item):
                matched_user_items.append(keymap_item)
        except Exception:
            continue
    if matched_user_items:
        confirm_on_release = any(_read_confirm_on_release(keymap_item) for keymap_item in matched_user_items)
        shared.secret_paint_brush_size_trace_log(
            "world.adjust_shortcut.confirm_on_release.user",
            context,
            event_type=getattr(event, "type", ""),
            event_value=getattr(event, "value", ""),
            matched_items=len(matched_user_items),
            confirm_on_release=confirm_on_release,
        )
        return confirm_on_release

    shared.secret_paint_brush_size_trace_log(
        "world.adjust_shortcut.confirm_on_release.default_false",
        context,
        event_type=getattr(event, "type", ""),
        event_value=getattr(event, "value", ""),
        shortcut_action=shortcut[1],
    )
    return False


def _world_action_shortcut(action_value):
    for shortcut in WORLD_SHORTCUT_ACTIONS:
        if shortcut[0] == "ACTION" and shortcut[1] == action_value:
            return shortcut
    return None


def _world_adjust_shortcut(adjust_mode):
    for shortcut in WORLD_SHORTCUT_ACTIONS:
        if shortcut[0] == "ADJUST" and shortcut[1] == adjust_mode:
            return shortcut
    return None


def _event_has_no_modifiers(event):
    return not any(
        bool(getattr(event, modifier_name, False))
        for modifier_name in ("shift", "ctrl", "alt", "oskey", "hyper")
    )


def _event_looks_like_keyboard_shortcut(event):
    event_type = getattr(event, "type", "")
    if not event_type:
        return False
    if getattr(event, "value", "") not in {'PRESS', 'CLICK', 'CLICK_DRAG'}:
        return False
    return event_type not in {
        'LEFTMOUSE',
        'RIGHTMOUSE',
        'MIDDLEMOUSE',
        'ACTIONMOUSE',
        'SELECTMOUSE',
        'EVT_TWEAK_L',
        'EVT_TWEAK_M',
        'EVT_TWEAK_R',
        'MOUSEMOVE',
        'INBETWEEN_MOUSEMOVE',
        'WHEELUPMOUSE',
        'WHEELDOWNMOUSE',
        'WHEELINMOUSE',
        'WHEELOUTMOUSE',
        'WINDOW_ACTIVATE',
        'WINDOW_DEACTIVATE',
        'WINDOW_ENTER',
        'WINDOW_LEAVE',
        'TIMER',
        'NONE',
    }


def _windows_virtual_key_for_event_type(event_type):
    if not event_type:
        return None
    if len(event_type) == 1:
        char = event_type.upper()
        if "A" <= char <= "Z" or "0" <= char <= "9":
            return ord(char)
    if event_type.startswith("F") and event_type[1:].isdigit():
        function_index = int(event_type[1:])
        if 1 <= function_index <= 24:
            return 0x70 + function_index - 1
    return {
        "ZERO": ord("0"),
        "ONE": ord("1"),
        "TWO": ord("2"),
        "THREE": ord("3"),
        "FOUR": ord("4"),
        "FIVE": ord("5"),
        "SIX": ord("6"),
        "SEVEN": ord("7"),
        "EIGHT": ord("8"),
        "NINE": ord("9"),
        "RET": 0x0D,
        "NUMPAD_ENTER": 0x0D,
        "ESC": 0x1B,
        "TAB": 0x09,
        "SPACE": 0x20,
        "LEFT_SHIFT": 0xA0,
        "RIGHT_SHIFT": 0xA1,
        "LEFT_CTRL": 0xA2,
        "RIGHT_CTRL": 0xA3,
        "LEFT_ALT": 0xA4,
        "RIGHT_ALT": 0xA5,
        "ALT": 0x12,
        "OSKEY": 0x5B,
    }.get(event_type)


def _windows_key_down_for_event_type(event_type):
    vk_code = _windows_virtual_key_for_event_type(event_type)
    if vk_code is None:
        return None
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
    except Exception:
        return None


def _windows_modifier_down(modifier_name):
    modifier_name = modifier_name.lower()
    if modifier_name == "shift":
        key_states = (
            _windows_key_down_for_event_type("LEFT_SHIFT"),
            _windows_key_down_for_event_type("RIGHT_SHIFT"),
        )
    elif modifier_name == "ctrl":
        key_states = (
            _windows_key_down_for_event_type("LEFT_CTRL"),
            _windows_key_down_for_event_type("RIGHT_CTRL"),
        )
    elif modifier_name == "alt":
        key_states = (
            _windows_key_down_for_event_type("LEFT_ALT"),
            _windows_key_down_for_event_type("RIGHT_ALT"),
            _windows_key_down_for_event_type("ALT"),
        )
    elif modifier_name == "oskey":
        key_states = (_windows_key_down_for_event_type("OSKEY"),)
    else:
        return None
    if any(state is True for state in key_states):
        return True
    if any(state is None for state in key_states):
        return None
    return False


def _base_paint_keymap_items(context, *, sync=True):
    cached_items = _WORLD_STATE.get("base_paint_keymap_items_cache")
    if cached_items is not None:
        return cached_items
    wm = getattr(context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None)
    if keyconfigs is None:
        _WORLD_STATE["base_paint_keymap_items_cache"] = ()
        return _WORLD_STATE["base_paint_keymap_items_cache"]

    keymap_names = ("Sculpt Curves", "Object Mode", "Weight Paint", "Curve")

    def _paint_keymap_items(keyconfig):
        items = []
        if keyconfig is None:
            return items
        for keymap_name in keymap_names:
            keymap = keyconfig.keymaps.get(keymap_name)
            if keymap is None:
                continue
            for keymap_item in keymap.keymap_items:
                try:
                    if getattr(keymap_item, "idname", "") == "secret.paint":
                        items.append(keymap_item)
                except Exception:
                    continue
        return items

    _WORLD_STATE["base_paint_keymap_items_cache"] = tuple(
        _paint_keymap_items(getattr(keyconfigs, "user", None))
        or _paint_keymap_items(getattr(keyconfigs, "addon", None))
    )
    return _WORLD_STATE["base_paint_keymap_items_cache"]


def _world_paint_shortcut_event_types(context, *, sync=True):
    mode_key = getattr(context, "mode", "") if context is not None else ""
    cache = _WORLD_STATE.setdefault("shortcut_event_types_cache", {})
    if mode_key in cache:
        return cache[mode_key]

    event_types = set()
    for shortcut in WORLD_SHORTCUT_ACTIONS:
        if not _world_shortcut_available(shortcut):
            continue
        configured_items = _shortcut_configured_items(context, shortcut, sync=False)
        if configured_items:
            keymap_items = configured_items
        else:
            key_type = shortcut[5]
            if key_type not in {"", "NONE"}:
                event_types.add(key_type)
            keymap_items = ()
        for keymap_item in keymap_items:
            if not bool(getattr(keymap_item, "active", False)):
                continue
            if getattr(keymap_item, "map_type", "") != 'KEYBOARD':
                continue
            key_type = getattr(keymap_item, "type", "")
            if key_type not in {"", "NONE"}:
                event_types.add(key_type)

    for keymap_item in _base_paint_keymap_items(context, sync=False):
        if not bool(getattr(keymap_item, "active", False)):
            continue
        if getattr(keymap_item, "map_type", "") != 'KEYBOARD':
            continue
        key_type = getattr(keymap_item, "type", "")
        if key_type not in {"", "NONE"}:
            event_types.add(key_type)

    cache[mode_key] = frozenset(event_types)
    return cache[mode_key]


def _world_paint_event_type_can_match_shortcut(context, event, fallback_key_type=""):
    event_type = getattr(event, "type", "")
    if not event_type:
        return True
    if fallback_key_type and event_type == fallback_key_type:
        return True
    return event_type in _world_paint_shortcut_event_types(context)


def _precache_world_modal_keymaps(context):
    _clear_world_keymap_lookup_caches()
    _base_paint_keymap_items(context, sync=False)
    _world_paint_shortcut_event_types(context, sync=False)
    _viewport_bookmark_keymap_item_groups(context)


def _world_keymap_item_is_alive(keymap, keymap_item):
    try:
        target_pointer = keymap_item.as_pointer()
    except Exception:
        target_pointer = None
    try:
        for item in keymap.keymap_items:
            if item is keymap_item:
                return True
            if target_pointer is not None:
                try:
                    if item.as_pointer() == target_pointer:
                        return True
                except Exception:
                    pass
    except Exception:
        return False
    return False


def _remove_world_right_delete_brush_keymap(context=None):
    _WORLD_STATE["right_delete_brush_keymaps"] = []
    return 0


def _ensure_world_right_delete_brush_keymap(context):
    _WORLD_STATE["right_delete_brush_keymaps"] = []
    return False


def restore_base_paint_shortcuts_for_exit(context):
    _q_debug_log_keymaps("restore_base_paint_shortcuts.enter", context)
    _set_world_paint_shortcuts_enabled(context, True)
    _q_debug_log_keymaps("restore_base_paint_shortcuts.exit", context, restored=0)
    return 0


def world_paint_exit_state_active(context=None):
    operator = _world_operator()
    return operator is not None or bool(
        _WORLD_STATE.get("ui_hijacked", False)
        or _WORLD_STATE.get("suppressed_world_paint_shortcut_items")
        or _WORLD_STATE.get("right_delete_brush_keymaps")
    )


def cleanup_world_paint_exit_state(context=None):
    context = context or bpy.context
    _q_debug_log_keymaps("cleanup_exit_state.enter", context)
    operator = _world_operator()
    if operator is not None:
        operator.finish_world_paint(context)
        restore_base_paint_shortcuts_for_exit(context)
        _q_debug_log_keymaps("cleanup_exit_state.running_operator_exit", context)
        return True

    was_active = world_paint_exit_state_active(context)
    try:
        _set_world_keymap_conflicts_enabled(context, True)
    except Exception:
        pass
    try:
        _set_world_paint_shortcuts_enabled(context, True)
    except Exception:
        pass
    try:
        _remove_world_right_delete_brush_keymap(context)
    except Exception:
        pass

    original_draw = _WORLD_STATE.get("header_draw_original")
    if original_draw is not None:
        try:
            bpy.types.VIEW3D_HT_header.draw = original_draw
        except Exception:
            pass
    _WORLD_STATE["header_draw_original"] = None

    original_tool_header_draw = _WORLD_STATE.get("tool_header_draw_original")
    if original_tool_header_draw is not None:
        try:
            bpy.types.VIEW3D_HT_tool_header.draw = original_tool_header_draw
        except Exception:
            pass
    _WORLD_STATE["tool_header_draw_original"] = None

    try:
        _restore_world_toolbar()
    except Exception:
        pass

    _WORLD_STATE["operator"] = None
    _WORLD_STATE["ui_hijacked"] = False
    _WORLD_STATE["exit_consume_paint_until"] = 0.0
    _WORLD_STATE["suppressed_world_paint_shortcut_items"] = []
    _clear_world_paint_object_mode_guard()

    try:
        shared.secret_paint_enable_sculpt_curves_cage(context)
    except Exception:
        pass
    try:
        _sanitize_sculpt_curves_tool_before_world_exit(context)
    except Exception:
        pass
    try:
        restore_base_paint_shortcuts_for_exit(context)
    except Exception:
        pass
    try:
        _tag_redraw_view3d_areas(context)
    except Exception:
        pass
    _q_debug_log_keymaps("cleanup_exit_state.exit", context, was_active=was_active)
    return was_active


def _event_matches_base_paint_shortcut(context, event, fallback_key_type="", *, ignore_value=False):
    if not ignore_value and getattr(event, "value", "") != 'PRESS':
        return False

    event_type = getattr(event, "type", "")
    if fallback_key_type and event_type == fallback_key_type and _event_has_no_modifiers(event):
        return True

    seen_items = set()
    for keymap_item in _base_paint_keymap_items(context):
        try:
            try:
                item_key = keymap_item.as_pointer()
            except Exception:
                item_key = id(keymap_item)
            if item_key in seen_items:
                continue
            seen_items.add(item_key)
            if _event_matches_keymap_item(event, keymap_item, ignore_value=ignore_value):
                return True
        except Exception:
            continue

    return False


def _start_base_paint_from_stopped_modal(context, event):
    _q_debug_log(
        "stopped_modal_start_base_paint.enter",
        context,
        event_type=getattr(event, "type", ""),
        event_value=getattr(event, "value", ""),
    )
    if event is None:
        return False
    if not _event_looks_like_keyboard_shortcut(event):
        _q_debug_log("stopped_modal_start_base_paint.not_keyboard", context)
        return False
    try:
        restore_base_paint_shortcuts_for_exit(context)
    except Exception:
        pass
    try:
        if not _event_matches_base_paint_shortcut(context, event):
            _q_debug_log_keymaps("stopped_modal_start_base_paint.no_match", context)
            return False
    except Exception:
        _q_debug_log("stopped_modal_start_base_paint.match_error", context)
        return False
    try:
        restart_operator = type(
            "_StoppedModalBasePaintRestart",
            (),
            {
                "exit_paint_mode": False,
                "use_selected_source": False,
                "report": lambda self, *_args, **_kwargs: None,
            },
        )()
        result = shared.orenscatter.invoke(restart_operator, context, event)
        _q_debug_log_keymaps("stopped_modal_start_base_paint.direct_invoked", context, result=result)
        return True
    except Exception:
        _q_debug_log_keymaps("stopped_modal_start_base_paint.direct_invoke_error", context)
    try:
        bpy.ops.secret.paint('INVOKE_DEFAULT')
        _q_debug_log_keymaps("stopped_modal_start_base_paint.dispatched", context)
        return True
    except Exception:
        _q_debug_log_keymaps("stopped_modal_start_base_paint.dispatch_error", context)
        return False


def _event_matches_pick_source_shortcut(context, event, fallback_key_type="", *, ignore_value=False):
    shortcut = _world_action_shortcut(WORLD_ACTION_PICK_SOURCE)
    if shortcut is not None:
        configured_items = _shortcut_configured_items(context, shortcut)
        if configured_items:
            if any(
                _event_matches_keymap_item(event, keymap_item, ignore_value=ignore_value)
                for keymap_item in configured_items
            ):
                return True
            return False
    return _event_matches_base_paint_shortcut(
        context,
        event,
        fallback_key_type,
        ignore_value=ignore_value,
    )


def _event_matches_shift_pick_source_shortcut(context, event, _fallback_key_type="", *, ignore_value=False):
    shortcut = _world_action_shortcut(WORLD_ACTION_BRUSH_SWITCH)
    if shortcut is None:
        return False

    configured_items = _shortcut_configured_items(context, shortcut)
    if configured_items:
        if any(
            _event_matches_keymap_item(event, keymap_item, ignore_value=ignore_value)
            for keymap_item in configured_items
        ):
            return True
        return False
    return _event_matches_default_shortcut(event, shortcut, ignore_value=ignore_value)


def _adjust_shortcut_key_specs(context, adjust_mode):
    shortcut = _world_adjust_shortcut(adjust_mode)
    if shortcut is None:
        return ()

    configured_items = _shortcut_configured_items(context, shortcut)
    specs = []
    for keymap_item in _active_keyboard_shortcut_items(configured_items):
        key_type = getattr(keymap_item, "type", "")
        if key_type in {"", "NONE"}:
            continue
        if getattr(keymap_item, "key_modifier", 'NONE') not in {'NONE', ''}:
            continue
        modifiers = {
            modifier_name
            for modifier_name in WORLD_MODIFIER_NAMES
            if bool(getattr(keymap_item, modifier_name, False))
        }
        specs.append({
            "key_type": key_type,
            "modifiers": frozenset(modifiers),
        })
    if specs:
        return tuple(specs)

    if not _allow_default_shortcut_fallback(shortcut, configured_items):
        return ()
    default_chord = _shortcut_chord_from_default(shortcut)
    return (default_chord,) if default_chord else ()


def _event_matches_current_adjust_shortcut(context, event, adjust_mode, *, ignore_value=False):
    if not adjust_mode:
        return False
    return _world_paint_event_matches_shortcut(
        context,
        event,
        "ADJUST",
        adjust_mode,
        ignore_value=ignore_value,
    )


def _event_view3d_window_override_and_mouse(context, event, invoke_area_pointer=0):
    if event is None:
        return None, None

    area, region = _hovered_area_region(context, event)
    if area is None or area.type != 'VIEW_3D':
        return None, None
    if invoke_area_pointer and area.as_pointer() != invoke_area_pointer:
        return None, None
    if region is None or region.type != 'WINDOW':
        return None, None

    mouse_x = getattr(event, "mouse_x", None)
    mouse_y = getattr(event, "mouse_y", None)
    if mouse_x is None or mouse_y is None:
        return None, None

    space = area.spaces.active if area.spaces else None
    if space is None:
        return None, None
    region_data = getattr(space, "region_3d", None)
    if region_data is None:
        return None, None

    override = {
        "area": area,
        "region": region,
        "space_data": space,
        "region_data": region_data,
    }
    window = getattr(context, "window", None)
    screen = getattr(context, "screen", None)
    if window is not None:
        override["window"] = window
    if screen is not None:
        override["screen"] = screen

    return override, (mouse_x - region.x, mouse_y - region.y)


def pick_entry_source_object(context, event, *, allow_procedural_systems=False):
    override, mouse_coord = _event_view3d_window_override_and_mouse(context, event)
    if override is None or mouse_coord is None:
        return None
    try:
        with context.temp_override(**override):
            return _raycast_source_object(
                bpy.context,
                mouse_coord,
                allow_procedural_systems=allow_procedural_systems,
            )
    except Exception:
        return _raycast_source_object(
            context,
            mouse_coord,
            allow_procedural_systems=allow_procedural_systems,
        )


def _view3d_area_data(context, area_pointer=0):
    def _from_screen(screen):
        if screen is None:
            return None, None, None
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            if area_pointer and area.as_pointer() != area_pointer:
                continue
            region = next((region for region in area.regions if region.type == 'WINDOW'), None)
            space = area.spaces.active if area.spaces else None
            return area, region, space
        return None, None, None

    area, region, space = _from_screen(getattr(context, "screen", None))
    if area is not None:
        return area, region, space

    try:
        for window in context.window_manager.windows:
            area, region, space = _from_screen(getattr(window, "screen", None))
            if area is not None:
                return area, region, space
    except Exception:
        pass
    return None, None, None


def _region_contains_xy(region, x, y):
    return (
        region is not None and
        region.x <= x < (region.x + region.width) and
        region.y <= y < (region.y + region.height)
    )


def _hovered_area_region(context, event):
    screen = getattr(context, "screen", None)
    if screen is None:
        return None, None

    mouse_x = getattr(event, "mouse_x", None)
    mouse_y = getattr(event, "mouse_y", None)
    if mouse_x is None or mouse_y is None:
        return None, None

    for area in screen.areas:
        if not _region_contains_xy(area, mouse_x, mouse_y):
            continue
        for region in area.regions:
            if _region_contains_xy(region, mouse_x, mouse_y):
                return area, region
        return area, None
    return None, None


def _event_region_context(context, event, invoke_area_pointer=0):
    area, region = _hovered_area_region(context, event)
    if area is None:
        return {
            "area": None,
            "region": None,
            "in_invoke_area": False,
            "in_window_region": False,
            "ui_region": False,
        }

    in_invoke_area = not invoke_area_pointer or area.as_pointer() == invoke_area_pointer
    region_type = region.type if region is not None else ""
    return {
        "area": area,
        "region": region,
        "in_invoke_area": in_invoke_area,
        "in_window_region": in_invoke_area and region_type == 'WINDOW',
        "ui_region": in_invoke_area and region_type in {'HEADER', 'TOOL_HEADER', 'TOOLS', 'UI'},
    }


def _is_primary_paint_event(event):
    return getattr(event, "type", "") in WORLD_PRIMARY_PAINT_EVENTS


def _is_primary_paint_active_event(event):
    return _is_primary_paint_event(event) and getattr(event, "value", "") in WORLD_PRIMARY_PAINT_ACTIVE_VALUES


def _is_primary_paint_end_event(event):
    return _is_primary_paint_event(event) and getattr(event, "value", "") in WORLD_PRIMARY_PAINT_END_VALUES


def _primary_paint_button_state_from_event(event, *, previous=False):
    event_type = getattr(event, "type_prev" if previous else "type", "")
    event_value = getattr(event, "value_prev" if previous else "value", "NOTHING")
    if event_type not in WORLD_PRIMARY_PAINT_EVENTS or event_value == 'ANY':
        return None
    if event_value in WORLD_PRIMARY_PAINT_ACTIVE_VALUES:
        return True
    if event_value in WORLD_PRIMARY_PAINT_END_VALUES:
        return False
    return None


def _tag_redraw_view3d_areas(context):
    screen = getattr(context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def _tag_view3d_tool_ui_regions(context, *, area_pointer=0):
    screen = getattr(context, "screen", None)
    if screen is None:
        return
    target_area = None
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        if area_pointer:
            try:
                if area.as_pointer() != area_pointer:
                    continue
            except Exception:
                pass
        target_area = area
        break
    if target_area is None:
        return
    for region in target_area.regions:
        if region.type in {'HEADER', 'TOOL_HEADER', 'TOOLS'}:
            try:
                region.tag_redraw()
            except Exception:
                pass


def _operator_result_ok(result):
    return bool(result) and 'CANCELLED' not in result


def _tool_set_by_id(context, tool_id, *, area_pointer=0):
    if not tool_id:
        return False

    area, region, space = _view3d_area_data(context, area_pointer)
    try:
        if area and region and space:
            with context.temp_override(area=area, region=region, space_data=space):
                result = bpy.ops.wm.tool_set_by_id(name=tool_id)
        else:
            result = bpy.ops.wm.tool_set_by_id(name=tool_id)
        return _operator_result_ok(result)
    except Exception:
        return False


def _tool_set_by_brush_type(context, brush_type, *, area_pointer=0):
    if not brush_type:
        return False

    area, region, space = _view3d_area_data(context, area_pointer)
    try:
        if area and region and space:
            with context.temp_override(area=area, region=region, space_data=space):
                result = bpy.ops.wm.tool_set_by_brush_type(brush_type=brush_type)
        else:
            result = bpy.ops.wm.tool_set_by_brush_type(brush_type=brush_type)
        return _operator_result_ok(result)
    except Exception:
        return False


def _brush_curves_type(brush):
    return shared.secret_paint_curves_brush_type(brush)


def _is_density_brush(brush):
    return shared.secret_paint_is_curves_brush_type(brush, 'DENSITY')


def _curves_brush_matches_type(brush, brush_type):
    return bool(brush_type and shared.secret_paint_is_curves_brush_type(brush, brush_type))


def _world_toolbar_tools(*, sculpt_curves_mode=False):
    ToolDef, _VIEW3D_PT_tools_active = _ensure_bl_ui_toolsystem()
    tools = []
    for index, (tool_id, label, description, icon) in enumerate(WORLD_TOOLBAR_SPECS):
        if index and tool_id in {WORLD_TOOL_SLIDE, WORLD_TOOL_SINGLE}:
            tools.append(None)
        tool_def = {
            "idname": _workspace_tool_id_for_world_tool(tool_id),
            "label": label,
            "description": description,
            "icon": icon,
            "cursor": None,
            "widget": None,
            "keymap": None,
            "data_block": None,
            "draw_settings": None,
            "draw_cursor": None,
        }
        tool_def["operator"] = None
        native_brush_type = _curves_brush_type_for_world_tool(tool_id)
        native_tool_id = _native_workspace_tool_id_for_world_tool(tool_id)
        if sculpt_curves_mode and native_brush_type and native_tool_id:
            tool_def["idname"] = native_tool_id
            tool_def["options"] = {'USE_BRUSHES'}
            tool_def["brush_type"] = native_brush_type
        tools.append(ToolDef.from_dict(tool_def))
    return tools


def _world_toolbar_override_map(base_tools):
    tools = dict(base_tools)
    tools.setdefault(None, [])
    return tools


def _iter_toolbar_item_idnames(item):
    if item is None:
        return
    if isinstance(item, (tuple, list)):
        for sub_item in item:
            yield from _iter_toolbar_item_idnames(sub_item)
        return
    idname = getattr(item, "idname", "")
    if idname:
        yield idname


def _toolbar_tools_contain_id(tools, mode, idname):
    if not isinstance(tools, dict):
        return False
    for key in (None, mode):
        for item in tools.get(key, ()) or ():
            if idname in _iter_toolbar_item_idnames(item):
                return True
    return False


def _toolbar_item_contains_id(item, idname):
    return idname in _iter_toolbar_item_idnames(item)


def _remove_duplicate_leading_toolbar_group(items, idname):
    if not items or not _toolbar_item_contains_id(items[0], idname):
        return items, False
    if not any(_toolbar_item_contains_id(item, idname) for item in items[1:]):
        return items, False

    remove_count = 2 if len(items) > 1 and items[1] is None else 1
    return items[remove_count:], True


def _remove_toolbar_items_with_id(items, idname):
    cleaned = []
    changed = False
    skip_separator = False
    for item in items:
        if _toolbar_item_contains_id(item, idname):
            changed = True
            skip_separator = True
            continue
        if skip_separator and item is None:
            changed = True
            skip_separator = False
            continue
        skip_separator = False
        cleaned.append(item)
    return cleaned, changed


def _cleanup_view3d_toolbar_tool_entries():
    try:
        import bl_ui.space_toolsystem_toolbar as toolbar_module
        VIEW3D_PT_tools_active = toolbar_module.VIEW3D_PT_tools_active
    except Exception:
        return False

    tools = getattr(VIEW3D_PT_tools_active, "_tools", None)
    if not isinstance(tools, dict):
        return False

    changed = False
    repaired_tools = dict(tools)

    for mode, items in tuple(repaired_tools.items()):
        if not isinstance(items, (list, tuple)):
            continue
        cleaned_items = list(items)
        if mode == 'SCULPT_CURVES':
            cleaned_items, mode_changed = _remove_toolbar_items_with_id(
                cleaned_items,
                "builtin.select_box",
            )
            changed = changed or mode_changed
        cleaned_items, mode_changed = _remove_duplicate_leading_toolbar_group(
            cleaned_items,
            "builtin.select_box",
        )
        if mode_changed:
            changed = True
        if mode_changed or cleaned_items != list(items):
            repaired_tools[mode] = cleaned_items

    if changed:
        try:
            VIEW3D_PT_tools_active._tools = repaired_tools
        except Exception:
            return False
    _WORLD_STATE["view3d_builtin_tool_entries_checked"] = True
    return changed


def _ensure_view3d_builtin_tool_entries():
    if _WORLD_STATE.get("view3d_builtin_tool_entries_checked", False):
        return False
    return _cleanup_view3d_toolbar_tool_entries()


def _iter_toolbar_tooldefs(item, context=None):
    if item is None:
        return
    if isinstance(item, (tuple, list)):
        for sub_item in item:
            yield from _iter_toolbar_tooldefs(sub_item, context)
        return
    if not getattr(item, "idname", "") and callable(item):
        try:
            dynamic_items = item(context)
        except Exception:
            return
        yield from _iter_toolbar_tooldefs(dynamic_items, context)
        return
    if getattr(item, "idname", ""):
        yield item


def _view3d_toolbar_tooldefs_for_mode(context, mode):
    try:
        _ToolDef, VIEW3D_PT_tools_active = _ensure_bl_ui_toolsystem()
    except Exception:
        return []

    tooldefs = []
    try:
        mode_tools = VIEW3D_PT_tools_active.tools_from_context(context, mode)
        for item in mode_tools:
            tooldefs.extend(_iter_toolbar_tooldefs(item, context))
    except Exception:
        return []
    return tooldefs


def _view3d_toolbar_tool_ids_for_mode(context, mode):
    return {
        getattr(item, "idname", "")
        for item in _view3d_toolbar_tooldefs_for_mode(context, mode)
        if getattr(item, "idname", "")
    }


def _view3d_toolbar_tooldef_for_mode(context, mode, preferred_ids):
    preferred_ids = tuple(preferred_ids or ())
    for item in _view3d_toolbar_tooldefs_for_mode(context, mode):
        if getattr(item, "idname", "") in preferred_ids:
            return item
    return None


def _sculpt_curves_density_tooldef(context):
    tooldef = _view3d_toolbar_tooldef_for_mode(
        context,
        'SCULPT_CURVES',
        ("builtin_brush.density", "builtin.brush", "builtin_brush.selection_paint"),
    )
    if tooldef is not None:
        return tooldef
    try:
        import bl_ui.space_toolsystem_toolbar as toolbar_module
        curves_defs = getattr(toolbar_module, "_defs_curves_sculpt", None)
        if curves_defs is not None:
            return getattr(curves_defs, "density", None)
    except Exception:
        pass
    return None


def _tooldef_keymap_name(tooldef):
    keymap = getattr(tooldef, "keymap", None)
    if keymap is None:
        return ""
    if isinstance(keymap, str):
        return keymap
    try:
        return keymap[0] if keymap else ""
    except Exception:
        return ""


def _setup_view3d_workspace_tool_from_tooldef(context, mode, tooldef):
    if tooldef is None:
        return False
    try:
        workspace_tool = context.workspace.tools.from_space_view3d_mode(mode, create=True)
    except Exception:
        workspace_tool = None
    if workspace_tool is None:
        return False

    try:
        workspace_tool.setup(
            idname=getattr(tooldef, "idname", ""),
            keymap=_tooldef_keymap_name(tooldef),
            cursor=getattr(tooldef, "cursor", None) or 'DEFAULT',
            options=set(getattr(tooldef, "options", None) or set()),
            gizmo_group=getattr(tooldef, "widget", None) or "",
            brush_type=getattr(tooldef, "brush_type", None) or 'ANY',
            data_block=getattr(tooldef, "data_block", None) or "",
            operator=getattr(tooldef, "operator", None) or "",
            index=-1,
            idname_fallback="",
            keymap_fallback="",
        )
        return True
    except Exception:
        return False


def _ensure_valid_sculpt_curves_workspace_tool(context):
    context = context or bpy.context
    return _setup_view3d_workspace_tool_from_tooldef(
        context,
        'SCULPT_CURVES',
        _sculpt_curves_density_tooldef(context),
    )


def _sanitize_sculpt_curves_tool_before_world_exit(context=None, *, area_pointer=0):
    context = context or bpy.context
    mode = getattr(context, "mode", "") or ""
    active_obj = getattr(context, "active_object", None)
    active_mode = getattr(active_obj, "mode", "") if active_obj is not None else ""
    if mode != 'SCULPT_CURVES' and active_mode != 'SCULPT_CURVES':
        return _cleanup_view3d_toolbar_tool_entries()

    fixed_tool = _ensure_valid_sculpt_curves_workspace_tool(context)
    cleaned = _cleanup_view3d_toolbar_tool_entries()
    return cleaned or fixed_tool


def _draw_secret_paint_world_toolbar_cls(cls, layout, context, detect_layout=True, scale_y=1.75):
    operator = _world_operator()
    original_draw_cls = _WORLD_STATE.get("toolbar_draw_cls_original")
    if operator is None or getattr(getattr(context, "space_data", None), "type", "") != 'VIEW_3D':
        if original_draw_cls is not None:
            return original_draw_cls(layout, context, detect_layout=detect_layout, scale_y=scale_y)
        return None

    try:
        from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    except Exception:
        if original_draw_cls is not None:
            return original_draw_cls(layout, context, detect_layout=detect_layout, scale_y=scale_y)
        return None

    if getattr(operator, "tool_id", "") == WORLD_TOOL_BEZIER and original_draw_cls is not None:
        try:
            original_draw_cls(layout, context, detect_layout=detect_layout, scale_y=scale_y)
            layout.separator()
        except Exception:
            pass

    if detect_layout:
        ui_gen, show_text = ToolSelectPanelHelper._layout_generator_detect_from_region(
            layout,
            context.region,
            scale_y,
        )
    else:
        ui_gen = ToolSelectPanelHelper._layout_generator_single_column(layout, scale_y)
        show_text = True

    ui_gen.send(None)
    native_passthrough = (
        operator._native_curves_brush_passthrough_active()
        or operator._active_brush_requests_native_passthrough(context)
    )
    for index, (tool_id, label, _description, icon) in enumerate(WORLD_TOOLBAR_SPECS):
        if index and tool_id in {WORLD_TOOL_SLIDE, WORLD_TOOL_SINGLE}:
            ui_gen.send(True)
        sub = ui_gen.send(False)
        props = sub.operator(
            WORLD_TOOL_OPERATOR_IDS.get(tool_id, "secret.world_paint_set_tool"),
            text=label if show_text else "",
            depress=(not native_passthrough and operator.tool_id == tool_id),
            icon=icon,
        )
        if hasattr(props, "tool_id"):
            props.tool_id = tool_id
    ui_gen.send(None)
    return None


def _hijack_world_toolbar():
    if _WORLD_STATE["toolbar_original"] is not None:
        return

    _ensure_view3d_builtin_tool_entries()
    _ToolDef, VIEW3D_PT_tools_active = _ensure_bl_ui_toolsystem()
    _WORLD_STATE["toolbar_original"] = VIEW3D_PT_tools_active._tools
    _WORLD_STATE["toolbar_draw_cls_original"] = VIEW3D_PT_tools_active.draw_cls
    VIEW3D_PT_tools_active.draw_cls = classmethod(_draw_secret_paint_world_toolbar_cls)


def _restore_world_toolbar():
    if _WORLD_STATE["toolbar_original"] is None:
        return

    _ensure_view3d_builtin_tool_entries()
    _ToolDef, VIEW3D_PT_tools_active = _ensure_bl_ui_toolsystem()
    original_draw_cls = _WORLD_STATE.get("toolbar_draw_cls_original")
    if original_draw_cls is not None:
        VIEW3D_PT_tools_active.draw_cls = original_draw_cls
    _WORLD_STATE["toolbar_draw_cls_original"] = None
    _WORLD_STATE["toolbar_original"] = None
    _WORLD_STATE["toolbar_temp_restore_depth"] = 0


def _with_original_world_toolbar(callback):
    if _WORLD_STATE.get("toolbar_temp_restore_depth", 0) > 0:
        return callback()

    restored_draw_cls = False
    VIEW3D_PT_tools_active = None
    try:
        try:
            _ToolDef, VIEW3D_PT_tools_active = _ensure_bl_ui_toolsystem()
        except Exception:
            return callback()
        original_draw_cls = _WORLD_STATE.get("toolbar_draw_cls_original")
        if original_draw_cls is not None:
            VIEW3D_PT_tools_active.draw_cls = original_draw_cls
            restored_draw_cls = True
        return callback()
    finally:
        _WORLD_STATE["toolbar_temp_restore_depth"] = 0
        if (
            restored_draw_cls and
            VIEW3D_PT_tools_active is not None and
            _WORLD_STATE.get("toolbar_draw_cls_original") is not None
        ):
            VIEW3D_PT_tools_active.draw_cls = classmethod(_draw_secret_paint_world_toolbar_cls)


def _mode_set_with_world_toolbar_restored(mode):
    try:
        if mode != 'SCULPT_CURVES':
            operator = _world_operator()
            _sanitize_sculpt_curves_tool_before_world_exit(
                bpy.context,
                area_pointer=getattr(operator, "_invoke_area_pointer", 0) if operator is not None else 0,
            )
        return _with_original_world_toolbar(
            lambda: _operator_result_ok(bpy.ops.object.mode_set(mode=mode))
        )
    except Exception:
        return False


def _force_object_mode_after_world_paint(context=None):
    context = context or bpy.context
    if _world_operator() is not None:
        return False

    mode = getattr(context, "mode", "") or ""
    active_obj = getattr(context, "active_object", None)
    active_mode = getattr(active_obj, "mode", "") if active_obj is not None else ""
    if mode != 'SCULPT_CURVES' and active_mode != 'SCULPT_CURVES':
        return False

    return _mode_set_with_world_toolbar_restored('OBJECT')


def _force_object_select_tool_after_world_paint(context=None):
    return False


def _refresh_sculpt_curves_workspace_tool(context):
    try:
        tool = context.workspace.tools.from_space_view3d_mode('SCULPT_CURVES', create=True)
    except Exception:
        tool = None
    if tool is None:
        return False
    try:
        tool.refresh_from_context()
        return True
    except Exception:
        return False


def _force_system_names_object_mode_after_world_paint(context, system_names):
    if _world_operator() is not None:
        return False

    names = [name for name in system_names if name]
    if not names:
        return False

    view_layer = getattr(context, "view_layer", None)
    if view_layer is None:
        return False

    try:
        original_active = view_layer.objects.active
    except Exception:
        original_active = None
    try:
        original_selected_names = [obj.name for obj in context.selected_objects]
    except Exception:
        original_selected_names = []

    changed = False
    try:
        for name in names:
            system_obj = bpy.data.objects.get(name)
            if system_obj is None or not _is_secret_paint_system(system_obj):
                continue
            try:
                if system_obj.name not in view_layer.objects:
                    continue
            except Exception:
                continue

            try:
                if context.mode != 'OBJECT':
                    _mode_set_with_world_toolbar_restored('OBJECT')
            except Exception:
                pass
            try:
                for obj in context.selected_objects:
                    obj.select_set(False)
            except Exception:
                pass
            try:
                system_obj.select_set(True)
                view_layer.objects.active = system_obj
                view_layer.update()
            except Exception:
                continue
            try:
                if context.mode != 'OBJECT' or getattr(system_obj, "mode", "") != 'OBJECT':
                    changed = _mode_set_with_world_toolbar_restored('OBJECT') or changed
            except Exception:
                pass
    finally:
        try:
            if context.mode != 'OBJECT':
                _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass
        try:
            for obj in context.selected_objects:
                obj.select_set(False)
        except Exception:
            pass
        for name in original_selected_names:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            try:
                if obj.name in view_layer.objects:
                    obj.select_set(True)
            except Exception:
                pass
        try:
            if original_active is not None and original_active.name in view_layer.objects:
                view_layer.objects.active = original_active
        except Exception:
            pass

    return changed


def _mark_world_paint_object_mode_guard(system_names, *, duration=30.0):
    names = {name for name in system_names if name}
    if not names:
        return
    _WORLD_STATE["object_mode_guard_system_names"] = names
    _WORLD_STATE["object_mode_guard_until"] = time.perf_counter() + duration


def _clear_world_paint_object_mode_guard():
    _WORLD_STATE["object_mode_guard_system_names"] = set()
    _WORLD_STATE["object_mode_guard_until"] = 0.0


def _enforce_world_paint_object_mode_guard(context=None):
    context = context or bpy.context
    if _world_operator() is not None:
        return False
    if time.perf_counter() > float(_WORLD_STATE.get("object_mode_guard_until", 0.0) or 0.0):
        _WORLD_STATE["object_mode_guard_system_names"] = set()
        return False

    active_obj = getattr(context, "active_object", None)
    if active_obj is None:
        return False
    guarded_names = _WORLD_STATE.get("object_mode_guard_system_names", set())
    if active_obj.name not in guarded_names or not _is_secret_paint_system(active_obj):
        return False

    mode = getattr(context, "mode", "") or ""
    active_mode = getattr(active_obj, "mode", "") or ""
    if mode != 'SCULPT_CURVES' and active_mode != 'SCULPT_CURVES':
        return False

    mode_ok = _force_object_mode_after_world_paint(context)
    _force_object_select_tool_after_world_paint(context)
    return mode_ok


def _schedule_object_mode_after_world_paint_cleanup():
    if not _WORLD_STATE.get("object_mode_guard_timer_running", False):
        _WORLD_STATE["object_mode_guard_timer_running"] = True

        def _guard_tick():
            try:
                _force_system_names_object_mode_after_world_paint(
                    bpy.context,
                    _WORLD_STATE.get("object_mode_guard_system_names", set()),
                )
                _enforce_world_paint_object_mode_guard(bpy.context)
            except Exception:
                pass
            _WORLD_STATE["object_mode_guard_timer_running"] = False
            return None

        try:
            bpy.app.timers.register(_guard_tick, first_interval=0.05)
        except Exception:
            _WORLD_STATE["object_mode_guard_timer_running"] = False


def _activate_native_curves_tool(context, brush_type, *, area_pointer=0):
    def _activate():
        if any(
            _tool_set_by_id(context, tool_id, area_pointer=area_pointer)
            for tool_id in WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.get(brush_type, ())
        ):
            return True
        if _tool_set_by_brush_type(context, brush_type, area_pointer=area_pointer):
            return True
        if brush_type != 'DENSITY':
            return _tool_set_by_id(context, "builtin.brush", area_pointer=area_pointer)
        return False

    result = _with_original_world_toolbar(_activate)
    if brush_type != 'DENSITY':
        try:
            result = bool(shared.secret_paint_activate_essential_curves_brush_asset(brush_type, context)) or result
        except Exception:
            pass
    if result:
        _refresh_sculpt_curves_workspace_tool(context)
    return result


def _force_native_curves_tool_rebuild(context, brush_type, *, area_pointer=0):
    def _activate():
        fallback_order = ("SELECTION_PAINT", "DENSITY", "ADD", "DELETE")
        for fallback_type in fallback_order:
            if fallback_type == brush_type:
                continue
            if any(
                _tool_set_by_id(context, tool_id, area_pointer=area_pointer)
                for tool_id in WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.get(fallback_type, ())
            ):
                break
        return _activate_native_curves_tool(context, brush_type, area_pointer=area_pointer)

    return _with_original_world_toolbar(_activate)


def _activate_native_density_tool(context, *, area_pointer=0):
    return _activate_native_curves_tool(context, 'DENSITY', area_pointer=area_pointer)


def _prepare_workspace_tool_for_native_density_session(context, *, area_pointer=0):
    active_workspace_tool = _active_workspace_tool_id(context)

    return _is_world_workspace_tool_id(active_workspace_tool)


def _priority_chord_key(chord):
    if not chord:
        return None
    key_type = chord.get("key_type", "")
    if key_type in {"", "NONE"}:
        return None
    return (
        key_type,
        tuple(sorted(chord.get("modifiers", ()) or ())),
    )


def _keymap_item_priority_chord_key(keymap_item):
    try:
        if not bool(getattr(keymap_item, "active", False)):
            return None
        if getattr(keymap_item, "map_type", "") != 'KEYBOARD':
            return None
        if getattr(keymap_item, "value", "PRESS") not in {'ANY', 'PRESS'}:
            return None
        if getattr(keymap_item, "key_modifier", 'NONE') not in {'NONE', ''}:
            return None
        chord = _shortcut_chord_from_keymap_item(keymap_item)
    except Exception:
        return None
    return _priority_chord_key(chord)


def _keymap_item_conflicts_with_priority_chords(keymap_item, priority_chords):
    try:
        if not bool(getattr(keymap_item, "active", False)):
            return False
        if getattr(keymap_item, "map_type", "") != 'KEYBOARD':
            return False
        if getattr(keymap_item, "value", "PRESS") not in {'ANY', 'PRESS'}:
            return False
        if getattr(keymap_item, "key_modifier", 'NONE') not in {'NONE', ''}:
            return False

        key_type = getattr(keymap_item, "type", "")
        if key_type in {"", "NONE"}:
            return False
        if getattr(keymap_item, "any", False):
            return any(chord_key[0] == key_type for chord_key in priority_chords)

        return _keymap_item_priority_chord_key(keymap_item) in priority_chords
    except Exception:
        return False


def _world_paint_priority_shortcut_chords(context):
    priority_chords = set()
    for shortcut in WORLD_SHORTCUT_ACTIONS:
        if not _world_shortcut_available(shortcut):
            continue
        configured_items = _shortcut_configured_items(context, shortcut)
        active_items = _active_keyboard_shortcut_items(configured_items)
        if active_items:
            for keymap_item in active_items:
                chord_key = _keymap_item_priority_chord_key(keymap_item)
                if chord_key is not None:
                    priority_chords.add(chord_key)
            continue

        if _allow_default_shortcut_fallback(shortcut, configured_items):
            chord_key = _priority_chord_key(_shortcut_chord_from_default(shortcut))
            if chord_key is not None:
                priority_chords.add(chord_key)
    return priority_chords


def _world_keymap_item_is_secret_paint_shortcut(keymap_item):
    idname = getattr(keymap_item, "idname", "")
    return idname.startswith("secret.") or idname in WORLD_PAINT_SHORTCUT_OPERATOR_IDNAMES


def _restore_world_keymap_conflicts():
    restored = 0
    for keymap, keymap_item in _WORLD_STATE.get("suppressed_keymap_items", ()) or ():
        try:
            if not _world_keymap_item_is_alive(keymap, keymap_item):
                continue
            keymap_item.active = True
            restored += 1
        except Exception:
            continue
    _WORLD_STATE["suppressed_keymap_items"] = []
    return restored


def _set_world_keymap_conflicts_enabled(context, enabled):
    restored = 0
    for suppressed_item in _WORLD_STATE.get("suppressed_keymap_items", ()) or ():
        try:
            first, second = suppressed_item
        except Exception:
            continue
        try:
            if hasattr(first, "keymap_items"):
                keymap, keymap_item = first, second
                if not _world_keymap_item_is_alive(keymap, keymap_item):
                    continue
                keymap_item.active = True
            else:
                keymap_item, original_active = first, second
                keymap_item.active = original_active
            restored += 1
        except Exception:
            continue
    _WORLD_STATE["suppressed_keymap_items"] = []
    _q_debug_log_keymaps(
        "set_world_keymap_conflicts.noop",
        context,
        enabled=enabled,
        restored=restored,
    )
    return restored


def _set_world_paint_shortcuts_enabled(context, enabled):
    _q_debug_log_keymaps(
        "set_world_paint_shortcuts.enter",
        context,
        enabled=enabled,
        suppressed_before=0,
    )
    _WORLD_STATE["suppressed_world_paint_shortcut_items"] = []
    _q_debug_log_keymaps(
        "set_world_paint_shortcuts.noop",
        context,
        disabled=0,
        skipped_base=0,
    )


def _context_curve_edit_mode_active(context, curve_obj=None):
    mode = getattr(context, "mode", "") or ""
    if mode not in {'EDIT', 'EDIT_CURVE'}:
        return False
    active_obj = getattr(context, "active_object", None)
    if getattr(active_obj, "type", None) != "CURVE":
        return False
    return curve_obj is None or active_obj == curve_obj


def _world_paint_bezier_curve_edit_active(context, operator=None):
    operator = operator or _world_operator()
    return bool(
        operator is not None
        and getattr(operator, "tool_id", "") == WORLD_TOOL_BEZIER
        and _context_curve_edit_mode_active(context)
    )


def _remove_stale_shift_delete_native_keymaps(context):
    return


def _invoke_native_density_size_adjust(context, *, area_pointer=0, release_confirm=False):
    area, region, space = _view3d_area_data(context, area_pointer)
    brush_container = _tool_settings_brush_container(context)
    brush = getattr(brush_container, "brush", None) if brush_container is not None else None
    unified_settings = (
        getattr(brush_container, "unified_paint_settings", None)
        if brush_container is not None
        else None
    )
    for size_owner in (brush, unified_settings):
        if size_owner is None or not hasattr(size_owner, "use_locked_size"):
            continue
        try:
            if getattr(size_owner, "use_locked_size", "") == 'SCENE':
                size_owner.use_locked_size = 'VIEW'
        except Exception:
            pass
    size_property = "size"
    kwargs = {
        "data_path_primary": f"tool_settings.curves_sculpt.brush.{size_property}",
        "data_path_secondary": f"tool_settings.curves_sculpt.unified_paint_settings.{size_property}",
        "use_secondary": "tool_settings.curves_sculpt.unified_paint_settings.use_unified_size",
        "rotation_path": "tool_settings.curves_sculpt.brush.texture_slot.angle",
        "color_path": "tool_settings.curves_sculpt.brush.cursor_color_add",
        "fill_color_path": "",
        "fill_color_override_path": "",
        "fill_color_override_test_path": "",
        "zoom_path": "",
        "image_id": "tool_settings.curves_sculpt.brush",
        "secondary_tex": False,
        "release_confirm": bool(release_confirm),
    }
    try:
        if area is not None and region is not None and space is not None:
            with context.temp_override(area=area, region=region, space_data=space):
                bpy.ops.wm.radial_control('INVOKE_DEFAULT', **kwargs)
        else:
            bpy.ops.wm.radial_control('INVOKE_DEFAULT', **kwargs)
        return True
    except TypeError:
        kwargs.pop("release_confirm", None)
        try:
            if area is not None and region is not None and space is not None:
                with context.temp_override(area=area, region=region, space_data=space):
                    bpy.ops.wm.radial_control('INVOKE_DEFAULT', **kwargs)
            else:
                bpy.ops.wm.radial_control('INVOKE_DEFAULT', **kwargs)
            return True
        except Exception:
            return False
    except Exception:
        return False


def _operator_supports_property(operator_callable, property_name):
    try:
        get_rna_type = getattr(operator_callable, "get_rna_type", None)
        if not callable(get_rna_type):
            return True
        properties = getattr(get_rna_type(), "properties", ())
        return any(getattr(prop, "identifier", "") == property_name for prop in properties)
    except Exception:
        return True


def _invoke_native_density_spacing_adjust(context, *, area_pointer=0, release_confirm=False):
    area, region, space = _view3d_area_data(context, area_pointer)
    operator_callable = bpy.ops.sculpt_curves.min_distance_edit
    kwargs = {}
    if _operator_supports_property(operator_callable, "release_confirm"):
        kwargs["release_confirm"] = bool(release_confirm)
    try:
        if area is not None and region is not None and space is not None:
            override = {
                "area": area,
                "region": region,
                "space_data": space,
            }
            region_data = getattr(space, "region_3d", None)
            if region_data is not None:
                override["region_data"] = region_data
            with context.temp_override(**override):
                operator_callable('INVOKE_DEFAULT', **kwargs)
        else:
            operator_callable('INVOKE_DEFAULT', **kwargs)
        return True
    except TypeError:
        try:
            if area is not None and region is not None and space is not None:
                override = {
                    "area": area,
                    "region": region,
                    "space_data": space,
                }
                region_data = getattr(space, "region_3d", None)
                if region_data is not None:
                    override["region_data"] = region_data
                with context.temp_override(**override):
                    operator_callable('INVOKE_DEFAULT')
            else:
                operator_callable('INVOKE_DEFAULT')
            return True
        except Exception:
            return False
    except Exception:
        return False


WORLD_NATIVE_MODE_SHORTCUT_IDNAMES = {
    "object.mode_set",
    "view3d.object_mode_pie_or_toggle",
    "wm.call_menu_pie",
}


def _native_mode_shortcut_kind(keymap_item):
    idname = getattr(keymap_item, "idname", "")
    properties = getattr(keymap_item, "properties", None)
    if idname == "view3d.object_mode_pie_or_toggle":
        return "PIE"
    if idname == "wm.call_menu_pie":
        return (
            "PIE"
            if properties is not None
            and getattr(properties, "name", "") == "VIEW3D_MT_object_mode_pie"
            else ""
        )
    if idname != "object.mode_set" or properties is None:
        return ""
    try:
        return "TOGGLE" if bool(getattr(properties, "toggle", False)) else ""
    except Exception:
        return ""


def _native_mode_shortcut_from_event(context, event):
    if (
        getattr(event, "type", "") == 'TAB'
        and getattr(event, "value", "") in {'PRESS', 'CLICK_DRAG'}
        and _event_has_no_modifiers(event)
    ):
        return "PIE"

    keyconfigs = getattr(getattr(context, "window_manager", None), "keyconfigs", None)
    active_keyconfig = getattr(keyconfigs, "active", None)
    if active_keyconfig is None:
        return ""

    preferred_keymaps = ("Sculpt Curves", "Object Non-modal", "3D View")
    for keymap_name in preferred_keymaps:
        keymap = active_keyconfig.keymaps.get(keymap_name)
        if keymap is None:
            continue
        for keymap_item in keymap.keymap_items:
            if getattr(keymap_item, "idname", "") not in WORLD_NATIVE_MODE_SHORTCUT_IDNAMES:
                continue
            shortcut_kind = _native_mode_shortcut_kind(keymap_item)
            if shortcut_kind and _event_matches_keymap_item(event, keymap_item):
                return shortcut_kind
    return ""


def _viewport_bookmark_shortcut_from_event(context, event):
    if getattr(event, "value", "") != 'PRESS':
        return False

    for keymap_items in _viewport_bookmark_keymap_item_groups(context):
        return any(_event_matches_keymap_item(event, keymap_item) for keymap_item in keymap_items)

    return False


def _viewport_bookmark_keymap_item_groups(context):
    cached_groups = _WORLD_STATE.get("viewport_bookmark_keymap_item_groups_cache")
    if cached_groups is not None:
        return cached_groups

    keyconfigs = getattr(getattr(context, "window_manager", None), "keyconfigs", None)
    def _bookmark_keymap_items(keyconfig):
        if keyconfig is None:
            return []
        items = []
        for keymap in keyconfig.keymaps:
            for keymap_item in keymap.keymap_items:
                if getattr(keymap_item, "idname", "") != "secret.toggle_viewport_tab_bookmark":
                    continue
                items.append(keymap_item)
        return items

    groups = []
    for keyconfig_name in ("user", "addon", "active"):
        keyconfig = getattr(keyconfigs, keyconfig_name, None) if keyconfigs is not None else None
        keymap_items = _bookmark_keymap_items(keyconfig)
        if not keymap_items:
            continue
        groups.append(tuple(keymap_items))
    _WORLD_STATE["viewport_bookmark_keymap_item_groups_cache"] = tuple(groups)
    return _WORLD_STATE["viewport_bookmark_keymap_item_groups_cache"]


def _modal_idle_for_viewport_bookmark(operator):
    return not (
        getattr(operator, "stroke_active", False)
        or getattr(operator, "adjust_mode", "")
        or getattr(operator, "_pick_source_hold_active", False)
        or getattr(operator, "_entry_source_preview_active", False)
    )


def _addon_preferences(context):
    addon = context.preferences.addons.get(shared.__package__)
    return addon.preferences if addon else None


def _world_paint_interpolate_preference(context):
    preferences = _addon_preferences(context)
    return bool(getattr(preferences, "world_paint_interpolate", True)) if preferences is not None else True


def _store_world_paint_interpolate_preference(context, enabled):
    preferences = _addon_preferences(context)
    if preferences is None or not hasattr(preferences, "world_paint_interpolate"):
        return
    try:
        preferences.world_paint_interpolate = bool(enabled)
    except Exception:
        pass


def _secret_modifier(obj):
    if obj is None:
        return None
    try:
        for modifier in obj.modifiers:
            if modifier.type == 'NODES' and modifier.node_group and modifier.node_group.name.startswith("Secret Paint"):
                return modifier
    except Exception:
        return None
    return None


def _is_secret_paint_system(obj):
    if obj is None:
        return False
    try:
        return bool(getattr(obj, "type", None) == "CURVES" and _secret_modifier(obj))
    except (ReferenceError, RuntimeError):
        return False


def _is_secret_paint_source_system(obj):
    return _secret_modifier(obj) is not None


def _secret_paint_system_is_procedural(obj):
    modifier = _secret_modifier(obj)
    if modifier is None:
        return False
    try:
        return bool(modifier["Input_69"])
    except Exception:
        return False


def _source_pick_secret_system_allowed(system_obj, *, allow_procedural_systems=False):
    if not _is_secret_paint_source_system(system_obj):
        return False
    if not allow_procedural_systems and _secret_paint_system_is_procedural(system_obj):
        return False
    return True


def _has_secret_paint_system_child(obj):
    if obj is None:
        return False

    children_to_check = list(getattr(obj, "children", []) or [])
    while children_to_check:
        child = children_to_check.pop()
        if _is_secret_paint_source_system(child):
            return True
        children_to_check.extend(list(getattr(child, "children", []) or []))
    return False


def _iter_secret_paint_systems(scene=None):
    if scene is not None:
        objects = scene.objects
    else:
        try:
            objects = bpy.data.objects
        except Exception:
            return
    for obj in objects:
        if _is_secret_paint_system(obj):
            yield obj


def _source_signature(brush_object, brush_collection):
    return (
        _safe_rna_name(brush_object),
        _safe_rna_name(brush_collection),
    )


def _same_source(modifier, brush_object, brush_collection):
    try:
        return modifier["Input_2"] == brush_object and modifier["Input_9"] == brush_collection
    except Exception:
        return False


def _curve_point_count(curves_obj):
    try:
        return sum(len(spline.points) for spline in curves_obj.data.curves)
    except Exception:
        return 0


def _system_curve_count(system_obj):
    try:
        return len(system_obj.data.curves)
    except Exception:
        return 0


def _system_surface_object(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return None
    try:
        surface_obj = modifier["Input_73"]
    except Exception:
        surface_obj = None
    if surface_obj is not None:
        return surface_obj
    try:
        surface_obj = getattr(system_obj.data, "surface", None)
    except Exception:
        surface_obj = None
    if surface_obj is not None:
        return surface_obj
    try:
        return getattr(system_obj, "parent", None)
    except (ReferenceError, RuntimeError):
        return None


def _secret_paint_surface_uv_name(surface_obj):
    if surface_obj is None or getattr(surface_obj, "type", "") != "MESH":
        return ""
    mesh = getattr(surface_obj, "data", None)
    uv_layers = getattr(mesh, "uv_layers", None) if mesh is not None else None
    if uv_layers is None:
        return ""

    try:
        custom_uv = uv_layers.get(shared.SECRET_PAINT_AUTO_UV_NAME)
    except Exception:
        custom_uv = None
    if custom_uv is not None:
        return custom_uv.name

    for uvmap in uv_layers:
        try:
            if uvmap.active_render:
                return uvmap.name
        except Exception:
            pass
    return ""


def _sync_secret_paint_system_surface_uv(system_obj, surface_obj=None):
    if system_obj is None or getattr(system_obj, "type", "") != "CURVES":
        return False
    curves_data = getattr(system_obj, "data", None)
    if curves_data is None:
        return False

    surface_obj = surface_obj if surface_obj is not None else _system_surface_object(system_obj)
    uv_name = _secret_paint_surface_uv_name(surface_obj)
    if not uv_name:
        return False

    changed = False
    try:
        if getattr(curves_data, "surface", None) != surface_obj:
            curves_data.surface = surface_obj
            changed = True
    except Exception:
        pass
    try:
        if curves_data.surface_uv_map != uv_name:
            curves_data.surface_uv_map = uv_name
            changed = True
    except Exception:
        pass
    return changed


def _ensure_world_target_secret_paint_uvs(operator, context, surface_obj):
    if surface_obj is None or getattr(surface_obj, "type", "") != "MESH":
        return False
    mesh = getattr(surface_obj, "data", None)
    if mesh is None:
        return False

    try:
        uv_ready = shared._secret_paint_auto_uv_cache_matches(mesh)
    except Exception:
        uv_ready = bool(_secret_paint_surface_uv_name(surface_obj))
    if uv_ready:
        return False

    try:
        shared.Check_if_trigger_UV_Reprojection(
            operator,
            context,
            activeobj=surface_obj,
            objselection=[surface_obj],
        )
        return bool(_secret_paint_surface_uv_name(surface_obj))
    except Exception:
        pass

    try:
        trigger_auto_uvs = shared._secret_paint_pref("trigger_auto_uvs", 150000, context)
    except Exception:
        trigger_auto_uvs = 150000
    try:
        face_count = len(mesh.polygons)
    except Exception:
        face_count = trigger_auto_uvs
    if trigger_auto_uvs <= 0 or face_count >= trigger_auto_uvs or getattr(mesh, "library", None):
        return False

    try:
        shared._secret_paint_fast_reproject_surface_uvs(surface_obj)
        return bool(_secret_paint_surface_uv_name(surface_obj))
    except Exception:
        return False


def _ensure_world_system_surface_uvs(operator, context, system_obj, target_info=None):
    surface_obj = None
    if target_info is not None:
        surface_obj = target_info.get("surface_obj")
    if surface_obj is None:
        surface_obj = _system_surface_object(system_obj)
    _ensure_world_target_secret_paint_uvs(operator, context, surface_obj)
    return _sync_secret_paint_system_surface_uv(system_obj, surface_obj)


def _tool_settings_brush_container(context):
    try:
        return context.tool_settings.curves_sculpt
    except Exception:
        return None


def _tool_settings_curve_paint(context):
    try:
        return context.scene.tool_settings.curve_paint_settings
    except Exception:
        return None


def _ensure_curves_brush(name, brush_type):
    matches = []
    for brush in bpy.data.brushes:
        try:
            if hasattr(brush, "use_paint_sculpt_curves") and not brush.use_paint_sculpt_curves:
                continue
            current_type = shared.secret_paint_curves_brush_type(brush)
            if current_type == brush_type:
                matches.append(brush)
        except Exception:
            continue

    if matches:
        return matches[0]

    brush = bpy.data.brushes.new(name, mode="SCULPT_CURVES")
    shared.secret_paint_set_curves_brush_type(brush, brush_type)
    brush.size = 150
    return brush


def _ensure_slide_brush():
    return _ensure_curves_brush("Slide Curves", "SLIDE")


def _ensure_select_tool():
    return False


def _activate_builtin_tool(*tool_ids):
    for tool_id in tool_ids:
        if not tool_id:
            continue
        try:
            result = bpy.ops.wm.tool_set_by_id(name=tool_id)
            if _operator_result_ok(result):
                return True
        except Exception:
            continue
    return False


def _ensure_curve_draw_settings(context):
    curve_settings = _tool_settings_curve_paint(context)
    if curve_settings is None:
        return
    curve_settings.depth_mode = 'SURFACE'
    curve_settings.use_project_only_selected = False
    curve_settings.use_offset_absolute = True
    curve_settings.use_stroke_endpoints = True
    curve_settings.error_threshold = 8
    curve_settings.fit_method = 'REFIT'
    curve_settings.use_corners_detect = False
    curve_settings.corner_angle = math.radians(70.0)
    curve_settings.radius_taper_start = 1
    curve_settings.radius_taper_end = 1
    curve_settings.radius_min = 0
    curve_settings.radius_max = 4
    curve_settings.use_pressure_radius = False
    curve_settings.surface_offset = 0.02
    curve_settings.surface_plane = 'VIEW'
    curve_settings.curve_type = 'BEZIER'
    draw_props = _curve_draw_operator_props(context)
    if draw_props is not None:
        try:
            draw_props.is_curve_2d = False
        except Exception:
            pass
        try:
            draw_props.bezier_as_nurbs = False
        except Exception:
            pass


def _curve_draw_operator_props(context):
    workspace = getattr(context, "workspace", None)
    if workspace is not None:
        tools = getattr(workspace, "tools", None)
        if tools is not None:
            for mode in (getattr(context, "mode", "") or "", "EDIT_CURVE"):
                if not mode:
                    continue
                try:
                    tool = tools.from_space_view3d_mode(mode, create=False)
                except Exception:
                    tool = None
                if tool is None:
                    continue
                try:
                    return tool.operator_properties("curves.draw")
                except Exception:
                    pass
    try:
        return context.window_manager.operator_properties_last("curves.draw")
    except Exception:
        return None


def _layout_prop_if_available(layout, data, prop_name, **kwargs):
    try:
        if not hasattr(data, prop_name):
            return False
        layout.prop(data, prop_name, **kwargs)
        return True
    except Exception:
        return False


def _draw_world_bezier_curve_topbar_controls(layout, context):
    curve_settings = _tool_settings_curve_paint(context)
    if curve_settings is None:
        return

    layout.label(icon='CURVE_BEZCURVE')
    _layout_prop_if_available(layout, curve_settings, "curve_type", text="")
    depth_row = layout.row(align=True)
    depth_mode = getattr(curve_settings, "depth_mode", 'SURFACE')
    cursor_op = depth_row.operator(
        "secret.world_paint_set_bezier_depth_mode",
        text="Cursor",
        depress=depth_mode == 'CURSOR',
    )
    cursor_op.depth_mode = 'CURSOR'
    surface_op = depth_row.operator(
        "secret.world_paint_set_bezier_depth_mode",
        text="Surface",
        depress=depth_mode == 'SURFACE',
    )
    surface_op.depth_mode = 'SURFACE'
    try:
        layout.popover("SECRET_PT_world_paint_bezier_settings", text="...")
    except Exception:
        pass


def _draw_world_bezier_curve_settings(layout, context):
    curve_settings = _tool_settings_curve_paint(context)
    if curve_settings is None:
        return

    layout.use_property_split = True
    layout.use_property_decorate = False

    if getattr(curve_settings, "curve_type", 'BEZIER') == 'BEZIER':
        _layout_prop_if_available(layout, curve_settings, "fit_method", text="Method")
        _layout_prop_if_available(layout, curve_settings, "error_threshold", text="Tolerance")
        row = layout.row(heading="Corners", align=True)
        _layout_prop_if_available(row, curve_settings, "use_corners_detect", text="")
        sub = row.row(align=True)
        try:
            sub.active = bool(curve_settings.use_corners_detect)
        except Exception:
            pass
        _layout_prop_if_available(sub, curve_settings, "corner_angle", text="")
        layout.separator()

    col = layout.column(align=True)
    _layout_prop_if_available(col, curve_settings, "radius_taper_start", text="Taper Start", slider=True)
    _layout_prop_if_available(col, curve_settings, "radius_taper_end", text="End", slider=True)

    col = layout.column(align=True)
    _layout_prop_if_available(col, curve_settings, "radius_min", text="Radius Min")
    _layout_prop_if_available(col, curve_settings, "radius_max", text="Max")
    _layout_prop_if_available(col, curve_settings, "use_pressure_radius", text="Use Pressure")

    if getattr(curve_settings, "depth_mode", "") == 'SURFACE':
        layout.separator()
        col = layout.column()
        _layout_prop_if_available(col, curve_settings, "use_project_only_selected", text="Project Onto Selected")
        _layout_prop_if_available(col, curve_settings, "surface_offset", text="Offset")
        _layout_prop_if_available(col, curve_settings, "use_offset_absolute", text="Absolute Offset")
        _layout_prop_if_available(col, curve_settings, "use_stroke_endpoints", text="Only First")
        try:
            show_surface_plane = bool(curve_settings.use_stroke_endpoints)
        except Exception:
            show_surface_plane = True
        if show_surface_plane:
            _layout_prop_if_available(col, curve_settings, "surface_plane", text="Plane")

    draw_props = _curve_draw_operator_props(context)
    if draw_props is not None:
        col = layout.column(align=True)
        _layout_prop_if_available(col, draw_props, "is_curve_2d", text="Curve 2D")
        _layout_prop_if_available(col, draw_props, "bezier_as_nurbs", text="As NURBS")


def _mesh_from_evaluated_object(target_obj, depsgraph):
    eval_obj = target_obj.evaluated_get(depsgraph)
    mesh = None
    try:
        mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph, preserve_all_data_layers=True)
    except TypeError:
        try:
            mesh = bpy.data.meshes.new_from_object(eval_obj, preserve_all_data_layers=True, depsgraph=depsgraph)
        except Exception:
            mesh = None
    except Exception:
        mesh = None

    if mesh is not None:
        return mesh

    try:
        temp_mesh = eval_obj.to_mesh()
    except Exception:
        temp_mesh = None

    if temp_mesh is None:
        return None

    mesh = bpy.data.meshes.new(f"Secret Paint Target {target_obj.name}")
    mesh.from_mesh(temp_mesh)
    try:
        eval_obj.to_mesh_clear()
    except Exception:
        pass
    return mesh


def _ensure_proxy_surface(context, target_system):
    if target_system is None:
        return None

    depsgraph = context.evaluated_depsgraph_get()
    mesh = _mesh_from_evaluated_object(target_system, depsgraph)
    if mesh is None:
        return None

    proxy_name = f"Secret Paint Target Surface {target_system.name}"
    proxy = bpy.data.objects.get(proxy_name)
    if proxy is None or proxy.type != "MESH":
        proxy = bpy.data.objects.new(proxy_name, mesh)
        context.scene.collection.objects.link(proxy)
    else:
        old_mesh = proxy.data
        proxy.data = mesh
        try:
            if old_mesh and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
        except Exception:
            pass

    proxy[WORLD_PAINT_PROXY_PROP] = target_system.name
    proxy.hide_render = True
    proxy.hide_select = True
    proxy.display_type = 'WIRE'
    proxy.hide_viewport = True
    proxy.matrix_world = target_system.matrix_world
    return proxy


def _majority_brush_collection(selected_objects):
    selected_objects = [
        obj for obj in selected_objects
        if _safe_object_type(obj) in {"MESH", "EMPTY", "CURVE"}
    ]
    if len(selected_objects) < 2:
        return None

    collection_counts = {}
    for obj in selected_objects:
        for collection in set(getattr(obj, "users_collection", ()) or ()):
            collection_counts[collection] = collection_counts.get(collection, 0) + 1

    if not collection_counts:
        return None
    highest_count = max(collection_counts.values())
    winners = [
        collection for collection, count in collection_counts.items()
        if count == highest_count
    ]
    if len(winners) != 1 or highest_count <= (len(selected_objects) / 2.0):
        return None
    return winners[0]


def _objects_share_collection(first_obj, second_obj):
    first_collections = set(getattr(first_obj, "users_collection", ()) or ())
    second_collections = set(getattr(second_obj, "users_collection", ()) or ())
    return bool(first_collections.intersection(second_collections))


def selected_pair_should_use_non_active_source(context):
    selected = list(getattr(context, "selected_objects", []) or [])
    active_object = getattr(context, "active_object", None)
    if len(selected) != 2 or active_object not in selected:
        return False

    selected_source = next((obj for obj in selected if obj != active_object), None)
    return bool(selected_source is not None and not _objects_share_collection(active_object, selected_source))


def _selected_source_from_context(self, context):
    selected = list(context.selected_objects)
    active_object = context.active_object
    if not selected and active_object is not None:
        selected = [active_object]
    if len(selected) > 1:
        brush_collection = _majority_brush_collection(selected)
        if brush_collection is not None:
            return {
                "origin_kind": "OBJECT",
                "origin_object": active_object if active_object in selected else selected[0],
                "brush_object": None,
                "brush_collection": brush_collection,
            }
        if len(selected) == 2 and active_object in selected:
            selected_source = next((obj for obj in selected if obj != active_object), None)
            if selected_source is not None and not _objects_share_collection(active_object, selected_source):
                source_data = _source_data_from_object_pick(self, context, selected_source, use_system_as_brush=True)
                if source_data is not None:
                    return source_data
        if active_object is not None:
            return _source_data_from_object_pick(self, context, active_object)
        return None
    if not selected:
        return None

    return _source_data_from_object_pick(self, context, selected[0])


def _source_data_from_object_pick(self, context, selected_obj, *, use_system_as_brush=False):
    if selected_obj is None:
        return None

    if _is_secret_paint_source_system(selected_obj):
        source_data = _source_data_from_system(selected_obj)
        if source_data is not None:
            if use_system_as_brush or selected_obj.type == "CURVE":
                source_data = dict(source_data)
                source_data["origin_kind"] = "OBJECT"
            return source_data
        if selected_obj.type != "CURVE":
            return None

    if selected_obj.type not in {"MESH", "EMPTY", "CURVE"}:
        return None

    brush_object = shared.secretpaint_prepare_q_brush_object(self, context, selected_obj)
    if brush_object is None:
        return None

    return {
        "origin_kind": "OBJECT",
        "origin_object": selected_obj,
        "brush_object": brush_object,
        "brush_collection": None,
    }


def _source_data_from_system(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return None
    try:
        brush_object = modifier["Input_2"] if "Input_2" in modifier else None
    except Exception:
        brush_object = None
    try:
        brush_collection = modifier["Input_9"] if "Input_9" in modifier else None
    except Exception:
        brush_collection = None
    return {
        "origin_kind": "SYSTEM",
        "origin_object": system_obj,
        "brush_object": brush_object,
        "brush_collection": brush_collection,
    }


def _first_curve_object_in_collection(collection):
    if collection is None:
        return None
    try:
        objects = collection.all_objects
    except Exception:
        return None
    for obj in objects:
        if _safe_object_type(obj) == "CURVE":
            return obj
    return None


def _source_data_curve_object(source_data):
    if not source_data:
        return None
    origin_object = source_data.get("origin_object")
    if _safe_object_type(origin_object) == "CURVE":
        return origin_object
    brush_object = source_data.get("brush_object")
    if _safe_object_type(brush_object) == "CURVE":
        return brush_object
    return _first_curve_object_in_collection(source_data.get("brush_collection"))


def _source_data_should_start_bezier_tool(source_data):
    return _source_data_curve_object(source_data) is not None


def _source_data_snapshot(source_data):
    if not source_data:
        return None

    origin_object = source_data.get("origin_object")
    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    return {
        "origin_kind": source_data.get("origin_kind", ""),
        "origin_object_name": _safe_rna_name(origin_object),
        "brush_object_name": _safe_rna_name(brush_object),
        "brush_collection_name": _safe_rna_name(brush_collection),
    }


def _source_data_from_snapshot(source_snapshot):
    if not source_snapshot:
        return None

    origin_kind = source_snapshot.get("origin_kind", "")
    origin_object_name = source_snapshot.get("origin_object_name", "")
    if not origin_object_name:
        return None

    origin_object = bpy.data.objects.get(origin_object_name)
    if origin_kind == "SYSTEM":
        if origin_object is None:
            return None
        return _source_data_from_system(origin_object)

    brush_object_name = source_snapshot.get("brush_object_name", "")
    brush_collection_name = source_snapshot.get("brush_collection_name", "")
    brush_object = bpy.data.objects.get(brush_object_name) if brush_object_name else None
    brush_collection = bpy.data.collections.get(brush_collection_name) if brush_collection_name else None
    if brush_object is None and brush_collection is None:
        return None

    return {
        "origin_kind": "OBJECT",
        "origin_object": origin_object or brush_object,
        "brush_object": brush_object,
        "brush_collection": brush_collection,
    }


def _source_data_key(source_data):
    if not source_data:
        return ("", "", "", "")

    origin_object = source_data.get("origin_object")
    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    return (
        source_data.get("origin_kind", ""),
        _safe_rna_name(origin_object),
        _safe_rna_name(brush_object),
        _safe_rna_name(brush_collection),
    )


def _source_data_contains_removed_references(source_data):
    if not source_data:
        return False
    for key in ("origin_object", "brush_object", "brush_collection"):
        datablock = source_data.get(key)
        if datablock is not None and not _safe_rna_name(datablock):
            return True
    return False


def _source_data_uses_object_as_brush(source_data, obj):
    if not isinstance(source_data, dict) or obj is None:
        return False

    try:
        if source_data.get("origin_kind") == "OBJECT" and obj == source_data.get("origin_object"):
            return True
    except Exception:
        pass

    try:
        if obj == source_data.get("brush_object"):
            return True
    except Exception:
        pass

    brush_collection = source_data.get("brush_collection")
    if brush_collection is not None:
        try:
            return any(collection_obj == obj for collection_obj in brush_collection.all_objects)
        except Exception:
            pass
    return False


def _brush_object_list(source_data):
    brush_collection = source_data.get("brush_collection")
    brush_object = source_data.get("brush_object")
    if _safe_rna_name(brush_collection):
        try:
            return [obj for obj in brush_collection.all_objects if _safe_object_type(obj) in {"MESH", "EMPTY", "CURVE"}]
        except Exception:
            return []
    if _safe_rna_name(brush_object):
        return [brush_object]
    if source_data.get("origin_kind") == "SYSTEM":
        origin_system = source_data.get("origin_object")
        if _is_secret_paint_source_system(origin_system):
            return [origin_system]
    return []


def _objects_share_data(obj_a, obj_b):
    try:
        if obj_a is None or obj_b is None:
            return False
        if obj_a == obj_b:
            return True
        return obj_a.data is not None and obj_a.data == obj_b.data
    except Exception:
        return False


def _system_uses_object_as_source(system_obj, source_obj):
    if system_obj is None or source_obj is None:
        return False
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return False
    try:
        brush_object = modifier["Input_2"] if "Input_2" in modifier else None
    except Exception:
        brush_object = None
    if brush_object == source_obj:
        return True
    if brush_object is not None and _objects_share_data(brush_object, source_obj):
        return True
    try:
        brush_collection = modifier["Input_9"] if "Input_9" in modifier else None
    except Exception:
        brush_collection = None
    if brush_collection is None:
        return False
    try:
        return any(
            collection_obj == source_obj or _objects_share_data(collection_obj, source_obj)
            for collection_obj in brush_collection.all_objects
        )
    except Exception:
        return False


def _matrices_close(matrix_a, matrix_b, tolerance=1.0e-5):
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


def _hit_matches_original_object_surface(obj, depsgraph, hit_location, tolerance=0.01):
    if obj is None or getattr(obj, "type", "") != "MESH" or depsgraph is None or hit_location is None:
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


def _nearest_system_root_distance(system_obj, location):
    if system_obj is None or location is None:
        return float("inf")
    _offsets, _positions, roots, _tips, _lengths = _system_curve_world_data(system_obj)
    distances = [
        (root_world - location).length
        for root_world in roots
        if root_world is not None
    ]
    if not distances:
        return float("inf")
    return min(distances)


def _source_system_candidates_for_object(source_obj, *, exclude=None):
    if source_obj is None:
        return []

    scene = bpy.context.scene
    now = time.perf_counter()
    cache = _WORLD_STATE.setdefault("source_system_candidates_cache", {})
    cache_key = (
        getattr(scene, "name", ""),
        getattr(source_obj, "name", ""),
        getattr(exclude, "name", "") if exclude is not None else "",
    )
    cached = cache.get(cache_key)
    if cached and now - cached.get("time", 0.0) < 0.35:
        return [
            obj for obj in cached.get("objects", [])
            if obj is not None and obj.name in bpy.data.objects
        ]

    candidates = [
        obj for obj in scene.objects
        if obj != exclude and _is_secret_paint_system(obj) and _system_uses_object_as_source(obj, source_obj)
    ]
    cache[cache_key] = {"time": now, "objects": candidates}
    if len(cache) > 64:
        oldest_key = min(cache, key=lambda key: cache[key].get("time", 0.0))
        cache.pop(oldest_key, None)
    return candidates


def _best_system_using_source_object(source_obj, hit_location, *, exclude=None):
    if source_obj is None:
        return None
    candidates = _source_system_candidates_for_object(source_obj, exclude=exclude)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return min(candidates, key=lambda candidate: _nearest_system_root_distance(candidate, hit_location))


def _best_source_system_for_hit_object(hit_obj, hit_location):
    if hit_obj is None:
        return None
    if _is_secret_paint_system(hit_obj):
        return hit_obj
    return _best_system_using_source_object(hit_obj, hit_location)


def _hit_is_original_source_object_surface(obj, hit_matrix, hit_location, depsgraph):
    if obj is None:
        return False
    if getattr(obj, "type", "") == "MESH":
        return _hit_matches_original_object_surface(obj, depsgraph, hit_location)
    try:
        return _matrices_close(hit_matrix, obj.matrix_world)
    except Exception:
        return False


def _source_system_from_instanced_source_hit(hit_obj, hit_location, hit_matrix, depsgraph):
    if hit_obj is None:
        return None
    hit_is_original = _hit_is_original_source_object_surface(hit_obj, hit_matrix, hit_location, depsgraph)
    if not hit_is_original:
        picked_system = _best_system_using_source_object(hit_obj, hit_location, exclude=hit_obj)
        if picked_system is not None:
            return picked_system
    if _is_secret_paint_source_system(hit_obj):
        return hit_obj
    if hit_is_original:
        return None
    return _best_system_using_source_object(hit_obj, hit_location)


def _secret_paint_system_from_target_hit(hit_obj, hit_location, hit_matrix, depsgraph):
    if _is_secret_paint_system(hit_obj):
        return hit_obj
    return _source_system_from_instanced_source_hit(
        hit_obj,
        hit_location,
        hit_matrix,
        depsgraph,
    )


def _target_info_for_secret_paint_hit(context, hit_obj, hit_location, hit_normal, hit_matrix, depsgraph):
    picked_system = _secret_paint_system_from_target_hit(hit_obj, hit_location, hit_matrix, depsgraph)
    if picked_system is None:
        return None
    if not (
        _world_target_surface_feature_enabled() and
        bool(picked_system.get(WORLD_PAINT_TARGET_ENABLED_PROP, False))
    ):
        return None

    surface_obj = _system_surface_object(picked_system)
    if surface_obj is None or getattr(surface_obj, "type", "") != "MESH":
        return None

    target_info = {
        "kind": WORLD_TARGET_KIND_MESH,
        "target_owner": surface_obj,
        "surface_obj": surface_obj,
        "hover_object": picked_system,
        "location": hit_location,
        "normal": hit_normal,
    }
    return _stabilize_target_info(context, target_info)


def _world_system_match_candidates(source_data):
    if (
        source_data.get("origin_kind") == "SYSTEM"
        and source_data.get("brush_object") is None
        and source_data.get("brush_collection") is None
    ):
        operator = _world_operator()
        if (
            operator is not None and
            getattr(operator, "surface_lock", False) and
            len(_operator_locked_target_infos(operator)) > 1
        ):
            return bpy.context.scene.objects
        origin_system = _explicit_world_source_system(source_data)
        return [origin_system] if origin_system is not None else []
    return bpy.context.scene.objects


def _explicit_world_source_system(source_data):
    if source_data.get("origin_kind") != "SYSTEM":
        return None
    origin_system = source_data.get("origin_object")
    return origin_system if _is_secret_paint_system(origin_system) else None


def _world_system_disabled_for_automatic_match(system_obj):
    try:
        return bool(system_obj.secret_paint_panel_render_hidden)
    except Exception:
        modifier = _secret_modifier(system_obj)
        if modifier is None:
            return False
        for socket_name in ("Input_99", "Socket_14"):
            try:
                if bool(modifier[socket_name]):
                    return True
            except Exception:
                pass
        return False


def _world_system_biome_disabled_for_automatic_match(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return False
    for socket_name in ("Socket_2", "Socket_15"):
        try:
            if bool(modifier[socket_name]):
                return True
        except Exception:
            pass
    return False


def _world_system_available_for_automatic_match(system_obj):
    return bool(
        not _secret_paint_system_is_procedural(system_obj)
        and not _world_system_disabled_for_automatic_match(system_obj)
        and not _world_system_biome_disabled_for_automatic_match(system_obj)
    )


def _world_system_allowed_for_source_match(system_obj, source_data):
    return (
        system_obj == _explicit_world_source_system(source_data)
        or _world_system_available_for_automatic_match(system_obj)
    )


def _world_system_biome_value(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return 0
    try:
        return modifier["Socket_0"]
    except Exception:
        return 0


def _world_system_panel_sort_key(system_obj):
    biome_value = _world_system_biome_value(system_obj)
    try:
        biome_key = (0, int(biome_value))
    except Exception:
        biome_key = (1, str(biome_value))
    try:
        panel_order = system_obj.get(
            getattr(shared, "SECRET_PAINT_PANEL_ORDER_PROP", "secret_paint_panel_order"),
            None,
        )
        no_panel_order = panel_order is None
        panel_order = int(panel_order) if panel_order is not None else 0
    except Exception:
        no_panel_order = True
        panel_order = 0
    return biome_key + (no_panel_order, panel_order, _safe_rna_name(system_obj).casefold())


def _world_system_matches_target(system_obj, surface_obj, *, target_kind=WORLD_TARGET_KIND_MESH, target_owner=None):
    existing_kind = system_obj.get(WORLD_PAINT_TARGET_KIND_PROP, WORLD_TARGET_KIND_MESH)
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
        return bool(
            existing_kind == WORLD_TARGET_KIND_SECRET_INSTANCE
            and system_obj.get(WORLD_PAINT_TARGET_OWNER_PROP, "") == _safe_rna_name(target_owner)
        )
    return _system_surface_object(system_obj) == surface_obj


def _world_target_systems(surface_obj, *, target_kind=WORLD_TARGET_KIND_MESH, target_owner=None):
    return sorted(
        [
            obj for obj in bpy.context.scene.objects
            if (
                _is_secret_paint_system(obj)
                and _world_system_matches_target(
                    obj,
                    surface_obj,
                    target_kind=target_kind,
                    target_owner=target_owner,
                )
            )
        ],
        key=_world_system_panel_sort_key,
    )


def _matching_world_system(surface_obj, source_data, *, target_kind=WORLD_TARGET_KIND_MESH, target_owner=None):
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE and not _world_target_surface_feature_enabled():
        return None

    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    explicit_system = _explicit_world_source_system(source_data)
    candidates = sorted(list(_world_system_match_candidates(source_data)), key=_world_system_panel_sort_key)
    if explicit_system is not None:
        candidates = [explicit_system] + [obj for obj in candidates if obj != explicit_system]
    for obj in candidates:
        if _safe_object_type(obj) != "CURVES":
            continue
        modifier = _secret_modifier(obj)
        if modifier is None:
            continue
        if not _same_source(modifier, brush_object, brush_collection):
            continue
        if not _world_system_allowed_for_source_match(obj, source_data):
            continue

        if not _world_system_matches_target(
            obj,
            surface_obj,
            target_kind=target_kind,
            target_owner=target_owner,
        ):
            continue
        return obj
    return None


def _matching_world_system_by_brush_hit(source_data, hit_location, radius):
    if hit_location is None:
        return None

    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    explicit_system = _explicit_world_source_system(source_data)
    if explicit_system is not None:
        modifier = _secret_modifier(explicit_system)
        if modifier is not None and _same_source(modifier, brush_object, brush_collection):
            found = _curve_roots_in_brush(explicit_system, hit_location, radius)
            if found:
                return explicit_system
    best_system = None
    best_distance = float("inf")
    for obj in _world_system_match_candidates(source_data):
        if obj == explicit_system:
            continue
        if _safe_object_type(obj) != "CURVES":
            continue
        modifier = _secret_modifier(obj)
        if modifier is None or not _same_source(modifier, brush_object, brush_collection):
            continue
        if not _world_system_allowed_for_source_match(obj, source_data):
            continue
        found = _curve_roots_in_brush(obj, hit_location, radius)
        if not found:
            continue
        nearest_distance = min(item["distance"] for item in found)
        if nearest_distance < best_distance:
            best_system = obj
            best_distance = nearest_distance
    return best_system


def _copy_brush_materials_from_object(system_obj, source_obj):
    if system_obj is None or source_obj is None:
        return False
    try:
        target_materials = system_obj.data.materials
    except Exception:
        return False

    try:
        target_materials.clear()
    except Exception:
        return False

    copied = False
    for mat_slot in getattr(source_obj, "material_slots", []) or []:
        material = getattr(mat_slot, "material", None)
        if material is None:
            continue
        try:
            target_materials.append(material)
            copied = True
        except Exception:
            pass
    return copied


def _copy_brush_materials_from_collection(system_obj, brush_collection):
    if system_obj is None or brush_collection is None:
        return False
    try:
        target_materials = system_obj.data.materials
    except Exception:
        return False

    materials = []
    try:
        collection_objects = list(brush_collection.all_objects)
    except Exception:
        collection_objects = []
    for obj in collection_objects:
        for mat_slot in getattr(obj, "material_slots", []) or []:
            material = getattr(mat_slot, "material", None)
            if material is not None and material not in materials:
                materials.append(material)

    try:
        target_materials.clear()
    except Exception:
        return False

    copied = False
    for material in materials:
        try:
            target_materials.append(material)
            copied = True
        except Exception:
            pass
    return copied


def _copy_world_system_object_display_settings(source_obj, target_obj):
    if source_obj is None or target_obj is None:
        return False
    copied = False
    for attr_name in WORLD_SYSTEM_COPY_OBJECT_DISPLAY_ATTRS:
        try:
            setattr(target_obj, attr_name, getattr(source_obj, attr_name))
            copied = True
        except Exception:
            pass
    return copied


def _copy_world_system_modifier_settings(source_modifier, target_modifier):
    if source_modifier is None or target_modifier is None:
        return False
    try:
        modifier_keys = list(source_modifier.keys())
    except Exception:
        return False
    copied = False
    for key in modifier_keys:
        try:
            target_modifier[key] = source_modifier[key]
            copied = True
        except Exception:
            pass
    return copied


def _surface_scale_compensation_value(surface_obj):
    try:
        return abs(max(surface_obj.scale))
    except Exception:
        return None


def _modifier_float_setting(modifier, key):
    if modifier is None:
        return None
    try:
        value = modifier.get(key, None)
    except Exception:
        value = None
    if value is None:
        try:
            value = modifier[key]
        except Exception:
            return None
    try:
        value = float(value)
    except Exception:
        return None
    if not math.isfinite(value):
        return None
    return value


def _modifier_positive_float_setting(modifier, key):
    value = _modifier_float_setting(modifier, key)
    return value if value is not None and value > 0.0 else None


def _modifier_density_spacing_value(modifier):
    value = _modifier_positive_float_setting(modifier, "Socket_11")
    return _density_spacing_value(value) if value is not None else None


def _target_density_spacing_value(modifier, *, source_density_spacing=None, source_scale_compensation=None):
    target_scale_compensation = _modifier_positive_float_setting(modifier, "Input_100")
    if target_scale_compensation is not None:
        if source_density_spacing is not None and source_scale_compensation is not None:
            return _density_spacing_value(
                source_density_spacing * source_scale_compensation / target_scale_compensation
            )
        density_value = _modifier_positive_float_setting(modifier, "Input_68")
        if density_value is not None:
            return _density_spacing_value(1.0 / ((density_value ** 0.5) * target_scale_compensation))
    if source_density_spacing is not None:
        return _density_spacing_value(source_density_spacing)
    return None


def _target_world_noise_scale_value(modifier, *, source_world_noise_scale=None, source_scale_compensation=None):
    target_scale_compensation = _modifier_positive_float_setting(modifier, "Input_100")
    if (
            source_world_noise_scale is not None
            and source_scale_compensation is not None
            and target_scale_compensation is not None
    ):
        return source_world_noise_scale * target_scale_compensation / source_scale_compensation
    density_value = _modifier_positive_float_setting(modifier, "Input_68")
    if density_value is not None:
        return 0.15 * (density_value ** 0.5)
    return source_world_noise_scale


def _surface_requires_deform_on_surface(surface_obj):
    try:
        surface_modifiers = list(surface_obj.modifiers)
    except Exception:
        return False
    for surface_modifier in surface_modifiers:
        try:
            if surface_modifier.type in WORLD_SURFACE_DEFORM_MODIFIER_TYPES:
                return True
        except Exception:
            pass
    return False


def _restore_world_system_target_modifier_settings(
        system_obj,
        modifier,
        surface_obj,
        *,
        deform_on_surface=None,
        source_density_spacing=None,
        source_scale_compensation=None,
        source_world_noise_scale=None,
):
    if modifier is None:
        return
    surface_requires_deform = False
    if surface_obj is not None:
        try:
            modifier["Input_73"] = surface_obj
        except Exception:
            pass
        scale_compensation = _surface_scale_compensation_value(surface_obj)
        if scale_compensation is not None:
            try:
                modifier["Input_100"] = scale_compensation
            except Exception:
                pass
        curves_data = getattr(system_obj, "data", None)
        if curves_data is not None:
            try:
                curves_data.surface = surface_obj
            except Exception:
                pass
        surface_requires_deform = _surface_requires_deform_on_surface(surface_obj)
    if surface_requires_deform:
        try:
            modifier["Input_63"] = True
        except Exception:
            pass
        try:
            surface_obj.add_rest_position_attribute = True
        except Exception:
            pass
    elif deform_on_surface:
        try:
            modifier["Input_63"] = True
        except Exception:
            pass
    density_spacing = _target_density_spacing_value(
        modifier,
        source_density_spacing=source_density_spacing,
        source_scale_compensation=source_scale_compensation,
    )
    if density_spacing is not None:
        _store_system_density_spacing(system_obj, density_spacing)
    world_noise_scale = _target_world_noise_scale_value(
        modifier,
        source_world_noise_scale=source_world_noise_scale,
        source_scale_compensation=source_scale_compensation,
    )
    if world_noise_scale is not None:
        try:
            modifier["Input_60"] = world_noise_scale
        except Exception:
            pass


def _copy_world_system_settings_from_source(system_obj, source_obj, *, surface_obj=None):
    source_modifier = _secret_modifier(source_obj)
    target_modifier = _secret_modifier(system_obj)
    if source_modifier is None or target_modifier is None:
        return False

    target_deform_on_surface = None
    try:
        target_deform_on_surface = bool(target_modifier["Input_63"])
    except Exception:
        pass
    source_density_spacing = _modifier_density_spacing_value(source_modifier)
    source_scale_compensation = _modifier_positive_float_setting(source_modifier, "Input_100")
    source_world_noise_scale = _modifier_float_setting(source_modifier, "Input_60")

    copied_modifier = _copy_world_system_modifier_settings(source_modifier, target_modifier)
    copied_display = _copy_world_system_object_display_settings(source_obj, system_obj)
    _restore_world_system_target_modifier_settings(
        system_obj,
        target_modifier,
        surface_obj if surface_obj is not None else _system_surface_object(system_obj),
        deform_on_surface=target_deform_on_surface,
        source_density_spacing=source_density_spacing,
        source_scale_compensation=source_scale_compensation,
        source_world_noise_scale=source_world_noise_scale,
    )
    return bool(copied_modifier or copied_display)


def _switch_system_brush_source(system_obj, source_data):
    modifier = _secret_modifier(system_obj)
    if modifier is None or not source_data:
        return False

    source_obj = source_data.get("origin_object")
    source_modifier = _secret_modifier(source_obj) if source_obj is not None and source_obj != system_obj else None
    if source_modifier is not None:
        copied_socket = _copy_world_system_settings_from_source(
            system_obj,
            source_obj,
            surface_obj=_system_surface_object(system_obj),
        )
        try:
            modifier["Input_39"] = False
        except Exception:
            pass
        _copy_brush_materials_from_object(system_obj, source_obj)
        try:
            system_obj.location = system_obj.location
        except Exception:
            pass
        return copied_socket

    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    if brush_object is None and brush_collection is None:
        return False

    changed = False
    try:
        modifier["Input_2"] = brush_object
        changed = True
    except Exception:
        pass
    try:
        modifier["Input_9"] = brush_collection
        changed = True
    except Exception:
        pass
    try:
        modifier["Input_39"] = False
    except Exception:
        pass

    if brush_collection is not None:
        _copy_brush_materials_from_collection(system_obj, brush_collection)
    elif brush_object is not None:
        _copy_brush_materials_from_object(system_obj, brush_object)

    try:
        system_obj.location = system_obj.location
    except Exception:
        pass
    return changed


def _configure_new_system(system_obj, source_data, surface_obj, *, target_kind=WORLD_TARGET_KIND_MESH, target_owner=None):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return system_obj

    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    source_obj = source_data.get("origin_object")
    source_modifier = _secret_modifier(source_obj) if source_obj is not None and source_obj != system_obj else None
    if source_modifier is not None:
        _copy_world_system_settings_from_source(
            system_obj,
            source_obj,
            surface_obj=surface_obj,
        )
    else:
        modifier["Input_16"] = 5
        modifier["Input_15"] = 0.25
        modifier["Input_62"] = 0.5
        modifier["Input_6"][2] = 20
        modifier["Input_60"] = 0.15 * ((modifier["Input_68"] ** 0.5)) if modifier.get("Input_68", 0.0) > 0 else 0.15
        modifier["Input_99"] = False
        try:
            modifier["Socket_14"] = False
        except Exception:
            pass
    modifier["Input_2"] = brush_object
    modifier["Input_9"] = brush_collection
    if source_modifier is None:
        _restore_world_system_target_modifier_settings(system_obj, modifier, surface_obj)
    system_obj[WORLD_PAINT_TARGET_KIND_PROP] = target_kind
    system_obj[WORLD_PAINT_TARGET_OWNER_PROP] = _safe_rna_name(target_owner)
    return system_obj


def _world_system_source_matches(system_obj, source_data):
    modifier = _secret_modifier(system_obj)
    return bool(
        modifier is not None
        and _same_source(
            modifier,
            source_data.get("brush_object"),
            source_data.get("brush_collection"),
        )
    )


def _world_new_system_biome_placement(surface_obj, source_data, *, target_kind=WORLD_TARGET_KIND_MESH, target_owner=None):
    terrain_systems = _world_target_systems(
        surface_obj,
        target_kind=target_kind,
        target_owner=target_owner,
    )
    if source_data.get("origin_kind") == "OBJECT":
        for system_obj in terrain_systems:
            if (
                _world_system_source_matches(system_obj, source_data)
                and _secret_paint_system_is_procedural(system_obj)
                and not _world_system_biome_disabled_for_automatic_match(system_obj)
            ):
                return terrain_systems, system_obj, system_obj
    first_visible_biome_system = next(
        (
            system_obj for system_obj in terrain_systems
            if not _world_system_biome_disabled_for_automatic_match(system_obj)
        ),
        None,
    )
    return terrain_systems, first_visible_biome_system, None


def _world_apply_new_system_biome_placement(
        system_obj,
        terrain_systems,
        biome_reference,
        order_after,
        *,
        preserve_modifier_settings=False,
):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return
    if not preserve_modifier_settings:
        reference_modifier = _secret_modifier(biome_reference)
        if reference_modifier is not None:
            try:
                modifier["Socket_0"] = reference_modifier["Socket_0"]
            except Exception:
                pass
            for socket_name in ("Socket_2", "Socket_15", "Socket_8"):
                try:
                    modifier[socket_name] = reference_modifier[socket_name]
                except Exception:
                    pass
        elif terrain_systems:
            biome_numbers = []
            for existing_system in terrain_systems:
                try:
                    biome_numbers.append(int(_world_system_biome_value(existing_system)))
                except Exception:
                    pass
            try:
                modifier["Socket_0"] = max(biome_numbers, default=0) + 1
            except Exception:
                pass
            for socket_name in ("Socket_2", "Socket_15"):
                try:
                    modifier[socket_name] = False
                except Exception:
                    pass

        for socket_name in ("Socket_3", "Socket_4", "Socket_5", "Socket_6"):
            try:
                modifier[socket_name] = False
            except Exception:
                pass

    target_biome = _world_system_biome_value(system_obj)
    biome_systems = [
        existing_system for existing_system in terrain_systems
        if _world_system_biome_value(existing_system) == target_biome
    ]
    insertion_index = len(biome_systems)
    if order_after in biome_systems:
        insertion_index = biome_systems.index(order_after) + 1
    biome_systems.insert(insertion_index, system_obj)
    panel_order_prop = getattr(shared, "SECRET_PAINT_PANEL_ORDER_PROP", "secret_paint_panel_order")
    for index, ordered_system in enumerate(biome_systems):
        try:
            ordered_system[panel_order_prop] = index * 10
        except Exception:
            pass
    try:
        shared._clear_side_panel_count_cache(reason="world_paint_create_system")
    except Exception:
        pass


def _find_or_create_world_system(self, context, source_data, surface_obj, *, target_kind=WORLD_TARGET_KIND_MESH, target_owner=None):
    if _source_data_uses_object_as_brush(source_data, surface_obj):
        return None
    _ensure_world_target_secret_paint_uvs(self, context, surface_obj)
    system_obj = _matching_world_system(
        surface_obj,
        source_data,
        target_kind=target_kind,
        target_owner=target_owner,
    )
    if system_obj is not None:
        _sync_secret_paint_system_surface_uv(system_obj, surface_obj)
        return system_obj

    brush_objects = _brush_object_list(source_data)
    if not brush_objects:
        return None

    terrain_systems, biome_reference, order_after = _world_new_system_biome_placement(
        surface_obj,
        source_data,
        target_kind=target_kind,
        target_owner=target_owner,
    )
    source_obj = source_data.get("origin_object")
    preserve_source_system_settings = (
        source_data.get("origin_kind") == "SYSTEM"
        and source_obj is not None
        and _secret_modifier(source_obj) is not None
    )
    system_obj = shared.secretpaint_create_curve(
        self,
        context,
        targetOBJ=surface_obj,
        brushOBJ=brush_objects,
        targetCollection=context.collection,
        transfer_modifier=False,
    )
    if system_obj is None:
        return None
    system_obj = _configure_new_system(
        system_obj,
        source_data,
        surface_obj,
        target_kind=target_kind,
        target_owner=target_owner,
    )
    _sync_secret_paint_system_surface_uv(system_obj, surface_obj)
    _world_apply_new_system_biome_placement(
        system_obj,
        terrain_systems,
        biome_reference,
        order_after,
        preserve_modifier_settings=preserve_source_system_settings,
    )
    try:
        context.view_layer.update()
    except Exception:
        pass
    _store_operator_or_system_brush_radius(
        self,
        context,
        system_obj,
        getattr(self, "brush_radius_setting", getattr(self, "brush_radius", 0.5)),
    )
    _set_system_enabled(system_obj, True)
    try:
        self._register_session_created_system(
            system_obj,
            target_kind=target_kind,
            surface_obj=surface_obj,
            target_owner=target_owner if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE else None,
        )
    except Exception:
        pass
    return system_obj


def _matching_curve_draw_object(surface_obj, source_data):
    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    expected_source = "|".join(_source_signature(brush_object, brush_collection))
    for obj in bpy.context.scene.objects:
        if obj.type != "CURVE":
            continue
        if obj.get(WORLD_PAINT_CURVE_DRAW_PROP, "") != expected_source:
            continue
        if getattr(obj, "parent", None) == surface_obj:
            return obj
    return None


def _find_or_create_curve_draw_object(context, source_data, surface_obj):
    curve_obj = _matching_curve_draw_object(surface_obj, source_data)
    if curve_obj is not None:
        _configure_curve_draw_object(context, curve_obj, source_data)
        return curve_obj

    curve_data = bpy.data.curves.new(name="Secret Paint", type="CURVE")
    curve_data.dimensions = '3D'
    curve_obj = bpy.data.objects.new("Secret Paint Curve", curve_data)
    context.collection.objects.link(curve_obj)
    curve_obj.parent = surface_obj
    curve_obj.matrix_parent_inverse = surface_obj.matrix_world.inverted()
    curve_obj[WORLD_PAINT_CURVE_DRAW_PROP] = "|".join(
        _source_signature(source_data.get("brush_object"), source_data.get("brush_collection"))
    )
    _configure_curve_draw_object(context, curve_obj, source_data)
    return curve_obj


def _matching_native_curve_draw_object(source_data):
    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    expected_source = "|".join(_source_signature(brush_object, brush_collection))
    for obj in bpy.context.scene.objects:
        if obj.type != "CURVE":
            continue
        if obj.get(WORLD_PAINT_CURVE_DRAW_PROP, "") != expected_source:
            continue
        if not obj.get(WORLD_PAINT_CURVE_DRAW_NATIVE_PROP, False):
            continue
        return obj
    return None


def _find_or_create_native_curve_draw_object(context, source_data):
    source_curve = _source_data_curve_object(source_data)
    if source_curve is not None:
        _configure_curve_draw_object(context, source_curve, source_data)
        return source_curve

    curve_obj = _matching_native_curve_draw_object(source_data)
    if curve_obj is not None:
        _configure_curve_draw_object(context, curve_obj, source_data)
        return curve_obj

    return _create_native_curve_draw_object(context, source_data)


def _create_native_curve_draw_object(context, source_data):
    curve_data = bpy.data.curves.new(name="Secret Paint", type="CURVE")
    curve_data.dimensions = '3D'
    curve_obj = bpy.data.objects.new("Secret Paint Curve", curve_data)
    context.collection.objects.link(curve_obj)
    try:
        curve_obj.location = context.scene.cursor.location
    except Exception:
        pass
    curve_obj[WORLD_PAINT_CURVE_DRAW_PROP] = "|".join(
        _source_signature(source_data.get("brush_object"), source_data.get("brush_collection"))
    )
    curve_obj[WORLD_PAINT_CURVE_DRAW_NATIVE_PROP] = True
    _configure_curve_draw_object(context, curve_obj, source_data)
    return curve_obj


def _curve_draw_density_source_object(source_obj):
    if source_obj is None:
        return None
    try:
        if source_obj.type == "MESH":
            assembly_parent = shared.secret_assembly_parent_object(source_obj)
            if assembly_parent is not None and assembly_parent.type == "MESH":
                return assembly_parent
    except Exception:
        pass
    return source_obj


def _curve_draw_source_density_value(source_data, context=None):
    density_objects = []
    for source_obj in _brush_object_list(source_data):
        density_obj = _curve_draw_density_source_object(source_obj)
        if density_obj is None:
            continue
        try:
            max_dimension = max(density_obj.dimensions)
        except Exception:
            continue
        if max_dimension > 0.0:
            density_objects.append((max_dimension, density_obj))
    if not density_objects:
        return None
    max_dimension, _density_obj = min(density_objects, key=lambda item: item[0])
    return shared.secret_paint_apply_object_size_density_multiplier(
        (1.0 / (max_dimension ** 2.0)) * 2.0,
        context,
    )


def _configure_curve_draw_object(context, curve_obj, source_data):
    if curve_obj is None or not source_data:
        return curve_obj

    modifier = _secret_modifier(curve_obj)
    if modifier is None:
        try:
            shared.contextorencurveappend(context, activeobj=curve_obj)
        except Exception:
            pass
        modifier = _secret_modifier(curve_obj)
    if modifier is None:
        return curve_obj

    source_obj = source_data.get("origin_object")
    source_modifier = _secret_modifier(source_obj) if source_obj is not None and source_obj != curve_obj else None
    if source_modifier is not None:
        for input_name in WORLD_BRUSH_SWITCH_COPY_INPUTS:
            try:
                modifier[input_name] = source_modifier[input_name]
            except Exception:
                pass
        try:
            modifier["Input_39"] = False
        except Exception:
            pass
        _copy_brush_materials_from_object(curve_obj, source_obj)
    else:
        brush_object = source_data.get("brush_object")
        brush_collection = source_data.get("brush_collection")
        try:
            modifier["Input_2"] = brush_object
        except Exception:
            pass
        try:
            modifier["Input_9"] = brush_collection
        except Exception:
            pass
        if brush_collection is not None:
            _copy_brush_materials_from_collection(curve_obj, brush_collection)
        elif brush_object is not None:
            _copy_brush_materials_from_object(curve_obj, brush_object)

    density_value = _curve_draw_source_density_value(source_data, context)
    if density_value is not None:
        try:
            modifier["Input_68"] = density_value
        except Exception:
            pass
    try:
        curve_obj.data.update_tag()
    except Exception:
        pass
    try:
        curve_obj.update_tag()
    except Exception:
        pass
    return curve_obj


def _world_paint_display_type_blocked(obj, *, allow_wire_bounds_surfaces=False):
    if allow_wire_bounds_surfaces or obj is None:
        return False
    return getattr(obj, "display_type", "TEXTURED") in WORLD_BLOCKED_SURFACE_DISPLAY_TYPES


def _system_target_needs_wire_bounds_surfaces(system_obj):
    if system_obj is None:
        return False
    target_kind = system_obj.get(WORLD_PAINT_TARGET_KIND_PROP, WORLD_TARGET_KIND_MESH)
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
        if not _world_target_surface_feature_enabled():
            return False
        display_obj = bpy.data.objects.get(system_obj.get(WORLD_PAINT_TARGET_OWNER_PROP, ""))
    else:
        display_obj = _system_surface_object(system_obj)
    return _world_paint_display_type_blocked(display_obj)


def _screen_distance_to_segment_2d(point, start, end):
    px, py = point
    ax, ay = start
    bx, by = end
    abx = bx - ax
    aby = by - ay
    length_sq = abx * abx + aby * aby
    if length_sq <= 0.000001:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / length_sq))
    closest_x = ax + abx * t
    closest_y = ay + aby * t
    return math.hypot(px - closest_x, py - closest_y)


def _project_world_to_screen(context, world_location):
    try:
        projected = view3d_utils.location_3d_to_region_2d(
            context.region,
            context.region_data,
            world_location,
        )
    except Exception:
        projected = None
    if projected is None:
        return None
    return (float(projected.x), float(projected.y))


def _screen_hit_projected_segment(context, mouse_coord, start_world, end_world, threshold_px):
    start_screen = _project_world_to_screen(context, start_world)
    end_screen = _project_world_to_screen(context, end_world)
    if start_screen is None or end_screen is None:
        return False
    return _screen_distance_to_segment_2d(mouse_coord, start_screen, end_screen) <= threshold_px


def _screen_hit_object_bounds(context, obj, mouse_coord, threshold_px=WORLD_SOURCE_VISIBLE_HIT_DISTANCE_PX):
    try:
        bound_box = list(obj.bound_box)
    except Exception:
        bound_box = []
    if len(bound_box) < 8:
        return False

    matrix_world = obj.matrix_world
    world_points = [matrix_world @ Vector(corner) for corner in bound_box[:8]]
    for start_index, end_index in WORLD_BOUND_BOX_EDGE_INDICES:
        if _screen_hit_projected_segment(
            context,
            mouse_coord,
            world_points[start_index],
            world_points[end_index],
            threshold_px,
        ):
            return True
    return False


def _screen_hit_mesh_wire(context, obj, mouse_coord, threshold_px=WORLD_SOURCE_VISIBLE_HIT_DISTANCE_PX):
    mesh = getattr(obj, "data", None)
    vertices = getattr(mesh, "vertices", None)
    edges = getattr(mesh, "edges", None)
    if vertices is None or edges is None:
        return False

    try:
        edge_count = len(edges)
    except Exception:
        edge_count = 0
    if edge_count <= 0:
        return False

    matrix_world = obj.matrix_world
    sample_step = max(1, edge_count // WORLD_SOURCE_WIRE_MAX_EDGES)
    for index, edge in enumerate(edges):
        if sample_step > 1 and index % sample_step:
            continue
        try:
            vertex_a, vertex_b = edge.vertices
            start_world = matrix_world @ vertices[vertex_a].co
            end_world = matrix_world @ vertices[vertex_b].co
        except Exception:
            continue
        if _screen_hit_projected_segment(context, mouse_coord, start_world, end_world, threshold_px):
            return True
    return False


def _object_visible_for_source_pick(context, obj):
    if obj is None or obj.name.startswith("Secret Paint Viewport Mask"):
        return False
    try:
        if obj.hide_get():
            return False
    except Exception:
        pass
    try:
        if bool(getattr(obj, "hide_viewport", False)):
            return False
    except Exception:
        pass
    try:
        return bool(obj.visible_get(view_layer=context.view_layer))
    except TypeError:
        try:
            return bool(obj.visible_get())
        except Exception:
            return True
    except Exception:
        return True


def _curve_local_point_to_world(obj, co):
    try:
        if len(co) >= 4 and abs(float(co[3])) > 0.000001:
            local = Vector((float(co[0]) / float(co[3]), float(co[1]) / float(co[3]), float(co[2]) / float(co[3])))
        else:
            local = Vector((float(co[0]), float(co[1]), float(co[2])))
    except Exception:
        return None
    try:
        return obj.matrix_world @ local
    except Exception:
        return None


def _bezier_world_point(point_obj, attr_name, obj):
    try:
        co = getattr(point_obj, attr_name)
    except Exception:
        return None
    return _curve_local_point_to_world(obj, co)


def _sample_curve_spline_world_points(obj, spline):
    try:
        spline_type = spline.type
    except Exception:
        return []

    if spline_type == 'BEZIER':
        try:
            bezier_points = list(spline.bezier_points)
        except Exception:
            return []
        point_count = len(bezier_points)
        if point_count <= 0:
            return []
        if point_count == 1:
            point = _bezier_world_point(bezier_points[0], "co", obj)
            return [point] if point is not None else []

        cyclic = bool(getattr(spline, "use_cyclic_u", False))
        segment_count = point_count if cyclic else point_count - 1
        steps_per_segment = max(4, min(12, WORLD_SOURCE_CURVE_MAX_SAMPLE_SEGMENTS // max(1, segment_count)))
        samples = []
        for segment_index in range(segment_count):
            current = bezier_points[segment_index]
            next_point = bezier_points[(segment_index + 1) % point_count]
            p0 = _bezier_world_point(current, "co", obj)
            h0 = _bezier_world_point(current, "handle_right", obj)
            h1 = _bezier_world_point(next_point, "handle_left", obj)
            p1 = _bezier_world_point(next_point, "co", obj)
            if any(point is None for point in (p0, h0, h1, p1)):
                continue
            if not samples:
                samples.append(p0)
            for step in range(1, steps_per_segment + 1):
                t = step / steps_per_segment
                one_minus_t = 1.0 - t
                samples.append(
                    p0 * (one_minus_t ** 3.0) +
                    h0 * (3.0 * (one_minus_t ** 2.0) * t) +
                    h1 * (3.0 * one_minus_t * (t ** 2.0)) +
                    p1 * (t ** 3.0)
                )
        return samples

    try:
        points = list(spline.points)
    except Exception:
        return []
    samples = []
    for point in points:
        world_point = _curve_local_point_to_world(obj, getattr(point, "co", None))
        if world_point is not None:
            samples.append(world_point)
    if bool(getattr(spline, "use_cyclic_u", False)) and len(samples) > 1:
        samples.append(samples[0])
    return samples


def _screen_distance_to_curve_object(context, obj, mouse_coord):
    if getattr(obj, "type", None) != "CURVE":
        return float("inf")
    curve_data = getattr(obj, "data", None)
    splines = getattr(curve_data, "splines", None)
    if splines is None:
        return float("inf")

    best_distance = float("inf")
    any_projected = False
    try:
        spline_list = list(splines)
    except Exception:
        spline_list = []
    for spline in spline_list:
        previous_screen = None
        for world_point in _sample_curve_spline_world_points(obj, spline):
            screen_point = _project_world_to_screen(context, world_point)
            if screen_point is None:
                previous_screen = None
                continue
            any_projected = True
            best_distance = min(
                best_distance,
                math.hypot(mouse_coord[0] - screen_point[0], mouse_coord[1] - screen_point[1]),
            )
            if previous_screen is not None:
                best_distance = min(
                    best_distance,
                    _screen_distance_to_segment_2d(mouse_coord, previous_screen, screen_point),
                )
            previous_screen = screen_point

    if any_projected:
        return best_distance

    origin_screen = _project_world_to_screen(context, _safe_object_world_translation(obj))
    if origin_screen is None:
        return float("inf")
    return math.hypot(mouse_coord[0] - origin_screen[0], mouse_coord[1] - origin_screen[1])


def _source_curve_pick_candidates(context):
    now = time.perf_counter()
    cache = _WORLD_STATE.setdefault("source_curve_candidates_cache", {})
    try:
        scene_key = getattr(context.scene, "name", "")
        view_layer_key = getattr(context.view_layer, "name", "")
    except Exception:
        scene_key = ""
        view_layer_key = ""
    cache_key = (scene_key, view_layer_key)
    cached = cache.get(cache_key)
    if cached and now - cached.get("time", 0.0) < 0.35:
        return [
            obj for obj in cached.get("objects", [])
            if obj is not None and obj.name in bpy.data.objects
        ]

    try:
        objects = context.scene.objects
    except Exception:
        return []

    candidates = [
        obj for obj in objects
        if getattr(obj, "type", None) == "CURVE" and _object_visible_for_source_pick(context, obj)
    ]
    cache[cache_key] = {"time": now, "objects": candidates}
    if len(cache) > 8:
        oldest_key = min(cache, key=lambda key: cache[key].get("time", 0.0))
        cache.pop(oldest_key, None)
    return candidates


def _nearest_source_curve_object_screen_hit(context, mouse_coord):
    best_obj = None
    best_distance = WORLD_SOURCE_CURVE_HIT_DISTANCE_PX
    for obj in _source_curve_pick_candidates(context):
        distance = _screen_distance_to_curve_object(context, obj, mouse_coord)
        if distance <= best_distance:
            best_obj = obj
            best_distance = distance
    return best_obj


def _source_visible_display_hit(context, obj, mouse_coord):
    display_type = getattr(obj, "display_type", "TEXTURED")
    if display_type not in WORLD_SOURCE_VISIBLE_DISPLAY_TYPES:
        return True
    if display_type == "BOUNDS":
        return _screen_hit_object_bounds(context, obj, mouse_coord)
    if getattr(obj, "type", "") == "MESH" and _screen_hit_mesh_wire(context, obj, mouse_coord):
        return True
    return _screen_hit_object_bounds(context, obj, mouse_coord)


def _target_info_display_object(target_info):
    if not target_info:
        return None
    if target_info.get("kind") == WORLD_TARGET_KIND_SECRET_INSTANCE:
        return target_info.get("target_owner")
    return target_info.get("surface_obj") or target_info.get("target_owner")


def _target_info_display_type_blocked(target_info, *, allow_wire_bounds_surfaces=False):
    if target_info and target_info.get("_ignore_display_type_block", False):
        return False
    return _world_paint_display_type_blocked(
        _target_info_display_object(target_info),
        allow_wire_bounds_surfaces=allow_wire_bounds_surfaces,
    )


def _copy_target_info(target_info):
    if not target_info:
        return None
    if _target_info_contains_removed_references(target_info):
        return None

    copied = dict(target_info)
    for key in ("location", "normal", "_depth_anchor"):
        value = copied.get(key)
        if value is None:
            continue
        copied_value = _safe_copy_target_vector(value)
        if copied_value is None:
            copied.pop(key, None)
        else:
            copied[key] = copied_value
    return copied


def _scene_locked_terrain_data_from_target(target_info):
    if not target_info:
        return None

    target_kind = target_info.get("kind", WORLD_TARGET_KIND_MESH)
    surface_obj = target_info.get("surface_obj")
    target_owner = target_info.get("target_owner") or surface_obj
    surface_name = _safe_rna_name(surface_obj)
    owner_name = _safe_rna_name(target_owner)

    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
        if not owner_name:
            return None
    else:
        if not surface_name and owner_name:
            surface_name = owner_name
        if not owner_name:
            owner_name = surface_name
        if not surface_name:
            return None

    return {
        "kind": target_kind,
        "surface_object": surface_name,
        "target_owner": owner_name,
        "ignore_display_type_block": bool(target_info.get("_ignore_display_type_block", False)),
    }


def _scene_locked_terrain_data_key(data):
    if not isinstance(data, dict):
        return None
    target_kind = str(data.get("kind", WORLD_TARGET_KIND_MESH))
    return (
        target_kind,
        str(data.get("surface_object", "")),
        str(data.get("target_owner", "")),
    )


def _scene_locked_terrain_data_from_targets(target_infos):
    data_items = []
    seen = set()
    for target_info in target_infos or []:
        data = _scene_locked_terrain_data_from_target(target_info)
        data_key = _scene_locked_terrain_data_key(data)
        if data is None or data_key in seen:
            continue
        seen.add(data_key)
        data_items.append(data)
    if not data_items:
        return None
    if len(data_items) == 1:
        return data_items[0]
    return {"targets": data_items}


def _clear_scene_locked_terrain(context):
    scene = getattr(context, "scene", None) if context is not None else None
    if scene is None or WORLD_PAINT_LOCKED_TERRAIN_PROP not in scene:
        return False
    try:
        del scene[WORLD_PAINT_LOCKED_TERRAIN_PROP]
        return True
    except Exception:
        return False


def _store_scene_locked_terrains(context, target_infos):
    scene = getattr(context, "scene", None) if context is not None else None
    if scene is None:
        return False
    data = _scene_locked_terrain_data_from_targets(target_infos)
    if data is None:
        return False
    try:
        scene[WORLD_PAINT_LOCKED_TERRAIN_PROP] = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
        )
        return True
    except Exception:
        return False


def _store_scene_locked_terrain(context, target_info):
    return _store_scene_locked_terrains(context, [target_info])


def _load_scene_locked_terrain_data(context):
    scene = getattr(context, "scene", None) if context is not None else None
    raw_data = scene.get(WORLD_PAINT_LOCKED_TERRAIN_PROP, "") if scene is not None else ""
    if not isinstance(raw_data, str) or not raw_data.strip():
        return None
    try:
        loaded_data = json.loads(raw_data)
    except Exception:
        _clear_scene_locked_terrain(context)
        return None
    if isinstance(loaded_data, (dict, list)):
        return loaded_data
    _clear_scene_locked_terrain(context)
    return None


def _scene_locked_terrain_entries_from_data(data):
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if isinstance(data, dict):
        targets = data.get("targets")
        if isinstance(targets, list):
            return [entry for entry in targets if isinstance(entry, dict)]
        return [data]
    return []


def _scene_locked_terrain_target_info_from_data(context, data, *, clear_missing=False):
    if not isinstance(data, dict):
        return None

    target_kind = data.get("kind", WORLD_TARGET_KIND_MESH)
    ignore_display_type_block = bool(data.get("ignore_display_type_block", False))
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
        if not _world_target_surface_feature_enabled():
            return None
        target_owner = bpy.data.objects.get(str(data.get("target_owner", "")))
        if target_owner is None:
            if clear_missing:
                _clear_scene_locked_terrain(context)
            return None
        proxy = _ensure_proxy_surface(context, target_owner)
        if proxy is None:
            return None
        location = _safe_object_world_translation(target_owner)
        if location is None:
            return None
        target_info = {
            "kind": WORLD_TARGET_KIND_SECRET_INSTANCE,
            "target_owner": target_owner,
            "surface_obj": proxy,
            "hover_object": target_owner,
            "location": location,
            "normal": Vector((0.0, 0.0, 1.0)),
        }
    else:
        surface_name = str(data.get("surface_object", ""))
        owner_name = str(data.get("target_owner", "")) or surface_name
        surface_obj = bpy.data.objects.get(surface_name) or bpy.data.objects.get(owner_name)
        if surface_obj is None:
            if clear_missing:
                _clear_scene_locked_terrain(context)
            return None
        target_owner = bpy.data.objects.get(owner_name) or surface_obj
        if _safe_object_type(surface_obj) != "MESH":
            return None
        location = _safe_object_world_translation(surface_obj)
        if location is None:
            return None
        target_info = {
            "kind": WORLD_TARGET_KIND_MESH,
            "target_owner": target_owner,
            "surface_obj": surface_obj,
            "hover_object": surface_obj,
            "location": location,
            "normal": Vector((0.0, 0.0, 1.0)),
        }

    if ignore_display_type_block:
        target_info["_ignore_display_type_block"] = True
    return _copy_target_info(target_info)


def _scene_locked_terrain_target_infos(context):
    data = _load_scene_locked_terrain_data(context)
    entries = _scene_locked_terrain_entries_from_data(data)
    if not entries:
        return []

    target_infos = []
    seen = set()
    for entry in entries:
        target_info = _scene_locked_terrain_target_info_from_data(
            context,
            entry,
            clear_missing=len(entries) == 1,
        )
        target_key = _target_key(target_info)
        if target_info is None or not target_key or target_key in seen:
            continue
        seen.add(target_key)
        target_infos.append(target_info)
    return target_infos


def _scene_locked_terrain_target_info(context):
    target_infos = _scene_locked_terrain_target_infos(context)
    return target_infos[0] if target_infos else None


def _target_info_display_target_object(target_info):
    if not target_info:
        return None
    if target_info.get("kind") == WORLD_TARGET_KIND_SECRET_INSTANCE:
        return target_info.get("target_owner")
    return target_info.get("target_owner") or target_info.get("surface_obj")


def _target_info_from_lock_object(context, obj):
    if obj is None:
        return None
    if _is_secret_paint_source_system(obj):
        target_info = _target_info_from_system(
            context,
            obj,
            allow_wire_bounds_surfaces=True,
            ignore_display_type_block=True,
        )
        if target_info is not None:
            return target_info

    surface_obj = None
    if getattr(obj, "type", "") == "MESH":
        surface_obj = obj
    elif getattr(obj, "type", "") == "CURVES":
        parent_obj = getattr(obj, "parent", None)
        if getattr(parent_obj, "type", "") == "MESH":
            surface_obj = parent_obj

    if surface_obj is None:
        return None
    location = _safe_object_world_translation(surface_obj)
    if location is None:
        return None
    return {
        "kind": WORLD_TARGET_KIND_MESH,
        "target_owner": surface_obj,
        "surface_obj": surface_obj,
        "hover_object": surface_obj,
        "location": location,
        "normal": Vector((0.0, 0.0, 1.0)),
        "_ignore_display_type_block": True,
    }


def _dedupe_target_infos(target_infos):
    deduped = []
    seen = set()
    for target_info in target_infos or []:
        copied = _copy_target_info(target_info)
        target_key = _target_key(copied)
        if copied is None or not target_key or target_key in seen:
            continue
        seen.add(target_key)
        deduped.append(copied)
    return deduped


def _target_info_key_set(target_infos):
    return {
        target_key
        for target_key in (_target_key(target_info) for target_info in target_infos or [])
        if target_key
    }


def _operator_locked_target_infos(operator):
    if operator is None:
        return []
    target_infos = []
    locked_targets = getattr(operator, "locked_targets", None)
    if isinstance(locked_targets, (list, tuple)):
        target_infos.extend(locked_targets)
    locked_target = getattr(operator, "locked_target", None)
    if locked_target is not None:
        target_infos.insert(0, locked_target)
    return _dedupe_target_infos(target_infos)


def _selected_lock_target_infos(context):
    if context is None:
        return []
    target_infos = []
    try:
        selected_objects = list(getattr(context, "selected_objects", []) or [])
    except Exception:
        selected_objects = []
    for selected_obj in selected_objects:
        target_info = _target_info_from_lock_object(context, selected_obj)
        if target_info is not None:
            target_infos.append(target_info)
    return _dedupe_target_infos(target_infos)


def _preferred_lock_target_infos(context):
    context = context or bpy.context
    selected_targets = _selected_lock_target_infos(context)
    if len(selected_targets) > 1:
        return selected_targets

    operator = _world_operator()
    if operator is not None:
        if getattr(operator, "surface_lock", False):
            locked_targets = _operator_locked_target_infos(operator)
            if locked_targets:
                return locked_targets
        target_info = getattr(operator, "hover_target", None) or getattr(operator, "preview_target", None)
        if target_info is not None:
            copied_target = _copy_target_info(target_info)
            if copied_target is not None:
                return [copied_target]

    if selected_targets:
        return selected_targets

    active_obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    target_info = _target_info_from_lock_object(context, active_obj)
    if target_info is not None:
        return [target_info]

    return _scene_locked_terrain_target_infos(context)


def _context_lock_target_info(context):
    target_infos = _preferred_lock_target_infos(context)
    return target_infos[0] if target_infos else None


def world_paint_surface_lock_enabled(context=None):
    operator = _world_operator()
    if operator is not None:
        return bool(getattr(operator, "surface_lock", False))

    return bool(_scene_locked_terrain_target_infos(context or bpy.context))


def world_paint_panel_target_object(context=None):
    context = context or bpy.context
    operator = _world_operator()
    if operator is not None:
        locked_targets = _operator_locked_target_infos(operator) if getattr(operator, "surface_lock", False) else []
        target_info = locked_targets[0] if locked_targets else (
            getattr(operator, "hover_target", None) or getattr(operator, "preview_target", None)
        )
        target_obj = _target_info_display_target_object(target_info)
        if target_obj is not None:
            return target_obj

    if world_paint_surface_lock_enabled(context):
        locked_targets = _scene_locked_terrain_target_infos(context)
        target_obj = _target_info_display_target_object(locked_targets[0] if locked_targets else None)
        if target_obj is not None:
            return target_obj

    active_obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    target_info = _target_info_from_lock_object(context, active_obj)
    return _target_info_display_target_object(target_info) or active_obj


def world_paint_panel_lock_button_text(context=None):
    context = context or bpy.context
    selected_targets = _selected_lock_target_infos(context)
    operator = _world_operator()
    if operator is not None and getattr(operator, "surface_lock", False):
        locked_targets = _operator_locked_target_infos(operator)
    else:
        locked_targets = _scene_locked_terrain_target_infos(context)

    if locked_targets:
        replacing_lock = (
            len(selected_targets) > 1 and
            _target_info_key_set(selected_targets) != _target_info_key_set(locked_targets)
        )
        action = "Lock" if replacing_lock else "Unlock"
        target_count = len(selected_targets) if replacing_lock else len(locked_targets)
    else:
        action = "Lock"
        target_count = len(_preferred_lock_target_infos(context))

    return f"{action} {'Terrain' if target_count == 1 else 'Terrains'}"


def _toggle_surface_lock_without_running_operator(context):
    context = context or bpy.context
    preferences = _addon_preferences(context)
    currently_locked = world_paint_surface_lock_enabled(context)
    if currently_locked:
        selected_targets = _selected_lock_target_infos(context)
        locked_targets = _scene_locked_terrain_target_infos(context)
        if (
            len(selected_targets) > 1 and
            _target_info_key_set(selected_targets) != _target_info_key_set(locked_targets)
        ):
            if preferences is not None:
                preferences.paint_only_current_surface = True
            _store_scene_locked_terrains(context, selected_targets)
            _tag_redraw_view3d_areas(context)
            return {'FINISHED'}
        if preferences is not None:
            preferences.paint_only_current_surface = False
        _clear_scene_locked_terrain(context)
        _tag_redraw_view3d_areas(context)
        return {'FINISHED'}

    target_infos = _preferred_lock_target_infos(context)
    if not target_infos:
        return {'CANCELLED'}
    if preferences is not None:
        preferences.paint_only_current_surface = True
    _store_scene_locked_terrains(context, target_infos)

    _tag_redraw_view3d_areas(context)
    return {'FINISHED'}


def _select_world_paint_panel_target(context):
    context = context or bpy.context
    target_obj = world_paint_panel_target_object(context)
    if target_obj is None:
        return {'CANCELLED'}
    try:
        if target_obj.name not in context.view_layer.objects:
            return {'CANCELLED'}
    except Exception:
        pass

    operator = _world_operator()
    if operator is not None:
        try:
            operator.finish_world_paint(context)
        except Exception:
            pass

    try:
        if (getattr(context, "mode", "") or "") != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    for selected_obj in list(getattr(context, "selected_objects", [])):
        try:
            selected_obj.select_set(False)
        except Exception:
            pass

    try:
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
    except Exception:
        return {'CANCELLED'}

    _tag_redraw_view3d_areas(context)
    return {'FINISHED'}


def _should_skip_raycast_hit(obj, hit_matrix, hit_location, depsgraph, source_data, *, allow_wire_bounds_surfaces=False):
    if obj is None:
        return True
    if obj.name.startswith("Secret Paint Viewport Mask"):
        return True
    if _source_data_uses_object_as_brush(source_data, obj):
        return True
    if _world_paint_display_type_blocked(obj, allow_wire_bounds_surfaces=allow_wire_bounds_surfaces):
        return True

    if _is_secret_paint_system(obj):
        if not _world_target_surface_feature_enabled():
            return True
        return not bool(obj.get(WORLD_PAINT_TARGET_ENABLED_PROP, False))

    picked_system = _secret_paint_system_from_target_hit(obj, hit_location, hit_matrix, depsgraph)
    if picked_system is not None:
        if not _world_target_surface_feature_enabled():
            return True
        return not bool(picked_system.get(WORLD_PAINT_TARGET_ENABLED_PROP, False))

    return False


def _scene_hit_matches_locked_target(obj, locked_target):
    if obj is None or not locked_target:
        return False

    if locked_target.get("kind") == WORLD_TARGET_KIND_SECRET_INSTANCE:
        return obj == locked_target.get("target_owner")

    surface_obj = locked_target.get("surface_obj")
    target_owner = locked_target.get("target_owner")
    return obj == surface_obj or obj == target_owner


def _raycast_target(context, mouse_coord, source_data=None, *, allow_wire_bounds_surfaces=False):
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None

    origin = view3d_utils.region_2d_to_origin_3d(region, region_data, mouse_coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, region_data, mouse_coord)
    depsgraph = context.evaluated_depsgraph_get()
    current_origin = origin
    max_steps = 24
    hit_epsilon = 0.001

    for _step in range(max_steps):
        try:
            hit, location, normal, _face_index, obj, matrix = context.scene.ray_cast(depsgraph, current_origin, direction)
        except TypeError:
            hit, location, normal, _face_index, obj, matrix = context.scene.ray_cast(
                depsgraph,
                current_origin,
                direction,
                distance=1.0e12,
            )
        except Exception:
            return None

        if not hit or obj is None:
            return None

        secret_paint_hit_target = _target_info_for_secret_paint_hit(
            context,
            obj,
            location,
            normal,
            matrix,
            depsgraph,
        )
        if secret_paint_hit_target is not None:
            return secret_paint_hit_target

        if _should_skip_raycast_hit(
            obj,
            matrix,
            location,
            depsgraph,
            source_data,
            allow_wire_bounds_surfaces=allow_wire_bounds_surfaces,
        ):
            current_origin = location + direction * hit_epsilon
            continue

        if (
            _world_target_surface_feature_enabled() and
            _is_secret_paint_system(obj) and
            bool(obj.get(WORLD_PAINT_TARGET_ENABLED_PROP, False))
        ):
            proxy = _ensure_proxy_surface(context, obj)
            if proxy is None:
                return None
            target_info = {
                "kind": WORLD_TARGET_KIND_SECRET_INSTANCE,
                "target_owner": obj,
                "surface_obj": proxy,
                "hover_object": obj,
                "location": location,
                "normal": normal,
            }
            return _stabilize_target_info(context, target_info)

        if obj.type == "MESH":
            target_info = {
                "kind": WORLD_TARGET_KIND_MESH,
                "target_owner": obj,
                "surface_obj": obj,
                "hover_object": obj,
                "location": location,
                "normal": normal,
            }
            return _stabilize_target_info(context, target_info)

        current_origin = location + direction * hit_epsilon
    return None


def _raycast_locked_target(context, mouse_coord, locked_target, source_data=None, *, allow_wire_bounds_surfaces=False):
    if not locked_target:
        return None
    locked_allows_wire_bounds = bool(
        allow_wire_bounds_surfaces or
        locked_target.get("_ignore_display_type_block", False)
    )
    if _target_info_display_type_blocked(
        locked_target,
        allow_wire_bounds_surfaces=locked_allows_wire_bounds,
    ):
        return None
    direct_target = _raycast_target_info_surface(context, mouse_coord, locked_target)
    if direct_target is not None:
        return _stabilize_target_info(context, direct_target)

    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None

    origin = view3d_utils.region_2d_to_origin_3d(region, region_data, mouse_coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, region_data, mouse_coord)
    depsgraph = context.evaluated_depsgraph_get()
    current_origin = origin
    max_steps = 24
    hit_epsilon = 0.001

    for _step in range(max_steps):
        try:
            hit, location, normal, _face_index, obj, matrix = context.scene.ray_cast(depsgraph, current_origin, direction)
        except TypeError:
            hit, location, normal, _face_index, obj, matrix = context.scene.ray_cast(
                depsgraph,
                current_origin,
                direction,
                distance=1.0e12,
            )
        except Exception:
            return None

        if not hit or obj is None:
            return None

        secret_paint_hit_target = _target_info_for_secret_paint_hit(
            context,
            obj,
            location,
            normal,
            matrix,
            depsgraph,
        )
        if secret_paint_hit_target is not None and _target_key(secret_paint_hit_target) == _target_key(locked_target):
            return secret_paint_hit_target

        if _should_skip_raycast_hit(
            obj,
            matrix,
            location,
            depsgraph,
            source_data,
            allow_wire_bounds_surfaces=locked_allows_wire_bounds,
        ):
            current_origin = location + direction * hit_epsilon
            continue

        if not _scene_hit_matches_locked_target(obj, locked_target):
            current_origin = location + direction * hit_epsilon
            continue

        if locked_target.get("kind") == WORLD_TARGET_KIND_SECRET_INSTANCE:
            proxy = _ensure_proxy_surface(context, obj)
            if proxy is None:
                return None
            target_info = {
                "kind": WORLD_TARGET_KIND_SECRET_INSTANCE,
                "target_owner": obj,
                "surface_obj": proxy,
                "hover_object": obj,
                "location": location,
                "normal": normal,
            }
            if locked_target.get("_ignore_display_type_block", False):
                target_info["_ignore_display_type_block"] = True
            return _stabilize_target_info(context, target_info)

        if obj.type == "MESH":
            target_info = {
                "kind": WORLD_TARGET_KIND_MESH,
                "target_owner": obj,
                "surface_obj": obj,
                "hover_object": obj,
                "location": location,
                "normal": normal,
            }
            if locked_target.get("_ignore_display_type_block", False):
                target_info["_ignore_display_type_block"] = True
            return _stabilize_target_info(context, target_info)

        current_origin = location + direction * hit_epsilon
    return None


def _raycast_locked_targets(context, mouse_coord, locked_targets, source_data=None, *, allow_wire_bounds_surfaces=False):
    locked_targets = _dedupe_target_infos(locked_targets)
    if not locked_targets:
        return None
    if len(locked_targets) == 1:
        return _raycast_locked_target(
            context,
            mouse_coord,
            locked_targets[0],
            source_data=source_data,
            allow_wire_bounds_surfaces=allow_wire_bounds_surfaces,
        )

    ray_origin = None
    try:
        if context.region is not None and context.region_data is not None:
            ray_origin = view3d_utils.region_2d_to_origin_3d(
                context.region,
                context.region_data,
                mouse_coord,
            )
    except Exception:
        ray_origin = None

    best_target = None
    best_distance = float("inf")
    for locked_target in locked_targets:
        target_info = _raycast_locked_target(
            context,
            mouse_coord,
            locked_target,
            source_data=source_data,
            allow_wire_bounds_surfaces=allow_wire_bounds_surfaces,
        )
        if target_info is None:
            continue
        if ray_origin is None:
            return target_info
        location = target_info.get("location")
        try:
            distance = (location - ray_origin).length if location is not None else float("inf")
        except Exception:
            distance = float("inf")
        if distance < best_distance:
            best_distance = distance
            best_target = target_info
    return best_target


def _raycast_surface_object_from_mouse(context, mouse_coord, surface_obj):
    if surface_obj is None or getattr(surface_obj, "type", "") != "MESH":
        return None

    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None

    try:
        origin_world = view3d_utils.region_2d_to_origin_3d(region, region_data, mouse_coord)
        direction_world = view3d_utils.region_2d_to_vector_3d(region, region_data, mouse_coord)
        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = surface_obj.evaluated_get(depsgraph)
        matrix_world = eval_obj.matrix_world
        matrix_inv = matrix_world.inverted()
        origin_local = matrix_inv @ origin_world
        direction_local = matrix_inv.to_3x3() @ direction_world
        if direction_local.length <= 0.0:
            return None
        direction_local.normalize()
        try:
            hit, location_local, normal_local, _face_index = eval_obj.ray_cast(
                origin_local,
                direction_local,
                distance=1.0e12,
            )
        except TypeError:
            hit, location_local, normal_local, _face_index = eval_obj.ray_cast(
                origin_local,
                direction_local,
            )
    except Exception:
        return None

    if not hit:
        return None

    try:
        normal_matrix = matrix_world.inverted().transposed().to_3x3()
        normal_world = normal_matrix @ normal_local
        if normal_world.length <= 0.0:
            normal_world = matrix_world.to_3x3() @ normal_local
        normal_world.normalize()
    except Exception:
        try:
            normal_world = (matrix_world.to_3x3() @ normal_local).normalized()
        except Exception:
            normal_world = Vector((0.0, 0.0, 1.0))

    return matrix_world @ location_local, normal_world


def _raycast_target_info_surface(context, mouse_coord, target_info):
    if not target_info:
        return None
    surface_obj = target_info.get("surface_obj")
    hit = _raycast_surface_object_from_mouse(context, mouse_coord, surface_obj)
    if hit is None:
        return None
    location, normal = hit
    result = _copy_target_info(target_info)
    if result is None:
        return None
    result["location"] = location
    result["normal"] = normal
    return result


def _raycast_source_system(context, mouse_coord):
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None

    origin = view3d_utils.region_2d_to_origin_3d(region, region_data, mouse_coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, region_data, mouse_coord)
    depsgraph = context.evaluated_depsgraph_get()
    current_origin = origin
    max_steps = 24
    hit_epsilon = 0.001

    for _step in range(max_steps):
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
            return None

        if not hit or obj is None:
            return None

        if obj.name.startswith("Secret Paint Viewport Mask"):
            current_origin = location + direction * hit_epsilon
            continue

        picked_system = _best_source_system_for_hit_object(obj, location)
        if picked_system is not None:
            return picked_system

        if obj.type in {"MESH", "CURVE", "CURVES", "EMPTY"}:
            return None

        current_origin = location + direction * hit_epsilon
    return None


def _raycast_source_object(context, mouse_coord, *, allow_procedural_systems=False):
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None

    curve_screen_hit = _nearest_source_curve_object_screen_hit(context, mouse_coord)
    if curve_screen_hit is not None:
        return curve_screen_hit

    origin = view3d_utils.region_2d_to_origin_3d(region, region_data, mouse_coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, region_data, mouse_coord)
    depsgraph = context.evaluated_depsgraph_get()
    current_origin = origin
    max_steps = 24
    hit_epsilon = 0.001

    for _step in range(max_steps):
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
            return None

        if not hit or obj is None:
            return None

        if obj.name.startswith("Secret Paint Viewport Mask"):
            current_origin = location + direction * hit_epsilon
            continue

        proxy_system_name = obj.get(WORLD_PAINT_PROXY_PROP, "") if hasattr(obj, "get") else ""
        if proxy_system_name:
            proxy_system = bpy.data.objects.get(proxy_system_name)
            if proxy_system is not None and _source_pick_secret_system_allowed(
                proxy_system,
                allow_procedural_systems=allow_procedural_systems,
            ):
                return proxy_system
            current_origin = location + direction * hit_epsilon
            continue

        picked_system = _source_system_from_instanced_source_hit(obj, location, matrix, depsgraph)
        if picked_system is not None:
            if _source_pick_secret_system_allowed(
                picked_system,
                allow_procedural_systems=allow_procedural_systems,
            ):
                return picked_system
            current_origin = location + direction * hit_epsilon
            continue

        if _is_secret_paint_source_system(obj):
            if _source_pick_secret_system_allowed(
                obj,
                allow_procedural_systems=allow_procedural_systems,
            ):
                return obj
            current_origin = location + direction * hit_epsilon
            continue

        if obj.type in {"MESH", "EMPTY", "CURVE"}:
            if not _source_visible_display_hit(context, obj, mouse_coord):
                current_origin = location + direction * hit_epsilon
                continue
            if obj.type != "CURVE" and _has_secret_paint_system_child(obj):
                return None
            return obj

        current_origin = location + direction * hit_epsilon
    return None


def _modifier_scale_value(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return 1.0
    try:
        return float(modifier["Input_8"])
    except Exception:
        return 1.0


def _set_modifier_scale(system_obj, value):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return
    try:
        modifier["Input_8"] = value
    except Exception:
        pass


def _modifier_socket_identifier_by_name(modifier, socket_name):
    if modifier is None:
        return None

    node_group = getattr(modifier, "node_group", None)
    if node_group is None:
        return None

    try:
        items = node_group.interface.items_tree if bpy.app.version_string >= "4.0.0" else node_group.inputs
    except Exception:
        try:
            items = node_group.inputs
        except Exception:
            return None

    for item in items:
        if getattr(item, "item_type", "SOCKET") == 'PANEL':
            continue
        if getattr(item, "name", "") != socket_name:
            continue
        identifier = getattr(item, "identifier", "")
        if identifier:
            return identifier
    return None


def _set_modifier_align_to_global_z(system_obj, value):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return

    candidate_keys = []
    socket_identifier = _modifier_socket_identifier_by_name(modifier, "Align to global Z")
    if socket_identifier:
        candidate_keys.append(socket_identifier)
    if "Input_51" not in candidate_keys:
        candidate_keys.append("Input_51")

    numeric_value = float(value)
    for key in candidate_keys:
        try:
            modifier[key] = numeric_value
            return
        except Exception:
            continue


def _get_modifier_align_to_global_z(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return None

    candidate_keys = []
    socket_identifier = _modifier_socket_identifier_by_name(modifier, "Align to global Z")
    if socket_identifier:
        candidate_keys.append(socket_identifier)
    if "Input_51" not in candidate_keys:
        candidate_keys.append("Input_51")

    for key in candidate_keys:
        try:
            return float(modifier[key])
        except Exception:
            continue
    return None


def _get_system_align_to_normal(system_obj):
    align_to_global_z = _get_modifier_align_to_global_z(system_obj)
    if align_to_global_z is None:
        return None
    return align_to_global_z <= 0.5


def _sync_system_align_to_normal(system_obj, align_to_normal):
    _set_modifier_align_to_global_z(system_obj, 0.0 if align_to_normal else 1.0)


def _set_system_enabled(system_obj, enabled):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return
    try:
        modifier["Input_99"] = not enabled
    except Exception:
        pass


def _delete_visible_empty_manual_paint_systems(context, system_names):
    context = context or bpy.context
    system_names = {name for name in (system_names or ()) if name}
    if not system_names:
        return 0

    scene = getattr(context, "scene", None)
    if scene is None:
        return 0
    try:
        context.view_layer.update()
    except Exception:
        pass

    protected_names = set(_WORLD_STATE.get("bezier_handoff_object_names", set()) or set())
    candidates = []
    for obj in list(getattr(scene, "objects", []) or []):
        if getattr(obj, "name", "") not in system_names:
            continue
        if getattr(obj, "name", "") in protected_names:
            continue
        if not _is_secret_paint_system(obj):
            continue
        if _secret_paint_system_is_procedural(obj):
            continue
        if _world_system_disabled_for_automatic_match(obj):
            continue
        if _system_curve_count(obj) > 0:
            continue
        candidates.append(obj)

    if not candidates:
        return 0

    view_layer = getattr(context, "view_layer", None)
    try:
        original_active_name = view_layer.objects.active.name if view_layer and view_layer.objects.active else ""
    except Exception:
        original_active_name = ""
    try:
        original_selected_names = [obj.name for obj in context.selected_objects]
    except Exception:
        original_selected_names = []

    try:
        if (getattr(context, "mode", "") or "") != 'OBJECT':
            _mode_set_with_world_toolbar_restored('OBJECT')
    except Exception:
        pass

    deleted_names = set()
    for obj in candidates:
        try:
            obj_name = obj.name
        except Exception:
            continue
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
            deleted_names.add(obj_name)
        except Exception:
            pass

    if view_layer is not None:
        try:
            for obj in context.selected_objects:
                obj.select_set(False)
        except Exception:
            pass
        for name in original_selected_names:
            if name in deleted_names:
                continue
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            try:
                if obj.name in view_layer.objects:
                    obj.select_set(True)
            except Exception:
                pass
        if original_active_name and original_active_name not in deleted_names:
            active_obj = bpy.data.objects.get(original_active_name)
            if active_obj is not None:
                try:
                    if active_obj.name in view_layer.objects:
                        view_layer.objects.active = active_obj
                except Exception:
                    pass

    try:
        shared._clear_side_panel_count_cache(reason="world_paint_delete_empty_manual_systems")
    except Exception:
        pass
    _tag_redraw_view3d_areas(context)
    return len(deleted_names)


def _system_cache_key(system_obj):
    if system_obj is None:
        return None
    try:
        return system_obj.as_pointer()
    except Exception:
        return id(system_obj)


def _system_cache_revision(system_obj):
    curves_data = getattr(system_obj, "data", None)
    if curves_data is None:
        return 0
    try:
        return int(curves_data.get(WORLD_PAINT_CACHE_REV_PROP, 0))
    except Exception:
        return 0


def _system_curve_cache_signature(system_obj):
    curves_data = getattr(system_obj, "data", None)
    if curves_data is None:
        return None
    try:
        return (len(curves_data.curves), len(curves_data.points))
    except Exception:
        return None


def _remember_system_curve_cache_signature(system_obj):
    cache_key = _system_cache_key(system_obj)
    signature = _system_curve_cache_signature(system_obj)
    if cache_key is None or signature is None:
        return signature
    _WORLD_STATE.setdefault("curve_cache_signatures", {})[cache_key] = signature
    return signature


def _mark_system_curve_cache_dirty_if_signature_changed(system_obj):
    cache_key = _system_cache_key(system_obj)
    signature = _system_curve_cache_signature(system_obj)
    if cache_key is None or signature is None:
        return False
    signatures = _WORLD_STATE.setdefault("curve_cache_signatures", {})
    previous = signatures.get(cache_key)
    signatures[cache_key] = signature
    if previous is None or previous == signature:
        return False
    _mark_system_curve_cache_dirty(system_obj)
    return True


def _mark_system_curve_cache_dirty(system_obj):
    curves_data = getattr(system_obj, "data", None)
    if curves_data is not None:
        try:
            curves_data[WORLD_PAINT_CACHE_REV_PROP] = _system_cache_revision(system_obj) + 1
        except Exception:
            pass
    cache_key = _system_cache_key(system_obj)
    if cache_key is not None:
        _WORLD_STATE.get("curve_data_cache", {}).pop(cache_key, None)
        signature = _system_curve_cache_signature(system_obj)
        if signature is not None:
            _WORLD_STATE.setdefault("curve_cache_signatures", {})[cache_key] = signature


def _discard_system_curve_cache(system_obj):
    cache_key = _system_cache_key(system_obj)
    if cache_key is not None:
        _WORLD_STATE.get("curve_data_cache", {}).pop(cache_key, None)


def _maybe_refresh_live_view(context, *, force=False):
    if not context.view_layer:
        return
    now = time.perf_counter()
    last_update = float(_WORLD_STATE.get("last_live_update_time", 0.0) or 0.0)
    if not force and (now - last_update) < WORLD_LIVE_UPDATE_INTERVAL:
        return
    with shared.secret_paint_world_perf_span(
        "world.view_layer_update",
        threshold_ms=1.0,
        force=force,
    ):
        context.view_layer.update()
    _WORLD_STATE["last_live_update_time"] = now


def _system_brush_object(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is None:
        return None
    try:
        return modifier["Input_2"] if "Input_2" in modifier else None
    except Exception:
        return None


def _same_brush_object_systems(brush_object):
    if brush_object is None:
        return []
    systems = []
    for obj in bpy.context.scene.objects:
        modifier = _secret_modifier(obj)
        if modifier is None:
            continue
        try:
            if modifier["Input_2"] == brush_object:
                systems.append(obj)
        except Exception:
            continue
    return systems


def _brush_radius_linked_systems(system_obj):
    if system_obj is None:
        return []

    brush_object = _system_brush_object(system_obj)
    if brush_object is None:
        return [system_obj]

    linked = [system_obj]
    for candidate in _same_brush_object_systems(brush_object):
        if candidate != system_obj:
            linked.append(candidate)
    return linked


def _brush_depth_location_from_system(system_obj):
    return _safe_object_world_translation(system_obj)


def _screen_brush_units_per_pixel(context, depth_location, mouse_coord=None):
    region = getattr(context, "region", None)
    region_data = getattr(context, "region_data", None)
    if region is None or region_data is None or depth_location is None:
        return None

    if mouse_coord is None:
        mouse_coord = (region.width * 0.5, region.height * 0.5)

    try:
        base_location = view3d_utils.region_2d_to_location_3d(region, region_data, mouse_coord, depth_location)
        offset_location = view3d_utils.region_2d_to_location_3d(
            region,
            region_data,
            (mouse_coord[0] + 1.0, mouse_coord[1]),
            depth_location,
        )
    except Exception:
        return None

    if base_location is None or offset_location is None:
        return None

    units_per_pixel = (offset_location - base_location).length
    if units_per_pixel <= 0.0:
        return None
    return units_per_pixel


def _world_radius_to_screen_brush(context, world_radius, depth_location, mouse_coord=None):
    world_radius = max(WORLD_MIN_OPERATION_RADIUS, float(world_radius))
    units_per_pixel = _screen_brush_units_per_pixel(context, depth_location, mouse_coord=mouse_coord)
    if units_per_pixel is None:
        return max(0.05, world_radius)
    return max(0.05, world_radius / max(units_per_pixel, WORLD_MIN_OPERATION_RADIUS) / WORLD_SCREEN_BRUSH_RADIUS_SCALE)


def _stored_system_brush_radius(system_obj, fallback=None, *, context=None, depth_location=None, mouse_coord=None):
    for candidate in _brush_radius_linked_systems(system_obj):
        curves_data = getattr(candidate, "data", None)
        if curves_data is None:
            continue
        try:
            value = curves_data.get(WORLD_PAINT_BRUSH_RADIUS_PROP, None)
            if value is None:
                continue
            return max(0.05, float(value))
        except Exception:
            continue
    return fallback


def _store_system_brush_radius(system_obj, value):
    stored_value = max(0.05, float(value))
    changed = False
    for candidate in _brush_radius_linked_systems(system_obj):
        curves_data = getattr(candidate, "data", None)
        if curves_data is None:
            continue
        try:
            prop_changed = _world_set_idprop_if_different(
                curves_data,
                WORLD_PAINT_BRUSH_RADIUS_PROP,
                stored_value,
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            )
            changed = prop_changed or changed
            if prop_changed and hasattr(curves_data, "id_properties_ui"):
                curves_data.id_properties_ui(WORLD_PAINT_BRUSH_RADIUS_PROP).update(
                    description="Last Secret Paint world-paint brush radius used by systems sharing this object brush",
                )
        except Exception:
            continue
    return changed


def _stored_operator_brush_radius(operator, context, system_obj, fallback=None):
    return _stored_system_brush_radius(
        system_obj,
        fallback=fallback,
        context=context,
    )


def _store_operator_or_system_brush_radius(operator, context, system_obj, value=None):
    if operator is None:
        return
    if system_obj is None:
        return
    stored_value = getattr(operator, "brush_radius_setting", getattr(operator, "brush_radius", 0.5)) if value is None else value
    _store_system_brush_radius(system_obj, stored_value)


def _stored_system_density_spacing(system_obj, fallback=None):
    if system_obj is None:
        return fallback

    try:
        value = system_obj.get(WORLD_PAINT_DENSITY_SPACING_PROP, None)
        if value is not None:
            return _density_spacing_value(value, fallback=fallback)
    except Exception:
        pass

    curves_data = getattr(system_obj, "data", None)
    if curves_data is not None:
        try:
            value = curves_data.get(WORLD_PAINT_DENSITY_SPACING_PROP, None)
            if value is not None:
                return _density_spacing_value(value, fallback=fallback)
        except Exception:
            pass

    modifier = _secret_modifier(system_obj)
    if modifier is not None:
        try:
            value = modifier.get("Socket_11", None)
        except Exception:
            value = None
        if value is None:
            try:
                value = modifier["Socket_11"]
            except Exception:
                value = None
        if value is not None:
            try:
                return _density_spacing_value(value, fallback=fallback)
            except Exception:
                pass

    return fallback


def _store_system_density_spacing(system_obj, value):
    if system_obj is None:
        return False
    try:
        stored_value = _density_spacing_value(value)
    except Exception:
        return False

    changed = False
    try:
        object_changed = _world_set_idprop_if_different(
            system_obj,
            WORLD_PAINT_DENSITY_SPACING_PROP,
            stored_value,
            epsilon=WORLD_DENSITY_SPACING_EPSILON,
        )
        changed = object_changed or changed
        if object_changed and hasattr(system_obj, "id_properties_ui"):
            system_obj.id_properties_ui(WORLD_PAINT_DENSITY_SPACING_PROP).update(
                description="Last Secret Paint world-paint density spacing used by this system",
            )
    except Exception:
        pass

    curves_data = getattr(system_obj, "data", None)
    if curves_data is not None:
        try:
            data_changed = _world_set_idprop_if_different(
                curves_data,
                WORLD_PAINT_DENSITY_SPACING_PROP,
                stored_value,
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            )
            changed = data_changed or changed
            if data_changed and hasattr(curves_data, "id_properties_ui"):
                curves_data.id_properties_ui(WORLD_PAINT_DENSITY_SPACING_PROP).update(
                    description="Last Secret Paint world-paint density spacing used by this system",
                )
        except Exception:
            pass

    modifier = _secret_modifier(system_obj)
    if modifier is not None:
        try:
            changed = _world_set_idprop_if_different(
                modifier,
                "Socket_11",
                stored_value,
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            ) or changed
        except Exception:
            pass
    return changed


def _store_operator_brush_radius(operator, context=None):
    if operator is None:
        return
    active_system = bpy.data.objects.get(operator.active_system_name) if operator.active_system_name else None
    if active_system is not None:
        _store_operator_or_system_brush_radius(
            operator,
            context or bpy.context,
            active_system,
            getattr(operator, "brush_radius_setting", operator.brush_radius),
        )


def _store_operator_density_spacing(operator):
    if operator is None:
        return
    active_system = bpy.data.objects.get(operator.active_system_name) if operator.active_system_name else None
    if active_system is not None:
        _store_system_density_spacing(
            active_system,
            getattr(operator, "density_spacing", 0.1),
        )


def _same_source_systems(source_data):
    systems = []
    brush_object = source_data.get("brush_object")
    brush_collection = source_data.get("brush_collection")
    for obj in bpy.context.scene.objects:
        modifier = _secret_modifier(obj)
        if modifier and _same_source(modifier, brush_object, brush_collection):
            systems.append(obj)
    return systems


def _mark_same_source_curve_caches_dirty(source_data, *, extra_system=None):
    seen = set()
    candidates = []
    if extra_system is not None:
        candidates.append(extra_system)
    candidates.extend(_same_source_systems(source_data))
    for system_obj in candidates:
        if system_obj is None:
            continue
        cache_key = _system_cache_key(system_obj)
        if cache_key in seen:
            continue
        seen.add(cache_key)
        _mark_system_curve_cache_dirty(system_obj)


def _curves_offsets(curves_data):
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


def _attribute_collection(attribute):
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


def _attribute_array(attribute, width=1):
    data = _attribute_collection(attribute)
    if data is None:
        return []

    default_value = False if getattr(attribute, "data_type", None) == 'BOOLEAN' else 0.0
    values = [default_value] * (len(data) * width)
    field = "vector" if width == 3 else "value"
    if values:
        data.foreach_get(field, values)
    return values


def _set_attribute_array(attribute, values, width=1):
    data = _attribute_collection(attribute)
    if data is None:
        return
    field = "vector" if width == 3 else "value"
    if values:
        data.foreach_set(field, values)


def _ensure_attribute(curves_data, name, attr_type, domain):
    attribute = curves_data.attributes.get(name)
    if attribute is None:
        attribute = curves_data.attributes.new(name, attr_type, domain)
    return attribute


def _int_attribute_values(curves_data, name):
    attribute = curves_data.attributes.get(name)
    if attribute is None:
        return None, []

    values = [int(value) for value in _attribute_array(attribute, width=1)]
    curve_count = len(curves_data.curves)
    if len(values) < curve_count:
        values.extend([0] * (curve_count - len(values)))
    elif len(values) > curve_count:
        values = values[:curve_count]
    return attribute, values


def _curve_id_seed_values(curves_data):
    attribute = curves_data.attributes.get("id")
    if attribute is None:
        return []

    try:
        domain = attribute.domain
    except Exception:
        domain = ""

    values = [int(value) for value in _attribute_array(attribute, width=1)]
    curve_count = len(curves_data.curves)
    if curve_count <= 0 or not values:
        return []

    if domain == 'CURVE':
        return values[:curve_count]

    if domain == 'POINT':
        offsets = _curves_offsets(curves_data)
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


def _sync_point_ids_from_curve_values(curves_data, curve_values):
    if curves_data is None:
        return None
    curve_count = len(curves_data.curves)
    point_count = len(curves_data.points)
    if curve_count <= 0 or point_count <= 0:
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

    offsets = _curves_offsets(curves_data)
    point_values = [0] * point_count
    for curve_index in range(min(curve_count, len(curve_values))):
        stable_id = int(curve_values[curve_index])
        start = offsets[curve_index]
        end = offsets[curve_index + 1]
        for point_index in range(start, end):
            point_values[point_index] = stable_id
    _set_attribute_array(attribute, point_values, width=1)
    return attribute


def _evaluated_int_attribute_values(context, system_obj, name):
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
        attribute = eval_attributes.get(name)
        if attribute is None:
            return []
        return [int(value) for value in _attribute_array(attribute, width=1)]
    except Exception:
        return []


def _set_next_stable_curve_id(curves_data, used_ids):
    next_id = max(1, int(curves_data.get(WORLD_PAINT_NEXT_STABLE_ID_PROP, 1) or 1))
    while next_id in used_ids:
        next_id += 1
    curves_data[WORLD_PAINT_NEXT_STABLE_ID_PROP] = next_id
    return next_id


def _allocate_stable_curve_ids(curves_data, count, used_ids):
    if count <= 0:
        return []

    next_id = _set_next_stable_curve_id(curves_data, used_ids)
    allocated = []
    while len(allocated) < count:
        allocated.append(next_id)
        used_ids.add(next_id)
        next_id += 1
        while next_id in used_ids:
            next_id += 1

    curves_data[WORLD_PAINT_NEXT_STABLE_ID_PROP] = next_id
    return allocated


def _ensure_stable_curve_ids(context, system_obj):
    curves_data = getattr(system_obj, "data", None)
    if curves_data is None:
        return []

    curve_count = len(curves_data.curves)
    attribute, values = _int_attribute_values(curves_data, WORLD_PAINT_STABLE_ID_ATTR)
    ids_ready = bool(curves_data.get(WORLD_PAINT_STABLE_IDS_READY_PROP, False))
    ids_migrated = bool(curves_data.get(WORLD_PAINT_STABLE_IDS_MIGRATED_PROP, False))
    try:
        migrated_curve_count = int(curves_data.get(WORLD_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP, 0) or 0)
    except Exception:
        migrated_curve_count = 0
    if ids_migrated and migrated_curve_count <= 0 and attribute is not None:
        migrated_curve_count = curve_count
        curves_data[WORLD_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP] = int(migrated_curve_count)
    elif ids_migrated and curve_count < migrated_curve_count:
        migrated_curve_count = curve_count
        curves_data[WORLD_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP] = int(migrated_curve_count)
    migrated_curve_count = max(0, min(curve_count, migrated_curve_count))

    if attribute is None:
        values = [0] * curve_count
    elif len(values) < curve_count:
        values.extend([0] * (curve_count - len(values)))
    elif len(values) > curve_count:
        values = values[:curve_count]

    final_values = [int(value) for value in values]
    used_ids = set()
    invalid_indices = []
    for curve_index, value in enumerate(final_values):
        if curve_index < migrated_curve_count:
            used_ids.add(value)
            continue
        if value == 0 or value in used_ids:
            invalid_indices.append(curve_index)
            continue
        used_ids.add(value)

    should_seed_from_evaluated = curve_count > 0 and (
        attribute is None or
        not ids_ready or
        not used_ids
    )
    if should_seed_from_evaluated:
        seeded_values = [
            int(value)
            for value in _evaluated_int_attribute_values(context, system_obj, WORLD_PAINT_STABLE_ID_ATTR)[:curve_count]
        ]
        for curve_index in list(invalid_indices):
            if curve_index >= len(seeded_values):
                continue
            candidate_id = seeded_values[curve_index]
            if candidate_id == 0 or candidate_id in used_ids:
                continue
            final_values[curve_index] = candidate_id
            used_ids.add(candidate_id)
            invalid_indices.remove(curve_index)

    if should_seed_from_evaluated:
        source_id_values = _curve_id_seed_values(curves_data)
        for curve_index in list(invalid_indices):
            if curve_index >= len(source_id_values):
                continue
            candidate_id = source_id_values[curve_index]
            if candidate_id == 0 or candidate_id in used_ids:
                continue
            final_values[curve_index] = candidate_id
            used_ids.add(candidate_id)
            invalid_indices.remove(curve_index)

    if invalid_indices:
        new_ids = _allocate_stable_curve_ids(curves_data, len(invalid_indices), used_ids)
        for curve_index, stable_id in zip(invalid_indices, new_ids):
            final_values[curve_index] = int(stable_id)

    values_changed = attribute is None or not ids_ready or final_values != values
    attribute = _ensure_attribute(curves_data, WORLD_PAINT_STABLE_ID_ATTR, 'INT', 'CURVE')
    _set_attribute_array(attribute, final_values, width=1)
    _sync_point_ids_from_curve_values(curves_data, final_values)
    _set_next_stable_curve_id(curves_data, {value for value in final_values if value > 0})
    curves_data[WORLD_PAINT_STABLE_IDS_READY_PROP] = True
    if values_changed:
        _mark_system_curve_cache_dirty(system_obj)
        try:
            curves_data.update_tag()
        except Exception:
            pass
    return final_values


def _append_stable_curve_ids(curves_data, start_index, count):
    if count <= 0:
        return []

    attribute = _ensure_attribute(curves_data, WORLD_PAINT_STABLE_ID_ATTR, 'INT', 'CURVE')
    curve_count = len(curves_data.curves)
    end_index = min(curve_count, max(start_index, 0) + count)
    assign_count = max(0, end_index - start_index)
    if assign_count <= 0:
        return []

    new_ids = _allocate_stable_curve_ids(curves_data, assign_count, set())
    data = _attribute_collection(attribute)
    try:
        for offset, stable_id in enumerate(new_ids):
            data[start_index + offset].value = int(stable_id)
    except Exception:
        values = [int(value) for value in _attribute_array(attribute, width=1)]
        if len(values) < curve_count:
            values.extend([0] * (curve_count - len(values)))
        elif len(values) > curve_count:
            values = values[:curve_count]
        for offset, stable_id in enumerate(new_ids):
            values[start_index + offset] = int(stable_id)
        _set_attribute_array(attribute, values, width=1)

    values = [int(value) for value in _attribute_array(attribute, width=1)]
    _sync_point_ids_from_curve_values(curves_data, values)
    curves_data[WORLD_PAINT_STABLE_IDS_READY_PROP] = True
    return new_ids


def ensure_secret_paint_system_stable_ids(context, system_obj):
    if not _is_secret_paint_system(system_obj):
        return []
    stable_curve_values = _ensure_stable_curve_ids(context, system_obj)
    try:
        shared.ensure_secret_paint_system_stable_root_positions(system_obj, stable_curve_values)
    except Exception:
        pass
    return stable_curve_values


def ensure_secret_paint_scene_stable_ids(context=None, *, scene=None, systems=None):
    sync_context = context if context is not None else bpy.context
    target_systems = systems if systems is not None else _iter_secret_paint_systems(scene=scene)
    synced = []
    for system_obj in target_systems:
        if not _is_secret_paint_system(system_obj):
            continue
        try:
            ensure_secret_paint_system_stable_ids(sync_context, system_obj)
            synced.append(system_obj)
        except Exception:
            continue
    return synced


def _sync_stable_ids_for_updated_systems(scene=None, depsgraph=None):
    if _WORLD_STATE.get("stable_id_sync_running"):
        return []

    target_systems = []
    full_scene_scan = depsgraph is None
    if depsgraph is not None:
        try:
            for update in depsgraph.updates:
                datablock = getattr(update.id, "original", update.id)
                identifier = getattr(getattr(datablock, "bl_rna", None), "identifier", "")
                if identifier == "Object" and _is_secret_paint_system(datablock):
                    target_systems.append(datablock)
                elif identifier == "Curves":
                    full_scene_scan = True
                    break
        except Exception:
            full_scene_scan = True

    if full_scene_scan:
        target_systems = list(_iter_secret_paint_systems(scene=scene))
    elif target_systems:
        target_systems = list(dict.fromkeys(target_systems))
    else:
        return []

    _WORLD_STATE["stable_id_sync_running"] = True
    try:
        return ensure_secret_paint_scene_stable_ids(
            bpy.context,
            scene=scene,
            systems=target_systems,
        )
    finally:
        _WORLD_STATE["stable_id_sync_running"] = False


def _remove_stable_ids_load_handlers():
    for handler in list(bpy.app.handlers.load_post):
        if getattr(handler, "__name__", "") != "_stable_ids_on_load_post":
            continue
        if not getattr(handler, "__module__", "").endswith("secret_paint_world_paint"):
            continue
        try:
            bpy.app.handlers.load_post.remove(handler)
        except Exception:
            pass


def _stable_ids_auto_sync_allowed():
    operator = _world_operator()
    if operator is not None:
        return bool(
            getattr(operator, "stroke_active", False) or
            getattr(operator, "_primary_paint_button_down", False)
        )
    mode = getattr(bpy.context, "mode", "") or ""
    object_mode = getattr(getattr(bpy.context, "object", None), "mode", "") or ""
    paint_modes = {'SCULPT_CURVES', 'PAINT_WEIGHT', 'WEIGHT_PAINT', 'EDIT', 'EDIT_CURVE', 'EDIT_CURVES'}
    return mode in paint_modes or object_mode in paint_modes


@persistent
def _stable_ids_on_depsgraph_update_post(scene, depsgraph):
    _enforce_world_paint_object_mode_guard(bpy.context)
    if not _stable_ids_auto_sync_allowed():
        return
    _sync_stable_ids_for_updated_systems(scene=scene, depsgraph=depsgraph)


def _default_curve_length(system_obj):
    return max(0.03, _modifier_scale_value(system_obj) * 0.25)


def _surface_basis(normal):
    normal = normal.normalized()
    axis = Vector((0.0, 0.0, 1.0))
    tangent = axis.cross(normal)
    if tangent.length < 0.0001:
        tangent = Vector((1.0, 0.0, 0.0))
    tangent.normalize()
    bitangent = normal.cross(tangent).normalized()
    return tangent, bitangent, normal


def _evaluated_surface_object(context, surface_obj):
    if surface_obj is None or surface_obj.type != "MESH":
        return None
    try:
        depsgraph = context.evaluated_depsgraph_get()
        return surface_obj.evaluated_get(depsgraph)
    except Exception:
        return None


def _snap_point_to_surface(context, surface_obj, candidate_world, *, eval_surface=None):
    eval_obj = eval_surface if eval_surface is not None else _evaluated_surface_object(context, surface_obj)
    if eval_obj is None:
        return None, None
    local_candidate = eval_obj.matrix_world.inverted() @ candidate_world
    try:
        hit, location, normal, _index = eval_obj.closest_point_on_mesh(local_candidate, distance=1.0e12)
    except TypeError:
        hit, location, normal, _index = eval_obj.closest_point_on_mesh(local_candidate)
    except Exception:
        return None, None

    if not hit:
        return None, None

    normal_world = eval_obj.matrix_world.to_3x3() @ normal
    if normal_world.length > 0:
        normal_world.normalize()
    return eval_obj.matrix_world @ location, normal_world


def _stabilize_target_info(context, target_info):
    if not target_info:
        return target_info

    surface_obj = target_info.get("surface_obj")
    candidate_world = target_info.get("location")
    if surface_obj is None or getattr(surface_obj, "type", "") != "MESH" or candidate_world is None:
        return target_info

    snapped_location, snapped_normal = _snap_point_to_surface(context, surface_obj, candidate_world)
    if snapped_location is not None:
        target_info["location"] = snapped_location
    if snapped_normal is not None and snapped_normal.length > 0:
        target_info["normal"] = snapped_normal
    return target_info


def _target_depth_anchor(target_info, *fallback_targets):
    if not target_info:
        return None

    anchor = target_info.get("_depth_anchor")
    if anchor is not None:
        anchor_copy = _safe_copy_target_vector(anchor)
        if anchor_copy is not None:
            return anchor_copy

    target_key = _target_key(target_info)
    for fallback_target in fallback_targets:
        if not fallback_target or _target_key(fallback_target) != target_key:
            continue
        anchor = fallback_target.get("_depth_anchor")
        if anchor is None:
            continue
        anchor_copy = _safe_copy_target_vector(anchor)
        if anchor_copy is None:
            continue
        target_info["_depth_anchor"] = anchor_copy
        return anchor_copy.copy()

    location = target_info.get("location")
    if location is not None:
        anchor = _safe_copy_target_vector(location)
        if anchor is not None:
            target_info["_depth_anchor"] = anchor
            return anchor.copy()

    surface_obj = target_info.get("surface_obj") or target_info.get("target_owner")
    if surface_obj is not None:
        anchor = _safe_object_world_translation(surface_obj)
        if anchor is not None:
            target_info["_depth_anchor"] = anchor
            return anchor.copy()

    return None


def _system_curve_world_data(system_obj):
    cache_key = _system_cache_key(system_obj)
    revision = _system_cache_revision(system_obj)
    cached = _WORLD_STATE.get("curve_data_cache", {}).get(cache_key)
    if cached is not None and cached.get("revision") == revision and not cached.get("root_only"):
        return cached["value"]

    curves_data = system_obj.data
    position_data = getattr(curves_data, "position_data", None)
    if position_data is None:
        return [], [], [], [], []

    positions = _attribute_array(position_data, width=3)
    offsets = _curves_offsets(curves_data)
    roots = []
    tips = []
    lengths = []
    inv = system_obj.matrix_world

    for curve_index in range(len(curves_data.curves)):
        start = offsets[curve_index]
        end = offsets[curve_index + 1]
        if end <= start or end * 3 > len(positions):
            roots.append(None)
            tips.append(None)
            lengths.append(0.0)
            continue
        root_local = Vector(positions[start * 3:start * 3 + 3])
        tip_local = Vector(positions[(end - 1) * 3:(end - 1) * 3 + 3])
        root_world = inv @ root_local
        tip_world = inv @ tip_local
        roots.append(root_world)
        tips.append(tip_world)
        lengths.append((tip_world - root_world).length)
    result = (offsets, positions, roots, tips, lengths)
    if cache_key is not None:
        _WORLD_STATE.setdefault("curve_data_cache", {})[cache_key] = {
            "revision": revision,
            "value": result,
        }
    return result


def _compact_system_root_cache_after_remove(system_obj, removed_indices):
    cache_key = _system_cache_key(system_obj)
    if cache_key is None:
        return False
    cache = _WORLD_STATE.setdefault("curve_data_cache", {}).get(cache_key)
    if cache is None or not removed_indices:
        return False
    value = cache.get("value")
    if not value or len(value) < 5:
        return False

    removed = set(removed_indices)
    offsets, positions, roots, tips, lengths = value

    def compact_sequence(sequence):
        if not isinstance(sequence, list):
            return []
        return [item for index, item in enumerate(sequence) if index not in removed]

    cache["value"] = (
        [],
        [],
        compact_sequence(roots),
        compact_sequence(tips),
        compact_sequence(lengths),
    )
    cache["root_only"] = True
    cache["root_grid"] = None
    cache.pop("root_grid_cell_size", None)
    return True


def _curve_query_cell_size(system_obj):
    modifier = _secret_modifier(system_obj)
    if modifier is not None:
        try:
            return max(0.02, float(modifier.get("Socket_11", 0.1)))
        except Exception:
            pass
    return 0.1


def _spatial_cell_key(location, cell_size):
    if location is None:
        return None
    inv = 1.0 / max(cell_size, 1.0e-6)
    return (
        int(math.floor(location.x * inv)),
        int(math.floor(location.y * inv)),
        int(math.floor(location.z * inv)),
    )


def _system_root_spatial_index(system_obj):
    cache_key = _system_cache_key(system_obj)
    revision = _system_cache_revision(system_obj)
    cache = _WORLD_STATE.setdefault("curve_data_cache", {}).get(cache_key)
    if cache is None or cache.get("revision") != revision:
        _system_curve_world_data(system_obj)
        cache = _WORLD_STATE.setdefault("curve_data_cache", {}).get(cache_key)
    if cache is None:
        return None, []

    grid = cache.get("root_grid")
    grid_cell_size = cache.get("root_grid_cell_size")
    roots = cache.get("value", ([], [], [], [], []))[2] if cache.get("value") else []
    desired_cell_size = _curve_query_cell_size(system_obj)
    if grid is not None and grid_cell_size == desired_cell_size:
        return grid, roots

    grid = {}
    for curve_index, root_world in enumerate(roots):
        if root_world is None:
            continue
        cell_key = _spatial_cell_key(root_world, desired_cell_size)
        if cell_key is None:
            continue
        grid.setdefault(cell_key, []).append(curve_index)

    cache["root_grid"] = grid
    cache["root_grid_cell_size"] = desired_cell_size
    return grid, roots


def _candidate_curve_indices_in_radius(system_obj, center_world, radius):
    grid, roots = _system_root_spatial_index(system_obj)
    if grid is None or center_world is None:
        return [], roots

    cell_size = _curve_query_cell_size(system_obj)
    min_corner = center_world - Vector((radius, radius, radius))
    max_corner = center_world + Vector((radius, radius, radius))
    min_key = _spatial_cell_key(min_corner, cell_size)
    max_key = _spatial_cell_key(max_corner, cell_size)
    if min_key is None or max_key is None:
        return [], roots

    found_indices = set()
    for grid_x in range(min_key[0], max_key[0] + 1):
        for grid_y in range(min_key[1], max_key[1] + 1):
            for grid_z in range(min_key[2], max_key[2] + 1):
                found_indices.update(grid.get((grid_x, grid_y, grid_z), ()))
    return list(found_indices), roots


def _curves_in_brush(system_obj, center_world, radius):
    candidate_indices, roots = _candidate_curve_indices_in_radius(system_obj, center_world, radius)
    found = []
    for curve_index in candidate_indices:
        if curve_index >= len(roots):
            continue
        root_world = roots[curve_index]
        if root_world is None:
            continue
        distance = (root_world - center_world).length
        if distance <= radius:
            found.append((curve_index, distance))
    return found


def _curve_roots_in_brush(system_obj, center_world, radius):
    candidate_indices, roots = _candidate_curve_indices_in_radius(system_obj, center_world, radius)
    found = []
    for curve_index in candidate_indices:
        if curve_index >= len(roots):
            continue
        root_world = roots[curve_index]
        if root_world is None:
            continue
        distance = (root_world - center_world).length
        if distance <= radius:
            found.append({
                "curve_index": curve_index,
                "location": root_world,
                "distance": distance,
            })
    return found


def _nearest_point_distance(point, points):
    if point is None or not points:
        return float("inf")
    return min((other - point).length for other in points if other is not None)


def _nearest_point_distance_in_grid(point, grid, cell_size, *, ignore_index=None):
    if point is None or not grid:
        return float("inf")
    cell_size = max(cell_size, 0.001)
    center_key = _spatial_cell_key(point, cell_size)
    if center_key is None:
        return float("inf")

    best_distance = float("inf")
    search_radius = 1
    while search_radius <= 2:
        for grid_x in range(center_key[0] - search_radius, center_key[0] + search_radius + 1):
            for grid_y in range(center_key[1] - search_radius, center_key[1] + search_radius + 1):
                for grid_z in range(center_key[2] - search_radius, center_key[2] + search_radius + 1):
                    for other_index, other in grid.get((grid_x, grid_y, grid_z), ()):
                        if ignore_index is not None and other_index == ignore_index:
                            continue
                        distance = (other - point).length
                        if distance < best_distance:
                            best_distance = distance
        if best_distance < float("inf"):
            break
        search_radius += 1
    return best_distance


def _crowded_curve_indices(found_items, remove_count, *, crowding_threshold=0.0):
    if remove_count <= 0 or not found_items:
        return []

    remaining = list(found_items)
    removed = []

    while remove_count > 0 and remaining:
        cell_size = crowding_threshold if crowding_threshold > 0.0 else 0.05
        grid = {}
        for item_index, item in enumerate(remaining):
            point = item.get("location")
            if point is None:
                continue
            cell_key = _spatial_cell_key(point, cell_size)
            if cell_key is None:
                continue
            grid.setdefault(cell_key, []).append((item_index, point))

        chosen_index = None
        chosen_score = (float("inf"), float("-inf"))

        for item_index, item in enumerate(remaining):
            nearest_neighbor = _nearest_point_distance_in_grid(
                item.get("location"),
                grid,
                cell_size,
                ignore_index=item_index,
            )
            if crowding_threshold > 0.0 and nearest_neighbor >= crowding_threshold:
                continue
            score = (nearest_neighbor, -item.get("distance", 0.0))
            if score < chosen_score:
                chosen_score = score
                chosen_index = item_index

        if chosen_index is None:
            break
        removed.append(remaining.pop(chosen_index)["curve_index"])
        remove_count -= 1

    return removed


def _write_curve_selection(curves_data, selected_curve_indices, *, deselect=False):
    selection_attr = _ensure_attribute(curves_data, WORLD_PAINT_SELECTION_ATTR, 'BOOLEAN', 'CURVE')
    data = _attribute_collection(selection_attr)
    values = [False] * len(data)
    if not deselect and values:
        data.foreach_get("value", values)
    for curve_index in selected_curve_indices:
        if 0 <= curve_index < len(values):
            values[curve_index] = not deselect
    data.foreach_set("value", values)


def _add_curves_to_system(context, system_obj, samples):
    if not samples:
        return

    curves_data = system_obj.data
    _ensure_stable_curve_ids(context, system_obj)
    curve_count_before = len(curves_data.curves)
    curves_data.add_curves([2] * len(samples))

    position_data = getattr(curves_data, "position_data", None)
    if position_data is None:
        return
    radius_attr = _ensure_attribute(curves_data, "radius", 'FLOAT', 'POINT')
    selection_attr = _ensure_attribute(curves_data, WORLD_PAINT_SELECTION_ATTR, 'BOOLEAN', 'CURVE')
    positions = _attribute_array(position_data, width=3)
    radii = _attribute_array(radius_attr, width=1)
    selection = _attribute_array(selection_attr, width=1)
    offsets = _curves_offsets(curves_data)
    inv = system_obj.matrix_world.inverted()

    needed_points = len(curves_data.points) * 3
    if len(positions) < needed_points:
        positions.extend([0.0] * (needed_points - len(positions)))
    if len(radii) < len(curves_data.points):
        radii.extend([0.0] * (len(curves_data.points) - len(radii)))
    if len(selection) < len(curves_data.curves):
        selection.extend([False] * (len(curves_data.curves) - len(selection)))
    _append_stable_curve_ids(curves_data, curve_count_before, len(samples))

    for sample_index, sample in enumerate(samples):
        curve_index = curve_count_before + sample_index
        start = offsets[curve_index]
        root_world = sample["location"]
        normal_world = sample["normal"]
        length = sample.get("length", _default_curve_length(system_obj))
        tip_world = root_world + normal_world * length
        root_local = inv @ root_world
        tip_local = inv @ tip_world

        z_rotation = sample.get("z_rotation", 0.0)
        positions[start * 3:start * 3 + 3] = [root_local.x, root_local.y, root_local.z]
        positions[(start + 1) * 3:(start + 1) * 3 + 3] = [tip_local.x, tip_local.y, tip_local.z]
        radii[start] = z_rotation
        radii[start + 1] = z_rotation
        selection[curve_index] = False

    _set_attribute_array(position_data, positions, width=3)
    _set_attribute_array(radius_attr, radii, width=1)
    _set_attribute_array(selection_attr, selection, width=1)
    try:
        shared.ensure_secret_paint_system_stable_root_positions(system_obj)
    except Exception:
        pass
    _set_system_enabled(system_obj, True)
    _mark_system_curve_cache_dirty(system_obj)
    curves_data.update_tag()
    _maybe_refresh_live_view(context)


def _remove_curves_from_system(context, system_obj, curve_indices, *, refresh=True, preserve_root_cache=False):
    if not curve_indices:
        return
    _ensure_stable_curve_ids(context, system_obj)
    curves_data = system_obj.data
    try:
        migrated_curve_count_before = int(curves_data.get(WORLD_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP, 0) or 0)
    except Exception:
        migrated_curve_count_before = 0
    curve_count = len(system_obj.data.curves)
    requested_indices = sorted(set(curve_indices))
    unique_indices = [index for index in requested_indices if 0 <= index < curve_count]
    if len(unique_indices) != len(requested_indices):
        _mark_system_curve_cache_dirty(system_obj)
    if not unique_indices:
        return
    try:
        system_obj.data.remove_curves(indices=unique_indices)
    except TypeError:
        try:
            system_obj.data.remove_curves(unique_indices)
        except RuntimeError:
            curve_count = len(system_obj.data.curves)
            retry_indices = [index for index in unique_indices if 0 <= index < curve_count]
            _mark_system_curve_cache_dirty(system_obj)
            if not retry_indices:
                return
            try:
                system_obj.data.remove_curves(retry_indices)
            except RuntimeError:
                return
            unique_indices = retry_indices
    except RuntimeError:
        curve_count = len(system_obj.data.curves)
        retry_indices = [index for index in unique_indices if 0 <= index < curve_count]
        _mark_system_curve_cache_dirty(system_obj)
        if not retry_indices:
            return
        try:
            system_obj.data.remove_curves(indices=retry_indices)
            unique_indices = retry_indices
        except TypeError:
            try:
                system_obj.data.remove_curves(retry_indices)
            except RuntimeError:
                return
            unique_indices = retry_indices
        except RuntimeError:
            return
    if migrated_curve_count_before > 0:
        removed_migrated_count = sum(1 for index in unique_indices if index < migrated_curve_count_before)
        if removed_migrated_count:
            migrated_curve_count = max(0, migrated_curve_count_before - removed_migrated_count)
            migrated_curve_count = min(migrated_curve_count, len(system_obj.data.curves))
            try:
                system_obj.data[WORLD_PAINT_STABLE_IDS_MIGRATED_CURVE_COUNT_PROP] = int(migrated_curve_count)
            except Exception:
                pass
    try:
        shared.ensure_secret_paint_system_stable_root_positions(system_obj)
    except Exception:
        pass
    if _system_curve_count(system_obj) > 0:
        _set_system_enabled(system_obj, True)
    if not (preserve_root_cache and _compact_system_root_cache_after_remove(system_obj, unique_indices)):
        _mark_system_curve_cache_dirty(system_obj)
    system_obj.data.update_tag()
    if refresh:
        _maybe_refresh_live_view(context)


def _update_curve_positions(context, system_obj, updates, *, z_rotation_updates=None, selection_mode=None):
    if not updates and not z_rotation_updates and selection_mode is None:
        return

    curves_data = system_obj.data
    position_data = getattr(curves_data, "position_data", None)
    if position_data is None:
        return
    _ensure_stable_curve_ids(context, system_obj)

    offsets = _curves_offsets(curves_data)
    positions = _attribute_array(position_data, width=3)
    inv = system_obj.matrix_world.inverted()

    for curve_index, curve_update in updates.items():
        if curve_index >= len(curves_data.curves):
            continue
        start = offsets[curve_index]
        end = offsets[curve_index + 1]
        if end <= start:
            continue
        root_local = inv @ curve_update["root"]
        tip_local = inv @ curve_update["tip"]
        positions[start * 3:start * 3 + 3] = [root_local.x, root_local.y, root_local.z]
        positions[(end - 1) * 3:(end - 1) * 3 + 3] = [tip_local.x, tip_local.y, tip_local.z]

    _set_attribute_array(position_data, positions, width=3)

    if z_rotation_updates:
        radius_attr = _ensure_attribute(curves_data, "radius", 'FLOAT', 'POINT')
        radii = _attribute_array(radius_attr, width=1)
        for curve_index, value in z_rotation_updates.items():
            if curve_index >= len(curves_data.curves):
                continue
            start = offsets[curve_index]
            end = offsets[curve_index + 1]
            for point_index in range(start, end):
                radii[point_index] = value
        _set_attribute_array(radius_attr, radii, width=1)

    if selection_mode is not None:
        curve_indices = list(selection_mode["indices"])
        _write_curve_selection(curves_data, curve_indices, deselect=selection_mode["deselect"])

    _mark_system_curve_cache_dirty(system_obj)
    curves_data.update_tag()
    _maybe_refresh_live_view(context)


def _safe_rna_name(datablock):
    if datablock is None:
        return ""
    try:
        return datablock.name
    except (ReferenceError, RuntimeError):
        return ""


def _safe_object_type(obj):
    if obj is None:
        return ""
    try:
        return getattr(obj, "type", "")
    except (ReferenceError, RuntimeError):
        return ""


def _safe_object_world_translation(obj):
    if obj is None:
        return None
    name = _safe_rna_name(obj)
    if not name:
        return None
    try:
        if bpy.data.objects.get(name) is not obj:
            return None
    except (ReferenceError, RuntimeError):
        return None
    except Exception:
        pass
    try:
        translation = obj.matrix_world.translation
        return Vector((float(translation[0]), float(translation[1]), float(translation[2])))
    except (ReferenceError, RuntimeError):
        return None
    except Exception:
        return None


def _safe_copy_target_vector(value):
    if value is None:
        return None
    try:
        if getattr(value, "is_wrapped", False):
            return None
    except (ReferenceError, RuntimeError):
        return None
    except Exception:
        pass
    try:
        return Vector((float(value[0]), float(value[1]), float(value[2])))
    except (ReferenceError, RuntimeError):
        return None
    except Exception:
        return None


def _target_key(target_info):
    if not target_info:
        return ""
    surface_obj = target_info.get("surface_obj")
    owner = target_info.get("target_owner")
    return "|".join((
        target_info.get("kind", ""),
        _safe_rna_name(surface_obj),
        _safe_rna_name(owner),
    ))


def _world_target_key_from_parts(target_kind, surface_obj, target_owner=None):
    owner = target_owner if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE else surface_obj
    return "|".join((
        target_kind or "",
        _safe_rna_name(surface_obj),
        _safe_rna_name(owner),
    ))


def _world_target_key_from_system(system_obj):
    if system_obj is None:
        return ""
    target_kind = system_obj.get(WORLD_PAINT_TARGET_KIND_PROP, WORLD_TARGET_KIND_MESH)
    surface_obj = _system_surface_object(system_obj)
    target_owner = None
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
        target_owner = bpy.data.objects.get(system_obj.get(WORLD_PAINT_TARGET_OWNER_PROP, ""))
    return _world_target_key_from_parts(target_kind, surface_obj, target_owner)


def _target_info_contains_removed_references(target_info):
    if not target_info:
        return False
    for key in ("surface_obj", "target_owner", "hover_object"):
        obj = target_info.get(key)
        if obj is not None and not _safe_rna_name(obj):
            return True
    return False


def _target_label(target_info):
    if not target_info:
        return "No Surface"
    owner = target_info.get("target_owner")
    owner_name = _safe_rna_name(owner)
    if not owner_name:
        return "No Surface"
    if target_info.get("kind") == WORLD_TARGET_KIND_SECRET_INSTANCE:
        return f"Target: {owner_name}"
    return f"Surface: {owner_name}"


def _world_source_label_info(source_data):
    if not source_data:
        return "(empty)", 'OBJECT_DATA'

    brush_collection = source_data.get("brush_collection")
    if brush_collection is not None:
        collection_name = _safe_rna_name(brush_collection)
        if collection_name:
            return collection_name, 'OUTLINER_COLLECTION'

    brush_object = source_data.get("brush_object")
    if brush_object is not None:
        brush_object_name = _safe_rna_name(brush_object)
        if brush_object_name:
            if _safe_object_type(brush_object) == "EMPTY":
                return brush_object_name, 'EMPTY_AXIS'
            return brush_object_name, 'OBJECT_DATA'

    return "(empty)", 'OBJECT_DATA'


def _world_surface_label(operator):
    locked_targets = _operator_locked_target_infos(operator) if operator.surface_lock else []
    if len(locked_targets) > 1:
        return f"Surface: {len(locked_targets)} Terrains"
    target_info = locked_targets[0] if locked_targets else operator.hover_target
    target_label = _target_label(target_info)
    if target_label == "No Surface":
        return "Surface: -"
    return target_label


def _world_surface_name(operator):
    locked_targets = _operator_locked_target_infos(operator) if operator.surface_lock else []
    if len(locked_targets) > 1:
        return f"{len(locked_targets)} Terrains"
    target_info = locked_targets[0] if locked_targets else operator.hover_target
    if not target_info:
        return "-"
    owner = target_info.get("target_owner")
    owner_name = _safe_rna_name(owner)
    if not owner_name:
        return "-"
    return owner_name


def _world_flag_button_label(flag_id, fallback_label):
    if flag_id == "LOCK_SURFACE":
        return "Lock Terrain"
    if flag_id == "TARGET_SURFACE":
        return "Target"
    if flag_id == "ALLOW_WIRE_BOUNDS_SURFACES":
        return "Wire"
    if flag_id == "INTERPOLATE":
        return "Interpolate"
    if flag_id == "RANDOM_Z":
        return "Random Z"
    if flag_id == "ALIGN_TO_NORMAL":
        return "Normal"
    return fallback_label


def _world_flag_is_enabled(operator, flag_id):
    if flag_id == "LOCK_SURFACE":
        return operator.surface_lock
    if flag_id == "TARGET_SURFACE":
        return operator.current_target_surface_toggle()
    if flag_id == "ALLOW_WIRE_BOUNDS_SURFACES":
        return operator.allow_wire_bounds_surfaces
    if flag_id == "INTERPOLATE":
        return operator.interpolate
    if flag_id == "RANDOM_Z":
        return operator.random_z
    if flag_id == "ALIGN_TO_NORMAL":
        return operator.align_to_normal
    return False


def _preview_target_info(operator, *, live=False, context=None):
    if getattr(operator, "surface_lock", False):
        locked_targets = _operator_locked_target_infos(operator)
        if locked_targets:
            return getattr(operator, "locked_target", None) or locked_targets[0]
    preview_target = getattr(operator, "preview_target", None)
    if preview_target is not None:
        return preview_target
    return getattr(operator, "hover_target", None)


def _viewport_navigation_state_key(operator, context=None):
    base_context = context if context is not None else getattr(bpy, "context", None)
    if base_context is None:
        return None

    area, _region, space = _view3d_area_data(base_context, getattr(operator, "_invoke_area_pointer", 0))
    region_3d = getattr(space, "region_3d", None) if space is not None else None
    if region_3d is None:
        region_3d = getattr(getattr(base_context, "space_data", None), "region_3d", None)
    if region_3d is None:
        return None

    def _rounded_tuple(values, digits=5):
        rounded = []
        for value in values:
            try:
                rounded.append(round(float(value), digits))
            except Exception:
                rounded.append(value)
        return tuple(rounded)

    try:
        return (
            _rounded_tuple(region_3d.view_location),
            _rounded_tuple(region_3d.view_rotation),
            round(float(region_3d.view_distance), 5),
            round(float(region_3d.view_camera_zoom), 5),
            _rounded_tuple(region_3d.view_camera_offset),
            getattr(region_3d, "view_perspective", ""),
        )
    except Exception:
        return None


def _hide_preview_for_viewport_navigation(operator, *, context=None):
    return bool(getattr(operator, "_viewport_navigation_active", False))


def _is_viewport_navigation_event(event):
    if event.type in {
        'MIDDLEMOUSE',
        'TRACKPADPAN',
        'TRACKPADZOOM',
        'MOUSEROTATE',
        'MOUSESMARTZOOM',
        'NDOF_MOTION',
    }:
        return True
    return event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and bool(getattr(event, "alt", False))


def _is_passive_idle_passthrough_event(event):
    event_type = getattr(event, "type", "")
    if event_type in {
        'MOUSEMOVE',
        'INBETWEEN_MOUSEMOVE',
        'MIDDLEMOUSE',
        'WHEELUPMOUSE',
        'WHEELDOWNMOUSE',
        'WHEELINMOUSE',
        'WHEELOUTMOUSE',
        'TRACKPADPAN',
        'TRACKPADZOOM',
        'MOUSEROTATE',
        'MOUSESMARTZOOM',
        'NDOF_MOTION',
    }:
        return True
    return event_type in {'LEFTMOUSE', 'RIGHTMOUSE'} and bool(getattr(event, "alt", False))


def _viewport_navigation_event_holds_input(event):
    if event.type == 'MIDDLEMOUSE':
        return True
    return event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and bool(getattr(event, "alt", False))


def _target_match_for_system(system_obj, source_data, target_info):
    if system_obj is None or target_info is None:
        return False
    target_kind = target_info.get("kind", WORLD_TARGET_KIND_MESH)
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE and not _world_target_surface_feature_enabled():
        return False
    target_owner = target_info.get("target_owner")
    surface_obj = target_info.get("surface_obj")
    matching_system = _matching_world_system(
        surface_obj,
        source_data,
        target_kind=target_kind,
        target_owner=target_owner if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE else None,
    )
    return matching_system == system_obj


def _target_info_from_system(context, system_obj, *, allow_wire_bounds_surfaces=False, ignore_display_type_block=False):
    if system_obj is None:
        return None
    allow_blocked_display = bool(allow_wire_bounds_surfaces or ignore_display_type_block)
    target_kind = system_obj.get(WORLD_PAINT_TARGET_KIND_PROP, WORLD_TARGET_KIND_MESH)
    if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
        if not _world_target_surface_feature_enabled():
            return None
        target_owner = bpy.data.objects.get(system_obj.get(WORLD_PAINT_TARGET_OWNER_PROP, ""))
        if target_owner is None:
            return None
        if _world_paint_display_type_blocked(
            target_owner,
            allow_wire_bounds_surfaces=allow_blocked_display,
        ):
            return None
        proxy = _ensure_proxy_surface(context, target_owner)
        if proxy is None:
            return None
        location = _safe_object_world_translation(target_owner)
        if location is None:
            return None
        target_info = {
            "kind": WORLD_TARGET_KIND_SECRET_INSTANCE,
            "target_owner": target_owner,
            "surface_obj": proxy,
            "hover_object": target_owner,
            "location": location,
            "normal": Vector((0.0, 0.0, 1.0)),
        }
        if ignore_display_type_block:
            target_info["_ignore_display_type_block"] = True
        return target_info

    surface_obj = _system_surface_object(system_obj)
    if surface_obj is None:
        return None
    if _world_paint_display_type_blocked(
        surface_obj,
        allow_wire_bounds_surfaces=allow_blocked_display,
    ):
        return None
    location = _safe_object_world_translation(surface_obj)
    if location is None:
        return None
    target_info = {
        "kind": WORLD_TARGET_KIND_MESH,
        "target_owner": surface_obj,
        "surface_obj": surface_obj,
        "hover_object": surface_obj,
        "location": location,
        "normal": Vector((0.0, 0.0, 1.0)),
    }
    if ignore_display_type_block:
        target_info["_ignore_display_type_block"] = True
    return target_info


def _brush_preview_radius(operator):
    return max(WORLD_MIN_OPERATION_RADIUS, getattr(operator, "brush_radius", WORLD_MIN_OPERATION_RADIUS))


def _screen_brush_radius_pixels(screen_radius):
    try:
        radius_px = max(0.05, float(screen_radius)) * WORLD_SCREEN_BRUSH_RADIUS_SCALE
    except (TypeError, ValueError):
        radius_px = 5.0
    if not math.isfinite(radius_px):
        radius_px = 5.0
    return max(1.0, radius_px)


def _preview_uses_2d_ui(operator):
    context = getattr(bpy, "context", None)
    if context is not None:
        try:
            preferences = _addon_preferences(context)
            if preferences is not None:
                return bool(getattr(preferences, "always_use_2d_world_paint_brush_ui", False))
        except Exception:
            pass
    return bool(getattr(operator, "always_use_2d_world_paint_brush_ui", False))


def _density_spacing_value(value, fallback=0.1):
    try:
        value = float(value)
    except Exception:
        try:
            value = float(fallback)
        except Exception:
            value = WORLD_DENSITY_SPACING_EPSILON
    if not math.isfinite(value):
        try:
            value = float(fallback)
        except Exception:
            value = WORLD_DENSITY_SPACING_EPSILON
    return max(WORLD_DENSITY_SPACING_EPSILON, value)


def _brush_strength_value(value, fallback=1.0):
    try:
        value = float(value)
    except Exception:
        try:
            value = float(fallback)
        except Exception:
            value = 1.0
    if not math.isfinite(value):
        try:
            value = float(fallback)
        except Exception:
            value = 1.0
    return min(1.0, max(0.0, value))


def _density_target_count(radius, spacing):
    spacing = _density_spacing_value(spacing)
    return max(1, int(round((math.pi * (radius ** 2)) / (spacing ** 2))))


def _density_operation_radius(radius, spacing):
    radius = max(WORLD_MIN_OPERATION_RADIUS, float(radius))
    spacing = _density_spacing_value(spacing)
    edge_buffer = max(radius * 0.14, spacing * 0.9)
    edge_buffer = min(edge_buffer, radius * 0.24)
    return max(radius * 0.76, radius - edge_buffer)


def _stable_preview_basis(operator, normal):
    normal = normal.normalized()
    reference_vectors = []
    preview_target = _preview_target_info(operator) or {}
    surface_obj = preview_target.get("surface_obj")

    if surface_obj is not None:
        try:
            basis = surface_obj.matrix_world.to_3x3()
            reference_vectors.extend((
                basis.col[0].copy(),
                basis.col[1].copy(),
                basis.col[2].copy(),
            ))
        except Exception:
            pass

    reference_vectors.extend((
        Vector((1.0, 0.0, 0.0)),
        Vector((0.0, 1.0, 0.0)),
        Vector((0.0, 0.0, 1.0)),
    ))

    best_tangent = None
    best_length = 0.0
    for reference_vector in reference_vectors:
        projected = reference_vector - normal * reference_vector.dot(normal)
        projected_length = projected.length
        if projected_length > best_length:
            best_tangent = projected
            best_length = projected_length

    if best_tangent is None or best_length < 0.0001:
        return _surface_basis(normal)

    best_tangent.normalize()
    bitangent = normal.cross(best_tangent)
    if bitangent.length < 0.0001:
        return _surface_basis(normal)
    bitangent.normalize()
    return best_tangent, bitangent, normal


def _density_preview_vertices(operator, center, normal, radius):
    if operator.adjust_mode != "STRENGTH" or operator.stroke_active:
        return []

    tangent, bitangent, normal = _stable_preview_basis(operator, normal)
    spacing = _density_spacing_value(operator.density_spacing)
    grid_extent = max(1, int(math.ceil(radius / spacing)))
    preview_vertices = []
    preview_offset = normal * 0.0025
    radius_squared = radius * radius

    for row in range(-grid_extent, grid_extent + 1):
        for column in range(-grid_extent, grid_extent + 1):
            offset = tangent * (column * spacing) + bitangent * (row * spacing)
            if offset.length_squared > radius_squared:
                continue
            preview_vertices.append(center + preview_offset + offset)

    if len(preview_vertices) <= 1 and spacing > radius:
        for column, row in WORLD_DENSITY_PREVIEW_SPARSE_RING_OFFSETS:
            offset = tangent * (column * spacing) + bitangent * (row * spacing)
            preview_vertices.append(center + preview_offset + offset)

    return preview_vertices


def _density_preview_square_triangles(operator, center, normal, radius):
    preview_vertices = _density_preview_vertices(operator, center, normal, radius)
    if not preview_vertices:
        return []

    tangent, bitangent, _normal = _stable_preview_basis(operator, normal)
    square_half_extent = max(radius * 0.02, min(operator.density_spacing * 0.35, radius * 0.08))
    triangle_vertices = []

    for preview_vertex in preview_vertices:
        corner_a = preview_vertex - tangent * square_half_extent - bitangent * square_half_extent
        corner_b = preview_vertex + tangent * square_half_extent - bitangent * square_half_extent
        corner_c = preview_vertex + tangent * square_half_extent + bitangent * square_half_extent
        corner_d = preview_vertex - tangent * square_half_extent + bitangent * square_half_extent
        triangle_vertices.extend((
            corner_a,
            corner_b,
            corner_c,
            corner_a,
            corner_c,
            corner_d,
        ))

    return triangle_vertices


def _density_preview_solid_triangles_2d(center_x, center_y, radius_px, region=None):
    if region is not None:
        width = float(getattr(region, "width", 0.0))
        height = float(getattr(region, "height", 0.0))
        farthest_corner_distance = max(
            math.hypot(corner_x - center_x, corner_y - center_y)
            for corner_x, corner_y in ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height))
        )
        if radius_px >= farthest_corner_distance:
            return [
                (0.0, 0.0),
                (width, 0.0),
                (width, height),
                (0.0, 0.0),
                (width, height),
                (0.0, height),
            ]

    triangle_vertices = []
    center = (center_x, center_y)
    for index in range(WORLD_DENSITY_PREVIEW_SOLID_STEPS):
        angle_a = (index / WORLD_DENSITY_PREVIEW_SOLID_STEPS) * math.tau
        angle_b = ((index + 1) / WORLD_DENSITY_PREVIEW_SOLID_STEPS) * math.tau
        triangle_vertices.extend((
            center,
            (center_x + math.cos(angle_a) * radius_px, center_y + math.sin(angle_a) * radius_px),
            (center_x + math.cos(angle_b) * radius_px, center_y + math.sin(angle_b) * radius_px),
        ))
    return triangle_vertices


def _density_preview_square_triangles_2d(operator, center_x, center_y, radius_px, region=None):
    if operator.adjust_mode != "STRENGTH" or operator.stroke_active:
        return [], False

    world_radius = _brush_preview_radius(operator)
    spacing_ratio = _density_spacing_value(operator.density_spacing) / max(world_radius, WORLD_MIN_OPERATION_RADIUS)
    spacing_px = max(3.0, min(radius_px * 1.5, radius_px * spacing_ratio))
    grid_extent = max(1, int(math.ceil(radius_px / spacing_px)))
    square_half_extent = max(1.5, min(spacing_px * 0.3, 8.0))
    radius_squared = radius_px * radius_px
    triangle_vertices = []
    width = None
    height = None

    def _append_square(point_x, point_y):
        left = point_x - square_half_extent
        right = point_x + square_half_extent
        bottom = point_y - square_half_extent
        top = point_y + square_half_extent
        if width is not None and height is not None:
            if right < 0.0 or left > width or top < 0.0 or bottom > height:
                return False
        triangle_vertices.extend((
            (left, bottom),
            (right, bottom),
            (right, top),
            (left, bottom),
            (right, top),
            (left, top),
        ))
        return True

    min_column = -grid_extent
    max_column = grid_extent
    min_row = -grid_extent
    max_row = grid_extent
    if region is not None:
        width = float(getattr(region, "width", 0.0))
        height = float(getattr(region, "height", 0.0))
        min_column = max(min_column, int(math.ceil((-square_half_extent - center_x) / spacing_px)))
        max_column = min(max_column, int(math.floor((width + square_half_extent - center_x) / spacing_px)))
        min_row = max(min_row, int(math.ceil((-square_half_extent - center_y) / spacing_px)))
        max_row = min(max_row, int(math.floor((height + square_half_extent - center_y) / spacing_px)))

    visible_grid_cells = max(0, max_column - min_column + 1) * max(0, max_row - min_row + 1)
    if visible_grid_cells > WORLD_DENSITY_PREVIEW_MAX_VISIBLE_DOTS:
        return _density_preview_solid_triangles_2d(center_x, center_y, radius_px, region), True

    dot_count = 0
    for row in range(min_row, max_row + 1):
        for column in range(min_column, max_column + 1):
            point_x = center_x + (column * spacing_px)
            point_y = center_y + (row * spacing_px)
            dx = point_x - center_x
            dy = point_y - center_y
            if (dx * dx) + (dy * dy) > radius_squared:
                continue
            if _append_square(point_x, point_y):
                dot_count += 1

    if dot_count <= 1 and spacing_px > radius_px:
        for column, row in WORLD_DENSITY_PREVIEW_SPARSE_RING_OFFSETS:
            point_x = center_x + (column * spacing_px)
            point_y = center_y + (row * spacing_px)
            dx = point_x - center_x
            dy = point_y - center_y
            if (dx * dx) + (dy * dy) <= radius_squared:
                continue
            if _append_square(point_x, point_y):
                dot_count += 1

    return triangle_vertices, False


def _project_world_triangles_to_region_2d(context, triangle_vertices):
    region = getattr(context, "region", None)
    region_data = getattr(context, "region_data", None)
    if region is None or region_data is None or not triangle_vertices:
        return []

    projected_vertices = []
    for index in range(0, len(triangle_vertices), 3):
        triangle = triangle_vertices[index:index + 3]
        if len(triangle) < 3:
            continue

        projected_triangle = []
        for vertex in triangle:
            try:
                projected = view3d_utils.location_3d_to_region_2d(region, region_data, vertex, default=None)
            except Exception:
                projected = None
            if projected is None:
                projected_triangle = []
                break
            projected_triangle.append((projected.x, projected.y))

        if projected_triangle:
            projected_vertices.extend(projected_triangle)

    return projected_vertices


def _draw_world_circle(operator, context):
    if not getattr(operator, "_running", False):
        return
    if getattr(operator, "adjust_mode", ""):
        return
    if operator._density_uses_native_ui():
        return
    if _hide_preview_for_viewport_navigation(operator, context=context):
        return
    preview_target = _preview_target_info(operator, live=True, context=context)
    if not preview_target or not preview_target.get("location") or not preview_target.get("normal"):
        return
    if _preview_uses_2d_ui(operator):
        return
    center = preview_target["location"]
    normal = preview_target["normal"]
    radius = _brush_preview_radius(operator)
    density_preview_square_triangles = _density_preview_square_triangles(operator, center, normal, radius)
    tangent, bitangent, normal = _stable_preview_basis(operator, normal)
    vertices = []
    steps = 48
    offset = normal * 0.002
    for index in range(steps + 1):
        angle = (index / steps) * math.tau
        offset_vec = (math.cos(angle) * tangent + math.sin(angle) * bitangent) * radius
        vertices.append(center + offset + offset_vec)

    if not vertices:
        return

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices})
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    preview_thickness = 2.0
    gpu.state.line_width_set(preview_thickness)
    shader.bind()
    shader.uniform_float("color", (1.0, 1.0, 1.0, 0.95))
    batch.draw(shader)

    if density_preview_square_triangles:
        preview_batch = batch_for_shader(shader, 'TRIS', {"pos": density_preview_square_triangles})
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.75))
        preview_batch.draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def _draw_text_line(font_id, x, y, text, color=(1.0, 1.0, 1.0, 1.0), size=12):
    blf.position(font_id, x, y, 0)
    blf.size(font_id, size)
    blf.color(font_id, *color)
    blf.draw(font_id, text)


def _draw_world_hud(operator, context):
    if not getattr(operator, "_running", False):
        return
    adjust_mode = getattr(operator, "adjust_mode", "")
    if operator._density_uses_native_ui():
        return
    preview_target = _preview_target_info(operator, live=True, context=context)
    if not adjust_mode and not _preview_uses_2d_ui(operator):
        return
    if _hide_preview_for_viewport_navigation(operator, context=context):
        return
    mouse_coord = getattr(operator, "hover_mouse_region", None)
    if mouse_coord is None:
        return

    center_x, center_y = mouse_coord
    screen_radius = _world_radius_to_screen_brush(
        context,
        getattr(operator, "brush_radius", WORLD_MIN_OPERATION_RADIUS),
        operator._brush_screen_depth_location(target_info=preview_target),
        mouse_coord=mouse_coord,
    )
    radius_px = _screen_brush_radius_pixels(screen_radius)
    steps = 48
    vertices = []
    for index in range(steps + 1):
        angle = (index / steps) * math.tau
        vertices.append((
            center_x + math.cos(angle) * radius_px,
            center_y + math.sin(angle) * radius_px,
        ))

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices})
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    shader.bind()
    shader.uniform_float("color", (1.0, 1.0, 1.0, 0.95))
    batch.draw(shader)

    if adjust_mode == "STRENGTH":
        density_preview_triangles, dense_preview = _density_preview_square_triangles_2d(
            operator,
            center_x,
            center_y,
            radius_px,
            context.region,
        )
        if density_preview_triangles:
            preview_batch = batch_for_shader(shader, 'TRIS', {"pos": density_preview_triangles})
            preview_alpha = 0.34 if dense_preview else 0.75
            shader.uniform_float("color", (1.0, 1.0, 1.0, preview_alpha))
            preview_batch.draw(shader)
    else:
        preview_center = preview_target.get("location") if preview_target else None
        preview_normal = preview_target.get("normal") if preview_target else None
        if preview_center is not None and preview_normal is not None:
            density_preview_triangles = _project_world_triangles_to_region_2d(
                context,
                _density_preview_square_triangles(
                    operator,
                    preview_center,
                    preview_normal,
                    _brush_preview_radius(operator),
                ),
            )
            if density_preview_triangles:
                preview_batch = batch_for_shader(shader, 'TRIS', {"pos": density_preview_triangles})
                shader.uniform_float("color", (1.0, 1.0, 1.0, 0.75))
                preview_batch.draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def _deselect_secret_paint_systems(context):
    active_obj = getattr(context.view_layer.objects, "active", None) if context.view_layer else None

    for obj in list(context.selected_objects):
        if _is_secret_paint_system(obj):
            obj.select_set(False)

    if active_obj is not None and _is_secret_paint_system(active_obj):
        try:
            context.view_layer.objects.active = active_obj
        except Exception:
            pass


def _deselect_all_world_paint_objects(context):
    try:
        selected_objects = list(context.selected_objects)
    except Exception:
        selected_objects = []
    for obj in selected_objects:
        try:
            obj.select_set(False)
        except Exception:
            pass


def _source_data_lightweight_context_object(source_data):
    if not source_data:
        return None

    origin_object = source_data.get("origin_object")
    if origin_object is not None and not _is_secret_paint_system(origin_object):
        return origin_object

    brush_object = source_data.get("brush_object")
    if brush_object is not None and not _is_secret_paint_system(brush_object):
        return brush_object

    brush_collection = source_data.get("brush_collection")
    if brush_collection is not None:
        try:
            for obj in brush_collection.all_objects:
                if obj is not None and not _is_secret_paint_system(obj):
                    return obj
        except Exception:
            pass

    surface_obj = _system_surface_object(origin_object) if _is_secret_paint_system(origin_object) else None
    if surface_obj is not None and not _is_secret_paint_system(surface_obj):
        return surface_obj
    return None


def _park_active_object_away_from_secret_system(context, source_data):
    view_layer = getattr(context, "view_layer", None)
    if view_layer is None:
        return
    active_obj = getattr(view_layer.objects, "active", None)
    if not _is_secret_paint_system(active_obj):
        return

    candidate = _source_data_lightweight_context_object(source_data)
    if candidate is not None and candidate != active_obj:
        try:
            view_layer.objects.active = candidate
            return
        except Exception:
            pass

    try:
        view_layer.objects.active = None
    except Exception:
        pass


def _keep_active_system_object(context, system_obj):
    if system_obj is None or context.view_layer is None:
        return
    try:
        context.view_layer.objects.active = system_obj
    except Exception:
        return
    try:
        system_obj.select_set(False)
    except Exception:
        pass


class secret_world_paint_mode(bpy.types.Operator):
    bl_idname = "secret.world_paint_mode"
    bl_label = "Secret Paint World Paint"
    bl_options = {'REGISTER', 'UNDO'}

    def _reset_runtime_state(self):
        self._running = False
        _WORLD_STATE["curve_data_cache"] = {}
        _WORLD_STATE["source_curve_candidates_cache"] = {}
        _WORLD_STATE["source_system_candidates_cache"] = {}
        _clear_world_keymap_lookup_caches()
        _WORLD_STATE["last_live_update_time"] = 0.0
        self._draw_handle_2d = None
        self._draw_handle_3d = None
        self._syncing_brush_props = False
        self._last_brush_control_sync_time = 0.0
        self._deferred_brush_radius_store_dirty = False
        self._deferred_density_spacing_store_dirty = False
        self._deferred_native_brush_sync_dirty = False
        self._deferred_brush_settings_flush_token = 0
        self._adjust_depth_location = None
        self._selection_names = []
        self._active_name = ""
        self._original_mode = "OBJECT"
        self._invoke_area_pointer = 0
        self._saved_workspace_tool_id = ""
        self._saved_workspace_tool_mode = ""
        self._saved_view3d_state = {}
        self.source_data = {}
        self._live_source_snapshot = None
        self.preview_target = None
        self.hover_target = None
        self.locked_target = None
        self.locked_targets = []
        self._surface_lock_retarget_pending = False
        self.active_system_name = ""
        self._touched_system_names = set()
        self._session_initial_target_key = ""
        self._session_created_system_names = set()
        self._session_empty_auto_delete_system_names = set()
        self.active_curve_draw_name = ""
        self.tool_id = WORLD_TOOL_DENSITY
        self.surface_lock = False
        self.allow_wire_bounds_surfaces = False
        self.always_use_2d_world_paint_brush_ui = False
        self.interpolate = True
        self.random_z = True
        self.align_to_normal = True
        self.brush_radius = 0.5
        self.brush_radius_setting = 0.5
        self.density_spacing = 0.1
        self.brush_strength = 1.0
        self.adjust_mode = ""
        self.adjust_origin_x = None
        self.adjust_base_value = 0.0
        self._native_density_adjust_confirm_pending = False
        self._native_density_adjust_sync_token = 0
        self._native_density_adjust_depth_location = None
        self._native_density_adjust_manual_spacing = None
        self._native_density_adjust_auto_confirm_until = 0.0
        self._native_density_adjust_release_watch_token = 0
        self._native_density_adjust_release_watch_running = False
        self._native_density_adjust_release_watch_saw_shortcut_down = False
        self._native_density_adjust_release_watch_started = 0.0
        self._native_density_adjust_finalizing = False
        self._native_density_adjust_waiting_for_alt_release = False
        self._native_density_adjust_live_sync_token = 0
        self._native_density_adjust_live_sync_running = False
        self._native_density_adjust_confirm_on_release = False
        self._native_density_adjust_native_release_confirm = False
        self._native_density_radial_passthrough_active = False
        self._native_density_radial_passthrough_token = 0
        self._native_density_radial_confirm_on_release = True
        self._native_density_radial_confirm_sent = False
        self._native_density_radial_confirm_pending = False
        self._native_density_radial_confirm_sent_time = 0.0
        self._native_density_radial_result_committed = False
        self._native_size_adjust_commit_token = 0
        self._native_brush_ui_size_interaction_active = False
        self._native_brush_ui_size_interaction_start_state = None
        self._native_brush_ui_size_interaction_changed = False
        self._native_density_confirmed_size_state = None
        self._disabled_size_adjust_passthrough_active = False
        self._native_density_pending_adjust_mode = ""
        self.last_hover_key = ""
        self.hover_mouse_region = None
        self._viewport_navigation_active = False
        self._viewport_navigation_input_held = False
        self._viewport_navigation_last_state_key = None
        self.last_slider_value = 1.0
        self._syncing_slider = False
        self.toggle_key_type = 'Q'
        self._paint_shortcut_release_chord = None
        self._paint_shortcut_release_down = set()
        self._selection_preview_token = 0
        self._selection_preview_cage_until = 0.0
        self._selection_preview_active = False
        self._selection_preview_name = ""
        self._selection_preview_was_selected = False
        self._selection_preview_previous_active_name = ""
        self._selection_preview_previous_selection_names = []
        self._selection_preview_overlay = None
        self._selection_preview_had_cage_overlay = False
        self._selection_preview_was_cage_visible = False
        self._selection_preview_had_show_overlays = False
        self._selection_preview_was_show_overlays = False
        self._entry_source_preview_active = False
        self._entry_source_preview_allows_hold_pick = False
        self._entry_source_preview_hold_start_time = 0.0
        self._pick_source_hold_active = False
        self._pick_source_hold_source_data = None
        self._pick_source_hold_picked_name = ""
        self._pick_source_hold_source_key = None
        self._pick_source_hold_last_mouse = None
        self._pick_source_hold_last_update_time = 0.0
        self._pick_source_hold_last_hit_time = 0.0
        self._pick_source_hold_restore_mode = ""
        self._source_switch_history = []
        self.stroke_active = False
        self.stroke_last_world = None
        self.stroke_last_sample_world = None
        self.stroke_current_target = ""
        self.bezier_stroke_points = []
        self._primary_paint_button_down = False
        self._active_density_stroke_mode = ""
        self._density_stroke_passthrough = False
        self._native_density_fallback = False
        self._native_density_session_active = False
        self._native_density_interaction_mode = ""
        self._native_density_restore_mode = "OBJECT"
        self._native_density_restore_active_name = ""
        self._native_density_restore_selection_names = []
        self._native_density_restore_density_mode = ""
        self._native_density_restore_minimum_distance = None
        self._native_density_active_system_name = ""
        self._native_density_brush_name = ""
        self._native_density_brush_radius_px = 0.0
        self._native_density_last_sample_mouse = None
        self._native_density_stroke_erase = False
        self._native_density_brush_overlay_name = ""
        self._native_density_brush_overlay_state = {}
        self._native_density_brush_visibility_state = {}
        self._native_density_adjust_passthrough = False
        self._defer_native_idle_session = not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE
        self._native_density_paused_for_navigation = False
        self._native_density_last_sync_key = None
        self._native_density_last_sync_time = 0.0
        self._idle_hover_last_raycast_mouse = None
        self._idle_hover_last_raycast_time = 0.0
        self._perf_passive_event_count = 0
        self._native_passthrough_finish_pending = False
        self._native_passthrough_finish_token = 0
        self._native_stroke_stable_id_sync_token = 0
        self._native_tool_override_until = 0.0
        self._native_tool_override_brush_type = ""
        self._requested_native_tool_until = 0.0
        self._requested_native_tool_brush_type = ""
        self._native_curves_brush_passthrough = False
        self._native_curves_passthrough_brush_name = ""
        self._locked_terrain_feedback_token = 0
        self._locked_terrain_feedback_time = 0.0
        self._native_cursor_activation_token = 0
        self._native_os_cursor_hidden = False
        self._brush_cursor_reentry_refresh_token = 0
        self._last_brush_cursor_refresh_time = 0.0
        self._last_modal_event_time = 0.0
        self._last_region_in_window = False
        self._brush_cursor_focus_lost = False
        self._shift_key_held = False
        self._density_right_delete_button_down = False
        self._density_right_delete_restore_pending = False
        self._density_right_delete_restore_token = 0
        self._shift_delete_tool_active = False
        self._shift_delete_return_tool_id = ""
        self._finish_requested = False
        self._finish_cleanup_done = False
        self._world_ui_cage_hidden = False

    def _refresh_undo_invalidated_references(self):
        if _source_data_contains_removed_references(self.source_data):
            refreshed_source = _source_data_from_snapshot(self._live_source_snapshot)
            if refreshed_source is None:
                return False
            self.source_data = refreshed_source

        discarded_target = False
        for attribute_name in ("preview_target", "hover_target", "locked_target"):
            if _target_info_contains_removed_references(getattr(self, attribute_name, None)):
                setattr(self, attribute_name, None)
                discarded_target = True
        locked_targets = _operator_locked_target_infos(self)
        valid_locked_targets = [
            target_info
            for target_info in locked_targets
            if not _target_info_contains_removed_references(target_info)
        ]
        if len(valid_locked_targets) != len(locked_targets):
            discarded_target = True
            self.locked_targets = valid_locked_targets
            self.locked_target = valid_locked_targets[0] if valid_locked_targets else None
            if valid_locked_targets:
                _store_scene_locked_terrains(bpy.context, valid_locked_targets)
            else:
                _clear_scene_locked_terrain(bpy.context)
        if discarded_target:
            self.last_hover_key = ""
            if self.surface_lock:
                self._surface_lock_retarget_pending = not bool(self._locked_target_infos())
        return True

    def current_target_surface_toggle(self):
        if not _world_target_surface_feature_enabled():
            return False
        active_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
        return bool(active_system and active_system.get(WORLD_PAINT_TARGET_ENABLED_PROP, False))

    def _density_backend_label(self):
        if self.tool_id != WORLD_TOOL_DENSITY:
            return ""
        return "Native" if self._use_native_density_backend() else "Manual"

    def _native_brush_type(self):
        return _native_brush_type_for_world_tool(self.tool_id)

    def _active_native_brush_type(self):
        if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
            return "DELETE"
        return _curves_brush_type_for_world_tool(self.tool_id)

    def _begin_native_tool_override(self, brush_type):
        if not brush_type:
            return
        self._native_tool_override_brush_type = brush_type
        self._native_tool_override_until = time.perf_counter() + WORLD_NATIVE_TOOL_OVERRIDE_SECONDS

    def _native_tool_override_active(self):
        brush_type = getattr(self, "_native_tool_override_brush_type", "")
        if not brush_type:
            return False
        if time.perf_counter() <= getattr(self, "_native_tool_override_until", 0.0):
            return True
        self._native_tool_override_brush_type = ""
        self._native_tool_override_until = 0.0
        return False

    def _mark_requested_native_tool(self, brush_type):
        if not brush_type:
            self._requested_native_tool_brush_type = ""
            self._requested_native_tool_until = 0.0
            return
        self._requested_native_tool_brush_type = brush_type
        self._requested_native_tool_until = time.perf_counter() + 0.75

    def _requested_native_tool_active(self):
        brush_type = getattr(self, "_requested_native_tool_brush_type", "")
        if not brush_type:
            return False
        if time.perf_counter() <= getattr(self, "_requested_native_tool_until", 0.0):
            return True
        self._requested_native_tool_brush_type = ""
        self._requested_native_tool_until = 0.0
        return False

    def _use_native_density_backend(self):
        return self.tool_id == WORLD_TOOL_DENSITY

    def _use_native_tool_backend(self):
        return bool(self._native_brush_type())

    def _locked_target_infos(self):
        return _operator_locked_target_infos(self)

    def _surface_lock_waiting_for_target(self):
        return bool(
            self.surface_lock and
            (not self._locked_target_infos() or self._surface_lock_retarget_pending)
        )

    def _set_locked_targets(self, context, target_infos, *, activate=False, active_target=None):
        locked_targets = _dedupe_target_infos(target_infos)
        if not locked_targets:
            return False

        active_key = _target_key(active_target)
        locked_target = None
        if active_key:
            for target_info in locked_targets:
                if _target_key(target_info) == active_key:
                    locked_target = _copy_target_info(target_info)
                    break
        if locked_target is None:
            locked_target = _copy_target_info(locked_targets[0])

        self.locked_targets = locked_targets
        self.locked_target = locked_target
        self._surface_lock_retarget_pending = False
        _store_scene_locked_terrains(context, locked_targets)
        if activate:
            self._activate_hover_target(context, locked_target)
        return True

    def _set_locked_target(self, context, target_info, *, activate=False):
        locked_target = _copy_target_info(target_info)
        if locked_target is None:
            return False
        return self._set_locked_targets(
            context,
            [locked_target],
            activate=activate,
            active_target=locked_target,
        )

    def _restore_scene_locked_target(self, context, *, activate=False):
        locked_targets = _scene_locked_terrain_target_infos(context)
        if not locked_targets:
            return False
        return self._set_locked_targets(context, locked_targets, activate=activate)

    def _notify_locked_terrain_miss(self, context):
        locked_targets = self._locked_target_infos()
        if not locked_targets:
            return False

        now = time.perf_counter()
        if now - float(getattr(self, "_locked_terrain_feedback_time", 0.0) or 0.0) < 0.65:
            return True
        self._locked_terrain_feedback_time = now
        self._locked_terrain_feedback_token += 1
        feedback_token = self._locked_terrain_feedback_token

        selection_restore = {}
        for target_info in locked_targets:
            target_owner = target_info.get("target_owner") if target_info else None
            target_name = _safe_rna_name(target_owner)
            if not target_name:
                continue
            try:
                selection_restore[target_name] = bool(target_owner.select_get())
            except Exception:
                selection_restore[target_name] = True
            try:
                target_owner.select_set(True)
            except Exception:
                pass

        if len(locked_targets) == 1:
            target_name = _safe_rna_name(locked_targets[0].get("target_owner"))
            message = f"Secret Paint is locked to {target_name}. Move the brush onto that terrain to paint"
        else:
            message = f"Secret Paint is locked to {len(locked_targets)} terrains. Move the brush onto one of them to paint"
        try:
            self.report({'INFO'}, message)
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text=message)
        except Exception:
            pass
        _tag_redraw_view3d_areas(context)

        def _restore_locked_terrain_feedback():
            operator = _world_operator()
            for terrain_name, was_selected in selection_restore.items():
                terrain_obj = bpy.data.objects.get(terrain_name)
                if terrain_obj is None or was_selected:
                    continue
                try:
                    terrain_obj.select_set(False)
                except Exception:
                    pass
            if operator is not None and feedback_token == getattr(operator, "_locked_terrain_feedback_token", 0):
                try:
                    operator._sync_tool_ui_mode(bpy.context)
                except Exception:
                    try:
                        bpy.context.workspace.status_text_set(text=WORLD_PAINT_STATUS_TEXT)
                    except Exception:
                        pass
            _tag_redraw_view3d_areas(bpy.context)
            return None

        try:
            bpy.app.timers.register(_restore_locked_terrain_feedback, first_interval=0.7)
        except Exception:
            pass
        return True

    def _locked_terrain_hit_from_event(self, context, event):
        locked_targets = self._locked_target_infos()
        if not (
            self.surface_lock and
            locked_targets and
            not self._surface_lock_retarget_pending and
            hasattr(event, "mouse_region_x") and
            hasattr(event, "mouse_region_y")
        ):
            return True
        raycast_context = context
        mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        try:
            override, override_mouse_coord = _event_view3d_window_override_and_mouse(
                context,
                event,
                self._invoke_area_pointer,
            )
        except Exception:
            override, override_mouse_coord = None, None
        if override is not None and override_mouse_coord is not None:
            try:
                with context.temp_override(**override):
                    target_info = _raycast_locked_targets(
                        bpy.context,
                        override_mouse_coord,
                        locked_targets,
                        source_data=self.source_data,
                        allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                    )
            except Exception:
                target_info = None
        else:
            target_info = _raycast_locked_targets(
                raycast_context,
                mouse_coord,
                locked_targets,
                source_data=self.source_data,
                allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
            )
        if target_info is None:
            self._notify_locked_terrain_miss(context)
            return False
        self.preview_target = target_info
        self.hover_target = target_info
        self.last_hover_key = _target_key(target_info)
        return True

    def _sync_modifier_key_state(self, event):
        if event.type not in {'LEFT_SHIFT', 'RIGHT_SHIFT'}:
            return False
        previous = self._shift_key_held
        if event.value == 'PRESS':
            self._shift_key_held = True
        elif event.value == 'RELEASE':
            self._shift_key_held = False
        return previous != self._shift_key_held

    def _remember_paint_shortcut_release_chord(self, context, event, *, prefer_pick_source=False):
        chord = None
        if event is not None:
            try:
                if prefer_pick_source:
                    chord = _pick_source_shortcut_chord_from_event(context, event)
                if chord is None:
                    chord = _base_paint_shortcut_chord_from_event(context, event)
                if chord is None and not prefer_pick_source:
                    chord = _pick_source_shortcut_chord_from_event(context, event)
                if chord is None and _event_looks_like_keyboard_shortcut(event):
                    chord = _shortcut_chord_from_event(event)
            except Exception:
                chord = None

        parts = _shortcut_chord_parts(chord)
        if not parts:
            self._paint_shortcut_release_chord = None
            self._paint_shortcut_release_down = set()
            return False

        self._paint_shortcut_release_chord = chord
        self._paint_shortcut_release_down = parts
        return True

    def _paint_shortcut_release_status(self, context, event):
        if event is None or getattr(event, "value", "") != 'RELEASE':
            return ""

        chord = getattr(self, "_paint_shortcut_release_chord", None)
        release_down = set(getattr(self, "_paint_shortcut_release_down", set()) or set())
        release_part = _shortcut_chord_release_part(event, chord)
        if release_part is not None and release_down:
            release_down.discard(release_part)
            self._paint_shortcut_release_down = release_down
            if release_down:
                return "pending"
            self._paint_shortcut_release_chord = None
            self._paint_shortcut_release_down = set()
            return "complete"

        if _event_matches_pick_source_shortcut(
            context,
            event,
            self.toggle_key_type,
            ignore_value=True,
        ):
            self._paint_shortcut_release_chord = None
            self._paint_shortcut_release_down = set()
            return "complete"

        return ""

    def _begin_shift_delete_tool(self, context):
        if self.tool_id != WORLD_TOOL_DENSITY or self.stroke_active or self.adjust_mode:
            return False
        self._shift_delete_tool_active = True
        self._shift_delete_return_tool_id = WORLD_TOOL_DENSITY
        self._set_tool(context, WORLD_TOOL_DELETE, sync_workspace=True, preserve_shift=True)
        return True

    def _restore_shift_delete_tool(self, context):
        if not self._shift_delete_tool_active:
            return False
        if self.stroke_active:
            return False
        return_tool_id = self._shift_delete_return_tool_id or WORLD_TOOL_DENSITY
        self._shift_delete_tool_active = False
        self._shift_delete_return_tool_id = ""
        self._set_tool(context, return_tool_id, sync_workspace=True, preserve_shift=True)
        return True

    def _sync_density_shift_delete_brush(self, context, event=None):
        _shift_delete_debug_log(
            "sync_shift_delete.enter",
            context,
            self,
            event=event,
            force=True,
            reason_tool_id=self.tool_id,
        )
        shift_active = self._event_shift_active(event)
        if self._shift_delete_tool_active:
            if not shift_active:
                self._restore_shift_delete_tool(context)
            return

        if self.tool_id != WORLD_TOOL_DENSITY:
            _shift_delete_debug_log("sync_shift_delete.skip_not_density", context, self, event=event, force=True)
            return

        if event is not None and hasattr(event, "shift") and event.type not in {'LEFT_SHIFT', 'RIGHT_SHIFT'} and not self.stroke_active:
            self._shift_key_held = bool(getattr(event, "shift", False))

        if shift_active:
            self._flush_pending_native_density_adjust_result(context)
            if self._begin_shift_delete_tool(context):
                return
            self._native_density_stroke_erase = True
            self._begin_native_tool_override("DELETE")
            if not self._native_density_session_active:
                _shift_delete_debug_log("sync_shift_delete.ensure_idle_before", context, self, event=event, force=True)
                self._ensure_idle_native_density_session(context, event=event)
                _shift_delete_debug_log("sync_shift_delete.ensure_idle_after", context, self, event=event, force=True)
            if context.mode != 'SCULPT_CURVES':
                self._ensure_shift_delete_preview_session(context)
            if context.mode != 'SCULPT_CURVES':
                _shift_delete_debug_log("sync_shift_delete.skip_not_sculpt_curves", context, self, event=event, force=True)
                return
            tool_ok = _activate_native_curves_tool(
                context,
                "DELETE",
                area_pointer=self._invoke_area_pointer,
            )
            system_obj = self._current_system()
            if system_obj is None and context.mode == 'SCULPT_CURVES':
                active_obj = getattr(context, "active_object", None)
                if active_obj is not None and getattr(active_obj, "type", "") == "CURVES":
                    system_obj = active_obj
            brush = self._sync_native_density_brush(context, system_obj=system_obj)
            cursor_ok = False
            if brush is not None:
                cursor_ok = self._activate_native_brush_cursor(context, brush, system_obj, defer=False)
            _shift_delete_debug_log(
                "sync_shift_delete.activated",
                context,
                self,
                event=event,
                force=True,
                tool_ok=tool_ok,
                cursor_ok=cursor_ok,
                system_obj=getattr(system_obj, "name", ""),
                brush=getattr(brush, "name", ""),
                brush_type=shared.secret_paint_curves_brush_type(brush) if brush is not None else "",
            )
            _native_brush_debug_log(
                "shift_delete_preview.enter",
                context,
                self,
                force=True,
                preview_brush=getattr(brush, "name", ""),
            )
            return

        if not self.stroke_active and self._native_density_stroke_erase:
            _shift_delete_debug_log("sync_shift_delete.restore_before", context, self, event=event, force=True)
            self._native_density_stroke_erase = False
            if context.mode == 'SCULPT_CURVES':
                self._restore_native_density_brush_mode(context)
                self._sync_native_density_brush(context, system_obj=self._current_system())
            _shift_delete_debug_log("sync_shift_delete.restore_after", context, self, event=event, force=True)
            _native_brush_debug_log("shift_delete_preview.restore", context, self, force=True)
            return

        _shift_delete_debug_log("sync_shift_delete.noop", context, self, event=event, force=True, shift_active=shift_active)

    def _event_shift_active(self, event):
        return bool(getattr(event, "shift", False) or getattr(self, "_shift_key_held", False))

    def _is_density_right_delete_event(self, event):
        return (
            (
                self.tool_id == WORLD_TOOL_DENSITY or
                bool(getattr(self, "_density_right_delete_button_down", False))
            ) and
            getattr(event, "type", "") == 'RIGHTMOUSE' and
            not bool(getattr(event, "alt", False))
        )

    def _is_density_right_delete_active_event(self, event):
        return self._is_density_right_delete_event(event) and getattr(event, "value", "") in WORLD_PRIMARY_PAINT_ACTIVE_VALUES

    def _is_density_right_delete_release_event(self, event):
        right_mouse_types = {'RIGHTMOUSE', 'EVT_TWEAK_R'}
        event_type = getattr(event, "type", "")
        event_value = getattr(event, "value", "")
        previous_type = getattr(event, "type_prev", "")
        previous_value = getattr(event, "value_prev", "")
        right_delete_state_active = bool(
            getattr(self, "_density_right_delete_restore_pending", False) or
            getattr(self, "_density_right_delete_button_down", False) or
            getattr(self, "_shift_delete_tool_active", False) or
            self.tool_id == WORLD_TOOL_DELETE
        )
        if event_type in right_mouse_types and event_value in WORLD_PRIMARY_PAINT_ACTIVE_VALUES:
            return False
        if event_type in right_mouse_types and event_value in WORLD_PRIMARY_PAINT_END_VALUES:
            return True
        if previous_type in right_mouse_types and previous_value in WORLD_PRIMARY_PAINT_END_VALUES:
            return True
        return bool(
            right_delete_state_active and
            event_type in right_mouse_types and
            event_value == 'ANY'
        )

    def _is_density_right_delete_end_event(self, event):
        return (
            (
                bool(getattr(self, "_density_right_delete_button_down", False)) or
                bool(getattr(self, "_density_right_delete_restore_pending", False))
            ) and
            self._is_density_right_delete_release_event(event)
        )

    def _is_density_right_delete_click_event(self, event):
        return (
            bool(getattr(self, "_density_right_delete_button_down", False)) and
            self._is_density_right_delete_event(event) and
            getattr(event, "value", "") == 'CLICK'
        )

    def _density_delete_input_active(self, event):
        return (
            self._event_shift_active(event) or
            bool(getattr(self, "_density_right_delete_button_down", False)) or
            self._is_density_right_delete_event(event)
        )

    def _paint_stroke_button_down(self):
        return bool(
            getattr(self, "_primary_paint_button_down", False) or
            getattr(self, "_density_right_delete_button_down", False)
        )

    def _multi_locked_density_add_active(self, event=None):
        return (
            self.tool_id == WORLD_TOOL_DENSITY and
            self.surface_lock and
            len(self._locked_target_infos()) > 1 and
            not self._density_delete_input_active(event)
        )

    def _is_density_erase_click_event(self, event):
        return (
            self.tool_id == WORLD_TOOL_DENSITY and
            _is_primary_paint_event(event) and
            getattr(event, "value", "") in {'CLICK', 'RELEASE'} and
            self._density_delete_input_active(event)
        )

    def _is_temporary_shift_delete_click_event(self, event):
        return (
            self.tool_id == WORLD_TOOL_DELETE and
            self._shift_delete_tool_active and
            _is_primary_paint_event(event) and
            getattr(event, "value", "") in {'CLICK', 'RELEASE'}
        )

    def _use_native_density_for_current_stroke(self, event=None):
        if self._use_native_tool_backend():
            return True
        if not self._use_native_density_backend():
            return False
        return True

    def _density_uses_native_ui(self):
        return self._use_native_density_backend() or self._use_native_tool_backend()

    def _native_curves_brush_passthrough_active(self):
        return bool(getattr(self, "_native_curves_brush_passthrough", False))

    def _native_tool_transition_pending(self):
        now = time.perf_counter()
        if (
            getattr(self, "_native_tool_override_brush_type", "")
            and now <= getattr(self, "_native_tool_override_until", 0.0)
        ):
            return True
        if (
            getattr(self, "_requested_native_tool_brush_type", "")
            and now <= getattr(self, "_requested_native_tool_until", 0.0)
        ):
            return True
        return False

    def _managed_native_brush_names(self, brush_type):
        names = set()
        last_brush_name = getattr(self, "_native_density_brush_name", "")
        if last_brush_name:
            names.add(last_brush_name)
        asset_name = shared.secret_paint_curves_brush_asset_name(brush_type)
        if asset_name:
            names.add(asset_name)
        return names

    def _active_brush_requests_native_passthrough(self, context, active_brush=None, active_brush_type=None):
        if not self._density_uses_native_ui():
            return False
        if getattr(context, "mode", "") != 'SCULPT_CURVES':
            return False
        if (
            self.stroke_active
            or self.adjust_mode
            or self._native_density_stroke_erase
            or self._density_right_delete_button_down
            or self._native_tool_transition_pending()
        ):
            return False
        if not getattr(self, "_native_density_brush_name", ""):
            return False
        if active_brush is None or active_brush_type is None:
            brush_container = _tool_settings_brush_container(context)
            active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
            active_brush_type = _brush_curves_type(active_brush)
        if active_brush is None or not active_brush_type:
            return False
        brush_name = getattr(active_brush, "name", "")
        return bool(brush_name and brush_name not in self._managed_native_brush_names(active_brush_type))

    def _enter_native_curves_brush_passthrough(self, context, brush=None):
        brush_name = getattr(brush, "name", "") if brush is not None else ""
        changed = (
            not self._native_curves_brush_passthrough_active()
            or brush_name != getattr(self, "_native_curves_passthrough_brush_name", "")
        )
        self._native_curves_brush_passthrough = True
        self._native_curves_passthrough_brush_name = brush_name
        self._native_tool_override_brush_type = ""
        self._native_tool_override_until = 0.0
        self._remove_draw_handlers()
        self._set_native_os_cursor_hidden(context, False)
        try:
            context.workspace.status_text_set(
                text="Secret Paint Mode: Blender Sculpt Curves brush active. Pick a Secret Paint tool or use its shortcut to return"
            )
        except Exception:
            pass
        if changed:
            _tag_view3d_tool_ui_regions(context, area_pointer=self._invoke_area_pointer)
            _tag_redraw_view3d_areas(context)
        return changed

    def _leave_native_curves_brush_passthrough(self, context):
        if not self._native_curves_brush_passthrough_active():
            return False
        self._native_curves_brush_passthrough = False
        self._native_curves_passthrough_brush_name = ""
        _tag_view3d_tool_ui_regions(context, area_pointer=self._invoke_area_pointer)
        _tag_redraw_view3d_areas(context)
        return True

    def _native_density_passthrough_active(self):
        return (
            self.stroke_active and
            self._active_density_stroke_mode == "native" and
            self._density_stroke_passthrough and
            self._native_density_interaction_mode == "NATIVE_UI" and
            self._native_density_session_active
        )

    def _activate_workspace_tool_for_world_tool(self, context, tool_id):
        if context.mode == 'SCULPT_CURVES':
            if tool_id == WORLD_TOOL_DENSITY:
                if self._native_density_stroke_erase or getattr(self, "_native_tool_override_brush_type", "") == "DELETE":
                    result = _activate_native_curves_tool(
                        context,
                        "DELETE",
                        area_pointer=self._invoke_area_pointer,
                    )
                    _shift_delete_debug_log(
                        "activate_workspace_tool.density_delete_override",
                        context,
                        self,
                        force=True,
                        result=result,
                    )
                    return result
                return _activate_native_density_tool(
                    context,
                    area_pointer=self._invoke_area_pointer,
                )
            native_brush_type = _native_brush_type_for_world_tool(tool_id)
            if native_brush_type:
                return _activate_native_curves_tool(
                    context,
                    native_brush_type,
                    area_pointer=self._invoke_area_pointer,
                )
        return True

    def _native_density_proxy_active(self):
        return (
            self.stroke_active and
            self._active_density_stroke_mode == "native" and
            not self._density_stroke_passthrough and
            self._native_density_interaction_mode == "HANDOFF_PROXY" and
            self._native_density_session_active
        )

    def _preserve_idle_native_density_session(self):
        return (
            WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE and
            self._density_uses_native_ui() and
            self._native_density_session_active and
            not self.stroke_active
        )

    def _native_idle_session_deferred(self, event=None):
        return (
            (
                not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE or
                bool(getattr(self, "_defer_native_idle_session", False))
            ) and
            self._density_uses_native_ui() and
            not self.stroke_active and
            not self.adjust_mode and
            not self._event_shift_active(event)
        )

    def _defer_idle_native_density_session(self, context=None):
        self._defer_native_idle_session = True
        if (
            WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE or
            not self._density_uses_native_ui() or
            self.stroke_active or
            self.adjust_mode or
            getattr(self, "_native_density_radial_passthrough_active", False)
        ):
            return False
        if not self._native_density_session_active:
            return False
        try:
            self._finish_native_density_session(context or bpy.context, restore_selection=False)
        except Exception:
            return False
        return True

    def _native_density_sync_key(self, context, system_obj):
        view_key = _viewport_navigation_state_key(self, context)
        return (
            getattr(system_obj, "name", ""),
            self.tool_id,
            self._active_native_brush_type(),
            round(float(getattr(self, "brush_radius_setting", 0.0) or 0.0), 4),
            round(float(getattr(self, "brush_radius", 0.0) or 0.0), 4),
            round(float(getattr(self, "density_spacing", 0.0) or 0.0), 4),
            False,
            bool(getattr(self, "interpolate", False)),
            bool(getattr(self, "_native_density_stroke_erase", False)),
            view_key,
        )

    def _native_density_sync_due(self, sync_key, *, interval=None):
        if sync_key != getattr(self, "_native_density_last_sync_key", None):
            return True
        if interval is None:
            return False
        return (time.perf_counter() - float(getattr(self, "_native_density_last_sync_time", 0.0) or 0.0)) >= interval

    def _mark_native_density_synced(self, sync_key):
        self._native_density_last_sync_key = sync_key
        self._native_density_last_sync_time = time.perf_counter()

    def _idle_native_hover_raycast_due(self, event):
        if self.hover_target is None:
            return True
        if event is None or not hasattr(event, "mouse_region_x") or not hasattr(event, "mouse_region_y"):
            return False

        mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        last_mouse = getattr(self, "_idle_hover_last_raycast_mouse", None)
        last_time = float(getattr(self, "_idle_hover_last_raycast_time", 0.0) or 0.0)
        if last_mouse is None:
            return True

        dx = float(mouse_coord[0]) - float(last_mouse[0])
        dy = float(mouse_coord[1]) - float(last_mouse[1])
        moved_enough = (dx * dx + dy * dy) >= (WORLD_NATIVE_IDLE_HOVER_RAYCAST_DISTANCE_PX ** 2.0)
        return moved_enough or (time.perf_counter() - last_time) >= WORLD_NATIVE_IDLE_HOVER_RAYCAST_INTERVAL

    def _mark_idle_native_hover_raycast(self, event):
        if event is None or not hasattr(event, "mouse_region_x") or not hasattr(event, "mouse_region_y"):
            return
        self._idle_hover_last_raycast_mouse = (event.mouse_region_x, event.mouse_region_y)
        self._idle_hover_last_raycast_time = time.perf_counter()

    def _pause_idle_native_density_for_navigation(self, context):
        if not self._preserve_idle_native_density_session():
            return False
        self._native_density_paused_for_navigation = True
        self._finish_native_density_session(context, restore_selection=False)
        self._native_density_last_sync_key = None
        self._native_density_last_sync_time = 0.0
        return True

    def _sync_tool_ui_mode(self, context):
        if _WORLD_STATE["ui_hijacked"] and _WORLD_STATE.get("toolbar_original") is None:
            _hijack_world_toolbar()

        if self._native_curves_brush_passthrough_active():
            self._remove_draw_handlers()
            self._set_native_os_cursor_hidden(context, False)
            try:
                context.workspace.status_text_set(
                    text="Secret Paint Mode: Blender Sculpt Curves brush active. Pick a Secret Paint tool or use its shortcut to return"
                )
            except Exception:
                pass
            _tag_redraw_view3d_areas(context)
            return

        if self._density_uses_native_ui():
            self._remove_draw_handlers()
            self._native_os_cursor_hidden = False
            try:
                context.window.cursor_modal_restore()
            except Exception:
                pass
            try:
                if self.tool_id == WORLD_TOOL_DENSITY:
                    if self._native_density_stroke_erase:
                        status_text = "Secret Paint Mode: native delete brush active. Release Shift to return to Density"
                    else:
                        status_text = "Secret Paint Mode: native density brush active. LMB paint, RMB or Shift remove, F size, Alt+F density/strength, paint key picks source"
                else:
                    tool_label = WORLD_TOOL_LABELS.get(self.tool_id, "Brush")
                    status_text = f"Secret Paint Mode: native {tool_label} brush active. LMB paint, paint key picks source, F size"
                context.workspace.status_text_set(
                    text=status_text
                )
            except Exception:
                pass
            _tag_redraw_view3d_areas(context)
            return

        self._set_native_os_cursor_hidden(context, False)
        if self._running:
            self._install_draw_handlers(context)
        try:
            context.window.cursor_modal_set('PAINT_CROSS')
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text=WORLD_PAINT_STATUS_TEXT)
        except Exception:
            pass
        _tag_redraw_view3d_areas(context)

    def _set_native_os_cursor_hidden(self, context, hidden):
        hidden = bool(hidden and self._density_uses_native_ui() and not self.adjust_mode)
        if hidden == bool(getattr(self, "_native_os_cursor_hidden", False)):
            return
        try:
            if hidden:
                context.window.cursor_modal_set('PAINT_CROSS')
            else:
                context.window.cursor_modal_restore()
            self._native_os_cursor_hidden = hidden
        except Exception:
            self._native_os_cursor_hidden = False

    def _sync_native_os_cursor_for_region(self, context, region_context):
        hide_cursor = bool(
            region_context and
            region_context.get("in_window_region") and
            self._density_uses_native_ui() and
            not self._native_curves_brush_passthrough_active() and
            not self.adjust_mode
        )
        self._set_native_os_cursor_hidden(context, hide_cursor)

    def _maybe_refresh_brush_cursor_for_region_reentry(self, context, event):
        if not self._density_uses_native_ui():
            return False
        if not hasattr(event, "mouse_x") or not hasattr(event, "mouse_y"):
            return False

        region_context = _event_region_context(context, event, self._invoke_area_pointer)
        in_window_region = bool(region_context.get("in_window_region"))
        was_in_window_region = bool(getattr(self, "_last_region_in_window", False))
        self._last_region_in_window = in_window_region
        self._sync_native_os_cursor_for_region(context, region_context)

        if not in_window_region:
            if was_in_window_region or region_context.get("ui_region") or region_context.get("area") is None:
                self._brush_cursor_focus_lost = True
            return False

        if self.adjust_mode:
            if getattr(self, "_native_density_adjust_passthrough", False):
                self._remove_draw_handlers()
                self._restore_native_density_brush_overlay()
                self._restore_native_density_brush_visibility(context)
                self._force_native_brush_visibility(context, allow_adjust=True)
            else:
                self._install_draw_handlers(context)
            _tag_redraw_view3d_areas(context)
            return True

        if getattr(self, "_brush_cursor_focus_lost", False) or not was_in_window_region:
            focus_recovery = bool(getattr(self, "_brush_cursor_focus_lost", False))
            now = time.perf_counter()
            if self._native_density_session_active and not focus_recovery:
                self._force_native_brush_visibility(context)
                self._brush_cursor_focus_lost = False
                return False
            if (
                self._native_density_session_active and
                focus_recovery and
                now - float(getattr(self, "_last_brush_cursor_refresh_time", 0.0) or 0.0) <
                WORLD_BRUSH_CURSOR_REENTRY_REFRESH_INTERVAL
            ):
                self._force_native_brush_visibility(context)
                self._brush_cursor_focus_lost = False
                return False
            self._refresh_brush_cursor_after_view_reentry(
                context,
                event,
                schedule=focus_recovery,
                force_rebuild=focus_recovery,
            )
            self._brush_cursor_focus_lost = False
            return True

        return False

    def _schedule_brush_cursor_reentry_refresh(self):
        self._brush_cursor_reentry_refresh_token += 1
        refresh_token = self._brush_cursor_reentry_refresh_token
        attempts = {"count": 0}

        def _refresh_tick():
            operator = _world_operator()
            if operator is None or not getattr(operator, "_running", False):
                return None
            if refresh_token != getattr(operator, "_brush_cursor_reentry_refresh_token", 0):
                return None

            attempts["count"] += 1
            try:
                operator._refresh_brush_cursor_after_view_reentry(bpy.context, schedule=False)
            except Exception:
                pass

            return 0.08 if attempts["count"] < 10 else None

        try:
            bpy.app.timers.register(_refresh_tick, first_interval=0.03)
        except Exception:
            pass

    def _force_native_brush_visibility(self, context, *, allow_adjust=False):
        if not self._density_uses_native_ui() or (self.adjust_mode and not allow_adjust):
            return False
        curves_sculpt = _tool_settings_brush_container(context)
        if curves_sculpt is None:
            return False

        changed = False
        for prop_name in ("show_brush", "show_brush_on_surface"):
            if not hasattr(curves_sculpt, prop_name):
                continue
            try:
                if not bool(getattr(curves_sculpt, prop_name)):
                    changed = _world_set_attr_if_different(curves_sculpt, prop_name, True) or changed
            except Exception:
                pass
        return changed

    def _refresh_brush_cursor_after_view_reentry(self, context, event=None, *, schedule=True, force_rebuild=False):
        if self._native_curves_brush_passthrough_active():
            self._force_native_brush_visibility(context)
            return True

        area, region, space = _view3d_area_data(context, self._invoke_area_pointer)
        current_area = getattr(context, "area", None)
        try:
            current_area_pointer = current_area.as_pointer() if current_area is not None else 0
            target_area_pointer = area.as_pointer() if area is not None else 0
        except Exception:
            current_area_pointer = 0
            target_area_pointer = 0
        if (
            area is not None and
            region is not None and
            space is not None and
            current_area_pointer != target_area_pointer
        ):
            try:
                with context.temp_override(area=area, region=region, space_data=space):
                    return self._refresh_brush_cursor_after_view_reentry(
                        bpy.context,
                        event,
                        schedule=schedule,
                        force_rebuild=force_rebuild,
                    )
            except Exception:
                pass

        self._last_brush_cursor_refresh_time = time.perf_counter()

        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)

        if self.adjust_mode:
            if getattr(self, "_native_density_adjust_passthrough", False):
                self._remove_draw_handlers()
                self._restore_native_density_brush_overlay()
                self._restore_native_density_brush_visibility(context)
                self._force_native_brush_visibility(context, allow_adjust=True)
            elif self._density_uses_native_ui():
                self._install_draw_handlers(context)
                self._suppress_native_brush_ui_for_adjust(context)
            _tag_redraw_view3d_areas(context)
            return True

        if not self._density_uses_native_ui():
            if force_rebuild:
                self._remove_draw_handlers()
            self._sync_tool_ui_mode(context)
            _tag_redraw_view3d_areas(context)
            if schedule:
                self._schedule_brush_cursor_reentry_refresh()
            return True

        if not self.adjust_mode:
            self._restore_native_density_brush_overlay()
            self._restore_native_density_brush_visibility(context)
            self._force_native_brush_visibility(context)

        if (
            force_rebuild and
            self._native_density_session_active and
            not self.stroke_active and
            not self._primary_paint_button_down and
            not self.adjust_mode
        ):
            try:
                self._finish_native_density_session(context, restore_selection=False)
            except Exception:
                self._native_density_session_active = False

        if not self._native_density_session_active:
            refreshed = self._ensure_idle_native_density_session(context, event=event)
            self._force_native_brush_visibility(context)
            if schedule:
                self._schedule_brush_cursor_reentry_refresh()
            return refreshed

        system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
        if system_obj is None:
            system_obj = self._current_system()
        if system_obj is None and context.mode == 'SCULPT_CURVES':
            active_obj = getattr(context, "active_object", None)
            if active_obj is not None and getattr(active_obj, "type", "") == "CURVES":
                system_obj = active_obj

        if system_obj is not None:
            _keep_active_system_object(context, system_obj)

        brush_type = self._active_native_brush_type()
        tool_ok = False
        if brush_type:
            if force_rebuild:
                tool_ok = _force_native_curves_tool_rebuild(
                    context,
                    brush_type,
                    area_pointer=self._invoke_area_pointer,
                )
            else:
                tool_ok = _activate_native_curves_tool(
                    context,
                    brush_type,
                    area_pointer=self._invoke_area_pointer,
                )

        brush = self._sync_native_density_brush(context, system_obj=system_obj)
        cursor_ok = False
        if brush is not None:
            cursor_ok = self._activate_native_brush_cursor(context, brush, system_obj, defer=False)

        self._force_native_brush_visibility(context)
        self._sync_tool_ui_mode(context)
        _tag_redraw_view3d_areas(context)

        if schedule:
            self._schedule_brush_cursor_reentry_refresh()

        return brush is not None and (tool_ok or cursor_ok)

    def _native_density_brush(self, context):
        brush_type = self._active_native_brush_type()
        if not brush_type:
            return None

        brush_container = _tool_settings_brush_container(context)
        brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        asset_name = shared.secret_paint_curves_brush_asset_name(brush_type)
        if _curves_brush_matches_type(brush, brush_type):
            return brush
        if brush_type != 'DENSITY':
            try:
                native_asset_brush = shared.secret_paint_activate_essential_curves_brush_asset(
                    brush_type,
                    context,
                )
            except Exception:
                native_asset_brush = None
            if _curves_brush_matches_type(native_asset_brush, brush_type):
                return native_asset_brush
        if shared.secret_paint_uses_curves_brush_assets():
            if (
                brush is not None
                and brush.name == asset_name
                and shared.secret_paint_is_curves_brush_type(brush, brush_type)
            ):
                return brush
            asset_brush = shared.secret_paint_ensure_sp_curves_brush_asset(
                brush_type,
                context,
                configure=False,
                override_settings=False,
                size=None,
            )
            if shared.secret_paint_is_curves_brush_type(asset_brush, brush_type):
                if brush_container is not None:
                    try:
                        if getattr(brush_container, "brush", None) != asset_brush:
                            brush_container.brush = asset_brush
                    except Exception:
                        pass
                return asset_brush

        fallback_name = "Density Curves" if brush_type == "DENSITY" else f"{WORLD_TOOL_LABELS.get(self.tool_id, brush_type)} Curves"
        brush = _ensure_curves_brush(fallback_name, brush_type)
        if brush_container is not None:
            try:
                if getattr(brush_container, "brush", None) != brush:
                    brush_container.brush = brush
            except Exception:
                pass
        return brush if shared.secret_paint_is_curves_brush_type(brush, brush_type) else None

    def _native_interpolate_enabled_from_settings(self, settings):
        if settings is None:
            return bool(self.interpolate)
        enabled_props = (
            "use_length_interpolate",
            "use_radius_interpolate",
            "use_shape_interpolate",
            "interpolate_length",
            "interpolate_radius",
            "interpolate_shape",
        )
        supported_values = []
        for prop_name in enabled_props:
            if hasattr(settings, prop_name):
                try:
                    supported_values.append(bool(getattr(settings, prop_name)))
                except Exception:
                    pass
        if not supported_values:
            return bool(self.interpolate)
        return all(supported_values)

    def _sync_interpolate_from_native_brush(self, context, *, ensure=False):
        if not self._density_uses_native_ui():
            return bool(self.interpolate)
        brush_type = self._active_native_brush_type()
        brush_container = _tool_settings_brush_container(context)
        brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if not shared.secret_paint_is_curves_brush_type(brush, brush_type):
            brush = self._native_density_brush(context) if ensure else None
        settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
        self.interpolate = self._native_interpolate_enabled_from_settings(settings)
        return bool(self.interpolate)

    def _apply_interpolate_to_native_settings(self, settings, enabled=None):
        if settings is None:
            return False
        enabled = bool(self.interpolate if enabled is None else enabled)
        changed = False
        for prop_name in (
            "use_length_interpolate",
            "use_radius_interpolate",
            "use_shape_interpolate",
            "interpolate_length",
            "interpolate_radius",
            "interpolate_shape",
        ):
            if not hasattr(settings, prop_name):
                continue
            changed = _world_set_attr_if_different(settings, prop_name, enabled) or changed
        for prop_name in ("use_point_count_interpolate", "interpolate_point_count"):
            if not hasattr(settings, prop_name):
                continue
            changed = _world_set_attr_if_different(settings, prop_name, False) or changed
        return changed

    def _apply_interpolate_to_native_brush(self, context, enabled=None):
        brush = self._native_density_brush(context)
        settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
        return self._apply_interpolate_to_native_settings(settings, enabled=enabled)

    def _copy_native_brush_runtime_settings(self, source_brush, target_brush, brush_type):
        if source_brush is None or target_brush is None or source_brush == target_brush:
            return False
        if not shared.secret_paint_is_curves_brush_type(target_brush, brush_type):
            return False

        for prop_name in (
            "strength",
            "use_locked_size",
            "unprojected_size",
            "falloff_shape",
        ):
            if not hasattr(source_brush, prop_name) or not hasattr(target_brush, prop_name):
                continue
            try:
                source_value = getattr(source_brush, prop_name)
                epsilon = 1.0e-6 if isinstance(source_value, float) else None
                _world_set_attr_if_different(target_brush, prop_name, source_value, epsilon=epsilon)
            except Exception:
                pass

        source_settings = getattr(source_brush, "curves_sculpt_settings", None)
        target_settings = getattr(target_brush, "curves_sculpt_settings", None)
        if source_settings is not None and target_settings is not None:
            for prop_name in (
                "minimum_distance",
                "curve_length",
                "points_per_curve",
                "density_mode",
                "density_add_attempts",
                "add_amount",
                "curve_radius",
                "use_length_interpolate",
                "use_radius_interpolate",
                "use_shape_interpolate",
                "use_point_count_interpolate",
                "interpolate_length",
                "interpolate_radius",
                "interpolate_shape",
                "interpolate_point_count",
            ):
                if not hasattr(source_settings, prop_name) or not hasattr(target_settings, prop_name):
                    continue
                try:
                    source_value = getattr(source_settings, prop_name)
                    epsilon = WORLD_DENSITY_SPACING_EPSILON if isinstance(source_value, float) else None
                    _world_set_attr_if_different(target_settings, prop_name, source_value, epsilon=epsilon)
                except Exception:
                    pass

        return True

    def _write_confirmed_native_brush_size(self, brush, lock_mode, unprojected_size):
        if brush is None:
            return False
        changed = False
        for prop_name, prop_value in (
            ("use_locked_size", lock_mode),
            ("unprojected_size", unprojected_size),
        ):
            if not hasattr(brush, prop_name):
                continue
            epsilon = WORLD_DENSITY_SPACING_EPSILON if isinstance(prop_value, float) else None
            changed = _world_set_attr_if_different(brush, prop_name, prop_value, epsilon=epsilon) or changed
        return changed

    def _persist_confirmed_native_brush_size(self, context):
        system_obj = self._current_system()
        lock_mode = 'SCENE'
        unprojected_size = max(WORLD_MIN_OPERATION_RADIUS, float(self.brush_radius) * 2.0)

        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        brushes = [active_brush]
        for _brush_type, asset_name in shared.SECRET_PAINT_CURVES_BRUSH_ASSET_SPECS:
            try:
                brushes.append(bpy.data.brushes.get(asset_name))
            except Exception:
                pass
        supported_brush_types = {
            brush_type
            for brush_type, _asset_name in shared.SECRET_PAINT_CURVES_BRUSH_ASSET_SPECS
        }
        try:
            brushes.extend(
                brush
                for brush in bpy.data.brushes
                if shared.secret_paint_curves_brush_type(brush) in supported_brush_types
            )
        except Exception:
            pass

        changed = False
        seen = set()
        for brush in brushes:
            if brush is None:
                continue
            try:
                brush_key = brush.as_pointer()
            except Exception:
                brush_key = id(brush)
            if brush_key in seen:
                continue
            seen.add(brush_key)
            changed = self._write_confirmed_native_brush_size(
                brush,
                lock_mode,
                unprojected_size,
            ) or changed

        unified_settings = getattr(brush_container, "unified_paint_settings", None) if brush_container is not None else None
        changed = self._write_confirmed_native_brush_size(
            unified_settings,
            lock_mode,
            unprojected_size,
        ) or changed
        remember_size_state = getattr(self, "_remember_confirmed_native_density_size_state", None)
        if callable(remember_size_state):
            remember_size_state(
                context,
                system_obj=system_obj,
                reason="persist_confirmed_native_brush_size",
            )
        return changed

    def _sync_active_native_runtime_brush(self, context, preset_brush, brush_type):
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if active_brush is None:
            return None
        if active_brush == preset_brush:
            return active_brush
        if not shared.secret_paint_is_curves_brush_type(active_brush, brush_type):
            return active_brush
        self._copy_native_brush_runtime_settings(preset_brush, active_brush, brush_type)
        return active_brush

    def _apply_density_spacing_to_brush_candidates(self, context, system_obj=None, *brushes):
        if self.tool_id != WORLD_TOOL_DENSITY or self._native_density_stroke_erase:
            return False
        spacing = _density_spacing_value(self.density_spacing)
        self.density_spacing = spacing
        active_system = system_obj if system_obj is not None else self._current_system()

        changed = False
        seen = set()
        for brush in brushes:
            if brush is None:
                continue
            try:
                pointer = brush.as_pointer()
            except Exception:
                pointer = id(brush)
            if pointer in seen:
                continue
            seen.add(pointer)
            changed = shared.secret_paint_apply_density_minimum_distance_to_brush(
                brush,
                context,
                active_system,
                spacing=spacing,
                density_mode='AUTO',
            ) or changed
        stored_changed = _store_system_density_spacing(active_system, spacing)
        changed = stored_changed or changed
        return changed

    def _tool_uses_brush_strength_adjust(self, tool_id=None):
        return (self.tool_id if tool_id is None else tool_id) in WORLD_NATIVE_STRENGTH_TOOL_IDS

    def _active_strength_brush(self, context, *, ensure=True):
        if not self._tool_uses_brush_strength_adjust():
            return None
        brush_type = self._active_native_brush_type()
        if not brush_type:
            return None
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if shared.secret_paint_is_curves_brush_type(active_brush, brush_type) and hasattr(active_brush, "strength"):
            return active_brush
        if not ensure:
            return None
        brush = self._native_density_brush(context)
        if shared.secret_paint_is_curves_brush_type(brush, brush_type) and hasattr(brush, "strength"):
            return brush
        return None

    def _read_active_brush_strength(self, context, *, ensure=False, brush=None):
        if not self._tool_uses_brush_strength_adjust():
            return None
        brush = brush if brush is not None else self._active_strength_brush(context, ensure=ensure)
        if brush is None or not hasattr(brush, "strength"):
            return None
        try:
            return _brush_strength_value(getattr(brush, "strength"), fallback=self.brush_strength)
        except Exception:
            return None

    def _sync_brush_strength_from_native_brush(self, context, *, ensure=False, brush=None):
        strength = self._read_active_brush_strength(context, ensure=ensure, brush=brush)
        if strength is None:
            return False
        changed = abs(strength - getattr(self, "brush_strength", 1.0)) >= WORLD_DENSITY_SPACING_EPSILON
        self.brush_strength = strength
        window_manager = getattr(context, "window_manager", None)
        if window_manager is not None and hasattr(window_manager, "secret_paint_world_brush_strength"):
            was_syncing = bool(getattr(self, "_syncing_brush_props", False))
            self._syncing_brush_props = True
            try:
                window_manager.secret_paint_world_brush_strength = strength
            finally:
                self._syncing_brush_props = was_syncing
        return changed

    def _apply_brush_strength_to_brush_candidates(self, context, *brushes, strength=None):
        if not self._tool_uses_brush_strength_adjust():
            return False
        brush_type = self._active_native_brush_type()
        if not brush_type:
            return False
        strength = _brush_strength_value(
            self.brush_strength if strength is None else strength,
            fallback=self.brush_strength,
        )
        self.brush_strength = strength
        changed = False
        seen = set()
        for brush in brushes:
            if brush is None or not shared.secret_paint_is_curves_brush_type(brush, brush_type):
                continue
            try:
                pointer = brush.as_pointer()
            except Exception:
                pointer = id(brush)
            if pointer in seen:
                continue
            seen.add(pointer)
            if not hasattr(brush, "strength"):
                continue
            changed = _world_set_attr_if_different(
                brush,
                "strength",
                strength,
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            ) or changed
        return changed

    def _set_active_brush_strength(self, context, value):
        if not self._tool_uses_brush_strength_adjust():
            return False
        strength = _brush_strength_value(value, fallback=self.brush_strength)
        brush_type = self._active_native_brush_type()
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        preset_brush = None
        try:
            preset_brush = shared.secret_paint_ensure_sp_curves_brush_asset(
                brush_type,
                context,
                self._current_system(),
                configure=False,
                override_settings=False,
                size=None,
            )
        except Exception:
            preset_brush = None
        native_brush = self._native_density_brush(context)
        changed = self._apply_brush_strength_to_brush_candidates(
            context,
            active_brush,
            preset_brush,
            native_brush,
            strength=strength,
        )
        self._sync_brush_controls(context, force=True)
        _tag_redraw_view3d_areas(context)
        return changed

    def _schedule_density_spacing_native_brush_sync(self, system_obj=None, *, first_interval=0.01, attempts=3):
        if self.tool_id != WORLD_TOOL_DENSITY or self._native_density_stroke_erase:
            return False
        activation_token = getattr(self, "_native_cursor_activation_token", 0)
        active_name = system_obj.name if system_obj is not None else ""
        operator = self
        state = {"remaining": max(1, int(attempts))}

        def _sync_density_spacing_later():
            try:
                if activation_token != getattr(operator, "_native_cursor_activation_token", 0):
                    return None
                if bpy.context.mode != 'SCULPT_CURVES':
                    return None
                if active_name:
                    active = bpy.context.active_object
                    if active is None or active.name != active_name:
                        return None
                operator._apply_density_spacing_to_native_brush(bpy.context)
                state["remaining"] -= 1
                if state["remaining"] > 0:
                    return 0.02
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(_sync_density_spacing_later, first_interval=first_interval)
        except Exception:
            return False
        return True

    def _active_falloff_brush_type(self):
        brush_type = self._active_native_brush_type()
        return brush_type if brush_type and brush_type != "" else ""

    def _active_falloff_brush(self, context, *, ensure=True):
        brush_type = self._active_falloff_brush_type()
        if not brush_type:
            return None
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if shared.secret_paint_is_curves_brush_type(active_brush, brush_type):
            return active_brush if shared.secret_paint_brush_supports_falloff_shape(active_brush) else None
        if not ensure:
            return None
        brush = shared.secret_paint_ensure_sp_curves_brush_asset(
            brush_type,
            context,
            self._current_system(),
            configure=True,
            override_settings=False,
            size=None,
        )
        return brush if shared.secret_paint_brush_supports_falloff_shape(brush) else None

    def _active_falloff_shape(self, context):
        brush = self._active_falloff_brush(context, ensure=True)
        if brush is None:
            return ""
        return getattr(brush, "falloff_shape", "")

    def _set_active_falloff_shape(self, context, falloff_shape):
        brush_type = self._active_falloff_brush_type()
        if not brush_type:
            return False
        preset_brush = shared.secret_paint_ensure_sp_curves_brush_asset(
            brush_type,
            context,
            self._current_system(),
            configure=True,
            override_settings=False,
            size=None,
        )
        changed = shared.secret_paint_set_curves_brush_falloff_shape(preset_brush, falloff_shape)
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if (
            active_brush is not None and
            active_brush != preset_brush and
            shared.secret_paint_is_curves_brush_type(active_brush, brush_type)
        ):
            changed = shared.secret_paint_set_curves_brush_falloff_shape(active_brush, falloff_shape) or changed
        if context.mode == 'SCULPT_CURVES':
            brush = self._sync_native_density_brush(context)
            if brush is not None:
                changed = shared.secret_paint_set_curves_brush_falloff_shape(brush, falloff_shape) or changed
                self._activate_native_brush_cursor(context, brush, self._current_system(), defer=False)
        _tag_redraw_view3d_areas(context)
        return changed

    def _activate_sp_native_preset_brush(self, context, brush_type, system_obj=None, *, source_brush=None):
        preset_brush = None
        try:
            preset_brush = shared.secret_paint_ensure_sp_curves_brush_asset(
                brush_type,
                context,
                system_obj,
                configure=False,
                override_settings=False,
                size=None,
            )
        except Exception:
            preset_brush = None
        self._copy_native_brush_runtime_settings(source_brush, preset_brush, brush_type)
        try:
            activated_brush = shared.secret_paint_activate_sp_curves_brush_asset(
                brush_type,
                context,
                system_obj,
                configure=False,
                override_settings=False,
                size=None,
            )
        except Exception:
            activated_brush = None
        if activated_brush is not None:
            preset_brush = activated_brush
            self._copy_native_brush_runtime_settings(source_brush, preset_brush, brush_type)
        brush_container = _tool_settings_brush_container(context)
        active_before = getattr(brush_container, "brush", None) if brush_container is not None else None
        delete_tool_ok = True
        if brush_type == "DELETE":
            delete_tool_ok = _with_original_world_toolbar(
                lambda: _tool_set_by_id(
                    context,
                    "builtin_brush.delete",
                    area_pointer=self._invoke_area_pointer,
                )
            )
        assigned = False
        active_after = active_before
        if preset_brush is not None and brush_container is not None:
            for _attempt in range(3):
                try:
                    if getattr(brush_container, "brush", None) != preset_brush:
                        brush_container.brush = preset_brush
                    active_after = brush_container.brush
                    assigned = (
                        active_after == preset_brush or
                        (
                            active_after is not None and
                            active_after.name == preset_brush.name and
                            shared.secret_paint_is_curves_brush_type(active_after, brush_type)
                        )
                    )
                    if assigned:
                        break
                except Exception:
                    active_after = getattr(brush_container, "brush", None)
        if (
            preset_brush is not None and
            active_after is not None and
            active_after != preset_brush and
            shared.secret_paint_is_curves_brush_type(active_after, brush_type)
        ):
            self._copy_native_brush_runtime_settings(preset_brush, active_after, brush_type)
        _native_brush_debug_log(
            "activate_sp_native_preset",
            context,
            self,
            force=True,
            brush_type=brush_type,
            preset_brush=getattr(preset_brush, "name", ""),
            active_before=getattr(active_before, "name", ""),
            active_after=getattr(active_after, "name", ""),
            assigned=assigned,
            delete_tool_ok=delete_tool_ok,
        )
        return active_after if assigned else None

    def _activate_native_brush_cursor(self, context, brush, system_obj=None, *, defer=False):
        brush_type = self._active_native_brush_type()
        self._native_cursor_activation_token += 1
        activation_token = self._native_cursor_activation_token
        if brush_type == "DELETE":
            _shift_delete_debug_log(
                "activate_cursor.enter",
                context,
                self,
                force=True,
                requested_brush=getattr(brush, "name", ""),
                requested_type=brush_type,
                system_obj=getattr(system_obj, "name", ""),
                defer=defer,
            )
        _native_brush_debug_log(
            "activate_native_cursor.enter",
            context,
            self,
            force=True,
            requested_brush=getattr(brush, "name", ""),
            requested_type=brush_type,
            defer=defer,
        )
        if brush is None or not brush_type:
            return False

        try:
            activation_asset_brush = shared.secret_paint_ensure_sp_curves_brush_asset(
                brush_type,
                context,
                system_obj,
                configure=False,
                override_settings=False,
                size=None,
            )
        except Exception:
            activation_asset_brush = None
        self._copy_native_brush_runtime_settings(brush, activation_asset_brush, brush_type)
        if brush_type == "DENSITY":
            self._apply_density_spacing_to_brush_candidates(
                context,
                system_obj,
                brush,
                activation_asset_brush,
            )

        activated_brush = None
        try:
            activated_brush = _with_original_world_toolbar(
                lambda: shared.secret_paint_activate_native_curves_brush(
                    brush_type,
                    context,
                    system_obj,
                    configure=False,
                    override_settings=False,
                    size=None,
                    defer=False,
                )
            )
        except Exception:
            activated_brush = None
        initial_runtime_brush = self._sync_active_native_runtime_brush(context, activation_asset_brush, brush_type)
        if brush_type == "DENSITY":
            self._apply_density_spacing_to_brush_candidates(
                context,
                system_obj,
                brush,
                activation_asset_brush,
                activated_brush,
                initial_runtime_brush,
            )
        if shared.secret_paint_is_curves_brush_type(activated_brush, brush_type):
            self._copy_native_brush_runtime_settings(brush, activated_brush, brush_type)
            if brush_type == "DENSITY":
                self._apply_density_spacing_to_brush_candidates(
                    context,
                    system_obj,
                    brush,
                    activation_asset_brush,
                    activated_brush,
                )
            if brush_type == "DELETE":
                tool_ok = _activate_native_curves_tool(
                    context,
                    "DELETE",
                    area_pointer=self._invoke_area_pointer,
                )
            else:
                tool_ok = self._activate_workspace_tool_for_world_tool(context, self.tool_id)
            brush_container = _tool_settings_brush_container(context)
            if brush_container is not None:
                try:
                    if getattr(brush_container, "brush", None) != activated_brush:
                        brush_container.brush = activated_brush
                except Exception:
                    pass
            runtime_brush = self._sync_active_native_runtime_brush(context, activated_brush, brush_type)
            if brush_type == "DENSITY":
                self._apply_density_spacing_to_brush_candidates(
                    context,
                    system_obj,
                    brush,
                    activation_asset_brush,
                    activated_brush,
                    runtime_brush,
                    getattr(brush_container, "brush", None) if brush_container is not None else None,
                )
                self._schedule_density_spacing_native_brush_sync(system_obj)
            if brush_type == "DELETE":
                _shift_delete_debug_log(
                    "activate_cursor.shared_ok",
                    context,
                    self,
                    force=True,
                    tool_ok=tool_ok,
                    activated_brush=getattr(activated_brush, "name", ""),
                    runtime_brush=getattr(runtime_brush, "name", ""),
                )
            _native_brush_debug_log(
                "activate_native_cursor.shared_ok",
                context,
                self,
                force=True,
                activated_brush=getattr(activated_brush, "name", ""),
                runtime_brush=getattr(runtime_brush, "name", ""),
                requested_type=brush_type,
            )
            _tag_redraw_view3d_areas(context)
            self._suppress_native_brush_ui_for_adjust(context)
            return True

        tool_ok = self._activate_workspace_tool_for_world_tool(context, self.tool_id)
        if not tool_ok:
            tool_ok = _activate_native_curves_tool(
                context,
                brush_type,
                area_pointer=self._invoke_area_pointer,
            )
        if brush_type == "DELETE":
            preset_brush = self._activate_sp_native_preset_brush(
                context,
                brush_type,
                system_obj,
                source_brush=brush,
            )
            if preset_brush is not None:
                brush = preset_brush
        brush_container = _tool_settings_brush_container(context)
        brush_ok = False
        if brush_container is not None:
            try:
                if getattr(brush_container, "brush", None) != brush:
                    brush_container.brush = brush
                active_brush = brush_container.brush
                brush_ok = (
                    active_brush == brush or
                    (
                        active_brush is not None and
                        active_brush.name == brush.name and
                        shared.secret_paint_is_curves_brush_type(active_brush, brush_type)
                    )
                )
            except Exception:
                pass
        runtime_brush = self._sync_active_native_runtime_brush(context, brush, brush_type)
        if brush_type == "DENSITY":
            self._apply_density_spacing_to_brush_candidates(
                context,
                system_obj,
                brush,
                runtime_brush,
                getattr(brush_container, "brush", None) if brush_container is not None else None,
            )
            self._schedule_density_spacing_native_brush_sync(system_obj)
        _tag_redraw_view3d_areas(context)
        self._suppress_native_brush_ui_for_adjust(context)
        if brush_type == "DELETE":
            _shift_delete_debug_log(
                "activate_cursor.manual_assign",
                context,
                self,
                force=True,
                tool_ok=tool_ok,
                brush_ok=brush_ok,
                assigned_brush=getattr(brush, "name", ""),
                runtime_brush=getattr(runtime_brush, "name", ""),
            )

        if defer:
            brush_name = brush.name
            active_name = system_obj.name if system_obj is not None else ""
            operator = self

            def _refresh_native_cursor():
                try:
                    if bpy.context.mode != 'SCULPT_CURVES':
                        return None
                    if activation_token != getattr(operator, "_native_cursor_activation_token", 0):
                        _native_brush_debug_log(
                            "activate_native_cursor.deferred_skip_token",
                            bpy.context,
                            operator,
                            force=True,
                            deferred_brush=brush_name,
                            deferred_type=brush_type,
                        )
                        return None
                    if operator._active_native_brush_type() != brush_type:
                        _native_brush_debug_log(
                            "activate_native_cursor.deferred_skip_type",
                            bpy.context,
                            operator,
                            force=True,
                            deferred_brush=brush_name,
                            deferred_type=brush_type,
                        )
                        return None
                    if active_name:
                        active = bpy.context.active_object
                        if active is None or active.name != active_name:
                            return None
                    deferred_brush = bpy.data.brushes.get(brush_name)
                    if deferred_brush is not None and operator._running:
                        _native_brush_debug_log(
                            "activate_native_cursor.deferred_before",
                            bpy.context,
                            operator,
                            force=True,
                            deferred_brush=brush_name,
                        )
                        operator._activate_native_brush_cursor(
                            bpy.context,
                            deferred_brush,
                            bpy.context.active_object,
                            defer=False,
                        )
                        _native_brush_debug_log(
                            "activate_native_cursor.deferred_after",
                            bpy.context,
                            operator,
                            force=True,
                            deferred_brush=brush_name,
                        )
                except Exception:
                    pass
                return None

            try:
                bpy.app.timers.register(_refresh_native_cursor, first_interval=0.01)
            except Exception:
                pass

        _native_brush_debug_log(
            "activate_native_cursor.exit",
            context,
            self,
            force=True,
            requested_brush=getattr(brush, "name", ""),
            requested_type=brush_type,
            tool_ok=tool_ok,
            brush_ok=brush_ok,
            runtime_brush=getattr(runtime_brush, "name", ""),
        )
        runtime_ok = shared.secret_paint_is_curves_brush_type(runtime_brush, brush_type)
        return (tool_ok or brush_ok or runtime_ok) and (brush_ok or runtime_ok)

    def _stash_native_density_brush_overlay_state(self, brush, *, force=False):
        if self._density_uses_native_ui() and not force:
            return
        if brush is None:
            return

        brush_name = brush.name
        if self._native_density_brush_overlay_name != brush_name:
            self._restore_native_density_brush_overlay()
            self._native_density_brush_overlay_name = brush_name
            self._native_density_brush_overlay_state = {
                "use_cursor_overlay": getattr(brush, "use_cursor_overlay", None) if hasattr(brush, "use_cursor_overlay") else None,
                "use_cursor_overlay_override": getattr(brush, "use_cursor_overlay_override", None) if hasattr(brush, "use_cursor_overlay_override") else None,
            }

        if hasattr(brush, "use_cursor_overlay"):
            _world_set_attr_if_different(brush, "use_cursor_overlay", False)
        if hasattr(brush, "use_cursor_overlay_override"):
            _world_set_attr_if_different(brush, "use_cursor_overlay_override", True)

    def _restore_native_density_brush_overlay(self):
        brush_name = getattr(self, "_native_density_brush_overlay_name", "")
        if not brush_name:
            return

        brush = bpy.data.brushes.get(brush_name)
        saved_state = getattr(self, "_native_density_brush_overlay_state", {}) or {}
        if brush is not None:
            for prop_name, prop_value in saved_state.items():
                if prop_value is None or not hasattr(brush, prop_name):
                    continue
                _world_set_attr_if_different(brush, prop_name, prop_value)

        self._native_density_brush_overlay_name = ""
        self._native_density_brush_overlay_state = {}

    def _stash_native_density_brush_visibility(self, context, *, force=False):
        if self._density_uses_native_ui() and not force:
            return
        curves_sculpt = _tool_settings_brush_container(context)
        if curves_sculpt is None:
            return

        if not self._native_density_brush_visibility_state:
            self._native_density_brush_visibility_state = {
                "show_brush": getattr(curves_sculpt, "show_brush", None) if hasattr(curves_sculpt, "show_brush") else None,
                "show_brush_on_surface": getattr(curves_sculpt, "show_brush_on_surface", None) if hasattr(curves_sculpt, "show_brush_on_surface") else None,
            }

        if hasattr(curves_sculpt, "show_brush"):
            _world_set_attr_if_different(curves_sculpt, "show_brush", False)
        if hasattr(curves_sculpt, "show_brush_on_surface"):
            _world_set_attr_if_different(curves_sculpt, "show_brush_on_surface", False)

    def _restore_native_density_brush_visibility(self, context):
        if not self._native_density_brush_visibility_state:
            return

        curves_sculpt = _tool_settings_brush_container(context)
        if curves_sculpt is not None:
            for prop_name, prop_value in self._native_density_brush_visibility_state.items():
                if prop_value is None or not hasattr(curves_sculpt, prop_name):
                    continue
                _world_set_attr_if_different(curves_sculpt, prop_name, prop_value)

        self._native_density_brush_visibility_state = {}

    def _suppress_native_brush_ui_for_adjust(self, context):
        if (
            not self.adjust_mode or
            not self._density_uses_native_ui() or
            getattr(self, "_native_density_adjust_passthrough", False) or
            not WORLD_CUSTOM_ADJUST_UI_ENABLED
        ):
            return
        brush = self._native_density_brush(context)
        if brush is not None:
            self._stash_native_density_brush_overlay_state(brush, force=True)
        self._stash_native_density_brush_visibility(context, force=True)

    def _native_density_current_brush_radius_px(self, context):
        brush_container = _tool_settings_brush_container(context)
        brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        unified_settings = (
            getattr(brush_container, "unified_paint_settings", None)
            if brush_container is not None
            else None
        )
        use_unified_size = bool(
            unified_settings is not None
            and getattr(unified_settings, "use_unified_size", False)
        )
        size_owner = unified_settings if use_unified_size and unified_settings is not None else brush
        try:
            size_px = float(getattr(size_owner, "size", 0.0) or 0.0)
        except Exception:
            size_px = 0.0
        return max(1.0, size_px * 0.5)

    def _sync_native_density_brush(self, context, system_obj=None):
        _native_brush_debug_log("sync_native_brush.enter", context, self, force=True, system_arg=getattr(system_obj, "name", ""))
        if self._native_density_fallback:
            _native_brush_debug_log("sync_native_brush.skip_fallback", context, self, force=True)
            return None
        brush_type = self._active_native_brush_type()
        if not brush_type:
            _native_brush_debug_log("sync_native_brush.no_type", context, self, force=True)
            return None
        if brush_type == "DELETE":
            _shift_delete_debug_log(
                "sync_native_brush.delete_enter",
                context,
                self,
                force=True,
                system_arg=getattr(system_obj, "name", ""),
            )
        system_obj = system_obj if system_obj is not None else self._current_system()
        if system_obj is None and context.mode == 'SCULPT_CURVES':
            active_obj = getattr(context, "active_object", None)
            if active_obj is not None and getattr(active_obj, "type", "") == "CURVES":
                system_obj = active_obj
        if system_obj is None:
            _native_brush_debug_log("sync_native_brush.no_system", context, self, force=True, brush_type=brush_type)
            if brush_type == "DELETE":
                _shift_delete_debug_log("sync_native_brush.delete_no_system", context, self, force=True)
            return None

        commit_pending_size = getattr(self, "_commit_pending_native_size_adjust_confirm", None)
        if callable(commit_pending_size):
            commit_pending_size(context)

        sync_pending_size = getattr(self, "_sync_pending_native_size_before_brush_write", None)
        if callable(sync_pending_size):
            sync_pending_size(context)

        brush = self._native_density_brush(context)
        if brush is None:
            _native_brush_debug_log("sync_native_brush.no_brush", context, self, force=True, brush_type=brush_type)
            if brush_type == "DELETE":
                _shift_delete_debug_log(
                    "sync_native_brush.delete_no_brush",
                    context,
                    self,
                    force=True,
                    system_obj=getattr(system_obj, "name", ""),
                )
            return None
        shared.secret_paint_ensure_default_curves_brush_falloff(brush)
        old_brush_size = getattr(brush, "size", None) if hasattr(brush, "size") else None
        old_unprojected_size = getattr(brush, "unprojected_size", None) if hasattr(brush, "unprojected_size") else None
        old_lock_mode = getattr(brush, "use_locked_size", "") if hasattr(brush, "use_locked_size") else ""
        old_brush_radius_px = 0.0
        try:
            old_brush_radius_px = float(old_brush_size or 0.0) * 0.5
        except Exception:
            old_brush_radius_px = 0.0
        native_radius_px = old_brush_radius_px if old_brush_radius_px > 0.0 else 1.0
        self._native_density_brush_radius_px = float(max(1.0, native_radius_px))
        preserve_native_size_for_adjust = bool(
            getattr(self, "_preserve_native_size_for_adjust", False)
            and brush_type == 'DENSITY'
        )
        lock_mode = 'SCENE'
        desired_unprojected_size = max(WORLD_MIN_OPERATION_RADIUS, float(self.brush_radius) * 2.0)
        shared.secret_paint_brush_size_trace_log(
            "world.sync_native_brush.write.before",
            context,
            self,
            brush=brush,
            brush_type=brush_type,
            old_size=old_brush_size,
            old_unprojected_size=old_unprojected_size,
            new_unprojected_size=desired_unprojected_size,
            old_lock_mode=old_lock_mode,
            new_lock_mode=lock_mode,
            system_obj=system_obj,
            preserve_native_size=preserve_native_size_for_adjust,
        )
        self._stash_native_density_brush_overlay_state(brush)
        if not preserve_native_size_for_adjust and hasattr(brush, "use_locked_size"):
            _world_set_attr_if_different(brush, "use_locked_size", lock_mode)
        if not preserve_native_size_for_adjust and hasattr(brush, "unprojected_size"):
            _world_set_attr_if_different(
                brush,
                "unprojected_size",
                desired_unprojected_size,
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            )
        if brush_type == 'DENSITY':
            _world_set_attr_if_different(brush, "strength", 1.0, epsilon=WORLD_DENSITY_SPACING_EPSILON)
        elif self._tool_uses_brush_strength_adjust():
            self._sync_brush_strength_from_native_brush(context, brush=brush)
        curves_paint_settings = _tool_settings_brush_container(context)
        unified_settings = getattr(curves_paint_settings, "unified_paint_settings", None) if curves_paint_settings is not None else None
        if unified_settings is not None and not preserve_native_size_for_adjust:
            if hasattr(unified_settings, "use_locked_size"):
                _world_set_attr_if_different(unified_settings, "use_locked_size", lock_mode)
            if hasattr(unified_settings, "unprojected_size"):
                _world_set_attr_if_different(
                    unified_settings,
                    "unprojected_size",
                    desired_unprojected_size,
                    epsilon=WORLD_DENSITY_SPACING_EPSILON,
                )
        shared.secret_paint_brush_size_trace_log(
            "world.sync_native_brush.write.after",
            context,
            self,
            brush=brush,
            brush_type=brush_type,
            requested_unprojected_size=desired_unprojected_size,
            requested_lock_mode=lock_mode,
            system_obj=system_obj,
            preserve_native_size=preserve_native_size_for_adjust,
        )
        remember_size_state = getattr(self, "_remember_confirmed_native_density_size_state", None)
        if callable(remember_size_state) and not preserve_native_size_for_adjust:
            remember_size_state(
                context,
                system_obj=system_obj,
                reason="sync_native_density_brush",
            )
        if brush_type != 'DENSITY':
            try:
                shared.secret_paint_configure_curves_brush_asset(
                    brush,
                    brush_type,
                    context,
                    system_obj,
                    override_settings=not self._tool_uses_brush_strength_adjust(),
                    size=None,
                )
            except Exception:
                pass

        settings = getattr(brush, "curves_sculpt_settings", None)
        if settings is None:
            return None

        self._apply_interpolate_to_native_settings(settings)

        if brush_type == 'DENSITY':
            _world_set_attr_if_different(brush, "strength", 1.0, epsilon=WORLD_DENSITY_SPACING_EPSILON)
            if bpy.app.version_string >= "5.0.0":
                if hasattr(brush, "curve_distance_falloff_preset"):
                    _world_set_attr_if_different(brush, "curve_distance_falloff_preset", 'SMOOTHER')
            elif hasattr(brush, "curve_preset"):
                _world_set_attr_if_different(brush, "curve_preset", 'SMOOTHER')

            minimum_distance = float(getattr(settings, "minimum_distance", self.density_spacing))
            if not (
                self.stroke_active and
                self._active_density_stroke_mode == "native"
            ):
                minimum_distance = float(self.density_spacing)
            _world_set_attr_if_different(
                settings,
                "minimum_distance",
                minimum_distance,
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            )
            _world_set_attr_if_different(settings, "curve_length", 0.32, epsilon=WORLD_DENSITY_SPACING_EPSILON)
            _world_set_attr_if_different(settings, "points_per_curve", 2)
            density_mode = getattr(settings, "density_mode", 'AUTO')
            if not (
                self.stroke_active and
                self._active_density_stroke_mode == "native"
            ):
                density_mode = 'AUTO'
            _world_set_attr_if_different(settings, "density_mode", density_mode)
            if getattr(settings, "density_add_attempts", 0) <= 100:
                _world_set_attr_if_different(settings, "density_add_attempts", 3000)

            _store_system_density_spacing(system_obj, self.density_spacing)
        elif brush_type == 'ADD':
            _world_set_attr_if_different(settings, "add_amount", 1)
            _world_set_attr_if_different(settings, "curve_length", 0.32, epsilon=WORLD_DENSITY_SPACING_EPSILON)
            _world_set_attr_if_different(settings, "points_per_curve", 2)

        runtime_brush = self._sync_active_native_runtime_brush(context, brush, brush_type)
        if brush_type == 'DENSITY':
            self._apply_density_spacing_to_brush_candidates(
                context,
                system_obj,
                brush,
                runtime_brush,
            )
        self._native_density_brush_name = brush.name
        if brush_type == "DELETE":
            _shift_delete_debug_log(
                "sync_native_brush.delete_exit",
                context,
                self,
                force=True,
                system_obj=getattr(system_obj, "name", ""),
                synced_brush=getattr(brush, "name", ""),
                runtime_brush=getattr(runtime_brush, "name", ""),
            )
        _native_brush_debug_log(
            "sync_native_brush.exit",
            context,
            self,
            force=True,
            brush_type=brush_type,
            synced_brush=brush.name,
            runtime_brush=getattr(runtime_brush, "name", ""),
        )
        return brush

    def _sync_density_spacing_from_native_brush(self, context):
        if self.tool_id != WORLD_TOOL_DENSITY:
            return
        if self._native_density_stroke_erase:
            return
        brush = self._native_density_brush(context)
        settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
        if settings is None:
            return

        self.density_spacing = _density_spacing_value(
            getattr(settings, "minimum_distance", self.density_spacing),
            fallback=self.density_spacing,
        )
        active_system = self._current_system()
        _store_system_density_spacing(active_system, self.density_spacing)
        self._sync_brush_controls(context)

    def _restore_native_density_brush_mode(self, context):
        _shift_delete_debug_log(
            "restore_density_brush.enter",
            context,
            self,
            force=self.tool_id == WORLD_TOOL_DENSITY,
            restore_mode=self._native_density_restore_density_mode or 'AUTO',
        )
        _native_brush_debug_log("restore_density_brush.enter", context, self, force=True)
        if self.tool_id != WORLD_TOOL_DENSITY:
            return
        restore_mode = self._native_density_restore_density_mode or 'AUTO'
        try:
            self._persist_confirmed_native_brush_size(context)
        except Exception:
            pass
        try:
            brush = _with_original_world_toolbar(
                lambda: shared.secret_paint_activate_native_curves_brush(
                    'DENSITY',
                    context,
                    self._current_system(),
                    configure=False,
                    override_settings=False,
                    size=None,
                    defer=False,
                )
            )
        except Exception:
            brush = None
        if brush is None:
            brush = shared.secret_paint_ensure_sp_density_brush_asset(
                context,
                self._current_system(),
                configure=False,
                override_settings=False,
                size=None,
            )
        self._sync_active_native_runtime_brush(context, brush, "DENSITY")
        settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
        if settings is not None:
            _world_set_attr_if_different(settings, "density_mode", restore_mode)
            restore_minimum_distance = getattr(self, "_native_density_restore_minimum_distance", None)
            try:
                _world_set_attr_if_different(
                    settings,
                    "minimum_distance",
                    float(
                        restore_minimum_distance
                        if restore_minimum_distance is not None
                        else self.density_spacing
                    ),
                    epsilon=WORLD_DENSITY_SPACING_EPSILON,
                )
            except Exception:
                pass
        self._native_density_restore_density_mode = ""
        self._native_density_restore_minimum_distance = None
        if getattr(self, "_native_tool_override_brush_type", "") == "DELETE":
            self._native_tool_override_brush_type = ""
            self._native_tool_override_until = 0.0
        _shift_delete_debug_log("restore_density_brush.exit", context, self, force=True)
        _native_brush_debug_log("restore_density_brush.exit", context, self, force=True)

    def _clear_density_delete_native_state(self):
        self._density_right_delete_button_down = False
        self._density_right_delete_restore_pending = False
        self._native_density_stroke_erase = False
        self._native_tool_override_brush_type = ""
        self._native_tool_override_until = 0.0
        self._requested_native_tool_brush_type = ""
        self._requested_native_tool_until = 0.0
        self._native_curves_brush_passthrough = False
        self._native_curves_passthrough_brush_name = ""

    def _restore_density_native_brush_after_delete(self, context, *, schedule=False):
        if self.tool_id != WORLD_TOOL_DENSITY:
            return False

        self._clear_density_delete_native_state()
        active_system = self._current_system()
        if (
            self._native_density_session_active and
            active_system is not None and
            not self._native_density_session_matches_system(context, active_system)
        ):
            self._finish_native_density_session(context, restore_selection=False)
            if WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
                self._ensure_idle_native_density_session(context)
                active_system = self._current_system()

        if WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
            self._restore_native_density_brush_mode(context)
            brush = self._sync_native_density_brush(context, system_obj=active_system)
            if getattr(context, "mode", "") == 'SCULPT_CURVES':
                _activate_native_density_tool(
                    context,
                    area_pointer=getattr(self, "_invoke_area_pointer", 0),
                )
                if brush is not None:
                    self._activate_native_brush_cursor(
                        context,
                        brush,
                        active_system,
                        defer=True,
                    )
        else:
            self._defer_idle_native_density_session(context)

        try:
            self._restore_native_density_brush_overlay()
            self._restore_native_density_brush_visibility(context)
            self._force_native_brush_visibility(context)
        except Exception:
            pass
        self._sync_tool_ui_mode(context)
        _tag_view3d_tool_ui_regions(
            context,
            area_pointer=getattr(self, "_invoke_area_pointer", 0),
        )
        _tag_redraw_view3d_areas(context)
        if schedule:
            self._schedule_density_native_brush_restore_after_delete()
        return True

    def _schedule_density_native_brush_restore_after_delete(self):
        self._density_right_delete_restore_token = getattr(
            self,
            "_density_right_delete_restore_token",
            0,
        ) + 1
        restore_token = self._density_right_delete_restore_token
        attempts = {"count": 0}

        def _restore_after_blender_event():
            try:
                operator = _world_operator()
                if operator is None or operator is not self:
                    return None
                if restore_token != getattr(operator, "_density_right_delete_restore_token", 0):
                    return None
                attempts["count"] += 1
                if operator.tool_id == WORLD_TOOL_DELETE:
                    operator._shift_delete_tool_active = False
                    operator._shift_delete_return_tool_id = ""
                    operator._set_tool(
                        bpy.context,
                        WORLD_TOOL_DENSITY,
                        sync_workspace=True,
                        preserve_shift=True,
                    )
                if getattr(operator, "stroke_active", False) or getattr(operator, "adjust_mode", ""):
                    return 0.02 if attempts["count"] < 6 else None
                if operator.tool_id == WORLD_TOOL_DENSITY:
                    operator._restore_density_native_brush_after_delete(
                        bpy.context,
                        schedule=False,
                    )
                if attempts["count"] < 6:
                    return 0.02
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(_restore_after_blender_event, first_interval=0.0)
        except Exception:
            return False
        return True

    def _prepare_native_density_stroke(self, context, *, erase=False):
        if erase:
            _shift_delete_debug_log("prepare_native_stroke.erase_enter", context, self, force=True)
        _native_brush_debug_log("prepare_native_stroke.enter", context, self, force=True, erase=erase)
        self._native_density_stroke_erase = bool(erase)
        brush = self._sync_native_density_brush(context)
        settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
        if brush is None:
            _native_brush_debug_log("prepare_native_stroke.no_brush", context, self, force=True, erase=erase)
            if erase:
                _shift_delete_debug_log("prepare_native_stroke.erase_no_brush", context, self, force=True)
            return False
        if self.tool_id != WORLD_TOOL_DENSITY:
            return True

        density_brush = shared.secret_paint_ensure_sp_density_brush_asset(
            context,
            self._current_system(),
            configure=False,
            override_settings=False,
            size=None,
        )
        density_settings = getattr(density_brush, "curves_sculpt_settings", None) if density_brush is not None else None
        if not self._native_density_restore_density_mode and density_settings is not None:
            self._native_density_restore_density_mode = getattr(density_settings, "density_mode", 'AUTO')
        if density_settings is not None:
            _world_set_attr_if_different(
                density_settings,
                "minimum_distance",
                float(self.density_spacing),
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            )
            _world_set_attr_if_different(density_settings, "density_mode", 'AUTO')
        if erase:
            self._native_density_restore_minimum_distance = float(self.density_spacing)
            self._begin_native_tool_override("DELETE")
            _activate_native_curves_tool(
                context,
                "DELETE",
                area_pointer=self._invoke_area_pointer,
            )
            self._activate_native_brush_cursor(context, brush, self._current_system(), defer=False)
            _shift_delete_debug_log(
                "prepare_native_stroke.erase_activated",
                context,
                self,
                force=True,
                prepared_brush=getattr(brush, "name", ""),
                prepared_type=shared.secret_paint_curves_brush_type(brush),
            )
        elif settings is not None:
            _world_set_attr_if_different(
                settings,
                "minimum_distance",
                float(self.density_spacing),
                epsilon=WORLD_DENSITY_SPACING_EPSILON,
            )
            _world_set_attr_if_different(settings, "density_mode", 'AUTO')
            self._apply_density_spacing_to_native_brush(context)
        _native_brush_debug_log(
            "prepare_native_stroke.exit",
            context,
            self,
            force=True,
            erase=erase,
            prepared_brush=getattr(brush, "name", ""),
            prepared_type=shared.secret_paint_curves_brush_type(brush),
        )
        return True

    def _native_density_stroke_mode(self, event=None):
        return 'NORMAL'

    def _native_density_session_matches_context(self, context):
        if not self._native_density_session_active or context.mode != 'SCULPT_CURVES':
            return False
        system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
        if system_obj is None:
            return False
        return getattr(context, "active_object", None) == system_obj

    def _native_density_session_matches_system(self, context, system_obj):
        return (
            system_obj is not None and
            self._native_density_session_active and
            self._native_density_active_system_name == system_obj.name and
            context.mode == 'SCULPT_CURVES' and
            getattr(context, "active_object", None) == system_obj
        )

    def _ensure_native_density_surface_attachment(self, context, system_obj):
        if system_obj is None or getattr(system_obj, "type", "") != "CURVES":
            return False
        curves_data = getattr(system_obj, "data", None)
        if curves_data is None:
            return False

        surface_obj = getattr(curves_data, "surface", None)
        if surface_obj is None and getattr(system_obj, "parent", None) is not None:
            try:
                curves_data.surface = system_obj.parent
                surface_obj = curves_data.surface
            except Exception:
                surface_obj = None
        if surface_obj is None:
            return False

        try:
            curve_count = len(curves_data.curves)
        except Exception:
            curve_count = 0
        if curve_count <= 0:
            return True

        attributes = getattr(curves_data, "attributes", None)
        if attributes is not None and "surface_uv_coordinate" in attributes:
            return True

        was_selected = False
        try:
            was_selected = system_obj.select_get()
        except Exception:
            pass

        try:
            system_obj.select_set(True)
        except Exception:
            pass
        try:
            context.view_layer.objects.active = system_obj
        except Exception:
            pass

        area, region, space = _view3d_area_data(context, self._invoke_area_pointer)
        try:
            if context.mode != 'SCULPT_CURVES':
                _mode_set_with_world_toolbar_restored('SCULPT_CURVES')
            if area is not None and region is not None and space is not None:
                with context.temp_override(area=area, region=region, space_data=space):
                    bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
            else:
                bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
        except Exception:
            pass
        finally:
            if not was_selected:
                try:
                    system_obj.select_set(False)
                except Exception:
                    pass
            _keep_active_system_object(context, system_obj)

        attributes = getattr(curves_data, "attributes", None)
        return attributes is not None and "surface_uv_coordinate" in attributes

    def _native_density_mouse_coord(self, event):
        mouse_coord = self.hover_mouse_region
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            mouse_coord = (event.mouse_region_x, event.mouse_region_y)
            self.hover_mouse_region = mouse_coord
        return mouse_coord

    def _native_density_stroke_spacing_px(self, context, system_obj=None):
        radius_px = float(getattr(self, "_native_density_brush_radius_px", 0.0) or 0.0)
        if radius_px <= 0.0:
            radius_px = float(self._native_density_current_brush_radius_px(context))
        return max(1.0, radius_px * 0.35)

    def _native_density_should_sample(self, context, event, system_obj=None):
        mouse_coord = self._native_density_mouse_coord(event)
        if mouse_coord is None:
            return False, None
        last_mouse = getattr(self, "_native_density_last_sample_mouse", None)
        if last_mouse is None:
            return True, mouse_coord
        spacing_px = self._native_density_stroke_spacing_px(context, system_obj=system_obj)
        dx = float(mouse_coord[0]) - float(last_mouse[0])
        dy = float(mouse_coord[1]) - float(last_mouse[1])
        return ((dx * dx) + (dy * dy)) >= (spacing_px * spacing_px), mouse_coord

    def _invoke_native_delete_modal_without_shift_toggle(self, context):
        if not self._native_density_session_active:
            return False
        system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
        if system_obj is not None:
            _keep_active_system_object(context, system_obj)
        brush = bpy.data.brushes.get(self._native_density_brush_name) if self._native_density_brush_name else None
        if brush is None or not shared.secret_paint_is_curves_brush_type(brush, "DELETE"):
            brush = self._sync_native_density_brush(context, system_obj=system_obj)
        if brush is None:
            return False

        area, region, space = _view3d_area_data(context, self._invoke_area_pointer)
        kwargs = {
            "mode": "NORMAL",
            "brush_toggle": 'None',
            "pen_flip": False,
        }
        try:
            if area is not None and region is not None and space is not None:
                with context.temp_override(area=area, region=region, space_data=space):
                    if not bpy.ops.sculpt_curves.brush_stroke.poll():
                        return False
                    result = bpy.ops.sculpt_curves.brush_stroke('INVOKE_DEFAULT', **kwargs)
            else:
                if not bpy.ops.sculpt_curves.brush_stroke.poll():
                    return False
                result = bpy.ops.sculpt_curves.brush_stroke('INVOKE_DEFAULT', **kwargs)
            return bool({'RUNNING_MODAL', 'FINISHED'} & set(result))
        except Exception:
            return False

    def _invoke_native_density_brush_stroke(self, context, event):
        if not self._native_density_session_active:
            if self._native_density_stroke_erase:
                _shift_delete_debug_log("invoke_native_stroke.no_session", context, self, event=event, force=True)
            return False
        if not self._native_density_stroke_erase:
            return False

        mouse_coord = self._native_density_mouse_coord(event)
        if mouse_coord is None:
            if self._native_density_stroke_erase:
                _shift_delete_debug_log("invoke_native_stroke.no_mouse", context, self, event=event, force=True)
            return False

        system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
        if system_obj is None:
            system_obj = self._current_system()
        brush_radius_px = float(getattr(self, "_native_density_brush_radius_px", 0.0) or 0.0)
        if brush_radius_px <= 0.0:
            brush_radius_px = float(self._native_density_current_brush_radius_px(context))
        stroke_size_px = max(1.0, brush_radius_px * 2.0)
        pressure = float(getattr(event, "pressure", 1.0) or 0.0)
        if pressure <= 0.0:
            pressure = 1.0

        area, region, space = _view3d_area_data(context, self._invoke_area_pointer)
        region_data = getattr(space, "region_3d", None) if space is not None else getattr(context, "region_data", None)
        current_hit = self._current_hit()
        fallback_location = current_hit["location"] if current_hit is not None else self._brush_depth_location(system_obj=system_obj)

        def stroke_location_for_point(point, *, is_center=False):
            location = current_hit["location"] if is_center and current_hit is not None else None
            if location is None and region is not None and region_data is not None and fallback_location is not None:
                try:
                    location = view3d_utils.region_2d_to_location_3d(region, region_data, point, fallback_location)
                except Exception:
                    location = None
            if location is None:
                location = fallback_location
            if location is None:
                return (0.0, 0.0, 0.0)
            return (float(location.x), float(location.y), float(location.z))

        if self._native_density_stroke_erase:
            brush = bpy.data.brushes.get(self._native_density_brush_name) if self._native_density_brush_name else None
            if brush is None or not shared.secret_paint_is_curves_brush_type(brush, "DELETE"):
                brush = self._sync_native_density_brush(context, system_obj=system_obj)
                if brush is not None:
                    self._activate_native_brush_cursor(context, brush, system_obj, defer=False)
            brush_container = _tool_settings_brush_container(context)
            unified_settings = getattr(brush_container, "unified_paint_settings", None) if brush_container is not None else None
            size_owner = brush
            if unified_settings is not None and bool(getattr(unified_settings, "use_unified_size", False)):
                size_owner = unified_settings
            if size_owner is not None:
                try:
                    stroke_size_px = max(1.0, float(getattr(size_owner, "size", stroke_size_px) or stroke_size_px))
                except Exception:
                    pass

        mouse_x = float(mouse_coord[0])
        mouse_y = float(mouse_coord[1])
        if self._native_density_stroke_erase:
            sample_step = max(0.5, min(2.0, stroke_size_px * 0.02))
            stroke_points = [
                (mouse_x, mouse_y),
                (mouse_x + sample_step, mouse_y),
                (mouse_x, mouse_y + sample_step),
            ]
        else:
            stroke_points = [(mouse_x, mouse_y)]
        stroke = [{
            "name": f"SP_DENSITY_STROKE_{index}",
            "mouse": point,
            "mouse_event": point,
            "location": stroke_location_for_point(point, is_center=index == 0),
            "size": float(stroke_size_px),
            "pressure": pressure,
            "x_tilt": 0.0,
            "y_tilt": 0.0,
            "time": float(index) * 0.01,
            "is_start": index == 0,
        } for index, point in enumerate(stroke_points)]

        try:
            repeat_count = 1
            if self._native_density_stroke_erase:
                _shift_delete_debug_log(
                    "invoke_native_stroke.enter",
                    context,
                    self,
                    event=event,
                    force=True,
                    repeat_count=repeat_count,
                    stroke_points=len(stroke),
                    area_ok=area is not None,
                    region_ok=region is not None,
                    space_ok=space is not None,
            )
            if area is not None and region is not None and space is not None:
                with context.temp_override(area=area, region=region, space_data=space):
                    if not bpy.ops.sculpt_curves.brush_stroke.poll():
                        return False
                    for _index in range(repeat_count):
                        result = bpy.ops.sculpt_curves.brush_stroke(
                            stroke=stroke,
                            mode=self._native_density_stroke_mode(event),
                            brush_toggle='None',
                            pen_flip=False,
                        )
                        if 'FINISHED' not in result:
                            if self._native_density_stroke_erase:
                                _shift_delete_debug_log(
                                    "invoke_native_stroke.not_finished",
                                    context,
                                    self,
                                    event=event,
                                    force=True,
                                    result=result,
                                    index=_index,
                            )
                            return False
            else:
                if not bpy.ops.sculpt_curves.brush_stroke.poll():
                    return False
                for _index in range(repeat_count):
                    result = bpy.ops.sculpt_curves.brush_stroke(
                        stroke=stroke,
                        mode=self._native_density_stroke_mode(event),
                        brush_toggle='None',
                        pen_flip=False,
                    )
                    if 'FINISHED' not in result:
                        if self._native_density_stroke_erase:
                            _shift_delete_debug_log(
                                "invoke_native_stroke.not_finished",
                                context,
                                self,
                                event=event,
                                force=True,
                                result=result,
                                index=_index,
                            )
                        return False
            if self._native_density_stroke_erase:
                _shift_delete_debug_log("invoke_native_stroke.finished", context, self, event=event, force=True)
            return True
        except Exception as exc:
            if self._native_density_stroke_erase:
                _shift_delete_debug_log(
                    "invoke_native_stroke.exception",
                    context,
                    self,
                    event=event,
                    force=True,
                    error=repr(exc),
                )
            return False

    def _finish_native_density_session(self, context, *, restore_selection=False):
        if not self._native_density_session_active and not restore_selection:
            return

        self._restore_native_density_brush_mode(context)
        self._restore_native_density_brush_overlay()
        self._restore_native_density_brush_visibility(context)

        try:
            if context.mode != 'OBJECT':
                _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass

        if restore_selection:
            try:
                for obj in context.selected_objects:
                    obj.select_set(False)
            except Exception:
                pass

            for name in self._native_density_restore_selection_names:
                obj = bpy.data.objects.get(name)
                if obj is not None:
                    try:
                        obj.select_set(True)
                    except Exception:
                        pass

            active_obj = bpy.data.objects.get(self._native_density_restore_active_name)
            if active_obj is not None:
                try:
                    context.view_layer.objects.active = active_obj
                except Exception:
                    pass
        else:
            _deselect_secret_paint_systems(context)
            _keep_active_system_object(context, self._current_system())

        self._native_density_session_active = False
        self._native_density_active_system_name = ""
        self._native_density_brush_name = ""
        self._native_density_last_sample_mouse = None
        self._native_density_stroke_erase = False
        self._native_density_interaction_mode = ""
        self._native_density_restore_minimum_distance = None
        self._native_density_last_sync_key = None
        self._native_density_last_sync_time = 0.0

    def _begin_native_density_session(self, context, *, create_system=True):
        if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
            _shift_delete_debug_log("begin_native_session.delete_enter", context, self, force=True)
        _native_brush_debug_log("begin_native_session.enter", context, self, force=True)
        if not (self._use_native_density_backend() or self._use_native_tool_backend()):
            if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
                _shift_delete_debug_log("begin_native_session.delete_skip_backend", context, self, force=True)
            _native_brush_debug_log("begin_native_session.skip_backend", context, self, force=True)
            return False
        if not self.hover_target:
            if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
                _shift_delete_debug_log("begin_native_session.delete_no_hover", context, self, force=True)
            _native_brush_debug_log("begin_native_session.no_hover", context, self, force=True)
            return False

        system_obj = self._ensure_current_system(context, create=create_system)
        if system_obj is None:
            if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
                _shift_delete_debug_log("begin_native_session.delete_no_system", context, self, force=True)
            _native_brush_debug_log("begin_native_session.no_system", context, self, force=True)
            return False

        if (
            self._native_density_session_matches_system(context, system_obj)
        ):
            self._track_touched_system(system_obj)
            sync_key = self._native_density_sync_key(context, system_obj)
            if not self._native_density_sync_due(sync_key):
                return True
            _native_brush_debug_log("begin_native_session.reuse", context, self, force=True, system=system_obj.name)
            brush = self._sync_native_density_brush(context, system_obj=system_obj)
            self._ensure_native_density_surface_attachment(context, system_obj)
            _keep_active_system_object(context, system_obj)
            _deselect_all_world_paint_objects(context)
            if brush is not None:
                self._activate_native_brush_cursor(context, brush, system_obj, defer=True)
                self._apply_density_spacing_to_native_brush(context)
                self._schedule_density_spacing_native_brush_sync(system_obj)
                self._mark_native_density_synced(sync_key)
            if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
                _shift_delete_debug_log(
                    "begin_native_session.delete_reuse_exit",
                    context,
                    self,
                    force=True,
                    system=getattr(system_obj, "name", ""),
                    brush=getattr(brush, "name", ""),
                )
            _native_brush_debug_log("begin_native_session.reuse_exit", context, self, force=True, brush=getattr(brush, "name", ""))
            return brush is not None

        if not self._native_density_session_active:
            self._native_density_restore_mode = context.mode if context.mode else "OBJECT"
            self._native_density_restore_active_name = context.active_object.name if context.active_object else ""
            self._native_density_restore_selection_names = [obj.name for obj in context.selected_objects]
        else:
            self._finish_native_density_session(context, restore_selection=False)

        try:
            if context.mode != 'OBJECT':
                _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass

        try:
            system_obj.select_set(True)
        except Exception:
            pass
        try:
            context.view_layer.objects.active = system_obj
        except Exception:
            pass

        _prepare_workspace_tool_for_native_density_session(
            context,
            area_pointer=self._invoke_area_pointer,
        )
        try:
            shared.context3sculptbrush(
                context,
                activeobj=system_obj,
                keep_active_brush=True,
                brush_setup_mode="native",
            )
        except Exception:
            pass
        _keep_active_system_object(context, system_obj)

        if context.mode != 'SCULPT_CURVES':
            try:
                _mode_set_with_world_toolbar_restored('SCULPT_CURVES')
                shared.secret_paint_disable_sculpt_curves_cage(context)
                self._world_ui_cage_hidden = True
            except Exception:
                self._finish_native_density_session(context, restore_selection=True)
                return False
        _keep_active_system_object(context, system_obj)
        self._ensure_native_density_surface_attachment(context, system_obj)

        tool_ok = self._activate_workspace_tool_for_world_tool(context, self.tool_id)
        if not tool_ok:
            if self.tool_id == WORLD_TOOL_DENSITY:
                tool_ok = _activate_native_density_tool(context, area_pointer=self._invoke_area_pointer)
            else:
                brush_type = self._native_brush_type()
                tool_ok = _activate_native_curves_tool(context, brush_type, area_pointer=self._invoke_area_pointer)
        brush = self._sync_native_density_brush(context, system_obj=system_obj)
        cursor_ok = False
        if brush is not None:
            cursor_ok = self._activate_native_brush_cursor(context, brush, system_obj, defer=True)
            self._apply_density_spacing_to_native_brush(context)
            self._schedule_density_spacing_native_brush_sync(system_obj)
            self._mark_native_density_synced(self._native_density_sync_key(context, system_obj))
        if (not tool_ok and not cursor_ok) or brush is None:
            if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
                _shift_delete_debug_log(
                    "begin_native_session.delete_fail_activation",
                    context,
                    self,
                    force=True,
                    tool_ok=tool_ok,
                    cursor_ok=cursor_ok,
                    brush=getattr(brush, "name", ""),
                )
            _native_brush_debug_log("begin_native_session.fail_activation", context, self, force=True, tool_ok=tool_ok, cursor_ok=cursor_ok, brush=getattr(brush, "name", ""))
            self._finish_native_density_session(context, restore_selection=True)
            return False

        self._stash_native_density_brush_visibility(context)
        _keep_active_system_object(context, system_obj)

        self._native_density_fallback = False
        self._native_density_session_active = True
        self._native_density_paused_for_navigation = False
        self._native_density_active_system_name = system_obj.name
        self._track_touched_system(system_obj)
        _keep_active_system_object(context, system_obj)
        _deselect_all_world_paint_objects(context)
        if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
            _shift_delete_debug_log(
                "begin_native_session.delete_exit",
                context,
                self,
                force=True,
                system=getattr(system_obj, "name", ""),
                brush=getattr(brush, "name", ""),
                tool_ok=tool_ok,
                cursor_ok=cursor_ok,
            )
        _native_brush_debug_log("begin_native_session.exit", context, self, force=True, system=system_obj.name, brush=getattr(brush, "name", ""), tool_ok=tool_ok, cursor_ok=cursor_ok)
        return True

    def _brush_depth_location(self, system_obj=None, target_info=None):
        if target_info is None:
            target_info = _preview_target_info(self)
        anchor = _target_depth_anchor(target_info, self.locked_target, self.preview_target, self.hover_target)
        if anchor is not None:
            return anchor
        system_obj = system_obj if system_obj is not None else self._current_system()
        return _brush_depth_location_from_system(system_obj)

    def _brush_screen_depth_location(self, system_obj=None, target_info=None):
        if target_info is None:
            target_info = _preview_target_info(self)

        if target_info is not None:
            location = target_info.get("location")
            if location is not None:
                copied_location = _safe_copy_target_vector(location)
                if copied_location is not None:
                    return copied_location

        return self._brush_depth_location(system_obj=system_obj, target_info=target_info)

    def _effective_brush_radius(self, context, *, depth_location=None, mouse_coord=None):
        return max(WORLD_MIN_OPERATION_RADIUS, self.brush_radius_setting)

    def _sync_effective_brush_radius(self, context, *, depth_location=None, mouse_coord=None):
        self.brush_radius = self._effective_brush_radius(
            context,
            depth_location=depth_location,
            mouse_coord=mouse_coord,
        )

    def _restore_selection(self, context):
        try:
            _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass

        try:
            selected_objects = list(context.selected_objects)
        except Exception:
            selected_objects = []
        for obj in selected_objects:
            try:
                obj.select_set(False)
            except Exception:
                pass

        for name in self._selection_names:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                try:
                    obj.select_set(True)
                except Exception:
                    pass

        if self._active_name:
            active_obj = bpy.data.objects.get(self._active_name)
            if active_obj is not None:
                try:
                    context.view_layer.objects.active = active_obj
                except Exception:
                    return

    def _set_pick_preview_as_only_selection(self, context, picked_obj, *, active_obj=None):
        if picked_obj is None or context is None:
            return
        try:
            selected_objects = list(context.selected_objects)
        except Exception:
            selected_objects = []
        for obj in selected_objects:
            if obj == picked_obj:
                continue
            try:
                obj.select_set(False)
            except Exception:
                pass
        try:
            picked_obj.select_set(True)
        except Exception:
            pass
        try:
            context.view_layer.objects.active = active_obj if active_obj is not None else picked_obj
        except Exception:
            pass

    def _restore_pick_selection_preview_object(self, context=None, *, restore_active=True):
        preview_name = getattr(self, "_selection_preview_name", "")
        if not preview_name:
            return
        context = context or bpy.context
        obj = bpy.data.objects.get(preview_name)
        if not restore_active:
            self._set_pick_preview_as_only_selection(context, obj)
            self._selection_preview_name = ""
            self._selection_preview_was_selected = False
            self._selection_preview_previous_active_name = ""
            self._selection_preview_previous_selection_names = []
            return

        try:
            for selected_obj in list(context.selected_objects):
                selected_obj.select_set(False)
        except Exception:
            pass
        for selected_name in getattr(self, "_selection_preview_previous_selection_names", []) or []:
            selected_obj = bpy.data.objects.get(selected_name)
            if selected_obj is None:
                continue
            try:
                selected_obj.select_set(True)
            except Exception:
                pass

        if obj is not None and not getattr(self, "_selection_preview_previous_selection_names", None):
            try:
                obj.select_set(bool(getattr(self, "_selection_preview_was_selected", False)))
            except Exception:
                pass

        try:
            previous_active_name = getattr(self, "_selection_preview_previous_active_name", "")
            previous_active = bpy.data.objects.get(previous_active_name) if previous_active_name else None
            if previous_active is not None and previous_active.name in context.view_layer.objects:
                context.view_layer.objects.active = previous_active
        except Exception:
            pass

        self._selection_preview_name = ""
        self._selection_preview_was_selected = False
        self._selection_preview_previous_active_name = ""
        self._selection_preview_previous_selection_names = []

    def _restore_pick_selection_preview(self, context=None, *, restore_cage=True, restore_active=True):
        self._selection_preview_token += 1
        self._restore_pick_selection_preview_object(context, restore_active=restore_active)
        if restore_cage and getattr(self, "_selection_preview_had_cage_overlay", False):
            preview_overlay = getattr(self, "_selection_preview_overlay", None)
            try:
                preview_overlay.show_sculpt_curves_cage = bool(getattr(self, "_selection_preview_was_cage_visible", False))
            except Exception:
                pass
        if restore_cage and getattr(self, "_selection_preview_had_show_overlays", False):
            preview_overlay = getattr(self, "_selection_preview_overlay", None)
            try:
                preview_overlay.show_overlays = bool(getattr(self, "_selection_preview_was_show_overlays", True))
            except Exception:
                pass
        self._selection_preview_active = False
        self._selection_preview_cage_until = 0.0
        self._selection_preview_overlay = None
        self._selection_preview_had_cage_overlay = False
        self._selection_preview_was_cage_visible = False
        self._selection_preview_had_show_overlays = False
        self._selection_preview_was_show_overlays = False

    def _preview_pick_selection(self, context, picked_obj, *, hold=False, active_obj=None):
        if picked_obj is None or context.view_layer is None:
            return None

        picked_name = _safe_rna_name(picked_obj)
        if not picked_name:
            return None
        same_preview = (
            bool(getattr(self, "_selection_preview_active", False)) and
            getattr(self, "_selection_preview_name", "") == picked_name
        )

        self._selection_preview_token += 1
        preview_token = self._selection_preview_token
        preview_duration = 0.4

        if not same_preview:
            if getattr(self, "_selection_preview_active", False):
                self._restore_pick_selection_preview_object(context)
            else:
                _area, _region, preview_space = _view3d_area_data(context, self._invoke_area_pointer)
                if preview_space is None:
                    preview_space = getattr(context, "space_data", None)
                preview_overlay = getattr(preview_space, "overlay", None) if preview_space is not None else None
                try:
                    self._selection_preview_had_cage_overlay = (
                        preview_overlay is not None and
                        hasattr(preview_overlay, "show_sculpt_curves_cage")
                    )
                    self._selection_preview_had_show_overlays = (
                        preview_overlay is not None and
                        hasattr(preview_overlay, "show_overlays")
                    )
                    self._selection_preview_was_cage_visible = (
                        bool(preview_overlay.show_sculpt_curves_cage)
                        if self._selection_preview_had_cage_overlay
                        else False
                    )
                    self._selection_preview_was_show_overlays = (
                        bool(preview_overlay.show_overlays)
                        if self._selection_preview_had_show_overlays
                        else True
                    )
                    self._selection_preview_overlay = preview_overlay
                except Exception:
                    self._selection_preview_had_cage_overlay = False
                    self._selection_preview_was_cage_visible = False
                    self._selection_preview_had_show_overlays = False
                    self._selection_preview_was_show_overlays = False
                    self._selection_preview_overlay = None

            try:
                self._selection_preview_was_selected = picked_obj.select_get()
            except Exception:
                self._selection_preview_was_selected = False
            try:
                current_active = context.view_layer.objects.active
                self._selection_preview_previous_active_name = current_active.name if current_active is not None else ""
            except Exception:
                self._selection_preview_previous_active_name = ""
            try:
                self._selection_preview_previous_selection_names = [
                    obj.name for obj in context.selected_objects
                ]
            except Exception:
                self._selection_preview_previous_selection_names = []
            self._set_pick_preview_as_only_selection(context, picked_obj, active_obj=active_obj)
            self._selection_preview_name = picked_name
            self._selection_preview_active = True
        else:
            self._set_pick_preview_as_only_selection(context, picked_obj, active_obj=active_obj)

        if getattr(self, "_selection_preview_had_cage_overlay", False):
            preview_overlay = getattr(self, "_selection_preview_overlay", None)
            try:
                preview_overlay.show_sculpt_curves_cage = True
            except Exception:
                self._selection_preview_had_cage_overlay = False
            self._selection_preview_cage_until = (
                time.perf_counter() + 3600.0
                if hold
                else time.perf_counter() + preview_duration
            )
        if hold and getattr(self, "_selection_preview_had_show_overlays", False):
            preview_overlay = getattr(self, "_selection_preview_overlay", None)
            try:
                preview_overlay.show_overlays = True
            except Exception:
                self._selection_preview_had_show_overlays = False

        if hold:
            return preview_token

        def _restore_preview_selection():
            operator = _world_operator()
            if operator is None or getattr(operator, "_selection_preview_token", -1) != preview_token:
                return None
            operator._restore_pick_selection_preview(bpy.context, restore_cage=True)
            return None

        try:
            bpy.app.timers.register(_restore_preview_selection, first_interval=preview_duration)
        except Exception:
            _restore_preview_selection()
        return preview_token

    def _begin_entry_source_preview(self, context, picked_obj, *, hold=False):
        if picked_obj is None:
            return False
        self._prepare_pick_source_object_mode(context)
        preview_token = self._preview_pick_selection(context, picked_obj, hold=True)
        if preview_token is None:
            self._entry_source_preview_allows_hold_pick = False
            self._restore_pick_source_paint_ui(context)
            return False
        self._entry_source_preview_active = True
        self._entry_source_preview_allows_hold_pick = bool(hold)
        self._entry_source_preview_hold_start_time = time.perf_counter() if hold else 0.0
        if hold:
            return True

        def _finish_entry_source_preview():
            operator = _world_operator()
            if (
                operator is None
                or not getattr(operator, "_entry_source_preview_active", False)
                or getattr(operator, "_selection_preview_token", -1) != preview_token
            ):
                return None
            operator._end_entry_source_preview(bpy.context)
            return None

        try:
            bpy.app.timers.register(_finish_entry_source_preview, first_interval=0.4)
        except Exception:
            self._end_entry_source_preview(context)
        return True

    def _end_entry_source_preview(self, context, event=None):
        if not getattr(self, "_entry_source_preview_active", False):
            return False
        area, region, space = _view3d_area_data(context, self._invoke_area_pointer)
        current_area = getattr(context, "area", None)
        try:
            needs_override = (
                area is not None
                and region is not None
                and space is not None
                and (
                    current_area is None
                    or current_area.as_pointer() != area.as_pointer()
                    or getattr(getattr(context, "region", None), "type", "") != 'WINDOW'
                )
            )
        except Exception:
            needs_override = False
        if needs_override:
            try:
                with context.temp_override(area=area, region=region, space_data=space):
                    return self._end_entry_source_preview(bpy.context, event)
            except Exception:
                pass
        self._entry_source_preview_active = False
        self._entry_source_preview_allows_hold_pick = False
        self._entry_source_preview_hold_start_time = 0.0
        self._restore_pick_selection_preview(context, restore_cage=True, restore_active=True)
        _keep_active_system_object(context, self._current_system())
        self._restore_pick_source_paint_ui(context, event)
        return True

    def _sync_scale_slider(self, context):
        active_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
        value = _modifier_scale_value(active_system) if active_system else 1.0
        if hasattr(context.window_manager, "secret_paint_world_asset_scale"):
            self._syncing_slider = True
            context.window_manager.secret_paint_world_asset_scale = value
            self._syncing_slider = False
        self.last_slider_value = value

    def _sync_brush_controls(self, context, *, force=False):
        if not hasattr(context.window_manager, "secret_paint_world_brush_radius"):
            return
        if not force and self.adjust_mode:
            now = time.perf_counter()
            last_sync_time = float(getattr(self, "_last_brush_control_sync_time", 0.0) or 0.0)
            if (now - last_sync_time) < WORLD_BRUSH_CONTROL_SYNC_INTERVAL:
                return
            self._last_brush_control_sync_time = now
        self._syncing_brush_props = True
        try:
            context.window_manager.secret_paint_world_brush_radius = self.brush_radius_setting
            context.window_manager.secret_paint_world_density_spacing = self.density_spacing
            if hasattr(context.window_manager, "secret_paint_world_density_spacing_coarse"):
                context.window_manager.secret_paint_world_density_spacing_coarse = self.density_spacing
            if hasattr(context.window_manager, "secret_paint_world_brush_strength"):
                if self._tool_uses_brush_strength_adjust():
                    self._sync_brush_strength_from_native_brush(context, ensure=False)
                context.window_manager.secret_paint_world_brush_strength = self.brush_strength
            shared.secret_paint_brush_size_trace_log(
                "world.sync_brush_controls",
                context,
                self,
                force=force,
                wm_radius=self.brush_radius_setting,
                wm_density=self.density_spacing,
                wm_strength=self.brush_strength,
            )
        finally:
            self._syncing_brush_props = False

    def _mark_deferred_brush_settings_dirty(
        self,
        *,
        radius=False,
        density=False,
        native_sync=False,
        context=None,
        schedule=False,
    ):
        self._deferred_brush_radius_store_dirty = bool(
            self._deferred_brush_radius_store_dirty or radius
        )
        self._deferred_density_spacing_store_dirty = bool(
            self._deferred_density_spacing_store_dirty or density
        )
        self._deferred_native_brush_sync_dirty = bool(
            self._deferred_native_brush_sync_dirty or native_sync
        )
        if schedule:
            self._schedule_deferred_brush_settings_flush(context)

    def _schedule_deferred_brush_settings_flush(self, context=None):
        self._deferred_brush_settings_flush_token += 1
        flush_token = self._deferred_brush_settings_flush_token
        operator = self

        def _flush_deferred_brush_settings():
            active_operator = _world_operator()
            if active_operator is not operator:
                return None
            if flush_token != getattr(operator, "_deferred_brush_settings_flush_token", 0):
                return None
            try:
                operator._flush_deferred_brush_settings(bpy.context)
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(
                _flush_deferred_brush_settings,
                first_interval=WORLD_DEFERRED_BRUSH_SETTINGS_FLUSH_SECONDS,
            )
        except Exception:
            self._flush_deferred_brush_settings(context or bpy.context)

    def _flush_deferred_brush_settings(self, context=None, *, sync_native=True):
        context = context or bpy.context
        radius_dirty = bool(getattr(self, "_deferred_brush_radius_store_dirty", False))
        density_dirty = bool(getattr(self, "_deferred_density_spacing_store_dirty", False))
        native_dirty = bool(getattr(self, "_deferred_native_brush_sync_dirty", False))
        shared.secret_paint_brush_size_trace_log(
            "world.flush_deferred_brush_settings.enter",
            context,
            self,
            radius_dirty=radius_dirty,
            density_dirty=density_dirty,
            native_dirty=native_dirty,
            sync_native=sync_native,
        )
        if not (radius_dirty or density_dirty or native_dirty):
            return False

        active_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
        density_store_handled_by_native_sync = (
            sync_native and
            native_dirty and
            self._native_density_session_active and
            active_system is not None and
            self._active_native_brush_type() == "DENSITY"
        )
        if radius_dirty:
            _store_operator_brush_radius(self, context)
        if density_dirty and not density_store_handled_by_native_sync:
            _store_system_density_spacing(active_system, self.density_spacing)
        if sync_native and native_dirty and self._native_density_session_active:
            synced_brush = self._sync_native_density_brush(context, system_obj=active_system)
            if synced_brush is not None and active_system is not None:
                if self.tool_id == WORLD_TOOL_DENSITY:
                    self._apply_density_spacing_to_native_brush(context)
                    self._schedule_density_spacing_native_brush_sync(active_system)
                self._mark_native_density_synced(self._native_density_sync_key(context, active_system))

        self._deferred_brush_radius_store_dirty = False
        self._deferred_density_spacing_store_dirty = False
        self._deferred_native_brush_sync_dirty = False
        self._sync_brush_controls(context, force=True)
        shared.secret_paint_brush_size_trace_log(
            "world.flush_deferred_brush_settings.exit",
            context,
            self,
            radius_dirty=radius_dirty,
            density_dirty=density_dirty,
            native_dirty=native_dirty,
            synced_brush=bool(sync_native and native_dirty and self._native_density_session_active),
        )
        return True

    def _track_touched_system(self, system_obj):
        if system_obj is None or not _is_secret_paint_system(system_obj):
            return
        try:
            self._touched_system_names.add(system_obj.name)
        except Exception:
            self._touched_system_names = {system_obj.name}

    def _note_session_target_for_system(self, system_obj):
        target_key = _world_target_key_from_system(system_obj)
        if target_key and not getattr(self, "_session_initial_target_key", ""):
            self._session_initial_target_key = target_key
        return target_key

    def _register_session_created_system(self, system_obj, *, target_kind, surface_obj, target_owner=None):
        if system_obj is None:
            return
        try:
            self._session_created_system_names.add(system_obj.name)
        except Exception:
            self._session_created_system_names = {system_obj.name}
        try:
            self._session_empty_auto_delete_system_names.add(system_obj.name)
        except Exception:
            self._session_empty_auto_delete_system_names = {system_obj.name}

    def _set_active_system(self, context, system_obj):
        if system_obj is None:
            return
        _ensure_world_system_surface_uvs(self, context, system_obj)
        self._track_touched_system(system_obj)
        self._note_session_target_for_system(system_obj)
        previous_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
        if previous_system is not None and previous_system != system_obj:
            _store_operator_or_system_brush_radius(
                self,
                context,
                previous_system,
                self.brush_radius_setting,
            )
            _store_system_density_spacing(previous_system, self.density_spacing)
        self.active_system_name = system_obj.name
        _keep_active_system_object(context, system_obj)
        existing_align_to_normal = _get_system_align_to_normal(system_obj)
        if existing_align_to_normal is None:
            _sync_system_align_to_normal(system_obj, self.align_to_normal)
        else:
            self.align_to_normal = existing_align_to_normal
        self.density_spacing = _stored_system_density_spacing(
            system_obj,
            fallback=self.density_spacing,
        )
        _store_system_density_spacing(system_obj, self.density_spacing)
        self.brush_radius_setting = _stored_operator_brush_radius(
            self,
            context,
            system_obj,
            fallback=self.brush_radius_setting,
        )
        shared.secret_paint_brush_size_trace_log(
            "world.set_active_system.stored_radius",
            context,
            self,
            system_obj=system_obj,
            previous_system=previous_system,
        )
        self._sync_effective_brush_radius(context, depth_location=self._brush_screen_depth_location(system_obj))
        self._sync_scale_slider(context)
        self._sync_brush_controls(context)
        if self._density_uses_native_ui() and self.tool_id == WORLD_TOOL_DENSITY:
            self._apply_density_spacing_to_native_brush(context)
            self._schedule_density_spacing_native_brush_sync(system_obj)
        if self._native_density_session_active and self._native_density_active_system_name == system_obj.name:
            self._sync_native_density_brush(context, system_obj=system_obj)
            if self.tool_id == WORLD_TOOL_DENSITY:
                self._apply_density_spacing_to_native_brush(context)
                self._schedule_density_spacing_native_brush_sync(system_obj)

    def _set_active_system_preserve_brush_controls(self, context, system_obj):
        radius_setting = float(getattr(self, "brush_radius_setting", 0.5) or 0.5)
        radius = float(getattr(self, "brush_radius", radius_setting) or radius_setting)
        density_spacing = float(getattr(self, "density_spacing", 0.1) or 0.1)
        self._set_active_system(context, system_obj)
        self.brush_radius_setting = max(0.05, radius_setting)
        self.brush_radius = max(WORLD_MIN_OPERATION_RADIUS, radius)
        self.density_spacing = _density_spacing_value(density_spacing, fallback=self.density_spacing)
        self._sync_effective_brush_radius(
            context,
            depth_location=self._brush_screen_depth_location(system_obj),
        )
        _store_operator_brush_radius(self, context)
        _store_system_density_spacing(system_obj, self.density_spacing)
        self._sync_brush_controls(context, force=True)
        if self._native_density_session_active and self._native_density_active_system_name == system_obj.name:
            self._sync_native_density_brush(context, system_obj=system_obj)
            if self.tool_id == WORLD_TOOL_DENSITY:
                self._apply_density_spacing_to_native_brush(context)
                self._schedule_density_spacing_native_brush_sync(system_obj)

    def _set_active_system_lightweight(self, context, system_obj):
        if system_obj is None:
            return
        _ensure_world_system_surface_uvs(self, context, system_obj)
        self._track_touched_system(system_obj)
        self._note_session_target_for_system(system_obj)
        self.active_system_name = system_obj.name
        existing_align_to_normal = _get_system_align_to_normal(system_obj)
        if existing_align_to_normal is not None:
            self.align_to_normal = existing_align_to_normal
        self.density_spacing = _stored_system_density_spacing(
            system_obj,
            fallback=self.density_spacing,
        )
        try:
            stored_radius = _stored_operator_brush_radius(
                self,
                context,
                system_obj,
                fallback=self.brush_radius_setting,
            )
        except Exception:
            stored_radius = None
        if stored_radius is not None:
            try:
                old_setting = self.brush_radius_setting
                self.brush_radius_setting = max(0.05, float(stored_radius))
                self._sync_effective_brush_radius(
                    context,
                    depth_location=self._brush_screen_depth_location(system_obj),
                    mouse_coord=self.hover_mouse_region,
                )
                shared.secret_paint_brush_size_trace_log(
                    "world.set_active_system_lightweight.stored_radius",
                    context,
                    self,
                    system_obj=system_obj,
                    brush_prop=WORLD_PAINT_BRUSH_RADIUS_PROP,
                    stored_radius=stored_radius,
                    old_setting=old_setting,
                    new_setting=self.brush_radius_setting,
                )
            except Exception:
                pass
        if self._density_uses_native_ui() and self.tool_id == WORLD_TOOL_DENSITY:
            self._apply_density_spacing_to_native_brush(context)
            self._schedule_density_spacing_native_brush_sync(system_obj)

    def _expected_native_density_size_state(self, context=None, *, system_obj=None):
        try:
            radius = float(getattr(self, "brush_radius", 0.0) or 0.0)
        except Exception:
            radius = 0.0
        return ("WORLD_RADIUS", max(WORLD_MIN_OPERATION_RADIUS, radius))

    def _remember_confirmed_native_density_size_state(self, context=None, *, system_obj=None, reason=""):
        try:
            state = self._expected_native_density_size_state(context, system_obj=system_obj)
        except Exception:
            state = None
        self._native_density_confirmed_size_state = state
        shared.secret_paint_brush_size_trace_log(
            "world.native_size_confirmed_state.remember",
            context,
            self,
            state=state,
            reason=reason,
            system_obj=system_obj,
        )
        return state

    def _ensure_wire_bounds_surfaces_for_source_system(self, context, system_obj):
        if (
            not _is_secret_paint_system(system_obj) or
            self.allow_wire_bounds_surfaces or
            not _system_target_needs_wire_bounds_surfaces(system_obj)
        ):
            return False

        toggled = False
        try:
            result = bpy.ops.secret.world_paint_toggle_wire_bounds_surfaces()
            toggled = 'FINISHED' in result
        except Exception:
            toggled = False

        if not self.allow_wire_bounds_surfaces:
            self.allow_wire_bounds_surfaces = True
            preferences = _addon_preferences(context)
            if preferences is not None:
                preferences.allow_world_paint_wire_bounds_surfaces = True
            _tag_redraw_view3d_areas(context)
        return toggled or self.allow_wire_bounds_surfaces

    def _switch_source_data(self, context, source_data, *, status_label="", reset_target_state=False):
        if not source_data:
            return False
        if self._density_uses_native_ui() and self.tool_id == WORLD_TOOL_DENSITY:
            try:
                self._commit_active_native_density_adjust_result(context)
            except Exception:
                pass
        if self._native_density_session_active:
            self._finish_native_density_session(context, restore_selection=False)

        previous_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
        if previous_system is not None:
            _store_operator_or_system_brush_radius(
                self,
                context,
                previous_system,
                self.brush_radius_setting,
            )
            _store_system_density_spacing(previous_system, self.density_spacing)

        self.source_data = source_data
        self._live_source_snapshot = _source_data_snapshot(source_data)
        self.active_system_name = ""
        self.active_curve_draw_name = ""
        source_origin = source_data.get("origin_object")
        source_origin_is_system = self._source_data_is_system_source(source_data)
        if source_origin_is_system:
            self._ensure_wire_bounds_surfaces_for_source_system(context, source_origin)
        source_system_target = None
        if self.surface_lock:
            if source_origin_is_system:
                source_system_target = _target_info_from_system(
                    context,
                    source_origin,
                    allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                    ignore_display_type_block=True,
                )
                reset_target_state = source_system_target is None
                self._surface_lock_retarget_pending = source_system_target is None
            else:
                if not self._locked_target_infos():
                    self._restore_scene_locked_target(context)
                if self._locked_target_infos():
                    reset_target_state = False
                    self._surface_lock_retarget_pending = False
                else:
                    reset_target_state = True
                    self._surface_lock_retarget_pending = True
        source_starts_bezier = _source_data_should_start_bezier_tool(source_data)
        if source_starts_bezier:
            self.tool_id = WORLD_TOOL_BEZIER
        if _is_secret_paint_source_system(source_origin):
            self.density_spacing = _stored_system_density_spacing(
                source_origin,
                fallback=self.density_spacing,
            )
            self.brush_radius_setting = _stored_operator_brush_radius(
                self,
                context,
                source_origin,
                fallback=self.brush_radius_setting,
            )
        if reset_target_state or source_starts_bezier:
            self.preview_target = None
            self.hover_target = None
            self.locked_target = None
            if reset_target_state:
                self.locked_targets = []
            self.last_hover_key = ""
            self._sync_effective_brush_radius(context)
            self._configure_tool(context)
        elif source_system_target is not None:
            locked_targets = self._locked_target_infos() if self.surface_lock else []
            source_key = _target_key(source_system_target)
            matching_locked_target = next(
                (target_info for target_info in locked_targets if _target_key(target_info) == source_key),
                None,
            )
            if matching_locked_target is not None:
                self.locked_target = _copy_target_info(matching_locked_target)
                self._surface_lock_retarget_pending = False
                self._activate_hover_target(context, self.locked_target)
            else:
                self._set_locked_target(context, source_system_target, activate=True)
        else:
            self.last_hover_key = ""
            if self.hover_target is not None:
                self._activate_hover_target(context, self.hover_target)
            elif self.surface_lock and self._locked_target_infos():
                self.locked_target = self.locked_target or self._locked_target_infos()[0]
                self._activate_hover_target(context, self.locked_target)
            else:
                self._sync_effective_brush_radius(context)
                self._configure_tool(context)
        self._sync_brush_controls(context)
        self._sync_scale_slider(context)
        if not status_label:
            status_label = _world_source_label_info(source_data)[0]
        try:
            context.workspace.status_text_set(
                text=f"Secret Paint Mode: {status_label} source picked. LMB paint, RMB remove, paint key picks source, F size, Alt+F density/strength"
            )
        except Exception:
            pass
        _tag_redraw_view3d_areas(context)
        return True

    def _switch_source_to_system(self, context, system_obj):
        return self._switch_source_data(context, _source_data_from_system(system_obj), status_label=system_obj.name)

    def _switch_source_to_object(self, context, source_obj):
        return self._switch_source_data(
            context,
            _source_data_from_object_pick(self, context, source_obj),
            status_label=source_obj.name,
            reset_target_state=True,
        )

    def _source_data_is_system_source(self, source_data):
        if not isinstance(source_data, dict):
            return False
        return _is_secret_paint_source_system(source_data.get("origin_object"))

    def _activate_picked_source_system(self, context, source_data):
        if not self._source_data_is_system_source(source_data):
            return False
        system_obj = source_data.get("origin_object")
        self._ensure_wire_bounds_surfaces_for_source_system(context, system_obj)
        self._defer_native_idle_session = not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE
        target_info = _target_info_from_system(
            context,
            system_obj,
            allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
            ignore_display_type_block=self.surface_lock,
        )
        if target_info is not None:
            self._activate_hover_target(context, target_info)
            if self.surface_lock:
                locked_targets = self._locked_target_infos()
                target_key = _target_key(target_info)
                matching_locked_target = next(
                    (locked_target for locked_target in locked_targets if _target_key(locked_target) == target_key),
                    None,
                )
                if matching_locked_target is not None:
                    self.locked_target = _copy_target_info(matching_locked_target)
                    self._surface_lock_retarget_pending = False
                else:
                    self._set_locked_target(context, target_info)
        if _is_secret_paint_system(system_obj):
            self._set_active_system(context, system_obj)
        if (
            WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE and
            self._density_uses_native_ui() and
            target_info is not None
        ):
            self._ensure_idle_native_density_session(context)
        return True

    def _restore_previous_source_pick(self, context):
        while self._source_switch_history:
            previous_source = _source_data_from_snapshot(self._source_switch_history.pop())
            if previous_source is None:
                continue
            picked_obj = previous_source.get("origin_object") or previous_source.get("brush_object")
            if self._switch_source_data(
                context,
                previous_source,
                reset_target_state=(
                    previous_source.get("origin_kind") == "OBJECT" and
                    not self._source_data_is_system_source(previous_source)
                ),
            ):
                if (
                    previous_source.get("origin_kind") == "OBJECT"
                    and not self._source_data_is_system_source(previous_source)
                    and not (self.surface_lock and self._surface_lock_retarget_pending)
                ):
                    self._refresh_hover_target_from_stored_mouse(context, commit=True)
                    if self._density_uses_native_ui():
                        self._ensure_idle_native_density_session(context)
                self._preview_pick_selection(context, picked_obj)
                return True
        return False

    def _source_pick_under_brush(self, context, event=None):
        override = None
        if event is not None:
            override, mouse_coord = _event_view3d_window_override_and_mouse(
                context,
                event,
                self._invoke_area_pointer,
            )
            if mouse_coord is not None:
                self.hover_mouse_region = mouse_coord
        elif self.hover_mouse_region is not None:
            mouse_coord = self.hover_mouse_region
        else:
            mouse_coord = None

        if mouse_coord is not None:
            self.hover_mouse_region = mouse_coord
        else:
            return None, None

        raycast_context = context
        if override is not None:
            try:
                with context.temp_override(**override):
                    picked_obj = _raycast_source_object(bpy.context, mouse_coord)
                    if picked_obj is None:
                        return None, None
                    source_data = _source_data_from_object_pick(self, bpy.context, picked_obj)
                    if source_data is None:
                        return None, None
                    return source_data, picked_obj
            except Exception:
                raycast_context = context

        picked_obj = _raycast_source_object(raycast_context, mouse_coord)
        if picked_obj is None:
            return None, None

        source_data = _source_data_from_object_pick(self, raycast_context, picked_obj)
        if source_data is None:
            return None, None
        return source_data, picked_obj

    def _preview_object_for_source_pick(self, source_data, picked_obj):
        if not source_data:
            return picked_obj
        if source_data.get("origin_kind") == "OBJECT":
            origin_object = source_data.get("origin_object")
            return origin_object if _safe_rna_name(origin_object) else picked_obj
        curve_obj = _source_data_curve_object(source_data)
        if curve_obj is not None and _safe_object_type(picked_obj) == "CURVE":
            return curve_obj
        origin_object = source_data.get("origin_object")
        return origin_object if _safe_rna_name(origin_object) else picked_obj

    def _active_object_for_source_pick(self, source_data, picked_obj):
        if not source_data:
            return picked_obj
        origin_object = source_data.get("origin_object")
        if source_data.get("origin_kind") == "OBJECT" and _safe_rna_name(origin_object):
            return origin_object
        return origin_object if _safe_rna_name(origin_object) else picked_obj

    def _object_source_immediate_target(self, context):
        if self.surface_lock:
            if not self._locked_target_infos():
                self._restore_scene_locked_target(context)
            locked_targets = self._locked_target_infos()
            if locked_targets:
                copied = _copy_target_info(self.locked_target or locked_targets[0])
                if copied is not None:
                    return copied

        for target_info in (self.hover_target, self.preview_target):
            copied = _copy_target_info(target_info)
            if copied is not None:
                return copied

        for system_name in (
            getattr(self, "active_system_name", ""),
            getattr(self, "_native_density_active_system_name", ""),
        ):
            if not system_name:
                continue
            target_info = _target_info_from_system(
                context,
                bpy.data.objects.get(system_name),
                allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                ignore_display_type_block=self.surface_lock,
            )
            copied = _copy_target_info(target_info)
            if copied is not None:
                return copied
        return None

    def _activate_object_source_target_system(self, context, target_info):
        target_info = _copy_target_info(target_info)
        if target_info is None:
            return False
        self._activate_hover_target(context, target_info)
        system_obj = self._ensure_current_system(context, create=True)
        if system_obj is None:
            return False
        if self._density_uses_native_ui() and self.tool_id != WORLD_TOOL_BEZIER:
            self._defer_native_idle_session = not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE
            if WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
                self._ensure_idle_native_density_session(context)
            else:
                self._sync_tool_ui_mode(context)
        else:
            self._configure_tool(context)
        self._sync_brush_controls(context)
        self._sync_scale_slider(context)
        _tag_redraw_view3d_areas(context)
        return True

    def _commit_source_pick(self, context, source_data, picked_obj, event=None, *, preview=True):
        if not source_data:
            return False

        current_source_key = _source_data_key(self.source_data)
        next_source_key = _source_data_key(source_data)
        source_is_system_source = self._source_data_is_system_source(source_data)
        object_source = (
            source_data.get("origin_kind") == "OBJECT"
            and not source_is_system_source
            and not _source_data_should_start_bezier_tool(source_data)
        )
        immediate_target = self._object_source_immediate_target(context) if object_source else None
        switched = False
        if current_source_key != next_source_key:
            current_source = _source_data_snapshot(self.source_data)
            switched = self._switch_source_data(
                context,
                source_data,
                status_label=_safe_rna_name(picked_obj),
                reset_target_state=object_source and immediate_target is None,
            )
            if switched and source_is_system_source:
                self._activate_picked_source_system(context, source_data)
            elif switched and object_source:
                if immediate_target is not None:
                    self._activate_object_source_target_system(context, immediate_target)
                elif not (self.surface_lock and self._surface_lock_retarget_pending):
                    if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                        self._update_hover_target(context, event, commit=True)
                    else:
                        self._refresh_hover_target_from_stored_mouse(context, commit=True)
                    if self._density_uses_native_ui():
                        self._ensure_idle_native_density_session(context, event=event)
            if switched and current_source is not None:
                self._source_switch_history.append(current_source)
        else:
            switched = True
            if source_is_system_source:
                self._activate_picked_source_system(context, source_data)
            elif object_source and immediate_target is not None:
                self._activate_object_source_target_system(context, immediate_target)
            elif object_source and self.surface_lock:
                if not self._locked_target_infos():
                    self._restore_scene_locked_target(context)
                if self._locked_target_infos():
                    self.locked_target = self.locked_target or self._locked_target_infos()[0]
                    self._surface_lock_retarget_pending = False
                    self._activate_hover_target(context, self.locked_target)
                else:
                    if self._native_density_session_active:
                        self._finish_native_density_session(context, restore_selection=False)
                    self.preview_target = None
                    self.hover_target = None
                    self.locked_target = None
                    self.locked_targets = []
                    self.last_hover_key = ""
                    self.active_system_name = ""
                    self._surface_lock_retarget_pending = True
                    self._sync_effective_brush_radius(context)
                    self._configure_tool(context)

        if switched and preview:
            self._preview_pick_selection(
                context,
                self._preview_object_for_source_pick(source_data, picked_obj),
                active_obj=self._active_object_for_source_pick(source_data, picked_obj),
            )
        return switched

    def _pick_source_under_brush(self, context, event=None, *, commit=True, hold_preview=False):
        source_data, picked_obj = self._source_pick_under_brush(context, event)
        if source_data is None:
            if not commit and hold_preview:
                last_hit_time = float(getattr(self, "_pick_source_hold_last_hit_time", 0.0) or 0.0)
                if (
                    getattr(self, "_pick_source_hold_source_data", None)
                    and (time.perf_counter() - last_hit_time) < 0.18
                ):
                    return True
                self._pick_source_hold_source_data = None
                self._pick_source_hold_picked_name = ""
                self._pick_source_hold_source_key = None
                self._restore_pick_selection_preview(context, restore_cage=True)
            return False

        if not commit:
            source_key = _source_data_key(source_data)
            self._pick_source_hold_last_hit_time = time.perf_counter()
            if source_key != getattr(self, "_pick_source_hold_source_key", None):
                self._pick_source_hold_source_key = source_key
                self._pick_source_hold_source_data = source_data
                self._pick_source_hold_picked_name = _safe_rna_name(picked_obj)
                self._preview_pick_selection(
                    context,
                    self._preview_object_for_source_pick(source_data, picked_obj),
                    hold=hold_preview,
                    active_obj=self._active_object_for_source_pick(source_data, picked_obj),
                )
            elif hold_preview:
                return True
            return True

        return self._commit_source_pick(context, source_data, picked_obj, event, preview=True)

    def _event_is_in_world_paint_view(self, context, event):
        region_context = _event_region_context(context, event, self._invoke_area_pointer)
        area = region_context["area"]
        return bool(area is not None and area.type == 'VIEW_3D' and region_context["in_window_region"])

    def _event_is_in_world_paint_area(self, context, event):
        region_context = _event_region_context(context, event, self._invoke_area_pointer)
        area = region_context["area"]
        if area is not None:
            return bool(area.type == 'VIEW_3D' and region_context["in_invoke_area"])
        area = getattr(context, "area", None)
        if area is None or getattr(area, "type", "") != 'VIEW_3D':
            return False
        try:
            return not self._invoke_area_pointer or area.as_pointer() == self._invoke_area_pointer
        except Exception:
            return True

    def _prepare_pick_source_object_mode(self, context):
        if not getattr(self, "_pick_source_hold_restore_mode", ""):
            self._pick_source_hold_restore_mode = getattr(context, "mode", "") or ""
        if self._native_density_session_active:
            self._finish_native_density_session(context, restore_selection=False)
        if self.adjust_mode:
            self._end_adjust(context)
        if self.stroke_active:
            self._finish_stroke(context, None)
        self._remove_draw_handlers()
        try:
            self._set_native_os_cursor_hidden(context, False)
            context.window.cursor_modal_restore()
        except Exception:
            pass
        try:
            if getattr(context, "mode", "") != 'OBJECT':
                _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text="Secret Paint Mode: pick source under mouse, release paint key to resume")
        except Exception:
            pass
        _tag_redraw_view3d_areas(context)

    def _restore_pick_source_paint_ui(self, context, event=None):
        self._pick_source_hold_restore_mode = ""
        if not self._running:
            return
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
        if self._surface_lock_waiting_for_target():
            self.preview_target = None
            self.hover_target = None
            self.last_hover_key = ""
            self._sync_effective_brush_radius(context, mouse_coord=self.hover_mouse_region)
            self._sync_tool_ui_mode(context)
            return
        if self.hover_target is None:
            self._refresh_hover_target_from_stored_mouse(context, commit=True)
        if self._density_uses_native_ui() and self.hover_target is not None:
            if self._ensure_idle_native_density_session(context, event=event):
                return
        self._sync_tool_ui_mode(context)

    def _begin_pick_source_hold(self, context, event):
        self._prepare_pick_source_object_mode(context)
        self._pick_source_hold_active = True
        self._pick_source_hold_source_data = None
        self._pick_source_hold_picked_name = ""
        self._pick_source_hold_source_key = None
        self._pick_source_hold_last_mouse = None
        self._pick_source_hold_last_update_time = 0.0
        self._pick_source_hold_last_hit_time = 0.0
        self._update_pick_source_hold(context, event)

    def _update_pick_source_hold(self, context, event):
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            mouse_coord = (event.mouse_region_x, event.mouse_region_y)
            last_mouse = getattr(self, "_pick_source_hold_last_mouse", None)
            if mouse_coord == last_mouse:
                return True
            now = time.perf_counter()
            last_update_time = float(getattr(self, "_pick_source_hold_last_update_time", 0.0) or 0.0)
            if last_mouse is not None and last_update_time > 0.0:
                mouse_delta = math.hypot(mouse_coord[0] - last_mouse[0], mouse_coord[1] - last_mouse[1])
                if (
                    mouse_delta < WORLD_PICK_SOURCE_HOLD_MIN_MOUSE_DELTA_PX
                    and now - last_update_time < WORLD_PICK_SOURCE_HOLD_UPDATE_INTERVAL
                ):
                    return True
            self._pick_source_hold_last_mouse = mouse_coord
            self._pick_source_hold_last_update_time = time.perf_counter()
        return self._pick_source_under_brush(context, event, commit=False, hold_preview=True)

    def _end_pick_source_hold(self, context, event=None, *, commit=True, restore_paint_ui=True):
        if not getattr(self, "_pick_source_hold_active", False):
            return False
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self._update_pick_source_hold(context, event)

        source_data = getattr(self, "_pick_source_hold_source_data", None)
        picked_name = getattr(self, "_pick_source_hold_picked_name", "")
        picked_obj = bpy.data.objects.get(picked_name) if picked_name else None
        active_source_obj = self._active_object_for_source_pick(source_data, picked_obj) if source_data else None
        source_is_system_source = self._source_data_is_system_source(source_data)
        switched = False
        if commit and source_data:
            switched = self._commit_source_pick(context, source_data, picked_obj, event, preview=False)

        self._pick_source_hold_active = False
        self._pick_source_hold_source_data = None
        self._pick_source_hold_picked_name = ""
        self._pick_source_hold_source_key = None
        self._pick_source_hold_last_mouse = None
        self._pick_source_hold_last_update_time = 0.0
        self._pick_source_hold_last_hit_time = 0.0
        self._restore_pick_selection_preview(context, restore_cage=True, restore_active=True)
        if (
            switched and
            source_data and
            source_data.get("origin_kind") == "OBJECT" and
            not source_is_system_source and
            active_source_obj is not None
        ):
            _deselect_all_world_paint_objects(context)
            try:
                context.view_layer.objects.active = active_source_obj
            except Exception:
                pass
        elif switched:
            _keep_active_system_object(context, self._current_system())
        if restore_paint_ui:
            self._restore_pick_source_paint_ui(context, event)
            if (
                switched
                and source_data
                and source_data.get("origin_kind") == "OBJECT"
                and not source_is_system_source
                and active_source_obj is not None
                and getattr(context, "mode", "") != 'SCULPT_CURVES'
            ):
                _deselect_all_world_paint_objects(context)
                try:
                    context.view_layer.objects.active = active_source_obj
                except Exception:
                    pass
        else:
            self._pick_source_hold_restore_mode = ""
        return switched

    def _pick_source_once(self, context, event):
        self._prepare_pick_source_object_mode(context)
        picked = self._pick_source_under_brush(context, event, commit=True, hold_preview=False)
        self._restore_pick_selection_preview(context, restore_cage=True, restore_active=True)
        if picked:
            _keep_active_system_object(context, self._current_system())
        self._restore_pick_source_paint_ui(context, event)
        return picked

    def _active_brush_switch_system(self, context):
        system_obj = self._current_system()
        if _is_secret_paint_system(system_obj):
            return system_obj
        active_obj = getattr(context, "active_object", None)
        if _is_secret_paint_system(active_obj):
            return active_obj
        return None

    def _switch_active_system_brush_from_source(self, context, source_data):
        active_system = self._active_brush_switch_system(context)
        if active_system is None or not source_data:
            return False

        if not _switch_system_brush_source(active_system, source_data):
            return False

        refreshed_source = _source_data_from_system(active_system) or source_data
        self.source_data = refreshed_source
        self._live_source_snapshot = _source_data_snapshot(refreshed_source)
        self.active_system_name = active_system.name
        self.active_curve_draw_name = ""
        self._set_active_system(context, active_system)
        self._configure_tool(context)
        self._sync_effective_brush_radius(context)
        self._sync_brush_controls(context)
        self._sync_scale_slider(context)
        try:
            context.view_layer.update()
        except Exception:
            pass
        try:
            source_label = _world_source_label_info(refreshed_source)[0]
            context.workspace.status_text_set(
                text=f"Secret Paint Mode: {active_system.name} switched to {source_label}. LMB paint, RMB remove, paint key picks source, F size, Alt+F density/strength"
            )
        except Exception:
            pass
        _tag_redraw_view3d_areas(context)
        return True

    def _switch_active_system_brush_under_mouse(self, context, event):
        self._prepare_pick_source_object_mode(context)
        source_data, _picked_obj = self._source_pick_under_brush(context, event)
        switched = self._switch_active_system_brush_from_source(context, source_data)
        self._restore_pick_selection_preview(context, restore_cage=True, restore_active=True)
        self._restore_pick_source_paint_ui(context, event)
        return switched

    def _set_tool(self, context, tool_id, *, sync_workspace=True, preserve_shift=False):
        _native_brush_debug_log("set_tool.enter", context, self, force=True, requested_tool=tool_id, sync_workspace=sync_workspace)
        if tool_id not in WORLD_TOOL_LABELS:
            _native_brush_debug_log("set_tool.invalid", context, self, force=True, requested_tool=tool_id)
            return
        if self.adjust_mode:
            self._commit_active_native_density_adjust_result(context)
            self._end_adjust(context)
        self._leave_native_curves_brush_passthrough(context)
        if tool_id == WORLD_TOOL_BEZIER:
            self.tool_id = WORLD_TOOL_BEZIER
            self._handoff_to_bezier_curve_edit(context, force_new_curve=True)
            _native_brush_debug_log("set_tool.bezier_handoff", context, self, force=True)
            return
        previous_tool_id = self.tool_id
        leaving_bezier_curve_edit = previous_tool_id == WORLD_TOOL_BEZIER and tool_id != WORLD_TOOL_BEZIER
        if (
            self._native_density_session_active and
            tool_id != WORLD_TOOL_DENSITY and
            not _world_tool_uses_native_brush(tool_id)
        ):
            self._finish_native_density_session(context, restore_selection=False)
        original_mode = context.mode if context.mode else ""
        if leaving_bezier_curve_edit:
            _set_world_paint_shortcuts_enabled(context, True)
            if getattr(context, "mode", "") != 'OBJECT':
                try:
                    _mode_set_with_world_toolbar_restored('OBJECT')
                except Exception:
                    pass
        self.tool_id = tool_id
        self._native_density_paused_for_navigation = False
        self._native_density_last_sync_key = None
        self._native_density_last_sync_time = 0.0
        self._native_density_stroke_erase = False
        if not preserve_shift:
            self._shift_key_held = False
            self._shift_delete_tool_active = False
            self._shift_delete_return_tool_id = ""
        requested_brush_type = _curves_brush_type_for_world_tool(tool_id)
        if requested_brush_type:
            self._begin_native_tool_override(requested_brush_type)
            self._mark_requested_native_tool(requested_brush_type)
        else:
            self._mark_requested_native_tool("")
        if sync_workspace:
            self._activate_workspace_tool_for_world_tool(context, tool_id)
        if tool_id == WORLD_TOOL_BEZIER:
            self._activate_bezier_curve_draw_tool(context)
        elif self.hover_target is not None:
            self.last_hover_key = ""
            self._activate_hover_target(context, self.hover_target)
        else:
            self._configure_tool(context)
        if sync_workspace and original_mode != (context.mode if context.mode else ""):
            self._activate_workspace_tool_for_world_tool(context, tool_id)
        if sync_workspace and tool_id == WORLD_TOOL_DELETE:
            self._ensure_shift_delete_preview_session(context)
        if context.mode == 'SCULPT_CURVES' and (
            tool_id == WORLD_TOOL_DENSITY or _world_tool_uses_native_brush(tool_id)
        ):
            brush = self._sync_native_density_brush(context)
            if brush is not None:
                self._activate_native_brush_cursor(context, brush, self._current_system(), defer=True)
        self._sync_brush_controls(context)
        self._sync_tool_ui_mode(context)
        _tag_redraw_view3d_areas(context)
        _native_brush_debug_log("set_tool.exit", context, self, force=True, requested_tool=tool_id, sync_workspace=sync_workspace)

    def _source_system_lock_target(self, context):
        source_data = self.source_data if isinstance(self.source_data, dict) else {}
        source_system = source_data.get("origin_object")
        if not self._source_data_is_system_source(source_data):
            return None, None

        target_info = _target_info_from_system(
            context,
            source_system,
            allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
            ignore_display_type_block=True,
        )
        if target_info is None:
            return None, None
        return source_system, target_info

    def _toggle_flag(self, context, flag_id):
        if flag_id == "LOCK_SURFACE":
            preferences = _addon_preferences(context)
            if self.surface_lock:
                selected_targets = _selected_lock_target_infos(context)
                if (
                    len(selected_targets) > 1 and
                    _target_info_key_set(selected_targets) != _target_info_key_set(self._locked_target_infos())
                ):
                    if preferences is not None:
                        preferences.paint_only_current_surface = True
                    self._set_locked_targets(
                        context,
                        selected_targets,
                        activate=True,
                        active_target=self.hover_target or self.preview_target or self.locked_target,
                    )
                    self._configure_tool(context)
                    self._sync_effective_brush_radius(context)
                    self._sync_brush_controls(context)
                    _tag_redraw_view3d_areas(context)
                    return

            self.surface_lock = not self.surface_lock
            if preferences is not None:
                preferences.paint_only_current_surface = self.surface_lock
            if not self.surface_lock:
                self.locked_target = None
                self.locked_targets = []
                self._surface_lock_retarget_pending = False
                self.last_hover_key = ""
                _clear_scene_locked_terrain(context)
            else:
                target_infos = _preferred_lock_target_infos(context)
                source_system, source_target = self._source_system_lock_target(context)
                if target_infos:
                    self._set_locked_targets(
                        context,
                        target_infos,
                        activate=True,
                        active_target=source_target,
                    )
                    if source_target is not None:
                        source_key = _target_key(source_target)
                        for target_info in self._locked_target_infos():
                            if _target_key(target_info) == source_key:
                                self.locked_target = _copy_target_info(target_info)
                                break
                    if _is_secret_paint_system(source_system):
                        self._set_active_system_lightweight(context, source_system)
                elif source_target is not None:
                    self._set_locked_target(context, source_target, activate=True)
                    if _is_secret_paint_system(source_system):
                        self._set_active_system_lightweight(context, source_system)
                elif self._restore_scene_locked_target(context, activate=True):
                    pass
                else:
                    self.locked_target = None
                    self.locked_targets = []
                    self._surface_lock_retarget_pending = True
                    self.last_hover_key = ""
        elif flag_id == "TARGET_SURFACE":
            if not _world_target_surface_feature_enabled():
                return
            active_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
            if active_system is not None:
                active_system[WORLD_PAINT_TARGET_ENABLED_PROP] = not bool(active_system.get(WORLD_PAINT_TARGET_ENABLED_PROP, False))
        elif flag_id == "ALLOW_WIRE_BOUNDS_SURFACES":
            self.allow_wire_bounds_surfaces = not self.allow_wire_bounds_surfaces
            preferences = _addon_preferences(context)
            if preferences is not None:
                preferences.allow_world_paint_wire_bounds_surfaces = self.allow_wire_bounds_surfaces
            if not self.allow_wire_bounds_surfaces:
                locked_targets = [
                    target_info
                    for target_info in self._locked_target_infos()
                    if not _target_info_display_type_blocked(target_info)
                ]
                self.locked_targets = locked_targets
                if _target_info_display_type_blocked(self.locked_target):
                    self.locked_target = locked_targets[0] if locked_targets else None
                if locked_targets:
                    _store_scene_locked_terrains(context, locked_targets)
                else:
                    _clear_scene_locked_terrain(context)
                    if self.surface_lock:
                        self._surface_lock_retarget_pending = True
                if _target_info_display_type_blocked(self.preview_target):
                    self.preview_target = None
                if _target_info_display_type_blocked(self.hover_target):
                    self.hover_target = None
                    self.last_hover_key = ""
                    if not self.stroke_active:
                        self.active_system_name = ""
        elif flag_id == "INTERPOLATE":
            if self._density_uses_native_ui():
                self._sync_interpolate_from_native_brush(context, ensure=True)
            self.interpolate = not self.interpolate
            _store_world_paint_interpolate_preference(context, self.interpolate)
            if self._density_uses_native_ui():
                self._apply_interpolate_to_native_brush(context, enabled=self.interpolate)
        elif flag_id == "RANDOM_Z":
            self.random_z = not self.random_z
            active_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
            modifier = _secret_modifier(active_system)
            if modifier is not None:
                modifier["Input_6"][2] = 20 if self.random_z else 0
        elif flag_id == "ALIGN_TO_NORMAL":
            self.align_to_normal = not self.align_to_normal
            active_system = bpy.data.objects.get(self.active_system_name) if self.active_system_name else None
            _sync_system_align_to_normal(active_system, self.align_to_normal)

        self._configure_tool(context)
        self._sync_effective_brush_radius(context)
        self._sync_brush_controls(context)
        _tag_redraw_view3d_areas(context)

    def _handle_reserved_modal_key(self, context, event):
        if not self._event_is_in_world_paint_view(context, event):
            return False

        undo_shortcut = (
            event.type == 'Z'
            and bool(getattr(event, "ctrl", False))
            and not bool(getattr(event, "shift", False))
            and self._source_switch_history
        )
        paint_shortcut_release_status = ""
        if (
            getattr(event, "value", "") == 'RELEASE'
            and (
                getattr(self, "_entry_source_preview_active", False)
                or getattr(self, "_pick_source_hold_active", False)
            )
        ):
            paint_shortcut_release_status = self._paint_shortcut_release_status(context, event)
        if (
            not undo_shortcut
            and not paint_shortcut_release_status
            and not _world_paint_event_type_can_match_shortcut(context, event, self.toggle_key_type)
        ):
            return False

        if _event_matches_shift_pick_source_shortcut(
            context,
            event,
            self.toggle_key_type,
            ignore_value=True,
        ):
            if event.value == 'PRESS':
                if not self._switch_active_system_brush_under_mouse(context, event):
                    self._pick_source_once(context, event)
            return True

        pick_source_shortcut = bool(paint_shortcut_release_status) or _event_matches_pick_source_shortcut(
            context,
            event,
            self.toggle_key_type,
            ignore_value=True,
        )
        if pick_source_shortcut:
            if getattr(self, "_entry_source_preview_active", False):
                if event.value == 'RELEASE' and paint_shortcut_release_status != "pending":
                    self._end_entry_source_preview(context, event)
                return True
            if event.value == 'PRESS':
                if not getattr(self, "_pick_source_hold_active", False):
                    self._remember_paint_shortcut_release_chord(context, event, prefer_pick_source=True)
                    self._begin_pick_source_hold(context, event)
            elif event.value == 'RELEASE':
                if paint_shortcut_release_status != "pending":
                    self._end_pick_source_hold(context, event, commit=True)
            return True

        if (
            undo_shortcut
        ):
            if event.value == 'PRESS':
                if self.stroke_active:
                    self._finish_stroke(context, event)
                self._restore_previous_source_pick(context)
            return True

        return False

    def _handle_shortcut_event(self, context, event):
        if event.value != 'PRESS':
            return False
        if not _world_paint_event_type_can_match_shortcut(context, event, self.toggle_key_type):
            return False
        if not self._event_is_in_world_paint_view(context, event):
            if not (
                _event_looks_like_keyboard_shortcut(event) and
                self._event_is_in_world_paint_area(context, event)
            ):
                return False

        shortcut = _world_paint_shortcut_from_event(context, event)
        if shortcut is None:
            return False

        action_kind, action_value = shortcut[0], shortcut[1]
        if (
            action_kind == "ADJUST"
            and action_value == "STRENGTH"
            and not self._tool_uses_brush_strength_adjust()
            and self._native_density_adjust_keymap_passthrough_enabled()
            and self._native_density_radial_adjust_passthrough_enabled()
        ):
            return False
        _native_brush_debug_log("shortcut.matched", context, self, force=True, action_kind=action_kind, action_value=action_value, event_type=getattr(event, "type", ""))
        if action_kind == "TOOL":
            self._set_tool(context, action_value, sync_workspace=True)
            return True

        if action_kind == "FLAG":
            self._toggle_flag(context, action_value)
            return True

        if action_kind == "ADJUST":
            if self.adjust_mode != action_value:
                confirm_on_release = _world_adjust_shortcut_confirm_on_release(
                    context,
                    event,
                    shortcut,
                )
                shared.secret_paint_brush_size_trace_log(
                    "world.shortcut.adjust_begin",
                    context,
                    self,
                    action_value=action_value,
                    confirm_on_release=confirm_on_release,
                    event_type=getattr(event, "type", ""),
                    event_value=getattr(event, "value", ""),
                    event_alt=bool(getattr(event, "alt", False)),
                )
                return self._begin_adjust(
                    context,
                    action_value,
                    event=event,
                    confirm_on_release=confirm_on_release,
                )
            return True

        if action_kind == "ACTION" and action_value == WORLD_ACTION_PICK_SOURCE:
            if self.stroke_active:
                self._finish_stroke(context, event)
            self._pick_source_under_brush(context, event)
            return True

        if action_kind == "ACTION" and action_value == WORLD_ACTION_BRUSH_SWITCH:
            if self.stroke_active:
                self._finish_stroke(context, event)
            self._switch_active_system_brush_under_mouse(context, event)
            return True

        return False

    def _handle_priority_shortcut_event(self, context, event):
        event_value = getattr(event, "value", "")
        if event_value not in {'PRESS', 'CLICK', 'CLICK_DRAG', 'RELEASE'}:
            return False
        if not _world_paint_event_type_can_match_shortcut(context, event, self.toggle_key_type):
            return False
        if not (
            _event_looks_like_keyboard_shortcut(event)
            or event_value == 'RELEASE'
        ):
            return False
        if self._handle_reserved_modal_key(context, event):
            return True
        return self._handle_shortcut_event(context, event)

    def _native_density_adjust_keymap_passthrough_enabled(self):
        return bool(
            self._density_uses_native_ui()
            and not WORLD_CUSTOM_ADJUST_UI_ENABLED
            and WORLD_NATIVE_DENSITY_MODAL_ADJUST_ENABLED
        )

    def _native_density_radial_adjust_passthrough_enabled(self):
        return False

    def _is_native_density_radial_adjust_shortcut_event(self, context, event):
        if getattr(event, "value", "") != 'PRESS':
            return False
        if not self._event_is_in_world_paint_view(context, event):
            return False
        if self._tool_uses_brush_strength_adjust():
            return False
        if not self._native_density_radial_adjust_passthrough_enabled():
            return False
        if _event_matches_default_shortcut(
            event,
            (
                "ADJUST",
                "STRENGTH",
                WORLD_ADJUST_OPERATOR_IDS["STRENGTH"],
                "",
                "",
                "F",
                False,
                False,
                True,
                ("3D View", "Sculpt Curves"),
            ),
        ):
            return True
        return _world_paint_event_matches_shortcut(
            context,
            event,
            "ADJUST",
            "STRENGTH",
        )

    def _native_density_radial_keymap_release_confirm_enabled(self, context, event=None):
        keyconfigs = getattr(getattr(context, "window_manager", None), "keyconfigs", None)
        if keyconfigs is None:
            return True

        def _matches_density_radial_keymap_item(keymap_item):
            if not getattr(keymap_item, "active", False):
                return False
            if getattr(keymap_item, "idname", "") != "wm.radial_control":
                return False
            properties = getattr(keymap_item, "properties", None)
            if (
                properties is None or
                getattr(properties, "data_path_primary", "") !=
                "tool_settings.curves_sculpt.brush.curves_sculpt_settings.minimum_distance"
            ):
                return False
            if event is not None:
                return _event_matches_keymap_item(event, keymap_item)
            return (
                getattr(keymap_item, "type", "") == 'F'
                and getattr(keymap_item, "value", "") == 'PRESS'
                and bool(getattr(keymap_item, "alt", False))
                and not bool(getattr(keymap_item, "shift", False))
                and not bool(getattr(keymap_item, "ctrl", False))
            )

        for keyconfig_name in ("user", "addon"):
            keyconfig = getattr(keyconfigs, keyconfig_name, None)
            if keyconfig is None:
                continue
            for keymap_name in ("Sculpt Curves", "3D View"):
                keymap = keyconfig.keymaps.get(keymap_name)
                if keymap is None:
                    continue
                for keymap_item in keymap.keymap_items:
                    if _matches_density_radial_keymap_item(keymap_item):
                        properties = getattr(keymap_item, "properties", None)
                        return bool(getattr(properties, "release_confirm", True))
        return True

    def _send_native_adjust_confirm_key_event(self):
        shared.secret_paint_brush_size_trace_log(
            "world.send_native_confirm_key.enter",
            bpy.context,
            self,
        )
        try:
            import ctypes
            from ctypes import wintypes
            self._native_density_adjust_auto_confirm_until = time.perf_counter() + 0.5
            user32 = ctypes.windll.user32
            input_keyboard = 1
            vk_return = 0x0D
            keyeventf_keyup = 0x0002
            ulong_ptr = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

            class _KeybdInput(ctypes.Structure):
                _fields_ = (
                    ("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ulong_ptr),
                )

            class _InputUnion(ctypes.Union):
                _fields_ = (("ki", _KeybdInput),)

            class _Input(ctypes.Structure):
                _fields_ = (
                    ("type", wintypes.DWORD),
                    ("union", _InputUnion),
                )

            events = (_Input * 2)()
            events[0].type = input_keyboard
            events[0].union.ki = _KeybdInput(vk_return, 0, 0, 0, 0)
            events[1].type = input_keyboard
            events[1].union.ki = _KeybdInput(vk_return, 0, keyeventf_keyup, 0, 0)
            try:
                user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int)
                user32.SendInput.restype = wintypes.UINT
                if user32.SendInput(2, events, ctypes.sizeof(_Input)) == 2:
                    shared.secret_paint_brush_size_trace_log(
                        "world.send_native_confirm_key.sendinput_success",
                        bpy.context,
                        self,
                    )
                    return True
            except Exception:
                pass
            try:
                user32.keybd_event(vk_return, 0x1C, 0, 0)
                user32.keybd_event(vk_return, 0x1C, keyeventf_keyup, 0)
                shared.secret_paint_brush_size_trace_log(
                    "world.send_native_confirm_key.keybd_success",
                    bpy.context,
                    self,
                )
                return True
            except Exception:
                shared.secret_paint_brush_size_trace_log(
                    "world.send_native_confirm_key.keybd_failed",
                    bpy.context,
                    self,
                )
                return False
        except Exception:
            shared.secret_paint_brush_size_trace_log(
                "world.send_native_confirm_key.exception",
                bpy.context,
                self,
            )
            return False

    def _schedule_native_density_radial_passthrough_sync(self, *, first_interval=0.03, max_attempts=6):
        try:
            self._schedule_native_density_adjust_result_sync(
                "STRENGTH",
                first_interval=first_interval,
                max_attempts=max_attempts,
            )
        except Exception:
            try:
                self._sync_density_spacing_from_native_brush(bpy.context)
            except Exception:
                pass

    def _confirm_native_density_radial_passthrough(self, *, prefer_mouse=True):
        if not bool(getattr(self, "_native_density_radial_confirm_on_release", True)):
            return False
        if bool(getattr(self, "_native_density_radial_confirm_sent", False)):
            return False
        self._native_density_radial_confirm_pending = False
        self._native_density_radial_confirm_sent = True
        self._native_density_radial_confirm_sent_time = time.perf_counter()
        sent = False
        if prefer_mouse:
            try:
                sent = bool(self._send_native_adjust_confirm_event())
            except Exception:
                pass
        if not sent:
            try:
                sent = bool(self._send_native_adjust_confirm_key_event())
            except Exception:
                pass
        if not sent and prefer_mouse:
            try:
                self._send_native_adjust_confirm_event()
            except Exception:
                pass
        self._schedule_native_density_radial_passthrough_sync(
            first_interval=0.08,
            max_attempts=6,
        )
        return True

    def _request_native_density_radial_release_confirm(
        self,
        *,
        prefer_mouse=True,
        wait_for_alt_release=True,
        first_interval=0.02,
    ):
        if not bool(getattr(self, "_native_density_radial_confirm_on_release", True)):
            return False
        if bool(getattr(self, "_native_density_radial_confirm_sent", False)):
            return False
        if bool(getattr(self, "_native_density_radial_confirm_pending", False)):
            return False

        def _alt_is_down():
            if not wait_for_alt_release:
                return False
            key_state = self._native_density_alt_f_key_state()
            if key_state is None:
                return False
            alt_down, _f_down = key_state
            return bool(alt_down)

        def _send_and_finish(operator):
            operator._confirm_native_density_radial_passthrough(prefer_mouse=prefer_mouse)
            operator._schedule_finish_native_density_radial_passthrough_after_confirm()
            return True

        if not _alt_is_down():
            return _send_and_finish(self)

        self._native_density_radial_confirm_pending = True
        confirm_token = getattr(self, "_native_density_radial_passthrough_token", 0)

        def _confirm_after_alt_release():
            operator = _world_operator()
            if operator is None:
                return None
            if confirm_token != getattr(operator, "_native_density_radial_passthrough_token", 0):
                return None
            if not getattr(operator, "_native_density_radial_passthrough_active", False):
                return None
            if getattr(operator, "_native_density_radial_confirm_sent", False):
                operator._native_density_radial_confirm_pending = False
                return None

            key_state = operator._native_density_alt_f_key_state()
            if key_state is not None:
                alt_down, _f_down = key_state
                if alt_down:
                    return 0.02

            operator._native_density_radial_confirm_pending = False
            try:
                _send_and_finish(operator)
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(
                _confirm_after_alt_release,
                first_interval=max(0.0, float(first_interval)),
            )
        except Exception:
            self._native_density_radial_confirm_pending = False
            return _send_and_finish(self)
        return True

    def _commit_native_density_radial_passthrough_result(self, context):
        committed = False
        native_spacing = None
        try:
            native_spacing = self._read_density_spacing_from_active_curves_brush(context)
            if native_spacing is None:
                native_spacing = self._read_density_spacing_from_native_brush(context)
        except Exception:
            native_spacing = None

        if native_spacing is not None:
            try:
                self.density_spacing = _density_spacing_value(native_spacing, fallback=self.density_spacing)
                self._native_density_adjust_manual_spacing = self.density_spacing
                try:
                    self._apply_density_spacing_to_native_brush(context)
                except Exception:
                    pass
                try:
                    active_system = self._current_system()
                    _store_system_density_spacing(active_system, self.density_spacing)
                except Exception:
                    pass
                self._sync_brush_controls(context, force=True)
                _tag_view3d_tool_ui_regions(
                    context,
                    area_pointer=getattr(self, "_invoke_area_pointer", 0),
                )
                _tag_redraw_view3d_areas(context)
                committed = True
            except Exception:
                committed = False

        if not committed:
            try:
                self._sync_native_density_adjust_result(context, "STRENGTH")
                committed = True
            except Exception:
                try:
                    self._sync_density_spacing_from_native_brush(context)
                    committed = True
                except Exception:
                    committed = False
        if committed:
            self._native_density_radial_result_committed = True
        return committed

    def _schedule_finish_native_density_radial_passthrough_after_confirm(self, delay=0.16):
        token = getattr(self, "_native_density_radial_passthrough_token", 0)

        def _finish_radial_passthrough():
            operator = _world_operator()
            if operator is None:
                return None
            if token != getattr(operator, "_native_density_radial_passthrough_token", 0):
                return None
            if not getattr(operator, "_native_density_radial_passthrough_active", False):
                return None
            if not getattr(operator, "_native_density_radial_confirm_sent", False):
                return None
            try:
                operator._finish_native_density_radial_passthrough(
                    bpy.context,
                    first_interval=0.02,
                    max_attempts=4,
                )
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(
                _finish_radial_passthrough,
                first_interval=max(0.01, float(delay)),
            )
        except Exception:
            _finish_radial_passthrough()
        return True

    def _finish_native_density_radial_passthrough(
        self,
        context,
        *,
        commit_result=True,
        schedule_sync=True,
        first_interval=0.02,
        max_attempts=4,
    ):
        committed = False
        if commit_result and not bool(getattr(self, "_native_density_radial_result_committed", False)):
            committed = self._commit_native_density_radial_passthrough_result(context)
        elif commit_result:
            committed = True
        self._native_density_radial_passthrough_active = False
        self._native_density_radial_confirm_sent = False
        self._native_density_radial_confirm_pending = False
        self._native_density_radial_confirm_sent_time = 0.0
        self._native_density_radial_result_committed = False
        try:
            self._native_density_radial_passthrough_token += 1
        except Exception:
            pass
        if schedule_sync:
            self._schedule_native_density_radial_passthrough_sync(
                first_interval=first_interval,
                max_attempts=max_attempts,
            )
        return committed

    def _start_native_density_radial_passthrough_release_watch(self):
        self._native_density_radial_passthrough_token += 1
        watch_token = self._native_density_radial_passthrough_token
        watch_started = time.perf_counter()

        def _watch_release():
            operator = _world_operator()
            if operator is None:
                return None
            if watch_token != getattr(operator, "_native_density_radial_passthrough_token", 0):
                return None
            if not getattr(operator, "_native_density_radial_passthrough_active", False):
                return None

            key_state = operator._native_density_alt_f_key_state()
            if key_state is None:
                if (time.perf_counter() - watch_started) > 30.0:
                    operator._finish_native_density_radial_passthrough(
                        bpy.context,
                        commit_result=False,
                    )
                    return None
                return 0.05

            alt_down, f_down = key_state
            if alt_down and f_down:
                return 0.02
            if not f_down or not alt_down:
                if bool(getattr(operator, "_native_density_radial_confirm_on_release", True)):
                    operator._commit_native_density_radial_passthrough_result(bpy.context)
                    operator._request_native_density_radial_release_confirm(
                        prefer_mouse=True,
                        wait_for_alt_release=bool(alt_down),
                    )
                    return None
                operator._schedule_native_density_radial_passthrough_sync()
                return None
            return 0.02

        try:
            bpy.app.timers.register(_watch_release, first_interval=0.02)
        except Exception:
            return False
        return True

    def _begin_native_density_radial_passthrough(self, context, event):
        self._commit_active_native_density_adjust_result(context)
        _disable_stale_secret_paint_density_adjust_keymaps_runtime(context)
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
        if self._begin_native_density_session(context, create_system=False):
            self._restore_native_density_brush_overlay()
            self._restore_native_density_brush_visibility(context)
            self._force_native_brush_visibility(context)
        self._native_density_radial_passthrough_active = True
        self._native_density_radial_confirm_on_release = self._native_density_radial_keymap_release_confirm_enabled(
            context,
            event,
        )
        self._native_density_radial_confirm_sent = False
        self._native_density_radial_confirm_pending = False
        self._native_density_radial_result_committed = False
        self._start_native_density_radial_passthrough_release_watch()
        return True

    def _handle_native_density_radial_passthrough_event(self, context, event):
        if self._is_native_density_radial_adjust_shortcut_event(context, event):
            self._begin_native_density_radial_passthrough(context, event)
            return True

        if not getattr(self, "_native_density_radial_passthrough_active", False):
            return False

        event_type = getattr(event, "type", "")
        event_value = getattr(event, "value", "")
        if event_type in {'F', 'LEFT_ALT', 'RIGHT_ALT', 'ALT'} and event_value == 'RELEASE':
            if bool(getattr(self, "_native_density_radial_confirm_on_release", True)):
                self._commit_native_density_radial_passthrough_result(context)
                self._request_native_density_radial_release_confirm(
                    prefer_mouse=True,
                    wait_for_alt_release=(event_type == 'F'),
                )
            elif event_type == 'F':
                self._schedule_native_density_radial_passthrough_sync()
            return True
        if event_type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event_value in {'PRESS', 'RELEASE'}:
            if event_value == 'RELEASE':
                self._finish_native_density_radial_passthrough(context)
            else:
                self._schedule_native_density_radial_passthrough_sync()
            return True
        if event_type in {'ESC', 'RIGHTMOUSE'} and event_value in {'PRESS', 'RELEASE'}:
            if event_value == 'RELEASE':
                self._finish_native_density_radial_passthrough(
                    context,
                    commit_result=False,
                    schedule_sync=False,
                )
            return True
        return event_type in {
            'MOUSEMOVE',
            'INBETWEEN_MOUSEMOVE',
            'TIMER',
        }

    def _handle_disabled_size_adjust_passthrough_event(self, context, event):
        if WORLD_SIZE_ADJUST_SHORTCUT_ENABLED or not self._density_uses_native_ui():
            return False
        if getattr(self, "adjust_mode", ""):
            return False
        if getattr(self, "_native_density_radial_passthrough_active", False):
            return False
        event_type = getattr(event, "type", "")
        event_value = getattr(event, "value", "")
        if event_type == 'F' and not any(
            bool(getattr(event, modifier_name, False))
            for modifier_name in ("shift", "ctrl", "alt", "oskey", "hyper")
        ):
            if event_value == 'PRESS':
                self._disabled_size_adjust_passthrough_active = True
                return True
            if event_value == 'RELEASE':
                self._disabled_size_adjust_passthrough_active = False
                return True

        if getattr(self, "_disabled_size_adjust_passthrough_active", False):
            return event_type in {
                'MOUSEMOVE',
                'INBETWEEN_MOUSEMOVE',
                'LEFTMOUSE',
                'RIGHTMOUSE',
                'ACTIONMOUSE',
                'SELECTMOUSE',
            }
        return False

    def _sync_workspace_tool(self, context):
        if self.tool_id == WORLD_TOOL_DENSITY and self._native_density_stroke_erase:
            _shift_delete_debug_log("sync_workspace.delete_enter", context, self, force=True)
        _native_brush_debug_log("sync_workspace.enter", context, self)
        if _world_paint_bezier_curve_edit_active(context, self):
            return True
        active_workspace_tool = _active_workspace_tool_id(context) or ""

        if not active_workspace_tool:
            _native_brush_debug_log("sync_workspace.no_active_tool", context, self, force=True)
        if _is_world_workspace_tool_id(active_workspace_tool):
            _native_brush_debug_log(
                "sync_workspace.clear_stale_secret_tool",
                context,
                self,
                force=True,
                active_workspace_tool=active_workspace_tool,
            )
            if context.mode == 'SCULPT_CURVES' and (
                self._use_native_density_backend() or self._use_native_tool_backend()
            ):
                self._activate_workspace_tool_for_world_tool(context, self.tool_id)
                active_workspace_tool = ""
            else:
                active_workspace_tool = ""

        world_tool = _world_tool_from_workspace_id(active_workspace_tool)
        native_workspace_tool = False
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        active_brush_type = _brush_curves_type(active_brush)
        override_active = self._native_tool_override_active()
        requested_active = self._requested_native_tool_active()
        if (
            not override_active
            and not requested_active
            and self._active_brush_requests_native_passthrough(context, active_brush, active_brush_type)
        ):
            self._enter_native_curves_brush_passthrough(context, active_brush)
            return True
        if (
            self.tool_id == WORLD_TOOL_DENSITY and
            context.mode == 'SCULPT_CURVES' and
            active_brush_type == 'DELETE' and
            not bool(getattr(self, "_native_density_stroke_erase", False)) and
            not bool(getattr(self, "_density_right_delete_button_down", False)) and
            not override_active
        ):
            self._restore_density_native_brush_after_delete(context)
            return True
        if self._native_curves_brush_passthrough_active():
            if context.mode == 'SCULPT_CURVES' and active_brush is not None:
                self._native_curves_passthrough_brush_name = getattr(active_brush, "name", "")
                return True
            self._leave_native_curves_brush_passthrough(context)
        if requested_active and context.mode == 'SCULPT_CURVES':
            desired_brush_type = (
                getattr(self, "_requested_native_tool_brush_type", "")
                or self._active_native_brush_type()
            )
            desired_brush_name = shared.secret_paint_curves_brush_asset_name(desired_brush_type)
            desired_tool_ids = WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.get(desired_brush_type, ())
            if desired_brush_type:
                active_is_desired = (
                    active_brush is not None
                    and _curves_brush_matches_type(active_brush, desired_brush_type)
                )
                tool_is_desired = (
                    active_workspace_tool in desired_tool_ids
                    if active_workspace_tool
                    else active_is_desired
                )
                if active_workspace_tool == "builtin.brush":
                    tool_is_desired = active_is_desired
                if not active_is_desired or not tool_is_desired:
                    _native_brush_debug_log(
                        "sync_workspace.requested_native_tool",
                        context,
                        self,
                        force=True,
                        active_workspace_tool=active_workspace_tool,
                        desired_brush_type=desired_brush_type,
                        desired_brush_name=desired_brush_name,
                        active_brush=getattr(active_brush, "name", ""),
                        active_brush_type=active_brush_type,
                        active_is_desired=active_is_desired,
                        tool_is_desired=tool_is_desired,
                    )
                    _activate_native_curves_tool(
                        context,
                        desired_brush_type,
                        area_pointer=self._invoke_area_pointer,
                    )
                    brush = self._sync_native_density_brush(context)
                    if brush is not None:
                        self._activate_native_brush_cursor(
                            context,
                            brush,
                            self._current_system(),
                            defer=True,
                        )
                    return True
        if not override_active and context.mode == 'SCULPT_CURVES':
            desired_brush_type = self._active_native_brush_type()
            desired_brush_name = shared.secret_paint_curves_brush_asset_name(desired_brush_type)
            native_workspace_tool = bool(
                active_workspace_tool == "builtin.brush"
                or active_workspace_tool.startswith("builtin_brush.")
            )
            if (
                native_workspace_tool
                and active_brush is not None
                and not _curves_brush_matches_type(active_brush, desired_brush_type)
            ):
                self._enter_native_curves_brush_passthrough(context, active_brush)
                return True
        if override_active and context.mode == 'SCULPT_CURVES':
            desired_brush_type = self._native_tool_override_brush_type or self._active_native_brush_type()
            desired_brush_name = shared.secret_paint_curves_brush_asset_name(desired_brush_type)
            desired_tool_ids = WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.get(desired_brush_type, ())
            active_is_desired = (
                active_brush is not None and
                _curves_brush_matches_type(active_brush, desired_brush_type)
            )
            tool_is_desired = (
                active_workspace_tool in desired_tool_ids
                if active_workspace_tool
                else active_is_desired
            )
            _native_brush_debug_log(
                "sync_workspace.override_active",
                context,
                self,
                force=True,
                desired_brush_type=desired_brush_type,
                desired_brush_name=desired_brush_name,
                active_brush_type=active_brush_type,
                active_is_desired=active_is_desired,
                tool_is_desired=tool_is_desired,
            )
            if desired_brush_type:
                if not tool_is_desired:
                    _activate_native_curves_tool(
                        context,
                        desired_brush_type,
                        area_pointer=self._invoke_area_pointer,
                    )
                if not active_is_desired or not tool_is_desired:
                    brush = self._sync_native_density_brush(context)
                    if brush is not None:
                        self._activate_native_brush_cursor(context, brush, self._current_system(), defer=True)
                return True
        if (
            _WORLD_STATE["ui_hijacked"] and
            context.mode == 'SCULPT_CURVES' and
            (self._use_native_density_backend() or self._use_native_tool_backend())
        ):
            desired_brush_type = self._active_native_brush_type()
            desired_brush_name = shared.secret_paint_curves_brush_asset_name(desired_brush_type)
            desired_tool_ids = WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.get(desired_brush_type, ())
            active_is_desired = (
                active_brush is not None and
                _curves_brush_matches_type(active_brush, desired_brush_type)
            )
            tool_is_desired = (
                active_workspace_tool in desired_tool_ids
                if active_workspace_tool
                else active_is_desired
            )
            _native_brush_debug_log(
                "sync_workspace.authoritative_tool",
                context,
                self,
                force=True,
                active_workspace_tool=active_workspace_tool,
                desired_brush_type=desired_brush_type,
                desired_brush_name=desired_brush_name,
                active_brush_type=active_brush_type,
                active_is_desired=active_is_desired,
                tool_is_desired=tool_is_desired,
            )
            if desired_brush_type and not tool_is_desired:
                _activate_native_curves_tool(
                    context,
                    desired_brush_type,
                    area_pointer=self._invoke_area_pointer,
                )
            if desired_brush_type and (not active_is_desired or not tool_is_desired):
                brush = self._sync_native_density_brush(context)
                if brush is not None:
                    self._activate_native_brush_cursor(context, brush, self._current_system(), defer=True)
            return True
        if world_tool is None:
            for brush_type, tool_ids in WORLD_NATIVE_TOOL_IDS_BY_BRUSH_TYPE.items():
                if active_workspace_tool in tool_ids:
                    world_tool = _world_tool_from_native_brush_type(brush_type)
                    native_workspace_tool = world_tool is not None
                    break
        if world_tool is None and active_workspace_tool in WORLD_NATIVE_DENSITY_TOOL_IDS:
            world_tool = WORLD_TOOL_DENSITY
            native_workspace_tool = True
        active_brush_world_tool = None
        if context.mode == 'SCULPT_CURVES':
            if active_brush_type == 'DENSITY':
                active_brush_world_tool = WORLD_TOOL_DENSITY
            else:
                active_brush_world_tool = _world_tool_from_native_brush_type(active_brush_type)
        if world_tool is None and not active_workspace_tool and active_brush_world_tool is not None:
            world_tool = active_brush_world_tool
            native_workspace_tool = True
        if (
            world_tool is None and
            active_brush_world_tool is not None and
            (active_workspace_tool == "builtin.brush" or active_workspace_tool.startswith("builtin_brush."))
        ):
            world_tool = active_brush_world_tool
            native_workspace_tool = True
        if world_tool is None and active_workspace_tool == "builtin.brush":
            if _is_density_brush(active_brush):
                world_tool = WORLD_TOOL_DENSITY
                native_workspace_tool = True
            else:
                world_tool = _world_tool_from_native_brush_type(active_brush_type)
                native_workspace_tool = world_tool is not None
        if world_tool is not None:
            _native_brush_debug_log(
                "sync_workspace.resolved_world_tool",
                context,
                self,
                force=True,
                active_workspace_tool=active_workspace_tool,
                resolved_world_tool=world_tool,
                native_workspace_tool=native_workspace_tool,
            )
            if (
                context.mode == 'SCULPT_CURVES' and
                native_workspace_tool and
                not _is_world_workspace_tool_id(active_workspace_tool)
            ):
                self._activate_workspace_tool_for_world_tool(context, world_tool)
            if world_tool != self.tool_id:
                self._set_tool(context, world_tool, sync_workspace=True)
            elif context.mode == 'SCULPT_CURVES' and (
                world_tool == WORLD_TOOL_DENSITY or _world_tool_uses_native_brush(world_tool)
            ):
                desired_brush_type = _curves_brush_type_for_world_tool(world_tool)
                desired_brush_name = shared.secret_paint_curves_brush_asset_name(desired_brush_type)
                active_is_desired = (
                    active_brush is not None
                    and _curves_brush_matches_type(active_brush, desired_brush_type)
                )
                if not active_is_desired:
                    brush = self._sync_native_density_brush(context)
                    if brush is not None:
                        self._activate_native_brush_cursor(context, brush, self._current_system(), defer=True)
            return True

        if self._use_native_density_backend() or self._use_native_tool_backend():
            desired_brush_type = self._active_native_brush_type()
            _native_brush_debug_log(
                "sync_workspace.native_backend_fallback",
                context,
                self,
                force=True,
                desired_brush_type=desired_brush_type,
                active_brush_type=active_brush_type,
            )
            if active_workspace_tool.startswith("builtin_brush.") and context.mode == 'SCULPT_CURVES':
                if active_brush_type != desired_brush_type:
                    if self.tool_id == WORLD_TOOL_DENSITY:
                        _activate_native_density_tool(context, area_pointer=self._invoke_area_pointer)
                    else:
                        _activate_native_curves_tool(
                            context,
                            desired_brush_type,
                            area_pointer=self._invoke_area_pointer,
                        )
                    self._sync_native_density_brush(context)
                return True
            if active_workspace_tool == "builtin.brush":
                if active_brush_type != desired_brush_type:
                    self._sync_native_density_brush(context)
                return True
            return True

        if (
            _WORLD_STATE["ui_hijacked"]
            and active_workspace_tool != self._saved_workspace_tool_id
            and not _world_tool_accepts_object_mode_fallback_tool(self.tool_id, active_workspace_tool)
        ):
            _native_brush_debug_log("sync_workspace.finish_due_tool_change", context, self, force=True, active_workspace_tool=active_workspace_tool)
            self.finish_world_paint(context)
            return False
        _native_brush_debug_log("sync_workspace.exit_default", context, self, force=True, active_workspace_tool=active_workspace_tool)
        return True

    def _set_active_curve_draw(self, context, curve_obj):
        if curve_obj is None:
            return
        self.active_curve_draw_name = curve_obj.name

    def _active_bezier_curve_draw_object(self):
        curve_obj = bpy.data.objects.get(self.active_curve_draw_name) if self.active_curve_draw_name else None
        if getattr(curve_obj, "type", None) == "CURVE":
            return curve_obj
        return _source_data_curve_object(self.source_data)

    def _activate_bezier_curve_draw_tool(
        self,
        context,
        *,
        curve_obj=None,
        activate_draw_tool=True,
        configure_settings=True,
        suppress_world_shortcuts=True,
    ):
        if curve_obj is not None and getattr(curve_obj, "type", None) != "CURVE":
            curve_obj = None
        if curve_obj is None:
            curve_obj = self._active_bezier_curve_draw_object()
        if curve_obj is None:
            curve_obj = _find_or_create_native_curve_draw_object(context, self.source_data)
        if curve_obj is None:
            return False

        self._set_active_curve_draw(context, curve_obj)
        if configure_settings:
            _ensure_curve_draw_settings(context)

        try:
            if context.mode != 'OBJECT' and getattr(context, "active_object", None) != curve_obj:
                _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass

        try:
            for selected_obj in list(context.selected_objects):
                selected_obj.select_set(False)
        except Exception:
            pass
        try:
            curve_obj.select_set(True)
            context.view_layer.objects.active = curve_obj
        except Exception:
            return False

        try:
            if not _context_curve_edit_mode_active(context, curve_obj):
                bpy.ops.object.mode_set(mode="EDIT")
        except Exception:
            return False

        if activate_draw_tool:
            try:
                bpy.ops.wm.tool_set_by_id(name="builtin.draw")
            except Exception:
                pass
        _set_world_paint_shortcuts_enabled(context, not suppress_world_shortcuts)
        _tag_redraw_view3d_areas(context)
        return True

    def _handoff_to_bezier_curve_edit(self, context, *, source_data=None, force_new_curve=False):
        source_data = source_data or self.source_data
        self.source_data = source_data
        curve_obj = None if force_new_curve else self._active_bezier_curve_draw_object()
        curve_name = _safe_rna_name(curve_obj)
        protected_names = {curve_name} if curve_name else set()

        _WORLD_STATE["bezier_handoff_object_names"] = protected_names
        try:
            if getattr(self, "_running", False):
                self.finish_world_paint(context)
                _clear_world_paint_object_mode_guard()
                if curve_name:
                    curve_obj = bpy.data.objects.get(curve_name)
                    if getattr(curve_obj, "type", None) != "CURVE":
                        curve_obj = None

            if curve_obj is None and force_new_curve:
                curve_obj = _create_native_curve_draw_object(context, source_data)
            elif curve_obj is None:
                curve_obj = _find_or_create_native_curve_draw_object(context, source_data)
            if curve_obj is None:
                return False

            self._set_active_curve_draw(context, curve_obj)
            _ensure_curve_draw_settings(context)
            return self._activate_bezier_curve_draw_tool(
                context,
                curve_obj=curve_obj,
                activate_draw_tool=True,
                configure_settings=False,
                suppress_world_shortcuts=False,
            )
        finally:
            _WORLD_STATE["bezier_handoff_object_names"] = set()

    def _configure_tool(self, context):
        if self.tool_id == WORLD_TOOL_BEZIER:
            self._activate_bezier_curve_draw_tool(context)
            return
        if self._use_native_density_backend() or self._use_native_tool_backend():
            if self._native_density_session_active:
                self._sync_native_density_brush(context)
            return
        if self._native_density_session_active:
            self._finish_native_density_session(context, restore_selection=False)
        if context.mode != 'OBJECT':
            try:
                _mode_set_with_world_toolbar_restored('OBJECT')
            except Exception:
                pass

    def _activate_hover_target(self, context, target_info):
        if not target_info:
            return
        if getattr(self, "surface_lock", False):
            target_key = _target_key(target_info)
            for locked_target in self._locked_target_infos():
                if target_key and _target_key(locked_target) == target_key:
                    self.locked_target = _copy_target_info(locked_target)
                    break
        if self.tool_id == WORLD_TOOL_BEZIER:
            self.preview_target = target_info
            self.hover_target = target_info
            self.last_hover_key = _target_key(target_info)
            self._sync_effective_brush_radius(
                context,
                depth_location=self._brush_screen_depth_location(target_info=target_info),
            )
            return

        self.preview_target = target_info
        self.hover_target = target_info
        self.last_hover_key = _target_key(target_info)
        self._sync_effective_brush_radius(
            context,
            depth_location=self._brush_screen_depth_location(target_info=target_info),
        )
        self._configure_tool(context)

    def _density_target_handoff_active(self):
        return bool(
            self.surface_lock and
            len(self._locked_target_infos()) > 1 and
            not self._surface_lock_retarget_pending
        )

    def _allow_idle_target_preview_switch(self, target_info):
        return True

    def _track_idle_native_density_mouse(self, context, event=None):
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)

        if self._native_idle_session_deferred(event):
            return

        if (
            self._native_density_session_active and
            not self.stroke_active and
            not self.adjust_mode
        ):
            return

        active_system = self._current_system()
        if active_system is not None:
            _keep_active_system_object(context, active_system)
            self._sync_effective_brush_radius(
                context,
                depth_location=_brush_depth_location_from_system(active_system),
                mouse_coord=self.hover_mouse_region,
            )
        else:
            self._sync_effective_brush_radius(context, mouse_coord=self.hover_mouse_region)
        _tag_redraw_view3d_areas(context)

    def _ensure_shift_delete_preview_session(self, context):
        if self.tool_id not in {WORLD_TOOL_DENSITY, WORLD_TOOL_DELETE}:
            return False

        system_obj = self._current_system()
        if system_obj is None:
            active_obj = getattr(context, "active_object", None)
            if _is_secret_paint_system(active_obj):
                system_obj = active_obj
                self.active_system_name = active_obj.name
        if system_obj is None:
            source_obj = self.source_data.get("origin_object") if isinstance(self.source_data, dict) else None
            if _is_secret_paint_system(source_obj):
                system_obj = source_obj
                self.active_system_name = source_obj.name
        if system_obj is None:
            return False

        if (
            self._native_density_session_active and
            self._native_density_active_system_name and
            self._native_density_active_system_name != system_obj.name
        ):
            self._finish_native_density_session(context, restore_selection=False)

        self._native_density_stroke_erase = self.tool_id == WORLD_TOOL_DENSITY
        self._begin_native_tool_override("DELETE")

        if not self._native_density_session_active:
            self._native_density_restore_mode = context.mode if context.mode else "OBJECT"
            self._native_density_restore_active_name = context.active_object.name if context.active_object else ""
            self._native_density_restore_selection_names = [obj.name for obj in context.selected_objects]

        try:
            if context.mode != 'OBJECT' and getattr(context, "active_object", None) != system_obj:
                _mode_set_with_world_toolbar_restored('OBJECT')
        except Exception:
            pass

        try:
            system_obj.select_set(True)
        except Exception:
            pass
        try:
            context.view_layer.objects.active = system_obj
        except Exception:
            pass
        try:
            context.view_layer.update()
        except Exception:
            pass

        try:
            shared.context3sculptbrush(
                context,
                activeobj=system_obj,
                keep_active_brush=True,
                brush_setup_mode="native",
            )
        except Exception:
            pass
        try:
            if context.mode != 'SCULPT_CURVES':
                _mode_set_with_world_toolbar_restored('SCULPT_CURVES')
                shared.secret_paint_disable_sculpt_curves_cage(context)
                self._world_ui_cage_hidden = True
        except Exception:
            return False

        _keep_active_system_object(context, system_obj)
        self._ensure_native_density_surface_attachment(context, system_obj)
        self._native_density_fallback = False
        self._native_density_session_active = True
        self._native_density_active_system_name = system_obj.name
        self._track_touched_system(system_obj)

        tool_ok = _activate_native_curves_tool(
            context,
            "DELETE",
            area_pointer=self._invoke_area_pointer,
        )
        brush = self._sync_native_density_brush(context, system_obj=system_obj)
        cursor_ok = False
        if brush is not None:
            cursor_ok = self._activate_native_brush_cursor(context, brush, system_obj, defer=False)

        self._sync_tool_ui_mode(context)
        _tag_redraw_view3d_areas(context)
        _shift_delete_debug_log(
            "shift_delete_preview_current_system",
            context,
            self,
            force=True,
            system=getattr(system_obj, "name", ""),
            tool_ok=tool_ok,
            cursor_ok=cursor_ok,
            brush=getattr(brush, "name", ""),
        )
        return brush is not None and (tool_ok or cursor_ok)

    def _ensure_idle_native_density_session(self, context, event=None):
        if self.tool_id == WORLD_TOOL_DENSITY and self._event_shift_active(event):
            _shift_delete_debug_log("ensure_idle_native.shift_enter", context, self, event=event, force=True)
        _native_brush_debug_log("ensure_idle_native.enter", context, self)
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
        if self._native_idle_session_deferred(event):
            return False
        if not self._density_uses_native_ui():
            if self.tool_id == WORLD_TOOL_DENSITY and self._event_shift_active(event):
                _shift_delete_debug_log("ensure_idle_native.shift_skip_no_native_ui", context, self, event=event, force=True)
            return False
        if self.stroke_active or self._primary_paint_button_down or self.adjust_mode:
            if self.tool_id == WORLD_TOOL_DENSITY and self._event_shift_active(event):
                _shift_delete_debug_log(
                    "ensure_idle_native.shift_skip_busy",
                    context,
                    self,
                    event=event,
                    force=True,
                    stroke_active=self.stroke_active,
                    primary_down=self._primary_paint_button_down,
                    adjust_mode=self.adjust_mode,
                )
            return False

        if self._surface_lock_waiting_for_target():
            if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            _tag_redraw_view3d_areas(context)
            _native_brush_debug_log("ensure_idle_native.skip_surface_lock_retarget", context, self, force=True)
            return False

        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            if self._idle_native_hover_raycast_due(event):
                with shared.secret_paint_world_perf_span(
                    "world.idle_native_hover_raycast",
                    threshold_ms=1.0,
                    event=getattr(event, "type", ""),
                ):
                    self._update_hover_target(context, event, commit=False)
                self._mark_idle_native_hover_raycast(event)
            if self._density_target_handoff_active():
                preview_key = _target_key(self.preview_target)
                hover_key = _target_key(self.hover_target)
                if self.preview_target is not None and preview_key and preview_key != hover_key:
                    self._activate_hover_target(context, self.preview_target)
        elif self.hover_mouse_region is not None:
            if self.hover_target is None:
                self._refresh_hover_target_from_stored_mouse(context, commit=False)
        elif self.surface_lock and self._locked_target_infos():
            self.locked_target = self.locked_target or self._locked_target_infos()[0]
            self._activate_hover_target(context, self.locked_target)

        if self.hover_target is None:
            _tag_redraw_view3d_areas(context)
            _native_brush_debug_log("ensure_idle_native.no_hover", context, self)
            if self.tool_id == WORLD_TOOL_DENSITY and self._event_shift_active(event):
                _shift_delete_debug_log("ensure_idle_native.shift_no_hover", context, self, event=event, force=True)
                return self._ensure_shift_delete_preview_session(context)
            return False

        shift_delete_preview = self.tool_id == WORLD_TOOL_DENSITY and self._event_shift_active(event)
        if self.tool_id == WORLD_TOOL_DENSITY:
            self._native_density_stroke_erase = bool(shift_delete_preview)
            if shift_delete_preview:
                self._begin_native_tool_override("DELETE")
                _shift_delete_debug_log("ensure_idle_native.shift_preview_set", context, self, event=event, force=True)

        if not shift_delete_preview:
            current_system = self._current_system()
            if self._native_density_session_matches_system(context, current_system):
                sync_key = self._native_density_sync_key(context, current_system)
                if not self._native_density_sync_due(sync_key):
                    return True

        with shared.secret_paint_world_perf_span(
            "world.ensure_idle_begin_native_session",
            threshold_ms=1.0,
            tool=self.tool_id,
            shift_delete=shift_delete_preview,
        ):
            native_session_started = self._begin_native_density_session(context, create_system=False)

        if not native_session_started:
            _native_brush_debug_log("ensure_idle_native.begin_failed", context, self, force=True)
            if shift_delete_preview:
                _shift_delete_debug_log("ensure_idle_native.shift_begin_failed", context, self, event=event, force=True)
            return False

        if shift_delete_preview and context.mode == 'SCULPT_CURVES':
            tool_ok = _activate_native_curves_tool(
                context,
                "DELETE",
                area_pointer=self._invoke_area_pointer,
            )
            brush = self._sync_native_density_brush(context)
            cursor_ok = False
            if brush is not None:
                cursor_ok = self._activate_native_brush_cursor(context, brush, self._current_system(), defer=False)
            _shift_delete_debug_log(
                "ensure_idle_native.shift_activated",
                context,
                self,
                event=event,
                force=True,
                tool_ok=tool_ok,
                cursor_ok=cursor_ok,
                brush=getattr(brush, "name", ""),
                brush_type=shared.secret_paint_curves_brush_type(brush) if brush is not None else "",
            )

        self._sync_tool_ui_mode(context)
        _tag_redraw_view3d_areas(context)
        _native_brush_debug_log("ensure_idle_native.exit_true", context, self, force=True)
        return True

    def _update_hover_target_from_coords(self, context, mouse_region_x, mouse_region_y, *, commit=False):
        self.hover_mouse_region = (mouse_region_x, mouse_region_y)
        locked_targets = self._locked_target_infos()
        density_handoff_active = self._density_target_handoff_active()
        preserve_preview = (
            not commit and
            (self._use_native_density_backend() or self._use_native_tool_backend()) and
            self._native_density_session_active and
            not density_handoff_active
        )
        with shared.secret_paint_world_perf_span(
            "world.hover_target_raycast",
            threshold_ms=1.0,
            commit=commit,
            surface_lock=bool(
                self.surface_lock and
                locked_targets and
                not self._surface_lock_retarget_pending
            ),
            tool=self.tool_id,
            native_session=self._native_density_session_active,
            stroke=self.stroke_active,
        ):
            if self.surface_lock and locked_targets and not self._surface_lock_retarget_pending:
                target_info = _raycast_locked_targets(
                    context,
                    (mouse_region_x, mouse_region_y),
                    locked_targets,
                    source_data=self.source_data,
                    allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                )
            else:
                target_info = _raycast_target(
                    context,
                    (mouse_region_x, mouse_region_y),
                    source_data=self.source_data,
                    allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                )
        if target_info is None:
            if not preserve_preview:
                self.preview_target = None
            if commit:
                self.hover_target = None
                self.last_hover_key = ""
            self._sync_effective_brush_radius(context, mouse_coord=self.hover_mouse_region)
            return
        if not commit and not self._allow_idle_target_preview_switch(target_info):
            if not preserve_preview:
                self.preview_target = None
            self._sync_effective_brush_radius(context, mouse_coord=self.hover_mouse_region)
            return
        if commit and self.surface_lock and (
            not self._locked_target_infos() or self._surface_lock_retarget_pending
        ):
            self._set_locked_target(context, target_info)
            target_info = self.locked_target
        self.preview_target = target_info
        if not commit:
            target_key = _target_key(target_info)
            if (
                self.stroke_active and
                self._paint_stroke_button_down() and
                target_key and
                target_key == self.last_hover_key
            ):
                self.hover_target = target_info
            self._sync_effective_brush_radius(
                context,
                depth_location=self._brush_screen_depth_location(target_info=target_info),
                mouse_coord=self.hover_mouse_region,
            )
            return
        if _target_key(target_info) != self.last_hover_key:
            self._activate_hover_target(context, target_info)
        else:
            self.hover_target = target_info
            self._sync_effective_brush_radius(
                context,
                depth_location=self._brush_screen_depth_location(target_info=target_info),
                mouse_coord=self.hover_mouse_region,
            )

    def _update_hover_target(self, context, event, *, commit=False):
        try:
            override, mouse_coord = _event_view3d_window_override_and_mouse(
                context,
                event,
                self._invoke_area_pointer,
            )
        except Exception:
            override, mouse_coord = None, None
        if override is not None and mouse_coord is not None:
            try:
                with context.temp_override(**override):
                    return self._update_hover_target_from_coords(
                        bpy.context,
                        mouse_coord[0],
                        mouse_coord[1],
                        commit=commit,
                    )
            except Exception:
                pass
        self._update_hover_target_from_coords(
            context,
            event.mouse_region_x,
            event.mouse_region_y,
            commit=commit,
        )

    def _density_delete_surface_target_candidates(self, context):
        candidates = []
        seen = set()

        def add_target(target_info):
            if not target_info:
                return
            target_key = _target_key(target_info)
            if not target_key or target_key in seen:
                return
            seen.add(target_key)
            candidates.append(target_info)

        if self.surface_lock and not self._surface_lock_retarget_pending:
            for locked_target in self._locked_target_infos():
                add_target(locked_target)
        add_target(self.hover_target)
        add_target(self.preview_target)

        system_candidates = [
            self._current_system(),
            bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None,
            self.source_data.get("origin_object") if self.source_data.get("origin_kind") == "SYSTEM" else None,
        ]
        for system_obj in system_candidates:
            add_target(
                _target_info_from_system(
                    context,
                    system_obj,
                    allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                )
            )

        if not (self.surface_lock and self._locked_target_infos() and not self._surface_lock_retarget_pending):
            brush_object = self.source_data.get("brush_object")
            brush_collection = self.source_data.get("brush_collection")
            for system_obj in sorted(list(_world_system_match_candidates(self.source_data)), key=_world_system_panel_sort_key):
                if not _is_secret_paint_system(system_obj):
                    continue
                modifier = _secret_modifier(system_obj)
                if modifier is None or not _same_source(modifier, brush_object, brush_collection):
                    continue
                if not _world_system_allowed_for_source_match(system_obj, self.source_data):
                    continue
                add_target(
                    _target_info_from_system(
                        context,
                        system_obj,
                        allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                    )
                )

        return candidates

    def _update_density_delete_target_through_instances(self, context, event, *, commit=False):
        if not (
            self.tool_id == WORLD_TOOL_DENSITY and
            event is not None and
            hasattr(event, "mouse_region_x") and
            hasattr(event, "mouse_region_y")
        ):
            return False

        mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        ray_origin = None
        try:
            if context.region is not None and context.region_data is not None:
                ray_origin = view3d_utils.region_2d_to_origin_3d(
                    context.region,
                    context.region_data,
                    mouse_coord,
                )
        except Exception:
            ray_origin = None

        best_target = None
        best_distance = float("inf")
        for target_info in self._density_delete_surface_target_candidates(context):
            direct_target = _raycast_target_info_surface(context, mouse_coord, target_info)
            if direct_target is None:
                continue
            if ray_origin is None:
                best_target = direct_target
                break
            location = direct_target.get("location")
            try:
                distance = (location - ray_origin).length if location is not None else float("inf")
            except Exception:
                distance = float("inf")
            if distance < best_distance:
                best_distance = distance
                best_target = direct_target

        if best_target is None:
            return False
        if commit and self.surface_lock and (
            not self._locked_target_infos() or self._surface_lock_retarget_pending
        ):
            self._set_locked_target(context, best_target)
            best_target = self.locked_target
        self._activate_hover_target(context, best_target)
        return True

    def _refresh_hover_target_from_stored_mouse(self, context, *, commit=False):
        mouse_coord = getattr(self, "hover_mouse_region", None)
        if mouse_coord is None:
            return

        area, region, space = _view3d_area_data(context, getattr(self, "_invoke_area_pointer", 0))
        if area is not None and region is not None and space is not None:
            try:
                with context.temp_override(area=area, region=region, space_data=space):
                    self._update_hover_target_from_coords(
                        bpy.context,
                        mouse_coord[0],
                        mouse_coord[1],
                        commit=commit,
                    )
                return
            except Exception:
                pass

        self._update_hover_target_from_coords(
            context,
            mouse_coord[0],
            mouse_coord[1],
            commit=commit,
        )

    def _sync_viewport_navigation_state(self, context):
        current_state_key = _viewport_navigation_state_key(self, context)
        previous_state_key = getattr(self, "_viewport_navigation_last_state_key", None)
        self._viewport_navigation_last_state_key = current_state_key
        if previous_state_key is None or current_state_key is None:
            return False
        return current_state_key != previous_state_key

    def _end_viewport_navigation(self, context, event=None):
        self._viewport_navigation_active = False
        self._viewport_navigation_input_held = False
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
        self._viewport_navigation_last_state_key = _viewport_navigation_state_key(self, context)
        if (
            self._density_uses_native_ui() and
            not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE and
            not self.stroke_active and
            not self.adjust_mode
        ):
            self._defer_idle_native_density_session(context)
            return
        self._refresh_hover_target_from_stored_mouse(context, commit=False)
        if not (self._density_uses_native_ui() and self._native_density_paused_for_navigation):
            _tag_redraw_view3d_areas(context)

    def _stroke_spacing(self, context, depth_location=None):
        radius = self._effective_brush_radius(context, depth_location=depth_location)
        if self.tool_id == WORLD_TOOL_SINGLE:
            return max(WORLD_MIN_OPERATION_RADIUS, radius * 0.85)
        if self.tool_id == WORLD_TOOL_BEZIER:
            return max(WORLD_MIN_OPERATION_RADIUS, radius * 0.15)
        return max(WORLD_MIN_OPERATION_RADIUS, radius * 0.35)

    def _current_system(self):
        return bpy.data.objects.get(self.active_system_name) if self.active_system_name else None

    def _ensure_current_system(self, context, *, create=True, hit_location=None, hit_radius=0.0):
        system_obj = self._current_system()
        if system_obj is not None and _target_match_for_system(system_obj, self.source_data, self.hover_target):
            _ensure_world_system_surface_uvs(self, context, system_obj, self.hover_target)
            self._track_touched_system(system_obj)
            return system_obj
        if (
            not create
            and system_obj is not None
            and hit_location is not None
            and _world_system_allowed_for_source_match(system_obj, self.source_data)
        ):
            found = _curve_roots_in_brush(system_obj, hit_location, hit_radius)
            if found:
                self._track_touched_system(system_obj)
                return system_obj
        if system_obj is not None:
            self.active_system_name = ""
        if not self.hover_target:
            return None
        target_kind = self.hover_target["kind"]
        target_owner = self.hover_target["target_owner"]
        surface_obj = self.hover_target["surface_obj"]
        if create:
            system_obj = _find_or_create_world_system(
                self,
                context,
                self.source_data,
                surface_obj,
                target_kind=target_kind,
                target_owner=target_owner if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE else None,
            )
        else:
            system_obj = _matching_world_system(
                surface_obj,
                self.source_data,
                target_kind=target_kind,
                target_owner=target_owner if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE else None,
            )
            if system_obj is None and hit_location is not None:
                system_obj = _matching_world_system_by_brush_hit(
                    self.source_data,
                    hit_location,
                    hit_radius,
                )
        if system_obj is not None:
            self.density_spacing = _stored_system_density_spacing(
                system_obj,
                fallback=self.density_spacing,
            )
            self._set_active_system(context, system_obj)
        return system_obj

    def _active_target_surface(self):
        if not self.hover_target:
            return None
        return self.hover_target.get("surface_obj")

    def _current_hit(self):
        if not self.hover_target:
            return None
        location = self.hover_target.get("location")
        normal = self.hover_target.get("normal")
        if location is None or normal is None:
            return None
        location_copy = _safe_copy_target_vector(location)
        normal_copy = _safe_copy_target_vector(normal)
        if location_copy is None or normal_copy is None:
            return None
        return {"location": location_copy, "normal": normal_copy}

    def _sample_brush_hits(self, context, center_world, normal_world, count, *, existing_locations=None, min_spacing=0.0, min_gap_distance=0.0, candidate_radius=None):
        if not self.hover_target or count <= 0:
            return []
        tangent, bitangent, _normal = _surface_basis(normal_world)
        target_surface = self._active_target_surface()
        eval_surface = _evaluated_surface_object(context, target_surface)
        samples = []
        existing_points = [location.copy() for location in (existing_locations or []) if location is not None]
        spacing = max(0.0, float(min_spacing))
        gap_threshold = max(0.0, float(min_gap_distance))
        sample_radius = max(
            WORLD_MIN_OPERATION_RADIUS,
            float(candidate_radius if candidate_radius is not None else self.brush_radius),
        )
        max_attempts = min(max(count * 12, 128), 2048)
        candidates = []

        for _index in range(max_attempts):
            angle = random.random() * math.tau
            radius = sample_radius * (random.random() ** 0.5)
            candidate = center_world + tangent * math.cos(angle) * radius + bitangent * math.sin(angle) * radius
            snapped_location, snapped_normal = _snap_point_to_surface(
                context,
                target_surface,
                candidate,
                eval_surface=eval_surface,
            )
            if snapped_location is None or snapped_normal is None:
                continue

            nearest_existing = _nearest_point_distance(snapped_location, existing_points)
            if spacing > 0.0 and nearest_existing < spacing:
                continue
            candidates.append((nearest_existing, snapped_location.copy(), snapped_normal.copy()))

        selected_points = list(existing_points)
        for nearest_existing, snapped_location, snapped_normal in sorted(candidates, key=lambda item: item[0], reverse=True):
            if len(samples) >= count:
                break
            if gap_threshold > 0.0 and nearest_existing < gap_threshold:
                continue
            if spacing > 0.0 and _nearest_point_distance(snapped_location, selected_points) < spacing:
                continue
            selected_points.append(snapped_location.copy())
            samples.append({
                "location": snapped_location,
                "normal": snapped_normal if self.align_to_normal else normal_world,
                "length": _default_curve_length(self._current_system() or bpy.data.objects.get(self.active_system_name)),
                "z_rotation": 0.0,
            })
        return samples

    def _apply_density_tool(self, context, hit, *, erase=False):
        operation_radius = _density_operation_radius(self.brush_radius, self.density_spacing)
        erase_radius = max(operation_radius, self.brush_radius, self.density_spacing)
        if erase:
            _mark_same_source_curve_caches_dirty(
                self.source_data,
                extra_system=self._current_system(),
            )
        system_obj = self._ensure_current_system(
            context,
            create=not erase,
            hit_location=hit["location"] if erase else None,
            hit_radius=erase_radius,
        )
        if system_obj is None:
            return
        found = _curve_roots_in_brush(system_obj, hit["location"], operation_radius)
        if erase:
            found = _curve_roots_in_brush(system_obj, hit["location"], erase_radius)
            _remove_curves_from_system(context, system_obj, [item["curve_index"] for item in found])
            return

        target_count = _density_target_count(operation_radius, self.density_spacing)
        current_count = len(found)
        if current_count > target_count:
            to_remove = _crowded_curve_indices(
                found,
                current_count - target_count,
                crowding_threshold=self.density_spacing * 0.72,
            )
            if not to_remove:
                return
            _remove_curves_from_system(
                context,
                system_obj,
                to_remove,
            )
        elif current_count < target_count:
            occupied_found = _curve_roots_in_brush(system_obj, hit["location"], self.brush_radius)
            new_samples = self._sample_brush_hits(
                context,
                hit["location"],
                hit["normal"],
                target_count - current_count,
                existing_locations=[item["location"] for item in occupied_found],
                min_spacing=self.density_spacing * 0.9,
                min_gap_distance=self.density_spacing * 1.08,
                candidate_radius=operation_radius,
            )
            if not new_samples:
                return
            _add_curves_to_system(
                context,
                system_obj,
                new_samples,
            )

    def _apply_single_tool(self, context, hit):
        system_obj = self._ensure_current_system(context)
        if system_obj is None:
            return
        target_surface = self._active_target_surface()
        eval_surface = _evaluated_surface_object(context, target_surface)
        snapped_location, snapped_normal = _snap_point_to_surface(
            context,
            target_surface,
            hit["location"],
            eval_surface=eval_surface,
        )
        if snapped_location is None or snapped_normal is None:
            return
        _add_curves_to_system(context, system_obj, [{
            "location": snapped_location,
            "normal": snapped_normal if self.align_to_normal else hit["normal"],
            "length": _default_curve_length(system_obj),
            "z_rotation": 0.0,
        }])

    def _apply_slide_tool(self, context, hit):
        system_obj = self._ensure_current_system(context)
        if system_obj is None or self.stroke_last_world is None:
            return
        delta = hit["location"] - self.stroke_last_world
        target_surface = self._active_target_surface()
        eval_surface = _evaluated_surface_object(context, target_surface)
        found = _curves_in_brush(system_obj, hit["location"], self.brush_radius)
        updates = {}
        _offsets, _positions, roots, tips, _lengths = _system_curve_world_data(system_obj)
        for curve_index, distance in found:
            falloff = max(0.0, 1.0 - distance / self.brush_radius)
            root_world = roots[curve_index]
            tip_world = tips[curve_index]
            if root_world is None or tip_world is None:
                continue
            snapped_location, _snapped_normal = _snap_point_to_surface(
                context,
                target_surface,
                root_world + delta * falloff,
                eval_surface=eval_surface,
            )
            if snapped_location is None:
                continue
            move_delta = snapped_location - root_world
            updates[curve_index] = {"root": snapped_location, "tip": tip_world + move_delta}
        _update_curve_positions(context, system_obj, updates)

    def _apply_comb_tool(self, context, hit, *, reset=False, rotate_only=False):
        system_obj = self._ensure_current_system(context)
        if system_obj is None:
            return
        found = _curves_in_brush(system_obj, hit["location"], self.brush_radius)
        updates = {}
        z_rotation_updates = {}
        _offsets, _positions, roots, tips, lengths = _system_curve_world_data(system_obj)
        stroke_delta = None if self.stroke_last_world is None else (hit["location"] - self.stroke_last_world)
        tangent, bitangent, normal = _surface_basis(hit["normal"])
        stroke_dir = tangent if stroke_delta is None or stroke_delta.length < 0.0001 else stroke_delta.normalized()
        angle = math.atan2(stroke_dir.y, stroke_dir.x)

        for curve_index, distance in found:
            falloff = max(0.0, 1.0 - distance / self.brush_radius)
            root_world = roots[curve_index]
            tip_world = tips[curve_index]
            if root_world is None or tip_world is None:
                continue
            length = max(lengths[curve_index], _default_curve_length(system_obj))
            if reset:
                updates[curve_index] = {"root": root_world, "tip": root_world + normal * length}
                z_rotation_updates[curve_index] = 0.0
                continue
            if rotate_only:
                z_rotation_updates[curve_index] = angle
                continue
            new_direction = ((tip_world - root_world).normalized() * (1.0 - falloff) + stroke_dir * falloff)
            if new_direction.length < 0.0001:
                new_direction = normal
            new_direction.normalize()
            updates[curve_index] = {"root": root_world, "tip": root_world + new_direction * length}
        _update_curve_positions(context, system_obj, updates, z_rotation_updates=z_rotation_updates if z_rotation_updates else None)

    def _apply_scale_tool(self, context, hit, *, shrink=False, normalize=False, randomize=False):
        system_obj = self._ensure_current_system(context)
        if system_obj is None:
            return
        found = _curves_in_brush(system_obj, hit["location"], self.brush_radius)
        updates = {}
        _offsets, _positions, roots, tips, lengths = _system_curve_world_data(system_obj)
        average_length = sum(length for length in lengths if length > 0.0) / max(1, len([length for length in lengths if length > 0.0]))
        delta = self.brush_radius * 0.15
        for curve_index, distance in found:
            falloff = max(0.0, 1.0 - distance / self.brush_radius)
            root_world = roots[curve_index]
            tip_world = tips[curve_index]
            if root_world is None or tip_world is None:
                continue
            direction = tip_world - root_world
            if direction.length < 0.0001:
                direction = hit["normal"]
            direction.normalize()
            length = max(lengths[curve_index], _default_curve_length(system_obj))
            if normalize:
                target_length = average_length
            elif randomize:
                target_length = max(0.01, length + random.uniform(-delta, delta))
            elif shrink:
                target_length = max(0.01, length - delta * falloff)
            else:
                target_length = length + delta * falloff
            updates[curve_index] = {"root": root_world, "tip": root_world + direction * target_length}
        _update_curve_positions(context, system_obj, updates)

    def _apply_select_tool(self, context, hit, *, deselect=False):
        system_obj = self._ensure_current_system(context)
        if system_obj is None:
            return
        found = _curves_in_brush(system_obj, hit["location"], self.brush_radius)
        _update_curve_positions(
            context,
            system_obj,
            {},
            selection_mode={"indices": [curve_index for curve_index, _distance in found], "deselect": deselect},
        )

    def _density_erase_candidate_matches(self, context, hit_location, radius):
        candidates = []
        seen = set()

        def add_candidate(system_obj):
            if not _is_secret_paint_system(system_obj):
                return
            if not _world_system_allowed_for_source_match(system_obj, self.source_data):
                return
            cache_key = _system_cache_key(system_obj)
            if cache_key in seen:
                return
            seen.add(cache_key)
            candidates.append(system_obj)

        add_candidate(self._current_system())
        if self._native_density_active_system_name:
            add_candidate(bpy.data.objects.get(self._native_density_active_system_name))
        if self.source_data.get("origin_kind") == "SYSTEM":
            add_candidate(self.source_data.get("origin_object"))

        if self.hover_target:
            target_kind = self.hover_target.get("kind", WORLD_TARGET_KIND_MESH)
            target_owner = self.hover_target.get("target_owner")
            target_surface = self.hover_target.get("surface_obj")
            if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE:
                add_candidate(target_owner)
            add_candidate(
                _matching_world_system(
                    target_surface,
                    self.source_data,
                    target_kind=target_kind,
                    target_owner=target_owner if target_kind == WORLD_TARGET_KIND_SECRET_INSTANCE else None,
                )
            )

        matching_candidates = []
        for system_obj in candidates:
            found = _curve_roots_in_brush(system_obj, hit_location, radius)
            if found:
                matching_candidates.append((system_obj, found))
        return matching_candidates

    def _apply_density_erase_tool(self, context, hit, *, force_refresh=False, preserve_root_cache=False):
        if hit is None:
            _native_brush_debug_log("density_erase.no_hit", context, self, force=True)
            return False
        operation_radius = _density_operation_radius(self.brush_radius, self.density_spacing)
        erase_radius = max(operation_radius, self.brush_radius, self.density_spacing)
        candidate_matches = self._density_erase_candidate_matches(context, hit["location"], erase_radius)
        removed_any = False
        found_count = 0
        candidate_names = []
        for system_obj, found in candidate_matches:
            candidate_names.append(getattr(system_obj, "name", ""))
            if not found:
                continue
            found_count += len(found)
            _remove_curves_from_system(
                context,
                system_obj,
                [item["curve_index"] for item in found],
                refresh=False,
                preserve_root_cache=preserve_root_cache,
            )
            removed_any = True
            if system_obj != self._current_system():
                self._set_active_system_preserve_brush_controls(context, system_obj)
            else:
                self.active_system_name = system_obj.name
                self._track_touched_system(system_obj)
        _native_brush_debug_log(
            "density_erase.apply",
            context,
            self,
            force=True,
            removed_any=removed_any,
            found_count=found_count,
            candidate_count=len(candidate_matches),
            candidate_names="|".join(candidate_names),
            erase_radius=erase_radius,
        )
        if removed_any:
            _maybe_refresh_live_view(context, force=force_refresh)
        return removed_any

    def _finish_bezier_stroke(self, context):
        if len(self.bezier_stroke_points) < 2 or not self.hover_target:
            self.bezier_stroke_points = []
            return
        surface_obj = self.hover_target["surface_obj"]
        curve_obj = _find_or_create_curve_draw_object(context, self.source_data, surface_obj)
        curve_data = curve_obj.data
        spline = curve_data.splines.new(type='BEZIER')
        spline.bezier_points.add(len(self.bezier_stroke_points) - 1)
        inv = curve_obj.matrix_world.inverted()
        for point, bezier_point in zip(self.bezier_stroke_points, spline.bezier_points):
            local_point = inv @ point
            bezier_point.co = local_point
            bezier_point.handle_left_type = 'AUTO'
            bezier_point.handle_right_type = 'AUTO'
        self.bezier_stroke_points = []

    def _apply_tool(self, context, hit, event, *, initial=False):
        if hit is None:
            return
        if self.tool_id == WORLD_TOOL_BEZIER:
            if initial:
                self.bezier_stroke_points = [hit["location"].copy()]
            elif not self.bezier_stroke_points or (self.bezier_stroke_points[-1] - hit["location"]).length >= self._stroke_spacing(
                context,
                depth_location=hit["location"],
            ):
                self.bezier_stroke_points.append(hit["location"].copy())
            return
        if self.tool_id == WORLD_TOOL_DENSITY:
            if self._density_delete_input_active(event):
                self._apply_density_erase_tool(context, hit)
            else:
                self._apply_density_tool(context, hit, erase=False)
        elif self.tool_id == WORLD_TOOL_SINGLE:
            self._apply_single_tool(context, hit)
        elif self.tool_id == WORLD_TOOL_SLIDE:
            self._apply_slide_tool(context, hit)
        elif self.tool_id == WORLD_TOOL_COMB:
            self._apply_comb_tool(context, hit, reset=event.shift, rotate_only=event.alt)
        elif self.tool_id == WORLD_TOOL_SCALE:
            self._apply_scale_tool(context, hit, shrink=event.shift, normalize=event.alt, randomize=event.ctrl)
        elif self.tool_id == WORLD_TOOL_SELECT:
            self._apply_select_tool(context, hit, deselect=event.shift)
        elif self.tool_id == WORLD_TOOL_DELETE:
            self._apply_native_density_delete_sample(
                context,
                hit,
                initial=initial,
                preserve_native_context=self._shift_delete_tool_active,
            )

    def _apply_native_density_delete_sample(self, context, hit, *, initial=False, preserve_native_context=False):
        restore_native_mode = (
            self._native_density_session_active and
            context.mode == 'SCULPT_CURVES' and
            not preserve_native_context
        )
        system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
        if restore_native_mode and system_obj is not None:
            _keep_active_system_object(context, system_obj)
            _mode_set_with_world_toolbar_restored('OBJECT')
        removed_any = self._apply_density_erase_tool(
            context,
            hit,
            preserve_root_cache=preserve_native_context,
        )
        if restore_native_mode and self._native_density_session_active:
            system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
            if system_obj is not None:
                _keep_active_system_object(context, system_obj)
            _mode_set_with_world_toolbar_restored('SCULPT_CURVES')
            self._prepare_native_density_stroke(context, erase=True)
        if hit is not None:
            self.stroke_last_sample_world = hit["location"].copy()
            self.stroke_last_world = hit["location"].copy()
        _native_brush_debug_log(
            "density_delete.manual_native_sample",
            context,
            self,
            force=True,
            initial=initial,
            removed_any=removed_any,
            preserve_native_context=preserve_native_context,
        )
        return removed_any

    def _sync_native_stroke_stable_ids(self, context, system_obj=None, *, force_refresh=False):
        system_obj = system_obj or self._current_system()
        if system_obj is None or not _is_secret_paint_system(system_obj):
            return False
        revision_before = _system_cache_revision(system_obj)
        try:
            stable_values = ensure_secret_paint_system_stable_ids(context, system_obj)
        except Exception:
            return False
        if not stable_values and _system_curve_count(system_obj) > 0:
            return False
        revision_changed = _system_cache_revision(system_obj) != revision_before
        if revision_changed:
            _remember_system_curve_cache_signature(system_obj)
        signature_changed = (
            False if revision_changed else
            _mark_system_curve_cache_dirty_if_signature_changed(system_obj)
        )
        if revision_changed or signature_changed:
            try:
                system_obj.data.update_tag()
            except Exception:
                pass
        if force_refresh:
            _maybe_refresh_live_view(context, force=True)
        return bool(stable_values or revision_changed or signature_changed)

    def _native_density_stable_id_system_names(self, context=None):
        system_names = set(getattr(self, "_touched_system_names", set()) or set())
        for name in (
            getattr(self, "active_system_name", ""),
            getattr(self, "_native_density_active_system_name", ""),
            getattr(self, "_active_name", ""),
        ):
            if name:
                system_names.add(name)

        current_system = self._current_system()
        if current_system is not None:
            system_names.add(current_system.name)

        if context is not None:
            active_obj = getattr(context, "active_object", None)
            if _is_secret_paint_system(active_obj):
                system_names.add(active_obj.name)

        source_obj = self.source_data.get("origin_object") if isinstance(self.source_data, dict) else None
        if _is_secret_paint_system(source_obj):
            system_names.add(source_obj.name)

        return {
            name
            for name in system_names
            if name and _is_secret_paint_system(bpy.data.objects.get(name))
        }

    def _schedule_native_stroke_stable_id_sync(
        self,
        context,
        system_obj=None,
        *,
        system_names=None,
        while_painting=False,
        force_refresh=False,
    ):
        if system_names is None:
            system_name = getattr(system_obj or self._current_system(), "name", "")
            system_names = (system_name,) if system_name else ()
        system_names = tuple(dict.fromkeys(name for name in system_names if name))
        if not system_names and hasattr(self, "_native_density_stable_id_system_names"):
            system_names = tuple(sorted(self._native_density_stable_id_system_names(context)))
        if not system_names:
            return False
        if while_painting:
            for system_name in system_names:
                target_system = bpy.data.objects.get(system_name)
                if target_system is not None:
                    _remember_system_curve_cache_signature(target_system)
        self._native_stroke_stable_id_sync_token += 1
        sync_token = self._native_stroke_stable_id_sync_token
        attempts = {"count": 0}
        max_attempts = 4
        max_live_attempts = 120

        def _sync_stable_ids_after_native_stroke():
            operator = _world_operator()
            if operator is None:
                return None
            if sync_token != getattr(operator, "_native_stroke_stable_id_sync_token", 0):
                return None
            attempts["count"] += 1
            paint_is_active = (
                while_painting and
                bool(getattr(operator, "_primary_paint_button_down", False))
            )
            for system_name in system_names:
                target_system = bpy.data.objects.get(system_name)
                if target_system is None:
                    continue
                operator._sync_native_stroke_stable_ids(
                    bpy.context,
                    target_system,
                    force_refresh=force_refresh or (not paint_is_active and attempts["count"] >= max_attempts),
                )
            if paint_is_active and attempts["count"] < max_live_attempts:
                return 0.05
            return 0.05 if attempts["count"] < max_attempts else None

        try:
            bpy.app.timers.register(_sync_stable_ids_after_native_stroke, first_interval=0.02)
        except Exception:
            for system_name in system_names:
                target_system = bpy.data.objects.get(system_name)
                if target_system is not None:
                    self._sync_native_stroke_stable_ids(
                        context,
                        target_system,
                        force_refresh=True,
                    )
        return True

    def _sync_touched_native_stroke_stable_ids(self, context):
        system_names = set(getattr(self, "_touched_system_names", set()) or set())
        current_system = self._current_system()
        if current_system is not None:
            system_names.add(current_system.name)
        if self._native_density_active_system_name:
            system_names.add(self._native_density_active_system_name)
        synced_any = False
        for system_name in list(system_names):
            system_obj = bpy.data.objects.get(system_name)
            if system_obj is None:
                continue
            synced_any = bool(self._sync_native_stroke_stable_ids(context, system_obj)) or synced_any
        self._schedule_native_stroke_stable_id_sync(
            context,
            system_names=system_names,
            force_refresh=True,
        )
        return synced_any

    def _schedule_native_adjust_passthrough_stable_id_sync(self, context, event=None):
        if self.tool_id != WORLD_TOOL_DENSITY or not self._density_uses_native_ui():
            return False
        system_names = self._native_density_stable_id_system_names(context)
        if not system_names:
            return False
        primary_active = event is not None and _is_primary_paint_active_event(event)
        primary_end = event is not None and _is_primary_paint_end_event(event)
        if primary_active:
            self._primary_paint_button_down = True
        elif primary_end:
            self._primary_paint_button_down = False
        return self._schedule_native_stroke_stable_id_sync(
            context,
            system_names=system_names,
            while_painting=primary_active,
            force_refresh=primary_end,
        )

    def _begin_stroke(self, context, event):
        right_delete_stroke = self._is_density_right_delete_event(event)
        density_delete_stroke = (
            self.tool_id == WORLD_TOOL_DENSITY and
            self._density_delete_input_active(event)
        )
        if right_delete_stroke:
            self._flush_pending_native_density_adjust_result(context)
            self._density_right_delete_restore_token = getattr(
                self,
                "_density_right_delete_restore_token",
                0,
            ) + 1
            self._density_right_delete_button_down = True
            self._density_right_delete_restore_pending = True
            density_delete_stroke = True
        if self.tool_id == WORLD_TOOL_DENSITY and density_delete_stroke:
            _shift_delete_debug_log("begin_stroke.shift_density_enter", context, self, event=event, force=True)
        _native_brush_debug_log(
            "begin_stroke.enter",
            context,
            self,
            force=True,
            event_type=getattr(event, "type", ""),
            event_value=getattr(event, "value", ""),
            event_shift=getattr(event, "shift", ""),
        )
        self._primary_paint_button_down = True
        if self._surface_lock_waiting_for_target() and context.mode != 'OBJECT':
            try:
                _mode_set_with_world_toolbar_restored('OBJECT')
            except Exception:
                pass
        previous_target_key = self.last_hover_key
        with shared.secret_paint_world_perf_span(
            "world.begin_stroke_hover_raycast",
            threshold_ms=1.0,
            tool=self.tool_id,
        ):
            self._update_hover_target(context, event, commit=True)
        if self.tool_id == WORLD_TOOL_DENSITY and density_delete_stroke:
            self._update_density_delete_target_through_instances(context, event, commit=True)
        target_switched_on_press = (
            self.tool_id == WORLD_TOOL_DENSITY and
            bool(previous_target_key) and
            bool(self.last_hover_key) and
            self.last_hover_key != previous_target_key
        )
        hit = self._current_hit()
        if hit is None and self.tool_id == WORLD_TOOL_DENSITY and density_delete_stroke:
            self._update_density_delete_target_through_instances(context, event, commit=True)
            hit = self._current_hit()
        if hit is None:
            self._primary_paint_button_down = False
            if right_delete_stroke:
                self._density_right_delete_button_down = False
                self._density_right_delete_restore_pending = False
            if self.surface_lock and self._locked_target_infos():
                self._notify_locked_terrain_miss(context)
            return False
        if right_delete_stroke and self.tool_id == WORLD_TOOL_DENSITY:
            self._begin_shift_delete_tool(context)
        _deselect_all_world_paint_objects(context)
        self._density_stroke_passthrough = False
        self.stroke_active = True
        self.stroke_last_world = hit["location"].copy()
        self.stroke_last_sample_world = hit["location"].copy()
        self.stroke_current_target = self.last_hover_key
        self._native_density_last_sample_mouse = None
        use_native_density_stroke = self._use_native_density_for_current_stroke(event)
        if use_native_density_stroke:
            self._defer_native_idle_session = False
        density_erase_stroke = density_delete_stroke
        temporary_shift_delete_stroke = (
            self.tool_id == WORLD_TOOL_DELETE and
            self._shift_delete_tool_active
        )
        native_delete_stroke = density_erase_stroke or temporary_shift_delete_stroke
        if density_erase_stroke:
            _shift_delete_debug_log(
                "begin_stroke.delete_decision",
                context,
                self,
                event=event,
                force=True,
                use_native_density_stroke=use_native_density_stroke,
                hit_ok=hit is not None,
                target_switched_on_press=target_switched_on_press,
                right_delete_stroke=right_delete_stroke,
            )
        self._native_density_stroke_erase = native_delete_stroke
        if native_delete_stroke:
            self._flush_pending_native_density_adjust_result(context)
            self._begin_native_tool_override("DELETE")
        _native_brush_debug_log(
            "begin_stroke.native_decision",
            context,
            self,
            force=True,
            use_native_density_stroke=use_native_density_stroke,
            density_erase_stroke=density_erase_stroke,
            target_switched_on_press=target_switched_on_press,
        )
        native_context_ready_before_press = False
        if use_native_density_stroke:
            press_system = self._ensure_current_system(context)
            if press_system is not None:
                _remember_system_curve_cache_signature(press_system)
            native_context_ready_before_press = self._native_density_session_matches_system(context, press_system)
        if (
            not use_native_density_stroke and
            self.tool_id == WORLD_TOOL_DENSITY and
            self._native_density_session_active and
            not density_erase_stroke
        ):
            self._finish_native_density_session(context, restore_selection=False)
        if use_native_density_stroke:
            with shared.secret_paint_world_perf_span(
                "world.begin_stroke_native_session",
                threshold_ms=1.0,
                tool=self.tool_id,
                erase=native_delete_stroke,
            ):
                native_session_ready = self._begin_native_density_session(context)
            if native_session_ready:
                with shared.secret_paint_world_perf_span(
                    "world.prepare_native_stroke",
                    threshold_ms=1.0,
                    tool=self.tool_id,
                    erase=native_delete_stroke,
                ):
                    native_stroke_ready = self._prepare_native_density_stroke(
                        context,
                        erase=native_delete_stroke,
                    )
                if native_stroke_ready:
                    _deselect_all_world_paint_objects(context)
                    if density_erase_stroke:
                        _shift_delete_debug_log("begin_stroke.delete_prepared", context, self, event=event, force=True)
                    self._active_density_stroke_mode = "native"
                    self.stroke_last_sample_world = hit["location"].copy()
                    self.stroke_last_world = hit["location"].copy()
                    self.stroke_current_target = self.last_hover_key
                    mouse_coord = self._native_density_mouse_coord(event)
                    if temporary_shift_delete_stroke:
                        self._active_density_stroke_mode = "native"
                        self._native_density_interaction_mode = "NATIVE_UI"
                        self._density_stroke_passthrough = True
                        modal_started = self._invoke_native_delete_modal_without_shift_toggle(context)
                        _native_brush_debug_log(
                            "begin_stroke.shift_delete_native_modal",
                            context,
                            self,
                            force=True,
                            modal_started=modal_started,
                        )
                        if modal_started:
                            self._native_density_interaction_mode = "NATIVE_UI"
                            self._density_stroke_passthrough = True
                            self._native_density_last_sample_mouse = mouse_coord
                            return False
                        self._native_density_interaction_mode = "HANDOFF_PROXY"
                        self._density_stroke_passthrough = False
                        stroke_ok = self._invoke_native_density_brush_stroke(context, event)
                        _native_brush_debug_log(
                            "begin_stroke.shift_delete_native_sample",
                            context,
                            self,
                            force=True,
                            stroke_ok=stroke_ok,
                        )
                        if stroke_ok:
                            self._native_density_last_sample_mouse = mouse_coord
                            return False
                        self._active_density_stroke_mode = "manual_shift_delete"
                        self._native_density_interaction_mode = "MANUAL_DELETE"
                        removed_any = self._apply_native_density_delete_sample(
                            context,
                            hit,
                            initial=True,
                            preserve_native_context=True,
                        )
                        _native_brush_debug_log(
                            "begin_stroke.shift_delete_manual_fallback",
                            context,
                            self,
                            force=True,
                            removed_any=removed_any,
                        )
                        self._native_density_last_sample_mouse = mouse_coord
                        return False
                    if density_erase_stroke:
                        if right_delete_stroke:
                            _shift_delete_debug_log(
                                "begin_stroke.right_delete_handoff",
                                context,
                                self,
                                event=event,
                                force=True,
                                target_switched_on_press=target_switched_on_press,
                                native_context_ready=native_context_ready_before_press,
                            )
                        self._native_density_interaction_mode = "HANDOFF_PROXY"
                        self._density_stroke_passthrough = False
                        stroke_ok = self._invoke_native_density_brush_stroke(context, event)
                        _shift_delete_debug_log(
                            "begin_stroke.delete_native_stroke_result",
                            context,
                            self,
                            event=event,
                            force=True,
                            stroke_ok=stroke_ok,
                        )
                        if stroke_ok:
                            self._native_density_last_sample_mouse = mouse_coord
                            return False
                        if right_delete_stroke:
                            self._active_density_stroke_mode = "manual_right_delete"
                            self._native_density_interaction_mode = "MANUAL_DELETE"
                            self._density_stroke_passthrough = False
                            removed_any = self._apply_native_density_delete_sample(
                                context,
                                hit,
                                initial=True,
                                preserve_native_context=True,
                            )
                            self._native_density_last_sample_mouse = mouse_coord
                            _shift_delete_debug_log(
                                "begin_stroke.right_delete_manual_fallback",
                                context,
                                self,
                                event=event,
                                force=True,
                                removed_any=removed_any,
                            )
                            return False
                        self._native_density_interaction_mode = "NATIVE_UI"
                        self._density_stroke_passthrough = True
                        self._native_density_last_sample_mouse = mouse_coord
                        _shift_delete_debug_log(
                            "begin_stroke.delete_native_passthrough_fallback",
                            context,
                            self,
                            event=event,
                            force=True,
                        )
                        return True
                    if self.tool_id != WORLD_TOOL_DENSITY:
                        self._native_density_interaction_mode = "NATIVE_UI"
                        self._density_stroke_passthrough = True
                        self._native_density_last_sample_mouse = mouse_coord
                        return True
                    if target_switched_on_press or not native_context_ready_before_press:
                        self._native_density_interaction_mode = "HANDOFF_PROXY"
                        self._density_stroke_passthrough = False
                        if self._invoke_native_density_brush_stroke(context, event):
                            self._native_density_last_sample_mouse = mouse_coord
                            return False
                    self._native_density_interaction_mode = "NATIVE_UI"
                    self._density_stroke_passthrough = True
                    self._native_density_last_sample_mouse = mouse_coord
                    return True
                self._finish_native_density_session(context, restore_selection=False)
            return self._abort_native_density_stroke(context, event)
        self._apply_tool(context, hit, event, initial=True)
        _native_brush_debug_log("begin_stroke.manual_apply_exit", context, self, force=True)
        return self._density_stroke_passthrough

    def _abort_native_density_stroke(self, context, event=None):
        self._finish_native_density_session(context, restore_selection=False)
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._update_hover_target(context, event, commit=False)
        self._primary_paint_button_down = False
        self.stroke_active = False
        self.stroke_last_world = None
        self.stroke_last_sample_world = None
        self.stroke_current_target = ""
        self._active_density_stroke_mode = ""
        self._native_density_interaction_mode = ""
        self._density_stroke_passthrough = False
        self._native_density_last_sample_mouse = None
        self._native_density_stroke_erase = False
        self._density_right_delete_button_down = False
        return False

    def _handoff_native_density_stroke(self, context, event, preview_target):
        if preview_target is None or not self._density_target_handoff_active():
            return False
        self._density_stroke_passthrough = False
        self._activate_hover_target(context, preview_target)
        self.stroke_current_target = self.last_hover_key
        self.stroke_last_sample_world = None
        hit = self._current_hit()
        if hit is not None:
            self.stroke_last_world = hit["location"].copy()
        erase_stroke = self._native_density_stroke_erase
        if not self._begin_native_density_session(context):
            return self._abort_native_density_stroke(context, event)
        self._native_density_stroke_erase = erase_stroke
        if not self._prepare_native_density_stroke(
            context,
            erase=erase_stroke,
        ):
            return self._abort_native_density_stroke(context, event)
        _deselect_all_world_paint_objects(context)
        mouse_coord = self._native_density_mouse_coord(event)
        if not erase_stroke:
            self._active_density_stroke_mode = "native"
            self._native_density_interaction_mode = "HANDOFF_PROXY"
            self._density_stroke_passthrough = False
            if self._invoke_native_density_brush_stroke(context, event):
                self._native_density_last_sample_mouse = mouse_coord
                hit = self._current_hit()
                if hit is not None:
                    self.stroke_last_sample_world = hit["location"].copy()
                    self.stroke_last_world = hit["location"].copy()
                return False
            self._native_density_interaction_mode = "NATIVE_UI"
            self._density_stroke_passthrough = True
            self._native_density_last_sample_mouse = mouse_coord
            return True

        self._native_density_interaction_mode = "HANDOFF_PROXY"
        self._density_stroke_passthrough = False
        if self._invoke_native_density_brush_stroke(context, event):
            self._native_density_last_sample_mouse = mouse_coord
            hit = self._current_hit()
            if hit is not None:
                self.stroke_last_sample_world = hit["location"].copy()
                self.stroke_last_world = hit["location"].copy()
            return False
        return self._abort_native_density_stroke(context, event)

    def _continue_stroke(self, context, event):
        if not self.stroke_active:
            return False
        if (
            (self._use_native_density_backend() or self._use_native_tool_backend()) and
            self._active_density_stroke_mode == "native"
        ):
            preview_target = None
            preview_key = ""
            handoff_active = self._density_target_handoff_active()
            needs_target_update = handoff_active or self._native_density_interaction_mode != "NATIVE_UI"
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
                if needs_target_update:
                    with shared.secret_paint_world_perf_span(
                        "world.continue_stroke_hover_raycast",
                        threshold_ms=1.0,
                        tool=self.tool_id,
                        mode=self._native_density_interaction_mode,
                    ):
                        self._update_hover_target(context, event, commit=False)
                    if self._native_density_stroke_erase:
                        self._update_density_delete_target_through_instances(context, event, commit=False)
                    preview_target = self.preview_target
                    preview_key = _target_key(preview_target)
            if (
                handoff_active and
                preview_target is not None and
                preview_key and
                preview_key != self.stroke_current_target
            ):
                return self._handoff_native_density_stroke(context, event, preview_target)
            if self._native_density_interaction_mode == "MANUAL_DELETE":
                self._native_density_interaction_mode = "HANDOFF_PROXY"
            if self._native_density_interaction_mode == "NATIVE_UI":
                if not self._native_density_session_matches_context(context):
                    return self._abort_native_density_stroke(context, event)
                hit = self._current_hit()
                if hit is not None:
                    self.stroke_last_sample_world = hit["location"].copy()
                    self.stroke_last_world = hit["location"].copy()
                self._native_density_last_sample_mouse = self._native_density_mouse_coord(event)
                return True
            if not self._native_density_session_matches_context(context):
                erase_stroke = self._native_density_stroke_erase
                if not self._begin_native_density_session(context):
                    return self._abort_native_density_stroke(context, event)
                self._native_density_stroke_erase = erase_stroke
                if not self._prepare_native_density_stroke(
                    context,
                    erase=erase_stroke,
                ):
                    return self._abort_native_density_stroke(context, event)
                self._native_density_interaction_mode = "HANDOFF_PROXY"
            system_obj = bpy.data.objects.get(self._native_density_active_system_name) if self._native_density_active_system_name else None
            should_sample, mouse_coord = self._native_density_should_sample(context, event, system_obj=system_obj)
            if self._native_density_stroke_erase:
                _shift_delete_debug_log(
                    "continue_stroke.delete_sample_decision",
                    context,
                    self,
                    event=event,
                    force=should_sample,
                    should_sample=should_sample,
                    system_obj=getattr(system_obj, "name", ""),
                )
            if should_sample:
                stroke_ok = self._invoke_native_density_brush_stroke(context, event)
                if self._native_density_stroke_erase:
                    _shift_delete_debug_log(
                        "continue_stroke.delete_native_stroke_result",
                        context,
                        self,
                        event=event,
                        force=True,
                        stroke_ok=stroke_ok,
                    )
                if stroke_ok:
                    self._native_density_last_sample_mouse = mouse_coord
                else:
                    if (
                        self._shift_delete_tool_active and
                        self._native_density_stroke_erase
                    ):
                        hit = self._current_hit()
                        if hit is not None:
                            self._active_density_stroke_mode = "manual_shift_delete"
                            self._native_density_interaction_mode = "MANUAL_DELETE"
                            removed_any = self._apply_native_density_delete_sample(
                                context,
                                hit,
                                preserve_native_context=True,
                            )
                            _native_brush_debug_log(
                                "continue_stroke.shift_delete_manual_fallback",
                                context,
                                self,
                                force=True,
                                removed_any=removed_any,
                            )
                            self._native_density_last_sample_mouse = mouse_coord
                            self.stroke_last_sample_world = hit["location"].copy()
                            self.stroke_last_world = hit["location"].copy()
                            return False
                    return self._abort_native_density_stroke(context, event)
                hit = self._current_hit()
                if hit is not None:
                    self.stroke_last_sample_world = hit["location"].copy()
                    self.stroke_last_world = hit["location"].copy()
            return False
        self._update_hover_target(context, event, commit=False)
        hit = self._current_hit()
        if hit is None and self.tool_id == WORLD_TOOL_DENSITY and self._density_delete_input_active(event):
            self._update_density_delete_target_through_instances(context, event, commit=False)
            hit = self._current_hit()
        if hit is None:
            self.stroke_last_world = None
            self.stroke_last_sample_world = None
            self.stroke_current_target = self.last_hover_key
            return self._density_stroke_passthrough
        if self.stroke_current_target != self.last_hover_key:
            self.stroke_last_sample_world = None
            self.stroke_current_target = self.last_hover_key

        if self.stroke_last_sample_world is None or (hit["location"] - self.stroke_last_sample_world).length >= self._stroke_spacing(
            context,
            depth_location=hit["location"],
        ):
            self._apply_tool(context, hit, event, initial=False)
            self.stroke_last_sample_world = hit["location"].copy()
        self.stroke_last_world = hit["location"].copy()
        return self._density_stroke_passthrough

    def _finish_stroke(self, context, event):
        _native_brush_debug_log("finish_stroke.enter", context, self, force=True, event_type=getattr(event, "type", "") if event is not None else "")
        if (
            self._shift_delete_tool_active and
            event is not None and
            hasattr(event, "shift") and
            getattr(event, "type", "") not in {'LEFT_SHIFT', 'RIGHT_SHIFT'}
        ):
            self._shift_key_held = bool(getattr(event, "shift", False))
        self._native_passthrough_finish_pending = False
        self._native_passthrough_finish_token = getattr(self, "_native_passthrough_finish_token", 0) + 1
        passthrough = self._density_stroke_passthrough
        native_proxy = self._active_density_stroke_mode == "native" and self._native_density_session_active
        right_delete_waiting_for_release = bool(
            getattr(self, "_density_right_delete_button_down", False) and
            not (
                event is not None and
                self._is_density_right_delete_release_event(event)
            )
        )
        restore_density_brush_size = native_proxy and (
            self._native_density_stroke_erase or self._native_tool_override_brush_type == "DELETE"
        )
        if native_proxy:
            if self._native_density_stroke_erase or self._native_tool_override_brush_type == "DELETE":
                self._restore_native_density_brush_mode(context)
            self._native_density_last_sample_mouse = None
            if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._sync_touched_native_stroke_stable_ids(context)
            self._defer_native_idle_session = not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE
        elif self.tool_id == WORLD_TOOL_BEZIER:
            self._finish_bezier_stroke(context)
        if not native_proxy:
            _maybe_refresh_live_view(context, force=True)
        self.stroke_active = False
        self.stroke_last_world = None
        self.stroke_last_sample_world = None
        self.stroke_current_target = ""
        self._active_density_stroke_mode = ""
        self._native_density_interaction_mode = ""
        self._density_stroke_passthrough = False
        self._native_density_stroke_erase = False
        if not right_delete_waiting_for_release:
            self._density_right_delete_button_down = False
        if restore_density_brush_size and self.tool_id == WORLD_TOOL_DENSITY:
            self._sync_native_density_brush(context, system_obj=self._current_system())
        if native_proxy and self.tool_id == WORLD_TOOL_DENSITY:
            try:
                self._restore_native_density_brush_overlay()
                self._restore_native_density_brush_visibility(context)
                self._force_native_brush_visibility(context)
            except Exception:
                pass
        if native_proxy and not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
            self._defer_idle_native_density_session(context)
        elif not native_proxy:
            _keep_active_system_object(context, self._current_system())
        if (
            self._shift_delete_tool_active and
            not self._shift_key_held and
            not right_delete_waiting_for_release
        ):
            self._restore_shift_delete_tool(context)
        _native_brush_debug_log("finish_stroke.exit", context, self, force=True, passthrough=passthrough)
        return passthrough

    def _finish_native_passthrough_after_blender_event(self, event=None):
        finish_right_delete_after_event = self._is_density_right_delete_end_event(event)
        if self._native_passthrough_finish_pending and not finish_right_delete_after_event:
            return
        self._native_passthrough_finish_pending = True
        self._native_passthrough_finish_token = getattr(self, "_native_passthrough_finish_token", 0) + 1
        finish_token = self._native_passthrough_finish_token
        operator = self
        shift_held_after_event = bool(
            getattr(event, "shift", operator._shift_key_held)
            if event is not None
            else operator._shift_key_held
        )

        def _finish_after_event():
            try:
                if operator._native_passthrough_finish_token != finish_token:
                    return None
                operator._native_passthrough_finish_pending = False
                if operator._running and operator.stroke_active:
                    if operator._shift_delete_tool_active:
                        operator._shift_key_held = shift_held_after_event
                    operator._end_paint_interaction(bpy.context, None)
                    if operator._shift_key_held and operator.tool_id == WORLD_TOOL_DENSITY:
                        operator._sync_density_shift_delete_brush(bpy.context)
                if finish_right_delete_after_event and operator._running:
                    operator._finish_density_right_delete_release(bpy.context)
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(
                _finish_after_event,
                first_interval=0.0 if finish_right_delete_after_event else 0.01,
            )
        except Exception:
            self._native_passthrough_finish_pending = False

    def _finish_density_right_delete_release(self, context):
        shared.secret_paint_brush_size_trace_log(
            "world.finish_right_delete_release.enter",
            context,
            self,
        )
        self._clear_density_delete_native_state()
        commit_pending_size = getattr(self, "_commit_pending_native_size_adjust_confirm", None)
        if callable(commit_pending_size):
            committed_pending_size = commit_pending_size(context)
        else:
            committed_pending_size = False
        shared.secret_paint_brush_size_trace_log(
            "world.finish_right_delete_release.after_pending_size_commit",
            context,
            self,
            committed_pending_size=committed_pending_size,
        )
        if self._shift_delete_tool_active or self.tool_id == WORLD_TOOL_DELETE:
            return_tool_id = self._shift_delete_return_tool_id or WORLD_TOOL_DENSITY
            self._shift_delete_tool_active = False
            self._shift_delete_return_tool_id = ""
            self._set_tool(context, return_tool_id, sync_workspace=True, preserve_shift=True)
            if return_tool_id == WORLD_TOOL_DENSITY:
                self._schedule_density_native_brush_restore_after_delete()
        elif self.tool_id == WORLD_TOOL_DENSITY:
            self._restore_density_native_brush_after_delete(context, schedule=True)
        shared.secret_paint_brush_size_trace_log(
            "world.finish_right_delete_release.exit",
            context,
            self,
        )

    def _sync_primary_paint_button_state(self, event):
        current_state = _primary_paint_button_state_from_event(event)
        if current_state is not None:
            self._primary_paint_button_down = current_state
            return
        previous_state = _primary_paint_button_state_from_event(event, previous=True)
        if previous_state is False:
            self._primary_paint_button_down = False

    def _end_paint_interaction(self, context, event=None):
        if self.stroke_active:
            self._finish_stroke(context, event)
        elif self._native_density_session_active:
            self._finish_native_density_session(context, restore_selection=False)
        self._primary_paint_button_down = False
        self.stroke_active = False
        self.stroke_last_world = None
        self.stroke_last_sample_world = None
        self.stroke_current_target = ""
        self._active_density_stroke_mode = ""
        self._native_density_interaction_mode = ""
        self._density_stroke_passthrough = False
        self._native_density_stroke_erase = False
        self._density_right_delete_button_down = False
        return False

    def _active_native_brush_size_state(self, context):
        brush_container = _tool_settings_brush_container(context)
        brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if brush is None or getattr(brush, "curves_sculpt_settings", None) is None:
            return "", 0.0
        unified_settings = (
            getattr(brush_container, "unified_paint_settings", None)
            if brush_container is not None
            else None
        )
        use_unified_size = bool(
            unified_settings is not None and
            getattr(unified_settings, "use_unified_size", False)
        )
        size_owners = []
        if use_unified_size and unified_settings is not None:
            size_owners.append(unified_settings)
        size_owners.append(brush)

        for owner in size_owners:
            if owner is None:
                continue
            lock_mode = ""
            try:
                lock_mode = getattr(owner, "use_locked_size", "")
            except Exception:
                lock_mode = ""
            if lock_mode == 'SCENE' and hasattr(owner, "unprojected_size"):
                try:
                    native_world_diameter = float(getattr(owner, "unprojected_size", 0.0))
                except Exception:
                    native_world_diameter = 0.0
                if native_world_diameter > 0.0:
                    return "WORLD_RADIUS", max(WORLD_MIN_OPERATION_RADIUS, native_world_diameter * 0.5)
            if hasattr(owner, "size"):
                try:
                    native_screen_diameter = float(getattr(owner, "size", 0.0))
                except Exception:
                    native_screen_diameter = 0.0
                if native_screen_diameter > 0.0:
                    return "SCREEN_RADIUS", max(1.0, native_screen_diameter * 0.5)

        return "", 0.0

    def _screen_radius_to_world_radius(self, context, screen_radius_px, *, depth_location=None):
        try:
            screen_radius_px = float(screen_radius_px)
        except Exception:
            screen_radius_px = 0.0
        if screen_radius_px <= 0.0:
            return 0.0

        area, region, space = _view3d_area_data(context, self._invoke_area_pointer)
        region_data = getattr(space, "region_3d", None) if space is not None else getattr(context, "region_data", None)
        if region is None or region_data is None:
            return 0.0

        depth_location = depth_location or self._brush_screen_depth_location()
        if depth_location is None:
            return 0.0

        mouse_coord = getattr(self, "hover_mouse_region", None)
        if not mouse_coord:
            mouse_coord = (float(region.width) * 0.5, float(region.height) * 0.5)
        center = (float(mouse_coord[0]), float(mouse_coord[1]))
        edge = (center[0] + screen_radius_px, center[1])
        try:
            center_world = view3d_utils.region_2d_to_location_3d(region, region_data, center, depth_location)
            edge_world = view3d_utils.region_2d_to_location_3d(region, region_data, edge, depth_location)
        except Exception:
            return 0.0
        try:
            return max(WORLD_MIN_OPERATION_RADIUS, (edge_world - center_world).length)
        except Exception:
            return 0.0

    def _active_native_brush_radius_setting(self, context, *, depth_location=None):
        size_kind, native_size = self._active_native_brush_size_state(context)
        try:
            native_size = float(native_size)
        except Exception:
            native_size = 0.0
        if native_size <= 0.0:
            return size_kind, 0.0, native_size
        depth_location = depth_location or self._brush_screen_depth_location()
        if size_kind == "WORLD_RADIUS":
            return size_kind, max(WORLD_MIN_OPERATION_RADIUS, native_size), native_size
        if size_kind == "SCREEN_RADIUS":
            return (
                size_kind,
                self._screen_radius_to_world_radius(
                    context,
                    native_size,
                    depth_location=depth_location,
                ),
                native_size,
            )

        return size_kind, 0.0, native_size

    def _stale_native_window_manager_radius_update_info(self, context, next_radius_setting):
        if not (
            self._density_uses_native_ui()
            and self.tool_id == WORLD_TOOL_DENSITY
            and getattr(self, "_native_density_session_active", False)
            and not getattr(self, "adjust_mode", "")
        ):
            return None
        try:
            old_setting = float(getattr(self, "brush_radius_setting", 0.0) or 0.0)
            next_radius_setting = float(next_radius_setting)
        except Exception:
            return None
        if next_radius_setting >= old_setting - 0.0001:
            return None

        size_kind, live_setting, native_size = self._active_native_brush_radius_setting(context)
        if live_setting <= 0.0:
            return None
        old_margin = max(0.0001, abs(old_setting) * 0.002)
        next_margin = max(0.0001, abs(next_radius_setting) * 0.002)
        if live_setting < old_setting - old_margin:
            return None
        if live_setting <= next_radius_setting + next_margin:
            return None
        return {
            "size_kind": size_kind,
            "native_size": native_size,
            "live_setting": live_setting,
            "old_setting": old_setting,
            "next_radius_setting": next_radius_setting,
        }

    def _sync_brush_radius_from_native_world_radius(self, context, world_radius, *, depth_location=None):
        try:
            world_radius = float(world_radius)
        except Exception:
            world_radius = 0.0
        if world_radius <= 0.0:
            return False
        old_setting = getattr(self, "brush_radius_setting", 0.0)
        old_radius = getattr(self, "brush_radius", 0.0)
        self.brush_radius_setting = max(WORLD_MIN_OPERATION_RADIUS, world_radius)
        self._sync_effective_brush_radius(
            context,
            depth_location=depth_location or getattr(self, "_native_density_adjust_depth_location", None) or self._adjust_depth_location,
            mouse_coord=self.hover_mouse_region,
        )
        _store_operator_brush_radius(self, context)
        self._sync_brush_controls(context, force=True)
        shared.secret_paint_brush_size_trace_log(
            "world.sync_radius_from_native_world_radius",
            context,
            self,
            native_world_radius=world_radius,
            old_setting=old_setting,
            old_radius=old_radius,
            new_setting=self.brush_radius_setting,
            new_radius=self.brush_radius,
        )
        return True

    def _sync_brush_radius_from_active_native_brush(
        self,
        context,
        *,
        depth_location=None,
        prefer_screen_size_if_larger=False,
    ):
        size_kind, native_size = self._active_native_brush_size_state(context)
        shared.secret_paint_brush_size_trace_log(
            "world.sync_radius_from_active_native_brush",
            context,
            self,
            size_kind=size_kind,
            native_size=native_size,
            prefer_screen_size_if_larger=False,
        )
        if size_kind == "WORLD_RADIUS":
            return self._sync_brush_radius_from_native_world_radius(
                context,
                native_size,
                depth_location=depth_location,
            )
        return False

    def _sync_pending_native_size_before_brush_write(self, context):
        if getattr(self, "_native_density_pending_adjust_mode", "") != "SIZE":
            return False
        shared.secret_paint_brush_size_trace_log(
            "world.pending_size.before_brush_write.enter",
            context,
            self,
        )
        try:
            synced = bool(
                self._sync_brush_radius_from_active_native_brush(
                    context,
                    depth_location=(
                        getattr(self, "_native_density_adjust_depth_location", None)
                        or getattr(self, "_adjust_depth_location", None)
                    ),
                    prefer_screen_size_if_larger=False,
                )
            )
            shared.secret_paint_brush_size_trace_log(
                "world.pending_size.before_brush_write.exit",
                context,
                self,
                synced=synced,
            )
            return synced
        except Exception:
            shared.secret_paint_brush_size_trace_log(
                "world.pending_size.before_brush_write.exception",
                context,
                self,
            )
            return False

    def _handle_native_brush_ui_size_event(self, context, event):
        if not self._density_uses_native_ui() or getattr(self, "adjust_mode", ""):
            self._native_brush_ui_size_interaction_active = False
            self._native_brush_ui_size_interaction_start_state = None
            self._native_brush_ui_size_interaction_changed = False
            return False

        event_type = getattr(event, "type", "")
        if _is_primary_paint_active_event(event):
            self._native_brush_ui_size_interaction_active = True
            self._native_brush_ui_size_interaction_start_state = self._active_native_brush_size_state(context)
            self._native_brush_ui_size_interaction_changed = False
            return False
        elif event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            if not getattr(self, "_native_brush_ui_size_interaction_active", False):
                return False
            current_state = self._active_native_brush_size_state(context)
            start_state = getattr(self, "_native_brush_ui_size_interaction_start_state", None)
            if self._native_brush_size_states_differ(start_state, current_state):
                self._native_brush_ui_size_interaction_changed = True
            return False
        elif _is_primary_paint_end_event(event):
            if not getattr(self, "_native_brush_ui_size_interaction_active", False):
                return False
            current_state = self._active_native_brush_size_state(context)
            start_state = getattr(self, "_native_brush_ui_size_interaction_start_state", None)
            changed = (
                bool(getattr(self, "_native_brush_ui_size_interaction_changed", False))
                or self._native_brush_size_states_differ(start_state, current_state)
            )
            self._native_brush_ui_size_interaction_active = False
            self._native_brush_ui_size_interaction_start_state = None
            self._native_brush_ui_size_interaction_changed = False
            if not changed:
                return False
        else:
            return False

        try:
            shared.secret_paint_brush_size_trace_log(
                "world.native_brush_ui_size_event.schedule",
                context,
                self,
                event_type=event_type,
                event_value=getattr(event, "value", ""),
            )
            self._schedule_native_density_adjust_result_sync(
                "SIZE",
                first_interval=0.04,
                max_attempts=8,
            )
            return True
        except Exception:
            return False

    def _native_brush_size_states_differ(self, left_state, right_state):
        if not left_state or not right_state:
            return False
        try:
            left_kind, left_value = left_state
            right_kind, right_value = right_state
            tolerance = 0.0001 if left_kind == "WORLD_RADIUS" else 0.5
            return left_kind != right_kind or abs(float(left_value) - float(right_value)) > tolerance
        except Exception:
            return False

    def _sync_live_native_adjust_controls(self, context, adjust_mode=None):
        adjust_mode = adjust_mode or self.adjust_mode
        changed = False
        if adjust_mode == "SIZE":
            return False
        elif adjust_mode == "STRENGTH":
            if getattr(self, "_native_density_adjust_finalizing", False):
                return False
            native_spacing = self._read_density_spacing_from_active_curves_brush(context)
            if native_spacing is not None:
                next_density_spacing = _density_spacing_value(native_spacing, fallback=self.density_spacing)
                if abs(next_density_spacing - self.density_spacing) >= 0.0001:
                    self.density_spacing = next_density_spacing
                    self._native_density_adjust_manual_spacing = self.density_spacing
                    changed = True
            elif getattr(self, "_native_density_adjust_manual_spacing", None) is not None:
                changed = True

            if changed:
                self._sync_brush_controls(context, force=True)

        if changed:
            _tag_view3d_tool_ui_regions(
                context,
                area_pointer=getattr(self, "_invoke_area_pointer", 0),
            )
        return changed

    def _cache_native_density_adjust_spacing_from_event(self, context, event=None):
        if self.adjust_mode != "STRENGTH" or getattr(self, "_native_density_adjust_finalizing", False):
            return False
        if (
            getattr(self, "_native_density_adjust_passthrough", False) and
            WORLD_NATIVE_DENSITY_MODAL_ADJUST_ENABLED
        ):
            return False

        changed = False
        if event is not None and hasattr(event, "mouse_region_x"):
            try:
                changed = bool(self._update_adjust(context, event))
            except Exception:
                changed = False
            self._native_density_adjust_manual_spacing = _density_spacing_value(self.density_spacing)
            try:
                self._sync_brush_controls(context, force=True)
            except Exception:
                pass
            _tag_view3d_tool_ui_regions(
                context,
                area_pointer=getattr(self, "_invoke_area_pointer", 0),
            )
            return changed

        try:
            return bool(self._sync_live_native_adjust_controls(context, "STRENGTH"))
        except Exception:
            return False

    def _sync_native_density_adjust_result(self, context, adjust_mode):
        shared.secret_paint_brush_size_trace_log(
            "world.sync_native_adjust_result.enter",
            context,
            self,
            adjust_mode=adjust_mode,
        )
        if adjust_mode == "SIZE":
            depth_location = (
                getattr(self, "_native_density_adjust_depth_location", None)
                or self._adjust_depth_location
            )
            size_synced = self._sync_brush_radius_from_active_native_brush(
                context,
                depth_location=depth_location,
                prefer_screen_size_if_larger=False,
            )
            if not size_synced:
                brush = self._native_density_brush(context)
                try:
                    native_world_diameter = float(getattr(brush, "unprojected_size", 0.0)) if brush is not None else 0.0
                except Exception:
                    native_world_diameter = 0.0
                if native_world_diameter > 0.0:
                    size_synced = self._sync_brush_radius_from_native_world_radius(
                        context,
                        native_world_diameter * 0.5,
                        depth_location=depth_location,
                    )
            synced = bool(size_synced)
        elif adjust_mode == "STRENGTH":
            synced = False
            manual_spacing = getattr(self, "_native_density_adjust_manual_spacing", None)
            if manual_spacing is not None:
                self.density_spacing = _density_spacing_value(manual_spacing, fallback=self.density_spacing)
                self._native_density_adjust_manual_spacing = self.density_spacing
                self._apply_density_spacing_to_native_brush(context)
                synced = True
            else:
                native_spacing = self._read_density_spacing_from_active_curves_brush(context)
                if native_spacing is None:
                    native_spacing = self._read_density_spacing_from_native_brush(context)
                if native_spacing is not None:
                    self.density_spacing = _density_spacing_value(native_spacing, fallback=self.density_spacing)
                    self._native_density_adjust_manual_spacing = self.density_spacing
                    self._apply_density_spacing_to_native_brush(context)
                    synced = True
        else:
            synced = bool(self._sync_density_spacing_from_native_brush(context))
        self._sync_brush_controls(context, force=True)
        _tag_view3d_tool_ui_regions(
            context,
            area_pointer=getattr(self, "_invoke_area_pointer", 0),
        )
        _tag_redraw_view3d_areas(context)
        shared.secret_paint_brush_size_trace_log(
            "world.sync_native_adjust_result.exit",
            context,
            self,
            adjust_mode=adjust_mode,
            synced=synced,
        )
        return synced

    def _flush_pending_native_density_adjust_result(self, context):
        adjust_mode = getattr(self, "_native_density_pending_adjust_mode", "")
        if not adjust_mode:
            return False
        self._native_density_adjust_sync_token += 1
        try:
            self._sync_native_density_adjust_result(context, adjust_mode)
        except Exception:
            return False
        self._native_density_pending_adjust_mode = ""
        self._native_density_adjust_depth_location = None
        self._native_density_adjust_manual_spacing = None
        return True

    def _commit_active_native_density_adjust_result(self, context):
        adjust_mode = self.adjust_mode if getattr(self, "_native_density_adjust_passthrough", False) else ""
        shared.secret_paint_brush_size_trace_log(
            "world.commit_active_native_adjust.enter",
            context,
            self,
            adjust_mode=adjust_mode,
        )
        if not adjust_mode:
            flushed = self._flush_pending_native_density_adjust_result(context)
            shared.secret_paint_brush_size_trace_log(
                "world.commit_active_native_adjust.flushed_pending",
                context,
                self,
                flushed=flushed,
            )
            return flushed

        self._native_density_adjust_sync_token += 1
        try:
            synced = self._sync_native_density_adjust_result(context, adjust_mode)
        except Exception:
            shared.secret_paint_brush_size_trace_log(
                "world.commit_active_native_adjust.sync_exception",
                context,
                self,
                adjust_mode=adjust_mode,
            )
            return False

        self.adjust_mode = ""
        self.adjust_origin_x = None
        self._adjust_depth_location = None
        self._native_density_adjust_passthrough = False
        self._native_density_adjust_confirm_pending = False
        self._native_density_adjust_auto_confirm_until = 0.0
        self._native_density_adjust_release_watch_token += 1
        self._native_density_adjust_release_watch_running = False
        self._native_density_adjust_release_watch_saw_shortcut_down = False
        self._native_density_adjust_release_watch_started = 0.0
        self._native_density_adjust_finalizing = False
        self._native_density_adjust_waiting_for_alt_release = False
        self._native_density_adjust_native_release_confirm = False
        self._native_density_pending_adjust_mode = ""
        self._native_density_adjust_depth_location = None
        self._native_density_adjust_manual_spacing = None
        self._stop_live_native_adjust_control_sync()
        if context is not None and self._density_uses_native_ui() and not self.stroke_active:
            self._restore_native_density_brush_overlay()
            self._restore_native_density_brush_visibility(context)
            self._force_native_brush_visibility(context)
            self._remove_draw_handlers()
            if context.area:
                context.area.tag_redraw()
        shared.secret_paint_brush_size_trace_log(
            "world.commit_active_native_adjust.exit",
            context,
            self,
            adjust_mode=adjust_mode,
            synced=synced,
        )
        return True

    def _commit_pending_native_size_adjust_confirm(self, context):
        shared.secret_paint_brush_size_trace_log(
            "world.commit_pending_size_confirm.enter",
            context,
            self,
        )
        if not (
            getattr(self, "adjust_mode", "") == "SIZE"
            and getattr(self, "_native_density_adjust_passthrough", False)
            and getattr(self, "_native_density_adjust_confirm_pending", False)
        ):
            shared.secret_paint_brush_size_trace_log(
                "world.commit_pending_size_confirm.skip",
                context,
                self,
            )
            return False
        try:
            committed = bool(self._commit_active_native_density_adjust_result(context))
            shared.secret_paint_brush_size_trace_log(
                "world.commit_pending_size_confirm.exit",
                context,
                self,
                committed=committed,
            )
            return committed
        except Exception:
            shared.secret_paint_brush_size_trace_log(
                "world.commit_pending_size_confirm.exception",
                context,
                self,
            )
            return False

    def _stop_live_native_adjust_control_sync(self):
        self._native_density_adjust_live_sync_token += 1
        self._native_density_adjust_live_sync_running = False

    def _start_live_native_adjust_control_sync(self, context, adjust_mode):
        if not WORLD_NATIVE_ADJUST_LIVE_SLIDER_SYNC_ENABLED:
            self._native_density_adjust_live_sync_running = False
            return False
        self._native_density_adjust_live_sync_token += 1
        sync_token = self._native_density_adjust_live_sync_token
        self._native_density_adjust_live_sync_running = True

        def _sync_live_adjust_controls():
            operator = _world_operator()
            if operator is None:
                return None
            if sync_token != getattr(operator, "_native_density_adjust_live_sync_token", 0):
                return None
            if not (
                getattr(operator, "adjust_mode", "") == adjust_mode
                and getattr(operator, "_native_density_adjust_passthrough", False)
            ):
                operator._native_density_adjust_live_sync_running = False
                return None
            if adjust_mode == "STRENGTH" and getattr(operator, "_native_density_adjust_finalizing", False):
                operator._native_density_adjust_live_sync_running = False
                return None
            try:
                operator._sync_live_native_adjust_controls(bpy.context, adjust_mode)
            except Exception:
                pass
            return WORLD_BRUSH_CONTROL_SYNC_INTERVAL

        try:
            bpy.app.timers.register(_sync_live_adjust_controls, first_interval=0.0)
        except Exception:
            self._native_density_adjust_live_sync_running = False
            try:
                self._sync_live_native_adjust_controls(context, adjust_mode)
            except Exception:
                pass
            return False
        return True

    def _schedule_native_density_adjust_result_sync(self, adjust_mode, *, first_interval=0.05, max_attempts=2):
        self._native_density_pending_adjust_mode = adjust_mode or ""
        self._native_density_adjust_sync_token += 1
        sync_token = self._native_density_adjust_sync_token
        attempts = {"count": 0}
        max_attempts = max(1, int(max_attempts))
        first_interval = max(0.0, float(first_interval))
        shared.secret_paint_brush_size_trace_log(
            "world.schedule_native_adjust_sync",
            bpy.context,
            self,
            adjust_mode=adjust_mode,
            first_interval=first_interval,
            max_attempts=max_attempts,
            token=sync_token,
        )

        def _sync_result():
            operator = _world_operator()
            if operator is None:
                return None
            if sync_token != getattr(operator, "_native_density_adjust_sync_token", 0):
                return None
            attempts["count"] += 1
            try:
                shared.secret_paint_brush_size_trace_log(
                    "world.schedule_native_adjust_sync.tick",
                    bpy.context,
                    operator,
                    adjust_mode=adjust_mode,
                    attempt=attempts["count"],
                    max_attempts=max_attempts,
                    token=sync_token,
                )
                synced = bool(operator._sync_native_density_adjust_result(bpy.context, adjust_mode))
                shared.secret_paint_brush_size_trace_log(
                    "world.schedule_native_adjust_sync.tick_result",
                    bpy.context,
                    operator,
                    adjust_mode=adjust_mode,
                    attempt=attempts["count"],
                    synced=synced,
                )
                if attempts["count"] >= max_attempts:
                    if adjust_mode != "SIZE" or synced:
                        operator._refresh_brush_cursor_after_view_reentry(
                            bpy.context,
                            schedule=True,
                            force_rebuild=bool(getattr(operator, "_brush_cursor_focus_lost", False)),
                        )
                        operator._native_density_pending_adjust_mode = ""
                        operator._native_density_adjust_depth_location = None
                        operator._native_density_adjust_manual_spacing = None
            except Exception:
                pass
            return 0.05 if attempts["count"] < max_attempts else None

        try:
            bpy.app.timers.register(_sync_result, first_interval=first_interval)
        except Exception:
            _sync_result()

    def _adjust_origin_from_event(self, event):
        if event is not None and hasattr(event, "mouse_region_x"):
            return event.mouse_region_x
        return None

    def _is_adjust_confirm_release_event(self, context, event):
        if not self.adjust_mode or getattr(event, "value", "") != 'RELEASE':
            return False
        if not bool(getattr(self, "_native_density_adjust_confirm_on_release", False)):
            return False
        return _event_matches_current_adjust_shortcut(
            context,
            event,
            self.adjust_mode,
            ignore_value=True,
        )

    def _is_brush_strength_adjust_active(self):
        return (
            self.adjust_mode == "STRENGTH"
            and self._tool_uses_brush_strength_adjust()
            and not getattr(self, "_native_density_adjust_passthrough", False)
        )

    def _is_brush_strength_adjust_shortcut_release_event(self, context, event):
        if not self._is_brush_strength_adjust_active() or getattr(event, "value", "") != 'RELEASE':
            return False
        if _event_matches_current_adjust_shortcut(context, event, "STRENGTH", ignore_value=True):
            return True
        event_type = getattr(event, "type", "")
        for spec in _adjust_shortcut_key_specs(context, "STRENGTH"):
            if event_type == spec.get("key_type", ""):
                return True
            modifier_name = WORLD_MODIFIER_KEY_TYPES.get(event_type)
            if modifier_name and modifier_name in (spec.get("modifiers", ()) or ()):
                return True
        return False

    def _handle_brush_strength_adjust_confirm_event(self, context, event):
        if not self._is_brush_strength_adjust_active():
            return False
        event_type = getattr(event, "type", "")
        event_value = getattr(event, "value", "")
        if (
            bool(getattr(self, "_native_density_adjust_confirm_on_release", False))
            and self._is_brush_strength_adjust_shortcut_release_event(context, event)
        ):
            self._confirm_adjust_from_event(context, event)
            return True
        if event_type in {'LEFTMOUSE', 'ACTIONMOUSE', 'SELECTMOUSE'} and event_value in {'PRESS', 'CLICK'}:
            self._confirm_adjust_from_event(context, event)
            return True
        return False

    def _schedule_native_adjust_finish(self, delay=0.08):
        def _finish_adjust():
            operator = _world_operator()
            if (
                operator is not None and
                getattr(operator, "adjust_mode", "") and
                getattr(operator, "_native_density_adjust_confirm_pending", False)
            ):
                try:
                    operator._end_adjust(bpy.context)
                except Exception:
                    pass
            return None

        try:
            bpy.app.timers.register(_finish_adjust, first_interval=delay)
        except Exception:
            _finish_adjust()
        return True

    def _read_density_spacing_from_native_brush(self, context):
        if self.tool_id != WORLD_TOOL_DENSITY or self._native_density_stroke_erase:
            return None
        brush = self._native_density_brush(context)
        settings = getattr(brush, "curves_sculpt_settings", None) if brush is not None else None
        if settings is None:
            return None
        try:
            return _density_spacing_value(
                getattr(settings, "minimum_distance", self.density_spacing),
                fallback=self.density_spacing,
            )
        except Exception:
            return None

    def _read_density_spacing_from_active_curves_brush(self, context):
        if self.tool_id != WORLD_TOOL_DENSITY or self._native_density_stroke_erase:
            return None
        brush_container = _tool_settings_brush_container(context)
        brush = getattr(brush_container, "brush", None) if brush_container is not None else None
        if not shared.secret_paint_is_curves_brush_type(brush, "DENSITY"):
            return None
        settings = getattr(brush, "curves_sculpt_settings", None)
        if settings is None:
            return None
        try:
            return _density_spacing_value(
                getattr(settings, "minimum_distance", self.density_spacing),
                fallback=self.density_spacing,
            )
        except Exception:
            return None

    def _native_density_alt_f_key_state(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            alt_down = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
            f_down = bool(user32.GetAsyncKeyState(0x46) & 0x8000)
            return alt_down, f_down
        except Exception:
            return None

    def _native_density_adjust_shortcut_key_state(self, context, adjust_mode):
        saw_known_state = False
        any_key_down = False
        any_modifier_down = False
        any_chord_down = False
        key_types = []
        for spec in _adjust_shortcut_key_specs(context, adjust_mode):
            key_type = spec.get("key_type", "")
            if key_type in {"", "NONE"}:
                continue
            key_down = _windows_key_down_for_event_type(key_type)
            modifier_states = [
                _windows_modifier_down(modifier_name)
                for modifier_name in spec.get("modifiers", ()) or ()
            ]
            if key_down is None or any(state is None for state in modifier_states):
                continue
            saw_known_state = True
            key_down = bool(key_down)
            modifiers_down = any(bool(state) for state in modifier_states)
            modifiers_match = all(bool(state) for state in modifier_states)
            any_key_down = any_key_down or key_down
            any_modifier_down = any_modifier_down or modifiers_down
            any_chord_down = any_chord_down or (key_down and modifiers_match)
            key_types.append(key_type)
        if not saw_known_state:
            return None
        return {
            "key_down": any_key_down,
            "modifier_down": any_modifier_down,
            "shortcut_down": any_key_down or any_modifier_down,
            "chord_down": any_chord_down,
            "key_types": tuple(key_types),
        }

    def _send_native_adjust_confirm_event(self):
        shared.secret_paint_brush_size_trace_log(
            "world.send_native_confirm_mouse.enter",
            bpy.context,
            self,
        )
        try:
            import ctypes
            from ctypes import wintypes
            self._native_density_adjust_auto_confirm_until = time.perf_counter() + 0.5
            user32 = ctypes.windll.user32
            input_mouse = 0
            mouseeventf_leftdown = 0x0002
            mouseeventf_leftup = 0x0004

            ulong_ptr = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

            class _MouseInput(ctypes.Structure):
                _fields_ = (
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ulong_ptr),
                )

            class _InputUnion(ctypes.Union):
                _fields_ = (("mi", _MouseInput),)

            class _Input(ctypes.Structure):
                _fields_ = (
                    ("type", wintypes.DWORD),
                    ("union", _InputUnion),
                )

            events = (_Input * 2)()
            events[0].type = input_mouse
            events[0].union.mi = _MouseInput(0, 0, 0, mouseeventf_leftdown, 0, 0)
            events[1].type = input_mouse
            events[1].union.mi = _MouseInput(0, 0, 0, mouseeventf_leftup, 0, 0)
            try:
                user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int)
                user32.SendInput.restype = wintypes.UINT
                if user32.SendInput(2, events, ctypes.sizeof(_Input)) == 2:
                    shared.secret_paint_brush_size_trace_log(
                        "world.send_native_confirm_mouse.sendinput_success",
                        bpy.context,
                        self,
                    )
                    return True
            except Exception:
                pass
            user32.mouse_event(mouseeventf_leftdown, 0, 0, 0, 0)
            user32.mouse_event(mouseeventf_leftup, 0, 0, 0, 0)
            shared.secret_paint_brush_size_trace_log(
                "world.send_native_confirm_mouse.mouse_event_success",
                bpy.context,
                self,
            )
            return True
        except Exception:
            shared.secret_paint_brush_size_trace_log(
                "world.send_native_confirm_mouse.exception",
                bpy.context,
                self,
            )
            return False

    def _finalize_native_density_adjust_release(self, context, *, wait_for_alt_release=False):
        if not (
            self.adjust_mode == "STRENGTH"
            and getattr(self, "_native_density_adjust_passthrough", False)
        ):
            return False
        if (
            getattr(self, "_native_density_adjust_finalizing", False)
            and getattr(self, "_native_density_adjust_confirm_pending", False)
        ):
            return True
        native_release_confirm = bool(
            getattr(self, "_native_density_adjust_native_release_confirm", False)
        )

        self._native_density_adjust_waiting_for_alt_release = False
        self._native_density_adjust_confirm_pending = True
        self._native_density_adjust_finalizing = True
        self._native_density_adjust_manual_spacing = None
        self._stop_live_native_adjust_control_sync()
        if not native_release_confirm and self._request_native_density_adjust_confirm(delay=0.03):
            return True
        if not native_release_confirm:
            sent = False
            try:
                sent = bool(self._send_native_adjust_confirm_event())
            except Exception:
                pass
            if not sent:
                try:
                    self._send_native_adjust_confirm_key_event()
                except Exception:
                    pass
        try:
            self._schedule_native_density_adjust_result_sync(
                "STRENGTH",
                first_interval=0.03,
                max_attempts=4,
            )
        except Exception:
            pass
        try:
            self._schedule_native_adjust_finish(delay=0.16)
        except Exception:
            pass
        return True

    def _request_native_density_adjust_confirm(self, delay=0.03):
        if not (
            self.adjust_mode == "STRENGTH"
            and getattr(self, "_native_density_adjust_passthrough", False)
        ):
            return False

        self._native_density_adjust_confirm_pending = True
        confirm_token = getattr(self, "_native_density_adjust_release_watch_token", 0)
        first_interval = max(0.0, float(delay))

        def _confirm_density_adjust():
            operator = _world_operator()
            if operator is None:
                return None
            if confirm_token != getattr(operator, "_native_density_adjust_release_watch_token", 0):
                return None
            if not (
                getattr(operator, "adjust_mode", "") == "STRENGTH"
                and getattr(operator, "_native_density_adjust_passthrough", False)
            ):
                return None
            key_state = operator._native_density_adjust_shortcut_key_state(
                bpy.context,
                "STRENGTH",
            )
            if key_state is not None and key_state.get("shortcut_down", False):
                operator._native_density_adjust_waiting_for_alt_release = True
                return 0.02
            if key_state is None:
                fallback_key_state = operator._native_density_alt_f_key_state()
                if fallback_key_state is not None:
                    alt_down, f_down = fallback_key_state
                    if alt_down or f_down:
                        operator._native_density_adjust_waiting_for_alt_release = True
                        return 0.02
            operator._native_density_adjust_waiting_for_alt_release = False
            sent = False
            try:
                sent = bool(operator._send_native_adjust_confirm_event())
            except Exception:
                pass
            if not sent:
                try:
                    operator._send_native_adjust_confirm_key_event()
                except Exception:
                    pass
            try:
                operator._schedule_native_density_adjust_result_sync(
                    "STRENGTH",
                    first_interval=0.03,
                    max_attempts=4,
                )
            except Exception:
                pass
            try:
                operator._schedule_native_adjust_finish(delay=0.16)
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(_confirm_density_adjust, first_interval=first_interval)
        except Exception:
            _confirm_density_adjust()
        return True

    def _request_native_size_adjust_confirm(self, delay=0.01, *, reason=""):
        shared.secret_paint_brush_size_trace_log(
            "world.request_size_confirm.enter",
            context=bpy.context,
            operator=self,
            delay=delay,
            reason=reason,
        )
        if not (
            self.adjust_mode == "SIZE"
            and getattr(self, "_native_density_adjust_passthrough", False)
        ):
            shared.secret_paint_brush_size_trace_log(
                "world.request_size_confirm.skip_not_active",
                bpy.context,
                self,
                delay=delay,
                reason=reason,
            )
            return False
        if getattr(self, "_native_density_adjust_confirm_pending", False):
            shared.secret_paint_brush_size_trace_log(
                "world.request_size_confirm.skip_already_pending",
                bpy.context,
                self,
                delay=delay,
                reason=reason,
            )
            return True

        self._native_density_adjust_confirm_pending = True
        self._stop_live_native_adjust_control_sync()
        self._native_density_adjust_sync_token += 1
        self._native_size_adjust_commit_token += 1
        sync_token = self._native_density_adjust_sync_token
        commit_token = self._native_size_adjust_commit_token
        attempts = {"count": 0}

        def _confirm_size_adjust():
            operator = _world_operator()
            shared.secret_paint_brush_size_trace_log(
                "world.request_size_confirm.tick",
                bpy.context,
                operator,
                delay=delay,
                reason=reason,
                sync_token=sync_token,
                commit_token=commit_token,
                attempt=attempts["count"] + 1,
            )
            if not (
                operator is not None
                and getattr(operator, "adjust_mode", "") == "SIZE"
                and getattr(operator, "_native_density_adjust_passthrough", False)
            ):
                return None
            if (
                sync_token != getattr(operator, "_native_density_adjust_sync_token", 0)
                or commit_token != getattr(operator, "_native_size_adjust_commit_token", 0)
            ):
                return None
            attempts["count"] += 1
            try:
                synced = bool(
                    operator._sync_native_density_adjust_result(
                        bpy.context,
                        "SIZE",
                    )
                )
            except Exception:
                synced = False
            if not synced and attempts["count"] < 4:
                shared.secret_paint_brush_size_trace_log(
                    "world.request_size_confirm.retry",
                    bpy.context,
                    operator,
                    delay=delay,
                    reason=reason,
                    attempt=attempts["count"],
                )
                return 0.02
            try:
                shared.secret_paint_brush_size_trace_log(
                    "world.native_size_adjust.confirmed",
                    bpy.context,
                    operator,
                    reason=reason,
                    attempts=attempts["count"],
                    synced=synced,
                )
            except Exception:
                pass
            operator._native_density_pending_adjust_mode = ""
            operator._native_density_adjust_depth_location = None
            operator._native_density_adjust_manual_spacing = None
            operator._native_density_adjust_confirm_pending = False
            operator._native_density_adjust_passthrough = False
            try:
                operator._refresh_brush_cursor_after_view_reentry(
                    bpy.context,
                    schedule=True,
                    force_rebuild=bool(getattr(operator, "_brush_cursor_focus_lost", False)),
                )
            except Exception:
                pass
            try:
                operator._end_adjust(bpy.context)
            except Exception:
                pass
            return None

        try:
            bpy.app.timers.register(_confirm_size_adjust, first_interval=max(0.0, float(delay)))
        except Exception:
            _confirm_size_adjust()
        shared.secret_paint_brush_size_trace_log(
            "world.request_size_confirm.scheduled",
            bpy.context,
            self,
            delay=delay,
            reason=reason,
            sync_token=sync_token,
            commit_token=commit_token,
        )
        return True

    def _start_native_density_adjust_release_watch(self, context, event=None):
        adjust_mode = self.adjust_mode
        if adjust_mode not in {"SIZE", "STRENGTH"}:
            return False
        started_from_shortcut = False
        if event is not None:
            if not _event_matches_current_adjust_shortcut(
                context,
                event,
                adjust_mode,
                ignore_value=True,
            ):
                return False
            started_from_shortcut = True

        self._native_density_adjust_release_watch_token += 1
        watch_token = self._native_density_adjust_release_watch_token
        self._native_density_adjust_release_watch_running = True
        self._native_density_adjust_release_watch_saw_shortcut_down = started_from_shortcut
        self._native_density_adjust_release_watch_started = time.perf_counter()
        self._native_density_adjust_finalizing = False
        self._native_density_adjust_waiting_for_alt_release = False
        shared.secret_paint_brush_size_trace_log(
            "world.release_watch.start",
            context,
            self,
            adjust_mode=adjust_mode,
            event_type=getattr(event, "type", "") if event is not None else "",
            event_value=getattr(event, "value", "") if event is not None else "",
            event_alt=bool(getattr(event, "alt", False)) if event is not None else False,
            watch_token=watch_token,
            saw_shortcut_down=self._native_density_adjust_release_watch_saw_shortcut_down,
        )

        def _watch_release():
            operator = _world_operator()
            if operator is None:
                return None
            if watch_token != getattr(operator, "_native_density_adjust_release_watch_token", 0):
                return None
            current_adjust_mode = getattr(operator, "adjust_mode", "")
            if not (current_adjust_mode == adjust_mode and getattr(operator, "_native_density_adjust_passthrough", False)):
                operator._native_density_adjust_release_watch_running = False
                return None

            key_state = operator._native_density_adjust_shortcut_key_state(
                bpy.context,
                adjust_mode,
            )
            if key_state is None:
                if (
                    time.perf_counter()
                    - float(getattr(operator, "_native_density_adjust_release_watch_started", 0.0) or 0.0)
                ) > 30.0:
                    operator._native_density_adjust_release_watch_running = False
                    return None
                return 0.05
            shortcut_down = bool(key_state.get("shortcut_down", False))
            shared.secret_paint_brush_size_trace_log(
                "world.release_watch.tick",
                bpy.context,
                operator,
                adjust_mode=adjust_mode,
                shortcut_down=shortcut_down,
                key_down=bool(key_state.get("key_down", False)),
                modifier_down=bool(key_state.get("modifier_down", False)),
                key_types=",".join(key_state.get("key_types", ()) or ()),
                saw_shortcut_down=getattr(operator, "_native_density_adjust_release_watch_saw_shortcut_down", False),
                watch_token=watch_token,
            )
            if shortcut_down:
                operator._native_density_adjust_release_watch_saw_shortcut_down = True
                return 0.02
            if (
                not shortcut_down
                and getattr(operator, "_native_density_adjust_release_watch_saw_shortcut_down", False)
            ):
                elapsed = (
                    time.perf_counter()
                    - float(getattr(operator, "_native_density_adjust_release_watch_started", 0.0) or 0.0)
                )
                if adjust_mode != "SIZE" and elapsed < 0.08:
                    return 0.02
                operator._native_density_adjust_release_watch_running = False
                shared.secret_paint_brush_size_trace_log(
                    "world.release_watch.shortcut_released",
                    bpy.context,
                    operator,
                    adjust_mode=adjust_mode,
                    elapsed=elapsed,
                    shortcut_down=shortcut_down,
                    key_down=bool(key_state.get("key_down", False)),
                    modifier_down=bool(key_state.get("modifier_down", False)),
                    watch_token=watch_token,
                )
                if adjust_mode == "STRENGTH":
                    operator._finalize_native_density_adjust_release(
                        bpy.context,
                        wait_for_alt_release=bool(key_state.get("modifier_down", False)),
                    )
                else:
                    operator._request_native_size_adjust_confirm(
                        delay=0.0,
                        reason="release_confirm_watch",
                    )
                return None
            return 0.02

        try:
            bpy.app.timers.register(_watch_release, first_interval=0.02)
        except Exception:
            return False
        return True

    def _apply_density_spacing_to_native_brush(self, context):
        if self.tool_id != WORLD_TOOL_DENSITY or self._native_density_stroke_erase:
            return False
        spacing = _density_spacing_value(self.density_spacing)
        self.density_spacing = spacing
        brush = self._native_density_brush(context)
        active_system = self._current_system()
        try:
            preset_brush = shared.secret_paint_ensure_sp_density_brush_asset(
                context,
                active_system,
                configure=False,
                override_settings=False,
                size=None,
            )
        except Exception:
            preset_brush = None
        brush_container = _tool_settings_brush_container(context)
        active_brush = getattr(brush_container, "brush", None) if brush_container is not None else None

        return self._apply_density_spacing_to_brush_candidates(
            context,
            active_system,
            preset_brush,
            brush,
            active_brush,
        )

    def _begin_native_adjust(self, context, adjust_mode, event=None, *, confirm_on_release=False):
        shared.secret_paint_brush_size_trace_log(
            "world.begin_native_adjust.enter",
            context,
            self,
            adjust_mode=adjust_mode,
            confirm_on_release=confirm_on_release,
            event_type=getattr(event, "type", "") if event is not None else "",
            event_value=getattr(event, "value", "") if event is not None else "",
            event_alt=bool(getattr(event, "alt", False)) if event is not None else False,
        )
        self._commit_active_native_density_adjust_result(context)
        if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)

        if self.hover_target is None:
            current_system_target = _target_info_from_system(
                context,
                self._current_system(),
                allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
            )
            if current_system_target is not None:
                self._activate_hover_target(context, current_system_target)

        if (
            self.tool_id == WORLD_TOOL_DENSITY and
            adjust_mode == "STRENGTH" and
            (
                bool(getattr(self, "_native_density_stroke_erase", False)) or
                getattr(self, "_native_tool_override_brush_type", "") == "DELETE" or
                getattr(self, "_requested_native_tool_brush_type", "") == "DELETE" or
                bool(getattr(self, "_native_curves_brush_passthrough", False))
            )
        ):
            self._restore_density_native_brush_after_delete(context)

        previous_preserve_size = bool(getattr(self, "_preserve_native_size_for_adjust", False))
        if adjust_mode == "SIZE":
            self._preserve_native_size_for_adjust = True
        try:
            if not self._begin_native_density_session(context, create_system=False):
                return False
        finally:
            self._preserve_native_size_for_adjust = previous_preserve_size

        self._remove_draw_handlers()
        self._restore_native_density_brush_overlay()
        self._restore_native_density_brush_visibility(context)
        self._force_native_brush_visibility(context)
        self.adjust_mode = adjust_mode
        self.adjust_origin_x = self._adjust_origin_from_event(event)
        self._adjust_depth_location = self._brush_screen_depth_location()
        self._native_density_adjust_depth_location = self._adjust_depth_location
        self._last_brush_control_sync_time = 0.0
        self.adjust_base_value = self.brush_radius_setting if adjust_mode == "SIZE" else self.density_spacing
        self._native_density_adjust_passthrough = True
        self._native_density_adjust_manual_spacing = None
        self._native_density_adjust_native_release_confirm = False
        self._native_density_adjust_confirm_on_release = bool(confirm_on_release)
        if adjust_mode == "SIZE":
            invoked = _invoke_native_density_size_adjust(
                context,
                area_pointer=self._invoke_area_pointer,
                release_confirm=self._native_density_adjust_confirm_on_release,
            )
        elif WORLD_NATIVE_DENSITY_MODAL_ADJUST_ENABLED:
            invoked = _invoke_native_density_spacing_adjust(
                context,
                area_pointer=self._invoke_area_pointer,
                release_confirm=self._native_density_adjust_confirm_on_release,
            )
        else:
            invoked = True
            self._apply_density_spacing_to_native_brush(context)

        if not invoked:
            self.adjust_mode = ""
            self.adjust_origin_x = None
            self._adjust_depth_location = None
            self._native_density_adjust_passthrough = False
            self._force_native_brush_visibility(context)
            shared.secret_paint_brush_size_trace_log(
                "world.begin_native_adjust.invoke_failed",
                context,
                self,
                adjust_mode=adjust_mode,
                confirm_on_release=confirm_on_release,
            )
            return False

        self._start_live_native_adjust_control_sync(context, adjust_mode)
        if event is not None and self._native_density_adjust_confirm_on_release:
            self._start_native_density_adjust_release_watch(context, event=event)
        shared.secret_paint_brush_size_trace_log(
            "world.begin_native_adjust.exit",
            context,
            self,
            adjust_mode=adjust_mode,
            confirm_on_release=confirm_on_release,
            invoked=invoked,
        )
        return True

    def _begin_adjust(self, context, adjust_mode, event=None, *, confirm_on_release=False):
        shared.secret_paint_brush_size_trace_log(
            "world.begin_adjust.enter",
            context,
            self,
            adjust_mode=adjust_mode,
            confirm_on_release=confirm_on_release,
            event_type=getattr(event, "type", "") if event is not None else "",
            event_value=getattr(event, "value", "") if event is not None else "",
            event_alt=bool(getattr(event, "alt", False)) if event is not None else False,
        )
        self._commit_active_native_density_adjust_result(context)
        self._native_density_adjust_passthrough = False
        if (
            self._density_uses_native_ui()
            and not WORLD_CUSTOM_ADJUST_UI_ENABLED
            and not (adjust_mode == "STRENGTH" and self._tool_uses_brush_strength_adjust())
        ):
            return self._begin_native_adjust(
                context,
                adjust_mode,
                event=event,
                confirm_on_release=confirm_on_release,
            )

        if self._density_uses_native_ui():
            if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
                self._update_hover_target(context, event, commit=False)
            if self.hover_target is None:
                current_system_target = _target_info_from_system(
                    context,
                    self._current_system(),
                    allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                )
                if current_system_target is not None:
                    self._activate_hover_target(context, current_system_target)
            if self._begin_native_density_session(context, create_system=False):
                self._stash_native_density_brush_overlay_state(
                    self._native_density_brush(context),
                    force=True,
                )
                self._stash_native_density_brush_visibility(context, force=True)
        self.adjust_mode = adjust_mode
        self.adjust_origin_x = self._adjust_origin_from_event(event)
        self._adjust_depth_location = self._brush_screen_depth_location()
        self._native_density_adjust_depth_location = self._adjust_depth_location
        self._native_density_adjust_manual_spacing = None
        self._native_density_adjust_confirm_pending = False
        self._native_density_adjust_finalizing = False
        self._native_density_adjust_waiting_for_alt_release = False
        self._native_density_adjust_confirm_on_release = bool(confirm_on_release)
        self._last_brush_control_sync_time = 0.0
        if adjust_mode == "SIZE":
            self.adjust_base_value = self.brush_radius_setting
        elif adjust_mode == "STRENGTH" and self._tool_uses_brush_strength_adjust():
            strength = self._read_active_brush_strength(context, ensure=True)
            self.adjust_base_value = self.brush_strength if strength is None else strength
        else:
            self.adjust_base_value = self.density_spacing
        if self._density_uses_native_ui():
            self._install_draw_handlers(context)
            self._suppress_native_brush_ui_for_adjust(context)
        if context.area:
            context.area.tag_redraw()
        return True

    def _update_adjust(self, context, event):
        if not self.adjust_mode:
            return False
        if self.adjust_origin_x is None:
            self.adjust_origin_x = event.mouse_region_x
            return True

        delta = (event.mouse_region_x - self.adjust_origin_x) * WORLD_ADJUST_DRAG_SCALE
        if self.adjust_mode == "SIZE":
            next_radius_setting = max(0.05, self.adjust_base_value + delta)
            if abs(next_radius_setting - self.brush_radius_setting) < 0.0001:
                return True
            self.brush_radius_setting = next_radius_setting
            self._sync_effective_brush_radius(
                context,
                depth_location=self._adjust_depth_location,
                mouse_coord=self.hover_mouse_region,
            )
            self._mark_deferred_brush_settings_dirty(radius=True, native_sync=True)
        elif self.adjust_mode == "STRENGTH" and self._tool_uses_brush_strength_adjust():
            next_strength = _brush_strength_value(
                self.adjust_base_value + delta * 0.2,
                fallback=self.brush_strength,
            )
            if abs(next_strength - self.brush_strength) < WORLD_DENSITY_SPACING_EPSILON:
                return True
            self._set_active_brush_strength(context, next_strength)
        else:
            next_density_spacing = _density_spacing_value(
                self.adjust_base_value + delta * 0.2,
                fallback=self.density_spacing,
            )
            if abs(next_density_spacing - self.density_spacing) < 0.0001:
                return True
            self.density_spacing = next_density_spacing
            _native_brush_debug_log("adjust_density.update", context, self, force=True, density_spacing=self.density_spacing)
            self._mark_deferred_brush_settings_dirty(density=True, native_sync=True)
        self._sync_brush_controls(context)
        if context.area:
            context.area.tag_redraw()
        return True

    def _end_adjust(self, context=None):
        native_adjust_mode = self.adjust_mode if self._native_density_adjust_passthrough else ""
        shared.secret_paint_brush_size_trace_log(
            "world.end_adjust.enter",
            context,
            self,
            native_adjust_mode=native_adjust_mode,
        )
        self.adjust_mode = ""
        self.adjust_origin_x = None
        self._adjust_depth_location = None
        self._native_density_adjust_passthrough = False
        self._native_density_adjust_confirm_pending = False
        self._native_density_adjust_auto_confirm_until = 0.0
        self._native_density_adjust_release_watch_token += 1
        self._native_density_adjust_release_watch_running = False
        self._native_density_adjust_release_watch_saw_shortcut_down = False
        self._native_density_adjust_release_watch_started = 0.0
        self._native_density_adjust_finalizing = False
        self._native_density_adjust_waiting_for_alt_release = False
        self._native_density_adjust_native_release_confirm = False
        self._stop_live_native_adjust_control_sync()

        if native_adjust_mode:
            if context is not None and self._density_uses_native_ui() and not self.stroke_active:
                self._restore_native_density_brush_overlay()
                self._restore_native_density_brush_visibility(context)
                self._force_native_brush_visibility(context)
                self._remove_draw_handlers()
                if context.area:
                    context.area.tag_redraw()
            self._schedule_native_density_adjust_result_sync(native_adjust_mode)
            if context is not None:
                self._schedule_native_adjust_passthrough_stable_id_sync(context, None)
            shared.secret_paint_brush_size_trace_log(
                "world.end_adjust.scheduled_native_sync",
                context,
                self,
                native_adjust_mode=native_adjust_mode,
            )
            return

        self._native_density_adjust_depth_location = None
        self._native_density_adjust_manual_spacing = None
        if context is not None:
            self._flush_deferred_brush_settings(context)
        if context is not None and self._density_uses_native_ui() and not self.stroke_active:
            self._restore_native_density_brush_overlay()
            self._restore_native_density_brush_visibility(context)
            self._force_native_brush_visibility(context)
            self._remove_draw_handlers()
            try:
                self._refresh_brush_cursor_after_view_reentry(
                    context,
                    schedule=True,
                    force_rebuild=bool(getattr(self, "_brush_cursor_focus_lost", False)),
                )
                self._brush_cursor_focus_lost = False
            except Exception:
                self._schedule_brush_cursor_reentry_refresh()
            if context.area:
                context.area.tag_redraw()
        shared.secret_paint_brush_size_trace_log(
            "world.end_adjust.exit",
            context,
            self,
            native_adjust_mode=native_adjust_mode,
        )

    def _confirm_adjust_from_event(self, context, event):
        if self.adjust_mode and not getattr(self, "_native_density_adjust_passthrough", False):
            if event is not None and hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
                try:
                    self._update_adjust(context, event)
                except Exception:
                    pass
        self._end_adjust(context)
        return True

    def _handle_native_adjust_passthrough_event(self, context, event):
        if not (self.adjust_mode and self._native_density_adjust_passthrough):
            return None
        event_type = getattr(event, "type", "")
        event_value = getattr(event, "value", "")
        if event_type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            shared.secret_paint_brush_size_trace_log(
                "world.native_adjust_passthrough.event",
                context,
                self,
                event_type=event_type,
                event_value=event_value,
                event_alt=bool(getattr(event, "alt", False)),
                event_shift=bool(getattr(event, "shift", False)),
                event_ctrl=bool(getattr(event, "ctrl", False)),
            )
        if (
            getattr(self, "_native_density_adjust_confirm_pending", False) and
            event_type == 'LEFTMOUSE' and
            time.perf_counter() <= float(getattr(self, "_native_density_adjust_auto_confirm_until", 0.0) or 0.0)
        ):
            shared.secret_paint_brush_size_trace_log(
                "world.native_adjust_passthrough.auto_confirm_leftmouse_passthrough",
                context,
                self,
                event_type=event_type,
                event_value=event_value,
            )
            self._schedule_native_adjust_passthrough_stable_id_sync(context, event)
            return {'PASS_THROUGH'}
        if (
            self.adjust_mode == "SIZE"
            and getattr(self, "_native_density_adjust_confirm_pending", False)
        ):
            commit_pending_size = getattr(self, "_commit_pending_native_size_adjust_confirm", None)
            if callable(commit_pending_size) and commit_pending_size(context):
                shared.secret_paint_brush_size_trace_log(
                    "world.native_adjust_passthrough.pending_size_committed",
                    context,
                    self,
                    event_type=event_type,
                    event_value=event_value,
                )
                return None
            shared.secret_paint_brush_size_trace_log(
                "world.native_adjust_passthrough.pending_size_wait",
                context,
                self,
                event_type=event_type,
                event_value=event_value,
            )
            return {'PASS_THROUGH'}
        if (
            self.adjust_mode == "SIZE"
            and bool(getattr(self, "_native_density_adjust_confirm_on_release", False))
            and not _event_matches_current_adjust_shortcut(
                context,
                event,
                self.adjust_mode,
                ignore_value=True,
            )
        ):
            try:
                key_state = self._native_density_adjust_shortcut_key_state(
                    context,
                    self.adjust_mode,
                )
            except Exception:
                key_state = None
            if (
                key_state is not None
                and not bool(key_state.get("shortcut_down", False))
                and bool(getattr(self, "_native_density_adjust_release_watch_saw_shortcut_down", False))
            ):
                try:
                    if self._commit_active_native_density_adjust_result(context):
                        shared.secret_paint_brush_size_trace_log(
                            "world.native_adjust_passthrough.size_committed_before_next_event",
                            context,
                            self,
                            event_type=event_type,
                            event_value=event_value,
                            key_state=key_state,
                        )
                        return None
                except Exception:
                    pass
        if event_value == 'PRESS':
            shortcut = _world_paint_shortcut_from_event(context, event)
            if shortcut is not None and shortcut[0] == "TOOL":
                adjust_mode = self.adjust_mode
                if adjust_mode == "STRENGTH":
                    self._cache_native_density_adjust_spacing_from_event(context, event)
                try:
                    self._sync_native_density_adjust_result(context, adjust_mode)
                except Exception:
                    pass
                self._native_density_pending_adjust_mode = ""
                self._native_density_adjust_passthrough = False
                self._end_adjust(context)
                try:
                    self._send_native_adjust_confirm_key_event()
                except Exception:
                    pass
                self._set_tool(context, shortcut[1], sync_workspace=True)
                return {'RUNNING_MODAL'}
        if self._is_adjust_confirm_release_event(context, event):
            if self.adjust_mode == "STRENGTH" and WORLD_NATIVE_DENSITY_MODAL_ADJUST_ENABLED:
                self._cache_native_density_adjust_spacing_from_event(context, event)
                self._finalize_native_density_adjust_release(
                    context,
                    wait_for_alt_release=bool(getattr(event, "alt", False)),
                )
                return {'PASS_THROUGH'}
            if not getattr(self, "_native_density_adjust_confirm_pending", False):
                adjust_mode = self.adjust_mode
                if adjust_mode == "SIZE":
                    shared.secret_paint_brush_size_trace_log(
                        "world.native_adjust_passthrough.release_confirm_size",
                        context,
                        self,
                        event_type=event_type,
                        event_value=event_value,
                    )
                    self._request_native_size_adjust_confirm(
                        delay=0.0,
                        reason="release_confirm_event",
                    )
                else:
                    try:
                        self._sync_native_density_adjust_result(context, adjust_mode)
                    except Exception:
                        pass
                    self._native_density_adjust_confirm_pending = True
                    self._schedule_native_density_adjust_result_sync(adjust_mode)
                    self._schedule_native_adjust_finish(delay=0.04)
                return {'PASS_THROUGH'}
            self._end_adjust(context)
            return {'PASS_THROUGH'}
        if self.adjust_mode == "STRENGTH" and event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self._cache_native_density_adjust_spacing_from_event(context, event)
            return {'PASS_THROUGH'}
        if self.adjust_mode == "SIZE" and event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self._sync_live_native_adjust_controls(context, "SIZE")
            return {'PASS_THROUGH'}
        if (
            self.adjust_mode == "SIZE"
            and not bool(getattr(self, "_native_density_adjust_confirm_on_release", False))
            and _event_matches_current_adjust_shortcut(
                context,
                event,
                self.adjust_mode,
                ignore_value=True,
            )
            and event_value == 'RELEASE'
        ):
            shared.secret_paint_brush_size_trace_log(
                "world.native_adjust_passthrough.size_shortcut_release_left_click_mode",
                context,
                self,
            )
            return {'PASS_THROUGH'}
        if (
            self.adjust_mode == "STRENGTH"
            and not bool(getattr(self, "_native_density_adjust_confirm_on_release", True))
            and (
                _event_matches_current_adjust_shortcut(
                    context,
                    event,
                    self.adjust_mode,
                    ignore_value=True,
                )
                or event_type in {'LEFT_ALT', 'RIGHT_ALT', 'ALT'}
            )
            and event_value == 'RELEASE'
        ):
            return {'PASS_THROUGH'}
        if (
            event_value == 'PRESS'
            and _event_matches_current_adjust_shortcut(
                context,
                event,
                self.adjust_mode,
            )
        ):
            adjust_mode = self.adjust_mode
            if adjust_mode == "STRENGTH":
                self._cache_native_density_adjust_spacing_from_event(context, event)
            try:
                self._sync_native_density_adjust_result(context, adjust_mode)
            except Exception:
                pass
            self._native_density_pending_adjust_mode = ""
            self._native_density_adjust_passthrough = False
            self._end_adjust(context)
            return None
        if (
            self.tool_id == WORLD_TOOL_DENSITY and
            event_type == 'RIGHTMOUSE' and
            event_value in {'PRESS', 'RELEASE'}
        ):
            adjust_mode = self.adjust_mode
            shared.secret_paint_brush_size_trace_log(
                "world.native_adjust_passthrough.rightmouse_ends_adjust",
                context,
                self,
                adjust_mode=adjust_mode,
                event_value=event_value,
            )
            if adjust_mode == "STRENGTH":
                self._cache_native_density_adjust_spacing_from_event(context, event)
                try:
                    self._sync_native_density_adjust_result(context, adjust_mode)
                except Exception:
                    pass
            self._native_density_pending_adjust_mode = ""
            self._native_density_adjust_passthrough = False
            self._end_adjust(context)
            return None
        if (
            (
                event_type in {'ESC', 'LEFTMOUSE', 'ACTIONMOUSE', 'SELECTMOUSE', 'RIGHTMOUSE'}
                or _event_matches_current_adjust_shortcut(
                    context,
                    event,
                    self.adjust_mode,
                    ignore_value=True,
                )
            )
            and event_value in {'PRESS', 'RELEASE', 'CLICK'}
        ):
            adjust_mode = self.adjust_mode
            if adjust_mode == "SIZE":
                if (
                    not bool(getattr(self, "_native_density_adjust_confirm_on_release", False))
                    and _is_primary_paint_event(event)
                ):
                    shared.secret_paint_brush_size_trace_log(
                        "world.native_adjust_passthrough.left_click_confirm_size",
                        context,
                        self,
                        event_type=event_type,
                        event_value=event_value,
                    )
                    self._request_native_size_adjust_confirm(
                        delay=0.01,
                        reason="left_click_confirm",
                    )
                    return {'PASS_THROUGH'}
                self._native_density_pending_adjust_mode = ""
                self._native_density_adjust_passthrough = False
            self._schedule_native_adjust_passthrough_stable_id_sync(context, event)
            self._end_adjust(context)
        return {'PASS_THROUGH'}

    def _install_draw_handlers(self, context):
        if self._density_uses_native_ui():
            self._remove_draw_handlers()
            return
        if self._draw_handle_3d is None:
            self._draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(
                _draw_world_circle,
                (self, context),
                'WINDOW',
                'POST_VIEW',
            )
        if self._draw_handle_2d is None:
            self._draw_handle_2d = bpy.types.SpaceView3D.draw_handler_add(
                _draw_world_hud,
                (self, context),
                'WINDOW',
                'POST_PIXEL',
            )

    def _remove_draw_handlers(self):
        if self._draw_handle_3d is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle_3d, 'WINDOW')
            except Exception:
                pass
            self._draw_handle_3d = None
        if self._draw_handle_2d is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle_2d, 'WINDOW')
            except Exception:
                pass
            self._draw_handle_2d = None

    def _world_paint_guard_system_names(self):
        guard_system_names = {
            self.active_system_name,
            self._native_density_active_system_name,
            self._active_name,
        }
        guard_system_names.update(getattr(self, "_touched_system_names", set()) or set())
        current_system = self._current_system()
        if current_system is not None:
            guard_system_names.add(current_system.name)
        return {name for name in guard_system_names if name}

    def _finish_world_paint_cleanup(self, context, guard_system_names):
        context = context or bpy.context
        self.adjust_mode = ""
        self.adjust_origin_x = None
        self._native_density_adjust_passthrough = False
        self._disabled_size_adjust_passthrough_active = False
        self.stroke_active = False
        self._active_density_stroke_mode = ""
        self._native_density_interaction_mode = ""
        self._density_stroke_passthrough = False
        self._native_density_stroke_erase = False
        self._density_right_delete_button_down = False
        self._native_density_session_active = False
        try:
            self._restore_native_density_brush_overlay()
        except Exception:
            pass
        try:
            self._restore_native_density_brush_visibility(context)
        except Exception:
            pass
        try:
            _store_operator_brush_radius(self, context)
            _store_operator_density_spacing(self)
        except Exception:
            pass
        self._remove_draw_handlers()
        try:
            _mark_world_paint_object_mode_guard(guard_system_names, duration=0.5)
            if (getattr(context, "mode", "") or "") != 'OBJECT':
                _mode_set_with_world_toolbar_restored('OBJECT')
            _force_system_names_object_mode_after_world_paint(context, guard_system_names)
            _delete_visible_empty_manual_paint_systems(
                context,
                getattr(self, "_session_empty_auto_delete_system_names", set()),
            )
            _force_object_select_tool_after_world_paint(context)
            _schedule_object_mode_after_world_paint_cleanup()
        except Exception:
            pass
        try:
            _restore_world_ui(self, context)
        except Exception:
            pass
        try:
            _force_object_select_tool_after_world_paint(context)
        except Exception:
            pass
        if getattr(self, "_world_ui_cage_hidden", False):
            try:
                shared.secret_paint_enable_sculpt_curves_cage(context)
                self._world_ui_cage_hidden = False
            except Exception:
                pass
        try:
            self._set_native_os_cursor_hidden(context, False)
            context.window.cursor_modal_restore()
        except Exception:
            pass
        try:
            context.workspace.status_text_set(text=None)
        except Exception:
            pass
        try:
            area = getattr(context, "area", None)
            if area:
                area.tag_redraw()
        except Exception:
            pass
        try:
            shared.secret_paint_world_perf_log_flush(force=True)
        except Exception:
            pass

    def finish_world_paint(self, context):
        _q_debug_log_keymaps("finish_world_paint.enter", context, finish_requested=getattr(self, "_finish_requested", False))
        if getattr(self, "_finish_requested", False):
            _q_debug_log("finish_world_paint.skip_already_requested", context)
            return
        self._finish_requested = True
        try:
            if getattr(self, "_pick_source_hold_active", False):
                self._end_pick_source_hold(context, commit=False, restore_paint_ui=False)
            else:
                self._restore_pick_selection_preview(context, restore_cage=True)
        except Exception:
            pass
        try:
            guard_system_names = self._world_paint_guard_system_names()
        except Exception:
            guard_system_names = set()
        try:
            locked_targets = self._locked_target_infos()
            if self.surface_lock and locked_targets and not self._surface_lock_retarget_pending:
                _store_scene_locked_terrains(context, locked_targets)
        except Exception:
            pass
        self._running = False
        _WORLD_STATE["operator"] = None
        self._selection_preview_token += 1
        self._selection_preview_cage_until = 0.0
        self._native_cursor_activation_token += 1
        self._native_passthrough_finish_pending = False
        _WORLD_STATE["exit_consume_paint_until"] = 0.0
        try:
            _set_world_keymap_conflicts_enabled(context, True)
        except Exception:
            pass
        try:
            _set_world_paint_shortcuts_enabled(context, True)
        except Exception:
            pass
        try:
            _remove_world_right_delete_brush_keymap(context)
        except Exception:
            pass
        _clear_world_keymap_lookup_caches()
        if not getattr(self, "_finish_cleanup_done", False):
            self._finish_cleanup_done = True
            try:
                self._finish_world_paint_cleanup(context, guard_system_names)
            except Exception:
                pass
        _q_debug_log_keymaps("finish_world_paint.exit", context)

    def invoke(self, context, event):
        _q_debug_log(
            "world_paint_mode.invoke.enter",
            context,
            event_type=getattr(event, "type", ""),
            event_value=getattr(event, "value", ""),
        )
        type(self)._reset_runtime_state(self)
        shared.secret_paint_world_perf_log_reset("world_paint_invoke")
        shared.secret_paint_brush_size_trace_reset("world_paint_invoke")
        _native_brush_debug_reset("world_paint_invoke")
        _shift_delete_debug_reset("world_paint_invoke")
        _shift_delete_debug_log("invoke.enter", context, self, event=event, force=True)
        _native_brush_debug_log("invoke.enter", context, self, force=True, event_type=getattr(event, "type", ""))
        running = _world_operator()
        if running is not None:
            _q_debug_log("world_paint_mode.invoke.finish_running", context)
            running.finish_world_paint(context)
            return {'FINISHED'}

        if context.area is None or context.area.type != 'VIEW_3D':
            _q_debug_log("world_paint_mode.invoke.cancel_no_view3d", context)
            self.report({'WARNING'}, "World paint only works from a 3D View")
            return {'CANCELLED'}

        self.source_data = _selected_source_from_context(self, context)
        if not self.source_data:
            _q_debug_log("world_paint_mode.invoke.cancel_no_source", context)
            self.report({'WARNING'}, "Select one brush object or one Secret Paint system first")
            return {'CANCELLED'}
        self._live_source_snapshot = _source_data_snapshot(self.source_data)
        if _source_data_should_start_bezier_tool(self.source_data):
            self.tool_id = WORLD_TOOL_BEZIER
            if self._handoff_to_bezier_curve_edit(context):
                return {'FINISHED'}
            return {'CANCELLED'}

        self._selection_names = [obj.name for obj in context.selected_objects]
        self._active_name = context.active_object.name if context.active_object else ""
        self._original_mode = context.mode if context.mode else "OBJECT"
        _deselect_secret_paint_systems(context)
        if context.mode != 'OBJECT':
            try:
                _mode_set_with_world_toolbar_restored('OBJECT')
            except Exception:
                pass
        if self._density_uses_native_ui() and self.tool_id != WORLD_TOOL_BEZIER:
            _park_active_object_away_from_secret_system(context, self.source_data)
        self.toggle_key_type = (
            event.type
            if _event_matches_base_paint_shortcut(context, event) or _event_looks_like_keyboard_shortcut(event)
            else ""
        )
        self._remember_paint_shortcut_release_chord(context, event)
        preferences = _addon_preferences(context)
        scene_locked_targets = _scene_locked_terrain_target_infos(context)
        self.surface_lock = bool(scene_locked_targets)
        self._surface_lock_retarget_pending = bool(self.surface_lock)
        self.allow_wire_bounds_surfaces = bool(
            getattr(preferences, "allow_world_paint_wire_bounds_surfaces", True)
            if preferences is not None else True
        )
        if (
            self.source_data.get("origin_kind") == "SYSTEM"
            and _system_target_needs_wire_bounds_surfaces(self.source_data.get("origin_object"))
        ):
            self.allow_wire_bounds_surfaces = True
        self.always_use_2d_world_paint_brush_ui = bool(
            preferences and getattr(preferences, "always_use_2d_world_paint_brush_ui", False)
        )
        self.interpolate = _world_paint_interpolate_preference(context)
        if not self._density_uses_native_ui():
            try:
                shared.secret_paint_ensure_sp_curves_brush_assets(
                    context,
                    configure=True,
                    override_settings=bool(preferences and getattr(preferences, "checkboxOverrideBrushes", False)),
                    size=150,
                )
            except Exception:
                pass
        self._running = True
        _WORLD_STATE["operator"] = self
        if not self._density_uses_native_ui():
            self._install_draw_handlers(context)
        _begin_world_ui(self, context)
        _precache_world_modal_keymaps(context)
        if self._density_uses_native_ui() and self.tool_id != WORLD_TOOL_BEZIER:
            _ensure_world_right_delete_brush_keymap(context)
        if self._density_uses_native_ui():
            try:
                context.window.cursor_modal_restore()
            except Exception:
                pass
        else:
            try:
                context.window.cursor_modal_set('PAINT_CROSS')
            except Exception:
                pass
        try:
            context.workspace.status_text_set(text=WORLD_PAINT_STATUS_TEXT)
        except Exception:
            pass

        if self._source_data_is_system_source(self.source_data) and self.tool_id != WORLD_TOOL_BEZIER:
            origin_system = self.source_data.get("origin_object")
            origin_target = _target_info_from_system(
                context,
                origin_system,
                allow_wire_bounds_surfaces=self.allow_wire_bounds_surfaces,
                ignore_display_type_block=self.surface_lock,
            )
            if origin_target is not None:
                if self.surface_lock:
                    origin_key = _target_key(origin_target)
                    if (
                        scene_locked_targets and
                        origin_key and
                        origin_key not in _target_info_key_set(scene_locked_targets)
                    ):
                        self._set_locked_target(context, origin_target)
                        scene_locked_targets = [self.locked_target] if self.locked_target is not None else []
                    elif scene_locked_targets:
                        self._set_locked_targets(context, scene_locked_targets, active_target=origin_target)
                    matching_locked_target = next(
                        (
                            target_info
                            for target_info in self._locked_target_infos()
                            if _target_key(target_info) == origin_key
                        ),
                        None,
                    )
                    if matching_locked_target is not None:
                        self.locked_target = _copy_target_info(matching_locked_target)
                    origin_target = self.locked_target or (
                        self._locked_target_infos()[0] if self._locked_target_infos() else origin_target
                    )
                else:
                    self._surface_lock_retarget_pending = False
                self.preview_target = origin_target
                self.hover_target = origin_target
                self.last_hover_key = _target_key(origin_target)
                self._set_active_system_lightweight(context, origin_system)
            _keep_active_system_object(context, origin_system)
            if self._density_uses_native_ui() and origin_target is not None:
                self._defer_native_idle_session = not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE
                if WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
                    self._ensure_idle_native_density_session(context)
        else:
            if self.surface_lock and self._restore_scene_locked_target(context, activate=True):
                self.preview_target = self.locked_target
                self.hover_target = self.locked_target
                self.last_hover_key = _target_key(self.locked_target)
            else:
                self.preview_target = None
                self.hover_target = None
                self.locked_target = None
                self.locked_targets = []
                self.last_hover_key = ""
            self.active_system_name = ""
            if (
                self.source_data.get("origin_kind") == "OBJECT"
                and not self._source_data_is_system_source(self.source_data)
                and self.surface_lock
                and self._locked_target_infos()
            ):
                self._activate_object_source_target_system(
                    context,
                    self.locked_target or self._locked_target_infos()[0],
                )

        if not self._density_uses_native_ui():
            self._sync_effective_brush_radius(context)
        self._sync_brush_controls(context)
        if not (self._density_uses_native_ui() and self.tool_id != WORLD_TOOL_BEZIER):
            self._set_tool(context, self.tool_id, sync_workspace=True)
        elif self._density_uses_native_ui() and self.tool_id != WORLD_TOOL_BEZIER:
            self._sync_tool_ui_mode(context)
        self._viewport_navigation_last_state_key = _viewport_navigation_state_key(self, context)
        context.window_manager.modal_handler_add(self)
        _q_debug_log_keymaps("world_paint_mode.invoke.ready", context)
        shared.secret_paint_world_perf_log(
            "world.invoke.ready",
            mode=context.mode,
            tool=self.tool_id,
            source_kind=self.source_data.get("origin_kind", ""),
            active_system=self.active_system_name,
            native_ui=self._density_uses_native_ui(),
        )
        _shift_delete_debug_log("invoke.exit_running", context, self, event=event, force=True)
        _native_brush_debug_log("invoke.exit_running", context, self, force=True)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self._running:
            _q_debug_log(
                "world_paint_mode.modal.stopped",
                context,
                event_type=getattr(event, "type", ""),
                event_value=getattr(event, "value", ""),
            )
            if _start_base_paint_from_stopped_modal(context, event):
                return {'CANCELLED'}
            return {'CANCELLED', 'PASS_THROUGH'}
        if (
            (getattr(context, "mode", "") or "") == 'OBJECT'
            and not getattr(self, "_pick_source_hold_active", False)
            and not getattr(self, "stroke_active", False)
            and not getattr(self, "adjust_mode", "")
            and _event_looks_like_keyboard_shortcut(event)
            and _event_matches_base_paint_shortcut(context, event)
        ):
            _q_debug_log(
                "world_paint_mode.modal.stale_object_mode",
                context,
                event_type=getattr(event, "type", ""),
                event_value=getattr(event, "value", ""),
            )
            self.finish_world_paint(context)
            if _event_looks_like_keyboard_shortcut(event):
                if _start_base_paint_from_stopped_modal(context, event):
                    return {'CANCELLED'}
            return {'CANCELLED', 'PASS_THROUGH'}
        event_type = getattr(event, "type", "")
        primary_down_before_event = bool(getattr(self, "_primary_paint_button_down", False))
        self._sync_primary_paint_button_state(event)
        primary_released_by_event_history = (
            primary_down_before_event and
            not bool(getattr(self, "_primary_paint_button_down", False))
        )
        if self.tool_id != WORLD_TOOL_BEZIER and self._handle_priority_shortcut_event(context, event):
            return {'RUNNING_MODAL'}
        if (
            _modal_idle_for_viewport_bookmark(self)
            and _viewport_bookmark_shortcut_from_event(context, event)
        ):
            bookmark_result = shared.secret_paint_toggle_viewport_bookmark(context)
            result = {'RUNNING_MODAL'} if 'FINISHED' in bookmark_result else {'PASS_THROUGH'}
            return result
        native_mode_shortcut = _native_mode_shortcut_from_event(context, event)
        if native_mode_shortcut:
            self.finish_world_paint(context)
            return {'CANCELLED', 'PASS_THROUGH'}
        if not self._refresh_undo_invalidated_references():
            self.report({'INFO'}, "Paint source is no longer available after undo")
            self.finish_world_paint(context)
            return {'FINISHED'}

        if (
            self.tool_id == WORLD_TOOL_DENSITY and
            event_type == 'RIGHTMOUSE' and
            getattr(event, "value", "") in WORLD_PRIMARY_PAINT_ACTIVE_VALUES and
            not bool(getattr(event, "alt", False))
        ):
            self._density_right_delete_restore_token = getattr(
                self,
                "_density_right_delete_restore_token",
                0,
            ) + 1
            self._density_right_delete_button_down = True
            self._density_right_delete_restore_pending = True

        right_delete_release_requested = (
            self._is_density_right_delete_release_event(event) and
            (
                getattr(self, "_density_right_delete_restore_pending", False) or
                getattr(self, "_density_right_delete_button_down", False) or
                getattr(self, "_shift_delete_tool_active", False) or
                self.tool_id == WORLD_TOOL_DELETE
            )
        )
        if right_delete_release_requested:
            self._density_right_delete_restore_pending = True
            if self._native_density_passthrough_active():
                self._primary_paint_button_down = False
                self._finish_native_passthrough_after_blender_event(event)
                self._finish_density_right_delete_release(context)
                return {'PASS_THROUGH'}
            if self.stroke_active or self._native_density_session_active:
                self._end_paint_interaction(context, event)
            self._finish_density_right_delete_release(context)
            return {'RUNNING_MODAL'}

        if self._handle_disabled_size_adjust_passthrough_event(context, event):
            return {'RUNNING_MODAL'}
        if self._handle_native_density_radial_passthrough_event(context, event):
            return {'PASS_THROUGH'}
        if (
            event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} and
            self._density_uses_native_ui() and
            (
                self.adjust_mode or
                getattr(self, "_brush_cursor_focus_lost", False) or
                not getattr(self, "_last_region_in_window", False)
            )
        ):
            self._maybe_refresh_brush_cursor_for_region_reentry(context, event)
        paint_shortcut_release_status = ""
        if (
            getattr(event, "value", "") == 'RELEASE'
            and (
                getattr(self, "_entry_source_preview_active", False)
                or getattr(self, "_pick_source_hold_active", False)
            )
        ):
            paint_shortcut_release_status = self._paint_shortcut_release_status(context, event)
        if (
            getattr(self, "_entry_source_preview_active", False)
            and paint_shortcut_release_status
        ):
            if paint_shortcut_release_status == "complete":
                self._end_entry_source_preview(context, event)
            return {'RUNNING_MODAL'}
        if (
            getattr(self, "_pick_source_hold_active", False)
            and paint_shortcut_release_status
        ):
            if paint_shortcut_release_status == "complete":
                self._end_pick_source_hold(context, event, commit=True)
            return {'RUNNING_MODAL'}
        if (
            getattr(self, "_entry_source_preview_active", False)
            and getattr(self, "_entry_source_preview_allows_hold_pick", False)
            and event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}
            and (
                time.perf_counter()
                - float(getattr(self, "_entry_source_preview_hold_start_time", 0.0) or 0.0)
            ) >= WORLD_ENTRY_SOURCE_HOLD_DELAY
        ):
            self._end_entry_source_preview(context, event)
            self._begin_pick_source_hold(context, event)
            return {'RUNNING_MODAL'}

        if (
            self._density_uses_native_ui() and
            not self.stroke_active and
            not self.adjust_mode and
            not getattr(self, "_pick_source_hold_active", False) and
            not self._event_shift_active(event) and
            not _is_primary_paint_event(event) and
            _is_passive_idle_passthrough_event(event)
        ):
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            if self._native_density_session_active and not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
                self._defer_idle_native_density_session(context)
                return {'PASS_THROUGH'}
            if (
                not self._native_density_session_active and
                not self._native_idle_session_deferred(event) and
                event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} and
                self._event_is_in_world_paint_view(context, event)
            ):
                self._ensure_idle_native_density_session(context, event=event)
            self._perf_passive_event_count = getattr(self, "_perf_passive_event_count", 0) + 1
            if self._perf_passive_event_count % 120 == 0:
                shared.secret_paint_world_perf_log(
                    "world.modal.passive_sample",
                    event=event_type,
                    value=getattr(event, "value", ""),
                    mode=context.mode,
                    active_object=getattr(getattr(context, "active_object", None), "name", ""),
                    native_session=self._native_density_session_active,
                    tool=self.tool_id,
                )
            return {'PASS_THROUGH'}

        now = time.perf_counter()
        last_modal_event_time = float(getattr(self, "_last_modal_event_time", 0.0) or 0.0)
        self._last_modal_event_time = now
        focus_gap_recovery = (
            last_modal_event_time > 0.0 and
            now - last_modal_event_time > 0.45 and
            event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'LEFTMOUSE', 'ACTIONMOUSE', 'SELECTMOUSE'}
        )

        if event_type in {'WINDOW_DEACTIVATE', 'WINDOW_LEAVE'}:
            if getattr(self, "_pick_source_hold_active", False):
                self._end_pick_source_hold(context, event, commit=False, restore_paint_ui=False)
            else:
                self._restore_pick_selection_preview(context, restore_cage=True)
            self._last_region_in_window = False
            self._brush_cursor_focus_lost = True
            self._set_native_os_cursor_hidden(context, False)
            _tag_redraw_view3d_areas(context)
            return {'PASS_THROUGH'}

        if event_type in {'WINDOW_ACTIVATE', 'WINDOW_ENTER'}:
            self._last_region_in_window = False
            self._brush_cursor_focus_lost = True
            try:
                if self.adjust_mode:
                    if getattr(self, "_native_density_adjust_passthrough", False):
                        self._remove_draw_handlers()
                        self._restore_native_density_brush_overlay()
                        self._restore_native_density_brush_visibility(context)
                        self._force_native_brush_visibility(context, allow_adjust=True)
                    else:
                        self._install_draw_handlers(context)
                    _tag_redraw_view3d_areas(context)
                else:
                    refresh_event = event if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y") else None
                    self._refresh_brush_cursor_after_view_reentry(
                        context,
                        refresh_event,
                        schedule=True,
                        force_rebuild=True,
                    )
                    self._brush_cursor_focus_lost = False
            except Exception:
                self._schedule_brush_cursor_reentry_refresh()
            try:
                self._sync_native_os_cursor_for_region(
                    context,
                    _event_region_context(context, event, self._invoke_area_pointer),
                )
            except Exception:
                self._set_native_os_cursor_hidden(context, False)
            _tag_redraw_view3d_areas(context)
            return {'PASS_THROUGH'}

        native_adjust_result = self._handle_native_adjust_passthrough_event(context, event)
        if native_adjust_result is not None:
            return native_adjust_result
        if self._handle_brush_strength_adjust_confirm_event(context, event):
            return {'RUNNING_MODAL'}

        bezier_tool_active = self.tool_id == WORLD_TOOL_BEZIER

        if not bezier_tool_active and (
            (event.type == 'ESC' and event.value == 'PRESS')
        ):
            self.finish_world_paint(context)
            return {'RUNNING_MODAL'}

        if (
            not bezier_tool_active and
            _is_primary_paint_active_event(event) and
            not self._event_shift_active(event) and
            (
                self._shift_delete_tool_active or
                self._density_right_delete_button_down
            )
        ):
            if self.stroke_active:
                self._end_paint_interaction(context, event)
            self._finish_density_right_delete_release(context)

        if getattr(self, "_pick_source_hold_active", False) and event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self._update_pick_source_hold(context, event)
            return {'RUNNING_MODAL'}

        idle_native_passthrough = (
            self._density_uses_native_ui() and
            self._native_density_session_active and
            not self.stroke_active and
            not self.adjust_mode and
            not self._event_shift_active(event) and
            (_is_passive_idle_passthrough_event(event) or _is_primary_paint_event(event))
        )
        if (
            idle_native_passthrough and
            _is_primary_paint_active_event(event) and
            self._multi_locked_density_add_active(event)
        ):
            idle_native_passthrough = False
        if (
            idle_native_passthrough and
            _is_primary_paint_active_event(event) and
            not self.surface_lock and
            hasattr(event, "mouse_region_x") and
            hasattr(event, "mouse_region_y")
        ):
            self._update_hover_target(context, event, commit=False)
            if (
                self.preview_target is not None and
                not _target_match_for_system(self._current_system(), self.source_data, self.preview_target)
            ):
                idle_native_passthrough = False
        if idle_native_passthrough:
            if _is_primary_paint_event(event) and not self._event_is_in_world_paint_view(context, event):
                return {'PASS_THROUGH'}
            if (
                _is_primary_paint_active_event(event) and
                self._event_is_in_world_paint_view(context, event) and
                not self._locked_terrain_hit_from_event(context, event)
            ):
                self._primary_paint_button_down = False
                return {'RUNNING_MODAL'}
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._force_native_brush_visibility(context)
            if _is_primary_paint_active_event(event):
                self._primary_paint_button_down = True
                active_system = self._current_system()
                if active_system is not None:
                    self._schedule_native_stroke_stable_id_sync(
                        context,
                        active_system,
                        while_painting=True,
                    )
            elif _is_primary_paint_end_event(event):
                self._primary_paint_button_down = False
                active_system = self._current_system()
                if active_system is not None:
                    _mark_system_curve_cache_dirty(active_system)
                    self._schedule_native_stroke_stable_id_sync(
                        context,
                        active_system,
                        force_refresh=True,
                    )
            elif primary_released_by_event_history:
                active_system = self._current_system()
                if active_system is not None:
                    _mark_system_curve_cache_dirty(active_system)
                    self._schedule_native_stroke_stable_id_sync(
                        context,
                        active_system,
                        force_refresh=True,
                    )
            return {'PASS_THROUGH'}

        if (
            self._native_idle_session_deferred(event) and
            _is_passive_idle_passthrough_event(event) and
            not _is_primary_paint_event(event)
        ):
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            return {'PASS_THROUGH'}

        shift_state_changed = self._sync_modifier_key_state(event)
        density_right_delete_active = self._is_density_right_delete_active_event(event)
        density_right_delete_end = self._is_density_right_delete_end_event(event)
        density_right_delete_click = self._is_density_right_delete_click_event(event)
        preserve_idle_native_density = self._preserve_idle_native_density_session()
        density_erase_click = self._is_density_erase_click_event(event)
        temporary_shift_delete_click = self._is_temporary_shift_delete_click_event(event)
        native_passthrough_stroke = self._native_density_passthrough_active()
        shift_delete_relevant_event = (
            self.tool_id == WORLD_TOOL_DENSITY and
            (
                shift_state_changed or
                self._event_shift_active(event) or
                self._native_density_stroke_erase or
                density_erase_click or
                density_right_delete_active or
                density_right_delete_end
            ) and
            (
                event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFTMOUSE', 'RIGHTMOUSE', 'ACTIONMOUSE', 'SELECTMOUSE', 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} or
                _is_primary_paint_event(event)
            )
        )
        if shift_delete_relevant_event:
            _shift_delete_debug_log(
                "modal.relevant_event",
                context,
                self,
                event=event,
                force=shift_state_changed or _is_primary_paint_event(event),
                shift_state_changed=shift_state_changed,
                density_erase_click=density_erase_click,
                density_right_delete_active=density_right_delete_active,
                density_right_delete_end=density_right_delete_end,
                native_passthrough_stroke=native_passthrough_stroke,
                preserve_idle_native_density=preserve_idle_native_density,
                primary_down=self._primary_paint_button_down,
            )
        if (
            shift_state_changed or
            (
                self.tool_id == WORLD_TOOL_DENSITY and
                self._density_uses_native_ui() and
                not self.stroke_active and
                (
                    self._event_shift_active(event) or
                    self._native_density_stroke_erase
                )
            )
        ):
            self._sync_density_shift_delete_brush(context, event=event)
            preserve_idle_native_density = self._preserve_idle_native_density_session()
            native_passthrough_stroke = self._native_density_passthrough_active()
            _shift_delete_debug_log(
                "modal.after_shift_sync",
                context,
                self,
                event=event,
                force=shift_delete_relevant_event,
                native_passthrough_stroke=native_passthrough_stroke,
                preserve_idle_native_density=preserve_idle_native_density,
            )
        if density_right_delete_end and not self.stroke_active and preserve_idle_native_density:
            self._finish_density_right_delete_release(context)
            preserve_idle_native_density = self._preserve_idle_native_density_session()
            native_passthrough_stroke = self._native_density_passthrough_active()
            return {'RUNNING_MODAL'}
        if native_passthrough_stroke:
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._force_native_brush_visibility(context)
            if _is_primary_paint_end_event(event) or density_right_delete_end:
                if density_right_delete_end:
                    self._primary_paint_button_down = False
                    self._finish_native_passthrough_after_blender_event(event)
                    return {'PASS_THROUGH'}
                if self._native_density_stroke_erase:
                    self._primary_paint_button_down = False
                    self._finish_native_passthrough_after_blender_event(event)
                else:
                    self._primary_paint_button_down = False
                    self._finish_native_passthrough_after_blender_event(event)
                return {'PASS_THROUGH'}
            if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} and not self._primary_paint_button_down:
                self._end_paint_interaction(context, event)
                return {'PASS_THROUGH'}
            if _is_primary_paint_active_event(event) or density_right_delete_active or event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                native_proxy = self._continue_stroke(context, event)
                result = {'PASS_THROUGH'} if native_proxy else {'RUNNING_MODAL'}
                return result
        reserved_modal_key = False if bezier_tool_active else self._handle_reserved_modal_key(context, event)
        if reserved_modal_key:
            return {'RUNNING_MODAL'}
        adjust_confirm_release = self._is_adjust_confirm_release_event(context, event)
        if adjust_confirm_release:
            self._confirm_adjust_from_event(context, event)
            return {'RUNNING_MODAL'}
        shortcut_event_handled = False if bezier_tool_active else self._handle_shortcut_event(context, event)
        if shortcut_event_handled:
            return {'RUNNING_MODAL'}
        navigation_event = _is_viewport_navigation_event(event)
        sample_navigation_state = (
            self._viewport_navigation_active and
            not navigation_event and
            event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TIMER', 'WINDOW_ACTIVATE', 'WINDOW_ENTER'}
        )
        view_changed = self._sync_viewport_navigation_state(context) if sample_navigation_state else False
        if view_changed:
            self._viewport_navigation_active = True
            if not (self._density_uses_native_ui() and not self.stroke_active and not self.adjust_mode):
                _tag_redraw_view3d_areas(context)

        if (_is_primary_paint_end_event(event) or density_right_delete_end) and (
            self.stroke_active or (self._native_density_session_active and not preserve_idle_native_density)
        ):
            release_passthrough = self._native_density_passthrough_active()
            self._end_paint_interaction(context, event)
            if density_right_delete_end:
                self._finish_density_right_delete_release(context)
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'} if release_passthrough else {'RUNNING_MODAL'}

        if navigation_event:
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            if event.value == 'RELEASE':
                self._viewport_navigation_input_held = False
                if self._viewport_navigation_active:
                    self._end_viewport_navigation(context, event)
                return {'PASS_THROUGH'}
            self._viewport_navigation_input_held = _viewport_navigation_event_holds_input(event)
            self._viewport_navigation_active = True
            self._pause_idle_native_density_for_navigation(context)
            return {'PASS_THROUGH'}

        navigation_resume_event = (
            not self._viewport_navigation_input_held
            or event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}
        )
        if (
            sample_navigation_state and
            self._viewport_navigation_active and
            not view_changed and
            not navigation_event and
            navigation_resume_event
        ):
            refresh_event = event if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y") else None
            self._end_viewport_navigation(context, refresh_event)

        if self._viewport_navigation_active and event.value == 'RELEASE':
            self._viewport_navigation_input_held = False
            self._end_viewport_navigation(context, event)
            return {'PASS_THROUGH'}

        region_context = _event_region_context(context, event, self._invoke_area_pointer)
        hovered_area = region_context["area"]
        in_window_region = region_context["in_window_region"]
        was_in_window_region = getattr(self, "_last_region_in_window", False)
        self._last_region_in_window = bool(in_window_region)
        self._sync_native_os_cursor_for_region(context, region_context)
        if focus_gap_recovery and in_window_region:
            self._brush_cursor_focus_lost = True

        if hovered_area is None:
            if preserve_idle_native_density:
                return {'PASS_THROUGH'}
            if self.stroke_active or (self._native_density_session_active and not preserve_idle_native_density):
                self._end_paint_interaction(context, event)
            return {'PASS_THROUGH'}

        if hovered_area.type != 'VIEW_3D':
            if preserve_idle_native_density:
                return {'PASS_THROUGH'}
            if self.stroke_active or (self._native_density_session_active and not preserve_idle_native_density):
                self._end_paint_interaction(context, event)
            return {'PASS_THROUGH'}

        workspace_sync_skipped = (
            self._density_uses_native_ui() and
            self._viewport_navigation_active and
            not self.stroke_active and
            not self.adjust_mode and
            not self._native_curves_brush_passthrough_active() and
            not self._requested_native_tool_active() and
            not self._native_tool_override_active() and
            (
                _event_looks_like_keyboard_shortcut(event) or
                getattr(event, "type", "") in {'LEFT_ALT', 'RIGHT_ALT', 'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_SHIFT', 'RIGHT_SHIFT'}
            ) and
            not _world_paint_event_type_can_match_shortcut(context, event, self.toggle_key_type)
        )
        if not workspace_sync_skipped:
            if not self._sync_workspace_tool(context):
                self.finish_world_paint(context)
                return {'CANCELLED'}
        native_multi_locked_density_route = (
            self._multi_locked_density_add_active(event) and
            (
                _is_primary_paint_active_event(event) or
                self.stroke_active or
                self._primary_paint_button_down
            )
        )
        if self._native_curves_brush_passthrough_active() and native_multi_locked_density_route:
            self._leave_native_curves_brush_passthrough(context)
        if self._native_curves_brush_passthrough_active():
            if not in_window_region:
                return {'PASS_THROUGH'}
            if (
                _is_primary_paint_active_event(event) and
                not self._locked_terrain_hit_from_event(context, event)
            ):
                return {'RUNNING_MODAL'}
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._force_native_brush_visibility(context)
            if _is_primary_paint_active_event(event) or _is_primary_paint_end_event(event):
                active_system = self._current_system()
                context_active = getattr(context, "active_object", None)
                if _is_secret_paint_system(context_active):
                    active_system = context_active
                if active_system is not None:
                    self._track_touched_system(active_system)
                    self._primary_paint_button_down = _is_primary_paint_active_event(event)
                    self._schedule_native_stroke_stable_id_sync(
                        context,
                        active_system,
                        while_painting=self._primary_paint_button_down,
                        force_refresh=not self._primary_paint_button_down,
                    )
            return {'PASS_THROUGH'}

        cursor_refresh_due = (
            in_window_region and
            (
                getattr(self, "_brush_cursor_focus_lost", False) or
                not was_in_window_region
            )
        )
        if cursor_refresh_due:
            focus_recovery = bool(getattr(self, "_brush_cursor_focus_lost", False))
            if self.adjust_mode:
                if getattr(self, "_native_density_adjust_passthrough", False):
                    self._remove_draw_handlers()
                    self._restore_native_density_brush_overlay()
                    self._restore_native_density_brush_visibility(context)
                    self._force_native_brush_visibility(context, allow_adjust=True)
                else:
                    self._install_draw_handlers(context)
                _tag_redraw_view3d_areas(context)
            else:
                now = time.perf_counter()
                if self._native_density_session_active and not focus_recovery:
                    self._force_native_brush_visibility(context)
                    self._brush_cursor_focus_lost = False
                elif (
                    self._native_density_session_active and
                    focus_recovery and
                    now - float(getattr(self, "_last_brush_cursor_refresh_time", 0.0) or 0.0) <
                    WORLD_BRUSH_CURSOR_REENTRY_REFRESH_INTERVAL
                ):
                    self._force_native_brush_visibility(context)
                    self._brush_cursor_focus_lost = False
                else:
                    self._refresh_brush_cursor_after_view_reentry(
                        context,
                        event,
                        schedule=focus_recovery,
                        force_rebuild=focus_recovery or not was_in_window_region,
                    )
                    self._brush_cursor_focus_lost = False

        if region_context["ui_region"]:
            if preserve_idle_native_density:
                if not self.adjust_mode and _is_primary_paint_event(event):
                    self._handle_native_brush_ui_size_event(context, event)
                    _schedule_world_tool_sync()
                elif not self.adjust_mode:
                    self._handle_native_brush_ui_size_event(context, event)
                return {'PASS_THROUGH'}
            if self.stroke_active or (self._native_density_session_active and not preserve_idle_native_density):
                self._end_paint_interaction(context, event)
                return {'PASS_THROUGH'}
            if not self.adjust_mode:
                if _is_primary_paint_event(event):
                    _schedule_world_tool_sync()
                return {'PASS_THROUGH'}

        if not region_context["in_window_region"] and not self.adjust_mode:
            if preserve_idle_native_density:
                return {'PASS_THROUGH'}
            if self.stroke_active or (self._native_density_session_active and not preserve_idle_native_density):
                self._end_paint_interaction(context, event)
            return {'PASS_THROUGH'}

        if (
            context.area and
            context.area.type == 'VIEW_3D' and
            (
                not self._density_uses_native_ui() or
                self.adjust_mode or
                self.stroke_active or
                (not self._native_density_session_active and not self._viewport_navigation_active)
            )
        ):
            context.area.tag_redraw()

        if self.tool_id == WORLD_TOOL_BEZIER:
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._activate_bezier_curve_draw_tool(
                context,
                activate_draw_tool=False,
                configure_settings=False,
            )
            return {'PASS_THROUGH'}

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} and (
            self.stroke_active or self._native_density_session_active
        ) and not self._paint_stroke_button_down() and not self.adjust_mode:
            if not (
                self.stroke_active and
                self._active_density_stroke_mode == "native" and
                self._native_density_interaction_mode == "NATIVE_UI"
            ) and not preserve_idle_native_density:
                idle_native_cleanup = self._native_density_session_active and not self.stroke_active
                self._end_paint_interaction(context, event)
                return {'PASS_THROUGH'} if idle_native_cleanup else {'RUNNING_MODAL'}
            if preserve_idle_native_density and region_context["in_window_region"]:
                if not WORLD_KEEP_NATIVE_SESSION_WHILE_IDLE:
                    self._defer_idle_native_density_session(context)
                    return {'PASS_THROUGH'}
                self._ensure_idle_native_density_session(context, event=event)
                self._track_idle_native_density_mouse(context, event)
                return {'PASS_THROUGH'}
            if not (
                self.stroke_active and
                self._active_density_stroke_mode == "native" and
                self._native_density_interaction_mode == "NATIVE_UI"
            ):
                self._end_paint_interaction(context, event)
                return {'RUNNING_MODAL'}

        if self.adjust_mode and event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self._update_adjust(context, event)
            return {'RUNNING_MODAL'}

        if event.type == 'MIDDLEMOUSE':
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            return {'PASS_THROUGH'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE'}:
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            return {'PASS_THROUGH'}

        if (
            _is_primary_paint_active_event(event) or
            density_right_delete_active or
            density_right_delete_click or
            density_erase_click or
            temporary_shift_delete_click
        ) and not self.stroke_active:
            if not region_context["in_window_region"]:
                return {'PASS_THROUGH'}
            native_proxy = self._begin_stroke(context, event)
            if (density_erase_click or density_right_delete_click or temporary_shift_delete_click) and self.stroke_active:
                if native_proxy and self._native_density_stroke_erase:
                    self._finish_native_passthrough_after_blender_event(event)
                else:
                    self._finish_stroke(context, event)
            result = {'PASS_THROUGH'} if native_proxy else {'RUNNING_MODAL'}
            return result

        if _is_primary_paint_active_event(event) and self.stroke_active and self._active_density_stroke_mode == "native":
            if event.value == 'PRESS':
                self._end_paint_interaction(context, event)
                if not region_context["in_window_region"]:
                    return {'PASS_THROUGH'}
                native_proxy = self._begin_stroke(context, event)
                result = {'PASS_THROUGH'} if native_proxy else {'RUNNING_MODAL'}
                return result
            native_proxy = self._continue_stroke(context, event)
            result = {'PASS_THROUGH'} if native_proxy else {'RUNNING_MODAL'}
            return result

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            if self._viewport_navigation_active:
                self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
                return {'PASS_THROUGH'}
            if self.stroke_active:
                native_proxy = self._continue_stroke(context, event)
                result = {'PASS_THROUGH'} if native_proxy else {'RUNNING_MODAL'}
                return result
            if not region_context["in_window_region"]:
                return {'PASS_THROUGH'}
            if self._density_uses_native_ui() and not self._primary_paint_button_down:
                if self._surface_lock_waiting_for_target():
                    self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
                    return {'PASS_THROUGH'}
                if self._native_idle_session_deferred(event):
                    self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
                    return {'PASS_THROUGH'}
                self._ensure_idle_native_density_session(context, event=event)
                self._track_idle_native_density_mouse(context, event)
                return {'PASS_THROUGH'}
            self.hover_mouse_region = (event.mouse_region_x, event.mouse_region_y)
            self._update_hover_target(context, event, commit=False)
            if self._density_uses_native_ui():
                return {'PASS_THROUGH'}
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}


def _active_world_scale_targets(operator):
    active_system = bpy.data.objects.get(operator.active_system_name) if operator.active_system_name else None
    if active_system is None:
        return []
    if operator.surface_lock:
        return _same_source_systems(operator.source_data)
    return [active_system]


def _apply_world_scale(context, value):
    operator = _world_operator()
    if operator is None:
        return
    if operator._syncing_slider:
        return

    previous_value = max(operator.last_slider_value, 0.0001)
    ratio = value / previous_value
    targets = _active_world_scale_targets(operator)
    if operator.surface_lock:
        for system_obj in targets:
            _set_modifier_scale(system_obj, max(0.01, _modifier_scale_value(system_obj) * ratio))
    else:
        for system_obj in targets:
            _set_modifier_scale(system_obj, value)
    operator.last_slider_value = value
    if context.area:
        context.area.tag_redraw()


def _world_scale_update(self, context):
    _apply_world_scale(context, self.secret_paint_world_asset_scale)


def _world_brush_radius_update(self, context):
    operator = _world_operator()
    if operator is None or getattr(operator, "_syncing_brush_props", False):
        return
    next_radius_setting = max(0.05, self.secret_paint_world_brush_radius)
    old_setting = getattr(operator, "brush_radius_setting", 0.0)
    shared.secret_paint_brush_size_trace_log(
        "world.window_manager_brush_radius_update",
        context,
        operator,
        wm_value=self.secret_paint_world_brush_radius,
        next_radius_setting=next_radius_setting,
        old_setting=old_setting,
    )
    if abs(next_radius_setting - old_setting) < 0.0001:
        return
    stale_native_info = operator._stale_native_window_manager_radius_update_info(
        context,
        next_radius_setting,
    )
    if stale_native_info is not None:
        shared.secret_paint_brush_size_trace_log(
            "world.window_manager_brush_radius_update.stale_ignored",
            context,
            operator,
            wm_value=self.secret_paint_world_brush_radius,
            **stale_native_info,
        )
        operator._sync_brush_controls(context, force=True)
        _tag_redraw_view3d_areas(context)
        return
    operator.brush_radius_setting = next_radius_setting
    operator._sync_effective_brush_radius(context)
    operator._mark_deferred_brush_settings_dirty(
        radius=True,
        native_sync=True,
        context=context,
        schedule=True,
    )
    _tag_redraw_view3d_areas(context)


def _world_density_spacing_update_value(self, context, value):
    operator = _world_operator()
    if operator is None or getattr(operator, "_syncing_brush_props", False):
        return
    next_density_spacing = _density_spacing_value(value)
    if abs(next_density_spacing - getattr(operator, "density_spacing", 0.0)) < WORLD_DENSITY_SPACING_EPSILON:
        return
    operator.density_spacing = next_density_spacing
    operator._syncing_brush_props = True
    try:
        self.secret_paint_world_density_spacing = next_density_spacing
        if hasattr(self, "secret_paint_world_density_spacing_coarse"):
            self.secret_paint_world_density_spacing_coarse = next_density_spacing
    finally:
        operator._syncing_brush_props = False
    _native_brush_debug_log(
        "wm_density_slider.update",
        context,
        operator,
        force=True,
        new_density=operator.density_spacing,
    )
    operator._mark_deferred_brush_settings_dirty(
        density=True,
        native_sync=True,
        context=context,
        schedule=True,
    )
    _tag_redraw_view3d_areas(context)


def _world_density_spacing_update(self, context):
    _world_density_spacing_update_value(self, context, self.secret_paint_world_density_spacing)


def _world_density_spacing_coarse_update(self, context):
    _world_density_spacing_update_value(self, context, self.secret_paint_world_density_spacing_coarse)


def _world_brush_strength_update(self, context):
    operator = _world_operator()
    if operator is None or getattr(operator, "_syncing_brush_props", False):
        return
    operator._set_active_brush_strength(context, self.secret_paint_world_brush_strength)


def _draw_world_falloff_shape_controls(layout, context, operator):
    brush = operator._active_falloff_brush(context, ensure=False)
    if brush is None:
        return
    falloff_shape = getattr(brush, "falloff_shape", "")
    if falloff_shape not in {'SPHERE', 'PROJECTED'}:
        return
    falloff_row = layout.row(align=True)
    sphere_op = falloff_row.operator(
        "secret.world_paint_set_falloff_shape",
        text="Sphere",
        depress=falloff_shape == 'SPHERE',
    )
    sphere_op.falloff_shape = 'SPHERE'
    projected_op = falloff_row.operator(
        "secret.world_paint_set_falloff_shape",
        text="Projected",
        depress=falloff_shape == 'PROJECTED',
    )
    projected_op.falloff_shape = 'PROJECTED'


def _draw_secret_paint_mode_header(self, context):
    operator = _world_operator()
    if operator is None:
        original_draw = _WORLD_STATE.get("header_draw_original")
        if original_draw is not None:
            original_draw(self, context)
        return

    layout = self.layout
    original_draw = _WORLD_STATE.get("header_draw_original")
    if (
        (
            operator._native_curves_brush_passthrough_active()
            or operator._active_brush_requests_native_passthrough(context)
        )
        and original_draw is not None
    ):
        original_draw(self, context)
        return
    if getattr(operator, "tool_id", "") == WORLD_TOOL_BEZIER and original_draw is not None:
        try:
            original_draw(self, context)
            layout.separator(factor=0.8)
        except Exception:
            layout.row(align=True).template_header()
    else:
        layout.row(align=True).template_header()

    badge_row = layout.row(align=True)
    badge_row.scale_y = 1.15
    op = badge_row.operator(
        "secret.world_paint_set_tool",
        text="Secret Paint",
        icon='BRUSH_DATA',
        depress=True,
    )
    op.tool_id = operator.tool_id

    layout.separator(factor=0.8)
    flag_row = layout.row(align=True)
    if operator._density_uses_native_ui():
        operator._sync_interpolate_from_native_brush(context)
    for flag_id, flag_label, _description in WORLD_FLAG_ITEMS:
        if not _world_flag_available(flag_id):
            continue
        op = flag_row.operator(
            WORLD_FLAG_OPERATOR_IDS.get(flag_id, "secret.world_paint_toggle_flag"),
            text=_world_flag_button_label(flag_id, flag_label),
            depress=_world_flag_is_enabled(operator, flag_id),
        )
        if hasattr(op, "flag_id"):
            op.flag_id = flag_id

    layout.separator(factor=0.8)
    prop_row = layout.row(align=True)
    prop_row.prop(context.window_manager, "secret_paint_world_brush_radius", text="Size (F)", slider=True)
    if operator.tool_id == WORLD_TOOL_DENSITY:
        density_prop = (
            "secret_paint_world_density_spacing_coarse"
            if operator.density_spacing >= 1.0 and hasattr(context.window_manager, "secret_paint_world_density_spacing_coarse")
            else "secret_paint_world_density_spacing"
        )
        prop_row.prop(context.window_manager, density_prop, text="Density (Alt+F)", slider=True)
    elif operator._tool_uses_brush_strength_adjust():
        operator._sync_brush_strength_from_native_brush(context, ensure=False)
        prop_row.prop(context.window_manager, "secret_paint_world_brush_strength", text="Strength (Alt+F)", slider=True)
    prop_row.separator(factor=0.8)
    _draw_world_falloff_shape_controls(prop_row, context, operator)

    layout.separator(factor=0.8)
    action_row = layout.row(align=True)
    action_row.operator("secret.world_paint_realize_selection", text="Realize")


def _draw_secret_paint_mode_tool_header(self, context):
    operator = _world_operator()
    if operator is None:
        original_draw = _WORLD_STATE.get("tool_header_draw_original")
        if original_draw is not None:
            original_draw(self, context)
        return

    layout = self.layout
    if (
        operator._native_curves_brush_passthrough_active()
        or operator._active_brush_requests_native_passthrough(context)
    ):
        original_draw = _WORLD_STATE.get("tool_header_draw_original")
        if original_draw is not None:
            original_draw(self, context)
        return
    if operator.tool_id == WORLD_TOOL_BEZIER:
        original_draw = _WORLD_STATE.get("tool_header_draw_original")
        if original_draw is not None:
            try:
                original_draw(self, context)
                layout.separator(factor=0.8)
            except Exception:
                pass
        _draw_world_bezier_curve_topbar_controls(layout, context)
        return

    source_name, source_icon = _world_source_label_info(operator.source_data)

    row = layout.row(align=True)
    row.label(text="Object:")
    row.label(text=source_name, icon=source_icon)
    row.separator(factor=1.2)
    row.label(text="Surface:")
    row.label(text=_world_surface_name(operator))
    if operator.tool_id == WORLD_TOOL_DENSITY:
        row.separator(factor=1.2)
        row.label(text="Density: Native Brush")
    elif operator.tool_id == WORLD_TOOL_DELETE:
        row.separator(factor=1.2)
        row.label(text="Delete: Native Brush")


class SECRET_PT_world_paint_bezier_settings(bpy.types.Panel):
    bl_label = "Bezier Settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 18

    @classmethod
    def poll(cls, context):
        operator = _world_operator()
        return operator is not None and operator.tool_id == WORLD_TOOL_BEZIER

    def draw(self, context):
        _draw_world_bezier_curve_settings(self.layout, context)


class secret_world_paint_set_bezier_depth_mode(bpy.types.Operator):
    bl_idname = "secret.world_paint_set_bezier_depth_mode"
    bl_label = "Set Bezier Depth Mode"

    depth_mode: bpy.props.EnumProperty(
        items=(
            ("CURSOR", "Cursor", "Draw Bezier curves at the 3D cursor depth"),
            ("SURFACE", "Surface", "Draw Bezier curves on the hovered surface"),
        )
    )

    @classmethod
    def poll(cls, context):
        operator = _world_operator()
        return operator is not None and operator.tool_id == WORLD_TOOL_BEZIER

    def execute(self, context):
        curve_settings = _tool_settings_curve_paint(context)
        if curve_settings is None:
            return {'CANCELLED'}
        try:
            curve_settings.depth_mode = self.depth_mode
        except Exception:
            return {'CANCELLED'}
        _tag_redraw_view3d_areas(context)
        return {'FINISHED'}


def _begin_world_ui(operator, context):
    if _WORLD_STATE["ui_hijacked"]:
        return

    operator._invoke_area_pointer = context.area.as_pointer() if context.area else 0
    operator._saved_workspace_tool_id = ""
    operator._saved_workspace_tool_mode = context.mode if context.mode else ""
    operator._saved_view3d_state = {}

    if context.area and context.area.type == 'VIEW_3D' and context.space_data is not None:
        space = context.space_data
        operator._saved_view3d_state = {
            "show_region_header": getattr(space, "show_region_header", True),
            "show_region_toolbar": getattr(space, "show_region_toolbar", True),
            "show_region_tool_header": getattr(space, "show_region_tool_header", True),
            "show_text": getattr(space.overlay, "show_text", True),
            "show_stats": getattr(space.overlay, "show_stats", True),
        }
        space.show_region_header = True
        space.show_region_toolbar = True
        space.show_region_tool_header = True
        space.overlay.show_text = False
        space.overlay.show_stats = False
    if getattr(context, "mode", "") == 'SCULPT_CURVES' or not operator._density_uses_native_ui():
        shared.secret_paint_disable_sculpt_curves_cage(context)
        operator._world_ui_cage_hidden = True

    operator._saved_workspace_tool_id = ""

    _WORLD_STATE["header_draw_original"] = bpy.types.VIEW3D_HT_header.draw
    bpy.types.VIEW3D_HT_header.draw = _draw_secret_paint_mode_header
    _WORLD_STATE["tool_header_draw_original"] = bpy.types.VIEW3D_HT_tool_header.draw
    bpy.types.VIEW3D_HT_tool_header.draw = _draw_secret_paint_mode_tool_header
    _hijack_world_toolbar()
    _set_world_keymap_conflicts_enabled(context, False)
    _remove_stale_shift_delete_native_keymaps(context)
    _WORLD_STATE["ui_hijacked"] = True
    if operator._density_uses_native_ui():
        _tag_view3d_tool_ui_regions(context, area_pointer=operator._invoke_area_pointer)
    else:
        _tag_redraw_view3d_areas(context)


def _restore_world_ui(operator, context):
    if not _WORLD_STATE["ui_hijacked"]:
        return

    original_draw = _WORLD_STATE.get("header_draw_original")
    if original_draw is not None:
        bpy.types.VIEW3D_HT_header.draw = original_draw
    _WORLD_STATE["header_draw_original"] = None
    original_tool_header_draw = _WORLD_STATE.get("tool_header_draw_original")
    if original_tool_header_draw is not None:
        bpy.types.VIEW3D_HT_tool_header.draw = original_tool_header_draw
    _WORLD_STATE["tool_header_draw_original"] = None
    _restore_world_toolbar()

    area, _region, space = _view3d_area_data(context, getattr(operator, "_invoke_area_pointer", 0))
    saved_state = getattr(operator, "_saved_view3d_state", {}) or {}
    if area is not None and space is not None and saved_state:
        try:
            space.show_region_header = saved_state["show_region_header"]
            space.show_region_toolbar = saved_state["show_region_toolbar"]
            space.show_region_tool_header = saved_state["show_region_tool_header"]
            space.overlay.show_text = saved_state["show_text"]
            space.overlay.show_stats = saved_state["show_stats"]
        except Exception:
            pass

    _set_world_keymap_conflicts_enabled(context, True)
    _set_world_paint_shortcuts_enabled(context, True)
    _WORLD_STATE["ui_hijacked"] = False
    _tag_redraw_view3d_areas(context)


def _execute_world_tool_choice(context, tool_id):
    operator = _world_operator()
    if operator is None:
        return {'CANCELLED'}
    if tool_id == WORLD_TOOL_BEZIER:
        return {'FINISHED'} if operator._handoff_to_bezier_curve_edit(context, force_new_curve=True) else {'CANCELLED'}
    operator._set_tool(context, tool_id, sync_workspace=True)
    return {'FINISHED'}


class _secret_world_paint_fixed_tool_operator:
    world_tool_id = ""

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    @classmethod
    def description(cls, context, properties):
        return _world_tool_spec(cls.world_tool_id).get("description", cls.bl_label)

    def execute(self, context):
        return _execute_world_tool_choice(context, type(self).world_tool_id)


class secret_world_paint_tool_density(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_density"
    bl_label = "Density"
    world_tool_id = WORLD_TOOL_DENSITY


class secret_world_paint_tool_delete(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_delete"
    bl_label = "Delete"
    world_tool_id = WORLD_TOOL_DELETE


class secret_world_paint_tool_single(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_single"
    bl_label = "Single"
    world_tool_id = WORLD_TOOL_SINGLE


class secret_world_paint_tool_bezier(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_bezier"
    bl_label = "Bezier"
    world_tool_id = WORLD_TOOL_BEZIER


class secret_world_paint_tool_slide(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_slide"
    bl_label = "Slide"
    world_tool_id = WORLD_TOOL_SLIDE


class secret_world_paint_tool_select(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_select"
    bl_label = "Select"
    world_tool_id = WORLD_TOOL_SELECT


class secret_world_paint_tool_rotation(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_rotation"
    bl_label = "Rotation"
    world_tool_id = WORLD_TOOL_COMB


class secret_world_paint_tool_scale(_secret_world_paint_fixed_tool_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_tool_scale"
    bl_label = "Scale"
    world_tool_id = WORLD_TOOL_SCALE


def _world_flag_label(flag_id):
    for current_flag_id, label, _description in WORLD_FLAG_ITEMS:
        if current_flag_id == flag_id:
            return label
    return flag_id


def _world_flag_description(flag_id, fallback="Toggle World Paint Flag"):
    for current_flag_id, _label, description in WORLD_FLAG_ITEMS:
        if current_flag_id == flag_id:
            return description
    return fallback


def _execute_world_flag_toggle(context, flag_id):
    operator = _world_operator()
    if operator is None:
        return {'CANCELLED'}
    if not _world_flag_available(flag_id):
        return {'CANCELLED'}
    operator._toggle_flag(context, flag_id)
    return {'FINISHED'}


class _secret_world_paint_fixed_flag_operator:
    world_flag_id = ""

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    @classmethod
    def description(cls, context, properties):
        return _world_flag_description(cls.world_flag_id, cls.bl_label)

    def execute(self, context):
        return _execute_world_flag_toggle(context, type(self).world_flag_id)


class secret_world_paint_toggle_lock_surface(_secret_world_paint_fixed_flag_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_lock_surface"
    bl_label = "Lock Terrain"
    world_flag_id = "LOCK_SURFACE"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if is_world_paint_running():
            return _execute_world_flag_toggle(context, type(self).world_flag_id)
        return _toggle_surface_lock_without_running_operator(context)

    def invoke(self, context, event):
        if bool(getattr(event, "shift", False)):
            return _select_world_paint_panel_target(context)
        return self.execute(context)


class secret_world_paint_toggle_target_surface(_secret_world_paint_fixed_flag_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_target_surface"
    bl_label = "Target Surface"
    world_flag_id = "TARGET_SURFACE"


class secret_world_paint_toggle_wire_bounds_surfaces(_secret_world_paint_fixed_flag_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_wire_bounds_surfaces"
    bl_label = "Wire"
    world_flag_id = "ALLOW_WIRE_BOUNDS_SURFACES"


class secret_world_paint_toggle_interpolate(_secret_world_paint_fixed_flag_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_interpolate"
    bl_label = "Interpolate"
    world_flag_id = "INTERPOLATE"


class secret_world_paint_toggle_random_z(_secret_world_paint_fixed_flag_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_random_z"
    bl_label = "Random Z"
    world_flag_id = "RANDOM_Z"


class secret_world_paint_toggle_align_to_normal(_secret_world_paint_fixed_flag_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_align_to_normal"
    bl_label = "Align To Normal"
    world_flag_id = "ALIGN_TO_NORMAL"


def _execute_world_adjust(context, adjust_mode, event=None, *, confirm_on_release=False):
    if adjust_mode == "SIZE" and not WORLD_SIZE_ADJUST_SHORTCUT_ENABLED:
        return {'PASS_THROUGH'}
    operator = _world_operator()
    if operator is None:
        return {'CANCELLED'}
    return {'FINISHED'} if operator._begin_adjust(
        context,
        adjust_mode,
        event=event,
        confirm_on_release=confirm_on_release,
    ) else {'CANCELLED'}


class _secret_world_paint_fixed_adjust_operator:
    world_adjust_mode = ""

    @classmethod
    def poll(cls, context):
        if cls.world_adjust_mode == "SIZE" and not WORLD_SIZE_ADJUST_SHORTCUT_ENABLED:
            return False
        return is_world_paint_running()

    def invoke(self, context, event):
        return _execute_world_adjust(
            context,
            type(self).world_adjust_mode,
            event=event,
            confirm_on_release=getattr(self, "confirm_on_release", False),
        )

    def execute(self, context):
        return _execute_world_adjust(
            context,
            type(self).world_adjust_mode,
            confirm_on_release=getattr(self, "confirm_on_release", False),
        )


class secret_world_paint_adjust_size(_secret_world_paint_fixed_adjust_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_adjust_size"
    bl_label = "Adjust Brush Size"
    world_adjust_mode = "SIZE"

    confirm_on_release: bpy.props.BoolProperty(
        name="Confirm on Release",
        description="Confirm the brush-size adjustment when the F shortcut is released",
        default=False,
    )


class secret_world_paint_adjust_strength(_secret_world_paint_fixed_adjust_operator, bpy.types.Operator):
    bl_idname = "secret.world_paint_adjust_strength"
    bl_label = "Adjust Brush Strength"
    world_adjust_mode = "STRENGTH"

    confirm_on_release: bpy.props.BoolProperty(
        name="Confirm on Release",
        description="Confirm the density adjustment when the Alt+F shortcut is released",
        default=False,
    )


class secret_world_paint_set_tool(bpy.types.Operator):
    bl_idname = "secret.world_paint_set_tool"
    bl_label = "Set World Paint Tool"

    tool_id: bpy.props.EnumProperty(items=WORLD_TOOL_ITEMS)

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    @classmethod
    def description(cls, context, properties):
        return _world_tool_spec(getattr(properties, "tool_id", "")).get("description", cls.bl_label)

    def execute(self, context):
        return _execute_world_tool_choice(context, self.tool_id)


class secret_world_paint_toggle_flag(bpy.types.Operator):
    bl_idname = "secret.world_paint_toggle_flag"
    bl_label = "Toggle World Paint Flag"

    flag_id: bpy.props.EnumProperty(items=WORLD_FLAG_ITEMS)

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    @classmethod
    def description(cls, context, properties):
        return _world_flag_description(getattr(properties, "flag_id", ""), cls.bl_label)

    def execute(self, context):
        return _execute_world_flag_toggle(context, self.flag_id)


class secret_world_paint_set_falloff_shape(bpy.types.Operator):
    bl_idname = "secret.world_paint_set_falloff_shape"
    bl_label = "Set Brush Falloff Shape"

    falloff_shape: bpy.props.EnumProperty(
        items=(
            ("SPHERE", "Sphere", "Use spherical brush falloff"),
            ("PROJECTED", "Projected", "Use projected brush falloff"),
        )
    )

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    def execute(self, context):
        operator = _world_operator()
        if operator is None:
            return {'CANCELLED'}
        return {'FINISHED'} if operator._set_active_falloff_shape(context, self.falloff_shape) else {'CANCELLED'}


class secret_world_paint_begin_adjust(bpy.types.Operator):
    bl_idname = "secret.world_paint_begin_adjust"
    bl_label = "Begin World Paint Adjust"

    adjust_mode: bpy.props.EnumProperty(
        items=(
            ("SIZE", "Size", "Adjust brush size"),
            ("STRENGTH", "Strength", "Adjust brush strength or density spacing"),
        )
    )

    confirm_on_release: bpy.props.BoolProperty(
        name="Confirm on Release",
        description="Confirm the brush adjustment when the shortcut is released",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    def invoke(self, context, event):
        return _execute_world_adjust(
            context,
            self.adjust_mode,
            event=event,
            confirm_on_release=getattr(self, "confirm_on_release", False),
        )

    def execute(self, context):
        return _execute_world_adjust(
            context,
            self.adjust_mode,
            confirm_on_release=getattr(self, "confirm_on_release", False),
        )


class secret_world_paint_pick_source(bpy.types.Operator):
    bl_idname = "secret.world_paint_pick_source"
    bl_label = "Pick World Paint Source"

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    def execute(self, context):
        operator = _world_operator()
        if operator is None:
            return {'CANCELLED'}
        if operator.stroke_active:
            operator._finish_stroke(context, None)
        return {'FINISHED'} if operator._pick_source_under_brush(context) else {'CANCELLED'}


class secret_world_paint_realize_selection(bpy.types.Operator):
    bl_idname = "secret.world_paint_realize_selection"
    bl_label = "Realize Selected World Paint"

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    def execute(self, context):
        operator = _world_operator()
        if operator is None:
            return {'CANCELLED'}
        active_system = bpy.data.objects.get(operator.active_system_name) if operator.active_system_name else None
        if active_system is None:
            return {'CANCELLED'}
        for obj in context.selected_objects:
            obj.select_set(False)
        active_system.select_set(True)
        context.view_layer.objects.active = active_system
        bpy.ops.secret.realize_instances()
        return {'FINISHED'}


class secret_world_paint_exit(bpy.types.Operator):
    bl_idname = "secret.world_paint_exit"
    bl_label = "Exit Secret Paint Mode"

    @classmethod
    def poll(cls, context):
        return is_world_paint_running()

    def execute(self, context):
        operator = _world_operator()
        if operator is None:
            return {'CANCELLED'}
        operator.finish_world_paint(context)
        return {'FINISHED'}


def register_secret_paint_world_paint_runtime():
    try:
        _sanitize_sculpt_curves_tool_before_world_exit(bpy.context)
    except Exception:
        pass
    try:
        _remove_world_right_delete_brush_keymap(bpy.context)
    except Exception:
        pass
    if not hasattr(bpy.types.WindowManager, "secret_paint_world_asset_scale"):
        bpy.types.WindowManager.secret_paint_world_asset_scale = bpy.props.FloatProperty(
            name="Asset Scale",
            default=1.0,
            min=0.01,
            soft_max=10.0,
            update=_world_scale_update,
        )
    if not hasattr(bpy.types.WindowManager, "secret_paint_world_brush_radius"):
        bpy.types.WindowManager.secret_paint_world_brush_radius = bpy.props.FloatProperty(
            name="Brush Radius",
            default=0.5,
            min=0.05,
            soft_max=10.0,
            update=_world_brush_radius_update,
        )
    if not hasattr(bpy.types.WindowManager, "secret_paint_world_density_spacing"):
        bpy.types.WindowManager.secret_paint_world_density_spacing = bpy.props.FloatProperty(
            name="Density",
            default=0.1,
            min=0.0,
            soft_min=0.0,
            soft_max=2.0,
            precision=6,
            update=_world_density_spacing_update,
        )
    if not hasattr(bpy.types.WindowManager, "secret_paint_world_density_spacing_coarse"):
        bpy.types.WindowManager.secret_paint_world_density_spacing_coarse = bpy.props.FloatProperty(
            name="Density",
            default=0.1,
            min=0.0,
            soft_min=0.0,
            soft_max=10.0,
            precision=1,
            update=_world_density_spacing_coarse_update,
        )
    if not hasattr(bpy.types.WindowManager, "secret_paint_world_brush_strength"):
        bpy.types.WindowManager.secret_paint_world_brush_strength = bpy.props.FloatProperty(
            name="Strength",
            default=1.0,
            min=0.0,
            max=1.0,
            soft_min=0.0,
            soft_max=1.0,
            precision=3,
            update=_world_brush_strength_update,
        )
    _remove_stable_ids_load_handlers()
    if _stable_ids_on_depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_stable_ids_on_depsgraph_update_post)
    _WORLD_STATE["runtime_registered"] = True


def unregister_secret_paint_world_paint_runtime():
    operator = _world_operator()
    if operator is not None:
        try:
            operator._running = False
            operator._remove_draw_handlers()
            operator._restore_selection(bpy.context)
            _restore_world_ui(operator, bpy.context)
            shared.secret_paint_enable_sculpt_curves_cage(bpy.context)
        except ReferenceError:
            pass
    _WORLD_STATE["operator"] = None
    _remove_stable_ids_load_handlers()
    if _stable_ids_on_depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_stable_ids_on_depsgraph_update_post)
    if _WORLD_STATE["ui_hijacked"]:
        dummy_operator = operator if operator is not None else type("SecretPaintDummy", (), {
            "_invoke_area_pointer": 0,
            "_saved_workspace_tool_id": "",
            "_saved_workspace_tool_mode": "",
            "_saved_view3d_state": {},
        })()
        _restore_world_ui(dummy_operator, bpy.context)
    try:
        _sanitize_sculpt_curves_tool_before_world_exit(bpy.context)
    except Exception:
        pass
    try:
        _remove_world_right_delete_brush_keymap(bpy.context)
    except Exception:
        pass
    shared.secret_paint_enable_sculpt_curves_cage(bpy.context)
    _WORLD_STATE["runtime_registered"] = False
    if hasattr(bpy.types.WindowManager, "secret_paint_world_asset_scale"):
        del bpy.types.WindowManager.secret_paint_world_asset_scale
    if hasattr(bpy.types.WindowManager, "secret_paint_world_brush_radius"):
        del bpy.types.WindowManager.secret_paint_world_brush_radius
    if hasattr(bpy.types.WindowManager, "secret_paint_world_density_spacing"):
        del bpy.types.WindowManager.secret_paint_world_density_spacing
    if hasattr(bpy.types.WindowManager, "secret_paint_world_density_spacing_coarse"):
        del bpy.types.WindowManager.secret_paint_world_density_spacing_coarse
    if hasattr(bpy.types.WindowManager, "secret_paint_world_brush_strength"):
        del bpy.types.WindowManager.secret_paint_world_brush_strength
