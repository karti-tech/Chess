# Chess Shorts Factory

A local Python 3.12 video factory for Windows 11, orchestrated by n8n in Docker. It renders **real animated moves**, tactical captions, original synthesized music and effects, and validates each MP4 before placing it in a review queue. No paid subscription, Lichess endpoint, GPU, AI key or YouTube credential is needed for the first video.

## Start here: three actions

1. Download and extract the project ZIP into a **new folder**, such as `C:\Users\karti\Downloads\ChessShortsFactory`. Keep your existing `ChessShorts` folder intact. Open PowerShell in the new folder:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Setup.ps1
   ```

2. Generate the first sample and launch the service:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Render-Sample.ps1
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Launch.ps1
   ```

   Leave the service window open. Open the MP4 in the UUID folder under `output`. The demo is an original legal Scholar's Mate demonstration, not an attributed tournament game. Setup uses 720×1280 for the laptop's first run; configuration supports 1080×1920.

3. In n8n, import `workflows/Chess-Shorts-Factory.json`. Create an **HTTP Header Auth** credential: name `X-Chess-Token`, value from your local `.env` after `CHESS_SERVICE_TOKEN=`. Select that credential on **Create Render Job** and **Poll Job**. Execute **Manual Test**. Do not paste the token in workflow code or chat.

The first run is `dry_run:true`: it renders and validates, permits repeated previews, and **cannot upload**. Scheduling is initially disabled. This is a working first release with stylized procedural pieces; it is not a promise of broadcast-level art direction or monetization. Review the sample's look before scheduling a channel.

## Use your Averbakh collection

Edit only `config/local.json` (other fields retain defaults):

```json
{
  "host": "0.0.0.0",
  "games_dir": "C:/Users/karti/Downloads/ChessShorts/games",
  "width": 720,
  "height": 1280,
  "target_seconds": 30,
  "style": "meme_chaos",
  "brand": "YOUR CHANNEL NAME"
}
```

The scanner reads every `.pgn` recursively, multiple games per file, main lines rather than variations, UTF-8/BOM or CP1252. It skips malformed/illegal games and short games, selects an eventful coherent window, and records the starting FEN and exact moves. It never modifies or deletes PGNs. PGN results are quoted as recorded metadata; only actual board checkmate is labelled CHECKMATE. An excerpt that ends earlier is labelled EXCERPT COMPLETE.

Restart the service after changing configuration. For production renders, change `dry_run:false` in n8n's **Configuration** node. Game hashes prevent repeat non-dry renders across restarts. Failed jobs release their game for another request. Exhaustion is an explicit error; add more PGNs. Delete neither the database nor history just to work around a failed upload.

## Docker to Windows connectivity

Your n8n container cannot directly read Windows `C:\...` files. It calls the authenticated Windows service at `http://host.docker.internal:8765`. Video generation, metadata and database files stay on Windows. An authenticated `GET /jobs/{id}/video` can return the binary if you need it in a future n8n node; the supplied factory uses a review queue rather than loading a large MP4 into n8n memory.

In another PowerShell window:

```powershell
Invoke-RestMethod http://localhost:8765/health
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-N8nConnection.ps1
```

If Docker cannot connect, confirm `host` is `0.0.0.0`, port 8765 is unused and the service is running. Allow this Python executable through Windows Firewall **only on your trusted Private network/Docker interface**. Restrict inbound TCP 8765 to the necessary local/Docker subnet in the firewall's advanced rules. Do not expose/forward it to the Internet or allow public networks. The service requires the token on job/readiness/publish endpoints, has no CORS/browser app, and keeps health public without secrets. For use entirely outside Docker, bind `127.0.0.1` instead. No Execute Command node is required.

Check the **container's** version (your host CLI can be different):

```powershell
docker exec n8n n8n --version
```

## n8n workflows

