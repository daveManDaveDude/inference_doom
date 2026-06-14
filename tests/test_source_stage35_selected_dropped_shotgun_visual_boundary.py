import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage35_selected_dropped_shotgun_visual_boundary as stage


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


def collect_stage35_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP35=3" in title and "S35SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage35 final title not reached; saw {titles!r}")


class SourceStage35SelectedDroppedShotgunVisualBoundaryTests(unittest.TestCase):
    def _ref(self) -> stage.Stage35SelectedDroppedShotgunVisualBoundaryReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_selected_dropped_shotgun_visual_boundary_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_selected_drop_spawn_and_world_draw_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_KillMobj_stage35_selected_shotguy_drop_spawn_boundary_debug", labels)
        self.assertIn("P_SpawnMobj_stage35_selected_dropped_shotgun_record_debug", labels)
        self.assertIn("info_stage35_selected_dropped_shotgun_state_debug", labels)
        self.assertIn("R_DrawSpriteRange_stage35_selected_dropped_shotgun_world_post_table_debug", labels)
        self.assertIn("V_DrawBlock_stage35_selected_dropped_shotgun_visual_present_debug", labels)

    def test_synthetic_frame_step_ordering_is_clear_wall_impact_death_drop_psprite_present(self) -> None:
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
                    s.drop_sequence,
                    s.psprite_sequence,
                    s.present_sequence,
                )
                for s in ref.samples
            ],
            [(1, 2, 3, 4, 5, 6, 7), (8, 9, 10, 11, 12, 13, 14), (15, 16, 17, 18, 19, 20, 21)],
        )

    def test_synthetic_selected_p_killmobj_drop_ordering_and_spawn_fields(self) -> None:
        ref = self._ref()
        drop = ref.dropped_record

        self.assertEqual(ref.target_mapthing_index, 37)
        self.assertEqual(ref.target_mobj_index, 28)
        self.assertEqual(ref.selected_kill_events, 1)
        self.assertEqual(ref.selected_death_state_sets, 1)
        self.assertEqual(ref.selected_drop_spawns, 1)
        self.assertEqual((drop.source_type_name, drop.item_type_name), ("MT_SHOTGUY", "MT_SHOTGUN"))
        self.assertEqual((drop.spawn_x, drop.spawn_y), (ref.stage17.final_target.x, ref.stage17.final_target.y))
        self.assertEqual((drop.spawn_z, drop.final_z), (stage.stage13.ONFLOORZ, 0))
        self.assertEqual((drop.spawnstate_name, drop.sprite_name, drop.frame), ("S_SHOT", "SHOT", 0))
        self.assertEqual((drop.radius, drop.height, drop.health), (20 * stage.FRACUNIT, 16 * stage.FRACUNIT, 1000))
        self.assertEqual(drop.spawn_flags, stage.stage13.MF_SPECIAL)

    def test_synthetic_mf_dropped_is_marked_without_pickup_side_effects(self) -> None:
        ref = self._ref()

        self.assertTrue(ref.dropped_record.final_flags & stage.stage13.MF_DROPPED)
        self.assertTrue(ref.dropped_record.final_flags & stage.stage13.MF_SPECIAL)
        self.assertEqual(ref.pickup_absent, 1)
        self.assertEqual(ref.touch_special_absent, 1)
        self.assertEqual(ref.give_weapon_absent, 1)
        self.assertEqual(ref.ammo_weapon_grant_absent, 1)
        self.assertEqual(ref.pickup_message_absent, 1)
        self.assertEqual(ref.item_removal_absent, 1)
        self.assertEqual(ref.respawn_queue_absent, 1)

    def test_synthetic_selected_drop_state_to_render_frame_mapping(self) -> None:
        ref = self._ref()

        self.assertEqual([s.drop_state_name for s in ref.samples], ["NONE", "S_SHOT", "S_SHOT"])
        self.assertEqual([s.drop_sprite_name for s in ref.samples], ["", "SHOT", "SHOT"])
        self.assertEqual([s.drop_patch_name for s in ref.samples], ["", "SHOTA0", "SHOTA0"])
        self.assertEqual([s.drop_frame for s in ref.samples], [0, 0, 0])
        self.assertEqual(ref.distinct_drop_states, 2)

    def test_synthetic_selected_dropped_shotgun_patch_post_command_generation(self) -> None:
        ref = self._ref()

        self.assertEqual([len(s.drop_commands) for s in ref.samples], [0, 44, 44])
        self.assertEqual([s.drop_pixels_drawn for s in ref.samples], [0, 284, 284])
        self.assertEqual(ref.distinct_drop_command_tables, 2)
        for sample in ref.samples[1:]:
            self.assertTrue(all(0 <= command.x < stage.FRAMEBUFFER_WIDTH for command in sample.drop_commands))
            self.assertTrue(all(command.patch_name == "SHOTA0" for command in sample.drop_commands))

    def test_synthetic_runtime_command_table_selection_and_ordering(self) -> None:
        ref = self._ref()

        tables = [
            tuple((command.x, command.yl, command.yh, command.texturemid, command.source_index) for command in sample.drop_commands)
            for sample in ref.samples
        ]
        self.assertEqual(len(set(tables)), 2)
        for sample in ref.samples:
            self.assertLess(sample.death_sequence, sample.drop_sequence)
            self.assertLess(sample.drop_sequence, sample.psprite_sequence)

    def test_synthetic_framebuffer_signatures_prove_selected_drop_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 3270148876)
        self.assertEqual([s.base_framebuffer_signature for s in ref.samples], [2926869513, 622680457, 1677820087])
        self.assertEqual([s.impact_framebuffer_signature for s in ref.samples], [2926869513, 330358001, 1300993588])
        self.assertEqual([s.death_framebuffer_signature for s in ref.samples], [2926869513, 1191322670, 2513680424])
        self.assertEqual([s.drop_framebuffer_signature for s in ref.samples], [2926869513, 3057214504, 3299982258])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2997224612, 1668066382, 4078405109])
        self.assertEqual(ref.drop_contribution_signatures, 2)
        for sample in ref.samples[1:]:
            self.assertNotEqual(sample.death_framebuffer_signature, sample.drop_framebuffer_signature)
            self.assertNotEqual(sample.drop_framebuffer_signature, sample.framebuffer_signature)

    def test_absence_flags_keep_deferred_systems_and_stage36_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage35_selected_dropped_shotgun_visual_boundary_exe()
        lower = image.lower()

        for value in (
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.wall_path_replayed,
            ref.flat_path_replayed,
            ref.death_or_pain_path_replayed,
            ref.drop_path_replayed,
            ref.psprite_path_replayed,
            ref.projectiles_absent,
            ref.explosions_absent,
            ref.monster_attack_execution_absent,
            ref.item_pickup_absent,
            ref.generalized_death_drop_absent,
            ref.generalized_combat_absent,
            ref.broad_ai_absent,
            ref.generalized_sprite_systems_absent,
            ref.generalized_specials_absent,
            ref.map_progression_absent,
            ref.ui_systems_absent,
            ref.real_audio_absent,
            ref.source_stage36_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage36", lower)
        for forbidden in (
            b"p_touchspecialthing implemented",
            b"p_giveweapon implemented",
            b"ammo weapon grant implemented",
            b"pickup message implemented",
            b"item removal implemented",
            b"respawn queue implemented",
            b"generalized item traversal implemented",
            b"projectile spawned",
            b"explosion spawned",
            b"broad ai implemented",
            b"generalized combat implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage35_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage35_selected_dropped_shotgun_visual_boundary_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage35_frame_pixels", image)
        self.assertNotIn(b"stage35_copy_rendered_frame", image)
        self.assertIn(b"Selected impact/death/drop visual log", image)
        self.assertIn(b"NOFULL35=1", image)
        self.assertIn(b"R_DrawMaskedColumn-shaped commands", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)
        command_bytes = sum(
            len(s.impact_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.death_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.drop_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.psprite_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage34.stage33.stage32.stage31.samples[i].wall_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage34.stage33.stage32.stage31.samples[i].flat_spans) * stage.stage31.SPAN_RECORD_SIZE
            for i, s in enumerate(ref.samples)
        )
        self.assertLess(command_bytes, stage.FRAMEBUFFER_BYTES * len(ref.samples) // 8)

    def test_pinned_replay_changes_weapon_impact_death_drop_visual_state(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage34.signature, 4027590938)
        self.assertEqual(ref.stage34.stage33.signature, 1614948054)
        self.assertEqual(ref.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(ref.stage34.stage33.stage32.stage31.signature, 3593583171)
        self.assertGreater(ref.samples[-1].wall_pixels_drawn + ref.samples[-1].flat_pixels_drawn, 50000)
        self.assertGreater(ref.samples[-1].impact_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].death_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].drop_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].psprite_pixels_drawn, 1000)

    def test_preserves_stage34_through_stage19_signatures(self) -> None:
        ref = self._ref()
        stage31_ref = ref.stage34.stage33.stage32.stage31
        stage29_ref = stage31_ref.stage30.stage29
        stage28_ref = stage29_ref.stage28

        self.assertEqual(ref.stage34.signature, 4027590938)
        self.assertEqual(ref.stage34.stage33.signature, 1614948054)
        self.assertEqual(ref.stage34.stage33.stage32.signature, 533488475)
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

    def test_executable_build_contains_stage35_markers_and_no_stage36_strings(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage35_selected_dropped_shotgun_visual_boundary_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage35_selected_dropped_shotgun_visual_boundary", image)
        self.assertIn(b"Selected dropped shotgun visual boundary proof OK", image)
        self.assertIn(b"S35 DROP START STEP35=0", image)
        self.assertIn(b"STEP35=1", image)
        self.assertIn(b"STEP35=2", image)
        self.assertIn(b"STEP35=3", image)
        self.assertIn(f"S35SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S34SIG=4027590938", image)
        self.assertIn(b"S33SIG=1614948054", image)
        self.assertIn(b"S32SIG=533488475", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage36", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage35_frames_drop_counters_and_distinct_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage35_selected_dropped_shotgun_visual_boundary.exe"
        stage.write_source_stage35_selected_dropped_shotgun_visual_boundary_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage35_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"(?:^| )FB35=(\d+)", title)]
                if match
            }

            self.assertIn("S35 DROP START STEP35=0", joined)
            self.assertTrue("STEP35=1" in joined or "STEP35=2" in joined)
            self.assertIn("STEP35=3", joined)
            self.assertEqual(fb_values, {sample.framebuffer_signature for sample in ref.samples})
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertIn("DROP35=S_SHOT", joined)
            self.assertIn("DRPATCH35=SHOTA0", joined)
            self.assertIn("DRC35=44", joined)
            self.assertIn("DRP35=284", joined)
            self.assertIn(f"S35SIG={ref.signature}", joined)
            self.assertIn("S34SIG=4027590938", joined)
            self.assertIn("S19SIG=2088411722", joined)
            self.assertIn("S36ABS=1", joined)
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
