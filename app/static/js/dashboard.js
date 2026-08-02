// ==========================================================
// dashboard.js
// Search, Create/Edit/Delete/Verify, Activity Log
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {

    loadFilters();
    loadActivityLog();
    loadSummaryCards();
    applyRolePermission();

    document.getElementById("searchBtn")
        ?.addEventListener("click", doSearch);

    document.getElementById("modalCancelBtn")
        ?.addEventListener("click", closeModal);

    document.getElementById("modalSaveBtn")
        ?.addEventListener("click", saveModal);

    document.getElementById("createDeviceBtn")
        ?.addEventListener("click", createDevice);

    document.getElementById("loadDeviceListBtn")
        ?.addEventListener("click", loadDeviceList);

    document.getElementById("changePasswordBtn")
        ?.addEventListener("click", changePassword);

    document.getElementById("createAdminBtn")
        ?.addEventListener("click", createAdmin);

    document.getElementById("loadAdminBtn")
        ?.addEventListener("click", loadAdminList);


    document.querySelectorAll(".sidebar-item[data-target]")
        .forEach((btn) => {
            btn.addEventListener("click", () => {
                switchPanel(btn.dataset.target);
            });
        });


    // ড্রপডাউনের বাইরে ক্লিক করলে বন্ধ হয়ে যাবে
    document.addEventListener("click", (e) => {
        document.querySelectorAll(".custom-dropdown.open")
            .forEach((dd) => {
                if (!dd.contains(e.target)) {
                    dd.classList.remove("open");
                }
            });
    });

});


// ==========================================================
// Dropdown Open/Close
// ==========================================================

function toggleFilterDropdown(dropdownId) {

    const dropdown = document.getElementById(dropdownId);

    if (!dropdown) {
        return;
    }

    const isOpen = dropdown.classList.contains("open");

    // অন্য সব ড্রপডাউন বন্ধ করে দেওয়া হচ্ছে
    document.querySelectorAll(".custom-dropdown.open")
        .forEach((dd) => dd.classList.remove("open"));

    if (!isOpen) {
        dropdown.classList.add("open");
    }
}


// ==========================================================
// Sidebar Panel Switching
// ==========================================================

function switchPanel(targetId) {

    document.querySelectorAll(".panel").forEach((p) => {
        p.classList.add("hidden");
    });

    const target = document.getElementById(targetId);

    if (target) {
        target.classList.remove("hidden");
    }

    document.querySelectorAll(".sidebar-item[data-target]")
        .forEach((b) => b.classList.remove("active"));

    const activeButton =
        document.querySelector(
            `.sidebar-item[data-target="${targetId}"]`
        );

    if (activeButton) {
        activeButton.classList.add("active");
    }
}


// ==========================================================
// Selected Values (checkbox ভিত্তিক multi-select থেকে)
// ==========================================================

function getSelectedValues(containerId) {

    const container = document.getElementById(containerId);

    if (!container) {
        return [];
    }

    return Array.from(
        container.querySelectorAll("input[type=checkbox]:checked")
    ).map((cb) => cb.value);
}


// ==========================================================
// Filters Load
// ==========================================================

