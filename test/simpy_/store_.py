import simpy

environment = simpy.Environment()
store = simpy.Store(environment, capacity=2)
resource = simpy.Resource(environment, capacity=2)


def producer(env: simpy.Environment, store: simpy.Store):
    for i in range(100):
        yield env.timeout(2)
        yield store.put(f"spam {i}")
        print("Produced spam at sim_time:", env.now)


def consumer(name: str, env: simpy.Environment, store: simpy.Store):
    while True:
        yield env.timeout(1)
        print(name, "requesting spam at sim_time:", env.now)
        item = yield store.get()
        print(name, "got", item, "at sim_time:", env.now)


prod = environment.process(producer(environment, store))
consumers = [environment.process(consumer(f"Consumer {i}", environment, store)) for i in range(2)]

environment.run(until=5)
