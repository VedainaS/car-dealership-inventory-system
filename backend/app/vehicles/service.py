"""Vehicle inventory service layer — pure database logic, no HTTP concerns.

Purchase safety
---------------
``purchase_vehicle`` must not allow stock to go negative even when two
requests arrive concurrently.  The approach:

1. Load the vehicle row with ``db.get(Vehicle, id)`` to distinguish a
   missing ID (VehicleNotFoundError → 404) from a zero-stock row
   (OutOfStockError → 409).

2. Execute a conditional UPDATE:

       UPDATE vehicles
       SET quantity = quantity - 1
       WHERE id = :id AND quantity > 0

   and inspect ``result.rowcount``.

   - rowcount == 1 → the UPDATE succeeded atomically; commit and return.
   - rowcount == 0 → the vehicle exists (verified in step 1) but its
     quantity reached 0 between the SELECT and the UPDATE (a concurrent
     purchase committed first).  Raise OutOfStockError → 409.

SQLite serialises all writes at commit time, so even with two independent
connections (NullPool + WAL) the losing transaction will see rowcount == 0
rather than committing a negative quantity.
"""

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models import Vehicle
from app.schemas import VehicleCreate, VehicleUpdate


# ---------------------------------------------------------------------------
# Domain exceptions (translated to HTTP errors in the router)
# ---------------------------------------------------------------------------


class VehicleNotFoundError(Exception):
    """No vehicle with the given ID exists in the database."""


class OutOfStockError(Exception):
    """The vehicle exists but its current quantity is zero."""


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def create_vehicle(db: Session, payload: VehicleCreate) -> Vehicle:
    """Insert a new vehicle row and return it."""
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def list_vehicles(db: Session) -> list[Vehicle]:
    """Return all vehicles, including those with quantity == 0 (out of stock).

    Out-of-stock vehicles are intentionally included so that clients can
    display an "out of stock" state. Callers that want only in-stock
    vehicles can filter on ``quantity`` in the client.
    """
    return db.query(Vehicle).all()


def search_vehicles(
    db: Session,
    *,
    make: str | None = None,
    model: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[Vehicle]:
    """Return vehicles matching all supplied filters (AND semantics).

    Text filters use exact case-insensitive comparison. Unlike ``ilike``,
    equality treats SQL wildcard characters as ordinary search text.
    Omitted parameters are ignored (no filter applied for that column).
    Price bounds are inclusive.
    Out-of-stock vehicles are included in search results.
    """
    query = db.query(Vehicle)
    if make is not None:
        query = query.filter(func.lower(Vehicle.make) == make.lower())
    if model is not None:
        query = query.filter(func.lower(Vehicle.model) == model.lower())
    if category is not None:
        query = query.filter(func.lower(Vehicle.category) == category.lower())
    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)
    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)
    return query.all()


def update_vehicle(db: Session, vehicle_id: int, payload: VehicleUpdate) -> Vehicle:
    """Replace all mutable fields on an existing vehicle.

    Raises VehicleNotFoundError if ``vehicle_id`` does not exist.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFoundError(vehicle_id)
    for key, value in payload.model_dump().items():
        setattr(vehicle, key, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: int) -> None:
    """Delete a vehicle.

    Raises VehicleNotFoundError if ``vehicle_id`` does not exist.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFoundError(vehicle_id)
    db.delete(vehicle)
    db.commit()


# ---------------------------------------------------------------------------
# Inventory operations
# ---------------------------------------------------------------------------


def purchase_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    """Atomically decrement stock by one.

    Two-step algorithm to distinguish 404 from 409:

    Step 1 – existence check
        ``db.get`` returns None iff the ID is not in the table → 404.

    Step 2 – conditional UPDATE
        ``UPDATE vehicles SET quantity = quantity - 1
         WHERE id = :id AND quantity > 0``

        If rowcount == 0 the vehicle exists (step 1 passed) but its stock
        hit zero before this commit → 409.

    This is safe under concurrent load because SQLite serialises commits:
    whichever transaction commits last will see the post-decrement quantity
    and get rowcount == 0.
    """
    # Step 1: verify existence (404 vs 409 distinction)
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFoundError(vehicle_id)

    # Step 2: atomic conditional decrement
    result = db.execute(
        update(Vehicle)
        .where(Vehicle.id == vehicle_id, Vehicle.quantity > 0)
        .values(quantity=Vehicle.quantity - 1)
        .execution_options(synchronize_session=False)
    )
    db.commit()

    if result.rowcount == 0:
        # Vehicle exists but was out of stock at commit time
        raise OutOfStockError(vehicle_id)

    db.refresh(vehicle)
    return vehicle


def restock_vehicle(db: Session, vehicle_id: int, amount: int) -> Vehicle:
    """Add ``amount`` units to the vehicle's stock.

    ``amount`` is validated as > 0 by the Pydantic schema before this
    function is called; the assertion here acts as an internal contract guard.

    Raises VehicleNotFoundError if ``vehicle_id`` does not exist.
    """
    assert amount > 0, "amount must be positive (schema should have caught this)"
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFoundError(vehicle_id)
    vehicle.quantity += amount
    db.commit()
    db.refresh(vehicle)
    return vehicle
