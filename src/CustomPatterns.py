"""
Custom pattern classes that mirror the AutoScript pattern types.
These classes replicate the structure of autoscript_sdb_microscope_client patterns
without requiring the AutoScript package to be installed.
"""

import html
import os
import xml.etree.ElementTree as ET
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class BasePattern:
    """
    Base class for all pattern types containing common attributes.
    All measurements are in SI units (meters, seconds, etc.) unless otherwise noted.
    """
    # Common properties for all patterns
    application_file: str = ""  # The name of the application file
    beam_type: str = "Ion"  # The beam used for patterning: "Electron" or "Ion"
    blur: float = 0.0  # Additional diameter of the blurred spot (meters)
    defocus: float = 0.0  # Defocus (WD change) of the beam (meters)
    depth: float = 0.0  # Depth of the pattern (meters)
    dose: float = 0.0  # Charge dose per area (C/µm²)
    dwell_time: float = 1e-6  # Time beam spends on a single pixel per pass (seconds, rounded to 25ns)
    enabled: bool = True  # If False, pattern is removed from the patterning job
    gas_flow: float = 0.0  # Custom gas flow for the pattern
    gas_needle_position: str = ""  # Position of MultiChem needle when patterning begins
    gas_type: str = ""  # Name of gas required, empty string if no gas
    interaction_diameter: float = 0.0  # Interaction diameter for infinitely small beam (meters)
    is_exclusion_zone: bool = False  # If True, pattern area is not processed
    pass_count: int = 1  # Number of passes (scans) over the pattern area
    refresh_time: float = 0.0  # Minimum loop time before next pass (seconds)
    rotation: float = 0.0  # Pattern rotation angle (radians)
    scan_direction: str = "TopToBottom"  # Direction of the scan movement
    scan_type: str = "Raster"  # Scanning strategy used while patterning
    time: float = 0.0  # Time required to process the pattern (seconds)
    volume_per_dose: float = 0.0  # Volume removed per charge (mm³/nC)
    
    # Read-only unique identifier
    _id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    @property
    def id(self) -> str:
        """A unique pattern identifier (read-only)."""
        return self._id


@dataclass
class RectanglePattern(BasePattern):
    """The pattern of a rectangular shape."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    width: float = 1e-6  # Pattern width (meters)
    height: float = 1e-6  # Pattern height (meters)
    overlap_x: float = 0.5  # Beam diameter overlap in X direction (0-1)
    overlap_y: float = 0.5  # Beam diameter overlap in Y direction (0-1)
    pitch_x: float = 0.0  # Pitch X between two spots (meters)
    pitch_y: float = 0.0  # Pitch Y between two spots (meters)


@dataclass
class CirclePattern(BasePattern):
    """The circular pattern. Set inner_diameter > 0 to create a ring."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    outer_diameter: float = 1e-6  # Diameter of the circle (meters)
    inner_diameter: float = 0.0  # Diameter of the inner circle for ring patterns (meters)
    overlap_r: float = 0.5  # Beam diameter overlap in radial direction (0-1)
    overlap_t: float = 0.5  # Beam diameter overlap in tangential direction (0-1)
    pitch_r: float = 0.0  # Pitch R between two spots (meters)
    pitch_t: float = 0.0  # Pitch T between two spots (meters)


@dataclass
class LinePattern(BasePattern):
    """The line shaped pattern."""
    start_x: float = 0.0  # X coordinate of the pattern start position (meters)
    start_y: float = 0.0  # Y coordinate of the pattern start position (meters)
    end_x: float = 1e-6  # X coordinate of the pattern end position (meters)
    end_y: float = 0.0  # Y coordinate of the pattern end position (meters)
    length: float = 1e-6  # Length of the pattern (meters)
    overlap: float = 0.5  # Beam diameter overlap (0-1)
    pitch: float = 0.0  # Pitch between two spots (meters)


@dataclass
class PolygonPattern(BasePattern):
    """The polygon pattern defined by vertices."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    vertices: List[Tuple[float, float]] = field(default_factory=list)  # List of (x, y) vertex coordinates
    overlap_x: float = 0.5  # Beam diameter overlap in X direction (0-1)
    overlap_y: float = 0.5  # Beam diameter overlap in Y direction (0-1)
    pitch_x: float = 0.0  # Pitch X between two spots (meters)
    pitch_y: float = 0.0  # Pitch Y between two spots (meters)


@dataclass
class BitmapPattern(BasePattern):
    """The bitmap pattern type for image-based patterning."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    width: float = 1e-6  # Pattern width (meters)
    height: float = 1e-6  # Pattern height (meters)
    fix_aspect_ratio: bool = True  # When True, aspect ratio is fixed
    bitmap_data: Optional[bytes] = None  # The bitmap image data


