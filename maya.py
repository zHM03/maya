import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime
import re

# Gerekli yetkiler (intents)
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Kategori ve kanal ID'leri
NİGHT_CLUB_CATEGORY_ID = 1278606665486303325  # Night Club kategorisi ID'si
POOL_VOICE_CHANNEL_ID = 1279066814776737842  # Pool sesli kanalının ID'si
WAITROOM_CHANNEL_ID = 1278606860957650974  # Waitroom yazı kanalının ID'si
LOG_CHANNEL_ID = 1276628103439061033  # Log kanalının ID'si
BAR_CHANNEL_ID = 1063493716419035289  # Doğum günü kutlama kanalının ID'si
REGISTER_CATEGORY_ID = 1276217866907291772  # Kayıt kategorisi ID'si
WELCOME_HB_CHANNEL_ID = 1272169166123569323  # Welcome-HB kanalı ID'si
ROLE_STRANGER_ID = 1276584128761827328  # Stranger rolü ID'si
ROLE_ROOKIE_ID = 1271963998237229090  # Rookie rolü ID'si
ROLE_SISTERS_ID = 1272279945422438481  # Sisters rolü ID'si

# Kayıt yönetimi
class RegistrationManager:
    def __init__(self):
        self.user_states = {}

    def start_registration(self, user_id, channel_id):
        self.user_states[user_id] = {
            'step': 'name',
            'channel_id': channel_id,
            'name': None,
            'birth_date': None,
            'gender': None
        }

    def get_state(self, user_id):
        return self.user_states.get(user_id)

    def set_name(self, user_id, name):
        state = self.user_states.get(user_id)
        if state:
            state['name'] = name
            state['step'] = 'birth_date'
            return True
        return False

    def set_birth_date(self, user_id, birth_date):
        state = self.user_states.get(user_id)
        if state:
            state['birth_date'] = birth_date
            state['step'] = 'gender'
            return True
        return False

    def set_gender(self, user_id, gender):
        state = self.user_states.get(user_id)
        if state:
            state['gender'] = gender
            state['step'] = None
            return True
        return False

    def complete_registration(self, user_id):
        return self.user_states.pop(user_id, None)

registration_manager = RegistrationManager()

# Botun hazır olduğunu anlamak için
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} pisi geldii!')
    # Belirli bir aralıkla waitroom kanalındaki mesajları temizlemek için görev başlatma
    clean_waitroom.start()
    # Doğum günü kontrolü görevini başlatma
    check_birthdays.start()

# Maya komutu
@bot.command()
async def maya(ctx):
    await ctx.send('Miuuww!')

# Mayayla mesajlaşma
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Botun kendi mesajlarına yanıt vermesini engeller

    if message.content.lower() == 'canım':
        await message.channel.send('ayyy kimler gelmişşş')

    # Kayıt aşamaları için işleme
    user_id = message.author.id
    state = registration_manager.get_state(user_id)

    if state and message.channel.id == state['channel_id']:
        if state['step'] == 'name':
            if registration_manager.set_name(user_id, message.content):
                await message.channel.send("Thanks babee! Doğum tarihini şu şekilde > `GG-AA-YYYY` girermisin. Doğum gününü kutluyıcaz")
                # İsim güncellemesini yap
                try:
                    await message.author.edit(nick=message.content)
                except discord.Forbidden:
                    await message.channel.send("olmadı bebeğim.")
        elif state['step'] == 'birth_date':
            if registration_manager.set_birth_date(user_id, message.content):
                await message.channel.send("Harika canımm! cinsiyetin nedir? (erkek/kız).")
                # Doğum tarihi log kanalı için mesaj gönder
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"{message.author.mention} Doğum Tarihi: {message.content}"
                    )
        elif state['step'] == 'gender':
            gender = message.content.lower()
            if gender in ['erkek', 'kız']:
                if registration_manager.set_gender(user_id, gender):
                    await complete_registration(user_id, message.author)
                else:
                    await message.channel.send("anlamadım gitti.")
            else:
                await message.channel.send("Dediğimi yap sadece 'erkek' veya 'kız' olarak yanıt ver.")
        else:
            await message.channel.send("Kayıt edemedim.")

    # Diğer komutların işlenmesini sağlar
    await bot.process_commands(message)

# Oda oluşturma komutu
@bot.command()
async def room(ctx):
    # Kullanıcının Pool kanalında olup olmadığını kontrol et
    if not ctx.author.voice or ctx.author.voice.channel.id != POOL_VOICE_CHANNEL_ID:
        await ctx.send('Tatlım bu komutu sadece Pool kanalında kullanabilirsin!')
        return

    category = ctx.guild.get_channel(NİGHT_CLUB_CATEGORY_ID)
    if category is None:
        await ctx.send('Night Club kategorisi bulunamadı!')
        return

    # Mevcut odaları kontrol et ve numaralandırma için en yüksek sayıyı bul
    channels = [channel for channel in category.channels if isinstance(channel, discord.VoiceChannel) and channel.name.startswith('Room')]
    highest_number = 0
    for channel in channels:
        try:
            number = int(channel.name.split('#')[-1].strip())
            if number > highest_number:
                highest_number = number
        except ValueError:
            continue

    # Yeni odanın ismini belirle
    new_room_number = highest_number + 1
    new_channel_name = f'Room #{new_room_number}'

    # Oda oluşturma
    new_channel = await ctx.guild.create_voice_channel(
        name=new_channel_name,
        category=category
    )

    # Kullanıcıyı kanala ekle ve kullanıcıyı kanala taşı
    await new_channel.set_permissions(ctx.author, connect=True, speak=True)
    await ctx.author.move_to(new_channel)
    await ctx.send(f'{ctx.author.mention} sesli odan hazırr! {new_channel.mention}')

