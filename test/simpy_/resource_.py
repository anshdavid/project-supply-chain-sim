import simpy

env = simpy.Environment()

resource = simpy.Resource(env, capacity=2)


def print_stats(res: simpy.Resource):
    """
    Prints the current status of a SimPy Resource.

    Args:
        res (simpy.Resource): The resource whose statistics are to be printed.

    Outputs:
        Prints the number of allocated slots, the list of current users, and the queue of pending events for the resource.
    """
    print(f"{res.count} of {res.capacity} slots are allocated.")
    print(f"  Users: {res.users}")
    print(f"  Queued events: {res.queue}")


def user(res: simpy.Resource):
    """
    SimPy process function that requests and releases a resource, printing its statistics before, during, and after usage.

    Args:
        res (simpy.Resource): The resource to be requested and released.

    Yields:
        simpy.events.Event: Event yielded while waiting for the resource request to be granted.
    """
    with res.request() as req:
        print_stats(res)
        yield req


procs = [
    env.process(user(resource)),
    env.process(user(resource)),
    env.process(user(resource)),
]
env.run()
