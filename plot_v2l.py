#!/usr/bin/env python3
"""
Post-process the V2L LTspice run (v2l.raw).

The netlist is stepped over MODE:
    MODE 1 -> 230 V / 50 Hz  (Europe / IEC)
    MODE 2 -> 120 V / 60 Hz  (North America)

Outputs:
  * console : a quantitative verification table for every output mode
  * v2l_results.png       : full 4-panel demonstration (Section-4 phases, MODE 1)
  * v2l_dual_voltage.png  : side-by-side comparison of the two output standards
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PyLTSpice import RawRead

raw = RawRead("v2l.raw")

# ---- enumerate the .step points -------------------------------------------
try:
    steps = list(raw.get_steps())
except Exception:
    steps = [0]
if not steps:
    steps = [0]

MODE_INFO = {0: ("230 V / 50 Hz  (Europe)",   230.0, 50.0, "#ff7f0e"),
             1: ("120 V / 60 Hz  (N. America)", 120.0, 60.0, "#9467bd")}

def wave(name, step):
    return np.real(raw.get_trace(name).get_wave(step))

def axis(step):
    return np.abs(raw.get_trace("time").get_wave(step))

def rms(x, t, t0):
    m = t >= t0
    return np.sqrt(np.trapz(x[m] ** 2, t[m]) / (t[m][-1] - t[m][0]))

def output_freq(lv, t, t0):
    """Fundamental frequency via FFT on a uniformly resampled window.
    LTspice uses adaptive time steps, so resample before transforming, and
    FFT (not zero-crossings) so switching ripple doesn't inflate the count."""
    m = t >= t0
    tm, lvm = t[m], lv[m]
    n = 200000
    tu = np.linspace(tm[0], tm[-1], n)
    lu = np.interp(tu, tm, lvm)
    lu = lu - lu.mean()
    dt = tu[1] - tu[0]
    spec = np.abs(np.fft.rfft(lu * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, dt)
    df = freqs[1] - freqs[0]
    band = (freqs >= 30) & (freqs <= 100)   # mains fundamental window
    k = np.flatnonzero(band)[np.argmax(spec[band])]
    # parabolic interpolation to refine the peak below FFT bin resolution
    if 0 < k < len(spec) - 1:
        y0, y1, y2 = spec[k - 1], spec[k], spec[k + 1]
        denom = (y0 - 2 * y1 + y2)
        delta = 0.5 * (y0 - y2) / denom if denom != 0 else 0.0
    else:
        delta = 0.0
    return freqs[k] + delta * df

# ---- per-mode quantitative checks -----------------------------------------
results = {}
t0 = 20e-3   # ignore startup transient
print("==================== V2L dual-voltage output checks ====================")
print(f"{'Mode':<26}{'RMS (V)':>9}{'Freq (Hz)':>11}{'Peak (V)':>10}{'Power (W)':>11}")
for s in steps:
    t = axis(s)
    load_v = wave("V(nfilt)", s) - wave("V(outb)", s)
    r = rms(load_v, t, t0)
    f = output_freq(load_v, t, t0)
    pk = np.max(np.abs(load_v[t >= t0]))
    p = r ** 2 / 50.0
    label = MODE_INFO.get(s, (f"step {s}", 0, 0, "#333"))[0]
    results[s] = dict(t=t, load_v=load_v, rms=r, freq=f, peak=pk, power=p, label=label)
    print(f"{label:<26}{r:>9.1f}{f:>11.1f}{pk:>10.1f}{p:>11.0f}")
print("========================================================================")

# ===========================================================================
# FIGURE 1 : full demonstration for MODE 1 (230 V / 50 Hz)
# ===========================================================================
s0 = steps[0]
t = axis(s0)
gridA = wave("V(grida)", s0); gridB = wave("V(gridb)", s0)
rect_p = wave("V(rect_p)", s0)
outa = wave("V(outa)", s0); outb = wave("V(outb)", s0)
grid_ac = gridA - gridB
bridge_out = outa - outb
load_v = results[s0]["load_v"]
ms = t * 1e3

fig, ax = plt.subplots(4, 1, figsize=(11, 12))
fig.suptitle("Vehicle-to-Load (V2L) Simulation — 230 V / 50 Hz mode (v2l.cir)",
             fontsize=14, weight="bold")

ax[0].plot(ms, grid_ac, color="#1f77b4", lw=0.8, label="V(grid) AC input  [325 Vpk / 230 Vrms]")
ax[0].plot(ms, rect_p, color="#d62728", lw=1.4, label="V(rect_p) rectified DC across Cgrid_filter")
ax[0].set_title("1) Rectification phase: 230 V AC grid  ->  smoothed DC")
ax[0].set_ylabel("Volts"); ax[0].legend(loc="upper right", fontsize=8); ax[0].grid(alpha=0.3)

ax[1].plot(ms, bridge_out, color="#2ca02c", lw=0.4)
ax[1].set_title("2) Inverter H-bridge output BEFORE LC filter — bipolar PWM blocks (+/-400 V)")
ax[1].set_ylabel("Volts"); ax[1].grid(alpha=0.3)

zlo, zhi = 50e-3, 52e-3
zm = (t >= zlo) & (t <= zhi)
ax[2].plot(t[zm] * 1e3, bridge_out[zm], color="#2ca02c", lw=0.8, label="PWM bridge output")
ax[2].plot(t[zm] * 1e3, load_v[zm], color="#ff7f0e", lw=1.8, label="filtered load voltage")
ax[2].set_title("2b) Zoom (50-52 ms): PWM pulse-width variation vs. the filtered sine")
ax[2].set_ylabel("Volts"); ax[2].legend(loc="upper right", fontsize=8); ax[2].grid(alpha=0.3)

ax[3].plot(ms, load_v, color="#ff7f0e", lw=1.4,
           label=f"V(Rload)  RMS={results[s0]['rms']:.0f} V  f={results[s0]['freq']:.0f} Hz")
ax[3].set_title("3) Clean V2L output across Rload — grid-quality ~230 V AC sine")
ax[3].set_xlabel("time (ms)"); ax[3].set_ylabel("Volts")
ax[3].legend(loc="upper right", fontsize=8); ax[3].grid(alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig("v2l_results.png", dpi=120)
print("Saved figure -> v2l_results.png")

# ===========================================================================
# FIGURE 2 : dual-voltage output comparison
# ===========================================================================
if len(steps) >= 2:
    fig2, bx = plt.subplots(3, 1, figsize=(11, 9))
    fig2.suptitle("V2L Dual-Voltage Output — selectable mains standard",
                  fontsize=14, weight="bold")

    for i, s in enumerate(steps[:2]):
        r = results[s]
        col = MODE_INFO.get(s, ("", 0, 0, "#333"))[3]
        bx[i].plot(r["t"] * 1e3, r["load_v"], color=col, lw=1.4,
                   label=f"{r['label']}   RMS={r['rms']:.0f} V   f={r['freq']:.0f} Hz   P={r['power']:.0f} W")
        bx[i].axhline(r["rms"] * np.sqrt(2), color="grey", ls="--", lw=0.7)
        bx[i].axhline(-r["rms"] * np.sqrt(2), color="grey", ls="--", lw=0.7)
        bx[i].set_title(f"Output across Rload — {r['label']}")
        bx[i].set_ylabel("Volts"); bx[i].set_ylim(-360, 360)
        bx[i].legend(loc="upper right", fontsize=8); bx[i].grid(alpha=0.3)

    # overlay
    for s in steps[:2]:
        r = results[s]
        col = MODE_INFO.get(s, ("", 0, 0, "#333"))[3]
        bx[2].plot(r["t"] * 1e3, r["load_v"], color=col, lw=1.2, label=r["label"])
    bx[2].set_title("Overlay — same inverter, modulation index sets the voltage/frequency")
    bx[2].set_xlabel("time (ms)"); bx[2].set_ylabel("Volts")
    bx[2].set_xlim(0, 100); bx[2].legend(loc="upper right", fontsize=8); bx[2].grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig("v2l_dual_voltage.png", dpi=120)
    print("Saved figure -> v2l_dual_voltage.png")
