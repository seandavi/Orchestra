#/usr/bin/env python
import workshop_orchestra.kube_utils as k
import workshop_orchestra.db as db
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    query = f"""
    with s as (select instance_id, status, timestamp, row_number() over (partition by instance_id order by timestamp desc) as rk
    from instance_events) select s.*,instances.name, current_timestamp-s.timestamp as age
    from s join instances on instances.id=s.instance_id where s.rk=1 and current_timestamp-s.timestamp > interval '8 hours' and status!='DELETED'"""
    
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
