import streamlit as st
import requests
import urllib.parse
import random
import pandas as pd
import polyline
import pydeck as pdk

# === GraphHopper Configuration ===
API_KEY = "82dcc496-97d4-45d7-b807-abc1f7b7eebe"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"
OSM_SEARCH_URL = "https://nominatim.openstreetmap.org/search?"

# === Utility Functions ===
def safe_request(url: str, params: dict):
    try:
        response = requests.get(url, params=params, timeout=10, headers={"User-Agent": "RoutePlannerApp"})
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
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
    deg = radius_km / 111
    params = {
        "q": keyword,
        "format": "json",
        "limit": 10,
        "bounded": 1,
        "viewbox": f"{lng - deg},{lat + deg},{lng + deg},{lat - deg}",
    }
    return safe_request(OSM_SEARCH_URL, params)

# === Route Calculation (UI SAFE — not executed during testing) ===
def calculate_route(start_point, dest_point, start_name, dest_name, vehicle, unit):
    # This function is unchanged — safe for UI use
    lat1, lng1 = start_point['lat'], start_point['lng']
    lat2, lng2 = dest_point['lat'], dest_point['lng']

    params = {
        "key": API_KEY,
        "vehicle": vehicle,
        "point": [f"{lat1},{lng1}", f"{lat2},{lng2}"],
        "instructions": "true",
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

    st.success("✅ Route calculated successfully!")
    st.subheader("📊 Summary")
    st.write(f"*From:* {start_name}")
    st.write(f"*To:* {dest_name}")
    st.write(f"*Vehicle:* {vehicle.capitalize()}")
    st.write(f"*Distance:* {dist_text}")
    st.write(f"*Duration:* {time_text}")

    st.subheader("🗺️ Route Map")
    encoded_points = path.get("points")

    if encoded_points and path.get("points_encoded", True):
        try:
            decoded_path = polyline.decode(encoded_points)
            if not decoded_path:
                raise Exception("Decoded path is empty.")
            path_data = [[lon, lat] for lat, lon in decoded_path]

            midpoint_lat = (lat1 + lat2) / 2
            midpoint_lng = (lng1 + lng2) / 2
            
            dist_km = dist_m / 1000
            if dist_km > 500: zoom = 5
            elif dist_km > 200: zoom = 7
            elif dist_km > 50: zoom = 9
            elif dist_km > 10: zoom = 11
            else: zoom = 13

            view_state = pdk.ViewState(
                latitude=midpoint_lat,
                longitude=midpoint_lng,
                zoom=zoom,
                pitch=0,
            )

            path_df = pd.DataFrame([{"path": path_data, "name": "Route Path"}])
            layer = pdk.Layer(
                "PathLayer",
                data=path_df,
                get_path="path",
                get_color="[0, 85, 255, 200]",
                get_width=5,
                width_min_pixels=3,
                pickable=True
            )

            point_data = pd.DataFrame([
                {"coordinates": [lng1, lat1], "name": "Start", "color": [0, 200, 0, 255]},
                {"coordinates": [lng2, lat2], "name": "Destination", "color": [255, 0, 0, 255]}
            ])
            
            pin_layer = pdk.Layer(
                "ScatterplotLayer",
                data=point_data,
                get_position="coordinates",
                get_fill_color="color",
                get_radius=100,
                radius_min_pixels=6,
                pickable=True
            )

            r = pdk.Deck(
                layers=[layer, pin_layer],
                initial_view_state=view_state,
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"html": "<b>{name}</b>"}
            )
            st.pydeck_chart(r)

        except Exception as e:
            st.error(f"Error decoding/displaying map path: {e}")
            st.warning("Displaying start and end points only.")
            map_data = pd.DataFrame({'lat': [lat1, lat2], 'lon': [lng1, lng2]})
            st.map(map_data)
    else:
        st.warning("No map path data available. Displaying start and end points.")
        map_data = pd.DataFrame({'lat': [lat1, lat2], 'lon': [lng1, lng2]})
        st.map(map_data)

