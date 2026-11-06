import io
from datetime import date, timedelta
from pathlib import Path
import altair as alt, numpy as np, pandas as pd, streamlit as st
import gizi

st.set_page_config(page_title="Posyandu Digital", page_icon="🌸", layout="wide", initial_sidebar_state="expanded")
D = Path(__file__).parent / "data"
FILES = {k: D / f"{k}.csv" for k in ["users", "peserta", "pemeriksaan_balita", "pemeriksaan_ibu_hamil", "laporan"]}
TODAY = date.today()
BULAN = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"]
# Palet pastel netral (selaras dengan .streamlit/config.toml)
INK, MUTED, GRID = "#4a4540", "#8b8279", "#eadfd3"
GREEN, ROSE, SKY, LAV, PEACH, BAD = "#8fb59a", "#c9a9a0", "#9fbbd0", "#b9acd6", "#e6b787", "#d98686"
PAL = [ROSE, GREEN, SKY, LAV, PEACH, "#b8a99a", "#c7d3b4", "#e0b6c4"]
FONT = "Plus Jakarta Sans, sans-serif"
SC = {"Normal": GREEN, "Risiko rendah": GREEN, "Gizi kurang": PEACH, "Perlu pemantauan": PEACH,
      "Stunting": BAD, "Risiko tinggi": BAD, "Risiko gizi lebih": LAV}
MENU = {"Kader": ["🏠 Dashboard", "👥 Data Peserta", "🧒 Pemeriksaan Balita", "🤰 Pemeriksaan Ibu Hamil", "📊 Laporan Bulanan", "🗂️ Riwayat Laporan"],
        "Ibu Hamil": ["🏠 Dashboard", "📖 Riwayat KIA Digital"],
        "Orang Tua Balita": ["🏠 Dashboard", "📈 Grafik Pertumbuhan"]}

# ---------- util ----------
def load(k): return pd.read_csv(FILES[k], dtype={"no_hp": str})
def save(df, k): df.to_csv(FILES[k], index=False)

def data():
    p, b, i = load("peserta"), load("pemeriksaan_balita"), load("pemeriksaan_ibu_hamil")
    for d in (b, i): d["tanggal_pemeriksaan"] = pd.to_datetime(d["tanggal_pemeriksaan"])
    b = b.merge(p[["id_peserta", "nama", "jenis_kelamin", "alamat_dusun", "no_hp", "tanggal_lahir", "id_orang_tua", "nama_orang_tua"]], on="id_peserta", how="left")
    i = i.merge(p[["id_peserta", "nama", "alamat_dusun", "no_hp"]], on="id_peserta", how="left")
    i["trimester"] = pd.cut(i["usia_kehamilan_minggu"], [0, 13, 27, 45], labels=["Trimester 1", "Trimester 2", "Trimester 3"]).astype(str)
    for d in (b, i):
        d["bulan"], d["tahun"] = d["tanggal_pemeriksaan"].dt.month, d["tanggal_pemeriksaan"].dt.year
        d["periode"] = d["tanggal_pemeriksaan"].dt.strftime("%Y-%m")
    return p, b, i

def latest(df): return df.sort_values("tanggal_pemeriksaan").groupby("id_peserta").tail(1)
def fmt(d): return pd.to_datetime(d).strftime("%d %b %Y") if pd.notna(d) and d != "" else "-"
def next_id(p, prefix):
    n = pd.to_numeric(p.loc[p.id_peserta.str.startswith(prefix), "id_peserta"].str[3:], errors="coerce").max()
    return f"{prefix}{int(0 if pd.isna(n) else n) + 1:03d}"

def colr(d, f, title=None):
    vals = list(d[f].dropna().unique()); t = f if title is None else title
    if vals and all(v in SC for v in vals):
        dom = [v for v in SC if v in vals]
        return alt.Color(f"{f}:N", title=t, scale=alt.Scale(domain=dom, range=[SC[v] for v in dom]), legend=alt.Legend(orient="bottom"))
    return alt.Color(f"{f}:N", title=t, scale=alt.Scale(range=PAL), legend=alt.Legend(orient="bottom"))

def donut(df, f, title, h=250):
    d = df[f].value_counts().rename_axis(f).reset_index(name="Jumlah")
    return alt.Chart(d).mark_arc(innerRadius=55).encode(theta="Jumlah:Q", color=colr(d, f, ""), tooltip=[f, "Jumlah"]).properties(title=title, height=h)

def bars(df, f, title, group=None, h=250):
    if group:
        d = df.groupby([f, group]).size().reset_index(name="Jumlah"); c = colr(d, group)
    else:
        d = df[f].value_counts().rename_axis(f).reset_index(name="Jumlah"); c = colr(d, f, "")
    return alt.Chart(d).mark_bar(cornerRadiusEnd=6).encode(x=alt.X("Jumlah:Q", title="Jumlah"), y=alt.Y(f"{f}:N", sort="-x", title=None),
        color=c, tooltip=[f, "Jumlah"] + ([group] if group else [])).properties(title=title, height=h)

def trend(df, x, ys, title, rule=None, ytitle=None, h=230):
    long = df[[x] + list(ys)].melt(x, var_name="Variabel", value_name="Nilai")
    ch = alt.Chart(long).mark_line(point=True).encode(x=alt.X(x, title=None), y=alt.Y("Nilai:Q", scale=alt.Scale(zero=False), title=ytitle),
        color=alt.Color("Variabel:N", legend=alt.Legend(orient="bottom", title=None)), tooltip=[x, "Variabel", "Nilai"])
    if rule is not None:
        ch += alt.Chart(pd.DataFrame({"y": [rule]})).mark_rule(color=BAD, strokeDash=[5, 4]).encode(y="y:Q")
    return ch.properties(title=title, height=h)

