"""
PROJECT 1: Control Chart and Capability Study
Story: A factory makes metal shafts. The customer wants diameter between 9.5 mm and 10.5 mm.
We (1) check if the process is STABLE (control chart) and (2) check if it is CAPABLE (Cp, Cpk).

Install needed libraries once:  pip install numpy pandas matplotlib scipy
"""

# ---------------------------------------------------------------
# STEP 0: IMPORT THE TOOLS WE NEED
# ---------------------------------------------------------------
import numpy as np                    # numpy = math with lists of numbers (averages, random numbers)
import pandas as pd                   # pandas = tables (like Excel inside Python)
import matplotlib.pyplot as plt       # matplotlib = drawing charts
from scipy import stats               # scipy.stats = statistics tools (normality test, bell curve math)
from scipy.stats import norm          # norm = the bell curve (normal distribution) functions

# ---------------------------------------------------------------
# STEP 1: SETTINGS (the "rules of the game")
# ---------------------------------------------------------------
LSL = 9.5        # Lower Specification Limit: customer says "nothing smaller than 9.5 mm"
USL = 10.5       # Upper Specification Limit: customer says "nothing bigger than 10.5 mm"
N = 5            # Subgroup size: we measure 5 shafts each time
K = 25           # Number of subgroups: we do 25 rounds of measuring

# Constants from the standard SPC table, valid ONLY for subgroup size n = 5.
# They are "magic multipliers" that turn the average range into 3-sigma limits.
A2 = 0.577       # used for X-bar chart limits
D3 = 0           # used for R chart lower limit (0 for n=5)
D4 = 2.114       # used for R chart upper limit
d2 = 2.326       # used to turn the average range into an estimate of standard deviation

# ---------------------------------------------------------------
# STEP 2: CREATE PRETEND FACTORY DATA (simulation)
# ---------------------------------------------------------------
rng = np.random.default_rng(42)   # random number generator; seed 42 means same numbers every run

rows = []                         # empty list; each item will be one subgroup (5 measurements)
for g in range(1, K + 1):         # loop g = 1, 2, 3, ... 25 (one loop per measuring round)
    # Before round 18 the machine is healthy (average 10.0).
    # From round 18 on, something went wrong (average jumps to 10.25). This is our planted "problem".
    true_mean = 10.0 if g < 18 else 10.25
    # Draw 5 random shaft diameters around true_mean; 0.12 is the natural wobble (std deviation)
    rows.append(rng.normal(true_mean, 0.12, size=N))

# Put the data in a table: row = subgroup number, columns = shaft 1..5
df = pd.DataFrame(rows, index=range(1, K + 1), columns=[f"shaft{i}" for i in range(1, N + 1)])
print("First 5 subgroups of data:")
print(df.head().round(3))        # show the first 5 rows, rounded to 3 decimals

# ---------------------------------------------------------------
# STEP 3: LOOK AT THE DATA FIRST (histogram + normality check)
# ---------------------------------------------------------------
all_values = df.values.flatten()  # turn the 25x5 table into one long list of 125 numbers

fig, axes = plt.subplots(1, 2, figsize=(11, 4))          # make a figure with 2 side-by-side plots

axes[0].hist(all_values, bins=15, edgecolor="black")     # histogram: bar chart of "how many shafts at each size"
axes[0].axvline(LSL, color="red", linestyle="--", label="LSL")   # red dashed line at lower spec limit
axes[0].axvline(USL, color="red", linestyle="--", label="USL")   # red dashed line at upper spec limit
axes[0].set_title("Histogram of all shaft diameters")    # title of left plot
axes[0].set_xlabel("Diameter (mm)")                      # label under the x axis
axes[0].legend()                                         # show the legend (LSL/USL names)

stats.probplot(all_values, dist="norm", plot=axes[1])    # Q-Q plot: dots on a straight line = bell-shaped data
axes[1].set_title("Q-Q plot (straight line = normal)")   # title of right plot

plt.tight_layout()                                       # stop plots from overlapping
plt.savefig("1_histogram_normality.png", dpi=150)        # save picture to a file
plt.show()                                               # display the picture

w_stat, p_value = stats.shapiro(all_values)              # Shapiro-Wilk test: is the data bell-shaped?
print(f"\nShapiro-Wilk normality test p-value = {p_value:.3f}")
print("p > 0.05 -> looks normal (OK)" if p_value > 0.05 else "p <= 0.05 -> NOT normal (be careful)")
# NOTE: our data has a planted shift, so it may look a bit less normal. That's expected here.

