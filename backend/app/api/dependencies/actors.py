from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.current_actor import CurrentActor, resolve_current_actor


def get_current_actor(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> CurrentActor:
    return resolve_current_actor(db, request)
