import tensorflow as tf
#tf.compat.v1.enable_eager_execution()

import os

# take before TREX trajectories and put results into after TREX traj
from gym_mujoco_planar_snake.common.dataset import Dataset, SubTrajectory
from gym_mujoco_planar_snake.common.trainer import Trainer
from gym_mujoco_planar_snake.common.documentation import to_excel, Params
#from gym_mujoco_planar_snake.common.performance_checker import reward_prediction
import tensorflow.keras as keras
#######################################################################
from gym_mujoco_planar_snake.common.misc_util import *

def test_predictions(model, trajectories, k):

    from random import choices

    sample = choices(trajectories, k=k)

    for trajectory in sample:
        reward_prediction(model, trajectory)


def preprocess_pairs(trajectories):
    pairs, labels, rewards = Dataset.data_to_pairs(trajectories)
    return pairs, labels

def train(args):
    mode = args.mode
    hparams = Params(args.hparams_path)
    trainer = Trainer(hparams,
                      save_path=args.net_save_path,
                      Save=args.save_model,
                      use_tensorboard=True
                      )

    trajectories = get_all_files_from_dir(args.data_dir)
    hparams.dataset_size = len(trajectories)

    if mode == "pair":
        data = preprocess_pairs(trajectories)
        trainer.fit_pair(data)
    elif mode == "triplet":
        triplets = Dataset.data_triplets(trajectories)
        trainer.fit_triplet(triplets)
    else:
        assert False, "Mode not Defined"

    # document training results
    #results = trainer.results
    # to_excel(hparams, results)


def main():
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--seed', help='RNG seed', type=int, default=0)
    parser.add_argument('--env', help='environment ID', default='Mujoco-planar-snake-cars-angle-line-v1')
    parser.add_argument('--data_dir', help='subtrajectory dataset', default="gym_mujoco_planar_snake/log/SubTrajectoryDataset")
    parser.add_argument('--net_save_path', help='subtrajectory dataset',
                        default='gym_mujoco_planar_snake/log/PyTorch_Models/') # /home/andreas/LRZ_Sync+Share/BachelorThesis/gym_mujoco_planar_snake/
    parser.add_argument('--hparams_path', default="gym_mujoco_planar_snake/agents/hparams.json")
    parser.add_argument('--mode', type=str, default="pair")
    parser.add_argument('--save_model', type=bool, default="True")

    args = parser.parse_args()

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

    train(args=args)


if __name__ == "__main__":
    main()
