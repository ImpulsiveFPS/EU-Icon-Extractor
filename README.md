# Entropia Universe Icon Extractor

A standalone tool for extracting item icons from Entropia Universe game cache.

<img src="icon.ico" width="64" height="64" alt="EU Icon Extractor">

## Description

Extract item icons from Entropia Universe cache and convert them to PNG format.

**Important:** Items must be seen/rendered in-game before they appear in the cache! If an icon is missing, view the item in your inventory or the auction first.

## Usage

```bash
python icon_extractor.py
```

### Requirements
- Python 3.11+
- PyQt6: `pip install PyQt6`
- Pillow: `pip install Pillow`

## Features

- **Auto-detects** game cache from `C:\ProgramData\Entropia Universe\public_users_data\cache\icon`
- **Version selector** - Choose which game version to extract from
- **"All Folders" option** - Extract from all versions at once
- **Double-click preview** - Preview TGA files before extraction
- **320x320 PNG output** - Icons centered on transparent canvas
- **Light/Dark theme** - Toggle between themes
- **Custom output folder** - Choose where to save extracted icons

## Output

Icons are saved to your Documents folder:
```
Documents\Entropia Universe\Icons\
```

(Same location where `chat.log` is normally stored)

## Links

- **Developer:** ImpulsiveFPS
- **Discord:** impulsivefps
- **GitHub:** https://github.com/ImpulsiveFPS/EU-Icon-Extractor
- **Support Me:** https://ko-fi.com/impulsivefps

## Disclaimer

Entropia Universe Icon Extractor is a fan-made resource and is not affiliated with [MindArk PE AB](https://www.mindark.com/). [Entropia Universe](https://www.entropiauniverse.com/) is a trademark of MindArk PE AB.

## License

MIT License - Feel free to use and modify!
