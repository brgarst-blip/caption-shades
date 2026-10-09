# Caption Shades

Live captions for LED glasses. Calm speech shows up in white Times New Roman. As you get louder the words turn warm and bold, then pulse in color, and a shouted word takes over the whole display with rainbow letters and lightning.

This is the phone prototype. It runs in Safari on an iPhone and draws a simulated LED grille on screen, so you can tune the feel before building hardware.

## Try it

Open https://brgarst-blip.github.io/caption-shades/ in **Safari** on your iPhone (not a home-screen shortcut), tap **Start listening**, and allow the microphone and speech recognition.

If Speech shows *blocked*, turn on Dictation in Settings › General › Keyboard and reload.

## What's in Settings

- **Shout threshold:** how many dB above your normal voice counts as a full shout.
- **Words:** *Scroll* slides the line left as you talk. *Pop on* drops each word in place and starts a fresh line when it fills or you pause. *One word* shows each word on its own.
- **LED bars:** rows of LEDs on the grille, from 6 to 20. Shows the LED count, how much of the lens you can see through, and the gap between bars, and flags gaps too narrow to manufacture.
- **LED size:** 1 mm LEDs (78 across, sharper) or 1.6 mm bright LEDs (66 across, about twice as bright, wider bars).
- **Display:** the LED grille as the hardware could draw it, to scale, or the ideal full-resolution version.
- **Show early guesses:** draws words the instant Safari guesses them, dimmed, then locks them in.
- **Typing cursor:** appears the moment you start talking, colored by how loud you are, so the glasses react before the words arrive.
- **Loudness tracking:** turn off if the mic level and speech recognition fight each other.
- **Calibrate:** talk normally for 4 seconds so it learns your normal voice.
- **Copy log:** timings and events for tuning.

## How it works

- Safari's speech recognition streams words as you talk.
- The Web Audio API measures loudness and how much energy sits in the upper frequencies, against a running baseline of your normal voice.
- New words get a score from the audio that arrived since the last word. A slow-decaying "heat" value lets a rant build up instead of flickering word to word.
- The glow around the lenses reacts to loudness instantly, before the words arrive.

Everything runs in one file, `index.html`, with no build step.
