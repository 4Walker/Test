"""DS01 v0.1: 2D sagittal angles; exploratory QC, not official FMS scoring."""
import numpy as np
import pandas as pd

LANDMARKS = {"L": (11, 23, 25, 27), "R": (12, 24, 26, 28)}
SIGN = {"L": -1, "R": 1}
REQUIRED = {"frame_index", "timestamp_ms", "landmark_id", "x", "y", "visibility"}

def load_pose(path, side, width, height):
    side = side.upper()
    if side not in LANDMARKS:
        raise ValueError("side must be L or R")
    raw = pd.read_csv(path)
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if raw.duplicated(["frame_index", "landmark_id"]).any():
        raise ValueError("Duplicate frame_index/landmark_id records")
    ids = LANDMARKS[side]
    raw = raw.loc[raw.landmark_id.isin(ids)].copy()
    if raw.empty:
        raise ValueError("No matching landmark records")
    fields = ["x", "y", "visibility"]
    wide = raw.pivot(index="frame_index", columns="landmark_id", values=fields)
    frames = np.arange(int(raw.frame_index.min()), int(raw.frame_index.max()) + 1)
    wide = wide.reindex(frames)
    out = pd.DataFrame(index=frames)
    for label, lid in zip(("shoulder","hip","knee","ankle"),ids):
        for field in fields:
            col=(field,lid)
            out[f"{label}_{field}"] = wide[col] if col in wide else np.nan
        out[f"{label}_x_px"] = out[f"{label}_x"] * width
        out[f"{label}_y_px"] = out[f"{label}_y"] * height
    times = pd.read_csv(path, usecols=["frame_index","timestamp_ms"]).drop_duplicates("frame_index")
    out["timestamp_ms"] = times.set_index("frame_index")["timestamp_ms"].reindex(frames)
    out.index.name="frame_index"
    return out.reset_index()

def compute_angles(df, side):
    side=side.upper()
    s=SIGN[side]
    out=df.copy()
    out["torso_deg"] = s*np.degrees(np.arctan2(
        out.shoulder_x_px-out.hip_x_px, out.hip_y_px-out.shoulder_y_px))
    out["tibia_deg"] = s*np.degrees(np.arctan2(
        out.knee_x_px-out.ankle_x_px, out.ankle_y_px-out.knee_y_px))
    out["difference_deg"]=out.torso_deg-out.tibia_deg
    out["abs_difference_deg"]=out.difference_deg.abs()
    out["min_visibility"]=out[[f"{j}_visibility" for j in ("shoulder","hip","knee","ankle")]].min(axis=1)
    return out

def detect_bottom(df, cfg):
    """Relative hip displacement from initial baseline; contiguous run around peak."""
    n=int(cfg["median_window_frames"])
    if n < 1 or n % 2 != 1:
        raise ValueError("median_window_frames must be positive and odd")
    out=df.copy()
    out["hip_y_smoothed"]=out.hip_y_px.rolling(n,center=True,min_periods=1).median()
    baseline_n=max(1,int(cfg["baseline_frames"]))
    baseline=out.hip_y_smoothed.iloc[:baseline_n].median()
    displacement=out.hip_y_smoothed-baseline
    out["hip_displacement_px"]=displacement
    if displacement.notna().sum()==0 or displacement.max() <= 0:
        out["is_bottom_window"]=False
        return out, None, "NO_VALID_DESCENT"
    peak_idx=int(displacement.idxmax())
    peak=float(displacement.iloc[peak_idx])
    mask=(displacement >= peak*float(cfg["displacement_fraction"])).fillna(False).to_numpy()
    lo=hi=peak_idx
    while lo>0 and mask[lo-1]: lo-=1
    while hi<len(mask)-1 and mask[hi+1]: hi+=1
    out["is_bottom_window"]=False
    out.loc[lo:hi,"is_bottom_window"]=True
    return out, {"frame":int(out.iloc[peak_idx].frame_index),
                 "start_frame":int(out.iloc[lo].frame_index),
                 "end_frame":int(out.iloc[hi].frame_index)}, "OK"

def extract(path, side, cfg):
    df=compute_angles(load_pose(path,side,cfg["video"]["width"],cfg["video"]["height"]),side)
    df,bottom,status=detect_bottom(df,cfg["bottom"])
    threshold=float(cfg["qc"]["visibility_warning_threshold"])
    jump=float(cfg["qc"]["max_frame_angle_jump_deg"])
    df["qc_low_visibility"]=df.min_visibility < threshold
    df["qc_angle_jump"]=(df.torso_deg.diff().abs()>jump)|(df.tibia_deg.diff().abs()>jump)
    df["qc_missing"]=df[["torso_deg","tibia_deg","difference_deg"]].isna().any(axis=1)
    df["qc_warning"]=df[["qc_low_visibility","qc_angle_jump","qc_missing"]].any(axis=1)
    bottom_df=df.loc[df.is_bottom_window & ~df.qc_missing]
    prefix=f"{side.upper()}_"
    summary={
        prefix+"max_torso_deg":float(df.torso_deg.max()),
        prefix+"max_tibia_deg":float(df.tibia_deg.max()),
        prefix+"bottom_difference_median_deg":float(bottom_df.difference_deg.median()) if len(bottom_df) else np.nan,
        prefix+"bottom_torso_median_deg":float(bottom_df.torso_deg.median()) if len(bottom_df) else np.nan,
        prefix+"bottom_tibia_median_deg":float(bottom_df.tibia_deg.median()) if len(bottom_df) else np.nan,
        prefix+"bottom_frame":bottom["frame"] if bottom else np.nan,
        prefix+"bottom_start_frame":bottom["start_frame"] if bottom else np.nan,
        prefix+"bottom_end_frame":bottom["end_frame"] if bottom else np.nan,
        prefix+"bottom_status":status,
        prefix+"valid_fraction":float((~df.qc_missing).mean()),
        prefix+"low_visibility_frames":int(df.qc_low_visibility.sum()),
        prefix+"angle_jump_frames":int(df.qc_angle_jump.sum()),
        prefix+"bottom_low_visibility_frames":int(bottom_df.qc_low_visibility.sum()),
    }
    summary[prefix+"qc_review_required"]=bool(
        status!="OK" or
        summary[prefix+"valid_fraction"] < float(cfg["qc"]["min_valid_fraction"]) or
        summary[prefix+"angle_jump_frames"]>0 or
        summary[prefix+"bottom_low_visibility_frames"]>0)
    return df,summary

def fuse(left,right,cfg,trial_id):
    result={"trial_id":trial_id, **left, **right}
    for feature in ("max_torso_deg","max_tibia_deg","bottom_difference_median_deg"):
        a=left.get("L_"+feature,np.nan); b=right.get("R_"+feature,np.nan)
        result["LR_"+feature+"_abs_diff"]=abs(a-b) if np.isfinite(a) and np.isfinite(b) else np.nan
    a=left.get("L_bottom_frame",np.nan); b=right.get("R_bottom_frame",np.nan)
    result["LR_bottom_time_diff_s"]=abs(a-b)/float(cfg["video"]["fps"]) if np.isfinite(a) and np.isfinite(b) else np.nan
    result["LR_disagreement_warning"]=any(
        np.isfinite(result["LR_"+f+"_abs_diff"]) and result["LR_"+f+"_abs_diff"] > float(cfg["qc"]["lr_disagreement_warning_deg"])
        for f in ("max_torso_deg","max_tibia_deg","bottom_difference_median_deg"))
    return result
