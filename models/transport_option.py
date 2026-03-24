from dataclasses import dataclass


@dataclass(slots=True)
class TransportOption:
    origin_id: str
    destination_id: str
    transport_mode: str
    distance_km: float = 0.0
    duration_min: int = 0
    estimated_carbon_g: int = 0
