import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "collect_wifi_rssi.py"
spec = importlib.util.spec_from_file_location("collect_wifi_rssi", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_parse_iw_link_rejects_zero_rssi_sentinel_and_keeps_radio_metadata():
    result = mod.parse_iw_link("""Connected to 36:9f:61:c1:00:9f (on wlp1s0)
\tfreq: 5745
\tsignal: 0 dBm
\trx bitrate: 86.7 MBit/s VHT-MCS 9
\ttx bitrate: 433.3 MBit/s VHT-MCS 9
""")
    assert result["signal_dbm"] == ""
    assert result["frequency_mhz"] == 5745
    assert result["bssid"] == "36:9f:61:c1:00:9f"
    assert "86.7" in result["rx_bitrate"]


def test_parse_iw_station_prefers_valid_beacon_average():
    result = mod.parse_iw_station("""Station 36:9f:61:c1:00:9f (on wlp1s0)
\tsignal: 0 [0] dBm
\tsignal avg: -25 [-25] dBm
\tbeacon signal avg: -45 dBm
""")
    assert result["station_signal_dbm"] == ""
    assert result["station_signal_avg_dbm"] == -25.0
    assert result["beacon_signal_avg_dbm"] == -45.0


def test_parse_iw_link_valid_signal():
    result = mod.parse_iw_link("""Connected to 36:9f:61:c1:00:9f (on wlp1s0)
\tsignal: -51.00 dBm
\tsignal avg: -53.00 dBm
""")
    assert result["signal_dbm"] == -51.0
    assert result["signal_avg_dbm"] == -53.0


def test_parse_proc_wireless():
    result = mod.parse_proc_wireless("""Inter-| sta
 face | link level noise | nwid crypt frag retry misc
wlp1s0: 0000  65.  -49.  -256.  0 0 0 0 0 0
""", "wlp1s0")
    assert result["signal_dbm"] == -49.0
    assert result["link_quality"] == 65.0


def test_parse_nmcli_wifi():
    result = mod.parse_nmcli_wifi(r"*:36\:9F\:61\:C1\:00\:9F:69")
    assert result["signal_percent"] == 69
    assert result["bssid"] == "36:9F:61:C1:00:9F"


def test_phase_order_interleaves_labels():
    assert mod.PHASES == ("ABSENT", "PRESENT", "ABSENT", "PRESENT", "ABSENT")
