import tkinter as tk
from tkinter import ttk
import threading
import requests
import urllib.parse
from typing import Optional, Tuple

# === GraphHopper Configuration ===
API_KEY = "82dcc496-97d4-45d7-b807-abc1f7b7eebe"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"

# === Light Theme Color Scheme ===
PRIMARY_COLOR = "#0066FF"
PRIMARY_HOVER = "#0052CC"
SUCCESS_COLOR = "#10B981"
ERROR_COLOR = "#EF4444"
WARNING_COLOR = "#F59E0B"
BG_COLOR = "#E8F0FF"
PANEL_COLOR = "#FFFFFF"
INPUT_BG = "#FFFFFF"
INPUT_FG = "#1F2937"
TEXT_PRIMARY = "#1F2937"
TEXT_SECONDARY = "#6B7280"
BORDER_COLOR = "#D1D5DB"
ACCENT_GREEN = "#16A34A"
ACCENT_RED = "#DC2626"

# === Utility Functions ===
def safe_request(url: str, params: dict) -> Optional[dict]:
    """Wrapper to safely make HTTP requests and handle errors."""
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print("API returned status:", response.status_code, "for", url)
            return None
    except requests.exceptions.Timeout:
        print("Request timed out for", url)
    except requests.exceptions.ConnectionError:
        print("Network error for", url)
    except Exception as e:
        print("Unexpected request error:", e)
    return None


def fetch_suggestions(entry_text: str, listbox: tk.Listbox) -> None:
    """Fetch autocomplete suggestions from GraphHopper."""
    try:
        listbox.delete(0, tk.END)
        if entry_text.strip() == "" or len(entry_text.strip()) < 2:
            return

        params = {"q": entry_text, "limit": 5, "key": API_KEY}
        data = safe_request(GEOCODE_URL, params)
        if not data:
            return

        for hit in data.get("hits", []):
            name = hit.get("name")
            if name:
                listbox.insert(tk.END, name)
    except Exception as e:
        print("Error fetching suggestions:", e)


def on_select_suggestion(event: tk.Event, entry: tk.Entry, listbox: tk.Listbox, location_var: tk.StringVar) -> None:
    """When the user selects a suggestion"""
    try:
        selection = listbox.get(listbox.curselection())
        entry.delete(0, tk.END)
        entry.insert(0, selection)
        listbox.delete(0, tk.END)
        location_var.set(selection)
    except (tk.TclError, IndexError):
        pass


