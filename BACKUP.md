# Backup & Restore Guide — EnterpriseMind AI

## Backups

### 1. Supabase Database
```bash
# Via Supabase Dashboard → Database → Backups
# Atau via pg_dump:
pg_dump --no-owner --schema=public -d postgresql://user:pass@host:5432/postgres > backup_$(date +%Y%m%d).sql
```

### 2. ChromaDB Vector Store
```bash
# Docker volume backup:
docker run --rm -v enterprisemind_chroma_data:/data -v $(pwd):/backup alpine tar czf /backup/chroma_backup_$(date +%Y%m%d).tar.gz -C /data .
```

### 3. File Uploads
```bash
# Docker volume backup:
docker run --rm -v enterprisemind_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_backup_$(date +%Y%m%d).tar.gz -C /data .
```

## Restore

### Supabase Database
```bash
# Via Supabase Dashboard → Database → Backups → Restore
psql postgresql://user:pass@host:5432/postgres < backup_20260706.sql
```

### ChromaDB Vector Store
```bash
docker run --rm -v enterprisemind_chroma_data:/data -v $(pwd):/backup alpine tar xzf /backup/chroma_backup_20260706.tar.gz -C /data
docker compose restart chroma
```

### File Uploads
```bash
docker run --rm -v enterprisemind_uploads:/data -v $(pwd):/backup alpine tar xzf /backup/uploads_backup_20260706.tar.gz -C /data
```

## Automation
- Set up cron job untuk backup harian
- Simpan backup ke S3 / Supabase Storage / external drive
- Test restore setiap 1 bulan