async function loadFilters() {
    try {
        const res = await fetch("/api/filters");

        if (res.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (!res.ok) {
            console.error("Filter loading failed");
            return;
        }

        const data = await res.json();

        window.FILTER_DATA = data;

        renderCheckboxOptions(
            "groupOptions",
            "group",
            data.groups || []
        );

        renderCheckboxOptions(
            "zoneOptions",
            "zone",
            getAllZones(data)
        );

        renderCheckboxOptions(
            "deviceOptions",
            "device",
            getAllDevices(data)
        );

        // "All" checkbox গুলো ডিফল্ট ভাবে চেক করা থাকবে
        setAllChecked("group", true);
        setAllChecked("zone", true);
        setAllChecked("device", true);

        updateFilterText("group");
        updateFilterText("zone");
        updateFilterText("device");

    } catch (error) {
        console.error("loadFilters error:", error);
    }
}

function getAllZones(data) {
    const zones = new Set();

    Object.values(data.zones_by_group || {}).forEach(groupZones => {
        groupZones.forEach(zone => zones.add(zone));
    });

    return Array.from(zones).sort();
}


function getAllDevices(data) {
    const devices = [];
    const seen = new Set();

    Object.values(data.devices_by_zone || {}).forEach(deviceList => {
        deviceList.forEach(device => {
            if (!seen.has(device.hostname)) {
                seen.add(device.hostname);
                devices.push({
                    id: device.id,
                    hostname: device.hostname
                });
            }
        });
    });

    devices.sort((a, b) => a.hostname.localeCompare(b.hostname));

    return devices;
}


// ==========================================================
// Checkbox Options রেন্ডার করা (Group / Zone / Device)
// ==========================================================

function renderCheckboxOptions(containerId, kind, values) {

    const container = document.getElementById(containerId);

    if (!container) {
        return;
    }

    container.innerHTML = "";

    values.forEach((value) => {

        const isObject = typeof value === "object" && value !== null;

        const val = isObject ? (value.hostname ?? "") : value;
        const label = isObject ? (value.hostname ?? "") : value;

        const wrapper = document.createElement("label");
        wrapper.className = "dropdown-option";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = val;
        checkbox.dataset.kind = kind;

        checkbox.addEventListener("change", () => {
            onFilterCheckboxChange(kind);
        });

        const span = document.createElement("span");
        span.textContent = label;

        wrapper.appendChild(checkbox);
        wrapper.appendChild(span);

        container.appendChild(wrapper);
    });
}


// ==========================================================
// "All" checkbox সেট/আনসেট করা
// ==========================================================

function setAllChecked(kind, checked) {

    const allBox = document.getElementById(`${kind}All`);

    if (allBox) {
        allBox.checked = checked;
    }
}


// ==========================================================
// Individual checkbox পরিবর্তন হলে ("All" এর সাথে সিংক করা
// এবং cascading চালানো)
// ==========================================================

function onFilterCheckboxChange(kind) {

    const optionsContainer = document.getElementById(`${kind}Options`);

    const anyChecked = optionsContainer
        ? optionsContainer.querySelectorAll(
            "input[type=checkbox]:checked"
        ).length > 0
        : false;

    // কোনো একটি individual option checked হলে "All" আনচেক হবে
    // কোনোটাই checked না থাকলে আবার "All" চেক হয়ে যাবে
    setAllChecked(kind, !anyChecked);

    updateFilterText(kind);

    if (kind === "group") {
        handleGroupChange();
    }

    if (kind === "zone") {
        handleZoneChange();
    }
}


// ==========================================================
// "All" checkbox ক্লিক হলে
// ==========================================================

function handleAllCheckboxClick(kind) {

    const allBox = document.getElementById(`${kind}All`);

    if (!allBox || !allBox.checked) {
        return;
    }

    // সব individual checkbox আনচেক করে দেওয়া হবে ("All" মানে সবই select)
    const optionsContainer = document.getElementById(`${kind}Options`);

    optionsContainer
        ?.querySelectorAll("input[type=checkbox]")
        .forEach((cb) => (cb.checked = false));

    updateFilterText(kind);

    if (kind === "group") {
        handleGroupChange();
    }

    if (kind === "zone") {
        handleZoneChange();
    }
}


document.addEventListener("DOMContentLoaded", () => {

    ["group", "zone", "device"].forEach((kind) => {
        document.getElementById(`${kind}All`)
            ?.addEventListener("change", () => {
                handleAllCheckboxClick(kind);
            });
    });

});


// ==========================================================
// ড্রপডাউনের উপরের টেক্সট আপডেট করা (কয়টা সিলেক্ট করা আছে)
// ==========================================================

function updateFilterText(kind) {

    const labels = {
        group: "🔘 All Groups",
        zone: "🔘 All Zones",
        device: "🔘 All Devices",
    };

    const selected = getSelectedValues(`${kind}Options`);

    const textEl = document.getElementById(`${kind}SelectedText`);

    if (!textEl) {
        return;
    }

    if (selected.length === 0) {
        textEl.textContent = labels[kind];
    } else if (selected.length === 1) {
        textEl.textContent = selected[0];
    } else {
        textEl.textContent = `${selected.length} selected`;
    }
}


// ==========================================================
// Group → Zone (Cascading)
// ==========================================================

function handleGroupChange() {

    const groups = getSelectedValues("groupOptions");

    const data = window.FILTER_DATA || {};

    // All Groups হলে সব Zone/Device দেখাবে
    if (groups.length === 0) {

        renderCheckboxOptions(
            "zoneOptions",
            "zone",
            getAllZones(data)
        );

        setAllChecked("zone", true);
        updateFilterText("zone");

        handleZoneChange();

        return;
    }

    const zoneSet = new Set();

    groups.forEach(group => {
        const zones = data.zones_by_group?.[group] || [];
        zones.forEach(zone => zoneSet.add(zone));
    });

    renderCheckboxOptions(
        "zoneOptions",
        "zone",
        Array.from(zoneSet).sort()
    );

    setAllChecked("zone", true);
    updateFilterText("zone");

    // Zone রিসেট হলো, তাই Device ও নতুন করে বসাতে হবে
    handleZoneChange();
}


// ==========================================================
// Zone → Device (Cascading)
// ==========================================================

function handleZoneChange() {

    const groups = getSelectedValues("groupOptions");
    const zones = getSelectedValues("zoneOptions");

    const data = window.FILTER_DATA || {};

    const devices = [];
    const seen = new Set();

    const pushDevice = (device) => {
        if (!seen.has(device.hostname)) {
            seen.add(device.hostname);
            devices.push(device);
        }
    };

    // কোনো Group select না থাকলে সব Group ধরা হবে (All Groups)
    const effectiveGroups =
        groups.length > 0
            ? groups
            : Object.keys(data.zones_by_group || {});

    if (zones.length === 0) {

        // All Zones
        effectiveGroups.forEach(group => {
            const groupZones = data.zones_by_group?.[group] || [];

            groupZones.forEach(zone => {
                const key = `${group}|||${zone}`;
                (data.devices_by_zone?.[key] || []).forEach(pushDevice);
            });
        });

    } else {

        effectiveGroups.forEach(group => {
            zones.forEach(zone => {
                const key = `${group}|||${zone}`;
                (data.devices_by_zone?.[key] || []).forEach(pushDevice);
            });
        });

    }

    devices.sort((a, b) => a.hostname.localeCompare(b.hostname));

    renderCheckboxOptions(
        "deviceOptions",
        "device",
        devices
    );

    setAllChecked("device", true);
    updateFilterText("device");
}


// ==========================================================
// Search
// ==========================================================

async function doSearch() {

    const payload = {

        groups: getSelectedValues("groupOptions"),

        zones: getSelectedValues("zoneOptions"),

        devices: getSelectedValues("deviceOptions"),

        username:
            document.getElementById("filterUsername")
                ?.value.trim() || ""

    };


    if (!payload.username) {

        alert("Enter Username");

        return;

    }


    const tbody = document.getElementById("resultBody");

    tbody.innerHTML = `
        <tr>
            <td colspan="8" class="text-muted">
                Searching...
            </td>
        </tr>
    `;


    try {

        const res = await fetch("/api/search", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(payload)

        });


        if (res.status === 401) {

            window.location.href = "/login";

            return;

        }


        const data = await res.json();


        if (!res.ok) {

            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-muted">
                        ${data.detail || "Search failed"}
                    </td>
                </tr>
            `;

            return;

        }


        renderResults(
            data.results,
            payload.username
        );


        loadActivityLog();

    }

    catch (error) {

        console.error("Search error:", error);

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-muted">
                    Search failed.
                </td>
            </tr>
        `;

    }

}


// ==========================================================
// Search Result
// ==========================================================

function renderResults(results, username) {

    const tbody =
        document.getElementById("resultBody");


    if (!results || results.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-muted">
                    No devices found.
                </td>
            </tr>
        `;

        return;

    }


    tbody.innerHTML = "";


    results.forEach((r) => {

        const tr = document.createElement("tr");


        // Connection/Error
        if (r.error) {

            tr.innerHTML = `
                <td>${username}</td>
                <td>${r.group_name}</td>
                <td>${r.zone}</td>
                <td>${r.vendor}</td>
                <td>${r.hostname}</td>
                <td>${r.ip_address}</td>

                <td>
                    <span class="status-badge status-error">
                        Error
                    </span>
                </td>

                <td class="text-muted">
                    ${r.error}
                </td>
            `;

        }


        // Found
        else if (r.found) {

            let action = "";


            if (CURRENT_ROLE === "read") {

                action = `
                    <span class="text-muted">
                        No Permission
                    </span>
                `;

            }

            else {

                action = `

                    <button
                        class="btn btn-sm btn-primary"
                        onclick='openModal(
                            "edit",
                            ${r.device_id},
                            "${username}",
                            "${r.vendor}"
                        )'
                    >
                        Edit
                    </button>


                    <button
                        class="btn btn-sm btn-danger"
                        onclick='deleteUser(
                            ${r.device_id},
                            "${username}"
                        )'
                    >
                        Delete
                    </button>

                `;

            }


            tr.innerHTML = `

                <td>${username}</td>

                <td>${r.group_name}</td>

                <td>${r.zone}</td>

                <td>${r.vendor}</td>

                <td>${r.hostname}</td>

                <td>${r.ip_address}</td>

                <td>
                    <span class="status-badge status-found">
                        Found
                    </span>
                </td>

                <td>${action}</td>

            `;

        }


        // Not Found
        else {

            let action = "";


            if (CURRENT_ROLE === "read") {

                action = `
                    <span class="text-muted">
                        No Permission
                    </span>
                `;

            }

            else {

                action = `

                    <button
                        class="btn btn-sm btn-success"
                        onclick='openModal(
                            "create",
                            ${r.device_id},
                            "${username}",
                            "${r.vendor}"
                        )'
                    >
                        Create User
                    </button>

                `;

            }


            tr.innerHTML = `

                <td>${username}</td>

                <td>${r.group_name}</td>

                <td>${r.zone}</td>

                <td>${r.vendor}</td>

                <td>${r.hostname}</td>

                <td>${r.ip_address}</td>

                <td>
                    <span class="status-badge status-notfound">
                        Not Found
                    </span>
                </td>

                <td>
                    ${action}
                </td>

            `;

        }


        tbody.appendChild(tr);

    });

}


// ==========================================================
// Create / Edit Modal
// ==========================================================

function openModal(mode, deviceId, username, vendor) {

    document.getElementById("modalMode").value = mode;

    document.getElementById("modalDeviceId").value = deviceId;

    document.getElementById("modalUsername").value = username;

    document.getElementById("modalPassword").value = "";

    document.getElementById("modalGroup").value = "full";

    document.getElementById("modalAddress").value = "";


    document.getElementById("modalTitle").textContent =
        mode === "create"
            ? "Create User"
            : "Edit User";

    // Group/Allowed Address শুধু MikroTik এর জন্য প্রযোজ্য (RouterOS-এ
    // group/address কনসেপ্ট আছে); Create আর Edit দুটোতেই একই ফিল্ড
    // দেখানো হয় যাতে দুটো ফর্ম সবসময় এক রকম থাকে।
    document.getElementById("modalGroupFields").style.display =
        vendor === "MikroTik" ? "block" : "none";

    document
        .getElementById("userModal")
        .classList.remove("hidden");

}


function closeModal() {

    document
        .getElementById("userModal")
        .classList.add("hidden");

}


// ==========================================================
// Save Create / Edit
// ==========================================================

async function saveModal() {

    const mode =
        document.getElementById("modalMode").value;

    const device_id =
        parseInt(
            document.getElementById("modalDeviceId").value
        );

    const username =
        document.getElementById("modalUsername").value.trim();

    const password =
        document.getElementById("modalPassword").value;

    const dryRun =
        document.getElementById("testModeToggle")?.checked || false;

    const group =
        document.getElementById("modalGroup")?.value || "full";

    const address =
        document.getElementById("modalAddress")?.value.trim() || null;


    if (!username) {

        alert("Enter Username");

        return;

    }


    if (!password) {

        alert("Enter Password");

        return;

    }


    const endpoint =
        mode === "create"
            ? "/api/user/create"
            : "/api/user/edit";


    try {

        const res = await fetch(endpoint, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                device_id,
                username,
                password,
                dry_run: dryRun,
                group,
                address
            })

        });


        const data = await res.json();


        if (res.ok) {

            alert(
                data.dry_run
                    ? "🧪 Test Mode: No change made on device (checked only)"
                    : data.verified
                        ? "✅ Success (Server Verified)"
                        : "⚠️ Action done but Verify Failed"
            );


            closeModal();

            loadActivityLog();

            doSearch();

        }

        else {

            alert(
                "Failed: " +
                (data.detail || "Unknown error")
            );

        }

    }

    catch (error) {

        console.error(error);

        alert("Server error occurred.");

    }

}


// ==========================================================
// Delete User
// ==========================================================

async function deleteUser(deviceId, username) {

    if (
        !confirm(
            `Are you sure you want to delete '${username}'?`
        )
    ) {
        return;
    }


    const dryRun =
        document.getElementById("testModeToggle")?.checked || false;


    const res = await fetch("/api/user/delete", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            device_id: deviceId,
            username,
            dry_run: dryRun
        })

    });


    const data = await res.json();


    if (res.ok) {

        alert(
            data.dry_run
                ? "🧪 Test Mode: No change made on device (checked only)"
                : data.verified
                    ? "✅ Delete successful (Server Verified)"
                    : "⚠️ Deleted but Verify Failed"
        );


        loadActivityLog();

        doSearch();

    }

    else {

        alert(
            "Failed: " +
            (data.detail || "Unknown error")
        );

    }

}


// ==========================================================
// Manual Verify
// ==========================================================

async function verifyUser(deviceId, username) {

    const res = await fetch("/api/user/verify", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            device_id: deviceId,
            username
        })

    });


    const data = await res.json();


    alert(
        data.exists
            ? "✅ Verify Success: User found"
            : "❌ Verify Failed: User not found"
    );

}


// ==========================================================
// Activity Log
// ==========================================================

async function loadActivityLog() {

    const res = await fetch("/api/activity-log");

    if (!res.ok) {
        return;
    }


    const data = await res.json();

    const ul =
        document.getElementById("activityLog");


    if (!data.logs || data.logs.length === 0) {

        ul.innerHTML = `
            <li class="text-muted">
                No activity yet
            </li>
        `;

        return;

    }


    ul.innerHTML = "";


    data.logs.forEach((log) => {

        const li = document.createElement("li");

        li.textContent =
            `${log.time} — ${log.message}`;

        ul.appendChild(li);

    });

}


// ==========================================================
// Form Alert
// ==========================================================

function showFormAlert(elId, message, type) {

    const el =
        document.getElementById(elId);

    if (!el) {
        return;
    }

    el.innerHTML =
        `<div class="alert alert-${type}">
            ${message}
        </div>`;

}


// ==========================================================
// Create Device
// ==========================================================

async function createDevice() {

    const payload = {

        group_name:
            document.getElementById("cdGroup").value.trim(),

        zone:
            document.getElementById("cdZone").value.trim(),

        vendor:
            document.getElementById("cdVendor").value,

        hostname:
            document.getElementById("cdHostname").value.trim(),

        ip_address:
            document.getElementById("cdIp").value.trim(),

        ssh_port:
            parseInt(
                document.getElementById("cdPort").value
            ) || 22,

        ssh_username:
            document.getElementById("cdSshUser").value.trim(),

        ssh_password:
            document.getElementById("cdSshPass").value

    };


    if (
        !payload.group_name ||
        !payload.zone ||
        !payload.hostname ||
        !payload.ip_address ||
        !payload.ssh_username ||
        !payload.ssh_password
    ) {

        showFormAlert(
            "createDeviceAlert",
            "Please fill in all fields.",
            "error"
        );

        return;

    }


    const res = await fetch("/api/device/create", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(payload)

    });


    const data = await res.json();


    if (res.ok) {

        showFormAlert(
            "createDeviceAlert",
            `✅ Device '${payload.hostname}' created successfully!`,
            "success"
        );


        [
            "cdGroup",
            "cdZone",
            "cdHostname",
            "cdIp",
            "cdSshUser",
            "cdSshPass"
        ].forEach((id) => {

            document.getElementById(id).value = "";

        });


        document.getElementById("cdPort").value = "22";


        loadFilters();

        loadActivityLog();

        loadDeviceList();

    }

    else {

        showFormAlert(
            "createDeviceAlert",
            "❌ Failed: " +
            (data.detail || "Unknown error"),
            "error"
        );

    }

}


// ==========================================================
// Change Password
// ==========================================================

async function changePassword() {

    const currentPassword =
        document.getElementById("stCurrentPassword").value;

    const newPassword =
        document.getElementById("stNewPassword").value;

    const confirmPassword =
        document.getElementById("stConfirmPassword").value;


    if (
        !currentPassword ||
        !newPassword ||
        !confirmPassword
    ) {

        showFormAlert(
            "settingsAlert",
            "Please fill in all fields.",
            "error"
        );

        return;

    }


    if (newPassword !== confirmPassword) {

        showFormAlert(
            "settingsAlert",
            "New Password must be entered the same way twice.",
            "error"
        );

        return;

    }


    const res = await fetch(
        "/api/admin/change-password",
        {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })

        }
    );


    const data = await res.json();


    if (res.ok) {

        showFormAlert(
            "settingsAlert",
            "✅ Password changed successfully.",
            "success"
        );


        document.getElementById(
            "stCurrentPassword"
        ).value = "";

        document.getElementById(
            "stNewPassword"
        ).value = "";

        document.getElementById(
            "stConfirmPassword"
        ).value = "";

    }

    else {

        showFormAlert(
            "settingsAlert",
            "❌ Failed: " +
            (data.detail || "Unknown error"),
            "error"
        );

    }

}


// ==========================================================
// Role Permission
// ==========================================================

function applyRolePermission() {

    const addDeviceMenu =
        document.querySelector(
            '[data-target="panel-create"]'
        );

    const adminMenu =
        document.querySelector(
            '[data-target="panel-admin"]'
        );


    if (
        CURRENT_ROLE === "read" ||
        CURRENT_ROLE === "write"
    ) {

        if (addDeviceMenu) {
            addDeviceMenu.style.display = "none";
        }

        if (adminMenu) {
            adminMenu.style.display = "none";
        }

    }

    // Bulk Create/Remove User বাটন শুধু write ও super_admin দেখবে
    if (CURRENT_ROLE === "read") {

        const bulkCreateBtn = document.getElementById("bulkCreateBtn");
        const bulkRemoveBtn = document.getElementById("bulkRemoveBtn");

        if (bulkCreateBtn) bulkCreateBtn.style.display = "none";
        if (bulkRemoveBtn) bulkRemoveBtn.style.display = "none";

    }

}


// ==========================================================
// Admin List
// ==========================================================

async function loadAdminList() {

    const res =
        await fetch("/api/admin/list");

    const body =
        document.getElementById("adminTableBody");


    if (!res.ok) {

        body.innerHTML = `
            <tr>
                <td colspan="5">
                    Admin List Load Failed
                </td>
            </tr>
        `;

        return;

    }


    const data = await res.json();

    body.innerHTML = "";


    data.admins.forEach((a) => {

        body.innerHTML += `

            <tr>

                <td>${a.id}</td>

                <td>
                    ${a.username}
                    ${a.is_me ? "(You)" : ""}
                </td>

                <td>
                    <span class="status-badge role-${a.role}">${a.role}</span>
                </td>

                <td>${a.created_at}</td>

                <td>

                    ${
                        CURRENT_ROLE === "super_admin"
                        ?
                        `

                        <button class="btn btn-sm btn-primary" onclick="changeRole(${a.id})">
                            Role
                        </button>

                        <button class="btn btn-sm btn-warning" onclick="resetPassword(${a.id})">
                            Reset
                        </button>

                        <button class="btn btn-sm btn-danger" onclick="deleteAdmin(${a.id})">
                            Delete
                        </button>

                        `
                        :
                        `
                        <span class="text-muted">
                            No Permission
                        </span>
                        `
                    }

                </td>

            </tr>

        `;

    });

}


// ==========================================================
// Dashboard Summary Cards (Total Devices / Groups / Online / Offline)
// ==========================================================

async function loadSummaryCards() {

    const totalEl = document.getElementById("summaryTotalDevices");
    const groupsEl = document.getElementById("summaryTotalGroups");
    const onlineEl = document.getElementById("summaryOnline");
    const offlineEl = document.getElementById("summaryOffline");

    if (!totalEl) {
        return;
    }

    try {

        const res = await fetch("/api/device/list");

        if (!res.ok) {
            return;
        }

        const data = await res.json();
        const devices = data.devices || [];

        const groups = new Set(devices.map((d) => d.group_name));
        const online = devices.filter((d) => d.status === "Online").length;

        totalEl.textContent = devices.length;
        groupsEl.textContent = groups.size;
        onlineEl.textContent = online;
        offlineEl.textContent = devices.length - online;

    } catch (err) {
        // চুপচাপ থাকবে -- summary card না দেখালেও বাকি Dashboard কাজ করবে
    }

}


// ==========================================================
// Summary Card Click -> নির্দিষ্ট Panel/Filter এ নিয়ে যায়
// ==========================================================

function summaryCardClick(type) {

    if (type === "groups") {
        // Groups এর আলাদা কোনো লিস্ট পেজ নেই -- তাই Search Filters এ
        // নিয়ে গিয়ে Group ড্রপডাউন খুলে দেওয়া হচ্ছে যাতে গ্রুপ অনুযায়ী দেখা যায়
        switchPanel("panel-search");
        toggleFilterDropdown("groupDropdown");
        return;
    }

    // all / online / offline -> Add Device পেজের Device List এ
    switchPanel("panel-create");

    if (type === "online") {
        loadDeviceList("online");
    } else if (type === "offline") {
        loadDeviceList("offline");
    } else {
        loadDeviceList();
    }

}


// ==========================================================
// Device List
// ==========================================================

async function loadDeviceList(statusFilter = null) {

    const res =
        await fetch("/api/device/list");

    const body =
        document.getElementById("deviceTableBody");

    const filterLabel =
        document.getElementById("deviceListFilterLabel");

    if (!body) {
        return;
    }


    if (!res.ok) {

        body.innerHTML = `
            <tr>
                <td colspan="7">
                    Device List Load Failed
                </td>
            </tr>
        `;

        return;

    }


    const data = await res.json();

    let devices = data.devices || [];

    if (statusFilter === "online") {
        devices = devices.filter((d) => d.status === "Online");
        if (filterLabel) filterLabel.textContent = "(Online only)";
    } else if (statusFilter === "offline") {
        devices = devices.filter((d) => d.status !== "Online");
        if (filterLabel) filterLabel.textContent = "(Offline / Unknown only)";
    } else if (filterLabel) {
        filterLabel.textContent = "";
    }

    body.innerHTML = "";


    if (devices.length === 0) {

        body.innerHTML = `
            <tr>
                <td colspan="7" class="text-muted">
                    No devices found.
                </td>
            </tr>
        `;

        return;

    }


    devices.forEach((d) => {

        body.innerHTML += `

            <tr>

                <td>${d.group_name}</td>

                <td>${d.zone}</td>

                <td>${d.vendor}</td>

                <td>${d.hostname}</td>

                <td>${d.ip_address}</td>

                <td>${d.status || "Unknown"}</td>

                <td>

                    ${
                        CURRENT_ROLE === "super_admin"
                        ?
                        `
                        <button class="btn btn-sm btn-primary" onclick="openEditDeviceModal(${d.id})">
                            ✏️ Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteDevice(${d.id}, '${d.hostname}')">
                            🗑️ Delete
                        </button>
                        `
                        :
                        `
                        <span class="text-muted">
                            No Permission
                        </span>
                        `
                    }

                </td>

            </tr>

        `;

    });

    // Edit মডালের জন্য মেমোরিতে রাখা হচ্ছে, যাতে আলাদা করে আবার fetch করতে না হয়
    window.DEVICE_LIST_CACHE = data.devices;

}


// ==========================================================
// Delete Device
// ==========================================================

async function deleteDevice(id, hostname) {

    if (
        !confirm(
            `Are you sure you want to remove '${hostname}' from the list?\n\n` +
            `⚠️ This only removes it from our system's database -- no change ` +
            `will be made on the device (router/switch), and any users on it will remain as-is.`
        )
    ) {
        return;
    }


    const res = await fetch("/api/device/delete", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            device_id: id
        })

    });


    const data = await res.json();

    alert(
        data.detail ||
        (res.ok ? "Deleted" : "Failed")
    );

    loadDeviceList();

    loadFilters();

}

