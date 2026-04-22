let data = {
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
  reports: []
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

function getTableConfig() {
  return {
    students: {
      label: "STUDENT",
      description: "Core student accounts used for memberships, registrations, and attendance history.",
      columns: ["StudentID", "Name", "Email", "ClassYear", "Major", "AccountStatus"],
      rows: data.students.map((student) => [
        student.studentId,
        `${student.firstName} ${student.lastName}`,
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

    data = await response.json();
  } catch (error) {
    console.error("Failed to load dashboard data:", error);
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

  primaryAction.addEventListener("click", () => scrollToSection("eventExplorer"));
  secondaryAction.addEventListener("click", () => scrollToSection("operationsPanel"));

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
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join("");

  const statusOptions = [
    ["all", "All statuses"],
    ...["Approved", "Scheduled", "Submitted", "Rejected"].map((status) => [status, status]),
  ];
  statusFilter.innerHTML = statusOptions
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
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
  termLabel.textContent = `${data.academicTerm.termName} | ${formatDate(data.academicTerm.startDate)} to ${formatDate(data.academicTerm.endDate)}`;
}

function renderRoleButtons() {
  const roles = Object.keys(roleProfiles);

  roleButtons.innerHTML = roles
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

  const stats = getRoleStats(state.role);
  heroStats.innerHTML = stats
    .map(
      (stat) => `
        <article class="stat-card">
          <span class="stat-label">${stat.label}</span>
          <strong class="stat-value">${stat.value}</strong>
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
          <span class="pulse-label">${card.label}</span>
          <strong class="pulse-value">${card.value}</strong>
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
    .map(([label, value]) => `<span class="entity-pill">${label}: ${value}</span>`)
    .join("");
}

function renderEvents() {
  const events = getFilteredEvents();
  eventSummary.textContent = `${events.length} events match the current filters for the ${capitalize(state.role)} view.`;

  if (!events.length) {
    eventsGrid.innerHTML = `
      <article class="event-card">
        <h4>No matching events</h4>
        <p class="event-meta">Try another category, status, or search term.</p>
      </article>
    `;
    return;
  }

  eventsGrid.innerHTML = events
    .map((event) => {
      const registeredCount = data.registrations.filter(
        (registration) =>
          registration.eventId === event.eventId && registration.registrationStatus === "Registered"
      ).length;
      const fillRate = Math.round((registeredCount / event.capacity) * 100);
      const location = getLocation(event.locationId);
      const capacityLabel = `${registeredCount}/${event.capacity} seats`;
      const metaTone = event.eventStatus === "Rejected" ? "warn" : event.eventStatus === "Submitted" ? "alt" : "";

      return `
        <article class="event-card">
          <div class="meta-row">
            <span class="meta-chip">${getCategoryName(event.categoryId)}</span>
            <span class="meta-chip ${metaTone}">${event.eventStatus}</span>
          </div>
          <div>
            <h4>${event.title}</h4>
            <p class="event-meta">${event.description}</p>
          </div>
          <div class="event-meta">
            <strong>${getOrgName(event.orgId)}</strong><br />
            ${formatDate(event.startDateTime, true)}<br />
            ${location.locationName}${location.isVirtual ? " | virtual" : ""}
          </div>
          <div class="meta-row">
            <span class="meta-chip alt">${capacityLabel}</span>
            <span class="meta-chip">Fill ${fillRate}%</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderFocusCards() {
  focusTitle.textContent = roleProfiles[state.role].focusTitle;

  const focusData = getFocusData(state.role);
  focusCards.innerHTML = focusData
    .map(
      (card) => `
        <article class="focus-card">
          <span class="focus-label">${card.label}</span>
          <h4>${card.title}</h4>
          ${card.value ? `<strong class="focus-value">${card.value}</strong>` : ""}
          ${
            card.items && card.items.length
              ? `<ul class="focus-list">${card.items.map((item) => `<li>${item}</li>`).join("")}</ul>`
              : `<p class="mini-text">${card.copy}</p>`
          }
        </article>
      `
    )
    .join("");
}

function renderActivityFeed() {
  const items = getActivityItems(state.role);
  activityFeed.innerHTML = items
    .map(
      (item) => `
        <article class="activity-item">
          <span class="activity-title">${item.title}</span>
          <div class="activity-copy">${item.copy}</div>
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
      return `<button type="button" class="${classes}" data-table="${key}">${config.label}</button>`;
    })
    .join("");

  tableButtons.querySelectorAll("[data-table]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTable = button.dataset.table;
      renderTableBrowser();
    });
  });

  const activeConfig = tableConfig[state.activeTable];
  tableDescription.textContent = activeConfig.description;
  tableHead.innerHTML = `<tr>${activeConfig.columns.map((column) => `<th>${column}</th>`).join("")}</tr>`;
  tableBody.innerHTML = activeConfig.rows
    .map((row) => `<tr>${row.map((value) => `<td>${value}</td>`).join("")}</tr>`)
    .join("");
}

function renderCategoryBars() {
  const upcoming = data.events.filter((event) => event.eventStatus !== "Rejected");
  const totals = data.categories.map((category) => {
    const count = upcoming.filter((event) => event.categoryId === category.categoryId).length;
    return {
      label: category.categoryName,
      value: count,
      width: upcoming.length ? Math.round((count / upcoming.length) * 100) : 0,
    };
  });

  categoryBars.innerHTML = totals
    .map(
      (item) => `
        <article class="bar-item">
          <div class="bar-head">
            <span>${item.label}</span>
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
  const reports = Array.isArray(data.reports) ? data.reports : [];

  reportCards.innerHTML = reports
    .map(
      (report) => `
        <article class="report-card">
          <span class="report-label">${report.reportType}</span>
          <h4>${report.summary}</h4>
          <div class="report-meta">
            ${formatDate(report.generatedAt, true)} | ${getAdminName(report.generatedByAdminId)}
          </div>
        </article>
      `
    )
    .join("");
}

function getFilteredEvents() {
  return data.events.filter((event) => {
    const location = getLocationName(event.locationId).toLowerCase();
    const organization = getOrgName(event.orgId).toLowerCase();
    const matchesSearch =
      !state.search ||
      event.title.toLowerCase().includes(state.search) ||
      event.description.toLowerCase().includes(state.search) ||
      location.includes(state.search) ||
      organization.includes(state.search);
    const matchesCategory = state.category === "all" || event.categoryId === state.category;
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
  const featuredStudent = "STU-102";
  const featuredOfficer = "STU-102";

  if (role === "student") {
    const registered = data.registrations.filter(
      (registration) =>
        registration.studentId === featuredStudent && registration.registrationStatus === "Registered"
    ).length;
    const memberships = data.memberships.filter(
      (membership) => membership.studentId === featuredStudent && !membership.leaveDate
    ).length;
    const attendance = data.attendance.filter((entry) => entry.studentId === featuredStudent).length;
    const upcoming = data.events.filter((event) =>
      data.registrations.some(
        (registration) =>
          registration.studentId === featuredStudent &&
          registration.eventId === event.eventId &&
          registration.registrationStatus === "Registered"
      )
    ).length;

    return [
      { label: "Active registrations", value: registered },
      { label: "Organization memberships", value: memberships },
      { label: "Checked-in events", value: attendance },
      { label: "Upcoming commitments", value: upcoming },
    ];
  }

  if (role === "officer") {
    const officer = data.organizationOfficers.find((entry) => entry.studentId === featuredOfficer);
    const orgEvents = data.events.filter((event) => event.orgId === officer.orgId);
    const roster = data.memberships.filter((membership) => membership.orgId === officer.orgId && !membership.leaveDate);
    const pending = data.approvals.filter(
      (approval) => approval.submittedByOfficerOrgId === officer.orgId && approval.decisionStatus === "Pending"
    ).length;
    const seats = data.registrations.filter(
      (registration) =>
        orgEvents.some((event) => event.eventId === registration.eventId) &&
        registration.registrationStatus === "Registered"
    ).length;

    return [
      { label: "Events under management", value: orgEvents.length },
      { label: "Active members", value: roster.length },
      { label: "Pending approvals", value: pending },
      { label: "Registered seats", value: seats },
    ];
  }

  const activeOrgs = data.organizations.filter((org) => org.orgStatus === "Active").length;
  const scheduledEvents = data.events.filter((event) =>
    ["Approved", "Scheduled"].includes(event.eventStatus)
  ).length;
  const pendingApprovals = data.approvals.filter((approval) => approval.decisionStatus === "Pending").length;
  const generatedReports = data.reports.length;

  return [
    { label: "Active organizations", value: activeOrgs },
    { label: "Scheduled events", value: scheduledEvents },
    { label: "Pending approvals", value: pendingApprovals },
    { label: "Generated reports", value: generatedReports },
  ];
}

function getFocusData(role) {
  if (role === "student") {
    const studentId = "STU-102";
    const memberships = data.memberships
      .filter((membership) => membership.studentId === studentId && !membership.leaveDate)
      .map((membership) => `${getOrgName(membership.orgId)} | ${membership.memberRole}`);

    const registrations = data.registrations
      .filter((registration) => registration.studentId === studentId)
      .map((registration) => `${getEventTitle(registration.eventId)} | ${registration.registrationStatus}`);

    return [
      {
        label: "Featured student",
        title: getStudentName(studentId),
        copy: "A representative student view grounded in the CESOMS registration and attendance tables.",
      },
      {
        label: "Current memberships",
        title: `${memberships.length} active organizations`,
        items: memberships,
      },
      {
        label: "Registration trail",
        title: `${registrations.length} tracked event records`,
        items: registrations,
      },
    ];
  }

  if (role === "officer") {
    const officer = data.organizationOfficers.find((entry) => entry.studentId === "STU-102");
    const org = getOrg(officer.orgId);
    const orgEvents = data.events
      .filter((event) => event.orgId === officer.orgId)
      .map((event) => `${event.title} | ${event.eventStatus}`);
    const roster = data.memberships
      .filter((membership) => membership.orgId === officer.orgId && !membership.leaveDate)
      .map((membership) => `${getStudentName(membership.studentId)} | ${membership.memberRole}`);

    return [
      {
        label: "Officer profile",
        title: `${getStudentName(officer.studentId)} | ${officer.roleTitle}`,
        copy: `${org.orgName} is shown as the working organization for the officer dashboard.`,
      },
      {
        label: "Managed event load",
        title: `${orgEvents.length} events in the pipeline`,
        items: orgEvents,
      },
      {
        label: "Roster preview",
        title: `${roster.length} active members`,
        items: roster,
      },
    ];
  }

  const pending = data.approvals
    .filter((approval) => approval.decisionStatus === "Pending")
    .map((approval) => `${getEventTitle(approval.eventId)} | ${approval.decisionNotes}`);
  const orgHealth = data.organizations.map((org) => `${org.orgName} | ${org.orgStatus}`);
  const reportTypes = data.reports.map((report) => `${report.reportType} | ${formatDate(report.generatedAt, true)}`);

  return [
    {
      label: "Approval queue",
      title: `${pending.length} submissions need review`,
      items: pending,
    },
    {
      label: "Organization status",
      title: `${data.organizations.length} tracked organizations`,
      items: orgHealth,
    },
    {
      label: "Reporting stream",
      title: `${data.reports.length} recent reports`,
      items: reportTypes,
    },
  ];
}

function getActivityItems(role) {
  const items = [
    {
      title: "Registration opened",
      copy: `Career Lab Live added ${countRegistrationsForEvent("EVT-2405")} registered students this week.`,
    },
    {
      title: "Approval checkpoint",
      copy: `River Cleanup Day is still pending while transportation waivers are reviewed.`,
    },
    {
      title: "Attendance captured",
      copy: `Hack Night Studio already has ${countAttendanceForEvent("EVT-2401")} attendance records linked to the officer log.`,
    },
  ];

  if (role === "officer") {
    items.unshift({
      title: "Roster movement",
      copy: `${getOrgName("ORG-ACM")} has ${countMembersForOrg("ORG-ACM")} active members on file.`,
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
    items.unshift({
      title: "Personal schedule",
      copy: `${getStudentName("STU-102")} is registered for ${countRegistrationsForStudent("STU-102")} events.`,
    });
  }

  return items;
}

function getStudentName(studentId) {
  const student = data.students.find((entry) => entry.studentId === studentId);
  return student ? `${student.firstName} ${student.lastName}` : studentId;
}

function getAdminName(adminId) {
  const admin = data.administrators.find((entry) => entry.adminId === adminId);
  return admin ? `${admin.firstName} ${admin.lastName}` : adminId;
}

function getOrgName(orgId) {
  const org = getOrg(orgId);
  return org ? org.orgName : orgId;
}

function getOrg(orgId) {
  return data.organizations.find((entry) => entry.orgId === orgId);
}

function getCategoryName(categoryId) {
  const category = data.categories.find((entry) => entry.categoryId === categoryId);
  return category ? category.categoryName : categoryId;
}

function getEventTitle(eventId) {
  const event = data.events.find((entry) => entry.eventId === eventId);
  return event ? event.title : eventId;
}

function getLocation(locationId) {
  return data.locations.find((entry) => entry.locationId === locationId);
}

function getLocationName(locationId) {
  const location = getLocation(locationId);
  return location ? location.locationName : locationId;
}

function countRegistrationsForStudent(studentId) {
  return data.registrations.filter(
    (registration) => registration.studentId === studentId && registration.registrationStatus === "Registered"
  ).length;
}

function countRegistrationsForEvent(eventId) {
  return data.registrations.filter(
    (registration) => registration.eventId === eventId && registration.registrationStatus === "Registered"
  ).length;
}

function countAttendanceForEvent(eventId) {
  return data.attendance.filter((entry) => entry.eventId === eventId).length;
}

function countMembersForOrg(orgId) {
  return data.memberships.filter((membership) => membership.orgId === orgId && !membership.leaveDate).length;
}

function formatDate(value, withTime = false) {
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

  return formatter.format(parseDateValue(value));
}

function parseDateValue(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  return new Date(value);
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
