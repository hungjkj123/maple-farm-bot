import io
import os
import re
from datetime import datetime, timezone, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps
import pytesseract

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_shifts = {}

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

def preprocess_crop(pil_crop):
    # Phóng to gấp 4 lần để OCR dễ đọc nét chữ nhỏ trong game
    resized = pil_crop.resize((pil_crop.width * 4, pil_crop.height * 4), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(resized)
    
    # Chuyển đổi nhị phân tuyệt đối (Thresholding) để xóa sạch bóng mờ/anti-aliasing của font game
    # Chỉnh ngưỡng (threshold) tùy thuộc vào độ sáng của chữ số trong game
    threshold = 170
    binary = gray.point(lambda p: 255 if p > threshold else 0)
    return binary

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot đã sẵn sàng với bộ lọc nhị phân chuẩn font game!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới")
@app_commands.describe(image="Ảnh chụp toàn màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # 1. Đọc Meso (Vùng tọa độ góc dưới bên phải)
        crop_meso = pil_img.crop((int(width * 0.60), int(height * 0.95), int(width * 0.72), int(height * 0.99)))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        # 2. Đọc Elixir
        crop_elixir = pil_img.crop((int(width * 0.72), int(height * 0.95), int(width * 0.77), int(height * 0.99)))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 7 -c tessedit_char_whitelist=0123456789')
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
                f"💰 Meso ban đầu: `{meso_val:,}`\n"
                f"🧪 Elixir ban đầu: `{elixir_val:,}`"
            )
        else:
            await interaction.followup.send(f"⚠️ Không đọc được số Meso ban đầu. Vui lòng kiểm tra lại ảnh.")
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
        
        # 1. Đọc Meso kết thúc
        crop_meso = pil_img.crop((int(width * 0.60), int(height * 0.95), int(width * 0.72), int(height * 0.99)))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        # 2. Đọc Elixir kết thúc
        crop_elixir = pil_img.crop((int(width * 0.72), int(height * 0.95), int(width * 0.77), int(height * 0.99)))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 7 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if len(n) >= 2]

        if valid_mesos:
            m_end = max(valid_mesos)
            data = active_shifts[user_id]
            start_meso = data["start_meso"]
            start_elixir = data["start_elixir"]
            
            e_end = next((n for n in elixir_numbers if 100 <= n <= 9999), start_elixir)
            if start_elixir - e_end > 500 or e_end < 10:
                e_end = start_elixir

            end_time = datetime.now(VN_TZ)
            start_time = data["start_time"]
            
            duration = end_time - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            earned = m_end - start_meso
            if earned < 0:
                earned = 0

            used = start_elixir - e_end
            if used < 0:
                used = 0
            
            total_hours = duration.total_seconds() / 3600
            meso_per_hour = int(earned / total_hours) if total_hours > 0 else earned

            del active_shifts[user_id]

            time_start_str = start_time.strftime("%H:%M")
            time_end_str = end_time.strftime("%H:%M")
            time_duration_str = f"{hours} giờ {minutes} phút" if hours > 0 else f"{minutes} phút"

            await interaction.followup.send(
                f"📊 **BÁO CÁO KẾT QUẢ CA FARM** - {interaction.user.mention}\n"
                f"----------------------------------------\n"
                f"⏱️ **Thời gian bắt đầu:** `{time_start_str}`\n"
                f"⏱️ **Thời gian kết thúc:** `{time_end_str}`\n"
                f"⏳ **Tổng thời gian farm:** `{time_duration_str}`\n"
                f"💰 **Lượng meso ban đầu:** `{start_meso:,}`\n"
                f"💰 **Lượng meso khi kết thúc:** `{m_end:,}`\n"
                f"💵 **Lượng meso kiếm được:** `+{earned:,}` `(~{meso_per_hour:,} Meso/h)`\n"
                f"🧪 **Bình elixir đã tiêu thụ:** `{used:,}` bình (Còn lại: `{e_end:,}`)\n"
                f"----------------------------------------"
            )
        else:
            await interaction.followup.send(f"⚠️ Không đọc được thông số kết thúc! Vui lòng thử lại.")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
