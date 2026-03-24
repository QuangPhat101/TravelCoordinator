from dataclasses import dataclass


@dataclass(slots=True)
class Destination:
    name: str
    province: str
    description: str
    eco_tip: str
