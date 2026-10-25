"""Vehicle inventory REST API router.

Route declaration order
-----------------------
``GET /api/vehicles/search`` is declared **before** ``PUT /api/vehicles/{vehicle_id}``
and ``DELETE /api/vehicles/{vehicle_id}`` to ensure that the literal string
"search" is never attempted as an integer path parameter.  (FastAPI matches
routes in declaration order; a literal path wins over a parameterised one
when registered first.)

Endpoints
---------
POST   /api/vehicles                     – create vehicle            (admin)
GET    /api/vehicles                     – list all vehicles         (authenticated)
GET    /api/vehicles/search              – filter vehicles           (authenticated)
PUT    /api/vehicles/{id}                – update vehicle            (admin)
DELETE /api/vehicles/{id}                – delete vehicle            (admin)
POST   /api/vehicles/{id}/purchase       – buy one unit              (authenticated)
POST   /api/vehicles/{id}/restock        – add stock                 (admin)

HTTP status codes
-----------------
201  Vehicle created
200  Success
204  Vehicle deleted (no body)
401  Missing or invalid / expired JWT
403  Authenticated but role is not admin
404  Vehicle ID not found
409  Vehicle exists but is out of stock (purchase only)
422  Request body fails Pydantic validation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models import User
from app.schemas import RestockRequest, VehicleCreate, VehiclePublic, VehicleUpdate
from app.vehicles.service import (
    OutOfStockError,
    VehicleNotFoundError,
    create_vehicle,
    delete_vehicle,
    list_vehicles,
    purchase_vehicle,
    restock_vehicle,
    search_vehicles,
    update_vehicle,
)

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


# ---------------------------------------------------------------------------
# Collection routes (no path parameter)
# ---------------------------------------------------------------------------


@router.post("", response_model=VehiclePublic, status_code=status.HTTP_201_CREATED)
def create(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> VehiclePublic:
    """Create a new vehicle listing.  Admin only."""
    return create_vehicle(db, payload)


@router.get("", response_model=list[VehiclePublic])
def list_all(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[VehiclePublic]:
    """List all vehicles including out-of-stock ones.  Authenticated users."""
    return list_vehicles(db)


@router.get("/search", response_model=list[VehiclePublic])
def search(
    make: str | None = Query(None, description="Exact case-insensitive make filter"),
    model: str | None = Query(None, description="Exact case-insensitive model filter"),
    category: str | None = Query(None, description="Exact case-insensitive category filter"),
    min_price: float | None = Query(None, ge=0, description="Inclusive lower price bound"),
    max_price: float | None = Query(None, ge=0, description="Inclusive upper price bound"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[VehiclePublic]:
    """Search vehicles with optional combined filters.  Authenticated users.

    All parameters are optional and applied with AND semantics.
    Text filters are exact case-insensitive (e.g. ``make=toyota`` matches
    a vehicle stored as ``Toyota``).
    Out-of-stock vehicles are included in results.
    """
    return search_vehicles(
        db,
        make=make,
        model=model,
        category=category,
        min_price=min_price,
        max_price=max_price,
    )


# ---------------------------------------------------------------------------
# Item routes (path parameter {vehicle_id})
# Declared after /search so the literal "search" is never parsed as an int.
# ---------------------------------------------------------------------------


@router.put("/{vehicle_id}", response_model=VehiclePublic)
def update(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> VehiclePublic:
    """Replace all fields on an existing vehicle.  Admin only."""
    try:
        return update_vehicle(db, vehicle_id, payload)
    except VehicleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    """Remove a vehicle from the inventory.  Admin only."""
    try:
        delete_vehicle(db, vehicle_id)
    except VehicleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )


@router.post("/{vehicle_id}/purchase", response_model=VehiclePublic)
def purchase(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> VehiclePublic:
    """Purchase one unit of a vehicle (decrement stock by 1).

    Returns 404 if the vehicle does not exist.
    Returns 409 if the vehicle exists but is currently out of stock.
    Safe under concurrent requests: uses a conditional UPDATE to prevent
    stock from going below zero.
    """
    try:
        return purchase_vehicle(db, vehicle_id)
    except VehicleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    except OutOfStockError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle {vehicle_id} is currently out of stock.",
        )


@router.post("/{vehicle_id}/restock", response_model=VehiclePublic)
def restock(
    vehicle_id: int,
    payload: RestockRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> VehiclePublic:
    """Add units to a vehicle's stock.  Admin only.

    ``amount`` must be a positive integer (> 0); zero and negative values
    are rejected with 422 by Pydantic before this handler is called.
    Returns 404 if the vehicle does not exist.
    """
    try:
        return restock_vehicle(db, vehicle_id, payload.amount)
    except VehicleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
