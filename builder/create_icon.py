"""Build the launcher icon from official Caprine source artwork at the selected tag."""
from pathlib import Path
from PIL import Image

source = Path('upstream/build/icon.png')
if not source.is_file():
    raise SystemExit('Official upstream build/icon.png is missing; cannot use a generic icon')
with Image.open(source) as image:
    image.convert('RGBA').save('build-icon.ico', format='ICO', sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
print('Prepared build-icon.ico from official upstream Caprine icon.png')
