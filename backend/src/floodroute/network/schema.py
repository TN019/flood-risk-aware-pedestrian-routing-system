"""The routing graph schema shared by every network source.

A routing graph is an undirected ``networkx.Graph`` in the metric CRS.

Graph attributes
    ``crs``, ``study_area`` (polygon or None), ``buffer_m``, ``source`` (optional).

Node attributes
    ``x``, ``y``          coordinates in the metric CRS
    ``kind``              ``JUNCTION`` or ``PARCEL_ACCESS``
    ``in_study_area``     whether the node lies inside the study area (start/end points must)
    ``parcel_id``         parcel the access stub belongs to (City of Melbourne network only)

Edge attributes, always present
    ``edge_id``, ``geometry`` (LineString), ``length_m``, ``in_study_area``,
    ``cost_factor``       multiplier on length for routing cost (>1 = discouraged, e.g. walking
                          along a carriageway that has a sidewalk beside it)

Edge attributes, source-specific
    OSM: ``osmid``, ``highway``, ``name``, ``is_steps``, ``is_crossing``, ``is_bridge``,
         ``is_tunnel``, ``is_carriageway``
    City of Melbourne: ``objectid``, ``is_parcel_link``
"""

from __future__ import annotations

import collections

import networkx as nx

JUNCTION = "junction"
PARCEL_ACCESS = "parcel_access"


def is_snappable(edge_data: dict) -> bool:
    """Whether an arbitrary point may be joined onto this edge. Parcel links are abstract
    connectors into a property, not walkways."""
    return not edge_data.get("is_parcel_link", False)


def parcel_access_nodes(graph: nx.Graph) -> dict[str, list]:
    """Map parcel_id -> its access stub nodes (one per link into the parcel)."""
    out: dict[str, list] = collections.defaultdict(list)
    for n, d in graph.nodes(data=True):
        if d.get("kind") == PARCEL_ACCESS:
            out[d["parcel_id"]].append(n)
    return dict(out)
