Feature: TASK Entourage Tasks sync with Microsoft To Do
  As the Vintage Client (Entourage 2008)
  I want Microsoft To Do lists and Outlook categories in Entourage Tasks
  So that I can work tasks in Entourage without opening an .ics or using POP flags

  Background:
    Given MailboxAccount is authenticated with Tasks.ReadWrite and MailboxSettings.Read
    And LibreELEC has published /storage/o365pop/tasks/snapshot.json
    And Mac taskd is running on the Entourage host

  Scenario: TASK1.1 Snapshot task becomes an Entourage Task
    Given Graph To Do list "Work" id "list-work" contains task id "task-q3" title "File the Q3 report" due "2026-09-12T21:00:00Z" status "notStarted" categories "Work"
    When Mac taskd pulls the snapshot
    Then Entourage has a task named "File the Q3 report" due Saturday 12 Sep 2026 17:00
    And that task content contains "o365pop-uid: task-q3"
    And that task belongs to Project "Work"
    And that task has category "Work"
    And logs on the Mac contain beat "exit" with created=1

  Scenario: TASK1.2 Missing To Do list creates an Entourage Project
    Given Graph has To Do list "Garden" id "list-garden" and Entourage has no Project named "Garden"
    When Mac taskd pulls the snapshot
    Then Entourage has a Project named "Garden"
    And the Project is joined to Graph id "list-garden"

  Scenario: TASK1.3 Renamed To Do list renames the Project
    Given Entourage Project "Garden" is joined to Graph id "list-garden"
    And Graph list "list-garden" displayName is now "Yard"
    When Mac taskd pulls the snapshot
    Then Entourage Project joined to "list-garden" is named "Yard"
    And Entourage has no Project named "Garden" for that Graph id

  Scenario: TASK1.4 Deleted To Do list deletes the synced Project
    Given Entourage Project "Yard" is joined to Graph id "list-garden"
    And Graph no longer has list "list-garden"
    When Mac taskd pulls the snapshot
    Then Entourage has no Project joined to "list-garden"

  Scenario: TASK1.5 Outlook category color maps onto Entourage
    Given Graph masterCategory id "cat-red" displayName "Urgent" color "preset1"
    And Entourage has no category named "Urgent"
    When Mac taskd pulls the snapshot
    Then Entourage has a category named "Urgent"
    And that category color is the mapped Entourage color for Graph preset1

  Scenario: TASK1.6 Completing in Entourage PATCHes Graph
    Given Entourage task content contains "o365pop-uid: task-q3" and completed is true
    And Graph task "task-q3" status is "notStarted"
    When Mac taskd writes a receipt and LibreELEC applies it
    Then Graph PATCHes /me/todo/lists/list-work/tasks/task-q3 with status "completed"
    And logs/app.log contains beat "exit" with patched=1

  Scenario: TASK1.7 Untagged local Entourage tasks stay local
    Given Entourage has a task named "Buy milk" with no o365pop-uid in content
    When Mac taskd runs
    Then Graph does not receive a POST or PATCH for that task

  Scenario: TASK1.8 LibreELEC unreachable does not crash taskd
    Given the snapshot path or host is unreachable (LibreELEC down, timeout, connection refused)
    When Mac taskd tries to pull
    Then taskd does not raise or exit
    And Entourage Tasks are left unchanged
    And receipts stay queued locally
    And logs contain beat "branch" with reachability="down" (WARNING, not ERROR traceback)
    And the next 60s tick tries again
