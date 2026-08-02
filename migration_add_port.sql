-- ============================================================
-- migration_add_port.sql
-- আপনি আগে থেকেই ডাটাবেজ বানিয়ে ফেলেছেন, তাই নতুন করে সব বানানোর
-- দরকার নেই -- শুধু এই একটা কমান্ড phpMyAdmin এর SQL ট্যাবে গিয়ে
-- Run করলেই হবে।
-- ============================================================

USE network_automation;

ALTER TABLE devices
    ADD COLUMN ssh_port INT NOT NULL DEFAULT 22 AFTER ssh_password;

-- আপনার MikroTik ডিভাইসের Port যদি 22 না হয়ে অন্য কিছু হয়,
-- তাহলে এভাবে বদলে দিন (id=1 আপনার MikroTik রো):
-- UPDATE devices SET ssh_port = 22 WHERE id = 1;
