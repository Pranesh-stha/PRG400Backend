import uuid
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.booking import Booking
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewerSummary, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReviewOut:
    booking = (
        await db.execute(select(Booking).where(Booking.id == payload.booking_id))
    ).scalar_one_or_none()
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.guest_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")
    if booking.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot review a cancelled booking"
        )
    if booking.check_out > date_type.today():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot review until after check-out"
        )

    existing = (
        await db.execute(select(Review).where(Review.booking_id == booking.id))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Review already exists for this booking"
        )

    review = Review(
        booking_id=booking.id,
        property_id=booking.property_id,
        guest_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return ReviewOut(
        id=review.id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        guest=ReviewerSummary(
            id=current_user.id,
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
        ),
    )


@router.get("/property/{property_id}", response_model=list[ReviewOut])
async def list_property_reviews(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ReviewOut]:
    rows = (
        await db.execute(
            select(Review, User)
            .join(User, Review.guest_id == User.id)
            .where(Review.property_id == property_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return [
        ReviewOut(
            id=r.id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            guest=ReviewerSummary(
                id=u.id, full_name=u.full_name, avatar_url=u.avatar_url
            ),
        )
        for r, u in rows
    ]
