## OpenAction Plugin Registry

This repository serves as the official registry and catalogue for OpenAction plugins.

### Project Structure

- `catalogue.json`: The central registry file containing metadata for all available plugins.
- `icons/`: A directory containing the formatted icons for the plugins.
- `format_icons.py` & `update_descriptions.py`: Python utility scripts used for maintaining the registry, fetching updates, and formatting assets.
- `pyproject.toml`: Python project configuration and dependencies for the utility scripts.

### Submitting a Plugin

To submit your plugin to the OpenAction Marketplace, please follow these steps:

1. **Add the Repository Tag**: Add the `openaction` topic/tag to your plugin's repository on GitHub.
2. **Update the Catalogue**: Fork this repository and add an entry for your plugin to the `catalogue.json` file.
    - The key should be your plugin's **bundle ID**.
    - The `name` and `author` fields must exactly match the values in your plugin's manifest file.
    - The `description` field should match the sidebar description of your plugin's GitHub repository.
3. **Correct Placement**: Ensure your entry is added to the correct logical section in `catalogue.json`. The catalog is organized in the following order:
    1. **Official plugins from the OpenAction project**
    2. **Native OpenAction plugins** (probably where you want to add your plugin)
    3. **Device support plugins**
    4. **Open-source Stream Deck plugins**

    *Note: Within each individual section, plugins are sorted alphabetically by their GitHub repository URL.*
4. **Add an Icon**: Add a high-resolution icon representing your plugin to the `icons/` directory. The icon should match the icon provided in your plugin's manifest / bundle. The file should be named matching your plugin's bundle ID (e.g. `com.yourname.plugin.png`). *Note: You do not need to run the `format_icons.py` script yourself; a maintainer will run it in a standardised environment to format your icon when reviewing your submission.*

Once you have added your entry to the appropriate section, submit a Pull Request to this repository for review.

### Alternative Method (The Easy Way)

If you prefer an easier route, simply get in contact with us via Matrix, Discord, or by opening a GitHub Issue in this repository. Drop your plugin's repository URL, and a maintainer will add the plugin for you!
