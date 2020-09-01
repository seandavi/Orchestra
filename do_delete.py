#/usr/bin/env python
import workshop_orchestra.kube_utils as k
import workshop_orchestra.db as db
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    query = f"""with s as (select name, status, timestamp, row_number() over (partition by name order by timestamp desc) as rk from instance_events) select s.*, current_timestamp-s.timestamp as age from s where s.rk=1 and current_timestamp-s.timestamp > interval '8 hours' and status!='DELETED'"""
    await db.connect()
    res = await db.database.fetch_all(query)
    for i in res:
        try:
            await k.delete_workshop(i.get('name'))
            logging.info(f"{i.get('name')} DELETED")
        except:
            logging.info(f"{i.get('name')} PROBLEMATIC")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
