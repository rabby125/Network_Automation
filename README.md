# Network Automation Tool — সম্পূর্ণ সেটআপ গাইড (বাংলায়)

আপনার দেওয়া অর্ডার অনুযায়ী পুরো প্রজেক্ট তৈরি করা হয়েছে:
```
✅ MySQL admin + devices টেবিল
✅ database.py
✅ Admin ও Device Model
✅ Login System
✅ Dashboard UI
✅ Search API
✅ SSH Connection (Netmiko)
✅ Vendor Command (MikroTik/Cisco/Huawei/Juniper/Arista)
✅ Search Result দেখানো
✅ Create/Edit/Delete/Verify
```

---

## ⚠️ Security/Bug Fix Changelog (এই ভার্সনে যা ঠিক করা হয়েছে)

কোড রিভিউতে ধরা পড়া সমস্যাগুলো এখানে ঠিক করা হয়েছে:

1. **Juniper password flow** — আগে `password` parameter নেওয়া হতো কিন্তু ব্যবহারই হতো না। এখন JunOS এর ইন্টারঅ্যাক্টিভ প্রম্পট হ্যান্ডেল করে password সেট করে (`send_command_timing` দিয়ে) — তবে এটা device-specific prompt এর উপর নির্ভরশীল, তাই real ডিভাইসে টেস্ট করে prompt না মিললে জানাবেন।
2. **Server-side Verify + Duplicate Check** — Create/Edit/Delete এখন একটাই SSH সেশনে (search → action → verify) করে, এবং duplicate/not-found চেক করে conflict এ block করে (409 error)। Frontend আর আলাদা করে verify কল করে না — API response এর `verified` field ই সত্যিকারের প্রমাণ।
3. **SSH Password Encryption** — `devices.ssh_password` এখন **Fernet এনক্রিপশন** দিয়ে সেভ হয় (plain text না)। নতুন `.env` এ `FERNET_KEY` লাগবে (নিচে জেনারেট করার কমান্ড আছে)। আগে থেকে plain-text এ বসানো password গুলোর জন্য `migrate_encrypt_passwords.py` script আছে।
4. **Activity Log Schema** — শুধু `message` এর বদলে এখন `admin_username`, `device_hostname`, `action`, `result` — আলাদা কলাম আছে। আগে থেকে সেটআপ করা থাকলে `migration_v2_activity_log.sql` চালান।
5. **Insecure Default SECRET_KEY বাদ** — আগে `.env` না থাকলে একটা hardcoded fallback secret ব্যবহার হতো (নিরাপদ না)। এখন `.env` এ `SECRET_KEY` না থাকলে **অ্যাপই চালু হবে না** — নিচে জেনারেট করার কমান্ড দেওয়া আছে।
6. **Bonus fix**: `routers/device.py` (Create Device API) লেখা হয়েছিল কিন্তু `main.py` তে register করা হয়নি বলে কাজ করছিল না — এখন ঠিক করা হয়েছে।
7. **Sidebar UI সম্পূর্ণ** — Dashboard এর বাম পাশে এখন সাইডবার আছে: 🔍 Dashboard (Search), ➕ Create Device (ফর্ম দিয়ে নতুন ডিভাইস যোগ), ⚙️ Settings (নিজের Password পরিবর্তন), 🚪 Logout।
8. **Group/Zone/Vendor ডিফল্ট "All"** — এখন Multi-Select এ শুরুতেই "🔘 All" সিলেক্ট করা থাকে (মানে সব ডিভাইসে খুঁজবে)। নির্দিষ্ট একটা চাইলে সরাসরি ক্লিক করুন (single select হয়ে যাবে), একাধিক চাইলে Ctrl চেপে ধরে ক্লিক করুন (এটা browser এর normal native আচরণ)।

### ⚠️ যা এখনো সৎভাবে বাকি আছে

- **Role-based Access** — এখনো নেই, সব Admin সমান ক্ষমতা পায়। এটা বড় কাজ (Role টেবিল, permission checking), চাইলে আলাদা ধাপে করব।

---

## নতুন Environment Variable — অবশ্যই লাগবে

`.env` ফাইলে এই দুটো এখন **required** (না থাকলে অ্যাপ চালু হবে না):

