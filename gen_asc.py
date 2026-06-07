#!/usr/bin/env python3
"""
Generate v2l.asc — LTspice schematic for the V2L circuit.

Ordering follows the LTspice .asc convention observed in working schematics:
  1. Version + SHEET
  2. WIRE lines
  3. FLAG lines
  4. SYMBOL + SYMATTR blocks
  5. TEXT (SPICE directives and comments)

Pin offsets confirmed from .asy files (~/Library/Application Support/LTspice/lib/sym/):
  Voltage : +(0,16)  –(0,96)
  Res     : p1(16,16)  p2(16,96)
  Cap     : p1(16,0)   p2(16,64)
  Ind     : p1(16,16)  p2(16,96)
  Diode   : anode(16,0)  cathode(16,64)   [SpiceOrder 1 = anode = "+"]
  Sw      : A(0,16)  B(0,96)  NC+(−48,80)  NC−(−48,32)
  Bv      : +(0,16)  –(0,96)

Rotation rule for offset (px,py) with anchor (ax,ay):
  R0  : (ax+px, ay+py)      R90 : (ax+py, ay−px)
  R180: (ax−px, ay−py)      R270: (ax−py, ay+px)

NOTE: LTspice macOS batch mode (-b) does not support .asc files — use the GUI:
      open -a LTspice v2l.asc
      Then press the Run button and probe any node to view waveforms.
"""

wires  = []   # WIRE x1 y1 x2 y2
flags  = []   # FLAG x y net
syms   = []   # (sym_line, [attr_lines])
texts  = []   # TEXT x y align size !directive  or  ;comment

def wr(x1,y1,x2,y2):  wires.append(f"WIRE {x1} {y1} {x2} {y2}")
def fl(x,y,net):       flags.append(f"FLAG {x} {y} {net}")
def tx(x,y,s):         texts.append(f"TEXT {x} {y} Left 2 !{s}")
def cm(x,y,s):         texts.append(f"TEXT {x} {y} Left 2 ;{s}")

def sym(name, x, y, rot, inst, val=None):
    attrs = [f"SYMATTR InstName {inst}"]
    if val is not None:
        attrs.append(f"SYMATTR Value {val}")
    syms.append((f"SYMBOL {name} {x} {y} {rot}", attrs))

# ─────────────────────────────────────────────────────────────────────────────
# WIRES  (local connections within sections)
# ─────────────────────────────────────────────────────────────────────────────

# Module A — bridge
wr(240, 368, 336, 368)   # rect_p rail (D1 & D2 cathodes)
wr(336, 368, 464, 368)   # rect_p rail extended to Cgrid_filter p1
wr(240, 560, 336, 560)   # GND rail   (D3 & D4 anodes)
wr(240, 432, 240, 496)   # right AC column — gridA (D1 anode ↕ D3 cathode)
wr(336, 432, 336, 496)   # left  AC column — gridB (D2 anode ↕ D4 cathode)

# Module C — H-bridge switch legs
wr(1104, 432, 1104, 512)   # outA: S1.B → S2.A
wr(1296, 432, 1296, 512)   # outB: S3.B → S4.A

# Module C — LC filter nfilt rail
wr(1584, 432, 1680, 432)   # L_filter p2 → C_filter p1
wr(1680, 432, 1776, 432)   # C_filter p1 → Rload p1

# ─────────────────────────────────────────────────────────────────────────────
# FLAGS / net labels
# ─────────────────────────────────────────────────────────────────────────────

# Module A — grid source
fl(80,  432, "gridA")   # Vgrid + terminal
fl(80,  512, "gridB")   # Vgrid – terminal

# Module A — bridge net labels
fl(288, 368, "rect_p")  # on rect_p rail (D1 & D2 cathodes, Cgrid_filter top)
fl(240, 432, "gridA")   # top of right AC column (joins Vgrid+)
fl(336, 432, "gridB")   # top of left  AC column (joins Vgrid–)
fl(288, 560, "0")       # GND rail mid-point

