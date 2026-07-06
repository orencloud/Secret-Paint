"""Blender UI integrations for the addon updater.

Implements draw calls, popups, and operators that use the addon_updater.
"""

import os
import json
import traceback

import bpy
from bpy.app.handlers import persistent
try:
    try:
        from .addon_updater import Updater as updater
    except Exception:
        from addon_updater import Updater as updater
except Exception as e:
    print("ERROR INITIALIZING UPDATER")
    print(str(e))
    traceback.print_exc()

    class SingletonUpdaterNone(object):
        """Fake, bare minimum fields and functions for the updater object."""

        def __init__(self):
            self.invalid_updater = True  # Used to distinguish bad install.

            self.addon = None
            self.verbose = False
            self.use_print_traces = True
            self.error = None
            self.error_msg = None
            self.async_checking = None

        def clear_state(self):
            self.addon = None
            self.verbose = False
            self.invalid_updater = True
            self.error = None
            self.error_msg = None
            self.async_checking = None

        def run_update(self, force, callback, clean):
            pass

        def check_for_update(self, now):
            pass

    updater = SingletonUpdaterNone()
    updater.error = "Error initializing updater module"
    updater.error_msg = str(e)
updater.addon = "secret_paint"
def make_annotations(cls):
    """Add annotation attribute to fields to avoid Blender 2.8+ warnings"""
    if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
        return cls
    if bpy.app.version < (2, 93, 0):
        bl_props = {k: v for k, v in cls.__dict__.items()
                    if isinstance(v, tuple)}
    else:
        bl_props = {k: v for k, v in cls.__dict__.items()
                    if isinstance(v, bpy.props._PropertyDeferred)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)
    return cls


def layout_split(layout, factor=0.0, align=False):
    """Intermediate method for pre and post blender 2.8 split UI function"""
    if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
        return layout.split(percentage=factor, align=align)
    return layout.split(factor=factor, align=align)


def get_user_preferences(context=None):
    """Intermediate method for pre and post blender 2.8 grabbing preferences"""
    if not context:
        context = bpy.context
    prefs = None
    if hasattr(context, "user_preferences"):
        prefs = context.user_preferences.addons.get(__package__, None)
    elif hasattr(context, "preferences"):
        prefs = context.preferences.addons.get(__package__, None)
    if prefs:
        return prefs.preferences
    return None


def online_access_disabled():
    return hasattr(bpy.app, "online_access") and not bpy.app.online_access


def online_access_disabled_message():
    return ("Blender online access is disabled. Enable Online Access in "
            "Blender preferences to check for updates.")
class AddonUpdaterInstallPopup(bpy.types.Operator):
    """Check and install update if available"""
    bl_label = "Update {x} addon".format(x=updater.addon)
    bl_idname = updater.addon + ".updater_install_popup"
    bl_description = "Popup to check and display current updates available"
    bl_options = {'REGISTER', 'INTERNAL'}
    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description=("If enabled, completely clear the addon's folder before "
                     "installing new update, creating a fresh install"),
        default=False,
        options={'HIDDEN'}
    )

    ignore_enum = bpy.props.EnumProperty(
        name="Process update",
        description="Decide to install, ignore, or defer new addon update",
        items=[
            ("install", "Update Now", "Install update now"),
            ("ignore", "Ignore", "Ignore this update to prevent future popups"),
            ("defer", "Defer", "Defer choice till next blender session")
        ],
        options={'HIDDEN'}
    )

    def check(self, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if updater.invalid_updater:
            layout.label(text="Updater module error")
            return
        elif updater.update_ready:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Update {} ready!".format(updater.update_version),
                      icon="LOOP_FORWARDS")
            col.label(text="Choose 'Update Now' & press OK to install, ",
                      icon="BLANK1")
            col.label(text="or click outside window to defer", icon="BLANK1")
            row = col.row()
            row.prop(self, "ignore_enum", expand=True)
            col.split()
        elif not updater.update_ready:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="No updates available")
            col.label(text="Press okay to dismiss dialog")
        else:
            layout.label(text="Check for update now?")
    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}

        if online_access_disabled() and not updater.manual_only:
            self.report({'WARNING'}, online_access_disabled_message())
            return {'CANCELLED'}

        if updater.manual_only:
            bpy.ops.wm.url_open(url=updater.website)
        elif updater.update_ready:
            if self.ignore_enum == 'defer':
                return {'FINISHED'}
            elif self.ignore_enum == 'ignore':
                updater.ignore_update()
                return {'FINISHED'}

            res = updater.run_update(force=False,
                                     callback=post_update_callback,
                                     clean=self.clean_install)
            if updater.verbose:
                if res == 0:
                    print("Updater returned successful")
                else:
                    print("Updater returned {}, error occurred".format(res))
        elif updater.update_ready is None:
            _ = updater.check_for_update(now=True)
            atr = AddonUpdaterInstallPopup.bl_idname.split(".")
            getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        else:
            updater.print_verbose("Doing nothing, not ready for update")
        return {'FINISHED'}
