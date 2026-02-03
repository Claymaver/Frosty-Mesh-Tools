# Frosty Mesh Tools

[![Blender](https://img.shields.io/badge/blender-%23F5792A.svg?style=flat-square&logo=blender&logoColor=white)](https://www.blender.org/)
[![Code](https://img.shields.io/badge/Python-FFD43B?style=flat-square&logo=python&logoColor=blue)](https://www.python.org/)
[![Status](https://img.shields.io/badge/build-beta-yellow?style=flat-square)]()


A Blender addon for generating LOD (Level of Detail) meshes for Frostbite engine modding. Works with mesh.res templates exported from Frosty Editor.

> **Tested on:** Blender 4.5 and 5.0  
> **May work on:** Other versions (untested)

![Frosty Mesh Tools Panel](https://via.placeholder.com/600x400?text=Screenshot+Coming+Soon)

## Features

- **Template-Based Workflow** - Load mesh.res files from Frosty Editor to get exact material/LOD structure
- **Non-Destructive Decimation** - Live decimate modifiers for iterative adjustment
- **Transform Prep Tools** - One-click Frostbite coordinate system fix
- **LOD Collections** - Auto-organize meshes into LOD0, LOD1, etc. collections
- **Configurable Presets** - High Quality, Medium, and Aggressive decimation presets
- **Preferences System** - Save default paths and settings

## Requirements

- Blender 4.5 or newer (tested on 4.5 and 5.0)
- [Frosty Editor](https://frostyeditor.com/) - For exporting mesh.res templates

## Installation

1. Download the latest release (`frosty_mesh_tools.py`)
2. In Blender: **Edit → Preferences → Add-ons**
3. Click **Install...** and select the downloaded file
4. Enable the addon by checking the box
5. Find the panel in **3D View → Sidebar → Frosty Mesh**

## Quick Start

```
1. TEMPLATE  →  Load mesh.res from Frosty Editor export
2. ASSIGN    →  Assign your meshes to material slots
3. GENERATE  →  Create LODs with decimation
4. EXPORT
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

**Free for personal and non-commercial use.** See [LICENSE](LICENSE) for full terms.

- ✅ Free to use
- ✅ Modify for personal use
- ❌ No selling
- ❌ No commercial use
- ❌ No redistributing modified versions

## Credits

**Author:** Clay MacDonald

**Related Tools:**
- [Frosty Editor](https://frostyeditor.com/)

---

## Changelog

### v1.0-beta
- Initial beta release
- Template-based LOD generation
- Non-destructive decimation workflow
- Transform prep tools for Frostbite
- LOD collection organization
- Addon preferences system
- Full documentation
=======
# Frosty Mesh Tools v1.0-beta

**Author:** Clay MacDonald  
<<<<<<<< HEAD:docs/FrostyMeshTools_Documentation.md
**Blender Version:** 4.5+ (tested on 4.5 and 5.0, may work on other versions)  
**Status:** Beta - Testing Phase  
========
**Blender Version:** 4.5+  
>>>>>>>> a657b2885a9d79b733aa429c004b76cee6409f1c:README.md
**Purpose:** Generate LOD meshes for Frostbite engine modding using mesh.res templates from Frosty Editor.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Complete Workflow](#complete-workflow)
4. [Panel Reference](#panel-reference)
5. [Preferences](#preferences)
6. [Troubleshooting](#troubleshooting)
7. [Technical Notes](#technical-notes)

---

## Installation

1. Download `frosty_mesh_tools.py`
2. In Blender: **Edit → Preferences → Add-ons**
3. Click **Install...** and select the .py file
4. Enable the addon by checking the box
5. The panel appears in **3D View → Sidebar → Frosty Mesh** tab

---

## Quick Start

1. **Export a mesh.res template** from Frosty Editor
2. **Import your custom mesh** into Blender
3. **Load the template** (Template tab)
4. **Assign your mesh** to material slots (Assign tab)
5. **Generate LODs** (Generate tab)
6. **Export FBX** (Export tab)

---

## Version History

- **v1.0-beta** - Initial beta release for testing
  - Template-based LOD generation
  - Non-destructive decimation workflow
  - Transform prep tools for Frostbite
  - LOD collection organization
  - Addon preferences system

---

**Related Tools:** [Frosty Editor](https://github.com/CadeEvs/FrostyToolsuite/releases)