def geocode_location(location: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
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
    except (KeyError, TypeError):
        return None, None, None


def show_error(message: str, title: str = "Error") -> None:
    """Display error message in error panel"""
    error_panel.config(state="normal")
    error_panel.delete(1.0, tk.END)
    error_panel.insert(tk.END, f"⚠️ {title}\n", "error_title")
    error_panel.insert(tk.END, message, "error_text")
    error_panel.config(state="disabled")
    # pack the error frame below the header_input (header_input exists after UI creation)
    error_frame.pack(fill="x", pady=(0, 12), ipady=10, padx=12, after=header_input)


def clear_error() -> None:
    """Clear error panel"""
    error_panel.config(state="normal")
    error_panel.delete(1.0, tk.END)
    error_panel.config(state="disabled")
    error_frame.pack_forget()


def calculate_route() -> None:
    """Main route calculation (thread-safe GUI updates)"""
    start = start_var.get().strip()
    dest = dest_var.get().strip()
    vehicle = vehicle_var.get()
    unit = unit_var.get()

    clear_error()

    # === Input Validation ===
    if not start or not dest:
        show_error("Please enter both start and destination locations.", "Invalid Input")
        return
    if start.lower() == dest.lower():
        show_error("Starting location and destination cannot be the same.", "Invalid Input")
        return
    if len(start) < 2 or len(dest) < 2:
        show_error("Please provide more descriptive location names (at least 2 characters).", "Invalid Input")
        return
    if not all(ch.isprintable() for ch in start + dest):
        show_error("Invalid characters detected in location names.", "Invalid Input")
        return

    output_text.config(state="normal")
    output_text.delete(1.0, tk.END)
    output_text.config(state="disabled")
    status_label.config(text="⏳ Calculating route...", foreground=WARNING_COLOR)
    get_directions_btn.config(state="disabled")

    def thread_task() -> None:
        try:
            lat1, lng1, name1 = geocode_location(start)
            lat2, lng2, name2 = geocode_location(dest)

            if lat1 is None or lat2 is None:
                def show_geo_error():
                    clear_error()
                    show_error("One or both locations could not be resolved. Please check the names and try again.", "Geocoding Error")
                    status_label.config(text="❌ Invalid or unknown location.", foreground=ERROR_COLOR)
                    get_directions_btn.config(state="normal")
                root.after(0, show_geo_error)
                return

            params = {
                "key": API_KEY,
                "vehicle": vehicle,
                "point": [f"{lat1},{lng1}", f"{lat2},{lng2}"]
            }

            data = safe_request(ROUTE_URL, params)
            if not data or "paths" not in data or len(data["paths"]) == 0:
                def show_route_error():
                    clear_error()
                    show_error("Unable to retrieve route data from the API. Please try again later.", "Routing Error")
                    status_label.config(text="❌ Unable to retrieve route data.", foreground=ERROR_COLOR)
                    get_directions_btn.config(state="normal")
                root.after(0, show_route_error)
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

            instructions = []
            for i, inst in enumerate(path.get("instructions", []) or [], 1):
                step = inst.get("text", "")
                step_dist_m = inst.get("distance", 0)
                step_dist = step_dist_m / (1000 if unit == "metric" else 1609.34)
                unit_symbol = "km" if unit == "metric" else "miles"
                instructions.append(f"{i}. {step} ({step_dist:.2f} {unit_symbol})")

            def update_ui():
                clear_error()
                status_label.config(text="✓ Route calculated successfully!", foreground=SUCCESS_COLOR)
                output_text.config(state="normal")
                output_text.delete(1.0, tk.END)

                output_text.insert(tk.END, "📍 ROUTE DETAILS\n", "header")
                output_text.insert(tk.END, "━" * 55 + "\n\n")
                output_text.insert(tk.END, f"From:    {name1}\n", "info")
                output_text.insert(tk.END, f"To:      {name2}\n", "info")
                output_text.insert(tk.END, f"Vehicle: {vehicle.upper()}\n\n", "info")

                output_text.insert(tk.END, "📊 SUMMARY\n", "subheader")
                output_text.insert(tk.END, "━" * 55 + "\n")
                output_text.insert(tk.END, f"Distance:  {dist_text}\n", "summary")
                output_text.insert(tk.END, f"Duration:  {time_text}\n\n", "summary")

                output_text.insert(tk.END, "🛣️ DIRECTIONS\n", "subheader")
                output_text.insert(tk.END, "━" * 55 + "\n")
                for line in instructions:
                    output_text.insert(tk.END, line + "\n", "instruction")

                output_text.config(state="disabled")
                get_directions_btn.config(state="normal")

            root.after(0, update_ui)

        except Exception as e:
            def show_unexpected():
                clear_error()
                show_error(f"Unexpected error occurred: {e}", "Error")
                status_label.config(text="❌ Unexpected error occurred.", foreground=ERROR_COLOR)
                get_directions_btn.config(state="normal")
            root.after(0, show_unexpected)

    threading.Thread(target=thread_task, daemon=True).start()


def clear_all() -> None:
    """Clear all input and output"""
    start_entry.delete(0, tk.END)
    dest_entry.delete(0, tk.END)
    start_suggestions.delete(0, tk.END)
    dest_suggestions.delete(0, tk.END)
    start_var.set("")
    dest_var.set("")
    output_text.config(state="normal")
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, "Enter locations and get directions", "placeholder")
    output_text.config(state="disabled")
    status_label.config(text="")
    clear_error()
    get_directions_btn.config(state="normal")


root = tk.Tk()
root.title("Route Planner")
root.geometry("1200x700")
root.configure(bg=BG_COLOR)
root.resizable(True, True)

style = ttk.Style()
style.theme_use('clam')

style.configure("TLabel", background=BG_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
style.configure("Title.TLabel", background=PANEL_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 20, "bold"))
style.configure("Subtitle.TLabel", background=BG_COLOR, foreground=TEXT_SECONDARY, font=("Segoe UI", 11))
style.configure("Heading.TLabel", background=PANEL_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 12, "bold"))
style.configure("Panel.TLabel", background=PANEL_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))

