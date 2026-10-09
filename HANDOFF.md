# Caption Shades: handoff for ChatGPT

**Written:** 2026-10-09, by Claude, for ChatGPT picking this project up.
**Repo:** https://github.com/brgarst-blip/caption-shades (public)
**Live prototype:** https://brgarst-blip.github.io/caption-shades/
**Owner:** Brendan (GitHub `brgarst-blip`)

## Auto EQ update — 2026-10-09

The app now defaults to **Auto**, with **Captions** and **EQ** overrides beside the main controls. After 2.5 seconds of audible sound without words, Auto shows a 16-band microphone spectrum. Recognition remains active; any nonempty speech result (including hidden interim guesses) interrupts EQ, with a 3-second caption hold. Quiet exits EQ after 1.2 seconds. This is an experimental sound fallback, **not** music classification; environmental noise can trigger it and sung lyrics can interrupt it.

The startup demo previews synthetic EQ → scripted captions → EQ. **Start listening** stops that preview and uses the microphone. FFT size is now 2048. Voice-baseline learning uses audio near recognized words instead of all loud frames; mixed music/speech can still influence calibration. Manual calibration should be done with music paused.

Logs are **v3 — Auto EQ**, including mode transitions, session-start settings, threshold/mode changes and periodic audio/gate summaries. `__cs.state()` includes selected mode, active display and EQ band values. Tests: `node --test tests/auto-eq.test.cjs` (deterministic browser/audio stubs, not real-device speech validation). This section supersedes older descriptions below where they differ. Keep shipping changes from `main` to `gh-pages`.

Read this file first, then `index.html` (the whole app is that one file, ~1,080 lines, no build step). Sections 2–7 were checked against the code at commit `9be0394`; section 1 is what Brendan has said about the project.

---

## 1. What Brendan is building

Wearable LED glasses that live-caption **his own speech** across the front of the lenses, in the spirit of Matt Bellamy's glasses on Muse's *Wow! Signal* tour. The louder he talks, the more aggressive and animated the color gets.

What he has said about it:

- It's for **day-to-day wear**, not a Halloween costume.
- He's **testing on his iPhone first**, and the plan is for **the phone to do the processing** (speech recognition, loudness, rendering) with the glasses as the display.
- He has an **iPhone and no Mac**, so anything that needs Xcode on his own machine is off the table unless that changes.
- Frame references he's given: **Pit Viper The Original, Wide Fit**, fits him perfectly. He also owns **Ray-Ban Meta, size 50□22 150**. The prototype assumes a **140 mm** wide front (see §5).

## 2. Where things stand

A working **iPhone Safari prototype** that listens, captions, scores loudness per word, and draws the result on a **to-scale simulation of a buildable LED grille** (shutter-shade style: horizontal bars of LEDs with see-through gaps between them). No hardware exists in the repo yet: no schematics, firmware, BOM, or phone-to-glasses link.

Commit history:

| Commit | What it did |
|---|---|
| `acf5a2a` | First prototype: live captions on a simulated LED grille, four loudness tiers, shout takeover with lightning. |
| `9be0394` | Buildable LED grid (real LED sizes, bar spacing, manufacturability check), three word display modes, typing cursor. |
| `cfbc68a` (on `gh-pages`) | PR #1 merged `main` into `gh-pages`. |

