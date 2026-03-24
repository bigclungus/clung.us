# Changelog

## Unreleased

### Bug Fixes
- move tasks API to /api/tasks so /tasks serves tasks.html

- update 404 page to use shared sitenav

- merge tools subheader into main nav, single-line layout

- active state detection for tool links on other domains

- cache-bust sitenav.js?v=2 to bypass Cloudflare cache

- preserve expanded task cards across auto-refresh

- don't apply red hover border to completed task cards

- persist verdict and status when session concludes

- custom scrollbar + non-overlapping speech feed panel


### Changes
- add /tasks endpoint and tasks.html dashboard

- replace GitHub project board link with clung.us/tasks

- redesign tasks.html: match site theme, terminal-log style, in-character empty state


### Chores
- Initial commit — hello.clung.us website

- Remove stale changelog.html

- Add GitHub repo link to changelog

- Add terminal.clung.us server source

- terminal server added to repo

- Add systemd user service for terminal server

- terminal server systemd service

- Clickable agent cards with expandable output panel

- clickable agent cards

- Add /health endpoint and VM health bar to terminal page

- VM health bar on terminal page

- Add JetBrains Mono, hover states, 404 page, spider easter egg

- Add fullscreen knowledge graph page changelog entry

- Add GitHub profile link to site navigation

- Add custom Python HTTP server with 404 page support

- Add dark/light mode toggle to all pages

- Add temporal.clung.us link to site navigation

- Add 1998.clung.us nav link and 2026-03-23 changelog entry

- Add cost.clung.us to site nav

- Log cost.clung.us launch in changelog

- Update bio (daily refresh 2026-03-23)

- Extract .sitenav-links-auth CSS to shared file

- Add mobile-responsive CSS for clung.us main page

- Add Centronias death tracker page

- Add extensionless URL support (.html fallback)

- Show in-progress congress sessions at top of list

- Update bio (daily refresh 2026-03-24)

- Add markdown rendering to congress session view


### Congress
- allow 'evolution' field in session PATCH, commit session files

- speech bubbles beside circles, clickable topic modal


### Features
- add summary stats header to tasks page

- /congress page - AI parliament for task deliberation

- congress page — 3-seat roster/severance sidebar layout

- gate congress API behind github auth

- show persona display names and avatars in congress

- congress session tracking with numbered sessions

- congress page becomes replay viewer, sessions triggered via Discord


### Refactoring
- shared sitenav component, terminal as subheader


### Tasks
- derive status from append-only log; show log timeline in cards

- surface run_in_background, isolation, model in UI



