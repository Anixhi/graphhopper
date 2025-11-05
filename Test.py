import streamlit as st
import requests


# === GraphHopper Configuration ===
# CRITICAL: Replace "YOUR_API_KEY" with a valid GraphHopper API key.
# The code WILL NOT run successfully without a valid key.
API_KEY = "82dcc496-97d4-45d7-b807-abc1f7b7eebe" 
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"