@dataclass
class RegularCrossSectionPattern(BasePattern):
    """The regular cross section pattern type for FIB milling."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    width: float = 1e-6  # Pattern width (meters)
    height: float = 1e-6  # Pattern height (meters)
    overlap_x: float = 0.5  # Beam diameter overlap in X direction (0-1)
    overlap_y: float = 0.5  # Beam diameter overlap in Y direction (0-1)
    pitch_x: float = 0.0  # Pitch X between two spots (meters)
    pitch_y: float = 0.0  # Pitch Y between two spots (meters)
    multi_scan_pass_count: int = 1  # Number of passes for multi-scan method
    scan_method: str = "MultiPass"  # Scanning method: use RegularCrossSectionScanMethod values
    scan_ratio: float = 1.0  # Ratio between dose at first line and last line


@dataclass
class CleaningCrossSectionPattern(BasePattern):
    """The cleaning cross section pattern type for surface cleaning."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    width: float = 1e-6  # Pattern width (meters)
    height: float = 1e-6  # Pattern height (meters)
    overlap_x: float = 0.5  # Beam diameter overlap in X direction (0-1)
    overlap_y: float = 0.5  # Beam diameter overlap in Y direction (0-1)
    pitch_x: float = 0.0  # Pitch X between two spots (meters)
    pitch_y: float = 0.0  # Pitch Y between two spots (meters)


@dataclass
class StreamPattern(BasePattern):
    """The stream file pattern type for custom beam paths."""
    center_x: float = 0.0  # X coordinate of the pattern center position (meters)
    center_y: float = 0.0  # Y coordinate of the pattern center position (meters)
    stream_file_path: str = ""  # Path to the stream file
    # Note: StreamPattern has fewer properties - no overlap, pitch, depth, scan_direction, scan_type, is_exclusion_zone
    
    def __post_init__(self):
        # StreamPattern doesn't use these properties from BasePattern
        pass


# Enumeration-like classes for pattern properties
class BeamType:
    """Enumeration for beam types."""
    ELECTRON = "Electron"
    ION = "Ion"


class ScanDirection:
    """Enumeration for scan directions."""
    TOP_TO_BOTTOM = "TopToBottom"
    BOTTOM_TO_TOP = "BottomToTop"
    LEFT_TO_RIGHT = "LeftToRight"
    RIGHT_TO_LEFT = "RightToLeft"


class ScanType:
    """Enumeration for scan types."""
    RASTER = "Raster"
    SERPENTINE = "Serpentine"


class RegularCrossSectionScanMethod:
    """Enumeration for regular cross section scan methods."""
    MULTI_PASS = "MultiPass"
    SINGLE_PASS = "SinglePass"


# =============================================================================
# Pattern File Parsing Functions
# =============================================================================

def _get_element_text(element: ET.Element, tag: str, default: str = "") -> str:
    """Get text content of a child element, handling namespaces."""
    child = element.find(tag)
    if child is not None and child.text is not None:
        return child.text.strip()
    return default


def _get_element_float(element: ET.Element, tag: str, default: float = 0.0) -> float:
    """Get float value from a child element."""
    text = _get_element_text(element, tag)
    if text:
        try:
            return float(text)
        except ValueError:
            return default
    return default


def _get_element_int(element: ET.Element, tag: str, default: int = 0) -> int:
    """Get integer value from a child element."""
    text = _get_element_text(element, tag)
    if text:
        try:
            return int(float(text))  # Handle scientific notation
        except ValueError:
            return default
    return default


def _get_element_bool(element: ET.Element, tag: str, default: bool = False) -> bool:
    """Get boolean value from a child element."""
    text = _get_element_text(element, tag).lower()
    if text in ("true", "1", "yes"):
        return True
    elif text in ("false", "0", "no"):
        return False
    return default


