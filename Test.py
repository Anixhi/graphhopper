import streamlit as st
import requests
import urllib.parse

# === GraphHopper Configuration ===
API_KEY = "82dcc496-97d4-45d7-b807-abc1f7b7eebe"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"

# === Utility Functions ===
def safe_request(url: str, params: dict):
    """Wrapper to safely make HTTP requests and handle errors."""
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API returned status: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Request error: {e}")
        return None

def geocode_location(location: str):
    """Get latitude and longitude from location name"""
    params = {"q": location, "limit": 1, "key": API_KEY}
    data = safe_request(GEOCODE_URL, params)
    if not data or "hits" not in data or len(data["hits"]) == 0:
        return None, None, None
    try:
        lat = data["hits"][0]["point"]["lat"]
        lng = data["hits"][0]["point"]["lng"]
        name = data["hits"][0].get("name", location)
        return lat, lng, name
    except Exception:
        return None, None, None

def calculate_route(start, dest, vehicle, unit):
    """Perform route calculation"""
    lat1, lng1, name1 = geocode_location(start)
    lat2, lng2, name2 = geocode_location(dest)

    if lat1 is None or lat2 is None:
        st.error("❌ One or both locations could not be found.")
        return

    params = {
        "key": API_KEY,
        "vehicle": vehicle,
        "point": [f"{lat1},{lng1}", f"{lat2},{lng2}"]
    }

    data = safe_request(ROUTE_URL, params)
    if not data or "paths" not in data or len(data["paths"]) == 0:
        st.error("❌ Unable to retrieve route data.")
        return

    path = data["paths"][0]
    dist_m = path.get("distance", 0)
    time_ms = path.get("time", 0)

    if unit == "metric":
        dist = dist_m / 1000
        dist_text = f"{dist:.1f} km"
    else:
        dist = dist_m / 1609.34
        dist_text = f"{dist:.1f} miles"

    sec = int(time_ms / 1000 % 60)
    mins = int(time_ms / 1000 / 60 % 60)
    hrs = int(time_ms / 1000 / 60 / 60)
    time_text = f"{hrs:02d}:{mins:02d}:{sec:02d}"

    # Display Route Summary
    st.success("✅ Route calculated successfully!")
    st.subheader("📊 Summary")
    st.write(f"**From:** {name1}")
    st.write(f"**To:** {name2}")
    st.write(f"**Vehicle:** {vehicle.upper()}")
    st.write(f"**Distance:** {dist_text}")
    st.write(f"**Duration:** {time_text}")

    # Directions
    st.subheader("🛣️ Directions")
    instructions = []
    for i, inst in enumerate(path.get("instructions", []) or [], 1):
        step = inst.get("text", "")
        step_dist_m = inst.get("distance", 0)
        step_dist = step_dist_m / (1000 if unit == "metric" else 1609.34)
        unit_symbol = "km" if unit == "metric" else "miles"
        st.markdown(f"**{i}.** {step} ({step_dist:.2f} {unit_symbol})")

# === Streamlit UI ===
st.set_page_config(page_title="Route Planner", layout="wide")
st.title("🗺️ Route Planner")
st.caption("Find the best route to your destination")

with st.sidebar:
    st.header("Inputs")
    start = st.text_input("📍 Start Location")
    dest = st.text_input("📍 Destination")
    vehicle = st.selectbox("Vehicle Type", ["car", "bike", "foot"])
    unit = st.radio("Distance Unit", ["metric", "imperial"], horizontal=True)
    calc_btn = st.button("Get Directions", type="primary")
    clear_btn = st.button("Clear")

if clear_btn:
    st.experimental_rerun()

if calc_btn:
    if not start or not dest:
        st.error("⚠️ Please enter both start and destination locations.")
    elif start.strip().lower() == dest.strip().lower():
        st.error("⚠️ Start and destination cannot be the same.")
    elif len(start.strip()) < 2 or len(dest.strip()) < 2:
        st.error("⚠️ Location names must have at least 2 characters.")
    else:
        with st.spinner("⏳ Calculating route..."):
            calculate_route(start, dest, vehicle, unit)
