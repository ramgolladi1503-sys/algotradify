
import redis, json

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def emit_event(event_type, payload):
    event = {"type": event_type, "payload": payload}
    r.publish("tradebot_events", json.dumps(event))
