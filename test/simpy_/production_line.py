"""
Quick demo of a production line where:
first station produces 3 entites a a time using 1 resoure type A
second station needs both a resource typa A and a resource type B
third station using a resource type B

set it up so the number of each station can be changed.

programmer: Michael R. Gibbs
"""

import simpy


class Prod:
    """
    simple class to model a entity/product
    has a unique id for tracking
    """

    next_id = 1

    def __init__(self):
        self.id = self.__class__.next_id

        self.__class__.next_id += 1


class Station_1_Process:
    """
    Station 1

    producess the entites in 3 at a time
    """

    def __init__(self, env, res_pool_a, next_station):
        """
        cache the env, and resource pool
        """
        self.env = env
        self.res_pool_a = res_pool_a
        self.next_station = next_station

        # start the process that creates products
        self.env.process(self.station_process())

    def station_process(self):
        """
        since this process creates entites and
        does not wait for entites to show up
        it runs in a infinate loop,
        but it does sieze and release the resource
        so it can be shared with other stations
        """

        while True:
            with self.res_pool_a.request() as req_a:

                # wait for resource
                yield req_a
                print(f"{self.env.now:.2f} Station 1 has resource")

                # make 3 entites
                for i in range(3):
                    # make entity
                    yield self.env.timeout(3)
                    prod = Prod()

                    # send to next station
                    self.env.process(self.next_station.station_process(prod))
                    print(f"{self.env.now:.2f} station 1 has made product {prod.id}")

            print(f"{self.env.now:.2f} station 1 has released its resource")


class Station_2_Process:
    """
    Station 2

    needs a two resouces, both a type A and type B
    """

    def __init__(self, env, res_pool_a, res_pool_b, station_2_pool, next_station):
        """
        cache the env, and resource pool
        """
        self.env = env
        self.res_pool_a = res_pool_a
        self.res_pool_b = res_pool_b
        self.next_station = next_station

        # controls how many station 2 are running
        self.sation_2_pool = station_2_pool

    def station_process(self, prod):
        """
        gets both resources and does next step
        """

        # get a station which also queues up the prods waitting for station 2
        with self.sation_2_pool.request() as stat:
            yield stat
            print(f"{self.env.now:.2f} station 2 has started processing product {prod.id}")

            # get both resources
            with self.res_pool_a.request() as req_a:
                with self.res_pool_b.request() as req_b:

                    # wait for both resources
                    yield self.env.all_of([req_a, req_b])
                    print(f"{self.env.now:.2f} station 2 has both resources for product {prod.id}")

                    # do process
                    yield self.env.timeout(1)

                    # send to next station
                    self.env.process(self.next_station.station_process(prod))

        print(f"{self.env.now:.2f} station 2 has finished product {prod.id}")


class Station_3_Process:
    """
    Station 3

    needs just type B resource
    No next station
    """

    def __init__(
        self,
        env,
        res_pool_b,
        station_3_pool,
    ):
        """
        cache the env, and resource pool
        """
        self.env = env
        self.res_pool_b = res_pool_b

        # controls how many station 3 are running
        self.sation_3_pool = station_3_pool

    def station_process(self, prod):
        """
        gets both resources and does next step
        """

        # get a station which also queues up prods waitting for station 3
        with self.sation_3_pool.request() as stat:
            yield stat
            print(f"{self.env.now:.2f} station 3 has started working on product {prod.id}")

            # get resources
            with self.res_pool_b.request() as req_b:

                # wait for both resources
                yield req_b
                print(f"{self.env.now:.2f} station 3 has a resource to process product {prod.id}")

                # do process
                yield self.env.timeout(2)

        # done processing, no next station
        print(f"{self.env.now:.2f} station 3 has finished product {prod.id}")


# boot up
env = simpy.Environment()

# define each resource type
resource_pool_A = simpy.Resource(env, capacity=1)
resource_pool_B = simpy.Resource(env, capacity=1)

# use resouces to define the number of station 2 and 3,
# station 1 is a generator and gets defined later
station_2_pool = simpy.Resource(env, capacity=1)
station_3_pool = simpy.Resource(env, capacity=1)

station_3 = Station_3_Process(env, resource_pool_B, station_3_pool)
station_2 = Station_2_Process(env, resource_pool_A, resource_pool_B, station_2_pool, station_3)

# there is no products 'watting' for station 1
# because station 1 is generating the prodeucts.
# use a loop to create each station 1 generater
for i in range(1):
    station_1 = Station_1_Process(env, resource_pool_A, station_2)

env.run(50)
print("done")
