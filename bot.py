from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, ApiIdInvalidError
import asyncio
import json
import os

BOT_API_ID = 32399630
BOT_API_HASH = 'bcb9ae8632535f024b267afdb8763445'
BOT_TOKEN = '8536756573:AAGJlnf3h03mY0J1oaVgxe2tU4qodAz8ASc'
OWNER_ID = 7484391566

bot = TelegramClient('main_bot', BOT_API_ID, BOT_API_HASH)

setup_sessions = {}
user_settings = {}
post_tasks = {}

DB_FILE = 'users.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

activated_users = load_db()

@bot.on(events.NewMessage(pattern=r'\.الاوامر'))
async def owner_panel(event):
    if event.sender_id != OWNER_ID:
        return
    total = len(activated_users)
    await event.respond(
        f"👑 يا ملك هذا لوحة تحكمك الخاصة\n\n"
        f"👥 عدد المفعلين حالياً: {total}\n\n"
        f"`.المستخدمين` — تشوف كل الجلسات شلونها\n"
        f"`.انهاء [ID]` — تنهي جلسة واحد معين"
    )

@bot.on(events.NewMessage(pattern=r'\.المستخدمين'))
async def list_users(event):
    if event.sender_id != OWNER_ID:
        return
    if not activated_users:
        return await event.respond("والله بعد محد مفعل حسابه")
    msg = "👥 هذني الجلسات الي شغالة حالياً:\n\n"
    for uid, info in activated_users.items():
        running = "🟢 شغال" if uid in post_tasks else "🔴 واقف"
        msg += f"{running} ID: `{uid}` | رقم: {info.get('phone', '')}\n"
    await event.respond(msg)

@bot.on(events.NewMessage(pattern=r'\.انهاء (\d+)'))
async def end_session(event):
    if event.sender_id != OWNER_ID:
        return
    uid = event.pattern_match.group(1)
    if uid in activated_users:
        if uid in post_tasks:
            post_tasks[uid].cancel()
            del post_tasks[uid]
        del activated_users[uid]
        save_db(activated_users)
        session_file = f'session_{uid}.session'
        if os.path.exists(session_file):
            os.remove(session_file)
        await event.respond(f"✅ تمام انهيت جلسة `{uid}`")
        try:
            await bot.send_message(int(uid), "❌ حبيبي المالك لغى جلستك")
        except:
            pass
    else:
        await event.respond("❌ هذا المستخدم مو موجود اصلاً")

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = str(event.sender_id)
    if uid in activated_users:
        return await event.respond(
            "✅ هيج حسابك مفعل خلاص\n\n"
            "دز `.مساعد` حتى تشوف لوحتك"
        )
    await event.respond(
        "هلا والله بالغالي!\n\n"
        "حتى افعلك يمك دزلي هذني:\n"
        "1️⃣ API ID\n"
        "2️⃣ API HASH\n\n"
        "تاخذهن من هنا: my.telegram.org\n\n"
        "هسة دزلي API ID:"
    )
    setup_sessions[uid] = {'step': 'api_id'}

@bot.on(events.NewMessage)
async def handle_setup(event):
    uid = str(event.sender_id)
    if uid not in setup_sessions:
        return
    if event.text and event.text.startswith('.'):
        return

    session = setup_sessions[uid]
    text = event.text.strip() if event.text else ''
    step = session.get('step')

    if step == 'api_id':
        if not text.isdigit():
            return await event.respond("❌ حبيبي API ID لازم ارقام بس، دزلي ياه مرة ثانية:")
        session['api_id'] = int(text)
        session['step'] = 'api_hash'
        await event.respond("✅ زين!\nهسة دزلي API HASH:")

    elif step == 'api_hash':
        session['api_hash'] = text
        session['step'] = 'phone'
        await event.respond("✅ تمام!\nهسة دزلي رقمك هيج:\n`+964xxxxxxxx`")

    elif step == 'phone':
        session['phone'] = text
        try:
            client = TelegramClient(f'session_{uid}', session['api_id'], session['api_hash'])
            await client.connect()
            await client.send_code_request(text)
            session['client'] = client
            session['step'] = 'code'
            await event.respond("✅ دزيته الكود ع التلي\nدزلي الكود بس ضع مسافات بين الارقام هيج مثلاً: 5 2 3 9 8")
        except ApiIdInvalidError:
            await event.respond("❌ API ID او HASH غلط\nرجع ابدي من جديد /start")
            del setup_sessions[uid]
        except Exception as e:
            await event.respond(f"❌ صار خطأ: {e}")

    elif step == 'code':
        try:
            code_no_spaces = text.replace(" ", "")
            client = session['client']
            await client.sign_in(session['phone'], code_no_spaces)
            await finish_setup(event, uid, session, client)
        except SessionPasswordNeededError:
            session['step'] = 'password'
            await event.respond("🔐 هذا الحساب عليه تحقق بخطوتين، دزلي كلمة المرور:")
        except Exception as e:
            await event.respond(f"❌ الكود غلط حاول مرة ثانية: {e}")

    elif step == 'password':
        try:
            await event.delete()
            client = session['client']
            await client.sign_in(password=text)
            await finish_setup(event, uid, session, client)
        except Exception as e:
            await event.respond(f"❌ كلمة المرور غلط: {e}")

