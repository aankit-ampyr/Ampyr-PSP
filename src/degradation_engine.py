"""
Degradation Engine Module

Advanced battery degradation modeling including:
- Rainflow cycle counting (ASTM E1049-85)
- Calendar aging with temperature/SOC factors
- Palmgren-Miner damage accumulation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np


# =============================================================================
# CONFIGURATION
# =============================================================================

# Default DoD stress curve for LFP chemistry
# Maps depth-of-discharge (%) to stress factor relative to 80% DoD baseline
DEFAULT_DOD_STRESS_CURVE = {
    10: 0.3,    # 10% DoD = 0.3x damage vs 80% DoD
    20: 0.5,
    40: 0.7,
    60: 0.85,
    80: 1.0,    # Baseline
    100: 1.2    # Deep discharge = 1.2x damage
}


@dataclass
class DegradationConfig:
    """Configuration for degradation calculations."""

    # Calendar aging
    calendar_degradation_rate: float = 0.02  # 2% per year baseline
    include_calendar_aging: bool = True

    # Cycle aging (DoD curve - Palmgren-Miner)
    dod_stress_curve: Dict[float, float] = field(default_factory=lambda: DEFAULT_DOD_STRESS_CURVE.copy())
    cycle_base_degradation: float = 0.0015  # 0.15% per equivalent full cycle
    use_rainflow_counting: bool = True

    # Strategy
    strategy: str = 'standard'  # 'standard', 'overbuild', 'augmentation'
    overbuild_factor: float = 0.20  # 20% overbuild
    augmentation_year: int = 8  # Year to add capacity


@dataclass
class RainflowCycle:
    """Single cycle extracted from rainflow counting."""
    range_pct: float      # Depth of discharge (%)
    mean_pct: float       # Mean SOC (%)
    count: float          # Cycle count (0.5 for half-cycle, 1.0 for full)
    start_idx: int = 0    # Start index in SOC history
    end_idx: int = 0      # End index in SOC history


@dataclass
class DegradationResult:
    """Results from degradation calculation."""
    # Cycle-based
    total_cycles_simple: float = 0.0       # Simple cycle count
    equivalent_full_cycles: float = 0.0    # DoD-weighted cycles
    cycle_degradation_pct: float = 0.0     # Degradation from cycling

    # Calendar-based
    calendar_degradation_pct: float = 0.0  # Degradation from time

    # Combined
    total_degradation_pct: float = 0.0     # Total capacity loss

    # Details
    rainflow_cycles: List[RainflowCycle] = field(default_factory=list)
    dod_distribution: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# RAINFLOW CYCLE COUNTING
# =============================================================================

class RainflowCounter:
    """
    Implements ASTM E1049-85 rainflow cycle counting algorithm.

    Rainflow counting identifies load cycles in variable amplitude loading
    by extracting closed hysteresis loops from the load history.
    """

    def __init__(self, soc_history: List[float]):
        """
        Initialize with SOC history.

        Args:
            soc_history: List of SOC values (0-100 as percentages)
        """
        self.soc_history = np.array(soc_history)
        self.cycles: List[RainflowCycle] = []
        self.reversals: List[Tuple[int, float]] = []

    def _find_reversals(self) -> List[Tuple[int, float]]:
        """
        Find turning points (local maxima and minima) in SOC history.

        Returns:
            List of (index, value) tuples for each reversal point
        """
        if len(self.soc_history) < 3:
            return [(i, v) for i, v in enumerate(self.soc_history)]

        reversals = [(0, self.soc_history[0])]  # Start point

        for i in range(1, len(self.soc_history) - 1):
            prev_val = self.soc_history[i - 1]
            curr_val = self.soc_history[i]
            next_val = self.soc_history[i + 1]

            # Check if local maximum or minimum
            is_max = curr_val > prev_val and curr_val > next_val
            is_min = curr_val < prev_val and curr_val < next_val

            if is_max or is_min:
                reversals.append((i, curr_val))

        reversals.append((len(self.soc_history) - 1, self.soc_history[-1]))  # End point
        return reversals

    def extract_cycles(self) -> List[RainflowCycle]:
        """
        Extract cycles using the four-point rainflow algorithm.

        Returns:
            List of RainflowCycle objects
        """
        self.reversals = self._find_reversals()

        if len(self.reversals) < 2:
            return []

        # Working array of reversal values
        points = [(idx, val) for idx, val in self.reversals]
        self.cycles = []

        i = 0
        while len(points) >= 4:
            # Get four consecutive points
            p1_idx, p1 = points[i]
            p2_idx, p2 = points[i + 1] if i + 1 < len(points) else (0, 0)
            p3_idx, p3 = points[i + 2] if i + 2 < len(points) else (0, 0)
            p4_idx, p4 = points[i + 3] if i + 3 < len(points) else (0, 0)

            if i + 3 >= len(points):
                break

            # Calculate ranges
            range_1 = abs(p2 - p1)
            range_2 = abs(p3 - p2)
            range_3 = abs(p4 - p3)

            # Check if middle range is enclosed
            if range_2 <= range_1 and range_2 <= range_3:
                # Extract full cycle (points 2 and 3)
                cycle_range = range_2
                cycle_mean = (p2 + p3) / 2

                self.cycles.append(RainflowCycle(
                    range_pct=cycle_range,
                    mean_pct=cycle_mean,
                    count=1.0,
                    start_idx=p2_idx,
                    end_idx=p3_idx
                ))

                # Remove points 2 and 3
                del points[i + 2]
                del points[i + 1]

                # Reset to beginning
                i = max(0, i - 1)
            else:
                i += 1

            if i + 3 >= len(points):
                break

        # Remaining points form half-cycles (residual)
        for j in range(len(points) - 1):
            p1_idx, p1 = points[j]
            p2_idx, p2 = points[j + 1]
            cycle_range = abs(p2 - p1)
            cycle_mean = (p1 + p2) / 2

            if cycle_range > 0.5:  # Ignore very small fluctuations
                self.cycles.append(RainflowCycle(
                    range_pct=cycle_range,
                    mean_pct=cycle_mean,
                    count=0.5,  # Half-cycle
                    start_idx=p1_idx,
                    end_idx=p2_idx
                ))

        return self.cycles

    def calculate_equivalent_full_cycles(
        self,
        dod_curve: Dict[float, float] = None
    ) -> float:
        """
        Calculate equivalent full cycles using Palmgren-Miner damage accumulation.

        Args:
            dod_curve: Dict mapping DoD% to stress factor

        Returns:
            Equivalent number of full cycles at 80% DoD
        """
        if dod_curve is None:
            dod_curve = DEFAULT_DOD_STRESS_CURVE

        if not self.cycles:
            self.extract_cycles()

        equivalent_cycles = 0.0

        for cycle in self.cycles:
            # Get stress factor for this DoD
            stress_factor = self._interpolate_stress_factor(cycle.range_pct, dod_curve)

            # Accumulate weighted damage
            equivalent_cycles += cycle.count * stress_factor

        return equivalent_cycles

    def _interpolate_stress_factor(
        self,
        dod: float,
        dod_curve: Dict[float, float]
    ) -> float:
        """Interpolate stress factor from DoD curve."""
        dod_points = sorted(dod_curve.keys())

        # Handle edge cases
        if dod <= dod_points[0]:
            return dod_curve[dod_points[0]]
        if dod >= dod_points[-1]:
            return dod_curve[dod_points[-1]]

        # Find bracketing points
        for i in range(len(dod_points) - 1):
            if dod_points[i] <= dod <= dod_points[i + 1]:
                # Linear interpolation
                x1, x2 = dod_points[i], dod_points[i + 1]
                y1, y2 = dod_curve[x1], dod_curve[x2]
                factor = (dod - x1) / (x2 - x1)
                return y1 + factor * (y2 - y1)

        return 1.0  # Fallback

    def get_dod_distribution(self) -> Dict[str, int]:
        """
        Get distribution of cycles by DoD range.

        Returns:
            Dict with DoD ranges as keys and cycle counts as values
        """
        if not self.cycles:
            self.extract_cycles()

        ranges = {
            '0-20%': 0,
            '20-40%': 0,
            '40-60%': 0,
            '60-80%': 0,
            '80-100%': 0
        }

        for cycle in self.cycles:
            dod = cycle.range_pct
            if dod < 20:
                ranges['0-20%'] += cycle.count
            elif dod < 40:
                ranges['20-40%'] += cycle.count
            elif dod < 60:
                ranges['40-60%'] += cycle.count
            elif dod < 80:
                ranges['60-80%'] += cycle.count
            else:
                ranges['80-100%'] += cycle.count

        return ranges


# =============================================================================
# DEGRADATION CALCULATIONS
# =============================================================================

def calculate_cycle_degradation(
    cycles: List[RainflowCycle],
    config: DegradationConfig
) -> float:
    """
    Calculate cycle-based degradation using damage curve.

    Args:
        cycles: List of rainflow cycles
        config: Degradation configuration

    Returns:
        Degradation percentage from cycling
    """
    if not cycles:
        return 0.0

    # Calculate equivalent full cycles
    equivalent_cycles = 0.0
    for cycle in cycles:
        stress_factor = _interpolate_stress_factor(cycle.range_pct, config.dod_stress_curve)
        equivalent_cycles += cycle.count * stress_factor

    # Apply base degradation rate
    degradation = equivalent_cycles * config.cycle_base_degradation * 100

    return degradation


def calculate_calendar_degradation(
    years: float,
    avg_soc_pct: float = 50.0,
    config: DegradationConfig = None
) -> float:
    """
    Calculate calendar aging degradation.

    Args:
        years: Time period in years
        avg_soc_pct: Average SOC during period (affects aging rate)
        config: Degradation configuration

    Returns:
        Degradation percentage from calendar aging
    """
    if config is None:
        config = DegradationConfig()

    if not config.include_calendar_aging:
        return 0.0

    # Base calendar degradation
    base_rate = config.calendar_degradation_rate

    # SOC adjustment factor (higher SOC = faster degradation)
    # Normalized around 50% SOC
    soc_factor = 1.0 + 0.005 * (avg_soc_pct - 50)  # +/- 0.25% per 50% SOC difference

    # Calculate degradation
    degradation = years * base_rate * soc_factor * 100

    return degradation


def calculate_total_degradation(
    cycle_deg: float,
    calendar_deg: float,
    method: str = 'additive'
) -> float:
    """
    Combine cycle and calendar degradation.

    Args:
        cycle_deg: Degradation from cycling (%)
        calendar_deg: Degradation from calendar aging (%)
        method: 'additive' (conservative) or 'max' (less conservative)

    Returns:
        Total degradation percentage
    """
    if method == 'additive':
        return cycle_deg + calendar_deg
    elif method == 'max':
        return max(cycle_deg, calendar_deg)
    else:
        return cycle_deg + calendar_deg


def _interpolate_stress_factor(dod: float, dod_curve: Dict[float, float]) -> float:
    """Interpolate stress factor from DoD curve."""
    dod_points = sorted(dod_curve.keys())

    if dod <= dod_points[0]:
        return dod_curve[dod_points[0]]
    if dod >= dod_points[-1]:
        return dod_curve[dod_points[-1]]

    for i in range(len(dod_points) - 1):
        if dod_points[i] <= dod <= dod_points[i + 1]:
            x1, x2 = dod_points[i], dod_points[i + 1]
            y1, y2 = dod_curve[x1], dod_curve[x2]
            factor = (dod - x1) / (x2 - x1)
            return y1 + factor * (y2 - y1)

    return 1.0


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

def calculate_degradation(
    soc_history: List[float],
    simulation_hours: int = 8760,
    config: DegradationConfig = None
) -> DegradationResult:
    """
    Calculate comprehensive degradation from SOC history.

    Args:
        soc_history: List of SOC values (0-100 as percentages)
        simulation_hours: Number of hours simulated (for calendar aging)
        config: Degradation configuration

    Returns:
        DegradationResult with all degradation metrics
    """
    if config is None:
        config = DegradationConfig()

    result = DegradationResult()

    # Convert hours to years
    years = simulation_hours / 8760

    # Calculate average SOC
    avg_soc = np.mean(soc_history) if soc_history else 50.0

    if config.use_rainflow_counting and len(soc_history) > 2:
        # Rainflow counting
        counter = RainflowCounter(soc_history)
        result.rainflow_cycles = counter.extract_cycles()
        result.equivalent_full_cycles = counter.calculate_equivalent_full_cycles(config.dod_stress_curve)
        result.dod_distribution = counter.get_dod_distribution()

        # Simple cycle count for comparison
        result.total_cycles_simple = sum(c.count for c in result.rainflow_cycles)

        # Cycle degradation using equivalent cycles
        result.cycle_degradation_pct = result.equivalent_full_cycles * config.cycle_base_degradation * 100
    else:
        # Simple cycle counting fallback
        if len(soc_history) > 1:
            # Count transitions
            transitions = 0
            for i in range(1, len(soc_history)):
                if abs(soc_history[i] - soc_history[i-1]) > 1.0:
                    transitions += 1
            result.total_cycles_simple = transitions / 2  # Rough estimate
            result.equivalent_full_cycles = result.total_cycles_simple

        result.cycle_degradation_pct = result.total_cycles_simple * config.cycle_base_degradation * 100

    # Calendar degradation
    result.calendar_degradation_pct = calculate_calendar_degradation(years, avg_soc, config)

    # Total degradation
    result.total_degradation_pct = calculate_total_degradation(
        result.cycle_degradation_pct,
        result.calendar_degradation_pct
    )

    return result


def project_capacity_over_years(
    initial_capacity_mwh: float,
    annual_degradation_pct: float,
    years: int = 20,
    config: DegradationConfig = None
) -> List[Dict]:
    """
    Project battery capacity over multiple years.

    Args:
        initial_capacity_mwh: Starting capacity
        annual_degradation_pct: Annual degradation rate (%)
        years: Number of years to project
        config: Degradation configuration (for strategy)

    Returns:
        List of dicts with year-by-year capacity projections
    """
    if config is None:
        config = DegradationConfig()

    # Apply overbuild if configured
    if config.strategy == 'overbuild':
        installed_capacity = initial_capacity_mwh * (1 + config.overbuild_factor)
    else:
        installed_capacity = initial_capacity_mwh

    projections = []
    current_capacity = installed_capacity

    for year in range(1, years + 1):
        # Apply annual degradation (compound)
        degradation_factor = 1 - (annual_degradation_pct / 100)
        current_capacity *= degradation_factor

        # Check for augmentation
        augmented = False
        if config.strategy == 'augmentation' and year == config.augmentation_year:
            # Add capacity to restore to initial
            augmentation_mwh = initial_capacity_mwh - current_capacity
            if augmentation_mwh > 0:
                current_capacity += augmentation_mwh
                augmented = True

        projections.append({
            'year': year,
            'installed_capacity_mwh': installed_capacity if not augmented else installed_capacity + augmentation_mwh,
            'effective_capacity_mwh': current_capacity,
            'capacity_retention_pct': (current_capacity / initial_capacity_mwh) * 100,
            'augmented': augmented
        })

        if augmented:
            installed_capacity = current_capacity

    return projections
