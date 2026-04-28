import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PropertyType = Literal["hotel", "villa", "apartment", "room", "cabin", "cottage"]


class PropertyImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    display_order: int
    is_primary: bool


class PropertyImageCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    display_order: int = 0
    is_primary: bool = False


class HostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    avatar_url: str | None = None


class PropertyBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    property_type: PropertyType
    address: str = Field(min_length=1)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    price_per_night: Decimal = Field(gt=0)
    max_guests: int = Field(gt=0)
    bedrooms: int = Field(ge=0)
    bathrooms: int = Field(ge=0)
    amenities: list[str] = []


class PropertyCreate(PropertyBase):
    images: list[PropertyImageCreate] = []


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    property_type: PropertyType | None = None
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    price_per_night: Decimal | None = Field(default=None, gt=0)
    max_guests: int | None = Field(default=None, gt=0)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    amenities: list[str] | None = None
    is_active: bool | None = None


class PropertySummary(BaseModel):
    """Compact shape for list views."""

    id: uuid.UUID
    title: str
    city: str
    country: str
    property_type: str
    price_per_night: Decimal
    max_guests: int
    bedrooms: int
    bathrooms: int
    primary_image_url: str | None
    average_rating: float | None
    review_count: int


class PropertyDetail(PropertyBase):
    id: uuid.UUID
    host_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[PropertyImageOut]
    host: HostSummary
    average_rating: float | None
    review_count: int


class PropertyList(BaseModel):
    items: list[PropertySummary]
    total: int
    limit: int
    offset: int
