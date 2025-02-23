from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BaseModelTimestamped(BaseModel):
    """Base model with timestamps."""
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
