import io
import os
import re
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageOps
import pytesseract

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_shifts = {}

def preprocess_crop(pil_crop):
    gray = ImageOps.grayscale(pil_crop)
    contrast = ImageEnhance.Contrast(gray).enhance(3.5)
    resized = contrast.resize((pil_crop.width * 3, pil_crop.height * 3), Image.Resampling.LANCZOS)
    return resized

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot đã sẵn sàng với code chuẩn chỉnh!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới")
@app_commands.describe(image="Ảnh chụp toàn màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # 1. Đọc Meso
        crop_meso = pil_img.crop((int(width * 0.58), int(height * 0.90), int(width * 0.72), height))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        # 2. Đọc Elixir (Sửa lại vùng cắt và config Tesseract chuẩn)
        crop_elixir = pil_img.crop((int(width * 0.72), int(height * 0.93), int(width * 0.78), height))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 7 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if 1 <= len(n) <= 5]

        if valid_mesos:
            meso_val = max(valid_mesos)
            elixir_val = max(elixir_numbers) if elixir_numbers else 1070

            active_shifts[interaction.user.id] = {
                "start_meso": meso_val,
                "start_elixir": elixir_val,
            }
            await interaction.followup.send(
                f"🟢 **ĐÃ BẮT ĐẦU CA THÀNH CÔNG!**\n"
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
        
        crop_meso = pil_img.crop((int(width * 0.58), int(height * 0.90), int(width * 0.72), height))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        all_numbers = re.findall(r'\d+', text_meso.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]

        crop_elixir = pil_img.crop((int(width * 0.72), int(height * 0.93), int(width * 0.78), height))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 7 -c tessedit_char_whitelist=0123456789')
        elixir_numbers = [int(n) for n in re.findall(r'\d+', text_elixir) if 1 <= len(n) <= 5]

        if valid_mesos:
            m_end = max(valid_mesos)
            e_end = max(elixir_numbers) if elixir_numbers else 0

            data = active_shifts[user_id]
            earned = m_end - data["start_meso"]
            used = data["start_elixir"] - e_end
            del active_shifts[user_id]

            await interaction.followup.send(
                f"📊 **BÁO CÁO KẾT QUẢ CA FARM** - {interaction.user.mention}\n"
                f"----------------------------------------\n"
                f"💰 **Meso kiếm được:** `+{earned:,}`\n"
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
