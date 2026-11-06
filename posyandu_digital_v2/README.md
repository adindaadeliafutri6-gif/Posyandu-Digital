# Posyandu Digital v3 (Streamlit)

Sesuai swimlane: Kader · Sistem · Ibu Hamil · Orang Tua Balita.

## Menjalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```
Untuk membuat ulang dataset: `python gen_data.py` (menimpa isi folder data/).

## Akun demo
| Peran | Username | Password |
|---|---|---|
| Kader | kader1 / kader2 / kader3 | kader123 |
| Ibu Hamil | ibu001 … ibu050 | demo123 |
| Orang Tua Balita | ort001 … ort080 | demo123 |

## Tampilan
Tema pastel netral (krem · rose · sage · lavender) dengan animasi halus. Warna dasar diatur di `.streamlit/config.toml`, gaya kartu/banner di fungsi `css()` pada `app.py`, dan palet grafik di konstanta `PAL`. Login punya tombol masuk cepat (mode demo).

## Fitur
- Halaman awal = login; dashboard & menu otomatis menyesuaikan peran.
- Sidebar mengecil menjadi ikon; melebar otomatis saat kursor diarahkan ke sidebar.
- Kader: dashboard (tren, status gizi, stunting per dusun, histogram Z-score, faktor risiko ibu, daftar tindak lanjut), cari/daftar peserta, input pemeriksaan (Z-score, status gizi, risiko, jadwal & HPL otomatis), laporan bulanan dengan dropdown variabel + pengelompokan, unduh CSV/Excel, simpan ke database laporan, serahkan ke Puskesmas.
- Ibu Hamil: KPI kehamilan/HPL/risiko, grafik BB, tekanan darah, Hb, LILA dengan garis batas, riwayat KIA digital.
- Orang Tua: grafik KMS (BB/U & TB/U dengan rentang -2 s.d. +2 SD), lingkar kepala, Z-score, jadwal.

## Dataset (sintetis)
150 peserta (100 balita + 50 ibu hamil), 244 pemeriksaan balita (data terakhir 5 Nov 2026), ±88 pemeriksaan ibu hamil, 133 akun.

## Catatan
Z-score memakai pendekatan sederhana dari tabel median/SD WHO (interpolasi linear), BUKAN perhitungan LMS resmi. Ambang: stunting TB/U < -2 SD, gizi kurang BB/U < -2 SD, KEK LILA < 23,5 cm, anemia Hb < 11 g/dL, hipertensi ≥ 140/90. Hanya untuk demo, bukan diagnosis medis. Password disimpan sebagai hash SHA-256 tanpa salt per-user (cukup untuk demo, tidak untuk produksi).