- **Chess-Shorts-Factory.json**: manual trigger → configuration → idempotent render submission → authenticated polling → status/validation/deadline check → success review queue. Pending jobs wait 15 seconds. Polling has a 45-minute deadline; HTTP calls have three bounded retries with the same request key. A failure throws a visible n8n execution error. Service SQLite and job logs retain the job independently.
- **Chess-Shorts-Publish-Reviewed.json**: separate optional manual workflow. Enter a reviewed non-dry job ID, set `approved:true`, and configure its Header Auth credential. It calls the official upload implementation on Windows, so the OAuth token stays on Windows. No blind retry of an upload POST.
- **Chess-Shorts-Error-Handler.json**: import and save, then select it as **Error Workflow** in factory/publish Settings. Automatic execution errors trigger it; manual errors appear directly in the editor. Optional email remains disabled until you supply actual addresses and an SMTP credential. No messages are sent by default.

After a successful manual run, configure workflow timezone (for example `Asia/Kolkata`), set the Schedule Trigger hour/cadence, enable that node and publish/activate the workflow in your version's UI. Default cadence is daily at 18:00 **in the workflow timezone**. Config's `schedule_hour` documents the intended default; n8n is the scheduler and must be edited separately. Automated renders still enter review; automatic public publishing is intentionally absent from the first release.

Workflow exports use standard Code v2, HTTP Request v4.2, IF v2.2, Wait v1.1, Schedule v1.2 nodes. See `TEST_REPORT.md` for actual import/execution evidence and remaining laptop checks.

## Configuration reference

`config/default.json` defines all settings; `config/local.json` contains your overrides. Python paths are resolved relative to the project unless absolute. `CHESS_CONFIG` can select a different override file. Unknown fields fail clearly.

| Setting | Use |
| --- | --- |
| games_dir/output_dir/data_dir/logs_dir | Input, validated artifacts, SQLite/OAuth token, per-job logs |
| width/height | 1080/1920 or 720/1280; change both together |
| fps/target_seconds/min_seconds/max_seconds | 30 FPS default; 15–60 seconds, 25–50 normally |
| style/orientation/brand | meme_chaos, cinematic, clean_chess; white/black; channel name |
| music_volume/sfx_volume | 0–1; initial 0.22/0.5; effects duck music; final -16 LUFS target |
| music_file/music_license | Optional user music; source/permission required; otherwise synthesized music |
| tts_file/tts_license | Optional local narration WAV and source declaration; music ducks under speech |
| font_path | Optional absolute path to a licensed TrueType font; otherwise installed system font |
| min_plies/max_excerpt_plies | Filter minimum 6 plies; coherent excerpt max 14 by default |
| engine_path/engine_seconds/engine_threads | Optional local Stockfish; 0.08 s/position, 2 threads, 64 MB hash |
| ai_provider/ai_model | local default; optional openai writes a proposed hook/title for human review |
| host/port | Loopback default; Setup selects 0.0.0.0 for Docker; port 8765 |
| output_prefix | Safe filename prefix; a UUID prevents overwrites |
| upload_privacy/allow_public/private_test_video_id | private default; explicit gate for public after a recorded test |
| debug/retention_days | Retain mixed WAV if debug; cleanup removes only old factory temporary WAVs |
| min_free_gb/ffmpeg/ffprobe/encoder/seed | Disk guard, executable names/paths, verified CPU libx264, deterministic audio |

If your laptop needs more speed, use 720 mode. All frames stream to FFmpeg; no enormous frame directory. GPU acceleration is not enabled: an RTX 4050 alone does not prove an NVENC build or compatibility. CPU libx264 is the supported, verified encoder.

For optional Stockfish, download the appropriate Windows x64 build from the official `stockfishchess.org` download page, extract it, scan/use its documented release checksums where provided, and put the **full executable path** in `engine_path`. Doctor verifies the file, and actual analysis verifies engine startup. Missing executables fail rather than silently pretending to analyze. Only engine-verified evaluation losses can produce the costly-move caption; comedy templates never assert a blunder.

