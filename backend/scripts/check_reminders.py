import sys
sys.path.insert(0, '/app')
import asyncio
from datetime import datetime
from sqlalchemy import select
from app.db import async_session_maker
from app.models import Reminder

async def check():
    async with async_session_maker() as db:
        result = await db.execute(
            select(Reminder)
            .where(Reminder.is_enabled == True)
            .order_by(Reminder.next_run_at)
        )
        reminders = result.scalars().all()
        
        print('\n' + '='*70)
        print('ACTIVE REMINDERS')
        print('='*70)
        
        now = datetime.utcnow()
        for r in reminders:
            if r.next_run_at:
                diff_secs = (r.next_run_at - now).total_seconds()
                mins = int(diff_secs / 60)
                status = 'OVERDUE' if diff_secs < 0 else f'{mins} min'
                print(f'\n{r.title}')
                print(f'  Type: {r.type} | Channel: {r.channel}')
                print(f'  Next: {r.next_run_at.strftime("%H:%M UTC")} ({status})')
        
        print('\n' + '='*70 + '\n')

asyncio.run(check())
