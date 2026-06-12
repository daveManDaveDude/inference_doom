import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage20_audio_channels_and_deferred_sound_playback as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def window_title_for_pid(
    pid: int, expected: tuple[str, ...] = (), timeout_seconds: float = 5.0
) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds
    last_seen = ""

    while time.monotonic() < deadline:
        found: list[tuple[int, str]] = []

        @enum_proc_type
        def enum_proc(hwnd, _lparam):
            process_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value != pid or not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, len(buffer))
            if buffer.value:
                found.append((int(hwnd), buffer.value))
                return False
            return True

        user32.EnumWindows(enum_proc, 0)
        if found:
            hwnd, title = found[0]
            last_seen = title
            if not expected or all(fragment in title for fragment in expected):
                return hwnd, title
        time.sleep(0.1)

    raise TimeoutError(f"no matching visible window title found for pid {pid}: {last_seen!r}")


def _origin(
    origin_id: int = 7,
    *,
    x: int = 128,
    y: int = 0,
    angle: int = 0,
    kind: str = "synthetic",
) -> stage.Stage20SoundOrigin:
    return stage.Stage20SoundOrigin(origin_id, kind, x * stage.FRACUNIT, y * stage.FRACUNIT, 0, angle)


def _world(listener: stage.Stage20SoundOrigin | None = None) -> stage.Stage20SoundWorld:
    if listener is None:
        listener = _origin(stage.SOUND_ORIGIN_PLAYER_PROBE, x=0, y=0, kind="player_probe")
    return stage.build_empty_stage20_sound_world(listener)


