#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║   IPTV VALIDATOR CHECKER — GUI Edition                  ║
║   by M4DI~UciH4  |  v3.1                               ║
║   Requires: Python 3.8+, requests                       ║
║   GUI: tkinter (built-in, no extra install)             ║
╚══════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────
#  DEPENDENCY CHECK
# ─────────────────────────────────────────────────────────
import sys, os

def _check_deps():
    missing = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    if missing:
        print(f"[!] Module tidak ditemukan: {', '.join(missing)}")
        print(f"    Jalankan: pip install {' '.join(missing)}")
        sys.exit(1)

_check_deps()

# ─────────────────────────────────────────────────────────
#  IMPORTS
# ─────────────────────────────────────────────────────────
import re, time, socket, urllib.parse
import threading, queue, csv, datetime
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ─────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────
VERSION    = "3.1"
AUTHOR     = "M4DI~UciH4"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Warna tema dark (hex)
C_BG       = "#0d0f14"   # background utama
C_PANEL    = "#161b22"   # panel / card
C_BORDER   = "#21262d"   # border halus
C_ACCENT   = "#00d4ff"   # cyan accent
C_ACCENT2  = "#ff6b35"   # orange accent
C_GREEN    = "#39d353"
C_RED      = "#f85149"
C_YELLOW   = "#e3b341"
C_PURPLE   = "#bc8cff"
C_TEXT     = "#c9d1d9"   # teks utama
C_MUTED    = "#484f58"   # teks redup
C_WHITE    = "#f0f6fc"
C_ROWALT   = "#1a2030"   # row alternating

STATUS_COLOR = {
    "ONLINE":   C_GREEN,
    "OFFLINE":  C_RED,
    "REDIRECT": C_YELLOW,
    "TIMEOUT":  C_YELLOW,
    "ERROR":    C_PURPLE,
    "PENDING":  C_MUTED,
}

# ─────────────────────────────────────────────────────────
#  CORE LOGIC
# ─────────────────────────────────────────────────────────
def parse_m3u(filepath: str):
    """
    Parse file M3U.
    Return: (list[dict], error_str | None)
    """
    if not os.path.exists(filepath):
        return [], f"File tidak ditemukan: {filepath}"
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except Exception as exc:
        return [], str(exc)

    channels = []
    cur: dict = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("##"):
            continue
        if line.startswith("#EXTINF"):
            cur = {"extinf": line, "name": "", "group": "", "logo": ""}
            if "," in line:
                cur["name"] = line.split(",", 1)[-1].strip()
            m = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
            if m:
                cur["group"] = m.group(1)
            m = re.search(r'tvg-logo="([^"]*)"', line, re.IGNORECASE)
            if m:
                cur["logo"] = m.group(1)
        elif line.startswith(("http://", "https://", "rtmp://", "rtsp://")):
            if not cur:
                cur = {"extinf": f"#EXTINF:-1,Channel_{len(channels)+1}",
                       "name": f"Channel_{len(channels)+1}", "group": "", "logo": ""}
            cur["url"] = line
            if not cur.get("name"):
                cur["name"] = f"Channel_{len(channels)+1}"
            channels.append(dict(cur))
            cur = {}
    return channels, None


def _make_session() -> requests.Session:
    sess = requests.Session()
    retry = Retry(total=1, backoff_factor=0.2,
                  status_forcelist=[500, 502, 503, 504],
                  raise_on_status=False)
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess


# ─────────────────────────────────────────────────────────
#  MPD MANIFEST PARSER
# ─────────────────────────────────────────────────────────
def parse_mpd_manifest(xml_text: str, base_url: str) -> dict:
    """
    Parse konten XML MPD manifest.
    Return dict:
      type        : 'LIVE' | 'VOD' | 'unknown'
      drm         : True/False
      drm_systems : list nama DRM (Widevine, PlayReady, ClearKey)
      base_url    : base URL stream
      init_url    : URL segment init/pertama untuk dicek
      error       : pesan error jika parse gagal
    """
    result = {
        "type": "unknown", "drm": False,
        "drm_systems": [], "base_url": base_url,
        "init_url": "", "error": ""
    }
    try:
        root = ET.fromstring(xml_text)

        # ── Tipe stream ──
        mpd_type = root.get("type", "static")
        result["type"] = "LIVE" if mpd_type == "dynamic" else "VOD"

        # ── Deteksi DRM via ContentProtection ──
        drm_set = set()
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "ContentProtection":
                s = elem.get("schemeIdUri", "").lower()
                val = elem.get("value", "").lower()
                if "edef8ba9" in s or "widevine" in s:
                    drm_set.add("Widevine")
                elif "9a04f079" in s or "playready" in s:
                    drm_set.add("PlayReady")
                elif "e2719d58" in s or "clearkey" in s or "clearkey" in val:
                    drm_set.add("ClearKey")
                elif s and s != "urn:mpeg:dash:mp4protection:2011":
                    drm_set.add("DRM-Unknown")
        result["drm"] = len(drm_set) > 0
        result["drm_systems"] = sorted(drm_set)

        # ── BaseURL ──
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "BaseURL" and elem.text:
                burl = elem.text.strip()
                result["base_url"] = (
                    burl if burl.startswith("http")
                    else urllib.parse.urljoin(base_url, burl)
                )
                break

        # ── Init / segment pertama ──
        # Prioritas: SegmentTemplate initialization > SegmentURL > SegmentBase
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "SegmentTemplate":
                init = elem.get("initialization", "")
                if init:
                    # Bersihkan template variable seperti $RepresentationID$
                    init_clean = re.sub(r"\$[^$]+\$", "1", init)
                    result["init_url"] = urllib.parse.urljoin(
                        result["base_url"], init_clean
                    )
                    break
            elif tag == "SegmentURL":
                media = elem.get("media", "")
                if media:
                    result["init_url"] = urllib.parse.urljoin(
                        result["base_url"], media
                    )
                    break
            elif tag == "SegmentBase":
                init_range = elem.get("indexRange", "")
                if init_range:
                    result["init_url"] = result["base_url"]
                    break

    except ET.ParseError as exc:
        result["error"] = f"XML parse error: {str(exc)[:60]}"
    except Exception as exc:
        result["error"] = f"MPD parse error: {str(exc)[:60]}"

    return result


