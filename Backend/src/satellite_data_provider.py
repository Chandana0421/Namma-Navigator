import random


class SatelliteDataProvider:

    def get_traffic_density(self, area: str) -> float:
        """
        Analyzes satellite imagery to determine traffic density in a given area.

        Args:
            area (str): The area to analyze (e.g., 'Koramangala').

        Returns:
            float: A traffic density score from 0.0 (no traffic) to 1.0 (heavy congestion).
        """
        # Mock implementation: returns a random density score.
        print(f"🛰️  [SATELLITE MOCK] Analyzing traffic density for {area}...")
        return round(random.uniform(0.1, 0.9), 2)

    def detect_large_gatherings(self, area: str) -> bool:
        """
        Analyzes satellite imagery to detect large gatherings of people or vehicles.

        Args:
            area (str): The area to analyze.

        Returns:
            bool: True if a large gathering is detected, False otherwise.
        """
        # Mock implementation: randomly detects a gathering.
        print(
            f"🛰️  [SATELLITE MOCK] Scanning for large gatherings in {area}...")
        return random.choice([True, False])
