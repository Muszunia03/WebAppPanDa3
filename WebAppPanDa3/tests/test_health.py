def test_health_endpoint_returns_200_and_status_ok(flask_app):
    response = flask_app.test_client().get('/health')

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
