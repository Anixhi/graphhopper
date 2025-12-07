import pytest
import polyline

from app import safe_request, get_geocode_suggestions, search_poi

def test_safe_request_invalid_url():
    data = safe_request("https://invalid-url.test", {})
    assert data is None

def test_geocode_empty_query():
    assert get_geocode_suggestions("") == []

def test_geocode_short_query():
    assert get_geocode_suggestions("ab") == []

def test_polyline_decode():
    # sample encoded polyline
    encoded = '_p~iF~ps|U_ulLnnqC_mqNvxq`@'
    path = polyline.decode(encoded)
    assert isinstance(path, list)
    assert len(path) > 0

def test_search_poi_returns_list():
    results = search_poi(14.5995, 120.9842, "restaurant")
    assert isinstance(results, list) or results is None
