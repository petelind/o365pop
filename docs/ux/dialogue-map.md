# Dialogue map — Collect and send through the bridge

**ESM-04 (stack-adjusted).** Not a GUI screen flow. Actors: Denis (operator), Entourage (vintage client), Celery (worker/beat), Graph, Mac `taskd`.

```mermaid
flowchart TD
  subgraph act1 [Act 1 Operator brings the bridge up]
    A[Denis SSH + compose up] --> B["python -m o365pop login"]
    B --> C[Device code on another machine]
    C --> D[Encrypted tokens on /storage]
    D --> E[Beat starts sync_mailbox]
  end

  subgraph act2 [Act 2 Vintage client collects]
    E --> F[Graph Inbox + Teams]
    F --> G[Tosser drops RFC822 into maildir]
    G --> H[Entourage POP USER/PASS RETR]
    H --> I{DELE?}
    I -->|yes| J[Remove maildir file only]
    I -->|no| K[Message stays for next RETR]
    J --> L[TossedMessage keeps graph_id]
  end

  subgraph act3 [Act 3 Vintage client sends]
    M[Entourage SMTP AUTH LOGIN DATA] --> N[smtpd writes spool/new]
    N --> O[scan_outbound_spool]
    O --> P{Reply map?}
    P -->|ordinary| Q[Graph sendMail MIME]
    P -->|teams address or In-Reply-To| R[Graph chat post]
    Q --> S[spool/sent]
    R --> S
    Q -.->|fail| T[retry then spool/failed]
    R -.->|map miss| T
  end

  subgraph act4 [Act 4 Reply to tossed Teams]
    H --> U[From teams.b32@o365pop.local]
    U --> V[Entourage Reply]
    V --> M
  end

  subgraph act5 [Act 5 Vintage client works Tasks]
    E --> TS[Celery publishes tasks/snapshot.json]
    TS --> TD[Mac taskd every 60s]
    TD -->|LibreELEC down| WAIT[WARNING reachability=down then retry]
    WAIT --> TD
    TD --> AS[osascript Entourage Tasks Projects Categories]
    AS --> RC[receipts/]
    RC --> GP[Graph PATCH To Do]
  end
```

Feature files: `docs/features/act-1-bridge/*.feature`. Phrase map: `docs/features/CATALOG.md`.
