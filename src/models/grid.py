class Grid:
    def __init__(self, price_profile, sell_price_profile=None):
        self.price_profile = price_profile  # €/kWh per hour (buying)
        self.sell_price_profile = sell_price_profile if sell_price_profile is not None else [p * 0.8 for p in price_profile]  # €/kWh per hour (selling, default 80% of buy price)

    def get_price(self, hour):
        """Return electricity price for buying energy for a specific hour."""
        return self.price_profile[hour % len(self.price_profile)]  # Cyclic pricing

    def get_sell_price(self, hour):
        """Return electricity price for selling energy for a specific hour."""
        return self.sell_price_profile[hour % len(self.sell_price_profile)]  # Cyclic sell pricing