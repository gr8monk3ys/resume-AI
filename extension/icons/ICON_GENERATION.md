# Icon Generation

The placeholder icons in this directory are minimal blue squares. Replace them with proper branded icons before publishing.

## Requirements

Chrome extensions require PNG icons in these sizes:
- `icon16.png` - 16x16 pixels (toolbar, favicon)
- `icon48.png` - 48x48 pixels (extension management page)
- `icon128.png` - 128x128 pixels (Chrome Web Store, installation)

## Generating Icons

### Option 1: From SVG (using ImageMagick)

```bash
# Install ImageMagick if needed
# brew install imagemagick  # macOS
# sudo apt install imagemagick  # Ubuntu

# Convert SVGs to PNGs
convert -background none icon16.svg icon16.png
convert -background none icon48.svg icon48.png
convert -background none icon128.svg icon128.png
```

### Option 2: From a single high-res source

```bash
# Start with a 512x512 or larger source image
convert source.png -resize 16x16 icon16.png
convert source.png -resize 48x48 icon48.png
convert source.png -resize 128x128 icon128.png
```

### Option 3: Using online tools

1. Create or upload your icon to https://favicon.io or similar
2. Download the icon pack
3. Rename files to match the required names

## Design Guidelines

- Use simple, recognizable shapes
- Ensure readability at 16x16 size
- Use the ResuBoost brand colors (#2563eb primary blue)
- Consider both light and dark browser themes
- Follow Chrome's extension icon guidelines