class AddonUpdaterCheckNow(bpy.types.Operator):
    bl_label = "Check now for " + updater.addon + " update"
    bl_idname = updater.addon + ".updater_check_now"
    bl_description = "Check now for an update to the {} addon".format(
        updater.addon)
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}

        if online_access_disabled():
            self.report({'WARNING'}, online_access_disabled_message())
            return {'CANCELLED'}

        if updater.async_checking and updater.error is None:
            return {'CANCELLED'}
        settings = get_user_preferences(context)
        if not settings:
            updater.print_verbose(
                "Could not get {} preferences, update check skipped".format(
                    __package__))
            return {'CANCELLED'}

        updater.set_check_interval(
            enabled=settings.auto_check_update,
            months=settings.updater_interval_months,
            days=settings.updater_interval_days,
            hours=settings.updater_interval_hours,
            minutes=settings.updater_interval_minutes)
        updater.check_for_update_now(ui_refresh)

        return {'FINISHED'}


class AddonUpdaterUpdateNow(bpy.types.Operator):
    bl_label = "Update " + updater.addon + " addon now"
    bl_idname = updater.addon + ".updater_update_now"
    bl_description = "Update to the latest version of the {x} addon".format(
        x=updater.addon)
    bl_options = {'REGISTER', 'INTERNAL'}
    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description=("If enabled, completely clear the addon's folder before "
                     "installing new update, creating a fresh install"),
        default=False,
        options={'HIDDEN'}
    )

    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}

        if updater.manual_only:
            bpy.ops.wm.url_open(url=updater.website)
            return {'FINISHED'}
        if online_access_disabled():
            self.report({'WARNING'}, online_access_disabled_message())
            return {'CANCELLED'}
        if updater.update_ready:
            try:
                res = updater.run_update(force=False,
                                         callback=post_update_callback,
                                         clean=self.clean_install)
                if updater.verbose:
                    if res == 0:
                        print("Updater returned successful")
                    else:
                        print("Updater error response: {}".format(res))
            except Exception as expt:
                updater._error = "Error trying to run update"
                updater._error_msg = str(expt)
                updater.print_trace()
                atr = AddonUpdaterInstallManually.bl_idname.split(".")
                getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        elif updater.update_ready is None:
            (update_ready, version, link) = updater.check_for_update(now=True)
            atr = AddonUpdaterInstallPopup.bl_idname.split(".")
            getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')

        elif not updater.update_ready:
            self.report({'INFO'}, "Nothing to update")
            return {'CANCELLED'}
        else:
            self.report(
                {'ERROR'}, "Encountered a problem while trying to update")
            return {'CANCELLED'}

        return {'FINISHED'}


class AddonUpdaterUpdateTarget(bpy.types.Operator):
    bl_label = updater.addon + " version target"
    bl_idname = updater.addon + ".updater_update_target"
    bl_description = "Install a targeted version of the {x} addon".format(
        x=updater.addon)
    bl_options = {'REGISTER', 'INTERNAL'}

    def target_version(self, context):
        if updater.invalid_updater:
            ret = []

        ret = []
        i = 0
        for tag in updater.tags:
            ret.append((tag, tag, "Select to install " + tag))
            i += 1
        return ret

    target = bpy.props.EnumProperty(
        name="Target version to install",
        description="Select the version to install",
        items=target_version
    )
    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description=("If enabled, completely clear the addon's folder before "
                     "installing new update, creating a fresh install"),
        default=False,
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        if updater.invalid_updater:
            return False
        if online_access_disabled():
            return False
        return updater.update_ready is not None and len(updater.tags) > 0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if updater.invalid_updater:
            layout.label(text="Updater error")
            return
        split = layout_split(layout, factor=0.5)
        sub_col = split.column()
        sub_col.label(text="Select install version")
        sub_col = split.column()
        sub_col.prop(self, "target", text="")

    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}
        if online_access_disabled():
            self.report({'WARNING'}, online_access_disabled_message())
            return {'CANCELLED'}

        res = updater.run_update(
            force=False,
            revert_tag=self.target,
            callback=post_update_callback,
            clean=self.clean_install)
        if res == 0:
            updater.print_verbose("Updater returned successful")
        else:
            updater.print_verbose(
                "Updater returned {}, , error occurred".format(res))
            return {'CANCELLED'}

        return {'FINISHED'}