def check_mpd(url: str, timeout: int = 10) -> dict:
    """
    Validasi khusus MPD/DASH stream dengan 3 tahap:
      1. Download manifest .mpd
      2. Parse XML → deteksi DRM, tipe, init URL
      3. Cek aksesibilitas init segment (jika tidak DRM)
    Return format sama dengan check_url.
    """
    result = {"url": url, "status": "OFFLINE",
              "code": None, "latency": 0, "reason": ""}
    sess = _make_session()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/dash+xml, application/xml, */*",
        "Connection": "close",
    }
    # Referer hints
    for pattern, ref in (
        ("cloudfront",  "https://www.visionplus.id/"),
        ("3bbtv",       "https://www.3bb.co.th/"),
        ("jwplive",     "https://cdn.jwplayer.com/"),
        ("telewebion",  "https://telewebion.com/"),
        ("ciao-ott",    "https://ciao-ott.net/"),
    ):
        if pattern in url:
            headers["Referer"] = ref
            break

    # ── Tahap 1: Download manifest ──
    try:
        t0 = time.monotonic()
        resp = sess.get(url, headers=headers, timeout=timeout, stream=True)
        # Baca max 512 KB (cukup untuk manifest XML)
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= 524288:
                break
        resp.close()
        lat = int((time.monotonic() - t0) * 1000)
        result["latency"] = lat
        result["code"] = resp.status_code
    except requests.exceptions.Timeout:
        result.update(status="TIMEOUT", reason=f"Timeout >{timeout}s saat download manifest")
        return result
    except requests.exceptions.ConnectionError as exc:
        err = str(exc)
        if "getaddrinfo" in err or "Name or service" in err:
            result.update(status="OFFLINE", reason="DNS gagal / host tidak ditemukan")
        else:
            result.update(status="OFFLINE", reason=err[:80])
        return result
    except Exception as exc:
        result.update(status="ERROR", reason=str(exc)[:80])
        return result

    if resp.status_code == 401:
        result.update(status="OFFLINE", reason="401 Unauthorized")
        return result
    if resp.status_code == 403:
        result.update(status="OFFLINE", reason="403 Forbidden (DRM/geo-block)")
        return result
    if resp.status_code == 404:
        result.update(status="OFFLINE", reason="404 Not Found")
        return result
    if resp.status_code not in (200, 206):
        result.update(status="OFFLINE", reason=f"HTTP {resp.status_code}")
        return result

    # ── Tahap 2: Parse XML ──
    try:
        xml_text = content.decode("utf-8", errors="ignore")
    except Exception:
        xml_text = ""

    if not xml_text.strip().startswith("<?xml") and "<MPD" not in xml_text:
        # Bukan XML valid — anggap OFFLINE
        result.update(status="OFFLINE",
                      reason="Response bukan MPD XML yang valid")
        return result

    parsed = parse_mpd_manifest(xml_text, url)

    if parsed["error"]:
        # Manifest ada tapi tidak bisa di-parse → tetap ONLINE (manifest accessible)
        result.update(status="ONLINE",
                      reason=f"MPD manifest OK (parse warn: {parsed['error'][:40]})")
        return result

    stream_type = parsed["type"]   # LIVE / VOD
    drm_info = ", ".join(parsed["drm_systems"]) if parsed["drm_systems"] else ""

    # ── Tahap 3: DRM check ──
    if parsed["drm"]:
        # DRM terdeteksi → manifest accessible tapi stream terkunci
        result.update(
            status="OFFLINE",
            reason=f"DRM Protected ({drm_info}) — butuh license key"
        )
        return result

    # ── Tahap 4: Cek init segment (non-DRM) ──
    init_url = parsed.get("init_url", "")
    if init_url and init_url != url:
        try:
            t0 = time.monotonic()
            r2 = sess.head(init_url, headers=headers, timeout=timeout,
                           allow_redirects=True)
            lat2 = int((time.monotonic() - t0) * 1000)
            result["latency"] = lat2
            if r2.status_code in (200, 206):
                result.update(
                    status="ONLINE",
                    reason=f"MPD {stream_type} OK — init seg HTTP {r2.status_code}"
                )
            elif r2.status_code == 405:
                # HEAD tidak support, manifest sudah OK cukup
                result.update(
                    status="ONLINE",
                    reason=f"MPD {stream_type} OK — manifest accessible"
                )
            else:
                result.update(
                    status="OFFLINE",
                    reason=f"MPD manifest OK tapi init seg HTTP {r2.status_code}"
                )
        except Exception:
            # Init seg gagal dicek tapi manifest sudah OK
            result.update(
                status="ONLINE",
                reason=f"MPD {stream_type} OK — manifest accessible"
            )
    else:
        result.update(
            status="ONLINE",
            reason=f"MPD {stream_type} OK — manifest accessible"
        )

    return result


def check_url(url: str, timeout: int = 10) -> dict:
    """
    Cek satu URL stream.
    Return dict: url, status, code, latency, reason
    Possible status: ONLINE | OFFLINE | REDIRECT | TIMEOUT | ERROR
    """
    result = {"url": url, "status": "OFFLINE",
              "code": None, "latency": 0, "reason": ""}

    # ── RTMP / RTSP → TCP connect only ──
    if url.startswith(("rtmp://", "rtsp://")):
        try:
            p = urllib.parse.urlparse(url)
            host = p.hostname or ""
            port = p.port or (1935 if url.startswith("rtmp") else 554)
            t0 = time.monotonic()
            with socket.create_connection((host, port), timeout=timeout):
                pass
            result.update(status="ONLINE",
                          latency=int((time.monotonic() - t0) * 1000),
                          reason="TCP connect OK")
        except socket.timeout:
            result.update(status="TIMEOUT", reason="TCP timeout")
        except Exception as exc:
            result.update(status="OFFLINE", reason=str(exc)[:80])
        return result

    # ── MPD / MPEG-DASH → dedicated checker ──
    url_path = url.lower().split("?")[0]
    if url_path.endswith(".mpd") or "/manifest" in url_path:
        return check_mpd(url, timeout)

    # ── HTTP / HTTPS ──
    sess = _make_session()
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Connection": "close"}

    # Referer hints untuk CDN tertentu
    for pattern, ref in (
        ("jwplive",         "https://cdn.jwplayer.com/"),
        ("googlecdncloud",  "https://kilat-live.com/"),
        ("telewebion",      "https://telewebion.com/"),
        ("3bbtv",           "https://www.3bb.co.th/"),
    ):
        if pattern in url:
            headers["Referer"] = ref
            break

    def _try_head():
        t0 = time.monotonic()
        r = sess.head(url, headers=headers, timeout=timeout,
                      allow_redirects=True)
        lat = int((time.monotonic() - t0) * 1000)
        return r, lat

    def _try_get():
        t0 = time.monotonic()
        r = sess.get(url, headers={**headers, "Range": "bytes=0-511"},
                     timeout=timeout, stream=True)
        r.close()
        lat = int((time.monotonic() - t0) * 1000)
        return r, lat

    try:
        resp, lat = _try_head()
        result["latency"] = lat
        result["code"] = resp.status_code

        if resp.status_code in (200, 206):
            result.update(status="ONLINE", reason=f"HTTP {resp.status_code}")

        elif resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location", "?")[:60]
            result.update(status="REDIRECT", reason=f"→ {loc}")

        elif resp.status_code == 405:
            # Server tidak support HEAD → fallback GET
            try:
                resp2, lat2 = _try_get()
                result["latency"] = lat2
                result["code"] = resp2.status_code
                if resp2.status_code in (200, 206):
                    result.update(status="ONLINE", reason=f"GET {resp2.status_code}")
                else:
                    result.update(status="OFFLINE", reason=f"GET HTTP {resp2.status_code}")
            except Exception:
                result.update(status="OFFLINE", reason="HEAD 405, GET failed")

        elif resp.status_code == 401:
            result.update(status="OFFLINE", reason="401 Unauthorized")
        elif resp.status_code == 403:
            result.update(status="OFFLINE", reason="403 Forbidden")
        elif resp.status_code == 404:
            result.update(status="OFFLINE", reason="404 Not Found")
        else:
            result.update(status="OFFLINE", reason=f"HTTP {resp.status_code}")

    except requests.exceptions.Timeout:
        result.update(status="TIMEOUT", reason=f"Timeout >{timeout}s")
    except requests.exceptions.SSLError as exc:
        result.update(status="OFFLINE", reason=f"SSL: {str(exc)[:60]}")
    except requests.exceptions.ConnectionError as exc:
        err_str = str(exc)
        if "Name or service not known" in err_str or "getaddrinfo" in err_str:
            result.update(status="OFFLINE", reason="DNS gagal / host tidak ditemukan")
        else:
            result.update(status="OFFLINE", reason=str(exc)[:80])
    except Exception as exc:
        result.update(status="ERROR", reason=str(exc)[:80])

    return result


# ─────────────────────────────────────────────────────────
#  EXPORT FUNCTIONS
# ─────────────────────────────────────────────────────────
def export_valid_m3u(results, channels, filepath):
    online_set = {r["url"] for r in results if r["status"] == "ONLINE"}
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("#EXTM3U\n\n")
        for ch in channels:
            if ch["url"] in online_set:
                fh.write(ch.get("extinf", f'#EXTINF:-1,{ch["name"]}') + "\n")
                fh.write(ch["url"] + "\n\n")


def export_report_txt(results, filepath):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ("ONLINE", "OFFLINE", "REDIRECT", "TIMEOUT", "ERROR")}
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("=" * 70 + "\n")
        fh.write(f"  IPTV VALIDATOR REPORT — by {AUTHOR}\n")
        fh.write(f"  Tanggal  : {ts}\n")
        fh.write("=" * 70 + "\n\n")
        for st, cnt in counts.items():
            fh.write(f"  {st:<10}: {cnt}\n")
        fh.write(f"  {'TOTAL':<10}: {len(results)}\n\n")
        fh.write("=" * 70 + "\n\n")
        for st in ("ONLINE", "OFFLINE", "REDIRECT", "TIMEOUT", "ERROR"):
            grp = [r for r in results if r["status"] == st]
            if not grp:
                continue
            fh.write(f"─── {st} ({len(grp)}) ───\n")
            for r in grp:
                fh.write(
                    f"  [{r['status']:<8}] [{r['code'] or '---':>3}] "
                    f"{r['latency']:>5}ms  {r.get('name','')}\n"
                    f"  URL    : {r['url']}\n"
                    f"  GROUP  : {r.get('group','')}\n"
                )
                if r["reason"]:
                    fh.write(f"  REASON : {r['reason']}\n")
                fh.write("\n")


def export_report_csv(results, filepath):
    fields = ["name", "group", "status", "code", "latency", "reason", "url", "logo"]
    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)


# ─────────────────────────────────────────────────────────
#  GUI APPLICATION
# ─────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"IPTV Validator Checker v{VERSION}  —  by {AUTHOR}")
        self.geometry("1060x720")
        self.minsize(800, 560)
        self.configure(bg=C_BG)
        self.resizable(True, True)

        # State
        self._channels: list  = []
        self._results:  list  = []
        self._running:  bool  = False
        self._q:  queue.Queue = queue.Queue()
        self._iid_map: dict   = {}      # url → treeview iid
        self._filter_var = tk.StringVar(value="ALL")

        self._build_ui()
        self._poll_queue()

    # ──────────────────────────────────────────────
    #  UI BUILDER
    # ──────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        self._build_controls()
        self._build_stats_bar()
        self._build_table()
        self._build_log()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=C_PANEL, height=58)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="◈  IPTV VALIDATOR CHECKER",
            font=("Consolas", 15, "bold"),
            fg=C_ACCENT, bg=C_PANEL
        ).pack(side=tk.LEFT, padx=18, pady=12)

        tk.Label(
            hdr, text=f"by {AUTHOR}  •  v{VERSION}",
            font=("Consolas", 9),
            fg=C_MUTED, bg=C_PANEL
        ).pack(side=tk.LEFT, pady=12)

        tk.Frame(hdr, bg=C_BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y, pady=8, padx=14)
        self._lbl_clock = tk.Label(hdr, text="", font=("Consolas", 9),
                                   fg=C_MUTED, bg=C_PANEL)
        self._lbl_clock.pack(side=tk.RIGHT, padx=12)
        self._tick_clock()

    def _tick_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self._lbl_clock.config(text=now)
        self.after(1000, self._tick_clock)

    def _build_controls(self):
        ctrl = tk.Frame(self, bg=C_BG, pady=8)
        ctrl.pack(fill=tk.X, padx=12)

        # Row 1 — file picker
        row1 = tk.Frame(ctrl, bg=C_BG)
        row1.pack(fill=tk.X, pady=3)

        tk.Label(row1, text="File M3U:", font=("Consolas", 9),
                 fg=C_TEXT, bg=C_BG, width=9, anchor="w").pack(side=tk.LEFT)

        self._var_file = tk.StringVar()
        ent = tk.Entry(row1, textvariable=self._var_file,
                       font=("Consolas", 9), bg=C_PANEL, fg=C_TEXT,
                       insertbackground=C_ACCENT, relief=tk.FLAT,
                       highlightthickness=1, highlightcolor=C_ACCENT,
                       highlightbackground=C_BORDER)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 6))

        self._btn_browse = self._mkbtn(row1, "📂 Browse", self._browse_file,
                                       bg=C_PANEL, fg=C_ACCENT)
        self._btn_browse.pack(side=tk.LEFT, padx=(0, 4))

        self._btn_load = self._mkbtn(row1, "⬆ Load", self._load_file,
                                     bg=C_BORDER, fg=C_WHITE)
        self._btn_load.pack(side=tk.LEFT)

        # Row 2 — settings + actions
        row2 = tk.Frame(ctrl, bg=C_BG)
        row2.pack(fill=tk.X, pady=3)

        def _spin_label(parent, text):
            tk.Label(parent, text=text, font=("Consolas", 9),
                     fg=C_MUTED, bg=C_BG).pack(side=tk.LEFT, padx=(8, 2))

        _spin_label(row2, "Timeout (s):")
        self._var_timeout = tk.IntVar(value=10)
        tk.Spinbox(row2, from_=3, to=60, textvariable=self._var_timeout,
                   width=4, font=("Consolas", 9), bg=C_PANEL, fg=C_TEXT,
                   buttonbackground=C_BORDER, relief=tk.FLAT).pack(side=tk.LEFT)

        _spin_label(row2, "Threads:")
        self._var_workers = tk.IntVar(value=20)
        tk.Spinbox(row2, from_=1, to=50, textvariable=self._var_workers,
                   width=4, font=("Consolas", 9), bg=C_PANEL, fg=C_TEXT,
                   buttonbackground=C_BORDER, relief=tk.FLAT).pack(side=tk.LEFT)

        # spacer
        tk.Frame(row2, bg=C_BG).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._btn_start = self._mkbtn(row2, "▶  START CHECK",
                                      self._start_check,
                                      bg=C_ACCENT, fg=C_BG, bold=True, padx=16)
        self._btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self._btn_stop = self._mkbtn(row2, "■  STOP",
                                     self._stop_check,
                                     bg=C_RED, fg=C_WHITE, padx=10)
        self._btn_stop.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_stop.config(state=tk.DISABLED)

        self._btn_export = self._mkbtn(row2, "💾 Export",
                                       self._export_results,
                                       bg=C_PANEL, fg=C_YELLOW, padx=10)
        self._btn_export.pack(side=tk.LEFT, padx=(0, 4))
        self._btn_export.config(state=tk.DISABLED)

        self._btn_clear = self._mkbtn(row2, "🗑 Clear",
                                      self._clear_all,
                                      bg=C_PANEL, fg=C_MUTED, padx=10)
        self._btn_clear.pack(side=tk.LEFT)

    def _build_stats_bar(self):
        bar = tk.Frame(self, bg=C_PANEL, height=36)
        bar.pack(fill=tk.X, padx=12, pady=(0, 4))
        bar.pack_propagate(False)

        self._stat_labels = {}
        stats = [
            ("total",    "TOTAL",    C_TEXT),
            ("online",   "ONLINE",   C_GREEN),
            ("offline",  "OFFLINE",  C_RED),
            ("redirect", "REDIRECT", C_YELLOW),
            ("timeout",  "TIMEOUT",  C_YELLOW),
            ("error",    "ERROR",    C_PURPLE),
        ]
        for key, label, color in stats:
            frame = tk.Frame(bar, bg=C_PANEL)
            frame.pack(side=tk.LEFT, padx=14, pady=4)
            tk.Label(frame, text=label, font=("Consolas", 7, "bold"),
                     fg=C_MUTED, bg=C_PANEL).pack()
            lbl = tk.Label(frame, text="0", font=("Consolas", 11, "bold"),
                           fg=color, bg=C_PANEL)
            lbl.pack()
            self._stat_labels[key] = lbl

        # progress
        tk.Frame(bar, bg=C_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y,
                                                  pady=4, padx=6)
        prog_frame = tk.Frame(bar, bg=C_PANEL)
        prog_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=8)
        self._lbl_prog = tk.Label(prog_frame, text="Siap", font=("Consolas", 9),
                                  fg=C_MUTED, bg=C_PANEL, anchor="w")
        self._lbl_prog.pack(fill=tk.X)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("M.Horizontal.TProgressbar",
                        troughcolor=C_BORDER, background=C_ACCENT,
                        darkcolor=C_ACCENT, lightcolor=C_ACCENT,
                        bordercolor=C_BORDER)
        self._progressbar = ttk.Progressbar(prog_frame, style="M.Horizontal.TProgressbar",
                                            maximum=100, value=0)
        self._progressbar.pack(fill=tk.X, pady=(3, 0))

        # Filter
        tk.Frame(bar, bg=C_BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y,
                                                   pady=4, padx=6)
        filter_frame = tk.Frame(bar, bg=C_PANEL)
        filter_frame.pack(side=tk.RIGHT, padx=8)
        tk.Label(filter_frame, text="Filter:", font=("Consolas", 8),
                 fg=C_MUTED, bg=C_PANEL).pack(side=tk.LEFT, padx=4)
        self._filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self._filter_var,
            values=["ALL", "ONLINE", "OFFLINE", "REDIRECT", "TIMEOUT", "ERROR"],
            state="readonly", width=10, font=("Consolas", 9)
        )
        self._filter_combo.pack(side=tk.LEFT)
        self._filter_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())

    def _build_table(self):
        outer = tk.Frame(self, bg=C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        cols = ("#", "STATUS", "LATENCY", "CODE", "NAME", "GROUP", "REASON")
        widths = (38, 78, 70, 52, 220, 160, 200)

        style = ttk.Style()
        style.configure("M.Treeview",
                         background=C_PANEL, foreground=C_TEXT,
                         fieldbackground=C_PANEL, rowheight=22,
                         font=("Consolas", 9), borderwidth=0)
        style.configure("M.Treeview.Heading",
                         background=C_BORDER, foreground=C_ACCENT,
                         font=("Consolas", 9, "bold"), relief=tk.FLAT)
        style.map("M.Treeview",
                  background=[("selected", "#1f3a5f")],
                  foreground=[("selected", C_WHITE)])
        style.layout("M.Treeview", [
            ("M.Treeview.treearea", {"sticky": "nswe"})
        ])

        self._tree = ttk.Treeview(outer, columns=cols, show="headings",
                                   style="M.Treeview", selectmode="browse")
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col,
                               command=lambda c=col: self._sort_tree(c))
            self._tree.column(col, width=w, minwidth=30, stretch=(col == "NAME"))

        vsb = ttk.Scrollbar(outer, orient=tk.VERTICAL,
                            command=self._tree.yview)
        hsb = ttk.Scrollbar(outer, orient=tk.HORIZONTAL,
                            command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set,
                              xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        # Tag warna row
        for st, color in STATUS_COLOR.items():
            self._tree.tag_configure(st, foreground=color)
        self._tree.tag_configure("ODD",  background=C_ROWALT)
        self._tree.tag_configure("EVEN", background=C_PANEL)
        self._tree.bind("<Double-1>", self._on_row_dbl)

        # sort state
        self._sort_col = None
        self._sort_rev = False

    def _build_log(self):
        log_frame = tk.Frame(self, bg=C_BG)
        log_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        tk.Label(log_frame, text="▸ LOG", font=("Consolas", 8, "bold"),
                 fg=C_MUTED, bg=C_BG).pack(side=tk.LEFT, padx=(0, 6))

        self._log_text = tk.Text(
            log_frame, height=4, bg=C_PANEL, fg=C_MUTED,
            font=("Consolas", 8), relief=tk.FLAT,
            state=tk.DISABLED, wrap=tk.WORD,
            insertbackground=C_ACCENT,
            highlightthickness=1, highlightbackground=C_BORDER
        )
        self._log_text.pack(fill=tk.X, expand=True)
        sb = ttk.Scrollbar(log_frame, orient=tk.VERTICAL,
                           command=self._log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.configure(yscrollcommand=sb.set)

    def _build_footer(self):
        ftr = tk.Frame(self, bg=C_BORDER, height=1)
        ftr.pack(fill=tk.X)
        ftr2 = tk.Frame(self, bg=C_PANEL, height=24)
        ftr2.pack(fill=tk.X, side=tk.BOTTOM)
        ftr2.pack_propagate(False)
        self._lbl_status = tk.Label(
            ftr2, text=f"  IPTV Validator v{VERSION} by {AUTHOR}  |  Selamat datang!",
            font=("Consolas", 8), fg=C_MUTED, bg=C_PANEL, anchor="w"
        )
        self._lbl_status.pack(side=tk.LEFT)

    # ──────────────────────────────────────────────
    #  HELPER WIDGET FACTORY
    # ──────────────────────────────────────────────
    @staticmethod
    def _mkbtn(parent, text, cmd, bg=C_PANEL, fg=C_TEXT,
               bold=False, padx=8):
        font = ("Consolas", 9, "bold") if bold else ("Consolas", 9)
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg, fg=fg, font=font,
                        relief=tk.FLAT, cursor="hand2",
                        activebackground=C_BORDER,
                        activeforeground=C_WHITE,
                        padx=padx, pady=4, bd=0)
        return btn

    # ──────────────────────────────────────────────
    #  LOG
    # ──────────────────────────────────────────────
    def _log(self, msg: str, color: str = C_MUTED):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)
        self._lbl_status.config(text=f"  {msg}")

    # ──────────────────────────────────────────────
    #  FILE OPERATIONS
    # ──────────────────────────────────────────────
    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Pilih file M3U",
            filetypes=[("M3U files", "*.m3u *.m3u8"), ("All files", "*.*")]
        )
        if path:
            self._var_file.set(path)

    def _load_file(self):
        path = self._var_file.get().strip().strip('"').strip("'")
        if not path:
            messagebox.showwarning("Input Kosong", "Silakan pilih atau isi path file M3U.")
            return
        channels, err = parse_m3u(path)
        if err:
            messagebox.showerror("Error", err)
            return
        if not channels:
            messagebox.showwarning("Kosong", "Tidak ada channel ditemukan dalam file.")
            return
        self._channels = channels
        self._results = []
        self._iid_map = {}
        self._clear_table()
        self._populate_table_pending()
        self._update_stats()
        self._log(f"Loaded {len(channels)} channel dari: {os.path.basename(path)}", C_ACCENT)
        self._btn_export.config(state=tk.DISABLED)

    def _clear_table(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

    def _populate_table_pending(self):
        """Isi tabel dengan semua channel sebagai PENDING sebelum check dimulai."""
        self._clear_table()
        self._iid_map = {}      # url  → iid
        self._idx_map = {}      # url  → int index (0-based)
        for idx, ch in enumerate(self._channels):
            row_tag = "ODD" if idx % 2 else "EVEN"
            iid = self._tree.insert(
                "", tk.END,
                values=(idx + 1, "PENDING", "-", "-",
                        ch.get("name", "")[:60],
                        ch.get("group", "")[:40],
                        "Menunggu..."),
                tags=(row_tag,)
            )
            self._iid_map[ch["url"]] = iid
            self._idx_map[ch["url"]] = idx

    # ──────────────────────────────────────────────
    #  CHECK CONTROL
    # ──────────────────────────────────────────────
    def _start_check(self):
        if not self._channels:
            messagebox.showwarning("Belum Ada Data",
                                   "Load file M3U terlebih dahulu.")
            return
        if self._running:
            return

        timeout = self._var_timeout.get()
        workers = self._var_workers.get()

        self._running  = True
        self._results  = []
        self._q        = queue.Queue()

        self._populate_table_pending()
        self._progressbar["value"] = 0
        self._update_stats(reset=True)
        self._btn_start.config(state=tk.DISABLED)
        self._btn_stop.config(state=tk.NORMAL)
        self._btn_export.config(state=tk.DISABLED)
        self._log(f"Mulai validasi {len(self._channels)} channel "
                  f"| timeout={timeout}s | threads={workers}", C_ACCENT)

        threading.Thread(
            target=self._worker_thread,
            args=(self._channels, timeout, workers),
            daemon=True
        ).start()

    def _stop_check(self):
        self._running = False
        self._log("Check dihentikan oleh user.", C_RED)
        # Reset tombol segera — worker thread akan selesai sendiri via flag
        self._btn_start.config(state=tk.NORMAL)
        self._btn_stop.config(state=tk.DISABLED)
        self._btn_export.config(state=tk.NORMAL if self._results else tk.DISABLED)

    def _worker_thread(self, channels, timeout, workers):
        total = len(channels)
        done  = 0

        def task(ch):
            if not self._running:
                return {"url": ch["url"], "name": ch.get("name", ""),
                        "group": ch.get("group", ""), "logo": ch.get("logo", ""),
                        "status": "OFFLINE", "code": None,
                        "latency": 0, "reason": "Dihentikan"}
            res = check_url(ch["url"], timeout)
            res["name"]  = ch.get("name", "")
            res["group"] = ch.get("group", "")
            res["logo"]  = ch.get("logo", "")
            return res

        with ThreadPoolExecutor(max_workers=workers) as exe:
            # Simpan semua future agar bisa di-cancel
            futures = {exe.submit(task, ch): ch for ch in channels}
            for future in as_completed(futures):
                try:
                    res = future.result()
                except Exception as exc:
                    ch  = futures[future]
                    res = {"url": ch.get("url", ""), "name": ch.get("name", ""),
                           "group": ch.get("group", ""), "logo": ch.get("logo", ""),
                           "status": "ERROR", "code": None,
                           "latency": 0, "reason": str(exc)[:80]}
                done += 1
                self._q.put(("result", res, done, total))
                if not self._running:
                    # Cancel semua future yang belum mulai
                    for f in futures:
                        f.cancel()
                    break

        self._q.put(("done", None, done, total))

    # ──────────────────────────────────────────────
    #  QUEUE POLLING (runs in main thread via after)
    # ──────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                msg = self._q.get_nowait()
                event, payload, done, total = msg

                if event == "result":
                    self._results.append(payload)
                    self._update_row(payload, done)
                    pct = int(done / total * 100)
                    self._progressbar["value"] = pct
                    self._lbl_prog.config(
                        text=f"Checking... {done}/{total}  ({pct}%)"
                    )
                    self._update_stats()

                elif event == "done":
                    self._running = False
                    self._progressbar["value"] = 100
                    online = sum(1 for r in self._results if r["status"] == "ONLINE")
                    self._lbl_prog.config(
                        text=f"Selesai — {done}/{total} channel  |  "
                             f"{online} ONLINE"
                    )
                    self._log(
                        f"Selesai! Total={total}  ONLINE={online}  "
                        f"OFFLINE={sum(1 for r in self._results if r['status']=='OFFLINE')}  "
                        f"TIMEOUT={sum(1 for r in self._results if r['status']=='TIMEOUT')}",
                        C_GREEN
                    )
                    self._btn_start.config(state=tk.NORMAL)
                    self._btn_stop.config(state=tk.DISABLED)
                    self._btn_export.config(state=tk.NORMAL)

        except queue.Empty:
            pass
        self.after(60, self._poll_queue)

    def _update_row(self, res: dict, seq: int):
        url = res["url"]
        iid = self._iid_map.get(url)
        if not iid:
            return
        status  = res["status"]
        lat_str = f"{res['latency']} ms" if res["latency"] else "-"
        code    = str(res["code"]) if res["code"] else "-"
        idx     = self._idx_map.get(url, 0)          # O(1) lookup
        row_tag = "ODD" if idx % 2 else "EVEN"
        self._tree.item(iid, values=(
            idx + 1, status, lat_str, code,
            res.get("name", "")[:60],
            res.get("group", "")[:40],
            res.get("reason", "")[:80],
        ), tags=(status, row_tag))

    # ──────────────────────────────────────────────
    #  STATS
    # ──────────────────────────────────────────────
    def _update_stats(self, reset: bool = False):
        if reset:
            for lbl in self._stat_labels.values():
                lbl.config(text="0")
            return
        total   = len(self._channels)
        online  = sum(1 for r in self._results if r["status"] == "ONLINE")
        offline = sum(1 for r in self._results if r["status"] == "OFFLINE")
        redir   = sum(1 for r in self._results if r["status"] == "REDIRECT")
        tout    = sum(1 for r in self._results if r["status"] == "TIMEOUT")
        error   = sum(1 for r in self._results if r["status"] == "ERROR")

        self._stat_labels["total"].config(text=str(total))
        self._stat_labels["online"].config(text=str(online))
        self._stat_labels["offline"].config(text=str(offline))
        self._stat_labels["redirect"].config(text=str(redir))
        self._stat_labels["timeout"].config(text=str(tout))
        self._stat_labels["error"].config(text=str(error))

    # ──────────────────────────────────────────────
    #  FILTER
    # ──────────────────────────────────────────────
    def _apply_filter(self):
        if self._running:
            return   # jangan filter saat check berjalan, hindari konflik detach/reattach
        flt = self._filter_var.get()
        for iid in self._tree.get_children():
            vals = self._tree.item(iid, "values")
            status = vals[1] if vals else ""
            if flt == "ALL" or status == flt:
                self._tree.reattach(iid, "", tk.END)
            else:
                self._tree.detach(iid)

    # ──────────────────────────────────────────────
    #  SORT
    # ──────────────────────────────────────────────
    def _sort_tree(self, col: str):
        items = [(self._tree.set(iid, col), iid)
                 for iid in self._tree.get_children("")]

        def key_fn(x):
            v = x[0]
            if col == "LATENCY":
                try:
                    return int(v.replace(" ms", "").strip())
                except Exception:
                    return -1
            if col in ("#", "CODE"):
                try:
                    return int(v)
                except Exception:
                    return -1
            return v.lower()

        rev = (self._sort_col == col and not self._sort_rev)
        items.sort(key=key_fn, reverse=rev)
        for i, (_, iid) in enumerate(items):
            self._tree.move(iid, "", i)
        self._sort_col = col
        self._sort_rev = rev

    # ──────────────────────────────────────────────
    #  DOUBLE CLICK — copy URL
    # ──────────────────────────────────────────────
    def _on_row_dbl(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        # Cari URL dengan reverse lookup dari _iid_map (akurat, tidak bergantung nama)
        url = next((u for u, i in self._iid_map.items() if i == iid), None)
        if not url:
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self._log(f"URL disalin: {url[:80]}", C_YELLOW)

    # ──────────────────────────────────────────────
    #  CLEAR ALL
    # ──────────────────────────────────────────────
    def _clear_all(self):
        if self._running:
            messagebox.showwarning("Running",
                                   "Stop check terlebih dahulu.")
            return
        self._channels = []
        self._results  = []
        self._iid_map  = {}
        self._clear_table()
        self._update_stats(reset=True)
        self._progressbar["value"] = 0
        self._lbl_prog.config(text="Siap")
        self._var_file.set("")
        self._btn_export.config(state=tk.DISABLED)
        self._log("Data dibersihkan.", C_MUTED)

    # ──────────────────────────────────────────────
    #  EXPORT
    # ──────────────────────────────────────────────
    def _export_results(self):
        if self._running:
            messagebox.showwarning("Masih Berjalan",
                                   "Tunggu proses selesai atau klik STOP sebelum export.")
            return
        if not self._results:
            messagebox.showwarning("Tidak Ada Data", "Belum ada hasil untuk di-export.")
            return

        out_dir = filedialog.askdirectory(title="Pilih folder simpan output")
        if not out_dir:
            return

        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(out_dir, f"iptv_valid_{ts}")

        saved = []

        # M3U valid
        m3u_path = base + ".m3u"
        export_valid_m3u(self._results, self._channels, m3u_path)
        saved.append(f"M3U VALID → {os.path.basename(m3u_path)}")

        # TXT report
        txt_path = base + "_report.txt"
        export_report_txt(self._results, txt_path)
        saved.append(f"REPORT TXT → {os.path.basename(txt_path)}")

        # CSV
        csv_path = base + "_report.csv"
        export_report_csv(self._results, csv_path)
        saved.append(f"REPORT CSV → {os.path.basename(csv_path)}")

        self._log(f"Export selesai ke: {out_dir}", C_GREEN)
        messagebox.showinfo(
            "Export Berhasil",
            "File tersimpan di:\n" + out_dir + "\n\n" + "\n".join(saved)
        )


# ─────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
