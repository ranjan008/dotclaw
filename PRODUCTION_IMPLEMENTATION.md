# Production Implementation Guide — DotClaw DISCOM Intelligence Platform

## Overview

This document covers everything needed to take DotClaw from the PoC state to a
production-grade DISCOM intelligence layer delivered over WhatsApp. It covers
infrastructure, integration with OT/IT systems, role-based access control (RBAC),
security, and a phased rollout plan.

---

## 1. System Integration Matrix

### 1.1 SCADA (OT Layer)

| Item | Detail |
|------|--------|
| **Purpose** | Real-time feeder telemetry — load, voltage, power factor, status |
| **Typical vendors** | GE iFIX, Siemens SICAM, ABB SYS600, Wonderware |
| **Protocols** | OPC-UA (preferred), OPC-DA, DNP3, IEC 60870-5-104, Modbus TCP |
| **Integration method** | OPC-UA client adapter → normalisation service → internal REST/gRPC API |
| **Polling interval** | 15–30 seconds for live queries; 5-minute aggregates for dashboards |
| **Network requirement** | Isolated OT-DMZ segment; read-only service account on SCADA historian |
| **Key data points** | Feeder load (MW), voltage (kV), power factor, CB status, capacity % |
| **Security** | One-way data diode or read-only OPC-UA session; no write path from DotClaw |

**Adapter sketch:**
```
SCADA Historian / OPC-UA Server
        │  (OPC-UA read-only session, port 4840)
        ▼
  OT-Adapter Service  (Python / Node, deployed in OT-DMZ)
        │  (REST/JSON over internal network only)
        ▼
  DotClaw Feeder API  →  skill: scada-feeder
```

---

### 1.2 OMS — Outage Management System

| Item | Detail |
|------|--------|
| **Purpose** | Active outages, crew status, fault location, restoration ETA |
| **Typical vendors** | Oracle Utilities NMS, Milsoft WindMil, Trimble, custom |
| **Integration method** | REST or SOAP API (vendor-provided); webhook for event-driven updates |
| **Key data points** | Outage ID, feeder, zone, start time, consumer count, crew status, outage type |
| **Update trigger** | Webhook POST to DotClaw on outage create/update/close events |
| **Fallback** | Polling every 2 minutes if webhooks unavailable |

---

### 1.3 MDMS / AMI (Meter Data Management)

| Item | Detail |
|------|--------|
| **Purpose** | Smart meter reads, AT&C loss computation, tamper/anomaly detection |
| **Typical vendors** | Itron, Landis+Gyr, Honeywell Elster, C-DAC MDMS |
| **Integration method** | REST API or SFTP-based batch export (15-min intervals) |
| **Key data points** | Meter ID, DT cluster, consumption, tamper flag, comm status, zero-read flag |
| **AT&C computation** | Input energy (SCADA MU) vs. billed energy (MDMS) per feeder per day |
| **Anomaly pipeline** | MDMS → anomaly detector service → DotClaw AMI skill |

---

### 1.4 SLDC — State Load Dispatch Centre

| Item | Detail |
|------|--------|
| **Purpose** | Grid drawal schedule, real-time drawal vs. schedule deviation, UI/OD alerts |
| **Protocol** | IEC 60870-5-101 / 104 (serial or TCP), ICCP (TASE.2), or REST API from state portal |
| **Integration method** | SLDC-to-DISCOM data link (already mandated by CERC); tap the existing RTU feed |
| **Key data points** | Scheduled drawal (MW), actual drawal, frequency, UI/OD units, grid frequency |
| **Compliance note** | Data access subject to SLDC data sharing agreement; read-only |

---

### 1.5 ERP / SAP IS-U

| Item | Detail |
|------|--------|
| **Purpose** | Consumer master, billing, revenue, O&M capex data |
| **Integration method** | SAP RFC / BAPI calls or SAP Integration Suite (CPI) REST wrapper |
| **Key data points** | Consumer count per feeder, billed units, collection efficiency, pending dues |
| **Use in DotClaw** | AT&C commercial loss context; revenue per feeder; collection reports |

---

### 1.6 GIS

| Item | Detail |
|------|--------|
| **Purpose** | Network topology, feeder route, DT locations |
| **Typical vendors** | ESRI ArcGIS, Bentley OpenUtilities, MapInfo |
| **Integration method** | ArcGIS REST API or WFS/WMS layer; read-only spatial queries |
| **Use in DotClaw** | Feeder-to-zone mapping; outage area polygon for consumer count estimates |

