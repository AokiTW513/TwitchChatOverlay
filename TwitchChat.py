import threading
import websocket
import time
import datetime
from config import *

#config.pyから資料取ります
access_token = f"oauth:{Access_Token}"  # oauth:access_token
nickname = BOT_NICK
channel = f"#{CHANNEL}"  # #忘れないように
twitchWebsocketURL = TwitchWebsocketURL

#今日の日付
today = datetime.date.today().strftime('%Y%m%d')

# WebSocket 接続成功した時
def on_open(ws):
    print("接続成功、ログイン中...")
    ws.send(f"PASS {access_token}")
    ws.send(f"NICK {nickname}")
    ws.send(f"JOIN {channel}")
    print(f"チャット入りました！チャンネルは{channel}です！")


#WebSocket メッセージ受けた時
def on_message(ws, message):
    #多分Twitch APIからボットまだ生きてるかテストするのもの
    if message.startswith("PING"):
        ws.send("PONG :tmi.twitch.tv")
        print("PONG")
        return
    
    #チャットのメッセージ
    if "PRIVMSG" in message:
        #チャットのユーザーネームとメッセージ分析する #元メッセージ多分こんな感じ :aokitw513!aokitw513@aokitw513.tmi.twitch.tv PRIVMSG #aokitw513 :wow
        try:
            #ユーザーネームとメッセージをprint
            user = message.split("!", 1)[0][1:] #[1:]は第一の文字スキップすること ex.hello[1:]=ello [0]なら分割したものの第一部分ですね
            content = message.split("PRIVMSG", 1)[1].split(":", 1)[1]
            print(f"{user}: {content.strip()}") #stripはstringの前後の\nとか削除するもの

            #チャットログ
            with open(today + '_chat' + '.txt', 'a', encoding='utf-8-sig') as f :
                localTime = time.localtime()
                f.write(f"{time.strftime('%H:%M:%S --',localTime)} " + user + ': ' + content)

            #コマンド
            if content.strip().startswith("安安"):
                reply = f"{user} ニーハオ！"
                ws.send(f"PRIVMSG {channel} :{reply}")

        except Exception as e:
            print(f"メッセージ分析失敗: {e}")

#WebSocket エラーの時
def on_error(ws, error):
    print(f"エラー: {error}")

#WebSocket 閉じる時
def on_close(ws, close_status_code, close_msg):
    print("接続終了")

#WebSocket 接続
def main():
    twitchWS = websocket.WebSocketApp(
        twitchWebsocketURL,
        on_open = on_open,
        on_message = on_message,
        on_error = on_error,
        on_close = on_close
    )
    twitchWS.run_forever()

if __name__ == '__main__':
    main()