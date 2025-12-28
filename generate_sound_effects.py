"""
Sound Effect Generator
効果音生成スクリプト - 3種類のWAVファイルを生成
"""
import numpy as np
import wave
import os

# 音声仕様
SAMPLE_RATE = 44100  # 44.1kHz
OUTPUT_DIR = "assets/sounds"

def apply_envelope(samples, attack_ms, decay_ms):
    """
    エンベロープ（音量変化）を適用

    Args:
        samples: 音声サンプル配列
        attack_ms: アタック時間（ミリ秒）
        decay_ms: ディケイ時間（ミリ秒）
    """
    length = len(samples)
    attack_samples = int(SAMPLE_RATE * attack_ms / 1000)

    envelope = np.ones(length)

    # アタック（フェードイン）
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # ディケイ（フェードアウト）
    decay_samples = int(SAMPLE_RATE * decay_ms / 1000)
    if decay_samples > 0:
        envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)

    return samples * envelope


def generate_decide_sound():
    """
    決定音（SE_DECIDE）を生成
    - 周波数: 880Hz（A5音）
    - 長さ: 0.15秒
    - 波形: サイン波
    - 音量: -6dB（0.5倍振幅）
    """
    duration = 0.15  # 秒
    frequency = 880  # Hz
    amplitude = 0.5  # -6dB

    # サイン波生成
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    samples = amplitude * np.sin(2 * np.pi * frequency * t)

    # エンベロープ適用（アタック5ms、ディケイ145ms）
    samples = apply_envelope(samples, attack_ms=5, decay_ms=145)

    return samples


def generate_battle_sound():
    """
    戦闘音（SE_BATTLE）を生成
    - 周波数: 220Hz → 110Hz 下降スイープ
    - 長さ: 0.3秒
    - 波形: 矩形波（倍音豊富）
    - 音量: -3dB（0.7倍振幅）
    """
    duration = 0.3  # 秒
    start_freq = 220  # Hz
    end_freq = 110  # Hz
    amplitude = 0.7  # -3dB

    # 周波数スイープ
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    freq_sweep = np.linspace(start_freq, end_freq, len(t))

    # 位相計算（周波数が変化する）
    phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE

    # 矩形波生成（サイン波の符号で作成）
    samples = amplitude * np.sign(np.sin(phase))

    # エンベロープ適用（アタック20ms、リリース80ms）
    attack_samples = int(SAMPLE_RATE * 0.02)
    release_samples = int(SAMPLE_RATE * 0.08)

    envelope = np.ones(len(samples))
    # アタック
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    # リリース
    envelope[-release_samples:] = np.linspace(1, 0, release_samples)

    samples = samples * envelope

    return samples


def generate_cancel_sound():
    """
    キャンセル音（SE_CANCEL）を生成
    - 周波数: 440Hz → 330Hz 下降スイープ
    - 長さ: 0.2秒
    - 波形: サイン波
    - 音量: -6dB（0.5倍振幅）
    """
    duration = 0.2  # 秒
    start_freq = 440  # Hz
    end_freq = 330  # Hz
    amplitude = 0.5  # -6dB

    # 周波数スイープ
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    freq_sweep = np.linspace(start_freq, end_freq, len(t))

    # 位相計算
    phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE

    # サイン波生成
    samples = amplitude * np.sin(phase)

    # エンベロープ適用（アタック5ms、ディケイ195ms）
    samples = apply_envelope(samples, attack_ms=5, decay_ms=195)

    return samples


def save_wav(filename, samples):
    """
    WAVファイルとして保存

    Args:
        filename: ファイル名
        samples: 音声サンプル配列（-1.0 ~ 1.0）
    """
    # 出力パス
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 16bit整数に変換
    samples_int16 = np.int16(samples * 32767)

    # WAVファイルに書き込み
    with wave.open(filepath, 'w') as wav_file:
        # パラメータ設定（モノラル、16bit）
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 2 bytes = 16 bits
        wav_file.setframerate(SAMPLE_RATE)

        # サンプル書き込み
        wav_file.writeframes(samples_int16.tobytes())

    print(f"Generated: {filepath}")


def main():
    """
    全効果音を生成
    """
    print("=" * 60)
    print("Sound Effect Generator")
    print("=" * 60)
    print(f"Sample rate: {SAMPLE_RATE}Hz")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # 出力ディレクトリ作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("[1/3] Generating decide.wav...")
    decide_samples = generate_decide_sound()
    save_wav("decide.wav", decide_samples)

    print("[2/3] Generating battle.wav...")
    battle_samples = generate_battle_sound()
    save_wav("battle.wav", battle_samples)

    print("[3/3] Generating cancel.wav...")
    cancel_samples = generate_cancel_sound()
    save_wav("cancel.wav", cancel_samples)

    print()
    print("=" * 60)
    print("Complete!")
    print("=" * 60)
    print()
    print("Generated 3 sound effect files:")
    print("- decide.wav (0.15s, 880Hz)")
    print("- battle.wav (0.3s, 220Hz->110Hz)")
    print("- cancel.wav (0.2s, 440Hz->330Hz)")


if __name__ == "__main__":
    main()
