"""Application roles and convenience permission groups.

These four roles mirror the options shown in the frontend role picker.
"""

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"
    STOREKEEPER = "storekeeper"
    STAFF = "staff"


ALL_ROLES: tuple[Role, ...] = tuple(Role)

# Convenience groupings used by the endpoints.
# owner/admin are full-access; staff is the lowest, operations-only role.
USER_ADMIN_ROLES: tuple[Role, ...] = (Role.OWNER, Role.ADMIN)
MANAGEMENT: tuple[Role, ...] = (Role.OWNER, Role.ADMIN, Role.MANAGER)
SALES_ROLES: tuple[Role, ...] = (Role.OWNER, Role.ADMIN, Role.MANAGER, Role.CASHIER)
STOCK_ROLES: tuple[Role, ...] = (Role.OWNER, Role.ADMIN, Role.MANAGER, Role.STOREKEEPER)
OPERATIONS_ROLES: tuple[Role, ...] = (
    Role.OWNER,
    Role.ADMIN,
    Role.MANAGER,
    Role.CASHIER,
    Role.STOREKEEPER,
    Role.STAFF,
)


def normalize_role(value: str) -> str:
    """Lowercase/trim a role string and validate it against the allowed set."""
    candidate = value.strip().lower()
    if candidate not in {role.value for role in Role}:
        allowed = ", ".join(role.value for role in Role)
        raise ValueError(f"Invalid role '{value}'. Allowed roles: {allowed}")
    return candidate
