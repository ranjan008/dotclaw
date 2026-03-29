"""
DotClaw Mock API Server — DISCOM OT + Supply Chain + Finance
Simulates SCADA/OMS/MDMS, Supply Chain, and Finance endpoints for PoC testing.
"""

import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, abort, jsonify, request

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


# ===========================================================================
# DISCOM — SCADA, OMS, MDMS/AMI
# ===========================================================================

FEEDERS = {
    "FDR-001": {"load_mw": 14.2, "voltage_kv": 11.0, "power_factor": 0.93, "capacity_percent": 71.0, "status": "normal"},
    "FDR-002": {"load_mw": 18.7, "voltage_kv": 10.8, "power_factor": 0.91, "capacity_percent": 93.5, "status": "overload"},
    "FDR-003": {"load_mw": 12.1, "voltage_kv": 11.1, "power_factor": 0.95, "capacity_percent": 60.5, "status": "normal"},
    "FDR-004": {"load_mw": 17.4, "voltage_kv": 10.6, "power_factor": 0.89, "capacity_percent": 87.0, "status": "warning"},
    "FDR-005": {"load_mw": 9.8,  "voltage_kv": 11.2, "power_factor": 0.97, "capacity_percent": 49.0, "status": "normal"},
    "FDR-006": {"load_mw": 15.3, "voltage_kv": 10.3, "power_factor": 0.85, "capacity_percent": 76.5, "status": "degraded"},
    "FDR-007": {"load_mw": 11.6, "voltage_kv": 11.0, "power_factor": 0.92, "capacity_percent": 58.0, "status": "normal"},
    "FDR-008": {"load_mw": 13.9, "voltage_kv": 11.1, "power_factor": 0.94, "capacity_percent": 69.5, "status": "normal"},
    "FDR-009": {"load_mw": 16.8, "voltage_kv": 10.7, "power_factor": 0.90, "capacity_percent": 84.0, "status": "normal"},
    "FDR-010": {"load_mw": 8.4,  "voltage_kv": 11.3, "power_factor": 0.98, "capacity_percent": 42.0, "status": "normal"},
}

_now = datetime.utcnow()

OUTAGES = [
    {"zone": "Zone-A", "feeder_id": "FDR-002",
     "start_time": (_now - timedelta(hours=2, minutes=15)).isoformat() + "Z",
     "consumers_affected": 1240, "crew_status": "on_site", "outage_type": "unplanned",
     "fault_description": "HT cable fault near substation SS-12"},
    {"zone": "Zone-A", "feeder_id": "FDR-004",
     "start_time": (_now - timedelta(minutes=45)).isoformat() + "Z",
     "consumers_affected": 580, "crew_status": "dispatched", "outage_type": "unplanned",
     "fault_description": "Transformer oil leakage reported"},
    {"zone": "Zone-B", "feeder_id": "FDR-006",
     "start_time": (_now - timedelta(hours=5)).isoformat() + "Z",
     "consumers_affected": 2100, "crew_status": "work_in_progress", "outage_type": "planned",
     "fault_description": "Scheduled maintenance — conductor replacement"},
]


def _build_atc_data():
    base_date = datetime.utcnow().date()
    loss_series = [18.4, 19.1, 17.8, 20.3, 19.7, 21.2, 18.9]
    rows = []
    for i, loss in enumerate(loss_series):
        day = base_date - timedelta(days=(6 - i))
        inp = round(120.0 + i * 0.5, 2)
        rows.append({
            "date": day.isoformat(),
            "units_input_mu": inp,
            "units_billed_mu": round(inp * (1 - loss / 100), 2),
            "atc_loss_percent": loss,
            "top_loss_feeders": [
                {"feeder": "FDR-006", "loss_percent": round(loss + 3.2, 1)},
                {"feeder": "FDR-002", "loss_percent": round(loss + 1.8, 1)},
                {"feeder": "FDR-004", "loss_percent": round(loss + 0.9, 1)},
            ],
        })
    return rows


ATC_DATA = _build_atc_data()

