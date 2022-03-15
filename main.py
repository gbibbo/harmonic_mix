# Copyright (c) 2021 Gabriel Bibbó, Music Technology Grup, University Pompeu Fabra
# This is an open-access library distributed under the terms of the Creative Commons Attribution 3.0 Unported License, which permits unrestricted use, distribution, and reproduction in any medium, provided the
# original author and source are credited.
# Released under MIT License.

"""This module is responsible for loading the audio tracks,
analyzing and comparing them, in order to calculate their
harmonic compatibility."""

import os
import os.path
import ntpath
from json import JSONEncoder
import json
import librosa
import numpy as np
from essentia.standard import LogSpectrum, MonoLoader, Windowing, \
  Spectrum, FrameGenerator, NNLSChroma
from harmonic_mix.tivlib import TIV

SONG_KEPT = 0.3  # percentage of the song to compare
SR = 44100  # Sample rate


def decompose_harmonic(audio):
    """Given the audio of a loop, applies source separation
    from librosa to extract only the harmonic part

    :param audio: Audio sample arrangement (1xn)
    :return: Arrangement of the harmonic part of the audio samples (1xn)
    """

    decomposed = librosa.stft(audio)
    decomposed_harmonic, decomposed_percussive = \
        librosa.decompose.hpss(decomposed,kernel_size=(13,31))
    harmonic_part = librosa.istft(decomposed_harmonic)

    return harmonic_part

def audio_to_nnls(audio):
    """Computes the NNNLS chroma from the audio

    :param audio: Audio sample arrangement
    :return: A 12-dimensional chromagram (1x12), the result of averaging the chroma of each frame.
    """
    frame_size = 8192 + 1

    window = Windowing(type='hann', normalized=False)
    spectrum = Spectrum()
    logspectrum = LogSpectrum(frameSize=frame_size)
    nnls = NNLSChroma(frameSize=frame_size, useNNLS=False)

    logfreqspectrogram = []
    for frame in FrameGenerator(audio, frameSize=16384, hopSize=2048,
                                startFromZero=True):
        logfreqspectrum, meanTuning, _ = logspectrum(spectrum(window(frame)))
        logfreqspectrogram.append(logfreqspectrum)
    logfreqspectrogram = np.array(logfreqspectrogram)

    tunedLogfreqSpectrum, semitoneSpectrum, bassChroma, chroma =\
    nnls(logfreqspectrogram, meanTuning,  np.array([]))

    mean_chroma = np.mean(np.array(chroma).T, axis = 1)
    #Rotate the chroma so that it starts in C
    mean_chroma = np.roll(mean_chroma,-3)

    return mean_chroma

def save_tiv (annotation_path,TIV):
    """Saves the vector and energy values of the TIV in a .json file

    :param annotation_path: Path where the annotation .json file is saved
    :param TIV: TIV instance with the values corresponding to the track analysis.
    """

    class NumpyArrayEncoder(JSONEncoder):
        """Creates a NumPy array, and saving it as context variable"""
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return JSONEncoder.default(self, obj)

    TIV_string = {"TIV.energy.real": TIV.energy.real, "TIV.energy.imag": TIV.energy.imag,
                  "TIV.vector[0].real": TIV.vector[0].real, "TIV.vector[0].imag": TIV.vector[0].imag,
                  "TIV.vector[1].real": TIV.vector[1].real, "TIV.vector[1].imag": TIV.vector[1].imag,
                  "TIV.vector[2].real": TIV.vector[2].real, "TIV.vector[2].imag": TIV.vector[2].imag,
                  "TIV.vector[3].real": TIV.vector[3].real, "TIV.vector[3].imag": TIV.vector[3].imag,
                  "TIV.vector[4].real": TIV.vector[4].real, "TIV.vector[4].imag": TIV.vector[4].imag,
                  "TIV.vector[5].real": TIV.vector[5].real, "TIV.vector[5].imag": TIV.vector[5].imag}

    with open(annotation_path, "w") as write_file:
        json.dump(TIV_string, write_file, cls=NumpyArrayEncoder)

def load_tiv (annotation_path):
    """Loads the vector and energy values of the TIV from a given .json file

    :param annotation_path: Annotation path to automatically generated .json file.
    :return: TIV instance (defined in tivlib.py) with the value of the track-specific vectors and energy.
    """

    chroma_ref = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    tiv = TIV.from_pcp(chroma_ref)
    open_file=open(annotation_path, 'r')
    TIV_dict= json.load(open_file)
    open_file.close()
    tiv.energy = complex(float(TIV_dict['TIV.energy.real']), float(TIV_dict['TIV.energy.imag']))
    temp = [np.complex(float(TIV_dict['TIV.vector[0].real']), float(TIV_dict['TIV.vector[0].imag'])),
                  np.complex(float(TIV_dict['TIV.vector[1].real']), float(TIV_dict['TIV.vector[1].imag'])),
                  np.complex(float(TIV_dict['TIV.vector[2].real']), float(TIV_dict['TIV.vector[2].imag'])),
                  np.complex(float(TIV_dict['TIV.vector[3].real']), float(TIV_dict['TIV.vector[3].imag'])),
                  np.complex(float(TIV_dict['TIV.vector[4].real']), float(TIV_dict['TIV.vector[4].imag'])),
                  np.complex(float(TIV_dict['TIV.vector[5].real']), float(TIV_dict['TIV.vector[5].imag']))]
    tiv.vector = np.asarray(temp)
    return tiv


