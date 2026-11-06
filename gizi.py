"""Perhitungan Z-score & status risiko (pendekatan SEDERHANA untuk demo, bukan standar WHO resmi)."""
import hashlib
import numpy as np

AGES = [0, 6, 12, 24, 36, 48, 60]
REF = {  # (median, SD) per umur (bulan) - pendekatan dari tabel WHO, diinterpolasi linear
    ("Laki-laki", "tb"): ([49.9, 67.6, 75.7, 87.8, 96.1, 103.3, 110.0], [1.9, 2.3, 2.5, 3.2, 3.7, 4.1, 4.5]),
    ("Perempuan", "tb"): ([49.1, 65.7, 74.0, 86.4, 95.1, 102.7, 109.4], [1.9, 2.3, 2.6, 3.3, 3.8, 4.2, 4.6]),
    ("Laki-laki", "bb"): ([3.3, 7.9, 9.6, 12.2, 14.3, 16.3, 18.3], [0.4, 0.9, 1.1, 1.4, 1.7, 2.0, 2.4]),
    ("Perempuan", "bb"): ([3.2, 7.3, 8.9, 11.5, 13.9, 16.1, 18.2], [0.4, 0.9, 1.1, 1.5, 1.8, 2.2, 2.6]),
}

def ref(sex, kind, age):
    m, s = REF[(sex if sex in ("Laki-laki", "Perempuan") else "Perempuan", kind)]
    return float(np.interp(age, AGES, m)), float(np.interp(age, AGES, s))

def zscore(sex, kind, age, val):
    m, s = ref(sex, kind, age)
    return round((val - m) / s, 2)

def status_gizi(z_bb, z_tb):
    if z_tb < -2: return "Stunting"
    if z_bb < -2: return "Gizi kurang"
    if z_bb > 2: return "Risiko gizi lebih"
    return "Normal"

def risiko_ibu(sis, dia, hb, lila):
    kek, anemia, hip = lila < 23.5, hb < 11, (sis >= 140 or dia >= 90)
    n = int(kek) + int(anemia) + int(hip)
    r = "Risiko tinggi" if (hip or hb < 8 or n >= 2) else "Perlu pemantauan" if n == 1 else "Risiko rendah"
    return ("KEK" if kek else "Tidak KEK"), ("Anemia" if anemia else "Tidak anemia"), ("Hipertensi" if hip else "Normal"), r

def hash_pw(p):
    return hashlib.sha256(("posyandu::" + p).encode()).hexdigest()
