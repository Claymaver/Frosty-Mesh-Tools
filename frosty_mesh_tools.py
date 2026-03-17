bl_info = {
    "name": "Frosty Mesh Tools",
    "author": "Clay MacDonald",
    "version": (4, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Frosty Mesh",
    "description": "Rename LODs, fix transforms, and export FBX meshes for Frostbite engine modding via Frosty Editor",
    "doc_url": "https://github.com/claymcdonald/frosty-mesh-tools/wiki",
    "category": "Object",
}

import bpy
import os
import re
import math
from bpy.props import (
    StringProperty, IntProperty, FloatProperty,
    BoolProperty, EnumProperty, CollectionProperty, PointerProperty
)
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences
from bpy_extras.io_utils import ImportHelper

# ============================================================================
# TEMPLATE SCANNING
# ============================================================================

_cached_samples = []
_cached_folder = ""


def is_mesh_res_file(filepath):
    """Check if file is a valid mesh.res (not a cloth asset)"""
    if not os.path.exists(filepath):
        return False
    name = os.path.basename(filepath).lower()

    if name == 'blocks.res':
        return False
    if 'clothwrap' in name or 'eacloth' in name:
        return False
    if not name.endswith('.res'):
        return False

    try:
        with open(filepath, 'rb') as f:
            data = f.read(100)
        return b'\x00' in data and len(data) >= 50
    except:
        return False


def scan_samples_folder(folder_path):
    """Scan folder for mesh.res templates (excludes cloth assets)"""
    samples = []
    if not folder_path or not os.path.exists(folder_path):
        return samples

    for root, dirs, files in os.walk(folder_path):
        for f in files:
            filepath = os.path.join(root, f)
            name_lower = f.lower()

            if not name_lower.endswith('.res'):
                continue
            if name_lower == 'blocks.res':
                continue
            if 'clothwrap' in name_lower or 'eacloth' in name_lower:
                continue
            if 'cloth' in name_lower and 'asset' in name_lower:
                continue

            if name_lower.endswith('_mesh.res') or is_mesh_res_file(filepath):
                rel_path = os.path.relpath(root, folder_path)
                if rel_path == '.':
                    display = os.path.splitext(f)[0]
                else:
                    display = rel_path.replace(os.sep, ' / ')
                samples.append((display, filepath))

    samples.sort(key=lambda x: x[0].lower())
    return samples


def get_sample_items(self, context):
    global _cached_samples, _cached_folder
    settings = context.scene.frosty_lod_settings

    if settings.samples_folder != _cached_folder:
        _cached_folder = settings.samples_folder
        _cached_samples = scan_samples_folder(settings.samples_folder)

    items = [('NONE', "-- Select Template --", "Choose a mesh.res template")]
    for display_name, filepath in _cached_samples:
        items.append((filepath, display_name, f"Load: {display_name}"))
    if len(items) == 1:
        items.append(('NO_SAMPLES', "(No templates found)", ""))
    return items


def on_sample_selected(self, context):
    settings = context.scene.frosty_lod_settings
    if settings.selected_sample not in ('NONE', 'NO_SAMPLES', ''):
        if os.path.exists(settings.selected_sample):
            load_template(context, settings.selected_sample)


def on_samples_folder_changed(self, context):
    global _cached_folder
    _cached_folder = ""


# ============================================================================
# TEMPLATE PARSING
# ============================================================================

def parse_mesh_res(filepath):
    """Extract material names and LOD info from mesh.res"""
    with open(filepath, 'rb') as f:
        data = f.read()

    text = data.decode('latin-1', errors='ignore')

    mesh_path_match = re.search(
        r'(?:characters|vehicles|weapons|props)/[^\x00]+?(?=_lod|\x00)',
        text
    )
    mesh_path = mesh_path_match.group(0) if mesh_path_match else ""

    lod_sections = {}

    for lod_match in re.finditer(r'Mesh:[^\x00]+?_lod(\d+)', text):
        lod_num = int(lod_match.group(1))
        pos = lod_match.start()

        backward_text = text[max(0, pos - 300):pos]

        for mat_match in re.finditer(r'([A-Za-z][A-Za-z0-9_]{2,})\x00', backward_text):
            mat_name = mat_match.group(1)

            if mat_name.lower() in {"mesh", "material", "shader", "lod", "model", "section", "bone", "vertex"}:
                continue
            if re.search(r'_lod\d+$', mat_name, re.IGNORECASE):
                continue
            if mat_name.isdigit():
                continue

            lod_sections.setdefault(lod_num, [])
            if mat_name not in lod_sections[lod_num]:
                lod_sections[lod_num].append(mat_name)

    if not lod_sections:
        for match in re.finditer(r'([A-Za-z0-9_]+)\x00', text):
            mat_name = match.group(1)

            if len(mat_name) < 3 or mat_name.isdigit():
                continue
            if re.search(r'_lod\d+$', mat_name, re.IGNORECASE):
                continue
            if mat_name.lower() in {"mesh", "material", "shader", "lod", "model"}:
                continue

            pos = match.start()
            forward_text = text[pos:pos + 300]

            lod_match = re.search(r'Mesh:[^\x00]+_lod(\d+)', forward_text)
            if not lod_match:
                lod_match = re.search(r'_[Ll][Oo][Dd](\d+)', forward_text)
            if not lod_match:
                continue

            lod_num = int(lod_match.group(1))

            lod_sections.setdefault(lod_num, [])
            if mat_name not in lod_sections[lod_num]:
                lod_sections[lod_num].append(mat_name)

    material_info = {}
    all_materials = set()

    for materials in lod_sections.values():
        all_materials.update(materials)

    for mat in all_materials:
        lods_with_mat = [lod for lod, mats in lod_sections.items() if mat in mats]
        if lods_with_mat:
            material_info[mat] = (min(lods_with_mat), max(lods_with_mat))

    if material_info:
        print(f"[FrostyMeshTools] Found {len(material_info)} materials:")
        for mat, (min_l, max_l) in sorted(material_info.items()):
            print(f"  {mat}: LOD {min_l}-{max_l}")
    else:
        print(f"[FrostyMeshTools] Warning: No materials with LOD info found in {filepath}")
        fallback_mats = set()
        for match in re.finditer(r'([A-Za-z][A-Za-z0-9_]{3,30})\x00', text):
            name = match.group(1)
            if name.lower() not in {"mesh", "material", "shader", "lod", "model", "section", "bone", "vertex", "index", "buffer", "texture", "normal", "tangent"}:
                if not re.search(r'_lod\d+$|^lod\d+$', name, re.IGNORECASE):
                    fallback_mats.add(name)

        if fallback_mats:
            print(f"[FrostyMeshTools] Using fallback - found {len(fallback_mats)} potential materials")
            for mat in sorted(fallback_mats)[:20]:
                material_info[mat] = (0, 4)

    return material_info, lod_sections, mesh_path


# ============================================================================
# COLLECTION MANAGEMENT
# ============================================================================

def get_or_create_collection(name):
    """Get an existing collection by name or create a new one under the scene."""
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
        if col.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(col)
        return col

    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def link_object_to_collection(obj, collection):
    """Move an object into a collection, removing it from others."""
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)


