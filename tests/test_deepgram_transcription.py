from content_automation.deepgram_transcription import extract_deepgram_words


def test_extract_deepgram_words_from_channel_alternative():
    payload = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "words": [
                                {"word": "profit", "punctuated_word": "Profit,", "start": 1.2, "end": 1.5},
                                {"word": "", "start": 1.5, "end": 1.6},
                                {"word": "margin", "start": "2.0", "end": "2.4"},
                            ]
                        }
                    ]
                }
            ]
        }
    }

    words = extract_deepgram_words(payload)

    assert words == [
        {"word": "profit", "punctuated_word": "Profit,", "text": "Profit,", "start": 1.2, "end": 1.5},
        {"word": "margin", "punctuated_word": "margin", "text": "margin", "start": 2.0, "end": 2.4},
    ]
