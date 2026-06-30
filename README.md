# 📺 IPTV Validator Checker — GUI Edition

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/GUI-Tkinter-cyan?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Version-3.1-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/by-M4DI~UciH4-purple?style=for-the-badge"/>
</p>

<p align="center">
  <b>Tool validasi playlist IPTV (M3U/M3U8/MPD) berbasis GUI ringan.</b><br/>
  Cek status channel secara paralel — ONLINE, OFFLINE, REDIRECT, TIMEOUT, ERROR.<br/>
  Deteksi DRM otomatis untuk stream MPEG-DASH. Export M3U bersih + laporan TXT & CSV.
</p>

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 🖥️ GUI Dark Theme | Tampilan modern, ringan, berbasis `tkinter` bawaan Python |
| ⚡ Multi-Thread | Validasi paralel hingga 50 thread sekaligus |
| 🎯 Deteksi Akurat | ONLINE / OFFLINE / REDIRECT / TIMEOUT / ERROR |
| 📡 Multi-Protocol | HTTP, HTTPS, RTMP, RTSP, M3U8, TS, **MPD/DASH** |
| 🔐 DRM Detection | Deteksi otomatis **Widevine**, **PlayReady**, **ClearKey** pada MPD |
| 📊 MPD 3-Stage Check | Download manifest → Parse XML → Cek init segment |
| 🔁 Fallback HEAD→GET | Otomatis fallback ke GET jika server tidak support HEAD (405) |
| 📈 Stats Live | Counter status update real-time selama proses berlangsung |
| 🔍 Filter & Sort | Filter tabel per status, sort per kolom |
| 📋 Copy URL | Double-click baris → URL langsung tersalin ke clipboard |
| 💾 Export 3 Format | M3U valid + Laporan TXT + Laporan CSV |
| 🛑 Stop Kapan Saja | Tombol STOP untuk menghentikan proses di tengah jalan |

---

## 🖼️ Tampilan

```
╔══════════════════════════════════════════════════════════════╗
║   ◈  IPTV VALIDATOR CHECKER                by M4DI~UciH4 v3.1║
╠══════════════════════════════════════════════════════════════╣
║  File M3U: [______________________________] [Browse] [Load]  ║
║  Timeout: [10]  Threads: [20]   [▶ START] [■ STOP] [💾] [🗑] ║
╠══════════════════════════════════════════════════════════════╣
║  TOTAL  ONLINE  OFFLINE  REDIRECT  TIMEOUT  ERROR            ║
║   97     61      28        3         4        1               ║
║  [████████████████████░░░░] 82%  (80/97)        Filter:[ALL] ║
╠══════════════════════════════════════════════════════════════╣
║  #   STATUS    LATENCY  CODE  NAME               GROUP       ║
║  1   ONLINE    142 ms   200   Argentina vs Ger   LIVE EVENT  ║
║  2   OFFLINE   -        404   Ukraine vs Fra     LIVE EVENT  ║
║  3   OFFLINE   80 ms    -     SCTV HD            DRM         ║
║  4   TIMEOUT   -        -     BeIN Sports        Sports      ║
╠══════════════════════════════════════════════════════════════╣
║  ▸ LOG                                                       ║
║  [14:22:01] Loaded 97 channels dari: ux_fixed.m3u            ║
║  [14:22:02] Mulai validasi | timeout=10s | threads=20        ║
║  [14:22:18] Selesai! ONLINE=61 OFFLINE=28 TIMEOUT=4         ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 🚀 Cara Install & Jalankan

### 1. Clone repo

```bash
git clone https://github.com/RizkyEvory/iptv-validator.git
cd iptv-validator
```

### 2. Install dependency

Hanya butuh satu library eksternal:

```bash
pip install requests
```

> `tkinter` dan `xml.etree.ElementTree` sudah **built-in** di Python — tidak perlu install tambahan.

### 3. Jalankan

```bash
python iptv_validator.py
```

---

## 📋 Cara Pakai

1. Klik **Browse** atau ketik langsung path file M3U kamu
2. Klik **Load** → semua channel tampil di tabel dengan status `PENDING`
3. Atur **Timeout** (detik) dan jumlah **Threads** sesuai kebutuhan
4. Klik **▶ START CHECK** → proses berjalan real-time
5. Gunakan **Filter** dropdown untuk fokus ke status tertentu
6. Klik **💾 Export** → pilih folder → 3 file tersimpan otomatis

### Tips
- **Double-click** baris di tabel → URL tersalin ke clipboard
- Klik **header kolom** untuk sort ascending/descending
- Naikkan **Threads** ke 30–50 untuk playlist besar agar lebih cepat
- Gunakan **Timeout 6–8s** untuk hasil lebih cepat tanpa banyak false timeout

---

## 📁 Struktur Output

```
folder-pilihan/
├── iptv_valid_20260629_142201.m3u          ← Playlist ONLINE saja (siap pakai)
├── iptv_valid_20260629_142201_report.txt   ← Laporan detail per channel
└── iptv_valid_20260629_142201_report.csv   ← Data lengkap (Excel-friendly)
```

---

## ⚙️ Status Penjelasan

| Status | Kode | Keterangan |
|---|---|---|
| ✅ `ONLINE` | 200 / 206 | Stream aktif & dapat diakses |
| ❌ `OFFLINE` | 4xx | Stream tidak aktif, forbidden, atau DRM protected |
| 🔀 `REDIRECT` | 3xx | URL diarahkan ke alamat lain |
| ⏱️ `TIMEOUT` | - | Tidak ada response dalam batas waktu |
| ⚠️ `ERROR` | - | Error tidak terduga (SSL, parsing, dsb) |

---

## 🔐 MPD / MPEG-DASH Support

Script melakukan validasi **3 tahap** untuk stream `.mpd`:

```
1. Download manifest XML
        ↓
