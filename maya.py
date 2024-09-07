import discord
from discord.ext import commands, tasks
from datetime import datetime
import re

# Bot ve ID'ler
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ID'ler
REGISTER_CATEGORY_ID = 1276217866907291772  # Kayıt kategorisi ID'si
LOG_CHANNEL_ID = 1276628103439061033  # Log kanalı ID'si
BAR_CHANNEL_ID = 1063493716419035289  # Doğum günü kutlama kanalının ID'si
ROLE_STRANGER_ID = 1276584128761827328  # Stranger rolü ID'si
ROLE_ROOKIE_ID = 1271963998237229090  # Rookie rolü ID'si
ROLE_SISTERS_ID = 1272279945422438481  # Sisters rolü ID'si
NIGHT_CLUB_CATEGORY_ID = 1278606665486303325  # Night Club kategorisi ID'si
POOL_VOICE_CHANNEL_ID = 1279066814776737842  # Pool sesli kanalının ID'si
WAITROOM_CHANNEL_ID = 1278606860957650974  # Waitroom yazı kanalının ID'si

# Kullanıcı kayıt aşamaları için durum yönetimi
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
    clean_waitroom.start()  # Waitroom kanalını temizleme görevini başlat

# !maya komutu
@bot.command()
async def maya(ctx):
    await ctx.send('Miuuww!')

# !salla komutu
@bot.command()
@commands.has_permissions(kick_members=True)
async def salla(ctx, member: discord.Member, *, reason=None):
    """Etiketlenen kişiyi sunucudan atar."""
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

# !clear komutu
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """
    Belirli sayıda mesajı siler.
    :param amount: Silinecek mesaj sayısı
    """
    if amount <= 0:
        await ctx.send("Silinecek mesaj sayısı 0'dan küçük olamaz.")
        return

    deleted = await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"{len(deleted) - 1} mesajı mayacık halletti.", delete_after=5)

# !test_birthdays komutu
@bot.command()
@commands.has_permissions(administrator=True)
async def test_birthdays(ctx):
    """Manuel olarak doğum günü kontrolü başlatır."""
    await check_birthdays()
    await ctx.send("Kimler doğmuş bakalım.")

# Doğum günü kontrolü
@tasks.loop(hours=24)
async def check_birthdays():
    now = datetime.now()
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    bar_channel = bot.get_channel(BAR_CHANNEL_ID)
    
    messages = []
    async for message in log_channel.history(limit=100):
        messages.append(message)

    date_pattern = re.compile(r'\b(\d{2})-(\d{2})-(\d{4})\b')
    for message in messages:
        match = date_pattern.search(message.content)
        if match:
            day, month, year = map(int, match.groups())
            if now.month == month and now.day == day:
                user_id_match = re.search(r'<@(\d+)>', message.content)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                    user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                    if user:
                        await bar_channel.send(f"🎉 Miiiuuwww! Bugün doğum günüüü {user.mention}! Doğum günün kutlu olsunnn! Yupppiii 🎉")

# Kullanıcı kayıt olayları
@bot.event
async def on_member_join(member):
    guild = member.guild

    stranger_role = discord.utils.get(guild.roles, id=ROLE_STRANGER_ID)
    if stranger_role:
        await member.add_roles(stranger_role)
    
    register_category = guild.get_channel(REGISTER_CATEGORY_ID)
    if register_category:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        register_channel = await guild.create_text_channel(
            f'{member.name}-kayıt', 
            category=register_category, 
            overwrites=overwrites
        )
        await register_channel.send(
            f"{member.mention}, Hoş geldinn! Miuuwww! Clupta hangi isimle hitap edilmek istersin?"
        )
        registration_manager.start_registration(member.id, register_channel.id)

