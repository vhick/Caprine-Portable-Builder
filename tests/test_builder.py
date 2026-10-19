import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


patch = load(ROOT / 'builder' / 'patch_upstream.py', 'patch_upstream')
package_mod = load(ROOT / 'builder' / 'package.py', 'package')


class CaprinePortableBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.src = self.root / 'upstream'
        (self.src / 'source').mkdir(parents=True)
        (self.src / 'build').mkdir()
        (self.src / 'package.json').write_text(json.dumps({'name':'caprine','version':'2.62.0'}))
        (self.src / 'source' / 'config.ts').write_text("import Store from 'electron-store';\nconst store = new Store({schema});")
        (self.src / 'source' / 'index.ts').write_text(
            "if (!is.development && config.get('autoUpdate')) {\n"
            "  autoUpdater.checkForUpdatesAndNotify();\n}\n"
            "webPreferences: {\n\t\t\tnodeIntegration: true,\n}\n")
        restart_labels = (
            'Switch to Work Chat…', 'Switch to Messenger…',
            'Delete Settings', 'Delete App Data', 'Relaunch Caprine',
        )
        relaunch_blocks = ''.join(
            f"\t\t\tlabel: '{label}',\n"
            "\t\t\tclick() {\n"
            "\t\t\t\tapp.relaunch();\n"
            "\t\t\t\tapp.quit();\n"
            "\t\t\t},\n"
            for label in restart_labels
        )
        (self.src / 'source' / 'menu.ts').write_text(
            "\t\t\tlabel: 'Launch at Login',\n\t\t\tvisible: !is.linux,\n"
            "\t\t\tlabel: 'Automatic Updates',\n\t\t\ttype: 'checkbox',\n\t\t\tchecked: config.get('autoUpdate'),\n"
            + relaunch_blocks)
        (self.src / 'source' / 'util.ts').write_text("\t\tapp.relaunch();\n\t\tapp.quit();\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_portable_paths_before_electron_store(self):
        patch.apply(self.src)
        data = (self.src / 'source/config.ts').read_text()
        self.assertLess(data.index("app.setPath(key, directory)"), data.index('const store = new Store'))
        self.assertIn("'sessionData'", data)
        self.assertIn("'downloads'", data)
        self.assertIn('CAPRINE_PORTABLE_DATA_DIR', data)

    def test_updater_guard_and_renderer_isolation(self):
        patch.apply(self.src)
        data = (self.src / 'source/index.ts').read_text()
        self.assertIn('nodeIntegration: false', data)
        self.assertIn('sandbox: false', data)
        self.assertIn('!process.env.CAPRINE_PORTABLE_DATA_DIR', data)

    def test_launch_at_login_hidden(self):
        patch.apply(self.src)
        self.assertIn('visible: !is.linux && !process.env.CAPRINE_PORTABLE_DATA_DIR', (self.src/'source/menu.ts').read_text())

    def test_restart_guard(self):
        patch.apply(self.src)
        menu = (self.src/'source/menu.ts').read_text()
        self.assertEqual(menu.count('app.relaunch();'), 5)
        self.assertEqual(menu.count('if (!process.env.CAPRINE_PORTABLE_DATA_DIR) {'), 5)
        self.assertIn('if (!process.env.CAPRINE_PORTABLE_DATA_DIR)', (self.src/'source/util.ts').read_text())

    def test_sixth_unreviewed_relaunch_is_rejected(self):
        menu_file = self.src / 'source/menu.ts'
        menu_file.write_text(menu_file.read_text() + '\napp.relaunch();\n')
        with self.assertRaisesRegex(RuntimeError, 'Expected 5 app.relaunch calls'):
            patch.apply(self.src)

    def test_missing_relaunch_is_rejected(self):
        menu_file = self.src / 'source/menu.ts'
        content = menu_file.read_text()
        menu_file.write_text(content.replace('app.relaunch();', '', 1))
        with self.assertRaisesRegex(RuntimeError, 'Expected 5 app.relaunch calls'):
            patch.apply(self.src)

    def test_changed_restart_action_is_rejected(self):
        menu_file = self.src / 'source/menu.ts'
        menu_file.write_text(menu_file.read_text().replace('Relaunch Caprine', 'Restart Application'))
        with self.assertRaisesRegex(RuntimeError, 'Missing or altered restart action'):
            patch.apply(self.src)

    def test_patch_fail_closed_on_second_application(self):
        patch.apply(self.src)
        with self.assertRaisesRegex(RuntimeError, 'compatibility failure'):
            patch.apply(self.src)

    def test_version_fail_closed(self):
        (self.src/'package.json').write_text(json.dumps({'name':'caprine','version':'2.63.0'}))
        with self.assertRaisesRegex(RuntimeError, 'only been reviewed'):
            patch.apply(self.src)

    def test_missing_anchor_fails_closed(self):
        (self.src/'source/index.ts').write_text('replaced main app implementation')
        with self.assertRaisesRegex(RuntimeError, 'compatibility failure'):
            patch.apply(self.src)

    def test_package_output_structure(self):
        from PIL import Image
        Image.new('RGBA', (512,512), (80,120,220,255)).save(self.src/'build/icon.png')
        (self.src/'license').write_text('Sample MIT license placeholder for test')
        unpacked = self.src/'dist/win-unpacked/resources'
        unpacked.mkdir(parents=True)
        (unpacked/'app.asar').write_bytes(b'FAKE TEST')
        (unpacked.parent/'Caprine.exe').write_bytes(b'MZ' + b'Z'*140)
        (self.root/'CaprinePortable.exe').write_bytes(b'MZ' + b'0'*200)
        archive = package_mod.package(self.root, '2.62.0', 'x64', self.root/'artifacts')
        self.assertTrue(archive.exists())
        import zipfile
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertIn('CaprinePortable/App/AppInfo/appicon_75.png', names)
            self.assertIn('CaprinePortable/CaprinePortable.exe', names)
            self.assertNotIn('CaprinePortable/Data/Caprine/config.json', names)
            self.assertIn(b'Name=Caprine Portable', z.read('CaprinePortable/App/AppInfo/appinfo.ini'))

    def test_unknown_architecture_refused(self):
        with self.assertRaisesRegex(ValueError, 'Only Caprine'):
            package_mod.package(self.root, '2.62.0', 'arm64', self.root/'artifacts')

    def test_build_yml_manual_only(self):
        workflow = (ROOT/'.github/workflows/build-caprine-portable.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertNotIn('schedule:', workflow)
        self.assertNotIn('push:', workflow)
        self.assertIn('retention-days: 7', workflow)
        self.assertIn('v2.62.0', workflow)

    def test_pillow_installed_before_tests(self):
        workflow = (ROOT/'.github/workflows/build-caprine-portable.yml').read_text()
        install = workflow.index('- name: Install Python builder dependencies')
        tests = workflow.index('- name: Run offline builder tests')
        self.assertLess(install, tests)
        self.assertIn('Pillow==11.3.0', workflow[install:tests])
        # Dependency should not be installed again later in the build.
        self.assertEqual(workflow.count('python -m pip install --disable-pip-version-check Pillow==11.3.0'), 1)

    def test_launcher_only_child_environment(self):
        launcher = (ROOT/'builder/CaprinePortable.cs').read_text()
        self.assertIn('UseShellExecute = false', launcher)
        self.assertIn('EnvironmentVariables["CAPRINE_PORTABLE_DATA_DIR"]', launcher)
        self.assertIn('@"Data\\Caprine"', launcher)
        self.assertIn('Path.Combine(root, @"App\\Caprine\\Caprine.exe")', launcher)
        self.assertNotIn('Registry.', launcher)


if __name__ == '__main__':
    unittest.main()
