# Docs

Place diagrams, screenshots, and report figures here.

# CESOMS ER Diagram

## Entities

### STUDENT
- `StudentID` (PK)
- `FirstName`
- `LastName`
- `Email` (UNIQUE)
- `ClassYear`
- `Major`
- `AccountStatus`

### ADMINISTRATOR
- `AdminID` (PK)
- `FirstName`
- `LastName`
- `Email` (UNIQUE)
- `Department`
- `AdminStatus`

### ORGANIZATION
- `OrgID` (PK)
- `OrgName`
- `Description`
- `ContactEmail`
- `OrgStatus`

### LOCATION
- `LocationID` (PK)
- `LocationName`
- `Building`
- `Room`
- `Address`
- `IsVirtual`
- `VirtualLink`
- `Capacity`

### EVENT_CATEGORY
- `CategoryID` (PK)
- `CategoryName`
- `Description`

### ACADEMIC_TERM
- `TermID` (PK)
- `TermName`
- `StartDate`
- `EndDate`

### EVENT
- `EventID` (PK)
- `OrgID` (FK → `ORGANIZATION.OrgID`)
- `LocationID` (FK → `LOCATION.LocationID`)
- `CategoryID` (FK → `EVENT_CATEGORY.CategoryID`)
- `TermID` (FK → `ACADEMIC_TERM.TermID`)
- `Title`
- `Description`
- `Capacity`
- `StartDateTime`
- `EndDateTime`
- `EventStatus`

### APP_USER
- `UserID` (PK)
- `AccountType`
- `AccountRefID`
- `PasswordHash`
- `CreatedAt`
- `LastPasswordChangedAt`

Note:
- `APP_USER` stores login credentials for both students and administrators.
- Logical relationship:
  - if `AccountType = 'student'`, `AccountRefID → STUDENT.StudentID`
  - if `AccountType = 'admin'`, `AccountRefID → ADMINISTRATOR.AdminID`

## Relationship Tables

### MEMBERSHIP
- `StudentID` (PK, FK → `STUDENT.StudentID`)
- `OrgID` (PK, FK → `ORGANIZATION.OrgID`)
- `JoinDate`
- `LeaveDate`
- `MemberRole`

Meaning:
- Resolves the many-to-many relationship between students and organizations.

### ORGANIZATION_OFFICER
- `StudentID` (PK, FK → `STUDENT.StudentID`)
- `OrgID` (PK, FK → `ORGANIZATION.OrgID`)
- `StartDate` (PK)
- `RoleTitle`
- `EndDate`

Meaning:
- Tracks officer roles over time.
- Composite primary key allows multiple officer terms.

### REGISTRATION
- `StudentID` (PK, FK → `STUDENT.StudentID`)
- `EventID` (PK, FK → `EVENT.EventID`)
- `RegisteredAt`
- `RegistrationStatus`

Meaning:
- Resolves the many-to-many relationship between students and events.

### ATTENDANCE
- `StudentID` (PK, FK → `STUDENT.StudentID`)
- `EventID` (PK, FK → `EVENT.EventID`)
- `CheckInTime`
- `AttendanceFlag`
- `RecordedByOfficerStudentID`
- `RecordedByOfficerOrgID`
- `RecordedByOfficerStartDate`

Foreign key:
- (`RecordedByOfficerStudentID`, `RecordedByOfficerOrgID`, `RecordedByOfficerStartDate`)
  → `ORGANIZATION_OFFICER(StudentID, OrgID, StartDate)`

Meaning:
- Stores attendance records and which officer recorded them.

### APPROVAL
- `EventID` (PK, FK → `EVENT.EventID`)
- `SubmittedByOfficerStudentID`
- `SubmittedByOfficerOrgID`
- `SubmittedByOfficerStartDate`
- `ReviewedByAdminID` (FK → `ADMINISTRATOR.AdminID`)
- `SubmittedAt`
- `ReviewedAt`
- `DecisionStatus`
- `DecisionNotes`

Foreign key:
- (`SubmittedByOfficerStudentID`, `SubmittedByOfficerOrgID`, `SubmittedByOfficerStartDate`)
  → `ORGANIZATION_OFFICER(StudentID, OrgID, StartDate)`

Meaning:
- Stores the event approval workflow.

### REPORT
- `ReportID` (PK)
- `GeneratedByAdminID` (FK → `ADMINISTRATOR.AdminID`)
- `ReportType`
- `GeneratedAt`
- `Summary`

Meaning:
- Stores generated administrative reports if the table exists.

## Relationships Summary

### Core Relationships
- `ORGANIZATION 1:M EVENT`
- `LOCATION 1:M EVENT`
- `EVENT_CATEGORY 1:M EVENT`
- `ACADEMIC_TERM 1:M EVENT`

### User / Account Relationships
- `STUDENT 1:0..1 APP_USER`  
  logical via `APP_USER(AccountType='student', AccountRefID=StudentID)`
- `ADMINISTRATOR 1:0..1 APP_USER`  
  logical via `APP_USER(AccountType='admin', AccountRefID=AdminID)`

### Membership / Role Relationships
- `STUDENT M:N ORGANIZATION` via `MEMBERSHIP`
- `STUDENT M:N ORGANIZATION` via `ORGANIZATION_OFFICER`

### Event Participation Relationships
- `STUDENT M:N EVENT` via `REGISTRATION`
- `STUDENT M:N EVENT` via `ATTENDANCE`

### Approval / Workflow Relationships
- `EVENT 1
