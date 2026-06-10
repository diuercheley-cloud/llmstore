from app.services.export_reporting import render_export_response


def test_render_export_response_json_sets_attachment_header():
    response = render_export_response("usage", [{"client_id": "1", "total_tokens": 10}], "json")

    assert response.headers["Content-Disposition"] == 'attachment; filename="usage.json"'


def test_render_export_response_csv_contains_header():
    response = render_export_response("usage", [{"client_id": "1", "total_tokens": 10}], "csv")

    body = response.body.decode("utf-8")
    assert "client_id,total_tokens" in body
    assert "1,10" in body