2. Parse XML → deteksi DRM, tipe stream (LIVE/VOD), BaseURL
        ↓
3a. DRM terdeteksi?  → OFFLINE "DRM Protected (ClearKey/Widevine/PlayReady)"
3b. Non-DRM?         → Cek init segment → ONLINE jika accessible
```

### DRM yang dideteksi otomatis:

| DRM System | UUID |
|---|---|
| **Widevine** (Google) | `edef8ba9-79d6-4ace-a3c8-27dcd51d21ed` |
| **PlayReady** (Microsoft) | `9a04f079-9840-4286-ab92-e65be0885f95` |
| **ClearKey** | `e2719d58-a985-b3c9-781a-b030af78d30e` |

> Stream dengan DRM akan selalu `OFFLINE` karena membutuhkan license key aktif dari server lisensi — ini **bukan bug**, melainkan proteksi konten dari broadcaster.

---

## 📦 Format yang Didukung

| Format | Protokol | Metode Cek |
|---|---|---|
| `.m3u8` / `.ts` | HTTP/HTTPS | HEAD → GET fallback |
| `.mpd` (MPEG-DASH) | HTTP/HTTPS | Download + XML parse + init segment |
| `.mp4` / `.flv` | HTTP/HTTPS | HEAD → GET fallback |
| `rtmp://` | RTMP | TCP socket connect |
| `rtsp://` | RTSP | TCP socket connect |

---

## 🔧 Persyaratan Sistem

| | Minimum |
|---|---|
| Python | 3.8 atau lebih baru |
| OS | Windows / Linux / macOS |
| Library eksternal | `requests` saja (`pip install requests`) |
| Library built-in | `tkinter`, `xml.etree`, `threading`, `socket` |

---

## 🐛 Known Limitations

- Stream yang butuh **DRM aktif** (Widevine/PlayReady/ClearKey) akan `OFFLINE` — ini behavior yang benar
- Beberapa CDN memblokir request tanpa **Referer** spesifik (sudah ada hint untuk cloudfront, jwplive, telewebion, 3bbtv)
- **RTMP/RTSP** hanya dicek koneksi TCP-nya, bukan isi stream
- MPD dengan `SegmentList` yang sangat panjang hanya dibaca 512 KB pertama

---

## 📜 License

```
MIT License — bebas digunakan, dimodifikasi, dan didistribusikan.
Harap tetap cantumkan credit: M4DI~UciH4
```

---

## 📝 Changelog

### v3.1
- ✅ Tambah **MPD/MPEG-DASH** parser (3-stage validation)
- ✅ Deteksi otomatis **Widevine**, **PlayReady**, **ClearKey**
- ✅ Parse `BaseURL`, `SegmentTemplate`, `SegmentURL` dari manifest XML
- ✅ Routing otomatis URL `.mpd` dan `/manifest` ke checker khusus

### v3.0
- ✅ GUI dark theme dengan tkinter (zero extra dependency)
- ✅ Multi-thread real-time validation
- ✅ Filter, sort, export 3 format
- ✅ HEAD→GET fallback, RTMP/RTSP TCP check

---

## 👤 Author

**M4DI~UciH4**  
GitHub: [@RizkyEvory](https://github.com/RizkyEvory)

---

<p align="center">
  Made with ❤️ for the IPTV community<br/>
  <i>If this tool helps you, consider giving it a ⭐</i>
</p>
