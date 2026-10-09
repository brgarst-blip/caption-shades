# Caption Shades

Live captions for LED glasses. Calm speech shows up in white Times New Roman. As you get louder the words turn warm and bold, then pulse in color, and a shouted word takes over the whole display with rainbow letters and lightning.

This is the phone prototype. It runs in Safari on an iPhone and draws a simulated LED grille on screen, so you can tune the feel before building hardware.

## Try it

Open https://brgarst-blip.github.io/caption-shades/ in **Safari** on your iPhone (not a home-screen shortcut), tap **Start listening**, and allow the microphone and speech recognition.

If Speech shows *blocked*, turn on Dictation in Settings › General › Keyboard and reload.

## What's in Settings

- **Mode (above Settings):** *Auto* (default) shows a 16-band EQ after 2.5 seconds of audible sound without recognized words. Speech results, including early guesses, bring captions back immediately; EQ returns after a 3-second speech hold if sound continues. Quiet fades the bars and exits EQ after 1.2 seconds. *Captions* and *EQ* force the chosen display; recognition keeps running in all modes. Auto is a sound-without-transcription fallback, not a music classifier: fans, traffic and unrecognized speech can also activate it, and sung lyrics can bring captions back.
- **Shout threshold:** how many dB above your normal voice counts as a full shout.
- **Words:** *Scroll* slides the line left as you talk. *Pop on* drops each word in place and starts a fresh line when it fills or you pause. *One word* shows each word on its own.
- **LED bars:** rows of LEDs on the grille, from 6 to 20. Shows the LED count, how much of the lens you can see through, and the gap between bars, and flags gaps too narrow to manufacture.
- **LED size:** 1 mm LEDs (78 across, sharper) or 1.6 mm bright LEDs (66 across, about twice as bright, wider bars).
- **Display:** the LED grille as the hardware could draw it, to scale, or the ideal full-resolution version.
- **Show early guesses:** draws words the instant Safari guesses them, dimmed, then locks them in.
- **Typing cursor:** appears the moment you start talking, colored by how loud you are, so the glasses react before the words arrive.
- **Audio analysis / EQ:** required for microphone EQ and loudness tracking; turn off if microphone analysis and recognition conflict. Turning it back on while listening restarts microphone analysis.
- **Calibrate:** pause background music and talk normally for 4 seconds so it learns your normal voice. Automatic learning is limited to audio near recognized words, but cannot separate speech and music playing together.
- **Copy log:** v3 includes display transitions, settings at session start, setting changes and audio/EQ gate summaries, as well as recognition timings.

## Try Auto EQ

The page opens with a **simulated** EQ → captions → EQ preview. It does not record or play audio. Select **Auto**, tap **Start listening**, and allow microphone/speech access. Play music nearby, wait about 3 seconds, then say “hello” or “can you hear me.” Captions should take over when the browser returns speech results, then the spectrum should return after the speech hold. Use **Copy log** to report the result. Desktop Chrome and iPhone Safari still need testing with real microphone audio, especially speech over music and sung lyrics.

If the browser reports speech-service network errors, the app retries after 1 and 2 seconds, then pauses after the third failure and offers **Retry speech**. Microphone EQ can keep working independently. If testing inside an app’s embedded browser, paste the URL into regular Chrome or iPhone Safari. A working microphone does not prove the browser’s speech service is available. Actual speech results clear the error; merely restarting recognition does not. Stop cancels pending retries.

## How it works

- Safari's speech recognition streams words as you talk.
- The Web Audio API measures loudness and how much energy sits in the upper frequencies, against a running baseline of your normal voice.
- New words get a score from the audio that arrived since the last word. A slow-decaying "heat" value lets a rant build up instead of flickering word to word.
- The glow around the lenses reacts to loudness instantly, before the words arrive.
- EQ uses 16 logarithmic frequency bands from 60 Hz to 12 kHz (limited by sample rate), with a 2048-point FFT, fast attack, smooth release and falling peak markers. Reduced-motion preference slows the bars and removes peak markers. The Shout threshold does not affect EQ sensitivity.

Everything runs in one file, `index.html`, with no build step.

Run deterministic transition, audio and microphone lifecycle tests with `node --test tests/auto-eq.test.cjs`. These use browser stubs and synthetic frequency data; they do not measure real speech-recognition accuracy or latency.
