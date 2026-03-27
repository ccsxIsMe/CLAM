import pandas as pd
from pathlib import Path

process_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/tcga_lihc_er_process_list_labeled_only.csv")
patch_dir = Path("/data3/chensx/CLAM/data/tcga_lihc_er/patches/patches")

out_ok_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/tcga_lihc_er_process_list_h5_ready.csv")
out_missing_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/missing_patch_h5.csv")

df = pd.read_csv(process_csv)

ok_rows = []
missing_rows = []
renamed = 0
already_ok = 0
matched_by_prefix = 0

for _, row in df.iterrows():
    slide_id = str(row["slide_id"]).strip()
    wsi_path = str(row["wsi_path"]).strip()

    short_h5 = patch_dir / f"{slide_id}.h5"
    if short_h5.exists():
        ok_rows.append(row)
        already_ok += 1
        continue

    # 尝试按前缀匹配长名 h5
    candidates = list(patch_dir.glob(f"{slide_id}*.h5"))

    if len(candidates) == 1:
        old_h5 = candidates[0]
        old_h5.rename(short_h5)
        ok_rows.append(row)
        renamed += 1
        matched_by_prefix += 1
    elif len(candidates) > 1:
        missing_rows.append({
            "slide_id": slide_id,
            "wsi_path": wsi_path,
            "reason": f"multiple_candidates:{[c.name for c in candidates]}"
        })
    else:
        missing_rows.append({
            "slide_id": slide_id,
            "wsi_path": wsi_path,
            "reason": "no_h5_found"
        })

ok_df = pd.DataFrame(ok_rows)
missing_df = pd.DataFrame(missing_rows)

ok_df.to_csv(out_ok_csv, index=False)
missing_df.to_csv(out_missing_csv, index=False)

print(f"[DONE] already_ok={already_ok}, renamed={renamed}, matched_by_prefix={matched_by_prefix}, missing={len(missing_df)}")
print(f"[OUT] h5-ready process list: {out_ok_csv}")
print(f"[OUT] missing patch h5 list: {out_missing_csv}")