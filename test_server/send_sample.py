"""카메라 없이 수신 서버를 테스트하는 샘플 전송기 (프로토콜 문서의 sample 그대로)

실행:  python send_sample.py [URL]    (기본 http://localhost:8080/lpr)
"""
import json
import sys
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/lpr"

sample = {
    "event_type": "general",
    "device_name": "4G ANPR Parking Camera",
    "mac_address": "1C:C3:16:56:BB:5A",
    "sn": "42302626QE210001",
    "uuid": "",
    "time": "2026-11-18 09:55:21",
    "utctime": "2026-11-18 09:55:21",
    "utc_iso_time": "2026-11-18 09:55:21",
    "local_iso_time": "2026-11-18 09:55:21",
    "detection_region": 1,
    "detection_region_name": "region_1",
    "trigger_line_state": "",
    "license_plate": "ABC1234",
    "plate_confidence": 90,
    "country_region": "",
    "plate_type": "normal",
    "plate_color": "white",
    "vehicle_type": "car",
    "vehicle_color": "black",
    "vehicle_brand": "-",
    "direction": "",
    "data_list": {"detection_trigger": "Always"},
    "resolution_width": 1920,
    "resolution_height": 1080,
    "coordinate_x1": 0, "coordinate_y1": 0, "coordinate_x2": 100, "coordinate_y2": 100,
    "vehicle_tracking_box_x1": 0, "vehicle_tracking_box_y1": 0,
    "vehicle_tracking_box_x2": 100, "vehicle_tracking_box_y2": 100,
    "license_plate_snapshot": "",
    "vehicle_snapshot": "",
    "full_snapshot": "",
}

req = urllib.request.Request(
    URL, data=json.dumps(sample).encode("utf-8"),
    headers={"Content-Type": "application/json"}, method="POST",
)
with urllib.request.urlopen(req, timeout=5) as resp:
    print(resp.status, resp.read().decode())
