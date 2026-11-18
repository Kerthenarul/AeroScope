"""AeroScope: an explainable, interactive aviation-consulting portfolio app."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from model import Assumptions, REQUIRED_COLUMNS, validate_airports, evaluate, apply_laf_scenario, make_memo

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "data" / "sample_airports.csv"

st.set_page_config(page_title="AeroScope | Aviation Market Intelligence", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1380px;}
.hero {border-radius:18px; background:linear-gradient(110deg,#0f2945 0%,#124d60 60%,#0f766e 100%);padding:27px 32px;color:#fff;margin-bottom:18px;}
.hero h1 {color:#fff;font-size:2.25rem;letter-spacing:-.04em;margin:0;}
.hero p {color:#d2e8ec;font-size:1rem;margin:8px 0 0;}
.kicker {font-size:.72rem;color:#9de3d5;font-weight:700;letter-spacing:.15em;text-transform:uppercase;}
.warning-line {border-left:4px solid #f59e0b;padding:.65rem 1rem;background:#fffbeb;border-radius:7px;color:#854d0e;margin:10px 0 23px;}
section[data-testid="stSidebar"] {background-color:#f6f9fc;}
[data-testid="stMetricValue"] {font-weight:730;}
.small-note {color:#64748b;font-size:.82rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="hero"><div class="kicker">Aviation Strategy & Analytics</div><h1>✈ AeroScope</h1><p>Airport competition, passenger choice, and scenario intelligence — built for practical consulting analysis.</p></div>''', unsafe_allow_html=True)
st.markdown('<div class="warning-line"><b>Portfolio demo, not a demand forecast.</b> Sample airport values are synthetic illustrations. Model parameters are not calibrated with real passenger-choice observations.</div>', unsafe_allow_html=True)

st.sidebar.subheader("Data source")
upload = st.sidebar.file_uploader("Upload airport data (.csv)", type=["csv"], help="Upload a CSV with the same columns as the sample file.")
try:
    frame = validate_airports(pd.read_csv(upload if upload is not None else SAMPLE))
except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
    st.error(f"The CSV could not be used: {exc}")
    st.info("Download the template and keep the same column names and numeric formats.")
    st.download_button("Download sample CSV", SAMPLE.read_bytes(), file_name="aeroscope_sample_airports.csv", mime="text/csv")
    st.stop()

st.sidebar.caption("Synthetic sample loaded" if upload is None else "Custom CSV loaded — verify the provenance of your inputs.")
st.sidebar.download_button("Download CSV template", SAMPLE.read_bytes(), file_name="aeroscope_template.csv", mime="text/csv", use_container_width=True)

st.sidebar.divider()
st.sidebar.subheader("Model assumptions")
travelers = st.sidebar.number_input("Hypothetical regional travelers", min_value=0, max_value=10000000, value=10000, step=1000)
value_time = st.sidebar.slider("Value of travel time ($/hour)", min_value=0, max_value=100, value=25, step=5)
trip_days = st.sidebar.slider("Parking days per trip", min_value=0, max_value=14, value=4)
roundtrip = st.sidebar.toggle("Count roundtrip driving", value=True)
with st.sidebar.expander("Advanced model preferences"):
    frequency_preference = st.slider("Flight availability preference", 0.0, 3.0, 1.4, .1)
    price_sensitivity = st.slider("Choice dispersion ($)", 20, 200, 65, 5, help="Higher values make the model less sensitive to cost differences.")
    fare_weight = st.slider("Fare cost weight", 0.0, 2.0, 1.0, .1)
    parking_weight = st.slider("Parking cost weight", 0.0, 2.0, 1.0, .1)

assumptions = Assumptions(traveler_count=int(travelers),value_of_time_usd_per_hour=float(value_time),
                          fare_weight=float(fare_weight),parking_weight=float(parking_weight),
                          frequency_preference=float(frequency_preference),price_sensitivity_usd=float(price_sensitivity),
                          trip_duration_days=int(trip_days),roundtrip_drive=roundtrip)

baseline = evaluate(frame, assumptions)
tabs = st.tabs(["📊 Market overview", "🛫 LAF scenario simulator", "⚖️ Airport comparison", "📚 Methodology & data"])

with tabs[0]:
    st.subheader("Competitive airport landscape")
    cols = st.columns(4)
    cols[0].metric("Airports modeled", f"{len(frame)}")
    cols[1].metric("Hypothetical travelers", f"{assumptions.traveler_count:,}")
    cols[2].metric("Lowest sample airfare", f"${frame['roundtrip_fare_usd'].min():,.0f}")
    cols[3].metric("Model leader", str(baseline.loc[baseline['modeled_share'].idxmax(),'airport_code']))
    a,b = st.columns([1.12,1])
    with a:
        fig = px.bar(baseline.sort_values('modeled_share',ascending=True),x='modeled_share',y='airport_code',orientation='h',
                     color='airport_code',text='modeled_share',color_discrete_sequence=['#0f766e','#26759c','#9caec2','#5b86a8'])
        fig.update_traces(texttemplate='%{x:.1%}',textposition='outside',cliponaxis=False)
        fig.update_layout(title="Hypothetical airport choice share",xaxis_title="Choice share",yaxis_title="",showlegend=False,
                          xaxis_tickformat='.0%',margin=dict(t=55,l=0,r=50,b=20),height=350)
        st.plotly_chart(fig,use_container_width=True)
    with b:
        fig = px.scatter(baseline,x='drive_time_min',y='roundtrip_fare_usd',size='weekly_departures',text='airport_code',
                         color='airport_code',color_discrete_sequence=['#0f766e','#26759c','#9caec2','#5b86a8'],size_max=55)
        fig.update_traces(textposition='top center')
        fig.update_layout(title="Cost, access & schedule trade-offs",xaxis_title="One-way driving time (min)",
                          yaxis_title="Illustrative roundtrip airfare ($)",showlegend=False,height=350,margin=dict(t=55,l=0,r=20,b=20))
        st.plotly_chart(fig,use_container_width=True)
    st.markdown("**Airport inputs and model outputs**")
    readable = baseline[['airport_code','airport_name','roundtrip_fare_usd','drive_time_min','weekly_departures',
                         'generalized_cost_usd','modeled_share','modeled_passengers']].copy()
    readable.columns=['Code','Airport','Roundtrip fare ($)','Drive (min)','Weekly departures','Generalized cost ($)','Modeled share','Modeled travelers']
    st.dataframe(readable.style.format({'Roundtrip fare ($)':'${:,.0f}','Generalized cost ($)':'${:,.0f}',
                                       'Modeled share':'{:.1%}','Modeled travelers':'{:,.0f}'}),use_container_width=True,hide_index=True)

with tabs[1]:
    st.subheader("Test strategic opportunities at LAF")
    if 'LAF' not in set(frame['airport_code']):
        st.info("Upload a CSV containing an airport_code of LAF to use the LAF scenario simulator. The other tabs work for any airport set.")
    else:
        st.caption("Scenario adjustments are relative to your current dataset. Moving a slider changes only LAF's assumed attributes.")
        c1,c2=st.columns(2)
        with c1:
            fare_change=st.slider("LAF roundtrip fare adjustment ($)",-150,150,-35,5)
            drive_change=st.slider("LAF one-way access-time adjustment (min)",-30,60,0,5)
        with c2:
            departures_change=st.slider("LAF weekly departure adjustment",-10,50,8,1)
            parking_change=st.slider("LAF daily parking adjustment ($)",-10,20,0,1)
        changed = apply_laf_scenario(frame,fare_change,departures_change,drive_change,parking_change)
        scenario = evaluate(changed,assumptions)
        base_laf=float(baseline.set_index('airport_code').loc['LAF','modeled_share'])
        new_laf=float(scenario.set_index('airport_code').loc['LAF','modeled_share'])
        diff=(new_laf-base_laf)*assumptions.traveler_count
        x,y,z=st.columns(3)
        x.metric("Baseline modeled LAF share",f"{base_laf:.1%}")
        y.metric("Scenario modeled LAF share",f"{new_laf:.1%}",delta=f"{(new_laf-base_laf)*100:+.2f} pp")
        z.metric("Change in hypothetical travelers",f"{diff:+,.0f}")
        comparison=pd.DataFrame({'Airport':baseline['airport_code'],'Baseline':baseline['modeled_share'],
                                 'Scenario':scenario['modeled_share']}).melt('Airport',var_name='Case',value_name='Share')
        fig=px.bar(comparison,x='Airport',y='Share',color='Case',barmode='group',text='Share',
                   color_discrete_map={'Baseline':'#94a3b8','Scenario':'#0f766e'})
        fig.update_traces(texttemplate='%{y:.1%}',textposition='outside')
        fig.update_layout(yaxis_tickformat='.0%',title="How the scenario changes modeled choice shares",height=370,margin=dict(t=55,b=20))
        st.plotly_chart(fig,use_container_width=True)
        st.info("Interpret these as illustrative *model outputs*, not measured passenger leakage, actual demand captured, or incremental revenue.")
        memo=make_memo(baseline,scenario,assumptions,fare_change,departures_change,drive_change,parking_change)
        st.download_button("⬇ Download consulting memo (.md)",memo,file_name="aeroscope_laf_scenario_memo.md",mime="text/markdown")
        st.download_button("⬇ Download scenario results (.csv)",scenario.to_csv(index=False),file_name="aeroscope_scenario_results.csv",mime="text/csv")

with tabs[2]:
    st.subheader("Airport competitiveness comparison")
    selected=st.multiselect("Choose airports to compare",options=baseline['airport_code'].tolist(),default=baseline['airport_code'].head(3).tolist())
    subset=baseline[baseline['airport_code'].isin(selected)].copy()
    if subset.empty:
        st.info("Select at least one airport.")
    else:
        p=px.bar(subset,x='airport_code',y=['roundtrip_fare_usd','generalized_cost_usd'],barmode='group',
                 labels={'value':'USD','airport_code':'Airport','variable':'Metric'},title="Fares versus total generalized travel costs",
                 color_discrete_sequence=['#0f766e','#466a97'])
        p.update_layout(height=365,margin=dict(t=55,b=20))
        st.plotly_chart(p,use_container_width=True)
        st.dataframe(subset[['airport_code','roundtrip_fare_usd','drive_time_min','weekly_departures',
                             'parking_total_usd','drive_cost_usd','connection_cost_usd','generalized_cost_usd']]
                     .rename(columns={'airport_code':'Airport','roundtrip_fare_usd':'Fare ($)',
                                      'drive_time_min':'Drive time (min)','weekly_departures':'Weekly departures',
                                      'parking_total_usd':'Trip parking ($)','drive_cost_usd':'Time cost ($)',
                                      'connection_cost_usd':'Connection cost ($)','generalized_cost_usd':'Total generalized cost ($)'}),
                     hide_index=True,use_container_width=True)
        st.caption("This is a comparison of provided assumptions, not live airfare or timetable data.")

with tabs[3]:
    st.subheader("Model documentation")
    st.markdown("""
