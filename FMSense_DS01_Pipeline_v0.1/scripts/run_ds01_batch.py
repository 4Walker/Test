"""Batch process paired L/R MediaPipe CSVs, preserving v0.1 DS01 formulas.

Expected names: <trial_key>_L.csv and <trial_key>_R.csv.
Example: S01_P01_M01_L_T01_L.csv and S01_P01_M01_L_T01_R.csv.
The final suffix is the CAMERA label, not the movement condition.
"""
import argparse
import csv
import sys
from pathlib import Path
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ds01 import extract, fuse
from src.bottom_qc import add_bottom_diagnostics
from src.visualization import plot_angles

def discover_pairs(source):
    groups={}
    for path in sorted(source.rglob("*.csv")):
        stem=path.stem
        if not (stem.endswith("_L") or stem.endswith("_R")):
            continue
        side=stem[-1]
        key=stem[:-2]
        groups.setdefault(key, {})[side]=path
    return groups

def main():
    parser=argparse.ArgumentParser(description="FMSense DS01 batch v0.2 (Floor/Board separate)")
    parser.add_argument("--input",required=True,help="Folder containing MediaPipe CSV files")
    parser.add_argument("--condition",choices=["FLOOR","BOARD"],required=True)
    parser.add_argument("--output",default="outputs/batch")
    parser.add_argument("--config",default=str(Path(__file__).resolve().parents[1]/"config.yaml"))
    parser.add_argument("--iou-warning",type=float,default=0.60,
                        help="Exploratory minimum bottom-window IoU before QC review")
    parser.add_argument("--plots",action="store_true",help="Save one plot per view (extra processing time)")
    args=parser.parse_args()

    source=Path(args.input)
    if not source.is_dir():
        parser.error(f"Input folder does not exist: {source}")
    config=yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    dest=Path(args.output)/args.condition.lower()
    dest.mkdir(parents=True,exist_ok=True)

    groups=discover_pairs(source)
    if not groups:
        parser.error("No *_L.csv or *_R.csv files found")

    rows=[]
    log=[]
    for trial_key, cameras in sorted(groups.items()):
        missing=[side for side in ("L","R") if side not in cameras]
        if missing:
            log.append({"trial_id":trial_key,"condition":args.condition,
                        "status":"MISSING_VIEW","detail":",".join(missing)})
            continue
        try:
            frames={}
            summaries={}
            for side in ("L","R"):
                frames[side],summaries[side]=extract(cameras[side],side,config)
            combined=fuse(summaries["L"],summaries["R"],config,trial_key)
            combined=add_bottom_diagnostics(combined,config["video"]["fps"],args.iou_warning)
            combined["condition"]=args.condition
            combined["L_file"]=cameras["L"].name
            combined["R_file"]=cameras["R"].name
            rows.append(combined)
            if args.plots:
                plot_folder=dest/"figures"/trial_key
                plot_folder.mkdir(parents=True,exist_ok=True)
                for side in ("L","R"):
                    plot_angles(frames[side],side,plot_folder/f"{side}_angles.png")
            flagged=bool(combined["L_qc_review_required"] or combined["R_qc_review_required"]
                         or combined["LR_disagreement_warning"]
                         or combined["LR_bottom_low_iou_warning"])
            log.append({"trial_id":trial_key,"condition":args.condition,
                        "status":"REVIEW" if flagged else "OK","detail":""})
        except (ValueError,KeyError,IndexError,TypeError,FileNotFoundError) as exc:
            log.append({"trial_id":trial_key,"condition":args.condition,
                        "status":"ERROR","detail":str(exc)[:500]})

    pd.DataFrame(rows).to_csv(dest/"trial_features.csv",index=False)
    pd.DataFrame(log,columns=["trial_id","condition","status","detail"]).to_csv(
        dest/"processing_log.csv",index=False)
    counts=pd.Series([item["status"] for item in log]).value_counts().to_dict()
    print("Detected trial keys:",len(groups))
    print("Successfully processed:",len(rows))
    print("Status counts:",counts)
    print("Outputs:",dest)
    if len(groups)!=15 and args.condition=="FLOOR":
        print("NOTE: expected 15 Trial pairs for your initial 5-participant pilot; review file pairing.")

if __name__=="__main__":
    main()
