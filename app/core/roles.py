"""Application roles and convenience permission groups.

These four roles mirror the options shown in the frontend role picker.
"""

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    CASHIER = "cashier"
    STOREKEEPER = "storekeeper"


ALL_ROLES: tuple[Role, ...] = tuple(Role)

# Convenience groupings used by the endpoints.
MANAGEMENT: tuple[Role, ...] = (Role.OWNER, Role.MANAGER)
SALES_ROLES: tuple[Role, ...] = (Role.OWNER, Role.MANAGER, Role.CASHIER)
STOCK_ROLES: tuple[Role, ...] = (Role.OWNER, Role.MANAGER, Role.STOREKEEPER)
OPERATIONS_ROLES: tuple[Role, ...] = (Role.OWNER, Role.MANAGER, Role.CASHIER, Role.STOREKEEPER)


def normalize_role(value: str) -> str:
    """Lowercase/trim a role string and validate it against the allowed set."""
    candidate = value.strip().lower()
    if candidate not in {role.value for role in Role}:
        allowed = ", ".join(role.value for role in Role)
        raise ValueError(f"Invalid role '{value}'. Allowed roles: {allowed}")
    return candidate
