## ScorebookPad

`ScorebookPad` is now a standalone native iPad app.

It keeps its own event log, replay-derived game state, undo/redo stack, lineup generation, scorecards, substitutions, baserunner events, and JSON save files locally on-device. It does not depend on the FastAPI service or the web frontend.

### Requirements

- Xcode 26.3 or newer
- `xcodegen`

### Generate the Xcode project

```bash
cd ios
xcodegen generate
```

### Run in the simulator

1. Open `ios/ScorebookPad.xcodeproj` in Xcode.
2. Choose an iPad simulator.
3. Run the `ScorebookPad` scheme.

Saved games are written into the app's sandboxed documents directory under `SavedGames/` using the same JSON event-log structure as the desktop app.

### Tests

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
xcodebuild -project ios/ScorebookPad.xcodeproj \
  -scheme ScorebookPad \
  -destination 'platform=iOS Simulator,name=iPad Air 13-inch (M3),OS=26.2' \
  test
```
