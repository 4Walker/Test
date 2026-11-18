import argparse
import sys
from pathlib import Path
import pandas as pd
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ds01 import extract, fuse
from src.visualization import plot_angles

def main():
    p=argparse.ArgumentParser(description="FMSense DS01 v0.1 trial-level extraction")
    p.add_argument("--left",required=True,help="MediaPipe CSV for camera L")
    p.add_argument("--right",required=True,help="MediaPipe CSV for camera R")
    p.add_argument("--trial-id",required=True)
    p.add_argument("--config",default=str(Path(__file__).resolve().parents[1]/"config.yaml"))
    p.add_argument("--output",default=str(Path(__file__).resolve().parents[1]/"outputs"))
    args=p.parse_args()
    cfg=yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    dest=Path(args.output)/args.trial_id
    dest.mkdir(parents=True,exist_ok=True)
    summaries={}
    for side,path in (("L",args.left),("R",args.right)):
        df,summaries[side]=extract(path,side,cfg)
        df.to_csv(dest/f"{side}_framewise.csv",index=False)
        plot_angles(df,side,dest/f"{side}_angles.png")
    merged=fuse(summaries["L"],summaries["R"],cfg,args.trial_id)
    pd.DataFrame([merged]).to_csv(dest/"trial_features.csv",index=False)
    print(pd.Series(merged).to_string())
    print(f"\nOutputs: {dest}")

if __name__=="__main__":
    main()
