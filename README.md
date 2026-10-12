# Airline Flight Data Analysis Using Python

An exploratory data analysis (EDA) of real U.S. airline on-time performance data: how often flights are delayed, which airlines and airports are most punctual, when delays happen, and what patterns appear in cancellations.

Built as a beginner-friendly portfolio project (Python, Pandas, NumPy, Matplotlib, Seaborn, Jupyter) for a Data Analyst Intern application.

> **No results are hardcoded.** The repository ships *code and documentation*. All numbers, charts and findings are computed from the public BTS data you download, so they are real and reproducible. After you run the project, the results appear in `outputs/`.

## 1. Objective

Use EDA to answer seven questions about flight performance:

1. What percentage of flights were delayed?
2. What was the average departure delay?
3. Which airlines had the highest and lowest average delays?
4. Which departure hours or days had more delays?
5. How did delays vary by month?
6. Which airports experienced higher average delays?
7. What patterns can be observed in cancellations?

## 2. Dataset

- **Source:** U.S. Department of Transportation, Bureau of Transportation Statistics (BTS) - *Reporting Carrier On-Time Performance*: https://www.transtats.bts.gov/ONTIME/
- **Size used:** a sample of about 3 months (roughly 1.5-2 million flights), not the whole archive.
- **License / usage:** public U.S. government data; confirm current terms on the BTS site and cite BTS (details in [`data/README.md`](data/README.md)).
- **Not included in the repo** (too large). Download steps and the column dictionary are in [`data/README.md`](data/README.md).

**Delay definition:** a flight is *delayed* if it departed **15+ minutes** after its scheduled time (same as the BTS `DepDel15` flag). Cancelled flights have no delay value and are analysed separately, never counted as "on time" or averaged in.

## 3. Quick start

```bash
# 1. get the code
git clone <your-repo-url>
cd airline-flight-data-analysis

# 2. create an environment and install packages
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. get the data (automatic; if it fails use the manual steps in data/README.md)
python src/download_data.py --year 2024 --months 1 2 3

# 4a. run everything from the command line ...
python src/data_analysis.py

# 4b. ... or explore step by step in the notebook
jupyter notebook notebooks/airline_flight_analysis.ipynb
```

Outputs: `outputs/charts/*.png` (10 charts), `outputs/reports/analysis_report.md` (findings, cleaning log, tables) and `outputs/reports/table_*.csv`.

## 4. Project structure

```
airline-flight-data-analysis/
├── data/
│   ├── README.md                  # source, license, download steps, column dictionary
│   └── raw/                       # put the downloaded CSV files here (git-ignored)
├── notebooks/
│   └── airline_flight_analysis.ipynb   # step-by-step analysis with explanations
├── src/
│   ├── data_analysis.py           # load -> clean -> features -> analysis -> charts -> findings
│   └── download_data.py           # optional helper to download BTS monthly files
├── outputs/
│   ├── charts/                    # generated PNG charts
│   └── reports/                   # generated report + CSV tables
├── docs/
│   └── STUDY_GUIDE.md             # how to learn and explain this project
├── README.md
├── requirements.txt
└── .gitignore
```

## 5. Method

| Step | What happens | Where |
|---|---|---|
| Load | Read CSV(s), keep only needed columns | `load_data()` |
| Inspect | Rows, types, missing values, summary statistics | notebook section 3 |
| Clean | Convert types, check duplicates / missing / invalid values, **log every decision** | `clean_data()` |
| Derive | Delay flag, status, scheduled hour, time-of-day group, day, month, airline name | `add_features()` |
| Analyse | Group-by summaries for airline, hour, day, month, airport, cancellations | `summarize_by()`, `compute_all()` |
| Visualise | 10 labelled charts | `plot_*()` |
| Report | Findings and recommendations **generated from the computed numbers** | `generate_findings()` |

**Handling of tricky values**

- *Cancelled flights:* kept, but excluded from delay percentages and averages (no departure happened).
- *Missing delay on a non-cancelled flight:* kept, excluded from delay statistics, reported as "Unknown".
- *Extreme delays:* kept (overnight delays are real). The median is reported next to the mean, and the histogram axis is clipped for readability only.
- *Duplicates:* only exact duplicate rows are removed, and the count is reported.
- *Small groups:* airlines need 500+ flights and airports 1,000+ flights to be ranked.

## 6. Visualizations (saved to `outputs/charts/`)

1. Flight outcomes: on-time vs delayed vs cancelled
2. Histogram of departure delays
3. Average delay by airline
4. Delay trend over time (daily + 7-day rolling average)
5. Delay by month *(needs 2+ months)*
6. Delay by scheduled departure hour
7. Delay by day of week
8. Airport performance (highest and lowest average delay)
9. Heatmap: day of week x hour
10. Cancellations by airline and reason

## 7. Technology choices

- **Python, Pandas, NumPy, Matplotlib, Seaborn, Jupyter, Git/GitHub** as required.
- **No SQL:** the data is a single flat table and Pandas `groupby` answers every question clearly.
- **No machine learning:** the goal is to describe patterns, not predict delays. Prediction would be a sensible extension but is not needed to answer these questions.

## 8. Results

Run the project, then open `outputs/reports/analysis_report.md` for the data-driven findings and recommendations (also printed in notebook section 7). Add your own summary here after you have run it, quoting real numbers from the report.

## 9. Limitations

- Only the downloaded months are analysed; delays are seasonal, so they do not represent a full year.
- Averages are not adjusted for route, airport mix, aircraft or weather, and correlation does not prove causation.
- Departure delay is analysed; BTS's own on-time statistic is based on arrival delay.

## 10. Publishing on GitHub

```bash
git init
git add .
git commit -m "Airline flight data analysis project"
git branch -M main
git remote add origin https://github.com/<your-username>/airline-flight-data-analysis.git
git push -u origin main
```

The `.gitignore` keeps the large data files out of the repository. Commit `outputs/charts/` and `outputs/reports/` **after you have run the analysis** so recruiters can see the results without running anything. Consider adding a `LICENSE` file for your code (for example MIT).

**Resume bullet template** (fill in the blanks from `analysis_report.md`; use only your real numbers):

- *Analysed X million U.S. flight records (BTS On-Time Performance, <months/year>) with Python, Pandas and Seaborn; found that Y% of flights departed 15+ minutes late and that <hour/airline/airport finding>.*
- *Built a reproducible cleaning and analysis pipeline (notebook + modular Python script) producing 10 charts and an auto-generated findings report.*

## Data source credit

Source: U.S. Department of Transportation, Bureau of Transportation Statistics, Reporting Carrier On-Time Performance.
