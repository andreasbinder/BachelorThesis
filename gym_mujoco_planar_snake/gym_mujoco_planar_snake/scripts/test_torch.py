import torch
import torch.nn as nn

#from gym_mujoco_planar_snake.common.trainer import Net

class Net(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(4, 16, 7, stride=3)
        self.conv2 = nn.Conv2d(16, 16, 5, stride=2)
        self.conv3 = nn.Conv2d(16, 16, 3, stride=1)
        self.conv4 = nn.Conv2d(16, 16, 3, stride=1)
        self.fc1 = nn.Linear(784, 64)
        self.fc2 = nn.Linear(64, 1)

model = nn.Linear(20, 5) # predict logits for 5 classes
x = torch.randn(1, 20)
y = torch.tensor([[1., 0., 1., 0., 0.]]) # get classA and classC as active
print(x)
print(y)

criterion = nn.BCEWithLogitsLoss()
optimizer = torch.optim.SGD(model.parameters(), lr=1e-1)

for epoch in range(20):
    optimizer.zero_grad()
    output = model(x)
    loss = criterion(output, y)
    loss.backward()
    optimizer.step()
    print('Loss: {:.3f}'.format(loss.item()))

torch.manual_seed(0)

loss = nn.CrossEntropyLoss()
input = torch.randn(3, 5, requires_grad=True)
target = torch.empty(3, dtype=torch.long).random_(5)
output = loss(input, target)
print(input)
print(target)
print(output)


'''from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter()'''

'''linear = nn.Linear(27, 1)

anchor = torch.randn(100, 27, requires_grad=True)

print(anchor.shape)
out = linear(anchor)
print(out.shape)

net = nn.Sequential(
    nn.Linear(27, 1)
)

out = net(anchor)
print(out.shape)'''


'''m = nn.Sigmoid()
loss = nn.BCELoss()
input = torch.randn(3, requires_grad=True)
target = torch.empty(3).random_(2)
print(input)
print(m(input))
print(target)
output = loss(m(input), target)
print(output)
output.backward()'''
'''triplet_loss = nn.TripletMarginLoss(margin=1.0, p=2)
anchor = torch.randn(100, 128, requires_grad=True)
print(anchor.shape)
positive = torch.randn(100, 128, requires_grad=True)
print(positive.shape)
negative = torch.randn(100, 128, requires_grad=True)
print(negative.shape)
output = triplet_loss(anchor, positive, negative)
print(output)
output.backward()'''