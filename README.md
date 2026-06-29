# 📺 IPTV Validator Checker — GUI Edition

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/GUI-Tkinter-cyan?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Version-3.0-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/by-M4DI~UciH4-purple?style=for-the-badge"/>
</p>

<p align="center">
  <b>Tool validasi playlist IPTV (M3U/M3U8) berbasis GUI ringan.</b><br/>
  Cek status channel secara paralel — ONLINE, OFFLINE, REDIRECT, TIMEOUT, ERROR.<br/>
  Export otomatis M3U bersih + laporan TXT & CSV.
</p>

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 🖥️ GUI Dark Theme | Tampilan modern, ringan, berbasis `tkinter` bawaan Python |
| ⚡ Multi-Thread | Validasi paralel hingga 50 thread sekaligus |
| 🎯 Deteksi Akurat | ONLINE / OFFLINE / REDIRECT / TIMEOUT / ERROR |
| 📡 Multi-Protocol | HTTP, HTTPS, RTMP, RTSP, M3U8, TS, MPD, MP4 |
| 🔁 Fallback HEAD→GET | Otomatis fallback ke GET jika server tidak support HEAD (405) |
| 📊 Stats Live | Counter status update real-time selama proses berlangsung |
| 🔍 Filter & Sort | Filter tabel per status, sort per kolom |
| 📋 Copy URL | Double-click baris → URL langsung tersalin ke clipboard |
| 💾 Export 3 Format | M3U valid + Laporan TXT + Laporan CSV |
| 🛑 Stop Kapan Saja | Tombol STOP untuk menghentikan proses di tengah jalan |

---

## 🖼️ Tampilan

```
╔══════════════════════════════════════════════════════════╗
║   ◈  IPTV VALIDATOR CHECKER          by M4DI~UciH4  v3.0 ║
╠══════════════════════════════════════════════════════════╣
║  File M3U: [__________________________] [Browse] [Load]  ║
║  Timeout: [10]  Threads: [20]   [▶ START] [■ STOP] [💾]  ║
╠══════════════════════════════════════════════════════════╣
║  TOTAL  ONLINE  OFFLINE  REDIRECT  TIMEOUT  ERROR        ║
║  [===========================] 78% (76/97)               ║
╠══════════════════════════════════════════════════════════╣
║  #  STATUS   LATENCY  CODE  NAME          GROUP  REASON  ║
║  1  ONLINE   142 ms   200   Argentina vs  LIVE   HTTP 200║
║  2  OFFLINE  -        404   Ukraine vs    LIVE   404     ║
║  ...                                                     ║
╠══════════════════════════════════════════════════════════╣
║  LOG: [14:22:01] Loaded 97 channels...                   ║
╚══════════════════════════════════════════════════════════╝
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

> `tkinter` sudah **built-in** di Python — tidak perlu install tambahan.

### 3. Jalankan

```bash
python iptv_validator.py
```

---

## 📋 Cara Pakai

1. **Browse / isi path** file M3U kamu
2. Klik **Load** → channel akan tampil di tabel
3. Atur **Timeout** (detik) dan jumlah **Threads** sesuai kebutuhan
4. Klik **▶ START CHECK**
5. Tunggu proses selesai — stats update real-time
6. Klik **💾 Export** → pilih folder → 3 file otomatis tersimpan:
   - `iptv_valid_YYYYMMDD_HHMMSS.m3u` — playlist bersih (ONLINE saja)
   - `iptv_valid_YYYYMMDD_HHMMSS_report.txt` — laporan lengkap
   - `iptv_valid_YYYYMMDD_HHMMSS_report.csv` — data tabel (bisa dibuka Excel)

### Tips
- **Double-click** baris di tabel → URL tersalin ke clipboard
- Klik **header kolom** untuk sort (Status, Latency, Name, dll)
- Gunakan **Filter** dropdown untuk tampilkan status tertentu saja
- Naikkan **Threads** ke 30–50 untuk playlist besar agar lebih cepat

---

## 📁 Struktur Output

```
folder-pilihan/
├── iptv_valid_20260629_142201.m3u          ← Playlist ONLINE saja
├── iptv_valid_20260629_142201_report.txt   ← Laporan detail per channel
└── iptv_valid_20260629_142201_report.csv   ← Data lengkap (Excel-friendly)
```

---

## ⚙️ Status Penjelasan

| Status | Keterangan |
|---|---|
| ✅ `ONLINE` | Stream aktif & dapat diakses (HTTP 200/206) |
| ❌ `OFFLINE` | Stream tidak aktif (404, 403, 401, connection error) |
| 🔀 `REDIRECT` | URL diarahkan ke alamat lain (301/302/307/308) |
| ⏱️ `TIMEOUT` | Tidak ada response dalam batas waktu |
| ⚠️ `ERROR` | Error tidak terduga (SSL, DNS, dsb) |

---

## 🔧 Persyaratan Sistem

| | Minimum |
|---|---|
| Python | 3.8 atau lebih baru |
| OS | Windows / Linux / macOS |
| Library | `requests` (`pip install requests`) |
| tkinter | Sudah built-in (tidak perlu install) |

---

## 📦 Format M3U yang Didukung

```
#EXTM3U
#EXTINF:-1 tvg-logo="..." group-title="...",Nama Channel
https://contoh.com/stream.m3u8

#EXTINF:-1 group-title="...",Channel 2
http://contoh.com/live/channel.ts

#EXTINF:-1,Channel RTMP
rtmp://streaming.contoh.com/live/stream
```

---

## 🐛 Known Limitations

- Stream yang butuh **DRM / Widevine / ClearKey** akan terdeteksi OFFLINE (akses tidak diizinkan tanpa license key aktif)
- Beberapa CDN memblokir request tanpa **Referer** spesifik — hasil bisa tidak akurat untuk channel jenis ini
- RTMP/RTSP hanya dicek koneksi TCP-nya, bukan isi stream

---

## 📜 License

```
MIT License — bebas digunakan, dimodifikasi, dan didistribusikan.
Harap tetap cantumkan credit: M4DI~UciH4
```

---

## 👤 Author

**M4DI~UciH4**  
GitHub: [@RizkyEvory](https://github.com/RizkyEvory)

---

<p align="center">
  Made with ❤️ for the IPTV community<br/>
  <i>If this tool helps you, consider giving it a ⭐</i>
</p>
