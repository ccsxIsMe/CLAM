import pandas as pd
from pathlib import Path

root = Path("/data3/chensx/CLAM/data/tcga_lihc_er")
meta = root / "metadata"
out_dataset = root / "dataset_csv"
out_splits = root / "splits"
out_dataset.mkdir(parents=True, exist_ok=True)
out_splits.mkdir(parents=True, exist_ok=True)

slides = pd.read_csv(meta / "slides.csv")          # patient_id, slide_id, wsi_path
labels = pd.read_csv(meta / "labels_24m.csv")      # patient_id, early_recurrence
splits = pd.read_csv(meta / "splits.csv")          # patient_id, slide_id, split

# 1) 训练主表
df = slides.merge(labels, on="patient_id", how="inner").copy()
df = df.rename(columns={
    "patient_id": "case_id",
    "early_recurrence": "label"
})
df = df[["case_id", "slide_id", "label"]].drop_duplicates()

# 保证 label 是整数 0/1
df["label"] = df["label"].astype(int)
df.to_csv(out_dataset / "tcga_lihc_er.csv", index=False)

# 2) process list: 给 patch / feature extraction 用
process_df = slides[["slide_id", "wsi_path"]].drop_duplicates().copy()
process_df.to_csv(out_dataset / "tcga_lihc_er_process_list.csv", index=False)

# 3) 生成一个 CLAM 可读的 split 文件（单折）
split_df = splits.merge(labels, on="patient_id", how="inner").copy()
split_df = split_df.rename(columns={
    "patient_id": "case_id",
    "early_recurrence": "label"
})
split_df = split_df[["case_id", "slide_id", "split"]].drop_duplicates()

# CLAM 常见 split 文件是三列并排：train / val / test
train_ids = split_df.loc[split_df["split"] == "train", "slide_id"].tolist()
val_ids   = split_df.loc[split_df["split"] == "val", "slide_id"].tolist()
test_ids  = split_df.loc[split_df["split"] == "test", "slide_id"].tolist()

max_len = max(len(train_ids), len(val_ids), len(test_ids))
pad = lambda x: x + [None] * (max_len - len(x))

split_out = pd.DataFrame({
    "train": pad(train_ids),
    "val": pad(val_ids),
    "test": pad(test_ids),
})
split_out.to_csv(out_splits / "split0.csv", index=False)

print("Done:")
print(" -", out_dataset / "tcga_lihc_er.csv")
print(" -", out_dataset / "tcga_lihc_er_process_list.csv")
print(" -", out_splits / "split0.csv")