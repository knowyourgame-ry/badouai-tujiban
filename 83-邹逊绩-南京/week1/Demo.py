# coding:utf8

import torch
import torch.nn as nn
import numpy as np
import random
import json
import matplotlib.pyplot as plt
import os

"""

基于pytorch的网络编写
实现一个网络完成一个简单nlp任务
判断文本中是否有某些特定字符出现

"""
char_dim = 4  # 每个字的维度
sentence_length = 6  # 样本文本长度
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model_path = "model.pth"
epoch_num = 100  # 训练轮数
batch_size = 1000  # 每次训练样本个数
train_sample = 10000  # 每轮训练总共训练的样本总数

class TorchModel(nn.Module):
    def __init__(self, input_dim, sentence_length, vocab):
        super(TorchModel, self).__init__()
        self.embedding = nn.Embedding(len(vocab) + 1, input_dim)
        self.layer = nn.Linear(input_dim, input_dim)
        self.pool = nn.AvgPool1d(sentence_length)
        self.classify = nn.Linear(input_dim, 1)
        self.activation = torch.sigmoid  # sigmoid做激活函数
        self.dropout = nn.Dropout(0.1)
        self.loss = nn.functional.mse_loss  # loss采用均方差损失

    # 当输入真实标签，返回loss值；无真实标签，返回预测值
    def forward(self, x, y=None):
        x = x.to(device)
        x = self.embedding(x)  # input shape:(batch_size, sen_len)
        x = self.layer(x)  # input shape:(batch_size, sen_len, input_dim)
        x = self.dropout(x)  # input shape:(batch_size, sen_len, input_dim)
        x = self.activation(x)  # input shape:(batch_size, sen_len, input_dim)
        # print(x.shape)
        # print(x)
        x = x.transpose(1, 2)
        # print(x.shape)
        # print(x)
        x = self.pool(x).squeeze()  # input shape:(batch_size, sen_len, input_dim)
        # print(x.shape)

        x = self.classify(x)  # input shape:(batch_size, input_dim)
        y_pred = self.activation(x)  # input shape:(batch_size, 1)
        y_pred = y_pred.to(device)
        if y is not None:
            y = y.to(device)
            return self.loss(y_pred, y)
        else:
            return y_pred


# 字符集随便挑了一些汉字，实际上还可以扩充
# 为每个字生成一个标号
# {"a":1, "b":2, "c":3...}
# abc -> [1,2,3]
def build_vocab():
    # chars = "abcdefghijklmnopqrstuvwxyz"  # 字符集
    chars = "一二三四五六姑苏"
    vocab = {}
    for index, char in enumerate(chars):
        vocab[char] = index + 1  # 每个字对应一个序号
    vocab['空'] = len(vocab) + 1
    return vocab


# 随机生成一个样本
# 从所有字中选取sentence_length个字
# 反之为负样本
def build_sample(vocab, sentence_length, i):
    # 随机从字表选取sentence_length个字，可能重复
    while True:
        x = [random.choice(list(vocab.keys())) for _ in range(sentence_length)]
        # 指定哪些字出现时为正样本
        # if set("姑苏") & set(x):
        #     y = 1
        # else:
        #     y = 0
        # break;
        str = ''.join(x)
        if i % 2 == 1:
            if str.find('姑苏') >= 0:
                y = 1
                break
        if i % 2 == 0:
            if str.find('姑苏') < 0:
                y = 0
                # if i % 22 == 0:
                #     x[0] = '苏'
                # if i % 38 == 0:
                #     x[-1] = '姑'
                break

    x = [vocab.get(word, vocab['空']) for word in x]  # 将字转换成序号，为了做embedding
    return x, y


# 建立数据集
# 输入需要的样本数量。需要多少生成多少
def build_dataset(sample_length, vocab, sentence_length):
    dataset_x = []
    dataset_y = []
    for i in range(sample_length):
        x, y = build_sample(vocab, sentence_length, i)
        dataset_x.append(x)
        dataset_y.append([y])
    return torch.LongTensor(dataset_x), torch.FloatTensor(dataset_y)


