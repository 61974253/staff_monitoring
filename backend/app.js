
"use strict";

/* =========================================
   STAFF MONITORING ADMIN DASHBOARD
   FastAPI + Supabase integration
========================================= */

const API_URL = "http://127.0.0.1:8002";

let accessToken = "";
let requestNumber = 0;

// HTML elements
const loginSection = document.getElementById("login-section");
const dashboardSection = document.getElementById("dashboard-section");
const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");
const loginButton = document.getElementById("login-button");

const usersButton = document.getElementById("users-button");
const logsButton = document.getElementById("logs-button");
const logoutButton = document.getElementById("logout-button");

const resultTitle = document.getElementById("result-title");
const resultMessage = document.getElementById("result-message");
const results = document.getElementById("results");
const sectionDescription = document.getElementById("section-description");

/* =========================================
   SAFE UI HELPERS
========================================= */

function el(tag, className = "", text = "") {
    const node = document.createElement(tag);

    if (className) node.className = className;

    if (text !== null && text !== undefined) {
        node.textContent = String(text);
    }

    return node;
}

function displayValue(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    if (typeof value === "boolean") {
        return value ? "Yes" : "No";
    }

    if (typeof value === "object") {
        if (Array.isArray(value)) {
            return value.map(displayValue).join(", ") || "—";
        }

        // Do not show raw JSON objects in the UI.
        return "Details unavailable";
    }

    return String(value);
}

function showLoading(message = "Loading...") {
    results.replaceChildren(el("p", "muted", message));
}

function showEmpty(message) {
    results.replaceChildren(el("p", "muted", message));
}

function showLoginMessage(message, isError = true) {
    loginMessage.textContent = message;
    loginMessage.className = isError
        ? "message error-message"
        : "message success-message";
}

function showDashboardMessage(message, isError = true) {
    resultMessage.textContent = message;
    resultMessage.className = isError
        ? "message dashboard-message error-message"
        : "message dashboard-message success-message";
}

function clearDashboardMessage() {
    resultMessage.textContent = "";
    resultMessage.className = "message dashboard-message";
}

function setHeading(title, description) {
    resultTitle.textContent = title;

    if (sectionDescription) {
        sectionDescription.textContent = description;
    }
}

function formatDateTime(value) {
    if (!value) return "—";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? displayValue(value)
        : date.toLocaleString();
}

/* =========================================
   API REQUEST
========================================= */

