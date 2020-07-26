"""Give me a try
"""
import logging
import string
import random
import re

from typing import Optional

from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .kube_utils import (list_deployments as ld, list_services as ls,
                         list_ingresses as li, create_instance)
from .security import check_authentication_header
from .description import api_description

app = FastAPI(title="Workshop Orchestration API",
              description = api_description)

logging.basicConfig(level=logging.INFO)

templates = Jinja2Templates(directory="workshop_orchestra/templates")

def random_string(k: int=8):
    return ''.join(random.choices(string.ascii_lowercase,k=k))


class Item(BaseModel):
    name: str
    price: float
    is_offer: Optional[bool] = None


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("start.html", {"request": request})

@app.get("/instance")
async def create_new_instance_web(request: Request, container: str, email: str):
    (org, repo) = container.split('/')
    res = _new_instance(org, repo, email)
    # should wait here
    return templates.TemplateResponse('new_instance.html', {"request": request, "url": res['url']})



def _new_instance(org: str, repo: str, email: Optional[str] = None,
                 ref: Optional[str] = None,
                 stuff: bool = Depends(check_authentication_header)):
    """Create a new instance of the container called org/repo
    """
    oldrepo = repo
    # Convert everything except letters, numbers, and . - to -
    repo = re.sub('[^a-zA-Z0-9.-]+', '-', repo)
    d = {"org": org, "repo": repo, "email": email}
    logging.info(d)
    s = random_string()
    create_instance(f"{repo}-{s}", f"{org}/{oldrepo}", email)
    d.update({"url": f"http://{repo}-{s}.bioc.cancerdatasci.org/"})
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