class AddonUpdaterInstallManually(bpy.types.Operator):
    """As a fallback, direct the user to download the addon manually"""
    bl_label = "Install update manually"
    bl_idname = updater.addon + ".updater_install_manually"
    bl_description = "Proceed to manually install update"
    bl_options = {'REGISTER', 'INTERNAL'}

    error = bpy.props.StringProperty(
        name="Error Occurred",
        default="",
        options={'HIDDEN'}
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)

    def draw(self, context):
        layout = self.layout

        if updater.invalid_updater:
            layout.label(text="Updater error")
            return
        if self.error != "":
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="There was an issue trying to auto-install",
                      icon="ERROR")
            col.label(text="Press the download button below and install",
                      icon="BLANK1")
            col.label(text="the zip file like a normal addon.", icon="BLANK1")
        else:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Install the addon manually")
            col.label(text="Press the download button below and install")
            col.label(text="the zip file like a normal addon.")
        row = layout.row()

        if updater.update_link is not None:
            row.operator(
                "wm.url_open",
                text="Direct download").url = updater.update_link
        else:
            row.operator(
                "wm.url_open",
                text="(failed to retrieve direct download)")
            row.enabled = False

            if updater.website is not None:
                row = layout.row()
                ops = row.operator("wm.url_open", text="Open website")
                ops.url = updater.website
            else:
                row = layout.row()
                row.label(text="See source website to download the update")

    def execute(self, context):
        return {'FINISHED'}


class AddonUpdaterUpdatedSuccessful(bpy.types.Operator):
    """Addon in place, popup telling user it completed or what went wrong"""
    bl_label = "Installation Report"
    bl_idname = updater.addon + ".updater_update_successful"
    bl_description = "Update installation response"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    error = bpy.props.StringProperty(
        name="Error Occurred",
        default="",
        options={'HIDDEN'}
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)

    def draw(self, context):
        layout = self.layout

        if updater.invalid_updater:
            layout.label(text="Updater error")
            return

        saved = updater.json
        if self.error != "":
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Error occurred, did not install", icon="ERROR")
            if updater.error_msg:
                msg = updater.error_msg
            else:
                msg = self.error
            col.label(text=str(msg), icon="BLANK1")
            rw = col.row()
            rw.scale_y = 2
            rw.operator(
                "wm.url_open",
                text="Click for manual download.",
                icon="BLANK1").url = updater.website
        elif not updater.auto_reload_post_update:
            if "just_restored" in saved and saved["just_restored"]:
                col = layout.column()
                col.label(text="Addon restored", icon="RECOVER_LAST")
                alert_row = col.row()
                alert_row.alert = True
                alert_row.operator(
                    "wm.quit_blender",
                    text="Restart blender to reload",
                    icon="BLANK1")
                updater.json_reset_restore()
            else:
                col = layout.column()
                col.label(
                    text="Addon successfully installed", icon="FILE_TICK")
                alert_row = col.row()
                alert_row.alert = True
                alert_row.operator(
                    "wm.quit_blender",
                    text="Restart blender to reload",
                    icon="BLANK1")

        else:
            if "just_restored" in saved and saved["just_restored"]:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon restored", icon="RECOVER_LAST")
                col.label(
                    text="Consider restarting blender to fully reload.",
                    icon="BLANK1")
                updater.json_reset_restore()
            else:
                col = layout.column()
                col.scale_y = 0.7
                col.label(
                    text="Addon successfully installed", icon="FILE_TICK")
                col.label(
                    text="Consider restarting blender to fully reload.",
                    icon="BLANK1")

    def execute(self, context):
        return {'FINISHED'}


class AddonUpdaterRestoreBackup(bpy.types.Operator):
    """Restore addon from backup"""
    bl_label = "Restore backup"
    bl_idname = updater.addon + ".updater_restore_backup"
    bl_description = "Restore addon from backup"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        try:
            return os.path.isdir(os.path.join(updater.stage_path, "backup"))
        except:
            return False

    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}
        updater.restore_backup()
        return {'FINISHED'}


class AddonUpdaterIgnore(bpy.types.Operator):
    """Ignore update to prevent future popups"""
    bl_label = "Ignore update"
    bl_idname = updater.addon + ".updater_ignore"
    bl_description = "Ignore update to prevent future popups"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if updater.invalid_updater:
            return False
        elif updater.update_ready:
            return True
        else:
            return False

    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}
        updater.ignore_update()
        self.report({"INFO"}, "Open addon preferences for updater options")
        return {'FINISHED'}


class AddonUpdaterEndBackground(bpy.types.Operator):
    """Stop checking for update in the background"""
    bl_label = "End background check"
    bl_idname = updater.addon + ".end_background_check"
    bl_description = "Stop checking for update in the background"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        if updater.invalid_updater:
            return {'CANCELLED'}
        updater.stop_async_check_update()
        return {'FINISHED'}
ran_auto_check_install_popup = False
ran_update_success_popup = False
ran_background_check = False


