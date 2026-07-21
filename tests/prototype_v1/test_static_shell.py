from fastapi.testclient import TestClient

from prototype_v1.app import app


client = TestClient(app)


def test_static_shell_exposes_chat_controls_and_accessibility_hooks():
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="transcript"' in response.text
    assert 'id="message-input"' in response.text
    assert 'id="new-conversation"' in response.text
    assert 'aria-live="polite"' in response.text
    assert 'app.js' in response.text
    assert 'styles.css' in response.text
