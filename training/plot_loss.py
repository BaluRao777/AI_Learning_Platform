"""Export the TensorBoard training loss to docs/training/loss_curve.png and loss.csv.

    python training/plot_loss.py [--run sana_edu_lora]
"""
import argparse
import csv
import glob
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator  # noqa: E402

from common import DOCS_DIR, OUTPUT_DIR  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="sana_edu_lora")
    parser.add_argument("--smooth", type=int, default=50)
    args = parser.parse_args()

    points = {}
    for path in glob.glob(os.path.join(OUTPUT_DIR, args.run, "logs", "**", "events.out.tfevents.*"), recursive=True):
        accumulator = EventAccumulator(path, size_guidance={"scalars": 0})
        accumulator.Reload()
        if "loss" in accumulator.Tags().get("scalars", []):
            for event in accumulator.Scalars("loss"):
                points[event.step] = event.value
    if not points:
        raise SystemExit("no loss scalars found")
    steps = sorted(points)
    values = [points[s] for s in steps]
    window = max(1, min(args.smooth, len(values)))
    smooth = [sum(values[max(0, i - window + 1): i + 1]) / len(values[max(0, i - window + 1): i + 1])
              for i in range(len(values))]

    out_dir = os.path.join(DOCS_DIR, "training")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "loss.csv"), "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["step", "loss", f"mean_last_{window}"])
        writer.writerows(zip(steps, values, smooth))

    plt.figure(figsize=(9, 4.5))
    plt.plot(steps, values, color="#9ecae1", linewidth=0.8, label="loss per step")
    plt.plot(steps, smooth, color="#08519c", linewidth=1.8, label=f"running mean ({window} steps)")
    plt.xlabel("training step")
    plt.ylabel("flow-matching loss")
    plt.title(f"SANA 1.5 LoRA fine-tuning loss ({args.run})")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "loss_curve.png"), dpi=150)
    print(f"steps={len(steps)} first_{window}_mean={sum(values[:window]) / window:.4f} "
          f"last_{window}_mean={smooth[-1]:.4f} final_step_loss={values[-1]:.4f}")


if __name__ == "__main__":
    main()
