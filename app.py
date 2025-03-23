import json
import logging
import os
import sys

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai
from google.genai import types

# INFOレベル以上のログメッセージを拾うように設定する
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数からMessaging APIのチャネルアクセストークンとチャネルシークレットを取得する
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

# 環境変数からGemini APIのAPIキーを取得する
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# それぞれ環境変数に登録されていないとエラー
if CHANNEL_ACCESS_TOKEN is None:
    logger.error(
        "Specify CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)
if CHANNEL_SECRET is None:
    logger.error("Specify CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if GEMINI_API_KEY is None:
    logger.error("Specify GEMINI_API_KEY as environment variable.")
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
webhook_handler = WebhookHandler(CHANNEL_SECRET)

# 質問に回答をする処理
@webhook_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    # Geminiに質問を投げて回答を取得する
    question = event.message.text
    client = genai.Client(api_key=GEMINI_API_KEY)
    answer_response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=question,
        config=types.GenerateContentConfig(
            stop_sequences=['。'],
        )
    )
    answer = answer_response.text
    
    # 受け取った回答のJSONを目視確認できるようにINFOでログに吐く
    logger.info(answer)

    # 応答トークンを使って回答を応答メッセージで送る
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=answer)
    )

# LINE Messaging APIからのWebhookを処理する
def lambda_handler(event, context):

    # リクエストヘッダーにx-line-signatureがあることを確認
    if 'x-line-signature' in event['headers']:
        signature = event["headers"]["x-line-signature"]

    body = event["body"]
    # 受け取ったWebhookのJSONを目視確認できるようにINFOでログに吐く
    logger.info(body)

    try:
        webhook_handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名を検証した結果、飛んできたのがLINEプラットフォームからのWebhookでなければ400を返す
        return {
            "statusCode": 400,
            "body": json.dumps('Only webhooks from the LINE Platform will accepted.')
        }
    except LineBotApiError as e:
        # 応答メッセージを送ろうとしたがLINEプラットフォームからエラーがかえってきたらエラーを吐く
        logger.error("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            logger.error("  %s: %s" % (m.property, m.message))

    return {
        "statusCode": 200,
        "body": json.dumps('Hello from Lambda!')
    }
