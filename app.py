from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import sqlite3
import csv
import io
from datetime import datetime, date
import json

app = Flask(__name__)
DB = 'inventaris.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS barang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kode TEXT UNIQUE NOT NULL,
        nama TEXT NOT NULL,
        kategori TEXT NOT NULL,
        stok INTEGER DEFAULT 0,
        stok_min INTEGER DEFAULT 5,
        satuan TEXT DEFAULT 'pcs',
        lokasi TEXT,
        deskripsi TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS peminjaman (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barang_id INTEGER NOT NULL,
        peminjam TEXT NOT NULL,
        divisi TEXT,
        jumlah INTEGER NOT NULL,
        tanggal_pinjam TEXT NOT NULL,
        tanggal_kembali TEXT,
        status TEXT DEFAULT 'dipinjam',
        keterangan TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (barang_id) REFERENCES barang(id)
    )''')
    # Seed data
    c.execute("SELECT COUNT(*) FROM barang")
    if c.fetchone()[0] == 0:
        seed_data = [
            ('BRG-001','Laptop Dell Latitude','Elektronik',15,3,'unit','Gudang A','Laptop bisnis'),
            ('BRG-002','Mouse Wireless','Elektronik',42,10,'pcs','Gudang A','Mouse nirkabel'),
            ('BRG-003','Keyboard Mekanikal','Elektronik',28,8,'pcs','Gudang A','Keyboard gaming'),
            ('BRG-004','Meja Kantor','Furnitur',12,2,'unit','Gudang B','Meja kerja standar'),
            ('BRG-005','Kursi Ergonomis','Furnitur',20,5,'unit','Gudang B','Kursi ergonomis'),
            ('BRG-006','Proyektor Epson','Elektronik',6,2,'unit','Gudang C','Proyektor 4K'),
            ('BRG-007','Kertas A4','ATK',150,50,'rim','Gudang D','Kertas HVS 80gr'),
            ('BRG-008','Spidol Whiteboard','ATK',85,20,'pcs','Gudang D','Spidol berbagai warna'),
            ('BRG-009','Flashdisk 64GB','Elektronik',35,10,'pcs','Gudang A','USB 3.0'),
            ('BRG-010','Kamera DSLR','Elektronik',4,1,'unit','Gudang C','Canon EOS'),
        ]
        c.executemany("INSERT INTO barang (kode,nama,kategori,stok,stok_min,satuan,lokasi,deskripsi) VALUES (?,?,?,?,?,?,?,?)", seed_data)
        pinjam_data = [
            (1,'Budi Santoso','IT',2,'2025-01-10','2025-01-17','dikembalikan',''),
            (2,'Sari Dewi','HR',5,'2025-02-01',None,'dipinjam','Untuk event'),
            (3,'Ahmad Fauzi','Finance',1,'2025-02-15','2025-02-22','dikembalikan',''),
            (6,'Rina Putri','Marketing',1,'2025-03-01',None,'dipinjam','Presentasi klien'),
            (7,'Deni Kurniawan','Operasional',10,'2025-03-05','2025-03-10','dikembalikan',''),
            (1,'Maya Sari','IT',1,'2025-03-10',None,'dipinjam','WFH'),
            (9,'Hendra Wijaya','Sales',3,'2025-03-12',None,'dipinjam','Tugas lapangan'),
        ]
        c.executemany("INSERT INTO peminjaman (barang_id,peminjam,divisi,jumlah,tanggal_pinjam,tanggal_kembali,status,keterangan) VALUES (?,?,?,?,?,?,?,?)", pinjam_data)
    conn.commit()
    conn.close()

# ─── DASHBOARD ────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    conn = get_db()
    total_barang = conn.execute("SELECT COUNT(*) FROM barang").fetchone()[0]
    total_stok = conn.execute("SELECT SUM(stok) FROM barang").fetchone()[0] or 0
    dipinjam = conn.execute("SELECT COUNT(*) FROM peminjaman WHERE status='dipinjam'").fetchone()[0]
    stok_rendah = conn.execute("SELECT COUNT(*) FROM barang WHERE stok <= stok_min").fetchone()[0]

    kategori_data = conn.execute("""
        SELECT kategori, COUNT(*) as jumlah, SUM(stok) as total_stok
        FROM barang GROUP BY kategori ORDER BY jumlah DESC
    """).fetchall()

    stok_rendah_list = conn.execute("""
        SELECT nama, kode, stok, stok_min, kategori
        FROM barang WHERE stok <= stok_min ORDER BY stok ASC LIMIT 5
    """).fetchall()

    recent_pinjam = conn.execute("""
        SELECT p.*, b.nama as nama_barang, b.kode
        FROM peminjaman p JOIN barang b ON p.barang_id=b.id
        ORDER BY p.created_at DESC LIMIT 5
    """).fetchall()

    top_items = conn.execute("""
        SELECT b.nama, b.kode, COUNT(p.id) as total_pinjam, SUM(p.jumlah) as total_unit
        FROM peminjaman p JOIN barang b ON p.barang_id=b.id
        GROUP BY b.id ORDER BY total_pinjam DESC LIMIT 5
    """).fetchall()

    conn.close()
    return render_template('dashboard.html',
        total_barang=total_barang, total_stok=total_stok,
        dipinjam=dipinjam, stok_rendah=stok_rendah,
        kategori_data=kategori_data, stok_rendah_list=stok_rendah_list,
        recent_pinjam=recent_pinjam, top_items=top_items)

# ─── DATA BARANG ──────────────────────────────────────────────────────────────
@app.route('/barang')
def barang():
    q = request.args.get('q', '')
    kat = request.args.get('kategori', '')
    conn = get_db()
    query = "SELECT * FROM barang WHERE 1=1"
    params = []
    if q:
        query += " AND (nama LIKE ? OR kode LIKE ?)"
        params += [f'%{q}%', f'%{q}%']
    if kat:
        query += " AND kategori=?"
        params.append(kat)
    query += " ORDER BY created_at DESC"
    items = conn.execute(query, params).fetchall()
    kategori_list = conn.execute("SELECT DISTINCT kategori FROM barang ORDER BY kategori").fetchall()
    conn.close()
    return render_template('barang.html', items=items, kategori_list=kategori_list, q=q, kat=kat)

@app.route('/barang/tambah', methods=['GET','POST'])
def tambah_barang():
    if request.method == 'POST':
        d = request.form
        conn = get_db()
        try:
            conn.execute("""INSERT INTO barang (kode,nama,kategori,stok,stok_min,satuan,lokasi,deskripsi)
                VALUES (?,?,?,?,?,?,?,?)""",
                (d['kode'], d['nama'], d['kategori'], int(d['stok']),
                 int(d['stok_min']), d['satuan'], d['lokasi'], d['deskripsi']))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('form_barang.html', error='Kode barang sudah ada!', data=d, mode='tambah')
        conn.close()
        return redirect(url_for('barang'))
    return render_template('form_barang.html', data={}, mode='tambah')

@app.route('/barang/edit/<int:id>', methods=['GET','POST'])
def edit_barang(id):
    conn = get_db()
    if request.method == 'POST':
        d = request.form
        conn.execute("""UPDATE barang SET kode=?,nama=?,kategori=?,stok=?,stok_min=?,
            satuan=?,lokasi=?,deskripsi=? WHERE id=?""",
            (d['kode'],d['nama'],d['kategori'],int(d['stok']),int(d['stok_min']),
             d['satuan'],d['lokasi'],d['deskripsi'],id))
        conn.commit()
        conn.close()
        return redirect(url_for('barang'))
    item = conn.execute("SELECT * FROM barang WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('form_barang.html', data=item, mode='edit')

@app.route('/barang/hapus/<int:id>', methods=['POST'])
def hapus_barang(id):
    conn = get_db()
    conn.execute("DELETE FROM barang WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('barang'))

# ─── PEMINJAMAN ───────────────────────────────────────────────────────────────
@app.route('/peminjaman')
def peminjaman():
    status = request.args.get('status', '')
    q = request.args.get('q', '')
    conn = get_db()
    query = """SELECT p.*, b.nama as nama_barang, b.kode, b.satuan
               FROM peminjaman p JOIN barang b ON p.barang_id=b.id WHERE 1=1"""
    params = []
    if status:
        query += " AND p.status=?"
        params.append(status)
    if q:
        query += " AND (p.peminjam LIKE ? OR b.nama LIKE ?)"
        params += [f'%{q}%', f'%{q}%']
    query += " ORDER BY p.created_at DESC"
    records = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('peminjaman.html', records=records, status=status, q=q)

@app.route('/peminjaman/tambah', methods=['GET','POST'])
def tambah_peminjaman():
    conn = get_db()
    if request.method == 'POST':
        d = request.form
        barang_id = int(d['barang_id'])
        jumlah = int(d['jumlah'])
        item = conn.execute("SELECT * FROM barang WHERE id=?", (barang_id,)).fetchone()
        if item['stok'] < jumlah:
            barang_list = conn.execute("SELECT id,kode,nama,stok,satuan FROM barang ORDER BY nama").fetchall()
            conn.close()
            return render_template('form_peminjaman.html', barang_list=barang_list, error=f'Stok tidak cukup! Tersedia: {item["stok"]}', data=d)
        conn.execute("UPDATE barang SET stok=stok-? WHERE id=?", (jumlah, barang_id))
        conn.execute("""INSERT INTO peminjaman (barang_id,peminjam,divisi,jumlah,tanggal_pinjam,keterangan)
            VALUES (?,?,?,?,?,?)""", (barang_id, d['peminjam'], d['divisi'], jumlah, d['tanggal_pinjam'], d['keterangan']))
        conn.commit()
        conn.close()
        return redirect(url_for('peminjaman'))
    barang_list = conn.execute("SELECT id,kode,nama,stok,satuan FROM barang ORDER BY nama").fetchall()
    conn.close()
    return render_template('form_peminjaman.html', barang_list=barang_list, data={'tanggal_pinjam': date.today().isoformat()})

@app.route('/peminjaman/kembalikan/<int:id>', methods=['POST'])
def kembalikan(id):
    conn = get_db()
    p = conn.execute("SELECT * FROM peminjaman WHERE id=?", (id,)).fetchone()
    if p and p['status'] == 'dipinjam':
        conn.execute("UPDATE peminjaman SET status='dikembalikan', tanggal_kembali=? WHERE id=?",
                     (date.today().isoformat(), id))
        conn.execute("UPDATE barang SET stok=stok+? WHERE id=?", (p['jumlah'], p['barang_id']))
        conn.commit()
    conn.close()
    return redirect(url_for('peminjaman'))

# ─── EXPORT ───────────────────────────────────────────────────────────────────
@app.route('/export/barang')
def export_barang():
    conn = get_db()
    rows = conn.execute("SELECT kode,nama,kategori,stok,stok_min,satuan,lokasi,deskripsi,created_at FROM barang ORDER BY nama").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Kode','Nama Barang','Kategori','Stok','Stok Minimum','Satuan','Lokasi','Deskripsi','Tanggal Input'])
    for r in rows:
        writer.writerow(list(r))
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=laporan_barang_{date.today()}.csv'
    return response

@app.route('/export/peminjaman')
def export_peminjaman():
    conn = get_db()
    rows = conn.execute("""SELECT b.kode, b.nama, p.peminjam, p.divisi, p.jumlah, b.satuan,
        p.tanggal_pinjam, p.tanggal_kembali, p.status, p.keterangan
        FROM peminjaman p JOIN barang b ON p.barang_id=b.id ORDER BY p.tanggal_pinjam DESC""").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Kode Barang','Nama Barang','Peminjam','Divisi','Jumlah','Satuan','Tgl Pinjam','Tgl Kembali','Status','Keterangan'])
    for r in rows:
        writer.writerow(list(r))
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=laporan_peminjaman_{date.today()}.csv'
    return response

@app.route('/api/stok-chart')
def stok_chart():
    conn = get_db()
    data = conn.execute("""SELECT kategori, SUM(stok) as total FROM barang GROUP BY kategori""").fetchall()
    conn.close()
    return jsonify([{'kategori': r['kategori'], 'total': r['total']} for r in data])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
