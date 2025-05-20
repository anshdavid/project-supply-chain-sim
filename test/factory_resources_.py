from collections import namedtuple
from typing import Any, Callable
import simpy

Machine = namedtuple("Machine", "size, duration")
m1 = Machine(1, 2)  # Small and slow
m2 = Machine(2, 1)  # Big and fast
m3 = Machine(2, 5)  # Big and slow

env = simpy.Environment()
machine_shop = simpy.FilterStore(env, capacity=2)
machine_shop.put(m1)
machine_shop.put(m2)
machine_shop.put(m3)


def test1():
    def user(name, env: simpy.Environment, ms: simpy.FilterStore, size: int):
        machine = yield ms.get(lambda machine: machine.size == size)

        print(name, "got", machine, "at", env.now)
        yield env.timeout(machine.duration)
        yield ms.put(machine)
        print(name, "released", machine, "at", env.now)

    _ = [env.process(user(i, env, machine_shop, 2)) for i in range(10)]
    env.run()


def test2():

    print(machine_shop.items)

    items = [1, 2, 3]
    filter_expr: Callable[[Any], bool] = lambda item: item > 1
    filtered_items = filter(filter_expr, items)

    print(list(filtered_items))  # Output: [2, 3]


test1()
# test2()
