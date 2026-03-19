"""
DISCOM OT Intelligence POC — Mock OT API Server
Simulates SCADA, OMS, and MDMS/AMI endpoints for testing.
"""

import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
VALID_TOKEN = "OT-POC-TOKEN-2026"


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {VALID_TOKEN}":
            abort(401, description="Invalid or missing Bearer token")
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# SCADA — Feeder live data (10 feeders)
# ---------------------------------------------------------------------------
FEEDERS = {
    "FDR-001": {"load_mw": 14.2, "voltage_kv": 11.0, "power_factor": 0.93, "capacity_percent": 71.0, "status": "normal"},
    "FDR-002": {"load_mw": 18.7, "voltage_kv": 10.8, "power_factor": 0.91, "capacity_percent": 93.5, "status": "overload"},   # >85%
    "FDR-003": {"load_mw": 12.1, "voltage_kv": 11.1, "power_factor": 0.95, "capacity_percent": 60.5, "status": "normal"},
    "FDR-004": {"load_mw": 17.4, "voltage_kv": 10.6, "power_factor": 0.89, "capacity_percent": 87.0, "status": "warning"},   # >85%
    "FDR-005": {"load_mw": 9.8,  "voltage_kv": 11.2, "power_factor": 0.97, "capacity_percent": 49.0, "status": "normal"},
    "FDR-006": {"load_mw": 15.3, "voltage_kv": 10.3, "power_factor": 0.85, "capacity_percent": 76.5, "status": "degraded"},  # degraded
    "FDR-007": {"load_mw": 11.6, "voltage_kv": 11.0, "power_factor": 0.92, "capacity_percent": 58.0, "status": "normal"},
    "FDR-008": {"load_mw": 13.9, "voltage_kv": 11.1, "power_factor": 0.94, "capacity_percent": 69.5, "status": "normal"},
    "FDR-009": {"load_mw": 16.8, "voltage_kv": 10.7, "power_factor": 0.90, "capacity_percent": 84.0, "status": "normal"},
    "FDR-010": {"load_mw": 8.4,  "voltage_kv": 11.3, "power_factor": 0.98, "capacity_percent": 42.0, "status": "normal"},
}