@persistent
def updater_run_success_popup_handler(scene):
    global ran_update_success_popup
    ran_update_success_popup = True
    if updater.invalid_updater:
        return

    try:
        if "scene_update_post" in dir(bpy.app.handlers):
            bpy.app.handlers.scene_update_post.remove(
                updater_run_success_popup_handler)
        else:
            bpy.app.handlers.depsgraph_update_post.remove(
                updater_run_success_popup_handler)
    except:
        pass

    atr = AddonUpdaterUpdatedSuccessful.bl_idname.split(".")
    getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')


@persistent
def updater_run_install_popup_handler(scene):
    global ran_auto_check_install_popup
    ran_auto_check_install_popup = True
    updater.print_verbose("Running the install popup handler.")
    if updater.invalid_updater:
        return

    try:
        if "scene_update_post" in dir(bpy.app.handlers):
            bpy.app.handlers.scene_update_post.remove(
                updater_run_install_popup_handler)
        else:
            bpy.app.handlers.depsgraph_update_post.remove(
                updater_run_install_popup_handler)
    except:
        pass

    if "ignore" in updater.json and updater.json["ignore"]:
        return  # Don't do popup if ignore pressed.
    elif "version_text" in updater.json and updater.json["version_text"].get("version"):
        version = updater.json["version_text"]["version"]
        ver_tuple = updater.version_tuple_from_text(version)

        if ver_tuple < updater.current_version:
            updater.print_verbose(
                "{} updater: appears user updated, clearing flag".format(
                    updater.addon))
            updater.json_reset_restore()
            return
    atr = AddonUpdaterInstallPopup.bl_idname.split(".")
    getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')


def background_update_callback(update_ready):
    """Passed into the updater, background thread updater"""
    global ran_auto_check_install_popup
    updater.print_verbose("Running background update callback")
    if updater.invalid_updater:
        return
    if not updater.show_popups:
        return
    if not update_ready:
        return
    handlers = []
    if "scene_update_post" in dir(bpy.app.handlers):  # 2.7x
        handlers = bpy.app.handlers.scene_update_post
    else:  # 2.8+
        handlers = bpy.app.handlers.depsgraph_update_post
    in_handles = updater_run_install_popup_handler in handlers

    if in_handles or ran_auto_check_install_popup:
        return

    if "scene_update_post" in dir(bpy.app.handlers):  # 2.7x
        bpy.app.handlers.scene_update_post.append(
            updater_run_install_popup_handler)
    else:  # 2.8+
        bpy.app.handlers.depsgraph_update_post.append(
            updater_run_install_popup_handler)
    ran_auto_check_install_popup = True
    updater.print_verbose("Attempted popup prompt")


def post_update_callback(module_name, res=None):
    """Callback for once the run_update function has completed.

    Only makes sense to use this if "auto_reload_post_update" == False,
    i.e. don't auto-restart the addon.

    Arguments:
        module_name: returns the module name from updater, but unused here.
        res: If an error occurred, this is the detail string.
    """
    if updater.invalid_updater:
        return

    if res is None:
        updater.print_verbose(
            "{} updater: Running post update callback".format(updater.addon))

        atr = AddonUpdaterUpdatedSuccessful.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        global ran_update_success_popup
        ran_update_success_popup = True
    else:
        atr = AddonUpdaterUpdatedSuccessful.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT', error=res)
    return


def ui_refresh(update_status):
    """Redraw the ui once an async thread has completed"""
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                area.tag_redraw()


def check_for_update_background():
    """Function for asynchronous background check.

    *Could* be called on register, but would be bad practice as the bare
    minimum code should run at the moment of registration (addon ticked).
    """
    if updater.invalid_updater:
        return
    if online_access_disabled():
        return
    global ran_background_check
    if ran_background_check:
        return
    elif updater.update_ready is not None or updater.async_checking:
        return
    settings = get_user_preferences(bpy.context)
    if not settings:
        return
    updater.set_check_interval(enabled=settings.auto_check_update,
                               months=settings.updater_interval_months,
                               days=settings.updater_interval_days,
                               hours=settings.updater_interval_hours,
                               minutes=settings.updater_interval_minutes)
    updater.check_for_update_async(background_update_callback)
    ran_background_check = True


def check_for_update_nonthreaded(self, context):
    """Can be placed in front of other operators to launch when pressed"""
    if updater.invalid_updater:
        return
    if online_access_disabled():
        self.report({'WARNING'}, online_access_disabled_message())
        return
    settings = get_user_preferences(bpy.context)
    if not settings:
        if updater.verbose:
            print("Could not get {} preferences, update check skipped".format(
                __package__))
        return
    updater.set_check_interval(enabled=settings.auto_check_update,
                               months=settings.updater_interval_months,
                               days=settings.updater_interval_days,
                               hours=settings.updater_interval_hours,
                               minutes=settings.updater_interval_minutes)

    (update_ready, version, link) = updater.check_for_update(now=False)
    if update_ready:
        atr = AddonUpdaterInstallPopup.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
    else:
        updater.print_verbose("No update ready")
        self.report({'INFO'}, "No update ready")


