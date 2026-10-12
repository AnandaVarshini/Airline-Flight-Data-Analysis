"""
Airline Flight Data Analysis - reusable analysis code
=====================================================

This module holds every step of the project as small, well-named functions:

    load_data  ->  clean_data  ->  add_features  ->  analysis functions
                                                 ->  plot functions
                                                 ->  generate_findings

The Jupyter notebook (notebooks/airline_flight_analysis.ipynb) calls these
functions one step at a time and explains each step. You can also run the
whole pipeline from the command line:

    python src/data_analysis.py

DATA: U.S. Bureau of Transportation Statistics (BTS) "Reporting Carrier
On-Time Performance" CSV files placed in the data/ folder (see data/README.md).

IMPORTANT: no result numbers are hardcoded anywhere in this project. Every
result and every finding is computed from the CSV files you download.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# --------------------------------------------------------------------------
# 1. Settings (change these in one place)
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CHART_DIR = PROJECT_ROOT / "outputs" / "charts"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"

# A flight is "delayed" if it left 15 or more minutes after its scheduled time.
# This is the same rule BTS uses for its DepDel15 column.
DELAY_THRESHOLD_MIN = 15

# Ignore tiny groups when ranking (a tiny airline with 20 flights is not reliable).
MIN_FLIGHTS_AIRLINE = 500
MIN_FLIGHTS_AIRPORT = 1000
MIN_FLIGHTS_HOUR = 200

# Columns we need. Anything else in the CSV is ignored to save memory.
REQUIRED_COLS = ["FlightDate", "Reporting_Airline", "Origin", "CRSDepTime", "DepDelay", "Cancelled"]
OPTIONAL_COLS = [
    "Dest", "DepTime", "DepDelayMinutes", "DepDel15", "CancellationCode", "Diverted",
    "Distance", "Flight_Number_Reporting_Airline", "Tail_Number",
]
ALL_COLS = REQUIRED_COLS + OPTIONAL_COLS

# Convenience labels for airline codes. Unknown codes simply show the code itself.
AIRLINE_NAMES = {
    "9E": "Endeavor Air", "AA": "American", "AS": "Alaska", "B6": "JetBlue",
    "C5": "CommutAir", "CP": "Compass", "DL": "Delta", "EV": "ExpressJet",
    "F9": "Frontier", "G4": "Allegiant", "G7": "GoJet", "HA": "Hawaiian",
    "MQ": "Envoy Air", "NK": "Spirit", "OH": "PSA Airlines", "OO": "SkyWest",
    "QX": "Horizon Air", "UA": "United", "WN": "Southwest", "YV": "Mesa",
    "YX": "Republic", "ZW": "Air Wisconsin",
}
CANCELLATION_REASONS = {"A": "Airline / carrier", "B": "Weather", "C": "National Air System", "D": "Security"}

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PERIOD_LABELS = ["Night (00-05)", "Morning (06-11)", "Afternoon (12-17)", "Evening (18-23)"]

MANUAL_DOWNLOAD_HELP = (
    "No CSV files were found in '{folder}'.\n"
    "Download BTS On-Time Performance data first - see data/README.md for the exact steps.\n"
    "Quick option:  python src/download_data.py --year 2024 --months 1 2 3"
)

C_MAIN = "#2a6f97"
C_BAD = "#c8553d"
C_GOOD = "#4f9d69"


# --------------------------------------------------------------------------
# 2. Loading
# --------------------------------------------------------------------------
def find_csv_files(data_dir: Path | str = DATA_DIR) -> list[Path]:
    """Return every .csv file below the data folder."""
    return sorted(Path(data_dir).rglob("*.csv"))


def load_data(data_dir: Path | str = DATA_DIR) -> tuple[pd.DataFrame, list[Path]]:
    """Read all CSV files in the data folder into ONE DataFrame.

    Only the columns listed in ALL_COLS are read (BTS files have ~110 columns,
    most of which we do not need). Returns (dataframe, list_of_files_used).
    """
    files = find_csv_files(data_dir)
    if not files:
        raise FileNotFoundError(MANUAL_DOWNLOAD_HELP.format(folder=data_dir))

    wanted = set(ALL_COLS)
    frames = []
    for path in files:
        part = pd.read_csv(path, usecols=lambda c: c in wanted, low_memory=False)
        missing = [c for c in REQUIRED_COLS if c not in part.columns]
        if missing:
            raise ValueError(
                f"{path.name} is missing required column(s): {missing}. "
                "Re-download the file and tick these fields (see data/README.md)."
            )
        frames.append(part)
    return pd.concat(frames, ignore_index=True), files


# --------------------------------------------------------------------------
# 3. Inspecting and cleaning
# --------------------------------------------------------------------------
def missing_value_report(df: pd.DataFrame) -> pd.DataFrame:
    """Count and percentage of missing values for each column."""
    report = pd.DataFrame({"missing": df.isna().sum(), "missing_pct": 100 * df.isna().mean()})
    return report.sort_values("missing", ascending=False).round(2)


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean the raw data and explain every change.

    Returns (clean_dataframe, cleaning_log). The log is a small table that
    says what was checked, what was found and what was done about it.

    Philosophy: we almost never delete flights. A cancelled flight has no
    delay value *by design*, and a very long delay can be a real event.
    Instead of deleting, we keep the row and use masks (see add_features).
    """
    df = df.copy()
    log: list[dict] = []

    def note(step: str, found, action: str) -> None:
        log.append({"step": step, "found": found, "action": action})

    note("Rows loaded", f"{len(df):,}", "-")

    # --- data types ---------------------------------------------------------
    df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")
    bad_dates = int(df["FlightDate"].isna().sum())
    if bad_dates:
        df = df[df["FlightDate"].notna()]
    note("Unreadable flight dates", bad_dates,
         "Removed these rows: a flight with no date cannot be placed in time." if bad_dates else "Nothing to do.")

    for col in ["CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes", "DepDel15", "Distance"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["Cancelled", "Diverted"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    note("Data types", "Dates parsed; numeric columns converted; Cancelled/Diverted -> 0/1 integers",
         "Converted.")

    # --- duplicates ---------------------------------------------------------
    n_dup = int(df.duplicated().sum())
    if n_dup:
        df = df.drop_duplicates()
    note("Exact duplicate rows", n_dup,
         "Dropped the repeated copies (identical in every loaded column, so they add no information)."
         if n_dup else "Nothing to do.")

    # --- missing / inconsistent delay values -------------------------------
    cancelled_mask = df["Cancelled"] == 1
    n_cancel = int(cancelled_mask.sum())
    note("Cancelled flights", f"{n_cancel:,}",
         "Kept. They never departed, so their DepDelay is empty by design; they are excluded from delay "
         "averages but counted in the cancellation analysis.")

    unexpected_missing = int((~cancelled_mask & df["DepDelay"].isna()).sum())
    note("Non-cancelled flights with NO departure delay value", f"{unexpected_missing:,}",
         "Kept in the table but excluded from delay statistics (we cannot guess their delay). "
         "Shown as 'Unknown' in the status chart.")

    contradictory = int((cancelled_mask & df["DepDelay"].notna()).sum())
    if contradictory:
        df.loc[df["Cancelled"] == 1, "DepDelay"] = np.nan
    note("Cancelled flights that still have a delay value", contradictory,
         "Set the delay to empty (a cancelled flight did not depart)." if contradictory else "Nothing to do.")

    # --- unusual / invalid values ------------------------------------------
    bad_time_mask = (df["CRSDepTime"] < 0) | (df["CRSDepTime"] > 2400)
    bad_time = int(bad_time_mask.sum())
    if bad_time:
        df.loc[bad_time_mask, "CRSDepTime"] = np.nan
    note("Scheduled departure time outside 0000-2400", bad_time,
         "Set to empty so it is ignored in the by-hour analysis." if bad_time else "Nothing to do.")

    extreme_late = int((df["DepDelay"] > 1440).sum())
    extreme_early = int((df["DepDelay"] < -120).sum())
    note("Extreme delays (> 24 h late, or > 2 h early)", f"{extreme_late} very late, {extreme_early} very early",
         "KEPT. Overnight delays are real events. The histogram clips the axis only for readability, "
         "and we report the median alongside the mean so extremes do not mislead.")

    if "DepDel15" in df.columns:
        known = df["DepDelay"].notna() & df["DepDel15"].notna()
        ours = (df.loc[known, "DepDelay"] >= DELAY_THRESHOLD_MIN).astype(int)
        mismatch = int((ours != df.loc[known, "DepDel15"].astype(int)).sum())
        note("Our delay rule vs BTS DepDel15 flag", f"{mismatch:,} disagreements",
             "We use our own rule (DepDelay >= 15) everywhere, which should match BTS.")

    note("Rows after cleaning", f"{len(df):,}", "-")
    return df.reset_index(drop=True), pd.DataFrame(log)


# --------------------------------------------------------------------------
# 4. Feature engineering (derived columns)
# --------------------------------------------------------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create the extra columns used by the analysis."""
    df = df.copy()

    # Does this flight have a usable departure delay?
    df["dep_delay_known"] = (df["Cancelled"] == 0) & df["DepDelay"].notna()
    df["is_delayed"] = df["DepDelay"] >= DELAY_THRESHOLD_MIN          # False if missing
    df["dep_delay_minutes"] = df["DepDelay"].clip(lower=0)            # early departures count as 0

    # One label per flight: On-time / Delayed / Cancelled / Unknown
    df["flight_status"] = np.select(
        [df["Cancelled"] == 1, ~df["dep_delay_known"], df["is_delayed"]],
        ["Cancelled", "Unknown", "Delayed"],
        default="On-time",
    )

    # Scheduled departure hour (0-23) and a broader time-of-day group.
    # We use the SCHEDULED time because it is the time a passenger books.
    df["sched_hour"] = ((df["CRSDepTime"] // 100) % 24).astype("Int64")
    df["dep_period"] = pd.cut(
        df["sched_hour"].astype("float"), bins=[-0.5, 5.5, 11.5, 17.5, 23.5], labels=PERIOD_LABELS
    )

    df["day_name"] = df["FlightDate"].dt.day_name()
    df["year_month"] = df["FlightDate"].dt.strftime("%Y-%m")
    df["airline_name"] = df["Reporting_Airline"].map(AIRLINE_NAMES).fillna(df["Reporting_Airline"])
    return df


# --------------------------------------------------------------------------
# 5. Analysis functions (each returns numbers computed from the data)
# --------------------------------------------------------------------------
def headline_metrics(df: pd.DataFrame) -> dict:
    """Overall numbers: how many flights, % delayed, average delay, etc."""
    known = df[df["dep_delay_known"]]
    n = len(known)
    if n == 0:
        raise ValueError("No flights with a recorded departure delay were found - check your CSV files.")
    delay = known["DepDelay"]
    delayed = int(known["is_delayed"].sum())
    total = len(df)
    cancelled = int(df["Cancelled"].sum())
    return {
        "first_date": df["FlightDate"].min().date(),
        "last_date": df["FlightDate"].max().date(),
        "total_flights": total,
        "cancelled": cancelled,
        "pct_cancelled": 100 * cancelled / total,
        "diverted": int(df["Diverted"].sum()),
        "flights_with_delay": n,
        "no_delay_recorded": total - cancelled - n,
        "delayed": delayed,
        "pct_delayed": 100 * delayed / n,
        "mean_delay": delay.mean(),
        "median_delay": delay.median(),
        "mean_delay_nonneg": known["dep_delay_minutes"].mean(),
        "p90_delay": delay.quantile(0.90),
        "max_delay": delay.max(),
        "pct_early": 100 * (delay < 0).mean(),
        "share_delayed_60plus": 100 * (delay >= 60).sum() / delayed if delayed else float("nan"),
    }


def status_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Number and % of flights that were On-time, Delayed, Cancelled or Unknown."""
    counts = df["flight_status"].value_counts()
    order = [s for s in ["On-time", "Delayed", "Cancelled", "Unknown"] if s in counts.index]
    out = counts.reindex(order).to_frame("flights")
    out["pct"] = 100 * out["flights"] / out["flights"].sum()
    return out


def summarize_by(df: pd.DataFrame, by: str, min_flights: int = 0) -> pd.DataFrame:
    """The workhorse: delay and cancellation statistics for each group in column `by`.

    Columns returned:
      scheduled_flights, cancelled, pct_cancelled   (all flights)
      flights_departed, avg_dep_delay, median_dep_delay, delayed, pct_delayed
      (only flights that have a recorded departure delay)

    avg_dep_delay is the mean of DepDelay in minutes. Early departures are
    negative, so they pull the average down (this is how BTS reports it).
    """
    all_stats = df.groupby(by, observed=True).agg(
        scheduled_flights=("Cancelled", "size"), cancelled=("Cancelled", "sum")
    )
    dep_stats = df[df["dep_delay_known"]].groupby(by, observed=True).agg(
        flights_departed=("DepDelay", "size"),
        avg_dep_delay=("DepDelay", "mean"),
        median_dep_delay=("DepDelay", "median"),
        delayed=("is_delayed", "sum"),
    )
    out = all_stats.join(dep_stats)
    out[["flights_departed", "delayed"]] = out[["flights_departed", "delayed"]].fillna(0)
    out["pct_delayed"] = 100 * out["delayed"] / out["flights_departed"].replace(0, np.nan)
    out["pct_cancelled"] = 100 * out["cancelled"] / out["scheduled_flights"]
    out = out[out["scheduled_flights"] >= min_flights]
    return out


def airline_summary(df: pd.DataFrame, min_flights: int = MIN_FLIGHTS_AIRLINE) -> pd.DataFrame:
    """summarize_by for airlines, sorted worst -> best, with a readable label."""
    out = summarize_by(df, "Reporting_Airline", min_flights).sort_values("avg_dep_delay", ascending=False)
    out["label"] = [f"{AIRLINE_NAMES[c]} ({c})" if c in AIRLINE_NAMES else c for c in out.index]
    return out


def daily_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Average delay for each calendar day, plus a 7-day rolling average."""
    daily = df[df["dep_delay_known"]].groupby("FlightDate").agg(
        flights=("DepDelay", "size"), avg_dep_delay=("DepDelay", "mean"), pct_delayed=("is_delayed", "mean")
    )
    daily["pct_delayed"] = daily["pct_delayed"] * 100
    daily["rolling_7d_avg"] = daily["avg_dep_delay"].rolling(7, min_periods=3).mean()
    return daily


def heatmap_table(df: pd.DataFrame) -> pd.DataFrame:
    """% of flights delayed for every (day of week, scheduled hour) pair."""
    table = df[df["dep_delay_known"]].pivot_table(
        index="day_name", columns="sched_hour", values="is_delayed", aggfunc="mean"
    ) * 100
    return table.reindex([d for d in DAY_ORDER if d in table.index])


def cancellation_reasons(df: pd.DataFrame) -> pd.DataFrame:
    """Why were flights cancelled? (BTS codes A/B/C/D). Empty if the column is absent."""
    if "CancellationCode" not in df.columns:
        return pd.DataFrame(columns=["flights", "pct"])
    codes = df.loc[df["Cancelled"] == 1, "CancellationCode"].dropna()
    if codes.empty:
        return pd.DataFrame(columns=["flights", "pct"])
    out = codes.map(CANCELLATION_REASONS).fillna("Other / unknown").value_counts().to_frame("flights")
    out["pct"] = 100 * out["flights"] / out["flights"].sum()
    return out


def compute_all(df: pd.DataFrame, min_airline: int = MIN_FLIGHTS_AIRLINE,
                min_airport: int = MIN_FLIGHTS_AIRPORT) -> dict:
    """Run every analysis once and return all the tables in a dictionary."""
    dow = summarize_by(df, "day_name").reindex(DAY_ORDER)
    return {
        "metrics": headline_metrics(df),
        "status": status_summary(df),
        "airline": airline_summary(df, min_airline),
        "hour": summarize_by(df, "sched_hour", MIN_FLIGHTS_HOUR).sort_index(),
        "period": summarize_by(df, "dep_period"),
        "dow": dow.dropna(subset=["scheduled_flights"]),
        "month": summarize_by(df, "year_month").sort_index(),
        "daily": daily_trend(df),
        "airport": summarize_by(df, "Origin", min_airport).sort_values("avg_dep_delay", ascending=False),
        "cancel_reasons": cancellation_reasons(df),
        "heatmap": heatmap_table(df),
        "min_airline": min_airline,
        "min_airport": min_airport,
    }


# --------------------------------------------------------------------------
# 6. Visualizations
# --------------------------------------------------------------------------
def _new_fig(*args, **kwargs):
    sns.set_theme(style="whitegrid")
    return plt.subplots(*args, **kwargs)


def _save(fig, name: str, save_dir):
    if save_dir is not None:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(save_dir) / f"{name}.png", dpi=150, bbox_inches="tight")
    return fig


def plot_status_share(status: pd.DataFrame, save_dir=None):
    """Chart 1: share of flights that were on-time, delayed, cancelled."""
    colors = {"On-time": C_GOOD, "Delayed": C_BAD, "Cancelled": "#6c757d", "Unknown": "#b8b8b8"}
    fig, ax = _new_fig(figsize=(8, 3.8))
    ax.barh(list(status.index), status["pct"], color=[colors[s] for s in status.index])
    ax.invert_yaxis()
    for y, (pct, n) in enumerate(zip(status["pct"], status["flights"])):
        ax.text(pct + 0.5, y, f"{pct:.1f}%  ({n:,} flights)", va="center", fontsize=9)
    ax.set_xlim(0, status["pct"].max() * 1.4)
    ax.set_xlabel("Share of all scheduled flights (%)")
    ax.set_title(f"Flight outcomes (delayed = departed {DELAY_THRESHOLD_MIN}+ min late)")
    return _save(fig, "01_flight_status_share", save_dir)


def plot_delay_histogram(df: pd.DataFrame, save_dir=None, lo: int = -30, hi: int = 180):
    """Chart 2: distribution of departure delays (axis clipped for readability)."""
    delay = df.loc[df["dep_delay_known"], "DepDelay"]
    shown = delay[(delay >= lo) & (delay <= hi)]
    outside = len(delay) - len(shown)
    fig, ax = _new_fig(figsize=(9, 4.5))
    ax.hist(shown, bins=np.arange(lo, hi + 5, 5), color=C_MAIN, edgecolor="white")
    ax.axvline(DELAY_THRESHOLD_MIN, color=C_BAD, linestyle="--", label=f"Delay threshold ({DELAY_THRESHOLD_MIN} min)")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Departure delay (minutes; negative = left early)")
    ax.set_ylabel("Number of flights")
    ax.set_title("Distribution of departure delays")
    ax.legend()
    ax.text(0.99, 0.62, f"{outside:,} flights outside\n{lo} to {hi} min not shown", transform=ax.transAxes,
            ha="right", fontsize=9, color="#555")
    return _save(fig, "02_delay_histogram", save_dir)


def plot_airline_delay(airline: pd.DataFrame, min_flights: int, save_dir=None):
    """Chart 3: average departure delay by airline."""
    data = airline.sort_values("avg_dep_delay", ascending=False)
    fig, ax = _new_fig(figsize=(9, max(4, 0.38 * len(data) + 1.5)))
    bars = ax.barh(data["label"], data["avg_dep_delay"], color=C_MAIN)
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    ax.set_xlabel("Average departure delay (minutes)")
    ax.set_title(f"Average departure delay by airline (airlines with {min_flights:,}+ flights)")
    return _save(fig, "03_airline_avg_delay", save_dir)


def plot_daily_trend(daily: pd.DataFrame, save_dir=None):
    """Chart 4: delay trend over time."""
    fig, ax = _new_fig(figsize=(10, 4.5))
    ax.plot(daily.index, daily["avg_dep_delay"], color=C_MAIN, alpha=0.45, marker="o", markersize=3,
            label="Daily average")
    ax.plot(daily.index, daily["rolling_7d_avg"], color=C_BAD, linewidth=2.2, label="7-day rolling average")
    ax.set_xlabel("Flight date")
    ax.set_ylabel("Average departure delay (minutes)")
    ax.set_title("Average departure delay over time")
    ax.legend()
    fig.autofmt_xdate()
    return _save(fig, "04_delay_trend_over_time", save_dir)


def plot_monthly(month: pd.DataFrame, save_dir=None):
    """Chart 5: delay by month (skipped, returns None, if only one month is loaded)."""
    if len(month) < 2:
        return None
    fig, axes = _new_fig(1, 2, figsize=(10, 4))
    axes[0].bar(list(month.index), month["avg_dep_delay"], color=C_MAIN)
    axes[0].set_ylabel("Average departure delay (minutes)")
    axes[0].set_title("Average delay by month")
    axes[1].bar(list(month.index), month["pct_delayed"], color=C_BAD)
    axes[1].set_ylabel("Flights delayed (%)")
    axes[1].set_title("Share of flights delayed by month")
    for ax in axes:
        ax.set_xlabel("Month")
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return _save(fig, "05_delay_by_month", save_dir)


def plot_by_hour(hour: pd.DataFrame, save_dir=None):
    """Chart 6: delays by scheduled departure hour."""
    fig, axes = _new_fig(2, 1, figsize=(10, 7), sharex=True)
    x = [int(h) for h in hour.index]
    axes[0].bar(x, hour["avg_dep_delay"], color=C_MAIN)
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_ylabel("Average delay (minutes)")
    axes[0].set_title("Departure delay by scheduled departure hour")
    axes[1].bar(x, hour["pct_delayed"], color=C_BAD)
    axes[1].set_ylabel("Flights delayed (%)")
    axes[1].set_xlabel("Scheduled departure hour (0 = midnight, 13 = 1 pm)")
    axes[1].set_xticks(range(0, 24))
    fig.tight_layout()
    return _save(fig, "06_delay_by_departure_hour", save_dir)


def plot_by_day(dow: pd.DataFrame, save_dir=None):
    """Chart 7: delays by day of the week."""
    fig, axes = _new_fig(1, 2, figsize=(11, 4.2))
    axes[0].bar(list(dow.index), dow["avg_dep_delay"], color=C_MAIN)
    axes[0].set_ylabel("Average delay (minutes)")
    axes[0].set_title("Average delay by day of week")
    axes[1].bar(list(dow.index), dow["pct_delayed"], color=C_BAD)
    axes[1].set_ylabel("Flights delayed (%)")
    axes[1].set_title("Share of flights delayed by day of week")
    for ax in axes:
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return _save(fig, "07_delay_by_day_of_week", save_dir)


def plot_airports(airport: pd.DataFrame, min_flights: int, n: int = 10, save_dir=None):
    """Chart 8: airports with the highest and lowest average departure delay."""
    worst = airport.sort_values("avg_dep_delay", ascending=False).head(n)
    best = airport.sort_values("avg_dep_delay", ascending=True).head(n)
    fig, axes = _new_fig(1, 2, figsize=(12, 5))
    for ax, data, color, title in [
        (axes[0], worst, C_BAD, f"Highest average delay (top {n})"),
        (axes[1], best, C_GOOD, f"Lowest average delay (best {n})"),
    ]:
        bars = ax.barh([str(i) for i in data.index], data["avg_dep_delay"], color=color)
        ax.invert_yaxis()
        ax.axvline(0, color="black", linewidth=0.8)
        ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
        ax.set_xlabel("Average departure delay (minutes)")
        ax.set_title(title)
    fig.suptitle(f"Origin airport performance (airports with {min_flights:,}+ scheduled flights)", y=1.02)
    fig.tight_layout()
    return _save(fig, "08_airport_performance", save_dir)


def plot_heatmap(table: pd.DataFrame, save_dir=None):
    """Chart 9: % delayed for each day-of-week x hour combination."""
    fig, ax = _new_fig(figsize=(12, 4.5))
    sns.heatmap(table, cmap="YlOrRd", ax=ax, cbar_kws={"label": "Flights delayed (%)"})
    ax.set_xlabel("Scheduled departure hour")
    ax.set_ylabel("")
    ax.set_title("When are flights most often delayed? (day of week x hour)")
    return _save(fig, "09_delay_heatmap_day_hour", save_dir)


def plot_cancellations(airline: pd.DataFrame, reasons: pd.DataFrame, save_dir=None, n: int = 10):
    """Chart 10: cancellation rate by airline and reasons for cancellation."""
    if airline["cancelled"].sum() == 0:
        return None
    has_reasons = not reasons.empty
    fig, axes = _new_fig(1, 2 if has_reasons else 1, figsize=(12 if has_reasons else 7, 4.5), squeeze=False)
    top = airline.sort_values("pct_cancelled", ascending=False).head(n)
    bars = axes[0, 0].barh(top["label"], top["pct_cancelled"], color="#6c757d")
    axes[0, 0].invert_yaxis()
    axes[0, 0].bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    axes[0, 0].set_xlabel("Flights cancelled (%)")
    axes[0, 0].set_title(f"Cancellation rate by airline (highest {n})")
    if has_reasons:
        bars = axes[0, 1].barh(list(reasons.index), reasons["pct"], color="#6c757d")
        axes[0, 1].invert_yaxis()
        axes[0, 1].bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
        axes[0, 1].set_xlabel("Share of cancelled flights (%)")
        axes[0, 1].set_title("Reported reason for cancellation")
    fig.tight_layout()
    return _save(fig, "10_cancellations", save_dir)


def make_all_charts(df: pd.DataFrame, results: dict, save_dir=CHART_DIR) -> list[Path]:
    """Create and save every chart. Returns the list of saved file paths."""
    figs = [
        plot_status_share(results["status"], save_dir),
        plot_delay_histogram(df, save_dir),
        plot_airline_delay(results["airline"], results["min_airline"], save_dir),
        plot_daily_trend(results["daily"], save_dir),
        plot_monthly(results["month"], save_dir),
        plot_by_hour(results["hour"], save_dir),
        plot_by_day(results["dow"], save_dir),
        plot_airports(results["airport"], results["min_airport"], save_dir=save_dir),
        plot_heatmap(results["heatmap"], save_dir),
        plot_cancellations(results["airline"], results["cancel_reasons"], save_dir),
    ]
    for fig in figs:
        if fig is not None:
            plt.close(fig)
    return sorted(Path(save_dir).glob("*.png"))


# --------------------------------------------------------------------------
# 7. Findings and recommendations (text is built FROM the computed results)
# --------------------------------------------------------------------------
def _hr(h) -> str:
    return f"{int(h):02d}:00"


def _gap_note(gap_minutes: float) -> str:
    """Warn the reader when the best-vs-worst gap is small."""
    return "The gap is small, so these groups look similar on this measure. " if gap_minutes < 2 else ""


def generate_findings(df: pd.DataFrame, results: dict | None = None) -> list[dict]:
    """Turn the computed tables into plain-English findings.

    Each finding is a dict with a title, the evidence (numbers) and what it
    means. Nothing is typed in advance - if you change the data, the findings
    change too.
    """
    r = results or compute_all(df)
    m = r["metrics"]
    out: list[dict] = []

    # 1. Overall delay level
    if m["mean_delay"] > m["median_delay"]:
        skew = ("The mean is higher than the median, so a minority of very long delays pulls the average up; "
                "a typical flight leaves closer to the median.")
    else:
        skew = "The mean is not above the median, so very long delays are not distorting the average much."
    out.append({
        "title": "Overall delay level",
        "evidence": (f"{m['pct_delayed']:.1f}% of the {m['flights_with_delay']:,} flights that operated "
                     f"departed {DELAY_THRESHOLD_MIN}+ minutes late. Mean departure delay was {m['mean_delay']:.1f} min "
                     f"(median {m['median_delay']:.1f} min, 90th percentile {m['p90_delay']:.0f} min). "
                     f"{m['pct_early']:.1f}% of flights left before the scheduled time."),
        "meaning": skew,
    })

    # 2. Severity
    out.append({
        "title": "Severity of delays",
        "evidence": (f"{m['share_delayed_60plus']:.1f}% of delayed flights were delayed 60+ minutes. "
                     f"The longest recorded departure delay was {m['max_delay']:.0f} minutes."),
        "meaning": (("Most delayed flights were delayed by less than an hour. "
                     if m["share_delayed_60plus"] < 50 else "More than half of delayed flights were delayed an hour or more. ")
                    + "Long delays matter most for missed connections and crew schedules."),
    })

    # 3. Airlines
    air = r["airline"]
    if len(air) >= 2:
        w, b = air.iloc[0], air.iloc[-1]
        out.append({
            "title": "Airline punctuality differs",
            "evidence": (f"Among {len(air)} airlines with {r['min_airline']:,}+ flights, {w['label']} had the highest "
                         f"average delay ({w['avg_dep_delay']:.1f} min, {w['pct_delayed']:.1f}% delayed) and "
                         f"{b['label']} the lowest ({b['avg_dep_delay']:.1f} min, {b['pct_delayed']:.1f}% delayed) "
                         f"- a gap of {w['avg_dep_delay'] - b['avg_dep_delay']:.1f} minutes."),
            "meaning": (_gap_note(w['avg_dep_delay'] - b['avg_dep_delay'])
                        + "These averages are NOT adjusted for route networks, hub airports, aircraft type or season, "
                        "so they describe what happened, not which airline is 'better managed'."),
        })

    # 4. Time of day
    hr = r["hour"].dropna(subset=["avg_dep_delay"])
    if len(hr) >= 2:
        lo, hi = hr["avg_dep_delay"].idxmin(), hr["avg_dep_delay"].idxmax()
        per = r["period"].dropna(subset=["avg_dep_delay"])
        per_txt = ""
        if len(per) >= 2:
            per_txt = (f" By time of day, {per['avg_dep_delay'].idxmax()} flights averaged "
                       f"{per['avg_dep_delay'].max():.1f} min vs {per['avg_dep_delay'].min():.1f} min for "
                       f"{per['avg_dep_delay'].idxmin()} flights.")
        out.append({
            "title": "Delays differ by scheduled departure time",
            "evidence": (f"Average delay was lowest for flights scheduled at {_hr(lo)} ({hr.loc[lo, 'avg_dep_delay']:.1f} min, "
                         f"{hr.loc[lo, 'pct_delayed']:.1f}% delayed) and highest at {_hr(hi)} "
                         f"({hr.loc[hi, 'avg_dep_delay']:.1f} min, {hr.loc[hi, 'pct_delayed']:.1f}% delayed).{per_txt}"),
            "meaning": ("This is an association. One common explanation is that delays build up during the day as "
                        "aircraft arrive late for their next flight, but this project does not test that."),
        })

    # 5. Day of week
    dow = r["dow"].dropna(subset=["avg_dep_delay"])
    if len(dow) >= 2:
        dmax, dmin = dow["avg_dep_delay"].idxmax(), dow["avg_dep_delay"].idxmin()
        out.append({
            "title": "Day-of-week pattern",
            "evidence": (f"{dmax} had the highest average delay ({dow.loc[dmax, 'avg_dep_delay']:.1f} min, "
                         f"{dow.loc[dmax, 'pct_delayed']:.1f}% delayed); {dmin} had the lowest "
                         f"({dow.loc[dmin, 'avg_dep_delay']:.1f} min, {dow.loc[dmin, 'pct_delayed']:.1f}% delayed)."),
            "meaning": ("With only a few months of data each weekday has just a handful of dates, so one stormy day "
                        "can shift a weekday average. Use more months before drawing firm conclusions."),
        })

    # 6. Time trend
    month, daily = r["month"], r["daily"]
    if len(month) >= 2:
        mw, mb = month["avg_dep_delay"].idxmax(), month["avg_dep_delay"].idxmin()
        out.append({
            "title": "Delays vary by month",
            "evidence": (f"{mw} had the highest average delay ({month.loc[mw, 'avg_dep_delay']:.1f} min, "
                         f"{month.loc[mw, 'pct_delayed']:.1f}% delayed) and {mb} the lowest "
                         f"({month.loc[mb, 'avg_dep_delay']:.1f} min, {month.loc[mb, 'pct_delayed']:.1f}% delayed)."),
            "meaning": ("Month-to-month differences may reflect seasonal weather and travel demand, but a few months "
                        "cannot separate season from one-off events."),
        })
    else:
        dw, db = daily["avg_dep_delay"].idxmax(), daily["avg_dep_delay"].idxmin()
        out.append({
            "title": "Day-to-day variation",
            "evidence": (f"The worst single day was {dw.date()} ({daily.loc[dw, 'avg_dep_delay']:.1f} min average delay) "
                         f"and the best was {db.date()} ({daily.loc[db, 'avg_dep_delay']:.1f} min)."),
            "meaning": "Individual days can differ a lot, which suggests event-driven disruption (e.g. weather) matters.",
        })

    # 7. Airports
    ap = r["airport"]
    if len(ap) >= 2:
        w, b = ap.iloc[0], ap.iloc[-1]
        out.append({
            "title": "Airport performance differs",
            "evidence": (f"Among {len(ap)} origin airports with {r['min_airport']:,}+ flights, {ap.index[0]} had the highest "
                         f"average delay ({w['avg_dep_delay']:.1f} min, {w['pct_delayed']:.1f}% delayed) and {ap.index[-1]} "
                         f"the lowest ({b['avg_dep_delay']:.1f} min, {b['pct_delayed']:.1f}% delayed)."),
            "meaning": (_gap_note(w['avg_dep_delay'] - b['avg_dep_delay'])
                        + "Airport averages mix many airlines and routes, so a difference is not necessarily caused "
                        "by the airport itself."),
        })

    # 8. Cancellations
    if m["cancelled"] > 0:
        reasons = r["cancel_reasons"]
        reason_txt = (f" The most common recorded reason was '{reasons.index[0]}' ({reasons['pct'].iloc[0]:.1f}% of cancellations)."
                      if not reasons.empty else "")
        ca = r["airline"].sort_values("pct_cancelled", ascending=False)
        ca_txt = (f" {ca.iloc[0]['label']} had the highest airline cancellation rate ({ca.iloc[0]['pct_cancelled']:.1f}%)."
                  if len(ca) else "")
        out.append({
            "title": "Cancellations",
            "evidence": f"{m['cancelled']:,} flights ({m['pct_cancelled']:.2f}%) were cancelled.{reason_txt}{ca_txt}",
            "meaning": ("Cancelled flights are excluded from the delay averages above, so this is a separate view of "
                        "reliability. Compare the cancelled share with the delayed share to judge which matters more."),
        })
    return out


def generate_recommendations(df: pd.DataFrame, results: dict | None = None) -> list[str]:
    """Practical suggestions that point back to the computed evidence."""
    r = results or compute_all(df)
    recs: list[str] = []
    hr = r["hour"].dropna(subset=["avg_dep_delay"])
    if len(hr) >= 2:
        lo, hi = hr["avg_dep_delay"].idxmin(), hr["avg_dep_delay"].idxmax()
        recs.append(f"**Travellers / planners:** where there is a choice, prefer flights scheduled near {_hr(lo)} "
                    f"(average delay {hr.loc[lo, 'avg_dep_delay']:.1f} min) over those near {_hr(hi)} "
                    f"({hr.loc[hi, 'avg_dep_delay']:.1f} min), and consider longer connection buffers around the high-delay hour.")
    air, ap = r["airline"], r["airport"]
    if len(air) >= 2 and len(ap) >= 2:
        recs.append(f"**Operations analysts:** investigate {air.iloc[0]['label']} (airline) and {ap.index[0]} (airport) first, since they "
                    "had the highest average delays in this sample. Use the BTS delay-cause columns (carrier, weather, "
                    "air-traffic system, late-arriving aircraft) to see what drives them.")
    dow = r["dow"].dropna(subset=["avg_dep_delay"])
    if len(dow) >= 2:
        recs.append(f"**Scheduling:** consider extra buffer (staff, spare aircraft, ground handling) on "
                    f"{dow['avg_dep_delay'].idxmax()}s, which had the highest average delay here.")
    if r["metrics"]["cancelled"] > 0 and not r["cancel_reasons"].empty:
        recs.append(f"**Disruption planning:** '{r['cancel_reasons'].index[0]}' was the most common cancellation reason; "
                    "contingency plans should be built around it.")
    recs.append("**Next analysis steps:** add more months (ideally a full year) to separate seasonality from one-off events, "
                "compare delays by route and distance, and use the delay-cause columns for a root-cause breakdown.")
    recs.append("**Caution:** these results describe patterns in the downloaded months only. Correlation is not causation, "
                "and the data does not prove why any pattern occurs.")
    return recs


def render_findings_markdown(findings: list[dict], recs: list[str]) -> str:
    """Format findings and recommendations as Markdown text."""
    lines = ["## Key findings (computed from the dataset)", ""]
    for i, f in enumerate(findings, 1):
        lines += [f"**{i}. {f['title']}.** {f['evidence']}", f"   *What it means:* {f['meaning']}", ""]
    lines += ["## Recommendations", ""]
    lines += [f"{i}. {rec}" for i, rec in enumerate(recs, 1)]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 8. Saving a text report
# --------------------------------------------------------------------------
def _table_block(title: str, table: pd.DataFrame, cols: list[str] | None = None, rows: int | None = None) -> str:
    t = table[cols] if cols else table
    t = t.head(rows) if rows else t
    return f"### {title}\n\n```\n{t.round(2).to_string()}\n```\n"


def write_report(path: Path, files: list[Path], cleaning_log: pd.DataFrame, results: dict,
                 findings: list[dict], recs: list[str]) -> Path:
    """Write outputs/reports/analysis_report.md (everything in one readable file)."""
    m = results["metrics"]
    cols = ["scheduled_flights", "flights_departed", "avg_dep_delay", "median_dep_delay", "pct_delayed", "pct_cancelled"]
    parts = [
        "# Airline Flight Data Analysis - Auto-generated Report\n",
        "Generated by `src/data_analysis.py`. Every number below was computed from the downloaded data.\n",
        "## Dataset\n",
        f"- Source files: {', '.join(f.name for f in files)}",
        "- Source: U.S. Bureau of Transportation Statistics, Reporting Carrier On-Time Performance",
        f"- Period covered: {m['first_date']} to {m['last_date']}",
        f"- Scheduled flights: {m['total_flights']:,} (cancelled: {m['cancelled']:,}; diverted: {m['diverted']:,}; "
        f"no delay recorded: {m['no_delay_recorded']:,})",
        f"- Delayed flight = departed {DELAY_THRESHOLD_MIN}+ minutes after the scheduled time. "
        "Cancelled flights and flights with no recorded delay are excluded from delay percentages and averages.\n",
        "## Data cleaning log\n",
        "```\n" + cleaning_log.to_string(index=False) + "\n```\n",
        render_findings_markdown(findings, recs) + "\n",
        "## Supporting tables\n",
        _table_block("Flight status", results["status"]),
        _table_block("Airlines (worst to best)", results["airline"], ["label"] + cols),
        _table_block("Scheduled departure hour", results["hour"], cols),
        _table_block("Day of week", results["dow"], cols),
        _table_block("Month", results["month"], cols),
        _table_block("Airports - 15 highest average delay", results["airport"], cols, rows=15),
    ]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def save_tables(results: dict, report_dir: Path = REPORT_DIR) -> None:
    """Save the main summary tables as CSV files (handy for Excel / Power BI)."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    for name in ["airline", "hour", "dow", "month", "airport", "daily", "status", "cancel_reasons"]:
        results[name].round(3).to_csv(report_dir / f"table_{name}.csv")


# --------------------------------------------------------------------------
# 9. Run everything from the command line
# --------------------------------------------------------------------------
def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run the full airline delay analysis.")
    parser.add_argument("--data-dir", default=str(DATA_DIR), help="Folder containing the BTS CSV file(s).")
    args = parser.parse_args(argv)

    import matplotlib
    matplotlib.use("Agg")  # draw charts to files, no window needed

    print("1/6 Loading data ...")
    raw, files = load_data(args.data_dir)
    print(f"    {len(raw):,} rows from {len(files)} file(s)")
    print("2/6 Cleaning ...")
    df, log = clean_data(raw)
    print("3/6 Creating derived columns ...")
    df = add_features(df)
    print("4/6 Analysing ...")
    results = compute_all(df)
    print("5/6 Saving charts ...")
    charts = make_all_charts(df, results)
    print(f"    {len(charts)} charts saved to {CHART_DIR}")
    print("6/6 Writing report ...")
    findings = generate_findings(df, results)
    recs = generate_recommendations(df, results)
    save_tables(results)
    report = write_report(REPORT_DIR / "analysis_report.md", files, log, results, findings, recs)
    print(f"Done. Report: {report}")


if __name__ == "__main__":
    main()
