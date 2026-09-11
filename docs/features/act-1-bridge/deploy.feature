Feature: DEP LibreELEC Docker stack behind WireGuard
  As Denis (Operator)
  I want popd and smtpd reachable on the WireGuard address without TLS
  So that Entourage at the far end of the tunnel can collect and send

  Scenario: ✅ DEP1.1 Compose publishes 110 and 587 on the bind address
    Given docker-compose defines services redis, worker, beat, popd, smtpd
    And POP3_BIND and SMTP_BIND are the WireGuard address
    When the stack is started with host networking
    Then popd listens on port 110 without TLS
    And smtpd listens on port 587 without TLS
    And neither process binds the WAN interface when ALLOW_LAN is unset
    And volumes persist data, maildir, spool, logs, and tasks under /storage/o365pop
