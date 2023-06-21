import torch
import torch.nn as nn
from torch.optim import Adam
import numpy as np
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
import pickle


# Main reference from capstone era: https://github.com/div-lab/video-highlights/blob/capstone/model_training/fine_grained_classification.py

class MultiClassClassifier(nn.Module):
    def __init__(self, input_dim, num_classes) :
        super().__init__()
        # not sure if input dimension should be something else but here we are
        self.input_dim = input_dim
        self.linear1 = nn.Linear(input_dim, 1024)
        self.linear2 = nn.Linear(1024, 256)
        self.out_layer = nn.Linear(256, num_classes)
        self.relu = torch.nn.ReLU()

    def forward(self, inputs):
        inputs = inputs.view(-1 , self.input_dim)
        out = self.relu(self.linear1(inputs))
        out = self.relu(self.linear2(out))
        out = self.out_layer(out)
        return out


class DetectionData(Dataset):
    def __init__(self, box_vectors, box_labels, unique_labels, transformations=None):
        super().__init__()
        self.box_vectors = box_vectors
        self.box_labels = box_labels
        self.transformations = transformations
        
        # Map each unique label to an index
        self.label2idx = {
            label: index for (index, label) in enumerate(unique_labels)
        }

        # Convert each box label to appropriate one-hot vector for model training
        labels_as_indices = [self.label2idx[label] for label in self.box_labels]
        num_classes = len(unique_labels)
        targets = np.array(labels_as_indices).reshape(-1)
        self.one_hot_labels = np.eye(num_classes)[targets]

    def __len__(self):
        return len(self.box_labels)
    
    def __getitem__(self, idx):
        x = pickle.loads(self.box_vectors[idx])

        if self.transformations is not None:
            x = self.transformations(x)

        y = self.one_hot_labels[idx]
        return x, y


class ClassifierManager():
    # box_vectors = byte arrays for each box containing the extracted image features 
    #               (aka learned values or features that help with classification)
    # box_labels = list of label names (strings) for each box vector
    # unique_labels = list of label names containing no duplicates
    def __init__(self, box_vectors, box_labels, unique_labels) :
        super().__init__()
        self.unique_labels = unique_labels
        self.box_labels = box_labels
        self.transformations = None
        self.train_data = DetectionData(box_vectors, box_labels, unique_labels, self.transformations)
        self.train_loader = DataLoader(self.train_data, batch_size=64, shuffle=True)

        single_sample_size = self.train_data[0][0].size()[1:]
        flat_features = 1
        for s in single_sample_size:
            flat_features *= s
        self.classifier = MultiClassClassifier(flat_features, len(unique_labels))

    
    def fit(self):
        optimizer = Adam(self.classifier.parameters())
        criterion = nn.CrossEntropyLoss()

        # Run through the training loop for a view epochs
        for epoch in range(5):
            self.classifier.train()

            for batch_num, (x, y) in enumerate(self.train_loader):
                y_pred = self.classifier(x)
                loss = criterion(y_pred, y)
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()
                print(f"Epoch: {epoch} | Batch: {batch_num} | Loss: {loss.item()}")


    # Inputs = list of image feature vectors
    def predict(self, inputs):
        self.classifier.eval()
        inputs_as_tensors = []
        for input in inputs:
            x = pickle.loads(input)
            if self.transformations is not None:
                x = self.transformations(x)
            inputs_as_tensors.append(x)
        inputs_as_tensors = torch.stack(inputs_as_tensors)
        
        logits = self.classifier(inputs_as_tensors)
        pred_probab = nn.Softmax(dim=1)(logits)
        y_pred = pred_probab.argmax(1)
        label_names = [self.unique_labels[(int(pred))] for pred in y_pred]
        return label_names

        
# Test stuff in this file as necessary
if __name__ == "__main__":
    exit()