---

## 2. Production Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CONSUMER CHANNEL                             │
│                                                                      │
│   WhatsApp Business API (Meta Cloud / On-Premise BSP)               │
│         │                                                            │
│         ▼                                                            │
│   DotClaw Gateway  (webhook receiver, auth, RBAC enforcement)       │
│         │                                                            │
│         ▼                                                            │
│   Claude Agent (claude-sonnet-4-6)  ←→  Skill Dispatcher            │
│         │                                                            │
│         ├── scada-feeder      →  OT Adapter   →  SCADA             │
│         ├── outage-status     →  OMS API                            │
│         ├── atc-analytics     →  MDMS API                           │
│         ├── ami-meters        →  AMI/MDMS API                       │
│         └── [future skills]   →  SLDC / SAP / GIS                  │
│                                                                      │
│   Supporting Services                                                │
│   ├── User Registry (WhatsApp number ↔ role ↔ scope)                │
│   ├── Audit Log Service                                              │
│   ├── Rate Limiter                                                   │
│   └── Alert Engine (threshold-based push notifications)             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Role-Based Access Control (RBAC)

### 3.1 Role Hierarchy

| Role | Level | Scope | Permitted Skills / Data |
|------|-------|-------|------------------------|
| **CMD / MD** | Corporate | All circles | AT&C summary, outage count, revenue KPIs, executive digest |
| **Director (Operations)** | Corporate | All circles | All operational skills, SCADA all feeders, OMS all zones |
| **Circle SE** | Circle | Own circle | SCADA (circle feeders), OMS (circle zones), AT&C (circle), AMI summary |
| **Division EE** | Division | Own division | SCADA (division feeders), OMS (division zones), AMI anomalies |
| **Sub-Division AEE / AE** | Sub-division | Own sub-division | SCADA (sub-div feeders), OMS (sub-div), AMI (sub-div DTs) |
| **Junior Engineer** | Field | Assigned feeders only | SCADA read for assigned feeders, active outages for zone |
| **Revenue Protection Officer** | Division | Own division | AMI anomalies (tamper + zero-read), meter field assignments |
| **MIS / Finance** | Corporate | Read-only | AT&C reports, billing data, no real-time OT access |
| **IT Admin** | System | Platform-wide | System health, user registry management, audit logs |

### 3.2 How RBAC Works via WhatsApp

```
Incoming WhatsApp message
        │
        ▼
  Gateway looks up sender's WA number in User Registry
        │
        ├── Not found → reply: "Your number is not registered. Contact IT Admin."
        │
        └── Found → load {role, circle, division, sub_division, allowed_feeders}
                │
                ▼
          Claude receives role + scope in system prompt context
                │
                ▼
          Skill Dispatcher enforces scope:
          - Checks requested feeder/zone is within user's allowed scope
          - Strips out-of-scope data before returning response
          - Logs access attempt to Audit Log
```

### 3.3 User Registry Schema

```json
{
  "wa_number": "+919XXXXXXXXX",
  "name": "Rajesh Kumar",
  "employee_id": "EMP-00123",
  "role": "division_ee",
  "circle": "Circle-North",
  "division": "Division-3",
  "sub_division": null,
  "allowed_feeders": ["FDR-001", "FDR-002", "FDR-003", "FDR-004"],
  "allowed_zones": ["Zone-A", "Zone-B"],
  "active": true,
  "registered_by": "admin",
  "registered_at": "2026-01-15T10:00:00Z",
  "last_active": "2026-03-25T08:32:11Z"
}
```

### 3.4 Admin Commands (IT Admin role only)

| Command | Action |
|---------|--------|
| `ADD USER +91XXXXXXXXXX role=circle_se circle=North` | Register new user |
| `DEACTIVATE USER +91XXXXXXXXXX` | Suspend access immediately |
| `LIST USERS division=Division-3` | List all active users in scope |
| `AUDIT +91XXXXXXXXXX last=24h` | Show last 24h query log for a user |

---

## 4. WhatsApp Business API Setup

### 4.1 Options

