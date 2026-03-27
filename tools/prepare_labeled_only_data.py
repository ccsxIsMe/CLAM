import os
import pandas as pd
from pathlib import Path

# =========================
# 1. 路径配置
# =========================
task_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/tcga_lihc_er.csv")
slides_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/metadata/slides.csv")

out_process_csv = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/tcga_lihc_er_process_list_labeled_only.csv")
flat_dir = Path("/data3/chensx/tcga_data_er_only")

# 是否覆盖已有软链接
overwrite_symlink = False

# =========================
# 2. 读取数据
# =========================
task_df = pd.read_csv(task_csv)
slides_df = pd.read_csv(slides_csv)

print(f"[INFO] task csv rows: {len(task_df)}")
print(f"[INFO] slides csv rows: {len(slides_df)}")

# 基本列检查
required_task_cols = {"slide_id"}
required_slides_cols = {"slide_id", "wsi_path"}

if not required_task_cols.issubset(task_df.columns):
    raise ValueError(f"tcga_lihc_er.csv 缺少列: {required_task_cols - set(task_df.columns)}")

if not required_slides_cols.issubset(slides_df.columns):
    raise ValueError(f"slides.csv 缺少列: {required_slides_cols - set(slides_df.columns)}")

# =========================
# 3. 只保留任务真正使用的 slide
# =========================
task_slide_ids = task_df["slide_id"].astype(str).str.strip().drop_duplicates()
task_slide_ids = pd.DataFrame({"slide_id": task_slide_ids})

merged = task_slide_ids.merge(
    slides_df[["slide_id", "wsi_path"]].copy(),
    on="slide_id",
    how="left"
)

print(f"[INFO] unique labeled slide_ids: {len(task_slide_ids)}")

# =========================
# 4. 清洗路径，检查缺失
# =========================
merged["wsi_path"] = merged["wsi_path"].astype(str).str.strip()

missing_path_df = merged[merged["wsi_path"].isna() | (merged["wsi_path"] == "") | (merged["wsi_path"].str.lower() == "nan")]
if len(missing_path_df) > 0:
    print("[WARNING] 以下 slide_id 在 slides.csv 中找不到 wsi_path:")
    print(missing_path_df.head(20).to_string(index=False))
    missing_path_df.to_csv(
        "/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/missing_wsi_path.csv",
        index=False
    )

# 只保留有路径的
merged = merged[~merged["wsi_path"].isna()].copy()
merged = merged[merged["wsi_path"] != ""].copy()
merged = merged[merged["wsi_path"].str.lower() != "nan"].copy()

# =========================
# 5. 检查文件是否真的存在
# =========================
merged["file_exists"] = merged["wsi_path"].apply(lambda x: Path(x).exists())

not_exist_df = merged[~merged["file_exists"]].copy()
if len(not_exist_df) > 0:
    print("[WARNING] 以下 wsi_path 对应文件不存在:")
    print(not_exist_df.head(20).to_string(index=False))
    not_exist_df.to_csv(
        "/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/nonexistent_wsi_path.csv",
        index=False
    )

valid_df = merged[merged["file_exists"]].copy()

print(f"[INFO] valid labeled slides with existing WSI: {len(valid_df)}")

# =========================
# 6. 保存 labeled-only process list
# =========================
out_process_csv.parent.mkdir(parents=True, exist_ok=True)
valid_df[["slide_id", "wsi_path"]].drop_duplicates().to_csv(out_process_csv, index=False)
print(f"[INFO] saved process list to: {out_process_csv}")

# =========================
# 7. 创建平铺目录软链接
# =========================
flat_dir.mkdir(parents=True, exist_ok=True)

created = 0
skipped = 0
conflict = 0

for _, row in valid_df.iterrows():
    src = Path(row["wsi_path"])
    dst = flat_dir / src.name

    if dst.exists() or dst.is_symlink():
        # 已存在时检查是不是同一个源
        if dst.is_symlink():
            try:
                current_target = Path(os.readlink(dst))
                # 如果 readlink 是相对路径，转成绝对判断
                if not current_target.is_absolute():
                    current_target = (dst.parent / current_target).resolve()
                else:
                    current_target = current_target.resolve()
                src_resolved = src.resolve()

                if current_target == src_resolved:
                    skipped += 1
                    continue
            except Exception:
                pass

        if overwrite_symlink:
            dst.unlink()
        else:
            print(f"[WARNING] 目标已存在且不覆盖: {dst}")
            conflict += 1
            continue

    os.symlink(src, dst)
    created += 1

print(f"[INFO] symlink created: {created}")
print(f"[INFO] symlink skipped (already correct): {skipped}")
print(f"[INFO] symlink conflicts: {conflict}")

# =========================
# 8. 额外保存一份统计信息
# =========================
summary_path = Path("/data3/chensx/CLAM/data/tcga_lihc_er/dataset_csv/prepare_labeled_only_summary.txt")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write(f"task csv rows: {len(task_df)}\n")
    f.write(f"unique labeled slide_ids: {len(task_slide_ids)}\n")
    f.write(f"valid labeled slides with existing WSI: {len(valid_df)}\n")
    f.write(f"symlink created: {created}\n")
    f.write(f"symlink skipped: {skipped}\n")
    f.write(f"symlink conflicts: {conflict}\n")

print(f"[INFO] summary saved to: {summary_path}")
print("[INFO] Done.")