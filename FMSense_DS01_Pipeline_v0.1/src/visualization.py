import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def plot_angles(df, side, destination):
    fig,ax=plt.subplots(figsize=(11,5))
    t=df.timestamp_ms/1000
    ax.plot(t,df.torso_deg,label="Torso (deg)")
    ax.plot(t,df.tibia_deg,label="Tibia (deg)")
    ax.plot(t,df.difference_deg,label="Torso - tibia (deg)")
    bottom=df[df.is_bottom_window]
    if not bottom.empty:
        ax.axvspan(bottom.timestamp_ms.iloc[0]/1000,bottom.timestamp_ms.iloc[-1]/1000,
                   alpha=.18,label="Bottom window")
    flagged=df[df.qc_angle_jump]
    if not flagged.empty:
        ax.scatter(flagged.timestamp_ms/1000,flagged.torso_deg,s=16,marker="x",label="Angle jump")
    ax.set(xlabel="Time (s)",ylabel="Angle (degrees)",title=f"DS01 {side} camera | v0.1")
    ax.grid(alpha=.25);ax.legend()
    fig.tight_layout();fig.savefig(destination,dpi=170);plt.close(fig)
