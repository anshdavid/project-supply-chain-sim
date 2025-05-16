from __future__ import annotations

from pydantic import BaseModel, Field
from src.machine import QMachine
from src.environment import QEnvironment


class QRepairman:

    class QRepairmanSchema(BaseModel):
        name: str = Field(description="Name of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0, le=1000)
        downtime: float = Field(description="Downtime for a repairman", gt=0, le=1000)

    class QRepairmanLog(BaseModel):
        timestamp: float
        repairman_name: str = Field(description="Name of the repairman")
        machine_name: str = Field(description="Name of the machine")
        state: str = Field(description="State of the repairman")

    class QRepairmanState(BaseModel):
        name: str = Field(description="Name of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0, le=1000)
        downtime: float = Field(description="Downtime for a repairman", gt=0, le=1000)

        logs: list[QRepairman.QRepairmanLog] = []

    def __init__(self, name: str, time_to_repair: float = 30, downtime: float = 1.5):

        self.repairman_state: QRepairman.QRepairmanState = QRepairman.QRepairmanState(
            name=name,
            time_to_repair=time_to_repair,
            downtime=downtime,
        )

    def start_repair(self, env: QEnvironment, machine: QMachine):
        if machine.machine_state.is_broken():
            machine.machine_state.set_repairing()
            yield env.timeout(self.repairman_state.time_to_repair)
            machine.machine_state.set_idle()
            machine.restart()