# ---------------------------------------------------------------
# STEP 4: A FUNCTION THAT BUILDS X-BAR AND R CHART NUMBERS
# (we make it a function so we can reuse it after cleaning the data)
# ---------------------------------------------------------------
def control_limits(data):
    """Takes a table of subgroups and returns all numbers needed for the charts."""
    xbar = data.mean(axis=1)                         # average of each subgroup (row)
    R = data.max(axis=1) - data.min(axis=1)          # range of each subgroup = biggest - smallest
    xbarbar = xbar.mean()                            # grand average = average of all subgroup averages
    Rbar = R.mean()                                  # average range
    return {
        "xbar": xbar, "R": R,                        # the points we will plot
        "xbarbar": xbarbar, "Rbar": Rbar,            # the center lines
        "ucl_x": xbarbar + A2 * Rbar,                # X-bar upper control limit  (center + 3 sigma)
        "lcl_x": xbarbar - A2 * Rbar,                # X-bar lower control limit  (center - 3 sigma)
        "ucl_r": D4 * Rbar,                          # R chart upper control limit
        "lcl_r": D3 * Rbar,                          # R chart lower control limit
    }

# ---------------------------------------------------------------
# STEP 5: A FUNCTION THAT FINDS "SIGNALS" (something changed!)
# ---------------------------------------------------------------
def find_signals(xbar, center, ucl, lcl):
    """Returns the subgroup numbers where the chart says 'something is wrong'."""
    flagged = set()                                  # a set = a list with no duplicates

    # RULE 1: any point outside the control limits
    for idx, val in xbar.items():                    # go through each subgroup average
        if val > ucl or val < lcl:                   # is it above UCL or below LCL?
            flagged.add(idx)                         # if yes, mark that subgroup

    # RULE 2: 8 points in a row on the same side of the center line (a "shift")
    side = np.sign(xbar.values - center)             # +1 if above center, -1 if below
    idxs = list(xbar.index)                          # list of subgroup numbers
    for i in range(len(side) - 7):                   # slide a window of 8 points along the chart
        window = side[i:i + 8]                       # take 8 points
        if abs(window.sum()) == 8:                   # all +1 (sum 8) or all -1 (sum -8)
            flagged.update(idxs[i:i + 8])            # mark all 8 points

    return sorted(flagged)                           # return flagged subgroups in order

# ---------------------------------------------------------------
# STEP 6: A FUNCTION THAT DRAWS THE TWO CONTROL CHARTS
# ---------------------------------------------------------------
def plot_charts(c, flagged, title, filename):
    fig, ax = plt.subplots(2, 1, figsize=(11, 8), sharex=True)   # two charts stacked vertically

    # ----- X-bar chart (watches the CENTER of the process) -----
    ax[0].plot(c["xbar"].index, c["xbar"].values, marker="o")    # blue line with dots
    ax[0].axhline(c["xbarbar"], color="green")                   # green center line
    ax[0].axhline(c["ucl_x"], color="red", linestyle="--")       # red upper control limit
    ax[0].axhline(c["lcl_x"], color="red", linestyle="--")       # red lower control limit
    bad = c["xbar"].loc[[i for i in flagged if i in c["xbar"].index]]  # the flagged points
    ax[0].scatter(bad.index, bad.values, color="red", s=90, zorder=5)  # paint flagged points red
    ax[0].set_title(f"X-bar chart: {title}")
    ax[0].set_ylabel("Subgroup average (mm)")

    # ----- R chart (watches the SPREAD of the process) -----
    ax[1].plot(c["R"].index, c["R"].values, marker="o", color="purple")
    ax[1].axhline(c["Rbar"], color="green")
    ax[1].axhline(c["ucl_r"], color="red", linestyle="--")
    ax[1].axhline(c["lcl_r"], color="red", linestyle="--")
    ax[1].set_title(f"R chart: {title}")
    ax[1].set_ylabel("Subgroup range (mm)")
    ax[1].set_xlabel("Subgroup number (time)")

    plt.tight_layout()
    plt.savefig(filename, dpi=150)                               # save the picture
    plt.show()                                                   # show the picture

# ---------------------------------------------------------------
# STEP 7: PHASE I - learn what "NORMAL" looks like
# We take the first 15 subgroups as our baseline (a period we believe the machine was healthy)
# and calculate the control limits from ONLY those. If we used all 25, the bad data would
# contaminate the limits and hide the problem.
# ---------------------------------------------------------------
BASELINE = 15                                                    # number of early subgroups treated as "healthy"
c_base = control_limits(df.iloc[:BASELINE])                      # limits calculated from baseline only
flag_base = find_signals(c_base["xbar"], c_base["xbarbar"], c_base["ucl_x"], c_base["lcl_x"])
print(f"\nPhase I: signals inside the baseline period: {flag_base}  (empty = baseline is stable, good)")
plot_charts(c_base, flag_base, "PHASE I (baseline, subgroups 1-15)", "2_control_chart_phase1.png")

