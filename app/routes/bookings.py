import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.booking import Booking
from app.models.property import Property
from app.models.user import User
from app.routes.properties import _primary_image_url
from app.schemas.booking import BookingCreate, BookingOut, PropertyMini

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def _enrich_bookings(
    db: AsyncSession, bookings: list[Booking]
) -> list[BookingOut]:
    if not bookings:
        return []
    prop_ids = list({b.property_id for b in bookings})
    properties = (
        await db.execute(
            select(Property)
            .where(Property.id.in_(prop_ids))
            .options(selectinload(Property.images))
        )
    ).scalars().all()
    props_map = {p.id: p for p in properties}

    out: list[BookingOut] = []
    for b in bookings:
        p = props_map.get(b.property_id)
        prop_mini = (
            PropertyMini(
                id=p.id,
                title=p.title,
                city=p.city,
                country=p.country,
                primary_image_url=_primary_image_url(p.images),
            )
            if p
            else None
        )
        out.append(
            BookingOut(
                id=b.id,
                property_id=b.property_id,
                guest_id=b.guest_id,
                check_in=b.check_in,
                check_out=b.check_out,
                num_guests=b.num_guests,
                total_price=b.total_price,
                status=b.status,
                created_at=b.created_at,
                property=prop_mini,
            )
        )
    return out


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookingOut:
    prop = (
        await db.execute(
            select(Property).where(
                Property.id == payload.property_id,
                Property.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    if prop.host_id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "You cannot book your own property"
        )
    if payload.num_guests > prop.max_guests:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"This property allows at most {prop.max_guests} guests",
        )

    overlap = (
        await db.execute(
            select(Booking.id).where(
                Booking.property_id == prop.id,
                Booking.status != "cancelled",
                Booking.check_in < payload.check_out,
                Booking.check_out > payload.check_in,
            )
        )
    ).scalar_one_or_none()
    if overlap is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Property is not available for the selected dates",
        )

    nights = (payload.check_out - payload.check_in).days
    total_price = prop.price_per_night * nights

    booking = Booking(
        property_id=prop.id,
        guest_id=current_user.id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        num_guests=payload.num_guests,
        total_price=total_price,
        status="confirmed",
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    enriched = await _enrich_bookings(db, [booking])
    return enriched[0]


@router.get("/me", response_model=list[BookingOut])
async def my_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[BookingOut]:
    bookings = (
        await db.execute(
            select(Booking)
            .where(Booking.guest_id == current_user.id)
            .order_by(Booking.check_in.desc())
        )
    ).scalars().all()
    return await _enrich_bookings(db, list(bookings))


@router.get("/host", response_model=list[BookingOut])
async def host_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[BookingOut]:
    """Bookings made on properties owned by the current user."""
    bookings = (
        await db.execute(
            select(Booking)
            .join(Property, Booking.property_id == Property.id)
            .where(Property.host_id == current_user.id)
            .order_by(Booking.check_in.desc())
        )
    ).scalars().all()
    return await _enrich_bookings(db, list(bookings))


@router.patch("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookingOut:
    booking = (
        await db.execute(select(Booking).where(Booking.id == booking_id))
    ).scalar_one_or_none()
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.guest_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You can only cancel your own bookings"
        )
    if booking.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Booking is already cancelled"
        )
    if booking.status == "completed":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot cancel a completed booking"
        )

    booking.status = "cancelled"
    await db.commit()
    await db.refresh(booking)
    enriched = await _enrich_bookings(db, [booking])
    return enriched[0]
