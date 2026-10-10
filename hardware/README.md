# Caption Shades hardware

## LED panels (`panel/`)

Two flat boards, one per side of the glasses, mirrored. `panel/gen_panel.py` generates them (standard-library Python; matplotlib only for the preview):

```
python3 hardware/panel/gen_panel.py
```

It writes `panel_R.kicad_pcb`, `panel_L.kicad_pcb` (KiCad 8), `placement_R.csv`, `placement_L.csv` and `preview.png`. The board files are generated, so they are not committed; rerun the script after changing it.

### Status: Rev D-1, layout started

Done:
- Board outline from the Rev D blueprint: 14 bars in a 55 mm tall window, 1.4 mm bars on a 3.93 mm pitch, Pit Viper-size nose opening (36 × 33 mm), 2 mm solid ring hidden under the frame, parts tab up to y = 59 under the top rim.
- 13 see-through slots per panel between the bars.
- 456 LEDs per panel (912 total), 1.8 mm apart, each with a 100 nF capacitor on the back directly under it.
- Nets assigned and the data chain ordered: it snakes along each bar, top to bottom, turning at the seam spine, the outer ring and the nose ring.

Not done yet:
1. **LED footprint check.** The LED pads are a placeholder (typical 1010 package: four 0.35 mm pads at ±0.3 mm; pin 1 DO, 2 VDD, 3 GND, 4 DI from the datasheet text). Replace them with LCSC's footprint for C5349953 before ordering.
2. **Copper.** In1 = GND plane, In2 = +5 V plane, F.Cu = data between LEDs, B.Cu = capacitors. Every LED and capacitor power pad needs a via into the planes, which means via-in-pad (filled and capped); confirm cost with JLCPCB for 4-layer 0.8 mm.
3. **Parts tab** (y 55–59, behind the top rim): wire pads (+5 V in, GND, data in, LED-enable), TPS22965 LED power switch, 2 A fuse, 5 V TVS, SN74LV1T125 level shifter with a 100 Ω series resistor, bulk capacitors.
4. **Seam.** The two panels are separate boards; each gets its own data line and power from the wiring channel, so nothing has to cross the seam.
5. **JLCPCB outputs:** Gerbers, drill, BOM and placement files (CPL), after a design-rule check in KiCad.

### Decisions so far

| Item | Choice | Why |
|---|---|---|
| LED | XINGLIGHT XL-1010RGBC-WS2812B, 1.0 × 1.0 mm | Smallest addressable RGB LED; keeps the bars thin. |
| Board | 4-layer, 0.8 mm, black solder mask both sides | Planes carry LED current; black hides the bars. |
| Decoupling | 100 nF 0201, one per LED, on the back | Datasheet asks for one per LED; no room on the 1.4 mm bar front. |
| Data | One chain per panel, about 456 LEDs, about 14 ms per frame at 800 kHz | Two chains keep the refresh above 60 frames per second. |
| Power | 5 V from the pocket power bank through the tether; switch cuts LED power between captions | Dark LEDs still draw about 2 mW each, about 1.9 W for the whole display. |
| Controller | Seeed XIAO nRF52840 Sense in the arm pod | Bluetooth, mic, charger, enough free pins for two data lines, the switch and the nose sensor. |
