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
from starlette_prometheus import metrics, PrometheusMiddleware

from starlette.responses import RedirectResponse
from pydantic import BaseModel

from . import kube_utils
from .security import check_authentication_header
from .description import api_description
from .config import config

app = FastAPI(title="Workshop Orchestration API",
              description = api_description)
app.add_middleware(SessionMiddleware, secret_key=config('API_KEY'))
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics/", metrics)


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

    res = await db.get_existing_workshop(email, container)

    if(len(res)>0):
        try:
            stuff = deployment_is_ready(res[0].get('name'))
            if(stuff):
                return RedirectResponse('http://'+res[0].get('name')+".bioc.cancerdatasci.org")
        except:
            logging.info(f"{container} instance {res[0].get('name')} for email {email} not found, so creating a new one")
    res = await _new_instance(container, repo, email)
    #await asyncio.sleep(2)
    return templates.TemplateResponse('new_instance.html',
                                      {
                                          "request": request,
                                          "url": res['url'],
                                          "name": res["name"]
                                      })

@app.get("/ready")
async def instance_is_ready(name: str):
    res = kube_utils.deployment_is_ready(name)
    return {'is_ready': res}

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
    kube_utils.create_instance(inst_name, container, email)
    d.update({"name": inst_name, "url": f"http://{inst_name}.bioc.cancerdatasci.org/"})
    await db.add_instance(name=inst_name, email=email, container=container)
    return d
