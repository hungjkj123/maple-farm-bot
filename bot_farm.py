import os
from datetime import datetime, timezone, timedelta
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_shifts = {}

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot nhập tay đã sẵn sàng hoạt động!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới")
@app_commands.describe(
    meso_ban_dau="Lượng meso ban đầu (Ví dụ: 50658887)",
    elixir_ban_dau="Số lượng bình elixir ban đầu (Ví dụ: 1069)"
)
async def batdau(interaction: discord.Interaction, meso_ban_dau: int, elixir_ban_dau: int):
    start_time = datetime.now(VN_TZ)
    
    active_shifts[interaction.user.id] = {
        "start_meso": meso_ban_dau,
        "start_elixir": elixir_ban_dau,
        "start_time": start_time
    }
    
    time_str = start_time.strftime("%H:%M")
    await interaction.response.send_message(
        f"🟢 **ĐÃ BẮT ĐẦU CA THÀNH CÔNG!**\n"
        f"⏱️ Thời gian bắt đầu: `{time_str}`\n"
        f"💰 Meso ban đầu: `{meso_ban_dau:,}`\n"
        f"🧪 Elixir ban đầu: `{elixir_ban_dau:,}`"
    )

@bot.tree.command(name="ketthuc", description="Kết thúc ca farm và nhận báo cáo")
@app_commands.describe(
    meso_ket_thuc="Lượng meso khi kết thúc",
    elixir_con_lai="Số lượng bình elixir còn lại khi kết thúc"
)
async def ketthuc(interaction: discord.Interaction, meso_ket_thuc: int, elixir_con_lai: int):
    user_id = interaction.user.id
    if user_id not in active_shifts:
        await interaction.response.send_message("⚠️ Bạn chưa bắt đầu ca nào cả! Hãy dùng lệnh `/batdau` trước.", ephemeral=True)
        return

    data = active_shifts[user_id]
    start_meso = data["start_meso"]
    start_elixir = data["start_elixir"]
    start_time = data["start_time"]
    end_time = datetime.now(VN_TZ)
    
    # Tính toán thời gian
    duration = end_time - start_time
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)
    
    # Tính toán Meso
    earned = meso_ket_thuc - start_meso
    if earned < 0:
        earned = 0
        
    total_hours = duration.total_seconds() / 3600
    meso_per_hour = int(earned / total_hours) if total_hours > 0 else earned

    # Tính toán Elixir tiêu thụ = Ban đầu - Còn lại
    used = start_elixir - elixir_con_lai
    if used < 0:
        used = 0

    del active_shifts[user_id]

    time_start_str = start_time.strftime("%H:%M")
    time_end_str = end_time.strftime("%H:%M")
    time_duration_str = f"{hours} giờ {minutes} phút" if hours > 0 else f"{minutes} phút"

    await interaction.response.send_message(
        f"📊 **BÁO CÁO KẾT QUẢ CA FARM** - {interaction.user.mention}\n"
        f"----------------------------------------\n"
        f"⏱️ **Thời gian bắt đầu:** `{time_start_str}`\n"
        f"⏱️ **Thời gian kết thúc:** `{time_end_str}`\n"
        f"⏳ **Tổng thời gian farm:** `{time_duration_str}`\n"
        f"💰 **Lượng meso ban đầu:** `{start_meso:,}`\n"
        f"💰 **Lượng meso khi kết thúc:** `{meso_ket_thuc:,}`\n"
        f"💵 **Lượng meso kiếm được:** `+{earned:,}` `(~{meso_per_hour:,} Meso/h)`\n"
        f"🧪 **Bình elixir đã tiêu thụ:** `{used:,}` bình (Còn lại: `{elixir_con_lai:,}`)\n"
        f"----------------------------------------"
    )

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