| Option | Recommended For | Notes |
|--------|----------------|-------|
| **Meta Cloud API** | Most DISCOMs | Easiest, managed by Meta, requires internet |
| **On-Premise BSP** | High-security / air-gapped needs | Self-hosted, more control, higher ops overhead |
| **BSP Partner** (Gupshup, Infobip, Twilio) | Quick start | Adds a vendor layer but faster onboarding |

### 4.2 Requirements

- **WhatsApp Business Account** verified with DISCOM's official business identity
- **Dedicated phone number** (not used for personal WA)
- **Green tick / Business verification** with Meta (recommended for trust)
- **Webhook endpoint** — HTTPS, publicly reachable, TLS 1.2+
- **Message templates** pre-approved by Meta for proactive alerts (outage notifications, AT&C alerts)

---

## 5. Security Architecture

### 5.1 Network Zones

```
Internet
   │
   ▼
[WAF / DDoS protection]  ← Cloudflare / AWS Shield
   │
   ▼
DMZ — DotClaw Gateway (HTTPS/443 only)
   │
   ▼
Internal App Network — Claude Agent, Skill Services, User Registry
   │
   ├──────────────────────────────────────────────────┐
   ▼                                                  ▼
IT Network                                      OT-DMZ
(OMS, MDMS, SAP, GIS)                     (OT Adapter only)
                                                 │
                                            [One-way data diode
                                             or read-only OPC-UA]
                                                 │
                                                 ▼
                                           OT Network (SCADA)
```

### 5.2 Key Security Controls

| Control | Implementation |
|---------|---------------|
| **Authentication** | WA number as identity; optional OTP PIN for sensitive roles (SE and above) |
| **Authorisation** | Server-side RBAC — never trust client-side claims |
| **OT isolation** | Read-only adapter in OT-DMZ; no write path to SCADA from DotClaw |
| **Encryption in transit** | TLS 1.3 for all APIs; end-to-end encryption from WA inherent |
| **Encryption at rest** | AES-256 for User Registry, Audit Logs, cached telemetry |
| **Secrets management** | HashiCorp Vault or AWS Secrets Manager for all API keys |
| **Audit logging** | Every query logged: timestamp, WA number, role, skill invoked, feeder/zone |
| **Rate limiting** | 20 queries/user/hour; 5 queries/minute burst |
| **Session timeout** | Conversations expire after 30 minutes of inactivity |
| **Data retention** | Telemetry cache: 24h; Audit logs: 1 year; PII: per IT policy |

### 5.3 Compliance Checklist

- [ ] CEA Cyber Security Regulations 2023 compliance for OT systems
- [ ] CERT-In reporting obligations for security incidents
- [ ] Data localisation — all servers in Indian data centres (or GovCloud)
- [ ] DISCOM IT policy approval for WhatsApp as a data channel
- [ ] OT vendor sign-off on read-only integration method
- [ ] SLDC data sharing agreement reviewed

---

## 6. Infrastructure Requirements

### 6.1 Minimum Production Setup

| Component | Spec | Notes |
|-----------|------|-------|
| **App Server** | 4 vCPU, 8 GB RAM, 100 GB SSD | DotClaw Gateway + Agent runtime |
| **OT Adapter Server** | 2 vCPU, 4 GB RAM | Deployed in OT-DMZ, separate from app |
| **Database** | PostgreSQL 15, 50 GB | User Registry, Audit Logs, config |
| **Cache** | Redis 7, 4 GB | Telemetry cache, rate limiter |
| **Load Balancer** | Nginx / AWS ALB | SSL termination, health checks |
| **Monitoring** | Prometheus + Grafana or equivalent | Skill latency, error rates, WA API health |

### 6.2 High-Availability (Recommended)

- App Server: 2-node active-passive or active-active behind LB
- Database: Primary + read replica with automated failover
- OT Adapter: Redundant instance with heartbeat monitoring
- RPO: 15 minutes | RTO: 30 minutes

---

## 7. Skill Integration Checklist (Per System)

### SCADA → scada-feeder skill
- [ ] OPC-UA endpoint URL, port, namespace confirmed with OT team
- [ ] Read-only service account created on SCADA historian
- [ ] OT Adapter deployed and tested in OT-DMZ
- [ ] Feeder ID mapping (SCADA tag names → DotClaw FDR-XXX IDs) completed
- [ ] Firewall rule: OT Adapter → SCADA historian (port 4840, one direction)
- [ ] Mock replaced with live adapter in skill config