def _parse_polygon_points(element: ET.Element) -> List[Tuple[float, float]]:
    """Parse polygon points from the Points element containing escaped XML."""
    points_text = _get_element_text(element, "Points")
    if not points_text:
        return []
    
    # The Points element contains escaped XML, so we need to parse it
    unescaped = html.unescape(points_text)
    
    vertices = []
    try:
        points_root = ET.fromstring(unescaped)
        for point in points_root.findall("Point"):
            x = _get_element_float(point, "PositionX", 0.0)
            y = _get_element_float(point, "PositionY", 0.0)
            vertices.append((x, y))
    except ET.ParseError:
        pass
    
    return vertices


def _parse_base_pattern_attrs(element: ET.Element) -> dict:
    """Parse common attributes shared by all pattern types."""
    return {
        "application_file": _get_element_text(element, "Application"),
        "beam_type": _get_element_text(element, "Beam", "Ion"),
        "blur": _get_element_float(element, "Blur"),
        "defocus": _get_element_float(element, "Defocus"),
        "depth": _get_element_float(element, "Depth"),
        "dose": _get_element_float(element, "Dose"),
        "dwell_time": _get_element_float(element, "DwellTime", 1e-6),
        "enabled": _get_element_bool(element, "Enable", True),
        "gas_needle_position": _get_element_text(element, "GasNeedlePosition"),
        "gas_type": _get_element_text(element, "GasType"),
        "interaction_diameter": _get_element_float(element, "InteractionDiameter"),
        "is_exclusion_zone": _get_element_bool(element, "ExclusionZone"),
        "pass_count": _get_element_int(element, "PassCount", 1),
        "refresh_time": _get_element_float(element, "RefreshTime"),
        "rotation": _get_element_float(element, "Rotation"),
        "scan_direction": _get_element_text(element, "ScanDirection", "TopToBottom"),
        "scan_type": _get_element_text(element, "ScanType", "Raster"),
        "time": _get_element_float(element, "TotalTime"),
        "volume_per_dose": _get_element_float(element, "VolumePerDose"),
    }


def _parse_rectangle_pattern(element: ET.Element) -> RectanglePattern:
    """Parse a PatternRectangle element into a RectanglePattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    # Note: In PTF files, "Length" corresponds to height and "Width" to width
    return RectanglePattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        width=_get_element_float(element, "Width", 1e-6),
        height=_get_element_float(element, "Length", 1e-6),  # PTF uses "Length" for height
        overlap_x=_get_element_float(element, "OverlapX", 50) / 100.0,  # Convert from percentage
        overlap_y=_get_element_float(element, "OverlapY", 50) / 100.0,
        pitch_x=_get_element_float(element, "PitchX"),
        pitch_y=_get_element_float(element, "PitchY"),
    )


def _parse_circle_pattern(element: ET.Element) -> CirclePattern:
    """Parse a PatternCircle element into a CirclePattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    return CirclePattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        outer_diameter=_get_element_float(element, "OuterDiameter", 1e-6),
        inner_diameter=_get_element_float(element, "InnerDiameter", 0.0),
        overlap_r=_get_element_float(element, "OverlapR", 50) / 100.0,
        overlap_t=_get_element_float(element, "OverlapT", 50) / 100.0,
        pitch_r=_get_element_float(element, "PitchR"),
        pitch_t=_get_element_float(element, "PitchT"),
    )


def _parse_line_pattern(element: ET.Element) -> LinePattern:
    """Parse a PatternLine element into a LinePattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    return LinePattern(
        **base_attrs,
        start_x=_get_element_float(element, "StartX"),
        start_y=_get_element_float(element, "StartY"),
        end_x=_get_element_float(element, "EndX"),
        end_y=_get_element_float(element, "EndY"),
        length=_get_element_float(element, "Length", 1e-6),
        overlap=_get_element_float(element, "Overlap", 50) / 100.0,
        pitch=_get_element_float(element, "Pitch"),
    )


def _parse_polygon_pattern(element: ET.Element) -> PolygonPattern:
    """Parse a PatternPolygon element into a PolygonPattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    vertices = _parse_polygon_points(element)
    
    return PolygonPattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        vertices=vertices,
        overlap_x=_get_element_float(element, "OverlapX", 50) / 100.0,
        overlap_y=_get_element_float(element, "OverlapY", 50) / 100.0,
        pitch_x=_get_element_float(element, "PitchX"),
        pitch_y=_get_element_float(element, "PitchY"),
    )


