from typing import List, Optional, Tuple


def bbox_to_quadpoints(
    bbox: Optional[List[float]],
    page_size: Optional[Tuple[float, float]] = None,
    *,
    origin: str = "top-left",
    units: str = "auto",
    observed_max: Optional[Tuple[float, float]] = None,
    content_coverage: float = 0.92,
) -> Optional[List[float]]:
    """
    Convert MinerU bbox to PDF quadpoints for annotpdf/highlights.

    Inputs:
    - bbox: [x1,y1,x2,y2] (most common) or 8-element quadpoints.
    - page_size: (page_width, page_height) in PDF points.
    - origin: "top-left" (default) or "bottom-left" for bbox coordinate origin.
    - units:
        - "auto": scale bbox to page_size using observed_max if bbox looks like pixels.
        - "px": always scale using observed_max -> page_size.
        - "pt": assume bbox already in PDF points.
    - observed_max: (max_x, max_y) observed in bbox space for the page, used to infer scaling.
    """
    if not bbox:
        return None

    # Prepare quad in bbox coordinate space
    if len(bbox) >= 8:
        quad = list(map(float, bbox[:8]))
        return _convert_quad(
            quad,
            page_size,
            origin=origin,
            units=units,
            observed_max=observed_max,
            content_coverage=content_coverage,
        )
    if len(bbox) == 4:
        x1, y1, x2, y2 = map(float, bbox)
        # normalize ordering
        left, right = (x1, x2) if x1 <= x2 else (x2, x1)
        top, bottom = (y1, y2) if y1 <= y2 else (y2, y1)
        # In top-left origin, top is smaller y; in bottom-left origin, top is larger y.
        # We'll convert by building a quad with semantic top/bottom and later flipping if needed.
        quad = [left, top, right, top, left, bottom, right, bottom]
        return _convert_quad(
            quad,
            page_size,
            origin=origin,
            units=units,
            observed_max=observed_max,
            content_coverage=content_coverage,
        )
    return None


def _convert_quad(
    quad: List[float],
    page_size: Optional[Tuple[float, float]],
    *,
    origin: str,
    units: str,
    observed_max: Optional[Tuple[float, float]],
    content_coverage: float,
) -> List[float]:
    quad = _scale_quad(
        quad,
        page_size,
        units=units,
        observed_max=observed_max,
        content_coverage=content_coverage,
    )

    if page_size and origin == "top-left":
        _, page_h = page_size
        quad = _flip_y(quad, page_h)

    # Ensure quad is in [ul, ur, ll, lr] ordering (annotpdf expects PDF quadpoints)
    # Current quad is [x1,y1,x2,y1,x1,y2,x2,y2] where y1 is top, y2 bottom in bottom-left origin after flip.
    x1, y1, x2, y1b, x3, y2, x4, y2b = quad
    y_top = max(y1, y1b, y2, y2b)
    y_bottom = min(y1, y1b, y2, y2b)
    x_left = min(x1, x2, x3, x4)
    x_right = max(x1, x2, x3, x4)
    normalized = [x_left, y_top, x_right, y_top, x_left, y_bottom, x_right, y_bottom]
    return [round(v, 2) for v in normalized]


def _scale_quad(
    quad: List[float],
    page_size: Optional[Tuple[float, float]],
    *,
    units: str,
    observed_max: Optional[Tuple[float, float]],
    content_coverage: float,
) -> List[float]:
    if not page_size:
        return quad
    page_w, page_h = page_size
    if units == "pt":
        return quad

    if not observed_max:
        # no scaling data available
        return quad

    max_x, max_y = observed_max
    if not max_x or not max_y:
        return quad

    # Infer full-page canvas size in bbox space from content extents.
    # MinerU bboxes are often in rendered-image pixels, while PDF is in points.
    # If content doesn't reach page edges, using raw max_x/max_y will overscale highlights.
    #
    # When `observed_max` is known to be the true full-page canvas size (e.g. from layout.json `page_size`
    # or rendered page images), callers should pass content_coverage=1.0 to avoid any global shrink/shift.
    cov = float(content_coverage)
    if cov >= 0.999:
        cov = 1.0
    cov = min(max(cov, 0.5), 1.0)
    # Estimate canvas so that content extents cover `cov` of page, while respecting page aspect ratio.
    cw_from_x = max_x / cov
    ch_from_y = max_y / cov
    # Enforce aspect ratio roughly matches the PDF page.
    ar = page_h / page_w if page_w else 1.0
    cw = max(cw_from_x, ch_from_y / ar if ar else cw_from_x)
    ch = cw * ar

    if cw <= 0 or ch <= 0:
        return quad

    # Auto: if bbox space is similar to page points, don't scale.
    if units == "auto":
        if cw <= page_w * 1.2 and ch <= page_h * 1.2:
            return quad

    sx = page_w / cw
    sy = page_h / ch
    scaled = []
    for i, v in enumerate(quad):
        scaled.append(v * (sx if i % 2 == 0 else sy))
    return scaled


def _flip_y(quad: List[float], page_height: float) -> List[float]:
    flipped = []
    for i, v in enumerate(quad):
        if i % 2 == 1:  # y coordinate
            flipped.append(page_height - v)
        else:
            flipped.append(v)
    return flipped