def kms(child_df, sex, kind, ycol, title, ytitle):
    ages = np.arange(0, 61)
    ref = pd.DataFrame({"usia": ages, "m": [gizi.ref(sex, kind, a)[0] for a in ages], "s": [gizi.ref(sex, kind, a)[1] for a in ages]})
    ref["-2SD"], ref["+2SD"], ref["Median"] = ref.m - 2 * ref.s, ref.m + 2 * ref.s, ref.m
    band = alt.Chart(ref).mark_area(opacity=.28, color=GREEN).encode(x="usia:Q", y="-2SD:Q", y2="+2SD:Q")
    med = alt.Chart(ref).mark_line(color="#6f9a7b", strokeDash=[4, 3]).encode(x="usia:Q", y="Median:Q")
    pts = alt.Chart(child_df).mark_line(point=alt.OverlayMarkDef(size=70, color="#a8776d"), color="#a8776d").encode(
        x=alt.X("usia_bulan:Q", title="Usia (bulan)"), y=alt.Y(f"{ycol}:Q", scale=alt.Scale(zero=False), title=ytitle),
        tooltip=["tanggal_pemeriksaan:T", "usia_bulan", ycol])
    return (band + med + pts).properties(title=title, height=270)

_N = [0]
def plot(target, ch):
    """Tampilkan chart di dalam kartu dengan tema pastel yang seragam."""
    ch = (ch.configure(background="transparent", font=FONT).configure_view(stroke=None)
          .configure_axis(gridColor=GRID, domainColor="#d9cdbf", tickColor="#d9cdbf", labelColor=MUTED, titleColor=MUTED,
                          labelFontSize=11, titleFontSize=11, titleFontWeight=500)
          .configure_title(color=INK, fontSize=14, fontWeight=600, anchor="start", offset=12, font=FONT)
          .configure_legend(labelColor=MUTED, titleColor=MUTED, symbolType="circle", labelFontSize=11)
          .configure_range(category=PAL))
    _N[0] += 1
    with target.container(border=True, key=f"card_{_N[0]}"):
        st.altair_chart(ch, theme=None, width="stretch")

def header(title, sub=""):
    ic, _, txt = title.partition(" ")
    st.markdown(f'<div class="hdr"><div class="ic">{ic}</div><div><h1>{txt}</h1>' + (f"<p>{sub}</p>" if sub else "") + "</div></div>", unsafe_allow_html=True)

def kpi(cols, items):
    for c, (l, v, *r) in zip(cols, items): c.metric(l, v, r[0] if r else None, delta_color="off")