# Entry styling - white background with dark text
style.configure("TEntry", fieldbackground=INPUT_BG, foreground=INPUT_FG, font=("Segoe UI", 11), 
                borderwidth=1, relief="solid", padding=6)
style.map("TEntry", 
         fieldbackground=[("focus", INPUT_BG)],
         borderwidth=[("focus", 2)],
         relief=[("focus", "solid")])

# Combobox styling
style.configure("TCombobox", fieldbackground=INPUT_BG, foreground=INPUT_FG, font=("Segoe UI", 11),
               borderwidth=1, relief="solid", padding=4)
style.map("TCombobox",
         fieldbackground=[("focus", INPUT_BG)])

# Button styling - blue primary button
style.configure("TButton", background=PRIMARY_COLOR, foreground=PANEL_COLOR, font=("Segoe UI", 11, "bold"),
               borderwidth=0, relief="flat", padding=10)
style.map("TButton",
         background=[("active", PRIMARY_HOVER), ("disabled", BORDER_COLOR)],
         foreground=[("disabled", TEXT_SECONDARY)])

# Secondary button - outline style
style.configure("Secondary.TButton", background=PANEL_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 11, "bold"),
               borderwidth=1, relief="solid", padding=10)
style.map("Secondary.TButton",
         background=[("active", "#F3F4F6"), ("disabled", "#F9FAFB")],
         relief=[("active", "solid")])

style.configure("TRadiobutton", background=PANEL_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 11))
style.configure("Panel.TFrame", background=PANEL_COLOR, relief="flat")

# === Variables ===
start_var = tk.StringVar()
dest_var = tk.StringVar()
vehicle_var = tk.StringVar(value="car")
unit_var = tk.StringVar(value="metric")

# === Layout - Two Column Layout ===
container_frame = ttk.Frame(root)
container_frame.pack(fill="both", expand=True, padx=16, pady=16)

# ===== LEFT SIDEBAR - INPUT PANEL =====
left_panel = ttk.Frame(container_frame, style="Panel.TFrame")
left_panel.pack(side="left", fill="both", expand=False, padx=(0, 12))
left_panel.config(width=320)

