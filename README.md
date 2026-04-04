# Sistem Pengajuan Dokumen

Aplikasi web berbasis FastAPI untuk pengajuan dokumen oleh `service_user` dan pengelolaan dokumen oleh petugas internal dengan role `monitoring`, `admin`, dan `super_admin`.

## Fitur Inti

- Registrasi dan login Pengguna Jasa
- Login Petugas internal
- Dashboard pengguna untuk upload dan pantau dokumen
- Dashboard admin/monitoring untuk verifikasi dokumen
- Upload file hasil dokumen oleh petugas
- Pembuatan tanda terima PDF otomatis
- Audit log aktivitas utama

## Teknologi

- FastAPI
- SQLAlchemy
- Jinja2
- SQLite
- ReportLab
- Session-based authentication

## Menjalankan Proyek

1. Install dependency:

```powershell
pip install -r requirements.txt
```

2. Jalankan server:

```powershell
python -m uvicorn app.main:app --reload --port 8010
```

3. Buka aplikasi:

`http://127.0.0.1:8010`

## Konfigurasi Opsional

Variabel environment yang didukung:

- `DATABASE_PATH`
- `SESSION_SECRET_KEY`
- `SESSION_HTTPS_ONLY`
- `SERVICE_USER_AUTO_APPROVE`

## Deploy ke Railway

Project ini sudah menyertakan `Procfile` dan `railway.json` agar Railway bisa langsung menjalankan FastAPI dengan `uvicorn`.

Environment variable yang disarankan di Railway:

- `SESSION_SECRET_KEY`
- `SESSION_HTTPS_ONLY=true`
- `SERVICE_USER_AUTO_APPROVE=false`

## Kelola Akun Petugas

Contoh perintah untuk membuat akun petugas:

```powershell
python -m app.manage_users create --username petugas1 --password Password123 --role monitoring --status ACTIVE
```

Lihat panduan lengkap di [README_KELOLA_AKUN_PETUGAS.md](README_KELOLA_AKUN_PETUGAS.md) dan alur demo di [MANUAL_DEMO.md](MANUAL_DEMO.md).
