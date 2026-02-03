# Contributing to Frosty Mesh Tools

Thanks for your interest in contributing! This project is currently in **beta**, so bug reports and feedback are especially valuable.

## Ways to Contribute

### 🐛 Bug Reports

Found a bug? Please open an issue with:

- **Blender version** (e.g., 4.5.0, 5.0.0)
- **Addon version** (shown in panel header)
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Error messages** (check Blender's console: Window → Toggle System Console)
- **Screenshots** if helpful

### 💡 Feature Requests

Have an idea? Open an issue with:

- Clear description of the feature
- Use case / why it would be helpful
- Any mockups or examples (optional)

### 🔧 Code Contributions

1. **Fork** the repository
2. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Test** in Blender 4.5+ 
5. **Commit** with clear messages:
   ```bash
   git commit -m "Add: description of feature"
   git commit -m "Fix: description of bug fix"
   ```
6. **Push** to your fork
7. **Open a Pull Request**

## Code Style

- Follow existing code patterns in the addon
- Use clear, descriptive variable names
- Add comments for complex logic
- Keep operators focused on single tasks
- Test with multiple mesh.res templates if possible

## Testing Checklist

Before submitting a PR, please test:

- [ ] Template loading (samples folder + manual browse)
- [ ] Mesh assignment
- [ ] LOD generation with different presets
- [ ] Update Ratios functionality
- [ ] Apply All modifiers
- [ ] FBX export
- [ ] Transform Prep tools
- [ ] Collection organization
- [ ] Cleanup (Remove Generated LODs)

## Questions?

Open an issue with the **question** label if you need help or clarification.

## License Note

By contributing to this project, you agree that your contributions will be licensed under the same terms as the project (free, non-commercial use only). See [LICENSE](LICENSE) for details.

---

Thanks for helping improve Frosty Mesh Tools!
