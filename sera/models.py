from dataclasses import dataclass


@dataclass
class SeraMedia:

    customer_id: str
    job_number: str | None

    filename: str

    url: str