# ============================================================================
# TEMPLATE LOADING
# ============================================================================

def load_template(context, filepath):
    """Load a mesh.res template and create a collection."""
    settings = context.scene.frosty_lod_settings
    prefs = context.preferences.addons[__name__].preferences

    if not is_mesh_res_file(filepath):
        return False, "Not a valid mesh.res file"

    try:
        material_info, lod_sections, mesh_path = parse_mesh_res(filepath)
    except Exception as e:
        return False, f"Parse error: {str(e)}"

    if not material_info:
        return False, "No materials found"

    settings.template_path = filepath
    settings.template_mesh_path = mesh_path
    folder_name = os.path.basename(os.path.dirname(filepath))
    settings.template_name = folder_name or os.path.splitext(os.path.basename(filepath))[0]

    if prefs.remember_last_template:
        prefs.last_template_path = filepath

    # Store material info
    settings.material_slots.clear()
    for mat_name in sorted(material_info.keys()):
        min_lod, max_lod = material_info[mat_name]
        slot = settings.material_slots.add()
        slot.name = mat_name
        slot.min_lod = min_lod
        slot.max_lod = max_lod

    # Create collection for this mesh
    get_or_create_collection(settings.template_name)

    print(f"Loaded template: {settings.template_name} ({len(material_info)} materials)")
    return True, f"Loaded {len(material_info)} materials"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_armature(obj):
    """Find armature for an object."""
    if obj.parent and obj.parent.type == 'ARMATURE':
        return obj.parent
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            return mod.object
    return None


def get_template_collection(settings):
    """Get the template collection."""
    if settings.template_name and settings.template_name in bpy.data.collections:
        return bpy.data.collections[settings.template_name]
    return None


