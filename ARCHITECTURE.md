# QuintOS — Architectural Specification & Threat Model

> **Author:** Nikhil Manvi  
> **Classification:** Public System Architecture Showcase  
> **Status:** Production Architecture

---

## 1. System Overview

QuintOS is engineered as an asynchronous, local-first microservices ecosystem. It decomposes cybersecurity posture evaluation into five specialized domains, orchestrated by an API Gateway and rendered via an interactive desktop shell.

```
+-------------------------------------------------------------------------+
|                  Sentinel Hub (React 18 / Tailwind)                     |
|                                                                         |
|  +-------------------+  +--------------------+  +--------------------+  |
|  | Floating Window   |  | Blast Radius Graph |  | Telemetry Stream   |  |
|  | Manager & Dock    |  | (Topology Engine)  |  | (SSE / Health Log) |  |
|  +-------------------+  +--------------------+  +--------------------+  |
+------------------------------------+------------------------------------+
                                     |
                                     | HTTP REST / EventStream
                                     v
+-------------------------------------------------------------------------+
|                 Quint-CLI Aggregation Gateway (:9000)                   |
|                   FastAPI / Asynchronous Dispatcher                     |
+---+----------------+----------------+-----------------+-----------------+
    |                |                |                 |                 |
    v                v                v                 v                 v
+---------+      +---------+      +---------+       +---------+       +---------+
| M01     |      | M02     |      | M03     |       | M04     |       | M05     |
| Supply  |      | Secret  |      | Infra   |       | API     |       | Cloud   |
| Watch   |      | Watch   |      | Guard   |       | Sentry  |       | Posture |
| (:8000) |      | (:8001) |      | (:8002) |       | (:8003) |       | (:8004) |
+---------+      +---------+      +---------+       +---------+       +---------+
```

---

## 2. STRIDE Threat Model

To ensure QuintOS does not introduce security vulnerabilities into the environments it monitors, each module operates under a rigorous STRIDE threat analysis:

| STRIDE Threat Category | Potential Attack Vector | QuintOS Architectural Mitigation |
|---|---|---|
| **Spoofing (Identity)** | Malicious third-party injection of fake security reports into the Gateway. | Module loopback binding (`127.0.0.1`), token-authenticated inter-service calls, and strict Pydantic v2 finding validation. |
| **Tampering (Data)** | Modification of scan results in-flight between services. | In-memory message bus, deterministic SHA-256 finding hashing, and local immutable JSON reports. |
| **Repudiation** | Operator denying scan execution or suppression of critical alerts. | Timestamped audit logs recorded locally with deterministic finding IDs and git-commit binding. |
| **Information Disclosure** | Leakage of discovered secrets or proprietary source code to external servers. | **Absolute Zero Cloud Transmission Policy.** All AST parsers and regex engines execute strictly in local memory. |
| **Denial of Service** | Infinite recursion during directory traversal or regex ReDoS attack on large minified files. | Bounded path traversals (max depth 12), file size caps (max 5MB per analyzed file), and non-backtracking regex compilation. |
| **Elevation of Privilege** | Using `APISentry` to scan internal LAN services (SSRF) or `InfraGuard` running with root privileges. | Strict SSRF RFC 1918 pre-check, drop root permissions in all Docker containers (`USER 10001`), and read-only host mounts. |

---

## 3. Data Flow Diagram (DFD)

```mermaid
flowchart TD
    subgraph ClientLayer["Client Layer (Untrusted Boundary)"]
        UI["Sentinel Hub Web Shell\n(localhost:5170)"]
        CLI["Quint CLI Tool\n(Developer Terminal)"]
    end

    subgraph GatewayLayer["Gateway & Orchestration"]
        GW["Quint-CLI Aggregator\nFastAPI (:9000)"]
    end

    subgraph Engines["Isolated Security Microservices"]
        M01["M01 SupplyWatch\nOSV / Package Registry"]
        M02["M02 SecretWatch\nShannon Entropy Engine"]
        M03["M03 InfraGuard\nAST IaC Engine"]
        M04["M04 APISentry\nSSRF Firewall & Prober"]
        M05["M05 CloudPosture\nCloud Misconfig Engine"]
    end

    subgraph Storage["Ephemeral & Local Storage"]
        Target["Local Project Codebase\n(Read-Only Target)"]
        Report["Audit Report Cache\n(/tmp/quint-audit.json)"]
    end

    UI -->|Async HTTP API| GW
    CLI -->|Command Dispatch| GW

    GW -->|Parallel Fan-Out| M01
    GW -->|Parallel Fan-Out| M02
    GW -->|Parallel Fan-Out| M03
    GW -->|Parallel Fan-Out| M04
    GW -->|Parallel Fan-Out| M05

    M01 -.->|Read AST/Deps| Target
    M02 -.->|Read Code Files| Target
    M03 -.->|Read Docker/K8s| Target
    M05 -.->|Read Terraform/CF| Target

    M04 -->|Outbound Probe\n(SSRF Blocked)| External["Public Live API Target"]

    M01 -->|Telemetry Stream| GW
    M02 -->|Telemetry Stream| GW
    M03 -->|Telemetry Stream| GW
    M04 -->|Telemetry Stream| GW
    M05 -->|Telemetry Stream| GW

    GW -->|Correlated Results| Report
    GW -->|Unified Telemetry| UI
```

---

## 4. Blast Radius Graph Computation

One of QuintOS's core innovations is its **Blast Radius Correlation Algorithm**. When multiple modules generate findings, Sentinel Hub correlates them into a connected attack graph:

```
[M02: Leaked AWS Secret Key in .env]
             │
             ▼ (Discovered Access Vector)
[M05: Over-Privileged IAM Role in Terraform]
             │
             ▼ (Resource Impact)
[M05: Public S3 Bucket with Customer Data]
             │
             ▼ (Network Exposure)
[M04: Missing CSP & Wildcard CORS in API]
```

### Synthesis Rules:
1. **Secret $\rightarrow$ Infrastructure Binding:** When an AWS/GCP key is found in Module 02, any cloud resource defined in Module 05 matching that provider is elevated to `CRITICAL`.
2. **Container $\rightarrow$ Network Exposure:** If Module 03 flags a Docker container running as `root` and Module 04 flags that same port with missing TLS or open CORS, the combined threat score scales non-linearly using:
   $$\text{Composite Risk} = \min\left(100, \, R_{\text{base}} \times (1 + \lambda_{\text{correlation}})\right)$$
   Where $\lambda_{\text{correlation}} \ge 0.35$ for multi-vector intersections.
