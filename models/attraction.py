from dataclasses import dataclass


@dataclass(slots=True)
class Attraction:
    attraction_id: str
    name: str
    category: str
    description: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    area: str = ""
    opening_hours: str = ""
    ticket_price: str = ""
    avg_rating: float = 0.0
    estimated_capacity: int = 0
    popularity_score: int = 0
    indoor_outdoor: str = ""
    tags: str = ""