def get_meshes_from_template_collection(settings):
    """Get all mesh objects from the template collection."""
    col = get_template_collection(settings)
    if not col:
        return []
    return [obj for obj in col.objects if obj.type == 'MESH']


# ============================================================================
# PROPERTY GROUPS
# ============================================================================

class MaterialSlotItem(PropertyGroup):
    name: StringProperty(name="Material Name")
    mesh_object: PointerProperty(name="Mesh", type=bpy.types.Object)
    min_lod: IntProperty(name="Min LOD", default=0, min=0, max=7)
    max_lod: IntProperty(name="Max LOD", default=4, min=0, max=7)


class FrostyLODSettings(PropertyGroup):
    # Template settings
    template_path: StringProperty(name="Template Path", subtype='FILE_PATH')
    template_name: StringProperty(name="Template Name", default="")
    template_mesh_path: StringProperty(name="Mesh Path", default="")
    samples_folder: StringProperty(
        name="Templates Folder",
        subtype='DIR_PATH',
        update=lambda s, c: on_samples_folder_changed(s, c)
    )
    selected_sample: EnumProperty(
        name="Template",
        items=get_sample_items,
        update=lambda s, c: on_sample_selected(s, c)
    )

    # Material slots (from template)
    material_slots: CollectionProperty(type=MaterialSlotItem)

    # Export settings
    export_path: StringProperty(name="Export Path", subtype='DIR_PATH', default="//")
    export_name: StringProperty(name="Export Name", default="mesh")
    export_scale: FloatProperty(name="Scale", default=1.0, min=0.001, max=100.0)

    # UI state
    active_tab: EnumProperty(
        name="Tab",
        items=[
            ('TEMPLATE', "Template", "Template loading"),
            ('RENAME', "Rename", "LOD renaming"),
            ('TRANSFORM', "Transform", "Transform fix"),
            ('EXPORT', "Export", "FBX export"),
        ],
        default='TEMPLATE'
    )

    # Misc
    auto_rename_meshes: BoolProperty(
        name="Auto-rename on assign",
        description="Rename meshes to materialname:lod0 format when assigned",
        default=True
    )


class FrostyPreferences(AddonPreferences):
    bl_idname = __name__

    remember_last_template: BoolProperty(
        name="Remember Last Template",
        description="Auto-load last used template on startup",
        default=True
    )
    last_template_path: StringProperty(name="Last Template", subtype='FILE_PATH')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "remember_last_template")


# ============================================================================
# OPERATORS
# ============================================================================

class FROSTY_OT_load_template(Operator, ImportHelper):
    bl_idname = "frosty.load_template"
    bl_label = "Load Template"
    bl_description = "Load a mesh.res template file"

    filename_ext = ".res"
    filter_glob: StringProperty(default="*_mesh.res;*.res", options={'HIDDEN'})

    def execute(self, context):
        success, message = load_template(context, self.filepath)
        self.report({'INFO' if success else 'ERROR'}, message)
        return {'FINISHED'} if success else {'CANCELLED'}


class FROSTY_OT_assign_mesh(Operator):
    bl_idname = "frosty.assign_mesh"
    bl_label = "Assign Mesh"
    bl_description = "Assign selected mesh to this material slot"
    bl_options = {'REGISTER', 'UNDO'}

    slot_index: IntProperty()

    def execute(self, context):
        settings = context.scene.frosty_lod_settings

        if self.slot_index >= len(settings.material_slots):
            self.report({'ERROR'}, "Invalid slot index")
            return {'CANCELLED'}

        slot = settings.material_slots[self.slot_index]

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object first")
            return {'CANCELLED'}

        slot.mesh_object = obj

        # Move into template collection
        template_col = get_template_collection(settings)
        if template_col:
            link_object_to_collection(obj, template_col)

        # Auto-rename
        if settings.auto_rename_meshes:
            obj.name = f"{slot.name}:lod0"

        self.report({'INFO'}, f"Assigned '{obj.name}' to slot '{slot.name}'")
        return {'FINISHED'}


class FROSTY_OT_rename_lods(Operator):
    bl_idname = "frosty.rename_lods"
    bl_label = "Rename LODs"
    bl_description = "Rename assigned meshes to materialname:lodN format"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.frosty_lod_settings
        return any(slot.mesh_object for slot in settings.material_slots)

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        renamed_count = 0

        for slot in settings.material_slots:
            if not slot.mesh_object:
                continue

            new_name = f"{slot.name}:lod0"
            if slot.mesh_object.name != new_name:
                slot.mesh_object.name = new_name
                renamed_count += 1

        self.report({'INFO'}, f"Renamed {renamed_count} meshes")
        return {'FINISHED'}