async def finish_setup(event, uid, session, client):
    await client.disconnect()
    activated_users[uid] = {'phone': session['phone']}
    save_db(activated_users)
    user_settings[uid] = {
        'content': None,
        'content_type': None,
        'caption': '',
        'channels': [],
        'delay_ms': 1000,
        'is_running': False,
        'api_id': session['api_id'],
        'api_hash': session['api_hash']
    }
    del setup_sessions[uid]
    await event.respond(
        "🎉 اييي خلص التفعيل تمام!\n\n"
        "دز `.مساعد` حتى تشوف لوحة التحكم مالته"
    )
    await bot.send_message(OWNER_ID, f"🔔 يا مالك واحد جديد فَعل\nID: `{uid}`\nرقمه: {session['phone']}")

@bot.on(events.NewMessage(pattern=r'\.مساعد'))
async def user_panel(event):
    uid = str(event.sender_id)
    if uid not in activated_users:
        return await event.respond("❌ فعّل حسابك بالاول /start")
    await event.respond(
        "🤖 اهلاً بيك هذا لوحتك:\n\n"
        "`.محتوى` — تحط رسالة او صورة او ملف\n"
        "`.قناة [username]` — تضيف قناة\n"
        "`.حذف_قناة [username]` — تحذف قناة\n"
        "`.نشر [ثواني]` — يبدي النشر\n"
        "`.إيقاف` — يوقف النشر\n"
        "`.الحالة` — تشوف شنو وضعك"
    )

waiting_content = {}

@bot.on(events.NewMessage(pattern=r'\.محتوى'))
async def set_content(event):
    uid = str(event.sender_id)
    if uid not in activated_users:
        return
    waiting_content[uid] = True
    await event.respond("📩 يلا دزلي المحتوى مالته (رسالة صورة او ملف):")

@bot.on(events.NewMessage)
async def receive_content(event):
    uid = str(event.sender_id)
    if uid not in waiting_content or not waiting_content.get(uid):
        return
    if event.text and event.text.startswith('.'):
        return
    if uid not in user_settings:
        return

    if event.photo:
        user_settings[uid]['content'] = event.photo.id
        user_settings[uid]['content_type'] = 'photo'
        user_settings[uid]['caption'] = event.message.message or ''
        await event.respond("✅ تمام حفظت الصورة!")
    elif event.document:
        user_settings[uid]['content'] = event.document.id
        user_settings[uid]['content_type'] = 'file'
        user_settings[uid]['caption'] = event.message.message or ''
        await event.respond("✅ تمام حفظت الملف!")
    elif event.text:
        user_settings[uid]['content'] = event.text
        user_settings[uid]['content_type'] = 'text'
        await event.respond("✅ حفظت الرسالة!")

    waiting_content[uid] = False

@bot.on(events.NewMessage(pattern=r'\.قناة (.+)'))
async def add_channel(event):
    uid = str(event.sender_id)
    if uid not in activated_users:
        return
    channel = event.pattern_match.group(1).strip()
    if uid not in user_settings:
        user_settings[uid] = {'channels': [], 'content': None, 'content_type': None,
                               'caption': '', 'delay_ms': 1000, 'is_running': False}
    if channel not in user_settings[uid]['channels']:
        user_settings[uid]['channels'].append(channel)
        await event.respond(f"✅ تمام ضفت {channel}")
    else:
        await event.respond("⚠️ هيج انت اصلاً ضايفها")

@bot.on(events.NewMessage(pattern=r'\.نشر (\d+)'))
async def start_posting(event):
    uid = str(event.sender_id)
    if uid not in activated_users:
        return
    settings = user_settings.get(uid)
    if not settings or not settings['content']:
        return await event.respond("❌ بس دز `.محتوى` اول شي")
    if not settings['channels']:
        return await event.respond("❌ ضيف قناة بالاول")

    seconds = int(event.pattern_match.group(1))
    settings['delay_ms'] = seconds * 1000
    settings['is_running'] = True

    async def post_loop():
        client = TelegramClient(
            f'session_{uid}',
            settings['api_id'],
            settings['api_hash']
        )
        await client.connect()
        while settings['is_running']:
            for channel in settings['channels']:
                try:
                    if settings['content_type'] == 'text':
                        await client.send_message(channel, settings['content'])
                    else:
                        await client.send_file(channel, settings['content'],
                                               caption=settings['caption'])
                except Exception as e:
                    print(f"خطأ: {e}")
                await asyncio.sleep(settings['delay_ms'] / 1000)
        await client.disconnect()

    post_tasks[uid] = asyncio.create_task(post_loop())
    await event.respond(f"🟢 تمام بديت النشر كل {seconds} ثانية!")

@bot.on(events.NewMessage(pattern=r'\.إيقاف'))
async def stop_posting(event):
    uid = str(event.sender_id)
    if uid not in activated_users:
        return
    if uid in user_settings:
        user_settings[uid]['is_running'] = False
    if uid in post_tasks:
        post_tasks[uid].cancel()
        del post_tasks[uid]
    await event.respond("🔴 تمام اوقفت النشر")

print("✅ البوت شغّال!")
bot.start(bot_token=BOT_TOKEN)
bot.run_until_disconnected()