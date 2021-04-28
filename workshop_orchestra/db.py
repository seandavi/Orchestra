import datetime

import sqlalchemy as sa

from databases import Database
from sqlalchemy import func, desc, and_

from .config import config

metadata = sa.MetaData()

instance_events = sa.Table(
    "instance_events",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("instance_id", sa.Integer,
                      sa.ForeignKey('instances.id'),
                      index=True),
    sa.Column("status", sa.Text),
    sa.Column("timestamp", sa.DateTime)
)

instance = sa.Table(
    "instances",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column('email', sa.Text, index=True),
    sa.Column('workshop_id', sa.Integer,
              sa.ForeignKey('workshops.id'),
              index=True),
    sa.Column('name', sa.Text, index=True, unique=True)
)

workshop = sa.Table(
    "workshops",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("title", sa.Text),
    sa.Column("description", sa.Text),
    sa.Column("url", sa.Text),
    sa.Column("container", sa.Text),
    sa.Column("port", sa.Integer,
                      comment="The port on which the container listens"),
    sa.Column("memory", sa.Text),
    sa.Column("cpu", sa.Text)
)

tag = sa.Table(
    "tags",
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column("tag", sa.String, unique=True)
)

workshop_tag = sa.Table(
    "workshop_tags",
    metadata,
    sa.Column("tag_id", sa.Integer,
                      sa.ForeignKey("tags.id"),
                      nullable=False, index=True),
    sa.Column("workshop_id", sa.Integer,
                      sa.ForeignKey("workshops.id"),
                      nullable=False, index=True),
    sa.UniqueConstraint('workshop_id', 'tag_id')
)

workshop_collection = sa.Table(
    "workshop_collections",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, unique=True),
    sa.Column("url", sa.String),
    sa.Column("description", sa.String)
)

workshop_workshop_collection = sa.Table(
    "workshop_workshop_collections",
    metadata,
    sa.Column("workshop_id", sa.Integer,
                      sa.ForeignKey("workshops.id"),
                      nullable=False, index=True),
    sa.Column("workshop_collection_id", sa.Integer,
                      sa.ForeignKey("workshop_collections.id"),
                      nullable=False, index=True),
    sa.UniqueConstraint('workshop_id', 'workshop_collection_id')
)


database = Database(config('SQLALCHEMY_URI'))

async def connect():
    if database.is_connected:
        return
    await database.connect()

async def get_outdated_workshops(interval = '4 hours'):
    query = f"""with s as (select id, status, timestamp, row_number()
    over (partition by id order by timestamp desc) as rk from instance_events)
    select s.*, current_timestamp-s.timestamp as age from s
    where s.rk=1 and current_timestamp-s.timestamp > interval '{interval}'
    and status!='DELETED'"""
    await connect()
    res = await database.fetch_all(query)
    return res


async def get_existing_workshop(email, workshop_id):
    await connect()
    i = instance
    query = i.select().where(and_(i.c.email==email, i.c.workshop_id==workshop_id)).order_by(desc('timestamp'))
    res = await database.fetch_all(query)
    return res

async def get_workshops(id=None):
    query = workshop.join(
        sa.select([instance.c.workshop_id,sa.func.count(instance.c.workshop_id).label('launches')])
        .group_by(instance.c.workshop_id).alias('abc'),
        isouter=True
    ).select()
    await connect()
    if(id is None):
        res = await database.fetch_all(query)
        return res
    query = query.where(workshop.c.id==id)
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

async def add_instance(name, email, workshop_id):
    await connect()
    query = instance.insert().values({"name": name, "workshop_id": workshop_id, "email": email})
    inst = await database.execute(query)
    query = instance_events.insert().values({
        "instance_id":inst,
        "status":'CREATED', "timestamp":datetime.datetime.utcnow()})
    res = await database.execute(query)
    return True

async def delete_instance(name):
    await connect()
    query = instance.select().where(instance.c.name==name)
    res = await database.fetch_one()
    query = instance_events.insert().values({
        "instance_id":inst,
        "status":'DELETED', "timestamp":datetime.datetime.utcnow()
    })
    res = await database.execute(query)
    return True

async def get_tags():
    await connect()
    query = tag.select()
    res = await database.fetch_all(query)
    return res

async def create_new_tag(new_tag) -> dict:
    await connect()
    query = tag.insert().values({"tag":new_tag})
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


async def instances_by_email(email: str):
    await connect()
    query = instance.join(workshop).select().where(instance.c.email==email)
    res = await database.fetch_all(query)
    return res

if __name__ == '__main__':
    engine = sa.create_engine(config('SQLALCHEMY_URI'))
    metadata.create_all(engine)
