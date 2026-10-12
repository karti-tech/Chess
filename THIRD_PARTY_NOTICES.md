# Asset and dependency rights

- Piece silhouettes, procedural music, synthesized effects, and the demonstration move sequence are original project assets under the project MIT license. No commercial song, meme or downloaded graphic is included.
- Fonts: Windows rendering uses installed Arial Bold if available; Linux tests use installed DejaVu Sans. Fonts are not distributed in the archive. Configure a font you have rights to use when branding a channel.
- Local PGN input: game move facts and annotations/source databases can have different legal treatment. User-supplied PGNs do not automatically grant redistribution rights. Confirm your source's terms, especially annotations, player images, and database reuse. This project does not fetch Lichess or another game database.
- User audio and narration require a source/license declaration in configuration. A declaration records your information, not proof of permission.
- python-chess / chess is GPL-3.0-or-later. It is installed as a separate dependency and not bundled in this source archive. Review its license obligations if distributing a combined application. Pillow uses HPND; NumPy BSD-3-Clause; FastAPI MIT; Uvicorn BSD-3-Clause; Google API client Apache-2.0. See each installed distribution for full terms.
- FFmpeg is a separately installed executable. Its license depends on the build; the tested Linux build enables GPL and libx264. Neither FFmpeg nor Stockfish is bundled. Stockfish is GPLv3; use official releases and preserve notices if distributing it.

Each rendered job's metadata.json records its asset sources, PGN source metadata and rendering configuration. No credentials are written there.