ANOMALIES = [
    {"meter_id": "MTR-10011", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "tamper",       "days_since_last_read": 3},
    {"meter_id": "MTR-10012", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "zero_read",    "days_since_last_read": 7},
    {"meter_id": "MTR-10013", "dt_id": "DT-001", "sector": "commercial",  "anomaly_type": "comm_failure", "days_since_last_read": 2},
    {"meter_id": "MTR-10014", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "tamper",       "days_since_last_read": 5},
    {"meter_id": "MTR-10015", "dt_id": "DT-001", "sector": "residential", "anomaly_type": "zero_read",    "days_since_last_read": 14},
    {"meter_id": "MTR-20021", "dt_id": "DT-002", "sector": "industrial",  "anomaly_type": "comm_failure", "days_since_last_read": 1},
    {"meter_id": "MTR-20022", "dt_id": "DT-002", "sector": "residential", "anomaly_type": "tamper",       "days_since_last_read": 4},
    {"meter_id": "MTR-20023", "dt_id": "DT-002", "sector": "residential", "anomaly_type": "zero_read",    "days_since_last_read": 9},
    {"meter_id": "MTR-20024", "dt_id": "DT-002", "sector": "commercial",  "anomaly_type": "comm_failure", "days_since_last_read": 3},
    {"meter_id": "MTR-20025", "dt_id": "DT-002", "sector": "residential", "anomaly_type": "tamper",       "days_since_last_read": 6},
    {"meter_id": "MTR-30031", "dt_id": "DT-003", "sector": "residential", "anomaly_type": "comm_failure", "days_since_last_read": 2},
    {"meter_id": "MTR-30032", "dt_id": "DT-003", "sector": "residential", "anomaly_type": "zero_read",    "days_since_last_read": 11},
    {"meter_id": "MTR-30033", "dt_id": "DT-003", "sector": "commercial",  "anomaly_type": "tamper",       "days_since_last_read": 8},
    {"meter_id": "MTR-30034", "dt_id": "DT-003", "sector": "residential", "anomaly_type": "comm_failure", "days_since_last_read": 1},
]


@app.route("/scada/feeders/<feeder_id>/live")
@require_token
def scada_feeder_live(feeder_id):
    f = FEEDERS.get(feeder_id.upper())
    if not f:
        abort(404, description=f"Feeder {feeder_id} not found")
    return jsonify({**f, "feeder_id": feeder_id.upper(),
                    "timestamp": datetime.utcnow().isoformat() + "Z"})


@app.route("/oms/outages")
@require_token
def oms_outages():
    zf = request.args.get("zone")
    result = [o for o in OUTAGES if not zf or o["zone"].lower() == zf.lower()]
    return jsonify(result)


@app.route("/mdms/atc")
@require_token
def mdms_atc():
    days = min(int(request.args.get("days", 7)), 7)
    return jsonify(ATC_DATA[-days:])


@app.route("/mdms/meters/anomalies")
@require_token
def mdms_meter_anomalies():
    atype = request.args.get("type")
    result = [a for a in ANOMALIES if not atype or a["anomaly_type"] == atype]
    return jsonify(result)


# ===========================================================================
# SUPPLY CHAIN — PO, Inventory, Delivery, Vendor, Spend
# ===========================================================================

PURCHASE_ORDERS = {
    "PO-1001": {
        "vendor": "VND-0010", "vendor_name": "Reliance Materials Pvt Ltd",
        "plant": "PLANT-DEL", "category": "CAT-RAW", "items": 5,
        "value_lakh": 12.4, "status": "in_transit",
        "ordered_date": "2026-03-20", "expected_delivery": "2026-03-30",
        "actual_delivery": None, "delay_days": 0, "remarks": "On schedule",
    },
    "PO-1002": {
        "vendor": "VND-0011", "vendor_name": "SunTech Electronics",
        "plant": "PLANT-DEL", "category": "CAT-ELEC", "items": 3,
        "value_lakh": 8.7, "status": "delayed",
        "ordered_date": "2026-03-15", "expected_delivery": "2026-03-28",
        "actual_delivery": None, "delay_days": 1,
        "remarks": "Delayed — customs clearance at Chennai port",
    },
    "PO-1003": {
        "vendor": "VND-0010", "vendor_name": "Reliance Materials Pvt Ltd",
        "plant": "PLANT-NCR", "category": "CAT-RAW", "items": 8,
        "value_lakh": 22.1, "status": "delivered",
        "ordered_date": "2026-03-10", "expected_delivery": "2026-03-20",
        "actual_delivery": "2026-03-19", "delay_days": -1, "remarks": "Delivered 1 day early",
    },
    "PO-1004": {
        "vendor": "VND-0012", "vendor_name": "PackRight Solutions",
        "plant": "PLANT-DEL", "category": "CAT-PKG", "items": 12,
        "value_lakh": 5.3, "status": "delayed",
        "ordered_date": "2026-03-05", "expected_delivery": "2026-03-18",
        "actual_delivery": None, "delay_days": 11,
        "remarks": "Supplier capacity issue — escalated to regional head",
    },
    "PO-1005": {
        "vendor": "VND-0011", "vendor_name": "SunTech Electronics",
        "plant": "PLANT-NCR", "category": "CAT-RAW", "items": 6,
        "value_lakh": 15.8, "status": "pending_approval",
        "ordered_date": "2026-03-28", "expected_delivery": "2026-04-07",
        "actual_delivery": None, "delay_days": 0, "remarks": "Awaiting GM approval",
    },
}

