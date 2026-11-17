#!/usr/bin/env sh
set -e

echo "⏳ Ждём Postgres..."
python - <<'PY'
import asyncio, os, sys
import asyncpg

async def wait():
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    for i in range(30):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print("✅ Postgres готов")
            return
        except Exception as e:
            print(f"  ... {i+1}/30: {e}")
            await asyncio.sleep(1)
    sys.exit("❌ Postgres не поднялся за 30 секунд")

asyncio.run(wait())
PY

echo "📦 Применяем миграции..."
alembic upgrade head

echo "🚀 Запускаем uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 $UVICORN_ARGS