# import simpy
# import plotly.express as px
# import plotly.graph_objects as go

# # ---------------------------
# # Global Constants and Settings
# # ---------------------------
# STORAGE_COST_PER_UNIT = 0.5  # Cost per unit of stored inventory
# BACKORDER_PENALTY_COST_PER_UNIT = 1  # Cost penalty per unit of backorder

# WEEKS_TO_PLAY = 100  # Total simulation period (in weeks)
# QUEUE_DELAY_WEEKS = 2  # Delay (in weeks) for orders/deliveries

# # Initial conditions
# INITIAL_STOCK = 12
# INITIAL_COST = 0
# INITIAL_CURRENT_ORDERS = 0

# # Customer ordering settings
# CUSTOMER_INITIAL_ORDERS = 5
# CUSTOMER_SUBSEQUENT_ORDERS = 9

# # Target stock level
# TARGET_STOCK = 12


# # ---------------------------
# # Customer Class
# # ---------------------------
# class Customer:
#     def __init__(self):
#         self.totalBeerReceived = 0

#     def RecieveFromRetailer(self, amountReceived):
#         self.totalBeerReceived += amountReceived

#     def CalculateOrder(self, weekNum):
#         if weekNum <= 5:
#             return CUSTOMER_INITIAL_ORDERS
#         else:
#             return CUSTOMER_SUBSEQUENT_ORDERS

#     def GetBeerReceived(self):
#         return self.totalBeerReceived


# # ---------------------------
# # SupplyChainQueue Class
# # ---------------------------
# class SupplyChainQueue:
#     def __init__(self, queueLength):
#         self.queueLength = queueLength
#         self.data = []  # internal FIFO list

#     def PushEnvelope(self, numberOfCasesToOrder):
#         orderSuccessfullyPlaced = False
#         if len(self.data) < self.queueLength:
#             self.data.append(numberOfCasesToOrder)
#             orderSuccessfullyPlaced = True
#         return orderSuccessfullyPlaced

#     def AdvanceQueue(self):
#         if self.data:
#             self.data.pop(0)

#     def PopEnvelope(self):
#         if len(self.data) >= 1:
#             quantityDelivered = self.data[0]
#             self.AdvanceQueue()
#         else:
#             quantityDelivered = 0
#         return quantityDelivered

#     def PrettyPrint(self):
#         print(self.data)


# # ---------------------------
# # SupplyChainActor Base Class
# # ---------------------------
# class SupplyChainActor:
#     def __init__(
#         self,
#         incomingOrdersQueue,
#         outgoingOrdersQueue,
#         incomingDeliveriesQueue,
#         outgoingDeliveriesQueue,
#     ):
#         self.currentStock = INITIAL_STOCK
#         self.currentOrders = INITIAL_CURRENT_ORDERS
#         self.costsIncurred = INITIAL_COST

#         self.incomingOrdersQueue = incomingOrdersQueue
#         self.outgoingOrdersQueue = outgoingOrdersQueue
#         self.incomingDeliveriesQueue = incomingDeliveriesQueue
#         self.outgoingDeliveriesQueue = outgoingDeliveriesQueue

#         self.lastOrderQuantity = 0

#     def PlaceOutgoingDelivery(self, amountToDeliver):
#         if self.outgoingDeliveriesQueue is not None:
#             self.outgoingDeliveriesQueue.PushEnvelope(amountToDeliver)

#     def PlaceOutgoingOrder(self, weekNum):
#         if weekNum <= 4:
#             amountToOrder = 4
#         else:
#             amountToOrder = 0.5 * self.currentOrders
#             if (TARGET_STOCK - self.currentStock) > 0:
#                 amountToOrder += TARGET_STOCK - self.currentStock
#         if self.outgoingOrdersQueue is not None:
#             self.outgoingOrdersQueue.PushEnvelope(amountToOrder)
#         self.lastOrderQuantity = amountToOrder

#     def ReceiveIncomingDelivery(self):
#         if self.incomingDeliveriesQueue is not None:
#             quantityReceived = self.incomingDeliveriesQueue.PopEnvelope()
#             if quantityReceived > 0:
#                 self.currentStock += quantityReceived

#     def ReceiveIncomingOrders(self):
#         if self.incomingOrdersQueue is not None:
#             thisOrder = self.incomingOrdersQueue.PopEnvelope()
#             if thisOrder > 0:
#                 self.currentOrders += thisOrder