```bash
# SECRET_KEY বানানোর কমান্ড:
python -c "import secrets; print(secrets.token_hex(32))"

# FERNET_KEY বানানোর কমান্ড:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

আগে থেকে অ্যাপ চালিয়ে থাকলে এই ধাপগুলো নিন:

```bash
# ১) নতুন .env variable যোগ করুন (উপরের কমান্ড দিয়ে জেনারেট করে)
# ২) phpMyAdmin এ migration_v2_activity_log.sql রান করুন
# ৩) devices টেবিলে ssh_port কলাম না থাকলে migration_add_port.sql রান করুন
# ৪) আগে থেকে থাকা plain-text ssh_password এনক্রিপ্ট করতে:
python migrate_encrypt_passwords.py
```

---

## ধাপ ১: প্রজেক্ট ফাইল প্রস্তুত করা

1. পুরো `Network_Automation` ফোল্ডারটা আপনার কম্পিউটার/সার্ভারে রাখুন।
2. Terminal খুলে ফোল্ডারের ভিতরে যান:
```bash
cd Network_Automation
```

---

## ধাপ ২: Python Virtual Environment বানানো (recommended)

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

---

## ধাপ ৩: প্রয়োজনীয় প্যাকেজ ইনস্টল করা

```bash
pip install -r requirements.txt
```

---

## ধাপ ৪: MySQL ডাটাবেজ তৈরি করা

আপনার MySQL এ লগইন করে `database_schema.sql` ফাইলটা রান করুন:

```bash
mysql -u root -p < database_schema.sql
```

এটা `network_automation` নামে একটা ডাটাবেজ বানাবে, তার ভিতরে `admin`, `devices` টেবিল বানাবে, এবং কিছু ডেমো ডিভাইস ডাটা ঢুকিয়ে দিবে।

> ⚠️ `devices` টেবিলে থাকা ডেমো ডাটার IP/username/password গুলো বদলে আপনার আসল ডিভাইসের তথ্য দিয়ে বসান (অথবা পরে Dashboard থেকেও নতুন ডিভাইস যোগ করার ফিচার বানিয়ে নিতে পারবেন)।

---

## ধাপ ৫: `.env` ফাইল বানানো

```bash
cp .env.example .env
```

তারপর `.env` ফাইল খুলে নিজের MySQL এর তথ্য বসান:

```
DB_USER=root
DB_PASSWORD=আপনার_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=network_automation
SECRET_KEY=যেকোনো-লম্বা-র‍্যান্ডম-স্ট্রিং-বসান
```

---

## ধাপ ৬: Admin User তৈরি করা (Login করার জন্য)

```bash
python create_admin.py
```

এটা আপনাকে জিজ্ঞেস করবে Username আর Password — যা দিবেন সেটা দিয়েই Login করতে পারবেন Dashboard এ।

---

## ধাপ ৭: Server চালু করা

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

এখন ব্রাউজারে যান:
```
http://localhost:8000
```
এটা automatically `/login` পেজে নিয়ে যাবে।

---

## কিভাবে কাজ করে (Flow)

1. **Login** করবেন `create_admin.py` দিয়ে বানানো username/password দিয়ে।
2. **Dashboard** এ Group/Zone/Vendor সিলেক্ট করে, Username লিখে **Search** চাপবেন।
3. সিস্টেম প্রতিটা মিলে যাওয়া ডিভাইসে **SSH (Netmiko)** দিয়ে ঢুকে, সেই ভেন্ডরের কমান্ড (MikroTik/Cisco/Huawei/...) চালিয়ে ইউজার আছে কিনা খুঁজে বের করবে।
4. যদি ইউজার **পাওয়া যায়** → Edit/Delete বাটন দেখাবে।
5. যদি ইউজার **না পাওয়া যায়** → Create User বাটন দেখাবে।
6. যেকোনো Action (Create/Edit/Delete) এর পর সিস্টেম **আবার Verify** করে নিশ্চিত হয় কাজ ঠিকমতো হয়েছে কিনা।
7. প্রতিটা কাজ **Activity Log** এ যোগ হয়ে যায়।

---

## ফোল্ডার স্ট্রাকচার

```
Network_Automation/
├── database_schema.sql       <- MySQL টেবিল বানানোর SQL
├── create_admin.py           <- Admin user তৈরির স্ক্রিপ্ট
├── requirements.txt
├── .env.example
│
├── app/
│   ├── main.py                <- FastAPI entry point
│   │
│   ├── automation/            <- Vendor অনুযায়ী কমান্ড
│   │   ├── ssh.py             <- Netmiko generic SSH connector
│   │   ├── mikrotik.py
│   │   ├── cisco.py
│   │   ├── huawei.py
│   │   ├── juniper.py
│   │   └── arista.py
│   │
│   ├── database/
│   │   └── database.py        <- MySQL কানেকশন (SQLAlchemy)
│   │
│   ├── models/
│   │   ├── admin.py
│   │   ├── device.py
│   │   └── activity_log.py    <- (Activity Log এর জন্য অতিরিক্ত)
│   │
│   ├── routers/
│   │   ├── auth.py            <- Login/Logout
│   │   ├── search.py          <- Search API + Filters + Activity Log
│   │   └── user.py            <- Create/Edit/Delete/Verify API
│   │
│   ├── services/
│   │   ├── auth_service.py    <- Password hash + JWT
│   │   ├── dependencies.py    <- Login-protected route checker
│   │   └── ssh_service.py     <- Vendor module orchestration
│   │
│   ├── templates/
│   │   ├── login.html
│   │   └── dashboard.html
│   │
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js
```

---

## ⚠️ গুরুত্বপূর্ণ নোট

1. **Vendor কমান্ড গুলো (mikrotik.py, cisco.py, huawei.py...)** — এগুলোতে সাধারণ/কমন সিনট্যাক্স দেওয়া আছে। আপনার ডিভাইসের exact OS version অনুযায়ী কমান্ড একটু ভিন্ন হতে পারে, তাই real ডিভাইসে টেস্ট করার আগে একবার manually SSH করে কমান্ডগুলো verify করে নিবেন।
2. **ssh_password** column এ এখন plain text এ পাসওয়ার্ড রাখা হচ্ছে ডেমোর জন্য সহজ রাখতে — প্রোডাকশনে এটা অবশ্যই এনক্রিপ্ট করে রাখা উচিত (যেমন `cryptography` লাইব্রেরির Fernet দিয়ে)। আমাকে বললে আমি এটাও যোগ করে দিতে পারি।
3. যদি কোনো জায়গায় ভুল পান বা এরর আসে, আমাকে exact error message সহ জানাবেন — আমি ঠিক করে দিব।
4. প্রতিটা ফাইলে বাংলায় কমেন্ট লেখা আছে, যাতে বুঝতে সুবিধা হয় কোন অংশ কী কাজ করছে।

---

## পরবর্তীতে যা যোগ করা যেতে পারে (আপনি চাইলে)

- Dashboard থেকেই নতুন Device (routers) যোগ/এডিট করার UI
- Password Encryption (Fernet)
- Role-based Access (Super Admin / Normal Admin)
- Bulk Search Progress Bar (অনেক ডিভাইস একসাথে চেক করলে)
- Docker দিয়ে Deployment
# Network_Automation
