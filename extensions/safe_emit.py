
from extensions.event_bus import emit_event

def safe_emit(event_type, payload):
    try:
        emit_event(event_type, payload)
    except Exception as e:
        print("EVENT ERROR:", e)
