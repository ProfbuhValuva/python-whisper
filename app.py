# coding: utf8

import pathlib
import random
import subprocess
import time
from urllib.parse import urlparse, parse_qs

import replicate
import requests
from PIL import Image
from flask import Flask, request, jsonify
from pydub import AudioSegment
from revChatGPT.V3 import Chatbot
from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

app = Flask(__name__)

final_filename = None


@app.route('/youtube', methods=['POST'])
def youtube_downloader():
    try:
        data = request.json
        print(str(data))
        url = data.get('content')
        name = data.get('id')
        subprocess.run(["yt-dlp", "-f best", "-o" + name + ".%(ext)s", "-x", "--audio-format=mp3", url])
        final_filename = str(pathlib.Path().resolve()) + "\\" + name + ".mp3"
        if (data.get('time') is not None) and (data.get('time').get('start_seconds') is not None) and (
                data.get('time').get('end_seconds') is not None):
            song = AudioSegment.from_file(final_filename,
                                          format="mp3")
            time = data.get('time')
            start_sec = time.get('start_seconds')
            end_sec = time.get('end_seconds')
            start = start_sec * 1000
            end = end_sec * 1000
            cut_track = song[start: end]
            cut_track.export(final_filename, format="mp3")
        print(final_filename)
        output = replicate.Client(api_token="r8_Si0ll04akWl9xUI9QBLgxLMOHjoifVi4Wz2c1").run(
            "openai/whisper:91ee9c0c3df30478510ff8c8a3a545add1ad0259ad3a9f78fba57fbc05ee64f7",
            input={"audio": open(final_filename, "rb")}
        )
        print(output)
        return jsonify(output)
    except Exception as e:
        print(f"Error: {e}")


@app.route('/llm', methods=['POST'])
def llm_response():
    try:
        data = request.json
        print("Request for LLM is: " + str(data))
        SYSTEM_PROMPT = "You are a friendly assistant. You will be provided with a transcription of YouTube video with " \
                        "timecodes. You must write an HTML article with introduction as you are a lecturer and write " \
                        "timecodes for each logical " \
                        "phrase. You MUST write a short introduction in 2-3 sentences without timecodes before the " \
                        "article " \
                        "itself.  In the end of each logical phrase in answer you must write a timecode in format " \
                        "'hh:mm:ss' where 'hh' is hours in 24 format, 'mm' is minutes and 'ss' is seconds and the " \
                        "example " \
                        "is: '00:05:12@@-00:12:30'. Timecodes ALWAYS MUST be as a HTML paragraph (<p>) near the " \
                        "corresponding " \
                        "phrase. All your timecodes MUST look exactly like in the example and be on the " \
                        "corresponding to phrase line. Notice, symbol '@' is only used for the first (left) part of " \
                        "range and " \
                        "" \
                        "you MUST use it. You MUST use headers and needed HTML tags to point out valuable information " \
                        "or " \
                        "topic (for example, <h1>, <strong>, <h2>). Your HTML article MUST be formatted with HTML " \
                        "tags. Each " \
                        "logical phrase " \
                        "with timecodes range mustn't be short. " \
                        "You must analyze text and write HTML article with timecodes. " \
                        "You always answer in Russian language. YOU ALWAYS MUST WRITE TIMECODES IN FORMAT " \
                        "'00:05:12@@-00:12:30'."
        chatbot = None
        flag = False
        if data.get('model') == 'gpt-4-0613':
            flag = True
            chatbot = Chatbot(api_key="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", max_tokens=8000,
                              system_prompt=SYSTEM_PROMPT,
                              engine="gpt-4-0613", temperature=0.9)
        if data.get('model') == 'gpt-3.5-turbo-16k-0613':
            flag = True
            chatbot = Chatbot(api_key="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", max_tokens=16000,
                              system_prompt=SYSTEM_PROMPT,
                              engine="gpt-3.5-turbo-16k-0613", temperature=0.65)
        print("Segments: " + str(data.get('segments')))
        prompt = ""
        if data.get('segments') is not None:
            annotation_prompt = "You MUST write a short introduction in 2-3 sentences without timecodes before the " \
                                "article itself."
            article_prompt = "You are not limited in article characters length - write as long as you want: "
            if data.get('annotation_length') is not None:
                annotation_prompt += "The length of introduction in characters MUST BE NEAR " + str(
                    data.get('annotation_length')) + " symbols. "
            if data.get('article_length') is not None:
                article_prompt = "Article amount of characters MUST BE NEAR " + str(
                    data.get('article_length')) + "symbols - don't write more:"
            prompt = "You must write an HTML article with introduction based on the following text with timecodes. " \
                     "YOU ALWAYS MUST WRITE " \
                     "TIMECODES IN FORMAT '00:05:12@@-00:12:30'. " + annotation_prompt + \
                     "All your timecodes MUST look exactly like in the example and be on the corresponding to phrase " \
                     "line. The structure of prompt is: " \
                     "'start' - initial time in seconds of text fragment, 'end' - ending time in seconds of text " \
                     "fragment, 'text' - text " \
                     "fragment itself. Timecodes must correspond to the provided structure. In the end of each logical " \
                     "phrase in answer you must write a range of time in " \
                     "format " \
                     "'hh:mm:ss' where 'hh' is hours in 24 format, 'mm' is minutes and 'ss' is seconds and the example " \
                     "is: '00:05:12@@-00:12:30'. Notice, symbol '@' is only used for the first (left) part of range " \
                     "and " \
                     "you MUST use it. Timecodes ALWAYS MUST be as a HTML paragraph (<p>) near the corresponding " \
                     "phrase. " \
                     "Your HTML article MUST be formatted with HTML tags. Analyze the text and write an HTML article " \
                     "taking " \
                     "the information sequentially with timecodes. Each logical phrase with timecodes range mustn't be " \
                     "short. " + article_prompt + str(data.get('segments'))
        else:
            print("TotalHTML: " + str(data.get('total_html')))
            if flag:
                chatbot.reset()
            prompt = "You are provided HTML with an article and images (<img> HTML tags). Your task is to write back " \
                     "an updated HTML " \
                     "where screenshots (images) are included directly in the article after corresponding time codes. " \
                     "Images (<img> HTML tags) must be moved to the needed parts of article: " + str(data.get('total_html'))
        response = ""
        if flag:
            response = chatbot.ask(prompt, "user")
        else:
            url = 'https://jtx4v48v10rby153.us-east-1.aws.endpoints.huggingface.cloud'
            headers = {
                'Authorization': 'Bearer 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',
                'Content-Type': 'application/json'
            }
            payload = {
                'inputs': prompt,
                'parameters': {
                    'min_length': 20,
                    'max_new_tokens': 8000,
                    'top_k': 50,
                    'top_p': 0.9,
                    'early_stopping': True,
                    'no_repeat_ngram_size': 2,
                    'use_cache': True,
                    'repetition_penalty': 1.5,
                    'length_penalty': 0.8,
                    'num_beams': 4
                }
            }
            response = requests.post(url, json=payload, headers=headers)
            return jsonify({"content": response.json().get('generated_text')})
        print(response)
        if flag:
            chatbot.reset(system_prompt=SYSTEM_PROMPT)
        return jsonify({"content": response})
    except Exception as e:
        print(f"Error: {e}")


