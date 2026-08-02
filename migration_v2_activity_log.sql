-- ============================================================
-- Migration v2: activity_log টেবিলে structured fields যোগ করা
-- আপনি যদি আগে থেকেই অ্যাপ চালিয়ে থাকেন (activity_log টেবিল
-- অটোমেটিক তৈরি হয়ে গেছে), তাহলে phpMyAdmin এর SQL ট্যাবে
-- এই কমান্ডগুলো রান করুন।
-- ============================================================

USE network_automation;

ALTER TABLE activity_log
    ADD COLUMN admin_username VARCHAR(50) NULL AFTER message,
    ADD COLUMN device_hostname VARCHAR(100) NULL AFTER admin_username,
    ADD COLUMN action VARCHAR(30) NULL AFTER device_hostname,
    ADD COLUMN result VARCHAR(30) NULL AFTER action;