# Header with icon
header_input = ttk.Frame(left_panel, style="Panel.TFrame")
header_input.pack(fill="x", padx=20, pady=(20, 24))
ttk.Label(header_input, text="🗺️ Route Planner", style="Title.TLabel").pack(anchor="w")
ttk.Label(header_input, text="Find the best route to your destination", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

# Error panel
error_frame = ttk.Frame(left_panel, style="Panel.TFrame")
error_panel = tk.Text(error_frame, height=3, wrap="word", bg="#FEE2E2", fg=ERROR_COLOR, 
                      bd=1, relief="solid", font=("Segoe UI", 9), state="disabled", padx=8, pady=6)
error_panel.pack(fill="x", padx=20, pady=(0, 12))
error_panel.tag_config("error_title", font=("Segoe UI", 9, "bold"), foreground=ERROR_COLOR)
error_panel.tag_config("error_text", foreground=ERROR_COLOR)

# Input container
input_container = ttk.Frame(left_panel, style="Panel.TFrame")
input_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

# Start location
start_label = ttk.Label(input_container, text="📍 Start Location", style="Heading.TLabel")
start_label.pack(anchor="w", pady=(0, 8))
start_entry = ttk.Entry(input_container, textvariable=start_var, style="TEntry")
start_entry.pack(fill="x", pady=(0, 4))
start_suggestions = tk.Listbox(input_container, height=3, bg=INPUT_BG, fg=INPUT_FG, bd=1, 
                               relief="solid", highlightthickness=0, selectbackground=PRIMARY_COLOR, 
                               selectforeground=PANEL_COLOR, activestyle="none", font=("Segoe UI", 10))
start_suggestions.pack(fill="x", pady=(0, 12))

# Destination location
dest_label = ttk.Label(input_container, text="📍 Destination", style="Heading.TLabel")
dest_label.pack(anchor="w", pady=(0, 8))
dest_entry = ttk.Entry(input_container, textvariable=dest_var, style="TEntry")
dest_entry.pack(fill="x", pady=(0, 4))
dest_suggestions = tk.Listbox(input_container, height=3, bg=INPUT_BG, fg=INPUT_FG, bd=1,
                              relief="solid", highlightthickness=0, selectbackground=PRIMARY_COLOR,
                              selectforeground=PANEL_COLOR, activestyle="none", font=("Segoe UI", 10))
dest_suggestions.pack(fill="x", pady=(0, 16))

# Vehicle Type
vehicle_label = ttk.Label(input_container, text="Vehicle Type", style="Heading.TLabel")
vehicle_label.pack(anchor="w", pady=(0, 8))
vehicle_combo = ttk.Combobox(input_container, textvariable=vehicle_var, 
                             values=["car", "bike", "foot"], state="readonly", style="TCombobox", width=25)
vehicle_combo.pack(fill="x", pady=(0, 16))

# Distance Unit
unit_label = ttk.Label(input_container, text="Distance Unit", style="Heading.TLabel")
unit_label.pack(anchor="w", pady=(0, 8))
units_frame = ttk.Frame(input_container, style="Panel.TFrame")
units_frame.pack(anchor="w", pady=(0, 20))
ttk.Radiobutton(units_frame, text="Kilometers", variable=unit_var, value="metric", 
               style="TRadiobutton").pack(anchor="w", pady=(0, 6))
ttk.Radiobutton(units_frame, text="Miles", variable=unit_var, value="imperial", 
               style="TRadiobutton").pack(anchor="w")

# Buttons
buttons_frame = ttk.Frame(input_container, style="Panel.TFrame")
buttons_frame.pack(fill="x")
get_directions_btn = ttk.Button(buttons_frame, text="Get Directions", command=calculate_route, style="TButton")
get_directions_btn.pack(fill="x", pady=(0, 8))
clear_btn = ttk.Button(buttons_frame, text="Clear", command=clear_all, style="Secondary.TButton")
clear_btn.pack(fill="x")

# ===== RIGHT PANEL - RESULTS =====
right_panel = ttk.Frame(container_frame, style="Panel.TFrame")
right_panel.pack(side="right", fill="both", expand=True)

output_scroll = ttk.Scrollbar(right_panel)
output_scroll.pack(side="right", fill="y")

output_text = tk.Text(right_panel, wrap="word", yscrollcommand=output_scroll.set, 
                     bg=PANEL_COLOR, fg=TEXT_PRIMARY, bd=0, relief="flat", 
                     font=("Segoe UI", 11), state="normal", padx=24, pady=24)
output_text.pack(fill="both", expand=True)
output_text.insert(tk.END, "Enter locations and get directions", "placeholder")
output_text.config(state="disabled")
output_scroll.config(command=output_text.yview)

# Text tags for styling
output_text.tag_config("placeholder", foreground=TEXT_SECONDARY, font=("Segoe UI", 14))
output_text.tag_config("header", font=("Segoe UI", 13, "bold"), foreground=PRIMARY_COLOR)
output_text.tag_config("subheader", font=("Segoe UI", 12, "bold"), foreground=TEXT_PRIMARY)
output_text.tag_config("info", foreground=TEXT_SECONDARY, font=("Segoe UI", 11))
output_text.tag_config("summary", foreground=PRIMARY_COLOR, font=("Segoe UI", 11, "bold"))
output_text.tag_config("instruction", foreground=TEXT_PRIMARY, lmargin1=16, lmargin2=32, font=("Segoe UI", 10))

# Status label in left panel
status_label = ttk.Label(left_panel, text="", style="Subtitle.TLabel")
status_label.pack(fill="x", padx=20, pady=(0, 12))

# Bindings for suggestions
def _start_fetch_suggestions(event, entry_widget, listbox_widget):
    text = entry_widget.get()
    threading.Thread(target=fetch_suggestions, args=(text, listbox_widget), daemon=True).start()

start_entry.bind("<KeyRelease>", lambda e: _start_fetch_suggestions(e, start_entry, start_suggestions))
dest_entry.bind("<KeyRelease>", lambda e: _start_fetch_suggestions(e, dest_entry, dest_suggestions))

start_suggestions.bind("<<ListboxSelect>>", lambda e: on_select_suggestion(e, start_entry, start_suggestions, start_var))
dest_suggestions.bind("<<ListboxSelect>>", lambda e: on_select_suggestion(e, dest_entry, dest_suggestions, dest_var))

root.mainloop()