# ---------------------------------------------------------------
# STEP 8: PHASE II - watch ALL the data using the baseline limits
# Now we keep the baseline limits FIXED and plot all 25 subgroups against them.
# If the machine changed, points will cross the limits or form long runs on one side.
# ---------------------------------------------------------------
c_all = dict(c_base)                                             # copy the baseline numbers (limits stay the same)
c_all["xbar"] = df.mean(axis=1)                                  # but plot the average of ALL 25 subgroups
c_all["R"] = df.max(axis=1) - df.min(axis=1)                     # and the range of ALL 25 subgroups
flagged = find_signals(c_all["xbar"], c_base["xbarbar"], c_base["ucl_x"], c_base["lcl_x"])
print(f"Phase II: subgroups flagged as out of control: {flagged}")
plot_charts(c_all, flagged, "PHASE II (all data vs baseline limits)", "3_control_chart_phase2.png")

# In a real factory you would now walk to the machine and ask "what happened at the first flagged
# subgroup?" (new material batch? tool wear?). We pretend we found and fixed it, so we keep only
# the stable subgroups for the capability study.
df_clean = df.drop(index=flagged)                                # remove flagged subgroups
c2 = control_limits(df_clean)                                    # numbers for the stable data (we need Rbar)

# ---------------------------------------------------------------
# STEP 9: CAPABILITY STUDY (only valid because the process is now stable)
# ---------------------------------------------------------------
clean_values = df_clean.values.flatten()                         # all measurements from stable subgroups
mean = clean_values.mean()                                       # the process average
sigma_within = c2["Rbar"] / d2                                   # short-term wobble, estimated from ranges
sigma_overall = clean_values.std(ddof=1)                         # long-term wobble, from ALL numbers together

Cp = (USL - LSL) / (6 * sigma_within)                            # potential: spec width / process width (ignores centering)
Cpk = min(USL - mean, mean - LSL) / (3 * sigma_within)           # actual: distance to the NEAREST spec limit
Pp = (USL - LSL) / (6 * sigma_overall)                           # like Cp but with long-term wobble
Ppk = min(USL - mean, mean - LSL) / (3 * sigma_overall)          # like Cpk but with long-term wobble

# PPM = parts per million defective. norm.cdf(LSL) = fraction below LSL; norm.sf(USL) = fraction above USL.
ppm = (norm.cdf(LSL, mean, sigma_within) + norm.sf(USL, mean, sigma_within)) * 1_000_000

# Print a neat summary table
summary = pd.DataFrame({
    "Metric": ["Mean", "Sigma (within)", "Sigma (overall)", "Cp", "Cpk", "Pp", "Ppk", "Estimated PPM"],
    "Value": [mean, sigma_within, sigma_overall, Cp, Cpk, Pp, Ppk, ppm],
}).round(3)
print("\n=== CAPABILITY SUMMARY ===")
print(summary.to_string(index=False))

# Capability picture: bell curve over the spec limits
x = np.linspace(LSL - 0.3, USL + 0.3, 400)                       # 400 x-values for drawing the curve
plt.figure(figsize=(9, 4))
plt.plot(x, norm.pdf(x, mean, sigma_within))                     # the process bell curve
plt.axvline(LSL, color="red", linestyle="--", label="LSL")       # lower spec limit
plt.axvline(USL, color="red", linestyle="--", label="USL")       # upper spec limit
plt.axvline(mean, color="green", label="Process mean")           # where the process is centered
plt.title(f"Process vs. spec limits (Cpk = {Cpk:.2f})")
plt.xlabel("Diameter (mm)")
plt.legend()
plt.tight_layout()
plt.savefig("4_capability.png", dpi=150)
plt.show()

# ---------------------------------------------------------------
# STEP 10: PLAIN-ENGLISH CONCLUSION
# ---------------------------------------------------------------
if Cpk >= 1.33:
    verdict = "CAPABLE (Cpk >= 1.33, the usual industry target)"
elif Cpk >= 1.0:
    verdict = "MARGINAL (Cpk between 1.0 and 1.33)"
else:
    verdict = "NOT CAPABLE (Cpk < 1.0)"

print("\n=== CONCLUSION ===")
print(f"Phase II charts flagged a shift at subgroups {flagged}.")
print(f"After removing the special cause, the process is stable and {verdict}.")
print(f"Cpk = {Cpk:.2f}, about {ppm:.0f} defective parts per million.")
print(f"Cp = {Cp:.2f} vs Cpk = {Cpk:.2f}: ", end="")
print("the process is well centered." if Cp - Cpk < 0.1 else "re-centering the process would improve capability.")
