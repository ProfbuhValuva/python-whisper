# coding: utf8

import pathlib
import subprocess

import replicate
from flask import Flask, request, jsonify
from revChatGPT.V3 import Chatbot

app = Flask(__name__)

final_filename = None
SYSTEM_PROMPT = "You are a friendly assistant. You will be provided with a transcription of YouTube video with " \
                "timecodes. You must " \
                "sequentially summarize information as you are a lecturer and write timecodes for each logical " \
                "phrase. In the end of each logical phrase in answer you must write a range of time in format " \
                "'hh:mm:ss' where 'hh' is hours in 24 format, 'mm' is minutes and 'ss' is seconds and the example " \
                "is: '00:05:12-00:12:30'. Each logical phrase with timecodes' range must be at least 20 seconds, " \
                "they can't be less than 20 seconds. You must analyze text and write articles with timecodes. " \
                "You always answer in Russian language."
chatbot = Chatbot(api_key="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", max_tokens=16000,
                  system_prompt=SYSTEM_PROMPT,
                  engine="gpt-3.5-turbo-16k-0613", temperature=1.0)


@app.route('/youtube', methods=['POST'])
def youtube_downloader():
    data = request.json
    url = data.get('content')
    name = data.get('id')
    subprocess.run(["yt-dlp", "-f best", "-o" + name + ".%(ext)s", "-x", "--audio-format=mp3", url])
    final_filename = str(pathlib.Path().resolve()) + "\\" + name + ".mp3"
    print(final_filename)
    output = replicate.Client(api_token="r8_8zKG1PCUCD6vdnyrrNfRh1xoYw05lEQ1Dz00F").run(
        "openai/whisper:91ee9c0c3df30478510ff8c8a3a545add1ad0259ad3a9f78fba57fbc05ee64f7",
        input={"audio": open(final_filename, "rb")}
    )
    print(output)
    return jsonify(output)


@app.route('/chatgpt', methods=['POST'])
def chatgpt_response():
    try:
        data = request.json
        print("Segments: " + str(data.get('segments')))
        prompt = "You must write an article based on the following text with timecodes. The structure of prompt is: " \
                 "'start' - initial time in seconds of text fragment, 'end' - ending time in seconds of text " \
                 "fragment, 'text' - text " \
                 "fragment itself. In the end of each logical phrase in answer you must write a range of time in " \
                 "format " \
                 "'hh:mm:ss' where 'hh' is hours in 24 format, 'mm' is minutes and 'ss' is seconds and the example " \
                 "is: '00:05:12-00:12:30'. Analyze the text and write an article taking " \
                 "the information sequentially with timecodes. Each logical phrase with timecodes' range must be at " \
                 "least 20 seconds, they can't be less than 20 seconds. Length of the article must be " \
                 "around 7000 " \
                 "characters: " + str(data.get('segments'))
        response = chatbot.ask(prompt, "user")
        print(response)
        print("Token count ", chatbot.get_token_count())
        chatbot.reset(system_prompt=SYSTEM_PROMPT)
        return jsonify({"content": response})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run()