async function createAdmin() {

    const username =
        document.getElementById("newAdminUsername").value;

    const password =
        document.getElementById("newAdminPassword").value;

    const role =
        document.getElementById("newAdminRole").value;


    const res = await fetch(
        "/api/admin/create",
        {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username,
                password,
                role
            })

        }
    );


    const data = await res.json();


    if (!res.ok) {

        alert(data.detail);

        return;

    }


    alert("Admin Created");


    document.getElementById(
        "newAdminUsername"
    ).value = "";

    document.getElementById(
        "newAdminPassword"
    ).value = "";


    loadAdminList();

}


// ==========================================================
// Change Role
// ==========================================================

async function changeRole(id) {

    const role =
        prompt(
            "read / write / super_admin"
        );


    if (!role) {
        return;
    }


    const res =
        await fetch(
            "/api/admin/edit-role",
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    admin_id: id,
                    role
                })

            }
        );


    const data = await res.json();


    alert(
        data.detail ||
        "Role Updated"
    );


    loadAdminList();

}


// ==========================================================
// Reset Password
// ==========================================================

async function resetPassword(id) {

    const pass =
        prompt("New Password");


    if (!pass) {
        return;
    }


    const res =
        await fetch(
            "/api/admin/reset-password",
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    admin_id: id,
                    new_password: pass
                })

            }
        );


    const data = await res.json();


    alert(
        data.detail ||
        "Password Reset"
    );

}


