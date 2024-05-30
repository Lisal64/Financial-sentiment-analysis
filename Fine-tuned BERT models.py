# -*- coding: utf-8 -*-
"""Latzelsperger_ CL_final project.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Ag6dEz9ZyVjMLo-MZk2ABEOqAp0vj7ot

Loading the dataset
"""

!pip install bertviz
!pip install transformers
!pip install bertviz transformers

!pip install datasets

!pip install transformers[torch]

"""Mounting google drive"""

from google.colab import drive
drive.mount('/content/drive')

!mkdir -p "/content/drive/My Drive/UniWien/Teaching/ComputationalLinguistics_2023/Latzelsperger"

"""Loading BERT"""

from bertviz import head_view, model_view
from transformers import BertTokenizer, BertModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification

bert_model_type = 'bert'
bert_model_version = 'bert-base-uncased'
bert_tokenizer = AutoTokenizer.from_pretrained(bert_model_version)
bert_model = AutoModelForSequenceClassification.from_pretrained(bert_model_version, num_labels = 3)

"""Loading RoBERTa"""

from transformers import RobertaTokenizer, RobertaForSequenceClassification

roberta_model_type = 'roberta'
roberta_model_version = "roberta-base"
roberta_tokenizer = RobertaTokenizer.from_pretrained(roberta_model_version)
roberta_model = RobertaForSequenceClassification.from_pretrained(roberta_model_version, output_attentions=True, num_labels = 3)

"""Loading Data"""

from datasets import load_dataset, DatasetDict
import csv
import random

fin_dataset = load_dataset("TimKoornstra/financial-tweets-sentiment")
print(fin_dataset['train'])
print(fin_dataset.keys())
fin_dataset.shape

# examining data
for key in fin_dataset:
  print(f"Length dataset: {len(fin_dataset)}")
  print(f"Dataset: {key}")
  print(f"Data: {fin_dataset[key]}")
  print(f"Tweet: {fin_dataset[key]['tweet'][:10]}")
  print(f"Sentiment: {fin_dataset[key]['sentiment'][:10]}")
  print(f"URL: {fin_dataset[key]['url'][:10]}")

def truncate(example):
  return {
      'tweet': " ".join(example['tweet'].split()),
      'sentiment': example['sentiment']
  }

# Due to memory issues the data used is very small resulting in worse results than hoped for.
small_fin_dataset = DatasetDict(
    train = fin_dataset['train'].shuffle(seed=24).select(range(128)).map(truncate),
    val = fin_dataset['train'].shuffle(seed=24).select(range(128, 160)).map(truncate),
    test = fin_dataset['train'].shuffle(seed=24).select(range(160, 192)).map(truncate),
)

small_fin_dataset

"""pre-processing - BERT"""

def bert_tokenize_dataset(examples):
  return bert_tokenizer(examples['tweet'], padding = True, truncation = True)

bert_viz_tokenized_dataset = small_fin_dataset.map(bert_tokenize_dataset, batched = True, batch_size = 16)
bert_small_tokenized_dataset = small_fin_dataset.map(bert_tokenize_dataset, batched = True, batch_size = 16)
bert_small_tokenized_dataset = bert_small_tokenized_dataset.remove_columns(['tweet'])
bert_small_tokenized_dataset = bert_small_tokenized_dataset.remove_columns(['url'])
bert_small_tokenized_dataset = bert_small_tokenized_dataset.rename_column('sentiment', 'labels')
bert_small_tokenized_dataset.set_format('torch')

bert_small_tokenized_dataset['train'][0:2]

from torch.utils.data import DataLoader

bert_train_dataloader = DataLoader(bert_small_tokenized_dataset['train'], batch_size = 16)
bert_eval_dataloader = DataLoader(bert_small_tokenized_dataset['val'], batch_size = 16)

print(bert_train_dataloader)
print(bert_eval_dataloader)

"""Training BERT"""

from transformers import AdamW, get_linear_schedule_with_warmup
from tqdm.notebook import tqdm
num_epochs = 15
num_training_steps = 5 * len(bert_train_dataloader)
optimizer = AdamW(bert_model.parameters(), lr=5e-5, weight_decay=0.01)
lr_scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=num_training_steps)

import torch
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
bert_model.to(device)

!mkdir bert_checkpoints

import torch
from tqdm.auto import tqdm

progress_bar = tqdm(range(num_training_steps))
best_val_loss = float("inf")

bert_model.train()
for epoch in range(num_epochs):
    for batch in bert_train_dataloader:
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = bert_model(**batch)
        loss = outputs.loss
        loss.backward()

        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()
        progress_bar.update(1)

    # validation
    bert_model.eval()
    with torch.no_grad():
      for batch_i, batch in enumerate(bert_eval_dataloader):
        batch = {k: v.to(device) for k, v in batch.items()}
        output = bert_model(**batch)
        loss += output.loss

    avg_val_loss = loss / len(bert_eval_dataloader)
    print(f"Validation loss: {avg_val_loss}")
    if avg_val_loss < best_val_loss:
        print("Saving checkpoint!")
        best_val_loss = avg_val_loss
        bert_model.save_pretrained(f"bert_checkpoints/epoch_{epoch}.pt")

