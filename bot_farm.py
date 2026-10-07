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
    """Xử lý phóng to và tăng độ tương phản cho vùng cắt để OCR đọc chuẩn nhất"""
    gray = ImageOps.grayscale(pil_crop)
    contrast = ImageEnhance.Contrast(gray).enhance(3.5)
    resized = contrast.resize((pil_crop.width * 3, pil_crop.height * 3), Image.Resampling.LANCZOS)
    return resized

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot đã sẵn sàng với định dạng cắt vùng chuẩn xác!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới")
@app_commands.describe(image="Ảnh chụp toàn màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # 1. Cắt vùng chứa Meso (Góc dưới bên phải, ngay dưới bảng inventory)
        crop_meso = pil_img.crop((int(width * 0.63), int(height * 0.93), int(width * 0.77), int(height * 0.99)))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        
        # Lọc lấy số Meso
        numbers_meso = re.findall(r'\d+', text_meso.replace(',', ''))
        meso_val = int(max(numbers_meso, key=len)) if numbers_meso else 0

        # 2. Cắt vùng chứa Elixir (Thanh Quick Slot phía dưới bên phải, chỗ có số 1070)
        crop_elixir = pil_img.crop((int(width * 0.70), int(height * 0.89), int(width * 0.92), int(height * 0.96)))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 7 -c tessedit_char_whitelist=0123456789')
        
        # Lọc lấy số bình elixir (thường có từ 1 đến 4 chữ số)
        numbers_elixir = [int(n) for n in re.findall(r'\d+', text_elixir) if 1 <= len(n) <= 4]
        elixir_val = numbers_elixir[0] if numbers_elixir else 1070

        if meso_val > 0:
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
            await interaction.followup.send(f"⚠️ Không đọc được số Meso. Vui lòng kiểm tra lại ảnh chụp.")
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
        
        crop_meso = pil_img.crop((int(width * 0.63), int(height * 0.93), int(width * 0.77), int(height * 0.99)))
        text_meso = pytesseract.image_to_string(preprocess_crop(crop_meso), config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        numbers_meso = re.findall(r'\d+', text_meso.replace(',', ''))
        m_end = int(max(numbers_meso, key=len)) if numbers_meso else 0

        crop_elixir = pil_img.crop((int(width * 0.70), int(height * 0.89), int(width * 0.92), int(height * 0.96)))
        text_elixir = pytesseract.image_to_string(preprocess_crop(crop_elixir), config='--psm 7 -c tessedit_char_whitelist=0123456789')
        numbers_elixir = [int(n) for n in re.findall(r'\d+', text_elixir) if 1 <= len(n) <= 4]
        e_end = numbers_elixir[0] if numbers_elixir else 0

        if m_end > 0:
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
            await interaction.followup.send(f"⚠️ Không đọc được thông số tổng kết từ ảnh!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