// ==========================================================
// Delete Admin
// ==========================================================

async function deleteAdmin(id) {

    if (!confirm("Delete Admin?")) {
        return;
    }


    const res =
        await fetch(
            "/api/admin/delete",
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    admin_id: id
                })

            }
        );


    const data = await res.json();


    alert(
        data.detail ||
        "Deleted"
    );


    loadAdminList();

}

// ==========================================================
// ⚡ Bulk Create/Remove User (Search Filters এর সাথে connected)
// নতুন, সম্পূর্ণ isolated ফিচার -- উপরের কোনো ফাংশন/লজিক এখানে
// পরিবর্তন করা হয়নি।
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("bulkCreateBtn")
        ?.addEventListener("click", openBulkCreateModal);

    document.getElementById("bulkRemoveBtn")
        ?.addEventListener("click", openBulkRemoveModal);

    document.getElementById("bulkCreateCancelBtn")
        ?.addEventListener("click", closeBulkCreateModal);

    document.getElementById("bulkCreateConfirmBtn")
        ?.addEventListener("click", confirmBulkCreate);

    document.getElementById("bulkRemoveCancelBtn")
        ?.addEventListener("click", closeBulkRemoveModal);

    document.getElementById("bulkRemoveConfirmBtn")
        ?.addEventListener("click", confirmBulkRemove);

});


