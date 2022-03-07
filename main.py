#Gabriel Bibbó, 2021
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
  Spectrum, FrameGenerator, NNLSChroma #, HPCP
from harmonic_mix.tivlib import TIV

SONG_KEPT = 0.3  # percentage of the song to compare
SR = 44100  # Sample rate


def decompose_harmonic(audio):
    """Given the audio of a loop, applies source separation
    from librosa to extract only the harmonic part"""

    decomposed = librosa.stft(audio)
    decomposed_harmonic, decomposed_percussive = \
        librosa.decompose.hpss(decomposed,kernel_size=(13,31))
    harmonic_part = librosa.istft(decomposed_harmonic)

    return harmonic_part

def audio_to_nnls(audio):
    """Computes the chroma from the audio"""
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
    """Saves the vector and energy values of the TIV in a .json file"""

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
    """Loads the vector and energy values of the TIV from a given .json file"""

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
    """Computes the TIV from a given song (path)
    0) Checks if the file exists
    1) Loads the song with MonoLoader (essentia)
    2) Cuts the song
    3) Retrives percusive part applying source separation (librosa)
    4) Computes NNLS chroma (essentia)
    5) Computes TIV (tivlib)
    6) Saves results"""

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
    """Computes harmonic compatibility between two given songs (paths). Also suggests
    the amount of pitch shift transpisition to maximize the harmonic compatibility"""

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
    We want to express them between 0% to 100%"""

    n_min = 70
    n_max = 100
    return (not_scaled_number-n_min)*n_max/(n_max-n_min)


if __name__ == '__main__':
    # @title Select two PROGESSIVE HOUSE songs to compute the hamonic similarity ↓↓↓↓ { run: "auto" }
    genre = 'progressive_house/'
    #genre = 'prueba/'
    current_song = "Blanka Barbara - Lost in Digital Fog (Original) - 11A - 124"  # @param ["Harley Sanders, Rion S - Awakenings (Paul Thomas & Fuenka Remix) - 1A - 124","Lezcano - Isaac (Ariel Lander Remix) - 1A - 124","Highjacks - Void (Extended Mix) - 2A - 124","Matt Fax - Atlas (Extended Mix) - 2A - 124", "Stan Kolev, Aaron Suiss - Fire Spirit (Original Mix) - 3A - 124", "Tryger - Take Me Home (Original Mix) - 3A - 124", "Naz, Deanna Leigh - Underwater (Extended Mix) - 4A - 124", "York - On The Beach (Kryder Extended Remix) - 4A - 124", "Four3Four - Ligature - 5A - 124", "Phi Phi & Manu Riga - Sharp Intellect - 5A - 124", "Einmusik, Lexer - Second Chance - 6A - 124", "Teklix - The Tribal Code - 6A - 124", "Ismael Rivas - Apocalipse (Original Mix) - 7A - 124", "Panoptic, Paul Anthonee - Surface (2021 Rendition) - 7A - 124", "Lateral Cut Groove - Diamonds - 8A - 124", "Spada feat. Richard Judge - Happy If You Are (Extended Mix) - 8A - 124", "Marius Drescher - Rush (Original Mix) - 9A  - 124", "Matt Fax - Torn (Extended Mix) - 9A - 124", "CHABI, Deejay Ox - Progression - 10A - 124", "Perpetual Universe - Deep Breath (Original Mix) - 10A - 124", "Blanka Barbara - Lost in Digital Fog (Original) - 11A - 124", "Sayman - Cuarentena (Extended Mix) - 11A - 124", "Matt Fax, Viiq - Run Away (Extended Club Mix) - 12A - 124", "Max Graham - Moonchild (Tim Penner Remix) - 12A - 124"]
    #current_song = "P1 - Oxia - Domino"
    #current_song = "Harley Sanders, Rion S - Awakenings (Paul Thomas & Fuenka Remix) - 1A - 124"
    # print('Now playing: ', current_song, '\n')

    candidate_song = "Teklix - The Tribal Code - 6A - 124"  # @param ["Harley Sanders, Rion S - Awakenings (Paul Thomas & Fuenka Remix) - 1A - 124","Lezcano - Isaac (Ariel Lander Remix) - 1A - 124","Highjacks - Void (Extended Mix) - 2A - 124","Matt Fax - Atlas (Extended Mix) - 2A - 124", "Stan Kolev, Aaron Suiss - Fire Spirit (Original Mix) - 3A - 124", "Tryger - Take Me Home (Original Mix) - 3A - 124", "Naz, Deanna Leigh - Underwater (Extended Mix) - 4A - 124", "York - On The Beach (Kryder Extended Remix) - 4A - 124", "Four3Four - Ligature - 5A - 124", "Phi Phi & Manu Riga - Sharp Intellect - 5A - 124", "Einmusik, Lexer - Second Chance - 6A - 124", "Teklix - The Tribal Code - 6A - 124", "Ismael Rivas - Apocalipse (Original Mix) - 7A - 124", "Panoptic, Paul Anthonee - Surface (2021 Rendition) - 7A - 124", "Lateral Cut Groove - Diamonds - 8A - 124", "Spada feat. Richard Judge - Happy If You Are (Extended Mix) - 8A - 124", "Marius Drescher - Rush (Original Mix) - 9A  - 124", "Matt Fax - Torn (Extended Mix) - 9A - 124", "CHABI, Deejay Ox - Progression - 10A - 124", "Perpetual Universe - Deep Breath (Original Mix) - 10A - 124", "Blanka Barbara - Lost in Digital Fog (Original) - 11A - 124", "Sayman - Cuarentena (Extended Mix) - 11A - 124", "Matt Fax, Viiq - Run Away (Extended Club Mix) - 12A - 124", "Max Graham - Moonchild (Tim Penner Remix) - 12A - 124"]
    #candidate_song = "P2 - Patrice Baumel - Surge (Original mix)"
    #candidate_song = "Blanka Barbara - Lost in Digital Fog (Original) - 11A - 124"
    #andidate_song = "Sayman - Cuarentena (Extended Mix) - 11A - 124"
    # print('Next playing: ', candidate_song)

    current_song_path = "harmonic_mix/music/" + genre + current_song + ".mp3"
    candidate_song_path = "harmonic_mix/music/" + genre + candidate_song + ".mp3"
    analyze_song(current_song_path)
    analyze_song(candidate_song_path)
    harmonic_compatibility, pitch_shift, min_small_scale_comp = \
        compare_songs(current_song_path, candidate_song_path,1)
    pitch_shift_sign = ""
    if pitch_shift > 0:
        pitch_shift_sign = "+"

    print("Harmonic compatibility: ", round(harmonic_compatibility, 2), "%")
    print("Recommended pitch shift: ", pitch_shift_sign , pitch_shift, "st")
    print("Resulting harmonic compatibility (after pitch shifting): ",
          round(min_small_scale_comp, 2), "%")