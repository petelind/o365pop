Feature: PALM VersaMail sees a Palm-safe POP view
  As the Vintage Client (Palm VersaMail)
  I want a second POP login on the same popd
  So that I get short UIDLs and 7-bit text without changing Entourage :110

  Background:
    Given popd listens on the Entourage port with TLS disabled
    And the Entourage mailbox user is "denis" with password "local-pass"
    And the Palm view user is "palm" with password "local-pass"

  Scenario: PALM1.1 Palm lists a hashed UIDL and 7-bit text
    Given maildir has a fresh multipart HTML message with a long Graph-style UIDL
    When a POP client sends USER "palm" and PASS "local-pass"
    Then STAT reports 1 message
    And UIDL is at most 70 ASCII characters and is not the Graph id
    And RETR is text/plain 7-bit CRLF with Date set and no multipart
    And the rewritten size is at most 5120 bytes

  Scenario: PALM1.2 Palm hides mail older than 24 hours
    Given maildir has one fresh message and one message dated 48 hours ago
    When a POP client sends USER "palm" and PASS "local-pass"
    Then STAT reports only the fresh message

  Scenario: PALM1.3 Entourage :110 is unchanged
    Given the same maildir as PALM1.1
    When a POP client sends USER "denis" and PASS "local-pass"
    Then UIDL is the original store id
    And RETR is the original RFC822 including multipart

  Scenario: PALM1.4 Palm DELE does not remove Entourage mail
    Given maildir has one fresh message
    When a POP client as "palm" DELE 1 and QUIT
    Then a later "denis" session still RETR the original message
