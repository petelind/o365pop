Feature: CAL Entourage Calendar sync with Outlook
  As the Vintage Client (Entourage 2008)
  I want Outlook appointments and meetings in Entourage Calendar
  So that I can work the calendar in Entourage without opening an .ics or using POP

  Background:
    Given MailboxAccount is authenticated with Calendars.ReadWrite
    And LibreELEC has published /storage/o365pop/calendar/snapshot.json
    And Mac taskd is running on the Entourage host

  Scenario: CAL1.1 Snapshot event becomes an Entourage event
    Given Graph calendar "Work" id "cal-work" contains event id "evt-standup" subject "Standup" start "2026-09-12T13:00:00Z" end "2026-09-12T13:30:00Z" location "Room A" categories "Work" showAs "busy" sensitivity "normal" reminderMinutesBeforeStart 15
    And that event has attendee "Ada Lovelace" email "ada@contoso.com" type "required"
    When Mac taskd pulls the calendar snapshot
    Then Entourage has an event subject "Standup" starting Saturday 12 Sep 2026 09:00 ending 09:30
    And that event content contains "o365pop-uid: evt-standup"
    And that event content contains attendee text "Ada Lovelace" and "ada@contoso.com"
    And that event is not an Entourage meeting invite (to recipients is empty)
    And that event project list contains Project "Work"
    And that event has category "Work"
    And that event reminder is 15 minutes before start
    And that event show-as is busy
    And that event sensitivity is normal
    And logs on the Mac contain beat "exit" with created=1

  Scenario: CAL1.2 Missing Outlook calendar creates an Entourage Project
    Given Graph has calendar "Garden" id "cal-garden" and Entourage has no Project named "Garden"
    And Graph has no To Do list named "Garden"
    When Mac taskd pulls the calendar snapshot
    Then Entourage has a Project named "Garden"
    And the Project is joined to Graph calendar id "cal-garden"

  Scenario: CAL1.3 Renamed Outlook calendar renames the Project
    Given Entourage Project "Garden" is joined to Graph calendar id "cal-garden"
    And Graph calendar "cal-garden" displayName is now "Yard"
    And no To Do list displayName disagrees
    When Mac taskd pulls the calendar snapshot
    Then Entourage Project joined to "cal-garden" is named "Yard"
    And Entourage has no Project named "Garden" for that Graph calendar id

  Scenario: CAL1.4 Deleted calendar keeps the Project when a To Do list still joins it
    Given Entourage Project "Yard" is joined to calendar id "cal-garden" and To Do list id "list-garden"
    And Graph no longer has calendar "cal-garden"
    And Graph still has To Do list "list-garden" displayName "Yard"
    When Mac taskd pulls the snapshots
    Then Entourage still has Project "Yard" joined to "list-garden"
    And Entourage has no calendar join "cal-garden"

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
    And Graph calendar "Work" id is "cal-work"
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
