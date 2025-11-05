import streamlit as st
import requests
import urllib.parse
import random
import pandas as pd
import polyline

# === GraphHopper Configuration ===
API_KEY = "82dcc496-97d4-45d7-b807-abc1f7b7eebe"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"
OSM_SEARCH_URL = "https://nominatim.openstreetmap.org/search?"

# === Utility Functions ===
def safe_request(url: str, params: dict):
    """Safely make HTTP requests with error handling."""
    try:
        response = requests.get(url, params=params, timeout=10, headers={"User-Agent": "RoutePlannerApp"})
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Request error: {e}")
        return None

# === Location Suggestion Functions ===
def get_geocode_suggestions(query: str):
    if not query or len(query.strip()) < 3:
        return []
    params = {"q": query, "limit": 5, "key": API_KEY}
    data = safe_request(GEOCODE_URL, params)
    if not data or "hits" not in data:
        return []
    suggestions = []
    for hit in data["hits"]:
        name = hit.get("name", "")
        state = hit.get("state", "")
        country = hit.get("country", "")
        display_name = ", ".join(p for p in [name, state, country] if p)
        if "point" in hit:
            suggestions.append({
                "display_name": display_name,
                "point": hit["point"]
            })
    return suggestions

# === POI Search ===
def search_poi(lat, lng, keyword, radius_km=3):
    """Search nearby POIs using OpenStreetMap Nominatim."""
    deg = radius_km / 111  # km → degrees
    params = {
        "q": keyword,
        "format": "json",
        "limit": 10,
        "bounded": 1,
        "viewbox": f"{lng - deg},{lat + deg},{lng + deg},{lat - deg}",
    }
    return safe_request(OSM_SEARCH_URL, params)

def display_poi_results(results):
    if not results:
        st.info("No locations found.")
        return
    for place in results:
        name = place.get("display_name", "Unknown")
        lat = place.get("lat", "")
        lon = place.get("lon", "")
        st.markdown(f"- **{name}** \n 📍 Lat: {lat}, Lng: {lon}")

