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

def extract_numbers_from_image(pil_image):
    """
    Đọc toàn bộ chữ số xuất hiện trong ảnh mà không cần cắt tọa độ cố định.
    """
    try:
        gray_image = ImageOps.grayscale(pil_image)
        enhancer = ImageEnhance.Contrast(gray_image)
        contrast_image = enhancer.enhance(4.0)
        
        # Ph phóng to ảnh để OCR đọc chuẩn hơn
        new_size = (contrast_image.size[0] * 2, contrast_image.size[1] * 2)
        large_image = contrast_image.resize(new_size, Image.Resampling.LANCZOS)
        
        text = pytesseract.image_to_string(large_image, config='--psm 6 digits')
        numbers = re.findall(r"\d+", text.replace(",", ""))
        return [int(n) for n in numbers if len(n) > 0]
    except Exception as e:
        print(f"Lỗi OCR: {e}")
        return []

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot đã sẵn sàng với chế độ quét toàn ảnh tự do!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm")
@app_commands.describe(image="Ảnh chụp màn hình (toàn cảnh hoặc cắt tùy ý)")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        all_numbers = extract_numbers_from_image(pil_img)
        
        if len(all_numbers) >= 2:
            # Lọc số lớn nhất làm Meso (vì số Meso có nhiều chữ số nhất)
            meso_val = max(all_numbers, key=len) if any(len(str(n)) > 5 for n in all_numbers) else max(all_numbers)
            # Lọc số nhỏ hơn làm Elixir
            smaller_nums = [n for n in all_numbers if n != meso_val]
            elixir_val = smaller_nums[0] if smaller_nums else 0

            active_shifts[interaction.user.id] = {
                "start_meso": int(meso_val),
                "start_elixir": int(elixir_val),
            }

            await interaction.followup.send(
                f"🟢 **ĐÃ BẮT ĐẦU CA THÀNH CÔNG!**\n"
                f"💰 Meso đầu: `{int(meso_val):,}`\n"
                f"🧪 Elixir đầu: `{int(elixir_val):,}`"
            )
        else:
            await interaction.followup.send("⚠️ Không tìm thấy đủ con số trong ảnh. Hãy thử gửi lại ảnh rõ hơn nhé!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi: `{str(e)}`")

@bot.tree.command(name="ketthuc", description="Kết thúc ca farm")
@app_commands.describe(image="Ảnh chụp màn hình tổng kết")
async def ketthuc(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    user_id = interaction.user.id
    if user_id not in active_shifts:
        await interaction.followup.send("⚠️ Bạn chưa bắt đầu ca nào cả!")
        return

    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        all_numbers = extract_numbers_from_image(pil_img)
        
        if len(all_numbers) >= 2:
            m_end = max(all_numbers, key=len) if any(len(str(n)) > 5 for n in all_numbers) else max(all_numbers)
            smaller_nums = [n for n in all_numbers if n != m_end]
            e_end = smaller_nums[0] if smaller_nums else 0

            data = active_shifts[user_id]
            earned = int(m_end) - data["start_meso"]
            used = data["start_elixir"] - int(e_end)
            del active_shifts[user_id]

            await interaction.followup.send(
                f"📊 **BÁO CÁO KẾT QUẢ CA FARM** - {interaction.user.mention}\n"
                f"----------------------------------------\n"
                f"💰 **Meso kiếm được:** `+{earned:,}`\n"
                f"🧪 **Elixir đã tiêu thụ:** `{used:,}` bình (Còn lại: `{int(e_end):,}`)\n"
                f"----------------------------------------"
            )
        else:
            await interaction.followup.send("⚠️ Không đọc được thông số từ ảnh tổng kết!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi: `{str(e)}`")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