def show_reload_popup():
    """For use in register only, to show popup after re-enabling the addon.

    Must be enabled by developer.
    """
    if updater.invalid_updater:
        return
    saved_state = updater.json
    global ran_update_success_popup

    has_state = saved_state is not None
    just_updated = "just_updated" in saved_state
    updated_info = saved_state["just_updated"]

    if not (has_state and just_updated and updated_info):
        return

    updater.json_reset_postupdate()  # So this only runs once.
    if not updater.auto_reload_post_update:
        return
    handlers = []
    if "scene_update_post" in dir(bpy.app.handlers):  # 2.7x
        handlers = bpy.app.handlers.scene_update_post
    else:  # 2.8+
        handlers = bpy.app.handlers.depsgraph_update_post
    in_handles = updater_run_success_popup_handler in handlers

    if in_handles or ran_update_success_popup:
        return

    if "scene_update_post" in dir(bpy.app.handlers):  # 2.7x
        bpy.app.handlers.scene_update_post.append(
            updater_run_success_popup_handler)
    else:  # 2.8+
        bpy.app.handlers.depsgraph_update_post.append(
            updater_run_success_popup_handler)
    ran_update_success_popup = True
def update_notice_box_ui(self, context):
    """Update notice draw, to add to the end or beginning of a panel.

    After a check for update has occurred, this function will draw a box
    saying an update is ready, and give a button for: update now, open website,
    or ignore popup. Ideal to be placed at the end / beginning of a panel.
    """

    if updater.invalid_updater:
        return

    saved_state = updater.json
    if not updater.auto_reload_post_update:
        if "just_updated" in saved_state and saved_state["just_updated"]:
            layout = self.layout
            box = layout.box()
            col = box.column()
            alert_row = col.row()
            alert_row.alert = True
            alert_row.operator(
                "wm.quit_blender",
                text="Restart blender",
                icon="ERROR")
            col.label(text="to complete update")
            return
    if "ignore" in updater.json and updater.json["ignore"]:
        return
    if not updater.update_ready:
        return

    layout = self.layout
    box = layout.box()
    col = box.column(align=True)
    col.alert = True
    col.label(text="Update ready!", icon="ERROR")
    col.alert = False
    col.separator()
    row = col.row(align=True)
    split = row.split(align=True)
    colL = split.column(align=True)
    colL.scale_y = 1.5
    colL.operator(AddonUpdaterIgnore.bl_idname, icon="X", text="Ignore")
    colR = split.column(align=True)
    colR.scale_y = 1.5
    if not updater.manual_only:
        colR.operator(AddonUpdaterUpdateNow.bl_idname,
                      text="Update", icon="LOOP_FORWARDS")
        col.operator("wm.url_open", text="Open website").url = updater.website
        col.operator(AddonUpdaterInstallManually.bl_idname,
                     text="Install manually")
    else:
        col.operator("wm.url_open", text="Get it now").url = updater.website