async function apiRequest(path, options = {}) {
    const headers = { ...(options.headers || {}) };

    if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`;
    }

    if (options.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    let response;

    try {
        response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers
        });
    } catch {
        throw new Error(
            "Cannot connect to the backend. Check whether FastAPI is running."
        );
    }

    const contentType = response.headers.get("content-type") || "";
    let data;

    try {
        data = contentType.includes("application/json")
            ? await response.json()
            : await response.text();
    } catch {
        throw new Error("The backend returned an unreadable response.");
    }

    if (!response.ok) {
        if (response.status === 401) {
            throw new Error("Login expired. Please sign in again.");
        }

        if (response.status === 403) {
            throw new Error("Admin permission is required.");
        }

        const detail =
            data && typeof data === "object"
                ? data.detail || data.message
                : data;

        throw new Error(
            typeof detail === "string"
                ? detail
                : `Backend request failed (${response.status}).`
        );
    }

    return data;
}

/* =========================================
   EXTRACT USER LIST FROM API RESPONSE
========================================= */

function getList(data, keys) {
    if (Array.isArray(data)) return data;

    if (!data || typeof data !== "object") return [];

    for (const key of keys) {
        if (Array.isArray(data[key])) {
            return data[key];
        }
    }

    return [];
}

/* =========================================
   LOGIN
========================================= */

loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const userId = document.getElementById("user-id").value.trim();
    const password = document.getElementById("password").value;

    if (!userId || !password) {
        showLoginMessage("Enter your Admin ID and password.");
        return;
    }

    loginButton.disabled = true;
    loginButton.textContent = "Signing in...";
    showLoginMessage("", false);

    try {
        const data = await apiRequest("/login", {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                password: password
            })
        });

        if (!data || typeof data !== "object") {
            throw new Error("Invalid login response from backend.");
        }

        const token =
            data.access_token ||
            data.accessToken ||
            data.token;

        if (!token) {
            throw new Error(
                "Login succeeded without an access token. Check the backend login response."
            );
        }

        if (
            data.role &&
            String(data.role).toLowerCase() !== "admin"
        ) {
            throw new Error("This account is not an administrator.");
        }

        accessToken = token;

        loginSection.hidden = true;
        dashboardSection.hidden = false;

        loginForm.reset();
        clearDashboardMessage();

        setActiveButton(usersButton);
        await loadUsers();

    } catch (error) {
        accessToken = "";
        showLoginMessage(error.message);
    } finally {
        loginButton.disabled = false;
        loginButton.textContent = "Sign In";
    }
});

/* =========================================
   NAVIGATION
========================================= */

function setActiveButton(button) {
    usersButton.classList.remove("active");
    logsButton.classList.remove("active");
    button.classList.add("active");
}

usersButton.addEventListener("click", function () {
    setActiveButton(usersButton);
    loadUsers();
});

logsButton.addEventListener("click", function () {
    setActiveButton(logsButton);
    loadLogs();
});

logoutButton.addEventListener("click", function () {
    accessToken = "";
    requestNumber++;

    dashboardSection.hidden = true;
    loginSection.hidden = false;

    loginForm.reset();
    results.replaceChildren();
    clearDashboardMessage();
    showLoginMessage("", false);

    document.getElementById("user-id").focus();
});

/* =========================================
   LOAD ALL USERS
========================================= */

async function loadUsers() {
    const thisRequest = ++requestNumber;

    setHeading(
        "Employee Management",
        "Select a user to view their individual information and attendance."
    );

    clearDashboardMessage();
    showLoading("Loading users from database...");

    try {
        const data = await apiRequest("/admin/users");

        // Ignore an older response if another page was opened meanwhile.
        if (thisRequest !== requestNumber) return;

        const users = getList(data, [
            "users",
            "employees",
            "data"
        ]);

        if (users.length === 0) {
            showEmpty(
                "No users were returned. Check the backend /admin/users endpoint."
            );
            return;
        }

        const grid = el("div", "employee-grid");

        users.forEach(function (user) {
            grid.appendChild(createUserCard(user));
        });

        results.replaceChildren(grid);

    } catch (error) {
        if (thisRequest !== requestNumber) return;

        showEmpty(error.message);
        showDashboardMessage(error.message);
    }
}

/* =========================================
   USER CARD
========================================= */

function createUserCard(user) {
    const userId =
        user.user_id ??
        user.username ??
        user.id ??
        "";

    const name =
        user.full_name ??
        user.name ??
        user.username ??
        user.user_id ??
        "Unnamed User";

    const role = user.role ?? "Employee";

    const card = el("button", "employee-card");
    card.type = "button";

    const avatar = el(
        "div",
        "employee-avatar",
        String(name).trim().charAt(0).toUpperCase() || "U"
    );

    const userName = el("h3", "", name);

    const idText = el(
        "p",
        "",
        `User ID: ${displayValue(userId)}`
    );

    const roleText = el(
        "p",
        "",
        `Role: ${displayValue(role)}`
    );

    card.append(avatar, userName, idText, roleText);

    // Show account status only if backend provides it.
    if (user.is_active !== undefined) {
        const active =
            user.is_active === true ||
            user.is_active === 1 ||
            String(user.is_active).toLowerCase() === "true";

        card.appendChild(
            el(
                "span",
                active ? "status-active" : "status-inactive",
                active ? "Active" : "Inactive"
            )
        );
    }

    card.appendChild(
        el("span", "view-profile", "View User Details →")
    );

    card.addEventListener("click", function () {
        if (!userId) {
            showDashboardMessage(
                "This user has no ID, so their details cannot be loaded."
            );
            return;
        }

        loadOneUser(userId);
    });

    return card;
}

/* =========================================
   LOAD SELECTED USER ONLY
========================================= */

async function loadOneUser(userId) {
    const thisRequest = ++requestNumber;

    clearDashboardMessage();
    showLoading("Loading selected user's information...");

    try {
        // This endpoint returns the selected employee and attendance.
        const data = await apiRequest(
            `/admin/users/${encodeURIComponent(userId)}/attendance`
        );

        if (thisRequest !== requestNumber) return;

        renderOneUser(data, userId);

    } catch (error) {
        if (thisRequest !== requestNumber) return;

        showEmpty(error.message);
        showDashboardMessage(error.message);
    }
}

/* =========================================
   DISPLAY SELECTED USER
========================================= */

function renderOneUser(data, selectedUserId) {
    const user = data.employee || data.user || {};
    const attendance = getList(data, [
        "attendance",
        "records"
    ]);

    setHeading(
        "User Details",
        "Information for the selected user only."
    );

    const container = el("div", "employee-details-view");

    const backButton = el(
        "button",
        "back-button",
        "← Back to Users"
    );

    backButton.type = "button";
    backButton.addEventListener("click", loadUsers);

    const profile = el("section", "profile-card");

    profile.appendChild(
        el(
            "h2",
            "",
            user.full_name ||
            user.name ||
            user.user_id ||
            selectedUserId
        )
    );

    const details = el("div", "profile-details");

    // Display only known user fields, not the raw response object.
    const fields = [
        ["User ID", user.user_id ?? selectedUserId],
        ["Full Name", user.full_name ?? user.name],
        ["Role", user.role],
        ["Account Status", user.is_active === undefined
            ? "—"
            : (
                user.is_active === true ||
                user.is_active === 1 ||
                String(user.is_active).toLowerCase() === "true"
                    ? "Active"
                    : "Inactive"
            )]
    ];

    fields.forEach(function ([label, value]) {
        const item = el("p");
        item.append(
            el("strong", "", `${label}: `),
            el("span", "", displayValue(value))
        );
        details.appendChild(item);
    });

    profile.appendChild(details);

    const attendanceHeading = el("h3", "", "Attendance History");

    const count = el(
        "p",
        "record-count",
        `Attendance records: ${attendance.length}`
    );

    const attendanceTable = createTable(
        ["Attendance In", "Attendance Out"],
        attendance.map(function (record) {
            return [
                formatDateTime(record.attendance_in),
                formatDateTime(record.attendance_out)
            ];
        }),
        "No attendance records found for this user."
    );

    container.append(
        backButton,
        profile,
        attendanceHeading,
        count,
        attendanceTable
    );

    results.replaceChildren(container);
}

/* =========================================
   LOAD MONITORING LOGS
========================================= */

async function loadLogs() {
    const thisRequest = ++requestNumber;

    setHeading(
        "Monitoring Logs",
        "Monitoring records returned by the backend."
    );

    clearDashboardMessage();
    showLoading("Loading monitoring logs...");

    try {
        const data = await apiRequest("/admin/monitoring-logs");

        if (thisRequest !== requestNumber) return;

        const logs = getList(data, [
            "logs",
            "monitoring_logs",
            "records",
            "data"
        ]);

        if (logs.length === 0) {
            showEmpty("No monitoring logs available.");
            return;
        }

        const columns = [
            ...new Set(
                logs.flatMap(function (log) {
                    return Object.keys(log).filter(function (key) {
                        const value = log[key];

                        // Avoid exposing nested raw objects in the table.
                        return value === null ||
                            typeof value !== "object";
                    });
                })
            )
        ];

        if (columns.length === 0) {
            showEmpty("No displayable log fields were returned.");
            return;
        }

        const rows = logs.map(function (log) {
            return columns.map(function (column) {
                return displayValue(log[column]);
            });
        });

        results.replaceChildren(
            createTable(columns, rows, "No monitoring logs available.")
        );

    } catch (error) {
        if (thisRequest !== requestNumber) return;

        showEmpty(error.message);
        showDashboardMessage(error.message);
    }
}

/* =========================================
   REUSABLE TABLE
========================================= */

function createTable(headers, rows, emptyMessage) {
    const wrapper = el("div", "table-wrapper");
    const table = el("table", "data-table");

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");

    headers.forEach(function (header) {
        const readableHeader = String(header)
            .replaceAll("_", " ")
            .replace(/\b\w/g, character => character.toUpperCase());

        headerRow.appendChild(el("th", "", readableHeader));
    });

    thead.appendChild(headerRow);

    const tbody = document.createElement("tbody");

    if (rows.length === 0) {
        const row = document.createElement("tr");
        const cell = el("td", "", emptyMessage);

        cell.colSpan = Math.max(headers.length, 1);
        row.appendChild(cell);
        tbody.appendChild(row);
    } else {
        rows.forEach(function (values) {
            const row = document.createElement("tr");

            values.forEach(function (value) {
                row.appendChild(el("td", "", displayValue(value)));
            });

            tbody.appendChild(row);
        });
    }

    table.append(thead, tbody);
    wrapper.appendChild(table);

    return wrapper;
}