class SourceStage20AudioChannelsDeferredSoundPlaybackTests(unittest.TestCase):
    def test_source_trace_and_parsed_bdopn_metadata_are_source_shaped(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("S_StartSound_bdopn_channel_state_source_shape_debug", labels)
        self.assertIn("S_GetChannel_bounded_channel_source_shape_debug", labels)
        self.assertIn("S_AdjustSoundParams_sector_origin_source_shape_debug", labels)
        self.assertIn("I_StartSound_deferred_stage20_debug", labels)

        enum_names = stage.parse_sfx_enum_source_shape()
        sfx = stage.parse_sfx_table_source_shape()[stage.SFX_BDOPN]
        self.assertEqual(enum_names[stage.SFX_BDOPN], "sfx_bdopn")
        self.assertEqual((sfx.name, sfx.priority, sfx.link_id), ("bdopn", 100, None))
        self.assertEqual((stage.NORM_PRIORITY, stage.NORM_SEP, stage.NORM_PITCH), (64, 128, 127))
        self.assertEqual(stage.parse_m_random_table_source_shape()[1], 8)

    def test_synthetic_s_start_sound_rejects_bogus_and_starts_selected_bdopn(self) -> None:
        bogus = _world()
        self.assertIsNone(stage.s_start_sound_stage20_source_shape(bogus, None, 0))
        self.assertEqual((bogus.counters.sound_start_calls, bogus.counters.bogus_id_rejections), (1, 1))

        world = _world()
        trace = stage.s_start_sound_stage20_source_shape(world, _origin(), stage.SFX_BDOPN)
        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual((trace.sfx_id, trace.sfx_name, trace.sfx_priority), (stage.SFX_BDOPN, "bdopn", 100))
        self.assertEqual((trace.pitch_before, trace.random_value, trace.pitch_after), (127, 8, 135))
        self.assertEqual((trace.usefulness_before, trace.usefulness_after), (-1, 1))
        self.assertEqual((trace.lump_before, trace.lump_after), (-1, 0))
        self.assertEqual((trace.channel_index, world.channels[0].sfx_id, world.channels[0].handle), (0, stage.SFX_BDOPN, 0))
        self.assertEqual((world.counters.lump_lookup_deferrals, world.counters.i_start_sound_deferrals), (1, 1))
        self.assertEqual((world.counters.device_playback_deferrals, world.counters.actual_device_playbacks), (1, 0))

    def test_synthetic_linked_sfx_volume_pitch_handling_uses_original_channel_sfx(self) -> None:
        world = _world()
        trace = stage.s_start_sound_stage20_source_shape(world, None, stage.SFX_CHGUN)

        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual((trace.sfx_id, trace.sfx_name), (stage.SFX_CHGUN, "chgun"))
        self.assertEqual((world.sfx[stage.SFX_CHGUN].link_id, trace.pitch_before), (stage.SFX_PISTOL, 150))
        self.assertEqual((trace.volume_after, trace.random_value, trace.pitch_after), (64, 8, 158))
        self.assertEqual((world.counters.linked_sfx_adjustments, world.channels[0].sfx_id), (1, stage.SFX_CHGUN))

    def test_synthetic_same_origin_stop_before_restart(self) -> None:
        origin = _origin(44)
        world = _world()
        world.sfx[stage.SFX_BDOPN].usefulness = 1
        world.channels[0] = stage.Stage20Channel(
            sfx_id=stage.SFX_BDOPN,
            origin_id=origin.origin_id,
            handle=7,
            pitch=123,
            playing=True,
        )

        trace = stage.s_start_sound_stage20_source_shape(world, origin, stage.SFX_BDOPN)

        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual((world.counters.stop_sound_calls, world.counters.same_origin_stops), (1, 1))
        self.assertEqual((world.counters.stop_channel_calls, world.counters.stop_sound_device_deferrals), (1, 1))
        self.assertEqual((trace.channel_index, trace.usefulness_before, trace.usefulness_after), (0, 0, 1))
        self.assertEqual((world.channels[0].sfx_id, world.channels[0].origin_id, world.channels[0].pitch), (stage.SFX_BDOPN, origin.origin_id, 135))

    def test_synthetic_channel_selection_priority_replacement_and_no_channel_rejection(self) -> None:
        free = _world()
        free_trace = stage.s_start_sound_stage20_source_shape(free, _origin(1), stage.SFX_BDOPN)
        self.assertIsNotNone(free_trace)
        self.assertEqual((free.counters.free_channel_selections, free.channels[0].sfx_id), (1, stage.SFX_BDOPN))

        replace = _world()
        replace.sfx[stage.SFX_BDOPN].usefulness = 8
        for index in range(stage.SND_CHANNELS):
            replace.channels[index] = stage.Stage20Channel(stage.SFX_BDOPN, 100 + index, 0, 135)
        rep_trace = stage.s_start_sound_stage20_source_shape(replace, _origin(2), stage.SFX_PISTOL)
        self.assertIsNotNone(rep_trace)
        assert rep_trace is not None
        self.assertEqual((rep_trace.channel_index, replace.counters.priority_replacements), (0, 1))
        self.assertEqual(replace.channels[0].sfx_id, stage.SFX_PISTOL)

        nochan = _world()
        for index in range(stage.SND_CHANNELS):
            nochan.channels[index] = stage.Stage20Channel(stage.SFX_PISTOL, 200 + index, 0, 135)
        no_trace = stage.s_start_sound_stage20_source_shape(nochan, _origin(3), stage.SFX_BDOPN)
        self.assertIsNone(no_trace)
        self.assertEqual((nochan.counters.no_channel_rejections, nochan.counters.i_start_sound_deferrals), (1, 0))

    def test_synthetic_adjust_sound_params_same_xy_near_far_and_math(self) -> None:
        listener = _origin(stage.SOUND_ORIGIN_PLAYER_PROBE, x=0, y=0, kind="player_probe")

        same_world = _world(listener)
        same = stage.s_start_sound_stage20_source_shape(same_world, _origin(10, x=0, y=0), stage.SFX_BDOPN)
        self.assertIsNotNone(same)
        assert same is not None
        self.assertEqual((same.volume_after, same.separation, same_world.counters.same_xy_sep_overrides), (64, 128, 1))

        near = stage.s_adjust_sound_params_stage20_source_shape(listener, _origin(11, x=100, y=0), 64, 128)
        self.assertTrue(near.audible)
        self.assertEqual((near.volume, near.approx_distance >> stage.FRACBITS), (64, 100))

        far = stage.s_adjust_sound_params_stage20_source_shape(listener, _origin(12, x=1301, y=0), 64, 128)
        self.assertFalse(far.audible)

        north = stage.s_adjust_sound_params_stage20_source_shape(listener, _origin(13, x=0, y=400), 64, 128)
        self.assertTrue(north.audible)
        self.assertEqual((north.volume, north.separation, north.approx_distance >> stage.FRACBITS), (51, 33, 400))

    def test_pinned_map_stage20_reference_mutates_one_bdopn_channel_and_preserves_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_audio_channels_and_deferred_sound_playback_for_pinned_map(PINNED_WAD)
        sound = ref.sound

        self.assertEqual(ref.stage19.signature, 2088411722)
        self.assertEqual(ref.stage19.stage18.signature, 1615679087)
        self.assertEqual(ref.stage19.stage18.stage17.signature, 2157381017)
        self.assertEqual((sound.call_site_line, sound.call_site_sector, sound.call_site_special), (332, 56, 117))
        self.assertEqual((sound.sfx_id, sound.sfx_name, sound.sfx_priority), (stage.SFX_BDOPN, "bdopn", 100))
        self.assertEqual((sound.origin_x >> stage.FRACBITS, sound.origin_y >> stage.FRACBITS), (1832, -160))
        self.assertEqual((sound.listener_x >> stage.FRACBITS, sound.listener_y >> stage.FRACBITS), (1792, -160))
        self.assertEqual((sound.approx_distance >> stage.FRACBITS, sound.volume_after, sound.separation), (40, 64, 129))
        self.assertEqual((sound.pitch_before, sound.random_value, sound.pitch_after), (127, 8, 135))
        self.assertEqual((sound.channel_index, ref.channels[0].sfx_id, ref.channels[0].origin_id), (0, stage.SFX_BDOPN, 1056))
        self.assertEqual((ref.channels[0].pitch, ref.channels[0].handle, ref.channels[0].playing), (135, 0, False))
        self.assertEqual((sound.usefulness_before, sound.usefulness_after, sound.lump_before, sound.lump_after), (-1, 1, -1, 0))
        self.assertEqual((ref.counters.lump_lookup_deferrals, ref.counters.i_start_sound_deferrals), (1, 1))
        self.assertEqual((ref.counters.device_playback_deferrals, ref.counters.actual_device_playbacks), (1, 0))
        self.assertEqual((ref.counters.mixer_absent, ref.counters.music_absent, ref.counters.all_sfx_runtime_absent), (0, 0, 0))
        self.assertEqual(ref.signature, 3226031347)

    def test_executable_build_contains_stage20_status_preserves_stage19_and_omits_later_system_strings(self) -> None:
        image = stage.build_source_stage20_audio_channels_and_deferred_sound_playback_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage20_audio_channels_and_deferred_sound_playback", image)
        self.assertIn(b"Sound channel state proof OK", image)
        self.assertIn(b"S_StartSound", image)
        self.assertIn(b"S_GetChannel", image)
        self.assertIn(b"S_AdjustSoundParams", image)
        self.assertIn(b"bdopn", image)
        self.assertIn(b" S19SIG=", image)
        self.assertIn(b" S20SIG=", image)
        self.assertIn(b" S20ID=", image)
        self.assertIn(b" CH20=", image)
        self.assertNotIn(b"source_stage21", lower)
        for forbidden in (
            b"generalized audio playback",
            b"mixer/device playback",
            b"all sound effects",
            b"broad sound caching",
            b"music",
            b"automap",
            b"menus",
            b"save/load",
            b"networking",
            b"live keyboard input",
            b"generalized specials",
            b"generalized doors",
            b"generalized switches",
            b"generalized sector effects",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage20_sound_channel_state_and_preserved_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_audio_channels_and_deferred_sound_playback_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage20_audio_channels_and_deferred_sound_playback.exe"
        stage.write_source_stage20_audio_channels_and_deferred_sound_playback_exe(exe_path)

        expected = (
            f"S17SIG={ref.stage19.stage18.stage17.signature}",
            f"S18SIG={ref.stage19.stage18.signature}",
            f"S19SIG={ref.stage19.signature}",
            f"S20SIG={ref.signature}",
            f"S20ID={ref.sound.sfx_id}",
            f"S20N={ref.sound.sfx_name}",
            f"CH20={ref.sound.channel_index}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S19LINE=332", title)
            self.assertIn("C191=24", title)
            self.assertIn("S20PRI=100", title)
            self.assertIn("ORG20=56", title)
            self.assertIn("VOL20=64", title)
            self.assertIn("SEP20=129", title)
            self.assertIn("P201=135", title)
            self.assertIn("LDEF20=1", title)
            self.assertIn("IST20=1", title)
            self.assertIn("PLAY20=0", title)
            self.assertIn("MUS20=0", title)
        finally:
            if hwnd:
                import ctypes

                ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