def _parse_bitmap_pattern(element: ET.Element) -> BitmapPattern:
    """Parse a PatternBitmap element into a BitmapPattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    return BitmapPattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        width=_get_element_float(element, "Width", 1e-6),
        height=_get_element_float(element, "Height", 1e-6),
        fix_aspect_ratio=_get_element_bool(element, "FixAspectRatio", True),
    )


def _parse_regular_cross_section_pattern(element: ET.Element) -> RegularCrossSectionPattern:
    """Parse a PatternRegularCrossSection element into a RegularCrossSectionPattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    return RegularCrossSectionPattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        width=_get_element_float(element, "Width", 1e-6),
        height=_get_element_float(element, "Length", 1e-6),
        overlap_x=_get_element_float(element, "OverlapX", 50) / 100.0,
        overlap_y=_get_element_float(element, "OverlapY", 50) / 100.0,
        pitch_x=_get_element_float(element, "PitchX"),
        pitch_y=_get_element_float(element, "PitchY"),
        multi_scan_pass_count=_get_element_int(element, "MultiScanPassCount", 1),
        scan_method=_get_element_text(element, "ScanMethod", "MultiPass"),
        scan_ratio=_get_element_float(element, "ScanRatio", 1.0),
    )


def _parse_cleaning_cross_section_pattern(element: ET.Element) -> CleaningCrossSectionPattern:
    """Parse a PatternCleaningCrossSection element into a CleaningCrossSectionPattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    return CleaningCrossSectionPattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        width=_get_element_float(element, "Width", 1e-6),
        height=_get_element_float(element, "Length", 1e-6),
        overlap_x=_get_element_float(element, "OverlapX", 50) / 100.0,
        overlap_y=_get_element_float(element, "OverlapY", 50) / 100.0,
        pitch_x=_get_element_float(element, "PitchX"),
        pitch_y=_get_element_float(element, "PitchY"),
    )


def _parse_stream_pattern(element: ET.Element) -> StreamPattern:
    """Parse a PatternStream element into a StreamPattern instance."""
    base_attrs = _parse_base_pattern_attrs(element)
    
    return StreamPattern(
        **base_attrs,
        center_x=_get_element_float(element, "CenterX"),
        center_y=_get_element_float(element, "CenterY"),
        stream_file_path=_get_element_text(element, "StreamFile"),
    )


# Mapping of XML tag names to parser functions
_PATTERN_PARSERS = {
    "PatternRectangle": _parse_rectangle_pattern,
    "PatternCircle": _parse_circle_pattern,
    "PatternLine": _parse_line_pattern,
    "PatternPolygon": _parse_polygon_pattern,
    "PatternBitmap": _parse_bitmap_pattern,
    "PatternRegularCrossSection": _parse_regular_cross_section_pattern,
    "PatternCleaningCrossSection": _parse_cleaning_cross_section_pattern,
    "PatternStream": _parse_stream_pattern,
}


def parse_pattern_file(file_path: str) -> dict:
    """
    Parse a .ptf pattern file and return a dictionary of pattern instances.
    
    Args:
        file_path: Path to the .ptf file to parse.
        
    Returns:
        A dictionary where keys are pattern indices (0, 1, 2, ...) and values
        are instances of the appropriate pattern class (RectanglePattern,
        CirclePattern, PolygonPattern, etc.).
        
    Raises:
        FileNotFoundError: If the file does not exist.
        ET.ParseError: If the file is not valid XML.
        
    Example:
        >>> patterns = parse_pattern_file("my_patterns.ptf")
        >>> patterns[0]
        RectanglePattern(center_x=1e-6, center_y=2e-6, ...)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Pattern file not found: {file_path}")
    
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    patterns = {}
    pattern_index = 0
    
    for child in root:
        tag = child.tag
        if tag in _PATTERN_PARSERS:
            parser = _PATTERN_PARSERS[tag]
            pattern = parser(child)
            patterns[pattern_index] = pattern
            pattern_index += 1
    
    return patterns


def parse_pattern_file_to_list(file_path: str) -> List[BasePattern]:
    """
    Parse a .ptf pattern file and return a list of pattern instances.
    
    This is an alternative to parse_pattern_file() that returns a list
    instead of a dictionary.
    
    Args:
        file_path: Path to the .ptf file to parse.
        
    Returns:
        A list of pattern instances in the order they appear in the file.
    """
    patterns_dict = parse_pattern_file(file_path)
    return [patterns_dict[i] for i in sorted(patterns_dict.keys())]


# =============================================================================
# Coordinate Conversion Functions
# =============================================================================

