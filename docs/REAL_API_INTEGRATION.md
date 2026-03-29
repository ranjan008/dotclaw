# Connecting Skills to Real Systems

## How it works today (PoC)

Every skill script calls the local Mock API:

```
Skill script  →  http://localhost:5000/<domain>/<endpoint>  (mock)
                 Bearer: OT-POC-TOKEN-2026
```

Two things control this:
```bash
# .env
OT_API_BASE=http://localhost:5000
OT_API_TOKEN=OT-POC-TOKEN-2026
```

**To connect to a real system, you change only these two lines (and add any
auth-specific variables). The skill script itself does not change.**

---

## Integration Patterns

### 1. REST API (most common — OMS, MDMS, SAP, ERP, modern SaaS)

The existing skill code already uses this pattern. Replace the mock URL and token.

```bash
# .env — pointing to a real OMS REST API
OT_API_BASE=https://oms.yourdiscom.in/api/v2
OT_API_TOKEN=<api-key-from-oms-vendor>
```

If the real API uses a different auth header format, update the header in the skill's
`fetch_*` function:

```python
# Current (Bearer token)
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# API key in custom header (some vendors)
headers = {"X-API-Key": API_TOKEN}

# Basic auth
import base64
creds = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
headers = {"Authorization": f"Basic {creds}"}
```

**Real-world examples:**

| System | Vendor | Typical Auth | Base URL pattern |
|--------|--------|-------------|-----------------|
| OMS | Oracle Utilities NMS | OAuth2 Bearer | `https://<host>/nms/api/v1` |
| MDMS | Itron OpenWay | API Key | `https://<host>/mdms/rest/v2` |
| ERP | SAP IS-U | SAP OAuth2 / Basic | `https://<host>/sap/opu/odata/sap/` |
| Supply Chain | SAP Ariba | OAuth2 | `https://openapi.ariba.com/api/` |
| Core Banking | Finacle / Temenos | API Key + HMAC | `https://<host>/cbs/api/v1` |
| Compliance | CERSAI / RBI APIs | Client cert (mTLS) | `https://cersai.org.in/api/` |

---

### 2. OAuth2 (SAP, Microsoft, Salesforce, modern banking APIs)

When the real system requires OAuth2 client credentials flow:

```python
# rbac/integrations/oauth_client.py  (new helper — create once, reuse across skills)
import os, requests

TOKEN_URL    = os.getenv("OAUTH_TOKEN_URL")
CLIENT_ID    = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET= os.getenv("OAUTH_CLIENT_SECRET")
SCOPE        = os.getenv("OAUTH_SCOPE", "")

_token_cache = {"token": None, "expires_at": 0}

def get_token() -> str:
    import time
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]
    r = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
    })
    r.raise_for_status()
    data = r.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["token"]
```

In the skill script, replace:
```python
# Before
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# After
from rbac.integrations.oauth_client import get_token
headers = {"Authorization": f"Bearer {get_token()}"}
```

```bash
# .env
OAUTH_TOKEN_URL=https://auth.yoursystem.com/oauth/token
OAUTH_CLIENT_ID=dotclaw-integration
OAUTH_CLIENT_SECRET=<secret>
OAUTH_SCOPE=supply_chain.read
```

---

### 3. SOAP / WSDL (legacy ERP, some core banking, SLDC)

When the vendor exposes a SOAP web service instead of REST:

```bash
pip install zeep   # add to requirements.txt
```

```python
# Replacing a REST fetch_* function with SOAP
from zeep import Client

WSDL_URL  = os.getenv("SOAP_WSDL_URL")
SOAP_USER = os.getenv("SOAP_USER")
SOAP_PASS = os.getenv("SOAP_PASSWORD")

def fetch_po_soap(po_id: str) -> dict:
    client = Client(WSDL_URL)
    # Pass credentials via SOAP header or transport
    from zeep.transports import Transport
    from requests import Session
    session = Session()
    session.auth = (SOAP_USER, SOAP_PASS)
    client = Client(WSDL_URL, transport=Transport(session=session))

    result = client.service.GetPurchaseOrder(PONumber=po_id)
    # Map SOAP response fields to the dict shape your print_report() expects
    return {
        "po_id":    result.PONumber,
        "status":   result.Status.lower(),
        "vendor":   result.VendorCode,
        "plant":    result.PlantCode,
        "value_lakh": float(result.TotalValue) / 100000,
        ...
    }
```

**The print_report() function never changes** — only the fetch function changes to
call SOAP instead of REST. This is why fetch and print are separated in every skill.

---

### 4. Direct Database Connection (custom in-house systems)

When the source system has no API but exposes a database:

```bash
pip install sqlalchemy psycopg2-binary  # for PostgreSQL
pip install sqlalchemy cx_Oracle        # for Oracle (SAP)
pip install sqlalchemy pyodbc           # for SQL Server
```