#     def CalcBeerToDeliver(self):
#         deliveryQuantity = 0
#         if self.currentStock >= self.currentOrders:
#             deliveryQuantity = self.currentOrders
#             self.currentStock -= deliveryQuantity
#             self.currentOrders -= deliveryQuantity
#         elif self.currentStock > 0:
#             deliveryQuantity = self.currentStock
#             self.currentStock = 0
#             self.currentOrders -= deliveryQuantity
#         return deliveryQuantity

#     def CalcCostForTurn(self):
#         inventoryStorageCost = self.currentStock * STORAGE_COST_PER_UNIT
#         backorderPenaltyCost = self.currentOrders * BACKORDER_PENALTY_COST_PER_UNIT
#         return inventoryStorageCost + backorderPenaltyCost

#     def GetCostIncurred(self):
#         return self.costsIncurred

#     def GetLastOrderQuantity(self):
#         return self.lastOrderQuantity

#     def CalcEffectiveInventory(self):
#         return self.currentStock - self.currentOrders


# # ---------------------------
# # Retailer Class
# # ---------------------------
# class Retailer(SupplyChainActor):
#     def __init__(
#         self,
#         incomingOrdersQueue,
#         outgoingOrdersQueue,
#         incomingDeliveriesQueue,
#         outgoingDeliveriesQueue,
#         theCustomer,
#     ):
#         super().__init__(
#             incomingOrdersQueue,
#             outgoingOrdersQueue,
#             incomingDeliveriesQueue,
#             outgoingDeliveriesQueue,
#         )
#         self.customer = theCustomer

#     def ReceiveIncomingOrderFromCustomer(self, weekNum):
#         self.currentOrders += self.customer.CalculateOrder(weekNum)

#     def ShipOutgoingDeliveryToCustomer(self):
#         self.customer.RecieveFromRetailer(self.CalcBeerToDeliver())

#     def TakeTurn(self, weekNum):
#         # 1. Receive new delivery from the wholesaler
#         self.ReceiveIncomingDelivery()

#         # 2. Receive new order from the customer
#         self.ReceiveIncomingOrderFromCustomer(weekNum)

#         # 3. Ship delivery to the customer (fixed early, then dynamic)
#         if weekNum <= 4:
#             self.customer.RecieveFromRetailer(4)
#         else:
#             self.customer.RecieveFromRetailer(self.CalcBeerToDeliver())

#         # 4. Place an outgoing order to the wholesaler
#         self.PlaceOutgoingOrder(weekNum)

#         # 5. Update cost incurred
#         self.costsIncurred += self.CalcCostForTurn()


# # ---------------------------
# # Wholesaler Class
# # ---------------------------
# class Wholesaler(SupplyChainActor):
#     def __init__(
#         self,
#         incomingOrdersQueue,
#         outgoingOrdersQueue,
#         incomingDeliveriesQueue,
#         outgoingDeliveriesQueue,
#     ):
#         super().__init__(
#             incomingOrdersQueue,
#             outgoingOrdersQueue,
#             incomingDeliveriesQueue,
#             outgoingDeliveriesQueue,
#         )

#     def TakeTurn(self, weekNum):
#         self.ReceiveIncomingDelivery()
#         self.ReceiveIncomingOrders()
#         if weekNum <= 4:
#             self.PlaceOutgoingDelivery(4)
#         else:
#             self.PlaceOutgoingDelivery(self.CalcBeerToDeliver())
#         self.PlaceOutgoingOrder(weekNum)
#         self.costsIncurred += self.CalcCostForTurn()


# # ---------------------------
# # Distributor Class
# # ---------------------------
# class Distributor(SupplyChainActor):
#     def __init__(
#         self,
#         incomingOrdersQueue,
#         outgoingOrdersQueue,
#         incomingDeliveriesQueue,
#         outgoingDeliveriesQueue,
#     ):
#         super().__init__(
#             incomingOrdersQueue,
#             outgoingOrdersQueue,
#             incomingDeliveriesQueue,
#             outgoingDeliveriesQueue,
#         )

#     def TakeTurn(self, weekNum):
#         self.ReceiveIncomingDelivery()
#         self.ReceiveIncomingOrders()
#         if weekNum <= 4:
#             self.PlaceOutgoingDelivery(4)
#         else:
#             self.PlaceOutgoingDelivery(self.CalcBeerToDeliver())
#         self.PlaceOutgoingOrder(weekNum)
#         self.costsIncurred += self.CalcCostForTurn()


