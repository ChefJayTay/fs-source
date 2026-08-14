"""Canvas-aware OBS scene item visibility helpers."""

from obswebsocket import requests as obs_requests


def _get_canvases(obs_ws, logger):
    try:
        canvases = obs_ws.call(obs_requests.GetCanvasList()).getCanvases()
        if canvases:
            return canvases
    except Exception as error:
        logger.debug(f"OBS canvas API unavailable; using main canvas only: {error}")

    return [{"canvasName": "Main", "canvasUuid": None}]


def set_source_visibility_global(
    obs_ws,
    source_name,
    visible,
    logger,
    exclude_scenes=None,
):
    """Set a source's visibility in every scene on every OBS canvas."""
    if not obs_ws:
        return False
    if not source_name:
        logger.warning("Source name not configured")
        return False

    excluded = set(exclude_scenes or [])
    changes_made = 0

    for canvas in _get_canvases(obs_ws, logger):
        canvas_uuid = canvas.get("canvasUuid")
        canvas_name = canvas.get("canvasName", "unknown")
        canvas_request = {"canvasUuid": canvas_uuid} if canvas_uuid else {}

        try:
            scenes = obs_ws.call(
                obs_requests.GetSceneList(**canvas_request)
            ).getScenes()
        except Exception as error:
            logger.debug(f"Could not list scenes on canvas '{canvas_name}': {error}")
            continue

        for scene in scenes:
            scene_name = scene["sceneName"]
            if scene_name in excluded:
                logger.debug(f"Skipping excluded scene: {scene_name}")
                continue

            scene_request = {"sceneUuid": scene.get("sceneUuid")}
            if not scene_request["sceneUuid"]:
                scene_request = {"sceneName": scene_name, **canvas_request}

            try:
                scene_items = obs_ws.call(
                    obs_requests.GetSceneItemList(**scene_request)
                ).getSceneItems()

                for item in scene_items:
                    if item["sourceName"] != source_name:
                        continue

                    obs_ws.call(obs_requests.SetSceneItemEnabled(
                        **scene_request,
                        sceneItemId=item["sceneItemId"],
                        sceneItemEnabled=visible,
                    ))
                    changes_made += 1
                    logger.debug(
                        f"Set {source_name} to {visible} in '{scene_name}' "
                        f"on canvas '{canvas_name}'"
                    )
            except Exception as error:
                logger.debug(
                    f"Could not modify {source_name} in scene '{scene_name}' "
                    f"on canvas '{canvas_name}': {error}"
                )

    if changes_made:
        action = "shown" if visible else "hidden"
        excluded_note = f" (excluded: {', '.join(sorted(excluded))})" if excluded else ""
        logger.info(
            f"{source_name} {action} in {changes_made} scene item(s) "
            f"across all canvases{excluded_note}"
        )
        return True

    logger.warning(f"Source '{source_name}' not found in any scene on any canvas")
    return False