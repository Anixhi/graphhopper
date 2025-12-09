from unittest.mock import patch, MagicMock
import netconf_automation

@patch("netconf_automation.manager.connect")
def test_netconf_execution(mock_connect):
    mock_mgr = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_mgr

    netconf_automation.send_webex_message = MagicMock()
    netconf_automation.manager = mock_mgr

    assert mock_connect.called
Write to John Andrei Tonel
