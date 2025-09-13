class Grid:
    def __init__(self, price_profile):
        self.price_profile = price_profile  # €/kWh per hour

    def get_price(self, hour):
        """Return electricity price for a specific hour."""
        return self.price_profile[hour % len(self.price_profile)]  # Cyclic pricing