"""
Fault: DB connection pool exhaustion
Symptoms: API latency spike, 500 errors
PNOG traces: postgres nodes weight spikes → app nodes respond → traces to pool config
"""
import asyncio
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://pnog:pnog_secret@localhost:5432/pnog_db")

async def exhaust():
    print("[FAULT] Exhausting DB connection pool...")
    connections = []
    try:
        for i in range(20):
            conn = await asyncpg.connect(DB_URL)
            connections.append(conn)
            print(f"  opened connection {i+1}")
            await asyncio.sleep(0.2)
    except Exception as e:
        print(f"  pool exhausted at connection {len(connections)}: {e}")

    print(f"[FAULT] Holding {len(connections)} connections for 15 seconds...")
    await asyncio.sleep(15)

    for conn in connections:
        await conn.close()
    print("[FAULT] Connections released. Watch PNOG graph normalize.")

asyncio.run(exhaust())
