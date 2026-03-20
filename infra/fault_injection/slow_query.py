"""
Fault: Slow query cascading to frontend timeout
Layers: L3 → L1 → L0 → L6
PNOG traces: DBQuery weight spikes → ServiceCall → NetworkRequest → FrontendError
"""
import asyncio
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://pnog:pnog_secret@localhost:5432/pnog_db")

async def inject():
    print("[FAULT] Injecting slow query via pg_sleep...")
    conn = await asyncpg.connect(DB_URL)
    try:
        # This will hold a lock and cause downstream timeouts
        print("  Running SELECT pg_sleep(10)...")
        await asyncio.wait_for(conn.fetch("SELECT pg_sleep(10)"), timeout=12)
        print("  Slow query completed. Check PNOG for cross-layer cascade.")
    except asyncio.TimeoutError:
        print("  Query timed out — expected behaviour. PNOG should show L3→L1→L0 cascade.")
    finally:
        await conn.close()

asyncio.run(inject())
