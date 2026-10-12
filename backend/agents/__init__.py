"""The five Campus Customs agent roles."""

from .accounting import build_accounting_agent
from .boss import build_boss_agent
from .customer_service import build_customer_service_agent
from .facilities import build_facilities_agent
from .inventory import build_inventory_agent

__all__ = [
    "build_accounting_agent",
    "build_boss_agent",
    "build_customer_service_agent",
    "build_facilities_agent",
    "build_inventory_agent",
]
