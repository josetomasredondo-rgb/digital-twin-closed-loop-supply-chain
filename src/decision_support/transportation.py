"""
Transportation modes with associated costs and emissions.
"""


class TransportationMode:
    """Base class for transportation modes."""
    
    def __init__(self, name, mode_type, cost_per_unit, emissions_per_unit, 
                 capacity, speed_factor=1.0):
        """
        Args:
            name: Name of the transportation mode
            mode_type: Type of transportation (e.g., 'truck', 'air', 'sea')
            cost_per_unit: Cost per unit transported
            emissions_per_unit: CO2 emissions per unit transported (kg)
            capacity: Maximum capacity per shipment
            speed_factor: Relative speed factor (1.0 = baseline)
        """
        self.name = name
        self.mode_type = mode_type
        self.cost_per_unit = cost_per_unit
        self.emissions_per_unit = emissions_per_unit
        self.capacity = capacity
        self.speed_factor = speed_factor
    
    def calculate_cost(self, quantity):
        """Calculate transport cost for given quantity."""
        return quantity * self.cost_per_unit
    
    def calculate_emissions(self, quantity):
        """Calculate emissions for given quantity."""
        return quantity * self.emissions_per_unit
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.name}, type={self.mode_type})"


class TruckTransport(TransportationMode):
    """Road transport via truck."""
    
    def __init__(self, name="Truck_Transport", cost_per_unit=2.0, 
                 emissions_per_unit=0.15, capacity=1000, speed_factor=1.0):
        super().__init__(name, "truck", cost_per_unit, emissions_per_unit, 
                        capacity, speed_factor)


class AirTransport(TransportationMode):
    """Air transport via airplane."""
    
    def __init__(self, name="Air_Transport", cost_per_unit=8.0, 
                 emissions_per_unit=0.85, capacity=500, speed_factor=3.0):
        super().__init__(name, "air", cost_per_unit, emissions_per_unit, 
                        capacity, speed_factor)


class SeaTransport(TransportationMode):
    """Sea transport via ship."""
    
    def __init__(self, name="Sea_Transport", cost_per_unit=1.5, 
                 emissions_per_unit=0.05, capacity=5000, speed_factor=0.5):
        super().__init__(name, "sea", cost_per_unit, emissions_per_unit, 
                        capacity, speed_factor)


# Default transportation modes configuration
DEFAULT_TRANSPORT_MODES = {
    "truck": TruckTransport(),
    "air": AirTransport(),
    "sea": SeaTransport(),
}
