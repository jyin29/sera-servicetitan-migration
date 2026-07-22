from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE
from database.models import Base


DATABASE.parent.mkdir(
    parents=True,
    exist_ok=True
)

engine = create_engine(
    f"sqlite:///{DATABASE}",
    echo=False,
    future=True
)

Session = sessionmaker(
    bind=engine
)


def initialize_database():

    Base.metadata.create_all(engine)

    print("Database initialized.")