# # ---------------------------
# # Factory Class
# # ---------------------------
# class Factory(SupplyChainActor):
#     def __init__(
#         self,
#         incomingOrdersQueue,
#         outgoingOrdersQueue,
#         incomingDeliveriesQueue,
#         outgoingDeliveriesQueue,
#         productionDelayWeeks,
#     ):
#         super().__init__(
#             incomingOrdersQueue,
#             outgoingOrdersQueue,
#             incomingDeliveriesQueue,
#             outgoingDeliveriesQueue,
#         )
#         # Production delay queue simulates brewing time
#         self.BeerProductionDelayQueue = SupplyChainQueue(productionDelayWeeks)
#         # Preload production queue for early stability
#         self.BeerProductionDelayQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
#         self.BeerProductionDelayQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)

#     def ProduceBeer(self, weekNum):
#         if weekNum <= 4:
#             amountToOrder = 4
#         else:
#             amountToOrder = 0.5 * self.currentOrders
#             if (TARGET_STOCK - self.currentStock) > 0:
#                 amountToOrder += TARGET_STOCK - self.currentStock
#         self.BeerProductionDelayQueue.PushEnvelope(amountToOrder)
#         self.lastOrderQuantity = amountToOrder

#     def FinishProduction(self):
#         amountProduced = self.BeerProductionDelayQueue.PopEnvelope()
#         if amountProduced > 0:
#             self.currentStock += amountProduced

#     def TakeTurn(self, weekNum):
#         self.FinishProduction()
#         self.ReceiveIncomingOrders()
#         if weekNum <= 4:
#             self.PlaceOutgoingDelivery(4)
#         else:
#             self.PlaceOutgoingDelivery(self.CalcBeerToDeliver())
#         self.ProduceBeer(weekNum)
#         self.costsIncurred += self.CalcCostForTurn()


# # ---------------------------
# # SupplyChainStatistics Class
# # ---------------------------
# class SupplyChainStatistics:
#     def __init__(self):
#         self.retailerCostsOverTime = []
#         self.wholesalerCostsOverTime = []
#         self.distributorCostsOverTime = []
#         self.factoryCostsOverTime = []
#         self.retailerOrdersOverTime = []
#         self.wholesalerOrdersOverTime = []
#         self.distributorOrdersOverTime = []
#         self.factoryOrdersOverTime = []
#         self.retailerEffectiveInventoryOverTime = []
#         self.wholesalerEffectiveInventoryOverTime = []
#         self.distributorEffectiveInventoryOverTime = []
#         self.factoryEffectiveInventoryOverTime = []

#     def RecordRetailerOrders(self, retailerOrdersThisWeek):
#         self.retailerOrdersOverTime.append(retailerOrdersThisWeek)
#         print("Retailer Order:", self.retailerOrdersOverTime[-1])

#     def RecordWholesalerOrders(self, wholesalerOrdersThisWeek):
#         self.wholesalerOrdersOverTime.append(wholesalerOrdersThisWeek)
#         print("Wholesaler Order:", self.wholesalerOrdersOverTime[-1])

#     def RecordDistributorOrders(self, distributorOrdersThisWeek):
#         self.distributorOrdersOverTime.append(distributorOrdersThisWeek)
#         print("Distributor Order:", self.distributorOrdersOverTime[-1])

#     def RecordFactoryOrders(self, factoryOrdersThisWeek):
#         self.factoryOrdersOverTime.append(factoryOrdersThisWeek)
#         print("Factory Order:", self.factoryOrdersOverTime[-1])

#     def RecordRetailerCost(self, retailerCostsThisWeek):
#         self.retailerCostsOverTime.append(retailerCostsThisWeek)
#         print("Retailer Cost:", self.retailerCostsOverTime[-1])

#     def RecordWholesalerCost(self, wholesalerCostsThisWeek):
#         self.wholesalerCostsOverTime.append(wholesalerCostsThisWeek)
#         print("Wholesaler Cost:", self.wholesalerCostsOverTime[-1])

#     def RecordDistributorCost(self, distributorCostsThisWeek):
#         self.distributorCostsOverTime.append(distributorCostsThisWeek)
#         print("Distributor Cost:", self.distributorCostsOverTime[-1])

#     def RecordFactoryCost(self, factoryCostsThisWeek):
#         self.factoryCostsOverTime.append(factoryCostsThisWeek)
#         print("Factory Cost:", self.factoryCostsOverTime[-1])

#     def RecordRetailerEffectiveInventory(self, retailerEffectiveInventoryThisWeek):
#         self.retailerEffectiveInventoryOverTime.append(
#             retailerEffectiveInventoryThisWeek
#         )
#         print(
#             "Retailer Effective Inventory:", self.retailerEffectiveInventoryOverTime[-1]
#         )

