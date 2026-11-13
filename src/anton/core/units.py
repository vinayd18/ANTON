"""SI unit conversion helpers.

Internal representation uses **metres** throughout.  These static helpers
convert to and from common sub-units used in antenna design.
"""


class Units:
    """Static unit-conversion methods (internal unit = metre)."""

    # -- to metres ----------------------------------------------------------

    @staticmethod
    def mm_to_m(value: float) -> float:
        """Convert millimetres to metres."""
        return value * 1e-3

    @staticmethod
    def cm_to_m(value: float) -> float:
        """Convert centimetres to metres."""
        return value * 1e-2

    @staticmethod
    def um_to_m(value: float) -> float:
        """Convert micrometres to metres."""
        return value * 1e-6

    @staticmethod
    def inch_to_m(value: float) -> float:
        """Convert inches to metres."""
        return value * 0.0254

    @staticmethod
    def mil_to_m(value: float) -> float:
        """Convert mils (thousandths of an inch) to metres."""
        return value * 0.0000254

    # -- from metres --------------------------------------------------------

    @staticmethod
    def m_to_mm(value: float) -> float:
        """Convert metres to millimetres."""
        return value * 1e3

    @staticmethod
    def m_to_cm(value: float) -> float:
        """Convert metres to centimetres."""
        return value * 1e2

    @staticmethod
    def m_to_um(value: float) -> float:
        """Convert metres to micrometres."""
        return value * 1e6

    @staticmethod
    def m_to_inch(value: float) -> float:
        """Convert metres to inches."""
        return value / 0.0254

    @staticmethod
    def m_to_mil(value: float) -> float:
        """Convert metres to mils."""
        return value / 0.0000254
