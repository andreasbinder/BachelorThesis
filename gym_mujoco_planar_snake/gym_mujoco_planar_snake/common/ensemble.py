#from gym_mujoco_planar_snake.common.documentation import *
from gym_mujoco_planar_snake.common.data_util import *
#from gym_mujoco_planar_snake.common.evaluate import *
import gym_mujoco_planar_snake.common.ranking_losses as custom_losses
import gym_mujoco_planar_snake.common.data_util as data

import os

import torch
import torch.nn as nn
import torch.optim as optim

from tqdm import tqdm


class Net(nn.Module):
    def __init__(self, input_dim):
        super().__init__()

        self.input_dim = input_dim

        '''self.model = nn.Sequential(
            nn.Linear(self.input_dim, 256),
            nn.Sigmoid(),
            nn.Linear(256, 256),
            nn.Sigmoid(),
            nn.Linear(256, 1)
        )'''

        self.model = nn.Sequential(
            nn.Linear(self.input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        )

        self.sigmoid = nn.Sigmoid()

    def cum_return(self, traj):
        # return of one traj
        sum_rewards = 0
        # sum_abs_rewards = 0
        r = self.model(traj)

        # TODO sigmoid
        #r = self.sigmoid(r)

        sum_rewards += torch.sum(r)
        # sum_abs_rewards += torch.sum(torch.abs(r))

        # TODO use sigmoid only when having BCELoss and not BCEwithLogitsLoss
        #sum_rewards = self.sigmoid(sum_rewards)


        return sum_rewards

    def forward(self, trajs):
        cum_rs = [self.cum_return(traj).unsqueeze(0) for traj in trajs]

        return torch.cat(tuple(cum_rs), 0).unsqueeze(0)

    '''def forward(self, traj_i, traj_j):
        cum_r_i = self.cum_return(traj_i)
        cum_r_j = self.cum_return(traj_j)

        return torch.cat((cum_r_i.unsqueeze(0), cum_r_j.unsqueeze(0)), 0).unsqueeze(0)'''


# TODO
# just replace what needs replacement
class Ensemble(object):

    def __init__(self, configs, net_save_path):
        self.num_nets = configs.get_num_nets()
        self.ranking_approach = configs.get_ranking_approach()
        self.net_save_path = net_save_path

        #
        # TODO save training results
        #self.hparams = Params(args.hparams_path)
        self.lr = configs.get_learning_rate()
        self.epochs = configs.get_epochs()
        self.split_ratio = configs.get_split_ratio()
        self.input_dim = configs.get_input_dim()


        # TODO for every mode
        self.loss_fn, self.preprocess_fn, self.forward_pass_fn = self.initialize_mode("triplet")


        self.train_summary_writer = None
        self.val_summary_writer = None
        self.initialize_tensorboard()

    def initialize_mode(self, mode):
        print("Mode %s" % mode)
        if mode == "pair":
            return (
                nn.BCEWithLogitsLoss(),
                lambda raw_data: data.build_custom_ranking_trainset(raw_data, ranking=2),
                lambda net, optimizer, inputs, label: self.forward_pass_pair_ranking(net, optimizer, inputs, label)
                    )
        if mode == "explicit":
            return (
                custom_losses.ExplicitRankingLoss(),
                lambda raw_data: data.build_custom_ranking_trainset(raw_data, ranking=self.ranking_approach),
                lambda net, optimizer, inputs, label: self.forward_pass_explicit_ranking(net, optimizer, inputs, label)
                    )
        if mode == "dcg":
            return (
                custom_losses.MultiLabelDCGLoss(),
                lambda raw_data: data.build_custom_ranking_trainset(raw_data, ranking=self.ranking_approach),
                lambda net, optimizer, inputs, label: self.forward_pass_dcg_ranking(net, optimizer, inputs, label)
                    )
        if mode == "triplet":
            return (
                nn.BCEWithLogitsLoss(),
                lambda raw_data: data.build_custom_triplet_trainset(raw_data, ranking=3),
                lambda net, optimizer, inputs, label: self.forward_pass_custom_triplet(net, optimizer, inputs, label)
                    )
        if mode == "triplet_sigmoid":
            return (
                nn.BCELoss(),
                lambda raw_data: data.build_custom_triplet_trainset(raw_data, ranking=3),
                lambda net, optimizer, inputs, label: self.forward_pass_custom_triplet_sigmoid(net, optimizer, inputs, label)
                    )

        if mode == "triplet_margin":
            return (
                nn.BCEWithLogitsLoss(),
                lambda raw_data: data.build_test_margin_triplet_trainset(raw_data, ranking=3),
                lambda net, optimizer, inputs, label: self.forward_pass_custom_triplet(net, optimizer, inputs, label)
                    )
        if mode == "triplet_better":
            return (
                nn.BCEWithLogitsLoss(),
                lambda raw_data: data.build_test_better_triplet_trainset(raw_data, ranking=3),
                lambda net, optimizer, inputs, label: self.forward_pass_custom_triplet(net, optimizer, inputs, label)
            )





    def preprocess_data(self, raw_data):
        # choose
        data = self.preprocess_fn(raw_data)

        #data = split_dataset_for_nets(data, self.num_nets)

        return data

    def fit(self, raw_data):

        whole_dataset = self.preprocess_data(raw_data)

        '''print(whole_dataset[0].shape)
        print(len(whole_dataset))

        import sys
        sys.exit()'''

        nets = [Net(self.input_dim)] * self.num_nets


        #nets = [Net(self.input_dim), Net(self.input_dim), Net(self.input_dim), Net(self.input_dim),Net(self.input_dim)]
        #final_dataset = [raw_data[i:i + self.num_nets] for i, _ in enumerate(raw_data[::self.num_nets])]

        #self.train(0, nets[0], whole_dataset[0])
        import numpy as np

        for index, net in enumerate(nets):
            self.initialize_tensorboard()
            self.train(index, net, whole_dataset)

            #np.random.shuffle(whole_dataset)
            whole_dataset = self.preprocess_data(raw_data)

        '''for index, net in enumerate(nets):
            self.train(index, net, whole_dataset[:,index,:])'''

        '''for index, (net, dataset) in enumerate(zip(nets, whole_dataset)):
            self.train(index, net, dataset)'''

    def train(self, index, net, dataset):

        train_set, val_set = data.split_into_train_val(dataset, self.split_ratio)


        optimizer = optim.Adam(net.parameters(), lr=self.lr)

        # training
        print("Start Learning")
        for epoch in range(self.epochs):

            running_loss = 0.0

            print("Training")
            for item in tqdm(train_set):
                inputs, label = item

                loss = self.forward_pass_fn(net, optimizer, inputs, label)

                loss.backward()
                optimizer.step()

                # print statistics
                running_loss += loss.item()

            print("Validating")
            running_val_loss = 0.0
            for item in tqdm(val_set):
                inputs, label = item

                loss = self.forward_pass_fn(net, optimizer, inputs, label)

                # print statistics
                running_val_loss += loss.item()

            template = 'Epoch {}, Loss: {:10.4f}, Validation Loss: {:10.4f}'
            stats = template.format(
                epoch + 1,
                running_loss / len(train_set),
                running_val_loss / len(val_set)
            )
            print(stats)

            self.train_summary_writer.add_scalar('train_loss', running_loss / len(train_set), epoch)
            self.val_summary_writer.add_scalar('val_loss', running_val_loss / len(val_set), epoch)

        self.save(index=index, net=net)

    def forward_pass_explicit_ranking(self, net, optimizer, inputs, label):

        trajs = [torch.from_numpy(inp).float() for inp in inputs]

        y = torch.tensor(label).unsqueeze(0)

        optimizer.zero_grad()

        rewards = net(trajs)

        loss = self.loss_fn(rewards, y)

        return loss

    def forward_pass_pair_ranking(self, net, optimizer, inputs, label):

        trajs = [torch.from_numpy(inp).float() for inp in inputs]

        y = torch.tensor(label).unsqueeze(0).float()

        optimizer.zero_grad()

        rewards = net(trajs)

        loss = self.loss_fn(rewards, y)

        return loss

    def forward_pass_dcg_ranking(self, net, optimizer, inputs, label):

        trajs = [torch.from_numpy(inp).float() for inp in inputs]

        y = torch.tensor(label).unsqueeze(0)

        optimizer.zero_grad()

        rewards = net(trajs)

        loss = self.loss_fn(rewards, y)

        return loss

    def forward_pass_custom_triplet(self, net, optimizer, inputs, label):

        trajs = [torch.from_numpy(inp).float() for inp in inputs]

        y = torch.tensor(label).unsqueeze(0)

        optimizer.zero_grad()

        rewards = net(trajs)

        loss = self.loss_fn(rewards, y)

        return loss

    def forward_pass_custom_triplet_sigmoid(self, net, optimizer, inputs, label):

        trajs = [torch.from_numpy(inp).float() for inp in inputs]

        y = torch.tensor(label).unsqueeze(0).float()

        optimizer.zero_grad()

        rewards = net(trajs)

        loss = self.loss_fn(rewards, y)

        return loss

    def save(self, index, net):

        torch.save(net.state_dict(), os.path.join(self.net_save_path, "model_" + str(index)))

    @staticmethod
    def load(log_dir, num_nets, input_dim=27):

        nets = []
        for index in range(num_nets):
            path = os.path.join(log_dir, "model_" + str(index))
            net = Net(input_dim)
            net.load_state_dict(torch.load(path))
            nets.append(net)

        return nets

    def initialize_tensorboard(self):


        from tensorboardX import SummaryWriter
        import datetime

        from time import ctime

        # log_dir = 'gym_mujoco_planar_snake/log/tensorboard/PyTorch/'
        log_dir = "/tmp/tensorboard/"

        current_time = ctime()
        train_log_dir = log_dir + current_time + '/train'
        val_log_dir = log_dir + current_time + '/val'


        self.train_summary_writer = SummaryWriter(train_log_dir)
        self.val_summary_writer = SummaryWriter(val_log_dir)

