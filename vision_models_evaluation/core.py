# AUTOGENERATED! DO NOT EDIT! File to edit: ../01_core.ipynb.

# %% auto 0
__all__ = ['evaluate']

# %% ../01_core.ipynb 2
from pathlib import Path
from sklearn.model_selection import BaseCrossValidator
from fastai.vision.learner import Learner
from fastai.data.block import DataBlock
from fastai.data.load import DataLoader
from fastai.data.transforms import IndexSplitter

from typing import Callable, Tuple

# %% ../01_core.ipynb 4
from pathlib import Path
from sklearn.model_selection import BaseCrossValidator
from fastai.vision.learner import unet_learner
from fastai.data.block import DataBlock
from fastai.data.load import DataLoader
from fastai.data.transforms import IndexSplitter

from typing import Callable, Tuple

import gc
import torch

def evaluate(
    datablock_hparams: dict, # The hyperparameters used to get and load the data.
    dataloader_hparams: dict, # The hyperparameters used to define how the data is supplied to the learner.
    technique: BaseCrossValidator, # The technique used to split the data.
    learner_hparams: dict,  # The parameters used to build the learner (backbone, cbs...). Those hyperparams are used to build all the models.
    learning_hparams: dict, # The parameters used to train the learner (learning_rate, freeze_epochs)
    learning_mode: str = "finetune" # The learning mode: random or finetune.
):
    
    # Defines all the metrics used in the training and evaluation phases
    metrics = ["validation"]
    other_metrics = learner_hparams["metrics"] if "metrics" in learner_hparams else []
    all_metrics = list(map(lambda metric: metric if type(metric) == str else metric.__class__.__name__, metrics + other_metrics))
    results = dict([[metric, []] for metric in all_metrics])
    
    # Gets all the data
    get_items_form = "get_items" if "get_items" in datablock_hparams else "get_x"
    get_items = [datablock_hparams[get_items_form], datablock_hparams["get_y"]]

    X = get_items[0](dataloader_hparams["source"])
    y = [get_items[1](x) for x in X]
    for _, testing_indexes in technique.split(X, y):
        dls = DataBlock(**datablock_hparams).dataloaders(**dataloader_hparams)
        learner = unet_learner(dls, **learner_hparams).to_fp16()
        if learning_mode == "random":
            learner.fit_one_cycle(**learning_hparams)
        elif learning_mode == "finetune":
            learner.fine_tune(**learning_hparams)
        else:
            raise Exception(f"{learning_mode} is not a learning_mode. Use 'random' or 'finetune' instead.")
        
        # Replaces the training dls and tests the model
        datablock_hparams["splitter"] = IndexSplitter(testing_indexes)
        learner.dls = DataBlock(**datablock_hparams).dataloaders(**dataloader_hparams)
        for metric, metric_value in zip(results, learner.validate()):
            results[metric] += [metric_value]
        
        # Wipes the memory of the gpu
        gc.collect()
        torch.cuda.empty_cache()
    
    return results