# ===========================================================
# ========== STREAMLIT UI — RUNS ONLY WHEN EXECUTED ==========
# ===========================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Route Planner", layout="wide")

    hide_st_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """
    st.markdown(hide_st_style, unsafe_allow_html=True)

    st.title("🗺️ Route Planner")
    st.caption("Find the best route with nearby restaurants and gas stations.")

    # Initialize session state
    for key in [
        "start_suggestions", "dest_suggestions", "selected_start_point",
        "selected_dest_point", "start_query_input", "dest_query_input",
        "start_select", "dest_select"
    ]:
        if key not in st.session_state:
            st.session_state[key] = [] if "suggestions" in key else None if "point" in key else ""

    def update_suggestions(mode):
        query = st.session_state.get(f"{mode}_query_input", "")
        st.session_state[f"{mode}_suggestions"] = get_geocode_suggestions(query)
        st.session_state[f"selected_{mode}_point"] = None
        st.session_state[f"{mode}_select"] = ""

    def set_location(mode, suggestion):
        st.session_state[f"selected_{mode}_point"] = suggestion["point"]
        st.session_state[f"{mode}_query_input"] = suggestion["display_name"]
        st.session_state[f"{mode}_select"] = suggestion["display_name"]
        st.session_state[f"{mode}_suggestions"] = []

    def clear_all():
        for key in st.session_state.keys():
            st.session_state[key] = [] if "suggestions" in key else None if "point" in key else ""

    def reverse_locations():
        st.session_state.selected_start_point, st.session_state.selected_dest_point = \
            st.session_state.selected_dest_point, st.session_state.selected_start_point
        
        st.session_state.start_query_input, st.session_state.dest_query_input = \
            st.session_state.dest_query_input, st.session_state.start_query_input
            
        st.session_state.start_select, st.session_state.dest_select = \
            st.session_state.dest_select, st.session_state.start_select
        
        st.session_state.start_suggestions = []
        st.session_state.dest_suggestions = []

    # Sidebar UI
    with st.sidebar:
        st.header("Inputs")

        st.text_input("📍 Start Location", key="start_query_input", on_change=lambda: update_suggestions("start"))
        if st.session_state.selected_start_point and st.session_state.start_select:
            st.success(f"Selected: {st.session_state.start_select}")

        if st.session_state.start_suggestions:
            st.write("Suggestions:")
            for i, s in enumerate(st.session_state.start_suggestions):
                st.button(s["display_name"], key=f"start_{i}", on_click=lambda s=s: set_location("start", s), use_container_width=True)

        st.button("🔄 Reverse Start & Destination", on_click=reverse_locations, use_container_width=True)

        st.text_input("📍 Destination", key="dest_query_input", on_change=lambda: update_suggestions("dest"))
        if st.session_state.selected_dest_point and st.session_state.dest_select:
            st.success(f"Selected: {st.session_state.dest_select}")

        if st.session_state.dest_suggestions:
            st.write("Suggestions:")
            for i, s in enumerate(st.session_state.dest_suggestions):
                st.button(s["display_name"], key=f"dest_{i}", on_click=lambda s=s: set_location("dest", s), use_container_width=True)

        st.divider()
        vehicle = st.selectbox("Travel Type", ["car", "bike", "foot"])
        unit = st.radio("Distance Unit", ["metric (km)", "imperial (mi)"], horizontal=True)

        col1, col2 = st.columns(2)
        with col1:
            calc_btn = st.button("Get Directions", type="primary", use_container_width=True)
        with col2:
            st.button("Clear", use_container_width=True, on_click=lambda: clear_all())

    if calc_btn:
        start_point = st.session_state.selected_start_point
        dest_point = st.session_state.selected_dest_point
        start_name = st.session_state.start_select
        dest_name = st.session_state.dest_select

        if not start_point or not dest_point:
            st.error("⚠️ Please search for and select both a start and destination.")
        elif start_point == dest_point:
            st.error("⚠️ Start and destination cannot be the same.")
        else:
            with st.spinner("⏳ Calculating route..."):
                unit_choice = "metric" if "metric" in unit else "imperial"
                calculate_route(start_point, dest_point, start_name, dest_name, vehicle, unit_choice)
