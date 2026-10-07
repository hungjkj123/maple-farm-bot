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

def process_image_safely(pil_img):
    """Cắt thẳng vùng góc dưới bên phải (nơi chứa Meso và Quick Slot) để OCR cực kỳ chính xác"""
    width, height = pil_img.size
    # Cắt góc dưới bên phải: từ 60% đến 100% chiều ngang, và từ 85% đến 100% chiều dọc
    box = (int(width * 0.60), int(height * 0.85), width, height)
    cropped = pil_img.crop(box)
    
    # Phóng to và tăng độ tương phản để OCR dễ đọc số
    gray = ImageOps.grayscale(cropped)
    contrast = ImageEnhance.Contrast(gray).enhance(3.5)
    resized = contrast.resize((cropped.width * 3, cropped.height * 3), Image.Resampling.LANCZOS)
    
    return resized

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot đã cập nhật cơ chế đọc vùng an toàn!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm")
@app_commands.describe(image="Ảnh chụp màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        processed_crop = process_image_safely(pil_img)
        text = pytesseract.image_to_string(processed_crop, config='--psm 6')
        
        # Tìm tất cả các con số có từ 6 chữ số trở lên (đặc thù của số Meso)
        all_numbers = re.findall(r'\d+', text.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]
        
        # Tìm số elixir (số ngắn ở quick slot, thường từ 1 đến 4 chữ số)
        valid_elixirs = [int(n) for n in all_numbers if 1 <= len(n) <= 4]

        if valid_mesos:
            meso_val = max(valid_mesos) # Lấy số lớn nhất (chính là Meso)
            elixir_val = valid_elixirs[0] if valid_elixirs else 1070

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
            # Gửi kèm đoạn text OCR để debug nếu vẫn lỗi
            await interaction.followup.send(f"⚠️ Không tìm thấy số Meso. Text đọc được từ ảnh: ```{text}```")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

@bot.tree.command(name="ketthuc", description="Kết thúc ca farm")
@app_commands.describe(image="Ảnh chụp màn hình tổng kết")
async def ketthuc(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    user_id = interaction.user.id
    if user_id not in active_shifts:
        await interaction.followup.send("⚠️ Bạn chưa bắt đầu ca nào cả! Hãy dùng lệnh `/batdau` trước.")
        return

    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        processed_crop = process_image_safely(pil_img)
        text = pytesseract.image_to_string(processed_crop, config='--psm 6')
        
        all_numbers = re.findall(r'\d+', text.replace(',', '').replace('.', ''))
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 6]
        valid_elixirs = [int(n) for n in all_numbers if 1 <= len(n) <= 4]

        if valid_mesos:
            m_end = max(valid_mesos)
            e_end = valid_elixirs[0] if valid_elixirs else 0

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
            await interaction.followup.send(f"⚠️ Không đọc được thông số tổng kết! Text đọc được: ```{text}```")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử/lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