def analyze_song (song_path):
    """
    Computes the TIV from a given song (path)
        0) Checks if the file exists
        1) Loads the song with MonoLoader (essentia)
        2) Cuts the song
        3) Retrives percusive part applying source separation (librosa)
        4) Computes NNLS chroma (essentia)
        5) Computes TIV (tivlib)
        6) Saves results

    :param song_path: The path of the track you want to analyze
    """

    folder_path, song_name = ntpath.split(song_path)

    annotation_path = folder_path + '/annotations/' + song_name.replace(".mp3", ".json")

    if os.path.isfile(annotation_path):
        # File exist
        print(song_name.replace(".mp3", "") + ' already analyzed')
    else:
        # File doesn't exist
        print('Analyzing ' + song_name.replace(".mp3", ""))
        song_audio = MonoLoader(filename=song_path, sampleRate=SR)()

        kept = SONG_KEPT / 2
        song_audio = song_audio[int(song_audio.size / 2 - song_audio.size * kept):int(
            song_audio.size / 2 + song_audio.size * kept)]

        harmonic = decompose_harmonic(song_audio)

        chroma = audio_to_nnls(harmonic)
        tiv = TIV.from_pcp(chroma)

        os.makedirs(folder_path + '/annotations/', exist_ok=True)
        save_tiv(annotation_path, tiv)


def compare_songs(current_song_path, candidate_song_path, transpose_candidate=0):
    """
    Computes harmonic compatibility between two given songs (paths).
    Also suggests the amount of pitch shift transpisition to maximize
    the harmonic compatibility.

    :param current_song_path: The path of the target track
    :param candidate_song_path: The path of the candidate track
    :param transpose_candidate: An interval (in positive or negative semitones) with which the
            pitch transposition of the candidate track will be simulated. Default zero.
    :return: The harmonic compatibility between the target track and each of the other tracks in the folder, all in their original versions.
            The suggested pitch transposition interval (in semitones) that would maximize harmonic compatibility.
            The resulting harmonic compatibility if the suggested pitch transposition were applied.
    """

    current_folder_path, current_song_name = ntpath.split(current_song_path)
    candidate_folder_path, candidate_song_name = ntpath.split(candidate_song_path)

    current_annotation_path = current_folder_path + '/annotations/' \
                              + current_song_name.replace(".mp3", ".json")
    candidate_annotation_path = candidate_folder_path + '/annotations/' \
                                + candidate_song_name.replace(".mp3", ".json")

    TIV_current = load_tiv(current_annotation_path)
    TIV_candidate = load_tiv(candidate_annotation_path)
    TIV_candidate.transpose(transpose_candidate, inplace=True)

    harmonic_compatibility = TIV_candidate.small_scale_compatibility(TIV_current)
    harmonic_compatibility = 100 * (1 - np.mean(harmonic_compatibility))

    pitch_shift, min_small_scale_comp = TIV_current.get_max_compatibility(TIV_candidate)
    min_small_scale_comp = 100 * (1 - np.mean(min_small_scale_comp))

    return scale(harmonic_compatibility), pitch_shift, scale(min_small_scale_comp)

def scale(not_scaled_number):
    """Harmonic compatibility values range from 70% to 100%
    We want to express them between 0% to 100%

    :param not_scaled_number: Real number from 0 to 100.
    :return: Real number from 70 to 100.
    """

    n_min = 70
    n_max = 100
    return (not_scaled_number-n_min)*n_max/(n_max-n_min)


if __name__ == '__main__':

    genre = 'progressive_house/'
    current_song = "Blanka Barbara - Lost in Digital Fog (Original) - 11A - 124"
    candidate_song = "Teklix - The Tribal Code - 6A - 124"
    current_song_path = "harmonic_mix/music/" + genre + current_song + ".mp3"
    candidate_song_path = "harmonic_mix/music/" + genre + candidate_song + ".mp3"
    analyze_song(current_song_path)
    analyze_song(candidate_song_path)
    harmonic_compatibility, pitch_shift, min_small_scale_comp = \
        compare_songs(current_song_path, candidate_song_path,1)  #Compares original version of current song with one semitone pitch shifted version of the candidate song.
    pitch_shift_sign = ""
    if pitch_shift > 0:
        pitch_shift_sign = "+"

    print("Harmonic compatibility: ", round(harmonic_compatibility, 2), "%")
    print("Recommended pitch shift: ", pitch_shift_sign , pitch_shift, "st")
    print("Resulting harmonic compatibility (after pitch shifting): ",
          round(min_small_scale_comp, 2), "%")
