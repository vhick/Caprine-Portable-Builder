"""Validate final artifact layout without exposing any user session data."""
import sys
import zipfile

if len(sys.argv) != 2:
    raise SystemExit('Usage: python builder/verify_zip.py <archive.zip>')
with zipfile.ZipFile(sys.argv[1]) as z:
    missing = z.testzip()
    if missing:
        raise SystemExit(f'Corrupted ZIP member: {missing}')
    names = set(z.namelist())
    required = {
        'CaprinePortable/CaprinePortable.exe',
        'CaprinePortable/App/Caprine/Caprine.exe',
        'CaprinePortable/App/Caprine/resources/app.asar',
        'CaprinePortable/App/AppInfo/appinfo.ini',
        'CaprinePortable/App/AppInfo/appicon.ico',
        'CaprinePortable/Data/KEEP-DATA-ON-UPDATE.txt',
    }
    required.update('CaprinePortable/App/AppInfo/appicon_%s.png' % s for s in [16, 32, 75, 128, 256])
    if required - names:
        raise SystemExit('Missing required paths: ' + ', '.join(sorted(required - names)))
    if len(z.read('CaprinePortable/CaprinePortable.exe')) < 100:
        raise SystemExit('Suspiciously small launcher executable')
    for name in names:
        if name.startswith('CaprinePortable/Data/') and not name.endswith('KEEP-DATA-ON-UPDATE.txt'):
            raise SystemExit('Unexpected content in Data: ' + name)
print('Portable ZIP passes layout, archive and empty-data checks')
