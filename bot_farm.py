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

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot đã sẵn sàng với chế độ quét toàn ảnh thông minh!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm")
@app_commands.describe(image="Ảnh chụp màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Tiền xử lý toàn bộ ảnh để chữ rõ nét nhất
        gray = ImageOps.grayscale(pil_img)
        contrast = ImageEnhance.Contrast(gray).enhance(3.0)
        text = pytesseract.image_to_string(contrast, config='--psm 6')
        
        # Tìm tất cả các con số có dấu phẩy (dạng Meso: xx,xxx,xxx)
        meso_matches = re.findall(r'\d{1,3},\d{3},\d{3}', text)
        if not meso_matches:
            # Fallback: tìm các chuỗi số dài liên tiếp nếu không có dấu phẩy
            long_nums = [n for n in re.findall(r'\d+', text) if len(n) >= 7]
            meso_val = int(max(long_nums, key=len)) if long_nums else 0
        else:
            meso_val = int(meso_matches[0].replace(',', ''))

        # Tìm số lượng bình elixir (các số ngắn hơn ở vùng quick slot)
        all_nums = [int(n) for n in re.findall(r'\d+', text) if len(n) < 4]
        elixir_val = all_nums[0] if all_nums else 1070 # Mặc định lấy số đầu tiên hoặc số quen thuộc

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
            await interaction.followup.send("⚠️ Không tìm thấy số Meso trong ảnh. Bạn hãy kiểm tra lại khung hình nhé!")
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
        
        gray = ImageOps.grayscale(pil_img)
        contrast = ImageEnhance.Contrast(gray).enhance(3.0)
        text = pytesseract.image_to_string(contrast, config='--psm 6')
        
        meso_matches = re.findall(r'\d{1,3},\d{3},\d{3}', text)
        if not meso_matches:
            long_nums = [n for n in re.findall(r'\d+', text) if len(n) >= 7]
            m_end = int(max(long_nums, key=len)) if long_nums else 0
        else:
            m_end = int(meso_matches[0].replace(',', ''))

        all_nums = [int(n) for n in re.findall(r'\d+', text) if len(n) < 4]
        e_end = all_nums[0] if all_nums else 0

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
            await interaction.followup.send("⚠️ Không đọc được thông số từ ảnh tổng kết!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
