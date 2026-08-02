"""
automation/mikrotik.py
------------------------
MikroTik (RouterOS) ডিভাইসের জন্য Search / Verify / Create / Edit / Delete   কমান্ড।

⚠️ নোট: এখানে PPP secret (PPPoE user) হিসেবে ধরে কমান্ড লেখা হয়েছে,
কারণ ISP নেটওয়ার্কে সাধারণত এভাবেই user ম্যানেজ করা হয়।
আপনার হলে সাধারণ /user হলে কমান্ডগুলো সহজেই বদলে নিতে পারবেন
(নিচে কমেন্টে দুই ধরনের কমান্ডই দেওয়া আছে)।
"""

"""
automation/mikrotik.py
------------------------
MikroTik RouterOS (/user) User Management Commands

Flow:
1. Search User
2. Verify User
3. Create User
4. Edit User
5. Delete User
"""


def search_user(connection, username: str):
    """
    User আছে কিনা Search করে।
    """
    command = f'/user print where name="{username}"'

    output = connection.send_command(command)
    exists = username in output

    return exists, output


def verify_user(connection, username: str):
    """
    Create/Edit/Delete এর পরে আবার Router থেকে User Check করে।
    """
    command = f'/user print detail where name="{username}"'

    output = connection.send_command(command)
    exists = username in output

    return exists, output


def create_user(connection, username: str, password: str, group: str = "full", address: str | None = None):
    """
    নতুন User Create করে (RouterOS-এ 'group' বাধ্যতামূলক, না দিলে
    রাউটার কমান্ডটা reject করে -- এটাই আগে "Server error" এর কারণ ছিল)।
    Allowed Address ঐচ্ছিক -- দিলে শুধু সেই address/network থেকেই লগইন করা যাবে।
    """
    command = (
        f'/user add '
        f'name="{username}" '
        f'password="{password}" '
        f'group="{group}"'
    )

    if address:
        command += f' address="{address}"'

    output = connection.send_command(command)

    return output


def edit_user(connection, username: str, new_password: str, group: str | None = None, address: str | None = None):
    """
    User Password Change করে -- এখন চাইলে Group / Allowed Address ও একসাথে
    Update করা যাবে (Create Form এর মতোই ফিল্ড), যদি সেগুলো দেওয়া থাকে।
    """
    command = (
        f'/user set '
        f'[find name="{username}"] '
        f'password="{new_password}"'
    )

    if group:
        command += f' group="{group}"'

    if address:
        command += f' address="{address}"'

    output = connection.send_command(command)

    return output


def delete_user(connection, username: str):
    """
    User Delete করে।
    """
    command = (
        f'/user remove '
        f'[find name="{username}"]'
    )

    output = connection.send_command(command)

    return output