#     def RecordWholesalerEffectiveInventory(self, wholesalerEffectiveInventoryThisWeek):
#         self.wholesalerEffectiveInventoryOverTime.append(
#             wholesalerEffectiveInventoryThisWeek
#         )
#         print(
#             "Wholesaler Effective Inventory:",
#             self.wholesalerEffectiveInventoryOverTime[-1],
#         )

#     def RecordDistributorEffectiveInventory(
#         self, distributorEffectiveInventoryThisWeek
#     ):
#         self.distributorEffectiveInventoryOverTime.append(
#             distributorEffectiveInventoryThisWeek
#         )
#         print(
#             "Distributor Effective Inventory:",
#             self.distributorEffectiveInventoryOverTime[-1],
#         )

#     def RecordFactoryEffectiveInventory(self, factoryEffectiveInventoryThisWeek):
#         self.factoryEffectiveInventoryOverTime.append(factoryEffectiveInventoryThisWeek)
#         print(
#             "Factory Effective Inventory:", self.factoryEffectiveInventoryOverTime[-1]
#         )

#     def PlotOrders(self):
#         fig = go.Figure()
#         weeks = list(range(0, WEEKS_TO_PLAY + 2))
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.retailerOrdersOverTime,
#                 mode="lines+markers",
#                 name="Retailer Orders",
#                 marker=dict(size=5),
#                 marker_color="rgb(215,48,39)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.wholesalerOrdersOverTime,
#                 mode="lines+markers",
#                 name="Wholesaler Orders",
#                 marker=dict(size=5),
#                 marker_color="rgb(255,186,0)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.distributorOrdersOverTime,
#                 mode="lines+markers",
#                 name="Distributor Orders",
#                 marker=dict(size=5),
#                 marker_color="rgb(126,2,114)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.factoryOrdersOverTime,
#                 mode="lines+markers",
#                 name="Factory Orders",
#                 marker=dict(size=5),
#                 marker_color="rgb(69,117,180)",
#             )
#         )
#         fig.update_layout(
#             title_text="*Orders Placed Over Time*",
#             xaxis_title="Weeks",
#             yaxis_title="Orders",
#             paper_bgcolor="rgba(0,0,0,0)",
#             height=580,
#         )
#         fig.update_xaxes(range=[0, WEEKS_TO_PLAY])
#         fig.show()

#     def PlotEffectiveInventory(self):
#         fig = go.Figure()
#         weeks = list(range(0, WEEKS_TO_PLAY + 2))
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.retailerEffectiveInventoryOverTime,
#                 mode="lines+markers",
#                 name="Retailer Inventory",
#                 marker=dict(size=5),
#                 marker_color="rgb(215,48,39)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.wholesalerEffectiveInventoryOverTime,
#                 mode="lines+markers",
#                 name="Wholesaler Inventory",
#                 marker=dict(size=5),
#                 marker_color="rgb(255,186,0)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.distributorEffectiveInventoryOverTime,
#                 mode="lines+markers",
#                 name="Distributor Inventory",
#                 marker=dict(size=5),
#                 marker_color="rgb(126,2,114)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.factoryEffectiveInventoryOverTime,
#                 mode="lines+markers",
#                 name="Factory Inventory",
#                 marker=dict(size=5),
#                 marker_color="rgb(69,117,180)",
#             )
#         )
#         fig.update_layout(
#             title_text="*Effective Inventory Over Time*",
#             xaxis_title="Weeks",
#             yaxis_title="Effective Inventory",
#             paper_bgcolor="rgba(0,0,0,0)",
#             height=580,
#         )
#         fig.update_xaxes(range=[0, WEEKS_TO_PLAY])
#         fig.show()

#     def PlotCosts(self):
#         fig = go.Figure()
#         weeks = list(range(0, WEEKS_TO_PLAY + 2))
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.retailerCostsOverTime,
#                 mode="lines+markers",
#                 name="Retailer Total Cost",
#                 marker=dict(size=5),
#                 marker_color="rgb(215,48,39)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.wholesalerCostsOverTime,
#                 mode="lines+markers",
#                 name="Wholesaler Total Cost",
#                 marker=dict(size=5),
#                 marker_color="rgb(255,186,0)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.distributorCostsOverTime,
#                 mode="lines+markers",
#                 name="Distributor Total Cost",
#                 marker=dict(size=5),
#                 marker_color="rgb(126,2,114)",
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=weeks,
#                 y=self.factoryCostsOverTime,
#                 mode="lines+markers",
#                 name="Factory Total Cost",
#                 marker=dict(size=5),
#                 marker_color="rgb(69,117,180)",
#             )
#         )
#         fig.update_layout(
#             title_text="*Cost Incurred Over Time*",
#             xaxis_title="Weeks",
#             yaxis_title="Cost ($)",
#             paper_bgcolor="rgba(0,0,0,0)",
#             height=580,
#         )
#         fig.update_xaxes(range=[0, WEEKS_TO_PLAY])
#         fig.show()


