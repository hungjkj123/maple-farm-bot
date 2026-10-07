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

def get_text_from_image(pil_img):
    """Xử lý toàn bộ ảnh để trích xuất số tốt nhất"""
    # Chuyển ảnh xám, tăng độ tương phản mạnh để làm nổi bật chữ trắng trên nền tối
    gray = ImageOps.grayscale(pil_img)
    contrast = ImageEnhance.Contrast(gray).enhance(4.0)
    
    # Dùng psm 11 (Sparse text) để tìm tất cả các cụm số xuất hiện rải rác trên ảnh
    config_psm11 = '--psm 11 -c tessedit_char_whitelist=0123456789,'
    text_psm11 = pytesseract.image_to_string(contrast, config=config_psm11)
    
    # Dùng thêm psm 6 để quét toàn trang phòng hờ
    config_psm6 = '--psm 6'
    text_psm6 = pytesseract.image_to_string(contrast, config=config_psm6)
    
    return text_psm11 + "\n" + text_psm6

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot đã sẵn sàng quét số toàn cục!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm")
@app_commands.describe(image="Ảnh chụp màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        text = get_text_from_image(pil_img)
        
        # Tìm tất cả các chuỗi số có định dạng từ 7 chữ số trở lên (đặc trưng của Meso như 51118887 hoặc 51,118,887)
        clean_text = text.replace(',', '')
        all_numbers = re.findall(r'\d+', clean_text)
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 7]
        
        # Tìm số elixir (các số ngắn từ 1 đến 4 chữ số)
        valid_elixirs = [int(n) for n in all_numbers if 1 <= len(n) <= 4]

        if valid_mesos:
            meso_val = max(valid_mesos) # Số lớn nhất chính là số Meso
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
            await interaction.followup.send(f"⚠️ Không tìm thấy số Meso. Các số bot quét được từ ảnh: `{all_numbers}`")
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
        
        text = get_text_from_image(pil_img)
        clean_text = text.replace(',', '')
        all_numbers = re.findall(r'\d+', clean_text)
        valid_mesos = [int(n) for n in all_numbers if len(n) >= 7]
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
            await interaction.followup.send(f"⚠️ Không đọc được số Meso tổng kết! Các số quét được: `{all_numbers}`")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
