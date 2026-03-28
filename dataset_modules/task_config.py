from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


_INT_PATTERN = re.compile(r"^-?\d+$")


@dataclass(frozen=True)
class TaskConfig:
    task: str
    dataset_csv: str
    n_classes: int
    label_dict: Dict[Any, int]
    label_col: str = "label"
    ignore: tuple = field(default_factory=tuple)
    features_subdir: Optional[str] = None
    features_dir: Optional[str] = None
    default_split_dir: Optional[str] = None
    mil_patient_strat: bool = False
    split_patient_strat: bool = True
    split_patient_voting: str = "max"
    subtyping: bool = False
    config_dir: Optional[Path] = None

    def resolve_dataset_csv(self) -> str:
        return _resolve_path(self.dataset_csv, self.config_dir)

    def resolve_features_dir(self, data_root_dir: Optional[str]) -> Optional[str]:
        if self.features_dir:
            return _resolve_path(self.features_dir, self.config_dir)

        if self.features_subdir:
            if data_root_dir is None:
                raise ValueError(
                    f"Task '{self.task}' requires --data_root_dir because it uses "
                    f"features_subdir='{self.features_subdir}'."
                )
            return str(Path(data_root_dir) / self.features_subdir)

        return None

    def resolve_split_dir(self, split_dir: Optional[str], label_frac: Optional[float] = None) -> Optional[str]:
        if split_dir:
            return _resolve_user_path(split_dir, self.config_dir)

        if self.default_split_dir:
            return _resolve_path(self.default_split_dir, self.config_dir)

        if label_frac is None:
            return None

        return str(Path("splits") / f"{self.task}_{int(label_frac * 100)}")


def load_task_config(task: Optional[str], task_config_path: Optional[str] = None) -> TaskConfig:
    if task_config_path:
        config = _load_task_config_from_json(task_config_path)
        if task and task != config.task:
            raise ValueError(
                f"--task ('{task}') does not match task_config task name ('{config.task}')."
            )
        return config

    if not task:
        raise ValueError("Please provide either --task or --task_config.")

    try:
        return _BUILTIN_TASKS[task]
    except KeyError as exc:
        valid = ", ".join(sorted(_BUILTIN_TASKS))
        raise ValueError(
            f"Unknown task '{task}'. Use one of [{valid}] or provide --task_config."
        ) from exc


def _load_task_config_from_json(task_config_path: str) -> TaskConfig:
    config_path = Path(task_config_path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    task = payload.get("task") or config_path.stem
    label_dict = _normalize_label_dict(payload["label_dict"])
    ignore = tuple(payload.get("ignore", ()))
    n_classes = int(payload.get("n_classes", len(set(label_dict.values()))))

    return TaskConfig(
        task=task,
        dataset_csv=payload["dataset_csv"],
        n_classes=n_classes,
        label_dict=label_dict,
        label_col=payload.get("label_col", "label"),
        ignore=ignore,
        features_subdir=payload.get("features_subdir"),
        features_dir=payload.get("features_dir"),
        default_split_dir=payload.get("default_split_dir"),
        mil_patient_strat=bool(payload.get("mil_patient_strat", False)),
        split_patient_strat=bool(payload.get("split_patient_strat", True)),
        split_patient_voting=payload.get("split_patient_voting", "max"),
        subtyping=bool(payload.get("subtyping", False)),
        config_dir=config_path.parent,
    )


def _normalize_label_dict(label_dict: Dict[Any, Any]) -> Dict[Any, int]:
    normalized = {}
    for key, value in label_dict.items():
        normalized[_coerce_scalar(key)] = int(value)
    return normalized


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if _INT_PATTERN.match(stripped):
            return int(stripped)
        return stripped
    return value


def _resolve_user_path(path_value: str, config_dir: Optional[Path]) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)

    if path.exists():
        return str(path)

    if config_dir is not None and _is_config_relative(path_value):
        config_path = config_dir / path
        if config_path.exists():
            return str(config_path)

    splits_path = Path("splits") / path
    if splits_path.exists():
        return str(splits_path)

    return str(path)


def _resolve_path(path_value: str, config_dir: Optional[Path]) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)

    if path.exists():
        return str(path)

    if config_dir is not None and _is_config_relative(path_value):
        return str(config_dir / path)

    return str(path)


def _is_config_relative(path_value: str) -> bool:
    return path_value.startswith(("./", ".\\", "../", "..\\"))


_BUILTIN_TASKS = {
    "task_1_tumor_vs_normal": TaskConfig(
        task="task_1_tumor_vs_normal",
        dataset_csv="dataset_csv/tumor_vs_normal_dummy_clean.csv",
        n_classes=2,
        label_dict={"normal_tissue": 0, "tumor_tissue": 1},
        features_subdir="tumor_vs_normal_resnet_features",
        mil_patient_strat=False,
        split_patient_strat=True,
    ),
    "task_2_tumor_subtyping": TaskConfig(
        task="task_2_tumor_subtyping",
        dataset_csv="dataset_csv/tumor_subtyping_dummy_clean.csv",
        n_classes=3,
        label_dict={"subtype_1": 0, "subtype_2": 1, "subtype_3": 2},
        features_subdir="tumor_subtyping_resnet_features",
        mil_patient_strat=False,
        split_patient_strat=True,
        split_patient_voting="maj",
        subtyping=True,
    ),
    "task_tcga_lihc_early_recurrence": TaskConfig(
        task="task_tcga_lihc_early_recurrence",
        dataset_csv="data/tcga_lihc_er/dataset_csv/tcga_lihc_er.csv",
        n_classes=2,
        label_dict={0: 0, 1: 1},
        features_subdir="features_uni",
        default_split_dir="data/tcga_lihc_er/splits",
        mil_patient_strat=True,
        split_patient_strat=True,
    ),
}
