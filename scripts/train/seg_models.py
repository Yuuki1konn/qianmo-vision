import torch
import torch.nn as nn
from torchvision.models.segmentation import deeplabv3_resnet50


class DoubleConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class UNet(nn.Module):
    def __init__(self, in_channels: int = 3, out_channels: int = 1):
        super().__init__()
        features = [64, 128, 256, 512]

        self.downs = nn.ModuleList()
        self.ups = nn.ModuleList()
        self.pool = nn.MaxPool2d(2, 2)

        c = in_channels
        for f in features:
            self.downs.append(DoubleConv(c, f))
            c = f

        self.bottleneck = DoubleConv(features[-1], features[-1] * 2)

        rev = features[::-1]
        c = features[-1] * 2
        for f in rev:
            self.ups.append(nn.ConvTranspose2d(c, f, kernel_size=2, stride=2))
            self.ups.append(DoubleConv(c, f))
            c = f

        self.final = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def forward(self, x):
        skips = []
        for down in self.downs:
            x = down(x)
            skips.append(x)
            x = self.pool(x)

        x = self.bottleneck(x)
        skips = skips[::-1]

        for i in range(0, len(self.ups), 2):
            x = self.ups[i](x)
            skip = skips[i // 2]
            if x.shape != skip.shape:
                x = nn.functional.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=False)
            x = torch.cat([skip, x], dim=1)
            x = self.ups[i + 1](x)

        return self.final(x)


class DeepLabBinary(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = deeplabv3_resnet50(weights=None, weights_backbone=None)
        self.net.classifier[4] = nn.Conv2d(256, 1, kernel_size=1)

    def forward(self, x):
        return self.net(x)['out']


def create_model(name: str):
    name = name.lower()
    if name == 'unet':
        return UNet(in_channels=3, out_channels=1)
    if name == 'deeplabv3plus' or name == 'deeplab':
        return DeepLabBinary()
    raise ValueError(f'不支持的模型类型: {name}')
