from __future__ import annotations


def explain_elevenlabs_error(raw_message: str) -> str:
    message = " ".join(str(raw_message or "").split())
    lowered = message.lower()

    if "missing_permissions" in lowered and "voices_read" in lowered:
        return (
            "ElevenLabs API key не имеет права voices_read. "
            "Создай или обнови ключ ElevenLabs с доступом Voices: Read и Text to Speech, "
            "затем обнови ELEVENLABS_API_KEY в Coolify и перезапусти приложение."
        )

    if "status_code" in lowered and "401" in lowered:
        return (
            "ElevenLabs отклонил API key (401). "
            "Проверь ELEVENLABS_API_KEY в Coolify: ключ должен быть активным и иметь права на генерацию речи."
        )

    if message.startswith("Error executing tool text_to_speech:"):
        return "ElevenLabs text_to_speech завершился ошибкой. Проверь API key, выбранный голос и права ключа."

    return message


def missing_audio_file_message(user_id: str, raw_message: str) -> str:
    return f"ElevenLabs не вернул audio file для пользователя {user_id}: {explain_elevenlabs_error(raw_message)}"
