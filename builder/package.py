"""Package a tagged, built Caprine app into the required PortableApps ZIP layout.

This script deliberately includes no user sessions, credentials, or personal Data.
"""
from __future__ import annotations
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image

SIZES = (16, 32, 75, 128, 256)


def package(root: Path, version: str, arch: str, dest: Path):
    if version != '2.62.0' or arch != 'x64':
        raise ValueError('Only Caprine v2.62.0 Windows x64 is reviewed by this builder')
    upstream = root / 'upstream'
    frozen = upstream / 'dist' / 'win-unpacked'
    exe = frozen / 'Caprine.exe'
    asar = frozen / 'resources' / 'app.asar'
    icon_source = upstream / 'build' / 'icon.png'
    license_source = upstream / 'license'
    for path in (exe, asar, icon_source, license_source):
        if not path.is_file():
            raise FileNotFoundError(f'Missing expected upstream build file: {path}')
    root_app = root / 'stage' / 'CaprinePortable'
    if root_app.exists():
        shutil.rmtree(root_app)
    app = root_app / 'App' / 'Caprine'
    shutil.copytree(frozen, app)
    appinfo = root_app / 'App' / 'AppInfo'
    appinfo.mkdir(parents=True, exist_ok=True)
    data = root_app / 'Data'
    data.mkdir(parents=True, exist_ok=True)
    (data / 'KEEP-DATA-ON-UPDATE.txt').write_text(
        'Caprine saves settings, browser session, cookies and downloaded files in this Data folder. '\
        'Never delete or overwrite it when updating. Never upload a used Data folder to GitHub.\n', encoding='utf-8')
    other = root_app / 'Other' / 'Source'
    other.mkdir(parents=True)
    shutil.copy2(license_source, other / 'LICENSE.txt')
    (other / 'BUILD-INFO.txt').write_text(
        f'Based on https://github.com/bankjaneo/caprine tag v{version}.\n'
        'Windows x64, community source modifications for portable storage and renderer isolation.\n'
        'This is an unofficial community build. Root launcher compiled from included source.\n', encoding='utf-8')

    image = Image.open(icon_source).convert('RGBA')
    image.save(appinfo / 'appicon.ico', format='ICO', sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
    for size in SIZES:
        image.resize((size, size), Image.Resampling.LANCZOS).save(appinfo / f'appicon_{size}.png')
    text = f'''[Format]\nType=PortableApps.comFormat\nVersion=3.9\n\n[Details]\nName=Caprine Portable\nAppID=CaprinePortable\nPublisher=bankjaneo Caprine contributors and community packager\nHomepage=https://github.com/bankjaneo/caprine\nCategory=Internet\nDescription=Unofficial Facebook Messenger desktop application, locally packaged for portable use.\nLanguage=Multilingual\n\n[License]\nShareable=true\nOpenSource=true\nFreeware=true\nCommercialUse=true\n\n[Version]\nPackageVersion={version}.0\nDisplayVersion={version}\n\n[Control]\nIcons=1\nStart=CaprinePortable.exe\n'''
    (appinfo / 'appinfo.ini').write_text(text, encoding='utf-8')
    # Launcher is compiled separately on Windows with the exact official icon.
    launcher = root / 'CaprinePortable.exe'
    if not launcher.is_file():
        raise FileNotFoundError('Windows launcher compilation failed: missing CaprinePortable.exe')
    shutil.copy2(launcher, root_app / 'CaprinePortable.exe')
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / f'Caprine-v{version}-Win-{arch}-Portable.zip'
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zipf:
        for file in root_app.rglob('*'):
            if file.is_file():
                zipf.write(file, file.relative_to(root_app.parent).as_posix())
    with zipfile.ZipFile(archive) as zipf:
        names = set(zipf.namelist())
        expected = {
            'CaprinePortable/CaprinePortable.exe',
            'CaprinePortable/App/Caprine/Caprine.exe',
            'CaprinePortable/App/Caprine/resources/app.asar',
            'CaprinePortable/App/AppInfo/appinfo.ini',
            'CaprinePortable/App/AppInfo/appicon.ico',
            'CaprinePortable/Data/KEEP-DATA-ON-UPDATE.txt',
        }
        expected.update(f'CaprinePortable/App/AppInfo/appicon_{size}.png' for size in SIZES)
        if not expected.issubset(names):
            raise RuntimeError('Incomplete ZIP: ' + ', '.join(sorted(expected - names)))
        if any('/App/Caprine/' in path and ('userData' in path or 'Cookies' in path) for path in names):
            raise RuntimeError('Unexpected user-data content in packaged App directory')
    print(f'Created {archive} ({archive.stat().st_size:,} bytes)')
    return archive


if __name__ == '__main__':
    argp = argparse.ArgumentParser()
    argp.add_argument('--root', type=Path, default=Path('.'))
    argp.add_argument('--version', default='2.62.0')
    argp.add_argument('--arch', default='x64')
    argp.add_argument('--out', type=Path, default=Path('artifacts'))
    args = argp.parse_args()
    package(args.root.resolve(), args.version, args.arch, args.out.resolve())
