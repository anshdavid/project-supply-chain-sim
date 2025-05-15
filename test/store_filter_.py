from typing import cast
import simpy
import simpy.events


class Material:
    def __init__(self, name):
        self.name = name


class Machine(object):
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.inputs = simpy.FilterStore(env)

    def run(self):
        mat = [
            self.inputs.get(lambda i, itemname=itemname: i.name == itemname) for itemname in ["mat3", "mat3", "mat3"]
        ]

        res: simpy.events.ConditionValue = yield self.env.any_of(mat)
        print(type(res))
        print([cast(Material, res.events[i].value).name for i in range(len(res.events))])


def input_materials(env: simpy.Environment, m: Machine):
    for i in range(5):
        m.inputs.put(Material("mat" + str(i)))
        m.inputs.put(Material("mat" + str(i)))
        yield env.timeout(1)


environment = simpy.Environment()
machine = Machine(environment)

environment.process(input_materials(environment, machine))
environment.process(machine.run())
environment.run()
