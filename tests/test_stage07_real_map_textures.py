import unittest

from tools import emit_stage07_real_map_view as stage07


class Stage07RealMapTextureTests(unittest.TestCase):
    def test_placeholder_wall_texture_atlas_has_expected_shape(self) -> None:
        atlas = stage07.PLACEHOLDER_WALL_TEXTURES

        self.assertEqual(len(atlas), stage07.WALL_TEXTURE_ATLAS_BYTES)
        first_texture = atlas[: stage07.WALL_TEXTURE_BYTES]
        first_pixels = {
            first_texture[index : index + 4]
            for index in range(0, len(first_texture), 4)
        }
        self.assertGreater(len(first_pixels), 3)

    def test_stage07_executable_builds_with_embedded_texture_atlas(self) -> None:
        image = stage07.build_stage07_real_map_view_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(stage07.PLACEHOLDER_WALL_TEXTURES[:1024], image)


if __name__ == "__main__":
    unittest.main()