class FROSTY_OT_fix_transforms(Operator):
    bl_idname = "frosty.fix_transforms"
    bl_label = "Fix Transforms"
    bl_description = "Fix transforms for Frosty import: unparent, apply transforms, rotate for engine axis, reparent"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_meshes:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        # Find all armatures associated with selected meshes
        armatures = set()
        mesh_armature_map = {}
        for obj in selected_meshes:
            arm = find_armature(obj)
            if arm:
                armatures.add(arm)
                mesh_armature_map[obj] = arm

        all_objects = list(selected_meshes) + list(armatures)

        # Step 1: Unparent meshes (keep transform)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_meshes:
            if obj.parent:
                obj.select_set(True)
        if context.selected_objects:
            context.view_layer.objects.active = context.selected_objects[0]
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

        # Step 2: Apply rotation, scale, and location on all objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objects:
            obj.select_set(True)
        if all_objects:
            context.view_layer.objects.active = all_objects[0]
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Step 3: Rotate X by -90 degrees
        for obj in all_objects:
            obj.rotation_euler[0] = math.radians(-90)

        # Step 4: Apply rotation
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        # Step 5: Rotate X by +90 degrees
        for obj in all_objects:
            obj.rotation_euler[0] = math.radians(90)

        # Step 6: Re-parent meshes to their armatures
        for mesh_obj, arm in mesh_armature_map.items():
            bpy.ops.object.select_all(action='DESELECT')
            mesh_obj.select_set(True)
            arm.select_set(True)
            context.view_layer.objects.active = arm
            bpy.ops.object.parent_set(type='ARMATURE')

        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_meshes:
            obj.select_set(True)
        if selected_meshes:
            context.view_layer.objects.active = selected_meshes[0]

        self.report({'INFO'}, f"Fixed transforms for {len(selected_meshes)} meshes and {len(armatures)} armatures")
        return {'FINISHED'}


class FROSTY_OT_export_fbx(Operator):
    bl_idname = "frosty.export_fbx"
    bl_label = "Export FBX"
    bl_description = "Export meshes to FBX for import into Frosty Editor"

    @classmethod
    def poll(cls, context):
        settings = context.scene.frosty_lod_settings
        return len(get_meshes_from_template_collection(settings)) > 0

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        lod_objects = get_meshes_from_template_collection(settings)

        view_layer_objects = set(context.view_layer.objects)
        lod_objects = [obj for obj in lod_objects if obj in view_layer_objects]

        if not lod_objects:
            self.report({'ERROR'}, "No meshes to export")
            return {'CANCELLED'}

        # Find armatures
        armatures = set()
        for obj in lod_objects:
            arm = find_armature(obj)
            if arm and arm in view_layer_objects:
                armatures.add(arm)

        # Select objects for export
        bpy.ops.object.select_all(action='DESELECT')
        for obj in lod_objects:
            obj.select_set(True)
        for arm in armatures:
            arm.select_set(True)

        if lod_objects:
            context.view_layer.objects.active = lod_objects[0]

        # Create export directory
        export_dir = bpy.path.abspath(settings.export_path)
        os.makedirs(export_dir, exist_ok=True)

        filepath = os.path.join(export_dir, f"{settings.export_name or 'mesh'}.fbx")

        # Export FBX with Frosty-compatible settings
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            apply_scale_options='FBX_SCALE_ALL',
            global_scale=settings.export_scale,
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_triangles=True,
            use_tspace=True,
            add_leaf_bones=False,
            bake_anim=False,
            use_armature_deform_only=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
        )

        self.report({'INFO'}, f"Exported {len(lod_objects)} meshes to: {filepath}")
        return {'FINISHED'}


class FROSTY_OT_open_docs(Operator):
    bl_idname = "frosty.open_docs"
    bl_label = "Open Documentation"
    bl_description = "Open online documentation"

    def execute(self, context):
        import webbrowser
        webbrowser.open("https://github.com/claymcdonald/frosty-mesh-tools/wiki")
        return {'FINISHED'}


# ============================================================================
# UI PANEL
# ============================================================================

