"""Places: turning a chosen location into the doors or points where walking starts or ends."""

from floodroute.places.resolver import (
    DESTINATION,
    ORIGIN,
    AccessPoint,
    Place,
    PlaceResolver,
    mark_indoor_entrances,
)

__all__ = ["DESTINATION", "ORIGIN", "AccessPoint", "Place", "PlaceResolver", "mark_indoor_entrances"]
