let data = {
  currentUser: {},
  academicTerm: {},
  students: [],
  administrators: [],
  organizations: [],
  organizationOfficers: [],
  memberships: [],
  locations: [],
  categories: [],
  events: [],
  registrations: [],
  attendance: [],
  approvals: [],
  reports: [],
};

const state = {
  role: "student",
  search: "",
  category: "all",
  status: "all",
  activeTable: "events",
};

const roleProfiles = {
  student: {
    title: "Student workspace",
    description:
      "Browse upcoming events, track registrations, and stay close to the organizations you belong to.",
    primaryAction: "Register for an event",
    secondaryAction: "Review attendance history",
    focusTitle: "Student involvement snapshot",
  },
  officer: {
    title: "Organization officer workspace",
    description:
      "Manage event activity, monitor membership, and keep approval-ready submissions moving without friction.",
    primaryAction: "Create event draft",
    secondaryAction: "Manage roster",
    focusTitle: "Officer operations board",
  },
  admin: {
    title: "University administrator workspace",
    description:
      "Review submissions, watch organization health, and turn campus activity into clear reporting signals.",
    primaryAction: "Review approvals",
    secondaryAction: "Generate report",
    focusTitle: "Administrative oversight",
  },
};

const arrays = [
  "students",
  "administrators",
  "organizations",
  "organizationOfficers",
  "memberships",
  "locations",
  "categories",
  "events",
  "registrations",
  "attendance",
  "approvals",
  "reports",
];

const roleButtons = document.getElementById("roleButtons");
const categoryFilter = document.getElementById("categoryFilter");
const statusFilter = document.getElementById("statusFilter");
const searchInput = document.getElementById("searchInput");
const eventsGrid = document.getElementById("eventsGrid");
const eventSummary = document.getElementById("eventSummary");
const heroStats = document.getElementById("heroStats");
const roleTitle = document.getElementById("roleTitle");
const roleDescription = document.getElementById("roleDescription");
const primaryAction = document.getElementById("primaryAction");
const secondaryAction = document.getElementById("secondaryAction");
const pulseCards = document.getElementById("pulseCards");
const entityPills = document.getElementById("entityPills");
const focusTitle = document.getElementById("focusTitle");
const focusCards = document.getElementById("focusCards");
const activityFeed = document.getElementById("activityFeed");
const tableButtons = document.getElementById("tableButtons");
const tableDescription = document.getElementById("tableDescription");
const tableHead = document.getElementById("tableHead");
const tableBody = document.getElementById("tableBody");
const categoryBars = document.getElementById("categoryBars");
const reportCards = document.getElementById("reportCards");
const termLabel = document.getElementById("termLabel");

init();

async function init() {
  await loadData();
  hydrateInitialRole();
  populateFilters();
  bindEvents();
  render();
  setupReveal();
}

async function loadData() {
  try {
    const response = await fetch("/api/dashboard");

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    data = normalizeDashboardData(await response.json());
  } catch (error) {
    console.error("Failed to load dashboard data:", error);
    eventSummary.textContent = "Dashboard data could not be loaded.";
    eventsGrid.innerHTML = emptyCard("Unable to load dashboard data", "Check the database connection and refresh.");
  }
}

function normalizeDashboardData(rawData) {
  const normalized = { ...data, ...rawData };
  arrays.forEach((key) => {
    normalized[key] = Array.isArray(normalized[key]) ? normalized[key] : [];
  });
  normalized.academicTerm = normalized.academicTerm || {};
  normalized.currentUser = normalized.currentUser || {};
  return normalized;
}

function hydrateInitialRole() {
  if (roleProfiles[data.currentUser.role]) {
    state.role = data.currentUser.role;
  }
}

function bindEvents() {
  searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderEvents();
  });

  categoryFilter.addEventListener("change", (event) => {
    state.category = event.target.value;
    renderEvents();
  });

  statusFilter.addEventListener("change", (event) => {
    state.status = event.target.value;
    renderEvents();
  });

  primaryAction.addEventListener("click", () => handleHeroAction("primary"));
  secondaryAction.addEventListener("click", () => handleHeroAction("secondary"));

  document.querySelectorAll("[data-scroll-target]").forEach((button) => {
    button.addEventListener("click", () => {
      scrollToSection(button.dataset.scrollTarget);
    });
  });
}