INVENTORY = [
    {"sku": "SKU-MAT-001", "description": "Steel Rods 6mm",     "plant": "PLANT-DEL", "warehouse": "WH-DEL-01", "on_hand": 2400, "unit": "kg",  "reorder_level": 1000, "status": "ok"},
    {"sku": "SKU-MAT-002", "description": "Copper Wire 2.5mm",  "plant": "PLANT-DEL", "warehouse": "WH-DEL-01", "on_hand": 180,  "unit": "m",   "reorder_level": 500,  "status": "low"},
    {"sku": "SKU-ELE-001", "description": "Circuit Breaker 32A","plant": "PLANT-DEL", "warehouse": "WH-DEL-02", "on_hand": 45,   "unit": "pcs", "reorder_level": 50,   "status": "critical"},
    {"sku": "SKU-PKG-001", "description": "Corrugated Box L",   "plant": "PLANT-DEL", "warehouse": "WH-DEL-02", "on_hand": 8200, "unit": "pcs", "reorder_level": 2000, "status": "ok"},
    {"sku": "SKU-MAT-003", "description": "Aluminium Sheet 3mm","plant": "PLANT-NCR", "warehouse": "WH-NCR-01", "on_hand": 620,  "unit": "kg",  "reorder_level": 800,  "status": "low"},
    {"sku": "SKU-ELE-002", "description": "Transformer 25KVA",  "plant": "PLANT-NCR", "warehouse": "WH-NCR-01", "on_hand": 12,   "unit": "pcs", "reorder_level": 10,   "status": "ok"},
]

DELIVERIES = [
    {"shipment_id": "SHP-5001", "po_id": "PO-1001", "vendor": "VND-0010",
     "origin": "Mumbai", "destination": "PLANT-DEL",
     "dispatched": "2026-03-25", "eta": "2026-03-30",
     "status": "in_transit", "vehicle": "MH-04-AB-1234",
     "eway_bill": "EWB-220300012345", "delay_days": 0},
    {"shipment_id": "SHP-5002", "po_id": "PO-1002", "vendor": "VND-0011",
     "origin": "Chennai", "destination": "PLANT-DEL",
     "dispatched": "2026-03-22", "eta": "2026-03-28",
     "status": "delayed", "vehicle": "TN-09-CD-5678",
     "eway_bill": "EWB-220300012346", "delay_days": 1},
    {"shipment_id": "SHP-4998", "po_id": "PO-1003", "vendor": "VND-0010",
     "origin": "Pune", "destination": "PLANT-NCR",
     "dispatched": "2026-03-16", "eta": "2026-03-20",
     "status": "delivered", "vehicle": "MH-12-EF-9012",
     "eway_bill": "EWB-220300011901", "delay_days": -1},
    {"shipment_id": "SHP-5003", "po_id": "PO-1004", "vendor": "VND-0012",
     "origin": "Delhi", "destination": "PLANT-DEL",
     "dispatched": "2026-03-08", "eta": "2026-03-18",
     "status": "delayed", "vehicle": "DL-01-GH-3456",
     "eway_bill": "EWB-220300012100", "delay_days": 11},
]

