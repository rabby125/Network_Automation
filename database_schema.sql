-- ============================================================
-- Network Automation Project - Database Schema
-- এই ফাইলটা প্রথমে MySQL এ রান করবেন
-- ============================================================

CREATE DATABASE IF NOT EXISTS network_automation
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE network_automation;

-- ============================================================
-- 1) admin টেবিল -> Login System এর জন্য
-- ============================================================
CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,   -- এখানে hashed password থাকবে (plain text না)
    role ENUM('read', 'write', 'super_admin') NOT NULL DEFAULT 'read',  -- ⚠️ ফিক্স: আগে schema তে ছিল না, কিন্তু app/models/admin.py এটা ব্যবহার করে
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- 2) devices টেবিল -> সব নেটওয়ার্ক ডিভাইসের তথ্য থাকবে
-- ============================================================
CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,      -- যেমন: Circle Home
    zone VARCHAR(100) NOT NULL,            -- যেমন: Dhaka
    vendor VARCHAR(50) NOT NULL,           -- MikroTik / Cisco / Huawei / Juniper / Arista
    hostname VARCHAR(100) NOT NULL,        -- ডিভাইসের নাম, যেমন: MT-DHK-01
    ip_address VARCHAR(45) NOT NULL,       -- ডিভাইসের IP
    ssh_username VARCHAR(100) NOT NULL,    -- SSH login username
    ssh_password VARCHAR(255) NOT NULL,    -- SSH login password (production এ encrypt করে রাখা ভালো)
    ssh_port INT NOT NULL DEFAULT 22,      -- SSH Port (ডিফল্ট 22, MikroTik এ ভিন্ন হতে পারে)
    status VARCHAR(20) DEFAULT 'Unknown',  -- Online / Offline / Unknown
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_group (group_name),
    INDEX idx_zone (zone),
    INDEX idx_vendor (vendor)
) ENGINE=InnoDB;

-- ============================================================
-- 3) activity_log টেবিল -> কে, কখন, কোন ডিভাইসে, কী action করেছে -- এসব লগ থাকবে
--    ⚠️ ফিক্স: আগে schema তে এই টেবিলটাই ছিল না, কিন্তু app এর প্রতিটা
--    search/create/edit/delete action এ এখানে লগ লেখা হয় (দেখুন migration_v2_activity_log.sql)
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message VARCHAR(255) NOT NULL,          -- মানুষের পড়ার জন্য সামারি লাইন
    admin_username VARCHAR(50) NULL,        -- কোন Admin এই কাজ করেছে
    device_hostname VARCHAR(100) NULL,      -- কোন ডিভাইসে করা হয়েছে
    action VARCHAR(30) NULL,                -- create / edit / delete / verify / search
    result VARCHAR(30) NULL,                -- success / verify_failed / found / not_found
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- Test/Demo ডাটা (আপনি চাইলে বাদ দিতে পারেন)
-- ============================================================

-- Default admin user: username=admin, password=admin123
-- (password টা database.py চালু করলে app এর মধ্যেই bcrypt দিয়ে hash করে বসানো হবে,
--  চাইলে নিচের seed script দিয়েও বসাতে পারেন)

INSERT INTO devices (group_name, zone, vendor, hostname, ip_address, ssh_username, ssh_password, ssh_port, status)
VALUES
('Circle Home', 'Dhaka', 'MikroTik', 'MT-DHK-01', '10.10.10.1', 'admin', 'changeme', 22, 'Unknown'),
('Circle Home', 'Chattogram', 'Cisco', 'CS-CTG-01', '10.10.20.1', 'admin', 'changeme', 22, 'Unknown'),
('Circle Home', 'Dhaka', 'Huawei', 'HW-DHK-01', '10.10.30.1', 'admin', 'changeme', 22, 'Unknown');