function populateFilters() {
  const categoryOptions = [
    ["all", "All categories"],
    ...data.categories.map((category) => [category.categoryId, category.categoryName]),
  ];
  categoryFilter.innerHTML = categoryOptions
    .map(([value, label]) => `<option value="${escapeAttribute(value)}">${escapeHtml(label)}</option>`)
    .join("");

  const statuses = [...new Set(data.events.map((event) => event.eventStatus).filter(Boolean))].sort();
  const statusOptions = [["all", "All statuses"], ...statuses.map((status) => [status, status])];
  statusFilter.innerHTML = statusOptions
    .map(([value, label]) => `<option value="${escapeAttribute(value)}">${escapeHtml(label)}</option>`)
    .join("");
}

function render() {
  renderHero();
  renderRoleButtons();
  renderPulse();
  renderEntityPills();
  renderEvents();
  renderFocusCards();
  renderActivityFeed();
  renderTableBrowser();
  renderCategoryBars();
  renderReports();
  renderTermLabel();
}

function renderRoleButtons() {
  roleButtons.innerHTML = Object.keys(roleProfiles)
    .map((role) => {
      const label = role === "admin" ? "Administrator" : capitalize(role);
      const classes = role === state.role ? "role-button is-active" : "role-button";
      return `<button type="button" class="${classes}" data-role="${role}">${label}</button>`;
    })
    .join("");

  roleButtons.querySelectorAll("[data-role]").forEach((button) => {
    button.addEventListener("click", () => {
      state.role = button.dataset.role;
      render();
    });
  });
}

function renderHero() {
  const profile = roleProfiles[state.role];
  roleTitle.textContent = profile.title;
  roleDescription.textContent = profile.description;
  primaryAction.textContent = profile.primaryAction;
  secondaryAction.textContent = profile.secondaryAction;

  heroStats.innerHTML = getRoleStats(state.role)
    .map(
      (stat) => `
        <article class="stat-card">
          <span class="stat-label">${escapeHtml(stat.label)}</span>
          <strong class="stat-value">${escapeHtml(stat.value)}</strong>
        </article>
      `
    )
    .join("");
}

function renderPulse() {
  const upcomingEvents = data.events.filter((event) =>
    ["Approved", "Scheduled", "Submitted"].includes(event.eventStatus)
  ).length;
  const activeOrgs = data.organizations.filter((org) => org.orgStatus === "Active").length;
  const pendingApprovals = data.approvals.filter((approval) => approval.decisionStatus === "Pending").length;
  const activeRegistrations = data.registrations.filter(
    (registration) => registration.registrationStatus === "Registered"
  ).length;

  const cards = [
    { label: "Upcoming events", value: upcomingEvents },
    { label: "Active organizations", value: activeOrgs },
    { label: "Pending approvals", value: pendingApprovals },
    { label: "Registered seats", value: activeRegistrations },
  ];

  pulseCards.innerHTML = cards
    .map(
      (card) => `
        <article class="pulse-card">
          <span class="pulse-label">${escapeHtml(card.label)}</span>
          <strong class="pulse-value">${escapeHtml(card.value)}</strong>
        </article>
      `
    )
    .join("");
}

function renderEntityPills() {
  const entities = [
    ["Students", data.students.length],
    ["Organizations", data.organizations.length],
    ["Events", data.events.length],
    ["Registrations", data.registrations.length],
    ["Attendance", data.attendance.length],
    ["Approvals", data.approvals.length],
    ["Reports", data.reports.length],
  ];

  entityPills.innerHTML = entities
    .map(([label, value]) => `<span class="entity-pill">${escapeHtml(label)}: ${escapeHtml(value)}</span>`)
    .join("");
}

