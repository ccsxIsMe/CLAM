import os
import pandas as pd
from pathlib import Path

process_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/tcga_lihc_er_process_list_labeled_only.csv")
flat_dir = Path("/data3/chensx/tcga_data_er_only")

# 是否先清空旧目录中的软链接
clear_old_links = True

df = pd.read_csv(process_csv)
required_cols = {"slide_id", "wsi_path"}
if not required_cols.issubset(df.columns):
    raise ValueError(f"process list 缺少列: {required_cols - set(df.columns)}")

flat_dir.mkdir(parents=True, exist_ok=True)

if clear_old_links:
    for p in flat_dir.iterdir():
        if p.is_symlink() or p.is_file():
            p.unlink()

created = 0
missing = 0
conflict = 0

for _, row in df.iterrows():
    slide_id = str(row["slide_id"]).strip()
    src = Path(str(row["wsi_path"]).strip())

    if not src.exists():
        print(f"[MISSING] {slide_id}: {src}")
        missing += 1
        continue

    dst = flat_dir / f"{slide_id}.svs"

    if dst.exists() or dst.is_symlink():
        print(f"[CONFLICT] already exists: {dst}")
        conflict += 1
        continue

    os.symlink(src, dst)
    created += 1

print(f"[DONE] created={created}, missing={missing}, conflict={conflict}")