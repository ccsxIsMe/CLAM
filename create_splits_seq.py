import os
from dataset_modules.dataset_generic import Generic_WSI_Classification_Dataset, save_splits
from dataset_modules.task_config import load_task_config
import argparse
import numpy as np

parser = argparse.ArgumentParser(description='Creating splits for whole slide classification')
parser.add_argument('--label_frac', type=float, default= 1.0,
                    help='fraction of labels (default: 1)')
parser.add_argument('--seed', type=int, default=1,
                    help='random seed (default: 1)')
parser.add_argument('--k', type=int, default=10,
                    help='number of splits (default: 10)')
parser.add_argument('--task', type=str, default=None,
                    help='built-in task name')
parser.add_argument('--task_config', type=str, default=None,
                    help='optional JSON task config for custom datasets')
parser.add_argument('--val_frac', type=float, default= 0.1,
                    help='fraction of labels for validation (default: 0.1)')
parser.add_argument('--test_frac', type=float, default= 0.1,
                    help='fraction of labels for test (default: 0.1)')
parser.add_argument('--output_dir', type=str, default=None,
                    help='optional directory to write generated split CSVs')

args = parser.parse_args()
try:
    task_config = load_task_config(args.task, args.task_config)
except ValueError as exc:
    parser.error(str(exc))
args.task = task_config.task
args.n_classes = task_config.n_classes

dataset = Generic_WSI_Classification_Dataset(
                        csv_path=task_config.resolve_dataset_csv(),
                        shuffle=False,
                        seed=args.seed,
                        print_info=True,
                        label_dict=task_config.label_dict,
                        label_col=task_config.label_col,
                        patient_strat=task_config.split_patient_strat,
                        patient_voting=task_config.split_patient_voting,
                        ignore=list(task_config.ignore))

num_slides_cls = np.array([len(cls_ids) for cls_ids in dataset.patient_cls_ids])
val_num = np.round(num_slides_cls * args.val_frac).astype(int)
test_num = np.round(num_slides_cls * args.test_frac).astype(int)

if __name__ == '__main__':
    if args.label_frac > 0:
        label_fracs = [args.label_frac]
    else:
        label_fracs = [0.1, 0.25, 0.5, 0.75, 1.0]
    
    for lf in label_fracs:
        split_dir = args.output_dir or task_config.resolve_split_dir(None, lf)
        os.makedirs(split_dir, exist_ok=True)
        dataset.create_splits(k = args.k, val_num = val_num, test_num = test_num, label_frac=lf)
        for i in range(args.k):
            dataset.set_splits()
            descriptor_df = dataset.test_split_gen(return_descriptor=True)
            splits = dataset.return_splits(from_id=True)
            save_splits(splits, ['train', 'val', 'test'], os.path.join(split_dir, 'splits_{}.csv'.format(i)))
            save_splits(splits, ['train', 'val', 'test'], os.path.join(split_dir, 'splits_{}_bool.csv'.format(i)), boolean_style=True)
            descriptor_df.to_csv(os.path.join(split_dir, 'splits_{}_descriptor.csv'.format(i)))



