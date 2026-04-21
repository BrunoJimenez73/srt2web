# SRT2Web Desktop Build System

This directory contains the build configuration and scripts for creating a desktop distribution of SRT2Web.

## Directory Structure

```
build/
├── icons/              # Icon variants for each platform
│   ├── 16x16.png
│   ├── 32x32.png
│   ├── 64x64.png
│   ├── 128x128.png
│   ├── 256x256.png
│   └── 512x512.png
├── installer.nsh       # Custom NSIS installer script
└── entitlements.mac   # macOS entitlements
```

## Creating Icons

### Option 1: Using ImageMagick (Recommended)

```bash
# Install ImageMagick
# Windows: choco install imagemagick
# macOS: brew install imagemagick
# Linux: apt install imagemagick

# Create icon from SVG
magick -background none icon.svg \
  -resize 16x16 build/icons/16x16.png \
  -resize 32x32 build/icons/32x32.png \
  -resize 64x64 build/icons/64x64.png \
  -resize 128x128 build/icons/128x128.png \
  -resize 256x256 build/icons/256x256.png \
  -resize 512x512 build/icons/512x512.png

# Create ICO for Windows
magick icon.svg -define icon:auto-resize=16,32,48,64,128,256 icon.ico

# Create ICNS for macOS (requires iconutil)
mkdir -p build/SRT2Web.iconset
for size in 16 32 64 128 256 512; do
    magick icon.svg -resize ${size}x${size} build/SRT2Web.iconset/icon_${size}x${size}.png
done
iconutil -c icns build/SRT2Web.iconset -o build/icon.icns
```

### Option 2: Using Online Converter

1. Design icon in Figma, Inkscape, or any design tool
2. Export as 512x512 PNG
3. Use [CloudConvert](https://cloudconvert.com/png-to-ico) for ICO
4. Use [CloudConvert](https://cloudconvert.com/png-to-icns) for ICNS

### Icon Requirements

| Platform | Format | Sizes |
|----------|--------|-------|
| Windows | ICO | 16, 32, 48, 64, 128, 256 |
| macOS | ICNS | 16, 32, 64, 128, 256, 512 |
| Linux | PNG | 16, 32, 48, 64, 128, 256, 512 |

## Build Commands

```bash
# Build for Windows
npm run build:win

# Build for macOS
npm run build:mac

# Build for Linux
npm run build:linux

# Build for all platforms
npm run build:all
```

## Verifying the Build

After building, the following files should be generated:

```
dist/
├── win-unpacked/              # Unpacked Windows app
│   └── SRT2Web.exe
├── SRT2Web-0.6.6 Setup.exe  # Windows installer
├── SRT2Web-0.6.6.dmg         # macOS disk image
├── SRT2Web-0.6.6.AppImage    # Linux AppImage
└── SRT2Web-0.6.6.deb        # Linux DEB package
```

## Troubleshooting

### Icon not appearing

1. Ensure icon files are in the correct format
2. Clear electron-builder cache: `rm -rf ~/.cache/electron-builder`
3. Run build again

### PyInstaller issues

If you encounter issues with PyInstaller bundling:

1. Test Python launcher separately:
   ```bash
   python src/python/launcher.py
   ```

2. Check FFmpeg is bundled:
   ```bash
   ls resources/ffmpeg/
   ```

### NSIS issues

If NSIS fails to create the installer:

1. Check NSIS version: `makensis -version`
2. Ensure `build/installer.nsh` is valid
3. Try with verbose output: `npm run build:win -- -c nsis.debug=true`

## Size Optimization

Typical sizes for the final installers:

| Platform | Format | Size |
|-----------|--------|------|
| Windows | NSIS | ~600-800 MB |
| macOS | DMG | ~500-700 MB |
| Linux | AppImage | ~500-700 MB |

The size is primarily due to:
- Python runtime (~15 MB)
- ML libraries (onnx, faster-whisper, etc.) (~400-500 MB)
- FFmpeg (~80 MB)
- Electron (~150 MB)

## Distribution

After building, upload to GitHub Releases:

1. Create a new release on GitHub
2. Tag version (e.g., `v0.6.6`)
3. Upload artifacts from `dist/` folder
4. The auto-updater will detect the new version