Feature: SMTP Entourage submits mail and scanner sends via Graph
  As the Vintage Client (Entourage 2008)
  I want to send RFC822 over SMTP without TLS
  So that Graph delivers the same bytes I composed

  Background:
    Given smtpd listens on 127.0.0.1 port 10587 with STARTTLS disabled
    And the local mailbox user is "denis" with password "local-pass"
    And the outbound spool is empty

  Scenario: ✅ SMTP1.1 Entourage AUTH LOGIN and DATA land in the spool
    When an SMTP client connects without TLS
    And the client AUTH LOGIN as "denis" with password "local-pass"
    And the client sends MAIL FROM:<denis@example.com>
    And the client sends RCPT TO:<ada@example.com>
    And the client DATA is a message with subject "Hello Ada"
    Then smtpd replies 250 after DATA
    And spool/new contains exactly 1 RFC822 file
    And that file contains subject "Hello Ada"
    And Graph is not called by smtpd

  Scenario: ✅ SEND1.1 Scanner posts spool MIME to Graph sendMail
    Given spool/new contains RFC822 with subject "Hello Ada"
    When Celery runs scan_outbound_spool
    Then Graph receives POST /me/sendMail with the same MIME bytes
    And the file is moved to spool/sent
    And logs/app.log contains beat "exit" with sent=1

  Scenario: ✅ SEND1.2 Graph reject moves mail to retry then failed
    Given spool/new contains RFC822 with subject "Bad recipient"
    And Graph sendMail returns HTTP 400
    When Celery runs scan_outbound_spool
    Then the file is in spool/retry
    And after the retry limit the file is in spool/failed
    And SyncSession or send log status is failed
    And logs/app.log contains beat "error" with reason="send_failed"
