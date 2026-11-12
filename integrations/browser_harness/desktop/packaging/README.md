# Standalone Windows build

This targets Windows x64. End users should install Friday Setup; the developer
build sources the Harness backend from the locally installed Harness release
and the frontend from the pinned Electron dependency. That source installation
is a build input, not an end-user prerequisite. Override it with
`FRIDAY_HARNESS_DIST`.

The frontend uses Electron 45.3 so existing Friday browser profiles are not
downgraded. The backend runs on bundled Node 24.21 with a materialized Harness
module tree; it does not depend on the newer frontend's Electron native loader.
The staged backend startup check passes with this arrangement. The Windows
installer remains work in progress: the last build failed during final output
writing under low disk space, and installation validation is not complete.

The payload includes Electron/Chromium, the complete Harness runtime and native
modules, Python/document libraries, Node, pnpm, LibreOffice Kit, the Friday
provider and native browser bridge, and a hash-pinned portable Git distribution.
Windows' built-in PowerShell remains the native shell fallback. Project-specific
packages can still be installed by the agent as part of a user's task.

From the desktop directory:

```
npm ci
npm run package:prepare
npm run package:git
npm run test:bundled-backend
npm run package:windows
npm run test:installer
```

Keep at least 4 GB free before the last two steps. The prepare step uses hard
links on the same volume to reduce staging space. It refuses to replace a prior
stage. Inspect prior stages or use a new `FRIDAY_BUILD_STAGE`. The installer
output can be redirected with `FRIDAY_RELEASE_DIR`.

Expected artifact: `release/Friday-Setup-0.1.0-x64.exe`, with a SHA-256 sidecar.
No installer artifact exists until `package:windows` succeeds. This build has
no signing certificate configured; it must not be described as signed.

## Data and permissions

The installer never carries a developer profile, connection token, conversation,
cookies or action receipts. It installs application resources per user, with
Start menu/Desktop shortcuts and an uninstaller. Existing `~/.dsh` data stays in
place, including the original desktop profile/partitions. Existing web-profile
plugins, presets, selected models and permission settings are not rewritten;
a generated overlay points Friday's own components to the installed runtime.
The existing social composer is included for clean profiles without distributing
its development workspace. Uninstall does not request removal of profile data.

Fresh profiles initialize defaults once. Interrupted initialization can resume
only when marked as an incomplete Friday bootstrap; unknown incomplete profiles
are preserved and produce a repair message. Closing an app-owned backend uses a
private IPC shutdown signal after the existing idle/release guard. An existing
authenticated backend may be reused; unknown listeners are never terminated.

## Validation gates

- `tests/installed-runtime.test.mjs`: clean setup, secret reuse, preservation of
  existing state/configuration and interruption handling.
- `test:bundled-backend`: real staged backend, empty home, restricted PATH,
  authenticated HTML, native client assets, bridge and graceful shutdown. Its
  local development fixture server is disabled to avoid colliding with an open
  developer instance; no provider prompt or browser action is submitted.
- `test:installer`: checksum-verified silent installation to a disposable folder,
  installed CLI/connector/runtime checks, in-place reinstall and uninstallation
  preserving a synthetic data sentinel. It refuses to overwrite a registered
  Friday installation. Same-version reinstall is not a cross-version upgrade
  certification.
- Live installed-app gates still require verifying first-run setup, native tools,
  authenticated provider streaming, actual cookies across restart, downloads,
  and action receipts. File-marker tests do not prove that provider login works.

Keep backend logs private: they contain local owner authentication links. The
packaging stage and release artifacts are excluded from Git. Keep upstream MIT,
Electron/Chromium, Python, Git and other third-party notices with distributions.
