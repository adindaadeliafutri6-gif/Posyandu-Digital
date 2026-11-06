"""Membuat dataset sintetis: 150 peserta (100 balita + 50 ibu hamil) + riwayat pemeriksaan + akun login."""
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd
import gizi

rng = np.random.default_rng(2026)
D = Path(__file__).parent / "data"; D.mkdir(exist_ok=True)
REF_DAY = date(2026, 11, 5)
DUSUN = ["Melati", "Mawar", "Kenanga", "Anggrek"]
FP = ["Siti","Dewi","Putri","Ayu","Rina","Sari","Wulan","Intan","Fitri","Nur","Lestari","Maya","Rani","Tika","Yuni","Ani","Bunga","Citra","Dian","Eka"]
MP = ["Budi","Agus","Andi","Rizki","Dimas","Fajar","Hadi","Joko","Eko","Bayu","Yoga","Rafi","Dani","Arif","Doni","Gilang","Naufal","Reza","Taufik","Wahyu"]
LN = ["Pratama","Saputra","Wijaya","Lestari","Hidayat","Kusuma","Maulana","Santoso","Rahmawati","Nugroho","Permata","Firmansyah","Utami","Setiawan","Ramadhan"]
def nm(f): return f"{rng.choice(FP if f else MP)} {rng.choice(LN)}"
def hp(): return "08" + "".join(map(str, rng.integers(0, 10, 10)))

peserta, bal, ibu, users = [], [], [], []
for k in (1, 2, 3):
    users.append(dict(username=f"kader{k}", password_hash=gizi.hash_pw("kader123"), role="Kader", nama=f"Kader {nm(True)}", id_peserta=""))

# ---- orang tua (80 akun), 100 balita (20 di antaranya adik/kakak) ----
parents = [dict(id=f"ORT{i+1:03d}", nama=nm(i % 2 == 0), dusun=rng.choice(DUSUN), hp=hp()) for i in range(80)]
for p in parents:
    users.append(dict(username=p["id"].lower(), password_hash=gizi.hash_pw("demo123"), role="Orang Tua Balita", nama=p["nama"], id_peserta=p["id"]))
for n in range(100):
    par = parents[n] if n < 80 else parents[rng.integers(0, 80)]
    sex = rng.choice(["Laki-laki", "Perempuan"]); age_now = int(rng.integers(6, 58))
    pid = f"BLT{n+1:03d}"; lahir = REF_DAY - timedelta(days=int(age_now * 30.4))
    peserta.append(dict(id_peserta=pid, jenis_peserta="Balita", nama=nm(sex == "Perempuan"), tanggal_lahir=lahir, usia_bulan=age_now,
        usia_ibu_tahun="", jenis_kelamin=sex, id_orang_tua=par["id"], nama_orang_tua=par["nama"], usia_kehamilan_minggu="",
        alamat_dusun=par["dusun"], no_hp=par["hp"], status="Terdaftar", tanggal_daftar=lahir + timedelta(days=30)))
    z_tb = rng.normal(-0.7, 1.1); z_bb = 0.6 * z_tb + rng.normal(-0.2, 0.8)
    backs = sorted(rng.choice(6, size=int(rng.integers(1, 5)), replace=False), reverse=True)
    for bk in backs:
        d = REF_DAY - timedelta(days=int(bk * 30 + rng.integers(0, 25)))
        age = max(1, age_now - (REF_DAY - d).days / 30.4)
        zt, zb = z_tb + rng.normal(0, .15), z_bb + rng.normal(0, .2)
        mt, st_ = gizi.ref(sex, "tb", age); mb, sb = gizi.ref(sex, "bb", age)
        tb, bb = round(mt + zt * st_, 1), round(mb + zb * sb, 1)
        zbb, ztb = gizi.zscore(sex, "bb", age, bb), gizi.zscore(sex, "tb", age, tb)
        bal.append(dict(id_peserta=pid, tanggal_pemeriksaan=d, usia_bulan=round(age, 1), berat_kg=bb, tinggi_cm=tb,
            lingkar_kepala_cm=round(34.5 + 12 * (1 - np.exp(-age / 10)) + rng.normal(0, .8), 1),
            vitamin_a=rng.choice(["Ya", "Tidak"], p=[.6, .4]), imunisasi=rng.choice(["Lengkap sesuai usia", "Belum lengkap"], p=[.75, .25]),
            z_bb_u=zbb, z_tb_u=ztb, status_gizi=gizi.status_gizi(zbb, ztb), jadwal_berikutnya=d + timedelta(days=28),
            catatan=rng.choice(["Kondisi baik", "Pantau kenaikan berat badan", "Edukasi MP-ASI", "Kontrol bulan depan"])))

