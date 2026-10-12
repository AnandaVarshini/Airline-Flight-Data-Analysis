# Data: U.S. BTS Airline On-Time Performance

**The data files are NOT included in this repository** (they are hundreds of MB and `.gitignore` excludes them).
Follow the steps below, put the CSV file(s) inside this `data/` folder (the `data/raw/` sub-folder is best), and the notebook and script will find them automatically.

## Source

- **Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics (BTS)
- **Dataset:** *Reporting Carrier On-Time Performance (1987-present)* - one row per scheduled domestic flight
- **Website:** https://www.transtats.bts.gov/ONTIME/
- **Coverage:** flights operated by large U.S. airlines (those reporting to BTS) within the U.S.; it does not include international routes or small carriers that do not report.

## License / usage conditions

BTS data is produced by a U.S. federal agency and is published openly for public use. U.S. government works are generally not subject to copyright, but **please confirm the current terms on the BTS website** before redistributing, and always cite the source:

> Source: U.S. Department of Transportation, Bureau of Transportation Statistics, Reporting Carrier On-Time Performance.

This project does not redistribute the data; each user downloads their own copy from BTS.

## Recommended sample size

Download **3 consecutive months** of one year (for example January-March, or any months you like). One month is roughly 500,000-650,000 flights, so three months is ~1.5-2 million rows: big enough to show real patterns and to compare months, but still manageable on a laptop (the code reads only the columns it needs). One month alone also works, but the "delay by month" chart is skipped.

## Option A - automatic download (try this first)

From the project folder:

```bash
python src/download_data.py --year 2024 --months 1 2 3
```

This fetches BTS's monthly ZIP files, unzips them into `data/raw/` and removes the ZIPs. It needs internet access. If the year/month is not published yet or the BTS site has changed, it will tell you, and you can use Option B.

## Option B - manual download (always works)

**B1. Pre-packaged monthly files (simplest)**

1. Open https://www.transtats.bts.gov/ONTIME/ and follow the link to the *Reporting Carrier On-Time Performance* data (look for the "Download" / pre-zipped files section).
2. Pick a year and month; download the ZIP file (named like `On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_1.zip`).
3. Unzip it and copy the `.csv` file into `data/raw/`.
4. Repeat for the other months.

**B2. Custom download with chosen columns (smaller files)**

1. On the BTS On-Time page, open the *Reporting Carrier On-Time Performance (1987-present)* "Download" page.
2. Choose **Filter Year** and **Filter Period** (month), and keep "Prezipped File" unticked.
3. Tick the fields listed under "Columns used" below, then click **Download**.
4. Unzip, put the CSV in `data/raw/`. Repeat per month.

## Columns used by this project

| Column | Meaning |
|---|---|
| `FlightDate` | Date of the flight (YYYY-MM-DD) |
| `Reporting_Airline` | Airline code (e.g. `DL`, `UA`) |
| `Origin` / `Dest` | Origin and destination airport codes |
| `CRSDepTime` | **Scheduled** departure time, local, hhmm format (e.g. `1530`) |
| `DepTime` | **Actual** departure time, local, hhmm |
| `DepDelay` | Departure delay in minutes; **negative = left early**; empty for cancelled flights |
| `DepDelayMinutes` | Departure delay with early departures set to 0 |
| `DepDel15` | 1 if the flight departed 15+ minutes late, else 0 |
| `Cancelled` | 1 if the flight was cancelled |
| `CancellationCode` | Reason: A = airline/carrier, B = weather, C = National Air System, D = security |
| `Diverted` | 1 if the flight was diverted to another airport |
| `Distance` | Distance in miles |
| `Flight_Number_Reporting_Airline`, `Tail_Number` | Used only to help recognise exact duplicates |

**Required:** `FlightDate`, `Reporting_Airline`, `Origin`, `CRSDepTime`, `DepDelay`, `Cancelled`. The rest are optional; the project adapts if they are missing. A full BTS file has ~110 columns (arrival delays, taxi times, delay-cause minutes, ...); extra columns are ignored.

## Delay definitions used in this project

- **Delayed flight:** departed **15 or more minutes** after the scheduled time (`DepDelay >= 15`). This matches BTS's `DepDel15` flag.
- **On-time flight:** departed less than 15 minutes late (including flights that left early).
- **Cancelled flight:** `Cancelled = 1`. It has no departure delay value, so it is excluded from delay percentages and averages and analysed separately.
- **Average delay:** mean of `DepDelay` in minutes over flights that actually have a departure delay value. Early departures are negative and lower the average; the median is reported too.
- This project analyses **departure** delays. (BTS's own "on-time" statistic is based on *arrival* delay, so numbers here will not match BTS's headline on-time percentage.)