VENDOR_PERF = {
    "VND-0010": {
        "name": "Reliance Materials Pvt Ltd", "category": "CAT-RAW",
        "orders_total": 28, "orders_on_time": 26,
        "otd_percent": 92.8, "quality_score": 4.4,
        "avg_delay_days": 0.3, "rating": "A",
        "remarks": "Preferred supplier — consistently high performance",
    },
    "VND-0011": {
        "name": "SunTech Electronics", "category": "CAT-ELEC",
        "orders_total": 15, "orders_on_time": 11,
        "otd_percent": 73.3, "quality_score": 3.6,
        "avg_delay_days": 2.1, "rating": "C",
        "remarks": "Logistics issues at Chennai port — under review",
    },
    "VND-0012": {
        "name": "PackRight Solutions", "category": "CAT-PKG",
        "orders_total": 22, "orders_on_time": 14,
        "otd_percent": 63.6, "quality_score": 3.2,
        "avg_delay_days": 4.8, "rating": "D",
        "remarks": "PIP initiated — capacity and quality concerns",
    },
}

SPEND_DATA = [
    {"plant": "PLANT-DEL", "category": "CAT-RAW",  "budget_lakh": 150.0, "actual_lakh": 138.4, "variance_lakh":  11.6, "po_count": 12},
    {"plant": "PLANT-DEL", "category": "CAT-ELEC", "budget_lakh":  80.0, "actual_lakh":  91.2, "variance_lakh": -11.2, "po_count":  7},
    {"plant": "PLANT-DEL", "category": "CAT-PKG",  "budget_lakh":  40.0, "actual_lakh":  38.7, "variance_lakh":   1.3, "po_count":  5},
    {"plant": "PLANT-NCR", "category": "CAT-RAW",  "budget_lakh": 120.0, "actual_lakh": 112.9, "variance_lakh":   7.1, "po_count":  9},
    {"plant": "PLANT-NCR", "category": "CAT-ELEC", "budget_lakh":  60.0, "actual_lakh":  58.3, "variance_lakh":   1.7, "po_count":  4},
]


@app.route("/sc/orders/<po_id>")
@require_token
def sc_po_status(po_id):
    po = PURCHASE_ORDERS.get(po_id.upper())
    if not po:
        abort(404, description=f"PO {po_id} not found")
    return jsonify({**po, "po_id": po_id.upper()})


@app.route("/sc/inventory")
@require_token
def sc_inventory():
    plant = request.args.get("plant", "").upper()
    warehouse = request.args.get("warehouse", "").upper()
    result = INVENTORY
    if plant:
        result = [i for i in result if i["plant"] == plant]
    if warehouse:
        result = [i for i in result if i["warehouse"] == warehouse]
    return jsonify(result)


@app.route("/sc/deliveries")
@require_token
def sc_deliveries():
    plant = request.args.get("plant", "").upper()
    vendor = request.args.get("vendor", "").upper()
    result = DELIVERIES
    if plant:
        result = [d for d in result if d["destination"] == plant]
    if vendor:
        result = [d for d in result if d["vendor"] == vendor]
    return jsonify(result)


@app.route("/sc/vendors/performance")
@require_token
def sc_vendor_performance():
    vendor = request.args.get("vendor", "").upper()
    if vendor:
        v = VENDOR_PERF.get(vendor)
        if not v:
            abort(404, description=f"Vendor {vendor} not found")
        return jsonify([{**v, "vendor_id": vendor}])
    return jsonify([{**v, "vendor_id": k} for k, v in VENDOR_PERF.items()])


@app.route("/sc/spend")
@require_token
def sc_spend():
    plant = request.args.get("plant", "").upper()
    category = request.args.get("category", "").upper()
    result = SPEND_DATA
    if plant:
        result = [s for s in result if s["plant"] == plant]
    if category:
        result = [s for s in result if s["category"] == category]
    return jsonify(result)


# ===========================================================================
# FINANCE — Accounts, Transactions, Loans, P&L, Compliance, Branch Perf
# ===========================================================================

