# Caprine True Portable Builder — Windows x64

**Based on:** [bankjaneo/caprine](https://github.com/bankjaneo/caprine), reviewed upstream tag **v2.62.0**.  
**Output:** a manual GitHub Actions **ZIP**, not a `.paf.exe`.  
**Status:** Pillow is installed before tests, and the guarded restart patch now accounts for all FIVE `app.relaunch()` calls in the reviewed upstream `source/menu.ts`. **15 offline tests pass; Windows Actions, Facebook login, and portability still require end-to-end verification**.

## Latest correction — five restart calls in upstream menu.ts

The subsequent GitHub Actions log failed in the **Apply guarded portable source modifications** step:

```text
RuntimeError: Expected four app.relaunch calls in menu.ts, found 5
```

The upstream **v2.62.0** menu has five restart operations: **Switch to Work Chat**, **Switch to Messenger**, **Delete Settings**, **Delete App Data**, and **Relaunch Caprine**. The original test fixture incorrectly included four. This release fixes both `builder/patch_upstream.py` and `tests/test_builder.py`, checks each of the five actions by name, and blocks unreviewed extra or missing restart calls.

**If your builder already has the Pillow fix:** replace ONLY `builder/patch_upstream.py` and `tests/test_builder.py`, then commit, push, and start a **NEW** GitHub Actions run. Keep `v2.62.0` selected. You don't need to replace the workflow or your launcher. No actual Caprine user data is modified.

Verification: **15 offline tests pass**, including tests for missing/extra restart calls and modified menu labels. This does not yet establish that the Windows build or Messenger login succeeds.

## Update to the original builder (Pillow fix)

The first GitHub Actions run failed during offline tests with `ModuleNotFoundError: No module named 'PIL'`. The workflow installed Pillow too late. This revision installs `Pillow==11.3.0` before running any tests and removes the duplicate later installation.

If your builder repository already contains the original kit, replace **only** `.github/workflows/build-caprine-portable.yml`, then **Commit to main > Push origin** in GitHub Desktop. Start a **new** Actions run rather than choosing Re-run jobs on the failed run. Your portable application `Data` folder is unaffected.

## What you get

The GitHub Actions workflow downloads the developer's **tagged source code**, applies guarded, portable-only patches, builds Caprine from source, and packages it like this:

```text
CaprinePortable/
  CaprinePortable.exe        <-- START THE APP HERE (not inner Caprine.exe)
  App/
    Caprine/
      Caprine.exe
      resources/app.asar
      (all other Electron dependencies)
    AppInfo/
      appinfo.ini
      appicon.ico
      appicon_16.png
      appicon_32.png
      appicon_75.png
      appicon_128.png
      appicon_256.png
  Data/                     <-- KEEP THIS WHOLE FOLDER WHEN UPDATING
    KEEP-DATA-ON-UPDATE.txt
    Caprine/                <-- Created on first launch
      config.json           <-- electron-store settings (may vary)
      Session/              <-- Browser login/session/cache
      Logs/
      Downloads/
    Temp/
  Other/
    Source/
      LICENSE.txt
      BUILD-INFO.txt
```

The original app icon is taken from **the selected official fork source release** at `build/icon.png`. The GitHub Action converts it to a multiple-resolution ICO for the root launcher and menu icons. It does not use generic icons or `ExtractAssociatedIcon`.

### Why the source patch is necessary

Caprine uses Electron's `userData` path and `electron-store` for settings, while its browser session normally also writes to Electron's default location. We redirect `userData`, `sessionData`, download location and app logs *before* creating its settings store. The launcher sets only **child-process** portable environment variables. It does not globally change AppData, PATH, the registry or your browser configuration.

In portable mode, the changes also disable automatic program updates, hide Windows Launch at Login and stop built-in restarts from starting the inner Caprine executable without the launcher. A restart-requiring setting will cause Caprine to close: **start `CaprinePortable.exe` again yourself**. This is deliberate.

### Security note

**Caprine is an unofficial Messenger client.** The linked upstream release has `nodeIntegration: true` in the remote web-content window, a known Electron security concern. This builder changes it to `nodeIntegration: false`, while explicitly retaining `sandbox: false` so the fork's existing privileged preload can work. This reduces direct Node integration in the website, but **does not make the app fully sandboxed** and has not yet been tested with Messenger login and calls. Do not assume this removes every security risk; if features stop working, stop and review the preload/API bridge instead of blindly reverting the security patch.

Your saved session cookies may remain sensitive. Never publish your **used** portable `Data` folder to GitHub or share it with others. Accounts and cached credentials may need reauthentication after reinstalling Windows.

## Setup: one-time installation into a separate GitHub repository

1. Go to **https://github.com/new** and create a new empty repository named `Caprine-Portable-Builder` (Public is easiest for Actions). Do not initialize it with README/.gitignore/licence because this kit contains its own.
2. Download and extract this builder ZIP onto Windows. **Do not upload the ZIP as a single GitHub file.**
3. In **GitHub Desktop**, choose **File > Clone repository**, select your new empty `Caprine-Portable-Builder` repository, and clone it.
4. Choose **Repository > Show in Explorer**. Copy *all extracted kit contents* into the local clone, including the hidden `.github` directory.
5. Return to GitHub Desktop. Enter a commit message, click **Commit to main**, then **Push origin**.
6. On GitHub.com open your repository, click **Actions > Build Caprine True Portable ZIP (Manual) > Run workflow**.
7. Select branch `main`. Leave **upstream_ref** as `v2.62.0`. Click the green **Run workflow** confirmation button.
8. Once the run turns green, open it, find **Artifacts**, download `Caprine-TruePortable-v2.62.0-x64`, extract the GitHub artifact, and extract `Caprine-v2.62.0-Win-x64-Portable.zip` inside.
9. Open `CaprinePortable` and launch **CaprinePortable.exe**. **Never launch `App/Caprine/Caprine.exe` directly**, as that bypasses the portable data location.

**If the Actions workflow fails:** open the red failed step, choose **Download log archive**, and share it. Do not assume the builder succeeded because the offline tests are green.

### GitHub browser alternative to hidden-folder upload

If you don't use GitHub Desktop, upload `builder`, `tests`, `README.md`, and `START-HERE.txt` through the browser. To create `.github/workflows`, choose **Add file > Create new file** and type `.github/workflows/README.md` as the filename. Save a placeholder, open the resulting folder, and upload only `build-caprine-portable.yml` from the extracted kit's `.github/workflows` folder.

## Initial Windows verification

1. Confirm there is no other Caprine process running. Note whether `%APPDATA%/caprine` or `%APPDATA%/Caprine` already exists. **Don't remove any existing account data.**
2. Launch **CaprinePortable.exe**. Sign into Facebook if needed.
3. Make a harmless setting change (e.g. theme). Exit Caprine completely — including its notification-area/tray process — and reopen it with the root launcher. Check the setting persists.
4. Check files appear under `CaprinePortable/Data/Caprine` and that login/session storage is under `Data/Caprine/Session`.
5. Confirm using **Settings > Show App Data** (if available) that the path points into `CaprinePortable/Data/Caprine`.
6. See whether the ordinary `%APPDATA%` Caprine folder gets any new app-created files during that test. Some Windows-managed traces can remain regardless of portable mode.
7. Test sending messages, notifications, downloads and calls. Our renderer hardening is a change to upstream behavior and still needs a live test.

### Upgrading later

1. Wait for a newer **stable** upstream release.
2. **Do not just change `upstream_ref` and assume the builder is compatible.** This initial builder intentionally rejects other versions because its source patches are reviewed for v2.62.0 only. Update the patch anchors and tests after reviewing upstream source changes.
3. Back up the existing `Data` folder. Close Caprine completely.
4. Replace only **App/** and **CaprinePortable.exe** with the new package. Optionally replace **Other/**; keep **Data/** unchanged.
5. Relaunch the root executable. Your preferences and login session should persist on the same Windows installation, subject to Facebook session expiration and Windows-linked encryption.

## Files in this builder kit

- `.github/workflows/build-caprine-portable.yml` — manual workflow, no automatic triggers.
- `builder/patch_upstream.py` — fail-closed source patch for v2.62.0.
- `builder/CaprinePortable.cs` — portable root launcher source.
- `builder/create_icon.py` — official icon conversion.
- `builder/compile_launcher.ps1` — Windows launcher compiler.
- `builder/package.py` — final ZIP packaging and PortableApps Menu metadata.
- `builder/verify_zip.py` — ZIP structure check.
- `tests/test_builder.py` — offline tests.
- `START-HERE.txt` — short instructions.

The kit does **not** contain Caprine binaries or your personal Messenger data; GitHub Actions builds the binaries from the selected official fork release. No automatic installer or `.paf.exe` workflow is included.

## References

- Upstream code: https://github.com/bankjaneo/caprine
- Upstream tagged release: https://github.com/bankjaneo/caprine/releases/tag/v2.62.0
- Electron security: https://www.electronjs.org/docs/latest/tutorial/security/
- Electron Builder `--dir`: https://www.electron.build/cli
- PortableApps Format specification: https://portableapps.com/development/portableapps.com_format
