const loginForm = document.getElementById("login-form");
const loginSection = document.getElementById("login-section");
const dashboard = document.getElementById("dashboard-section");
const loginMessage = document.getElementById("login-message");
const resultMessage = document.getElementById("result-message");
const resultTitle = document.getElementById("result-title");
const sectionDescription = document.getElementById("section-description");
const results = document.getElementById("results");
const loginButton = document.getElementById("login-button");

let accessToken = null;
let employees = [];

async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: {
            Accept: "application/json",
            ...(options.headers || {}),
            ...(accessToken
                ? { Authorization: `Bearer ${accessToken}` }
                : {})
        }
    });

    const responseText = await response.text();
    let result = {};
    if (responseText) {
        try {
            result = JSON.parse(responseText);
        } catch {
            result = { detail: responseText };
        }
    }

    if (!response.ok) {
        throw new Error(
            result.detail || `Request failed (${response.status})`
        );
    }

    return result;
}

function setMessage(text, isError = false) {
    resultMessage.textContent = text;
    resultMessage.classList.toggle("error-message", isError);
    resultMessage.classList.toggle("success-message", !isError && Boolean(text));
}

function formatLabel(value) {
    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDateTime(value) {
    if (value == null || value === "") {
        return "—";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hourCycle: "h23"
    }).format(date);
}

function formatActivityValue(value) {
    if (value == null || value === "") {
        return "—";
    }

    if (Array.isArray(value)) {
        return value.length
            ? value.map(formatActivityValue).join("\n")
            : "—";
    }

    if (typeof value === "object") {
        const entries = Object.entries(value);
        return entries.length
            ? entries
                .map(([key, item]) => `${formatLabel(key)}: ${formatActivityValue(item)}`)
                .join("\n")
            : "—";
    }

    if (typeof value === "string" && /^\d{4}-\d\d-\d\dT/.test(value)) {
        return formatDateTime(value);
    }

    return String(value);
}

