# Kfir's stable Yapfast fork

Based on the **v0.3.0 release**, commit
`03862f6394fad09b541d731181b819a3c9713d3f`, with its original Slint 1.18.1
and Skia 0.153.3 pins. The release's account/voice dock, navigation, fonts,
profile cards, settings, and renderer patches are unchanged.

The previous fork started from unreleased `main`, which included a broad UI
redesign and Slint 1.19 development code. That introduced the new appearance
and profile controls. Its profile card's three-dot menu reused the card's
positioning anchor, moving the open card. That unreleased profile control is
absent from the release UI restored here. The previous fork also fixed chat
at 420px with no resize control; that limitation was ours.

The changes on top of the release are limited to:

- Applying incoming camera orientation before fitting video in its tile,
  preserving metadata through packet reordering, assembly, and RTX.
- Keeping a voice call visible beside its chat. Drag the chat's left edge
  to resize it; its width is saved independently of navigation and threads.
  Double-click the divider to restore 420px. It reserves at least 240px for
  the call, clamps chat to 280–800px where space permits, and narrows chat
  further in small windows. Opening a menu does not size the conversation.
  Closing chat leaves the call at full height: the hidden column no longer
  passes its children's zero maximum height to the shared call layout.
- A distinct **Yapfast — Kfir** window/app ID and user-local installer.

Build using [building.md](building.md), then run
`scripts/install-kfir-desktop` (or pass `--binary PATH`). Existing fork data
is preserved. The first install copies the original app's settings and
caches to a separate `yapfast-kfir` folder. Credentials remain in Yapfast's
existing OS credential store.

Tests cover video rotation, RTP orientation metadata, actual mouse drags,
resize limits, saved width/restoration, narrow windows, call/PiP visibility,
and menu opening without shifting the release layout. The real close button
is exercised through the application callback. A separate rendered-window
regression checks the call after six open/close cycles, a divider drag, and
narrowing the window; it reproduces the blank view that headless preview
geometry missed. Run it with Xvfb, xdotool, ImageMagick, Pillow and bun:

```sh
python3 testing/probe_call_chat.py --output /tmp/yapfast-call-chat
```

It uses a private display, bus, profile and fake Discord without joining a
call. Visual comparisons use the packaged 0.3.0 binary and that local account.
