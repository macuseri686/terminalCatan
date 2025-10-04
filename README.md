### Term Catan

A terminal-based Settlers of Catan-like game built with Python and urwid. Supports single-player and experimental multiplayer via JSON game state sync over websockets.

<img width="2226" height="1443" alt="Screenshot from 2025-10-04 12-16-53" src="https://github.com/user-attachments/assets/4d460563-cbf1-4ac5-a20b-1d7b38f22581" />

### Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m term_catan
```

### Requirements

- Python 3.10+
- A terminal that supports mouse input and 256 colors (urwid UI)
- Linux/macOS/Windows supported (use a modern terminal emulator)


### Project layout

- `term_catan/`: app package
  - `ui/`: urwid views and widgets
  - `core/`: game rules, models, AI
  - `services/`: persistence, networking, assets
  - `assets/`: generated and static art
  - `__main__.py`: entry point

### Save/Load

- Game state is a JSON-serializable dict.
- Saves are stored under `saves/save_###.json`.
- In-game, press `s` to save and `l` to load the latest save.
- From the main menu, "Load Game" shows available saves; current implementation loads the latest.

### Multiplayer (experimental)

Simple host/join over websockets. Current implementation is demo-only (echo sync):

- From the main menu choose "Host Multiplayer" and press Start to launch a local server at `ws://localhost:8765`.
- On another client choose "Join Multiplayer". Leave the default `localhost:8765` or enter a different host, then Join.
- The client sends its game state to the host; full turn sync and conflict resolution are not implemented.

### Controls

- `r`: roll dice and distribute resources
- `b`: attempt to build a road (demo: costs 1 wood + 1 brick)
- `e`: end turn (AI will auto-play when it's their turn)
- `d`: buy a development card (costs 1 wheat, 1 sheep, 1 ore)
- `k`: play a knight (if owned); moves the robber to a chosen tile
- `m`: move robber (only during robber phase after rolling a 7)
- `s`: save game
- `l`: load latest save
- `q`: quit

- `enter` (setup phase): prime placement; then click a vertex/edge with the mouse to place settlement/road
- Mouse: click on the board to place settlements/roads during setup

### License

MIT

