import os
import argparse
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam
import json
from torch.utils.data import DataLoader
import time

from config import EEG_LEN, TEXT_LEN, d_model, d_inner, \
    num_layers, num_heads, d_k, d_v, class_num, dropout
from optim_new import ScheduledOptim
from trainer import train
from model_new import FusionTransformer, EEGTransformer, TextTransformer, Transformer
from utils import open_file
from dataset_new import prepare_sr_eeg_data, EEGDataset, clean_dic, shuffle_split_data
torch.set_num_threads(2)

def get_args():
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument('--model', type=str, help="Please choose a model from the following list: ['transformer', 'biLSTM', 'MLP', 'resnet', 'fusion', 'CCA_fusion', 'CCA_ds', 'WD_fusion', 'WD_ds']")
    parser.add_argument('--modality', type = str, default = None, help="Please choose a modality from the following list: ['eeg', 'text', fusion]")
    parser.add_argument('--dataset', type=str, help="Please choose a dataset from the following list: ['KEmoCon', 'ZuCo']")
    parser.add_argument('--task', default ='SA', type=str, help="If dataset == Zuco, please choose a task from the following list: ['SA', 'RD']")
    parser.add_argument('--level', type=str, default = 'sentence', help="If ZuCo, please choose the level of EEG feature you want to work with from this list: ['word', 'concatword', 'sentence']")
    parser.add_argument('--batch_size', type=int, default = 16)
    parser.add_argument('--text_feature_len', type = int, default = 768)
    parser.add_argument('--eeg_feature_len', type = int, default = 832)
    parser.add_argument('--lr', type = float, default = 1e-5)
    parser.add_argument('--eps', type = float, default = 1e-4)
    parser.add_argument('--weight_decay', type = float, default = 1e-2)
    parser.add_argument('--warm_steps', type = int, default = 2000)
    parser.add_argument('--epochs', type = int, default = 200)
    parser.add_argument('--dev', type = bool, default = False)
    parser.add_argument('--device', type = str, default = 'cuda')
    
    return parser.parse_args()


if __name__ == '__main__':
    
    args = get_args()
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    device = torch.device(args.device)
    print(device)
    
    if args.dataset == 'KEmoCon':
        ###### COMING SOON #####
        pass
    
    elif args.dataset == 'ZuCo':
        
        if args.task == 'RD':
            ###### COMING SOON #####
            pass
        
        elif args.task == 'SA':
            
            assert (args.level == 'sentence' or args.level == 'word' or args.level == 'concatword'), 'Please choose a correct eeg feature type'
            
            if args.level == 'word':
                ###### COMING SOON #####
                pass
            elif args.level == 'concatword':
                ###### COMING SOON #####
                pass      
            
            else:
                # Load csv
                sentiment_labels = pd.read_csv('data/sentiment_labels_clean.csv')
                
                sr_eeg_data_path = 'data/SR'
                
                sentence_list = sentiment_labels.sentence.tolist()
                labels_list = sentiment_labels.sentiment_label.tolist()
                sentence_ids_list = sentiment_labels.sentence_id.tolist()
                
                eeg_dict = prepare_sr_eeg_data(sr_eeg_data_path, sentence_list, labels_list, sentence_ids_list, args)
                
                eeg_train_split, eeg_val_split, eeg_test_split = shuffle_split_data(eeg_dict)
                
                train_set, train_id_mapping = clean_dic(eeg_train_split)
                val_set, val_id_mapping = clean_dic(eeg_val_split)
                test_set, test_id_mapping = clean_dic(eeg_test_split)
                
                
                train_dataset = EEGDataset(train_set)
                val_dataset = EEGDataset(val_set)
                test_dataset = EEGDataset(test_set)
                                
                train_loader = DataLoader(
                    dataset=train_dataset,
                    batch_size=args.batch_size,
                    shuffle=True,
                )
                val_loader = DataLoader(
                    dataset=val_dataset,
                    batch_size=args.batch_size,
                    shuffle=False,
                )
                test_loader = DataLoader(
                    dataset=test_dataset,
                    batch_size=1,
                    shuffle=False,
                )
                
                # if args.model == 'transformer' and args.modality == 'fusion':
                #     model = FusionTransformer(device = device, d_feature_text = TEXT_LEN, d_feature_eeg = EEG_LEN,\
                #                             d_model = d_model, d_inner = d_inner, n_layers = num_layers, \
                #                             n_head=num_heads, d_k = d_k, d_v = d_v, dropout= dropout, \
                #                             class_num = class_num, args = args)
                    
                # elif args.model == 'transformer' and args.modality == 'text':
                #     model = TextTransformer(device = device, d_feature_text = TEXT_LEN,\
                #                             d_model = d_model, d_inner = d_inner, n_layers = num_layers, \
                #                             n_head=num_heads, d_k = d_k, d_v = d_v, dropout= dropout, \
                #                             class_num = class_num, args = args)
                    
                # elif args.model == 'transformer' and args.modality == 'eeg':
                #     print('hello')
                #     model = EEGTransformer(device = device, d_feature_eeg = EEG_LEN,\
                #                             d_model = d_model, d_inner = d_inner, n_layers = num_layers, \
                #                             n_head=num_heads, d_k = d_k, d_v = d_v, dropout= dropout, \
                #                             class_num = class_num, args = args)
                
                if args.model == 'transformer':
                    model = Transformer(device = device, d_feature_text = TEXT_LEN, d_feature_eeg = EEG_LEN,\
                                            d_model = d_model, d_inner = d_inner, n_layers = num_layers, \
                                            n_head=num_heads, d_k = d_k, d_v = d_v, dropout= dropout, \
                                            class_num = class_num, args = args)
                model = model.to(device)
                    
                optimizer = ScheduledOptim(
                    Adam(filter(lambda x: x.requires_grad, model.parameters()), 
                         betas = (0.9, 0.98), eps = args.eps, lr = args.lr, weight_decay = args.weight_decay),
                    d_model = d_model, n_warmup_steps = args.warm_steps
                )
                
                all_train_loss, all_train_acc = [], []
                for epoch in range(args.epochs):
                    
                    print('[ Epoch', epoch, ']')
                    start = time.time()
                    
                    trian_loss, train_acc, cm, all_pred, all_labels = train(train_loader, device, model, optimizer, train_dataset.__len__(), args)
                    
                    
                    
                    
                    
                    
            
                
