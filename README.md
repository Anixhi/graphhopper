import tkinter as tk
from tkinter import ttk, messagebox
import requests
import urllib.parse
import threading
from datetime import timedelta

# === API Config ===
API_KEY = "82dcc496-97d4-45d7-b807-abc1f7b7eebe"
ROUTE_URL = "https://graphhopper.com/api/1/route?"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"

# === Utility Functions ===

def geocode(location):
    """Convert a place name to latitude and longitude using GraphHopper."""
    if not location.strip():
        return None, None, None, "Location cannot be empty."

    url = GEOCODE_URL + urllib.parse.urlencode({
        "q": location,
        "limit": "1",
        "key": API_KEY
    })

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if response.status_code == 200 and data.get("hits"):
            hit = data["hits"][0]
            lat, lng = hit["point"]["lat"], hit["point"]["lng"]
            name = hit.get("name", "")
            state = hit.get("state", "")
            country = hit.get("country", "")
            full_name = ", ".join(filter(None, [name, state, country]))
            return lat, lng, full_name, None
        else:
            return None, None, None, f"Could not find '{location}'. Try again."

    except requests.exceptions.RequestException as e:
        return None, None, None, f"Network error: {e}"

def get_route(start, end, vehicle, use_miles):
    """Fetch route from GraphHopper and return formatted data."""
    try:
        url = (
            f"{ROUTE_URL}key={API_KEY}&vehicle={vehicle}"
            f"&point={start[0]},{start[1]}&point={end[0]},{end[1]}"
            "&instructions=true"
        )
        response = requests.get(url, timeout=15)
        data = response.json()

        if response.status_code != 200:
            return None, f"Routing failed: {data.get('message', 'Unknown error')}"

        if not data.get("paths"):
            return None, "No route found between these locations."

        path = data["paths"][0]
        distance_km = path["distance"] / 1000
        distance_miles = distance_km / 1.609
        time_sec = path["time"] / 1000

        distance = distance_miles if use_miles else distance_km
        unit = "miles" if use_miles else "km"
        duration = str(timedelta(seconds=int(time_sec)))

        summary = f"Distance: {distance:.1f} {unit}\nDuration: {duration}"

        directions = []
        for step in path.get("instructions", []):
            txt = step["text"]
            dist_km = step["distance"] / 1000
            dist = dist_km / 1.609 if use_miles else dist_km
            directions.append(f"• {txt}  ({dist:.2f} {unit})")

        return (summary, directions), None

    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"

# === GUI Setup ===

class RouteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GraphHopper Route Planner")
        self.geometry("750x650")
        self.configure(bg="#f0f2f5")
        self.resizable(False, False)
        self.create_widgets()

    def create_widgets(self):
        # Title
        title = tk.Label(
            self, text="GraphHopper Route Planner", font=("Segoe UI", 20, "bold"), bg="#f0f2f5"
        )
        title.pack(pady=15)

        # Input Frame
        frm_input = tk.Frame(self, bg="#f0f2f5")
        frm_input.pack(pady=5)

        labels = ["Starting Location:", "Destination:", "Vehicle Type:"]
        for i, text in enumerate(labels):
            tk.Label(frm_input, text=text, bg="#f0f2f5", font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="e", padx=8, pady=8)

        self.start_entry = tk.Entry(frm_input, width=40, font=("Segoe UI", 10))
        self.end_entry = tk.Entry(frm_input, width=40, font=("Segoe UI", 10))
        self.start_entry.grid(row=0, column=1, padx=5)
        self.end_entry.grid(row=1, column=1, padx=5)

        self.vehicle_choice = ttk.Combobox(
            frm_input, values=["car", "bike", "foot"], width=12, state="readonly"
        )
        self.vehicle_choice.set("car")
        self.vehicle_choice.grid(row=2, column=1, sticky="w", padx=5)

        # Miles checkbox
        self.unit_var = tk.BooleanVar()
        tk.Checkbutton(frm_input, text="Use Miles", variable=self.unit_var, bg="#f0f2f5").grid(row=3, column=1, sticky="w", padx=5)

        # Get Route Button
        self.get_route_btn = tk.Button(
            self, text="Get Route", command=self.run_route_thread,
            width=20, bg="#0078D7", fg="white", font=("Segoe UI", 10, "bold")
        )
        self.get_route_btn.pack(pady=12)

        # Status Label
        self.status_label = tk.Label(self, text="", bg="#f0f2f5", fg="green", font=("Segoe UI", 9, "italic"))
        self.status_label.pack(pady=2)

        # Output area
        self.output_text = tk.Text(
            self, wrap="word", width=90, height=25, state="disabled",
            bg="#ffffff", fg="#333333", font=("Consolas", 10)
        )
        self.output_text.pack(padx=10, pady=10)

    def run_route_thread(self):
        """Run the route calculation in a separate thread to keep the GUI responsive."""
        thread = threading.Thread(target=self.on_get_route)
        thread.daemon = True
        thread.start()

    def on_get_route(self):
        start_loc = self.start_entry.get().strip()
        end_loc = self.end_entry.get().strip()
        vehicle = self.vehicle_choice.get()
        use_miles = self.unit_var.get()

        if not start_loc or not end_loc:
            messagebox.showerror("Input Error", "Please enter both starting and destination locations.")
            return

        self.set_status("Geocoding locations...")
        self.clear_output()

        start_lat, start_lng, start_name, err1 = geocode(start_loc)
        if err1:
            self.set_status("")
            messagebox.showerror("Error", err1)
            return

        end_lat, end_lng, end_name, err2 = geocode(end_loc)
        if err2:
            self.set_status("")
            messagebox.showerror("Error", err2)
            return

        self.display_output(f"From: {start_name}\nTo: {end_name}\nVehicle: {vehicle}\n")
        self.set_status("Fetching route data...")

        result, error = get_route((start_lat, start_lng, start_name),
                                  (end_lat, end_lng, end_name),
                                  vehicle, use_miles)

        if error:
            self.set_status("")
            messagebox.showerror("Route Error", error)
            return

        summary, directions = result
        self.display_output("\n=== ROUTE SUMMARY ===\n" + summary + "\n\n=== DIRECTIONS ===\n")
        for step in directions:
            self.display_output(step + "\n")

        self.set_status("Route retrieved successfully!")

    def display_output(self, text):
        self.output_text.config(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state="disabled")

    def clear_output(self):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state="disabled")

    def set_status(self, msg):
        self.status_label.config(text=msg)
        self.update_idletasks()

if __name__ == "__main__":
    app = RouteApp()
    app.mainloop()
