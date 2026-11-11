"""
DompetKu - Aplikasi Pencatat Keuangan Pribadi
Python 3, tanpa library eksternal.

File data:
- transaksi.jsonl : satu transaksi JSON per baris
- anggaran.json   : batas anggaran bulanan per kategori
- pin.json        : salt dan hash PIN (bukan PIN mentah)
- laporan_YYYY-MM.txt : laporan bulanan hasil ekspor
"""

import json
import calendar
import hashlib
import hmac
import getpass
from datetime import datetime
from pathlib import Path

DATA_FILE = Path("transaksi.jsonl")
BUDGET_FILE = Path("anggaran.json")
PIN_FILE = Path("pin.json")
MAX_PIN_ATTEMPTS = 3

JENIS_VALID = {"pemasukan", "pengeluaran"}


def rupiah(nominal):
    """Mengubah angka menjadi format rupiah, misalnya Rp1.500.000."""
    return "Rp" + f"{nominal:,.0f}".replace(",", ".")


def baca_tanggal(teks):
    """Validasi tanggal dengan format YYYY-MM-DD."""
    try:
        return datetime.strptime(teks, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Tanggal harus valid dan berformat YYYY-MM-DD.")


def baca_bulan(teks):
    """Validasi bulan dengan format YYYY-MM."""
    try:
        datetime.strptime(teks, "%Y-%m")
        return teks
    except ValueError:
        raise ValueError("Bulan harus berformat YYYY-MM, contoh 2026-10.")


def input_nominal(prompt="Nominal (angka positif): "):
    while True:
        teks = input(prompt).strip().replace(".", "").replace(",", "")
        try:
            nilai = int(teks)
            if nilai <= 0:
                print("Nominal harus lebih besar dari 0.")
                continue
            return nilai
        except ValueError:
            print("Nominal tidak valid. Masukkan angka bulat, misalnya 1500000.")


def input_tanggal(prompt="Tanggal (YYYY-MM-DD): "):
    while True:
        teks = input(prompt).strip()
        try:
            return baca_tanggal(teks).isoformat()
        except ValueError as error:
            print(error)


def muat_transaksi():
    """Muat data; baris JSON yang rusak dilewati dan jumlahnya dilaporkan."""
    if not DATA_FILE.exists():
        DATA_FILE.touch()
        return []

    transaksi = []
    gagal = 0

    with DATA_FILE.open("r", encoding="utf-8") as file:
        for nomor_baris, baris in enumerate(file, start=1):
            if not baris.strip():
                continue
            try:
                data = json.loads(baris)
                # Validasi struktur minimum agar data rusak tidak masuk program.
                if not isinstance(data, dict):
                    raise ValueError("Data bukan objek")
                if not all(k in data for k in
                           ("id", "tanggal", "jenis", "kategori", "deskripsi", "nominal")):
                    raise ValueError("Kolom wajib tidak lengkap")
                if data["jenis"] not in JENIS_VALID:
                    raise ValueError("Jenis transaksi tidak valid")
                baca_tanggal(data["tanggal"])
                if int(data["nominal"]) <= 0:
                    raise ValueError("Nominal tidak valid")
                data["id"] = int(data["id"])
                data["nominal"] = int(data["nominal"])
                transaksi.append(data)
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                gagal += 1

    if gagal:
        print(f"Peringatan: {gagal} baris data gagal dimuat dan dilewati.")
    return transaksi


def simpan_transaksi(transaksi):
    """Tulis ulang seluruh transaksi ke file JSONL."""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        for item in transaksi:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def muat_anggaran():
    if not BUDGET_FILE.exists():
        BUDGET_FILE.write_text("{}", encoding="utf-8")
        return {}
    try:
        data = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k).casefold(): int(v) for k, v in data.items()
                    if int(v) > 0}
    except (json.JSONDecodeError, ValueError, TypeError):
        print("Peringatan: file anggaran rusak. Anggaran dimulai dari data kosong.")
    return {}


