import queue
import tkinter.font as tkFont
import tkinter as tk
import websocket
import time
import datetime
import csv
from config import *
import threading
import keyboard

class PopupManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # 隱藏主視窗

        self.queue = queue.Queue()
        self.popup = None
        self.font = tkFont.Font(family="Arial", size=18)

        self.bot = None

        self.check_queue()

        self.setup_hotkey()

    def set_bot(self, bot):
        self.bot = bot

    def check_queue(self):
        try:
            while True:
                user, message = self.queue.get_nowait()
                self.show_popup(user, message)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    # 顯示視窗
    def show_popup(self, user, message, duration=5000):
        text = f"{user}: {message}"

        if self.popup is not None and self.popup.winfo_exists():
            label = self.popup.label
            label.config(text=text, wraplength=600)
            self.resize_popup(text)
            self.popup.after_cancel(self.popup.after_id)
            self.popup.after_id = self.popup.after(duration, self.popup.destroy)
        else:
            self.popup = tk.Toplevel(self.root)
            self.popup.overrideredirect(True)
            self.popup.attributes("-topmost", True)
            self.popup.configure(
                bg="#1e1e1e",
                highlightbackground="#ffffff",  # 邊框顏色
                highlightthickness=3           # 邊框寬度（像素）
            )

            self.popup.label = tk.Label(self.popup,
                                        text=text,
                                        font=self.font,
                                        fg="#00aaff",
                                        bg="#1e1e1e",
                                        anchor="w",
                                        justify="left",
                                        wraplength=600)
            self.popup.label.pack(fill="both", padx=10, pady=10)

            self.resize_popup(text)

            x, y = 20, 40

            self.popup.geometry(f"{self.width}x{self.height}+{x}+{y}")

            self.popup.after_id = self.popup.after(duration, self.popup.destroy)

    # 更新視窗大小
    def resize_popup(self, text):
        paddingX = 30
        paddingY = 20
        min_width = 0    # 最小寬度
        max_width = 600    # 最大寬度

        # 先用字體量測文字寬度（大概）
        text_width_px = self.font.measure(text)

        # 設定寬度限制，寬度為文字寬度 + padding
        width = text_width_px + paddingX

        # 限制寬度區間
        if width < min_width:
            width = min_width
        elif width > max_width:
            width = max_width

        # 設定 Label 的 wraplength 為視窗寬度減去 padding
        wraplength = width - paddingX

        self.popup.label.config(text=text, wraplength=wraplength)
        self.popup.label.update_idletasks()

        req_height = self.popup.label.winfo_reqheight()
        height = req_height + paddingY

        self.width = width
        self.height = height

        self.popup.geometry(f"{self.width}x{self.height}+20+40")

    # 快速鍵開啟回覆聊天室用的視窗
    def setup_hotkey(self):
    # 使用 keyboard 全局監聽熱鍵（非 Tkinter 綁定）
        keyboard.add_hotkey('ctrl+shift+t', lambda: self.root.after(0, self.open_reply_window))

    # 開啟回覆聊天室用的視窗
    def open_reply_window(self, event=None):
        if not hasattr(self, "reply_window") or not self.reply_window.winfo_exists():
            self.reply_window = tk.Toplevel(self.root)
            self.reply_window.title("")  # 不顯示標題文字
            self.reply_window.configure(bg="black")  # 背景色可改成白色
            self.reply_window.overrideredirect(True)

            width, height = 400, 60

            # 計算螢幕中央位置
            screen_width = self.reply_window.winfo_screenwidth()
            screen_height = self.reply_window.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
    
            self.reply_window.geometry(f"{width}x{height}+{x}+{y}")
    
            self.reply_entry = tk.Entry(
                self.reply_window,
                width=50,
                bg="black",        # 背景色
                fg="#00aaff",        # 文字顏色
                insertbackground="white",  # 游標顏色
                relief="flat",     # 去掉邊框
                borderwidth=0,       # 無邊框
                highlightthickness=0,# 無高亮邊
                font=("Arial", 14) # 可選的字體設定
            )
            self.reply_entry.pack(padx=10, pady=20)

            # 這段主要是拿來讓我把它叫出來後可以自動選定他，不然原本她還需要點一下
            self.reply_window.lift()
            self.reply_window.attributes("-topmost", True)
            self.reply_window.after_idle(self.reply_window.attributes, '-topmost', False)
            self.reply_window.after(100, lambda: (self.reply_entry.focus_force(), self.reply_entry.focus_set()))

            # 按下Enter觸發送出
            self.reply_window.bind("<Return>", lambda e: self.send_reply())
            # 按ESC退出
            self.reply_window.bind("<Escape>", lambda e: self.reply_window.destroy())

    # 傳出回覆
    def send_reply(self):
        message = self.reply_entry.get().strip()
        if message:
            # 假設有ws物件可以拿到
            global global_ws
            if global_ws:
                self.bot.send_message_to_chat(global_ws, message)
                print("已向聊天室發送訊息：", message)
                self.bot.show_popup("發送", message)
            self.reply_window.destroy()