BRANCH_ACCOUNTS = {
    "BR-MUM-001": {
        "branch_name": "Mumbai Main", "region": "West",
        "casa_accounts": 4820, "casa_balance_cr": 284.6,
        "fd_accounts": 1240, "fd_balance_cr": 892.3,
        "loan_accounts": 680, "loan_outstanding_cr": 1124.7,
        "npa_accounts": 18, "npa_cr": 22.4, "npa_percent": 1.99,
        "casa_ratio": 38.7,
    },
    "BR-MUM-002": {
        "branch_name": "Mumbai West", "region": "West",
        "casa_accounts": 2940, "casa_balance_cr": 156.2,
        "fd_accounts": 890, "fd_balance_cr": 612.1,
        "loan_accounts": 420, "loan_outstanding_cr": 684.3,
        "npa_accounts": 11, "npa_cr": 14.8, "npa_percent": 2.16,
        "casa_ratio": 34.2,
    },
    "BR-PUN-001": {
        "branch_name": "Pune CBD", "region": "West",
        "casa_accounts": 3180, "casa_balance_cr": 198.4,
        "fd_accounts": 1020, "fd_balance_cr": 748.6,
        "loan_accounts": 510, "loan_outstanding_cr": 830.2,
        "npa_accounts": 9, "npa_cr": 11.2, "npa_percent": 1.35,
        "casa_ratio": 42.1,
    },
}


def _build_txn_data():
    base = datetime.utcnow().date()
    rows = []
    branch_stats = {
        "BR-MUM-001": [(1240, 980, 48.2), (1380, 1120, 52.4), (1190, 940, 44.6),
                       (1520, 1240, 58.1), (1310, 1080, 50.2), (1420, 1150, 55.8), (1290, 1020, 49.7)],
        "BR-MUM-002": [(780, 620, 29.4), (840, 680, 32.1), (760, 600, 28.8),
                       (910, 740, 35.2), (830, 660, 31.5), (870, 700, 33.8), (800, 640, 30.9)],
        "BR-PUN-001": [(920, 740, 35.6), (980, 800, 38.2), (890, 710, 34.1),
                       (1060, 860, 41.4), (970, 780, 37.5), (1010, 820, 39.8), (940, 760, 36.7)],
    }
    for branch, daily in branch_stats.items():
        for i, (cr_count, dr_count, volume_cr) in enumerate(daily):
            rows.append({
                "branch": branch,
                "date": (base - timedelta(days=6 - i)).isoformat(),
                "credit_count": cr_count,
                "debit_count": dr_count,
                "total_volume_cr": volume_cr,
                "upi_count": int(cr_count * 0.42),
                "neft_rtgs_count": int(cr_count * 0.18),
                "cash_count": int(cr_count * 0.40),
            })
    return rows


TXN_DATA = _build_txn_data()

LOAN_DATA = {
    "BR-MUM-001": [
        {"product": "PROD-HL", "name": "Home Loan",      "accounts": 280, "outstanding_cr": 548.2, "npa_cr": 8.4, "npa_pct": 1.53, "avg_emi_delay_days": 1.2},
        {"product": "PROD-PL", "name": "Personal Loan",  "accounts": 240, "outstanding_cr": 384.1, "npa_cr": 9.8, "npa_pct": 2.55, "avg_emi_delay_days": 3.1},
        {"product": "PROD-SB", "name": "SME/Business",   "accounts": 160, "outstanding_cr": 192.4, "npa_cr": 4.2, "npa_pct": 2.18, "avg_emi_delay_days": 2.4},
    ],
    "BR-MUM-002": [
        {"product": "PROD-HL", "name": "Home Loan",      "accounts": 180, "outstanding_cr": 312.8, "npa_cr": 6.2, "npa_pct": 1.98, "avg_emi_delay_days": 1.8},
        {"product": "PROD-PL", "name": "Personal Loan",  "accounts": 160, "outstanding_cr": 248.6, "npa_cr": 6.9, "npa_pct": 2.77, "avg_emi_delay_days": 3.5},
        {"product": "PROD-SB", "name": "SME/Business",   "accounts":  80, "outstanding_cr": 122.9, "npa_cr": 1.7, "npa_pct": 1.38, "avg_emi_delay_days": 1.9},
    ],
    "BR-PUN-001": [
        {"product": "PROD-HL", "name": "Home Loan",      "accounts": 220, "outstanding_cr": 412.4, "npa_cr": 4.1, "npa_pct": 0.99, "avg_emi_delay_days": 0.8},
        {"product": "PROD-PL", "name": "Personal Loan",  "accounts": 190, "outstanding_cr": 284.2, "npa_cr": 5.2, "npa_pct": 1.83, "avg_emi_delay_days": 2.2},
        {"product": "PROD-SB", "name": "SME/Business",   "accounts": 100, "outstanding_cr": 133.6, "npa_cr": 1.9, "npa_pct": 1.42, "avg_emi_delay_days": 1.6},
    ],
}


