import simpy
from simpy.resources.resource import Request


class MonitoredResource(simpy.Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = []

    def do_something(self):
        # This method can be used to perform some action with the data
        # collected in the resource.
        self.data.append("did something")


def test_process(env: simpy.Environment, res: MonitoredResource):
    with res.request() as req:
        yield req
        req.resource.do_something()
        yield env.timeout(1)


env = simpy.Environment()

res = MonitoredResource(env, capacity=1)
p1 = env.process(test_process(env, res))
p2 = env.process(test_process(env, res))
env.run()

print(res.data)