// বর্তমান Search Filter থেকে payload বানানো (groups/zones/devices/username)
function getBulkFilterPayload() {

    return {
        groups: getSelectedValues("groupOptions"),
        zones: getSelectedValues("zoneOptions"),
        devices: getSelectedValues("deviceOptions"),
        username:
            document.getElementById("filterUsername")
                ?.value.trim() || "",
        dry_run:
            document.getElementById("testModeToggle")
                ?.checked || false,
    };
}


// filter অনুযায়ী কয়টা ডিভাইসে action পড়বে, একটা আনুমানিক count বের করা
// (deviceOptions এ যা checkbox আছে, সেটাই বর্তমান cascade অনুযায়ী সম্ভাব্য ডিভাইস তালিকা)
function getBulkDeviceCount(payload) {

    if (payload.devices.length > 0) {
        return payload.devices.length;
    }

    const deviceContainer = document.getElementById("deviceOptions");
    return deviceContainer
        ? deviceContainer.querySelectorAll("input[type=checkbox]").length
        : 0;
}


// ==========================================================
// Bulk Create User
// ==========================================================

function openBulkCreateModal() {

    const payload = getBulkFilterPayload();

    if (!payload.username) {
        alert("Please enter a username in the Username box first.");
        return;
    }

    const count = getBulkDeviceCount(payload);

    if (count === 0) {
        alert("No devices found matching the filter.");
        return;
    }

    document.getElementById("bulkCreateUsername").value = payload.username;
    document.getElementById("bulkCreatePassword").value = "";
    document.getElementById("bulkCreateGroup").value = "full";
    document.getElementById("bulkCreateAddress").value = "";
    document.getElementById("bulkCreateAlert").innerHTML = "";

    const testModeNote = payload.dry_run
        ? " 🧪 Test Mode is ON -- no real change will be made on devices."
        : "";

    document.getElementById("bulkCreateSummary").textContent =
        (payload.devices.length === 0
            ? `⚠️ "All Devices" is selected -- this action will apply to all ${count} devices.`
            : `This action will apply to ${count} selected devices.`) + testModeNote;

    document.getElementById("bulkCreateModal").classList.remove("hidden");
}


