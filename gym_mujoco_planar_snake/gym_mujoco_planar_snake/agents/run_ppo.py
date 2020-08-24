#!/usr/bin/env python
import tensorflow as tf
import torch
import numpy as np

# TODO eager exec
# tf.enable_eager_execution()

from baselines.common import set_global_seeds, tf_util as U
from baselines import bench
from baselines.ppo1 import mlp_policy
from baselines.ppo1.pposgd_simple import learn
from baselines.bench.monitor import Monitor
from baselines import logger

import gym, logging

import argparse
import os
import os.path as osp
from time import ctime

from gym_mujoco_planar_snake.common.model_saver_wrapper import ModelSaverWrapper
from gym_mujoco_planar_snake.common.custom_action_wrapper import ClipActionWrapper
from gym_mujoco_planar_snake.common.custom_observation_wrapper import GenTrajWrapper
from gym_mujoco_planar_snake.common.reward_wrapper import *
from gym_mujoco_planar_snake.common.reward_nets import *




class PPOAgent(object):

    def __init__(self, env):

        self.env = env

        self.policy_func = lambda name, ob_space, ac_space: mlp_policy.MlpPolicy(name=name, ob_space=ob_space,
                                                                                 ac_space=ac_space,
                                                                                 hid_size=64, num_hid_layers=2
                                                                                 )
        self.policy = None

    def learn(self, num_timesteps):
        self.policy = learn(self.env, self.policy_func,
                            max_timesteps=num_timesteps,
                            timesteps_per_actorbatch=2048,
                            clip_param=0.2,
                            entcoeff=0.0,
                            optim_epochs=10, optim_stepsize=3e-4, optim_batchsize=64,
                            gamma=0.99, lam=0.95,
                            schedule='linear',
                            )
        return self.policy

    def act(self, obs, stochastic=False):
        return self.policy.act(stochastic, obs)



def set_configs(args):

    gym.logger.setLevel(logging.WARN)
    #logger.configure(dir=args.log_dir + "/" + ctime())
    set_global_seeds(args.seed)
    torch.manual_seed(args.seed)
    model_dir = None

    if args.save:
        logger.configure(dir=args.log_dir + "/" + args.name_dir)
        name = 'ppo'
        model_dir = osp.join(logger.get_dir(), 'models')
        os.mkdir(model_dir)
        model_dir = ModelSaverWrapper.gen_model_dir_path(model_dir, args.env, name)
        logger.log("model_dir: %s" % model_dir)
    return model_dir

def net_by_path():
    paths = [
        "/home/andreas/LRZ_Sync+Share/BachelorThesis/gym_mujoco_planar_snake/gym_mujoco_planar_snake/results/improved_runs/crossentropy/ensemble_v1/model1/model",
        "/home/andreas/LRZ_Sync+Share/BachelorThesis/gym_mujoco_planar_snake/gym_mujoco_planar_snake/results/improved_runs/crossentropy/ensemble_v1/model2/model",
        "/home/andreas/LRZ_Sync+Share/BachelorThesis/gym_mujoco_planar_snake/gym_mujoco_planar_snake/results/improved_runs/crossentropy/ensemble_v1/model3/model",
        "/home/andreas/LRZ_Sync+Share/BachelorThesis/gym_mujoco_planar_snake/gym_mujoco_planar_snake/results/improved_runs/crossentropy/ensemble_v1/model4/model",
        "/home/andreas/LRZ_Sync+Share/BachelorThesis/gym_mujoco_planar_snake/gym_mujoco_planar_snake/results/improved_runs/crossentropy/ensemble_v1/model5/model"
    ]
    nets = []
    for path in paths:
        net = SingleStepPairNet()
        net.load_state_dict(torch.load(path))
        nets.append(net)

    return nets

def get_nets(args):
    nets = []
    for index in range(args.num_nets):
        path = os.path.join(args.log_dir, "model_" + str(index))
        net = SingleStepPairNet()
        net.load_state_dict(torch.load(path))
        nets.append(net)

    return nets


def prepare_env(args, model_dir):

    env = gym.make(args.env)

    env.seed(args.seed)

    joints = np.array(args.fixed_joints)

    wrap_action = False if args.fixed_joints is None else True

    if wrap_action:
        assert joints[joints >= 0].size == 0 and joints[joints <= 7].size == 0, "Joint Index does not exist"
        env = ClipActionWrapper(env, args.clip_value, joints)

    # either you run agent with learnt reward
    if args.custom_reward:

        '''net = SingleStepPairNet()
        net.load_state_dict(torch.load(args.reward_net_dir))'''
        # env = HorizonRewardWrapper_v3(env, self.reward_net_dir, model)
        # venv, nets, max_timesteps, log_dir
        nets = get_nets(args)
        env = MyRewardWrapper(env, nets, args.num_timesteps, args.log_dir, args.name_dir, args.crtl_coeff)
        #env = SingleStepRewardWrapper(env, net, args.num_timesteps, args.log_dir)
        #env = SingleStepNormalizedRewardWrapper(env, net, args.num_timesteps)
        #env = EnsembleNormalizedRewardWrapper(env, net, args.num_timesteps)
    # or you generate trajectories
    else:
        trajectory_length = 50 if args.env == "Mujoco-planar-snake-cars-angle-line-v1" else 20
        num_traj_per_epoch = 10 if args.env == "Mujoco-planar-snake-cars-angle-line-v1" else 1
        env = GenTrajWrapper(env, args.log_dir + "/" + args.name_dir,
                             args.num_timesteps,
                             trajectory_length,
                             num_traj_per_epoch)


    if args.save:
        log_dir = osp.join(logger.get_dir(), 'log_ppo')
        logger.log("log_dir: %s" % log_dir)
        env = bench.Monitor(env, log_dir)
        env = ModelSaverWrapper(env, model_dir, args.sfs)

    if args.monitor:
        env = Monitor(env, None)

    return env



def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--seed', help='RNG seed', type=int, default=0)
    parser.add_argument('--num-timesteps', type=int, default=int(1e6))  # 1e6
    parser.add_argument('--sfs', help='save_frequency_steps', type=int, default=10000)  # for mujoco
    parser.add_argument('--env', help='environment ID', default='Mujoco-planar-snake-cars-angle-line-v1')
    parser.add_argument('--log_dir', help='log directory', default='gym_mujoco_planar_snake/results/initial_runs/')
    parser.add_argument('--injured', type=bool, default=False)
    parser.add_argument('--clip_value', type=float, default=1.5)
    parser.add_argument('--fixed_joints', nargs='*', type=int, default=None)
    parser.add_argument('--custom_reward', type=bool, default=False)
    parser.add_argument('--reward_net_dir', default='gym_mujoco_planar_snake/log/PyTorch_Models/Thu Aug  6 20:30:12 2020/model')
    parser.add_argument('--name_dir', type=str, default=ctime()[4:19]) # [4:19]
    parser.add_argument('--save', default=True)
    parser.add_argument('--mode', default='pair')
    parser.add_argument('--monitor', default=True)
    parser.add_argument('--crtl_coeff', type=float, default=0.1)
    parser.add_argument('--num_nets', type=int, default=5)

    args = parser.parse_args()


    U.make_session(num_cpu=1, make_default=True)  # interactive

    model_dir = set_configs(args)

    env = prepare_env(args=args,
                      model_dir=model_dir)



    agent = PPOAgent(env=env)

    agent.learn(args.num_timesteps)

    with open(os.path.join(args.log_dir, args.name_dir, "rewards.npy"), 'wb') as f:
        np.save(f, env.get_episode_rewards())



if __name__ == '__main__':
    main()
