import os
from threading import Thread
from flask import Flask
from bot import app, bot, run_flask

if __name__ == "__main__":
    # 1. تشغيل البوت في Thread منفصل لكي لا يعطل سيرفر الويب
    token = os.environ.get('TOKEN')
    if token:
        print("Starting Discord Bot...")
        Thread(target=lambda: bot.run(token)).start()
    else:
        print("Error: TOKEN environment variable not found!")

    # 2. تشغيل فلاسك ليبقى التطبيق مستيقظاً كـ Web Service
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
