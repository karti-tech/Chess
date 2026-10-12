# Verification report

Tested on the cloud Linux machine with Python 3.12.14, FFmpeg/ffprobe 7.1.5, pinned Python dependencies, and a real Docker container running **n8n 2.37.10**. Your Windows interpreter is 3.12.7; Windows-specific scripts and filesystem/firewall behavior still need a laptop run.

## Passed

- **21 automated tests**: PGN legality and checkmate, multiple games, variation exclusion, CP1252, malformed inputs, no-repeat game selection, missing engine detection, duration/resolution limits, deterministic audible audio, sample counts/clipping, animation for both castling directions, en passant and promotion, orientation and movement, SQLite recovery/idempotency, service authentication/request validation, mocked official-upload success/idempotency/uncertain-outcome/public gates, workflow structure, real FFmpeg rejection of black/missing-audio/corrupt videos.
- `pip check`: no broken dependency requirements.
- Real sample render: **720×1280, 30 FPS, 30.000 seconds**. H.264, yuv420p, AAC, fast-start, audible decoded soundtrack (RMS ~0.154), no detected black frames. Full FFmpeg decode passed. This sample was created by the n8n workflow through the HTTP service, not just CLI code.
- Real **1080×1920, 30 FPS, 15.000-second** cinematic sample through authenticated HTTP submit/poll/download. H.264/AAC, audio/video duration checks, fast-start, audible audio and full decode passed. The added black-frame detector also passed on revalidation.
- Docker → Windows-style host service route (`host.docker.internal:8765` mapped to Linux host gateway for cloud test) returned health 200. HTTP service job replay returned the original ID and validated video download returned actual bytes.
- All **three workflow exports imported** in n8n 2.37.10. Factory execution ran Code, HTTP Request, IF and Wait nodes: 1 submission, **3 polls, 2 waits**, then success/review-queue output. Final exported factory parameters were tested (30 seconds, 720 mode, dry run); only local test credentials and workflow ID were added for testing.
- Contact sheets inspected to verify visible pieces, labels, correct end position, layout and safe separation between board and caption card. Smooth piece movement is implemented frame by frame; special move square occupancy is tested.

## Initial issues corrected

- A small-font edge case in text wrapping failed the first render; corrected and subsequent exports/tests passed.
- The initial caption card overlapped the bottom rank; moved the board/card and inspected regenerated contact sheets.
- The cloud's injected HTTP proxy rejected host.docker.internal; the disposable n8n test execution used NO_PROXY specifically for local host destinations. This is local routing configuration, not TLS/signature disabling. Docker Desktop laptop setups without that proxy should not need it.
- A workflow execution during a service restart saw connection refusal. After the service was stable, the same tested configuration completed successfully. Keep the service running while workflows execute.

## Not verified with external credentials or on your laptop

- **No YouTube video was uploaded.** OAuth authorization, channel selection, token refresh, actual quota/verification rules, API processing and privacy need your Google account. Upload safeguards were tested with mocks; no real success is claimed.
- OpenAI optional provider was not called; no API key was supplied. AI drafts stay for review. Local mode was exercised end to end.
- Stockfish executable/analysis was not installed or executed in cloud. Missing-executable behavior was tested; install your chosen official binary if desired.
- Windows Setup/Launch/Doctor/Narrate/Firewall and your Averbakh.pgn were not available here. Follow README's three-action first run, then switch games_dir. Local Windows TTS is optional and untested here.
- SMTP notification node imported but was disabled and not sent. Scheduled unattended activation/error-trigger notifications need your n8n configuration; manual factory execution was tested.
- NVENC acceleration and automatic thumbnail upload are not implemented. CPU renderer is verified. Thumbnail is an optional generated review artifact, not a guaranteed YouTube Shorts cover.
- No public/automatic publication, new cloud snapshot publication, or fresh-task restoration was performed. Code is in the local checkout and downloadable archive, and was subsequently pushed to the chess-shorts-factory branch of karti-tech/Chess for GitHub delivery.

The deliverable is a tested first end-to-end release with original procedural visuals/audio and a review queue. Windows connectivity and credential-backed publishing remain installation/integration steps, so the full laptop definition of done cannot yet be claimed.
