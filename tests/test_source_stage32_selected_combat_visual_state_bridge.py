import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage32_selected_combat_visual_state_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def window_title_for_pid(pid: int, timeout_seconds: float = 5.0) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds

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
            return found[0]
        time.sleep(0.05)

    raise TimeoutError(f"no visible window title found for pid {pid}")


def collect_stage32_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP32=3" in title and "S32SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage32 final title not reached; saw {titles!r}")


class SourceStage32SelectedCombatVisualStateBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage32SelectedCombatVisualStateReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_selected_combat_visual_state_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_selected_psprite_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_SetPsprite_stage32_selected_shotgun_psprite_state_debug", labels)
        self.assertIn("R_DrawPSprite_stage32_selected_weapon_post_table_debug", labels)
        self.assertIn("V_DrawBlock_stage32_selected_combat_visual_present_debug", labels)

    def test_synthetic_frame_step_ordering_is_start_samples_final(self) -> None:
        ref = self._ref()

        self.assertEqual([sample.step for sample in ref.samples], [1, 2, 3])
        self.assertEqual([sample.tic for sample in ref.samples], [0, 4, 7])
        self.assertEqual(
            [(s.clear_sequence, s.wall_flat_sequence, s.psprite_sequence, s.present_sequence) for s in ref.samples],
            [(1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12)],
        )
        titles = stage._stage32_replay_titles(ref)
        self.assertIn("STEP32=1", titles[0])
        self.assertIn("STEP32=3", titles[-1])
        self.assertIn("S32SIG=", titles[-1])

    def test_synthetic_selected_state_to_render_frame_mapping(self) -> None:
        ref = self._ref()

        self.assertEqual([s.psprite_state_name for s in ref.samples], ["S_SGUN", "S_SGUN3", "S_SGUN4"])
        self.assertEqual([s.psprite_sprite_name for s in ref.samples], ["SHTG", "SHTG", "SHTG"])
        self.assertEqual([s.psprite_patch_name for s in ref.samples], ["SHTGA0", "SHTGB0", "SHTGC0"])
        self.assertEqual([s.psprite_frame for s in ref.samples], [0, 1, 2])
        self.assertEqual(ref.distinct_visual_states, 3)

    def test_synthetic_selected_patch_post_command_generation(self) -> None:
        ref = self._ref()

        self.assertEqual([len(s.psprite_commands) for s in ref.samples], [66, 96, 135])
        self.assertEqual([s.psprite_pixels_drawn for s in ref.samples], [2083, 5906, 7493])
        for sample in ref.samples:
            self.assertGreater(len(sample.psprite_commands), 0)
            self.assertGreater(sample.psprite_pixels_drawn, 0)
            self.assertTrue(all(0 <= command.x < stage.FRAMEBUFFER_WIDTH for command in sample.psprite_commands))
            self.assertTrue(all(command.patch_name == sample.psprite_patch_name for command in sample.psprite_commands))

    def test_synthetic_runtime_command_table_selection_changes_psprite_tables(self) -> None:
        ref = self._ref()

        first_posts = [
            tuple((command.x, command.yl, command.yh, command.texturemid) for command in sample.psprite_commands[:16])
            for sample in ref.samples
        ]
        self.assertEqual(ref.distinct_psprite_command_tables, 3)
        self.assertEqual(len(set(first_posts)), 3)

    def test_synthetic_framebuffer_clear_wall_flat_psprite_present_ordering(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertLess(sample.clear_sequence, sample.wall_flat_sequence)
            self.assertLess(sample.wall_flat_sequence, sample.psprite_sequence)
            self.assertLess(sample.psprite_sequence, sample.present_sequence)
            self.assertGreater(sample.wall_pixels_drawn, 0)
            self.assertGreater(sample.flat_pixels_drawn, 0)
            self.assertGreater(sample.psprite_pixels_drawn, 0)

    def test_synthetic_distinct_framebuffer_signatures_include_psprite_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 533488475)
        self.assertEqual([s.base_framebuffer_signature for s in ref.samples], [2926869513, 622680457, 1677820087])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2997224612, 3655441960, 2243530028])
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.sprite_contribution_signatures, 3)
        for sample in ref.samples:
            self.assertNotEqual(sample.base_framebuffer_signature, sample.framebuffer_signature)

    def test_absence_flags_keep_deferred_systems_and_stage33_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage32_selected_combat_visual_state_bridge_exe()
        lower = image.lower()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertEqual(ref.wall_path_replayed, 1)
        self.assertEqual(ref.flat_path_replayed, 1)
        self.assertEqual(ref.psprite_path_replayed, 1)
        self.assertEqual(ref.projectiles_absent, 1)
        self.assertEqual(ref.explosions_absent, 1)
        self.assertEqual(ref.monster_attack_execution_absent, 1)
        self.assertEqual(ref.damage_death_drop_absent, 1)
        self.assertEqual(ref.generalized_combat_absent, 1)
        self.assertEqual(ref.broad_ai_absent, 1)
        self.assertEqual(ref.generalized_sprite_systems_absent, 1)
        self.assertEqual(ref.generalized_specials_absent, 1)
        self.assertEqual(ref.map_progression_absent, 1)
        self.assertEqual(ref.ui_systems_absent, 1)
        self.assertEqual(ref.real_audio_absent, 1)
        self.assertEqual(ref.source_stage33_absent, 1)
        self.assertNotIn(b"source_stage33", lower)
        for forbidden in (
            b"projectile spawned",
            b"explosion spawned",
            b"monster attack executed",
            b"damage death drop implemented",
            b"generalized combat implemented",
            b"broad ai implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage32_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage32_selected_combat_visual_state_bridge_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage32_frame_pixels", image)
        self.assertNotIn(b"stage32_copy_rendered_frame", image)
        self.assertIn(b"Selected psprite frame log", image)
        self.assertIn(b"NOFULL32=1", image)
        self.assertIn(b"R_DrawColumn-shaped post commands", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)
        command_bytes = sum(
            len(s.psprite_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage31.samples[i].wall_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage31.samples[i].flat_spans) * stage.SPAN_RECORD_SIZE
            for i, s in enumerate(ref.samples)
        )
        self.assertLess(command_bytes, stage.FRAMEBUFFER_BYTES * len(ref.samples) // 8)

    def test_pinned_replay_changes_visual_state_and_runtime_renderer_pixels(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage31.signature, 3593583171)
        self.assertEqual(ref.stage31.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.distinct_visual_states, 3)
        self.assertEqual(ref.distinct_psprite_command_tables, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertGreaterEqual(len({sample.framebuffer_signature for sample in ref.samples}), 2)
        self.assertGreater(ref.samples[-1].wall_pixels_drawn + ref.samples[-1].flat_pixels_drawn, 50000)
        self.assertGreater(ref.samples[-1].psprite_pixels_drawn, 1000)

    def test_preserves_stage31_through_stage19_signatures(self) -> None:
        ref = self._ref()
        stage31_ref = ref.stage31
        stage29_ref = stage31_ref.stage30.stage29
        stage28_ref = stage29_ref.stage28

        self.assertEqual(stage31_ref.signature, 3593583171)
        self.assertEqual(stage31_ref.stage30.signature, 3898523864)
        self.assertEqual(stage29_ref.signature, 3738922932)
        self.assertEqual(stage28_ref.signature, 2805406010)
        self.assertEqual(stage28_ref.stage27.signature, 1735738182)
        self.assertEqual(stage28_ref.stage27.stage26.signature, 132405987)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.signature, 1688844032)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_executable_build_contains_stage32_markers_and_no_stage33_strings(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage32_selected_combat_visual_state_bridge_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage32_selected_combat_visual_state_bridge", image)
        self.assertIn(b"Selected combat visual state bridge proof OK", image)
        self.assertIn(b"S32 PSVIS START STEP32=0", image)
        self.assertIn(b"STEP32=1", image)
        self.assertIn(b"STEP32=2", image)
        self.assertIn(b"STEP32=3", image)
        self.assertIn(f"S32SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S31SIG=3593583171", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage33", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage32_frames_and_distinct_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage32_selected_combat_visual_state_bridge.exe"
        stage.write_source_stage32_selected_combat_visual_state_bridge_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage32_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"(?:^| )FB32=(\d+)", title)]
                if match
            }

            self.assertIn("S32 PSVIS START STEP32=0", joined)
            self.assertIn("STEP32=1", joined)
            self.assertIn("STEP32=2", joined)
            self.assertIn("STEP32=3", joined)
            self.assertEqual(fb_values, {sample.framebuffer_signature for sample in ref.samples})
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertIn(f"FBDIST32={ref.distinct_framebuffer_signatures}", joined)
            self.assertIn("PSDIST32=3", joined)
            self.assertIn("NOFULL32=1", joined)
            self.assertIn(f"S32SIG={ref.signature}", joined)
            self.assertIn("S31SIG=3593583171", joined)
            for stage_num, signature in (
                (30, 3898523864),
                (29, 3738922932),
                (28, 2805406010),
                (27, 1735738182),
                (26, 132405987),
                (25, 1688844032),
                (24, 1919312263),
                (23, 3216085132),
                (22, 2207028069),
                (21, 1770773845),
                (20, 3226031347),
                (19, 2088411722),
            ):
                self.assertIn(f"S{stage_num}SIG={signature}", joined)
            self.assertIn("S33ABS=1", joined)
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
