import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BookingStatus = Literal["pending", "confirmed", "cancelled", "completed"]


class BookingCreate(BaseModel):
    property_id: uuid.UUID
    check_in: date
    check_out: date
    num_guests: int = Field(gt=0)

    @model_validator(mode="after")
    def _check_dates(self) -> "BookingCreate":
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if self.check_in < date.today():
            raise ValueError("check_in cannot be in the past")
        return self


class PropertyMini(BaseModel):
    """Minimal property fields embedded in booking responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    city: str
    country: str
    primary_image_url: str | None = None


class BookingOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    guest_id: uuid.UUID
    check_in: date
    check_out: date
    num_guests: int
    total_price: Decimal
    status: BookingStatus
    created_at: datetime
    property: PropertyMini | None = None
