# Frosty Mesh Tools

![Blender](https://img.shields.io/badge/blender-%23F5792A.svg?style=for-the-badge&logo=blender&logoColor=white)
![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
[![Status](https://img.shields.io/badge/Build_Status-Beta-red?style=for-the-badge)]()

A Blender addon for generating LOD (Level of Detail) meshes for Frostbite engine modding. Works with mesh.res templates exported from Frosty Editor.

> **Tested on:** Blender 4.5 and 5.0  
> **May work on:** Other versions (untested)

![Frosty Mesh Tools Panel](https://via.placeholder.com/600x400?text=Screenshot+Coming+Soon)

## Features

- **Template-Based Workflow** - Load mesh.res files from Frosty Editor to get exact material/LOD structure
- **Non-Destructive Decimation** - Live decimate modifiers for real-time adjustment
- **Transform Prep Tools** - One-click Frostbite coordinate system fix
- **LOD Collections** - Auto-organize meshes into LOD0, LOD1, etc. collections
- **Configurable Presets** - High Quality, Medium, and Aggressive decimation presets
- **Preferences System** - Save default paths and settings

## Requirements

- Blender 4.5 or newer (tested on 4.5 and 5.0)
- [Frosty Editor](https://github.com/CadeEvs/FrostyToolsuite/releases) - For exporting mesh.res templates

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
4. EXPORT    →  FBX at 0.01 scale
```

## Documentation
<<<<<<< Updated upstream
=======



## Contributing
>>>>>>> Stashed changes

- 📖 [Full Documentation](docs/FrostyMeshTools_Documentation.md) - Complete workflow and reference

## License

**Free for personal and non-commercial use.** See [LICENSE](LICENSE) for full terms.

- ✅ Free to use
- ✅ Modify for personal use
- ❌ No selling
- ❌ No commercial use
- ❌ No redistributing modified versions

## Credits

**Author:** Clay MacDonald

---

## Changelog

### v1.0-beta
- Initial beta release
- Template-based LOD generation
- Non-destructive decimation workflow
- Transform prep tools for Frostbite
- LOD collection organization
- Addon preferences system
