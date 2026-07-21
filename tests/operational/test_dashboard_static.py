from pathlib import Path


STATIC = Path("operational/static")


def test_dashboard_shell_has_required_views_and_accessibility_hooks():
    html = (STATIC / "dashboard.html").read_text()
    css = (STATIC / "dashboard.css").read_text()
    js = (STATIC / "dashboard.js").read_text()

    for value in ("Inbox", "Pengaturan", "Pengguna", "aria-live", "Balasan petugas"):
        assert value in html
    for value in (
        "Basis Pengetahuan",
        "BELUM DIVERIFIKASI",
        "knowledge-form",
        "knowledge-content",
    ):
        assert value in html
    assert "/dashboard/api/knowledge" in js
    assert "textContent" in js and "innerHTML" not in js
    assert "min-height:44px" in css
    assert "100dvh" in css
    assert "@media(max-width:640px)" in css
    assert "min-height:44px" in css
    assert "setInterval(refreshDashboard,5000)" in js
    assert "textContent" in js and "innerHTML" not in js


def test_dashboard_never_embeds_secret_or_provider_configuration():
    combined = "".join(
        (STATIC / name).read_text()
        for name in ("dashboard.html", "dashboard.css", "dashboard.js")
    )
    for forbidden in (
        "EVOLUTION_API_KEY",
        "WEBHOOK_SECRET",
        "DASHBOARD_SESSION_SECRET",
    ):
        assert forbidden not in combined
