from the_kit.io import nidaqmx_io


def test_square_wave_length():
    wave = nidaqmx_io.generate_1way_square_wave(
        frequency=0.278, duration=3.6, amplitude=1.2, sampling_rate=400
    )
    assert len(wave) == int(400 * 3.6)


def test_direction_channels():
    wave = [1.0, 0.0, 1.0]
    ch0, ch1 = nidaqmx_io._direction_channels(wave, "LATD")
    assert ch0[0] == -1.0
    assert ch1[0] == 1.0


def test_dry_run_stim():
    nidaqmx_io.init_from_config({"enabled": True, "simulation_mode": True}, dry_run=True)
    meta = nidaqmx_io.send_square_wave_stim(
        direction="AP", amplitude=0.8, duration_s=0.01, dry_run=True
    )
    assert meta["direction"] == "AP"
    nidaqmx_io.shutdown()


def test_preset_valid():
    from pathlib import Path

    from the_kit.protocol.loader import load_protocol
    from the_kit.protocol.validator import validate_protocol

    root = Path(__file__).resolve().parents[1]
    p = load_protocol(root / "examples" / "presets" / "ni_stim_alba_demo.json")
    validate_protocol(p)
    assert p.nodes[1].type == "ni_stim"