class FROSTY_PT_main(Panel):
    bl_label = "Frosty Mesh Tools"
    bl_idname = "FROSTY_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Frosty Mesh"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.frosty_lod_settings

        # Tab selector
        row = layout.row(align=True)
        row.prop(settings, "active_tab", expand=True)

        layout.separator()

        if settings.active_tab == 'TEMPLATE':
            self.draw_template_tab(layout, context, settings)
        elif settings.active_tab == 'RENAME':
            self.draw_rename_tab(layout, context, settings)
        elif settings.active_tab == 'TRANSFORM':
            self.draw_transform_tab(layout, context, settings)
        elif settings.active_tab == 'EXPORT':
            self.draw_export_tab(layout, context, settings)

    def draw_template_tab(self, layout, context, settings):
        # Template folder
        box = layout.box()
        box.label(text="Templates Folder", icon='FILE_FOLDER')
        box.prop(settings, "samples_folder", text="")

        if settings.samples_folder:
            box.prop(settings, "selected_sample", text="")

        layout.separator()

        # Manual load
        box = layout.box()
        box.label(text="Or Load Directly", icon='IMPORT')
        box.operator("frosty.load_template", text="Browse mesh.res...", icon='FILEBROWSER')

        if settings.template_name:
            layout.separator()
            box = layout.box()
            box.label(text=f"Loaded: {settings.template_name}", icon='CHECKMARK')
            box.label(text=f"Materials: {len(settings.material_slots)}")
            box.label(text=f"Collection: {settings.template_name}", icon='OUTLINER_COLLECTION')

    def draw_rename_tab(self, layout, context, settings):
        if not settings.material_slots:
            layout.label(text="Load a template first", icon='INFO')
            return

        # Material slots with assign buttons
        box = layout.box()
        box.label(text="Material Assignments", icon='MATERIAL')

        for i, slot in enumerate(settings.material_slots):
            row = box.row(align=True)

            lod_info = f"[LOD {slot.min_lod}-{slot.max_lod}]"
            row.label(text=f"{slot.name} {lod_info}")

            if slot.mesh_object:
                row.label(text=slot.mesh_object.name, icon='MESH_DATA')
            else:
                row.operator("frosty.assign_mesh", text="Assign", icon='ADD').slot_index = i

        layout.separator()

        # Auto-rename toggle
        box = layout.box()
        box.label(text="Naming", icon='SORTALPHA')
        box.prop(settings, "auto_rename_meshes")

        layout.separator()

        # Rename button
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("frosty.rename_lods", text="Rename All LODs", icon='SORTALPHA')

    def draw_transform_tab(self, layout, context, settings):
        box = layout.box()
        box.label(text="Transform Fix", icon='OBJECT_DATA')

        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="Fixes transforms for Frosty import:")
        col.label(text="1. Unparent meshes (keep transform)")
        col.label(text="2. Apply all transforms")
        col.label(text="3. Rotate X -90, apply, rotate X +90")
        col.label(text="4. Re-parent to armature")

        layout.separator()

        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']

        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("frosty.fix_transforms", text=f"Fix Transforms ({len(selected_meshes)} meshes)", icon='OBJECT_DATA')

        if not selected_meshes:
            layout.label(text="Select mesh objects first", icon='ERROR')

    def draw_export_tab(self, layout, context, settings):
        # Export settings
        box = layout.box()
        box.label(text="Export Settings", icon='EXPORT')
        box.prop(settings, "export_path")
        box.prop(settings, "export_name")
        box.prop(settings, "export_scale")

        layout.separator()

        # Mesh count
        mesh_count = len(get_meshes_from_template_collection(settings))

        # Export button
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("frosty.export_fbx", text=f"Export FBX ({mesh_count} meshes)", icon='EXPORT')

        if mesh_count == 0:
            layout.label(text="No meshes in template collections", icon='ERROR')

        # Workflow info
        layout.separator()
        box = layout.box()
        box.label(text="Workflow:", icon='INFO')
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="1. Export FBX")
        col.label(text="2. In Frosty: Right-click MeshSet")
        col.label(text="3. Import the exported FBX")


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    MaterialSlotItem,
    FrostyLODSettings,
    FrostyPreferences,
    FROSTY_OT_load_template,
    FROSTY_OT_assign_mesh,
    FROSTY_OT_rename_lods,
    FROSTY_OT_fix_transforms,
    FROSTY_OT_export_fbx,
    FROSTY_OT_open_docs,
    FROSTY_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.frosty_lod_settings = PointerProperty(type=FrostyLODSettings)

    print(f"Frosty Mesh Tools v{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]} registered")


def unregister():
    del bpy.types.Scene.frosty_lod_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