# ---- 50 ibu hamil ----
for n in range(50):
    pid = f"IBU{n+1:03d}"; w0 = int(rng.integers(8, 39)); umur = int(rng.integers(19, 43))
    nama = nm(True); dus = rng.choice(DUSUN); lila0 = rng.normal(25.3, 2.4); pre = rng.normal(55, 8)
    peserta.append(dict(id_peserta=pid, jenis_peserta="Ibu Hamil", nama=nama, tanggal_lahir="", usia_bulan="", usia_ibu_tahun=umur,
        jenis_kelamin="Perempuan", id_orang_tua="", nama_orang_tua="", usia_kehamilan_minggu=w0, alamat_dusun=dus, no_hp=hp(),
        status="Terdaftar", tanggal_daftar=REF_DAY - timedelta(days=int(rng.integers(30, 200)))))
    users.append(dict(username=pid.lower(), password_hash=gizi.hash_pw("demo123"), role="Ibu Hamil", nama=nama, id_peserta=pid))
    hipertensi = rng.random() < .15; hb0 = rng.normal(11.3, 1.3)
    for bk in sorted(rng.choice(6, size=int(rng.integers(1, 5)), replace=False), reverse=True):
        d = REF_DAY - timedelta(days=int(bk * 28 + rng.integers(0, 20))); w = w0 - round((REF_DAY - d).days / 7)
        if w < 4: continue
        sis = int(rng.normal(146 if hipertensi else 112, 8)); dia = int(rng.normal(94 if hipertensi else 72, 6))
        hb, lila = round(hb0 + rng.normal(0, .3), 1), round(lila0 + rng.normal(0, .2), 1)
        kek, an, hip, r = gizi.risiko_ibu(sis, dia, hb, lila)
        ibu.append(dict(id_peserta=pid, tanggal_pemeriksaan=d, usia_kehamilan_minggu=w, berat_kg=round(pre + .35 * w + rng.normal(0, .8), 1),
            lila_cm=lila, sistol=sis, diastol=dia, hb_gdl=hb, tfu_cm=round(max(0, w - 4 + rng.normal(0, 1)), 1) if w >= 20 else "",
            djj_bpm=int(rng.normal(140, 8)) if w >= 12 else "", tablet_fe=rng.choice(["Diberikan", "Belum diberikan"], p=[.8, .2]),
            status_kek=kek, status_anemia=an, status_hipertensi=hip, risiko=r,
            jadwal_berikutnya=d + timedelta(days=14 if r == "Risiko tinggi" else 28), hpl=d + timedelta(days=(40 - w) * 7),
            catatan="Rujuk ke bidan" if r == "Risiko tinggi" else "Kontrol rutin"))

pd.DataFrame(peserta).to_csv(D / "peserta.csv", index=False)
pd.DataFrame(bal).to_csv(D / "pemeriksaan_balita.csv", index=False)
pd.DataFrame(ibu).to_csv(D / "pemeriksaan_ibu_hamil.csv", index=False)
pd.DataFrame(users).to_csv(D / "users.csv", index=False)
pd.DataFrame(columns=["id_laporan","periode","kelompok","variabel","dibuat_oleh","tanggal_dibuat","status","tanggal_serah"]).to_csv(D / "laporan.csv", index=False)
print(len(peserta), "peserta |", len(bal), "pemeriksaan balita |", len(ibu), "pemeriksaan ibu |", len(users), "akun")