def css(logged):
    base = """<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    :root{--ink:#4a4540;--muted:#8b8279;--rose:#c9a9a0;--rose-d:#a8776d;--sage:#8fb59a;--sand:#f1e9df;--line:#e9ddd0;}
    .stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp button, .stApp input, .stApp textarea,
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stCaptionContainer"] {font-family:'Plus Jakarta Sans',sans-serif!important;}
    @keyframes bg {0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%}}
    @keyframes fadeUp {from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:translateY(0)}}
    @keyframes float {0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)}}
    [data-testid="stAppViewContainer"] {background:linear-gradient(-45deg,#faf6f1,#f7ede7,#ecf1ec,#eceff4); background-size:320% 320%; animation:bg 30s ease infinite;}
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none!important;}
    [data-testid="stHeader"] {background:transparent!important; height:0!important;}
    [data-testid="stMainBlockContainer"] {padding-top:1.8rem; max-width:1240px; animation:fadeUp .55s ease both;}
    h2, h3 {color:var(--ink); font-weight:700!important; letter-spacing:-.01em;}
    /* banner halaman */
    .hdr {display:flex; align-items:center; gap:16px; padding:20px 26px; margin-bottom:1.3rem; border-radius:22px;
        background:linear-gradient(120deg,#f4dfd8 0%,#ebe3f1 55%,#dfe9e1 100%); border:1px solid rgba(255,255,255,.85);
        box-shadow:0 8px 28px rgba(120,100,90,.08); animation:fadeUp .6s ease both;}
    .hdr .ic {width:54px; height:54px; flex:none; border-radius:16px; background:rgba(255,255,255,.78); display:grid; place-items:center;
        font-size:1.7rem; box-shadow:0 4px 12px rgba(120,100,90,.1); animation:float 5s ease-in-out infinite;}
    .hdr h1 {margin:0!important; padding:0!important; font-size:1.55rem!important; font-weight:800!important; color:var(--ink); line-height:1.25;}
    .hdr p {margin:3px 0 0!important; color:var(--muted); font-size:.9rem;}
    /* kartu (chart, form, kpi) */
    [class*="st-key-card_"], [data-testid="stForm"], [data-testid="stExpander"], [data-testid="stDataFrame"] {
        background:rgba(255,255,255,.72)!important; border:1px solid rgba(255,255,255,.95)!important; border-radius:18px!important;
        box-shadow:0 6px 22px rgba(120,100,90,.07); transition:box-shadow .3s ease, transform .3s ease;}
    [class*="st-key-card_"] {padding:10px 14px 6px; margin-bottom:.4rem; animation:fadeUp .6s ease both;}
    [class*="st-key-card_"]:hover, [data-testid="stForm"]:hover {box-shadow:0 12px 30px rgba(120,100,90,.12);}
    [data-testid="stExpander"] details {border:none!important;}
    [data-testid="stMetric"] {background:rgba(255,255,255,.78); border:1px solid rgba(255,255,255,.95); border-radius:16px; padding:14px 16px;
        box-shadow:0 4px 16px rgba(120,100,90,.06); transition:transform .25s ease, box-shadow .25s ease; animation:fadeUp .6s ease both; height:100%;}
    [data-testid="stMetric"]:hover {transform:translateY(-3px); box-shadow:0 10px 24px rgba(120,100,90,.12);}
    [data-testid="stMetricLabel"] p {font-size:.78rem; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.03em;}
    [data-testid="stMetricValue"] {font-size:1.35rem; font-weight:700; color:var(--ink);}
    [data-testid="stMetricValue"] > div {white-space:normal!important; overflow:visible!important; text-overflow:clip!important; line-height:1.25;}
    /* tombol & input */
    .stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {border-radius:12px; font-weight:600; border:1px solid var(--line); transition:all .25s ease;}
    .stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {transform:translateY(-2px); box-shadow:0 8px 18px rgba(168,119,109,.25);}
    button[kind="primary"], button[kind="primaryFormSubmit"] {background:linear-gradient(135deg,#c9a9a0,#a8776d)!important; border:none!important; color:#fff!important;}
    [data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {border-radius:12px!important; background:rgba(255,255,255,.85)!important;}
    [data-testid="stAlert"] {border-radius:14px; border:none;}
    .login-hero {text-align:center; padding:1.2rem 0 1rem; animation:fadeUp .8s ease both;}
    .login-hero .em {font-size:3.4rem; display:inline-block; animation:float 4s ease-in-out infinite;}
    .login-hero h1 {font-size:1.9rem!important; font-weight:800!important; margin:.2rem 0 .3rem!important; color:var(--ink);}
    .login-hero p {color:var(--muted); margin:0;}
    .badge {display:inline-block; padding:4px 14px; border-radius:99px; background:#f2d9d4; color:#8a5f57; font-size:.72rem; font-weight:700; letter-spacing:.05em; margin-bottom:.5rem;}
    .side-brand {text-align:left; padding:.3rem .2rem .6rem; line-height:1.4;}
    .side-brand b {font-size:1.02rem; color:var(--ink);} .side-brand small {color:var(--muted);}
    .chip {display:inline-block; margin-top:6px; padding:2px 11px; border-radius:99px; background:#dfe9e1; color:#4d6b57; font-size:.72rem; font-weight:700;}
    @media (prefers-reduced-motion: reduce) {* {animation:none!important; transition:none!important;}}
    """
    side = """
    section[data-testid="stSidebar"] {position:fixed!important; inset:0 auto 0 0!important; top:0!important; height:100vh!important; height:100dvh!important;
        width:72px!important; min-width:72px!important; max-width:none!important; transform:none!important; margin:0!important; visibility:visible!important;
        overflow:hidden!important; z-index:1000; background:linear-gradient(180deg,#f4ece3,#ede4da)!important; border-right:1px solid var(--line);
        transition:width .3s cubic-bezier(.4,0,.2,1), box-shadow .3s ease;}
    section[data-testid="stSidebar"]:hover {width:280px!important; box-shadow:8px 0 28px rgba(120,100,90,.16);}
    section[data-testid="stSidebar"] > div {width:280px!important; height:100%!important; padding-top:0!important;}
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding:1rem .7rem;}
    [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarHeader"] {display:none!important;}
    [data-testid="stMain"], section.main {margin-left:72px; width:calc(100% - 72px);}
    section[data-testid="stSidebar"] * {white-space:nowrap;}
    section[data-testid="stSidebar"] button {justify-content:flex-start!important; text-align:left; border:none!important; box-shadow:none!important;
        background:transparent!important; color:var(--ink)!important; padding:.55rem .85rem; border-radius:12px; transition:background .2s ease, transform .2s ease;}
    section[data-testid="stSidebar"] button:hover {background:rgba(201,169,160,.22)!important; transform:translateX(3px);}
    section[data-testid="stSidebar"] button[kind="primary"] {background:rgba(201,169,160,.38)!important; box-shadow:inset 3px 0 0 #a8776d!important; font-weight:700;}
    section[data-testid="stSidebar"] button p {margin:0;}
    section[data-testid="stSidebar"] hr {margin:.8rem 0; border-color:var(--line);}
    """ if logged else '[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none!important;}'
    st.markdown(base + side + "</style>", unsafe_allow_html=True)

