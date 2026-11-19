"""Bottom-window QC diagnostics v0.2.

Pure trial-summary calculations. Existing DS01 angle and bottom-window algorithms
remain unchanged. Intervals are inclusive; IoU is intersection / union.
"""
import math

def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False

def add_bottom_diagnostics(row, fps, iou_warning_threshold=0.60):
    """Return a new enriched summary dict without modifying the original.

    IoU warning threshold is exploratory, not a validated FMS cutoff.
    """
    out = dict(row)
    if float(fps) <= 0:
        raise ValueError("fps must be positive")
    windows = {}
    for side in ("L", "R"):
        start = out.get(f"{side}_bottom_start_frame")
        end = out.get(f"{side}_bottom_end_frame")
        if _finite(start) and _finite(end) and float(end) >= float(start):
            start, end = int(start), int(end)
            length = end - start + 1
            windows[side] = (start, end, length)
            out[f"{side}_bottom_center_frame"] = (start + end) / 2
            out[f"{side}_bottom_duration_s"] = length / float(fps)
        else:
            out[f"{side}_bottom_center_frame"] = math.nan
            out[f"{side}_bottom_duration_s"] = math.nan

    if set(windows) == {"L", "R"}:
        ls, le, ll = windows["L"]
        rs, re, rl = windows["R"]
        intersection = max(0, min(le, re) - max(ls, rs) + 1)
        union = ll + rl - intersection
        out["LR_bottom_window_intersection_frames"] = intersection
        out["LR_bottom_window_union_frames"] = union
        out["LR_bottom_window_iou"] = intersection / union
        out["LR_bottom_center_time_diff_s"] = abs(
            out["L_bottom_center_frame"] - out["R_bottom_center_frame"]) / float(fps)
        out["LR_bottom_low_iou_warning"] = (
            out["LR_bottom_window_iou"] < float(iou_warning_threshold))
    else:
        for key in ("LR_bottom_window_intersection_frames",
                    "LR_bottom_window_union_frames",
                    "LR_bottom_window_iou", "LR_bottom_center_time_diff_s"):
            out[key] = math.nan
        out["LR_bottom_low_iou_warning"] = True

    # Preserve v0.1 QC assessment for direct side-by-side comparison.
    out["qc_review_v01"] = bool(
        out.get("L_qc_review_required", True) or
        out.get("R_qc_review_required", True) or
        out.get("LR_disagreement_warning", True))
    out["qc_review_v02"] = bool(
        out["qc_review_v01"] or out["LR_bottom_low_iou_warning"])
    return out
