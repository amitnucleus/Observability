import os
import hashlib
import hmac
from fastapi import FastAPI, Request, HTTPException, Header
from app.kafka_client import publish

app = FastAPI(title="PNOG Git Webhook")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "pnog_webhook_secret")

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    payload = await request.body()

    if x_hub_signature_256 and not verify_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    publish("git.releases", {
        "event":      x_github_event or "push",
        "ref":        data.get("ref", ""),
        "commit":     data.get("after", ""),
        "pusher":     data.get("pusher", {}).get("name", "unknown"),
        "repo":       data.get("repository", {}).get("full_name", ""),
        "compare":    data.get("compare", ""),
        "layer":      "L5",
    })

    return {"status": "received"}

@app.post("/webhook/simulate")
async def simulate_release(ref: str = "refs/heads/main", commit: str = "abc123"):
    """Inject a fake git release for demo/testing purposes."""
    publish("git.releases", {
        "event":   "push",
        "ref":     ref,
        "commit":  commit,
        "pusher":  "demo-user",
        "repo":    "pnog/demo-service",
        "compare": "",
        "layer":   "L5",
    })
    return {"status": "simulated", "ref": ref, "commit": commit}
