Feature: SYNC Inbound Graph pull and toss into maildir
  As the Vintage Client (Entourage 2008)
  I want new Outlook mail and Teams chats in one POP mailbox
  So that I can read them without talking to O365

  Background:
    Given MailboxAccount is authenticated
    And the inbound maildir is empty
    And no TossedMessage rows exist

  Scenario: SYNC1.1 Tosser drops Outlook MIME into maildir
    Given Graph Inbox contains message id "AAMk-outlook-1" with subject "Q3 close"
    And GET /me/messages/AAMk-outlook-1/$value returns RFC822 bytes
    When Celery runs sync_mailbox
    Then maildir contains exactly 1 message
    And that message subject is "Q3 close"
    And TossedMessage records graph_id="AAMk-outlook-1" source="outlook"
    And a second sync_mailbox does not create a duplicate
    And logs/app.log contains beat "processing" with tossed=1 skipped_dup=0

  Scenario: SYNC1.2 Tosser synthesizes Teams chat as RFC822
    Given Graph chat "19:general" has a new message from "Ada Lovelace" saying "Ship it"
    When Celery runs sync_mailbox
    Then maildir contains a message with subject starting with "Teams:"
    And the From header contains "Ada Lovelace"
    And the From address is "teams.{chat_b32}@o365pop.local" not Ada's real mailbox
    And Message-ID starts with "<teams."
    And Reply-To equals From
    And the body contains "Ship it"
    And TossedMessage records source="teams" and that Message-ID
    And ChatMap maps chat "19:general" to that teams.* address

  Scenario: SYNC1.3 Empty Inbox and no new chats is a successful no-op
    Given Graph Inbox and chats have no messages newer than the last sync
    When Celery runs sync_mailbox
    Then maildir is still empty
    And SyncSession status is "completed"
    And logs/app.log contains beat "exit" with tossed=0
