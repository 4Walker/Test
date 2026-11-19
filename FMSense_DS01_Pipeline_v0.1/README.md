# FMSense DS01 Pipeline v0.1

Reproducible 2D Deep Squat torso–tibia measurements from **two synchronized MediaPipe CSVs**. This is an exploratory research prototype, **not** a validated FMS scoring system.

## Privacy

This is a **public** repository. Research participant videos and landmark CSVs are **not committed**. Keep them on your own machine. Do not commit identifying participant metadata.

## Required input

Two CSV files, one per camera. Each has long-format columns:
`frame_index,timestamp_ms,landmark_id,x,y,z,visibility,presence`

Required: `frame_index,timestamp_ms,landmark_id,x,y,visibility`.

- Default resolution: 1440×1920, 50 fps. No video rotation or mirroring.
- L camera: person faces screen left, landmarks 11/23/25/27; sign −1.
- R camera: person faces screen right, landmarks 12/24/26/28; sign +1.
- Four views of the same trial are not independent ML samples.

## Installation

Clone this repository and open the subfolder `FMSense_DS01_Pipeline_v0.1` in PyCharm.

```bash
git clone https://github.com/4Walker/Test.git
cd Test/FMSense_DS01_Pipeline_v0.1
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

## Run on your local research files

For example, place your two **local** CSVs in `data/raw` (create that directory locally; it is excluded from Git).

```bash
python scripts/run_ds01.py --left data/raw/S01_P01_M01_L_T01_L.csv --right data/raw/S01_P01_M01_L_T01_R.csv --trial-id S01_P01_M01_T01
```

Results under `outputs/S01_P01_M01_T01/`:
- `L_framewise.csv` and `R_framewise.csv`: pixel coordinates, angle series, bottom mask and QC flags.
- `L_angles.png` and `R_angles.png`: angle curves.
- `trial_features.csv`: one trial-level record with **separate L/R values**, disagreements and QC flags.

## Method

Normalized x/y must be scaled by actual video width/height before 2D angle calculation.

- `torso_deg = sign * degrees(atan2(shoulder_x_px - hip_x_px, hip_y_px - shoulder_y_px))`
- `tibia_deg = sign * degrees(atan2(knee_x_px - ankle_x_px, ankle_y_px - knee_y_px))`
- `difference_deg = torso_deg - tibia_deg`
- Maximum forward torso lean is computed over all available frames, assuming a single full squat.
- Bottom: 5-frame median filter on hip image y; standing baseline from first 15 frames; peak displacement downward; contiguous window containing peak where displacement reaches ≥95% of peak.
- Bottom-position alignment: median torso–tibia signed difference over that bottom window.

The 95%, 0.5 visibility, 8° jump, and 5° cross-view disagreement settings are **provisional engineering parameters** rather than official FMS thresholds.

Low visibility triggers a warning, **not** automatic frame exclusion. Missing landmarks are retained as NaN; no interpolation or L/R averaging.

## Limitations

This version does not yet implement formal movement-phase segmentation, 3D reconstruction, video overlay, biomechanical calibration, batch scanning or expert scoring. Low-quality tracking can influence the maximum-angle feature. Baseline estimation assumes the initial frames contain standing posture, and L/R input streams are synchronized.

Future ML validation must split by participant, not camera or trial.

## Next steps

Batch validation, movement segmentation, improved QC and DS02–DS06 features.

## Batch validation (Step 5C-6A)

The batch runner processes **one condition per invocation** and scans recursively for files ending in `_L.csv` and `_R.csv` with the same trial key before that last suffix. For example, `S01_P01_M01_L_T01_L.csv` matches `S01_P01_M01_L_T01_R.csv`. Check your filename pattern before use: if the camera label appears elsewhere, rename files or use an explicit manifest-based approach instead. Keep FLOOR and BOARD files in **separate directories** and never mix conditions during a run.

Prepare `data/raw/floor/` with the 30 L/R CSVs for 15 trials. Then run:

```bash
python scripts/run_ds01_batch.py --input data/raw/floor --condition FLOOR --output outputs/batch
```

Add `--plots` to generate angle plots for every L/R view. Outputs are `outputs/batch/floor/trial_features.csv` (one row per successfully processed trial) and `outputs/batch/floor/processing_log.csv` (one row per detected trial key, status `OK`, `REVIEW`, `MISSING_VIEW`, or `ERROR`). Review the log and file pairing before interpreting results; `REVIEW` means QC screening, not failure or FMS score. Missing-view trials are retained in the log but do not receive trial-level features.

Important: the batch runner inherits DS01 v0.1 thresholds and its assumptions about starting standing posture and full one-squat clips. Avoid public Git commits containing participant CSVs or exported features.

## Bottom-window QC diagnostics (Step 5C-6B, v0.2)

After a local `git pull origin main`, run the existing batch command again:

```bash
python scripts/run_ds01_batch.py --input data/raw/floor --condition FLOOR --output outputs/batch
```

The batch output now has additional columns:
- `L_bottom_center_frame`, `R_bottom_center_frame`: arithmetic centers of inclusive bottom windows; these may be half frames
- `L_bottom_duration_s`, `R_bottom_duration_s`: window duration computed as **number of frames / fps**
- `LR_bottom_window_iou`: overlap between inclusive L/R frame intervals, intersection / union
- `LR_bottom_center_time_diff_s`: cross-view difference between window centers
- `LR_bottom_low_iou_warning`: exploratory warning if IoU < 0.60
- `qc_review_v01`, `qc_review_v02`: retain old QC state and add the new overlap warning

For an alternate exploratory warning threshold, add `--iou-warning 0.70`. **Neither the 0.60 default nor any other IoU threshold is a validated clinical threshold.** The new version does not change DS01 angle formulas, the 95% bottom interval extraction rule or the original bottom-frame feature. The diagnostic file derived from the previous batch feature table does **not** require re-running MediaPipe, but the full batch command does require original local CSVs.

Review short-duration, long-duration, and low-IoU cases on original L/R videos; a high IoU by itself does not establish pose tracking accuracy.