def _build_pl_data():
    base = datetime.utcnow().date()
    rows = []
    branch_pl = {
        "BR-MUM-001": [(18.4, 11.2, 4.8, 2.4), (19.1, 11.6, 5.0, 2.5), (17.8, 10.9, 4.6, 2.3),
                       (20.3, 12.4, 5.2, 2.7), (19.6, 12.0, 5.1, 2.5), (21.1, 12.8, 5.4, 2.9), (18.9, 11.5, 4.9, 2.5)],
        "BR-MUM-002": [(11.2, 6.8, 2.9, 1.5), (11.8, 7.2, 3.1, 1.5), (10.9, 6.6, 2.8, 1.5),
                       (12.4, 7.6, 3.2, 1.6), (11.9, 7.3, 3.1, 1.5), (12.7, 7.8, 3.3, 1.6), (11.5, 7.0, 3.0, 1.5)],
        "BR-PUN-001": [(14.1, 8.6, 3.7, 1.8), (14.8, 9.0, 3.9, 1.9), (13.7, 8.4, 3.6, 1.7),
                       (15.6, 9.5, 4.1, 2.0), (15.0, 9.2, 3.9, 1.9), (15.9, 9.7, 4.2, 2.0), (14.4, 8.8, 3.8, 1.8)],
    }
    for branch, daily in branch_pl.items():
        for i, (revenue, expenses, nim, pat) in enumerate(daily):
            rows.append({
                "branch": branch,
                "date": (base - timedelta(days=6 - i)).isoformat(),
                "revenue_cr": revenue,
                "expenses_cr": expenses,
                "nim_cr": nim,
                "pat_cr": pat,
                "roa_percent": round(pat / (revenue * 12) * 100, 2),
            })
    return rows


PL_DATA = _build_pl_data()

COMPLIANCE_FLAGS = {
    "BR-MUM-001": [
        {"flag_id": "KYC-001", "type": "KYC_EXPIRY",     "account": "ACC-884421", "due_date": "2026-04-01", "severity": "high",   "remarks": "KYC due in 3 days"},
        {"flag_id": "KYC-002", "type": "KYC_EXPIRY",     "account": "ACC-773312", "due_date": "2026-04-15", "severity": "medium", "remarks": "KYC due in 17 days"},
        {"flag_id": "AML-001", "type": "SUSPICIOUS_TXN", "account": "ACC-991234", "due_date": "2026-03-29", "severity": "high",   "remarks": "3 cash deposits >2L in 7 days"},
        {"flag_id": "REG-001", "type": "CTR_PENDING",    "account": "ACC-556677", "due_date": "2026-03-30", "severity": "medium", "remarks": "CTR filing due tomorrow"},
    ],
    "BR-MUM-002": [
        {"flag_id": "KYC-003", "type": "KYC_EXPIRY",     "account": "ACC-221198", "due_date": "2026-04-05", "severity": "medium", "remarks": "KYC due in 7 days"},
        {"flag_id": "AML-002", "type": "SUSPICIOUS_TXN", "account": "ACC-334455", "due_date": "2026-03-29", "severity": "high",   "remarks": "Unusual cross-border transfer pattern"},
    ],
    "BR-PUN-001": [
        {"flag_id": "KYC-004", "type": "KYC_EXPIRY",     "account": "ACC-667788", "due_date": "2026-04-20", "severity": "low",    "remarks": "KYC due in 22 days"},
        {"flag_id": "REG-002", "type": "FORM_15G_PENDING","account": "ACC-778899", "due_date": "2026-03-31", "severity": "medium", "remarks": "Form 15G not submitted for FD renewal"},
    ],
}

