# DESIGN.md — Threads Studio Pro

## Surface & Design System
- **Mode**: `Operate` (Impeccable Craft Floor compliant).
- **Web UI**: React + Tailwind CSS, built with Vite. Semantic colors live in `web/src/studio.css`; components use Tailwind utilities and preserve the Vietnamese three-zone studio shell.
- **Desktop fallback & renderer**: `fluent-blue` (`0.2.0`) on `PyQt6` via `fluent_blue.compatibility.qt`, launched with `--desktop`.
- **Theme Default**: Web opens in Light, with a top-right Light/Dark toggle and browser-local preference; desktop keeps saved Light/Dark/high-contrast through `ThemeManager`.

## Architectural & Anti-Slop Rules
1. **Semantic Tokens**: Desktop custom surfaces use `ThemeManager`. Web uses centralized light/dark/high-contrast CSS tokens with matching semantic roles; keep component styling in Tailwind and reserve explicit media colors for the stage illustration.
2. **Flat Container Hierarchy (No Cards-in-Cards)**: Structural regions use `Splitter`, `Panel`, and `Divider` — never nested `Card` inside `Card`.
3. **No Modal Interruption for Core Tasks**: Reviewing and editing scraped comments happens in the dedicated **Duyệt Kịch Bản** split inspector right beside the `9:16` / `16:9` stage so background jobs keep running uninterrupted. A separate paginated candidate table exposes Likes, Replies, Reposts, and Quotes; sorting it does not reorder the production script until the user applies top N.
4. **Typography & Numerals**: Single system sans stack (`Segoe UI`); desktop uses `ThemeManager.font()` roles, web uses corresponding Tailwind sizes/weights. Use monospace for timecodes/coordinates/logs. Maximum 4 active type roles per view.
5. **Spatial Shell**:
   - **Home**: Theme-aware two-zone layout: resizable sidebar, minimal title bar and centered “Dựng video mới” composer. No account chrome or hot-post grid. Reference navigation and existing studio navigation stay in separate labeled groups. A route-based step bar guides content → voice → sources → layout → AI → processing → review → output.
   - **Studio tools** retain the three-zone layout below:
   - **Left Rail**: Collapsible `Sidebar` (`220px` / `56px`) with live queue & pending-review `Badge` counters.
   - **Center Workspace**: Task-focused pages (`Batch Queue DataTable`, `Inline Script Inspector`, `Voice Pool`, `Media Presets`, `Settings`, `Meme Library`). The separate **Kho Meme** sidebar section groups Sound management and the future Image placeholder.
   - **Right Dock**: Resizable interactive stage for `9:16` / `16:9` and output preview, with a separate scrolling AI token/quota region below. The processing log is a collapsible, resizable bottom dock across the workspace. Store panel dimensions and current route/job locally.
6. **Mandatory Style Consistency**: Follow the existing project structure, component patterns, naming, Vietnamese UI copy, and documentation conventions. Introducing a separate visual or coding style is strictly prohibited.

