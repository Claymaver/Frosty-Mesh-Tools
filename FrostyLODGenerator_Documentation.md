# Frosty LOD Generator (Beta)

**Author:** Clay MacDonald  
**Blender Version:** 4.5+  
**Purpose:** Generate LOD meshes for Frostbite engine modding using mesh.res templates from Frosty Editor. Exports FBX files compatible with FrostMeshy conversion tool.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Complete Workflow](#complete-workflow)
4. [Panel Reference](#panel-reference)
5. [Preferences](#preferences)
6. [FrostMeshy Integration](#frostmeshy-integration)
7. [Troubleshooting](#troubleshooting)
8. [Technical Notes](#technical-notes)

---

## Installation

1. Download `frosty_lod_generator.py`
2. In Blender: **Edit → Preferences → Add-ons**
3. Click **Install...** and select the .py file
4. Enable the addon by checking the box
5. The panel appears in **3D View → Sidebar → Frosty LOD** tab

---

## Quick Start

1. **Export a mesh.res template** from Frosty Editor
2. **Import your custom mesh** into Blender
3. **Load the template** (Template tab)
4. **Assign your mesh** to material slots (Assign tab)
5. **Generate LODs** (Generate tab)
6. **Export FBX** (Export tab)

---

## Complete Workflow

### Step 1: Prepare Your Template

In Frosty Editor:
1. Find the asset you want to replace
2. Right-click → **Export**
3. Save to a "Samples" folder: `Samples/AssetName/assetname_mesh.res`

### Step 2: Prepare Your Mesh

In Blender:
1. Import or create your replacement mesh
2. Set up materials
3. If rigged, ensure armature is configured

### Step 3: Fix Transforms (if needed)

Use the **Tools tab**:
1. Select all meshes and armature
2. Click **Full Transform Prep**

This does:
- Clear parents (keep transforms)
- Apply all transforms
- Rotate -90° X, apply
- Rotate +90° X
- Re-parent to armature

### Step 4: Load Template

In the **Template tab**:
1. Set your **Samples Folder** path
2. Select template from dropdown
3. Or click **Browse...** to load manually

### Step 5: Assign Meshes

In the **Assign tab**:
1. Select a material slot from the list
2. Select your mesh in the viewport
3. Click **Assign Selected** or use the object picker
4. Repeat for each slot
5. Disable unused slots with the checkbox

### Step 6: Generate LODs

In the **Generate tab**:
1. Choose a **Preset** (High Quality recommended)
2. Adjust ratios if needed
3. Click **Generate LODs**

The addon will:
- Rename source mesh to `materialname:lod0`
- Create LOD1-5 with decimate modifiers
- Organize into collections (if enabled)

### Step 7: Fine-Tune (Optional)

- Adjust ratios → click **Update Ratios**
- Use **Isolate LOD** to preview each level
- Click **Apply All** when satisfied

### Step 8: Export

In the **Export tab**:
1. Set **Path** and **Name**
2. Keep **Scale** at 0.01
3. Click **Export FBX**

---

## Panel Reference

### Template Tab

| Element | Description |
|---------|-------------|
| **Samples Folder** | Folder containing template subfolders |
| **Template Dropdown** | Select from available templates |
| **Refresh** | Rescan samples folder |
| **Browse...** | Manually select mesh.res |
| **Last** | Reload last used template |

**Folder structure:**
```
Samples/
├── DarthVader/
│   └── darthvader_01_mesh.res
├── Stormtrooper/
│   └── stormtrooper_mesh.res
└── ...
```

### Assign Tab

| Element | Description |
|---------|-------------|
| **Material List** | Materials from template with LOD ranges |
| **Enable Checkbox** | Toggle material on/off |
| **Source Object** | Assigned mesh |
| **Assign Selected** | Assign active mesh to slot |
| **Clear** | Remove assignment |

### Generate Tab

| Element | Description |
|---------|-------------|
| **Preset** | Quick decimation presets |
| **LOD1 Ratio** | Ratio for LOD1 (0.5 = 50%) |
| **Ratio Step** | Decrease per level |
| **Preview** | Calculated ratios + poly counts |
| **Method** | Decimation algorithm |
| **Symmetry** | Preserve axis symmetry |
| **Generate LODs** | Create LOD meshes |
| **Update Ratios** | Update existing modifiers |
| **Apply All** | Bake modifiers |

**Presets:**
| Preset | LOD1 | LOD2 | LOD3 | LOD4 | LOD5 |
|--------|------|------|------|------|------|
| High Quality | 50% | 40% | 30% | 20% | 10% |
| Medium | 50% | 38% | 26% | 14% | 2% |
| Aggressive | 40% | 30% | 20% | 10% | 1% |

**Utilities:**
- **Select LOD 0-5** - Select meshes by LOD
- **Isolate LOD 0-5** - Hide all except that LOD
- **Show All** - Unhide all
- **Organize** - Sort into collections
- **Remove Generated** - Delete LOD1+ (keeps LOD0)

### Export Tab

| Element | Description |
|---------|-------------|
| **Path** | Export directory |
| **Name** | FBX filename |
| **Scale** | Export scale (0.01 for Frostbite) |
| **Export FBX** | Export all LODs |

### Tools Tab

**Transform Prep:**
- **Full Transform Prep** - Complete Frostbite transform fix
- **Check** - Validate transforms
- **Apply** - Apply all transforms

**Mesh Tools:**
- **Rename LOD0 Back** - Remove :lod0 suffix

---

## Preferences

Access: **Edit → Preferences → Add-ons → Frosty LOD Generator**

### Default Paths
- Default Samples Folder
- Default Export Path

### Default Export Settings
- Default Export Scale (0.01)

### Default Generation Settings
- Default Preset
- Default LOD1 Ratio / Ratio Step
- Default Decimation Method
- Default Symmetry

### Behavior
- Auto-Apply Defaults to New Scenes
- Remember Last Template
- Confirm Destructive Actions
- Auto-Organize LODs into Collections

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No materials found | Use `*_mesh.res`, not `blocks.res` |
| Wrong scale in-game | Export at 0.01 |
| Model sideways | Run Full Transform Prep |
| Missing LODs | Check naming `mat:lodN` |
| Decimate artifacts | Try different method or higher ratios |

---

## Technical Notes

### Parser
- Finds alphanumeric names (3+ chars) + null bytes
- Filters: numbers, `_lodN`, reserved words
- Looks 300 chars forward for `Mesh:path_lodN`

### LOD Naming
- `{material}:lod{level}`
- LOD0 = renamed source
- LOD1+ = duplicates with decimate

### FBX Export Settings
```
scale = 0.01
triangles = True
tangent_space = True
mesh_modifiers = True
deform_bones_only = True
bone_axis = Y-up
```

---

**Related Tools:** [Frosty Editor](https://github.com/CadeEvs/FrostyToolsuite/releases), FrostMeshy, [Blender](https://www.blender.org/)
