# Classical Piano Composer

This project allows you to train a neural network to generate midi music files that make use of a single instrument

## Requirements

```
    conda env create
```
## How to run

### To download the Maestro dataset run:

```
sh /data/scripts/get_maestro.sh
```

### To train the network run:

```
python train.py -h
```

The network will use every midi file in ./midi_songs to train the network. The midi files should only contain a single instrument to get the most out of the training.

**NOTE**: You can stop the process at any point in time and the weights from the latest completed epoch will be available for text generation purposes.

### To start ngrok server with Tensorboard:

```
python tensorboard.py -h
```

### To generate music run:

```
python predict.py -h
```