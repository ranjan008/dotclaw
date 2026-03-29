"""
rbac_gateway.py — RBAC-enforcing gateway for DotClaw DISCOM Intelligence.

Sits between the WhatsApp Business API webhook and the OpenClaw agent.

                     WhatsApp Business API
                            │
                            │  POST /wa/webhook  (port 8080)
                            ▼
                     rbac_gateway.py  ◄── this file
                    /              \
             DENIED                ALLOWED
                │                     │
       reply sent back          enrich message
       to user on WA            (inject RBAC ctx)
                                      │
                                      ▼
                            OpenClaw  POST /hooks/agent
                            (port 18789)
                                      │
                                      ▼
                            Claude agent + skills

Inbound webhook format (Meta WhatsApp Business API v18+):
  POST /wa/webhook
  X-Hub-Signature-256: sha256=<hmac>   ← verified if WHATSAPP_APP_SECRET is set
  {
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "919XXXXXXXXX",
            "text": {"body": "..."},
            "type": "text"
          }],
          "metadata": {"phone_number_id": "..."}
        }
      }]
    }]
  }

For local testing, a simplified payload is also accepted:
  POST /wa/webhook
  X-Gateway-Token: <RBAC_GATEWAY_TOKEN>
  { "from": "+919XXXXXXXXX", "message": "What is the load on FDR-002?" }
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add project root to path so rbac package is importable
sys.path.insert(0, os.path.dirname(__file__))

from rbac.admin_commands import handle as handle_admin, is_admin_command
from rbac.db import init_db
from rbac.middleware import enforce
from rbac.user_registry import get_user

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

RBAC_GATEWAY_TOKEN  = os.getenv("RBAC_GATEWAY_TOKEN", "RBAC-GW-TOKEN-2026")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")   # set in prod
WA_VERIFY_TOKEN     = os.getenv("WA_VERIFY_TOKEN", "dotclaw-verify-2026")

OPENCLAW_WEBHOOK_URL   = os.getenv("OPENCLAW_WEBHOOK_URL",   "http://localhost:18789/hooks/agent")
OPENCLAW_WEBHOOK_TOKEN = os.getenv("OPENCLAW_WEBHOOK_TOKEN", "WEBHOOK-SECRET-2026")
OPENCLAW_AGENT_ID      = os.getenv("OPENCLAW_AGENT_ID",      "discom-ot-agent")

GATEWAY_PORT = int(os.getenv("RBAC_GATEWAY_PORT", 8080))

# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rbac_gateway")

app = Flask(__name__)
init_db()


# --------------------------------------------------------------------------- #
# Signature verification (Meta HMAC-SHA256)
# --------------------------------------------------------------------------- #

def _verify_meta_signature(payload: bytes, signature_header: str) -> bool:
    if not WHATSAPP_APP_SECRET:
        return True  # skip in dev / when secret not configured
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        WHATSAPP_APP_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _forward_to_openclaw(enriched_message: str, wa_from: str) -> bool:
    """POST the enriched message to the OpenClaw agent webhook."""
    payload = {
        "message":  enriched_message,
        "agentId":  OPENCLAW_AGENT_ID,
        "wakeMode": "now",
        "deliver":  True,
        "metadata": {"wa_from": wa_from},
    }
    headers = {
        "Content-Type":    "application/json",
        "x-openclaw-token": OPENCLAW_WEBHOOK_TOKEN,
    }
    try:
        resp = requests.post(OPENCLAW_WEBHOOK_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        log.info("Forwarded to OpenClaw — status %s", resp.status_code)
        return True
    except Exception as exc:
        log.error("Failed to forward to OpenClaw: %s", exc)
        return False


def _send_wa_reply(to: str, text: str) -> None:
    """
    Send a reply back to the user on WhatsApp.

    In production this calls the Meta Graph API.
    In dev/PoC it just logs the reply (no WA credentials needed).
    """
    wa_token       = os.getenv("WHATSAPP_API_TOKEN", "")
    phone_num_id   = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    if wa_token and phone_num_id:
        url = f"https://graph.facebook.com/v18.0/{phone_num_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "text",
            "text": {"body": text},
        }
        try:
            requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {wa_token}"},
                timeout=10,
            )
        except Exception as exc:
            log.error("WA reply failed: %s", exc)
    else:
        log.info("[WA REPLY → %s]\n%s", to, text)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/wa/webhook")
def wa_verify():
    """Meta webhook verification challenge."""
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WA_VERIFY_TOKEN:
        log.info("WhatsApp webhook verified.")
        return challenge, 200
    return "Forbidden", 403


@app.post("/wa/webhook")
def wa_webhook():
    """
    Receive WhatsApp messages from Meta or a local test client.

    Accepts two formats:
      1. Full Meta Business API payload  (object = "whatsapp_business_account")
      2. Simplified test payload         ({ "from": "...", "message": "..." })
    """
    # --- signature check (Meta) ---
    sig = request.headers.get("X-Hub-Signature-256", "")
    if WHATSAPP_APP_SECRET and not _verify_meta_signature(request.data, sig):
        log.warning("Invalid Meta signature — request rejected")
        return jsonify({"error": "invalid signature"}), 403

    # --- simple token check (dev / non-Meta clients) ---
    if not WHATSAPP_APP_SECRET:
        token = request.headers.get("X-Gateway-Token", "")
        if token != RBAC_GATEWAY_TOKEN:
            return jsonify({"error": "unauthorised"}), 401

    body = request.get_json(silent=True) or {}

    # ---- extract (wa_from, message_text) from either format ----------------
    wa_from = None
    message_text = None

    if body.get("object") == "whatsapp_business_account":
        # Meta production format
        try:
            entry   = body["entry"][0]
            change  = entry["changes"][0]["value"]
            msg     = change["messages"][0]
            if msg.get("type") != "text":
                return jsonify({"status": "ignored", "reason": "non-text message"}), 200
            wa_from      = "+" + msg["from"]
            message_text = msg["text"]["body"].strip()
        except (KeyError, IndexError):
            return jsonify({"status": "ignored", "reason": "unrecognised payload shape"}), 200
    else:
        # Simplified test / simulation format
        wa_from      = body.get("from", "")
        message_text = body.get("message", "").strip()

    if not wa_from or not message_text:
        return jsonify({"error": "missing 'from' or 'message'"}), 400

    log.info("Incoming message from %s: %s", wa_from, message_text[:80])

    # ---- admin command? (it_admin role only) --------------------------------
    user = get_user(wa_from)
    if user and user.get("role") == "it_admin" and is_admin_command(message_text):
        reply = handle_admin(message_text, admin_wa=wa_from)
        _send_wa_reply(wa_from, reply)
        return jsonify({"status": "admin_command_handled"}), 200

    # ---- RBAC enforcement ---------------------------------------------------
    result = enforce(wa_from, message_text)

    if not result["allowed"]:
        _send_wa_reply(wa_from, result["reply"])
        return jsonify({"status": "denied"}), 200

    # ---- forward enriched message to OpenClaw ------------------------------
    ok = _forward_to_openclaw(result["enriched_message"], wa_from)
    if not ok:
        _send_wa_reply(wa_from, "Service temporarily unavailable. Please try again in a moment.")
        return jsonify({"status": "forwarding_failed"}), 502

    return jsonify({"status": "forwarded"}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "rbac_gateway"}), 200


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    log.info("DotClaw RBAC Gateway starting on port %s", GATEWAY_PORT)
    app.run(host="0.0.0.0", port=GATEWAY_PORT, debug=False)