"""Pre-processing Roberta"""

def roberta_tokenize_dataset(examples):
  return roberta_tokenizer(examples['tweet'], padding = True, truncation = True)

roberta_viz_tokenized_dataset = small_fin_dataset.map(roberta_tokenize_dataset, batched = True, batch_size = 16)
roberta_small_tokenized_dataset = small_fin_dataset.map(roberta_tokenize_dataset, batched = True, batch_size = 16)
roberta_small_tokenized_dataset = roberta_small_tokenized_dataset.remove_columns(['tweet'])
roberta_small_tokenized_dataset = roberta_small_tokenized_dataset.remove_columns(['url'])
roberta_small_tokenized_dataset = roberta_small_tokenized_dataset.rename_column('sentiment', 'labels')
roberta_small_tokenized_dataset.set_format('torch')

roberta_small_tokenized_dataset['train'][0:2]

from torch.utils.data import DataLoader

roberta_train_dataloader = DataLoader(roberta_small_tokenized_dataset['train'], batch_size = 16)
roberta_eval_dataloader = DataLoader(roberta_small_tokenized_dataset['val'], batch_size = 16)

"""Training Roberta"""

from transformers import AdamW, get_linear_schedule_with_warmup
from tqdm.notebook import tqdm
print(len(roberta_train_dataloader))
num_epochs = 12
num_training_steps = 6 * len(roberta_train_dataloader)
optimizer = AdamW(roberta_model.parameters(), lr=5e-5, weight_decay=0.01)
lr_scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=num_training_steps)

import torch
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
roberta_model.to(device)

!mkdir roberta_checkpoints

import torch
from tqdm.auto import tqdm

progress_bar = tqdm(range(num_training_steps))
best_val_loss = float("inf")

roberta_model.train()
for epoch in range(num_epochs):
    for batch in roberta_train_dataloader:
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = roberta_model(**batch)
        loss = outputs.loss
        loss.backward()

        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()
        progress_bar.update(1)

    roberta_model.eval()
    with torch.no_grad():
      for batch_i, batch in enumerate(roberta_eval_dataloader):
        batch = {k: v.to(device) for k, v in batch.items()}
        output = roberta_model(**batch)
        loss += output.loss

    avg_val_loss = loss / len(roberta_eval_dataloader)
    print(f"Validation loss: {avg_val_loss}")
    if avg_val_loss < best_val_loss:
        print("Saving checkpoint!")
        best_val_loss = avg_val_loss
        roberta_model.save_pretrained(f"roberta_checkpoints/epoch_{epoch}.pt")

"""Testing fine-tuned BERT"""

from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
from sklearn.metrics import matthews_corrcoef
from sklearn.metrics import confusion_matrix
import pandas as pd
import seaborn as sns

bert_test_dataloader = DataLoader(bert_small_tokenized_dataset['test'], batch_size=8)

bert_fine_tuned_model = AutoModelForSequenceClassification.from_pretrained("/content/bert_checkpoints/epoch_2.pt").to(device)

total_predict = []
total_label = []

for batch in bert_test_dataloader:
    model_inputs = {k: v.to(device) for k, v in batch.items()}
    labels = model_inputs.pop("labels")  # Remove labels from model_inputs
    labels = labels.to(device)

    predictions = torch.argmax(bert_fine_tuned_model(**model_inputs).logits, dim=1)
    total_predict.extend(predictions.cpu().tolist())
    total_label.extend(labels.cpu().tolist())

    for prediction in predictions:
        ["neutral", "positive", "negative"][prediction]  # 0 = neutral, 1 = positive, 2 = negative


# Evaluation
accuracy = accuracy_score(total_label, total_predict)
recall = recall_score(total_label, total_predict, average = "micro")
precision = precision_score(total_label, total_predict, average = "micro")
f1 = f1_score(total_label, total_predict, average = "micro")
mmc = matthews_corrcoef(total_label, total_predict)

conf_matrix = confusion_matrix(total_label, total_predict)

print(f"Accuracy: {accuracy * 100}")
print(f"Recall: {recall * 100}")
print(f"Precision: {precision * 100}")
print(f"F1: {f1 * 100}")
print(f"MMC: {mmc * 100}")

labels = ["neutral", "positive", "negative"]
df_cm = pd.DataFrame(conf_matrix, labels, labels)

sns.set(font_scale=1.4)
sns.heatmap(df_cm, annot=True, fmt='d', cmap="YlGnBu")

"""Testing fine-tuned RoBERTa"""

roberta_test_dataloader = DataLoader(roberta_small_tokenized_dataset['test'], batch_size = 16)

roberta_fine_tuned_model = RobertaForSequenceClassification.from_pretrained("/content/roberta_checkpoints/epoch_2.pt").to(device)

