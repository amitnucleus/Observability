from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class CanonicalEvent(BaseModel):
    layer:      int               # 0-7
    layer_name: str               # network, app, pod, db, cache, git, frontend, metrics
    node_id:    str               # unique identifier for the node
    event_type: str               # what happened
    timestamp:  datetime          # when it happened
    severity:   str = "INFO"      # INFO | WARN | ERROR
    payload:    dict[str, Any]    # raw event data
    source:     str = ""          # which service produced this