@app.route('/screenshots', methods=['POST'])
def take_screenshots():
    data = request.json
    timecodes = data['timecodes']
    screenshot_paths = []

    for timecode in timecodes:
        try:
            opt = webdriver.ChromeOptions()
            opt.add_argument("--start-maximized")
            opt.page_load_strategy = 'none'
            driver = webdriver.Chrome(service=Service("D:\\DownloadsChrome\\chromedriver_win32\\chromedriver.exe"),
                                      options=opt)
            driver.get(timecode)
            time.sleep(5)

            player = driver.find_element(By.CLASS_NAME, "html5-video-player")

            actions = ActionChains(driver).move_to_element(player)
            actions.send_keys("k")
            actions.send_keys(Keys.ENTER)
            actions.perform()

            time.sleep(5)

            screenshot_path = f"Screenshot_{random.randint(1, 65535)}.png"
            driver.save_screenshot(screenshot_path)

            screenshot = Image.open(screenshot_path)
            screenshot = screenshot.crop(
                (51, 68, 1380, 805))
            screenshot.save(screenshot_path)
            screenshot_paths.append(
                "<div> <img width=\"600\" height=\"400\" src=\"https://b25c-77-94-216-241.ngrok-free.app/url/" + screenshot_path + "\" alt=\"" + seconds_to_time(
                    get_seconds_from_url(timecode)) + "\"> <p><center><a href=\"" + timecode + "\">" + seconds_to_time(
                    get_seconds_from_url(timecode)) + "</a></center></p> </div>")

            driver.quit()
        except Exception as e:
            continue
    return jsonify({'screenshots': screenshot_paths})


def get_seconds_from_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    if 't' in query_params:
        time_param = query_params['t'][0]
        seconds = time_param[:-1]
        return int(seconds)
    else:
        return None


def seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)


if __name__ == '__main__':
    app.run()
