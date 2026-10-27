import os

import asyncio

from flask import Flask

from threading import Thread

import discord

from discord.ext import commands



# --- BURAYA 2 KİŞİNİN BİLGİLERİNİ YAZ ---

TOKEN = "BURAYA_BOTUNUN_TOKENINI_YAZ"



# 2 Farklı Bot Sahibinin Discord ID'sini buraya sayı olarak yaz:

OWNERS = {

    1547400739775844356, # 1. Sahibin ID'si

    1506368638897356941  # 2. Sahibin ID'si

}



# --- RENDER / UPTIME UYUMLU FLASK SUNUCUSU ---

app = Flask('')



@app.route('/')

def home():

    return "Bot aktif ve çalışıyor!"



def run_flask():

    app.run(host='0.0.0.0', port=8080)



def keep_alive():

    t = Thread(target=run_flask)

    t.start()



# --- DISCORD BOT AYARLARI ---

intents = discord.Intents.default()

intents.guilds = True

intents.members = True

intents.moderation = True

intents.guild_messages = True

intents.message_content = True



bot = commands.Bot(command_prefix="!", intents=intents)



# Whitelist listesine doğrudan 2 owner otomatik eklenir

whitelist = set(OWNERS)



def is_whitelisted(member_id: int) -> bool:

    return member_id in whitelist or member_id in OWNERS



@bot.event

async def on_ready():

    print(f"[{bot.user}] olarak giriş yapıldı ve koruma sistemi aktif!")

    print(f"Bot Sahipleri (Owners) ID'leri: {OWNERS}")



# --- YETKİ & MUAFİYET KOMUTLARI ---

@bot.command(name="yetkili-ekle")

async def yetkili_ekle(ctx, member: discord.Member):

    if ctx.author.id not in OWNERS:

        await ctx.send("❌ Bu komutu sadece Bot Sahipleri kullanabilir.")

        return

    

    whitelist.add(member.id)

    await ctx.send(f"✅ {member.mention} başarıyla koruma whitelist listesine eklendi.")



@bot.command(name="yetkili-sil")

async def yetkili_sil(ctx, member: discord.Member):

    if ctx.author.id not in OWNERS:

        await ctx.send("❌ Bu komutu sadece Bot Sahipleri kullanabilir.")

        return

    

    if member.id in OWNERS:

        await ctx.send("❌ Bot sahiplerini listeden çıkaramazsın.")

        return



    whitelist.discard(member.id)

    await ctx.send(f"🗑️ {member.mention} whitelist listesinden kaldırıldı.")





# --- 1. KANAL KORUMASI ---

@bot.event

async def on_guild_channel_delete(channel):

    guild = channel.guild

    try:

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):

            user = entry.user

            if user.bot or is_whitelisted(user.id):

                return

            

            await guild.ban(user, reason="İzinsiz Kanal Silme Koruması")

            

            if isinstance(channel, discord.TextChannel):

                await guild.create_text_channel(

                    name=channel.name,

                    category=channel.category,

                    topic=channel.topic,

                    slowmode_delay=channel.slowmode_delay,

                    nsfw=channel.nsfw,

                    overwrites=channel.overwrites,

                    position=channel.position,

                    reason="Kanal Silindiği İçin Geri Oluşturuldu"

                )

            elif isinstance(channel, discord.VoiceChannel):

                await guild.create_voice_channel(

                    name=channel.name,

                    category=channel.category,

                    bitrate=channel.bitrate,

                    user_limit=channel.user_limit,

                    overwrites=channel.overwrites,

                    position=channel.position,

                    reason="Ses Kanalı Silindiği İçin Geri Oluşturuldu"

                )

            elif isinstance(channel, discord.CategoryChannel):

                await guild.create_category(

                    name=channel.name,

                    overwrites=channel.overwrites,

                    position=channel.position,

                    reason="Kategori Silindiği İçin Geri Oluşturuldu"

                )

    except Exception as e:

        print(f"Kanal koruma hatası: {e}")





# --- 2. KANAL EKLEME KORUMASI ---

@bot.event

async def on_guild_channel_create(channel):

    guild = channel.guild

    try:

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):

            user = entry.user

            if user.bot or is_whitelisted(user.id):

                return

            

            await guild.ban(user, reason="İzinsiz Kanal / Kategori Açma Koruması")

            await channel.delete(reason="İzinsiz açılan kanal imha edildi.")

    except Exception as e:

        print(f"Kanal ekleme koruma hatası: {e}")





# --- 3. ROL KORUMASI ---

@bot.event

async def on_guild_role_delete(role):

    guild = role.guild

    try:

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):

            user = entry.user

            if user.bot or is_whitelisted(user.id):

                return

            

            await guild.ban(user, reason="İzinsiz Rol Silme Koruması")

            await guild.create_role(

                name=role.name,

                permissions=role.permissions,

                colour=role.colour,

                hoist=role.hoist,

                mentionable=role.mentionable,

                reason="Silinen Rol Geri Oluşturuldu"

            )

    except Exception as e:

        print(f"Rol koruma hatası: {e}")





# --- 4. SUNUCU GÖRÜNÜMÜ & AYARLARI KORUMASI ---

@bot.event

async def on_guild_update(before, after):

    guild = after

    try:

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):

            user = entry.user

            if user.bot or is_whitelisted(user.id):

                return



            if before.name != after.name or before.description != after.description or before.verification_level != after.verification_level:

                await guild.edit(

                    name=before.name,

                    description=before.description,

                    verification_level=before.verification_level,

                    reason="Sunucu ayarları izinsiz değiştirildi."

                )

                await guild.ban(user, reason="Sunucu Ayarlarını Değiştirme Koruması")

            

            if before.icon != after.icon or before.banner != after.banner:

                await guild.ban(user, reason="İzinsiz İkon/Afiş Değiştirme Koruması")

    except Exception as e:

        print(f"Sunucu güncelleme koruma hatası: {e}")





# --- 5. BOT KORUMASI ---

@bot.event

async def on_member_join(member):

    if member.bot:

        guild = member.guild

        try:

            await asyncio.sleep(0.3)

            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):

                user = entry.user

                if user.bot or is_whitelisted(user.id):

                    return

                

                await guild.ban(member, reason="İzinsiz Bot Girişi")

                await guild.ban(user, reason="Sunucuya İzinsiz Bot Soktu")

        except Exception as e:

            print(f"Bot koruma hatası: {e}")





# --- 6. DAVET & LİNK REKLAM KORUMASI ---

@bot.event

async def on_message(message):

    if message.author.bot or not message.guild:

        return

    

    if is_whitelisted(message.author.id):

        await bot.process_commands(message)

        return



    content = message.content.lower()

    reklam_tetikleyicileri = ["http://", "https://", "discord.gg/", ".com", ".net", ".org", "discord.com/invite"]



    if any(reklami in content for reklami in reklam_tetikleyicileri):

        try:

            await message.delete()

            warning_msg = await message.channel.send(f"{message.author.mention}, bu sunucuda link ve reklam paylaşımı yasaktır!")

            await asyncio.sleep(5)

            await warning_msg.delete()

        except Exception as e:

            print(f"Reklam engelleme hatası: {e}")

            

    await bot.process_commands(message)



# Botu başlat ve Uptime sunucusunu devreye sok

if __name__ == "__main__":

    keep_alive()

    bot.run(TOKEN)