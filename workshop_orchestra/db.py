import datetime

import sqlalchemy

from databases import Database
from sqlalchemy import func, desc, and_

from .config import config

metadata = sqlalchemy.MetaData()

instance_events = sqlalchemy.Table(
    "instance_events",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.Text, index=True),
    sqlalchemy.Column("container", sqlalchemy.Text),
    sqlalchemy.Column("email", sqlalchemy.Text, index=True),
    sqlalchemy.Column("status", sqlalchemy.Text),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime)
)

workshops = sqlalchemy.Table(
    "workshops",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("description", sqlalchemy.Text),
    sqlalchemy.Column("url", sqlalchemy.Text),
    sqlalchemy.Column("container", sqlalchemy.Text)
)


database = Database(config('SQLALCHEMY_URI'))

async def connect():
    if database.is_connected:
        return
    await database.connect()

async def get_outdated_workshops(interval = '4 hours'):
    query = f"""with s as (select name, status, timestamp, row_number() over (partition by name order by timestamp desc) as rk from instance_events) select s.*, current_timestamp-s.timestamp as age from s whe
 re s.rk=1 and current_timestamp-s.timestamp > interval '{interval}' and status!='DELETED'"""
    await db.connect()
    res = await database.fetch_all(query)


async def get_existing_workshop(email, container):
    await connect()
    i = instance_events
    query = i.select().where(and_(i.c.email==email, i.c.container==container)).order_by(desc('timestamp'))
    res = await database.fetch_all(query)
    return res

async def get_workshops(id=None):
    await connect()
    if(id is None):
        res = await database.fetch_all('select * from workshops')
        return res
    res = await database.fetch_one(f'select * from workshops where id = {id}')
    return(res)

async def create_new_workshop(description: str, container: str, url: str=None):
    await connect()
    sql = workshops.insert().values(
        description = description,
        container = container,
        url = url
    )
    res = await database.execute(sql)
    return res

async def add_instance(name, email, container):
    await connect()
    query = instance_events.insert().values(
        name=name, email=email, container=container,
        status = 'CREATED', timestamp=datetime.datetime.utcnow())
    res = await database.execute(query)
    return True

async def delete_instance(name):
    await connect()
    query = instance_events.insert().values(
        name=name, status="DELETED", timestamp=datetime.datetime.utcnow()
    )
    res = await database.execute(query)
    return True


if __name__ == '__main__':
    engine = sqlalchemy.create_engine(config('SQLALCHEMY_URI'))
    metadata.create_all(engine)
