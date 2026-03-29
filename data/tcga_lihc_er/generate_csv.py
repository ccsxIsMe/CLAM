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
    parser.add_argument(
        "--patches-dir",
        type=Path,
        default=None,
        help="Optional directory containing patch coordinate .h5 files used to build a filtered trainable subset.",
    )
    parser.add_argument(
        "--features-pt-dir",
        type=Path,
        default=None,
        help="Optional directory containing extracted .pt features used to build a filtered trainable subset.",
    )
    parser.add_argument(
        "--out-filtered-dataset-csv",
        type=Path,
        default=root / "dataset_csv" / "tcga_lihc_er_filtered.csv",
        help="Filtered dataset CSV written when --patches-dir or --features-pt-dir is provided.",
    )
    parser.add_argument(
        "--out-filtered-process-list-csv",
        type=Path,
        default=root / "dataset_csv" / "tcga_lihc_er_process_list_filtered.csv",
        help="Filtered process list CSV written when availability filtering is enabled.",
    )
    parser.add_argument(
        "--out-filtered-splits-dir",
        type=Path,
        default=root / "splits_filtered",
        help="Directory for filtered CLAM split CSVs when availability filtering is enabled.",
    )
    parser.add_argument(
        "--missing-report-csv",
        type=Path,
        default=root / "dataset_csv" / "missing_required_files.csv",
        help="CSV report listing slides excluded by availability filtering.",
    )
    parser.add_argument(
        "--summary-txt",
        type=Path,
        default=root / "dataset_csv" / "prepare_trainable_summary.txt",
        help="Summary text for availability filtering.",
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


def build_split_frame(split_df, split_col):
    train_ids = split_df.loc[split_df[split_col] == "train", "slide_id"].tolist()
    val_ids = split_df.loc[split_df[split_col] == "val", "slide_id"].tolist()
    test_ids = split_df.loc[split_df[split_col] == "test", "slide_id"].tolist()

    max_len = max(len(train_ids), len(val_ids), len(test_ids))
    return pd.DataFrame(
        {
            "train": pad_column(train_ids, max_len),
            "val": pad_column(val_ids, max_len),
            "test": pad_column(test_ids, max_len),
        }
    )


def collect_missing_requirements(process_df, slide_id_col, patches_dir=None, features_pt_dir=None):
    if patches_dir is None and features_pt_dir is None:
        return [], set(process_df[slide_id_col].tolist())

    missing_rows = []
    available_slide_ids = set()

    for row in process_df.itertuples(index=False):
        slide_id = getattr(row, slide_id_col)
        reasons = []

        if patches_dir is not None:
            patch_path = patches_dir / f"{slide_id}.h5"
            if not patch_path.is_file():
                reasons.append("missing_patch_h5")

        if features_pt_dir is not None:
            feature_path = features_pt_dir / f"{slide_id}.pt"
            if not feature_path.is_file():
                reasons.append("missing_feature_pt")

        if reasons:
            missing_rows.append(
                {
                    "slide_id": slide_id,
                    "wsi_path": getattr(row, "wsi_path"),
                    "reason": ";".join(reasons),
                }
            )
        else:
            available_slide_ids.add(slide_id)

    return missing_rows, available_slide_ids


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
    split_df = None

    if not args.skip_splits:
        splits = pd.read_csv(args.splits_csv)
        split_df = splits.merge(labels, on=args.case_col, how="inner").copy()
        split_df = split_df.rename(columns={args.slide_id_col: "slide_id"})
        split_df = split_df[["slide_id", args.split_col]].drop_duplicates()
        split_out = build_split_frame(split_df, args.split_col)
        split_out.to_csv(args.out_split_csv, index=False)
        written_files.append(args.out_split_csv)

    missing_rows, available_slide_ids = collect_missing_requirements(
        process_df.rename(columns={args.slide_id_col: "slide_id", args.slide_path_col: "wsi_path"}),
        "slide_id",
        patches_dir=args.patches_dir,
        features_pt_dir=args.features_pt_dir,
    )

    if args.patches_dir is not None or args.features_pt_dir is not None:
        args.out_filtered_dataset_csv.parent.mkdir(parents=True, exist_ok=True)
        args.out_filtered_process_list_csv.parent.mkdir(parents=True, exist_ok=True)
        args.out_filtered_splits_dir.mkdir(parents=True, exist_ok=True)
        args.missing_report_csv.parent.mkdir(parents=True, exist_ok=True)
        args.summary_txt.parent.mkdir(parents=True, exist_ok=True)

        filtered_dataset_df = dataset_df[dataset_df["slide_id"].isin(available_slide_ids)].copy()
        filtered_process_df = process_df[process_df[args.slide_id_col].isin(available_slide_ids)].copy()

        filtered_dataset_df.to_csv(args.out_filtered_dataset_csv, index=False)
        filtered_process_df.to_csv(args.out_filtered_process_list_csv, index=False)
        written_files.extend([args.out_filtered_dataset_csv, args.out_filtered_process_list_csv])

        missing_report_df = pd.DataFrame(missing_rows, columns=["slide_id", "wsi_path", "reason"])
        missing_report_df.to_csv(args.missing_report_csv, index=False)
        written_files.append(args.missing_report_csv)

        summary_lines = [
            f"total_dataset_rows={len(dataset_df)}",
            f"available_rows={len(filtered_dataset_df)}",
            f"excluded_rows={len(missing_rows)}",
            f"patches_dir={args.patches_dir}",
            f"features_pt_dir={args.features_pt_dir}",
        ]

        if split_df is not None:
            filtered_split_df = split_df[split_df["slide_id"].isin(available_slide_ids)].copy()
            filtered_split_out = build_split_frame(filtered_split_df, args.split_col)
            filtered_split_path = args.out_filtered_splits_dir / "splits_0.csv"
            filtered_split_out.to_csv(filtered_split_path, index=False)
            written_files.append(filtered_split_path)
            summary_lines.extend(
                [
                    f"filtered_train={len(filtered_split_df[filtered_split_df[args.split_col] == 'train'])}",
                    f"filtered_val={len(filtered_split_df[filtered_split_df[args.split_col] == 'val'])}",
                    f"filtered_test={len(filtered_split_df[filtered_split_df[args.split_col] == 'test'])}",
                ]
            )

        args.summary_txt.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        written_files.append(args.summary_txt)

    print("Wrote:")
    for path in written_files:
        print(f" - {path}")


if __name__ == "__main__":
    main()
