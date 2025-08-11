import os
import uuid
from datetime import datetime

def unique_id(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

def ensure_dirs(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)