def pattern_to_image_coords(
    pattern: BasePattern,
    image_width_px: int,
    image_height_px: int,
    field_of_view_width_m: float,
    field_of_view_height_m: Optional[float] = None
) -> List[Tuple[int, int]]:
    """
    Convert a pattern's coordinates from the patterning coordinate system (meters)
    to image pixel coordinates.
    
    The patterning coordinate system has:
    - Origin at the center of the image field of view
    - X-axis: positive to the right
    - Y-axis: positive upward
    
    The image coordinate system has:
    - Origin at the top-left corner
    - X-axis: positive to the right  
    - Y-axis: positive downward
    
    Args:
        pattern: A pattern object (RectanglePattern, PolygonPattern, etc.)
        image_width_px: Width of the image in pixels
        image_height_px: Height of the image in pixels
        field_of_view_width_m: Horizontal field of view in meters
        field_of_view_height_m: Vertical field of view in meters. If None,
            assumes square pixels and calculates from width.
    
    Returns:
        A list of (x, y) tuples representing the pattern vertices in pixel coordinates.
        For rectangles, returns the 4 corners. For polygons, returns all vertices.
        For circles, returns points approximating the circle.
    """
    if field_of_view_height_m is None:
        # Assume square pixels
        field_of_view_height_m = field_of_view_width_m * image_height_px / image_width_px
    
    # Calculate meters per pixel
    m_per_px_x = field_of_view_width_m / image_width_px
    m_per_px_y = field_of_view_height_m / image_height_px
    
    # Image center in pixels
    center_px_x = image_width_px / 2
    center_px_y = image_height_px / 2
    
    def meters_to_pixels(x_m: float, y_m: float) -> Tuple[int, int]:
        """Convert from patterning coords (meters) to image coords (pixels)."""
        # Convert meters to pixels relative to center
        x_px = x_m / m_per_px_x
        y_px = y_m / m_per_px_y
        
        # Translate to image coordinates (origin at top-left, Y flipped)
        img_x = int(center_px_x + x_px)
        img_y = int(center_px_y - y_px)  # Flip Y axis
        
        return (img_x, img_y)
    
    # Handle different pattern types
    if isinstance(pattern, RectanglePattern):
        # Get the 4 corners of the rectangle
        cx, cy = pattern.center_x, pattern.center_y
        w, h = pattern.width / 2, pattern.height / 2
        rot = pattern.rotation
        
        # Corners before rotation (relative to center)
        corners = [
            (-w, -h),
            (+w, -h),
            (+w, +h),
            (-w, +h),
        ]
        
        # Apply rotation if non-zero
        if rot != 0:
            import math
            cos_r, sin_r = math.cos(rot), math.sin(rot)
            corners = [
                (x * cos_r - y * sin_r, x * sin_r + y * cos_r)
                for x, y in corners
            ]
        
        # Translate to pattern center and convert to pixels
        return [meters_to_pixels(cx + x, cy + y) for x, y in corners]
    
    elif isinstance(pattern, PolygonPattern):
        # Polygon vertices are already in absolute coordinates
        return [meters_to_pixels(x, y) for x, y in pattern.vertices]
    
    elif isinstance(pattern, CirclePattern):
        # Approximate circle with polygon points
        import math
        cx, cy = pattern.center_x, pattern.center_y
        r = pattern.outer_diameter / 2
        
        # Use 32 points for a smooth circle
        num_points = 32
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points + pattern.rotation
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append(meters_to_pixels(x, y))
        
        return points
    
    elif isinstance(pattern, LinePattern):
        # Return start and end points
        return [
            meters_to_pixels(pattern.start_x, pattern.start_y),
            meters_to_pixels(pattern.end_x, pattern.end_y),
        ]
    
    elif isinstance(pattern, (RegularCrossSectionPattern, CleaningCrossSectionPattern, BitmapPattern)):
        # Treat like rectangle
        cx, cy = pattern.center_x, pattern.center_y
        w, h = pattern.width / 2, pattern.height / 2
        rot = pattern.rotation
        
        corners = [(-w, -h), (+w, -h), (+w, +h), (-w, +h)]
        
        if rot != 0:
            import math
            cos_r, sin_r = math.cos(rot), math.sin(rot)
            corners = [
                (x * cos_r - y * sin_r, x * sin_r + y * cos_r)
                for x, y in corners
            ]
        
        return [meters_to_pixels(cx + x, cy + y) for x, y in corners]
    
    elif isinstance(pattern, StreamPattern):
        # Stream patterns don't have geometric coordinates - return center point
        return [meters_to_pixels(pattern.center_x, pattern.center_y)]
    
    else:
        # Unknown pattern type - try to get center if available
        if hasattr(pattern, 'center_x') and hasattr(pattern, 'center_y'):
            return [meters_to_pixels(pattern.center_x, pattern.center_y)]
        return []


