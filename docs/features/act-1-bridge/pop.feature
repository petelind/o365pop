Feature: POP Entourage collects mail without TLS
  As the Vintage Client (Entourage 2008)
  I want POP3 on port 110 with USER/PASS and no SSL
  So that I can download tossed mail over WireGuard

  Background:
    Given popd listens on 127.0.0.1 port 11110 with TLS disabled
    And the local mailbox user is "denis" with password "local-pass"
    And maildir contains one RFC822 message with UIDL "uid-outlook-1"

  Scenario: POP1.1 Entourage lists and retrieves
    When a POP client connects without TLS
    And the client sends USER "denis" and PASS "local-pass"
    Then the server replies +OK
    And STAT reports 1 message
    And UIDL contains "uid-outlook-1"
    And RETR 1 returns the RFC822 including the Subject header
    And TOP 1 0 returns headers only

  Scenario: POP1.2 Wrong password is rejected
    When a POP client sends USER "denis" and PASS "wrong"
    Then the server replies -ERR
    And RETR is not allowed
    And logs/app.log contains beat "error" with reason="auth_failed"
    And the password is not written to the log

  Scenario: POP1.3 DELE removes local copy only
    Given TossedMessage exists for graph_id "AAMk-outlook-1"
    When a POP client DELE 1 and QUIT
    Then maildir no longer contains that message
    And TossedMessage for "AAMk-outlook-1" still exists
    And Graph is not called
