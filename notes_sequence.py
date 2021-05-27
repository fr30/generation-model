from keras.utils import Sequence, np_utils
import math
import numpy as np


class NotesSequence(Sequence):

    def __init__(
            self,
            notes,
            batch_size,
            sequence_length,
            vocab,
            vocab_size,
            num_notes_to_predict):
        self.notes = notes
        self.batch_size = batch_size
        self.sequence_length = sequence_length
        self.vocab = vocab
        self.vocab_size = vocab_size
        self.num_notes_to_predict = num_notes_to_predict

    def __len__(self):
        return math.ceil(len(self.notes) / self.batch_size)

    def __getitem__(self, idx):
        network_input = []
        network_output = []
        batch = self.notes[idx * self.batch_size:(idx + 1) * self.batch_size]
        for i in range(len(batch) - self.sequence_length):
            sequence_in = batch[i: i + self.sequence_length]
            note_out = batch[i + self.sequence_length]
            network_input.append([self.vocab[note] for note in sequence_in])
            network_output.append(self.vocab[note_out])

        n_patterns = len(network_input)

        unnormalized_network_input = np.reshape(
            network_input, (n_patterns, self.sequence_length, self.num_notes_to_predict))
        normalized_network_input = unnormalized_network_input / float(self.vocab_size)

        network_output = np_utils.to_categorical(network_output, self.vocab_size)

        return (normalized_network_input, network_output)
