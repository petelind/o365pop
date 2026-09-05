Feature: TEAM Reply to a tossed Teams chat via SMTP
  As the Vintage Client (Entourage 2008)
  I want Reply on a Teams-as-email message to post into that chat
  So that I can continue the conversation without Outlook sending a real email

  Background:
    Given MailboxAccount is authenticated
    And chat "19:general" is mapped to address "teams.mjqxg2a@o365pop.local"
    And TossedMessage exists with source="teams" chat_id="19:general" message_id="<teams.mjqxg2a.abc@o365pop.local>"

  Scenario: TEAM1.1 In-Reply-To maps the reply onto the chat
    Given spool/new contains an RFC822 with In-Reply-To "<teams.mjqxg2a.abc@o365pop.local>"
    And the body starts with "On it"
    When Celery runs scan_outbound_spool
    Then Graph receives POST /chats/19:general/messages with text "On it"
    And Graph does not receive sendMail
    And the file is moved to spool/sent
    And logs/app.log contains beat "branch" with route="teams_chat" chat_id="19:general"

  Scenario: TEAM1.2 Entourage dropped In-Reply-To; To address still maps
    Given spool/new contains an RFC822 To "teams.mjqxg2a@o365pop.local" and no In-Reply-To
    And the body starts with "Still on it"
    When Celery runs scan_outbound_spool
    Then Graph receives POST /chats/19:general/messages with text "Still on it"
    And Graph does not receive sendMail

  Scenario: TEAM1.3 Ordinary mail still uses sendMail
    Given spool/new contains an RFC822 To "ada@example.com" with subject "Hello Ada"
    And there is no In-Reply-To matching a Teams TossedMessage
    When Celery runs scan_outbound_spool
    Then Graph receives POST /me/sendMail
    And Graph does not receive a chat message POST

  Scenario: TEAM1.4 Unknown o365pop.local address fails closed
    Given spool/new contains an RFC822 To "teams.unknown@o365pop.local"
    When Celery runs scan_outbound_spool
    Then Graph is not called
    And after the retry limit the file is in spool/failed
    And logs/app.log contains beat "error" with reason="teams_map_miss"