def update_settings_ui(self, context, element=None):
    """Preferences - for drawing with full width inside user preferences

    A function that can be run inside user preferences panel for prefs UI.
    Place inside UI draw using:
        addon_updater_ops.update_settings_ui(self, context)
    or by:
        addon_updater_ops.update_settings_ui(context)
    """
    if element is None:
        element = self.layout
    box = element.box()
    if updater.invalid_updater:
        box.label(text="Error initializing updater code:")
        box.label(text=updater.error_msg)
        return
    settings = get_user_preferences(context)
    if not settings:
        box.label(text="Error getting updater preferences", icon='ERROR')
        return
    box.label(text="Updater Settings")
    row = box.row()
    online_disabled = online_access_disabled()
    if not updater.auto_reload_post_update:
        saved_state = updater.json
        if "just_updated" in saved_state and saved_state["just_updated"]:
            row.alert = True
            row.operator("wm.quit_blender",
                         text="Restart blender to complete update",
                         icon="ERROR")
            return

    split = layout_split(row, factor=0.4)
    sub_col = split.column()
    sub_col.enabled = not online_disabled
    sub_col.prop(settings, "auto_check_update")
    sub_col = split.column()

    if online_disabled or not settings.auto_check_update:
        sub_col.enabled = False
    sub_row = sub_col.row()
    sub_row.label(text="Interval between checks")
    sub_row = sub_col.row(align=True)
    check_col = sub_row.column(align=True)
    check_col.prop(settings, "updater_interval_months")
    check_col = sub_row.column(align=True)
    check_col.prop(settings, "updater_interval_days")
    check_col = sub_row.column(align=True)
    if online_disabled:
        row = box.row()
        row.alert = True
        row.label(text=online_access_disabled_message(), icon='ERROR')
        row = box.row()
        row.scale_y = 2
        row.operator(AddonUpdaterCheckNow.bl_idname)
        if updater.website:
            row = box.row()
            row.operator("wm.url_open", text="Open Secret Paint website").url = updater.website
        row = box.row()
        row.scale_y = 0.7
        last_check = updater.json["last_check"]
        if last_check:
            last_check = last_check[0: last_check.index(".")]
            row.label(text="Last update check: " + last_check)
        else:
            row.label(text="Last update check: Never")
        return
    row = box.row()
    col = row.column()
    if updater.error is not None:
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.scale_y = 2
        if "ssl" in updater.error_msg.lower():
            split.enabled = True
            split.operator(AddonUpdaterInstallManually.bl_idname,
                           text=updater.error)
        else:
            split.enabled = False
            split.operator(AddonUpdaterCheckNow.bl_idname,
                           text=updater.error)
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    elif updater.update_ready is None and not updater.async_checking:
        col.scale_y = 2
        col.operator(AddonUpdaterCheckNow.bl_idname)
    elif updater.update_ready is None:  # async is running
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="Checking...")
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterEndBackground.bl_idname, text="", icon="X")

    elif updater.include_branches and \
            len(updater.tags) == len(updater.include_branch_list) and not \
            updater.manual_only:
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.scale_y = 2
        update_now_txt = "Update directly to {}".format(
            updater.include_branch_list[0])
        split.operator(AddonUpdaterUpdateNow.bl_idname, text=update_now_txt)
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    elif updater.update_ready and not updater.manual_only:
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterUpdateNow.bl_idname,
                       text="Update now to " + str(updater.update_version))
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    elif updater.update_ready and updater.manual_only:
        col.scale_y = 2
        dl_now_txt = "Download " + str(updater.update_version)
        col.operator("wm.url_open",
                     text=dl_now_txt).url = updater.website
    else:  # i.e. that updater.update_ready == False.
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="Addon is up to date")
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    if not updater.manual_only:
        col = row.column(align=True)
        if updater.include_branches and len(updater.include_branch_list) > 0:
            branch = updater.include_branch_list[0]
            col.operator(AddonUpdaterUpdateTarget.bl_idname,
                         text="Install {} / old version".format(branch))
        else:
            col.operator(AddonUpdaterUpdateTarget.bl_idname,
                         text="(Re)install addon version")
        last_date = "none found"
        backup_path = os.path.join(updater.stage_path, "backup")
        if "backup_date" in updater.json and os.path.isdir(backup_path):
            if updater.json["backup_date"] == "":
                last_date = "Date not found"
            else:
                last_date = updater.json["backup_date"]
        backup_text = "Restore addon backup ({})".format(last_date)
        col.operator(AddonUpdaterRestoreBackup.bl_idname, text=backup_text)

    row = box.row()
    row.scale_y = 0.7
    last_check = updater.json["last_check"]
    if updater.error is not None and updater.error_msg is not None:
        row.label(text=updater.error_msg)
    elif last_check:
        last_check = last_check[0: last_check.index(".")]
        row.label(text="Last update check: " + last_check)
    else:
        row.label(text="Last update check: Never")


