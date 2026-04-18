from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


import app.models.audit  # noqa: F401,E402
import app.models.billing  # noqa: F401,E402
import app.models.hardware  # noqa: F401,E402
import app.models.learning  # noqa: F401,E402
import app.models.realtime_observability  # noqa: F401,E402
import app.models.review  # noqa: F401,E402
import app.models.simulation  # noqa: F401,E402
import app.models.user  # noqa: F401,E402
