-- EnterpriseMind AI — Migration 002
-- Sederhanakan role menjadi HANYA 'admin' dan 'user'.
-- Role 'analyst' dan 'viewer' dihapus (tidak ada perilaku khusus di sistem).
-- Aman dijalankan ulang (idempotent). Jalankan:
--   psql -U postgres -d enterprisemind -f app/db/migrations/002_roles_two_only.sql

-- Migrasi data: user lama ber-role analyst/viewer diubah jadi 'user'
UPDATE users SET role = 'user', updated_at = NOW() WHERE role IN ('analyst', 'viewer');

-- Ganti constraint role
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'user'));