# === Route Calculation ===
def calculate_route(start_point, dest_point, start_name, dest_name, vehicle, unit):
    lat1, lng1 = start_point['lat'], start_point['lng']
    lat2, lng2 = dest_point['lat'], dest_point['lng']

    params = {
        "key": API_KEY,
        "vehicle": vehicle,
        "point": [f"{lat1},{lng1}", f"{lat2},{lng2}"],
        "instructions": "true"
        "points_encoded": "true"
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

    hrs = int(time_ms / 1000 / 60 / 60)
    mins = int(time_ms / 1000 / 60 % 60)
    sec = int(time_ms / 1000 % 60)
    time_text = f"{hrs:02d}:{mins:02d}:{sec:02d}"

    # --- Tabs ---
    st.success("✅ Route calculated successfully!")
    Jen
    st.subheader("📊 Summary")
    st.write(f"*From:* {start_name}")
    st.write(f"*To:* {dest_name}")
    st.write(f"*Vehicle:* {vehicle.capitalize()}")
    st.write(f"*Distance:* {dist_text}")
    st.write(f"*Duration:* {time_text}")

    # --- Map Display ---
    st.subheader("🗺️ Route Map")
    encoded_points = path.get("points")

    if encoded_points and path.get("points_encoded", True):
        try:
            decoded_path = polyline.decode(encoded_points)
            map_data = pd.DataFrame(decoded_path, columns=['lat', 'lon'])
            st.map(map_data)
        except Exception as e:
            st.error(f"Error decoding map path: {e}")
            map_data = pd.DataFrame({'lat': [lat1, lat2], 'lon': [lng1, lng2]})
            st.map(map_data)
    else:
        map_data = pd.DataFrame({'lat': [lat1, lat2], 'lon': [lng1, lng2]})
        st.map(map_data)

    # --- Directions ---
    st.subheader("🛣️ Directions")
    for i, inst in enumerate(path.get("instructions", []), 1):
        step = inst.get("text", "")
        step_dist_m = inst.get("distance", 0)
        step_dist = step_dist_m / (1000 if unit == "metric" else 1609.34)
        unit_symbol = "km" if unit == "metric" else "miles"
        st.markdown(f"*{i}.* {step} ({step_dist:.2f} {unit_symbol})")

    # --- Road & Traffic Conditions ---
    if vehicle in ["car", "bike"]:
        st.divider()
        st.header("🚦 Road & Traffic Conditions")
        def simulate_road_conditions(instructions):
            """Simulate random traffic or construction events."""
            simulated = []
            for inst in instructions:
                condition = None
                rand = random.random()
                if rand < 0.15:
                    condition = "🚧 Road Construction Ahead"
                elif rand < 0.30:
                    condition = "🚗 Heavy Traffic"
                elif rand < 0.40:
                    condition = "⏱️ Minor Delay"
                if condition:
                    simulated.append({
                        "text": inst.get("text", ""),
                        "condition": condition
                    })
            return simulated

        conditions = simulate_road_conditions(path.get("instructions", []))
        if conditions:
            for c in conditions:
                st.warning(f"{c['condition']} near *{c['text']}*")
        else:
            st.info("✅ No traffic or road construction reported along this route.")

    # --- POIs ---
    st.divider()
    st.header("🍽️ Nearby Places")

    midpoint_lat = (lat1 + lat2) / 2
    midpoint_lng = (lng1 + lng2) / 2

    # Always show restaurants
    display_poi_results("🍔 Restaurants near START", search_poi(lat1, lng1, "restaurant"))
    display_poi_results("🍔 Restaurants MID-ROUTE", search_poi(midpoint_lat, midpoint_lng, "restaurant"))
    display_poi_results("🍔 Restaurants near DESTINATION", search_poi(lat2, lng2, "restaurant"))

    # Only show gas stations for cars
    if vehicle == "car":

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Summary & Directions",
        "🚧 Road Traffic Conditions",
        "🍽️ Nearby Restaurants",
        "⛽ Nearby Gas Stations"
    ])

    # --- Summary & Directions Tab ---
    with tab1:
        st.subheader("📊 Summary")
        st.write(f"*From:* {start_name}")
        st.write(f"*To:* {dest_name}")
        st.write(f"*Vehicle:* {vehicle.capitalize()}")
        st.write(f"*Distance:* {dist_text}")
        st.write(f"*Duration:* {time_text}")
 main
        st.divider()
        st.subheader("🛣️ Directions")
        for i, inst in enumerate(path.get("instructions", []), 1):
            step = inst.get("text", "")
            step_dist_m = inst.get("distance", 0)
            step_dist = step_dist_m / (1000 if unit == "metric" else 1609.34)
            unit_symbol = "km" if unit == "metric" else "miles"
            st.markdown(f"**{i}.** {step} ({step_dist:.2f} {unit_symbol})")

    # --- Road Traffic Conditions Tab ---
    with tab2:
        if vehicle in ["car", "bike"]:
            st.subheader("🚧 Road & Traffic Conditions")

            def simulate_road_conditions(instructions):
                simulated = []
                for inst in instructions:
                    condition = None
                    rand = random.random()
                    if rand < 0.15:
                        condition = "🚧 Road Construction Ahead"
                    elif rand < 0.30:
                        condition = "🚗 Heavy Traffic"
                    elif rand < 0.40:
                        condition = "⚠️ Minor Delay"
                    if condition:
                        simulated.append({
                            "text": inst.get("text", ""),
                            "condition": condition
                        })
                return simulated

            conditions = simulate_road_conditions(path.get("instructions", []))
            if conditions:
                for c in conditions:
                    st.warning(f"{c['condition']} near **{c['text']}**")
            else:
                st.info("✅ No traffic or road construction reported along this route.")
        else:
            st.info("🚶 Road and traffic conditions are only available for cars and bikes.")

    # --- Nearby Restaurants Tab ---
    with tab3:
        st.subheader("🍔 Nearby Restaurants")
        midpoint_lat = (lat1 + lat2) / 2
        midpoint_lng = (lng1 + lng2) / 2
        display_poi_results(search_poi(lat1, lng1, "restaurant"))
        display_poi_results(search_poi(midpoint_lat, midpoint_lng, "restaurant"))
        display_poi_results(search_poi(lat2, lng2, "restaurant"))

    # --- Nearby Gas Stations Tab ---
    with tab4:
        if vehicle == "car":
            st.subheader("⛽ Gas Stations Nearby")
            midpoint_lat = (lat1 + lat2) / 2
            midpoint_lng = (lng1 + lng2) / 2
            display_poi_results(search_poi(lat1, lng1, "fuel"))
            display_poi_results(search_poi(midpoint_lat, midpoint_lng, "fuel"))
            display_poi_results(search_poi(lat2, lng2, "fuel"))
        else:
            st.info("⛽ Gas station info is only available for cars.")

