import pandas as pd
from pathlib import Path

process_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/tcga_lihc_er_process_list_labeled_only.csv")
patch_dir = Path("/data3/chensx/CLAM/data/tcga_lihc_er/patches/patches")

df = pd.read_csv(process_csv)

renamed = 0
missing = 0
conflict = 0

for _, row in df.iterrows():
    slide_id = str(row["slide_id"]).strip()
    wsi_path = Path(str(row["wsi_path"]).strip())

    old_h5 = patch_dir / f"{wsi_path.stem}.h5"
    new_h5 = patch_dir / f"{slide_id}.h5"

    if not old_h5.exists():
        print(f"[MISSING] {old_h5}")
        missing += 1
        continue

    if new_h5.exists() and old_h5 != new_h5:
        print(f"[CONFLICT] {new_h5}")
        conflict += 1
        continue

    if old_h5 != new_h5:
        old_h5.rename(new_h5)
        renamed += 1

print(f"[DONE] renamed={renamed}, missing={missing}, conflict={conflict}")