from content_automation.elevenlabs_errors import explain_elevenlabs_error, missing_audio_file_message


RAW_MISSING_PERMISSION = (
    "Error executing tool text_to_speech: headers: {'date': 'Wed, 17 Jun 2026 14:25:50 GMT'}, "
    "status_code: 401, body: {'detail': {'status': 'missing_permissions', "
    "'message': 'The API key you used is missing the permission voices_read to execute this operation.'}}"
)


def test_explain_elevenlabs_missing_voices_permission_is_actionable():
    message = explain_elevenlabs_error(RAW_MISSING_PERMISSION)

    assert "voices_read" in message
    assert "headers" not in message
    assert "Coolify" in message


def test_missing_audio_file_message_keeps_user_context():
    message = missing_audio_file_message("6079284305", RAW_MISSING_PERMISSION)

    assert "6079284305" in message
    assert "ElevenLabs не вернул audio file" in message
    assert "обнови ELEVENLABS_API_KEY" in message
