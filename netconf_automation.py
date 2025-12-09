from ncclient import manager
import requests

DEVICE = {
    "host": "192.0.2.1",  # CHANGE if you have a real/simulated router
    "port": 830,
    "username": "admin",
    "password": "admin",
    "hostkey_verify": False
}

WEBEX_TOKEN = "PASTE_YOUR_WEBEX_TOKEN"
ROOM_ID = "PASTE_YOUR_ROOM_ID"

def send_webex_message(text):
    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {WEBEX_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"roomId": ROOM_ID, "text": text}
    requests.post(url, headers=headers, json=payload)

with manager.connect(**DEVICE) as m:
    before = m.get_config("running").data_xml
    open("running_before.xml", "w").write(before)

    edit_payload = """
    <config>
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>Loopback100</name>
          <description>Configured via NETCONF</description>
          <enabled>true</enabled>
        </interface>
      </interfaces>
    </config>
    """

    m.edit_config(target="running", config=edit_payload)

    after = m.get_config("running").data_xml
    open("running_after.xml", "w").write(after)

    send_webex_message("✅ L1 requested interface update completed successfully.")