total_predict = []
total_label = []

for batch in roberta_test_dataloader:
    model_inputs = {k: v.to(device) for k, v in batch.items()}
    labels = model_inputs.pop("labels")  # Remove labels from model_inputs
    labels = labels.to(device)

    predictions = torch.argmax(roberta_fine_tuned_model(**model_inputs).logits, dim = 1)
    total_predict.extend(predictions.cpu().tolist())
    total_label.extend(labels.cpu().tolist())


    for prediction in predictions:
        ["neutral", "positive", "negative"][prediction]

accuracy = accuracy_score(total_label, total_predict)
recall = recall_score(total_label, total_predict, average = "micro")
precision = precision_score(total_label, total_predict, average = "micro")
f1 = f1_score(total_label, total_predict, average = "micro")
mmc = matthews_corrcoef(total_label, total_predict)

conf_matrix = confusion_matrix(total_label, total_predict)

print(f"Accuracy: {accuracy * 100}")
print(f"Recall: {recall * 100}")
print(f"Precision: {precision * 100}")
print(f"F1: {f1 * 100}")
print(f"MMC: {mmc * 100}")

labels = ["neutral", "positive", "negative"]
df_cm = pd.DataFrame(conf_matrix, labels, labels)

sns.set(font_scale=1.4)
sns.heatmap(df_cm, annot=True, fmt='d', cmap="YlGnBu")

"""# **Visualization**

**BERT**
"""

from torch.utils.tensorboard import SummaryWriter
import re
import torch
import tensorflow as tf
import tensorboard as tb

import numpy as np
import os
from transformers import TrainingArguments, Trainer
from transformers import AutoModelForSequenceClassification

bert_model_inputs = bert_tokenizer(bert_viz_tokenized_dataset['test']['tweet'], padding=True, truncation=True, return_tensors='pt').to(device)
bert_outputs = bert_fine_tuned_model(**bert_model_inputs, output_hidden_states=True)

path = "/content/drive/MyDrive/Uni/MT_CL/final project/bert_viz_results_final"
layer = 0

if not os.path.exists(path):
    os.mkdir(path)

while layer < len(bert_outputs['hidden_states']):
    if not os.path.exists(path+'/layer_' + str(layer)):
        os.mkdir(path +'/layer_' + str(layer))

    example = 0
    tensors = []
    labels = []

    while example < len(bert_model_inputs['input_ids']):
        sp_token_position = 0
        for token in bert_model_inputs['input_ids'][example]:
            if token != 101:
                sp_token_position += 1
            else:
                tensor = bert_outputs['hidden_states'][layer][example][sp_token_position]
                tensors.append(tensor)
                break

        label = [bert_viz_tokenized_dataset['test']['tweet'][example], str(bert_viz_tokenized_dataset['test']['sentiment'][example])]
        labels.append(label)
        example += 1

    if tensors:
        writer = SummaryWriter(path+'/layer_' + str(layer))
        writer.add_embedding(torch.stack(tensors), metadata=labels, metadata_header=['Tweet','Sentiment'])

    layer += 1

"""**Roberta**

"""

roberta_model_inputs = roberta_tokenizer(roberta_viz_tokenized_dataset['test']['tweet'], padding=True, truncation=True, return_tensors='pt').to(device)
roberta_outputs = roberta_fine_tuned_model(**roberta_model_inputs, output_hidden_states=True)

print(roberta_model_inputs['input_ids'].shape)
print(roberta_model_inputs['input_ids'].device)

print(roberta_viz_tokenized_dataset['test']['tweet'])

# making sure that they are equal in length
print(len(roberta_model_inputs['input_ids']))
print(len(roberta_viz_tokenized_dataset['test']['tweet']))
print(len(roberta_viz_tokenized_dataset['test']['sentiment']))

path = "/content/drive/MyDrive/Uni/MT_CL/final project/roberta_viz_results_final"
layer = 0

if not os.path.exists(path):
    os.mkdir(path)

while layer < len(roberta_outputs['hidden_states']):
    if not os.path.exists(path+'/layer_' + str(layer)):
        os.mkdir(path +'/layer_' + str(layer))

    example = 0
    tensors = []
    labels = []

    while example < len(roberta_model_inputs['input_ids']):
        sp_token_position = 0
        for token in roberta_model_inputs['input_ids'][example]:
            if token != 2:
                sp_token_position += 1
            else:
                tensor = roberta_outputs['hidden_states'][layer][example][sp_token_position]
                tensors.append(tensor)
                break

        label = [roberta_viz_tokenized_dataset['test']['tweet'][example], str(roberta_viz_tokenized_dataset['test']['sentiment'][example])]
        labels.append(label)
        example += 1

    if tensors:
        writer = SummaryWriter(path+'/layer_' + str(layer))
        writer.add_embedding(torch.stack(tensors), metadata=labels, metadata_header=['Tweet','Sentiment'])

    layer += 1

