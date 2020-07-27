from .config import config
from databases import Database
import asyncio
import datetime
from datetime import timezone

import sqlalchemy


metadata = sqlalchemy.MetaData()

instance_events = sqlalchemy.Table(
    "instance_events",
    metadata,
    sqlalchemy.Column("name", sqlalchemy.Text, primary_key=True),
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

async def get_workshops(id=None):
    await connect()
    if(id is None):
        res = await database.fetch_all('select * from workshops')
        return res
    res = await database.fetch_one(f'select * from workshops where id = {id}')
    return(res)

async def add_instance(name, email, container):
    await connect()
    query = instance_events.insert().values(
        name=name, email=email, container=container,
        status = 'CREATED', timestamp=datetime.datetime.utcnow())
    res = await database.execute(query)
    return True

if __name__ == '__main__':
    engine = sqlalchemy.create_engine(config('SQLALCHEMY_URI'))
    metadata.create_all(engine)