@app.route("/scada/feeders/<feeder_id>/live", methods=["GET"])
@require_token
def scada_feeder_live(feeder_id):
    feeder = FEEDERS.get(feeder_id.upper())
    if not feeder:
        abort(404, description=f"Feeder {feeder_id} not found")
    return jsonify({
        "feeder_id": feeder_id.upper(),
        "load_mw": feeder["load_mw"],
        "voltage_kv": feeder["voltage_kv"],
        "power_factor": feeder["power_factor"],
        "capacity_percent": feeder["capacity_percent"],
        "status": feeder["status"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ---------------------------------------------------------------------------
# OMS — Active outages (3 outages, 2 zones)
# ---------------------------------------------------------------------------
_now = datetime.utcnow()

OUTAGES = [
    {
        "zone": "Zone-A",
        "feeder_id": "FDR-002",
        "start_time": (_now - timedelta(hours=2, minutes=15)).isoformat() + "Z",
        "consumers_affected": 1240,
        "crew_status": "on_site",
        "outage_type": "unplanned",
        "fault_description": "HT cable fault near substation SS-12",
    },
    {
        "zone": "Zone-A",
        "feeder_id": "FDR-004",
        "start_time": (_now - timedelta(hours=0, minutes=45)).isoformat() + "Z",
        "consumers_affected": 580,
        "crew_status": "dispatched",
        "outage_type": "unplanned",
        "fault_description": "Transformer oil leakage reported",
    },
    {
        "zone": "Zone-B",
        "feeder_id": "FDR-006",
        "start_time": (_now - timedelta(hours=5, minutes=0)).isoformat() + "Z",
        "consumers_affected": 2100,
        "crew_status": "work_in_progress",
        "outage_type": "planned",
        "fault_description": "Scheduled maintenance — conductor replacement",
    },
]


@app.route("/oms/outages", methods=["GET"])
@require_token
def oms_outages():
    zone_filter = request.args.get("zone")
    result = OUTAGES
    if zone_filter:
        result = [o for o in OUTAGES if o["zone"].lower() == zone_filter.lower()]
    return jsonify(result)


# ---------------------------------------------------------------------------
# MDMS — AT&C loss data (7 days)
# ---------------------------------------------------------------------------
def _build_atc_data():
    base_date = datetime.utcnow().date()
    rows = []
    loss_series = [18.4, 19.1, 17.8, 20.3, 19.7, 21.2, 18.9]
    for i, loss in enumerate(loss_series):
        day = base_date - timedelta(days=(6 - i))
        units_input = round(120.0 + i * 0.5, 2)
        units_billed = round(units_input * (1 - loss / 100), 2)
        rows.append({
            "date": day.isoformat(),
            "units_input_mu": units_input,
            "units_billed_mu": units_billed,
            "atc_loss_percent": loss,
            "top_loss_feeders": [
                {"feeder": "FDR-006", "loss_percent": round(loss + 3.2, 1)},
                {"feeder": "FDR-002", "loss_percent": round(loss + 1.8, 1)},
                {"feeder": "FDR-004", "loss_percent": round(loss + 0.9, 1)},
            ],
        })
    return rows


ATC_DATA = _build_atc_data()


@app.route("/mdms/atc", methods=["GET"])
@require_token
def mdms_atc():
    days = int(request.args.get("days", 7))
    days = min(days, 7)
    return jsonify(ATC_DATA[-days:])


# ---------------------------------------------------------------------------
# MDMS/AMI — Meter anomalies (14 anomalies, 3 DT clusters)
# ---------------------------------------------------------------------------
ANOMALIES = [
    # DT-001 cluster
    {"meter_id": "MTR-10011", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "tamper",         "days_since_last_read": 3},
    {"meter_id": "MTR-10012", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "zero_read",      "days_since_last_read": 7},
    {"meter_id": "MTR-10013", "dt_id": "DT-001", "sector": "commercial",  "anomaly_type": "comm_failure",   "days_since_last_read": 2},
    {"meter_id": "MTR-10014", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "tamper",         "days_since_last_read": 5},
    {"meter_id": "MTR-10015", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "zero_read",      "days_since_last_read": 14},
    # DT-002 cluster
    {"meter_id": "MTR-20021", "dt_id": "DT-002", "sector": "industrial",  "anomaly_type": "comm_failure",   "days_since_last_read": 1},
    {"meter_id": "MTR-20022", "dt_id": "DT-002", "sector": "residential", "anomaly_type": "tamper",         "days_since_last_read": 4},
    {"meter_id": "MTR-20023", "dt_id": "DT-002", "sector": "residential", "anomaly_type": "zero_read",      "days_since_last_read": 9},
    {"meter_id": "MTR-20024", "dt_id": "DT-002", "sector": "commercial",  "anomaly_type": "comm_failure",   "days_since_last_read": 3},
    {"meter_id": "MTR-20025", "dt_id": "DT-002", "sector": "residential", "anomaly_type": "tamper",         "days_since_last_read": 6},
    # DT-003 cluster
    {"meter_id": "MTR-30031", "dt_id": "DT-003", "sector": "residential", "anomaly_type": "comm_failure",   "days_since_last_read": 2},
    {"meter_id": "MTR-30032", "dt_id": "DT-003", "sector": "residential", "anomaly_type": "zero_read",      "days_since_last_read": 11},
    {"meter_id": "MTR-30033", "dt_id": "DT-003", "sector": "commercial",  "anomaly_type": "tamper",         "days_since_last_read": 8},
    {"meter_id": "MTR-30034", "dt_id": "DT-003", "sector": "residential", "anomaly_type": "comm_failure",   "days_since_last_read": 1},
]


@app.route("/mdms/meters/anomalies", methods=["GET"])
@require_token
def mdms_meter_anomalies():
    anomaly_type = request.args.get("type")
    result = ANOMALIES
    if anomaly_type:
        result = [a for a in ANOMALIES if a["anomaly_type"] == anomaly_type]
    return jsonify(result)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Unauthorized", "message": str(e.description)}), 401


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found", "message": str(e.description)}), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("OT_API_PORT", 5000))
    print(f"Starting Mock OT API Server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