**Branches:** `main` is the source. `gh-pages` is what the live URL serves; shipping has been done by merging `main` into `gh-pages` (that's what PR #1 was). As of `9be0394` the two branches have identical app files.

## 3. How the prototype works

### Pipeline

```
mic ──► Web Audio analyser ──► per-frame dB + high-frequency ratio ──► intensity score ("live", "heat")
                                                                              │
Safari SpeechRecognition ──► words (interim + final) ──► each new word gets a score ──► tier
                                                                              │
                                     source canvas (what the display "wants" to show)
                                                                              │
                         LED mode: downsample to one value per LED ──► draw LEDs to scale + bloom
                         Ideal mode: draw source at full resolution inside the lens shape
```

Main loop (`frame()`, every animation frame): `analyze` → `updateBaselines` → `tickDemo` → `stepLive` → `renderSource` → `renderGlasses` → `updateMeter`.

### Loudness → intensity score

`scoreOf(db, hf)`:

```
score = max(0, 0.15 + 0.85 · (dB − normalVoice) / shoutRange
              + 0.2 · clamp((hfRatio − hfBase) / 0.25, −0.4, 0.8))
```

- `0.15` ≈ normal voice, `1.0` = full shout.
- `shoutRange` is the **Shout threshold** setting: dB above normal voice that counts as a shout. Default 16, slider 8–30.
- `hfRatio` = power in 2–6 kHz ÷ power in 150 Hz–6 kHz. Shouting pushes energy up the spectrum, so this catches a shout even when the mic level doesn't jump as much.

Baselines (`updateBaselines`, every 500 ms):

- **Room noise** = 15th percentile of the last ~600 frames' dB (clamped −90…−20).
- A frame is **voiced** when dB > max(noise + 9, −62).
- **Normal voice** = 70th percentile of voiced dB (never below noise + 8). It keeps learning as he talks.
- **hfBase** = median voiced `hfRatio`.
- **Calibrate** button: 4 s of normal talk replaces that history (needs ≥ 40 voiced frames).

Analyser: FFT size 1024, smoothing 0, read once per animation frame.

Smoothing (`stepLive`):

- **live** (drives the meter, glow ring and cursor): rises with a 30 ms time constant, falls with 350 ms.
- **heat** follows live slowly (2 s up, 5 s down) so a rant builds instead of flickering. New words get a bump of `0.25 · max(0, heat − 0.3)`.

### Giving each word a score

Recognition lags the audio, so `newScores(k, t)` looks back when `k` new words arrive: it takes the voiced frames from the end of the last assignment (at most 2.5 s back) up to 200 ms ago, splits them evenly into `k` slices, and scores each word as the **75th percentile** of its slice plus the heat bump. If there are fewer than `2k` frames, every new word gets the 75th percentile of the last 1.2 s.

A word's tier is **fixed when it first appears**. If Safari later revises the text, the word's text updates but its tier doesn't.

### Tiers and how they look

Thresholds in `TIER = [0, 0.45, 0.70, 1.0]`.

| Tier | Score | Text | Glow ring (edge LEDs) |
|---|---|---|---|
| Calm | < 0.45 | White Times New Roman | Off |
| Raised | 0.45–0.70 | Times New Roman bold, amber → orange gradient | Amber, brighter as it climbs |
| Loud | 0.70–1.0 | Anton, UPPERCASE, magenta/pink gradient, pops in and pulses | Pulsing magenta |
| Shout | ≥ 1.0 | Takes over the whole display: rainbow letters one by one, random sparks, white flash, two lightning bolts, shake. Held 720 ms (380 ms if another shout is queued). | Chasing rainbow |

The glow ring and the typing cursor react to `live` instantly, before any words arrive. `prefers-reduced-motion` turns off the shake and letter bounce and dims the flash.

### Word display modes (Settings › Words)

- **Scroll** (default): one line that slides left to keep the newest word in view; words slide in.
- **Pop on:** words drop in place left to right; a full line or a pause over 1.5 s starts a fresh line.
- **One word:** each word alone, centered, held about 170 ms; if more than three pile up it skips ahead.

Text fades out over 0.8 s after 3.8 s without new words (and 1.2 s of silence while listening). Early guesses (interim results) draw at 68% opacity until final.

**Typing cursor:** a block caret after the last word, shown when he's been voiced in the last 700 ms and no word has arrived for 350 ms, colored by the current tier.

### LED rendering (`renderGlasses`)

- In LED mode the source canvas is 4 px per LED across and tall enough per row to match the real bar spacing.
- Each LED's color = `0.55 × brightest pixel in its block + 1.15 × block average`, capped at 255, so thin serif strokes don't vanish the way they would with a plain average.
- LEDs inside the lens outline only (`lensPath()`: one shield shape with rounded corners and a nose notch). The outermost LEDs of that shape form the glow ring.
- LEDs are drawn as circles at their real size in mm over dark bars, then a cheap bloom (downscale to ⅓ and ⅑, add back).
- Ideal mode skips the LED grid and draws the source at 1240 px wide clipped to the lens.

## 4. Speech and iOS Safari: workarounds already in the code

These were all needed to make it work on iPhone. Don't remove them without testing on a real iPhone.

- Uses `webkitSpeechRecognition`, `en-US`, `continuous`, `interimResults`. **Dictation must be on** (Settings › General › Keyboard) or Safari blocks it.
- Must be opened in **Safari itself, not a home-screen shortcut**.
- Safari **repeats or accumulates results**; `rec.onresult` normalizes and collapses them into one transcript.
- Recognition sessions **end on their own** often. `onend` restarts after 60 ms, backing off to 1.2 s if it ended within 1.5 s three times running.
- Safari sometimes **refuses an automatic restart with `not-allowed`**. The app then shows "Tap to resume", and tapping the glasses restarts it.
- Everything iOS wants **inside the user's tap** (resume `AudioContext`, `rec.start()`) happens **before the first `await`** in `startListening()`.
- `getUserMedia` with **echoCancellation, noiseSuppression and autoGainControl all off**, since AGC would flatten the loudness signal.
- The analyser feeds a **zero-gain node into the destination** so Safari keeps pulling audio through the graph.
- **Screen wake lock** while listening. On returning to the page it re-requests the wake lock, resumes audio and restarts recognition.
- The mic stream and speech recognition can fight over the mic. **Loudness tracking** in Settings turns the audio analysis off to isolate that.

**Lag** (chip at the top, median shown) = time from voice onset to the first word appearing. Green under 600 ms, amber under 1 s, red above.

## 5. Hardware assumptions baked into the code

| Constant | Value | Meaning |
|---|---|---|
| `FRONT_MM` | 140 | Width of the glasses front |
| `ASPECT` | 3.1 | Front width ÷ height (≈ 45 mm tall) |
| `LEDS.fine` | 78 across, 1.0 mm LEDs on 1.4 mm bars | Code comment: 1 × 1 mm, 5 mA per color |
| `LEDS.bright` | 66 across, 1.6 mm LEDs on 1.9 mm bars | Code comment: 1.6 × 1.5 mm, 12 mA per color, about twice as bright |
| `MIN_GAP_MM` | 1.0 | Narrowest see-through slot a board maker will reliably cut |
| Rows | 6–20, default 14 | Rows of LEDs (one per bar) |

LEDs across is fixed by how tightly the LEDs sit side by side. Rows only change the bar spacing. Figures the page reports (LED count is less than across × rows because the lens shape trims the corners and nose):

| LED size | Bars | LEDs | See-through | Gap |
|---|---|---|---|---|
| 1 mm | 6 | 438 | 81% | 6.1 mm |
| 1 mm | 10 | 726 | 69% | 3.1 mm |
| **1 mm** | **14 (default)** | **1,020** | **57%** | **1.8 mm** |
| 1 mm | 17 | 1,236 | 47% | 1.3 mm |
| 1.6 mm | 6 | 368 | 75% | 5.6 mm |
| 1.6 mm | 10 | 618 | 58% | 2.6 mm |
| 1.6 mm | 14 | 862 | 41% | 1.3 mm |

Most bars before gaps drop under 1 mm: **18 with 1 mm LEDs, 15 with 1.6 mm LEDs.**

No power budget, driver choice or brightness-in-daylight work has been done yet; the mA figures above are the only electrical numbers in the repo.

## 6. Other things worth knowing in the code

- **Settings** persist in `localStorage` under `caption-shades`: `{ range, rows, led, flow, view, interim, cursor, analysis }`.
- **Demo** plays on load: a scripted line that climbs from calm to shout ("These glasses are completely normal…" → "TAKE A BOW! WOW."), with fake loudness. Defined in `DEMO`.
- **Test hook** in the console: `__cs.feed(text, finalCount)` injects a transcript as if Safari produced it, `__cs.state()` returns words with scores and tiers plus live/heat/baselines/lags, `__cs.log()` returns the event log.
- **Copy log** (Settings) copies a header (`Caption Shades log v2`, user agent, settings, noise/normal-voice/hfBase, lag list) plus timestamped events (`mic`, `rec`, `onset`, `words`, `lag`, `shout`, `calib`, `wake`, `vis`). This is how Brendan reports what happened on his phone. Its help text currently says to paste it "back to Claude".
- Fonts: **Anton** for loud tiers and **Times New Roman** for calm, both measured so text fills the display height. UI uses Archivo and IBM Plex Mono from Google Fonts.

## 7. How work has been done so far

- **One file, no build step.** Keep the app in `index.html`.
- Keep the **README in sync** with Settings when you add or change one.
- **Test on a real iPhone in Safari.** Desktop Chrome can load the page and the demo, but it doesn't reproduce Safari's speech recognition behavior.
- Tune from **Copy log** output rather than guesses.
- Ship by merging `main` into `gh-pages`.

## 8. Open threads (nothing in the repo covers these yet)

- **Phone → glasses link:** what the phone sends (finished LED frames vs. text plus tier and let the glasses render), over what (BLE, etc.), and the latency budget on top of recognition lag.
- **Display electronics:** microcontroller, LED type and driver, matrix scanning vs. addressable LEDs, power and battery for the LED counts above, brightness outdoors.
- **Frame and fit:** how the 140 mm grille maps to the frames he's named, and what the wearer sees through the gaps.
- **Only his voice:** the goal is captioning his own speech, but the phone mic hears everyone nearby. Nothing in the code tells his voice apart from other people's.
- **Beyond Safari:** the prototype assumes Safari stays in the foreground with the screen on (wake lock, restart when the page comes back). A native or always-on version would need a different speech path, and he has no Mac.

## 9. Starter prompt

Brendan can paste this into ChatGPT along with a link to this file:

> Read HANDOFF.md and index.html in github.com/brgarst-blip/caption-shades. Summarize where the project stands in five bullets, then ask me what I want to tackle next.
