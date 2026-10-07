import io
import os
import re
from datetime import datetime, timezone, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageOps
import pytesseract

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_shifts = {}

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

def preprocess_crop(pil_crop):
    gray = ImageOps.grayscale(pil_crop)
    contrast = ImageEnhance.Contrast(gray).enhance(3.5)
    resized = contrast.resize((pil_crop.width * 3, pil_crop.height * 3), Image.Resampling.LANCZOS)
    return resized

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot đã sẵn sàng với bộ lọc Meso thông minh chống đọc nhầm!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới")
@app_commands.describe(image="Ảnh chụp toàn màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # 1. Đọc Meso (Giới hạn chuẩn xác vùng chứa số Meso)
        crop_meso = pil_img.crop((int(width * 0.63), int(height * 0.93), int(width * 0.72), int(height * 0.98)))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 6 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        # 2. Đọc Elixir
        crop_elixir = pil_img.crop((int(width * 0.72), int(height * 0.92), int(width * 0.79), height))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 6 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if len(n) >= 2]
        elixir_val = next((n for n in elixir_numbers if 100 <= n <= 9999), 1069)

        if valid_mesos:
            meso_val = max(valid_mesos)
            start_time = datetime.now(VN_TZ)

            active_shifts[interaction.user.id] = {
                "start_meso": meso_val,
                "start_elixir": elixir_val,
                "start_time": start_time
            }
            
            time_str = start_time.strftime("%H:%M")
            await interaction.followup.send(
                f"🟢 **ĐÃ BẮT ĐẦU CA THÀNH CÔNG!**\n"
                f"⏱️ Thời gian bắt đầu: `{time_str}`\n"
                f"💰 Meso đầu: `{meso_val:,}`\n"
                f"🧪 Elixir đầu: `{elixir_val:,}`"
            )
        else:
            await interaction.followup.send(f"⚠️ Không đọc được số Meso. Vui lòng kiểm tra lại ảnh.")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

@bot.tree.command(name="ketthuc", description="Kết thúc ca farm và nhận báo cáo")
@app_commands.describe(image="Ảnh chụp toàn màn hình tổng kết")
async def ketthuc(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    user_id = interaction.user.id
    if user_id not in active_shifts:
        await interaction.followup.send("⚠️ Bạn chưa bắt đầu ca nào cả! Hãy dùng lệnh `/batdau` trước.")
        return

    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # 1. Đọc Meso kết thúc với vùng crop chuẩn xác tương tự
        crop_meso = pil_img.crop((int(width * 0.63), int(height * 0.93), int(width * 0.72), int(height * 0.98)))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 6 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        # 2. Đọc Elixir
        crop_elixir = pil_img.crop((int(width * 0.72), int(height * 0.92), int(width * 0.79), height))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 6 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if len(n) >= 2]

        if valid_mesos:
            m_end = max(valid_mesos)
            data = active_shifts[user_id]
            start_elixir = data["start_elixir"]
            
            e_end = next((n for n in elixir_numbers if 100 <= n <= 9999), start_elixir)
            if start_elixir - e_end > 500 or e_end < 10:
                e_end = start_elixir

            end_time = datetime.now(VN_TZ)
            start_time = data["start_time"]
            
            duration = end_time - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            earned = m_end - data["start_meso"]
            
            # Kiểm tra chống đọc nhầm số âm hoặc nhảy số quá vô lý
            if earned < 0:
                earned = 0

            used = start_elixir - e_end
            
            total_hours = duration.total_seconds() / 3600
            meso_per_hour = int(earned / total_hours) if total_hours > 0 else earned

            del active_shifts[user_id]

            time_start_str = start_time.strftime("%H:%M")
            time_end_str = end_time.strftime("%H:%M")
            time_duration_str = f"{hours} giờ {minutes} phút" if hours > 0 else f"{minutes} phút"

            await interaction.followup.send(
                f"📊 **BÁO CÁO KẾT QUẢ CA FARM** - {interaction.user.mention}\n"
                f"----------------------------------------\n"
                f"⏱️ **Bắt đầu:** `{time_start_str}` | **Kết thúc:** `{time_end_str}`\n"
                f"⏳ **Tổng thời gian:** `{time_duration_str}`\n"
                f"💰 **Meso kiếm được:** `+{earned:,}` `(~{meso_per_hour:,} Meso/h)`\n"
                f"🧪 **Elixir đã tiêu thụ:** `{used:,}` bình (Còn lại: `{e_end:,}`)\n"
                f"----------------------------------------"
            )
        else:
            await interaction.followup.send(f"⚠️ Không đọc được thông số kết thúc! Vui lòng thử lại.")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