def patterns_to_image_coords(
    patterns: dict,
    image_width_px: int,
    image_height_px: int,
    field_of_view_width_m: float,
    field_of_view_height_m: Optional[float] = None
) -> dict:
    """
    Convert all patterns in a dictionary from patterning coordinates to image coordinates.
    
    Args:
        patterns: Dictionary of {id: pattern} as returned by parse_pattern_file()
        image_width_px: Width of the image in pixels
        image_height_px: Height of the image in pixels
        field_of_view_width_m: Horizontal field of view in meters
        field_of_view_height_m: Vertical field of view in meters (optional)
    
    Returns:
        Dictionary of {id: {"pattern": pattern, "coords": [(x,y), ...]}}
        where coords are in image pixel coordinates.
    
    Example:
        >>> patterns = parse_pattern_file("my_patterns.ptf")
        >>> image_patterns = patterns_to_image_coords(
        ...     patterns,
        ...     image_width_px=1536,
        ...     image_height_px=1024,
        ...     field_of_view_width_m=100e-6  # 100 µm
        ... )
        >>> for pid, data in image_patterns.items():
        ...     print(f"Pattern {pid}: {data['coords']}")
    """
    result = {}
    for pid, pattern in patterns.items():
        coords = pattern_to_image_coords(
            pattern,
            image_width_px,
            image_height_px,
            field_of_view_width_m,
            field_of_view_height_m
        )
        result[pid] = {
            "pattern": pattern,
            "coords": coords
        }
    return result


@dataclass
class DisplayablePattern:
    """
    A pattern with pre-computed image coordinates for display.
    
    This class wraps a BasePattern and adds pixel coordinates for rendering
    onto an image.
    """
    pattern: BasePattern
    coords: List[Tuple[int, int]] = field(default_factory=list)
    
    @classmethod
    def from_pattern(
        cls,
        pattern: BasePattern,
        image_width_px: int,
        image_height_px: int,
        field_of_view_width_m: float,
        field_of_view_height_m: Optional[float] = None
    ) -> "DisplayablePattern":
        """Create a DisplayablePattern from a BasePattern."""
        coords = pattern_to_image_coords(
            pattern,
            image_width_px,
            image_height_px,
            field_of_view_width_m,
            field_of_view_height_m
        )
        return cls(pattern=pattern, coords=coords)
    
    def clone(self) -> "DisplayablePattern":
        """Create a deep copy of this displayable pattern."""
        import copy
        return DisplayablePattern(
            pattern=copy.deepcopy(self.pattern),
            coords=[(x, y) for x, y in self.coords]
        )


# Predefined colors for PatternGroup (in order)
PATTERN_GROUP_COLORS = [
    (255, 255, 0),   # Yellow
    (255, 0, 0),     # Red
    (0, 100, 255),   # Blue
    (255, 165, 0),   # Orange
    (0, 200, 0),     # Green
]


@dataclass
class PatternGroup:
    """
    A group of displayable patterns that share common milling parameters.
    
    This class groups multiple DisplayablePattern objects that should be milled
    together with the same current setting.
    
    Attributes:
        patterns: Dictionary mapping pattern IDs to DisplayablePattern objects
        milling_current: The milling current in Amperes for all patterns in this group
        color: RGB tuple for display color (assigned based on group order)
        sequential_group: Integer for ordering/grouping patterns during milling
        delay: Delay in seconds before milling this group (integer)
    """
    patterns: dict = field(default_factory=dict)  # Dict of {id: DisplayablePattern}
    milling_current: float = 0.0  # Milling current in Amperes
    color: Tuple[int, int, int] = (255, 255, 0)  # RGB color tuple, default yellow
    sequential_group: int = 0  # Group ordering for milling sequence
    delay: int = 0  # Delay in seconds before milling this group
    
    @classmethod
    def create_with_index(cls, patterns: dict, milling_current: float, index: int, sequential_group: int = 0, delay: int = 0) -> "PatternGroup":
        """
        Create a PatternGroup with color automatically assigned based on index.
        
        Args:
            patterns: Dictionary of {id: DisplayablePattern}
            milling_current: Milling current in Amperes
            index: Index of this group (0=first, 1=second, etc.) for color assignment
            sequential_group: Optional group ordering number
            delay: Delay in seconds before milling this group
            
        Returns:
            PatternGroup with appropriate color assigned
        """
        import random
        if index < len(PATTERN_GROUP_COLORS):
            color = PATTERN_GROUP_COLORS[index]
        else:
            # Random color for groups beyond predefined colors
            color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        
        return cls(
            patterns=patterns,
            milling_current=milling_current,
            color=color,
            sequential_group=sequential_group,
            delay=delay
        )
    
    def clone(self) -> "PatternGroup":
        """Create a deep copy of this pattern group."""
        return PatternGroup(
            patterns={pid: dp.clone() for pid, dp in self.patterns.items()},
            milling_current=self.milling_current,
            color=self.color,
            sequential_group=self.sequential_group,
            delay=self.delay
        )


