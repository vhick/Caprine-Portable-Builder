"""Fail-closed, version-scoped portable patch for bankjaneo/caprine v2.62.0.

Only patch the upstream checkout obtained from a trusted GitHub release tag.
Each changed block is matched exactly once to avoid silently building an
unportable app after source changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(file: Path, before: str, after: str) -> None:
    text = file.read_text(encoding='utf-8')
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f'Upstream compatibility failure in {file}: expected one match, got {count}. Do not bypass this protection.')
    file.write_text(text.replace(before, after, 1), encoding='utf-8')


def apply(source: Path):
    pkg = source / 'package.json'
    config = source / 'source/config.ts'
    index = source / 'source/index.ts'
    menu = source / 'source/menu.ts'
    util = source / 'source/util.ts'
    for f in (pkg, config, index, menu, util):
        if not f.is_file():
            raise FileNotFoundError(f'Expected upstream file missing: {f}')
    import json
    meta = json.loads(pkg.read_text(encoding='utf-8'))
    if meta.get('name') != 'caprine' or meta.get('version') != '2.62.0':
        raise RuntimeError('This kit has only been reviewed for Caprine v2.62.0. Review newer tags before updating.')

    # This must run before the first electron-store instance. Separate session
    # storage avoids Chromium's cookies/caches defaulting to Windows AppData.
    replace_once(config,
        "import Store from 'electron-store';",
        """import Store from 'electron-store';
import {app} from 'electron';
import {mkdirSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';

// Portable-only; normal Caprine installs are unchanged.
const portableData = process.env.CAPRINE_PORTABLE_DATA_DIR;
if (portableData) {
\tif (!path.isAbsolute(portableData)) {
\t\tthrow new Error('CAPRINE_PORTABLE_DATA_DIR must be absolute');
\t}
\tfor (const [key, directory] of [
\t\t['userData', portableData],
\t\t['sessionData', path.join(portableData, 'Session')],
\t\t['downloads', path.join(portableData, 'Downloads')],
\t] as const) {
\t\tmkdirSync(directory, {recursive: true});
\t\tapp.setPath(key, directory);
\t}
\tmkdirSync(path.join(portableData, 'Logs'), {recursive: true});
\tapp.setAppLogsPath(path.join(portableData, 'Logs'));
}
""")
    # Built-in updater must never modify a manually upgraded app.
    replace_once(index,
        "if (!is.development && config.get('autoUpdate')) {",
        "if (!process.env.CAPRINE_PORTABLE_DATA_DIR && !is.development && config.get('autoUpdate')) {")
    replace_once(index,
        "\t\t\tnodeIntegration: true,",
        "\t\t\tnodeIntegration: false,\n\t\t\tsandbox: false, // Retain the existing Node-powered preload; web content has no Node integration.")
    # Portable mode cannot auto-register itself at Windows startup.
    replace_once(menu,
        "\t\t\tlabel: 'Launch at Login',\n\t\t\tvisible: !is.linux,",
        "\t\t\tlabel: 'Launch at Login',\n\t\t\tvisible: !is.linux && !process.env.CAPRINE_PORTABLE_DATA_DIR,")
    # Make the UI accurately reflect that updater is disabled, even if old
    # settings still contain autoUpdate=true.
    replace_once(menu,
        "\t\t\tlabel: 'Automatic Updates',\n\t\t\ttype: 'checkbox',\n\t\t\tchecked: config.get('autoUpdate'),",
        "\t\t\tlabel: 'Automatic Updates',\n\t\t\ttype: 'checkbox',\n\t\t\tvisible: !process.env.CAPRINE_PORTABLE_DATA_DIR,\n\t\t\tchecked: config.get('autoUpdate'),")
    # All five known restart operations (four in menu.ts and one in util.ts) must not start the unpacked inner EXE,
    # since that would lack the portable environment and write to host AppData.
    relaunch_count = menu.read_text(encoding='utf-8').count('app.relaunch();')
    if relaunch_count != 4:
        raise RuntimeError(f'Expected four app.relaunch calls in menu.ts, found {relaunch_count}')
    text = menu.read_text(encoding='utf-8')
    text = text.replace('app.relaunch();', 'if (!process.env.CAPRINE_PORTABLE_DATA_DIR) {\n\t\t\t\t\tapp.relaunch();\n\t\t\t\t}', 4)
    menu.write_text(text, encoding='utf-8')
    replace_once(util,
        '\t\tapp.relaunch();\n\t\tapp.quit();',
        '\t\tif (!process.env.CAPRINE_PORTABLE_DATA_DIR) {\n\t\t\tapp.relaunch();\n\t\t}\n\t\tapp.quit();')
    print('Applied Caprine v2.62.0 guarded portable + renderer hardening patch.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('upstream', type=Path)
    args = parser.parse_args()
    apply(args.upstream.resolve())
