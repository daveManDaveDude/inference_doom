import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage34_selected_hitscan_death_visual_boundary as stage


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
            return True

        user32.EnumWindows(enum_proc_type(enum_proc), 0)
        if found:
            return found[0]
        time.sleep(0.05)
    return 0, ""


def collect_stage34_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP34=3" in title and "S34SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage34 final title not reached; saw {titles!r}")


class SourceStage34SelectedHitscanDeathVisualBoundaryTests(unittest.TestCase):
    def _ref(self) -> stage.Stage34SelectedHitscanDeathVisualBoundaryReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_selected_hitscan_death_visual_boundary_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_selected_lethal_death_and_world_draw_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("A_FireShotgun_stage34_selected_lethal_replay_setup_debug", labels)
        self.assertIn("P_LineAttack_stage34_selected_hitscan_lethal_boundary_debug", labels)
        self.assertIn("P_DamageMobj_P_KillMobj_stage34_selected_death_state_visual_boundary_debug", labels)
        self.assertIn("P_SetMobjState_stage34_selected_shotguy_death_route_debug", labels)
        self.assertIn("R_DrawSpriteRange_stage34_selected_death_world_post_table_debug", labels)
        self.assertIn("V_DrawBlock_stage34_selected_hitscan_death_visual_present_debug", labels)

    def test_synthetic_frame_step_ordering_is_clear_wall_impact_death_psprite_present(self) -> None:
        ref = self._ref()

        self.assertEqual([sample.step for sample in ref.samples], [1, 2, 3])
        self.assertEqual([sample.tic for sample in ref.samples], [0, 4, 7])
        self.assertEqual(
            [
                (
                    s.clear_sequence,
                    s.wall_flat_sequence,
                    s.impact_sequence,
                    s.death_sequence,
                    s.psprite_sequence,
                    s.present_sequence,
                )
                for s in ref.samples
            ],
            [(1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12), (13, 14, 15, 16, 17, 18)],
        )
        titles = stage._stage34_replay_titles(ref)
        self.assertIn("STEP34=1", titles[0])
        self.assertIn("STEP34=3", titles[-1])
        self.assertIn("S34SIG=", titles[-1])

    def test_synthetic_selected_lethal_damage_ordering_and_state_mapping(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.target_mapthing_index, 37)
        self.assertEqual(ref.target_mobj_index, 28)
        self.assertEqual(ref.selected_nonlethal_damage, 10)
        self.assertEqual(ref.selected_target_health_before_lethal, 20)
        self.assertEqual(ref.selected_lethal_damage, 20)
        self.assertEqual(ref.selected_damage_total, 30)
        self.assertEqual(ref.selected_target_health_after, 0)
        self.assertEqual(ref.selected_kill_events, 1)
        self.assertEqual(ref.selected_death_state_sets, 1)
        self.assertEqual(ref.selected_drop_deferred, 1)
        self.assertTrue(ref.selected_corpse_flags & stage.stage13.MF_CORPSE)
        self.assertTrue(ref.selected_corpse_flags & stage.stage13.MF_DROPOFF)
        self.assertFalse(ref.selected_corpse_flags & stage.stage13.MF_SHOOTABLE)
        self.assertEqual([s.psprite_state_name for s in ref.samples], ["S_SGUN", "S_SGUN3", "S_SGUN4"])
        self.assertEqual([s.impact_state_name for s in ref.samples], ["NONE", "S_SPOS_PAIN", "S_SPOS_PAIN2"])
        self.assertEqual([s.death_state_name for s in ref.samples], ["NONE", "S_SPOS_DIE1", "S_SPOS_DIE2"])
        self.assertEqual([s.death_patch_name for s in ref.samples], ["", "SPOSH0", "SPOSI0"])
        self.assertEqual([s.death_frame for s in ref.samples], [0, 7, 8])

    def test_synthetic_selected_death_patch_post_command_generation(self) -> None:
        ref = self._ref()

        self.assertEqual([len(s.death_commands) for s in ref.samples], [0, 79, 91])
        self.assertEqual([s.death_pixels_drawn for s in ref.samples], [0, 1075, 1013])
        self.assertEqual(ref.distinct_death_command_tables, 3)
        for sample in ref.samples[1:]:
            self.assertGreater(len(sample.death_commands), 0)
            self.assertGreater(sample.death_pixels_drawn, 0)
            self.assertTrue(all(0 <= command.x < stage.FRAMEBUFFER_WIDTH for command in sample.death_commands))
            self.assertTrue(all(command.patch_name == sample.death_patch_name for command in sample.death_commands))

    def test_synthetic_runtime_command_table_selection_changes_death_tables(self) -> None:
        ref = self._ref()

        tables = [
            tuple((command.x, command.yl, command.yh, command.texturemid, command.source_index) for command in sample.death_commands)
            for sample in ref.samples
        ]
        self.assertEqual(len(set(tables)), 3)
        self.assertNotEqual(tables[1], tables[2])

    def test_synthetic_framebuffer_signatures_prove_selected_death_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 4027590938)
        self.assertEqual([s.base_framebuffer_signature for s in ref.samples], [2926869513, 622680457, 1677820087])
        self.assertEqual([s.impact_framebuffer_signature for s in ref.samples], [2926869513, 330358001, 1300993588])
        self.assertEqual([s.death_framebuffer_signature for s in ref.samples], [2926869513, 1191322670, 2513680424])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2997224612, 2851578387, 1194192847])
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.impact_contribution_signatures, 2)
        self.assertEqual(ref.death_contribution_signatures, 2)
        self.assertEqual(ref.psprite_contribution_signatures, 3)
        for sample in ref.samples[1:]:
            self.assertNotEqual(sample.impact_framebuffer_signature, sample.death_framebuffer_signature)
            self.assertNotEqual(sample.death_framebuffer_signature, sample.framebuffer_signature)

    def test_absence_flags_keep_deferred_systems_and_stage35_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage34_selected_hitscan_death_visual_boundary_exe()
        lower = image.lower()

        for value in (
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.wall_path_replayed,
            ref.flat_path_replayed,
            ref.death_or_pain_path_replayed,
            ref.psprite_path_replayed,
            ref.blood_puff_spawn_deferred,
            ref.projectiles_absent,
            ref.explosions_absent,
            ref.monster_attack_execution_absent,
            ref.item_pickup_absent,
            ref.generalized_death_drop_absent,
            ref.selected_drop_visual_deferred,
            ref.generalized_combat_absent,
            ref.broad_ai_absent,
            ref.generalized_sprite_systems_absent,
            ref.generalized_specials_absent,
            ref.map_progression_absent,
            ref.ui_systems_absent,
            ref.real_audio_absent,
            ref.source_stage35_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage35", lower)
        for forbidden in (
            b"item pickup implemented",
            b"projectile spawned",
            b"explosion spawned",
            b"monster attack executed",
            b"generalized death/drop implemented",
            b"generalized combat implemented",
            b"broad ai implemented",
            b"generalized sprite systems implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage34_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage34_selected_hitscan_death_visual_boundary_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage34_frame_pixels", image)
        self.assertNotIn(b"stage34_copy_rendered_frame", image)
        self.assertIn(b"Selected impact/death visual log", image)
        self.assertIn(b"NOFULL34=1", image)
        self.assertIn(b"R_DrawMaskedColumn-shaped commands", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)
        command_bytes = sum(
            len(s.impact_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.death_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.psprite_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage33.stage32.stage31.samples[i].wall_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage33.stage32.stage31.samples[i].flat_spans) * stage.stage31.SPAN_RECORD_SIZE
            for i, s in enumerate(ref.samples)
        )
        self.assertLess(command_bytes, stage.FRAMEBUFFER_BYTES * len(ref.samples) // 8)

    def test_pinned_replay_changes_weapon_impact_death_visual_state(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage33.signature, 1614948054)
        self.assertEqual(ref.stage33.stage32.signature, 533488475)
        self.assertEqual(ref.stage33.stage32.stage31.signature, 3593583171)
        self.assertEqual(ref.distinct_death_states, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertGreaterEqual(len({sample.framebuffer_signature for sample in ref.samples}), 2)
        self.assertGreater(ref.samples[-1].wall_pixels_drawn + ref.samples[-1].flat_pixels_drawn, 50000)
        self.assertGreater(ref.samples[-1].impact_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].death_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].psprite_pixels_drawn, 1000)

    def test_preserves_stage33_through_stage19_signatures(self) -> None:
        ref = self._ref()
        stage31_ref = ref.stage33.stage32.stage31
        stage29_ref = stage31_ref.stage30.stage29
        stage28_ref = stage29_ref.stage28

        self.assertEqual(ref.stage33.signature, 1614948054)
        self.assertEqual(ref.stage33.stage32.signature, 533488475)
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

    def test_executable_build_contains_stage34_markers_and_no_stage35_strings(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage34_selected_hitscan_death_visual_boundary_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage34_selected_hitscan_death_visual_boundary", image)
        self.assertIn(b"Selected hitscan death visual boundary proof OK", image)
        self.assertIn(b"S34 DEATH START STEP34=0", image)
        self.assertIn(b"STEP34=1", image)
        self.assertIn(b"STEP34=2", image)
        self.assertIn(b"STEP34=3", image)
        self.assertIn(f"S34SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S33SIG=1614948054", image)
        self.assertIn(b"S32SIG=533488475", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage35", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage34_frames_and_distinct_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage34_selected_hitscan_death_visual_boundary.exe"
        stage.write_source_stage34_selected_hitscan_death_visual_boundary_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage34_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"(?:^| )FB34=(\d+)", title)]
                if match
            }

            self.assertIn("S34 DEATH START STEP34=0", joined)
            self.assertIn("STEP34=1", joined)
            self.assertIn("STEP34=2", joined)
            self.assertIn("STEP34=3", joined)
            self.assertEqual(fb_values, {sample.framebuffer_signature for sample in ref.samples})
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertIn(f"FBDIST34={ref.distinct_framebuffer_signatures}", joined)
            self.assertIn("DEATHDIST34=3", joined)
            self.assertIn("NOFULL34=1", joined)
            self.assertIn(f"S34SIG={ref.signature}", joined)
            self.assertIn("S33SIG=1614948054", joined)
            self.assertIn("S32SIG=533488475", joined)
            self.assertIn("S31SIG=3593583171", joined)
            self.assertIn("S19SIG=2088411722", joined)
            self.assertIn("S35ABS=1", joined)
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
