from gopilot.gopro.commands import CameraAction, Hero7Endpoint, endpoint_for_command


def test_command_endpoint_mapping_start_stop_to_shutter():
    assert endpoint_for_command(CameraAction.START) == Hero7Endpoint.COMMAND_SHUTTER
    assert endpoint_for_command(CameraAction.STOP) == Hero7Endpoint.COMMAND_SHUTTER


def test_command_endpoint_mapping_none_to_mode():
    assert endpoint_for_command(CameraAction.NONE) == Hero7Endpoint.COMMAND_MODE
