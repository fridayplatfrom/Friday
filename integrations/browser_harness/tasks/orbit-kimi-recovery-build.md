This is the implementation task for the current Kimi session. A previous session completed only workspace/runtime checks and a plan; it created no project files. Use the existing target orbit-studio-kimi and preserve any files you find. The connector currently has an issue continuing Kimi conversations after the first response, so make the first implementation tool call self-contained: use native pwsh with the explicit working directory to write the complete backend, frontend and integration tests, run the isolated tests, and start the preview if they pass. You may return one substantial tool call with a long command; use literal here-strings carefully. Keep code concise and dependency-free using Node built-ins. Do not end with merely a plan or use your website's own artifact sandbox. Friday must execute the actual local tool call. Subsequent browser verification can follow once real files exist. All execution and permission checks remain native Harness operations.
Build ORBIT, a complete local full-stack project-management website, through this Friday/Harness session. Use the supplied native Harness tools for all work. You are Kimi connected through a visible-text browser bridge: Harness tools are external operations, not website functions. Write HARNESS_TOOL_CALL followed by one fenced JSON object with name and arguments to request each operation. Harness executes it and returns the actual result. Never claim execution without that result.

This is implementation work, not a proposal. Continue until the website is built, runs locally, and its main flows have been tested. Use native planning/progress and permission controls. Do not modify Friday, the connector, Harness configuration, or existing projects. Use only a new orbit-studio-kimi folder under the current native session workspace. Inspect the workspace before writing. Do not delegate to other agents or switch model/API providers.

Design direction:
- Visual thesis: a calm, precise studio workspace with warm off-white surfaces, charcoal typography, subtle dividers, and one indigo action accent.
- Content plan: a narrow ORBIT navigation rail, project switcher and utility toolbar, a working Kanban board as the dominant surface, and a task inspector for secondary detail. Projects and Reports are separate working views, not marketing sections.
- Interaction thesis: short drawer/modal transitions, clear drag-and-drop placement feedback, and restrained hover/toast motion; honor reduced-motion preferences.
- Use system fonts or local assets, inline SVG icons, consistent spacing, visible focus states and readable contrast. Task cards are justified as draggable objects; avoid ornamental dashboard-card mosaics, gradients and filler copy. No external image or font dependency is needed for this app.

Required functionality:
1. Seed four realistic fictional projects, five fictional team members, and roughly 20 varied tasks so the first screen is useful.
2. Projects view: create, edit, archive, and select projects. Archiving must remain reversible. Show project progress derived from real stored tasks.
3. Board view: Backlog, In progress, Review and Done columns; create/edit tasks, move them through drag-and-drop and an accessible status selector, and retain changes after reload.
4. Task inspector: title, description, assignee, priority, due date, status, editable checklist and timestamped comments, all persisted. Validate required fields and show actionable server errors.
5. Search and filtering by text, assignee and priority; clear filters and useful no-results/empty states. Search must work across stored tasks, not just decorative sample text.
6. Reports view: live completion counts and simple SVG charts derived from stored tasks; project and status totals must match board changes.
7. Activity view: persisted event history for task/project edits and status changes. No invented live users or fake synchronization indicators.
8. Working navigation, responsive mobile layout, keyboard-accessible dialogs, Escape to close and focus restoration. Theme preference may use localStorage; project/task data must use the backend.

Backend and running:
- Prefer Node.js built-in HTTP plus SQLite through node:sqlite, after checking the installed Node runtime supports it. Keep dependencies minimal. If SQLite is unavailable, explain and use a small durable local store with atomic writes rather than requiring an external service.
- Provide real REST endpoints for the required operations, request/body validation, useful status codes, bounded bodies and sensible error handling.
- This is a local single-workspace demonstration. Make that clear; do not add fake login screens or claim production authentication/security.
- Bind the preview server only to 127.0.0.1:8010, which is already permitted by the existing Harness browser. Check availability first; do not stop another server or change browser security settings if the port becomes occupied.
- Start the preview using a managed native background job, record its ID, and collect its startup result. Avoid installing large packages or downloading browser engines.

Validation and delivery:
- Add and run meaningful backend integration checks for CRUD, invalid input, status/report consistency, comments/checklists and persistence across a store reopen. Use an isolated test database; never reset a live project database to run tests.
- Use the existing Harness browser tools for an end-to-end check: open the actual preview, create a uniquely named test task, move its status, add a comment/checklist item, reload and verify persistence, search/filter it and verify report totals. Use keyboard controls when testing accessibility. Record actual results and any failures.
- Capture a desktop screenshot and a mobile-width screenshot through the existing browser tools. Inspect them and correct obvious layout issues. Do not invent screenshot paths or claim browser tests ran when they did not.
- Leave the preview running and return its clickable URL, the real project folder, tested flows, actual test results, screenshot paths, startup command, and honest limitations. Keep working on implementation and verification instead of ending after a plan or scaffold.