# ---------- login ----------
def login_page():
    users = load("users")
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown('<div class="login-hero"><span class="badge">POSYANDU DIGITAL</span><br><span class="em">🌸</span>'
                    '<h1>Sehat Bersama, Tumbuh Bersama</h1><p>Masuk sesuai peran: Kader, Ibu Hamil, atau Orang Tua Balita.</p></div>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username", placeholder="contoh: kader1 / ibu001 / ort001"); pw = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", width="stretch", type="primary"):
                m = users[(users.username == u.strip().lower()) & (users.password_hash == gizi.hash_pw(pw))]
                if len(m): st.session_state["user"] = m.iloc[0].fillna("").to_dict(); st.rerun()
                else: st.error("Username atau password salah.")
        st.caption("✨ Mode demo — masuk cepat tanpa mengetik:")
        c = st.columns(3)
        for col, (lbl, role) in zip(c, [("👩‍⚕️ Kader", "Kader"), ("🤰 Ibu Hamil", "Ibu Hamil"), ("👶 Balita", "Orang Tua Balita")]):
            if col.button(lbl, key="q_" + role, width="stretch"):
                st.session_state["user"] = users[users.role == role].iloc[0].fillna("").to_dict(); st.rerun()
        with st.expander("🔑 Daftar akun demo"):
            ex = pd.concat([users[users.role == r].head(2) for r in ["Kader", "Ibu Hamil", "Orang Tua Balita"]])
            ex = ex.assign(password=np.where(ex.role == "Kader", "kader123", "demo123"))[["role", "username", "password", "nama"]]
            st.dataframe(ex, hide_index=True, width="stretch")
            st.caption("Semua akun ibu hamil (ibu001–ibu050) & orang tua (ort001–ort080) memakai password demo123.")

# ---------- KADER ----------
def kader_dash(p, b, i):
    header("🏠 Dashboard Kader", f"Ringkasan kondisi posyandu · {TODAY.strftime('%d %B %Y')}")
    dus = st.selectbox("Wilayah dusun", ["Semua dusun"] + sorted(p.alamat_dusun.unique()))
    if dus != "Semua dusun": p, b, i = p[p.alamat_dusun == dus], b[b.alamat_dusun == dus], i[i.alamat_dusun == dus]
    lb, li = latest(b), latest(i)
    tl = int(lb.status_gizi.isin(["Stunting", "Gizi kurang"]).sum() + (li.risiko == "Risiko tinggi").sum())
    per = pd.concat([b.tanggal_pemeriksaan, i.tanggal_pemeriksaan]).dt.strftime("%Y-%m")
    pk = TODAY.strftime("%Y-%m") if (per == TODAY.strftime("%Y-%m")).any() or per.empty else per.max()
    bln = (per == pk).sum()
    kpi(st.columns(5), [("Total peserta", len(p)), ("Balita", (p.jenis_peserta == "Balita").sum()), ("Ibu hamil", (p.jenis_peserta == "Ibu Hamil").sum()),
                        (f"Pemeriksaan {BULAN[int(pk[5:]) - 1]}", int(bln)), ("Perlu tindak lanjut", tl)])
    t = pd.concat([b.assign(Kelompok="Balita"), i.assign(Kelompok="Ibu Hamil")]).groupby(["periode", "Kelompok"]).size().reset_index(name="Jumlah")
    c1, c2 = st.columns([3, 2])
    plot(c1, alt.Chart(t).mark_line(point=True).encode(x=alt.X("periode:N", title=None), y="Jumlah:Q", color=alt.Color("Kelompok:N", legend=alt.Legend(orient="bottom")),
                    tooltip=["periode", "Kelompok", "Jumlah"]).properties(title="Tren jumlah pemeriksaan per bulan", height=260))
    plot(c2, donut(lb, "status_gizi", "Status gizi balita (pemeriksaan terakhir)", 260))
    c3, c4 = st.columns(2)
    plot(c3, bars(lb, "alamat_dusun", "Status gizi balita per dusun", "status_gizi"))
    h = alt.Chart(lb).mark_bar(color=SKY).encode(x=alt.X("z_tb_u:Q", bin=alt.Bin(step=.5), title="Z-score TB/U"), y=alt.Y("count()", title="Jumlah balita"))
    r = alt.Chart(pd.DataFrame({"x": [-2]})).mark_rule(color=BAD, strokeDash=[5, 4]).encode(x="x:Q")
    plot(c4, (h + r).properties(title="Distribusi Z-score TB/U (garis merah = batas stunting −2)", height=250))
    c5, c6 = st.columns(2)
    plot(c5, donut(li, "risiko", "Tingkat risiko ibu hamil", 250))
    fk = pd.DataFrame({"Faktor risiko": ["KEK (LILA<23,5)", "Anemia (Hb<11)", "Hipertensi (≥140/90)", "Belum dapat tablet Fe"],
                       "Jumlah": [(li.status_kek == "KEK").sum(), (li.status_anemia == "Anemia").sum(), (li.status_hipertensi == "Hipertensi").sum(), (li.tablet_fe == "Belum diberikan").sum()]})
    plot(c6, alt.Chart(fk).mark_bar(color=PEACH, cornerRadiusEnd=6).encode(x="Jumlah:Q", y=alt.Y("Faktor risiko:N", sort="-x", title=None)).properties(title="Faktor risiko ibu hamil", height=250))
    st.subheader("⚠️ Daftar tindak lanjut")
    a = lb[lb.status_gizi.isin(["Stunting", "Gizi kurang"])].assign(Kelompok="Balita", Kondisi=lambda x: x.status_gizi)
    c = li[li.risiko == "Risiko tinggi"].assign(Kelompok="Ibu Hamil", Kondisi="Risiko tinggi")
    tl_df = pd.concat([a, c])[["Kelompok", "id_peserta", "nama", "alamat_dusun", "Kondisi", "no_hp", "jadwal_berikutnya"]]
    st.dataframe(tl_df.sort_values("jadwal_berikutnya"), hide_index=True, width="stretch")

def kader_peserta(p, b, i):
    header("👥 Data Peserta", "Cari peserta, lihat riwayat, atau daftarkan peserta baru")
    q = st.text_input("🔍 Cari peserta (nama / ID)  — langkah 3")
    f = st.radio("Jenis", ["Semua", "Balita", "Ibu Hamil"], horizontal=True)
    v = p if f == "Semua" else p[p.jenis_peserta == f]
    if q: v = v[v.nama.str.contains(q, case=False, na=False) | v.id_peserta.str.contains(q, case=False)]
    st.dataframe(v.drop(columns=["id_orang_tua"]), hide_index=True, width="stretch", height=260)
    if q and v.empty: st.warning("Peserta belum terdaftar — silakan isi form pendaftaran di bawah.")
    if len(v) and len(v) <= 40:
        pid = st.selectbox("Lihat riwayat peserta (langkah 6)", v.id_peserta, format_func=lambda x: f"{x} — {p.set_index('id_peserta').nama[x]}")
        h = (b if pid.startswith("BLT") else i)
        h = h[h.id_peserta == pid].sort_values("tanggal_pemeriksaan", ascending=False)
        st.dataframe(h.drop(columns=["nama", "alamat_dusun", "no_hp", "bulan", "tahun", "periode"], errors="ignore"), hide_index=True, width="stretch") if len(h) else st.info("Belum ada riwayat pemeriksaan.")
    with st.expander("➕ Daftarkan peserta baru (langkah 4–5)", expanded=bool(q and v.empty)):
        with st.form("reg", clear_on_submit=True):
            jenis = st.selectbox("Jenis peserta", ["Balita", "Ibu Hamil"]); nama = st.text_input("Nama peserta")
            c1, c2 = st.columns(2)
            dusun = c1.selectbox("Dusun", ["Melati", "Mawar", "Kenanga", "Anggrek"]); hp = c2.text_input("No. HP")
            ortu = c1.text_input("Nama orang tua (balita)"); sex = c2.selectbox("Jenis kelamin (balita)", ["Laki-laki", "Perempuan"])
            lahir = c1.date_input("Tanggal lahir (balita)", date(TODAY.year - 2, 1, 1)); umur = c2.number_input("Usia ibu (tahun)", 15, 50, 28)
            hamil = c1.number_input("Usia kehamilan (minggu)", 1, 42, 12)
            if st.form_submit_button("Simpan pendaftaran", type="primary"):
                if not nama.strip(): st.error("Nama wajib diisi.")
                else:
                    pre = "BLT" if jenis == "Balita" else "IBU"; pid = next_id(p, pre); users = load("users"); idot = ""
                    if jenis == "Balita":
                        ex = p[(p.jenis_peserta == "Balita") & (p.nama_orang_tua.str.lower() == ortu.strip().lower())]
                        if len(ex): idot = ex.id_orang_tua.iloc[0]
                        else:
                            idot = next_id(p.assign(id_peserta=p.id_orang_tua.fillna("")), "ORT") if p.id_orang_tua.notna().any() else "ORT001"
                            users = pd.concat([users, pd.DataFrame([dict(username=idot.lower(), password_hash=gizi.hash_pw("demo123"), role="Orang Tua Balita", nama=ortu or "Orang tua", id_peserta=idot)])])
                    else:
                        users = pd.concat([users, pd.DataFrame([dict(username=pid.lower(), password_hash=gizi.hash_pw("demo123"), role="Ibu Hamil", nama=nama, id_peserta=pid)])])
                    row = dict(id_peserta=pid, jenis_peserta=jenis, nama=nama.strip(), tanggal_lahir=lahir if jenis == "Balita" else "",
                               usia_bulan=max(0, (TODAY.year - lahir.year) * 12 + TODAY.month - lahir.month) if jenis == "Balita" else "",
                               usia_ibu_tahun=umur if jenis == "Ibu Hamil" else "", jenis_kelamin=sex if jenis == "Balita" else "Perempuan",
                               id_orang_tua=idot, nama_orang_tua=ortu, usia_kehamilan_minggu=hamil if jenis == "Ibu Hamil" else "",
                               alamat_dusun=dusun, no_hp=hp, status="Terdaftar", tanggal_daftar=TODAY)
                    save(pd.concat([load("peserta"), pd.DataFrame([row])]), "peserta"); save(users, "users")
                    st.success(f"✅ Pendaftaran berhasil. ID: {pid} (akun login: {pid.lower() if jenis == 'Ibu Hamil' else idot.lower()} / demo123)")

def kader_balita(p, b, i):
    header("🧒 Pemeriksaan Balita", "Input hasil timbang & ukur — status gizi dihitung otomatis")
    bl = p[p.jenis_peserta == "Balita"]
    with st.form("fb"):
        c1, c2 = st.columns(2)
        pid = c1.selectbox("Balita", bl.id_peserta, format_func=lambda x: f"{x} — {bl.set_index('id_peserta').nama[x]}")
        tgl = c2.date_input("Tanggal pemeriksaan", TODAY)
        bb = c1.number_input("Berat (kg)", 2.0, 40.0, 10.0, .1); tb = c2.number_input("Tinggi/panjang (cm)", 40.0, 130.0, 80.0, .5)
        lk = c1.number_input("Lingkar kepala (cm)", 30.0, 60.0, 46.0, .5)
        va = c2.selectbox("Vitamin A", ["Ya", "Tidak"]); im = c1.selectbox("Imunisasi", ["Lengkap sesuai usia", "Belum lengkap"]); cat = c2.text_input("Catatan")
        ok = st.form_submit_button("💾 Simpan & hitung status gizi (langkah 7–9)", type="primary")
    if ok:
        r = bl.set_index("id_peserta").loc[pid]; age = round(max(0, (tgl.year - pd.to_datetime(r.tanggal_lahir).year) * 12 + tgl.month - pd.to_datetime(r.tanggal_lahir).month), 1)
        zb, zt = gizi.zscore(r.jenis_kelamin, "bb", age, bb), gizi.zscore(r.jenis_kelamin, "tb", age, tb); s = gizi.status_gizi(zb, zt)
        row = dict(id_peserta=pid, tanggal_pemeriksaan=tgl, usia_bulan=age, berat_kg=bb, tinggi_cm=tb, lingkar_kepala_cm=lk, vitamin_a=va, imunisasi=im,
                   z_bb_u=zb, z_tb_u=zt, status_gizi=s, jadwal_berikutnya=tgl + timedelta(days=28), catatan=cat)
        save(pd.concat([load("pemeriksaan_balita"), pd.DataFrame([row])]), "pemeriksaan_balita"); st.session_state["last_b"] = (pid, row)
        p, b, i = data()
    if "last_b" in st.session_state:
        pid, row = st.session_state["last_b"]; st.success(f"Tersimpan untuk {pid}.")
        kpi(st.columns(4), [("Z-score BB/U", row["z_bb_u"]), ("Z-score TB/U", row["z_tb_u"]), ("Status gizi", row["status_gizi"]), ("Jadwal berikutnya", fmt(row["jadwal_berikutnya"]))])
    st.subheader("Riwayat terbaru")
    st.dataframe(b.sort_values("tanggal_pemeriksaan", ascending=False).head(15)[["tanggal_pemeriksaan", "id_peserta", "nama", "berat_kg", "tinggi_cm", "status_gizi", "jadwal_berikutnya"]], hide_index=True, width="stretch")

def kader_ibu(p, b, i):
    header("🤰 Pemeriksaan Ibu Hamil", "Input hasil pemeriksaan — risiko, jadwal & HPL dihitung otomatis")
    il = p[p.jenis_peserta == "Ibu Hamil"]
    with st.form("fi"):
        c1, c2, c3 = st.columns(3)
        pid = c1.selectbox("Ibu hamil", il.id_peserta, format_func=lambda x: f"{x} — {il.set_index('id_peserta').nama[x]}")
        tgl = c2.date_input("Tanggal", TODAY); w = c3.number_input("Usia kehamilan (minggu)", 1, 42, 20)
        bb = c1.number_input("Berat (kg)", 30.0, 150.0, 60.0, .1); lila = c2.number_input("LILA (cm)", 15.0, 40.0, 25.0, .1); hb = c3.number_input("Hb (g/dL)", 4.0, 18.0, 11.5, .1)
        sis = c1.number_input("Sistol", 70, 220, 115); dia = c2.number_input("Diastol", 40, 140, 75); tfu = c3.number_input("TFU (cm)", 0.0, 50.0, 0.0, .5)
        fe = c1.selectbox("Tablet tambah darah", ["Diberikan", "Belum diberikan"]); cat = c2.text_input("Catatan")
        ok = st.form_submit_button("💾 Simpan & analisis kondisi ibu (langkah 12–15)", type="primary")
    if ok:
        kek, an, hip, r = gizi.risiko_ibu(sis, dia, hb, lila)
        row = dict(id_peserta=pid, tanggal_pemeriksaan=tgl, usia_kehamilan_minggu=w, berat_kg=bb, lila_cm=lila, sistol=sis, diastol=dia, hb_gdl=hb, tfu_cm=tfu or "", djj_bpm="",
                   tablet_fe=fe, status_kek=kek, status_anemia=an, status_hipertensi=hip, risiko=r, jadwal_berikutnya=tgl + timedelta(days=14 if r == "Risiko tinggi" else 28),
                   hpl=tgl + timedelta(days=(40 - w) * 7), catatan=cat)
        save(pd.concat([load("pemeriksaan_ibu_hamil"), pd.DataFrame([row])]), "pemeriksaan_ibu_hamil"); st.session_state["last_i"] = (pid, row); p, b, i = data()
    if "last_i" in st.session_state:
        pid, row = st.session_state["last_i"]; st.success(f"Tersimpan untuk {pid}.")
        kpi(st.columns(5), [("Risiko", row["risiko"]), ("KEK", row["status_kek"]), ("Anemia", row["status_anemia"]), ("Tekanan darah", f"{row['sistol']}/{row['diastol']}"), ("Kontrol berikutnya", fmt(row["jadwal_berikutnya"]))])
    st.subheader("Riwayat terbaru")
    st.dataframe(i.sort_values("tanggal_pemeriksaan", ascending=False).head(15)[["tanggal_pemeriksaan", "id_peserta", "nama", "usia_kehamilan_minggu", "risiko", "jadwal_berikutnya", "hpl"]], hide_index=True, width="stretch")

# ---------- LAPORAN (dropdown variabel) ----------
VAR = {"Balita": {"cat": {"Status gizi": "status_gizi", "Jenis kelamin": "jenis_kelamin", "Dusun": "alamat_dusun", "Imunisasi": "imunisasi", "Vitamin A": "vitamin_a"},
                  "num": {"Berat badan (kg)": "berat_kg", "Tinggi badan (cm)": "tinggi_cm", "Lingkar kepala (cm)": "lingkar_kepala_cm", "Z-score BB/U": "z_bb_u", "Z-score TB/U": "z_tb_u", "Usia (bulan)": "usia_bulan"}},
       "Ibu Hamil": {"cat": {"Tingkat risiko": "risiko", "Status KEK": "status_kek", "Status anemia": "status_anemia", "Hipertensi": "status_hipertensi", "Tablet Fe": "tablet_fe", "Trimester": "trimester", "Dusun": "alamat_dusun"},
                     "num": {"Berat badan (kg)": "berat_kg", "LILA (cm)": "lila_cm", "Hb (g/dL)": "hb_gdl", "Tekanan sistol": "sistol", "Tekanan diastol": "diastol", "Usia kehamilan (minggu)": "usia_kehamilan_minggu"}}}

def kader_laporan(p, b, i):
    header("📊 Laporan Bulanan", "Pilih periode & variabel, lalu unduh atau simpan laporan")
    c1, c2, c3, c4 = st.columns(4)
    kel = c1.selectbox("Kelompok", ["Balita", "Ibu Hamil"]); tahun = c2.selectbox("Tahun", sorted(set(b.tahun) | set(i.tahun), reverse=True))
    bln = c3.selectbox("Bulan", [0] + list(range(1, 13)), index=TODAY.month, format_func=lambda x: "Semua bulan" if x == 0 else BULAN[x - 1])
    opts = {**VAR[kel]["cat"], **VAR[kel]["num"]}; vlabel = c4.selectbox("Variabel laporan", list(opts))
    grp_opts = {"Tanpa pengelompokan": None, "Dusun": "alamat_dusun"} | ({"Jenis kelamin": "jenis_kelamin"} if kel == "Balita" else {"Trimester": "trimester"})
    glabel = st.selectbox("Pecah berdasarkan", list(grp_opts)); grp = grp_opts[glabel]
    df = (b if kel == "Balita" else i); df = df[df.tahun == tahun]; df = df if bln == 0 else df[df.bulan == bln]
    col = opts[vlabel]; is_num = col in VAR[kel]["num"].values()
    if grp == col: grp = None
    if df.empty: st.info("Tidak ada data pada periode ini."); return
    kpi(st.columns(4), [("Jumlah pemeriksaan", len(df)), ("Peserta unik", df.id_peserta.nunique()), ("Periode", "Semua" if bln == 0 else BULAN[bln - 1]), ("Variabel", vlabel)])
    if is_num:
        enc = dict(x=alt.X(f"{col}:Q", bin=alt.Bin(maxbins=15), title=vlabel), y=alt.Y("count()", title="Jumlah"))
        if grp: enc["color"] = alt.Color(f"{grp}:N", legend=alt.Legend(orient="bottom"))
        a, bx = st.columns(2)
        plot(a, alt.Chart(df).mark_bar().encode(**enc).properties(title=f"Distribusi {vlabel}", height=280))
        g = grp or "periode"
        plot(bx, alt.Chart(df).mark_boxplot(extent="min-max").encode(x=alt.X(f"{g}:N", title=None), y=alt.Y(f"{col}:Q", scale=alt.Scale(zero=False), title=vlabel), color=alt.Color(f"{g}:N", legend=None)).properties(title=f"Sebaran {vlabel}" + (f" per {glabel}" if grp else " per bulan"), height=280))
        tr = df.groupby("periode")[col].mean().reset_index()
        plot(st, alt.Chart(tr).mark_line(point=True, color=GREEN, strokeWidth=3).encode(x=alt.X("periode:N", title=None), y=alt.Y(f"{col}:Q", scale=alt.Scale(zero=False), title=f"Rata-rata {vlabel}")).properties(title=f"Tren rata-rata {vlabel}", height=220))
        summ = df.groupby(grp)[col].describe().round(2).reset_index() if grp else df[col].describe().round(2).to_frame().T
    else:
        a, bx = st.columns(2)
        plot(a, bars(df, col, f"{vlabel}" + (f" per {glabel}" if grp else ""), grp))
        a2 = df.groupby(["periode", col]).size().reset_index(name="Jumlah")
        plot(bx, alt.Chart(a2).mark_line(point=True).encode(x=alt.X("periode:N", title=None), y="Jumlah:Q", color=colr(a2, col, ""), tooltip=["periode", col, "Jumlah"]).properties(title=f"Tren {vlabel} per bulan", height=250))
        summ = pd.crosstab(df[col], df[grp] if grp else "Jumlah", margins=True, margins_name="Total").reset_index()
    st.subheader("Ringkasan data"); st.dataframe(summ, hide_index=True, width="stretch")
    pr = f"{tahun}-{bln:02d}" if bln else str(tahun)
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ CSV", df.to_csv(index=False).encode("utf-8-sig"), f"laporan_{kel}_{pr}.csv", "text/csv", width="stretch")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, sheet_name="Data", index=False); summ.to_excel(w, sheet_name="Ringkasan", index=False)
    d2.download_button("⬇️ Excel", buf.getvalue(), f"laporan_{kel}_{pr}.xlsx", width="stretch")
    if d3.button("💾 Simpan ke database laporan", type="primary", width="stretch"):
        lap = load("laporan")
        row = dict(id_laporan=f"LAP{len(lap) + 1:03d}", periode=pr, kelompok=kel, variabel=vlabel, dibuat_oleh=st.session_state["user"]["nama"], tanggal_dibuat=TODAY, status="Siap diserahkan", tanggal_serah="")
        save(pd.concat([lap, pd.DataFrame([row])]), "laporan"); st.success(f"Laporan {row['id_laporan']} tersimpan. Buka menu Riwayat Laporan untuk menyerahkan ke Puskesmas.")

def kader_riwayat_laporan(*_):
    header("🗂️ Riwayat Laporan", "Laporan yang sudah dibuat dan status penyerahan ke Puskesmas"); lap = load("laporan")
    if lap.empty: st.info("Belum ada laporan tersimpan."); return
    st.dataframe(lap, hide_index=True, width="stretch")
    pend = lap[lap.status != "Diserahkan ke Puskesmas"]
    if len(pend):
        s = st.selectbox("Pilih laporan untuk diserahkan (langkah 21)", pend.id_laporan)
        if st.button("📤 Serahkan ke Puskesmas", type="primary"):
            lap.loc[lap.id_laporan == s, ["status", "tanggal_serah"]] = ["Diserahkan ke Puskesmas", TODAY.isoformat()]; save(lap, "laporan"); st.rerun()

# ---------- IBU HAMIL ----------
def ibu_dash(p, b, i, u):
    h = i[i.id_peserta == u["id_peserta"]].sort_values("tanggal_pemeriksaan"); me = p[p.id_peserta == u["id_peserta"]].iloc[0]
    header(f"🏠 Selamat datang, {u['nama']}", "Pantau kesehatan dan jadwal kehamilan Anda di sini")
    if h.empty: st.info("Belum ada pemeriksaan tercatat."); return
    l = h.iloc[-1]
    kpi(st.columns(5), [("Usia kehamilan", f"{int(l.usia_kehamilan_minggu)} mgg", l.trimester), ("Perkiraan persalinan (HPL)", fmt(l.hpl)), ("Tingkat risiko", l.risiko), ("Kontrol berikutnya", fmt(l.jadwal_berikutnya)), ("Tablet Fe", l.tablet_fe)])
    (st.error if l.risiko == "Risiko tinggi" else st.warning if l.risiko == "Perlu pemantauan" else st.success)(f"Status terakhir: **{l.risiko}** — KEK: {l.status_kek}, Anemia: {l.status_anemia}, Tekanan darah: {l.status_hipertensi}. Hasil ini bukan diagnosis; konsultasikan dengan bidan.")
    a, c = st.columns(2)
    plot(a, trend(h, "usia_kehamilan_minggu", ["berat_kg"], "Berat badan per usia kehamilan (kg)", ytitle="kg"))
    plot(c, trend(h, "usia_kehamilan_minggu", ["sistol", "diastol"], "Tekanan darah (garis merah = batas sistol 140)", rule=140, ytitle="mmHg"))
    d, e = st.columns(2)
    plot(d, trend(h, "usia_kehamilan_minggu", ["hb_gdl"], "Hemoglobin (garis merah = batas anemia 11 g/dL)", rule=11, ytitle="g/dL"))
    plot(e, trend(h, "usia_kehamilan_minggu", ["lila_cm"], "LILA (garis merah = batas KEK 23,5 cm)", rule=23.5, ytitle="cm"))

def ibu_riwayat(p, b, i, u):
    header("📖 Riwayat KIA Digital", "Catatan seluruh kunjungan pemeriksaan kehamilan Anda")
    h = i[i.id_peserta == u["id_peserta"]].sort_values("tanggal_pemeriksaan", ascending=False)
    st.dataframe(h.drop(columns=["nama", "alamat_dusun", "no_hp", "bulan", "tahun", "periode", "id_peserta"]), hide_index=True, width="stretch")
    st.download_button("⬇️ Unduh riwayat (CSV)", h.to_csv(index=False).encode("utf-8-sig"), "riwayat_kia.csv", "text/csv")

# ---------- ORANG TUA ----------
def _anak(p, b, u):
    kids = p[p.id_orang_tua == u["id_peserta"]]
    k = st.selectbox("Pilih anak", kids.id_peserta, format_func=lambda x: f"{kids.set_index('id_peserta').nama[x]} ({x})") if len(kids) > 1 else kids.id_peserta.iloc[0]
    return kids.set_index("id_peserta").loc[k], b[b.id_peserta == k].sort_values("tanggal_pemeriksaan")

def ortu_dash(p, b, i, u):
    header(f"🏠 Selamat datang, {u['nama']}", "Pantau tumbuh kembang si kecil dan jadwal kunjungan berikutnya"); kid, h = _anak(p, b, u)
    st.subheader(f"👶 {kid.nama} — {kid.jenis_kelamin}")
    if h.empty: st.info("Belum ada pemeriksaan tercatat."); return
    l = h.iloc[-1]
    kpi(st.columns(5), [("Usia", f"{l.usia_bulan:.0f} bln"), ("Berat / Tinggi", f"{l.berat_kg} kg / {l.tinggi_cm} cm"), ("Status gizi", l.status_gizi), ("Imunisasi", l.imunisasi), ("Jadwal berikutnya", fmt(l.jadwal_berikutnya))])
    msg = {"Normal": "Pertumbuhan anak sesuai kurva. Pertahankan pola makan bergizi dan kunjungan rutin.", "Stunting": "Tinggi badan di bawah kurva normal. Segera konsultasikan ke kader/bidan/Puskesmas.",
           "Gizi kurang": "Berat badan di bawah kurva normal. Konsultasikan menu MP-ASI ke kader/bidan.", "Risiko gizi lebih": "Berat badan di atas kurva normal. Konsultasikan pola makan ke kader/bidan."}[l.status_gizi]
    (st.success if l.status_gizi == "Normal" else st.warning)(msg + " (Hasil demo, bukan diagnosis.)")
    a, c = st.columns(2)
    plot(a, kms(h, kid.jenis_kelamin, "bb", "berat_kg", "Grafik KMS — Berat badan menurut umur", "Berat (kg)"))
    plot(c, kms(h, kid.jenis_kelamin, "tb", "tinggi_cm", "Grafik — Tinggi badan menurut umur", "Tinggi (cm)"))
    st.caption("Area hijau = rentang normal (−2 s.d. +2 SD), garis putus-putus = median, garis biru = anak Anda.")

def ortu_grafik(p, b, i, u):
    header("📈 Grafik Pertumbuhan", "Lingkar kepala, Z-score, dan riwayat pemeriksaan anak"); kid, h = _anak(p, b, u)
    if h.empty: st.info("Belum ada data."); return
    plot(st, trend(h, "tanggal_pemeriksaan", ["lingkar_kepala_cm"], "Lingkar kepala (cm)", ytitle="cm"))
    plot(st, trend(h, "tanggal_pemeriksaan", ["z_bb_u", "z_tb_u"], "Z-score BB/U & TB/U (garis merah = −2)", rule=-2, ytitle="Z-score"))
    st.dataframe(h[["tanggal_pemeriksaan", "usia_bulan", "berat_kg", "tinggi_cm", "lingkar_kepala_cm", "vitamin_a", "imunisasi", "status_gizi", "catatan"]].sort_values("tanggal_pemeriksaan", ascending=False), hide_index=True, width="stretch")

# ---------- main ----------
if "user" not in st.session_state:
    css(False); login_page(); st.stop()
css(True)
u = st.session_state["user"]; role = u["role"]
st.sidebar.markdown(f'<div class="side-brand"><b>🌸 Posyandu Digital</b><br><small>👤 {u["nama"]}</small><br><span class="chip">{role}</span></div>', unsafe_allow_html=True)
st.sidebar.divider()
if st.session_state.get("page") not in MENU[role]: st.session_state["page"] = MENU[role][0]
for m in MENU[role]:
    if st.sidebar.button(m, key="nav_" + m, type="primary" if st.session_state["page"] == m else "secondary", width="stretch"):
        st.session_state["page"] = m; st.rerun()
page = st.session_state["page"]
st.sidebar.divider()
if st.sidebar.button("🚪 Keluar", key="logout", width="stretch"): st.session_state.clear(); st.rerun()
st.sidebar.caption("Data sintetis untuk demo, bukan data kesehatan nyata.")
p, b, i = data()
PAGES = {"Kader": {"🏠 Dashboard": kader_dash, "👥 Data Peserta": kader_peserta, "🧒 Pemeriksaan Balita": kader_balita, "🤰 Pemeriksaan Ibu Hamil": kader_ibu,
                   "📊 Laporan Bulanan": kader_laporan, "🗂️ Riwayat Laporan": kader_riwayat_laporan},
         "Ibu Hamil": {"🏠 Dashboard": ibu_dash, "📖 Riwayat KIA Digital": ibu_riwayat},
         "Orang Tua Balita": {"🏠 Dashboard": ortu_dash, "📈 Grafik Pertumbuhan": ortu_grafik}}
fn = PAGES[role][page]
fn(p, b, i) if role == "Kader" else fn(p, b, i, u)