class TwitchBot:
    def __init__(self):
        #config.pyから資料取ります
        self.access_token = f"oauth:{Access_Token}"  # oauth:access_token
        self.nickname = BOT_NICK
        self.channel = f"#{CHANNEL}"  # #忘れないように
        self.twitchWebsocketURL = TwitchWebsocketURL

        #今日の日付
        self.today = datetime.date.today().strftime('%Y%m%d')

        self.popup_manager = None
    
    def set_popup_manager(self, popup_manager):
        self.popup_manager = popup_manager

    def show_popup(self, user, message):
        self.popup_manager.queue.put((user, message))

    #csvからコマンドを読み込める
    def load_responses(filename):
        responses = {}
        with open(filename, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                responses[row['trigger']] = row['response']
        return responses

    responses = load_responses('responses.csv')

    def check_and_reply(self, message):
        for trigger, reply in responses.items():
            if trigger in message:
                return reply
        return None

    #WebSocket 接続成功した時
    def on_open(self, ws):
        global global_ws
        global_ws = ws
        print("接続成功、ログイン中...")
        ws.send(f"PASS {self.access_token}")
        ws.send(f"NICK {self.nickname}")
        ws.send(f"JOIN {self.channel}")
        print(f"チャット入りました！チャンネルは{self.channel}です！")
        reply = "MrDestructoid チャット入りました！"
        self.send_message_to_chat(ws, reply)

    #WebSocket メッセージ受けた時
    def on_message(self, ws, message):
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

                self.show_popup(user, content.strip())

                #チャットログ
                with open(self.today + '_chat' + '.txt', 'a', encoding='utf-8-sig') as f :
                    localTime = time.localtime()
                    f.write(f"{time.strftime('%H:%M:%S --',localTime)} " + user + ': ' + content)

                #コマンド
                """ if content.strip().startswith("安安"):
                    reply = f"{user} ニーハオ！"
                    send_message_to_chat(ws, reply) """
                reply = self.check_and_reply(message)
                if reply:
                    self.send_message_to_chat(ws, f"@{user} {reply}")

                #特殊コマンド
                if content.strip().startswith("早安"):
                    now = datetime.datetime.now() #今の時間
                    hour = now.hour #今何時
                    if 5 <= hour < 12:
                        reply = f"@{user} 早啊 aokitwGood"
                        self.send_message_to_chat(ws, reply)
                    else:
                        reply = f"@{user} 不是，早個屁，都{hour}點了 aokitwHatena"
                        self.send_message_to_chat(ws, reply)

                #テスト
                if (content.strip().startswith("!テスト")  or content.strip().startswith("!test")) and user == CHANNEL:
                    reply = "無事に実行されました！"
                    self.send_message_to_chat(ws, reply)

                #!csv入力すればCSVリセットできる
                if (content.strip().startswith("!csv") or content.strip().startswith("!CSV")) and user == CHANNEL:
                    global responses 
                    responses = self.load_responses('responses.csv')
                    reply = "CSVリセットしました！"
                    self.send_message_to_chat(ws, reply)

                #チャットボット終了
                if content.strip().startswith("!終了") or content.strip().startswith("!close") and user == CHANNEL:
                    print("終了します")
                    reply = "チャットボット終了します"
                    self.send_message_to_chat(ws, reply)
                    ws.send(f"PART {self.channel}")
                    print("チャットを離れました")
                    ws.close()

            except Exception as e:
                print(f"メッセージ分析失敗: {e}")

    #チャットにメッセージ送る
    def send_message_to_chat(self, ws, reply):
        ws.send(f"PRIVMSG {self.channel} :{reply}")

    #WebSocket エラーの時
    def on_error(ws, error):
        print(f"エラー: {error}")

    #WebSocket 閉じる時
    def on_close(ws, close_status_code, close_msg):
        print("接続終了")

    #WebSocket 接続
    def websocket_thread(self):
        self.twitchWS = websocket.WebSocketApp(
            self.twitchWebsocketURL,
            on_open = self.on_open,
            on_message = self.on_message,
            on_error = self.on_error,
            on_close = self.on_close
        )
        self.twitchWS.run_forever()

if __name__ == '__main__':
    bot = TwitchBot()
    popup_manager = PopupManager()

    # 避免循環
    bot.set_popup_manager(popup_manager)
    popup_manager.set_bot(bot)
    # 用子執行緒跑 WebSocket
    threading.Thread(target=bot.websocket_thread, daemon=True).start()
    # 主執行緒跑 Tkinter mainloop
    popup_manager.root.mainloop()