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
            st.error(f"API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Request error: {e}")
        return None

def get_geocode_suggestions(query: str):
    """Fetches a list of geocode hits (suggestions)."""
    # Don't search for empty or very short strings
    if not query or len(query.strip()) < 3:
        return []
        
    params = {"q": query, "limit": 5, "key": API_KEY}
    data = safe_request(GEOCODE_URL, params)
    
    if not data or "hits" not in data or len(data["hits"]) == 0:
        return []
    
    # Format for display and store the lat/lng point
    suggestions = []
    for hit in data["hits"]:
        # Build a descriptive name
        name = hit.get("name", "")
        state = hit.get("state", "")
        country = hit.get("country", "")
        
        # Join the parts that actually exist
        parts = [name, state, country]
        display_name = ", ".join(p for p in parts if p)
        
        # Include the point (lat/lng) for route calculation
        if "point" in hit:
            suggestions.append({
                "display_name": display_name,
                "point": hit["point"] 
            })
    return suggestions

def calculate_route(start_point, dest_point, start_name, dest_name, vehicle, unit):
    """Perform route calculation using lat/lng points."""
    
    lat1, lng1 = start_point['lat'], start_point['lng']
    lat2, lng2 = dest_point['lat'], dest_point['lng']

    params = {
        "key": API_KEY,
        "vehicle": vehicle,
        "point": [f"{lat1},{lng1}", f"{lat2},{lng2}"],
        "instructions": "true",
        "calc_points": "false", # We don't need the full geometry
    }

    data = safe_request(ROUTE_URL, params)
    if not data or "paths" not in data or len(data["paths"]) == 0:
        st.error("❌ Unable to retrieve route data.")
        return

    path = data["paths"][0]
    dist_m = path.get("distance", 0)
    time_ms = path.get("time", 0)

    # Unit conversion
    if unit == "metric":
        dist = dist_m / 1000
        dist_text = f"{dist:.1f} km"
    else:
        dist = dist_m / 1609.34
        dist_text = f"{dist:.1f} miles"

    # Time conversion
    sec = int(time_ms / 1000 % 60)
    mins = int(time_ms / 1000 / 60 % 60)
    hrs = int(time_ms / 1000 / 60 / 60)
    time_text = f"{hrs:02d}:{mins:02d}:{sec:02d}"

    # Display Route Summary
    st.success("✅ Route calculated successfully!")
    st.subheader("📊 Summary")
    st.write(f"**From:** {start_name}")
    st.write(f"**To:** {dest_name}")
    st.write(f"**Vehicle:** {vehicle.capitalize()}")
    st.write(f"**Distance:** {dist_text}")
    st.write(f"**Duration:** {time_text}")

    # Directions
    st.subheader("🛣️ Directions")
    instructions = path.get("instructions", [])
    if not instructions:
        st.write("No turn-by-turn directions available for this route.")
        return

    for i, inst in enumerate(instructions, 1):
        step = inst.get("text", "")
        step_dist_m = inst.get("distance", 0)
        
        # Convert step distance
        if unit == "metric":
            step_dist = step_dist_m / 1000
            unit_symbol = "km"
        else:
            step_dist = step_dist_m / 1609.34
            unit_symbol = "miles"
            
        st.markdown(f"**{i}.** {step} ({step_dist:.2f} {unit_symbol})")

# === Callbacks for Suggestions ===
def update_start_suggestions():
    """Callback to update start suggestions based on text input."""
    query = st.session_state.get("start_query_input", "")
    st.session_state.start_suggestions = get_geocode_suggestions(query)
    # Clear selected point if the user types a new query
    st.session_state.selected_start_point = None

def update_dest_suggestions():
    """Callback to update destination suggestions based on text input."""
    query = st.session_state.get("dest_query_input", "")
    st.session_state.dest_suggestions = get_geocode_suggestions(query)
    # Clear selected point if the user types a new query
    st.session_state.selected_dest_point = None

# === Callbacks for Suggestion Selection ===
def set_start_location(suggestion):
    """Callback to set the selected start location."""
    st.session_state.selected_start_point = suggestion['point']
    # Update the text box to show the selected name
    st.session_state.start_query_input = suggestion['display_name'] 
    # Store the selected name for the summary
    st.session_state.start_select = suggestion['display_name']
    # Clear suggestions now that one is selected
    st.session_state.start_suggestions = [] 

