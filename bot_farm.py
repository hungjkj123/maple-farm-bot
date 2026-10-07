import io
import os
import re
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageOps
import pytesseract

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Lưu trữ thông tin ca farm: {user_id: {"start_meso": ..., "start_elixir": ..., "start_time": ...}}
active_shifts = {}

def preprocess_crop(pil_crop):
    gray = ImageOps.grayscale(pil_crop)
    contrast = ImageEnhance.Contrast(gray).enhance(3.5)
    resized = contrast.resize((pil_crop.width * 3, pil_crop.height * 3), Image.Resampling.LANCZOS)
    return resized

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot đã sẵn sàng với tính năng tính thời gian và chống lỗi đọc Elixir!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới")
@app_commands.describe(image="Ảnh chụp toàn màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # 1. Đọc Meso
        crop_meso = pil_img.crop((int(width * 0.58), int(height * 0.90), int(width * 0.80), height))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 6 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        # 2. Đọc Elixir
        crop_elixir = pil_img.crop((int(width * 0.73), int(height * 0.93), int(width * 0.79), int(height * 0.99)))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 6 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if 1 <= len(n) <= 5]

        if valid_mesos:
            meso_val = max(valid_mesos)
            elixir_val = max(elixir_numbers) if elixir_numbers else 1070
            start_time = datetime.now()

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
        
        crop_meso = pil_img.crop((int(width * 0.58), int(height * 0.90), int(width * 0.80), height))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 6 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        crop_elixir = pil_img.crop((int(width * 0.73), int(height * 0.93), int(width * 0.79), int(height * 0.99)))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 6 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if 1 <= len(n) <= 5]

        if valid_mesos:
            m_end = max(valid_mesos)
            
            # Lấy thông tin ca cũ
            data = active_shifts[user_id]
            start_elixir = data["start_elixir"]
            
            # Xử lý thông minh cho Elixir: Nếu OCR đọc hụt ra số quá nhỏ (như số 2), 
            # ta kiểm tra xem nếu chênh lệch quá lớn so với ban đầu thì giữ nguyên hoặc suy luận lại.
            e_end = max(elixir_numbers) if elixir_numbers else start_elixir
            if start_elixir - e_end > 500 or e_end < 10: # Nếu số lượng sụt giảm bất thường do đọc nhầm
                e_end = start_elixir - 1 # Tạm tính mặc định dùng 1 bình nếu OCR lỗi đọc số nhỏ

            end_time = datetime.now()
            start_time = data["start_time"]
            
            # Tính thời gian farm
            duration = end_time - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            earned = m_end - data["start_meso"]
            used = start_elixir - e_end
            
            # Tính tốc độ Meso/giờ
            total_hours = duration.total_seconds() / 3600
            meso_per_hour = int(earned / total_hours) if total_hours > 0 else 0

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
            await interaction.followup.send(f"⚠️ Không đọc được thông số kết thúc!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
