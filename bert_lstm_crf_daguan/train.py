# -*- coding: utf-8 -*-
# @Author: ding zeyuan
# @Date:   2019-7-5 18:24:32

from tqdm import tqdm
import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.optim as optim
from torch.utils.data import TensorDataset
from torch.utils.data import DataLoader

from utils import load_vocab, load_data, recover_label, get_ner_fmeasure, save_model, load_model
from constants import *
from model import BERT_LSTM_CRF


if torch.cuda.is_available():
    device = torch.device("cuda", 0)
    print('device',device)
    use_cuda = True
else:
    device = torch.device("cpu")
    use_cuda = False

vocab = load_vocab(vocab_file)
####读取训练集
print('max_length',max_length)

train_data = load_data(train_file, max_length=max_length, label_dic=l2i_dic, vocab=vocab)



train_ids = torch.LongTensor([temp.input_id for temp in train_data[1500:]])
train_masks = torch.LongTensor([temp.input_mask for temp in train_data[1500:]])
train_tags = torch.LongTensor([temp.label_id for temp in train_data[1500:]])
train_lenghts = torch.LongTensor([temp.lenght for temp in train_data[1500:]])


train_dataset = TensorDataset(train_ids, train_masks, train_tags,train_lenghts)
train_loader = DataLoader(train_dataset, shuffle=True, batch_size=batch_size)


#######读取测试集
dev_data = load_data(dev_file, max_length=max_length, label_dic=l2i_dic, vocab=vocab)

dev_ids = torch.LongTensor([temp.input_id for temp in dev_data[:1500]])
dev_masks = torch.LongTensor([temp.input_mask for temp in dev_data[:1500]])
dev_tags = torch.LongTensor([temp.label_id for temp in dev_data[:1500]])
dev_lenghts = torch.LongTensor([temp.lenght for temp in dev_data[:1500]])


dev_dataset = TensorDataset(dev_ids, dev_masks, dev_tags,dev_lenghts)
dev_loader = DataLoader(dev_dataset, shuffle=True, batch_size=batch_size)


# 读取test数据集

test_data = load_data(test_file, max_length=max_length, label_dic=l2i_dic, vocab=vocab)

test_ids = torch.LongTensor([temp.input_id for temp in test_data])
test_masks = torch.LongTensor([temp.input_mask for temp in test_data])
test_tags = torch.LongTensor([temp.label_id for temp in test_data])
test_lenghts = torch.LongTensor([temp.lenght for temp in test_data])


test_dataset = TensorDataset(test_ids, test_masks, test_tags,test_lenghts)
test_loader = DataLoader(test_dataset, shuffle=False, batch_size=batch_size)




######测试函数
def evaluate(medel, dev_loader):
    medel.eval()
    pred = []
    gold = []
    pred_test = []

    print('evaluate')
    with torch.no_grad():
        for i, dev_batch in enumerate(dev_loader):
            sentence, masks, tags , lengths = dev_batch
            sentence, masks, tags, lengths = Variable(sentence), Variable(masks), Variable(tags), Variable(lengths)
            if use_cuda:
                sentence = sentence.cuda()
                masks = masks.cuda()
                tags = tags.cuda()

            predict_tags = medel(sentence, masks)
            loss = model.neg_log_likelihood_loss(sentence, masks, tags)

            pred.extend([t for t in predict_tags.tolist()])
            gold.extend([t for t in tags.tolist()])

            # batch_tagids = medel.test(
            #     scores, lengths, l2i_dic)
            # pred_test = [t for t in batch_tagids.tolist()]

        pred_label,gold_label = recover_label(pred, gold, l2i_dic,i2l_dic)

        # pred_label_test,gold_label = recover_label(pred_test, gold, l2i_dic,i2l_dic)
        #
        # print('xin test fang fa', pred_label_test[0])

        print('dev loss {}'.format(loss.item()))
        pred_label_1 = [t[1:] for t in pred_label]
        gold_label_1 = [t[1:] for t in gold_label]
        print(pred_label_1[0], len(pred_label_1))
        print(gold_label_1[0])
        acc, p, r, f = get_ner_fmeasure(gold_label_1,pred_label_1)
        print('p: {}，r: {}, f: {}'.format(p, r, f))
        # model.train()
        return acc, p, r, f

# test 函数
def evaluate_test(medel,test_loader,dev_f):
    medel.eval()
    pred = []
    gold = []
    print('test')
    with torch.no_grad():
        for i, dev_batch in enumerate(test_loader):
            sentence, masks, tags, lengths = dev_batch
            sentence, masks, tags , lengths = Variable(sentence), Variable(masks), Variable(tags),Variable(lengths)
            if use_cuda:
                sentence = sentence.cuda()
                masks = masks.cuda()
                tags = tags.cuda()
            predict_tags = medel(sentence, masks)

            pred.extend([t for t in predict_tags.tolist()])
            gold.extend([t for t in tags.tolist()])

        pred_label,gold_label = recover_label(pred, gold, l2i_dic,i2l_dic)
        pred_label_2 = [t[1:] for t in pred_label]
        gold_label_2 = [t[1:] for t in gold_label]
        fw = open('data/predict_result'+str(dev_f)+'bert.txt','w')
        print(pred_label_2[0],len(pred_label))
        print(gold_label_2[0])
        for i in pred_label_2:
            for j in range(len(i)-1):
                fw.write(i[j])
                fw.write(' ')
            fw.write(i[len(i)-1])
            fw.write('\n')
        acc, p, r, f = get_ner_fmeasure(gold_label_2,pred_label_2)
        print('p: {}，r: {}, f: {}'.format(p, r, f))
        # model.train()
        return acc, p, r, f



########加载模型


model = BERT_LSTM_CRF('data/my_bert', tagset_size, 768, 200, 1,
                      dropout_ratio=0.5, dropout1=0.5, use_cuda = use_cuda)

if use_cuda:
    model.cuda()

optimizer = getattr(optim, 'Adam')
optimizer = optimizer(model.parameters(), lr=0.0001, weight_decay=0.00005)

best_f = -100

for epoch in range(epochs):
    print('epoch: {}，train'.format(epoch))
    for i, train_batch in enumerate(tqdm(train_loader)):
        sentence, masks, tags , lengths= train_batch

        sentence, masks, tags , lengths = Variable(sentence), Variable(masks), Variable(tags), Variable(lengths)

        if use_cuda:
            sentence = sentence.cuda()
            masks = masks.cuda()
            tags = tags.cuda()
        model.train()
        optimizer.zero_grad()
        loss = model.neg_log_likelihood_loss(sentence, masks, tags)
        loss.backward()
        optimizer.step()

    print('epoch: {}，train loss: {}'.format(epoch, loss.item()))
    acc, p, r, f = evaluate(model,dev_loader)


    if f > best_f:
        best_f = f
        _, _, _, _ = evaluate_test(model, test_loader,loss.item())
        model_name  = save_model_dir + '.' + str(float('%.3f' % best_f)) + ".pkl"
        torch.save(model.state_dict(), model_name)












