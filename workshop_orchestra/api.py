"""Give me a try
"""
import logging
import string
import random
import re
import asyncio
import typing

from typing import Optional

from workshop_orchestra import db

from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_prometheus import metrics, PrometheusMiddleware

from starlette.responses import HTMLResponse, RedirectResponse
from starlette.authentication import requires
from pydantic import BaseModel
from authlib.integrations.starlette_client import OAuth
from fastapi.security.oauth2 import OAuth2

from . import kube_utils
from .security import check_authentication_header
from .description import api_description
from .config import config
import json

app = FastAPI(title="Workshop Orchestration API",
              description=api_description)
app.add_middleware(SessionMiddleware, secret_key=config('API_KEY'))
app.add_middleware(PrometheusMiddleware)

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_route("/metrics/", metrics)

logging.basicConfig(level=logging.INFO)

templates = Jinja2Templates(directory="workshop_orchestra/templates")



#################################################
#################################################
#################################################
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
from google.auth.transport import requests
import google.oauth2.id_token

@app.route('/login')
async def homepage(request):
    print(request.headers)
    f = open('workshop_orchestra/templates/login_template.html').read()
    return HTMLResponse(f)


firebase_request_adapter = requests.Request()

@app.route('/auth')
async def loggedin(request):
    print(request.headers)
    print(request.cookies)
    id_token = request.cookies.get('token')
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, firebase_request_adapter)
    print(claims)
    request.session['user']=dict(claims)
    f = open('workshop_orchestra/templates/checklogin.html').read()
    return RedirectResponse('/1')


# app = Starlette(debug=True, routes=[
#     Route('/', homepage),
#     Route('/loggedin', loggedin)
# ])


def random_string(k: int=8):
    return ''.join(random.choices(string.ascii_lowercase, k=k))


class Item(BaseModel):
    name: str
    price: float
    is_offer: Optional[bool] = None

class BaseContainer(BaseModel):
    description: str
    url: str=None
    container: str

class ExistingContainer(BaseContainer):
    id: int

class TagItem(BaseModel):
    tag: str

class TagReturnItem(TagItem):
    id: int


oauth = OAuth(config)

# Keycloak details
CONF_URL = 'http://login.cancerdatasci.org/auth/realms/cancerdatasci/.well-known/openid-configuration'
oauth.register(
    name='keycloak_client',
    server_metadata_url=CONF_URL,
    client_id='login',
    client_kwargs={
        'scope': 'openid email profile'
    }
)



# CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
# oauth.register(
#     name='google',
#     server_metadata_url=CONF_URL,
#     client_kwargs={
#         'scope': 'openid email profile',
#         'hostedDomain': 'gmail.com'
#     }
# )

@app.route('/')
async def homepage(request):
    user = request.session.get('user')
    if user:
        data = json.dumps(user)
        html = (
            f'<pre>{data}</pre>'
            '<a href="/logout">logout</a>'
        )
        return RedirectResponse('/1')
    return templates.TemplateResponse("home.html", context={"request": request})


#@app.route('/login')
async def login(request):
    redirect_uri = request.url_for('auth')
    return await oauth.keycloak_client.authorize_redirect(request, redirect_uri)


#@app.route('/auth')
async def auth(request):
    token = await oauth.keycloak_client.authorize_access_token(request)
    user = await oauth.keycloak_client.parse_id_token(request, token)
    request.session['user'] = dict(user)
    return RedirectResponse(url='/')


