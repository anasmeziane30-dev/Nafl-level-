from bot import app, bot
from threading import Thread
import os

if __name__ == "__main__":
    # تشغيل البوت في الخلفية
    token = os.environ.get('TOKEN')
    if token:
        Thread(target=lambda: bot.run(token)).start()
    
    # تشغيل فلاسك لكي يكون هو الواجهة الأساسية لـ Render Web Service
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
