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

workshop = sqlalchemy.Table(
    "workshops",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("description", sqlalchemy.Text),
    sqlalchemy.Column("url", sqlalchemy.Text),
    sqlalchemy.Column("container", sqlalchemy.Text),
    sqlalchemy.Column("port", sqlalchemy.Integer,
                      comment="The port on which the container listens"),
    sqlalchemy.Column("memory", sqlalchemy.Text),
    sqlalchemy.Column("cpu", sqlalchemy.Text)
)

tag = sqlalchemy.Table(
    "tags",
    metadata,
    sqlalchemy.Column("tag", sqlalchemy.String, unique=True)
)

workshop_tag = sqlalchemy.Table(
    "workshop_tags",
    metadata,
    sqlalchemy.Column("tag_id", sqlalchemy.Integer,
                      sqlalchemy.ForeignKey("tags.id"),
                      nullable=False, index=True),
    sqlalchemy.Column("workshop_id", sqlalchemy.Integer,
                      sqlalchemy.ForeignKey("workshops.id"),
                      nullable=False, index=True),
    sqlalchemy.UniqueConstraint('workshop_id', 'tag_id')
)

workshop_collection = sqlalchemy.Table(
    "workshop_collections",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("url", sqlalchemy.String),
    sqlalchemy.Column("description", sqlalchemy.String)
)

workshop_workshop_collection = sqlalchemy.Table(
    "workshop_workshop_collections",
    metadata,
    sqlalchemy.Column("workshop_id", sqlalchemy.Integer,
                      sqlalchemy.ForeignKey("workshops.id"),
                      nullable=False, index=True),
    sqlalchemy.Column("workshop_collection_id", sqlalchemy.Integer,
                      sqlalchemy.ForeignKey("workshop_collections.id"),
                      nullable=False, index=True),
    sqlalchemy.UniqueConstraint('workshop_id', 'workshop_collection_id')
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
    query = """
    select workshops.*,counts.launches
    from workshops
    join (
          select container, count(*) as launches
          from instance_events
          group by container
    ) counts
    on workshops.container=counts.container"""
    await connect()
    if(id is None):
        res = await database.fetch_all(query)
        return res
    query = query + f'select * from workshops where id = {id}'
    res = await database.fetch_one(query)
    return(res)

async def create_new_workshop(description: str, container: str, url: str=None):
    await connect()
    sql = workshop.insert().values(
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

async def get_tags():
    await connect()
    query = tag.select()
    res = await database.fetch_all(query)
    return res

async def create_new_tag(new_tag) -> dict:
    await connect()
    query = tag.insert().values(new_tag)
    res = await database.fetch_one(query)
    return res

async def create_new_collection(name: str, url: str=None, description: str=None) -> dict:
    await connect()
    query = workshop_collection.insert().values(
        name=name, url=url, description=description
    )
    res = await database.fetch_one(query)
    return res

async def list_collections():
    await connect()
    query = workshop_collection.select()
    res = await database.fetch_all(query)
    return res

async def delete_collection(id:int):
    await connect()
    query = workshop_collection.delete().where(workshop_collection.c.id==id)
    res = await database.fetch_one(query)
    return {'delete': id}

async def new_collection_workshop(workshop_id: int, collection_id: int):
    await connect()
    query = workshop_workshop_collection.insert().values(
        workshop_id=workshop_id,
        workshop_collection_id = collection_id
    )
    res = await database.fetch_one(query)
    return res

async def workshops_by_collection(collection_id: int):
    await connect()
    query = workshop.select().select_from(workshop.join(
        workshop_workshop_collection,
        workshop_workshop_collection.c.workshop_collection_id==collection_id))
    res = await database.fetch_all(query)
    return res

if __name__ == '__main__':
    engine = sqlalchemy.create_engine(config('SQLALCHEMY_URI'))
    metadata.create_all(engine)
