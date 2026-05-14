"""Broker contract resolution primitives for Algotradify.

This package standardizes option contract resolution behavior. It does not place
orders and does not mark candidates executable.
"""

from broker_contract.resolver import (
    BrokerContractResolution,
    BrokerContractResolutionStatus,
    OptionContractRequest,
    TokenCoverageError,
    resolve_option_contract,
)

__all__ = [
    "BrokerContractResolution",
    "BrokerContractResolutionStatus",
    "OptionContractRequest",
    "TokenCoverageError",
    "resolve_option_contract",
]
