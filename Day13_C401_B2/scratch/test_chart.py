import pandas as pd
import altair as alt
from datetime import datetime, timezone, timedelta
import json

def render_multi_line_chart_logic(data, y_fields, y_title, color_domain, color_range):
    df = pd.DataFrame(data)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    
    # Simulate Altair spec generation
    base = alt.Chart(df).transform_fold(
        y_fields, as_=["series", "value"]
    ).encode(
        x=alt.X("time:T", title="Time"),
        y=alt.Y("value:Q", title=y_title),
        color=alt.Color("series:N", scale=alt.Scale(domain=color_domain, range=color_range))
    )
    
    # Just check if it succeeds without error
    spec = (base.mark_line() + base.mark_circle()).to_json()
    return spec

# Test data
now = datetime.now(timezone.utc)
test_data = [
    {"time": now - timedelta(seconds=1), "p50": 100, "p95": 200},
    {"time": now, "p50": 110, "p95": 210}
]

try:
    spec = render_multi_line_chart_logic(
        test_data, 
        ["p50", "p95"], 
        "Ms", 
        ["p50", "p95"], 
        ["green", "blue"]
    )
    print("Success: Spec generated")
    # print(spec[:200])
except Exception as e:
    print(f"Failed: {e}")