```python
# skills/inventory/scripts/fetch_inventory.py — DB version
import os
from sqlalchemy import create_engine, text

DB_URL = os.getenv("INVENTORY_DB_URL")  # e.g. oracle+cx_oracle://user:pass@host:1521/SID
_engine = create_engine(DB_URL, pool_pre_ping=True)

def fetch_inventory(plant=None, warehouse=None):
    query = """
        SELECT item_code AS sku, description, plant_code AS plant,
               whse_code AS warehouse, qty_on_hand AS on_hand,
               uom AS unit, reorder_qty AS reorder_level,
               CASE WHEN qty_on_hand = 0 THEN 'critical'
                    WHEN qty_on_hand < reorder_qty * 0.5 THEN 'low'
                    ELSE 'ok' END AS status
        FROM inventory_master
        WHERE active_flag = 'Y'
    """
    params = {}
    if plant:     query += " AND plant_code = :plant";     params["plant"]     = plant
    if warehouse: query += " AND whse_code  = :warehouse"; params["warehouse"] = warehouse

    with _engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]
```

```bash
# .env
INVENTORY_DB_URL=oracle+cx_oracle://inv_reader:password@erp.company.in:1521/PROD
```

---

### 5. File / SFTP Batch (legacy MDMS, government portals, SLDC reports)

When the source system drops CSV/Excel files on an SFTP server periodically:

```python
# skills/atc-analytics/scripts/fetch_atc.py — file-based version
import os, paramiko, csv, io
from datetime import date, timedelta

SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASSWORD")
SFTP_PATH = os.getenv("SFTP_ATC_PATH", "/exports/atc/")

def fetch_atc(days: int) -> list:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SFTP_HOST, username=SFTP_USER, password=SFTP_PASS)
    sftp = ssh.open_sftp()

    rows = []
    for i in range(days):
        day = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        remote_file = f"{SFTP_PATH}atc_{day}.csv"
        try:
            with sftp.open(remote_file) as f:
                reader = csv.DictReader(io.TextIOWrapper(f))
                for row in reader:
                    rows.append({
                        "date": row["Date"],
                        "units_input_mu":  float(row["InputMU"]),
                        "units_billed_mu": float(row["BilledMU"]),
                        "atc_loss_percent":float(row["ATCLoss%"]),
                        "top_loss_feeders": [],  # may need a separate file
                    })
        except FileNotFoundError:
            pass  # file not yet available for this date
    sftp.close(); ssh.close()
    return rows
```

---

### 6. Message Queue / Event Stream (Kafka, RabbitMQ — real-time OT data)

For real-time SCADA data where polling is too slow:

```python
# skills/scada-feeder/scripts/fetch_feeder.py — Kafka consumer version
import os
from kafka import KafkaConsumer
import json

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
KAFKA_TOPIC   = os.getenv("KAFKA_SCADA_TOPIC", "scada.feeders.live")
KAFKA_GROUP   = os.getenv("KAFKA_GROUP_ID", "dotclaw-scada")

def fetch_feeder(feeder_id: str) -> dict:
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKERS.split(","),
        group_id=KAFKA_GROUP,
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode()),
        consumer_timeout_ms=5000,  # 5s timeout
    )
    latest = None
    for msg in consumer:
        if msg.value.get("feeder_id") == feeder_id.upper():
            latest = msg.value
            break
    consumer.close()
    if not latest:
        raise ValueError(f"No recent data for feeder {feeder_id}")
    return latest
```

---

## Per-Domain: What to Replace

### DISCOM

| Skill | Mock endpoint | Real system | Auth type |
|-------|--------------|-------------|-----------|
| `scada-feeder` | `GET /scada/feeders/<id>/live` | SCADA Historian OPC-UA → REST adapter | Bearer / API Key |
| `outage-status` | `GET /oms/outages` | Oracle NMS / Milsoft REST API | OAuth2 |
| `atc-analytics` | `GET /mdms/atc` | Itron / C-DAC MDMS REST API | API Key |
| `ami-meters` | `GET /mdms/meters/anomalies` | AMI head-end system REST API | API Key |

```bash
# .env additions for DISCOM production
OT_API_BASE=https://scada-adapter.yourdiscom.in    # OT adapter service (internal)
OT_API_TOKEN=<rotating-api-key>
OMS_API_BASE=https://oms.yourdiscom.in/api/v1
OMS_API_TOKEN=<oms-api-key>
MDMS_API_BASE=https://mdms.yourdiscom.in/api/v2
MDMS_API_TOKEN=<mdms-api-key>
```

Each skill reads its own `*_API_BASE` variable — skills can point to different backends.

---

### Supply Chain

