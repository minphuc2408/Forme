# PRODUCT.md — Threads Studio Pro

## What It Is
**Threads Studio Pro** is a high-throughput Windows desktop production studio for Vietnamese short-form creators who turn Threads discussions and multi-part stories into `9:16` (`1080x1920`) narrated videos for TikTok, Reels, and YouTube Shorts.

## Primary User & Scene
- **Who**: Solo channel operators and multi-channel content teams producing 5–50 vertical videos per session.
- **Scene**: Desk workstation (`1920x1080` or `2560x1440`), extended editing sessions with saved Light/Dark preference (new settings default to Light).
- **Surface Mode**: **Operate** — speed, scanability, batch visibility, inline review without modal lockups, and direct canvas manipulation take priority over decorative chrome.

## Core Capabilities
1. **Batch Ingestion & Scraping**: Accept 1 to 100+ Threads URLs (or manual story scripts) simultaneously via Playwright persistent login, filtering spam/affiliate replies across 3 selection modes (*Author Only*, *Top Likes excl. Author*, *Top Likes incl. Author*).
2. **Vietnamese Teencode & Image Normalization**: Expand Vietnamese abbreviations/slang and read image text through account-authenticated Codex CLI or Antigravity CLI, with an explicit offline dictionary mode. See [current features and limits](docs/project/features.md).
3. **Inline Script Inspector**: Reorder segments, toggle inclusion, edit spoken text, preview individual voice lines, and see live Threads card renders side-by-side without blocking background render workers.
4. **Multi-Engine AI Voice Router**: Mix and match the dynamically loaded `K07VN/capcut-tts-api` voice catalog, `edge-tts` (`Hoài My`, `Nam Minh`), and optional `pnnbao97/VieNeu-TTS` presets/cloning. Output is normalized to 44.1kHz stereo WAV; backend availability depends on installation and account access.
5. **Direct `9:16` Stage & GPU FFmpeg Compositor**: Drag/resize card and B-roll regions directly on a `9:16` preview stage and render `1080x1920` H.264 MP4s concurrently via `h264_nvenc` / `libx264`.

