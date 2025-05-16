from __future__ import annotations
from typing import Mapping, Union


from src.environment import QEnvironment
from src.machine import QMachine
from src.repairman import QRepairman
from src.resources import QMaterial


class QFactory:

    class QFactorySchema:
        dummy: int

    class QFactoryLog:
        dummy: int = 1

    class QFactoryState:
        name: str
        no_machines: int = 0
        machine_list: list[QMachine.QMachineState] = []

        no_repairman: int = 0
        repairman_list: list[QRepairman.QRepairmanState] = []

        logs: list[QFactory.QFactoryLog] = []

    @classmethod
    def from_config(
        cls,
        env: QEnvironment,
        config: Mapping[
            str,
            Union[list[QMaterial.QMaterialSchema], list[QMachine.QMachineSchema], list[QRepairman.QRepairmanSchema]],
        ],
    ) -> "QFactory":
        factory_materials = []
        factory_machines = []
        factory_repairman = []

        factory_instance = cls(env=env)

        for idm, material in enumerate(config.get("materials", [])):
            if not isinstance(material, QMaterial.QMaterialSchema):
                raise TypeError(f"Expected QMaterial.QMaterialSchema, got {type(material)} for item {idm}")
            factory_materials.append(
                QMaterial(
                    material_name=material.material_name,
                    material_id=material.material_id,
                    env=env,
                    capacity=material.capacity,
                    init=material.init,
                )
            )

        for idm, machine in enumerate(config.get("machines", [])):
            if not isinstance(machine, QMachine.QMachineSchema):
                raise TypeError(f"Expected QMachine.QMachineSchema, got {type(machine)} for item {idm}")
            factory_machines.append(QMachine.from_config(env=env, factory=factory_instance, config=machine))

        factory_instance.setup(
            materials=factory_materials,
            machines=factory_machines,
            repairman=factory_repairman,
        )

        return factory_instance

    def __init__(self, env: QEnvironment):
        self.env = env
        self.factory_state: QFactory.QFactoryState = QFactory.QFactoryState()

    def setup(self, materials: list[QMaterial], machines: list[QMachine], repairman: list[QRepairman]):
        self.materials = materials
        self.machines = machines
        self.repairman = repairman
