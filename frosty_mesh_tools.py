bl_info = {
    "name": "Frosty Mesh Tools",
    "author": "Clay MacDonald",
    "version": (3, 0, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Frosty Mesh",
    "description": "Generate LODs and export FBX meshes for Frostbite engine modding via Frosty Editor",
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
# CONSTANTS
# ============================================================================

MANAGED_PROP = "frosty_managed"
LOD_PROP = "frosty_lod_level"
MATERIAL_PROP = "frosty_material"

# ============================================================================
# TEMPLATE SCANNING (must be before PropertyGroup)
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


def on_preset_changed(self, context):
    settings = context.scene.frosty_lod_settings
    presets = {'HIGH': (0.50, 0.10), 'MEDIUM': (0.50, 0.12), 'AGGRESSIVE': (0.40, 0.10)}
    if settings.preset in presets:
        settings.lod1_ratio, settings.ratio_step = presets[settings.preset]

# ============================================================================
# PROPERTY GROUPS
# ============================================================================

class MaterialSlotItem(PropertyGroup):
    name: StringProperty(name="Material Name")
    enabled: BoolProperty(name="Enabled", default=True)
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
    
    # Material slots
    material_slots: CollectionProperty(type=MaterialSlotItem)
    active_slot_index: IntProperty()
    
    # LOD settings
    lod_count: IntProperty(name="LOD Count", default=4, min=1, max=8)
    lod1_ratio: FloatProperty(name="LOD1 Ratio", default=0.5, min=0.01, max=1.0)
    ratio_step: FloatProperty(name="Step", default=0.1, min=0.01, max=0.5)
    preset: EnumProperty(
        name="Quality Preset",
        items=[
            ('HIGH', "High Quality", "Less aggressive decimation"),
            ('MEDIUM', "Medium", "Balanced decimation"),
            ('AGGRESSIVE', "Aggressive", "More aggressive decimation"),
        ],
        default='MEDIUM',
        update=lambda s, c: on_preset_changed(s, c)
    )
    
    # Export settings
    export_path: StringProperty(name="Export Path", subtype='DIR_PATH', default="//")
    export_name: StringProperty(name="Export Name", default="mesh")
    export_scale: FloatProperty(name="Scale", default=1.0, min=0.001, max=100.0)
    export_filter: EnumProperty(
        name="Export Filter",
        items=[
            ('SLOTS', "Assigned Meshes", "Export meshes assigned to material slots"),
            ('VISIBLE', "Visible LODs", "Export all visible LOD meshes"),
            ('SELECTED', "Selected", "Export selected LOD meshes"),
            ('ALL', "All LODs", "Export all generated LOD meshes"),
        ],
        default='SLOTS'
    )
    
    # UI state
    active_tab: EnumProperty(
        name="Tab",
        items=[
            ('TEMPLATE', "Template", "Template loading"),
            ('LODS', "LODs", "LOD generation"),
            ('EXPORT', "Export", "FBX export"),
            ('SETTINGS', "Settings", "Addon settings"),
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
# TEMPLATE LOADING
# ============================================================================

def parse_mesh_res(filepath):
    """Extract material names and LOD info from mesh.res"""
    with open(filepath, 'rb') as f:
        data = f.read()

    text = data.decode('latin-1', errors='ignore')

    # Extract mesh path
    mesh_path_match = re.search(
        r'(?:characters|vehicles|weapons|props)/[^\x00]+?(?=_lod|\x00)',
        text
    )
    mesh_path = mesh_path_match.group(0) if mesh_path_match else ""

    lod_sections = {}
    
    # Strategy 1: Find "Mesh:path_lodN" patterns and extract nearby material names
    for lod_match in re.finditer(r'Mesh:[^\x00]+?_lod(\d+)', text):
        lod_num = int(lod_match.group(1))
        pos = lod_match.start()
        
        # Look backwards for material name (within 300 chars before)
        backward_text = text[max(0, pos - 300):pos]
        
        # Find null-terminated strings that look like material names
        for mat_match in re.finditer(r'([A-Za-z][A-Za-z0-9_]{2,})\x00', backward_text):
            mat_name = mat_match.group(1)
            
            # Skip common non-material names
            if mat_name.lower() in {"mesh", "material", "shader", "lod", "model", "section", "bone", "vertex"}:
                continue
            if re.search(r'_lod\d+$', mat_name, re.IGNORECASE):
                continue
            if mat_name.isdigit():
                continue
                
            lod_sections.setdefault(lod_num, [])
            if mat_name not in lod_sections[lod_num]:
                lod_sections[lod_num].append(mat_name)
    
    # Strategy 2: If no materials found, try forward search from material candidates
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
                # Also try _LOD pattern
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

    # Debug output
    if material_info:
        print(f"[FrostyMeshTools] Found {len(material_info)} materials:")
        for mat, (min_l, max_l) in sorted(material_info.items()):
            print(f"  {mat}: LOD {min_l}-{max_l}")
    else:
        print(f"[FrostyMeshTools] Warning: No materials with LOD info found in {filepath}")
        # Fallback: extract any plausible material names
        fallback_mats = set()
        for match in re.finditer(r'([A-Za-z][A-Za-z0-9_]{3,30})\x00', text):
            name = match.group(1)
            if name.lower() not in {"mesh", "material", "shader", "lod", "model", "section", "bone", "vertex", "index", "buffer", "texture", "normal", "tangent"}:
                if not re.search(r'_lod\d+$|^lod\d+$', name, re.IGNORECASE):
                    fallback_mats.add(name)
        
        if fallback_mats:
            print(f"[FrostyMeshTools] Using fallback - found {len(fallback_mats)} potential materials")
            for mat in sorted(fallback_mats)[:20]:  # Limit to first 20
                material_info[mat] = (0, 4)  # Default LOD range

    return material_info, lod_sections, mesh_path


def load_template(context, filepath):
    """Load a mesh.res template"""
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
    
    settings.material_slots.clear()
    for mat_name in sorted(material_info.keys()):
        min_lod, max_lod = material_info[mat_name]
        slot = settings.material_slots.add()
        slot.name = mat_name
        slot.min_lod = min_lod
        slot.max_lod = max_lod
        slot.enabled = True
    
    print(f"Loaded template: {settings.template_name} ({len(material_info)} materials)")
    return True, f"Loaded {len(material_info)} materials"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_armature(obj):
    """Find armature for an object"""
    if obj.parent and obj.parent.type == 'ARMATURE':
        return obj.parent
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            return mod.object
    return None


def get_generated_lods(filter_mode='SLOTS'):
    """Get all generated LOD meshes based on filter mode"""
    settings = bpy.context.scene.frosty_lod_settings
    
    valid_mat_names = {slot.name.lower() for slot in settings.material_slots if slot.enabled}
    
    lod_objects = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        if not obj.get(MANAGED_PROP, False):
            continue
        
        name_lower = obj.name.lower()
        
        if filter_mode == 'SLOTS':
            mat_part = name_lower.split(':')[0] if ':' in name_lower else name_lower
            if mat_part not in valid_mat_names:
                continue
        elif filter_mode == 'VISIBLE':
            if not obj.visible_get():
                continue
        elif filter_mode == 'SELECTED':
            if not obj.select_get():
                continue
        
        lod_objects.append(obj)
    
    return lod_objects


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
        
        # Assign mesh
        slot.mesh_object = obj
        obj[MANAGED_PROP] = True
        obj[LOD_PROP] = 0
        obj[MATERIAL_PROP] = slot.name
        
        # Auto-rename
        if settings.auto_rename_meshes:
            obj.name = f"{slot.name}:lod0"
        
        self.report({'INFO'}, f"Assigned '{obj.name}' to slot '{slot.name}'")
        return {'FINISHED'}


class FROSTY_OT_generate_lods(Operator):
    bl_idname = "frosty.generate_lods"
    bl_label = "Generate LODs"
    bl_description = "Generate LOD meshes for all assigned meshes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        
        generated_count = 0
        
        for slot in settings.material_slots:
            if not slot.enabled or not slot.mesh_object:
                continue
            
            base_obj = slot.mesh_object
            
            for lod_level in range(1, settings.lod_count):
                if lod_level < slot.min_lod or lod_level > slot.max_lod:
                    continue
                
                # Calculate decimation ratio
                ratio = settings.lod1_ratio
                for _ in range(lod_level - 1):
                    ratio -= settings.ratio_step
                ratio = max(0.01, ratio)
                
                # Create LOD copy
                new_mesh = base_obj.data.copy()
                new_obj = base_obj.copy()
                new_obj.data = new_mesh
                new_obj.name = f"{slot.name}:lod{lod_level}"
                
                # Link to collection
                context.collection.objects.link(new_obj)
                
                # Apply decimate modifier
                context.view_layer.objects.active = new_obj
                mod = new_obj.modifiers.new(name="Decimate", type='DECIMATE')
                mod.ratio = ratio
                bpy.ops.object.modifier_apply(modifier=mod.name)
                
                # Mark as managed
                new_obj[MANAGED_PROP] = True
                new_obj[LOD_PROP] = lod_level
                new_obj[MATERIAL_PROP] = slot.name
                
                generated_count += 1
        
        self.report({'INFO'}, f"Generated {generated_count} LOD meshes")
        return {'FINISHED'}


class FROSTY_OT_export_fbx(Operator):
    bl_idname = "frosty.export_fbx"
    bl_label = "Export FBX"
    bl_description = "Export meshes to FBX for import into Frosty Editor"
    
    @classmethod
    def poll(cls, context):
        settings = context.scene.frosty_lod_settings
        filter_mode = getattr(settings, 'export_filter', 'SLOTS')
        return len(get_generated_lods(filter_mode)) > 0
    
    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        filter_mode = getattr(settings, 'export_filter', 'SLOTS')
        lod_objects = get_generated_lods(filter_mode)
        
        view_layer_objects = set(context.view_layer.objects)
        lod_objects = [obj for obj in lod_objects if obj in view_layer_objects]
        
        if not lod_objects:
            self.report({'ERROR'}, "No LOD objects to export")
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
        
        # Export FBX
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


class FROSTY_OT_cleanup_lods(Operator):
    bl_idname = "frosty.cleanup_lods"
    bl_label = "Remove Generated LODs"
    bl_description = "Delete all generated LOD1+ meshes (keeps LOD0)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        count = 0
        
        for obj in list(bpy.data.objects):
            if obj.type != 'MESH':
                continue
            if not obj.get(MANAGED_PROP, False):
                continue
            
            lod_level = obj.get(LOD_PROP, 0)
            if lod_level > 0:
                bpy.data.objects.remove(obj, do_unlink=True)
                count += 1
        
        self.report({'INFO'}, f"Removed {count} LOD meshes")
        return {'FINISHED'}


class FROSTY_OT_clear_all(Operator):
    bl_idname = "frosty.clear_all"
    bl_label = "Clear All Assignments"
    bl_description = "Clear all mesh assignments from slots"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.frosty_lod_settings
        
        for slot in settings.material_slots:
            slot.mesh_object = None
        
        self.report({'INFO'}, "Cleared all assignments")
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
# UI PANELS
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
        
        # Draw active tab
        if settings.active_tab == 'TEMPLATE':
            self.draw_template_tab(layout, context, settings)
        elif settings.active_tab == 'LODS':
            self.draw_lods_tab(layout, context, settings)
        elif settings.active_tab == 'EXPORT':
            self.draw_export_tab(layout, context, settings)
        elif settings.active_tab == 'SETTINGS':
            self.draw_settings_tab(layout, context, settings)
    
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
    
    def draw_lods_tab(self, layout, context, settings):
        if not settings.material_slots:
            layout.label(text="Load a template first", icon='INFO')
            return
        
        # Material slots with LOD info
        box = layout.box()
        box.label(text="Material Assignments", icon='MATERIAL')
        
        for i, slot in enumerate(settings.material_slots):
            row = box.row(align=True)
            row.prop(slot, "enabled", text="")
            
            # Show material name with LOD range
            lod_info = f"[LOD {slot.min_lod}-{slot.max_lod}]"
            row.label(text=f"{slot.name} {lod_info}")
            
            if slot.mesh_object:
                row.label(text=slot.mesh_object.name, icon='MESH_DATA')
            else:
                row.operator("frosty.assign_mesh", text="Assign", icon='ADD').slot_index = i
        
        layout.separator()
        
        # LOD settings
        box = layout.box()
        box.label(text="LOD Settings", icon='MOD_DECIM')
        box.prop(settings, "preset")
        box.prop(settings, "lod_count")
        
        row = box.row(align=True)
        row.prop(settings, "lod1_ratio")
        row.prop(settings, "ratio_step")
        
        layout.separator()
        
        # Generate button
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("frosty.generate_lods", text="Generate LODs", icon='MOD_DECIM')
        
        layout.operator("frosty.cleanup_lods", text="Remove LODs", icon='TRASH')
    
    def draw_export_tab(self, layout, context, settings):
        # Export settings
        box = layout.box()
        box.label(text="Export Settings", icon='EXPORT')
        box.prop(settings, "export_path")
        box.prop(settings, "export_name")
        box.prop(settings, "export_scale")
        box.prop(settings, "export_filter")
        
        layout.separator()
        
        # Export button
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("frosty.export_fbx", text="Export FBX", icon='EXPORT')
        
        # Workflow info
        layout.separator()
        box = layout.box()
        box.label(text="Workflow:", icon='INFO')
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="1. Export FBX")
        col.label(text="2. In Frosty: Right-click MeshSet → Import")
    
    def draw_settings_tab(self, layout, context, settings):
        box = layout.box()
        box.label(text="Mesh Naming", icon='SORTALPHA')
        box.prop(settings, "auto_rename_meshes")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Help", icon='QUESTION')
        box.operator("frosty.open_docs", text="Open Documentation", icon='URL')
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Version", icon='INFO')
        version = bl_info.get("version", (0, 0, 0))
        box.label(text=f"Frosty Mesh Tools v{version[0]}.{version[1]}.{version[2]}")


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    MaterialSlotItem,
    FrostyLODSettings,
    FrostyPreferences,
    FROSTY_OT_load_template,
    FROSTY_OT_assign_mesh,
    FROSTY_OT_generate_lods,
    FROSTY_OT_export_fbx,
    FROSTY_OT_cleanup_lods,
    FROSTY_OT_clear_all,
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
