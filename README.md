# Frosty Mesh Tools

![Blender](https://img.shields.io/badge/blender-%23F5792A.svg?style=for-the-badge&logo=blender&logoColor=white)
![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
[![Status](https://img.shields.io/badge/Build_Status-Beta-red?style=for-the-badge)]()

A Blender addon for generating and exporting LOD (Level of Detail) meshes for **Frostbite engine modding** using Frosty Editor.

> Tested on Blender 4.5 & 5.0  
> Minimum Version: 4.0+

![Frosty Mesh Tools Panel](images/Preview.png)

---

## What It Does

- Loads `mesh.res` templates from Frosty Editor  
- Extracts material names and valid LOD ranges  
- Assigns meshes per material slot  
- Generates optimized LODs with configurable decimation  
- Exports FBX files ready for Frosty import  

No manual LOD setup. No guessing material names.

---

## Quick Workflow

1. Load `mesh.res` template  
2. Assign meshes to material slots  
3. Generate LODs  
4. Export FBX  
5. Import into Frosty  

---

## Requirements

- Blender 4.0+  
- Frosty Editor (for exporting `mesh.res` templates)

---

## Installation

1. Download `frosty_mesh_tools.py`  
2. Blender → Edit → Preferences → Add-ons  
3. Click **Install…** and select the file  
4. Enable the addon  
5. Find it in **3D View → Sidebar → Frosty Mesh**

---

## License

Free for personal and non-commercial use.  
See [LICENSE](LICENSE) for details.