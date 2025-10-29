"""Tests for the meta endpoints that expose API metadata."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_meta_endpoints_lists_api_routes():
    """Ensure the endpoint returns metadata for the registered API routes."""
    with patch("app.main.init_supabase"):
        with TestClient(app) as client:
            response = client.get("/api/v1/meta/endpoints")

    assert response.status_code == 200

    payload = response.json()
    assert payload["count"] == len(payload["routes"])

    meta_route = next((route for route in payload["routes"] if route["path"] == "/api/v1/meta/endpoints"), None)
    assert meta_route is not None
    assert "GET" in meta_route["methods"]
    assert meta_route["name"] == "list_api_endpoints"
