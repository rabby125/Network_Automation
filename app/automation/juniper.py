"""
automation/juniper.py
-----------------------
Juniper (JunOS) ডিভাইসের জন্য Search / Create / Edit / Delete / Verify কমান্ড।

⚠️ ফিক্স নোট: আগের ভার্সনে password parameter নেওয়া হতো কিন্তু কোনো
কমান্ডে ব্যবহারই হতো না (create/edit আসলে password সেট করত না)।

JunOS এ 'authentication plain-text-password' কমান্ড দিলে ডিভাইস
ইন্টারঅ্যাক্টিভভাবে "New password:" এবং "Retype new password:" জিজ্ঞেস করে।
তাই send_config_set() দিয়ে এক লাইনে হয় না -- send_command_timing() দিয়ে
ধাপে ধাপে প্রম্পটের জবাব দিতে হয়।
"""


"""
automation/juniper.py
----------------------
Juniper JunOS User Management Commands

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
    command = f"show configuration system login user {username}"

    output = connection.send_command(command)
    exists = output.strip() != "" and "unknown" not in output.lower()

    return exists, output


def verify_user(connection, username: str):
    """
    Create/Edit/Delete এর পরে আবার User Verify করে।
    """
    command = f"show configuration | display set | match {username}"

    output = connection.send_command(command)
    exists = output.strip() != "" and "unknown" not in output.lower()

    return exists, output


def _set_password_interactive(connection, username: str, password: str):
    """
    JunOS Interactive Password Prompt Handle করে।
    """
    output = connection.config_mode()

    output += connection.send_command_timing(
        f"set system login user {username} authentication plain-text-password"
    )

    output += connection.send_command_timing(password)

    output += connection.send_command_timing(password)

    return output


def create_user(connection, username: str, password: str):
    """
    নতুন User Create করে।
    """
    output = connection.send_config_set(
        [
            f"set system login user {username} class super-user"
        ]
    )

    output += _set_password_interactive(connection, username, password)

    output += connection.commit()

    connection.exit_config_mode()

    return output


def edit_user(connection, username: str, new_password: str):
    """
    User Password Change করে।
    """
    output = _set_password_interactive(
        connection,
        username,
        new_password,
    )

    output += connection.commit()

    connection.exit_config_mode()

    return output


def delete_user(connection, username: str):
    """
    User Delete করে।
    """
    config_commands = [
        f"delete system login user {username}",
    ]

    output = connection.send_config_set(config_commands)

    # ⚠️ ফিক্স: send_config_set() ডিফল্টভাবে কমান্ড পাঠানোর পর config mode
    # থেকে বের হয়ে আসে, ফলে এর ঠিক পরেই commit() কল করলে সেটা config mode
    # এর বাইরে থেকে চলত (create_user/edit_user এর মতো নয়, ওগুলোতে commit()
    # এর আগে config mode খোলাই থাকে)। এখন commit()-এর আগে আবার config mode এ
    # ঢুকে নেওয়া হচ্ছে যাতে candidate change (delete) ঠিকভাবে commit হয়।
    output += connection.config_mode()

    output += connection.commit()

    connection.exit_config_mode()

    return output