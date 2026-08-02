"""
automation/huawei.py
----------------------
Huawei (VRP) ডিভাইসের জন্য Search / Create / Edit / Delete / Verify কমান্ড।
"""


"""
automation/huawei.py
---------------------
Huawei VRP User Management Commands

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
    command = f"display current-configuration | include local-user {username}"

    output = connection.send_command(command)
    # ⚠️ ফিক্স: আগে "output.strip() != ''" থাকায় যেকোনো নন-এম্পটি আউটপুট
    # (এমনকি এরর মেসেজ বা প্রিফিক্স-ম্যাচ যেমন 'admin' খুঁজতে গিয়ে 'admin2'
    # লাইনে মিলে যাওয়া) ভুলভাবে exists=True দেখাতো। এখন প্রতিটা লাইন আলাদাভাবে
    # চেক করে দেখা হচ্ছে ঠিক সেই username-ই আছে কিনা।
    exists = any(
        line.strip().startswith(f"local-user {username} ")
        for line in output.splitlines()
    )

    return exists, output


def verify_user(connection, username: str):
    """
    Create/Edit/Delete এর পরে আবার User Verify করে।
    """
    command = f"display current-configuration | section local-user {username}"

    output = connection.send_command(command)
    # ⚠️ ফিক্স: search_user()-এর মতোই একই কারণে -- নন-এম্পটি আউটপুট মানেই
    # user আছে ধরে নেওয়া ভুল, এখন exact লাইন ম্যাচ করা হচ্ছে।
    exists = any(
        line.strip().startswith(f"local-user {username} ")
        for line in output.splitlines()
    )

    return exists, output


def create_user(connection, username: str, password: str):
    """
    নতুন User Create করে।
    """
    config_commands = [
        f"local-user {username} password irreversible-cipher {password}",
        f"local-user {username} privilege level 15",
        f"local-user {username} service-type ssh terminal",
    ]

    output = connection.send_config_set(config_commands)

    connection.save_config()

    return output


def edit_user(connection, username: str, new_password: str):
    """
    User Password Change করে।
    """
    config_commands = [
        f"local-user {username} password irreversible-cipher {new_password}",
    ]

    output = connection.send_config_set(config_commands)

    connection.save_config()

    return output


def delete_user(connection, username: str):
    """
    User Delete করে।
    """
    config_commands = [
        f"undo local-user {username}",
    ]

    output = connection.send_config_set(config_commands)

    connection.save_config()

    return output