import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description="Prepare CLAM dataset_csv and split CSVs for TCGA-LIHC early recurrence."
    )
    parser.add_argument(
        "--slides-csv",
        type=Path,
        default=root / "metadata" / "slides.csv",
        help="CSV containing slide metadata with slide_id and wsi_path columns.",
    )
    parser.add_argument(
        "--labels-csv",
        type=Path,
        default=root / "metadata" / "labels_24m.csv",
        help="CSV containing patient-level labels.",
    )
    parser.add_argument(
        "--splits-csv",
        type=Path,
        default=root / "metadata" / "splits.csv",
        help="Optional CSV containing train/val/test assignments.",
    )
    parser.add_argument(
        "--out-dataset-csv",
        type=Path,
        default=root / "dataset_csv" / "tcga_lihc_er.csv",
        help="Output CLAM dataset CSV with case_id, slide_id, and label columns.",
    )
    parser.add_argument(
        "--out-process-list-csv",
        type=Path,
        default=root / "dataset_csv" / "tcga_lihc_er_process_list.csv",
        help="Output process list CSV for patch/feature extraction.",
    )
    parser.add_argument(
        "--out-split-csv",
        type=Path,
        default=root / "splits" / "splits_0.csv",
        help="Output CLAM split CSV with train/val/test columns.",
    )
    parser.add_argument("--case-col", type=str, default="patient_id")
    parser.add_argument("--slide-id-col", type=str, default="slide_id")
    parser.add_argument("--slide-path-col", type=str, default="wsi_path")
    parser.add_argument("--label-col", type=str, default="early_recurrence")
    parser.add_argument("--split-col", type=str, default="split")
    parser.add_argument(
        "--skip-splits",
        action="store_true",
        help="Only write dataset_csv and process_list outputs.",
    )

    return parser.parse_args()


def pad_column(values, target_len):
    return values + [None] * (target_len - len(values))


def main():
    args = parse_args()

    slides = pd.read_csv(args.slides_csv)
    labels = pd.read_csv(args.labels_csv)

    args.out_dataset_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_process_list_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_split_csv.parent.mkdir(parents=True, exist_ok=True)

    dataset_df = slides.merge(labels, on=args.case_col, how="inner").copy()
    dataset_df = dataset_df.rename(
        columns={
            args.case_col: "case_id",
            args.label_col: "label",
        }
    )
    dataset_df = dataset_df[["case_id", args.slide_id_col, "label"]].drop_duplicates()
    dataset_df = dataset_df.rename(columns={args.slide_id_col: "slide_id"})
    dataset_df["label"] = dataset_df["label"].astype(int)
    dataset_df.to_csv(args.out_dataset_csv, index=False)

    process_df = slides[[args.slide_id_col, args.slide_path_col]].drop_duplicates().copy()
    process_df.to_csv(args.out_process_list_csv, index=False)

    written_files = [args.out_dataset_csv, args.out_process_list_csv]

    if not args.skip_splits:
        splits = pd.read_csv(args.splits_csv)
        split_df = splits.merge(labels, on=args.case_col, how="inner").copy()
        split_df = split_df.rename(columns={args.slide_id_col: "slide_id"})
        split_df = split_df[["slide_id", args.split_col]].drop_duplicates()

        train_ids = split_df.loc[split_df[args.split_col] == "train", "slide_id"].tolist()
        val_ids = split_df.loc[split_df[args.split_col] == "val", "slide_id"].tolist()
        test_ids = split_df.loc[split_df[args.split_col] == "test", "slide_id"].tolist()

        max_len = max(len(train_ids), len(val_ids), len(test_ids))
        split_out = pd.DataFrame(
            {
                "train": pad_column(train_ids, max_len),
                "val": pad_column(val_ids, max_len),
                "test": pad_column(test_ids, max_len),
            }
        )
        split_out.to_csv(args.out_split_csv, index=False)
        written_files.append(args.out_split_csv)

    print("Wrote:")
    for path in written_files:
        print(f" - {path}")


if __name__ == "__main__":
    main()