def load_patterns_for_display(
    file_path: str,
    image_width_px: int,
    image_height_px: int,
    field_of_view_width_m: float,
    field_of_view_height_m: Optional[float] = None,
    milling_current: float = 0.0,
    group_index: int = 0
) -> "PatternGroup":
    """
    Load patterns from a .ptf file and convert them to a PatternGroup.
    
    This is a convenience function that combines parse_pattern_file() and
    coordinate conversion into a single call.
    
    Args:
        file_path: Path to the .ptf pattern file
        image_width_px: Width of the target image in pixels
        image_height_px: Height of the target image in pixels
        field_of_view_width_m: Horizontal field of view in meters
        field_of_view_height_m: Vertical field of view in meters (optional)
        milling_current: Milling current in Amperes (default 0.0)
        group_index: Index for color assignment (default 0 = yellow)
    
    Returns:
        PatternGroup containing DisplayablePatterns ready for rendering.
    
    Example:
        >>> pattern_group = load_patterns_for_display(
        ...     "my_patterns.ptf",
        ...     image_width_px=1536,
        ...     image_height_px=1024,
        ...     field_of_view_width_m=100e-6
        ... )
        >>> for pid, dp in pattern_group.patterns.items():
        ...     print(f"Pattern {pid}: {dp.coords}")
        ...     print(f"  Depth: {dp.pattern.depth}")
    """
    raw_patterns = parse_pattern_file(file_path)
    
    patterns_dict = {}
    for pid, pattern in raw_patterns.items():
        patterns_dict[pid] = DisplayablePattern.from_pattern(
            pattern,
            image_width_px,
            image_height_px,
            field_of_view_width_m,
            field_of_view_height_m
        )
    
    return PatternGroup.create_with_index(
        patterns=patterns_dict,
        milling_current=milling_current,
        index=group_index
    )


def convert_xT_patterns_to_displayable(
    xT_patterns,
    image_width_px: int,
    image_height_px: int,
    field_of_view_width_m: float,
    field_of_view_height_m: Optional[float] = None,
    milling_current: float = 0.0,
    group_index: int = 0
) -> "PatternGroup":
    """
    Convert AutoScript xT patterns to a PatternGroup for display.
    
    The xT patterns already contain all necessary attributes (depth, dwell_time, etc.),
    so this function only computes the pixel coordinates for rendering.
    
    Args:
        xT_patterns: List of AutoScript pattern objects from microscope.patterning.get_patterns()
        image_width_px: Width of the image in pixels
        image_height_px: Height of the image in pixels
        field_of_view_width_m: Horizontal field of view in meters
        field_of_view_height_m: Vertical field of view in meters (optional)
        milling_current: Milling current in Amperes (default 0.0)
        group_index: Index for color assignment (default 0 = yellow)
    
    Returns:
        PatternGroup containing DisplayablePatterns ready for rendering.
    """
    patterns_dict = {}
    for pid, xT_pattern in enumerate(xT_patterns):
        coords = pattern_to_image_coords(
            xT_pattern,
            image_width_px,
            image_height_px,
            field_of_view_width_m,
            field_of_view_height_m
        )
        patterns_dict[pid] = DisplayablePattern(pattern=xT_pattern, coords=coords)
    
    return PatternGroup.create_with_index(
        patterns=patterns_dict,
        milling_current=milling_current,
        index=group_index
    )