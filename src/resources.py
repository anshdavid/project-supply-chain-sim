from pydantic import BaseModel
from simpy import Container, Environment
from simpy.resources.container import ContainerAmount


class QMaterial(Container):
    """
    A container that can be used to manage resources in a simulation environment.
    It extends the simpy Container class to include additional functionality for resource management.
    """

    class QMaterialSchema(BaseModel):
        """
        A model that can be used to manage resources in a simulation environment.
        """

        material_name: str
        material_id: str
        capacity: ContainerAmount = float("inf")
        init: ContainerAmount = 0

    class QMaterialState(BaseModel):
        """
        A model that can be used to manage resources in a simulation environment.
        """

        material_name: str
        material_id: str
        capacity: ContainerAmount = float("inf")
        init: ContainerAmount = 0

    def __init__(
        self,
        material_name: str,
        material_id: str,
        env: Environment,
        capacity: ContainerAmount = float("inf"),
        init: ContainerAmount = 0,
    ):
        """
        Initializes a new instance of the class.
        Args:
            material_name (str): The name of the material.
            material_id (str): The resource ID associated with the material.
            env (Environment): The simulation environment.
            capacity (ContainerAmount, optional): The maximum capacity of the container. Defaults to infinity.
            init (ContainerAmount, optional): The initial amount in the container. Defaults to 0.
        """
        super().__init__(env=env, capacity=capacity, init=init)
        self.q_material_name = material_name
        self.q_material_id = material_id
