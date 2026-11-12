# Friday default design

The normal web interface and desktop use the shared ../friday.css stylesheet.
No preview flag or theme activation is needed. System and Dark use Friday;
an explicit Light selection retains the native light appearance. The older preview launcher is a
compatibility alias for normal startup. Ctrl+Shift+F12 reloads desktop CSS.

## Appearance

Grey-to-lavender home gradient; charcoal conversation and workspace surfaces;
near-black navigation and tool cards; lavender primary actions and user bubbles.
Shared tokens cover settings, menus, dialogs, tool results, scrollbars and focus
rings. Success, warning, error and diff colours retain their meaning.

Native chat, browser/file tabs, splits, resizing, attachments, goals, plans,
compact, export, model selection and permission controls retain their existing
implementation. The sidebar uses its native open/close icon, centred rail
controls, and locally bundled provider marks (Lobe Icons 1.97.0, MIT).

## Isolation and persistence

The server injects an idempotent style element into its own authenticated HTML.
Desktop also inserts the same CSS only into its trusted local Harness view and
reapplies it after refresh or recovery. Provider pages and rendered workspace
websites retain their original appearance. Logins, profiles, task state, saved
pane sizes, tool permissions and connector protocol are unchanged.

## Validation — 2026-11-11

380 tests pass, including default activation, trusted-origin isolation, refresh
reapplication and idempotent web startup without navigation or storage writes.
The normal desktop launcher was restarted while idle to verify the default theme.
This appearance change does not resolve historical provider errors and is not
a new end-to-end provider, upload or download validation.

## UI audit and startup branding

Audited General, Models, Built-in plugins, Agent presets, dock/file tabs, menu surfaces, Chat and Trajectory. Dock selection, toolbar/menu radii and recovery shell now share the theme. Navigation uses a consistent rounded outline family. Native boot markup receives the Friday image before plugin activation; its loading hint is hidden while real startup errors and progress remain intact. Both favicon variants and the desktop window icon use Friday. Protected provider tabs and rendered HTML keep their own behavior and content styling. A native boot-markup fixture verified the loaded logo and zero visible loading-hint text; an error fixture verified diagnostics remain visible.

## Panel width preferences

Friday seeds the native right-panel width at 68% of the workspace after the icon rail, subject to Harness's existing minimum chat width and panel limits. A versioned local preference records native divider changes and restores them on refresh/restart. Native actions still own geometry, panel visibility, fullscreen, tab selection and provider bounds. Width writes are debounced and flushed on release, page hide and teardown. Invalid or unavailable browser storage falls back without blocking resizing.
