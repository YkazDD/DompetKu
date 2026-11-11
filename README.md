# 💰 DompetKu - Aplikasi Pencatat Keuangan Pribadi

**DompetKu** adalah aplikasi konsol berbasis Python untuk mengelola pencatatan keuangan pribadi secara aman, terstruktur, dan efisien tanpa memerlukan instalasi library eksternal pihak ketiga. Proyek ini dikembangkan sebagai bagian dari Ujian Tengah Semester (UTS) mata kuliah Pemrograman Dasar.

---

## ✨ Fitur Utama

- 🔐 **Keamanan PIN Terenkripsi**: Akses aplikasi dilindungi dengan PIN (4-6 digit) yang di-*hash* menggunakan algoritma **SHA-256 dan Salt** (tidak menyimpan PIN mentah demi keamanan).
- 📝 **Manajemen Transaksi Lengkap**: Mendukung pencatatan pemasukan dan pengeluaran dengan validasi input yang ketat.
- 🎯 **Pengaturan Anggaran (Budgeting) Bulanan**: Menetapkan batas anggaran per kategori dan mendeteksi secara otomatis jika pengeluaran hampir habis atau melebihi batas.
- 📊 **Rekapitulasi & Filter Otomatis**: Menampilkan ringkasan saldo, rekap per kategori, persentase pengeluaran, serta filter transaksi berdasarkan bulan, kategori, atau rentang tanggal.
- 📄 **Ekspor Laporan Bulanan**: Mengekspor ringkasan keuangan, rata-rata harian, hingga daftar pengeluaran terbesar ke dalam file teks (`.txt`) secara otomatis.
- 🛡️ **Pencegahan Data Rusak (*Corrupt File Protection*)**: Sistem pembacaan file menggunakan format JSON Lines (`.jsonl`) dengan mekanisme validasi baris untuk mengabaikan data yang rusak tanpa merusak keseluruhan aplikasi.

---

## 🛠️ Teknologi yang Digunakan
- **Bahasa Pemrograman:** Python 3 (Pure Python standard library: `json`, `hashlib`, `hmac`, `datetime`, `pathlib`, dll.)
- **Penyimpanan Data:** JSON Lines (`.jsonl`) dan JSON

---

## 🚀 Cara Menjalankan Program

1. Pastikan komputer Anda sudah terinstal **Python 3**.
2. Unduh atau *clone* repository ini:
   ```bash
   git clone [https://github.com/YkazDD/DompetKu.git](https://github.com/YkazDD/DompetKu.git)