BRANCH_TARGETS = {
    "BR-MUM-001": {
        "casa_target": 300.0,  "casa_actual": 284.6, "casa_pct": 94.9,
        "loan_target": 1200.0, "loan_actual": 1124.7,"loan_pct": 93.7,
        "npa_target_pct": 2.0, "npa_actual_pct": 1.99,
        "fee_income_target_cr": 22.0, "fee_income_actual_cr": 19.4, "fee_pct": 88.2,
        "new_accounts_target": 250, "new_accounts_actual": 218,
    },
    "BR-MUM-002": {
        "casa_target": 180.0,  "casa_actual": 156.2, "casa_pct": 86.8,
        "loan_target": 720.0,  "loan_actual": 684.3, "loan_pct": 95.0,
        "npa_target_pct": 2.0, "npa_actual_pct": 2.16,
        "fee_income_target_cr": 14.0, "fee_income_actual_cr": 11.8, "fee_pct": 84.3,
        "new_accounts_target": 150, "new_accounts_actual": 124,
    },
    "BR-PUN-001": {
        "casa_target": 210.0,  "casa_actual": 198.4, "casa_pct": 94.5,
        "loan_target": 880.0,  "loan_actual": 830.2, "loan_pct": 94.3,
        "npa_target_pct": 1.5, "npa_actual_pct": 1.35,
        "fee_income_target_cr": 16.0, "fee_income_actual_cr": 15.1, "fee_pct": 94.4,
        "new_accounts_target": 180, "new_accounts_actual": 172,
    },
}


@app.route("/fin/accounts/summary")
@require_token
def fin_accounts_summary():
    branch = request.args.get("branch", "").upper()
    if branch:
        b = BRANCH_ACCOUNTS.get(branch)
        if not b:
            abort(404, description=f"Branch {branch} not found")
        return jsonify([{**b, "branch_id": branch}])
    return jsonify([{**v, "branch_id": k} for k, v in BRANCH_ACCOUNTS.items()])


@app.route("/fin/transactions")
@require_token
def fin_transactions():
    branch = request.args.get("branch", "").upper()
    days = min(int(request.args.get("days", 7)), 7)
    result = TXN_DATA
    if branch:
        result = [t for t in result if t["branch"] == branch]
    return jsonify(result[-days * (3 if not branch else 1):])


@app.route("/fin/loans")
@require_token
def fin_loans():
    branch = request.args.get("branch", "").upper()
    product = request.args.get("product", "").upper()
    if branch:
        loans = LOAN_DATA.get(branch, [])
        if product:
            loans = [l for l in loans if l["product"] == product]
        return jsonify(loans)
    all_loans = []
    for b, loans in LOAN_DATA.items():
        for l in loans:
            all_loans.append({**l, "branch": b})
    return jsonify(all_loans)


@app.route("/fin/pl")
@require_token
def fin_pl():
    branch = request.args.get("branch", "").upper()
    days = min(int(request.args.get("days", 7)), 7)
    result = PL_DATA
    if branch:
        result = [r for r in result if r["branch"] == branch]
    return jsonify(result[-days * (3 if not branch else 1):])


@app.route("/fin/compliance")
@require_token
def fin_compliance():
    branch = request.args.get("branch", "").upper()
    severity = request.args.get("severity", "").lower()
    if branch:
        flags = COMPLIANCE_FLAGS.get(branch, [])
    else:
        flags = [f for v in COMPLIANCE_FLAGS.values() for f in v]
    if severity:
        flags = [f for f in flags if f["severity"] == severity]
    return jsonify(flags)


@app.route("/fin/branches/performance")
@require_token
def fin_branch_performance():
    branch = request.args.get("branch", "").upper()
    if branch:
        t = BRANCH_TARGETS.get(branch)
        if not t:
            abort(404, description=f"Branch {branch} not found")
        acc = BRANCH_ACCOUNTS.get(branch, {})
        return jsonify([{**t, **acc, "branch_id": branch}])
    result = []
    for b, t in BRANCH_TARGETS.items():
        result.append({**t, **BRANCH_ACCOUNTS.get(b, {}), "branch_id": b})
    return jsonify(result)


# ===========================================================================
# Error handlers
# ===========================================================================

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Unauthorized", "message": str(e.description)}), 401


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found", "message": str(e.description)}), 404


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    port = int(os.environ.get("OT_API_PORT", 5000))
    print(f"Starting DotClaw Mock API Server on port {port} ...")
    print("  DISCOM : /scada, /oms, /mdms")
    print("  SC     : /sc/orders, /sc/inventory, /sc/deliveries, /sc/vendors, /sc/spend")
    print("  Finance: /fin/accounts, /fin/transactions, /fin/loans, /fin/pl, /fin/compliance, /fin/branches")
    app.run(host="0.0.0.0", port=port, debug=False)
