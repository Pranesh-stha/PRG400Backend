import uuid
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.booking import Booking
from app.models.property import Property, PropertyImage
from app.models.review import Review
from app.models.user import User
from app.schemas.property import (
    HostSummary,
    PropertyCreate,
    PropertyDetail,
    PropertyImageCreate,
    PropertyImageOut,
    PropertyList,
    PropertySummary,
    PropertyUpdate,
)

router = APIRouter(prefix="/properties", tags=["properties"])


def _primary_image_url(images: list[PropertyImage]) -> str | None:
    if not images:
        return None
    primary = next((img for img in images if img.is_primary), None)
    return (primary or images[0]).url


async def _load_property_detail(db: AsyncSession, property_id: uuid.UUID) -> PropertyDetail:
    p = (
        await db.execute(
            select(Property)
            .where(Property.id == property_id)
            .options(selectinload(Property.images))
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")

    host = (await db.execute(select(User).where(User.id == p.host_id))).scalar_one()
    rating_row = (
        await db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.property_id == p.id
            )
        )
    ).one()
    avg = float(rating_row[0]) if rating_row[0] is not None else None

    return PropertyDetail(
        id=p.id,
        host_id=p.host_id,
        title=p.title,
        description=p.description,
        property_type=p.property_type,
        address=p.address,
        city=p.city,
        country=p.country,
        latitude=p.latitude,
        longitude=p.longitude,
        price_per_night=p.price_per_night,
        max_guests=p.max_guests,
        bedrooms=p.bedrooms,
        bathrooms=p.bathrooms,
        amenities=p.amenities,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
        images=[PropertyImageOut.model_validate(i) for i in p.images],
        host=HostSummary.model_validate(host),
        average_rating=avg,
        review_count=rating_row[1],
    )


@router.get("", response_model=PropertyList)
async def list_properties(
    db: Annotated[AsyncSession, Depends(get_db)],
    city: str | None = None,
    country: str | None = None,
    location: str | None = None,
    property_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    guests: int | None = None,
    check_in: date_type | None = None,
    check_out: date_type | None = None,
    amenities: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PropertyList:
    filters = [Property.is_active.is_(True)]
    if city:
        filters.append(Property.city.ilike(f"%{city}%"))
    if country:
        filters.append(Property.country.ilike(f"%{country}%"))
    if location:
        filters.append(
            or_(
                Property.city.ilike(f"%{location}%"),
                Property.country.ilike(f"%{location}%"),
            )
        )
    if property_type:
        filters.append(Property.property_type == property_type)
    if min_price is not None:
        filters.append(Property.price_per_night >= min_price)
    if max_price is not None:
        filters.append(Property.price_per_night <= max_price)
    if guests is not None:
        filters.append(Property.max_guests >= guests)
    if amenities:
        filters.append(Property.amenities.contains(amenities))

    if check_in and check_out:
        if check_out <= check_in:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "check_out must be after check_in"
            )
        booked_subq = select(Booking.property_id).where(
            Booking.status != "cancelled",
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
        filters.append(~Property.id.in_(booked_subq))

    total = (
        await db.execute(select(func.count()).select_from(Property).where(*filters))
    ).scalar_one()

    result = await db.execute(
        select(Property)
        .where(*filters)
        .options(selectinload(Property.images))
        .order_by(Property.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    properties = list(result.scalars().all())

    ratings_map: dict[uuid.UUID, tuple[float, int]] = {}
    if properties:
        prop_ids = [p.id for p in properties]
        rating_rows = (
            await db.execute(
                select(
                    Review.property_id,
                    func.avg(Review.rating).label("avg"),
                    func.count(Review.id).label("count"),
                )
                .where(Review.property_id.in_(prop_ids))
                .group_by(Review.property_id)
            )
        ).all()
        ratings_map = {r.property_id: (float(r.avg), r.count) for r in rating_rows}

    items = [
        PropertySummary(
            id=p.id,
            title=p.title,
            city=p.city,
            country=p.country,
            property_type=p.property_type,
            price_per_night=p.price_per_night,
            max_guests=p.max_guests,
            bedrooms=p.bedrooms,
            bathrooms=p.bathrooms,
            primary_image_url=_primary_image_url(p.images),
            average_rating=ratings_map.get(p.id, (None, 0))[0],
            review_count=ratings_map.get(p.id, (None, 0))[1],
        )
        for p in properties
    ]

    return PropertyList(items=items, total=total, limit=limit, offset=offset)


@router.get("/host/me", response_model=list[PropertySummary])
async def list_my_properties(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PropertySummary]:
    """Properties owned by the current user (active + inactive)."""
    result = await db.execute(
        select(Property)
        .where(Property.host_id == current_user.id)
        .options(selectinload(Property.images))
        .order_by(Property.created_at.desc())
    )
    properties = list(result.scalars().all())

    return [
        PropertySummary(
            id=p.id,
            title=p.title,
            city=p.city,
            country=p.country,
            property_type=p.property_type,
            price_per_night=p.price_per_night,
            max_guests=p.max_guests,
            bedrooms=p.bedrooms,
            bathrooms=p.bathrooms,
            primary_image_url=_primary_image_url(p.images),
            average_rating=None,
            review_count=0,
        )
        for p in properties
    ]


@router.get("/{property_id}", response_model=PropertyDetail)
async def get_property(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PropertyDetail:
    detail = await _load_property_detail(db, property_id)
    if not detail.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    return detail


@router.post("", response_model=PropertyDetail, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PropertyDetail:
    prop = Property(
        host_id=current_user.id,
        title=payload.title,
        description=payload.description,
        property_type=payload.property_type,
        address=payload.address,
        city=payload.city,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        price_per_night=payload.price_per_night,
        max_guests=payload.max_guests,
        bedrooms=payload.bedrooms,
        bathrooms=payload.bathrooms,
        amenities=payload.amenities,
    )
    db.add(prop)
    await db.flush()

    for idx, img in enumerate(payload.images):
        db.add(
            PropertyImage(
                property_id=prop.id,
                url=img.url,
                display_order=img.display_order if img.display_order else idx,
                is_primary=img.is_primary or (idx == 0),
            )
        )

    if not current_user.is_host:
        current_user.is_host = True

    await db.commit()
    return await _load_property_detail(db, prop.id)


@router.put("/{property_id}", response_model=PropertyDetail)
async def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PropertyDetail:
    prop = (
        await db.execute(select(Property).where(Property.id == property_id))
    ).scalar_one_or_none()
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    if prop.host_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't own this property")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)

    await db.commit()
    return await _load_property_detail(db, property_id)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    prop = (
        await db.execute(select(Property).where(Property.id == property_id))
    ).scalar_one_or_none()
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    if prop.host_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't own this property")

    prop.is_active = False
    await db.commit()


@router.post(
    "/{property_id}/images",
    response_model=list[PropertyImageOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_property_images(
    property_id: uuid.UUID,
    images: list[PropertyImageCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PropertyImageOut]:
    prop = (
        await db.execute(select(Property).where(Property.id == property_id))
    ).scalar_one_or_none()
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    if prop.host_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't own this property")

    new_images = [
        PropertyImage(
            property_id=property_id,
            url=img.url,
            display_order=img.display_order,
            is_primary=img.is_primary,
        )
        for img in images
    ]
    db.add_all(new_images)
    await db.commit()
    for img in new_images:
        await db.refresh(img)

    return [PropertyImageOut.model_validate(i) for i in new_images]