def update_settings_ui_condensed(self, context, element=None):
    """Preferences - Condensed drawing within preferences.

    Alternate draw for user preferences or other places, does not draw a box.
    """
    if element is None:
        element = self.layout
    row = element.row()
    if updater.invalid_updater:
        row.label(text="Error initializing updater code:")
        row.label(text=updater.error_msg)
        return
    settings = get_user_preferences(context)
    if not settings:
        row.label(text="Error getting updater preferences", icon='ERROR')
        return
    if online_access_disabled():
        row.alert = True
        row.label(text=online_access_disabled_message(), icon='ERROR')
        row = element.row()
        row.scale_y = 2
        row.operator(AddonUpdaterCheckNow.bl_idname)
        row = element.row()
        row.enabled = False
        row.prop(settings, "auto_check_update")
        return
    if not updater.auto_reload_post_update:
        saved_state = updater.json
        if "just_updated" in saved_state and saved_state["just_updated"]:
            row.alert = True  # mark red
            row.operator(
                "wm.quit_blender",
                text="Restart blender to complete update",
                icon="ERROR")
            return

    col = row.column()
    if updater.error is not None:
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.scale_y = 2
        if "ssl" in updater.error_msg.lower():
            split.enabled = True
            split.operator(AddonUpdaterInstallManually.bl_idname,
                           text=updater.error)
        else:
            split.enabled = False
            split.operator(AddonUpdaterCheckNow.bl_idname,
                           text=updater.error)
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    elif updater.update_ready is None and not updater.async_checking:
        col.scale_y = 2
        col.operator(AddonUpdaterCheckNow.bl_idname)
    elif updater.update_ready is None:  # Async is running.
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="Checking...")
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterEndBackground.bl_idname, text="", icon="X")

    elif updater.include_branches and \
            len(updater.tags) == len(updater.include_branch_list) and not \
            updater.manual_only:
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.scale_y = 2
        now_txt = "Update directly to " + str(updater.include_branch_list[0])
        split.operator(AddonUpdaterUpdateNow.bl_idname, text=now_txt)
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    elif updater.update_ready and not updater.manual_only:
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterUpdateNow.bl_idname,
                       text="Update now to " + str(updater.update_version))
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    elif updater.update_ready and updater.manual_only:
        col.scale_y = 2
        dl_txt = "Download " + str(updater.update_version)
        col.operator("wm.url_open", text=dl_txt).url = updater.website
    else:  # i.e. that updater.update_ready == False.
        sub_col = col.row(align=True)
        sub_col.scale_y = 1
        split = sub_col.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="Addon is up to date")
        split = sub_col.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname,
                       text="", icon="FILE_REFRESH")

    row = element.row()
    row.prop(settings, "auto_check_update")

    row = element.row()
    row.scale_y = 0.7
    last_check = updater.json["last_check"]
    if updater.error is not None and updater.error_msg is not None:
        row.label(text=updater.error_msg)
    elif last_check != "" and last_check is not None:
        last_check = last_check[0: last_check.index(".")]
        row.label(text="Last check: " + last_check)
    else:
        row.label(text="Last check: Never")


def skip_tag_function(self, tag):
    """A global function for tag skipping.

    A way to filter which tags are displayed, e.g. to limit downgrading too
    long ago.

    Args:
        self: The instance of the singleton addon update.
        tag: the text content of a tag from the repo, e.g. "v1.2.3".

    Returns:
        bool: True to skip this tag name (ie don't allow for downloading this
            version), or False if the tag is allowed.
    """
    if self.invalid_updater:
        return False
    if self.include_branches:
        for branch in self.include_branch_list:
            if tag["name"].lower() == branch:
                return False
    tupled = self.version_tuple_from_text(tag["name"])
    if not isinstance(tupled, tuple):
        return True
    if self.version_min_update is not None:
        if tupled < self.version_min_update:
            return True  # Skip if current version below this.
    if self.version_max_update is not None:
        if tupled >= self.version_max_update:
            return True  # Skip if current version at or above this.
    return False


def select_link_function(self, tag):
    """Only customize if trying to leverage "attachments" in *GitHub* releases.

    A way to select from one or multiple attached downloadable files from the
    server, instead of downloading the default release/tag source code.
    """
    link = tag["zipball_url"]
    return link


def _cli_args(argv):
    if len(argv) == 1 and isinstance(argv[0], (list, tuple)):
        return list(argv[0])
    return list(argv)


def _cli_arg_value(argv, option_name):
    args = _cli_args(argv)
    try:
        index = args.index(option_name)
    except ValueError:
        return None
    next_index = index + 1
    if next_index >= len(args):
        return None
    return args[next_index]


def _tuple_or_none(value):
    if value is None:
        return None
    return tuple(value)


def _json_safe_version(value):
    if isinstance(value, tuple):
        return list(value)
    return value


def _configure_updater_from_cli_payload(payload):
    updater.clear_state()
    updater.addon = payload.get("addon") or updater.addon
    updater.engine = payload.get("engine") or "Github"
    if payload.get("api_url"):
        updater.api_url = payload["api_url"]
    updater.private_token = None
    updater.user = payload.get("user")
    updater.repo = payload.get("repo")
    updater.website = payload.get("website")
    updater.subfolder_path = payload.get("subfolder_path")
    updater.current_version = tuple(payload.get("current_version") or (0, 0, 0))
    updater.use_releases = bool(payload.get("use_releases", False))
    updater.include_branches = bool(payload.get("include_branches", False))
    updater.include_branch_list = payload.get("include_branch_list") or None
    updater.include_branch_auto_check = bool(payload.get("include_branch_auto_check", False))
    updater.manual_only = bool(payload.get("manual_only", False))
    updater.version_min_update = _tuple_or_none(payload.get("version_min_update"))
    updater.version_max_update = _tuple_or_none(payload.get("version_max_update"))
    updater.fake_install = bool(payload.get("fake_install", False))
    updater.verbose = bool(payload.get("verbose", False))
    updater.use_print_traces = bool(payload.get("use_print_traces", True))
    updater.skip_tag = skip_tag_function
    updater.select_link = select_link_function

    interval = payload.get("check_interval") or {}
    updater.set_check_interval(
        enabled=bool(interval.get("enabled", False)),
        months=int(interval.get("months", 0)),
        days=int(interval.get("days", 0)),
        hours=int(interval.get("hours", 0)),
        minutes=int(interval.get("minutes", 0)))


