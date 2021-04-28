import logging

from starlette.config import Config

config = Config(".env")

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("orchestra")
