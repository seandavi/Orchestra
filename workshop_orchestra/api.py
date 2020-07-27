"""Give me a try
"""
import logging
import string
import random
import re
import asyncio

from typing import Optional

from workshop_orchestra import db


from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from pydantic import BaseModel

from .kube_utils import (list_deployments as ld, list_services as ls,
                         list_ingresses as li, create_instance,
                         deployment_is_ready)
from .security import check_authentication_header
from .description import api_description
from .config import config

app = FastAPI(title="Workshop Orchestration API",
              description = api_description)
app.add_middleware(SessionMiddleware, secret_key=config('API_KEY'))



logging.basicConfig(level=logging.INFO)

templates = Jinja2Templates(directory="workshop_orchestra/templates")

def random_string(k: int=8):
    return ''.join(random.choices(string.ascii_lowercase, k=k))


class Item(BaseModel):
    name: str
    price: float
    is_offer: Optional[bool] = None


@app.get("/")
async def read_root(request: Request):
    logging.info(request.session)
    request.session['data'] = 'abc'
    containers = await db.get_workshops()
    return templates.TemplateResponse("start.html", {"request": request,
                                                     "containers": containers
    })

@app.get("/instance")
async def create_new_instance_web(request: Request, container: str, email: str):
    repo = re.sub('[:#].*','',container).split('/')[1]

    res = await _new_instance(container, repo, email)
    #await asyncio.sleep(2)
    stuff = deployment_is_ready(res['name'])
    logging.info(res)
    logging.info(stuff)
    if(stuff):
        return RedirectResponse(res['url'])
    return templates.TemplateResponse('new_instance.html',
                                      {
                                          "request": request,
                                          "url": res['url'],
                                          "name": res["name"]
                                      })

@app.get("/ready")
async def instance_is_ready(name: str):
    res = deployment_is_ready(name)
    return {'is_ready': res}



async def _new_instance(container: str, repo: str, email: Optional[str] = None,
                 ref: Optional[str] = None,
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
    create_instance(inst_name, container, email)
    d.update({"name": inst_name, "url": f"http://{inst_name}.bioc.cancerdatasci.org/"})
    await db.add_instance(name=inst_name, email=email, container=container)
    return d

@app.get("/instances/{org}/{repo}")
def new_instance(org: str, repo: str, email: str):
    return _new_instance(org, repo, email)


@app.get("/deployments")
def list_deployments(stuff: bool = Depends(check_authentication_header)):
    return ld()

@app.get("/ingresses")
def list_ingresses(stuff: bool = Depends(check_authentication_header)):
    return li()

@app.get("/services")
def list_services(stuff: bool = Depends(check_authentication_header)):
    return ls()

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
