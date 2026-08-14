import unittest
from unittest.mock import Mock

from obs_scene_visibility import set_source_visibility_global


class FakeObsWebSocket:
    def __init__(self, supports_canvases=True):
        self.supports_canvases = supports_canvases
        self.calls = []
        self.scenes = {
            "main-canvas": [
                {"sceneName": "Horizontal", "sceneUuid": "horizontal-scene"},
                {"sceneName": "Detection", "sceneUuid": "detection-scene"},
            ],
            "vertical-canvas": [
                {"sceneName": "Vertical", "sceneUuid": "vertical-scene"},
            ],
            None: [
                {"sceneName": "Horizontal", "sceneUuid": "horizontal-scene"},
            ],
        }
        self.items = {
            "horizontal-scene": [{"sourceName": "Face Camera", "sceneItemId": 1}],
            "detection-scene": [{"sourceName": "Face Camera", "sceneItemId": 2}],
            "vertical-scene": [{"sourceName": "Face Camera", "sceneItemId": 3}],
        }

    def call(self, request):
        request_name = request.name
        request_data = request.data()
        self.calls.append((request_name, request_data))

        if request_name == "GetCanvasList":
            if not self.supports_canvases:
                raise RuntimeError("GetCanvasList is unavailable")
            response_data = {
                "canvases": [
                    {"canvasName": "Main", "canvasUuid": "main-canvas"},
                    {"canvasName": "Aitum Vertical", "canvasUuid": "vertical-canvas"},
                ]
            }
        elif request_name == "GetSceneList":
            response_data = {"scenes": self.scenes[request_data.get("canvasUuid")]}
        elif request_name == "GetSceneItemList":
            response_data = {"sceneItems": self.items[request_data["sceneUuid"]]}
        elif request_name == "SetSceneItemEnabled":
            response_data = {}
        else:
            raise AssertionError(f"Unexpected OBS request: {request_name}")

        request.input(response_data, True)
        return request


class SetSourceVisibilityGlobalTests(unittest.TestCase):
    def test_updates_all_canvases_except_detection_scene(self):
        obs_ws = FakeObsWebSocket()

        result = set_source_visibility_global(
            obs_ws,
            "Face Camera",
            False,
            Mock(),
            exclude_scenes=["Detection"],
        )

        self.assertTrue(result)
        updates = [data for name, data in obs_ws.calls if name == "SetSceneItemEnabled"]
        self.assertEqual(
            {update["sceneUuid"] for update in updates},
            {"horizontal-scene", "vertical-scene"},
        )
        self.assertTrue(all(update["sceneItemEnabled"] is False for update in updates))

    def test_falls_back_to_main_canvas(self):
        obs_ws = FakeObsWebSocket(supports_canvases=False)

        result = set_source_visibility_global(
            obs_ws,
            "Face Camera",
            True,
            Mock(),
        )

        self.assertTrue(result)
        scene_list_calls = [data for name, data in obs_ws.calls if name == "GetSceneList"]
        self.assertEqual(scene_list_calls, [{}])


if __name__ == "__main__":
    unittest.main()