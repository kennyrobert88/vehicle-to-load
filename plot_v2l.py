#!/usr/bin/env python3
"""
Post-process the V2L LTspice run (v2l.raw) and produce the three
visualizations called out in Section 4 of CLAUDE.md:

  1. Rectification phase : grid AC sine  ->  flat DC across Cgrid_filter
  2. PWM inverter phase   : H-bridge output (PWM blocks) before the LC filter
  3. Clean V2L output     : smooth ~230 V AC sine across Rload

Also prints quantitative checks (DC bus level, output RMS, frequency).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PyLTSpice import RawRead

raw = RawRead("v2l.raw")
t = raw.get_trace("time").get_wave()
t = np.abs(t)  # LTspice can store time with a sign quirk

def v(name):
    return np.real(raw.get_trace(name).get_wave())

gridA   = v("V(grida)")
gridB   = v("V(gridb)")
rect_p  = v("V(rect_p)")
dcbus   = v("V(dcbus)")
outa    = v("V(outa)")
outb    = v("V(outb)")
nfilt   = v("V(nfilt)")

grid_ac   = gridA - gridB          # AC across the bridge input
bridge_out = outa - outb           # raw PWM (before LC filter)
load_v    = nfilt - outb           # across Rload (the clean V2L output)

# ---- quantitative checks --------------------------------------------------
def rms(x, tt, t0):
    m = tt >= t0
    return np.sqrt(np.trapz(x[m]**2, tt[m]) / (tt[m][-1] - tt[m][0]))

# settle: ignore first 20 ms transient, measure on 20..100 ms
t0 = 20e-3
mask = t >= t0
dc_level   = np.mean(rect_p[mask])
bus_level  = np.mean(dcbus[mask])
out_rms    = rms(load_v, t, t0)
out_pk     = np.max(np.abs(load_v[mask]))

# estimate output frequency via zero crossings of the load voltage
lv = load_v[mask]; tt = t[mask]
zc = np.where((lv[:-1] < 0) & (lv[1:] >= 0))[0]
if len(zc) > 1:
    periods = np.diff(tt[zc])
    freq = 1.0 / np.mean(periods)
else:
    freq = float("nan")

print("================ V2L quantitative checks ================")
print(f"Grid AC peak           : {np.max(np.abs(grid_ac[mask])):7.1f} V  (expect ~325 V)")
print(f"Rectified DC (Cfilter) : {dc_level:7.1f} V  mean")
print(f"EV DC bus (dcbus)      : {bus_level:7.1f} V  (expect ~400 V)")
print(f"V2L output RMS         : {out_rms:7.1f} V  (target ~230 V AC)")
print(f"V2L output peak        : {out_pk:7.1f} V")
print(f"V2L output frequency   : {freq:7.1f} Hz  (expect 50 Hz)")
print(f"Load power (Vrms^2/R)  : {out_rms**2/50:7.0f} W  into 50 ohm")
print("=========================================================")

# ---- figure ---------------------------------------------------------------
ms = t * 1e3  # time in ms for plotting
fig, ax = plt.subplots(4, 1, figsize=(11, 12), sharex=False)
fig.suptitle("Vehicle-to-Load (V2L) Simulation — LTspice (v2l.cir)", fontsize=14, weight="bold")

# 1a. Grid AC + rectified DC (Rectification phase)
ax[0].plot(ms, grid_ac, color="#1f77b4", lw=0.8, label="V(grid) AC input  [325 Vpk / 230 Vrms]")
ax[0].plot(ms, rect_p, color="#d62728", lw=1.4, label="V(rect_p) rectified DC across Cgrid_filter")
ax[0].set_title("1) Rectification phase: 230 V AC grid  →  smoothed DC")
ax[0].set_ylabel("Volts")
ax[0].legend(loc="upper right", fontsize=8); ax[0].grid(alpha=0.3)

# 2. PWM bridge output before the LC filter (full span)
ax[1].plot(ms, bridge_out, color="#2ca02c", lw=0.4)
ax[1].set_title("2) Inverter H-bridge output BEFORE LC filter — bipolar PWM blocks (±400 V)")
ax[1].set_ylabel("Volts"); ax[1].grid(alpha=0.3)

# 2b. Zoom on the PWM so the pulse-width variation is visible
zlo, zhi = 50e-3, 52e-3
zm = (t >= zlo) & (t <= zhi)
ax[2].plot(t[zm]*1e3, bridge_out[zm], color="#2ca02c", lw=0.8, label="PWM bridge output")
ax[2].plot(t[zm]*1e3, load_v[zm], color="#ff7f0e", lw=1.8, label="filtered load voltage")
ax[2].set_title("2b) Zoom (50–52 ms): PWM pulse-width variation vs. the filtered sine")
ax[2].set_ylabel("Volts")
ax[2].legend(loc="upper right", fontsize=8); ax[2].grid(alpha=0.3)

# 3. Clean V2L output across Rload
ax[3].plot(ms, load_v, color="#ff7f0e", lw=1.4,
           label=f"V(Rload)  RMS={out_rms:.0f} V  f={freq:.0f} Hz")
ax[3].axhline( out_rms*np.sqrt(2),  color="grey", ls="--", lw=0.7)
ax[3].axhline(-out_rms*np.sqrt(2),  color="grey", ls="--", lw=0.7)
ax[3].set_title("3) Clean V2L output across Rload — grid-quality ~230 V AC sine")
ax[3].set_xlabel("time (ms)"); ax[3].set_ylabel("Volts")
ax[3].legend(loc="upper right", fontsize=8); ax[3].grid(alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig("v2l_results.png", dpi=120)
print("Saved figure -> v2l_results.png")
