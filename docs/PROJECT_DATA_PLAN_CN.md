# CLAM 数据集开工方案

## 1. 结论先行

当前最稳妥的推进顺序是：

1. 用 `CAMELYON16` 跑通 CLAM + UNI 全流程，作为 warm-up 和 pipeline 验证。
2. 保留 `TCGA-LIHC`，把它作为单队列 pilot，用来验证特征缓存、MIL 训练和评估是否稳定。
3. 尽快补下载 `CAMELYON17`，把它作为方向 1 的主实验数据集。
4. 如果后续要做更自然的外部验证，再补 `TCGA-BRCA + CPTAC-BRCA`，其次是 `TCGA-LUAD + CPTAC-LUAD`。

一句话版本：

`CAMELYON16 + TCGA-LIHC` 负责让平台跑起来，`CAMELYON17` 负责主结果，`TCGA/CPTAC` 负责后续增强外部验证故事。

## 2. 最小下载清单

现在立刻需要：

- `CAMELYON17`

已经值得保留：

- `CAMELYON16`
- `TCGA-LIHC`

磁盘和时间允许时再补：

- `TCGA-BRCA`
- `CPTAC-BRCA`

## 3. 推荐目录规划

建议把大文件和仓库元数据分开。

仓库内保留轻量元数据：

```text
CLAM/
  data/
    tcga_lihc_er/
      metadata/
      dataset_csv/
      splits/
  dataset_configs/
  dataset_csv/
  splits/
```

说明：

- `dataset_csv/` 和 `splits/` 根目录继续保留 CLAM 自带 toy 示例。
- 真实项目数据建议放到 `data/<task_name>/...` 下，避免仓库根目录越来越乱。

仓库外或单独磁盘保留大文件：

```text
WSI_ROOT/
  camelyon16/
    slides/
  camelyon17/
    slides/
  tcga_lihc/
    slides/

COORD_ROOT/
  camelyon16/
    patches/
    masks/
    stitches/
  camelyon17/
    patches/
    masks/
    stitches/
  tcga_lihc_er/
    patches/
    masks/
    stitches/

FEATURE_ROOT/
  camelyon16_uni/
    pt_files/
    h5_files/
  camelyon17_uni/
    pt_files/
    h5_files/
  tcga_lihc_er/
    features_uni/
      pt_files/
      h5_files/
```

和当前仓库脚本最兼容的习惯是：

- `--data_slide_dir` 指向 `WSI_ROOT/<dataset>/slides`
- `--data_h5_dir` 指向 `COORD_ROOT/<dataset>`
- `--data_root_dir` 指向 `FEATURE_ROOT/<dataset_root>`
- `task_config` 里的 `features_subdir` 再补上特征子目录，例如 `features_uni`

对你当前的 `TCGA-LIHC`，建议直接用：

- `data_root_dir = <FEATURE_ROOT>/tcga_lihc_er`
- `features_subdir = features_uni`

## 4. 这次已经补好的能力

仓库现在支持用 `task_config` 驱动自定义任务，不需要每加一个数据集都改 `main.py` / `eval.py`。

已经改好的入口：

- `main.py`
- `eval.py`
- `create_splits_seq.py`

现成配置：

- `dataset_configs/tcga_lihc_er_uni.json`

你后面新增 `CAMELYON17` 时，最简单的做法就是复制这个 JSON，再改：

- `task`
- `dataset_csv`
- `features_subdir` 或 `features_dir`
- `default_split_dir`
- `label_dict`
- `n_classes`

## 5. task_config 最小模板

```json
{
  "task": "task_camelyon17_center_split",
  "dataset_csv": "data/camelyon17/dataset_csv/camelyon17.csv",
  "features_subdir": "features_uni",
  "default_split_dir": "data/camelyon17/splits",
  "label_dict": {
    "0": 0,
    "1": 1
  },
  "label_col": "label",
  "n_classes": 2,
  "mil_patient_strat": true,
  "split_patient_strat": true,
  "split_patient_voting": "max",
  "ignore": []
}
```

字段含义：

- `dataset_csv`: 至少包含 `case_id`, `slide_id`, `label`
- `features_subdir`: 相对于 `--data_root_dir` 的特征目录
- `default_split_dir`: 放 `splits_0.csv` 这类切分文件的目录
- `mil_patient_strat`: 训练入口加载元数据时是否按 patient/case 统计
- `split_patient_strat`: 自动切分时是否按 patient/case 切

## 6. 命令模板

### 6.1 TCGA-LIHC pilot

先根据已有 metadata 生成 CLAM 需要的 CSV：

```powershell
python data\tcga_lihc_er\generate_csv.py
```

如果还没有坐标和特征：

```powershell
python create_patches_fp.py --source <WSI_ROOT>\\tcga_lihc\\slides --save_dir <COORD_ROOT>\\tcga_lihc_er --preset tcga.csv --patch_size 256 --seg --patch --stitch
```

```powershell
python extract_features_fp.py --data_h5_dir <COORD_ROOT>\\tcga_lihc_er --data_slide_dir <WSI_ROOT>\\tcga_lihc\\slides --csv_path data\\tcga_lihc_er\\dataset_csv\\tcga_lihc_er_process_list.csv --feat_dir <FEATURE_ROOT>\\tcga_lihc_er\\features_uni --model_name uni_v1 --batch_size 64 --slide_ext .svs
```

训练：

```powershell
python main.py --task_config dataset_configs\\tcga_lihc_er_uni.json --data_root_dir <FEATURE_ROOT>\\tcga_lihc_er --results_dir results --exp_code tcga_lihc_uni_clam --model_type clam_sb --bag_loss ce --seed 1
```

评估：

```powershell
python eval.py --task_config dataset_configs\\tcga_lihc_er_uni.json --data_root_dir <FEATURE_ROOT>\\tcga_lihc_er --results_dir results --models_exp_code tcga_lihc_uni_clam_s1 --save_exp_code tcga_lihc_uni_clam_eval --split test
```

### 6.2 CAMELYON16 warm-up

建议把它组织成：

```text
data/camelyon16/
  dataset_csv/
  splits/
  metadata/
```

然后复制一份 `dataset_configs/tcga_lihc_er_uni.json`，改成 `camelyon16` 版本。

### 6.3 CAMELYON17 主实验

建议从一开始就按中心信息准备好 `dataset_csv` 和 `splits`，确保主结果是中心间泛化而不是随机切分。

最推荐的做法是：

- `dataset_csv` 里保留中心字段，哪怕当前训练脚本只用到 `case_id`, `slide_id`, `label`
- `default_split_dir` 直接对应你定义好的中心间切分
- 主实验先固定 protocol，再跑 encoder 和 MIL 变体

## 7. 立刻可以执行的下一步

最省事的执行顺序如下：

1. 先把 `TCGA-LIHC` 的坐标和 UNI 特征补齐，确认 pilot 能稳定训练和评估。
2. 并行补下载 `CAMELYON17`。
3. 为 `CAMELYON17` 新建 `data/camelyon17/metadata`、`dataset_csv`、`splits` 和对应 `task_config`。
4. 等 LIHC pilot 跑通后，把主实验算力切到 `CAMELYON17`。