# === Streamlit UI Setup ===
st.set_page_config(page_title="Route Planner", layout="wide")

# --- Hide Streamlit Deploy / Menu Buttons ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("🗺️ Route Planner")
st.caption("Find the best route with nearby restaurants, gas stations, and traffic updates.")

# Initialize session state
for key in [
    "start_suggestions", "dest_suggestions",
    "selected_start_point", "selected_dest_point",
    "start_query_input", "dest_query_input",
    "start_select", "dest_select"
]:
    if key not in st.session_state:
        st.session_state[key] = [] if "suggestions" in key else None if "point" in key else ""

# === Helper Callbacks ===
def update_suggestions(mode):
    query = st.session_state.get(f"{mode}_query_input", "")
    st.session_state[f"{mode}_suggestions"] = get_geocode_suggestions(query)
    st.session_state[f"selected_{mode}_point"] = None

def set_location(mode, suggestion):
    st.session_state[f"selected_{mode}_point"] = suggestion["point"]
    st.session_state[f"{mode}_query_input"] = suggestion["display_name"]
    st.session_state[f"{mode}_select"] = suggestion["display_name"]
    st.session_state[f"{mode}_suggestions"] = []

def clear_all():
    for key in st.session_state.keys():
        st.session_state[key] = [] if "suggestions" in key else None if "point" in key else ""

# === Sidebar Inputs ===
with st.sidebar:
    st.header("Inputs")

    # Start
    st.text_input("📍 Start Location", key="start_query_input", on_change=lambda: update_suggestions("start"))
    if st.session_state.start_suggestions:
        st.write("Suggestions:")
        for i, s in enumerate(st.session_state.start_suggestions):
            st.button(s["display_name"], key=f"start_{i}", on_click=lambda s=s: set_location("start", s), use_container_width=True)

    # --- Reverse Button ---
    st. button("🔄 Reverse Start & Destination", on_click=reverse_locations, use_container_width=True)

    # Destination
    st.text_input("📍 Destination", key="dest_query_input", on_change=lambda: update_suggestions("dest"))
    if st.session_state.dest_suggestions:
        st.write("Suggestions:")
        for i, s in enumerate(st.session_state.dest_suggestions):
            st.button(s["display_name"], key=f"dest_{i}", on_click=lambda s=s: set_location("dest", s), use_container_width=True)

    
    st.divider()
    vehicle = st.selectbox("Vehicle Type", ["car", "bike", "foot"])
    unit = st.radio("Distance Unit", ["metric (km)", "imperial (mi)"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        calc_btn = st.button("Get Directions", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("Clear", use_container_width=True, on_click=lambda: clear_all())

# === Main Logic ===
if calc_btn:
    start_point = st.session_state.selected_start_point
    dest_point = st.session_state.selected_dest_point
    start_name = st.session_state.start_select
    dest_name = st.session_state.dest_select

    if not start_point or not dest_point or not start_name or not dest_name:
        st.error("⚠️ Please search for and select both a start and destination.")
        st.toast("Please select locations.", icon="⚠️")
    elif start_point == dest_point:
        st.error("⚠️ Start and destination cannot be the same.")
        st.toast("Locations are the same.", icon="⚠️")
    else:
        with st.spinner("⏳ Calculating route..."):
            unit_choice = "metric" if "metric" in unit else "imperial"
            calculate_route(start_point, dest_point, start_name, dest_name, vehicle, unit_choice)
            st.toast("Roast calculated!", icon="✅")
  main