### OMS → outage-status skill
- [ ] OMS REST/SOAP API credentials obtained
- [ ] Webhook endpoint registered in OMS for outage events
- [ ] Zone and feeder mapping to DISCOM hierarchy verified
- [ ] Timezone handling confirmed (IST throughout)
- [ ] Mock replaced with live OMS client

### MDMS/AMI → atc-analytics + ami-meters skills
- [ ] MDMS API access credentials obtained
- [ ] AT&C loss formula agreed with commercial team (input from SCADA, billed from MDMS)
- [ ] DT cluster mapping for AMI anomaly grouping verified
- [ ] Anomaly thresholds (days silent for zero-read, tamper flag definition) confirmed
- [ ] Batch export schedule aligned (MDMS export → DotClaw ingestion pipeline)

### SLDC Integration (Phase 2)
- [ ] SLDC data link type identified (IEC 104 / REST portal)
- [ ] SLDC data sharing agreement signed
- [ ] New skill: `sldc-drawal` — scheduled vs actual MW, UI/OD status
- [ ] Grid frequency alert threshold configured

---

## 8. Phased Rollout Plan

### Phase 1 — Foundation (Weeks 1–4)
- [ ] Production infrastructure provisioned
- [ ] WhatsApp Business Account verified
- [ ] User Registry set up with pilot users (IT Admin + 2–3 SEs)
- [ ] RBAC enforced in Gateway
- [ ] Live SCADA adapter deployed (scada-feeder skill goes live)
- [ ] Live OMS integration (outage-status skill goes live)
- [ ] Audit logging active

### Phase 2 — Analytics Layer (Weeks 5–8)
- [ ] MDMS/AMI integration live (atc-analytics + ami-meters skills)
- [ ] AT&C loss pipeline validated against manual MIS reports
- [ ] Proactive alert templates approved by Meta and deployed
- [ ] Role expansion: EE and AEE levels onboarded

### Phase 3 — SLDC + ERP (Weeks 9–14)
- [ ] SLDC drawal skill live
- [ ] SAP/ERP read integration for billing and consumer data
- [ ] Executive digest skill for CMD/Director level (daily push at 8 AM)
- [ ] Full RBAC hierarchy deployed across all roles

### Phase 4 — Hardening & Scale (Weeks 15–20)
- [ ] HA setup validated (failover tested)
- [ ] Load testing (simulate 200 concurrent users)
- [ ] Security audit / VAPT completed
- [ ] CERT-In compliance review
- [ ] Rollout to all field staff (JEs, linemen, RPOs)
- [ ] Helpdesk runbook published

---

## 9. Operational Runbook (Day-to-Day)

### Adding a New User
1. IT Admin sends: `ADD USER +91XXXXXXXXXX role=junior_engineer division=Division-3 feeders=FDR-005,FDR-006`
2. System registers and sends welcome message to the new WA number
3. User is active immediately

### Removing a User (e.g. transfer / resignation)
1. IT Admin sends: `DEACTIVATE USER +91XXXXXXXXXX`
2. Access revoked within seconds; session terminated if active

### When SCADA Adapter Goes Down
- DotClaw returns: _"Live SCADA data unavailable. Last cached data as of [time]. Please contact IT."_
- Alert fires to IT Admin on WA automatically
- Adapter health is monitored every 60 seconds; auto-restart on crash

### Rotating API Credentials
1. Generate new credentials in OMS/MDMS/SCADA admin console
2. Update secret in Vault/Secrets Manager
3. Restart relevant adapter service (zero-downtime rolling restart)
4. Verify with a test query via admin WA number

---

## 10. Key Contacts / Ownership Matrix

| Area | Owner | Dependency |
|------|-------|------------|
| WhatsApp API & Meta compliance | IT / Digital team | Meta approval SLA: 2–5 days |
| SCADA read-only access | OT / SCADA team | Requires CISO sign-off |
| OMS API credentials | IT / OMS vendor | Vendor SLA varies |
| MDMS API access | IT / MDMS vendor | Data agreement needed |
| SLDC connectivity | GM (Operations) | SLDC coordination required |
| SAP/ERP integration | IT / SAP team | SAP Basis involvement |
| User onboarding | IT Admin (DotClaw) | HR feeds employee data |
| Security audit | CISO / empanelled agency | Recommend before Phase 4 go-live |
