"""
automation/arista.py
----------------------
Arista (EOS) ডিভাইসের জন্য Search / Create / Edit / Delete / Verify কমান্ড।
(Cisco IOS এর মতোই সিনট্যাক্স)
"""


"""
automation/arista.py
---------------------
Arista EOS User Management Commands

Flow:
1. Search User
2. Verify User
3. Create User
4. Edit User
5. Delete User
"""


def search_user(connection, username: str):
    """
    Arista EOS-এ User আছে কিনা Search করে।
    """
    command = f"show users accounts | include {username}"

    output = connection.send_command(command)
    # ⚠️ ফিক্স: আগে "username in output" থাকায় prefix-match (যেমন 'admin'
    # খুঁজতে গিয়ে 'admin2' লাইনে মিলে যাওয়া) ভুলভাবে exists=True দেখাতো।
    # এখন প্রতিটা লাইন আলাদাভাবে চেক করে দেখা হচ্ছে ঠিক সেই username-ই আছে কিনা
    # (cisco.py/huawei.py তে যেভাবে আগেই ফিক্স করা হয়েছিল, সেভাবেই)।
    exists = any(
        line.strip().startswith(f"{username} ") or line.strip() == username
        for line in output.splitlines()
    )

    return exists, output


def verify_user(connection, username: str):
    """
    Create/Edit/Delete এর পরে আবার User Verify করে।
    """
    command = f"show users accounts {username}"

    output = connection.send_command(command)
    # ⚠️ ফিক্স: search_user()-এর মতোই একই কারণে -- সরাসরি substring
    # containment না দেখে exact লাইন ম্যাচ করা হচ্ছে।
    exists = any(
        line.strip().startswith(f"{username} ") or line.strip() == username
        for line in output.splitlines()
    ) and "% " not in output and "invalid" not in output.lower()

    return exists, output


def create_user(connection, username: str, password: str):
    """
    নতুন User Create করে।
    """
    config_commands = [
        f"username {username} privilege 15 secret {password}",
    ]

    output = connection.send_config_set(config_commands)

    connection.save_config()

    return output


def edit_user(connection, username: str, new_password: str):
    """
    User Password Change করে।
    """
    config_commands = [
        f"username {username} privilege 15 secret {new_password}",
    ]

    output = connection.send_config_set(config_commands)

    connection.save_config()

    return output


def delete_user(connection, username: str):
    """
    User Delete করে।
    """
    config_commands = [
        f"no username {username}",
    ]

    output = connection.send_config_set(config_commands)

    connection.save_config()

    return output