from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_cors_allows_configured_localhost_origin():
    # A browser preflight from the dev frontend origin must be allowed, or
    # every UI call fails silently in the browser (curl/TestClient without
    # an Origin header never exercises this).
    response = client.options(
        "/cases",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
