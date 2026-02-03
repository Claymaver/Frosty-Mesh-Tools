bl_info = {
    "name": "Frosty Mesh Tools (Beta)",
    "author": "Clay MacDonald",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Frosty Mesh",
    "description": "Generate LODs for Frostbite engine modding using mesh.res templates",
    "doc_url": "",
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
# ADDON PREFERENCES
# ============================================================================

class FrostyLODPreferences(AddonPreferences):
    bl_idname = __name__
    
    default_samples_folder: StringProperty(
        name="Default Samples Folder",
        default="",
        subtype='DIR_PATH'
    )
    
    default_export_path: StringProperty(
        name="Default Export Path",
        default="//",
        subtype='DIR_PATH'
    )
    
    default_export_scale: FloatProperty(
        name="Default Export Scale",
        default=0.01,
        min=0.001,
        max=1000.0
    )
    
    default_preset: EnumProperty(
        name="Default Preset",
        items=[
            ('HIGH', "High Quality", ""),
            ('MEDIUM', "Medium", ""),
            ('AGGRESSIVE', "Aggressive", ""),
            ('CUSTOM', "Custom", ""),
        ],
        default='HIGH'
    )
    
    default_lod1_ratio: FloatProperty(
        name="Default LOD1 Ratio",
        default=0.5,
        min=0.01, max=1.0,
        subtype='FACTOR'
    )
    
    default_ratio_step: FloatProperty(
        name="Default Ratio Step",
        default=0.1,
        min=0.01, max=0.5,
        subtype='FACTOR'
    )
    
    default_decimation_method: EnumProperty(
        name="Default Decimation Method",
        items=[
            ('COLLAPSE', "Collapse", ""),
            ('UNSUBDIV', "Un-Subdivide", ""),
            ('PLANAR', "Planar", ""),
        ],
        default='COLLAPSE'
    )
    
    default_symmetry: EnumProperty(
        name="Default Symmetry",
        items=[('NONE', "None", ""), ('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")],
        default='NONE'
    )
    
    auto_apply_defaults: BoolProperty(
        name="Auto-Apply Defaults to New Scenes",
        default=True
    )
    
    remember_last_template: BoolProperty(
        name="Remember Last Template",
        default=True
    )
    
    last_template_path: StringProperty(default="", options={'HIDDEN'})
    
    confirm_destructive: BoolProperty(
        name="Confirm Destructive Actions",
        default=True
    )
    
    auto_organize_collections: BoolProperty(
        name="Auto-Organize LODs into Collections",
        default=True
    )
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Default Paths", icon='FILE_FOLDER')
        box.prop(self, "default_samples_folder")
        box.prop(self, "default_export_path")
        
        box = layout.box()
        box.label(text="Default Export Settings", icon='EXPORT')
        box.prop(self, "default_export_scale")
        
        box = layout.box()
        box.label(text="Default Generation Settings", icon='MOD_DECIM')
        box.prop(self, "default_preset")
        row = box.row()
        row.prop(self, "default_lod1_ratio")
        row.prop(self, "default_ratio_step")
        row = box.row()
        row.prop(self, "default_decimation_method")
        row.prop(self, "default_symmetry")
        
        box = layout.box()
        box.label(text="Behavior", icon='PREFERENCES')
        box.prop(self, "auto_apply_defaults")
        box.prop(self, "remember_last_template")
        box.prop(self, "confirm_destructive")
        box.prop(self, "auto_organize_collections")
        
        layout.separator()
        row = layout.row()
        row.operator("frosty.apply_defaults_to_scene", icon='IMPORT')
        row.operator("frosty.reset_preferences", icon='LOOP_BACK')


class FROSTY_OT_apply_defaults_to_scene(Operator):
    bl_idname = "frosty.apply_defaults_to_scene"
    bl_label = "Apply Defaults to Scene"
    
    def execute(self, context):
        apply_defaults_to_scene(context)
        self.report({'INFO'}, "Applied default settings")
        return {'FINISHED'}


class FROSTY_OT_reset_preferences(Operator):
    bl_idname = "frosty.reset_preferences"
    bl_label = "Reset to Factory Defaults"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        prefs = get_prefs()
        prefs.default_samples_folder = ""
        prefs.default_export_path = "//"
        prefs.default_export_scale = 0.01
        prefs.default_preset = 'HIGH'
        prefs.default_lod1_ratio = 0.5
        prefs.default_ratio_step = 0.1
        prefs.default_decimation_method = 'COLLAPSE'
        prefs.default_symmetry = 'NONE'
        prefs.auto_apply_defaults = True
        prefs.remember_last_template = True
        prefs.confirm_destructive = True
        prefs.auto_organize_collections = True
        prefs.last_template_path = ""
        self.report({'INFO'}, "Reset preferences")
        return {'FINISHED'}


def get_prefs():
    return bpy.context.preferences.addons[__name__].preferences


def apply_defaults_to_scene(context):
    prefs = get_prefs()
    settings = context.scene.frosty_lod_settings
    
    if prefs.default_samples_folder:
        settings.samples_folder = prefs.default_samples_folder
    if prefs.default_export_path:
        settings.export_path = prefs.default_export_path
    
    settings.export_scale = prefs.default_export_scale
    settings.preset = prefs.default_preset
    settings.lod1_ratio = prefs.default_lod1_ratio
    settings.ratio_step = prefs.default_ratio_step
    settings.decimation_method = prefs.default_decimation_method
    settings.symmetry_axis = prefs.default_symmetry


# ============================================================================
# RES FILE HANDLING
# ============================================================================

def is_mesh_res_file(filepath):
    filename = os.path.basename(filepath).lower()
    if filename == 'blocks.res':
        return False
    if '_mesh.res' in filename:
        return True
    try:
        with open(filepath, 'rb') as f:
            data = f.read(8192)
        return 'Mesh:' in data.decode('latin-1', errors='ignore')
    except:
        return False


def scan_samples_folder(folder_path):
    templates = []
    if not folder_path or not os.path.exists(folder_path):
        return templates
    
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            for filename in os.listdir(item_path):
                if filename.endswith('.res') and filename.lower() != 'blocks.res':
                    filepath = os.path.join(item_path, filename)
                    if is_mesh_res_file(filepath):
                        templates.append((item, filepath))
                        break
    
    return sorted(templates, key=lambda x: x[0].lower())


def parse_mesh_res(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    text = data.decode('latin-1', errors='ignore')

    mesh_path_match = re.search(
        r'(?:characters|vehicles|weapons|props)/[^\x00]+?(?=_lod|\x00)',
        text
    )
    mesh_path = mesh_path_match.group(0) if mesh_path_match else ""

    lod_sections = {}

    for match in re.finditer(r'([A-Za-z0-9_]+)\x00', text):
        mat_name = match.group(1)

        if len(mat_name) < 3:
            continue
        if mat_name.isdigit():
            continue
        if re.search(r'_lod\d+$', mat_name, re.IGNORECASE):
            continue
        if mat_name.lower() in {"mesh", "material", "shader", "lod", "model"}:
            continue

        pos = match.start()
        forward_text = text[pos:pos + 300]

        lod_match = re.search(r'Mesh:[^\x00]+_lod(\d+)', forward_text)
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
        lods_with_mat = [
            lod for lod, mats in lod_sections.items() if mat in mats
        ]
        if lods_with_mat:
            material_info[mat] = (min(lods_with_mat), max(lods_with_mat))

    return material_info, lod_sections, mesh_path


# ============================================================================
# TEMPLATE LOADING
# ============================================================================

def load_template(context, filepath):
    settings = context.scene.frosty_lod_settings
    prefs = get_prefs()
    
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
    
    settings.material_slots.clear()
    for mat_name in sorted(material_info.keys()):
        min_lod, max_lod = material_info[mat_name]
        slot = settings.material_slots.add()
        slot.name = mat_name
        slot.min_lod = min_lod
        slot.max_lod = max_lod
        slot.enabled = True
    
    print(f"\n{'='*50}\nLOADED: {settings.template_name}\n{'='*50}")
    for mat in sorted(material_info.keys()):
        min_l, max_l = material_info[mat]
        print(f"  {mat}: LOD {min_l}-{max_l}")
    print('='*50 + "\n")
    
    return True, f"Loaded {len(material_info)} materials"


# ============================================================================
# SAMPLES DROPDOWN
# ============================================================================

_cached_samples = []
_cached_folder = ""

def get_sample_items(self, context):
    global _cached_samples, _cached_folder
    settings = context.scene.frosty_lod_settings
    
    if settings.samples_folder != _cached_folder:
        _cached_folder = settings.samples_folder
        _cached_samples = scan_samples_folder(settings.samples_folder)
    
    items = [('NONE', "-- Select Template --", "")]
    for display_name, filepath in _cached_samples:
        items.append((filepath, display_name, filepath))
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


def on_preset_changed(self, context):
    settings = context.scene.frosty_lod_settings
    presets = {'HIGH': (0.50, 0.10), 'MEDIUM': (0.50, 0.12), 'AGGRESSIVE': (0.40, 0.10)}
    if settings.preset in presets:
        settings.lod1_ratio, settings.ratio_step = presets[settings.preset]


# ============================================================================
# PROPERTY GROUPS
# ============================================================================

class FrostyMaterialSlot(PropertyGroup):
    name: StringProperty(name="Material Name")
    min_lod: IntProperty(name="Min LOD", default=0)
    max_lod: IntProperty(name="Max LOD", default=5)
    source_object: PointerProperty(name="Source Mesh", type=bpy.types.Object,
                                   poll=lambda self, obj: obj.type == 'MESH')
    enabled: BoolProperty(name="Enabled", default=True)


class FrostyLODSettings(PropertyGroup):
    
    ui_tab: EnumProperty(
        name="Tab",
        items=[
            ('TEMPLATE', "Template", "Load mesh.res template"),
            ('ASSIGN', "Assign", "Assign meshes to materials"),
            ('GENERATE', "Generate", "LOD generation settings"),
            ('EXPORT', "Export", "Export settings"),
            ('TOOLS', "Tools", "Mesh preparation tools"),
        ],
        default='TEMPLATE'
    )

    samples_folder: StringProperty(
        name="Samples Folder", 
        default="", 
        subtype='DIR_PATH',
        update=on_samples_folder_changed
    )
    selected_sample: EnumProperty(name="Template", items=get_sample_items, update=on_sample_selected)

    template_path: StringProperty(default="")
    template_mesh_path: StringProperty(default="")
    template_name: StringProperty(default="")

    material_slots: CollectionProperty(type=FrostyMaterialSlot)
    active_material_index: IntProperty(default=0)

    lod1_ratio: FloatProperty(name="LOD1 Ratio", default=0.5, min=0.01, max=1.0, subtype='FACTOR')
    ratio_step: FloatProperty(name="Ratio Step", default=0.1, min=0.01, max=0.5, subtype='FACTOR')

    preset: EnumProperty(
        name="Preset",
        items=[
            ('CUSTOM', "Custom", ""),
            ('HIGH', "High Quality", ""),
            ('MEDIUM', "Medium", ""),
            ('AGGRESSIVE', "Aggressive", ""),
        ],
        default='HIGH',
        update=on_preset_changed
    )

    decimation_method: EnumProperty(
        name="Method",
        items=[
            ('COLLAPSE', "Collapse", ""),
            ('UNSUBDIV', "Un-Subdivide", ""),
            ('PLANAR', "Planar", ""),
        ],
        default='COLLAPSE'
    )

    symmetry_axis: EnumProperty(
        name="Symmetry",
        items=[('NONE', "None", ""), ('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")],
        default='NONE'
    )

    export_path: StringProperty(name="Export Path", default="//", subtype='DIR_PATH')
    export_name: StringProperty(name="Export Name", default="mesh_export")
    export_scale: FloatProperty(name="Scale", default=0.01, min=0.001, max=1000.0)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

DECIMATE_MOD_NAME = "FrostyLOD_Decimate"

def calculate_ratio_for_lod(settings, lod_level):
    if lod_level == 0:
        return 1.0
    ratio = settings.lod1_ratio - (settings.ratio_step * (lod_level - 1))
    return max(ratio, 0.01)


def get_lod_level_from_name(name):
    match = re.search(r':lod(\d+)$', name.lower())
    return int(match.group(1)) if match else -1


def find_armature(obj):
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            return mod.object
    if obj.parent and obj.parent.type == 'ARMATURE':
        return obj.parent
    return None


def get_generated_lods():
    return [obj for obj in bpy.data.objects if obj.type == 'MESH' and ':lod' in obj.name.lower()]


def get_lods_with_modifiers():
    lods = []
    for obj in get_generated_lods():
        if DECIMATE_MOD_NAME in obj.modifiers:
            lods.append(obj)
    return lods


def get_slot_status(settings):
    enabled_slots = [s for s in settings.material_slots if s.enabled]
    assigned = sum(1 for s in enabled_slots if s.source_object and is_valid(s.source_object))
    return assigned, len(enabled_slots) - assigned, len(enabled_slots)


def is_valid(obj):
    if obj is None:
        return False
    try:
        _ = obj.name
        return True
    except ReferenceError:
        return False


def get_or_create_collection(name, parent=None):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    
    coll = bpy.data.collections.new(name)
    if parent:
        parent.children.link(coll)
    else:
        bpy.context.scene.collection.children.link(coll)
    return coll


def organize_lods_into_collections():
    lods = get_generated_lods()
    if not lods:
        return 0
    
    parent_coll = get_or_create_collection("LODs")
    
    lod_collections = {}
    for i in range(7):
        lod_collections[i] = get_or_create_collection(f"LOD{i}", parent_coll)
    
    moved = 0
    for obj in lods:
        lod_level = get_lod_level_from_name(obj.name)
        if lod_level < 0 or lod_level > 6:
            continue
        
        target_coll = lod_collections[lod_level]
        
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        
        target_coll.objects.link(obj)
        moved += 1
    
    return moved


def get_poly_counts_by_lod():
    counts = {}
    for obj in get_generated_lods():
        lod_level = get_lod_level_from_name(obj.name)
        if lod_level < 0:
            continue
        
        if DECIMATE_MOD_NAME in obj.modifiers:
            mod = obj.modifiers[DECIMATE_MOD_NAME]
            face_count = int(len(obj.data.polygons) * mod.ratio)
        else:
            face_count = len(obj.data.polygons)
        
        counts[lod_level] = counts.get(lod_level, 0) + face_count
    
    return counts


# ============================================================================
# OPERATORS
# ============================================================================

class FROSTY_OT_refresh_samples(Operator):
    bl_idname = "frosty.refresh_samples"
    bl_label = "Refresh"
    
    def execute(self, context):
        global _cached_folder
        _cached_folder = ""
        return {'FINISHED'}


class FROSTY_OT_load_template(Operator, ImportHelper):
    bl_idname = "frosty.load_template"
    bl_label = "Browse..."
    filter_glob: StringProperty(default="*_mesh.res;*.res", options={'HIDDEN'})
    
    def execute(self, context):
        if os.path.basename(self.filepath).lower() == 'blocks.res':
            self.report({'ERROR'}, "Select *_mesh.res, not blocks.res")
            return {'CANCELLED'}
        success, msg = load_template(context, self.filepath)
        self.report({'INFO' if success else 'ERROR'}, msg)
        return {'FINISHED'} if success else {'CANCELLED'}


class FROSTY_OT_load_last_template(Operator):
    bl_idname = "frosty.load_last_template"
    bl_label = "Load Last Template"
    
    @classmethod
    def poll(cls, context):
        prefs = get_prefs()
        return prefs.last_template_path and os.path.exists(prefs.last_template_path)
    
    def execute(self, context):
        prefs = get_prefs()
        success, msg = load_template(context, prefs.last_template_path)
        self.report({'INFO' if success else 'ERROR'}, msg)
        return {'FINISHED'} if success else {'CANCELLED'}


class FROSTY_OT_assign_selected(Operator):
    bl_idname = "frosty.assign_selected"
    bl_label = "Assign Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.frosty_lod_settings
        return settings.material_slots and context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        if settings.active_material_index < len(settings.material_slots):
            slot = settings.material_slots[settings.active_material_index]
            slot.source_object = context.active_object
            self.report({'INFO'}, f"Assigned → {slot.name}")
        return {'FINISHED'}


class FROSTY_OT_clear_assignment(Operator):
    bl_idname = "frosty.clear_assignment"
    bl_label = "Clear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        if settings.active_material_index < len(settings.material_slots):
            settings.material_slots[settings.active_material_index].source_object = None
        return {'FINISHED'}


class FROSTY_OT_generate_lods(Operator):
    bl_idname = "frosty.generate_lods"
    bl_label = "Generate LODs"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.frosty_lod_settings.material_slots) > 0

    def invoke(self, context, event):
        settings = context.scene.frosty_lod_settings
        assigned, unassigned, total = get_slot_status(settings)
        
        if assigned == 0:
            self.report({'ERROR'}, "No meshes assigned")
            return {'CANCELLED'}
        
        if unassigned > 0:
            return context.window_manager.invoke_props_dialog(self, width=300)
        
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.frosty_lod_settings
        assigned, unassigned, total = get_slot_status(settings)
        layout.label(text=f"Warning: {unassigned} slot(s) not assigned!", icon='ERROR')
        layout.label(text="Empty slots will be skipped. Continue?")

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        prefs = get_prefs()
        total_created = 0
        renamed_sources = 0
        
        generation_tasks = []
        for slot in settings.material_slots:
            if not slot.enabled or not slot.source_object or not is_valid(slot.source_object):
                continue
            generation_tasks.append({
                'source_obj': slot.source_object,
                'mat_name': slot.name,
                'min_lod': slot.min_lod,
                'max_lod': slot.max_lod,
            })
        
        if not generation_tasks:
            self.report({'ERROR'}, "No valid source meshes")
            return {'CANCELLED'}
        
        source_objects = {id(t['source_obj']) for t in generation_tasks}
        
        for obj in list(bpy.data.objects):
            if ':lod' in obj.name.lower() and obj.type == 'MESH':
                if id(obj) not in source_objects:
                    if not obj.name.lower().endswith(':lod0'):
                        mesh = obj.data
                        bpy.data.objects.remove(obj, do_unlink=True)
                        if mesh and mesh.users == 0:
                            bpy.data.meshes.remove(mesh)
        
        for task in generation_tasks:
            source_obj = task['source_obj']
            if not is_valid(source_obj):
                continue
            
            mat_name = task['mat_name']
            min_lod = task['min_lod']
            max_lod = task['max_lod']
            
            if min_lod == 0:
                lod0_name = f"{mat_name}:lod0"
                source_obj.name = lod0_name
                source_obj.data.name = lod0_name
                total_created += 1
                renamed_sources += 1
            
            for lod_level in range(max(1, min_lod), max_lod + 1):
                lod_name = f"{mat_name}:lod{lod_level}"
                
                bpy.ops.object.select_all(action='DESELECT')
                source_obj.select_set(True)
                context.view_layer.objects.active = source_obj
                bpy.ops.object.duplicate()

                lod_obj = context.active_object
                lod_obj.name = lod_name
                lod_obj.data = lod_obj.data.copy()
                lod_obj.data.name = lod_name

                ratio = calculate_ratio_for_lod(settings, lod_level)
                
                decimate = lod_obj.modifiers.new(name=DECIMATE_MOD_NAME, type='DECIMATE')
                decimate.decimate_type = settings.decimation_method
                decimate.ratio = ratio

                if settings.decimation_method == 'COLLAPSE':
                    decimate.use_collapse_triangulate = True
                    if settings.symmetry_axis != 'NONE':
                        decimate.use_symmetry = True
                        decimate.symmetry_axis = settings.symmetry_axis

                total_created += 1

        bpy.ops.object.select_all(action='DESELECT')
        for obj in get_generated_lods():
            obj.select_set(True)

        if prefs.auto_organize_collections:
            organize_lods_into_collections()

        self.report({'INFO'}, f"Generated {total_created} LODs ({renamed_sources} renamed)")
        return {'FINISHED'}


class FROSTY_OT_update_ratios(Operator):
    bl_idname = "frosty.update_ratios"
    bl_label = "Update Ratios"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(get_lods_with_modifiers()) > 0

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        updated = 0
        
        for obj in get_generated_lods():
            lod_level = get_lod_level_from_name(obj.name)
            if lod_level <= 0:
                continue
            
            mod = obj.modifiers.get(DECIMATE_MOD_NAME)
            if mod and mod.type == 'DECIMATE':
                new_ratio = calculate_ratio_for_lod(settings, lod_level)
                mod.ratio = new_ratio
                mod.decimate_type = settings.decimation_method
                
                if settings.decimation_method == 'COLLAPSE':
                    mod.use_collapse_triangulate = True
                    if settings.symmetry_axis != 'NONE':
                        mod.use_symmetry = True
                        mod.symmetry_axis = settings.symmetry_axis
                    else:
                        mod.use_symmetry = False
                
                updated += 1
        
        self.report({'INFO'}, f"Updated {updated} modifiers")
        return {'FINISHED'}


class FROSTY_OT_apply_modifiers(Operator):
    bl_idname = "frosty.apply_modifiers"
    bl_label = "Apply All Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(get_lods_with_modifiers()) > 0

    def invoke(self, context, event):
        prefs = get_prefs()
        if prefs.confirm_destructive:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        applied = 0
        
        for obj in get_generated_lods():
            mod = obj.modifiers.get(DECIMATE_MOD_NAME)
            if mod:
                context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=mod.name)
                applied += 1
        
        self.report({'INFO'}, f"Applied {applied} modifiers")
        return {'FINISHED'}


class FROSTY_OT_organize_collections(Operator):
    bl_idname = "frosty.organize_collections"
    bl_label = "Organize into Collections"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(get_generated_lods()) > 0

    def execute(self, context):
        moved = organize_lods_into_collections()
        self.report({'INFO'}, f"Organized {moved} LODs into collections")
        return {'FINISHED'}


class FROSTY_OT_export_fbx(Operator):
    bl_idname = "frosty.export_fbx"
    bl_label = "Export FBX"

    @classmethod
    def poll(cls, context):
        return len(get_generated_lods()) > 0

    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        lod_objects = get_generated_lods()

        armatures = set()
        for obj in lod_objects:
            arm = find_armature(obj)
            if arm and not arm.hide_viewport:
                armatures.add(arm)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in lod_objects:
            obj.select_set(True)
        for arm in armatures:
            arm.select_set(True)

        if lod_objects:
            context.view_layer.objects.active = lod_objects[0]

        export_dir = bpy.path.abspath(settings.export_path)
        os.makedirs(export_dir, exist_ok=True)

        filepath = os.path.join(export_dir, f"{settings.export_name or 'mesh'}.fbx")

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

        self.report({'INFO'}, f"Exported {len(lod_objects)} meshes to {filepath}")
        return {'FINISHED'}


class FROSTY_OT_cleanup_lods(Operator):
    bl_idname = "frosty.cleanup_lods"
    bl_label = "Remove Generated LODs (Keep LOD0)"
    bl_description = "Removes LOD1+ and keeps LOD0 (your source meshes)"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        prefs = get_prefs()
        if prefs.confirm_destructive:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        count = 0

        for obj in list(bpy.data.objects):
            if obj.type != 'MESH':
                continue

            name = obj.name.lower()

            if ':lod' in name and not name.endswith(':lod0'):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)

                if mesh and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)

                count += 1

        self.report({'INFO'}, f"Removed {count} LODs (kept LOD0)")
        return {'FINISHED'}


class FROSTY_OT_select_lod(Operator):
    bl_idname = "frosty.select_lod"
    bl_label = "Select"
    bl_options = {'REGISTER', 'UNDO'}
    lod_level: IntProperty(default=0)

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        count = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.name.lower().endswith(f':lod{self.lod_level}'):
                obj.select_set(True)
                count += 1
                if count == 1:
                    context.view_layer.objects.active = obj
        return {'FINISHED'}


class FROSTY_OT_isolate_lod(Operator):
    bl_idname = "frosty.isolate_lod"
    bl_label = "Isolate"
    bl_options = {'REGISTER', 'UNDO'}
    lod_level: IntProperty(default=0)

    def execute(self, context):
        for obj in bpy.data.objects:
            if ':lod' in obj.name.lower() and obj.type == 'MESH':
                obj.hide_viewport = not obj.name.lower().endswith(f':lod{self.lod_level}')
        return {'FINISHED'}


class FROSTY_OT_show_all(Operator):
    bl_idname = "frosty.show_all"
    bl_label = "Show All"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.data.objects:
            if ':lod' in obj.name.lower():
                obj.hide_viewport = False
        return {'FINISHED'}


class FROSTY_OT_open_preferences(Operator):
    bl_idname = "frosty.open_preferences"
    bl_label = "Preferences"
    
    def execute(self, context):
        bpy.ops.preferences.addon_show(module=__name__)
        return {'FINISHED'}


# ============================================================================
# TRANSFORM PREP TOOLS
# ============================================================================

class FROSTY_OT_prep_transforms(Operator):
    """Prepare mesh transforms for Frostbite (90° X rotation workflow)"""
    bl_idname = "frosty.prep_transforms"
    bl_label = "Prep Transforms for Frostbite"
    bl_description = "Full transform prep: clear parents, apply transforms, rotate -90/+90 on X, re-parent to armature"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type in {'MESH', 'ARMATURE'} for obj in context.selected_objects)

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        armature = None
        
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            for mesh in meshes:
                arm = find_armature(mesh)
                if arm:
                    armature = arm
                    break
        
        if not meshes:
            self.report({'ERROR'}, "No meshes selected")
            return {'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        for mesh in meshes:
            mesh.select_set(True)
        context.view_layer.objects.active = meshes[0]
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        if armature:
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        all_objects = meshes + ([armature] if armature else [])
        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objects:
            obj.select_set(True)
        context.view_layer.objects.active = all_objects[0]
        bpy.ops.transform.rotate(value=math.radians(-90), orient_axis='X')
        
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X')
        
        if armature:
            bpy.ops.object.select_all(action='DESELECT')
            for mesh in meshes:
                mesh.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.parent_set(type='ARMATURE')
        
        bpy.ops.object.select_all(action='DESELECT')
        for mesh in meshes:
            mesh.select_set(True)
        
        self.report({'INFO'}, f"Prepared transforms for {len(meshes)} meshes")
        return {'FINISHED'}


class FROSTY_OT_check_transforms(Operator):
    """Check if transforms are correctly set up for Frostbite"""
    bl_idname = "frosty.check_transforms"
    bl_label = "Check Transforms"

    def execute(self, context):
        issues = []
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not meshes:
            self.report({'WARNING'}, "No meshes selected")
            return {'CANCELLED'}
        
        for obj in meshes:
            if not all(abs(s - 1.0) < 0.001 for s in obj.scale):
                issues.append(f"{obj.name}: Scale not applied ({obj.scale[0]:.2f}, {obj.scale[1]:.2f}, {obj.scale[2]:.2f})")
            
            rot_x = math.degrees(obj.rotation_euler.x)
            if abs(rot_x - 90) > 1.0 and abs(rot_x) > 1.0:
                issues.append(f"{obj.name}: X rotation is {rot_x:.1f}° (expected ~90° or 0°)")
        
        if issues:
            self.report({'WARNING'}, f"Found {len(issues)} issues - see console")
            print("\n" + "="*50)
            print("TRANSFORM CHECK ISSUES:")
            print("="*50)
            for issue in issues:
                print(f"  ✗ {issue}")
            print("="*50 + "\n")
        else:
            self.report({'INFO'}, f"All {len(meshes)} meshes look good!")
        
        return {'FINISHED'}


class FROSTY_OT_apply_all_transforms(Operator):
    bl_idname = "frosty.apply_all_transforms"
    bl_label = "Apply All Transforms"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        self.report({'INFO'}, "Applied transforms")
        return {'FINISHED'}


class FROSTY_OT_rename_lod0_back(Operator):
    bl_idname = "frosty.rename_lod0_back"
    bl_label = "Rename LOD0 Back"
    bl_description = "Remove :lod0 suffix from LOD0 meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        renamed = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.name.lower().endswith(':lod0'):
                new_name = obj.name[:-5]
                obj.name = new_name
                obj.data.name = new_name
                renamed += 1
        
        self.report({'INFO'}, f"Renamed {renamed} meshes")
        return {'FINISHED'}


class FROSTY_OT_print_poly_counts(Operator):
    bl_idname = "frosty.print_poly_counts"
    bl_label = "Print Poly Counts"

    def execute(self, context):
        counts = get_poly_counts_by_lod()
        
        if not counts:
            self.report({'WARNING'}, "No LODs found")
            return {'CANCELLED'}
        
        print("\n" + "="*40)
        print("POLYGON COUNTS BY LOD")
        print("="*40)
        
        lod0_count = counts.get(0, 0)
        for lod in sorted(counts.keys()):
            count = counts[lod]
            if lod == 0:
                print(f"  LOD{lod}: {count:,} polys (100%)")
            else:
                pct = (count / lod0_count * 100) if lod0_count else 0
                print(f"  LOD{lod}: {count:,} polys ({pct:.1f}%)")
        
        print("="*40 + "\n")
        
        self.report({'INFO'}, f"Poly counts printed to console")
        return {'FINISHED'}


# ============================================================================
# UI LIST
# ============================================================================

class FROSTY_UL_material_slots(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        slot = item
        row = layout.row(align=True)
        row.prop(slot, "enabled", text="")
        sub = row.row(align=True)
        sub.active = slot.enabled
        sub.label(text=slot.name)
        sub.label(text=f"{slot.min_lod}-{slot.max_lod}")
        has_valid = slot.source_object and is_valid(slot.source_object)
        sub.label(text="", icon='CHECKMARK' if has_valid else 'BLANK1')


# ============================================================================
# UI PANEL
# ============================================================================

class FROSTY_PT_main(Panel):
    bl_label = "Frosty Mesh Tools"
    bl_idname = "FROSTY_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Frosty Mesh'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.frosty_lod_settings
        prefs = get_prefs()
        
        row = layout.row()
        row.label(text="v1.0-beta", icon='MODIFIER')
        row.operator("frosty.open_preferences", text="", icon='PREFERENCES')
        
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.prop_enum(settings, "ui_tab", 'TEMPLATE')
        row.prop_enum(settings, "ui_tab", 'ASSIGN')
        row.prop_enum(settings, "ui_tab", 'GENERATE')
        row.prop_enum(settings, "ui_tab", 'EXPORT')
        row.prop_enum(settings, "ui_tab", 'TOOLS')
        
        layout.separator()
        
        if settings.template_path:
            box = layout.box()
            row = box.row()
            row.label(text=f"Template: {settings.template_name}", icon='CHECKMARK')
            assigned, unassigned, total = get_slot_status(settings)
            if unassigned > 0:
                row.label(text=f"({unassigned} missing)", icon='ERROR')
            
            lods = get_generated_lods()
            live_mods = len(get_lods_with_modifiers())
            if lods:
                if live_mods > 0:
                    box.label(text=f"LODs: {len(lods)} ({live_mods} with live modifiers)", icon='MODIFIER')
                else:
                    box.label(text=f"LODs: {len(lods)} (applied)", icon='MESH_DATA')
        
        layout.separator()
        
        if settings.ui_tab == 'TEMPLATE':
            self.draw_template_tab(context, layout, settings, prefs)
        elif settings.ui_tab == 'ASSIGN':
            self.draw_assign_tab(context, layout, settings)
        elif settings.ui_tab == 'GENERATE':
            self.draw_generate_tab(context, layout, settings)
        elif settings.ui_tab == 'EXPORT':
            self.draw_export_tab(context, layout, settings)
        elif settings.ui_tab == 'TOOLS':
            self.draw_tools_tab(context, layout, settings)
    
    def draw_template_tab(self, context, layout, settings, prefs):
        box = layout.box()
        box.label(text="Samples Folder", icon='FILE_FOLDER')
        box.prop(settings, "samples_folder", text="")
        
        if settings.samples_folder and os.path.exists(settings.samples_folder):
            row = box.row(align=True)
            row.prop(settings, "selected_sample", text="")
            row.operator("frosty.refresh_samples", text="", icon='FILE_REFRESH')
        
        layout.separator()
        
        row = layout.row(align=True)
        row.operator("frosty.load_template", text="Browse...", icon='FILEBROWSER')
        if prefs.remember_last_template and prefs.last_template_path:
            row.operator("frosty.load_last_template", text="Last", icon='LOOP_BACK')
        
        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 0.85
        col.label(text="Setup:", icon='INFO')
        col.label(text="1. Set Samples folder")
        col.label(text="2. Pick template from dropdown")
        col.separator()
        col.label(text="Select *_mesh.res (not blocks.res)")
    
    def draw_assign_tab(self, context, layout, settings):
        if not settings.material_slots:
            layout.label(text="Load a template first", icon='INFO')
            return
        
        layout.template_list("FROSTY_UL_material_slots", "", settings, "material_slots",
                            settings, "active_material_index", rows=6)
        
        if settings.active_material_index < len(settings.material_slots):
            slot = settings.material_slots[settings.active_material_index]
            
            box = layout.box()
            box.label(text=f"{slot.name}", icon='MATERIAL')
            box.label(text=f"LOD Range: {slot.min_lod} - {slot.max_lod}")
            box.separator()
            box.prop(slot, "source_object", text="")
            row = box.row(align=True)
            row.operator("frosty.assign_selected", text="Assign Selected", icon='EYEDROPPER')
            row.operator("frosty.clear_assignment", text="", icon='X')
        
        assigned, unassigned, total = get_slot_status(settings)
        layout.label(text=f"Assigned: {assigned} / {total}", 
                    icon='CHECKMARK' if unassigned == 0 else 'ERROR')
    
    def draw_generate_tab(self, context, layout, settings):
        layout.prop(settings, "preset")
        
        col = layout.column(align=True)
        col.prop(settings, "lod1_ratio", slider=True)
        col.prop(settings, "ratio_step", slider=True)
        
        box = layout.box()
        box.label(text="Preview:", icon='VIEWZOOM')
        
        poly_counts = get_poly_counts_by_lod()
        
        row = box.row()
        col1 = row.column(align=True)
        col2 = row.column(align=True)
        col1.scale_y = 0.8
        col2.scale_y = 0.8
        
        for i in range(3):
            r = calculate_ratio_for_lod(settings, i)
            if i in poly_counts:
                col1.label(text=f"LOD{i}: {r*100:.0f}% ({poly_counts[i]:,})")
            else:
                col1.label(text=f"LOD{i}: {r*100:.0f}%")
        for i in range(3, 6):
            r = calculate_ratio_for_lod(settings, i)
            if i in poly_counts:
                col2.label(text=f"LOD{i}: {r*100:.0f}% ({poly_counts[i]:,})")
            else:
                col2.label(text=f"LOD{i}: {r*100:.0f}%")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Advanced", icon='PREFERENCES')
        box.prop(settings, "decimation_method")
        box.prop(settings, "symmetry_axis")
        
        layout.separator()
        
        row = layout.row()
        row.scale_y = 1.4
        row.operator("frosty.generate_lods", icon='MOD_DECIM')
        
        live_count = len(get_lods_with_modifiers())
        if live_count > 0:
            layout.separator()
            box = layout.box()
            box.label(text=f"{live_count} LODs with live modifiers", icon='MODIFIER')
            row = box.row(align=True)
            row.operator("frosty.update_ratios", text="Update Ratios", icon='FILE_REFRESH')
            row.operator("frosty.apply_modifiers", text="Apply All", icon='CHECKMARK')
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Utilities", icon='TOOL_SETTINGS')
        
        col = box.column(align=True)
        col.label(text="Select LOD:")
        row = col.row(align=True)
        for i in range(6):
            row.operator("frosty.select_lod", text=str(i)).lod_level = i
        
        col.separator()
        col.label(text="Isolate LOD:")
        row = col.row(align=True)
        for i in range(6):
            row.operator("frosty.isolate_lod", text=str(i)).lod_level = i
        col.operator("frosty.show_all", text="Show All")
        
        col.separator()
        row = col.row(align=True)
        row.operator("frosty.organize_collections", icon='OUTLINER_COLLECTION')
        row.operator("frosty.print_poly_counts", text="", icon='INFO')
        col.operator("frosty.cleanup_lods", text="Remove Generated LODs", icon='TRASH')
    
    def draw_export_tab(self, context, layout, settings):
        box = layout.box()
        box.label(text="Export Settings", icon='EXPORT')
        box.prop(settings, "export_path", text="Path")
        box.prop(settings, "export_name", text="Name")
        row = box.row()
        row.prop(settings, "export_scale")
        row.label(text="(0.01 = game)")
        
        lod_count = len(get_generated_lods())
        live_count = len(get_lods_with_modifiers())
        
        if live_count > 0:
            layout.label(text=f"Ready: {lod_count} LODs (modifiers applied on export)", icon='INFO')
        else:
            layout.label(text=f"Ready: {lod_count} LODs", icon='INFO')
        
        row = layout.row()
        row.scale_y = 1.4
        row.operator("frosty.export_fbx", icon='EXPORT')
        
        layout.label(text="Armatures included if assigned & visible", icon='INFO')
    
    def draw_tools_tab(self, context, layout, settings):
        box = layout.box()
        box.label(text="Transform Prep (Frostbite)", icon='ORIENTATION_GIMBAL')
        
        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("frosty.prep_transforms", text="Full Transform Prep", icon='CON_ROTLIKE')
        
        col.separator()
        row = col.row(align=True)
        row.operator("frosty.check_transforms", text="Check", icon='CHECKMARK')
        row.operator("frosty.apply_all_transforms", text="Apply", icon='OBJECT_DATA')
        
        box.separator()
        col = box.column(align=True)
        col.scale_y = 0.85
        col.label(text="Full prep does:")
        col.label(text="1. Clear parents (keep transform)")
        col.label(text="2. Apply all transforms")
        col.label(text="3. Rotate -90° X, apply")
        col.label(text="4. Rotate +90° X")
        col.label(text="5. Re-parent to armature")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Mesh Tools", icon='MESH_DATA')
        col = box.column(align=True)
        col.operator("frosty.rename_lod0_back", icon='LOOP_BACK')


# ============================================================================
# HANDLERS
# ============================================================================

@bpy.app.handlers.persistent
def on_load_post(dummy):
    try:
        prefs = get_prefs()
        if prefs.auto_apply_defaults:
            apply_defaults_to_scene(bpy.context)
    except:
        pass


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    FrostyLODPreferences,
    FROSTY_OT_apply_defaults_to_scene,
    FROSTY_OT_reset_preferences,
    FrostyMaterialSlot,
    FrostyLODSettings,
    FROSTY_OT_refresh_samples,
    FROSTY_OT_load_template,
    FROSTY_OT_load_last_template,
    FROSTY_OT_assign_selected,
    FROSTY_OT_clear_assignment,
    FROSTY_OT_generate_lods,
    FROSTY_OT_update_ratios,
    FROSTY_OT_apply_modifiers,
    FROSTY_OT_organize_collections,
    FROSTY_OT_export_fbx,
    FROSTY_OT_cleanup_lods,
    FROSTY_OT_select_lod,
    FROSTY_OT_isolate_lod,
    FROSTY_OT_show_all,
    FROSTY_OT_open_preferences,
    FROSTY_OT_prep_transforms,
    FROSTY_OT_check_transforms,
    FROSTY_OT_apply_all_transforms,
    FROSTY_OT_rename_lod0_back,
    FROSTY_OT_print_poly_counts,
    FROSTY_UL_material_slots,
    FROSTY_PT_main,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.frosty_lod_settings = bpy.props.PointerProperty(type=FrostyLODSettings)
    bpy.app.handlers.load_post.append(on_load_post)

def unregister():
    bpy.app.handlers.load_post.remove(on_load_post)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.frosty_lod_settings

if __name__ == "__main__":
    register()