| Skill | Real system examples | Typical API |
|-------|---------------------|------------|
| `po-status` | SAP Ariba, Oracle Procurement | SAP Ariba REST, SAP OData |
| `inventory` | SAP MM, Oracle WMS, Infor | SAP OData / REST |
| `delivery-tracking` | FedEx/Delhivery APIs, SAP TM | REST + webhook |
| `vendor-performance` | SAP SRM, Jaggaer | REST |
| `spend-analytics` | SAP BW/Analytics, Coupa | REST / OData |

For SAP specifically — SAP exposes OData services. Example:
```python
# SAP OData — fetch inventory
import requests, os
SAP_BASE = os.getenv("SAP_ODATA_BASE")  # e.g. https://sap.company.in/sap/opu/odata/sap
SAP_USER = os.getenv("SAP_USER")
SAP_PASS = os.getenv("SAP_PASSWORD")

def fetch_inventory_sap(plant):
    url = f"{SAP_BASE}/MM_INVENTORY_SRV/InventorySet?$filter=Plant eq '{plant}'&$format=json"
    r = requests.get(url, auth=(SAP_USER, SAP_PASS), timeout=15)
    r.raise_for_status()
    items = r.json()["d"]["results"]
    # Map SAP field names to DotClaw field names
    return [{
        "sku":           i["MaterialNumber"],
        "description":   i["MaterialDescription"],
        "plant":         i["Plant"],
        "warehouse":     i["StorageLocation"],
        "on_hand":       float(i["UnrestrictedStock"]),
        "unit":          i["BaseUnit"],
        "reorder_level": float(i.get("ReorderPoint", 0)),
        "status":        "critical" if float(i["UnrestrictedStock"]) == 0
                         else "low" if float(i["UnrestrictedStock"]) < float(i.get("ReorderPoint",0))
                         else "ok",
    } for i in items]
```

---

### Finance

| Skill | Real system examples | Typical API / Protocol |
|-------|---------------------|----------------------|
| `account-summary` | Finacle, Temenos T24, Mambu | REST / SOAP |
| `transaction-report` | CBS, Data warehouse | REST / JDBC |
| `loan-status` | LOS (LoanPro, nCino, custom) | REST |
| `pl-report` | BI / Hyperion, SAP BPC | REST / OData |
| `compliance-report` | KYC/AML engine (NICE Actimize, Oracle FCCM) | REST |
| `branch-performance` | MIS / BI platform | REST / file export |

For RBI-mandated APIs and government portals, client certificates (mTLS) are common:
```python
import requests, os
CERT_FILE = os.getenv("CLIENT_CERT_PATH")   # path to .pem file
KEY_FILE  = os.getenv("CLIENT_KEY_PATH")    # path to private key

r = requests.get(url, cert=(CERT_FILE, KEY_FILE), timeout=15)
```

---

## Environment Variable Strategy for Multiple Backends

Rather than one `OT_API_BASE` for everything, use per-skill or per-domain vars:

```bash
# .env — production with real systems

# DISCOM OT
SCADA_API_BASE=https://scada-adapter.internal/api
SCADA_API_TOKEN=<token>
OMS_API_BASE=https://oms.internal/api/v1
OMS_API_TOKEN=<token>
MDMS_API_BASE=https://mdms.internal/api/v2
MDMS_API_TOKEN=<token>

# Supply Chain
SC_API_BASE=https://sap-gateway.internal/sc/api
SAP_USER=sc_svc_dotclaw
SAP_PASSWORD=<password>

# Finance
CBS_API_BASE=https://finacle.internal/api/v1
CBS_API_TOKEN=<token>
AML_API_BASE=https://actimize.internal/api
AML_API_TOKEN=<token>

# Secrets should be stored in HashiCorp Vault or AWS Secrets Manager
# and injected as env vars at container startup — never commit real credentials
```

In each skill's `fetch_*` function, read the domain-specific variable:
```python
# scada-feeder
API_BASE = os.getenv("SCADA_API_BASE", os.getenv("OT_API_BASE", "http://localhost:5000"))

# po-status
API_BASE = os.getenv("SC_API_BASE", os.getenv("OT_API_BASE", "http://localhost:5000"))
```

The `OT_API_BASE` fallback keeps the PoC mock working during development.

---

## Summary: What changes vs what stays the same

| Component | Change needed for real system | Stays the same |
|-----------|------------------------------|---------------|
| `.env` | API base URL + credentials | — |
| `fetch_*()` in skill | URL, auth header, response field mapping | Function signature |
| `print_report()` in skill | Nothing | Entire function |
| SKILL.md | Nothing | Entire file |
| RBAC gateway | Nothing | Entire file |
| Domain YAML | Nothing | Entire file |
| Skill scope flags (`--allowed-*`) | Nothing | Entire mechanism |

The integration boundary is **always inside the `fetch_*` function**. Everything
above it (RBAC, Claude agent, skill detection) and everything below it
(output formatting, scope filtering) is untouched.