Optional local narration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Narrate.ps1 -Text "The king would like a refund."
```

Then set `tts_file` to the generated WAV's absolute path and fill `tts_license` with your source/voice terms. This uses Windows system speech, optional and untested in the Linux cloud. External music/narration gets trimmed or padded to the configured duration. Automatic synthesized music is always available.

Optional OpenAI: set `ai_provider` to `openai` and store `CHESS_AI_API_KEY` in `.env`. ChatGPT Plus does **not** include API credits. No website scraping is used. AI text is stored as an `ai_draft` in metadata for review, not inserted as unchecked chess claims. The video and publishing metadata remain deterministic local content. Never commit `.env`, OAuth client files or `data`.

## YouTube setup: only after local rendering works

1. At Google Cloud Console create a project, enable **YouTube Data API v3**, and configure Google Auth Platform/OAuth consent. For a personal channel use External/testing and add your own Google account as a test user. Create an OAuth **Desktop app** client. Download JSON to `config/client_secret.json`; it is ignored by Git.
2. In the project PowerShell window:

   ```powershell
   .\.venv\Scripts\python.exe .\scripts\youtube_auth.py
   ```

   Approve the browser consent for your channel account. Official installed-app loopback OAuth is used. A local refresh token is saved under `data/youtube_token.json`. Do not copy it into n8n or share it. Protect the project/data folders with your Windows user's filesystem permissions. Reauthorize if consent/test-mode token expiry requires it.
3. Produce a non-dry render, review the MP4, provenance and metadata, then use the separate publish workflow or:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Review-And-Publish.ps1 -JobId YOUR_JOB_ID
   ```

   It opens the video and asks you to type APPROVE. Default is **private**. Only an API response containing a video ID is recorded as success. Check the video in YouTube Studio, including copyright processing and actual privacy, before continuing.

For later public uploads set `upload_privacy:"public"`, `allow_public:true` and `private_test_video_id` to a **confirmed recorded private/unlisted upload** from this database. Restart the service. A review approval is still needed for each job. Private/unlisted workflows can run without that public gate. In config use `unlisted` for an unlisted testing phase if desired.

Uploads use official resumable chunks and refresh handling. The service atomically claims each job; confirmed uploads return the existing ID on subsequent calls. If the connection/process dies after YouTube may have received the video, the job stays `uploading` or `uncertain`, and no second insert is attempted. Inspect YouTube Studio and resolve manually rather than blindly uploading again. Request-level timeout does not establish upload failure. Do not delete the DB to reset this guard.

YouTube API quota costs and verification requirements change; consult the current official quota and videos.insert documentation. Some unverified API projects are restricted to private uploads regardless of requested privacy, and testing OAuth refresh tokens can expire. Category is Gaming (20), hashtags are included; there is no API flag that guarantees Shorts classification. YouTube determines classification and processing. Thumbnail JPG is generated for review; automatic custom-thumbnail upload is not included because Shorts cover behavior differs by surface. No channel/account credentials or real upload were available in the cloud tests.

## Output and operations

Each job directory holds a validated MP4, thumbnail, contact sheet, metadata JSON (FEN, moves, sources, script and asset rights), validation JSON and FFmpeg log. SQLite stores request keys, states, selected games and confirmed upload IDs. Per-job service logs are in `logs`. Failed artifacts stay for diagnosis; no failed video is eligible for publishing. Restart marks queued/running render jobs failed instead of losing them silently. A new request key can retry a failed render; never retry an uncertain upload automatically.

Single worker and a three-job queue limit bound CPU usage. Do not run multiple service workers or a simultaneous CLI render against the same DB: selection is serialized by the service. The workflow's metadata generation happens inside the Python pipeline, so there is no extra AI dependency in n8n. Cleanup deletes only old soundtrack WAVs inside UUID job directories; originals, completed MP4s and metadata are retained. Back up `data/factory.sqlite3` and `output` locally, but keep OAuth tokens out of shared backups.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Doctor.ps1
.\.venv\Scripts\python.exe -m renderer.cli cleanup
```

Advanced Linux/cloud setup uses `python -m venv .venv`, `.venv/bin/python -m pip install -r requirements.lock.txt`, a random `CHESS_SERVICE_TOKEN` in `.env`, then `.venv/bin/python -m uvicorn renderer.service:app --host 127.0.0.1 --port 8765 --workers 1 --no-access-log`. Use the existing checkout; no Git worktree is required. API examples and known limitations are in `docs/TROUBLESHOOTING.md` and `TEST_REPORT.md`.

## Content responsibility

No external copyrighted music, commercial memes or player photos are downloaded. Confirm rights/source terms for your PGNs and supplied assets. Template variety is limited; review jokes and excerpts and add your own editorial perspective. YouTube can reject repetitive or mass-produced content for monetization even if the upload is technically valid. This project makes no claims about virality or revenue.
