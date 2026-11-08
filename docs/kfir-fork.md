# Kfir's Yapfast fork

This fork keeps the upstream Discord sign-in and adds two call UI fixes:

- Camera orientation from Discord's RTP CVO extension survives reordering,
  frame assembly and retransmissions. The decoded I420 planes rotate before
  fitting the picture in its tile, so portrait/landscape phone video has the
  correct orientation and aspect ratio. No rotation is guessed from a face.
- Opening a voice channel's chat keeps its call stage visible on the left.
  Chat takes up to 420 pixels, capped at 42% of the conversation area. Closing
  it gives the stage its width back. The video still floats when navigating
  to another conversation; opening the current call's chat never triggers it.
  Direct-message calls keep their existing position above their messages.

The window and launcher are named **Yapfast — Kfir**, with a distinct desktop
app ID. Build using the upstream instructions in [building.md](building.md),
then run `scripts/install-kfir-desktop` (or pass `--binary PATH` for another
build profile). This installs a user-local binary, icon and desktop entry.

The first install copies the packaged app's local settings and encrypted
caches to a separate `yapfast-kfir` data folder. Sign-in continues through
Yapfast's existing OS credential store; no token is put in the source,
launcher or installer. Later installs preserve the fork's local data.
The original packaged app stays available under its existing launcher.

Regression coverage includes RTP extension formats and retransmissions,
pixel-level plane rotation at all four orientations with odd sizes and padded
strides, and call/chat geometry at several window sizes.
