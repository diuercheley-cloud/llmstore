def test_simple():
    assert True


def test_import_app():
    from app.main import app

    assert app is not None