# 建立模型
def build_model(vocab, char_dim, sentence_length):
    model = TorchModel(char_dim, sentence_length, vocab)
    model.to(device)

    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path))  # 加载训练好的权重
    return model


# 测试代码
# 用来测试每轮模型的准确率
def evaluate(model, vocab, sample_length):
    model.eval()
    x, y = build_dataset(200, vocab, sample_length)  # 建立200个用于测试的样本
    print("本次预测集中共有%d个正样本，%d个负样本" % (sum(y), 200 - sum(y)))
    correct, wrong = 0, 0
    with torch.no_grad():
        y_pred = model(x)  # 模型预测
        for y_p, y_t in zip(y_pred, y):  # 与真实标签进行对比
            if float(y_p) < 0.5 and int(y_t) == 0:
                correct += 1  # 负样本判断正确
            elif float(y_p) >= 0.5 and int(y_t) == 1:
                correct += 1  # 正样本判断正确
            else:
                wrong += 1
    print("正确预测个数：%d, 正确率：%f" % (correct, correct / (correct + wrong)))
    return correct / (correct + wrong)


def main():
    vocab = build_vocab()  # 建立字表
    model = build_model(vocab, char_dim, sentence_length)  # 建立模型
    optim = torch.optim.Adam(model.parameters(), lr=0.005)  # 建立优化器
    log = []
    for epoch in range(epoch_num):
        model.train()
        watch_loss = []
        for batch in range(int(train_sample / batch_size)):
            x, y = build_dataset(batch_size, vocab, sentence_length)  # 构建一组训练样本
            optim.zero_grad()  # 梯度归零
            loss = model(x, y)  # 计算loss
            loss.backward()  # 计算梯度
            optim.step()  # 更新权重
            watch_loss.append(loss.item())
        print("=========\n第%d轮平均loss:%f" % (epoch + 1, np.mean(watch_loss)))
        acc = evaluate(model, vocab, sentence_length)  # 测试本轮模型结果
        log.append([acc, np.mean(watch_loss)])
    # plt.figure()
    plt.plot(range(len(log)), [l[0] for l in log])  # 画acc曲线
    plt.plot(range(len(log)), [l[1] for l in log])  # 画loss曲线
    plt.show()
    # 保存模型
    torch.save(model.state_dict(), model_path)
    # 保存词表
    writer = open("vocab.json", "w", encoding="utf8")
    writer.write(json.dumps(vocab, ensure_ascii=False, indent=2))
    writer.close()
    return


# 最终预测
def predict(vocab_path, input_strings):
    vocab = json.load(open(vocab_path, "r", encoding="utf8"))
    model = build_model(vocab, char_dim, sentence_length)  # 建立模型
    x = []
    tmps = []
    for input_string in input_strings:
        need = sentence_length - len(input_string)
        a = [random.choice(list(vocab.keys())) for _ in range(need)]
        tmp = input_string + ''.join(a)
        tmps.append(tmp)
        x.append([vocab[char] for char in tmp])  # 将输入序列化
    # for input_string in input_strings:
    #     for char in input_string:
    #         ii = vocab[char]
    #         x.append(ii)  # 将输入序列化
    model.eval()  # 测试模式，不使用dropout
    with torch.no_grad():  # 不计算梯度
        result = model.forward(torch.LongTensor(x))  # 模型预测

    for i, input_string in enumerate(input_strings):
        print(round(float(result[i])), tmps[i], result[i])  # 打印结果


if __name__ == "__main__":
    main()
    # test_strings = ["一姑二三姑四", "五姑六苏", "苏一二三五苏", "二四姑苏三五", "一二"]
    # predict("vocab.json", test_strings)


    # test_strings = ["东败唯我方", "日出到方姑山苏客船", "苏城唯我姑苏不败外寒", "东寺夜半苏姑钟声"]