@app.route('/logout')
async def logout(request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')



@app.get("/1")
async def read_root(request: Request):
    logging.info(request.session)
    workshops = await db.get_workshops()
    user=request.session.get('user')
    if not user:
        return RedirectResponse('/')
    return templates.TemplateResponse("start.html", {"request": request,
                                                     "workshops": workshops
    })

@app.get('/new_workshop')
async def new_workshop_web(request: Request, i = Depends(lambda x: True)):
    logging.info(request.session)
    logging.info(i)
    containers = await db.get_workshops()
    return templates.TemplateResponse(
        "new.html", {
            "request": request,
            "containers": containers
        }
    )


@app.get('/instances/{email}')
async def list_instances(email: str):
    instances = await db.instances_by_email(email)
    return list(dict(r.items()) for r in instances)

# TODO ensure logged in else redirect
@app.get("/instance")
async def create_new_instance_web(request: Request, workshop_id: int):
    """Create a new instance or return existing one
    """

    email = request.session.get('user')['email']
    workshop = await db.get_workshops(id=workshop_id)
    container = workshop.get('container')
    # res = await db.get_existing_workshop(email, container)

    # if(len(res)>0):
    #     try:
    #         stuff = deployment_is_ready(res[0].get('name'))
    #         if(stuff):
    #             return RedirectResponse('http://'+res[0].get('name')+".bioc.cancerdatasci.org")
    #     except:
    #         logging.info(f"{container} instance {res[0].get('name')} for email {email} not found, so creating a new one")
    res = await kube_utils.create_instance(workshop_id, email)
    #await asyncio.sleep(2)
    return templates.TemplateResponse('new_instance.html',
                                      {
                                          "request": request,
                                          "url": res['url'],
                                          "name": res["name"]
                                      })

@app.get('/instances/outdated/{interval}')
async def get_outdated_instances(interval: str='4 hours'):
    """Get a list of instances that are older than "interval"
    """
    outdated_instances = await db.get_outdated_workshops(interval)
    return list(dict(r.items()) for r in outdated_instances)


@app.get("/ready")
async def instance_is_ready(name: str):
    res = kube_utils.deployment_is_ready(name)
    return {'is_ready': res}

@app.get('/containers')
async def get_containers() -> typing.List[ExistingContainer]:
    res = await db.get_workshops()
    res = list([ExistingContainer(**r) for r in res])
    return res

@app.post("/containers")
async def create_container(container: BaseContainer):
    res = await db.create_new_workshop(**container.dict())
    return res


@app.get("/tags")
async def get_tags() -> typing.List[TagReturnItem]:
    res = await db.get_tags()
    res = list([TagReturnItem(**r) for r in res])
    return res

@app.post("/tags")
async def new_tag(new_tag: TagItem) -> TagReturnItem:
    res = await db.create_new_tag(new_tag.dict())
    res = new_tag.dict().update({"id":res})
    return TagReturnItem(**new_tag)

# TODO these need to be converted to instance.
@app.get("/instance/{name}")
async def get_instance(name: str):
    return await kube_utils.get_deployment(name)

@app.delete("/instance/{name}")
async def delete_instance(name: str):
    try:
        await kube_utils.delete_workshop(name)
    except Exception as e:
        print(e)
        return None
    return {"name": name, "status": "DELETED"}

class Collection(BaseModel):
    name: str
    description: str=None
    url: str=None

class CollectionOut(Collection):
    id: int

@app.get("/collections")
async def list_collections() -> list:
    res = await db.list_collections()
    return [CollectionOut(**r) for r in res]

@app.post("/collections")
async def create_new_collection(collection: Collection):
    res = await db.create_new_collection(**collection.dict())
    return res

@app.delete("/collections/{collection_id}")
async def delete_collection(collection_id: int):
    res = await db.delete_collection(collection_id)
    return res

@app.get("/collections/{collection_id}/workshops")
async def workshops_for_collection(collection_id: int):
    res = await db.workshops_by_collection(collection_id)
    return res

@app.post("/collections/{collection_id}/workshops/{workshop_id}")
async def delete_workshop_from_collection(collection_id: int, workshop_id: int):
    res = await db.new_collection_workshop(workshop_id=workshop_id, collection_id=collection_id)
    return res

# FIXME this is no longer used
async def _new_instance(workshop_id: int, email: Optional[str] = None,
                 stuff: bool = Depends(check_authentication_header)):
    """Create a new instance of the container called org/repo
    """
    oldrepo = repo
    # Convert everything except letters, numbers, and . - to -
    repo = re.sub('[^a-zA-Z0-9.-]+', '-', repo)
    d = {"container": container, "repo": repo, "email": email}
    logging.info(d)
    s = random_string()
    inst_name = f"{repo}-{s}"
    kube_utils.create_instance(inst_name, container, email)
    d.update({"name": inst_name, "url": f"http://{inst_name}.orchestra.cancerdatasci.org/"})
    await db.add_instance(name=inst_name, email=email, container=container)
    return d
