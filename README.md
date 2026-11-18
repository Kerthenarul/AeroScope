# ✈ AeroScope — Airport Leakage & Competitiveness Analytics

An interactive Python/Streamlit aviation-consulting portfolio application for exploring airport competition and hypothetical passenger choice, with a built-in **LAF / IND / ORD** demonstration.

> **IMPORTANT:** The bundled airport numbers are synthetic. AeroScope is an uncalibrated scenario model, **not an estimate of real airport leakage**, measured passenger demand, route profitability, or a certified forecasting product.

## Features

- Airport competitiveness overview with comparisons of fares, driving times, flight frequency, and generalized travel costs.
- Interactive LAF scenario simulator: adjust fares, weekly departures, drive time and parking assumptions.
- Explainable choice model with adjustable time value, schedule preference, parking days and sensitivity.
- Interactive Plotly charts and side-by-side airport comparisons.
- Upload your own CSV with data validation; export scenario results and a consulting-style Markdown memo.
- Automated tests of calculation logic and CSV validation.

## Quickstart (Mac, Windows, Linux)

**Python 3.10+ required.** In your terminal:

```bash
cd aeroscope_project
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the localhost URL that Streamlit prints (typically `http://localhost:8501`).

Run tests:

```bash
python -m pytest -q
```

## CSV format

Upload a CSV with the following header (use **one row per airport**):

```csv
airport_code,airport_name,roundtrip_fare_usd,drive_time_min,weekly_departures,parking_cost_usd,connection_penalty_min
LAF,Purdue University Airport,310,15,12,10,75
IND,Indianapolis International Airport,265,75,260,14,10
ORD,Chicago O'Hare International Airport,240,150,900,24,0
```

These sample values are **invented for demonstrating the application**, even though the airport names and codes are real. Do not cite them as factual prices, flight schedules, or passenger counts.

Column definitions:
- `roundtrip_fare_usd`: illustrative fare for comparable itinerary, in USD.
- `drive_time_min`: one-way ground access time from a common traveler origin, in minutes.
- `weekly_departures`: example number of relevant scheduled departures per week (must be consistently defined across airports).
- `parking_cost_usd`: daily parking cost.
- `connection_penalty_min`: assumed added connection inconvenience in minutes, e.g., considering typical itinerary mix.

## Financial and behavioral methodology

For each airport, the model computes:

```
generalized_cost = fare_weight * roundtrip_fare
    + (drive_time * (2 if roundtrip else 1) / 60) * value_of_time
    + (connection_penalty / 60) * value_of_time
    + parking_weight * parking_per_day * parking_days

utility = -generalized_cost / price_sensitivity
    + frequency_preference * log1p(weekly_departures)

modeled_choice_share = softmax(utilities)
modeled_passengers = modeled_choice_share * hypothetical_travelers
```

These **coefficients are not fitted or validated**. The model helps communicate trade-offs and stress-test assumptions. Real leakage analysis must incorporate observed passenger origin/itinerary surveys, reliable matched fare and schedule samples, proper travel market segmentation, and empirical model validation. Increasing hypothetical travelers does not create actual demand.

## Suggested extension roadmap

1. Source and cite consistent airport/route-level observations from [BTS](https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data) and [FAA](https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger).
2. Collect local survey results and calibrate a discrete-choice model, with train/test split and uncertainty estimates.
3. Add a route-specific market-selection page and break-even model based on separately sourced airline costs and airport revenue.
4. Save imported datasets and metadata with SQLite only if needed; this MVP intentionally avoids a stateful backend.

## Deploy to Streamlit Community Cloud

1. Publish this folder as a GitHub repository (do **not** commit `.venv/`, credentials, or private survey responses).
2. Go to [share.streamlit.io](https://share.streamlit.io/) and create a new app.
3. Select the repo and point the entry file to `app.py`.
4. Deploy. The CSV sample is checked into the repository so the first visit works immediately.

## Resume presentation

After you've used and tested the app, you can truthfully say:

> Built a Streamlit-based airport competition analytics application using Python, pandas, and Plotly to evaluate hypothetical passenger choice and run interactive sensitivity analyses; implemented validated CSV ingestion, scenario memo exports, and automated calculation tests.

Only describe real data integration, empirical forecasting, or measurable business results **if you later add and verify those capabilities**.

## License

MIT (see `LICENSE`).