# Module A — filter components
fl(464, 432, "0")       # Cgrid_filter bottom
fl(544, 368, "rect_p")  # Rbleed top
fl(544, 448, "0")       # Rbleed bottom

# Module B — battery
fl(720, 432, "batt")    # Vbattery +
fl(720, 512, "0")       # Vbattery –
fl(816, 432, "batt")    # Rinternal p1
fl(896, 432, "dcbus")   # Rinternal p2

# Module C — H-bridge (left leg: S1/S2, outA)
fl(1104, 352, "dcbus")
fl(1104, 432, "outA")   # sole outA flag on the S1.B-S2.A wire segment
fl(1056, 416, "gp")     # S1 NC+
fl(1056, 368, "0")      # S1 NC–
fl(1104, 592, "0")      # S2 B
fl(1056, 576, "gn")     # S2 NC+
fl(1056, 528, "0")      # S2 NC–

# Module C — H-bridge (right leg: S3/S4, outB)
fl(1296, 352, "dcbus")
fl(1296, 432, "outB")   # sole outB flag
fl(1248, 416, "gn")     # S3 NC+
fl(1248, 368, "0")      # S3 NC–
fl(1296, 592, "0")      # S4 B
fl(1248, 576, "gp")     # S4 NC+
fl(1248, 528, "0")      # S4 NC–

# Module C — LC filter + load
fl(1504, 432, "outA")   # L_filter p1
fl(1632, 432, "nfilt")  # on nfilt rail (sole nfilt flag)
fl(1680, 496, "outB")   # C_filter p2
fl(1776, 512, "outB")   # Rload p2

# Module D — control
fl(800,  1232, "ref")
fl(800,  1312, "0")
fl(1000, 1232, "carrier")
fl(1000, 1312, "0")
fl(1200, 1232, "gp")
fl(1200, 1312, "0")
fl(1400, 1232, "gn")
fl(1400, 1312, "0")

# ─────────────────────────────────────────────────────────────────────────────
# SYMBOLS
# ─────────────────────────────────────────────────────────────────────────────

# Module A — Grid source
sym("Voltage", 80, 416, "R0", "Vgrid", "SINE(0 325 50)")

# Module A — Full-wave diode bridge (R180: anode below, cathode above → current ↑)
# D anode=(ax−16,ay)  cathode=(ax−16,ay−64)
sym("Diode", 256, 432, "R180", "D1", "D1N4007")  # anode(240,432)=gridA  cathode(240,368)=rect_p
sym("Diode", 352, 432, "R180", "D2", "D1N4007")  # anode(336,432)=gridB  cathode(336,368)=rect_p
sym("Diode", 256, 560, "R180", "D3", "D1N4007")  # anode(240,560)=GND    cathode(240,496)=gridA
sym("Diode", 352, 560, "R180", "D4", "D1N4007")  # anode(336,560)=GND    cathode(336,496)=gridB

# Module A — Smoothing cap + bleed resistor
# Cap R0 p1=(ax+16,ay):   anchor(448,368) → p1=(464,368)=rect_p  p2=(464,432)=GND
sym("Cap", 448, 368, "R0", "Cgrid_filter", "1000u")
# Res R0 p1=(ax+16,ay+16): anchor(528,352) → p1=(544,368)=rect_p  p2=(544,448)=GND
sym("Res", 528, 352, "R0", "Rbleed", "500")

# Module B — Battery
# Voltage R0: anchor(720,416) → +(720,432)=batt  –(720,512)=GND
sym("Voltage", 720, 416, "R0", "Vbattery", "400")
# Res R90 p1=(ax+16,ay−16): anchor(800,448) → p1=(816,432)=batt  p2=(896,432)=dcbus
sym("Res", 800, 448, "R90", "Rinternal", "0.5")

# Module C — H-bridge switches
# Sw R0: A=(ax,ay+16) B=(ax,ay+96) NC+=(ax−48,ay+80) NC−=(ax−48,ay+32)
sym("Sw", 1104, 336, "R0", "S1", "MySwitch")
sym("Sw", 1104, 496, "R0", "S2", "MySwitch")
sym("Sw", 1296, 336, "R0", "S3", "MySwitch")
sym("Sw", 1296, 496, "R0", "S4", "MySwitch")

