from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NodeSnapshot:
    """One reading of a node, as stored and as reported."""

    node_id: int
    taken_at: datetime  # UTC
    operator_nym: float  # pledge plus compounded operator rewards, per the mixnet contract
    pledge_nym: float
    delegates_nym: float
    profit_margin: float  # fraction: 0.2 means 20 %
    operating_cost_nym: float  # per rewarding interval
    performance: float | None  # 0 to 1
    uptime_percent: int | None
    uptime_date: str | None  # the day the uptime figure refers to

    @property
    def day(self) -> str:
        return self.taken_at.date().isoformat()

    @property
    def total_stake_nym(self) -> float:
        return self.operator_nym + self.delegates_nym

    @property
    def operator_rewards_nym(self) -> float:
        return self.operator_nym - self.pledge_nym