@bot.event
async def on_message(message):
    if not message.author.bot:
        user_id = message.author.id
        state = registration_manager.get_state(user_id)

        if state and message.channel.id == state['channel_id']:
            if state['step'] == 'name':
                if registration_manager.set_name(user_id, message.content):
                    await message.channel.send("Thanks babee! Doğum tarihini şu şekilde > `GG-AA-YYYY` girermisin. Doğum gününü kutluyıcaz")
                    try:
                        await message.author.edit(nick=message.content)
                    except discord.Forbidden:
                        await message.channel.send("olmadı bebeğim.")
            elif state['step'] == 'birth_date':
                if registration_manager.set_birth_date(user_id, message.content):
                    await message.channel.send("Harika canımm! cinsiyetin nedir? (erkek/kız).")
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

    await bot.process_commands(message)

async def complete_registration(user_id, member):
    guild = bot.get_guild(member.guild.id)
    stranger_role = discord.utils.get(guild.roles, id=ROLE_STRANGER_ID)
    rookie_role = discord.utils.get(guild.roles, id=ROLE_ROOKIE_ID)
    sisters_role = discord.utils.get(guild.roles, id=ROLE_SISTERS_ID)

    state = registration_manager.complete_registration(user_id)
    if state:
        if stranger_role:
            await member.remove_roles(stranger_role)
        
        roles_to_add = [rookie_role]
        if state['gender'] == 'kız':
            roles_to_add.append(sisters_role)
        
        for role in roles_to_add:
            if role:
                await member.add_roles(role)
        
        register_channel = bot.get_channel(state['channel_id'])
        if register_channel:
            await register_channel.delete()

# !room komutu
@bot.command()
async def room(ctx):
    if not ctx.author.voice or ctx.author.voice.channel.id != POOL_VOICE_CHANNEL_ID:
        await ctx.send('Tatlım bu komutu sadece Pool kanalında kullanabilirsin!')
        return

    category = ctx.guild.get_channel(NIGHT_CLUB_CATEGORY_ID)
    if category is None:
        await ctx.send('Night Club kategorisi bulunamadı!')
        return

    channels = [channel for channel in category.channels if isinstance(channel, discord.VoiceChannel) and channel.name.startswith('Room')]
    highest_number = 0
    for channel in channels:
        try:
            number = int(channel.name.split('#')[-1].strip())
            if number > highest_number:
                highest_number = number
        except ValueError:
            continue

    new_room_number = highest_number + 1
    new_channel_name = f'Room #{new_room_number}'

    new_channel = await ctx.guild.create_voice_channel(
        name=new_channel_name,
        category=category
    )

    await new_channel.set_permissions(ctx.author, connect=True, speak=True)
    await ctx.author.move_to(new_channel)
    await ctx.send(f'{ctx.author.mention} sesli odan hazırr! {new_channel.mention}')

# !invite komutu
@bot.command()
async def invite(ctx, user: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send('Bir sesli kanalda olmalısınız.')
        return

    channel = ctx.author.voice.channel
    if user in channel.members:
        await ctx.send(f'{user.mention} zaten bu kanalda.')
        return

    await user.move_to(channel)
    await ctx.send(f'{user.mention} tutup getirdim.')

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.category and before.channel.category.id == NIGHT_CLUB_CATEGORY_ID:
        if len(before.channel.members) == 0 and before.channel.id != POOL_VOICE_CHANNEL_ID:
            await before.channel.delete()

    if after.channel and after.channel.id == POOL_VOICE_CHANNEL_ID:
        for channel in after.channel.category.channels:
            if isinstance(channel, discord.VoiceChannel) and channel.name.startswith('Room'):
                if len(channel.members) == 0:
                    await channel.delete()

@tasks.loop(minutes=3)
async def clean_waitroom():
    waitroom_channel = bot.get_channel(WAITROOM_CHANNEL_ID)
    if waitroom_channel is None:
        print('Waitroom kanalı bulunamadı!')
        return

    pinned_messages = await waitroom_channel.pins()
    pinned_ids = [message.id for message in pinned_messages]

    async for message in waitroom_channel.history(limit=100):
        if message.id not in pinned_ids:
            await message.delete()