def secret_paint_update_check_cli(*argv):
    request_path = _cli_arg_value(argv, "--request")
    if not request_path:
        print("secret_paint_update_check requires --request <path>")
        return 2

    status_path = None
    try:
        with open(request_path, encoding='utf-8') as request_file:
            payload = json.load(request_file)
        status_path = payload.get("status_path")
        _configure_updater_from_cli_payload(payload)
        updater.check_for_update(now=bool(payload.get("now", False)))
        status = {
            "update_ready": updater.update_ready,
            "update_version": _json_safe_version(updater.update_version),
            "update_link": updater.update_link,
            "error": updater.error,
            "error_msg": updater.error_msg,
            "json": updater.json,
        }
        exit_code = 0 if updater.error is None else 1
    except Exception as exception:
        traceback.print_exc()
        status = {
            "update_ready": False,
            "update_version": None,
            "update_link": None,
            "error": "Error occurred",
            "error_msg": str(exception),
            "json": {},
        }
        exit_code = 1

    if status_path:
        try:
            with open(status_path, 'w', encoding='utf-8') as status_file:
                status_file.write(json.dumps(status, indent=4))
        except Exception:
            traceback.print_exc()
            return 1

    return exit_code


_REGISTERED_CLI_COMMANDS = {}


def _register_updater_cli_commands():
    register_cli_command = getattr(bpy.utils, "register_cli_command", None)
    if register_cli_command is None:
        print("Secret Paint updater CLI command unavailable: bpy.utils.register_cli_command is missing")
        return
    if "secret_paint_update_check" in _REGISTERED_CLI_COMMANDS:
        return
    try:
        command = register_cli_command("secret_paint_update_check", secret_paint_update_check_cli)
        _REGISTERED_CLI_COMMANDS["secret_paint_update_check"] = command
    except Exception:
        traceback.print_exc()


def _unregister_updater_cli_commands():
    unregister_cli_command = getattr(bpy.utils, "unregister_cli_command", None)
    if unregister_cli_command is None:
        _REGISTERED_CLI_COMMANDS.clear()
        return
    for command_id, command in tuple(_REGISTERED_CLI_COMMANDS.items()):
        try:
            unregister_cli_command(command)
        except Exception:
            traceback.print_exc()
        finally:
            _REGISTERED_CLI_COMMANDS.pop(command_id, None)
classes = (
    AddonUpdaterInstallPopup,
    AddonUpdaterCheckNow,
    AddonUpdaterUpdateNow,
    AddonUpdaterUpdateTarget,
    AddonUpdaterInstallManually,
    AddonUpdaterUpdatedSuccessful,
    AddonUpdaterRestoreBackup,
    AddonUpdaterIgnore,
    AddonUpdaterEndBackground
)


def register(bl_info):
    """Registering the operators in this module"""
    if updater.error:
        print("Exiting updater registration, " + updater.error)
        return
    updater.clear_state()  # Clear internal vars, avoids reloading oddities.
    updater.engine = "Github"
    updater.private_token = None  # "tokenstring"
    updater.user = "orencloud"
    updater.repo = "Secret-Paint"
    updater.website = "https://github.com/orencloud/Secret-Paint/"
    updater.subfolder_path = ""
    updater.current_version = bl_info["version"]
    updater.verbose = True  # make False for production default
    updater.backup_current = True  # True by default
    updater.backup_ignore_patterns = ["__pycache__"]
    updater.overwrite_patterns = ["*"]
    updater.remove_pre_update_patterns = ["*.pyc"]
    updater.include_branches = True
    updater.use_releases = False
    updater.include_branch_list = None  # None is the equivalent = ['main']
    updater.manual_only = False
    updater.fake_install = False  # Set to true to test callback/reloading.
    updater.show_popups = True
    updater.version_min_update = (0, 0, 0)
    updater.version_max_update = None  # None or default for no max.
    updater.skip_tag = skip_tag_function  # min and max used in this function
    updater.select_link = select_link_function
    updater.auto_reload_post_update = False
    for cls in classes:
        make_annotations(cls)
        bpy.utils.register_class(cls)
    _register_updater_cli_commands()
    show_reload_popup()


def unregister():
    _unregister_updater_cli_commands()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    updater.clear_state()  # Clear internal vars, avoids reloading oddities.

    global ran_auto_check_install_popup
    ran_auto_check_install_popup = False

    global ran_update_success_popup
    ran_update_success_popup = False

    global ran_background_check
    ran_background_check = False