function closeBulkCreateModal() {
    document.getElementById("bulkCreateModal").classList.add("hidden");
}


async function confirmBulkCreate() {

    const payload = getBulkFilterPayload();
    payload.password = document.getElementById("bulkCreatePassword").value;
    payload.group = document.getElementById("bulkCreateGroup").value || "full";
    payload.address = document.getElementById("bulkCreateAddress").value.trim() || null;

    if (!payload.password) {
        showFormAlert("bulkCreateAlert", "Password is required.", "error");
        return;
    }

    const btn = document.getElementById("bulkCreateConfirmBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Working...";

    try {

        const res = await fetch("/api/bulk-user/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();

        if (!res.ok) {
            showFormAlert(
                "bulkCreateAlert",
                "❌ Failed: " + (data.detail || "Unknown error"),
                "error"
            );
            return;
        }

        closeBulkCreateModal();

        renderBulkResults(
            data.dry_run ? "Create User (🧪 Test Mode)" : "Create User",
            payload.username,
            data,
            data.dry_run
                ? `🧪 ${data.would_create} would be created | ⚠️ ${data.skipped} already existed | ❌ ${data.errored} errors (no real change made)`
                : `✅ ${data.created} created | ⚠️ ${data.skipped} already existed | ❌ ${data.errored} errors`
        );

        loadActivityLog();

    } catch (error) {

        console.error("bulk create error:", error);
        showFormAlert("bulkCreateAlert", "❌ Failed to send request.", "error");

    } finally {

        btn.disabled = false;
        btn.textContent = "✅ Create";

    }
}


// ==========================================================
// Bulk Remove User
// ==========================================================

function openBulkRemoveModal() {

    const payload = getBulkFilterPayload();

    if (!payload.username) {
        alert("Please enter a username in the Username box first.");
        return;
    }

    const count = getBulkDeviceCount(payload);

    if (count === 0) {
        alert("No devices found matching the filter.");
        return;
    }

    const testModeNote = payload.dry_run
        ? " 🧪 Test Mode is ON -- no real change will be made on devices."
        : "";

    document.getElementById("bulkRemoveSummary").textContent =
        (payload.devices.length === 0
            ? `⚠️ "All Devices" is selected -- '${payload.username}' will be removed from all ${count} devices.`
            : `'${payload.username}' will be removed from ${count} selected devices.`) + testModeNote;

    document.getElementById("bulkRemoveModal").classList.remove("hidden");
}


function closeBulkRemoveModal() {
    document.getElementById("bulkRemoveModal").classList.add("hidden");
}


async function confirmBulkRemove() {

    const payload = getBulkFilterPayload();

    const btn = document.getElementById("bulkRemoveConfirmBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Working...";

    try {

        const res = await fetch("/api/bulk-user/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();

        if (!res.ok) {
            alert("❌ Failed: " + (data.detail || "Unknown error"));
            return;
        }

        closeBulkRemoveModal();

        renderBulkResults(
            data.dry_run ? "Remove User (🧪 Test Mode)" : "Remove User",
            payload.username,
            data,
            data.dry_run
                ? `🧪 ${data.would_delete} would be removed | ℹ️ ${data.skipped} not found | ❌ ${data.errored} errors (no real change made)`
                : `✅ ${data.deleted} removed | ℹ️ ${data.skipped} not found | ❌ ${data.errored} errors`
        );

        loadActivityLog();

    } catch (error) {

        console.error("bulk delete error:", error);
        alert("❌ Failed to send request.");

    } finally {

        btn.disabled = false;
        btn.textContent = "🗑️ Confirm, Remove";

    }
}


// ==========================================================
// Bulk Result Table রেন্ডার করা (Create ও Remove দুটোতেই ব্যবহার হয়)
// ==========================================================

function renderBulkResults(actionTitle, username, data, summaryText) {

    const card = document.getElementById("bulkResultCard");
    const title = document.getElementById("bulkResultTitle");
    const summary = document.getElementById("bulkResultSummary");
    const body = document.getElementById("bulkResultBody");

    title.textContent = `⚡ Bulk ${actionTitle} Result -- '${username}'`;
    summary.textContent = summaryText;

    body.innerHTML = "";

    if (!data.results || data.results.length === 0) {
        body.innerHTML = `<tr><td colspan="4" class="text-muted">No devices found.</td></tr>`;
    } else {

        data.results.forEach((r) => {

            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${r.group_name}</td>
                <td>${r.zone}</td>
                <td>${r.hostname}</td>
                <td>${r.message}</td>
            `;

            body.appendChild(tr);
        });
    }

    card.classList.remove("hidden");
    card.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ==========================================================
// ✏️ Edit Device (নতুন, isolated -- Delete/Add Device এর লজিক টাচ হয়নি)
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("editDeviceCancelBtn")
        ?.addEventListener("click", closeEditDeviceModal);

    document.getElementById("editDeviceSaveBtn")
        ?.addEventListener("click", confirmEditDevice);

});


function openEditDeviceModal(deviceId) {

    const device = (window.DEVICE_LIST_CACHE || [])
        .find((d) => d.id === deviceId);

    if (!device) {
        alert("Device data not found, please Load the list again.");
        return;
    }

    document.getElementById("edDeviceId").value = device.id;
    document.getElementById("edGroup").value = device.group_name;
    document.getElementById("edZone").value = device.zone;
    document.getElementById("edVendor").value = device.vendor;
    document.getElementById("edHostname").value = device.hostname;
    document.getElementById("edIp").value = device.ip_address;
    document.getElementById("edPort").value = device.ssh_port || 22;
    document.getElementById("edSshUser").value = device.ssh_username || "";
    document.getElementById("edSshPass").value = "";
    document.getElementById("editDeviceAlert").innerHTML = "";

    document.getElementById("editDeviceModal").classList.remove("hidden");
}


function closeEditDeviceModal() {
    document.getElementById("editDeviceModal").classList.add("hidden");
}


async function confirmEditDevice() {

    const payload = {
        device_id: parseInt(document.getElementById("edDeviceId").value, 10),
        group_name: document.getElementById("edGroup").value.trim(),
        zone: document.getElementById("edZone").value.trim(),
        vendor: document.getElementById("edVendor").value,
        hostname: document.getElementById("edHostname").value.trim(),
        ip_address: document.getElementById("edIp").value.trim(),
        ssh_port: parseInt(document.getElementById("edPort").value, 10) || 22,
        ssh_username: document.getElementById("edSshUser").value.trim(),
        ssh_password: document.getElementById("edSshPass").value || null,
    };

    if (!payload.group_name || !payload.zone || !payload.hostname || !payload.ip_address || !payload.ssh_username) {
        showFormAlert("editDeviceAlert", "All fields (except Password) are required.", "error");
        return;
    }

    const btn = document.getElementById("editDeviceSaveBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Saving...";

    try {

        const res = await fetch("/api/device/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();

        if (!res.ok) {
            showFormAlert("editDeviceAlert", "❌ " + (data.detail || "Failed"), "error");
            return;
        }

        closeEditDeviceModal();
        loadDeviceList();
        loadFilters();

    } catch (error) {

        console.error("edit device error:", error);
        showFormAlert("editDeviceAlert", "❌ Failed to send request.", "error");

    } finally {

        btn.disabled = false;
        btn.textContent = "💾 Save";

    }
}