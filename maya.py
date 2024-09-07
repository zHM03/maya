import discord
from discord.ext import commands, tasks
from datetime import datetime
import re

# Intents ve bot tanımlamaları
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Kategori ve kanal ID'leri
REGISTER_CATEGORY_ID = 1276217866907291772  # Kayıt kategorisi ID'si
LOG_CHANNEL_ID = 1276628103439061033  # Log kanalı ID'si
WELCOME_HB_CHANNEL_ID = 1272169166123569323  # Welcome-HB kanalı ID'si
ROLE_STRANGER_ID = 1276584128761827328  # Stranger rolü ID'si
ROLE_ROOKIE_ID = 1271963998237229090  # Rookie rolü ID'si
ROLE_SISTERS_ID = 1272279945422438481  # Sisters rolü ID'si
BAR_CHANNEL_ID = 1063493716419035289  # Doğum günü kutlama kanalının ID'si

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
    # Belirli bir aralıkla waitroom kanalındaki mesajları temizlemek için görev başlatma
    clean_waitroom.start()

@bot.event
async def on_member_join(member):
    guild = member.guild

    # Stranger rolünü ver
    stranger_role = discord.utils.get(guild.roles, id=ROLE_STRANGER_ID)
    if stranger_role:
        await member.add_roles(stranger_role)

    # Welcome-HB kanalında hoş geldin mesajı gönder
    welcome_channel = guild.get_channel(WELCOME_HB_CHANNEL_ID)
    if welcome_channel:
        async for message in welcome_channel.history(limit=5):
            if message.author == bot.user and member.mention in message.content:
                return
        await welcome_channel.send(f"Hoş geldin {member.mention}! 🎉 Sunucumuza katıldığın için çok mutluyuz!")

    # Kayıt kategorisini al
    register_category = guild.get_channel(REGISTER_CATEGORY_ID)
    if register_category:
        # Kullanıcıya özel bir kayıt kanalı oluştur
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        register_channel = await guild.create_text_channel(
            f'{member.name}-kayıt',
            category=register_category,
            overwrites=overwrites
        )

        # Kurallar mesajını göster
        rules_message = (
            "Burda herkes eşit aminyum.\n"
            "✅ Kabul ediyorum\n"
            "❌ Kabul etmiyorum"
        )
        await send_rules_message(register_channel, member, rules_message)
    
async def send_rules_message(channel, member, rules_message):
    view = discord.view()

    # ✅ butonu
    accept_button = discord.abcbutton(label="Kabul Ediyorum", emoji="✅", style=discord.ButtonStyle.success)
    async def accept_callback(interaction):
        if interaction.user == member:
            await interaction.response.defer()
            await channel.send(f"{member.mention}, Clupta hangi isimle hitap edilmek istersin?")
            registration_manager.start_registration(member.id, channel.id)
            view.stop()
    accept_button.callback = accept_callback

    # ❌ butonu
    reject_button = discord.Button(label="Kabul Etmiyorum", emoji="❌", style=discord.ButtonStyle.danger)
    async def reject_callback(interaction):
        if interaction.user == member:
            await interaction.response.defer()
            await member.kick(reason="Kuralları kabul etmedi.")
            view.stop()
    reject_button.callback = reject_callback

    # Butonları ekle
    view.add_item(accept_button)
    view.add_item(reject_button)

    # Mesajı gönder
    await channel.send(rules_message, view=view)

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

# Sesli kanal işlevleri
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

    new_channel = await ctx.guild.create_voice_channel(name=new_channel_name, category=category)
    await new_channel.set_permissions(ctx.author, connect=True, speak=True)
    await ctx.author.move_to(new_channel)
    await ctx.send(f'{ctx.author.mention} sesli odan hazırr! {new_channel.mention}')

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

@tasks.loop(minutes=7)
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


