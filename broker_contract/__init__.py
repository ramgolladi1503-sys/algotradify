"""Broker contract resolution primitives for Algotradify.

This package standardizes option contract resolution and readiness behavior. It
does not place orders and does not mark candidates executable.
"""

from broker_contract.instrument_resolution_health import (
    InstrumentResolutionHealthPanel,
    InstrumentResolutionHealthStatus,
    build_instrument_resolution_health_panel,
    instrument_resolution_health_schema_contract,
)
from broker_contract.readiness import (
    BrokerContractReadiness,
    BrokerContractReadinessStatus,
    build_broker_contract_readiness,
    build_broker_contract_readiness_batch,
)
from broker_contract.resolver import (
    BrokerContractResolution,
    BrokerContractResolutionStatus,
    OptionContractRequest,
    TokenCoverageError,
    resolve_option_contract,
)

__all__ = [
    "BrokerContractReadiness",
    "BrokerContractReadinessStatus",
    "BrokerContractResolution",
    "BrokerContractResolutionStatus",
    "InstrumentResolutionHealthPanel",
    "InstrumentResolutionHealthStatus",
    "OptionContractRequest",
    "TokenCoverageError",
    "build_broker_contract_readiness",
    "build_broker_contract_readiness_batch",
    "build_instrument_resolution_health_panel",
    "instrument_resolution_health_schema_contract",
    "resolve_option_contract",
]