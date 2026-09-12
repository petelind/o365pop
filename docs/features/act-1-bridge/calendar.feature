Feature: CAL Entourage Calendar sync with Outlook
  As the Vintage Client (Entourage 2008)
  I want Outlook appointments and meetings in Entourage Calendar
  So that I can work the calendar in Entourage without opening an .ics or using POP

  Background:
    Given MailboxAccount is authenticated with Calendars.ReadWrite
    And LibreELEC has published /storage/o365pop/calendar/snapshot.json
    And Mac taskd is running on the Entourage host

  Scenario: CAL1.1 Snapshot event becomes an Entourage event
    Given Graph calendar "Calendar" id "cal-work" contains event id "evt-standup" subject "Standup" start "2026-09-12T13:00:00Z" end "2026-09-12T13:30:00Z" location "Room A" categories "Work" showAs "busy" sensitivity "normal" reminderMinutesBeforeStart 15
    And that event has attendee "Ada Lovelace" email "ada@contoso.com" type "required"
    When Mac taskd pulls the calendar snapshot
    Then Entourage has an event subject "Standup" starting Saturday 12 Sep 2026 09:00 ending 09:30
    And that event content contains "o365pop-uid: evt-standup"
    And that event content contains attendee text "Ada Lovelace" and "ada@contoso.com"
    And that event is not an Entourage meeting invite (to recipients is empty)
    And that event project list contains Project "Work"
    And Entourage has no Project named "Calendar"
    And that event has category "Work"
    And that event reminder is 15 minutes before start
    And that event show-as is busy
    And that event sensitivity is normal
    And logs on the Mac contain beat "exit" with created=1

  Scenario: CAL1.2 Event category creates an Entourage Project
    Given Graph calendar "Calendar" id "cal-work" contains event id "evt-standup" with category "Garden"
    And Entourage has no Project named "Garden"
    When Mac taskd pulls the calendar snapshot
    Then Entourage has a Project named "Garden"
    And that event project list contains Project "Garden"
    And Entourage has no Project named "Calendar"

  Scenario: CAL1.3 Uncategorized event is Calendar-only
    Given Graph calendar "Calendar" id "cal-work" contains event id "evt-dentist" subject "Dentist" with no categories
    When Mac taskd pulls the calendar snapshot
    Then Entourage has an event subject "Dentist"
    And that event project list is empty
    And Entourage has no Project named "Calendar"

  Scenario: CAL1.4 Outlook calendar displayName does not create or rename a Project
    Given Entourage has Project "Work" from event category "Work"
    And Graph calendar id "cal-work" displayName is now "Mailbox"
    When Mac taskd pulls the calendar snapshot
    Then Entourage still has Project "Work"
    And Entourage has no Project named "Mailbox"
    And Entourage has no Project named "Calendar"

  Scenario: CAL1.5 Event categories apply without mutating the catalog
    Given Graph event "evt-standup" categories are "Urgent"
    And Entourage already has category "Urgent" from TASK catalog sync
    When Mac taskd pulls the calendar snapshot
    Then that Entourage event has category "Urgent"
    And calendar sync does not create rename or delete masterCategories

  Scenario: CAL1.6 Editing in Entourage PATCHes Graph
    Given Entourage event content contains "o365pop-uid: evt-standup" subject "Standup moved" location "Room B" reminderMinutesBeforeStart 10 showAs "tentative" sensitivity "private"
    And Graph event "evt-standup" subject is "Standup"
    When Mac taskd writes a receipt and LibreELEC applies it
    Then Graph PATCHes /me/events/evt-standup with subject "Standup moved" location "Room B" reminderMinutesBeforeStart 10 showAs "tentative" sensitivity "private"
    And Graph attendees are not patched
    And logs/app.log contains beat "exit" with patched=1

  Scenario: CAL1.7 Untagged local Entourage event POSTs to Graph
    Given Entourage has an event subject "Dentist" start "2026-09-15T18:00:00Z" end "2026-09-15T19:00:00Z" with no o365pop-uid in content
    And that event project list contains Project "Work"
    And Graph default calendar "Calendar" id is "cal-work"
    When Mac taskd writes a create receipt and LibreELEC applies it
    Then Graph POSTs /me/calendars/cal-work/events with subject "Dentist"
    And the next calendar snapshot includes the new Graph event id
    And that Entourage event content then contains "o365pop-uid:" for that id

  Scenario: CAL1.8 LibreELEC unreachable does not crash taskd
    Given the calendar snapshot path or host is unreachable (LibreELEC down, timeout, connection refused)
    When Mac taskd tries to pull
    Then taskd does not raise or exit
    And Entourage Calendar events are left unchanged
    And receipts stay queued locally
    And logs contain beat "branch" with reachability="down" (WARNING, not ERROR traceback)
    And the next 60s tick tries again

  Scenario: CAL1.9 Event attachment files sync both ways
    Given Graph event "evt-standup" has attachment name "agenda.pdf" contentType "application/pdf"
    And LibreELEC wrote calendar/attachments/evt-standup/agenda.pdf
    When Mac taskd pulls the calendar snapshot
    Then that Entourage event has a file attachment named "agenda.pdf"
    And when the operator adds attachment "notes.txt" on that Entourage event
    And Mac taskd writes a receipt
    Then LibreELEC POSTs the attachment to Graph /me/events/evt-standup/attachments
