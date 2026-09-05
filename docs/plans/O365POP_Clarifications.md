# O365POP Clarifications

Recommended answers are baked into the plan. Change any before implementation starts.

### Q1: One mailbox or many?
**Question**: One Graph account on this LibreELEC box, or many users?  
**Recommended**: One `MailboxAccount`. POP/SMTP auth is that one local user.

### Q2: Why not Django?
**Question**: taciturn2 is Django+Celery. Do we need Django here?  
**Recommended**: **No.** No web UI, no users, no admin. Keep Celery + Redis + SQLite (`sqlite3`). CLI is `python -m o365pop login`.

### Q3: POP DELE vs Graph?
**Question**: When Entourage deletes, delete in Outlook too?  
**Recommended**: Local maildir only. Keep `TossedMessage` so we never re-toss. Graph delete is a later scenario.

### Q4: Which Graph folders?
**Question**: Inbox only, or Inbox+Sent+others?  
**Recommended**: Inbox + Teams chats into the **same** POP mailbox (POP has one folder). No folder tree in v1.

### Q5: Redis on LibreELEC?
**Question**: Redis sidecar vs filesystem Celery broker?  
**Recommended**: Redis container, same as taciturn2. Filesystem broker is a fallback if Redis is too heavy — not v1.

### Q6: Live Graph in CI?
**Question**: Device-code against the real tenant in the merge gate?  
**Recommended**: No. `FileGraphAdapter` / local HTTP fixture for integration. Live Graph is a manual lane-3 smoke on the box.

### Q7: Init git / GitHub issues?
**Question**: This workspace is not a git repo yet.  
**Recommended**: After plan approval: `git init`, first docs commit, then one GitHub issue per feature file (AUTH, SYNC, POP, SMTP/SEND, TEAM, DEP).

### Q8: Teams reply mapping?
**Question**: How does Entourage Reply become a Teams chat message?  
**Recommended**: Each chat gets `teams.{base32(chat_id)}@o365pop.local` as From/Reply-To plus a minted Message-ID. Scanner routes by In-Reply-To, then by To. Never put the person’s real email on tossed Teams mail. Never sendMail a mapped reply.
