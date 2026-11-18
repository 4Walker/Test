import numpy as np
import pandas as pd
from src.ds01 import compute_angles, detect_bottom

def test_signed_angles():
    d=pd.DataFrame({
        "shoulder_x_px":[80],"hip_x_px":[100],"hip_y_px":[200],"shoulder_y_px":[100],
        "knee_x_px":[90],"ankle_x_px":[100],"ankle_y_px":[300],"knee_y_px":[200],
        **{f"{name}_visibility":[1.0] for name in ("shoulder","hip","knee","ankle")}})
    l=compute_angles(d,"L")
    assert np.isclose(l.torso_deg.iloc[0],11.309932,atol=.0001)
    assert np.isclose(l.tibia_deg.iloc[0],5.710593,atol=.0001)

def test_bottom_relative_displacement():
    y=[100,100,100,120,150,180,200,200,198,150,100]
    d=pd.DataFrame({"frame_index":range(len(y)),"hip_y_px":y})
    out,b,status=detect_bottom(d,{"median_window_frames":3,"baseline_frames":3,"displacement_fraction":.95})
    assert status=="OK"
    assert b["start_frame"]<=b["frame"]<=b["end_frame"]
    assert out.is_bottom_window.sum()>0
