Feature: AUTH Device-code login and token refresh
  As Denis (Operator)
  I want the daemon to hold a Graph access token and refresh it
  So that Celery syncs can call Graph without a browser on LibreELEC

  Background:
    Given TOKEN_ENCRYPTION_KEY is configured
    And no valid Graph access token is cached

  Scenario: AUTH1.1 Denis completes device-code login
    Given Denis runs the device-code login command
    When Microsoft accepts the device code for account "denis@example.com"
    Then MailboxAccount stores an encrypted refresh token and access token
    And azure_token_expires_at is in the future
    And logs/app.log contains beat "exit" with user="denis@example.com"
    And logs do not contain the refresh token or access token

  Scenario: AUTH1.2 Sync refreshes an expired access token
    Given MailboxAccount has an encrypted refresh token
    And the access token is expired
    When Celery starts sync_mailbox
    Then GraphAuthService refreshes the access token
    And the new access token is stored encrypted
    And sync continues with the new bearer token

  Scenario: AUTH1.3 Refresh token revoked fails without retry loop
    Given MailboxAccount has a refresh token Microsoft rejects
    When Celery starts sync_mailbox
    Then the SyncSession status is "failed"
    And the task does not enqueue a retry
    And logs/app.log contains beat "error" with reason="auth_failed"