function renderEvents() {
  const events = getFilteredEvents();
  eventSummary.textContent = `${events.length} event${events.length === 1 ? "" : "s"} match the current filters for the ${capitalize(state.role)} view.`;

  if (!events.length) {
    eventsGrid.innerHTML = emptyCard("No matching events", "Try another category, status, or search term.");
    return;
  }

  eventsGrid.innerHTML = events
    .map((event) => {
      const registeredCount = data.registrations.filter(
        (registration) =>
          idsMatch(registration.eventId, event.eventId) && registration.registrationStatus === "Registered"
      ).length;
      const capacity = Number(event.capacity);
      const hasCapacity = Number.isFinite(capacity) && capacity > 0;
      const fillRate = hasCapacity ? Math.min(100, Math.round((registeredCount / capacity) * 100)) : 0;
      const location = getLocation(event.locationId);
      const capacityLabel = hasCapacity ? `${registeredCount}/${capacity} seats` : `${registeredCount} registered`;
      const metaTone = event.eventStatus === "Rejected" ? "warn" : event.eventStatus === "Submitted" ? "alt" : "";

      return `
        <article class="event-card">
          <div class="meta-row">
            <span class="meta-chip">${escapeHtml(getCategoryName(event.categoryId))}</span>
            <span class="meta-chip ${metaTone}">${escapeHtml(event.eventStatus || "No status")}</span>
          </div>
          <div>
            <h4>${escapeHtml(event.title || "Untitled event")}</h4>
            <p class="event-meta">${escapeHtml(event.description || "No description provided.")}</p>
          </div>
          <div class="event-meta">
            <strong>${escapeHtml(getOrgName(event.orgId))}</strong><br />
            ${escapeHtml(formatDate(event.startDateTime, true))}<br />
            ${escapeHtml(location.locationName)}${location.isVirtual ? " | virtual" : ""}
          </div>
          <div class="meta-row">
            <span class="meta-chip alt">${escapeHtml(capacityLabel)}</span>
            ${hasCapacity ? `<span class="meta-chip">Fill ${fillRate}%</span>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderFocusCards() {
  focusTitle.textContent = roleProfiles[state.role].focusTitle;

  focusCards.innerHTML = getFocusData(state.role)
    .map(
      (card) => `
        <article class="focus-card">
          <span class="focus-label">${escapeHtml(card.label)}</span>
          <h4>${escapeHtml(card.title)}</h4>
          ${card.value ? `<strong class="focus-value">${escapeHtml(card.value)}</strong>` : ""}
          ${
            card.items && card.items.length
              ? `<ul class="focus-list">${card.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
              : `<p class="mini-text">${escapeHtml(card.copy || "No records are available yet.")}</p>`
          }
        </article>
      `
    )
    .join("");
}

function renderActivityFeed() {
  activityFeed.innerHTML = getActivityItems(state.role)
    .map(
      (item) => `
        <article class="activity-item">
          <span class="activity-title">${escapeHtml(item.title)}</span>
          <div class="activity-copy">${escapeHtml(item.copy)}</div>
        </article>
      `
    )
    .join("");
}

function renderTableBrowser() {
  const tableConfig = getTableConfig();

  tableButtons.innerHTML = Object.entries(tableConfig)
    .map(([key, config]) => {
      const classes = key === state.activeTable ? "table-button is-active" : "table-button";
      return `<button type="button" class="${classes}" data-table="${key}">${escapeHtml(config.label)}</button>`;
    })
    .join("");

  tableButtons.querySelectorAll("[data-table]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTable = button.dataset.table;
      renderTableBrowser();
    });
  });

  const activeConfig = tableConfig[state.activeTable] || tableConfig.events;
  tableDescription.textContent = activeConfig.description;
  tableHead.innerHTML = `<tr>${activeConfig.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;

  if (!activeConfig.rows.length) {
    tableBody.innerHTML = `<tr><td colspan="${activeConfig.columns.length}">No records found.</td></tr>`;
    return;
  }

  tableBody.innerHTML = activeConfig.rows
    .map((row) => `<tr>${row.map((value) => `<td>${escapeHtml(formatCell(value))}</td>`).join("")}</tr>`)
    .join("");
}

function renderCategoryBars() {
  const upcoming = data.events.filter((event) => event.eventStatus !== "Rejected");
  const totals = data.categories.map((category) => {
    const count = upcoming.filter((event) => idsMatch(event.categoryId, category.categoryId)).length;
    return {
      label: category.categoryName,
      value: count,
      width: upcoming.length ? Math.round((count / upcoming.length) * 100) : 0,
    };
  });

  if (!totals.length) {
    categoryBars.innerHTML = emptyCard("No categories found", "Categories will appear here after they are added.");
    return;
  }

  categoryBars.innerHTML = totals
    .map(
      (item) => `
        <article class="bar-item">
          <div class="bar-head">
            <span>${escapeHtml(item.label)}</span>
            <span>${item.value} event${item.value === 1 ? "" : "s"}</span>
          </div>
          <div class="bar-line">
            <div class="bar-fill" style="width: ${item.width}%"></div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderReports() {
  if (!data.reports.length) {
    reportCards.innerHTML = emptyCard("No reports found", "Generated summaries will appear here.");
    return;
  }

  reportCards.innerHTML = data.reports
    .map(
      (report) => `
        <article class="report-card">
          <span class="report-label">${escapeHtml(report.reportType || "Report")}</span>
          <h4>${escapeHtml(report.summary || "No summary provided.")}</h4>
          <div class="report-meta">
            ${escapeHtml(formatDate(report.generatedAt, true))} | ${escapeHtml(getAdminName(report.generatedByAdminId))}
          </div>
        </article>
      `
    )
    .join("");
}

function renderTermLabel() {
  if (!data.academicTerm.termName) {
    termLabel.textContent = "No academic term is currently available.";
    return;
  }

  termLabel.textContent = `${data.academicTerm.termName} | ${formatDate(data.academicTerm.startDate)} to ${formatDate(data.academicTerm.endDate)}`;
}

function getTableConfig() {
  return {
    students: {
      label: "STUDENT",
      description: "Core student accounts used for memberships, registrations, and attendance history.",
      columns: ["StudentID", "Name", "Email", "ClassYear", "Major", "AccountStatus"],
      rows: data.students.map((student) => [
        student.studentId,
        `${student.firstName || ""} ${student.lastName || ""}`.trim(),
        student.email,
        student.classYear,
        student.major,
        student.accountStatus,
      ]),
    },
    organizations: {
      label: "ORGANIZATION",
      description: "Student organizations with status, contact info, and hosted event ownership.",
      columns: ["OrgID", "OrgName", "Status", "ContactEmail", "Description"],
      rows: data.organizations.map((org) => [
        org.orgId,
        org.orgName,
        org.orgStatus,
        org.contactEmail,
        org.description,
      ]),
    },
    events: {
      label: "EVENT",
      description: "Event records linked to an organization, location, category, and academic term.",
      columns: ["EventID", "Title", "Organization", "Category", "Location", "Status", "Capacity"],
      rows: data.events.map((event) => [
        event.eventId,
        event.title,
        getOrgName(event.orgId),
        getCategoryName(event.categoryId),
        getLocationName(event.locationId),
        event.eventStatus,
        event.capacity,
      ]),
    },
    registrations: {
      label: "REGISTRATION",
      description: "Student-to-event registration records with timing and waitlist visibility.",
      columns: ["Student", "Event", "RegisteredAt", "Status"],
      rows: data.registrations.map((registration) => [
        getStudentName(registration.studentId),
        getEventTitle(registration.eventId),
        formatDate(registration.registeredAt, true),
        registration.registrationStatus,
      ]),
    },
    approvals: {
      label: "APPROVAL",
      description: "Administrative review data for submitted events and their final decisions.",
      columns: ["Event", "SubmittedBy", "ReviewedBy", "DecisionStatus", "SubmittedAt", "Notes"],
      rows: data.approvals.map((approval) => [
        getEventTitle(approval.eventId),
        getStudentName(approval.submittedByOfficerStudentId),
        approval.reviewedByAdminId ? getAdminName(approval.reviewedByAdminId) : "Pending review",
        approval.decisionStatus,
        formatDate(approval.submittedAt, true),
        approval.decisionNotes,
      ]),
    },
    attendance: {
      label: "ATTENDANCE",
      description: "Check-in tracking for completed events, recorded by organization officers.",
      columns: ["Student", "Event", "CheckInTime", "AttendanceFlag", "RecordedBy"],
      rows: data.attendance.map((entry) => [
        getStudentName(entry.studentId),
        getEventTitle(entry.eventId),
        formatDate(entry.checkInTime, true),
        entry.attendanceFlag,
        `${getStudentName(entry.recordedByOfficerStudentId)} / ${getOrgName(entry.recordedByOfficerOrgId)}`,
      ]),
    },
  };
}

function getFilteredEvents() {
  return data.events.filter((event) => {
    const location = getLocationName(event.locationId).toLowerCase();
    const organization = getOrgName(event.orgId).toLowerCase();
    const title = String(event.title || "").toLowerCase();
    const description = String(event.description || "").toLowerCase();
    const matchesSearch =
      !state.search ||
      title.includes(state.search) ||
      description.includes(state.search) ||
      location.includes(state.search) ||
      organization.includes(state.search);
    const matchesCategory = state.category === "all" || idsMatch(event.categoryId, state.category);
    const matchesStatus = state.status === "all" || event.eventStatus === state.status;

    if (state.role === "student" && !["Approved", "Scheduled"].includes(event.eventStatus)) {
      return false;
    }

    if (state.role === "officer" && !["Approved", "Scheduled", "Submitted"].includes(event.eventStatus)) {
      return false;
    }

    return matchesSearch && matchesCategory && matchesStatus;
  });
}

function getRoleStats(role) {
  if (role === "student") {
    const student = getFeaturedStudent();
    const studentId = student?.studentId;
    const registered = countRegistrationsForStudent(studentId);
    const memberships = data.memberships.filter(
      (membership) => idsMatch(membership.studentId, studentId) && !membership.leaveDate
    ).length;
    const attendance = data.attendance.filter((entry) => idsMatch(entry.studentId, studentId)).length;

    return [
      { label: "Active registrations", value: registered },
      { label: "Organization memberships", value: memberships },
      { label: "Checked-in events", value: attendance },
      { label: "Upcoming commitments", value: registered },
    ];
  }

  if (role === "officer") {
    const context = getOfficerContext();

    return [
      { label: "Events under management", value: context.orgEvents.length },
      { label: "Active members", value: context.roster.length },
      { label: "Pending approvals", value: context.pendingApprovals },
      { label: "Registered seats", value: context.registeredSeats },
    ];
  }

  const activeOrgs = data.organizations.filter((org) => org.orgStatus === "Active").length;
  const scheduledEvents = data.events.filter((event) =>
    ["Approved", "Scheduled"].includes(event.eventStatus)
  ).length;
  const pendingApprovals = data.approvals.filter((approval) => approval.decisionStatus === "Pending").length;

  return [
    { label: "Active organizations", value: activeOrgs },
    { label: "Scheduled events", value: scheduledEvents },
    { label: "Pending approvals", value: pendingApprovals },
    { label: "Generated reports", value: data.reports.length },
  ];
}

function getFocusData(role) {
  if (role === "student") {
    const student = getFeaturedStudent();
    const studentId = student?.studentId;
    const memberships = data.memberships
      .filter((membership) => idsMatch(membership.studentId, studentId) && !membership.leaveDate)
      .map((membership) => `${getOrgName(membership.orgId)} | ${membership.memberRole || "Member"}`);

    const registrations = data.registrations
      .filter((registration) => idsMatch(registration.studentId, studentId))
      .map((registration) => `${getEventTitle(registration.eventId)} | ${registration.registrationStatus}`);

    return [
      {
        label: "Featured student",
        title: student ? getStudentName(student.studentId) : "No student records",
        copy: "This card follows the logged-in student when available, otherwise it uses the first student with activity.",
      },
      {
        label: "Current memberships",
        title: `${memberships.length} active organization${memberships.length === 1 ? "" : "s"}`,
        items: memberships,
        copy: "No active memberships found.",
      },
      {
        label: "Registration trail",
        title: `${registrations.length} tracked event record${registrations.length === 1 ? "" : "s"}`,
        items: registrations,
        copy: "No registrations found.",
      },
    ];
  }

  if (role === "officer") {
    const context = getOfficerContext();

    if (!context.officer) {
      return [
        {
          label: "Officer profile",
          title: "No active officer records",
          copy: "Assign an organization officer role to populate this workspace.",
        },
      ];
    }

    return [
      {
        label: "Officer profile",
        title: `${getStudentName(context.officer.studentId)} | ${context.officer.roleTitle}`,
        copy: `${context.org.orgName} is shown as the working organization for the officer dashboard.`,
      },
      {
        label: "Managed event load",
        title: `${context.orgEvents.length} event${context.orgEvents.length === 1 ? "" : "s"} in the pipeline`,
        items: context.orgEvents.map((event) => `${event.title} | ${event.eventStatus}`),
        copy: "No events are assigned to this officer organization yet.",
      },
      {
        label: "Roster preview",
        title: `${context.roster.length} active member${context.roster.length === 1 ? "" : "s"}`,
        items: context.roster.map((membership) => `${getStudentName(membership.studentId)} | ${membership.memberRole || "Member"}`),
        copy: "No active roster records found.",
      },
    ];
  }

  const pending = data.approvals
    .filter((approval) => approval.decisionStatus === "Pending")
    .map((approval) => `${getEventTitle(approval.eventId)} | ${approval.decisionNotes || "Awaiting review"}`);
  const orgHealth = data.organizations.map((org) => `${org.orgName} | ${org.orgStatus}`);
  const reportTypes = data.reports.map((report) => `${report.reportType} | ${formatDate(report.generatedAt, true)}`);

  return [
    {
      label: "Approval queue",
      title: `${pending.length} submission${pending.length === 1 ? "" : "s"} need review`,
      items: pending,
      copy: "No pending approvals right now.",
    },
    {
      label: "Organization status",
      title: `${data.organizations.length} tracked organization${data.organizations.length === 1 ? "" : "s"}`,
      items: orgHealth,
      copy: "No organizations found.",
    },
    {
      label: "Reporting stream",
      title: `${data.reports.length} recent report${data.reports.length === 1 ? "" : "s"}`,
      items: reportTypes,
      copy: "No reports are currently available.",
    },
  ];
}

function getActivityItems(role) {
  const busiestEvent = [...data.events].sort(
    (a, b) => countRegistrationsForEvent(b.eventId) - countRegistrationsForEvent(a.eventId)
  )[0];
  const latestApproval = data.approvals[0];
  const latestAttendance = [...data.attendance].sort(
    (a, b) => parseDateValue(b.checkInTime).getTime() - parseDateValue(a.checkInTime).getTime()
  )[0];

  const items = [
    busiestEvent
      ? {
          title: "Registration opened",
          copy: `${busiestEvent.title} has ${countRegistrationsForEvent(busiestEvent.eventId)} registered student${countRegistrationsForEvent(busiestEvent.eventId) === 1 ? "" : "s"}.`,
        }
      : { title: "Registration opened", copy: "No event registrations are currently available." },
    latestApproval
      ? {
          title: "Approval checkpoint",
          copy: `${getEventTitle(latestApproval.eventId)} is marked ${latestApproval.decisionStatus}.`,
        }
      : { title: "Approval checkpoint", copy: "No approval records are currently available." },
    latestAttendance
      ? {
          title: "Attendance captured",
          copy: `${getEventTitle(latestAttendance.eventId)} has ${countAttendanceForEvent(latestAttendance.eventId)} attendance record${countAttendanceForEvent(latestAttendance.eventId) === 1 ? "" : "s"}.`,
        }
      : { title: "Attendance captured", copy: "No attendance records are currently available." },
  ];

  if (role === "officer") {
    const context = getOfficerContext();
    items.unshift({
      title: "Roster movement",
      copy: context.org
        ? `${context.org.orgName} has ${context.roster.length} active member${context.roster.length === 1 ? "" : "s"} on file.`
        : "No active officer organization is available yet.",
    });
  }

  if (role === "admin") {
    items.unshift({
      title: "Report generated",
      copy: data.reports.length
        ? `${data.reports[0].reportType} was generated on ${formatDate(data.reports[0].generatedAt, true)}.`
        : "No reports are currently available.",
    });
  }

  if (role === "student") {
    const student = getFeaturedStudent();
    items.unshift({
      title: "Personal schedule",
      copy: student
        ? `${getStudentName(student.studentId)} is registered for ${countRegistrationsForStudent(student.studentId)} event${countRegistrationsForStudent(student.studentId) === 1 ? "" : "s"}.`
        : "No student records are currently available.",
    });
  }

  return items;
}

function getFeaturedStudent() {
  if (data.currentUser.studentId) {
    const current = data.students.find((student) => idsMatch(student.studentId, data.currentUser.studentId));
    if (current) {
      return current;
    }
  }

  return (
    data.students.find((student) =>
      data.registrations.some((registration) => idsMatch(registration.studentId, student.studentId))
    ) || data.students[0]
  );
}

function getOfficerContext() {
  const currentOfficer = data.currentUser.studentId
    ? data.organizationOfficers.find(
        (entry) => idsMatch(entry.studentId, data.currentUser.studentId) && !entry.endDate
      )
    : null;
  const officer = currentOfficer || data.organizationOfficers.find((entry) => !entry.endDate) || data.organizationOfficers[0];
  const org = officer ? getOrg(officer.orgId) || { orgName: fallbackId(officer.orgId) } : null;
  const orgEvents = officer ? data.events.filter((event) => idsMatch(event.orgId, officer.orgId)) : [];
  const roster = officer
    ? data.memberships.filter((membership) => idsMatch(membership.orgId, officer.orgId) && !membership.leaveDate)
    : [];
  const pendingApprovals = officer
    ? data.approvals.filter(
        (approval) => idsMatch(approval.submittedByOfficerOrgId, officer.orgId) && approval.decisionStatus === "Pending"
      ).length
    : 0;
  const registeredSeats = data.registrations.filter(
    (registration) =>
      orgEvents.some((event) => idsMatch(event.eventId, registration.eventId)) &&
      registration.registrationStatus === "Registered"
  ).length;

  return {
    officer,
    org,
    orgEvents,
    roster,
    pendingApprovals,
    registeredSeats,
  };
}

function handleHeroAction(action) {
  const loggedInRole = data.currentUser.role;
  const routeMap = {
    student: { primary: "/my-signups", secondary: "/my-signups" },
    officer: { primary: "/create-event", secondary: "/officer-dashboard" },
    admin: { primary: "/admin-dashboard", secondary: "/admin-dashboard" },
  };

  if (loggedInRole === state.role && routeMap[state.role]?.[action]) {
    window.location.href = routeMap[state.role][action];
    return;
  }

  scrollToSection(action === "primary" ? "eventExplorer" : "operationsPanel");
}

function getStudentName(studentId) {
  const student = data.students.find((entry) => idsMatch(entry.studentId, studentId));
  return student ? `${student.firstName} ${student.lastName}` : fallbackId(studentId);
}

function getAdminName(adminId) {
  const admin = data.administrators.find((entry) => idsMatch(entry.adminId, adminId));
  return admin ? `${admin.firstName} ${admin.lastName}` : fallbackId(adminId, "System generated");
}

function getOrgName(orgId) {
  const org = getOrg(orgId);
  return org ? org.orgName : fallbackId(orgId);
}

function getOrg(orgId) {
  return data.organizations.find((entry) => idsMatch(entry.orgId, orgId));
}

function getCategoryName(categoryId) {
  const category = data.categories.find((entry) => idsMatch(entry.categoryId, categoryId));
  return category ? category.categoryName : fallbackId(categoryId);
}

function getEventTitle(eventId) {
  const event = data.events.find((entry) => idsMatch(entry.eventId, eventId));
  return event ? event.title : fallbackId(eventId);
}

function getLocation(locationId) {
  return data.locations.find((entry) => idsMatch(entry.locationId, locationId)) || {
    locationName: fallbackId(locationId, "Location not set"),
    isVirtual: false,
  };
}

function getLocationName(locationId) {
  return getLocation(locationId).locationName;
}

function countRegistrationsForStudent(studentId) {
  return data.registrations.filter(
    (registration) => idsMatch(registration.studentId, studentId) && registration.registrationStatus === "Registered"
  ).length;
}

function countRegistrationsForEvent(eventId) {
  return data.registrations.filter(
    (registration) => idsMatch(registration.eventId, eventId) && registration.registrationStatus === "Registered"
  ).length;
}

function countAttendanceForEvent(eventId) {
  return data.attendance.filter((entry) => idsMatch(entry.eventId, eventId)).length;
}

function formatDate(value, withTime = false) {
  const dateValue = parseDateValue(value);
  if (Number.isNaN(dateValue.getTime())) {
    return "Not set";
  }

  const formatter = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(withTime
      ? {
          hour: "numeric",
          minute: "2-digit",
        }
      : {}),
  });

  return formatter.format(dateValue);
}

function parseDateValue(value) {
  if (!value) {
    return new Date(Number.NaN);
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const [year, month, day] = String(value).split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  return new Date(value);
}

function idsMatch(left, right) {
  return String(left ?? "") === String(right ?? "");
}

function fallbackId(value, fallback = "Unknown") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function formatCell(value) {
  return value === null || value === undefined || value === "" ? "Not set" : value;
}

function emptyCard(title, copy) {
  return `
    <article class="event-card">
      <h4>${escapeHtml(title)}</h4>
      <p class="event-meta">${escapeHtml(copy)}</p>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

function setupReveal() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    },
    {
      threshold: 0.15,
    }
  );

  document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));
}