**Objective.** Compare how passengers might trade off price, airport access, schedule convenience, and connections.

**Generalized cost**, measured in illustrative dollar equivalents:

`fare_weight × airfare + (drive_minutes × driving_multiplier / 60 × value_of_time) + (connection_minutes / 60 × value_of_time) + parking_weight × daily_parking × parking_days`

**Modeled utility** for airport `i`:

`utility_i = -generalized_cost_i / choice_dispersion + frequency_preference × ln(1 + weekly_departures_i)`

**Choice share** uses a stable softmax:

`share_i = exp(utility_i - max_utility) / sum_j exp(utility_j - max_utility)`

**Hypothetical travelers at airport i** = `choice_share_i × user_selected_region_travelers`

The formula is deliberately simple and explainable. Its coefficients are *assumed*, not estimated. Frequency acts as an imperfect proxy for destination and departure-time choice. An increase in LAF supply shifts choices in the model; it does **not** establish that an airline would operate those departures, that demand would materialize, or that the service would be profitable.

### Data integrity
- The bundled `data/sample_airports.csv` has illustrative values only. Even plausible-looking airport numbers are **not historical measurements**.
- CSV imports allow you to replace the sample with your own observed data. Keep a record of source, download date, time period, definitions, and units.
- A local survey of travelers near Lafayette would be needed to estimate leakage directly. Public airport totals alone cannot identify home-region airport choice.
- BTS O&D Survey, FAA enplanements, and BTS On-Time Performance can supplement your research, but require interpretation and careful joining to geographic survey evidence.

### How to turn this into a stronger consulting study
1. Segment passengers by destination, trip purpose, party size, and willingness to pay.
2. Collect observed fare/itinerary options at the same booking horizon.
3. Estimate coefficients from your airport-choice survey and report holdout accuracy and uncertainty.
4. Incorporate route economics, airline feasibility, sensitivity ranges, and airport revenue before making recommendations.

**Not a commercial aviation forecasting tool.** It is an analytical portfolio demonstration.
""")
    st.markdown("**Required CSV columns**")
    st.code(", ".join(REQUIRED_COLUMNS),language="text")
    st.markdown("**Public aviation research sources**")
    st.markdown("- [BTS Origin & Destination Survey](https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data)\n- [FAA Passenger Boarding Statistics](https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger)\n- [BTS On-Time Performance](https://transtats.bts.gov/ONTIME/Index.aspx)")

st.divider()
st.caption("AeroScope · Aviation consulting portfolio app · Transparent methodology · Synthetic starting data")