# # ---------------------------
# # SimPy Process: Supply Chain Simulation
# # ---------------------------
# def supply_chain_simulation(env):
#     # Initialize queues between each actor (orders and deliveries)
#     wholesalerRetailerTopQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
#     wholesalerRetailerBottomQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
#     distributorWholesalerTopQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
#     distributorWholesalerBottomQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
#     factoryDistributorTopQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
#     factoryDistributorBottomQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)

#     # Prepopulate queues with initial orders/deliveries for stability
#     for i in range(2):
#         wholesalerRetailerTopQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
#         wholesalerRetailerBottomQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
#         distributorWholesalerTopQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
#         distributorWholesalerBottomQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
#         factoryDistributorTopQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
#         factoryDistributorBottomQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)

#     # Instantiate the customer and the actors in the supply chain
#     theCustomer = Customer()
#     myRetailer = Retailer(
#         None,
#         wholesalerRetailerTopQueue,
#         wholesalerRetailerBottomQueue,
#         None,
#         theCustomer,
#     )
#     myWholesaler = Wholesaler(
#         wholesalerRetailerTopQueue,
#         distributorWholesalerTopQueue,
#         distributorWholesalerBottomQueue,
#         wholesalerRetailerBottomQueue,
#     )
#     myDistributor = Distributor(
#         distributorWholesalerTopQueue,
#         factoryDistributorTopQueue,
#         factoryDistributorBottomQueue,
#         distributorWholesalerBottomQueue,
#     )
#     myFactory = Factory(
#         factoryDistributorTopQueue,
#         None,
#         None,
#         factoryDistributorBottomQueue,
#         QUEUE_DELAY_WEEKS,
#     )

#     myStats = SupplyChainStatistics()

#     # Run the simulation week by week.
#     for thisWeek in range(WEEKS_TO_PLAY):
#         print("\n" + "-" * 49)
#         print(f" Week {thisWeek}")
#         print("-" * 49)

#         # Retailer's turn
#         myRetailer.TakeTurn(thisWeek)
#         myStats.RecordRetailerCost(myRetailer.GetCostIncurred())
#         myStats.RecordRetailerOrders(myRetailer.GetLastOrderQuantity())
#         myStats.RecordRetailerEffectiveInventory(myRetailer.CalcEffectiveInventory())

#         # Wholesaler's turn
#         myWholesaler.TakeTurn(thisWeek)
#         myStats.RecordWholesalerCost(myWholesaler.GetCostIncurred())
#         myStats.RecordWholesalerOrders(myWholesaler.GetLastOrderQuantity())
#         myStats.RecordWholesalerEffectiveInventory(
#             myWholesaler.CalcEffectiveInventory()
#         )

#         # Distributor's turn
#         myDistributor.TakeTurn(thisWeek)
#         myStats.RecordDistributorCost(myDistributor.GetCostIncurred())
#         myStats.RecordDistributorOrders(myDistributor.GetLastOrderQuantity())
#         myStats.RecordDistributorEffectiveInventory(
#             myDistributor.CalcEffectiveInventory()
#         )

#         # Factory's turn
#         myFactory.TakeTurn(thisWeek)
#         myStats.RecordFactoryCost(myFactory.GetCostIncurred())
#         myStats.RecordFactoryOrders(myFactory.GetLastOrderQuantity())
#         myStats.RecordFactoryEffectiveInventory(myFactory.CalcEffectiveInventory())

#         # Advance one week in the simulation.
#         yield env.timeout(1)

#     # After simulation ends, print and plot final statistics.
#     print("\n--- Final Statistics ----")
#     print("Beer received by customer: {0}".format(theCustomer.GetBeerReceived()))

#     myStats.PlotOrders()
#     myStats.PlotEffectiveInventory()
#     myStats.PlotCosts()


# # ---------------------------
# # Main: Create Environment and Run Simulation
# # ---------------------------
# env = simpy.Environment()
# env.process(supply_chain_simulation(env))
# env.run()