# Kullanıcıları sesli kanala davet etme komutu
@bot.command()
async def invite(ctx, *users: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send('Bir sesli kanalda olmalısın.')
        return

    channel = ctx.author.voice.channel
    users_already_in_channel = []
    users_moved = []

    for user in users:
        if user in channel.members:
            users_already_in_channel.append(user)
        else:
            await user.move_to(channel)
            users_moved.append(user)

    if users_moved:
        moved_users_mentions = ', '.join([user.mention for user in users_moved])
        await ctx.send(f'{moved_users_mentions} tutup getirdim.')
    
    if users_already_in_channel:
        already_in_mentions = ', '.join([user.mention for user in users_already_in_channel])
        await ctx.send(f'{already_in_mentions} burda ya.')

# Sesli durum güncellemeleri
@bot.event
async def on_voice_state_update(member, before, after):
    # Night Club kategorisi altında yapılan değişiklikler
    if before.channel and before.channel.category and before.channel.category.id == NİGHT_CLUB_CATEGORY_ID:
        # Eğer kanal boşsa ve odalar oluşturulmuşsa sil
        if len(before.channel.members) == 0 and before.channel.id != POOL_VOICE_CHANNEL_ID:
            await before.channel.delete()

    # Pool sesli kanalını asla silme, sadece boş odaları yönet
    if after.channel and after.channel.id == POOL_VOICE_CHANNEL_ID:
        # Pool kanalında boş odaları kontrol et ve sil
        for channel in after.channel.category.channels:
            if isinstance(channel, discord.VoiceChannel) and channel.name.startswith('Room'):
                if len(channel.members) == 0:
                    await channel.delete()

# Mesajları temizleme görev
@tasks.loop(minutes=7)  # Her 7 dakikada bir çalışacak şekilde ayarlanmıştır
async def clean_waitroom():
    # Waitroom kanalındaki mesajları temizle
    waitroom_channel = bot.get_channel(WAITROOM_CHANNEL_ID)
    if waitroom_channel is None:
        print('Waitroom kanalı bulunamadı!')
        return

    pinned_messages = await waitroom_channel.pins()
    pinned_ids = [message.id for message in pinned_messages]

    async for message in waitroom_channel.history(limit=100):
        if message.id not in pinned_ids:
            await message.delete()

# Kayıt işleminin tamamlanması
async def complete_registration(user_id, member):
    state = registration_manager.complete_registration(user_id)
    if state:
        name = state['name']
        birth_date = state['birth_date']
        gender = state['gender']

        # Mesajı log kanalına gönder
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"{member.mention} kayıt oldu! \nİsim: {name} \nDoğum Tarihi: {birth_date} \nCinsiyet: {gender}"
            )

        # Kullanıcıya rol verme
        roles = {
            'erkek': ROLE_ROOKIE_ID,
            'kız': ROLE_SISTERS_ID
        }
        role_id = roles.get(gender)
        if role_id:
            role = discord.utils.get(member.guild.roles, id=role_id)
            if role:
                await member.add_roles(role)
                await member.send(f"Kayıt tamamlandı! Size {role.name} rolü verildi.")
            else:
                await member.send("Rol bulunamadı.")
        else:
            await member.send("Geçersiz cinsiyet girildi.")

        # Hoş geldin mesajı gönder
        welcome_channel = bot.get_channel(WELCOME_HB_CHANNEL_ID)
        if welcome_channel:
            await welcome_channel.send(f"Hoş geldin {member.mention}! 🎉")
        else:
            await member.send("Hoş geldin mesajı gönderilemedi.")

# Kullanıcıyı sesli kanaldan atma komutu
@bot.command()
@commands.has_permissions(kick_members=True)
async def salla(ctx, member: discord.Member, *, reason=None):
    if ctx.author == member:
        await ctx.send("sallayamadım!")
        return
    
    bot_role = ctx.guild.get_member(bot.user.id).top_role

    if bot_role.position <= member.top_role.position:
        await ctx.send("hayırdır!")
        return

    try:
        await ctx.send("patimi yalıyorum bi saniye...")
        await ctx.send(f"{member} tırmaladım!")
        await member.kick(reason=reason)
    except discord.Forbidden:
        await ctx.send("yatağımdan kalkamam.")
    except discord.HTTPException as e:
        await ctx.send(f":bu benden korkmuyor ben bunu yolarım. {e}")

# Mesajları temizleme komutu
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount < 1 or amount > 100:
        await ctx.send("1 ile 100 arasında bir sayı girin.")
        return

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f'{len(deleted)} mesaj silindi.', delete_after=5)

# Botu çalıştırma
bot.run('MTI3MzY4NTY5NzM3MDI1OTY3MA.GzUQAs.pax1ZsSLYmUAvVLib8_gbblaIjri7kIoLc7PBc')
