"""Milesight AI LPR 카메라 HTTP Post 수신 테스트 서버 (Python 표준 라이브러리만 사용)

실행:  python lpr_receiver.py [포트]      (기본 포트 8080)
카메라 Alarm Server 설정: Destination IP = 이 PC IP, Port = 위 포트, Path = /lpr
브라우저에서 http://localhost:8080/ 접속하면 수신 내역 확인 가능
"""
import base64
import json
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "received")
SNAPSHOT_KEYS = ("license_plate_snapshot", "vehicle_snapshot", "full_snapshot")
SAVE_IMAGE_KEYS = ("license_plate_snapshot",)  # 용량 절약: 번호판 이미지만 파일로 저장
DIRECTION_LABELS = {"Approach": "진입", "Away": "출차"}
LOW_CONFIDENCE = 0.45  # 이 값 이하 신뢰도는 화면에 빨간색 표시

events = []  # 최근 수신 내역 (메모리)


def save_snapshot(b64: str, path: str) -> bool:
    """base64 문자열(data URI 접두어 허용)을 jpg로 저장"""
    if not b64:
        return False
    if b64.startswith("data:") and "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    except Exception as e:
        print(f"  [!] 스냅샷 디코딩 실패 {os.path.basename(path)}: {e}")
        return False


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        os.makedirs(SAVE_DIR, exist_ok=True)

        print("=" * 70)
        print(f"[{datetime.now():%H:%M:%S}] POST {self.path} from {self.client_address[0]}  ({length} bytes)")
        print(f"  Content-Type : {self.headers.get('Content-Type')}")
        if self.headers.get("Authorization"):
            print(f"  Authorization: {self.headers.get('Authorization')[:20]}...")

        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            # JSON이 아닐 때만 원본 저장 (포맷 분석용)
            with open(os.path.join(SAVE_DIR, f"{stamp}_raw.bin"), "wb") as f:
                f.write(body)
            print("  [!] JSON 아님 - raw 파일만 저장. 앞부분:")
            print("  ", body[:300])
            events.append({"time": stamp, "path": self.path, "json": False, "size": length})
            self._reply()
            return

        # 스냅샷은 JSON에서 떼어내고 길이만 남김 (번호판 이미지만 파일로 저장)
        images = []
        for key in SNAPSHOT_KEYS:
            val = data.get(key)
            if isinstance(val, str) and val and val != "-":  # 카메라는 이미지 없으면 "-" 전송
                if key in SAVE_IMAGE_KEYS:
                    fname = f"{stamp}_{key}.jpg"
                    if save_snapshot(val, os.path.join(SAVE_DIR, fname)):
                        images.append(fname)
                    data[key] = f"<base64 {len(val)} chars -> {fname}>"
                else:
                    data[key] = f"<base64 {len(val)} chars, 저장 안 함>"

        with open(os.path.join(SAVE_DIR, f"{stamp}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  번호판   : {data.get('license_plate')}  (신뢰도 {data.get('plate_confidence')})")
        print(f"  이벤트   : {data.get('event_type')}  / 장치 {data.get('device_name')} ({data.get('mac_address')})")
        print(f"  시간     : {data.get('time')}  / 방향 {data.get('direction')}")
        print(f"  차량     : {data.get('vehicle_type')} {data.get('vehicle_color')} {data.get('vehicle_brand')}")
        print(f"  이미지   : {images or '없음'}")

        events.append({"time": stamp, "path": self.path, "json": True, "data": data, "images": images})
        del events[:-100]
        self._reply()

    def do_PUT(self):
        self.do_POST()

    def do_GET(self):
        # /received/파일 -> 저장된 이미지 제공
        if self.path.startswith("/received/"):
            fp = os.path.join(SAVE_DIR, os.path.basename(self.path))
            if os.path.isfile(fp):
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.end_headers()
                with open(fp, "rb") as f:
                    self.wfile.write(f.read())
                return
            self.send_error(404)
            return

        rows = []
        for e in reversed(events):
            if not e["json"]:
                rows.append(f"<tr><td colspan=7>JSON 아님 ({e['size']} bytes)</td></tr>")
                continue
            d = e["data"]
            imgs = "".join(f'<img src="/received/{i}" height=80> ' for i in e["images"])
            direction = DIRECTION_LABELS.get(d.get("direction"), d.get("direction") or "-")
            plate = d.get("license_plate") or ""
            conf = d.get("plate_confidence")
            try:
                low = float(conf) <= LOW_CONFIDENCE
            except (TypeError, ValueError):
                low = False
            conf_style = " style='color:red;font-weight:bold'" if low else ""
            rows.append(
                f"<tr><td>{d.get('time')}</td><td>{direction}</td>"
                f"<td>{d.get('vehicle_type')} {d.get('vehicle_color')}</td>"
                f"<td{conf_style}>{conf}</td><td><b>{plate}</b></td>"
                f"<td>{imgs}</td><td><b>{plate[-4:]}</b></td></tr>"
            )
        html = (
            "<html><head><meta charset=utf-8><meta http-equiv=refresh content=3>"
            "<title>LPR 수신 테스트</title></head><body style='font-family:sans-serif'>"
            f"<h2>LPR 수신 내역 ({len(events)}건)</h2>"
            "<table border=1 cellpadding=4 style='border-collapse:collapse'>"
            "<tr><th>감지시각</th><th>방향</th><th>차량</th><th>신뢰도</th><th>번호판</th><th>이미지</th><th>4자리</th></tr>"
            + "".join(rows) + "</table></body></html>"
        )
        self._reply(html.encode("utf-8"), "text/html; charset=utf-8")

    def _reply(self, body=b'{"result":"ok"}', ctype="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # 기본 접근 로그 생략 (do_POST에서 직접 출력)


if __name__ == "__main__":
    print(f"LPR 수신 서버 시작: 0.0.0.0:{PORT}  (저장 폴더: {SAVE_DIR})")
    print(f"수신 내역 보기: http://localhost:{PORT}/")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