def set_dest_location(suggestion):
    """Callback to set the selected destination."""
    st.session_state.selected_dest_point = suggestion['point']
    # Update the text box to show the selected name
    st.session_state.dest_query_input = suggestion['display_name']
    # Store the selected name for the summary
    st.session_state.dest_select = suggestion['display_name']
    # Clear suggestions now that one is selected
    st.session_state.dest_suggestions = []

def clear_all():
    """Callback to clear all session state values."""
    st.session_state.start_suggestions = []
    st.session_state.dest_suggestions = []
    st.session_state.selected_start_point = None
    st.session_state.selected_dest_point = None
    st.session_state.start_query_input = ""
    st.session_state.dest_query_input = ""
    st.session_state.start_select = ""
    st.session_state.dest_select = ""

# === Streamlit UI ===
st.set_page_config(page_title="Route Planner", layout="wide")

# Initialize session state
if 'start_suggestions' not in st.session_state:
    st.session_state.start_suggestions = []
if 'dest_suggestions' not in st.session_state:
    st.session_state.dest_suggestions = []
if 'selected_start_point' not in st.session_state:
    st.session_state.selected_start_point = None
if 'selected_dest_point' not in st.session_state:
    st.session_state.selected_dest_point = None
# Keys for widgets to persist their state
if 'start_query_input' not in st.session_state:
    st.session_state.start_query_input = ""
if 'dest_query_input' not in st.session_state:
    st.session_state.dest_query_input = ""
# Store the selected display names
if 'start_select' not in st.session_state:
    st.session_state.start_select = ""
if 'dest_select' not in st.session_state:
    st.session_state.dest_select = ""

st.title("🗺️ Route Planner")
st.caption("Find the best route to your destination")

with st.sidebar:
    st.header("Inputs")
    
    # --- Start Location ---
    st.text_input(
        "📍 Start Location", 
        key="start_query_input", 
        on_change=update_start_suggestions,
        help="Type 3+ characters and press Enter to see suggestions."
    )

    # Show suggestions as clickable buttons
    if st.session_state.start_suggestions:
        st.write("Suggestions:")
        # Add enumerate to get a unique index 'i'
        for i, s in enumerate(st.session_state.start_suggestions):
            st.button(
                s['display_name'], 
                # Add the index 'i' to the key to make it unique
                key=f"start_sug_{i}_{s['display_name']}",
                on_click=set_start_location, 
                args=(s,),
                use_container_width=True
            )
    
    # --- Destination ---
    st.text_input(
        "📍 Destination", 
        key="dest_query_input", 
        on_change=update_dest_suggestions,
        help="Type 3+ characters and press Enter to see suggestions."
    )

    # Show suggestions as clickable buttons
    if st.session_state.dest_suggestions:
        st.write("Suggestions:")
        # Add enumerate to get a unique index 'i'
        for i, s in enumerate(st.session_state.dest_suggestions):
            st.button(
                s['display_name'], 
                # Add the index 'i' to the key to make it unique
                key=f"dest_sug_{i}_{s['display_name']}",
                on_click=set_dest_location, 
                args=(s,),
                use_container_width=True
            )

    # --- Other Inputs ---
    vehicle = st.selectbox("Vehicle Type", ("car", "bike", "foot"))
    unit = st.radio("Distance Unit", ("metric", "imperial"), horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        calc_btn = st.button("Get Directions", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button(
            "Clear", 
            use_container_width=True,
            on_click=clear_all  # Use the on_click callback
        )

# --- Main App Logic ---

if calc_btn:
    start_point = st.session_state.selected_start_point
    dest_point = st.session_state.selected_dest_point
    
    # Get the selected display names from the selectbox keys
    start_name = st.session_state.get("start_select")
    dest_name = st.session_state.get("dest_select")

    if not start_point or not dest_point or not start_name or not dest_name:
        st.error("⚠️ Please search for and select both a start and destination.")
    elif start_point['lat'] == dest_point['lat'] and start_point['lng'] == dest_point['lng']:
         st.error("⚠️ Start and destination cannot be the same.")
    else:
        with st.spinner("⏳ Calculating route..."):
            calculate_route(start_point, dest_point, start_name, dest_name, vehicle, unit)
