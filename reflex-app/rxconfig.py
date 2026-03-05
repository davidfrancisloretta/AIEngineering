import reflex as rx

config = rx.Config(
    app_name="rave_ai",
    # Reflex WebSocket backend — browser connects here for state updates.
    # Must be a URL reachable from the user's browser (not internal Docker hostname).
    api_url="http://localhost:8001",
    backend_port=8001,
    stylesheets=["rave.css"],
)