function addTable(container, heading, rows, columns, emptyMessage) {
    const section = document.createElement("section");
    section.className = "table-section";

    const title = document.createElement("h3");
    title.textContent = heading;
    section.append(title);

    if (!rows.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = emptyMessage;
        section.append(empty);
        container.append(section);
        return;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    const table = document.createElement("table");
    table.className = "data-table";
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");

    for (const column of columns) {
        const th = document.createElement("th");
        th.scope = "col";
        th.textContent = column.label;
        headerRow.append(th);
    }

    thead.append(headerRow);
    table.append(thead);

    const tbody = document.createElement("tbody");
    for (const row of rows) {
        const tr = document.createElement("tr");
        for (const column of columns) {
            const td = document.createElement("td");
            const value = row[column.key];
            td.textContent = column.format
                ? column.format(value, row)
                : formatActivityValue(value);
            if (column.key === "details" || column.key === "break_sessions") {
                td.className = "activity-details";
            }
            tr.append(td);
        }
        tbody.append(tr);
    }

    table.append(tbody);
    wrapper.append(table);
    section.append(wrapper);
    container.append(section);
}

function renderEmployees() {
    resultTitle.textContent = "Employees";
    sectionDescription.textContent =
        "Select an employee to view their profile, attendance, and activity.";
    results.replaceChildren();

    if (!employees.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "No employees found.";
        results.append(empty);
        return;
    }

    const count = document.createElement("p");
    count.className = "record-count";
    count.textContent = `${employees.length} employee(s)`;
    results.append(count);

    const grid = document.createElement("div");
    grid.className = "employee-grid";

    for (const employee of employees) {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "employee-card";
        card.setAttribute(
            "aria-label",
            `View details for ${employee.full_name || employee.user_id}`
        );

        const avatar = document.createElement("span");
        avatar.className = "employee-avatar";
        avatar.textContent = (employee.full_name || employee.user_id || "?")
            .trim()
            .charAt(0)
            .toUpperCase();

        const name = document.createElement("h3");
        name.textContent = employee.full_name || "Unnamed employee";

        const userId = document.createElement("p");
        userId.textContent = `ID: ${employee.user_id}`;

        const role = document.createElement("p");
        role.textContent = `Role: ${employee.role || "employee"}`;

        const status = document.createElement("span");
        status.className = employee.is_active
            ? "status-active"
            : "status-inactive";
        status.textContent = employee.is_active ? "Active" : "Inactive";

        const view = document.createElement("span");
        view.className = "view-profile";
        view.textContent = "View employee details →";

        card.append(avatar, name, userId, role, status, view);
        card.addEventListener("click", () => {
            loadEmployeeDetails(employee.user_id);
        });
        grid.append(card);
    }

    results.append(grid);
}

async function loadEmployees() {
    resultTitle.textContent = "Employees";
    sectionDescription.textContent =
        "Select an employee to view their profile, attendance, and activity.";
    setMessage("Loading employees...");
    results.replaceChildren();

    try {
        const result = await apiRequest("/admin/users");
        employees = result.users || [];
        renderEmployees();
        setMessage(`Loaded ${employees.length} employee(s).`);
    } catch (error) {
        employees = [];
        results.replaceChildren();
        setMessage(error.message, true);
    }
}

function dateKey(date) {
    return [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0")
    ].join("-");
}

function eventDateKey(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : dateKey(date);
}

function parseEventDate(value) {
    if (value == null || value === "") {
        return null;
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDurationHHMM(totalSeconds) {
    const seconds = Math.max(0, Math.floor(totalSeconds || 0));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function intervalFromDetails(details, startKeys, endKeys, timestamp) {
    const startValue = startKeys.map((key) => details?.[key]).find(Boolean);
    const endValue = endKeys.map((key) => details?.[key]).find(Boolean);
    let start = parseEventDate(startValue);
    let end = parseEventDate(endValue);
    const durationSeconds = Number(details?.duration_seconds);

    if (
        Number.isFinite(durationSeconds) &&
        durationSeconds > 0 &&
        start &&
        !end
    ) {
        end = new Date(start.getTime() + durationSeconds * 1000);
    } else if (
        !start &&
        timestamp &&
        Number.isFinite(durationSeconds) &&
        durationSeconds > 0
    ) {
        start = timestamp;
        end = new Date(start.getTime() + durationSeconds * 1000);
    }
    return start && end && end > start ? { start, end } : null;
}

function mergeIntervals(intervals) {
    const sorted = intervals
        .filter((interval) => interval.end > interval.start)
        .sort((left, right) => left.start - right.start);
    const merged = [];
    for (const interval of sorted) {
        const previous = merged[merged.length - 1];
        if (previous && interval.start <= previous.end) {
            previous.end = new Date(Math.max(
                previous.end.getTime(),
                interval.end.getTime()
            ));
        } else {
            merged.push({
                start: new Date(interval.start),
                end: new Date(interval.end)
            });
        }
    }
    return merged;
}

function clippedIntervals(intervals, start, end) {
    return mergeIntervals(intervals.map((interval) => ({
        start: new Date(Math.max(interval.start.getTime(), start.getTime())),
        end: new Date(Math.min(interval.end.getTime(), end.getTime()))
    })).filter((interval) => interval.end > interval.start));
}

function intervalSeconds(intervals) {
    return intervals.reduce(
        (total, interval) => total + (interval.end - interval.start) / 1000,
        0
    );
}

function getDailyAttendanceData(details, selectedDate) {
    const dayStart = new Date(`${selectedDate}T00:00:00`);
    const dayEnd = new Date(dayStart);
    dayEnd.setDate(dayEnd.getDate() + 1);
    const now = new Date();
    const sessions = (details.attendance || []).map((session) => ({
        ...session,
        start: parseEventDate(session.login_time),
        end: parseEventDate(session.logout_time) || now
    })).filter((session) => session.start && session.end > session.start);
    const daySessions = sessions.filter(
        (session) => session.start < dayEnd && session.end > dayStart
    );
    const sessionIntervals = mergeIntervals(daySessions.map((session) => ({
        start: new Date(Math.max(session.start.getTime(), dayStart.getTime())),
        end: new Date(Math.min(session.end.getTime(), dayEnd.getTime()))
    })));
    const logs = (details.logs || []).filter(
        (log) => log.employee_user_id === details.employee.user_id
    );
    const idleIntervals = [];
    const breakIntervals = [];
    const idleFallbacks = new Map();
    const summaryIdleFallbacks = new Map();
    const orderedLogs = logs
        .map((log) => ({ ...log, parsedTime: parseEventDate(log.event_timestamp) }))
        .filter((log) => log.parsedTime)
        .sort((left, right) => left.parsedTime - right.parsedTime);

    for (const log of orderedLogs) {
        const name = String(log.event_name || "").toUpperCase();
        const detailsValue = log.details && typeof log.details === "object"
            ? log.details
            : {};
        if (name === "IDLE_SESSION") {
            const interval = intervalFromDetails(
                detailsValue,
                ["idle_start", "start_time"],
                ["idle_end", "end_time"],
                log.parsedTime
            );
            if (interval) {
                idleIntervals.push(interval);
            } else if (eventDateKey(log.event_timestamp) === selectedDate) {
                const seconds = Number(detailsValue.idle_seconds);
                if (Number.isFinite(seconds) && seconds > 0) {
                    const key = log.parsedTime.toISOString().slice(0, 19);
                    idleFallbacks.set(
                        key,
                        {
                            seconds: Math.max(
                                idleFallbacks.get(key)?.seconds || 0,
                                seconds
                            ),
                            end: log.parsedTime
                        }
                    );
                }
            }
        } else if (
            name === "SESSION_SUMMARY" &&
            eventDateKey(log.event_timestamp) === selectedDate
        ) {
            const seconds = Number(detailsValue.idle_seconds);
            if (Number.isFinite(seconds) && seconds > 0) {
                const key = log.parsedTime.toISOString().slice(0, 19);
                summaryIdleFallbacks.set(key, {
                    seconds: Math.max(
                        summaryIdleFallbacks.get(key)?.seconds || 0,
                        seconds
                    ),
                    end: log.parsedTime
                });
            }
        }

        if (name === "BREAK_SESSION") {
            const breakDetails = log.break_sessions &&
                typeof log.break_sessions === "object"
                ? log.break_sessions
                : detailsValue;
            const interval = intervalFromDetails(
                breakDetails,
                ["break_start", "start_time"],
                ["break_end", "end_time"],
                log.parsedTime
            );
            if (interval) {
                breakIntervals.push(interval);
            }
        }
    }

    for (const fallback of idleFallbacks.values()) {
        idleIntervals.push({
            start: new Date(fallback.end.getTime() - fallback.seconds * 1000),
            end: fallback.end
        });
    }

    let idleByStatus = null;
    for (const log of orderedLogs) {
        const name = String(log.event_name || "").toUpperCase();
        if (
            ["STATUS_IDLE", "IDLE_STARTED", "IDLE_START"].includes(name) &&
            idleByStatus === null
        ) {
            idleByStatus = log.parsedTime;
        } else if (
            idleByStatus &&
            [
                "STATUS_ACTIVE",
                "IDLE_ENDED",
                "IDLE_END",
                "MONITORING_STOPPED",
                "SESSION_SUMMARY"
            ].includes(name)
        ) {
            if (log.parsedTime > idleByStatus) {
                idleIntervals.push({
                    start: idleByStatus,
                    end: log.parsedTime
                });
            }
            idleByStatus = null;
        }
    }
    if (idleByStatus && idleByStatus < now) {
        idleIntervals.push({ start: idleByStatus, end: now });
    }

    const hasRecordedIdleForDay = idleIntervals.some(
        (interval) => interval.start < dayEnd && interval.end > dayStart
    );
    if (!hasRecordedIdleForDay) {
        for (const fallback of summaryIdleFallbacks.values()) {
            idleIntervals.push({
                start: new Date(fallback.end.getTime() - fallback.seconds * 1000),
                end: fallback.end
            });
        }
    }

    const dayIdle = clippedIntervals(idleIntervals, dayStart, dayEnd);
    const dayBreaks = clippedIntervals(breakIntervals, dayStart, dayEnd);
    const allPauses = mergeIntervals([...dayIdle, ...dayBreaks]);
    const elapsedSeconds = intervalSeconds(sessionIntervals);
    const pauseWithinAttendance = sessionIntervals.reduce((total, session) => {
        const pauses = clippedIntervals(allPauses, session.start, session.end);
        return total + intervalSeconds(pauses);
    }, 0);
    let idleSeconds = sessionIntervals.reduce((total, session) => {
        return total + intervalSeconds(
            clippedIntervals(dayIdle, session.start, session.end)
        );
    }, 0);
    const summarySessions = daySessions
        .filter((session) => eventDateKey(session.login_time) === selectedDate)
        .sort((left, right) => left.start - right.start);
    const firstSession = summarySessions[0] || daySessions[0];
    const activeSession = daySessions.some((session) => !session.logout_time);
    const lastLogout = daySessions
        .filter((session) => session.logout_time)
        .map((session) => parseEventDate(session.logout_time))
        .filter(Boolean)
        .sort((left, right) => right - left)[0];

    const activityRows = [];
    const seenRows = new Set();
    const displayedBreaks = [];
    const addActivity = (row, fingerprint) => {
        if (seenRows.has(fingerprint)) {
            return;
        }
        seenRows.add(fingerprint);
        activityRows.push(row);
    };
    for (const session of sessions) {
        if (eventDateKey(session.login_time) === selectedDate) {
            addActivity({
                event_name: "Login",
                event_timestamp: session.login_time,
                duration_seconds: null,
                details: "Attendance session started."
            }, `login:${session.id || session.login_time}`);
        }
        if (
            session.logout_time &&
            eventDateKey(session.logout_time) === selectedDate
        ) {
            addActivity({
                event_name: "Logout",
                event_timestamp: session.logout_time,
                duration_seconds: Math.max(
                    0,
                    (session.end - session.start) / 1000
                ),
                details: "Attendance session ended."
            }, `logout:${session.id || session.logout_time}`);
        }
    }

    const displayIdleIntervals = mergeIntervals(idleIntervals);
    for (const interval of displayIdleIntervals) {
        const startInDay = eventDateKey(interval.start) === selectedDate;
        const endInDay = eventDateKey(interval.end) === selectedDate;
        const dailySeconds = intervalSeconds(
            clippedIntervals([interval], dayStart, dayEnd)
        );
        if (startInDay) {
            addActivity({
                event_name: "Idle Start",
                event_timestamp: interval.start.toISOString(),
                duration_seconds: null,
                details: "Employee became idle."
            }, `idle-start:${Math.round(interval.start.getTime() / 1000)}`);
        }
        if (endInDay) {
            addActivity({
                event_name: "Idle End",
                event_timestamp: interval.end.toISOString(),
                duration_seconds: dailySeconds,
                details: "Employee activity resumed or monitoring stopped."
            }, `idle-end:${Math.round(interval.end.getTime() / 1000)}`);
        }
    }

    for (const log of orderedLogs) {
        const name = String(log.event_name || "Unknown event").toUpperCase();
        if ([
            "IDLE_SESSION",
            "STATUS_IDLE",
            "STATUS_ACTIVE",
            "IDLE_STARTED",
            "IDLE_ENDED",
            "IDLE_START",
            "IDLE_END",
            "LOGIN",
            "LOGOUT"
        ].includes(name)) {
            continue;
        }
        if (eventDateKey(log.event_timestamp) !== selectedDate) {
            continue;
        }
        const breakDetails = log.break_sessions &&
            typeof log.break_sessions === "object"
            ? log.break_sessions
            : log.details;
        const breakInterval = name === "BREAK_SESSION"
            ? intervalFromDetails(
                breakDetails || {},
                ["break_start", "start_time"],
                ["break_end", "end_time"],
                log.parsedTime
            )
            : null;
        if (breakInterval && displayedBreaks.some(
            (previous) =>
                Math.abs(previous.start - breakInterval.start) <= 2000 &&
                Math.abs(previous.end - breakInterval.end) <= 2000
        )) {
            continue;
        }
        if (breakInterval) {
            displayedBreaks.push(breakInterval);
        }
        const timestampKey = log.parsedTime.toISOString().slice(0, 19);
        const eventDetails = name === "BREAK_SESSION"
            ? breakDetails
            : log.details;
        addActivity({
            event_name: formatLabel(name),
            event_timestamp: log.event_timestamp,
            duration_seconds: breakInterval
                ? (breakInterval.end - breakInterval.start) / 1000
                : Number(log.details?.duration_seconds) || null,
            details: eventDetails
        }, `${name}:${timestampKey}:${JSON.stringify(eventDetails || {})}`);
    }
    activityRows.sort(
        (left, right) =>
            new Date(left.event_timestamp) - new Date(right.event_timestamp)
    );

    return {
        loginTime: firstSession ? formatDateTime(firstSession.login_time) : "—",
        logoutTime: activeSession
            ? "Not logged out"
            : lastLogout
                ? formatDateTime(lastLogout.toISOString())
                : "—",
        idleTime: formatDurationHHMM(idleSeconds),
        workingTime: formatDurationHHMM(
            Math.max(0, elapsedSeconds - pauseWithinAttendance)
        ),
        activityRows
    };
}

function attendanceHistoryDates(details) {
    const dates = new Set();
    const includeDate = (value) => {
        const key = eventDateKey(value);
        if (key) {
            dates.add(key);
        }
    };
    for (const session of details.attendance || []) {
        includeDate(session.login_time);
        includeDate(session.logout_time);
    }
    for (const log of details.logs || []) {
        includeDate(log.event_timestamp);
        const values = [
            log.details?.idle_start,
            log.details?.idle_end,
            log.details?.start_time,
            log.details?.end_time,
            log.break_sessions?.break_start,
            log.break_sessions?.break_end
        ];
        values.forEach(includeDate);
    }
    return [...dates].sort();
}

function renderEmployeeDetails(details) {
    const employee = details.employee;
    const attendance = details.attendance || [];
    const name = employee.full_name || employee.user_id;
    resultTitle.textContent = name;
    sectionDescription.textContent =
        "Attendance summary and daily activity for the selected employee.";
    results.replaceChildren();

    const card = document.createElement("section");
    card.className = "attendance-detail-card";

    const cardHeader = document.createElement("div");
    cardHeader.className = "attendance-card-header";
    const backButton = document.createElement("button");
    backButton.type = "button";
    backButton.className = "back-button";
    backButton.textContent = "← Back to employees";
    backButton.addEventListener("click", renderEmployees);

    const employeeIdentity = document.createElement("div");
    employeeIdentity.className = "attendance-employee-identity";
    const employeeHeading = document.createElement("h2");
    employeeHeading.textContent = name || "Employee";
    const employeeId = document.createElement("p");
    employeeId.textContent = `Employee ID: ${employee.user_id}`;
    employeeIdentity.append(employeeHeading, employeeId);
    cardHeader.append(backButton, employeeIdentity);
    card.append(cardHeader);

    const history = document.createElement("section");
    history.className = "attendance-history";
    const historyHeading = document.createElement("h3");
    historyHeading.textContent = "Date-wise Attendance History";
    const dateControls = document.createElement("div");
    dateControls.className = "attendance-date-controls";
    const previousButton = document.createElement("button");
    previousButton.type = "button";
    previousButton.className = "date-nav-button";
    previousButton.textContent = "← Previous";
    const dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.setAttribute("aria-label", "Select attendance date");
    const nextButton = document.createElement("button");
    nextButton.type = "button";
    nextButton.className = "date-nav-button";
    nextButton.textContent = "Next →";
    dateControls.append(previousButton, dateInput, nextButton);
    history.append(historyHeading, dateControls);
    card.append(history);

    const summaries = document.createElement("div");
    summaries.className = "attendance-summary-grid";
    const summaryItems = [
        ["Login Time", "—"],
        ["Logout Time", "—"],
        ["Idle Time", "00:00"],
        ["Total Working Time", "00:00"]
    ];
    const summaryValues = [];
    for (const [label] of summaryItems) {
        const summaryCard = document.createElement("article");
        summaryCard.className = "attendance-summary-item";
        const summaryLabel = document.createElement("p");
        summaryLabel.textContent = label;
        const summaryValue = document.createElement("strong");
        summaryValue.textContent = "—";
        summaryCard.append(summaryLabel, summaryValue);
        summaries.append(summaryCard);
        summaryValues.push(summaryValue);
    }
    card.append(summaries);

    const activitySection = document.createElement("section");
    activitySection.className = "daily-activity-section";
    card.append(activitySection);
    results.append(card);

    const historyDates = attendanceHistoryDates(details);
    const latestDate = historyDates[historyDates.length - 1] ||
        dateKey(new Date());
    dateInput.value = latestDate;

    const updateDateNavigation = () => {
        previousButton.disabled = !historyDates.some(
            (date) => date < dateInput.value
        );
        nextButton.disabled = !historyDates.some(
            (date) => date > dateInput.value
        );
    };

    const renderDate = () => {
        if (!dateInput.value) {
            return;
        }
        const daily = getDailyAttendanceData(details, dateInput.value);
        const values = [
            daily.loginTime,
            daily.logoutTime,
            daily.idleTime,
            daily.workingTime
        ];
        summaryValues.forEach((element, index) => {
            element.textContent = values[index];
        });
        activitySection.replaceChildren();
        addTable(
            activitySection,
            "Daily Activity Details",
            daily.activityRows,
            [
                {
                    key: "event_name",
                    label: "Event",
                    format: String
                },
                {
                    key: "event_timestamp",
                    label: "Timestamp",
                    format: formatDateTime
                },
                {
                    key: "duration_seconds",
                    label: "Duration",
                    format: (value) => value == null
                        ? "—"
                        : formatDurationHHMM(value)
                },
                { key: "details", label: "Details" }
            ],
            "No activity records for this date."
        );
        updateDateNavigation();
    };

    previousButton.addEventListener("click", () => {
        const previous = historyDates
            .filter((date) => date < dateInput.value)
            .pop();
        if (previous) {
            dateInput.value = previous;
            renderDate();
        }
    });
    nextButton.addEventListener("click", () => {
        const next = historyDates.find((date) => date > dateInput.value);
        if (next) {
            dateInput.value = next;
            renderDate();
        }
    });
    dateInput.addEventListener("change", renderDate);
    renderDate();
    setMessage(`Loaded attendance details for ${name}.`);
}

async function loadEmployeeDetails(userId) {
    resultTitle.textContent = "Employee details";
    setMessage("Loading employee details...");
    results.replaceChildren();

    try {
        const details = await apiRequest(
            `/admin/users/${encodeURIComponent(userId)}/attendance`
        );
        renderEmployeeDetails(details);
    } catch (error) {
        setMessage(error.message, true);
        const backButton = document.createElement("button");
        backButton.type = "button";
        backButton.className = "back-button";
        backButton.textContent = "← Back to employees";
        backButton.addEventListener("click", renderEmployees);
        results.append(backButton);
    }
}

async function loadMonitoringLogs() {
    resultTitle.textContent = "Monitoring Logs";
    sectionDescription.textContent = "Recent employee activity records.";
    setMessage("Loading monitoring logs...");
    results.replaceChildren();

    try {
        const result = await apiRequest("/admin/monitoring-logs");
        addTable(
            results,
            "Recent activity",
            result.logs || [],
            [
                {
                    key: "event_timestamp",
                    label: "Time",
                    format: formatDateTime
                },
                { key: "employee_user_id", label: "Employee ID" },
                {
                    key: "event_name",
                    label: "Event",
                    format: (value) => formatLabel(String(value || "Unknown event"))
                },
                { key: "details", label: "Details" },
                { key: "break_sessions", label: "Break session" }
            ],
            "No monitoring logs found."
        );
        setMessage(`Loaded ${(result.logs || []).length} log(s).`);
    } catch (error) {
        setMessage(error.message, true);
    }
}

function setActiveNavigation(activeId) {
    for (const id of ["users-button", "logs-button"]) {
        const button = document.getElementById(id);
        const active = id === activeId;
        button.classList.toggle("active", active);
        button.setAttribute("aria-current", active ? "page" : "false");
    }
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginButton.disabled = true;
    loginMessage.textContent = "Checking admin credentials...";
    loginMessage.classList.remove("error-message");

    const user_id = document.getElementById("user-id").value.trim();
    const password = document.getElementById("password").value;

    try {
        const result = await apiRequest("/admin/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id, password })
        });

        if (result.role !== "admin" || !result.access_token) {
            throw new Error("Admin access only.");
        }

        accessToken = result.access_token;
        loginSection.hidden = true;
        dashboard.hidden = false;
        dashboard.querySelector(".dashboard-heading h2").textContent =
            `Welcome, ${result.full_name}`;
        loginMessage.textContent = "";
        setActiveNavigation("users-button");
        await loadEmployees();
    } catch (error) {
        accessToken = null;
        loginMessage.textContent = error.message;
        loginMessage.classList.add("error-message");
    } finally {
        loginButton.disabled = false;
    }
});

document.getElementById("users-button").addEventListener("click", () => {
    setActiveNavigation("users-button");
    loadEmployees();
});

document.getElementById("logs-button").addEventListener("click", () => {
    setActiveNavigation("logs-button");
    loadMonitoringLogs();
});

document.getElementById("logout-button").addEventListener("click", () => {
    accessToken = null;
    employees = [];
    dashboard.hidden = true;
    loginSection.hidden = false;
    loginForm.reset();
    resultTitle.textContent = "Employee Management";
    sectionDescription.textContent =
        "Select an employee to view their profile.";
    results.replaceChildren();
    setMessage("");
    loginMessage.textContent = "Signed out.";
    loginMessage.classList.remove("error-message");
});
