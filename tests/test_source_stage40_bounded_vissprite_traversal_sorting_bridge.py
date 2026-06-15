import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage40_bounded_vissprite_traversal_sorting_bridge as stage


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


def collect_stage40_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP40=3" in title and "S40SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage40 final title not reached; saw {titles!r}")


class SourceStage40BoundedVisspriteTraversalSortingBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage40BoundedVisspriteTraversalSortingBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_bounded_vissprite_traversal_sorting_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_cover_selected_vissprite_pipeline(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("R_AddSprites_stage40_bounded_selected_sector_intake_debug", labels)
        self.assertIn("R_ProjectSprite_stage40_selected_troopshot_bal1_debug", labels)
        self.assertIn("R_SortVisSprites_stage40_bounded_depth_sort_debug", labels)
        self.assertIn("R_DrawMasked_stage40_selected_world_vissprite_posts_debug", labels)
        self.assertIn("info_stage40_selected_bal1_metadata_debug", labels)
        self.assertIn("stage40_vissprite_present_bridge_preserves_stage39_debug", labels)

    def test_synthetic_selected_mobj_and_addsprites_intake_census(self) -> None:
        ref = self._ref()
        self.assertEqual(len(ref.selected_mobjs), 1)
        mobj = ref.selected_mobjs[0]

        self.assertEqual((mobj.type_name, mobj.state_name, mobj.sprite_name), ("MT_TROOPSHOT", "S_TBALL1", "BAL1"))
        self.assertEqual(mobj.frame_letter, "A")
        self.assertEqual((mobj.validcount_guard, mobj.bounded_mobj_count), (1, 1))
        self.assertEqual(ref.bounded_selected_mobj_census, 1)
        self.assertEqual(ref.selected_addsprites_intake, 1)
        self.assertTrue(mobj.source_marker.startswith("R_AddSprites->R_ProjectSprite selected MT_TROOPSHOT"))

    def test_synthetic_projectsprite_xrange_scale_texturemid_and_metadata(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertGreaterEqual(sample.x1, 0)
            self.assertLess(sample.x2, stage.FRAMEBUFFER_WIDTH)
            self.assertLessEqual(sample.x1, sample.x2)
            self.assertLessEqual(sample.raw_x1, sample.x1)
            self.assertGreater(sample.scale, 0)
            self.assertEqual(sample.xiscale, stage.FRACUNIT)
            self.assertEqual(sample.startfrac, 0)
            self.assertGreater(sample.texturemid, 0)
            self.assertGreater(sample.tz, 0)
            self.assertTrue(sample.patch_name.startswith("BAL1"))
            self.assertGreater(sample.patch_width, 0)
            self.assertGreater(sample.patch_height, 0)
            self.assertEqual((sample.intake_count, sample.projected_count), (1, 1))
        self.assertEqual(ref.selected_projectsprite_projection, 1)
        self.assertEqual(ref.selected_sprite_metadata_posts, 1)

    def test_synthetic_sortvis_depth_ordering_and_drawmasked_column_ordering(self) -> None:
        ref = self._ref()
        far = ref.samples[0]
        near = ref.samples[-1]

        sorted_samples = stage.sort_selected_vissprites_source_shape((near, far))
        self.assertEqual(sorted_samples, (far, near))
        for sample in ref.samples:
            self.assertEqual((sample.sorted_count, sample.sort_rank), (1, 0))
            self.assertLess(sample.drop_sequence, sample.world_vissprite_sequence)
            self.assertLess(sample.world_vissprite_sequence, sample.psprite_sequence)
            self.assertLess(sample.psprite_sequence, sample.feedback_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)
        self.assertEqual(ref.selected_sortvis_depth_order, 1)
        self.assertEqual(ref.selected_drawmasked_posts, 1)

    def test_synthetic_bal1_post_data_bounds_and_framebuffer_ownership(self) -> None:
        ref = self._ref()

        self.assertGreater(len(ref.sources), 0)
        self.assertTrue(all(source for source in ref.sources))
        for sample in ref.samples:
            self.assertGreater(len(sample.commands), 0)
            self.assertGreater(sample.columns_drawn, 0)
            self.assertGreater(sample.posts_drawn, 0)
            self.assertGreater(sample.pixels_drawn, 0)
            for command in sample.commands:
                self.assertGreaterEqual(command.x, 0)
                self.assertLess(command.x, stage.FRAMEBUFFER_WIDTH)
                self.assertGreaterEqual(command.yl, 0)
                self.assertLess(command.yh, stage.FRAMEBUFFER_HEIGHT)
                self.assertLessEqual(command.yl, command.yh)
                self.assertLess(command.source_index, len(ref.sources))
                self.assertTrue(command.patch_name.startswith("BAL1"))

    def test_synthetic_projectile_marker_replaced_and_stage39_state_preserved(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe()

        self.assertEqual(ref.projectile_marker_replaced_by_vissprite_posts, 1)
        self.assertEqual(ref.stage39_projectile_state_preserved, 1)
        self.assertEqual(ref.stage39.signature, 3469618451)
        self.assertEqual(ref.stage39.projectile.state_signature, 1403583302)
        self.assertNotIn(b"stage40_draw_projectile_marker", image)
        self.assertIn(b"R_AddSprites->R_ProjectSprite->R_SortVisSprites->R_DrawMasked", image)
        self.assertIn(b"REPL40=1", image)

    def test_synthetic_present_after_final_vissprite_preserves_stage39_behavior(self) -> None:
        ref = self._ref()

        self.assertEqual((ref.timer_samples, ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3, 3))
        self.assertEqual(ref.paint_after_final_vissprite, 1)
        self.assertEqual(ref.stage38_present_preserved, 1)
        self.assertEqual((ref.stage39.invalidate_calls, ref.stage39.update_window_calls, ref.stage39.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.stage39.paint_after_final_projectile_marker, 1)

    def test_synthetic_vissprite_state_signature_and_framebuffer_change(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 2737672056)
        self.assertEqual(ref.state_signature, 268409133)
        self.assertEqual(ref.distinct_vissprite_state_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertGreaterEqual(ref.vissprite_contribution_signatures, 2)
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [3448704092, 2498345585, 3733715286])
        self.assertEqual([s.selected_state_signature for s in ref.samples], [1957020629, 3758004534, 1436017657])

    def test_absence_flags_keep_deferred_systems_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe()
        lower = image.lower()

        for value in (
            ref.no_broad_all_map_sprite_traversal,
            ref.no_generalized_thing_iteration,
            ref.no_generalized_projectile_manager,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.broad_ai_absent,
            ref.broad_combat_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.statusbar_hud_rebuild_absent,
            ref.map_progression_absent,
            ref.ui_systems_absent,
            ref.real_audio_absent,
            ref.source_stage41_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage41", lower)
        for forbidden in (
            b"all-map sprite traversal implemented",
            b"generalized thing iteration implemented",
            b"generalized projectile manager implemented",
            b"explosion spawned",
            b"radius damage implemented",
            b"splash damage implemented",
            b"infighting implemented",
            b"player death implemented",
            b"enemy kill drop implemented",
            b"generalized monster ai implemented",
            b"broad combat implemented",
            b"statusbar hud rebuild implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage40_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertNotIn(b"stage40_frame_pixels", image)
        self.assertNotIn(b"stage40_copy_rendered_frame", image)
        self.assertIn(b"NOFULL40=1", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_pinned_replay_preserves_stage39_through_stage19_signatures_and_paths(self) -> None:
        ref = self._ref()
        s29 = ref.stage39.stage38.stage29
        s36 = ref.stage39.stage38.stage36
        s31 = s36.stage34.stage33.stage32.stage31

        self.assertEqual(ref.stage31_wall_flat_preserved, 1)
        self.assertEqual(ref.stage32_psprite_preserved, 1)
        self.assertEqual(ref.stage33_impact_preserved, 1)
        self.assertEqual(ref.stage34_death_preserved, 1)
        self.assertEqual(ref.stage35_drop_preserved, 1)
        self.assertEqual(ref.stage36_pickup_preserved, 1)
        self.assertEqual(ref.stage37_feedback_preserved, 1)
        self.assertEqual(ref.stage38_present_preserved, 1)
        self.assertEqual(ref.stage39.signature, 3469618451)
        self.assertEqual(ref.stage39.stage38.signature, 2314527789)
        self.assertEqual(stage.stage39.BASELINE_S37_SIGNATURE, 2681905384)
        self.assertEqual(s36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(s36), 3270148876)
        self.assertEqual(s36.stage34.signature, 4027590938)
        self.assertEqual(s36.stage34.stage33.signature, 1614948054)
        self.assertEqual(s36.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(s31.signature, 3593583171)
        self.assertEqual(s31.stage30.signature, 3898523864)
        self.assertEqual(s29.signature, 3738922932)
        self.assertEqual(s29.stage28.signature, 2805406010)
        self.assertEqual(s29.stage28.stage27.signature, 1735738182)
        self.assertEqual(s29.stage28.stage27.stage26.signature, 132405987)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.signature, 1688844032)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_build_output_contains_stage40_markers_and_no_stage41_strings(self) -> None:
        output = REPO_ROOT / "build" / "source_stage40_bounded_vissprite_traversal_sorting_bridge.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        image = stage.build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe()
        output.write_bytes(image)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 100_000)
        self.assertIn(b"source_stage40_bounded_vissprite_traversal_sorting_bridge", image)
        self.assertIn(b"S40SIG=2737672056", image)
        self.assertIn(b"STATE40=268409133", image)
        self.assertIn(b"PATCH40=BAL1", image)
        self.assertIn(b"MISS39=MT_TROOPSHOT", image)
        self.assertIn(b"INV40=3 UPD40=3 PAINT40=3 PAF40=1", image)
        self.assertIn(b"INV39=3 UPD39=3 PAINT39=3 PAF39=1", image)
        self.assertNotIn(b"source_stage41", image.lower())

    @unittest.skipUnless(os.name == "nt", "Win32 GUI smoke test requires Windows")
    def test_smoke_executable_launches_reports_vissprite_samples_and_closes(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        output = REPO_ROOT / "build" / "source_stage40_bounded_vissprite_traversal_sorting_bridge.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(stage.build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe())

        proc = subprocess.Popen([str(output)], cwd=REPO_ROOT)
        try:
            hwnd, titles = collect_stage40_titles(proc.pid)
            final = titles[-1]
            self.assertNotEqual(hwnd, 0)
            self.assertIn("STEP40=3", final)
            self.assertIn("S40SIG=2737672056", final)
            self.assertIn("STATE40=268409133", final)
            self.assertIn("PATCH40=BAL1", final)
            self.assertIn("MISS39=MT_TROOPSHOT", final)
            self.assertIn("PST39=1403583302", final)
            self.assertIn("INV40=3 UPD40=3 PAINT40=3 PAF40=1", final)
            self.assertIn("INV39=3 UPD39=3 PAINT39=3 PAF39=1", final)
            self.assertIn("S41ABS=1", final)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"FB40=(\d+)", title)
            }
            state_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"VSTATE40=(\d+)", title)
            }
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertGreaterEqual(len(state_values), 2)
            time.sleep(0.25)
            self.assertIsNone(proc.poll())
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3.0)
        self.assertIn(proc.returncode, (0, 1))


if __name__ == "__main__":
    unittest.main()
