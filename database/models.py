from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)

    sera_id = Column(String, unique=True, index=True)
    servicetitan_id = Column(String, index=True)
    legacy_id = Column(String, index=True)

    name = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)

    status = Column(String, default="Pending")

    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship(
        "Job",
        back_populates="customer",
        cascade="all, delete-orphan"
    )


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id")
    )

    sera_job_number = Column(String, index=True)
    servicetitan_job_number = Column(String, index=True)

    job_date = Column(String)
    description = Column(Text)

    status = Column(String, default="Pending")

    customer = relationship(
        "Customer",
        back_populates="jobs"
    )

    media = relationship(
        "Media",
        back_populates="job",
        cascade="all, delete-orphan"
    )


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True)

    job_id = Column(
        Integer,
        ForeignKey("jobs.id")
    )

    filename = Column(String)
    original_filename = Column(String)

    local_path = Column(Text)

    media_type = Column(String)

    quote_number = Column(String)
    invoice_number = Column(String)

    file_date = Column(String)

    sera_url = Column(Text)

    downloaded = Column(Boolean, default=False)

    uploaded = Column(Boolean, default=False)

    verified = Column(Boolean, default=False)

    upload_attempts = Column(Integer, default=0)

    last_error = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    job = relationship(
        "Job",
        back_populates="media"
    )


class Setting(Base):
    __tablename__ = "settings"

    key = Column(
        String,
        primary_key=True
    )

    value = Column(Text)


class Log(Base):
    __tablename__ = "logs"

    id = Column(
        Integer,
        primary_key=True
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow
    )

    level = Column(String)

    message = Column(Text)