import glob
import os
import sys
import pickle
import math
import datetime
import shutil
import checksumdir
from multiprocessing import Pool, cpu_count
import numpy as np
from music21 import converter, instrument, stream, note, chord
from random_word import RandomWords
from notes_sequence import NotesSequence


CHECKPOINTS_DIR = "checkpoints"
MIDI_SONGS_DIR = "midi_songs"
TRAINING_DATA_DIR = "training_data"
NOTES_FILENAME = "notes"
HASH_FILENAME = "dataset_hash"
RESULTS_DIR = "results"
SEQUENCE_LENGTH = 60
VALIDATION_SPLIT = 0.2
PREDICTION_SIZE = 88

"""
changing this value requires refactoring

predict.py -> loop inside generate_notes() [getting prediction]
data_preparation.py -> loop inside prepare_sequences_for_training() [out sequences]
"""
NUM_NOTES_TO_PREDICT = 1


def clear_checkpoints():
    try:
        shutil.rmtree(CHECKPOINTS_DIR)
    except FileNotFoundError:
        print("Checkpoints directory doesn't exist")


def clear_training_data():
    try:
        shutil.rmtree(TRAINING_DATA_DIR)
    except FileNotFoundError:
        print("Training data directory doesn't exist")


def save_data_hash(hash_value):
    if not os.path.isdir(TRAINING_DATA_DIR):
        os.mkdir(TRAINING_DATA_DIR)

    hash_file_path = os.path.join(TRAINING_DATA_DIR, HASH_FILENAME)
    with open(hash_file_path, "wb") as hash_file:
        pickle.dump(hash_value, hash_file)


def is_data_changed():
    current_hash = checksumdir.dirhash(MIDI_SONGS_DIR)

    hash_file_path = os.path.join(TRAINING_DATA_DIR, HASH_FILENAME)
    if not os.path.exists(hash_file_path):
        save_data_hash(current_hash)
        return True

    with open(hash_file_path, "rb") as hash_file:
        previous_hash = pickle.load(hash_file)

    if previous_hash != current_hash:
        save_data_hash(current_hash)
        return True

    return False


def get_notes_from_file(file):
    print(f"Parsing {file}")

    midi = converter.parse(file)
    notes = []
    try:
        # file has instrument parts
        instrument_stream = instrument.partitionByInstrument(midi)
        notes_to_parse = instrument_stream.parts[0].recurse()
    except:
        # file has notes in a flat structure
        notes_to_parse = midi.flat.notes

    for element in notes_to_parse:
        multi_label_pattern = np.zeros(PREDICTION_SIZE)

        if isinstance(element, note.Note):
            midi_pitch = element.pitch.midi
            multi_label_pattern[midi_pitch - 21] = 1
            multi_label_pattern.astype(np.int8)
            notes.append(multi_label_pattern)

        elif isinstance(element, chord.Chord):
            for pitch in element.pitches:
                midi_pitch = pitch.midi
                multi_label_pattern[midi_pitch - 21] = 1

            multi_label_pattern.astype(np.int8)
            notes.append(multi_label_pattern)

    return notes


def get_notes_from_dataset():
    notes_path = os.path.join(TRAINING_DATA_DIR, NOTES_FILENAME)
    notes = []
    if is_data_changed():
        try:
            with Pool(cpu_count() - 1) as pool:
                notes_from_files = pool.map(
                    get_notes_from_file, glob.glob(f"{MIDI_SONGS_DIR}/*.mid")
                )

            for notes_from_file in notes_from_files:
                for note in notes_from_file:
                    notes.append(note)

            with open(notes_path, "wb") as notes_data_file:
                pickle.dump(notes, notes_data_file)

        except:
            hash_file_path = os.path.join(TRAINING_DATA_DIR, HASH_FILENAME)
            os.remove(hash_file_path)
            print("Removed the hash file")
            sys.exit(1)

    else:
        with open(notes_path, "rb") as notes_data_file:
            notes = pickle.load(notes_data_file)

    return notes


def prepare_sequences_for_training(notes, batch_size):
    training_split = 1 - VALIDATION_SPLIT
    dataset_split = math.ceil(training_split * len(notes))

    training_sequence = NotesSequence(
        notes[:dataset_split], batch_size, SEQUENCE_LENGTH, PREDICTION_SIZE
    )

    validation_sequence = NotesSequence(
        notes[dataset_split:], batch_size, SEQUENCE_LENGTH, PREDICTION_SIZE
    )

    return training_sequence, validation_sequence


def prepare_sequence_for_prediction(notes):
    if len(notes) < SEQUENCE_LENGTH:
        print(
            f"File is to short. Min length: {SEQUENCE_LENGTH} sounds, provided: {len(notes)}."
        )
        sys.exit(1)

    sequence_in = notes[:SEQUENCE_LENGTH]
    network_input = notes[SEQUENCE_LENGTH]

    return network_input


def save_midi_file(prediction_output):
    offset = 0
    output_notes = []

    # create note and chord objects based on the values generated by the model
    for pattern in prediction_output:
        # pattern is a chord
        if np.count_nonzero(pattern) > 1:
            non_zero_indices = []
            for non_zero_idx in np.nonzero(pattern)[0]:
                non_zero_indices.append(non_zero_idx)

            # midi values on piano starts from 21
            midis = [non_zero_idx + 21 for non_zero_idx in non_zero_indices]

            notes = []
            for midi in midis:
                new_note = note.Note(midi)
                new_note.storedInstrument = instrument.Piano()
                notes.append(new_note)

            new_chord = chord.Chord(notes)
            new_chord.offset = offset
            output_notes.append(new_chord)

        # pattern is a note
        else:
            midi = np.nonzero(pattern)[0][0]
            new_note = note.Note(midi)
            new_note.offset = offset
            new_note.storedInstrument = instrument.Piano()
            output_notes.append(new_note)

        # increase offset each iteration so that notes do not stack
        offset += 0.5

    output_name = ""
    try:
        random_words = RandomWords().get_random_words()
        for i in range(2):
            output_name += random_words[i] + "_"
        output_name = output_name.rstrip("_").lower()

    except:
        output_name = f"output_{datetime.datetime.now()}"

    midi_stream = stream.Stream(output_notes)
    midi_stream.write("midi", fp=f"{RESULTS_DIR}/{output_name}.mid")

    print(f"Result saved as {output_name}")
