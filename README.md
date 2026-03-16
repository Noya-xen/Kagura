# Kagura (AirdropsQuest) Auto Mission & Daily Claim — Multi-Account

Script Python untuk **auto claim daily login** dan **auto complete task/mission** di `airdropsquest.com`, dengan dukungan **multi-account** via `cookies.txt`.

## Fitur

- Multi-account (1 cookie/JWT per baris)
- Auto **Daily Login Claim**
- Auto **Complete semua task** yang tersedia
- Tidak menampilkan task yang sudah selesai (skip “already completed”)
- **Loop mode**: jalan terus dan repeat setiap **24 jam**

## Requirements

- Python 3.9+ (disarankan)
- Package: `requests`

Install dependency:

```bash
pip install requests
```

## Setup

1. Siapkan file `cookies.txt` di folder yang sama (repo ini sudah ada contohnya).
2. Isi **1 token per baris**.

Format token yang benar:

- **Hanya JWT string** (contoh: `eyJhbGciOi...`)
- **Jangan** pakai prefix `__Host-app_session_id=`
- Baris yang diawali `#` dianggap komentar dan akan di-skip

Contoh:

```text
# one cookie per line
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Cara Menjalankan

Jalankan script:

```bash
python kagura_multi.py
```

Default behavior:

- Script akan menjalankan semua akun
- Menunggu 5 detik antar akun
- Setelah selesai, **sleep 24 jam** lalu jalan lagi (loop). Stop dengan `Ctrl + C`.

## Keamanan

- `cookies.txt` berisi credential/token. **Jangan upload ke GitHub.**
- Repo ini sudah menyertakan `.gitignore` untuk mengabaikan `cookies.txt`.

## Troubleshooting singkat

- **Auth failed / cookie expired**: token/JWT sudah tidak valid → ambil cookie baru.
- **Daily already claimed**: normal, berarti sudah claim hari ini.
- **API berubah**: kalau ada pesan seperti endpoint “no longer exists”, berarti API AirdropsQuest berubah dan script perlu update.

## Disclaimer

Gunakan dengan risiko sendiri. Otomasi bisa melanggar ToS platform tertentu, dan akun bisa terkena limit/rate-limit/ban.

