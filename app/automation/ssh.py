"""
automation/ssh.py
-------------------
Netmiko দিয়ে যেকোনো Vendor এর ডিভাইসে SSH কানেকশন করার
জেনেরিক (Generic) ফাংশন এখানে থাকবে।
"""

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)
from app.services.crypto_service import decrypt_secret

# ডিভাইসের vendor নাম -> Netmiko এর device_type ম্যাপিং
VENDOR_DEVICE_TYPE_MAP = {
    "MikroTik": "mikrotik_routeros",
    "Cisco": "cisco_ios",
    "Huawei": "huawei",
    "Juniper": "juniper_junos",
    "Arista": "arista_eos",
}


class SSHConnectionError(Exception):
    """SSH কানেকশন এ সমস্যা হলে এই Exception থ্রো হবে"""
    pass


def get_netmiko_device_type(vendor: str) -> str:
    device_type = VENDOR_DEVICE_TYPE_MAP.get(vendor)
    if not device_type:
        raise SSHConnectionError(f"Vendor '{vendor}' is not supported.")
    return device_type


def connect_device(device):
    """
    device: app/models/device.py এর Device object (অথবা dict)
    রিটার্ন করবে: Netmiko ConnectHandler object (open কানেকশন)

    ব্যবহারের পর অবশ্যই connection.disconnect() কল করতে হবে,
    তাই এটা 'with' context এর মতো ব্যবহার করাই ভালো (নিচের helper দেখুন)।
    """
    device_type = get_netmiko_device_type(device.vendor)

    connection_params = {
        "device_type": device_type,
        "host": device.ip_address,
        "port": getattr(device, "ssh_port", 22) or 22,
        "username": device.ssh_username,
        "password": decrypt_secret(device.ssh_password),  # এখন এনক্রিপ্টেড থাকে, ব্যবহারের আগে ডিক্রিপ্ট
        "timeout": 15,
        "conn_timeout": 15,
        "banner_timeout": 15,
        "auth_timeout": 15,
        "fast_cli": False,
    }

    try:
        connection = ConnectHandler(**connection_params)
        return connection
    except NetmikoAuthenticationException:
        raise SSHConnectionError(
            f"'{device.hostname}' ({device.ip_address}) -> Wrong Username/Password."
        )
    except NetmikoTimeoutException:
        raise SSHConnectionError(
            f"'{device.hostname}' ({device.ip_address}) -> Connection Timeout, device may be Offline."
        )
    except Exception as e:
        raise SSHConnectionError(f"'{device.hostname}' -> Connection Error: {str(e)}")


class DeviceSession:
    """
    'with' statement দিয়ে ব্যবহার করার জন্য একটা সুবিধাজনক wrapper:

        with DeviceSession(device) as conn:
            output = conn.send_command("some command")

    কানেকশন শেষে automatic disconnect হয়ে যাবে।
    """

    def __init__(self, device):
        self.device = device
        self.connection = None

    def __enter__(self):
        self.connection = connect_device(self.device)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()