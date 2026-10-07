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

def preprocess_image(pil_image):
    """Tiền xử lý ảnh để Tesseract đọc số chính xác nhất."""
    try:
        gray = ImageOps.grayscale(pil_image)
        contrast = ImageEnhance.Contrast(gray).enhance(3.0)
        new_size = (contrast.size[0] * 2, contrast.size[1] * 2)
        large = contrast.resize(new_size, Image.Resampling.LANCZOS)
        binary = large.point(lambda p: 255 if p > 130 else 0)
        return binary
    except Exception:
        return pil_image

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot {bot.user} đã sẵn sàng với tọa độ chuẩn!")

@bot.tree.command(name="batdau", description="Bắt đầu ca farm mới từ ảnh chụp màn hình")
@app_commands.describe(image="Ảnh chụp toàn màn hình game")
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        image_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        
        # --- Cắt vùng chứa Meso (Dựa trên vị trí bảng Inventory ở góc dưới bên phải) ---
        crop_meso = pil_img.crop((int(width * 0.63), int(height * 0.93), int(width * 0.77), int(height * 0.99)))
        text_meso = pytesseract.image_to_string(preprocess_image(crop_meso), config='--psm 7 digits')
        numbers_meso = re.findall(r"\d+", text_meso.replace(",", ""))

        # --- Cắt vùng chứa Elixir (Thanh Quick Slot phía dưới) ---
        crop_elixir = pil_img.crop((int(width * 0.35), int(height * 0.93), int(width * 0.58), height))
        text_elixir = pytesseract.image_to_string(preprocess_image(crop_elixir), config='--psm 6 digits')
        numbers_elixir = re.findall(r"\d+", text_elixir.replace(",", ""))
        valid_elixir = [n for n in numbers_elixir if len(n) < 4]

        if numbers_meso:
            meso_val = int(max(numbers_meso, key=len))
            elixir_val = int(valid_elixir[0]) if valid_elixir else 0

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
            await interaction.followup.send("⚠️ Không đọc được số Meso. Hãy đảm bảo bạn gửi ảnh toàn màn hình giữ nguyên khung như mẫu nhé!")
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
        text_meso = pytesseract.image_to_string(preprocess_image(crop_meso), config='--psm 7 digits')
        numbers_meso = re.findall(r"\d+", text_meso.replace(",", ""))

        crop_elixir = pil_img.crop((int(width * 0.35), int(height * 0.93), int(width * 0.58), height))
        text_elixir = pytesseract.image_to_string(preprocess_image(crop_elixir), config='--psm 6 digits')
        numbers_elixir = re.findall(r"\d+", text_elixir.replace(",", ""))
        valid_elixir = [n for n in numbers_elixir if len(n) < 4]

        if numbers_meso:
            m_end = int(max(numbers_meso, key=len))
            e_end = int(valid_elixir[0]) if valid_elixir else 0

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
