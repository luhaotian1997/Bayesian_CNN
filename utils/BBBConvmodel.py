import torch.nn as nn
from .BBBdistributions import Normal
from .BBBlayers import BBBConv2d, BBBLinearFactorial, FlattenLayer


class BBBCNN(nn.Module):
    def __init__(self, num_tasks):
        # create AlexNet with probabilistic weights
        super(BBBCNN, self).__init__()

        # FEATURES
        self.conv1 = BBBConv2d(3, 64, kernel_size=11, stride=4, padding=2)
        self.conv1a = nn.Sequential(
            nn.ReLU(inplace=True),
            # nn.BatchNorm2d(64),
            nn.MaxPool2d(kernel_size=3, stride=2)
        )
        self.conv2 = BBBConv2d(64, 192, kernel_size=5, padding=2)
        self.conv2a = nn.Sequential(
            nn.ReLU(inplace=True),
            # nn.BatchNorm2d(192),
            nn.MaxPool2d(kernel_size=3, stride=2)
        )
        self.conv3 = BBBConv2d(192, 384, kernel_size=3, padding=1)
        self.conv3a = nn.Sequential(
            nn.ReLU(inplace=True),
            # nn.BatchNorm2d(384),
        )
        self.conv4 = BBBConv2d(384, 256, kernel_size=3, padding=1)
        self.conv4a = nn.Sequential(
            nn.ReLU(inplace=True),
            # nn.BatchNorm2d(256),
        )
        self.conv5 = BBBConv2d(256, 256, kernel_size=3, padding=1)
        self.conv5a = nn.Sequential(
            nn.ReLU(inplace=True),
            # nn.BatchNorm2d(256),
            nn.MaxPool2d(kernel_size=3, stride=2)
        )
        # CLASSIFIER
        self.flatten = FlattenLayer(256 * 6 * 6)
        self.drop1 = nn.Dropout()
        self.fc1 = BBBLinearFactorial(256 * 6 * 6, 4096)
        self.relu1 = nn.ReLU(inplace=True)
        self.drop2 = nn.Dropout()
        self.fc2 = BBBLinearFactorial(4096, 4096)
        self.relu2 = nn.ReLU(inplace=True)
        self.fc3 = BBBLinearFactorial(4096, num_tasks)

        layers = [self.conv1, self.conv1a, self.conv2, self.conv2a, self.conv3, self.conv3a, self.conv4, self.conv4a,
                  self.conv5, self.conv5a, self.flatten, self.drop1, self.fc1, self.relu1, self.drop2, self.fc2, self.relu2, self.fc3]

        self.layers = nn.ModuleList(layers)

    def probforward(self, x):
        kl = 0
        for layer in self.layers:
            if hasattr(layer, 'convprobforward') and callable(layer.convprobforward):
                x, _kl, = layer.convprobforward(x)
                kl += _kl

            elif hasattr(layer, 'fcprobforward') and callable(layer.fcprobforward):
                x, _kl, = layer.fcprobforward(x)
                kl += _kl
            else:
                x = layer(x)
        logits = x
        print('logits', logits)
        return logits, kl

    def load_prior(self, state_dict):
        d_q = {k: v for k, v in state_dict.items() if "q" in k}
        for i, layer in enumerate(self.layers):
            if type(layer) is BBBConv2d:
                layer.pw = Normal(mu=d_q["layers.{}.qw_mean".format(i)],
                                  logvar=d_q["layers.{}.qw_logvar".format(i)])
                # layer.pb = Normal(mu=d_q["layers.{}.qb_mean".format(i)], logvar=d_q["layers.{}.qb_logvar".format(i)])

            elif type(layer) is BBBLinearFactorial:
                layer.pw = Normal(mu=(d_q["layers.{}.qw_mean".format(i)]),
                                  logvar=(d_q["layers.{}.qw_logvar".format(i)]))

                layer.pb = Normal(mu=(d_q["layers.{}.qb_mean".format(i)]),
                                  logvar=(d_q["layers.{}.qb_logvar".format(i)]))
