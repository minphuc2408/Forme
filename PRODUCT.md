# PRODUCT.md — Threads Studio Pro

## What It Is
**Threads Studio Pro** is a local browser production studio for Vietnamese creators who turn Threads discussions and multi-part stories into narrated videos: `9:16` (`1080x1920`) for TikTok, Reels, and YouTube Shorts, or `16:9` (`1920x1080`) for landscape output. React + Tailwind CSS provide the UI; Python keeps scraping, AI CLI, TTS, Qt card rendering and FFmpeg. The former Windows desktop UI remains available with `--desktop`.

## Primary User & Scene
- **Who**: Solo channel operators and multi-channel content teams producing 5–50 vertical videos per session.
- **Scene**: Desk workstation (`1920x1080` or `2560x1440`), extended editing sessions with saved Light/Dark preference (new settings default to Light).
- **Surface Mode**: **Operate** — speed, scanability, batch visibility, inline review without modal lockups, and direct canvas manipulation take priority over decorative chrome.

## Core Capabilities
1. **Batch Ingestion & Scraping**: Accept Threads URLs or manual story scripts. Playwright opens Microsoft Edge with an app-owned profile, scrolls ten times, and reads network/embedded JSON with a DOM fallback. Identify the original post and its replies, filter spam and authors, then rank the loaded comments by likes by default. No third-party scraping token is required; coverage is limited to what Threads loads.
2. **Vietnamese Teencode & Image Normalization**: Expand Vietnamese abbreviations/slang and read image text through account-authenticated Codex CLI or Antigravity CLI, with an explicit offline dictionary mode. See [current features and limits](docs/project/features.md).
3. **Inline Script Inspector**: Sort a four-metric candidate table, apply top N from the cached pool, reorder segments, toggle inclusion, edit spoken text, preview individual voice lines, and see Threads card renders without blocking background workers.
4. **Multi-Engine AI Voice Router**: Mix and match the dynamically loaded `K07VN/capcut-tts-api` voice catalog, `edge-tts` (`Hoài My`, `Nam Minh`), and optional `pnnbao97/VieNeu-TTS` presets/cloning. Output is normalized to 44.1kHz stereo WAV; backend availability depends on installation and account access.
5. **Portrait/Landscape Stage & GPU FFmpeg Compositor**: Drag/resize card and B-roll regions on a matching `9:16` or `16:9` layout preview. Select a local background file, optionally seek to a random continuous section, and crop or fit it during H.264 rendering via `h264_nvenc` / `libx264`.
6. **Contextual Meme Sound Library**: Import local audio and JSON descriptions, merge them into one catalog, report duplicate/missing files, and preview or disable sounds. After script approval, the selected AI CLI matches reactions to the post and reviewed replies; the timeline reserves time after narration. No web downloader or filename-based description generation. Meme Image remains a future placeholder.
7. **Local PostgreSQL Metadata**: Store configuration/presets, video jobs and script segments in the existing `thread` schema. Videos stay on disk and are referenced by path. Web startup restores saved jobs; interrupted work requires review rather than automatic online processing.

