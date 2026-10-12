# Study Guide (for after your exams)

A calm, step-by-step way to understand this project well enough to explain it in an interview. About 6-8 hours in total; split it over several days.

## Step 1 - Understand the goal and definitions (30 min)
Read `README.md` sections 1, 2 and 5, then `data/README.md` ("Delay definitions"). You should be able to answer:
- What counts as a delayed flight here, and why 15 minutes?
- Why are cancelled flights **not** counted as "on time" or included in the average delay?
- What is the difference between `CRSDepTime` and `DepTime`? Between departure delay and arrival delay?

## Step 2 - Get the data and run it once (1 hour)
Follow the Quick start in `README.md`. Run `python src/data_analysis.py` and open `outputs/reports/analysis_report.md` and the charts. Seeing the finished result first makes the code easier to follow.

## Step 3 - Read the notebook top to bottom (2 hours)
Run each cell and read the explanations. For every cell, say in one sentence what it does. Pay attention to the cleaning log (section 4): can you explain *why* each row was kept or removed?

## Step 4 - Read `src/data_analysis.py` in this order (2 hours)
1. Settings at the top (constants)
2. `clean_data()` - the cleaning decisions
3. `add_features()` - how `sched_hour` and `flight_status` are made
4. `summarize_by()` - the one function behind most tables (a `groupby` with `agg`)
5. One plot function, e.g. `plot_airline_delay()`
6. `generate_findings()` - how numbers become sentences

## Step 5 - Pandas concepts to practise (1-2 hours)
`read_csv(usecols=...)`, boolean masks (`df[df["Cancelled"] == 0]`), `groupby().agg()`, `pivot_table`, `pd.cut`, `value_counts`, `isna().sum()`, `duplicated()`, mean vs median. Try changing a threshold (e.g. 15 -> 30 minutes in `DELAY_THRESHOLD_MIN`) and re-run to see what changes.

## Step 6 - Practise explaining it
Be ready for questions like:
- *Why use the median as well as the mean?* (Long right tail of rare very long delays.)
- *Why group by scheduled rather than actual hour?* (Scheduled time is what passengers book and what airlines plan around.)
- *Can you say hours cause delays?* (No - association only; for example delays may build through the day as late aircraft knock on to later flights. Testing that needs the delay-cause columns.)
- *What are the limits of this analysis?* (A few months only, not adjusted for route/weather, departure vs arrival delay.)
- *How would you extend it?* (More months, delay-cause columns, route analysis, a dashboard, then maybe a prediction model with a proper train/test split.)

## Step 7 - Make it yours
Download a different set of months, or add one question of your own (for example delay by distance). Write your own summary in `README.md` section 8 using your real numbers.