def simpan_anggaran(anggaran):
    BUDGET_FILE.write_text(
        json.dumps(anggaran, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def hash_pin(pin, salt):
    """Hash PIN dengan SHA-256 dan salt; jangan menyimpan PIN mentah."""
    return hashlib.sha256((salt + pin).encode("utf-8")).hexdigest()


def atur_pin_awal():
    """Saat pertama dijalankan, minta pengguna membuat PIN 4-6 digit."""
    while True:
        pin = getpass.getpass("Buat PIN baru (4-6 digit): ").strip()
        if not (pin.isdigit() and 4 <= len(pin) <= 6):
            print("PIN harus terdiri dari 4 sampai 6 angka.")
            continue

        konfirmasi = getpass.getpass("Ulangi PIN: ").strip()
        if pin != konfirmasi:
            print("PIN tidak cocok. Coba lagi.")
            continue

        import secrets
        salt = secrets.token_hex(16)
        data = {"salt": salt, "pin_hash": hash_pin(pin, salt)}
        PIN_FILE.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        print("PIN berhasil dibuat.")
        return True


def autentikasi_pin():
    """Minta PIN sebelum menu utama dibuka; batasi percobaan."""
    if not PIN_FILE.exists():
        print("=" * 48)
        print("PENGATURAN KEAMANAN DOMPETKU")
        print("Buat PIN untuk mengunci akses ke aplikasi.")
        print("=" * 48)
        if not atur_pin_awal():
            return False

    try:
        data = json.loads(PIN_FILE.read_text(encoding="utf-8"))
        salt = data["salt"]
        pin_hash = data["pin_hash"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        print("File PIN bermasalah. Akses dihentikan demi keamanan.")
        return False

    for percobaan in range(1, MAX_PIN_ATTEMPTS + 1):
        pin = getpass.getpass("Masukkan PIN DompetKu: ").strip()
        if hmac.compare_digest(hash_pin(pin, salt), pin_hash):
            print("PIN benar. Selamat datang!")
            return True

        sisa = MAX_PIN_ATTEMPTS - percobaan
        if sisa:
            print(f"PIN salah. Sisa percobaan: {sisa}.")
        else:
            print("Terlalu banyak percobaan. Program ditutup.")

    return False


def buat_id(transaksi):
    return max((item["id"] for item in transaksi), default=0) + 1


def cari_id(transaksi, id_transaksi):
    for item in transaksi:
        if item["id"] == id_transaksi:
            return item
    return None


def filter_transaksi(transaksi, bulan=None, kategori=None,
                     tanggal_awal=None, tanggal_akhir=None):
    hasil = transaksi[:]
    if bulan:
        hasil = [t for t in hasil if t["tanggal"][:7] == bulan]
    if kategori:
        hasil = [t for t in hasil
                 if t["kategori"].casefold() == kategori.casefold()]
    if tanggal_awal:
        hasil = [t for t in hasil if t["tanggal"] >= tanggal_awal]
    if tanggal_akhir:
        hasil = [t for t in hasil if t["tanggal"] <= tanggal_akhir]
    return sorted(hasil, key=lambda t: (t["tanggal"], t["id"]))


def tampilkan_transaksi(transaksi):
    if not transaksi:
        print("Belum ada transaksi.")
        return

    header = (
        f"{'ID':<5} {'Tanggal':<12} {'Jenis':<13} "
        f"{'Kategori':<18} {'Deskripsi':<28} {'Nominal':>18}"
    )
    print(header)
    print("-" * len(header))
    for t in sorted(transaksi, key=lambda x: (x["tanggal"], x["id"])):
        kategori = t["kategori"][:17]
        deskripsi = t["deskripsi"][:27]
        print(
            f"{t['id']:<5} {t['tanggal']:<12} {t['jenis']:<13} "
            f"{kategori:<18} {deskripsi:<28} {rupiah(t['nominal']):>18}"
        )


def hitung_ringkasan(transaksi):
    pemasukan = sum(t["nominal"] for t in transaksi
                    if t["jenis"] == "pemasukan")
    pengeluaran = sum(t["nominal"] for t in transaksi
                      if t["jenis"] == "pengeluaran")
    return pemasukan, pengeluaran, pemasukan - pengeluaran


def tampilkan_saldo(transaksi):
    pemasukan, pengeluaran, saldo = hitung_ringkasan(transaksi)
    print(f"Total pemasukan  : {rupiah(pemasukan)}")
    print(f"Total pengeluaran: {rupiah(pengeluaran)}")
    print(f"Saldo            : {rupiah(saldo)}")


def buat_rekap(transaksi):
    rekap = {}
    total_pengeluaran = sum(
        t["nominal"] for t in transaksi if t["jenis"] == "pengeluaran"
    )
    for t in transaksi:
        kategori = t["kategori"]
        if kategori not in rekap:
            rekap[kategori] = {"pemasukan": 0, "pengeluaran": 0}
        rekap[kategori][t["jenis"]] += t["nominal"]

    return rekap, total_pengeluaran


def tampilkan_rekap(transaksi, anggaran, bulan_anggaran=None, transaksi_semua=None):
    rekap, total_pengeluaran = buat_rekap(transaksi)
    if bulan_anggaran is None:
        bulan_anggaran = datetime.now().strftime("%Y-%m")
    sumber_anggaran = transaksi_semua if transaksi_semua is not None else transaksi
    pengeluaran_bulanan = {}
    for item in sumber_anggaran:
        if item["jenis"] == "pengeluaran" and item["tanggal"][:7] == bulan_anggaran:
            kunci = item["kategori"].casefold()
            pengeluaran_bulanan[kunci] = pengeluaran_bulanan.get(kunci, 0) + item["nominal"]
    if not rekap:
        print("Belum ada data untuk direkap.")
        return

    print("\nREKAP PER KATEGORI")
    print("-" * 105)
    print(f"{'Kategori':<20} {'Pemasukan':>17} {'Pengeluaran':>17} "
          f"{'% dari pengeluaran':>20} {'Sisa anggaran':>17}  Status")
    print("-" * 105)

    for kategori, nilai in sorted(rekap.items()):
        keluar = nilai["pengeluaran"]
        persen = (keluar / total_pengeluaran * 100) if total_pengeluaran else 0

        batas = anggaran.get(kategori.casefold())
        keluar_bulanan = pengeluaran_bulanan.get(kategori.casefold(), 0)
        if batas is None:
            sisa = "-"
            status = "BELUM DIATUR"
        else:
            sisa_nominal = batas - keluar_bulanan
            sisa = rupiah(sisa_nominal)
            pemakaian = (keluar_bulanan / batas * 100) if batas else 0
            if pemakaian < 80:
                status = "AMAN"
            elif pemakaian <= 100:
                status = "HAMPIR HABIS"
            else:
                status = "MELEBIHI"

        print(f"{kategori[:19]:<20} {rupiah(nilai['pemasukan']):>17} "
              f"{rupiah(keluar):>17} {persen:>19.2f}% {sisa:>17}  {status}")

    print(f"\nStatus anggaran dihitung untuk bulan {bulan_anggaran}; "
          f"angka rekap mengikuti transaksi yang sedang ditampilkan.")


def tambah_transaksi(transaksi, anggaran):
    print("\nTAMBAH TRANSAKSI")
    tanggal = input_tanggal()
    while True:
        jenis = input("Jenis (pemasukan/pengeluaran): ").strip().casefold()
        if jenis in JENIS_VALID:
            break
        print("Jenis harus 'pemasukan' atau 'pengeluaran'.")

    while True:
        kategori = input("Kategori: ").strip()
        if kategori:
            break
        print("Kategori tidak boleh kosong.")

    while True:
        deskripsi = input("Deskripsi: ").strip()
        if deskripsi:
            break
        print("Deskripsi tidak boleh kosong.")

    nominal = input_nominal()
    item = {
        "id": buat_id(transaksi),
        "tanggal": tanggal,
        "jenis": jenis,
        "kategori": kategori,
        "deskripsi": deskripsi,
        "nominal": nominal,
    }

    if jenis == "pengeluaran":
        bulan = tanggal[:7]
        batas = anggaran.get(kategori.casefold())
        if batas is not None:
            sudah = sum(
                t["nominal"] for t in transaksi
                if t["jenis"] == "pengeluaran"
                and t["kategori"].casefold() == kategori.casefold()
                and t["tanggal"][:7] == bulan
            )
            if sudah + nominal > batas:
                print("\nPERINGATAN: transaksi ini membuat anggaran terlampaui.")
                print(f"Anggaran kategori : {rupiah(batas)}")
                print(f"Pengeluaran lama  : {rupiah(sudah)}")
                print(f"Pengeluaran baru  : {rupiah(sudah + nominal)}")
                konfirmasi = input("Tetap simpan transaksi? (y/n): ").strip().casefold()
                if konfirmasi != "y":
                    print("Transaksi dibatalkan.")
                    return

    transaksi.append(item)
    simpan_transaksi(transaksi)
    print(f"Transaksi berhasil disimpan dengan ID {item['id']}.")


def ubah_transaksi(transaksi):
    try:
        id_transaksi = int(input("Masukkan ID transaksi yang ingin diubah: "))
    except ValueError:
        print("ID harus berupa angka.")
        return

    item = cari_id(transaksi, id_transaksi)
    if not item:
        print(f"Transaksi dengan ID {id_transaksi} tidak ditemukan.")
        return

    print("Kosongkan input jika ingin mempertahankan nilai lama.")
    tanggal = input(f"Tanggal [{item['tanggal']}]: ").strip()
    if tanggal:
        try:
            item["tanggal"] = baca_tanggal(tanggal).isoformat()
        except ValueError as error:
            print(f"{error} Perubahan dibatalkan.")
            return

    jenis = input(f"Jenis [{item['jenis']}] (pemasukan/pengeluaran): ").strip().casefold()
    if jenis:
        if jenis not in JENIS_VALID:
            print("Jenis tidak valid. Perubahan dibatalkan.")
            return
        item["jenis"] = jenis

    kategori = input(f"Kategori [{item['kategori']}]: ").strip()
    if kategori:
        item["kategori"] = kategori

    deskripsi = input(f"Deskripsi [{item['deskripsi']}]: ").strip()
    if deskripsi:
        item["deskripsi"] = deskripsi

    nominal = input(f"Nominal [{item['nominal']}], kosongkan untuk tetap: ").strip()
    if nominal:
        try:
            nilai = int(nominal.replace(".", "").replace(",", ""))
            if nilai <= 0:
                raise ValueError
            item["nominal"] = nilai
        except ValueError:
            print("Nominal tidak valid. Perubahan dibatalkan.")
            return

    simpan_transaksi(transaksi)
    print("Transaksi berhasil diubah.")


def hapus_transaksi(transaksi):
    try:
        id_transaksi = int(input("Masukkan ID transaksi yang ingin dihapus: "))
    except ValueError:
        print("ID harus berupa angka.")
        return

    item = cari_id(transaksi, id_transaksi)
    if not item:
        print(f"Transaksi dengan ID {id_transaksi} tidak ditemukan.")
        return

    print(f"ID {item['id']} | {item['tanggal']} | {item['kategori']} | "
          f"{item['deskripsi']} | {rupiah(item['nominal'])}")
    konfirmasi = input("Yakin menghapus transaksi ini? (y/n): ").strip().casefold()
    if konfirmasi == "y":
        transaksi.remove(item)
        simpan_transaksi(transaksi)
        print("Transaksi berhasil dihapus.")
    else:
        print("Penghapusan dibatalkan.")


def menu_filter(transaksi, anggaran):
    print("\nFILTER TRANSAKSI")
    print("1. Berdasarkan bulan (YYYY-MM)")
    print("2. Berdasarkan kategori")
    print("3. Berdasarkan rentang tanggal")
    print("4. Gabungan filter bulan dan kategori")
    pilihan = input("Pilih filter: ").strip()

    try:
        if pilihan == "1":
            bulan = baca_bulan(input("Bulan (YYYY-MM): ").strip())
            hasil = filter_transaksi(transaksi, bulan=bulan)
        elif pilihan == "2":
            kategori = input("Kategori: ").strip()
            if not kategori:
                print("Kategori tidak boleh kosong.")
                return
            hasil = filter_transaksi(transaksi, kategori=kategori)
        elif pilihan == "3":
            awal = input_tanggal("Tanggal awal (YYYY-MM-DD): ")
            akhir = input_tanggal("Tanggal akhir (YYYY-MM-DD): ")
            if awal > akhir:
                print("Tanggal awal tidak boleh setelah tanggal akhir.")
                return
            hasil = filter_transaksi(transaksi, tanggal_awal=awal, tanggal_akhir=akhir)
        elif pilihan == "4":
            bulan = baca_bulan(input("Bulan (YYYY-MM): ").strip())
            kategori = input("Kategori: ").strip()
            if not kategori:
                print("Kategori tidak boleh kosong.")
                return
            hasil = filter_transaksi(transaksi, bulan=bulan, kategori=kategori)
        else:
            print("Pilihan filter tidak valid.")
            return
    except ValueError as error:
        print(error)
        return

    print(f"\nDitemukan {len(hasil)} transaksi.")
    tampilkan_transaksi(hasil)
    print("\nRingkasan untuk hasil filter:")
    tampilkan_saldo(hasil)
    tampilkan_rekap(hasil, anggaran, transaksi_semua=transaksi)


def atur_anggaran(anggaran):
    kategori = input("Nama kategori anggaran: ").strip()
    if not kategori:
        print("Kategori tidak boleh kosong.")
        return
    batas = input_nominal("Batas anggaran bulanan (angka positif): ")
    anggaran[kategori.casefold()] = batas
    simpan_anggaran(anggaran)
    print(f"Anggaran {kategori} disimpan: {rupiah(batas)} per bulan.")


def ekspor_laporan(transaksi):
    try:
        bulan = baca_bulan(input("Bulan laporan (YYYY-MM): ").strip())
    except ValueError as error:
        print(error)
        return

    data_bulan = filter_transaksi(transaksi, bulan=bulan)
    pemasukan, pengeluaran, saldo = hitung_ringkasan(data_bulan)
    rekap, total_pengeluaran = buat_rekap(data_bulan)
    tahun, nomor_bulan = map(int, bulan.split("-"))
    jumlah_hari = calendar.monthrange(tahun, nomor_bulan)[1]
    rata_harian = pengeluaran / jumlah_hari if jumlah_hari else 0

    terbesar = sorted(
        (t for t in data_bulan if t["jenis"] == "pengeluaran"),
        key=lambda t: t["nominal"],
        reverse=True
    )[:3]

    baris = [
        f"==============================================",
        f"       LAPORAN KEUANGAN BULAN {bulan}",
        f"==============================================",
        f"Total Pemasukan   : {rupiah(pemasukan)}",
        f"Total Pengeluaran : {rupiah(pengeluaran)}",
        f"Saldo Bulan Ini   : {rupiah(saldo)}",
        f"Rata-rata Harian  : {rupiah(round(rata_harian))} ({jumlah_hari} hari)",
        "",
        "REKAPITULASI PER KATEGORI",
        "----------------------------------------------",
    ]

    if rekap:
        for kategori, nilai in sorted(rekap.items()):
            persen = (nilai["pengeluaran"] / total_pengeluaran * 100
                      if total_pengeluaran else 0)
            baris.append(
                f"- {kategori.title()}:"
                f"\n  * Pemasukan   : {rupiah(nilai['pemasukan'])}"
                f"\n  * Pengeluaran : {rupiah(nilai['pengeluaran'])} ({persen:.2f}% dari total)"
            )
    else:
        baris.append("Tidak ada transaksi pada bulan ini.")

    baris.extend(["", "3 PENGELUARAN TERBESAR", "----------------------------------------------"])
    if terbesar:
        for i, t in enumerate(terbesar, 1):
            baris.append(
                f"{i}. [{t['tanggal']}] {t['kategori']} - {t['deskripsi']} : {rupiah(t['nominal'])}"
            )
    else:
        baris.append("Tidak ada pengeluaran pada bulan ini.")

    baris.extend(["", "==============================================", "       Dibuat Otomatis oleh DompetKu", "=============================================="])

    nama_file = Path(f"laporan_{bulan}.txt")
    nama_file.write_text("\n".join(baris) + "\n", encoding="utf-8")
    print(f"Laporan berhasil diekspor ke file teks: {nama_file}")


def ganti_pin():
    """Ganti PIN setelah pengguna memasukkan PIN lama dengan benar."""
    try:
        data = json.loads(PIN_FILE.read_text(encoding="utf-8"))
        salt_lama = data["salt"]
        hash_lama = data["pin_hash"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        print("File PIN bermasalah; PIN tidak dapat diubah.")
        return

    pin_lama = getpass.getpass("Masukkan PIN lama: ").strip()
    if not hmac.compare_digest(hash_pin(pin_lama, salt_lama), hash_lama):
        print("PIN lama salah.")
        return

    while True:
        pin_baru = getpass.getpass("Masukkan PIN baru (4-6 digit): ").strip()
        if not (pin_baru.isdigit() and 4 <= len(pin_baru) <= 6):
            print("PIN harus terdiri dari 4 sampai 6 angka.")
            continue
        konfirmasi = getpass.getpass("Ulangi PIN baru: ").strip()
        if pin_baru != konfirmasi:
            print("PIN tidak cocok. Coba lagi.")
            continue
        import secrets
        salt_baru = secrets.token_hex(16)
        data_baru = {
            "salt": salt_baru,
            "pin_hash": hash_pin(pin_baru, salt_baru)
        }
        PIN_FILE.write_text(
            json.dumps(data_baru, indent=2), encoding="utf-8"
        )
        print("PIN berhasil diganti.")
        return


def cari_transaksi(transaksi):
    kata_kunci = input("Kata kunci deskripsi: ").strip().casefold()
    if not kata_kunci:
        print("Kata kunci tidak boleh kosong.")
        return
    hasil = [t for t in transaksi if kata_kunci in t["deskripsi"].casefold()]
    print(f"Ditemukan {len(hasil)} transaksi.")
    tampilkan_transaksi(hasil)


def main():
    if not autentikasi_pin():
        return

    transaksi = muat_transaksi()
    anggaran = muat_anggaran()

    print("=" * 48)
    print("SELAMAT DATANG DI DOMPETKU")
    print(f"{len(transaksi)} transaksi berhasil dimuat.")
    print("=" * 48)

    while True:
        print("""
MENU UTAMA
1. Tambah transaksi
2. Lihat semua transaksi
3. Hitung saldo
4. Rekap per kategori
5. Ubah transaksi
6. Hapus transaksi
7. Filter transaksi
8. Atur anggaran kategori
9. Ekspor laporan bulanan (.txt)
10. Cari transaksi berdasarkan deskripsi
11. Ganti PIN
0. Keluar
""")
        pilihan = input("Pilih menu: ").strip()

        try:
            if pilihan == "1":
                tambah_transaksi(transaksi, anggaran)
            elif pilihan == "2":
                tampilkan_transaksi(transaksi)
            elif pilihan == "3":
                tampilkan_saldo(transaksi)
            elif pilihan == "4":
                tampilkan_rekap(transaksi, anggaran, transaksi_semua=transaksi)
            elif pilihan == "5":
                ubah_transaksi(transaksi)
            elif pilihan == "6":
                hapus_transaksi(transaksi)
            elif pilihan == "7":
                menu_filter(transaksi, anggaran)
            elif pilihan == "8":
                atur_anggaran(anggaran)
            elif pilihan == "9":
                ekspor_laporan(transaksi)
            elif pilihan == "10":
                cari_transaksi(transaksi)
            elif pilihan == "11":
                ganti_pin()
            elif pilihan == "0":
                print("Data sudah tersimpan. Terima kasih telah menggunakan DompetKu!")
                break
            else:
                print("Pilihan menu tidak tersedia. Silakan pilih lagi.")
        except (OSError, PermissionError) as error:
            print(f"Terjadi masalah saat mengakses file: {error}")
        except Exception as error:
            print(f"Terjadi kesalahan: {error}. Silakan coba lagi.")


if __name__ == "__main__":
    main()