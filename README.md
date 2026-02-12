# Entropia Universe Icon Extractor

A standalone cross-platform tool for extracting item icons from Entropia Universe game cache.

<img src="icon.ico" width="64" height="64" alt="EU Icon Extractor">

## Version

**Current Version:** 1.0.1

## Download

**[Download Latest Release](https://github.com/ImpulsiveFPS/EU-Icon-Extractor/releases/latest)**

- **Windows:** `EU-Icon-Extractor-Windows.exe`
- **Linux:** `EU-Icon-Extractor-Linux`

No installation needed - just download and run!

## Description

Extract item icons from Entropia Universe cache and convert them to PNG format.

**Important:** Items must be seen/rendered in-game before they appear in the cache! If an icon is missing, view the item in your inventory or the auction first.

## Features

### Cross-Platform Support
- **Windows** - Auto-detects from Registry and standard paths
- **Linux** - Auto-detects Steam installations

### Multiple Cache Sources
- **Standard Install** - Detected from Windows Registry (`PublicUsersDataParentFolder`)
- **Steam** - Auto-detects from Steam library folders
- **Manual Browse** - Select custom cache folder
- **Extract from All** - Combine icons from multiple sources

### Extraction Options
- **Version selector** - Choose which game version to extract from
- **"All Folders" option** - Extract from all versions at once
- **320x320 PNG output** - Icons centered on transparent canvas
- **Multiple upscale methods** - HQ4x, Lanczos, or Nearest Neighbor

### User Interface
- **Source selection** - Choose between Standard, Steam, or All sources
- **Double-click preview** - Preview TGA files before extraction
- **Light/Dark theme** - Toggle between themes
- **Custom output folder** - Choose where to save extracted icons

## Usage

### Option 1: Download Executable (Recommended)
1. Download the appropriate executable for your OS from [Releases](https://github.com/ImpulsiveFPS/EU-Icon-Extractor/releases/latest)
2. Double-click to run - no installation needed!

### Option 2: Run from Source
```bash
python icon_extractor.py
```

#### Requirements
- Python 3.11+
- PyQt6: `pip install PyQt6`
- Pillow: `pip install Pillow`

## Cache Locations

### Windows
The tool automatically detects the cache location from the Windows Registry:
```
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\MindArk\Entropia Universe
PublicUsersDataParentFolder = C:\ProgramData\Entropia Universe
```

Full cache path: `{PublicUsersDataParentFolder}\public_users_data\cache\icon\{VERSION}`

### Linux (Steam)
The tool checks these Steam installation paths:
- `~/.steam/steam/`
- `~/.local/share/Steam/`
- `~/.steam/root/`

Full cache path: `{Steam}/steamapps/common/Entropia Universe/public_users_data/cache/icon/{VERSION}`

## Output

Icons are saved to your Documents folder:

**Windows:**
```
Documents\Entropia Universe\Icons\
```

**Linux:**
```
~/Documents/Entropia Universe/Icons/
```

(Same location where `chat.log` is normally stored)

## Links

- **Developer:** ImpulsiveFPS
- **Discord:** impulsivefps
- **GitHub:** https://github.com/ImpulsiveFPS/EU-Icon-Extractor
- **Report Bug:** https://github.com/ImpulsiveFPS/EU-Icon-Extractor/issues
- **Support Me:** https://ko-fi.com/impulsivefps

## Disclaimer

Entropia Universe Icon Extractor is a fan-made resource and is not affiliated with [MindArk PE AB](https://www.mindark.com/). [Entropia Universe](https://www.entropiauniverse.com/) is a trademark of MindArk PE AB.

## Building from Source

### Windows
```bash
# Install dependencies
pip install pyinstaller
pip install -r requirements.txt

# Build executable
pyinstaller icon_extractor.spec --clean
```

### Linux
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libgl1-mesa-glx libglib2.0-0 libxkbcommon-x11-0

# Install Python dependencies
pip install pyinstaller
pip install -r requirements.txt

# Build executable
pyinstaller icon_extractor.spec --clean
```

The executable will be in `dist/`

## License

MIT License - Feel free to use and modify!
