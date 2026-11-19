import math
from src.bottom_qc import add_bottom_diagnostics

def test_inclusive_overlap_p04_t01():
    row = {
        "L_bottom_start_frame":271, "L_bottom_end_frame":322,
        "R_bottom_start_frame":266, "R_bottom_end_frame":325,
        "L_qc_review_required":True, "R_qc_review_required":False,
        "LR_disagreement_warning":False,
    }
    result=add_bottom_diagnostics(row, 50)
    assert result["L_bottom_duration_s"] == 52 / 50
    assert result["R_bottom_duration_s"] == 60 / 50
    assert result["LR_bottom_window_intersection_frames"] == 52
    assert result["LR_bottom_window_union_frames"] == 60
    assert math.isclose(result["LR_bottom_window_iou"],52/60)
    assert math.isclose(result["LR_bottom_center_time_diff_s"],0.02)
    assert not result["LR_bottom_low_iou_warning"]
    assert result["qc_review_v02"]  # existing low-visibility review remains

def test_disjoint_windows():
    result=add_bottom_diagnostics({
        "L_bottom_start_frame":1,"L_bottom_end_frame":5,
        "R_bottom_start_frame":10,"R_bottom_end_frame":12,
        "L_qc_review_required":False,"R_qc_review_required":False,
        "LR_disagreement_warning":False},50)
    assert result["LR_bottom_window_iou"]==0
    assert result["LR_bottom_low_iou_warning"]
    assert not result["qc_review_v01"] and result["qc_review_v02"]

def test_missing_window():
    result=add_bottom_diagnostics({
        "L_bottom_start_frame":None,"L_bottom_end_frame":None,
        "R_bottom_start_frame":1,"R_bottom_end_frame":2},50)
    assert math.isnan(result["LR_bottom_window_iou"])
    assert result["LR_bottom_low_iou_warning"]