# Module C — LC filter + load
# Ind R90 p1=(ax+16,ay−16): anchor(1488,448) → p1=(1504,432)=outA  p2=(1584,432)=nfilt
sym("Ind", 1488, 448, "R90", "L_filter", "10m")
# Cap R0 p1=(ax+16,ay):   anchor(1664,432) → p1=(1680,432)=nfilt  p2=(1680,496)=outB
sym("Cap", 1664, 432, "R0", "C_filter", "4.7u")
# Res R0 p1=(ax+16,ay+16): anchor(1760,416) → p1=(1776,432)=nfilt  p2=(1776,512)=outB
sym("Res", 1760, 416, "R0", "Rload", "50")

# Module D — PWM control
sym("Voltage", 800,  1216, "R0", "Vref",
    "SINE(0 1 50)")           # 230 V / 50 Hz mode; for 120V/60Hz use SINE(0 0.524 60)
sym("Voltage", 1000, 1216, "R0", "Vcarrier",
    "PULSE(-1.2 1.2 0 25u 25u 1u 50u)")
sym("Bv", 1200, 1216, "R0", "Bgp", "V=if(V(ref)>V(carrier),1,0)")
sym("Bv", 1400, 1216, "R0", "Bgn", "V=if(V(ref)>V(carrier),0,1)")

# ─────────────────────────────────────────────────────────────────────────────
# TEXT — comments and SPICE directives
# ─────────────────────────────────────────────────────────────────────────────
cm(80, 48,  "V2L System — Vehicle-to-Load Power Electronics Simulation")
cm(80, 80,  "Module A (left): 230V AC grid + diode bridge + 1000uF smoothing cap")
cm(80, 112, "Module B (centre-left): 400V EV traction battery with 0.5 ohm internal resistance")
cm(80, 144, "Module C (centre-right): H-bridge inverter + 10mH/4.7uF LC filter + 50-ohm load")
cm(80, 176, "Module D (bottom): 50Hz sine reference + 20kHz triangular carrier + gate comparators")
cm(80, 208, "OUTPUT: ~229 V RMS / 50 Hz  |  For 120V/60Hz: change Vref to SINE(0 0.524 60)")

for directive in [
    ".tran 0 100m 0 10u",
    ".model D1N4007 D(Is=7.02767n Rs=0.0341512 N=1.80803 Cjo=2.6e-11 M=0.333 Vj=0.7 Bv=1000 Ibv=5e-08 Tt=1e-07)",
    ".model MySwitch SW(Ron=0.01 Roff=1Meg Vt=0.5)",
    ".option plotwinsize=0",
]:
    tx(80, 1520 + texts.count(directive) * 32, directive)

# correct y positions for TEXT directives
texts_directives = [t for t in texts if t.startswith("TEXT") and "!" in t]
texts_comments   = [t for t in texts if t.startswith("TEXT") and ";" in t]
texts_clean = texts_comments  # comments go first in the text list

y = 1520
texts_clean_directives = []
for directive in [
    ".tran 0 100m 0 10u",
    ".model D1N4007 D(Is=7.02767n Rs=0.0341512 N=1.80803 Cjo=2.6e-11 M=0.333 Vj=0.7 Bv=1000 Ibv=5e-08 Tt=1e-07)",
    ".model MySwitch SW(Ron=0.01 Roff=1Meg Vt=0.5)",
    ".option plotwinsize=0",
]:
    texts_clean_directives.append(f"TEXT 80 {y} Left 2 !{directive}")
    y += 32

# ─────────────────────────────────────────────────────────────────────────────
# Assemble and print
# ─────────────────────────────────────────────────────────────────────────────
print("Version 4")
print("SHEET 1 3600 2400")
for w in wires:   print(w)
for f in flags:   print(f)
for sline, attrs in syms:
    print(sline)
    for a in attrs: print(a)
for t in texts_comments:         print(t)
for t in texts_clean_directives: print(t)
