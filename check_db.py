from app.db import get_db_context
from app.db.models import ScanHistory
from sqlalchemy import desc

with get_db_context() as db:
    records = db.query(ScanHistory).order_by(desc(ScanHistory.id)).limit(10).all()
    print("\n=== 扫描历史记录 ===")
    for r in records:
        print(f"ID: {r.id}")
        print(f"  Batch ID: {r.batch_id}")
        print(f"  Type: {r.scan_type}")
        print(f"  Total: {r.total_files}")
        print(f"  New: {r.new_files}")
        print(f"  Updated: {r.updated_files}")
        print(f"  Skipped: {r.skipped_files}")
        print(f"  Failed: {r.failed_files}")
        print(f"  Path: {r.target_path}")
        print(f"  Started: {r.started_at}")
        print(f"  Completed: {r.completed_at}")
        print()
