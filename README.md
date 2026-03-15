# InvenTrack — Sistem Informasi Inventaris

Aplikasi manajemen inventaris berbasis Flask dengan antarmuka modern.

## Fitur
- **Dashboard** — Statistik real-time, grafik distribusi stok, peringatan stok rendah
- **Data Barang** — CRUD lengkap, filter/pencarian, indikator stok visual
- **Peminjaman** — Catat & kembalikan barang, riwayat lengkap, filter status
- **Export** — Laporan CSV untuk barang dan peminjaman

## Cara Menjalankan

```bash
# 1. Install dependensi
pip install -r requirements.txt

# 2. Jalankan aplikasi
python app.py

# 3. Buka browser
# http://localhost:5000
```

Database SQLite (`inventaris.db`) dibuat otomatis dengan data contoh saat pertama kali dijalankan.
